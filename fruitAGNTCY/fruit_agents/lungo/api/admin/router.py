# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

"""Admin endpoints — verify caller-supplied LLM credentials without persisting them.

This is intentionally limited to a one-shot probe. Cluster Secrets are not
modified; the caller's key is held only for the duration of the request.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Awaitable, Callable, Literal, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.admin.models_catalog import ModelInfo, Provider as CatalogProvider, list_models
from common import active_llm_config

RebuildHook = Callable[[], Union[None, Awaitable[None]]]


# NB: keep these Pydantic models at module level. Defining them inside
# ``create_admin_router`` triggers a FastAPI/Pydantic introspection quirk
# where the parameter is treated as a query string instead of a JSON body.


class LLMModelsRequest(BaseModel):
    provider: CatalogProvider
    api_key: str = Field(min_length=1)
    base_url: Optional[str] = None
    api_version: Optional[str] = None


class LLMModelsResponse(BaseModel):
    ok: bool
    models: list[ModelInfo]
    message: Optional[str] = None


class ActiveConfigPayload(BaseModel):
    provider: CatalogProvider
    api_key: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: Optional[str] = None
    api_version: Optional[str] = None


class ActiveConfigResponse(BaseModel):
    ok: bool
    component: str
    active: Optional[active_llm_config.ActiveLLMConfigPublic] = None
    rebuilt: bool
    message: Optional[str] = None

logger = logging.getLogger("lungo.admin.router")

Provider = Literal["openai", "azure", "anthropic"]


class LLMTestRequest(BaseModel):
    provider: Provider
    api_key: str = Field(min_length=1)
    model: str = Field(min_length=1)
    base_url: Optional[str] = None
    api_version: Optional[str] = None


class LLMTestResponse(BaseModel):
    ok: bool
    message: str
    reply: Optional[str] = None
    provider: Provider
    model: str
    latency_ms: int


def _build_litellm_kwargs(req: LLMTestRequest) -> dict:
    # Note: no ``temperature`` override — gpt-5* / o-series reasoning models
    # reject anything other than 1, and the default already is 1. We rely on
    # ``litellm.drop_params = True`` (set in common/llm.py) to handle the
    # ``max_tokens`` -> ``max_completion_tokens`` translation when needed.
    kwargs: dict = {
        "messages": [
            {
                "role": "user",
                "content": "Reply with the single word: pong",
            }
        ],
        # Reasoning models (gpt-5*, o1*, o3*) consume tokens for internal
        # reasoning before emitting output, so 16 is too tight. 512 still
        # caps spend on a probe but leaves room for reasoning + a one-word
        # reply. ``drop_params`` translates this to max_completion_tokens.
        "max_tokens": 512,
        "api_key": req.api_key,
        "timeout": 30,
        "drop_params": True,
    }
    if req.provider == "openai":
        kwargs["model"] = req.model
        if req.base_url:
            kwargs["api_base"] = req.base_url
    elif req.provider == "azure":
        if not req.base_url:
            raise HTTPException(
                status_code=400,
                detail="base_url is required for Azure (e.g. https://<resource>.openai.azure.com).",
            )
        if not req.api_version:
            raise HTTPException(
                status_code=400,
                detail="api_version is required for Azure (e.g. 2024-02-15-preview).",
            )
        kwargs["model"] = f"azure/{req.model}"
        kwargs["api_base"] = req.base_url
        kwargs["api_version"] = req.api_version
    elif req.provider == "anthropic":
        kwargs["model"] = (
            req.model if req.model.startswith("anthropic/") else f"anthropic/{req.model}"
        )
    return kwargs


def create_admin_router(
    *,
    rebuild_hook: Optional[RebuildHook] = None,
    component_name: str = "agentic-workflows-api",
) -> APIRouter:
    """Create the admin router.

    Args:
      rebuild_hook: callback invoked after a successful POST /admin/active-config.
        Use it to swap the in-memory graph in supervisors so the new model is
        used by the very next prompt. If async, it's awaited; if sync, it's
        called directly.
      component_name: short name reported back in /admin/active-config so the
        UI can show which supervisors accepted the change.
    """

    router = APIRouter(prefix="/admin", tags=["admin"])

    @router.post("/llm/test", response_model=LLMTestResponse)
    async def test_llm(req: LLMTestRequest) -> LLMTestResponse:
        try:
            import litellm
        except ImportError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"litellm is not installed: {exc}",
            )
        litellm.drop_params = True

        kwargs = _build_litellm_kwargs(req)
        started = time.perf_counter()
        try:
            response = await litellm.acompletion(**kwargs)
            latency_ms = int((time.perf_counter() - started) * 1000)
            reply = ""
            try:
                reply = response.choices[0].message.content or ""
            except Exception:  # pragma: no cover — defensive
                reply = ""
            logger.info(
                "LLM probe ok provider=%s model=%s latency_ms=%d",
                req.provider,
                req.model,
                latency_ms,
            )
            return LLMTestResponse(
                ok=True,
                message="Credentials accepted; model responded.",
                reply=reply.strip() or None,
                provider=req.provider,
                model=req.model,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            err_text = str(exc)
            logger.warning(
                "LLM probe failed provider=%s model=%s latency_ms=%d err=%s",
                req.provider,
                req.model,
                latency_ms,
                err_text[:200],
            )
            return LLMTestResponse(
                ok=False,
                message=err_text or "Probe failed",
                provider=req.provider,
                model=req.model,
                latency_ms=latency_ms,
            )

    @router.post("/llm/models", response_model=LLMModelsResponse)
    async def list_llm_models(req: LLMModelsRequest) -> LLMModelsResponse:
        """Return the models this key can access, enriched with context/cost.

        OpenAI / Azure / Anthropic each have a different listing API; the
        results are normalised through ``api.admin.models_catalog.list_models``.
        """
        try:
            models = await list_models(
                req.provider,
                req.api_key,
                base_url=req.base_url,
                api_version=req.api_version,
            )
            logger.info(
                "Models listed provider=%s count=%d", req.provider, len(models)
            )
            return LLMModelsResponse(ok=True, models=models)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            err = str(exc)
            logger.warning(
                "Models listing failed provider=%s err=%s",
                req.provider,
                err[:200],
            )
            return LLMModelsResponse(ok=False, models=[], message=err)

    @router.get("/active-config", response_model=ActiveConfigResponse)
    async def get_active_config() -> ActiveConfigResponse:
        return ActiveConfigResponse(
            ok=True,
            component=component_name,
            active=active_llm_config.get_active_public(),
            rebuilt=False,
        )

    @router.post("/active-config", response_model=ActiveConfigResponse)
    async def set_active_config(req: ActiveConfigPayload) -> ActiveConfigResponse:
        cfg = active_llm_config.ActiveLLMConfig(**req.model_dump())
        active_llm_config.apply(cfg)
        rebuilt = False
        msg: Optional[str] = None
        if rebuild_hook is not None:
            try:
                result = rebuild_hook()
                if asyncio.iscoroutine(result):
                    await result
                rebuilt = True
            except Exception as exc:
                # Config is applied even if rebuild failed; surface the error
                # so the UI can show it but don't roll back the env vars.
                msg = f"applied but rebuild failed: {exc}"
                logger.warning(
                    "Active config applied but rebuild_hook failed on %s: %s",
                    component_name,
                    exc,
                )
        return ActiveConfigResponse(
            ok=True,
            component=component_name,
            active=active_llm_config.get_active_public(),
            rebuilt=rebuilt,
            message=msg,
        )

    @router.delete("/active-config", response_model=ActiveConfigResponse)
    async def clear_active_config() -> ActiveConfigResponse:
        active_llm_config.clear()
        rebuilt = False
        if rebuild_hook is not None:
            try:
                result = rebuild_hook()
                if asyncio.iscoroutine(result):
                    await result
                rebuilt = True
            except Exception as exc:
                logger.warning("Clear active config rebuild failed: %s", exc)
        return ActiveConfigResponse(
            ok=True,
            component=component_name,
            active=None,
            rebuilt=rebuilt,
        )

    return router
