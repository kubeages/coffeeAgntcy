# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0
"""
Minimal admin endpoint so the fruitCognition Settings panel can configure this
standalone recruiter's LLM the same way it configures the supervisors.

The recruiter-supervisor forwards its active LLM config here (POST
/admin/active-config). We update the process env (model / OPENAI_API_BASE / key,
mirroring fruit_cognition's active_llm_config.apply) and rebuild the agent team
so the next request uses the new model. Process-level only (reverts on restart).
"""

import os

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from agent_recruiter.common.logging import get_logger

logger = get_logger(__name__)


def _apply_llm_env(provider: str, api_key: str, model: str, base_url: str | None) -> None:
    provider = (provider or "openai").lower()
    m = model or ""
    if provider in ("vllm", "ollama") and m and not m.startswith("openai/"):
        m = f"openai/{m}"
    elif provider == "azure" and m and not m.startswith("azure/"):
        m = f"azure/{m}"
    elif provider == "anthropic" and m and not m.startswith("anthropic/"):
        m = f"anthropic/{m}"
    if m:
        os.environ["LLM_MODEL"] = m

    if provider in ("openai", "vllm", "ollama"):
        os.environ["OPENAI_API_KEY"] = api_key or "EMPTY"
        if base_url:
            os.environ["OPENAI_API_BASE"] = base_url
        else:
            os.environ.pop("OPENAI_API_BASE", None)
        os.environ.pop("AZURE_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
    elif provider == "azure":
        os.environ["AZURE_API_KEY"] = api_key or ""
        if base_url:
            os.environ["AZURE_API_BASE"] = base_url
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
    elif provider == "anthropic":
        os.environ["ANTHROPIC_API_KEY"] = api_key or ""
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("AZURE_API_KEY", None)


def add_admin_routes(app, executor) -> None:
    """Attach /admin/active-config (POST+GET) and /admin/health to the Starlette app."""

    async def set_active_config(request: Request) -> JSONResponse:
        try:
            body = await request.json()
            provider = body.get("provider", "openai")
            _apply_llm_env(
                provider,
                body.get("api_key", ""),
                body.get("model", ""),
                body.get("base_url"),
            )
            executor.reload()
            logger.info(
                f"[admin] active LLM config applied: provider={provider} "
                f"model={os.getenv('LLM_MODEL')} base_url={os.getenv('OPENAI_API_BASE')}"
            )
            return JSONResponse({"ok": True, "model": os.getenv("LLM_MODEL")})
        except Exception as e:  # noqa: BLE001
            logger.error(f"[admin] failed to apply active config: {e}", exc_info=True)
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    async def get_active_config(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "ok": True,
                "model": os.getenv("LLM_MODEL"),
                "base_url": os.getenv("OPENAI_API_BASE"),
            }
        )

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"ok": True})

    app.routes.append(Route("/admin/active-config", set_active_config, methods=["POST"]))
    app.routes.append(Route("/admin/active-config", get_active_config, methods=["GET"]))
    app.routes.append(Route("/admin/health", health, methods=["GET"]))
    logger.info("[admin] /admin/active-config route registered")
