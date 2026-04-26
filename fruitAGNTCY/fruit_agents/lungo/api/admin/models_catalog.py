# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

"""List models the caller's key has access to, enriched with context window
and per-token cost from the litellm pricing catalog.

OpenAI / Azure / Anthropic listing APIs each return a different shape; this
module normalises them into a single ModelInfo schema so the UI doesn't have
to special-case providers.
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger("lungo.admin.models_catalog")

Provider = Literal["openai", "azure", "anthropic"]

# Filter out non-chat OpenAI models so the UI doesn't show embeddings, audio, image, etc.
_OPENAI_CHAT_PREFIXES = (
    "gpt-",
    "o1",
    "o3",
    "o4",
    "chatgpt-",
)
_OPENAI_NON_CHAT_HINTS = (
    "embedding",
    "whisper",
    "tts",
    "dall-e",
    "moderation",
    "audio",
    "transcribe",
    "image",
    "search",
)


class ModelInfo(BaseModel):
    id: str
    label: Optional[str] = None
    context_window: Optional[int] = None
    max_output_tokens: Optional[int] = None
    input_cost_per_1k: Optional[float] = None
    output_cost_per_1k: Optional[float] = None
    provider: Provider
    notes: Optional[str] = None


def _is_openai_chat_model(model_id: str) -> bool:
    lower = model_id.lower()
    if any(hint in lower for hint in _OPENAI_NON_CHAT_HINTS):
        return False
    return any(lower.startswith(p) for p in _OPENAI_CHAT_PREFIXES)


def _enrich_from_litellm(provider: Provider, model_id: str) -> dict:
    """Return enrichment fields (context/cost) for a model id, if litellm knows it.

    litellm.model_cost is keyed by various forms; try a couple of lookups.
    """
    try:
        import litellm  # type: ignore
    except Exception:
        return {}

    cost_map = getattr(litellm, "model_cost", {}) or {}

    candidates = [model_id]
    if provider == "anthropic" and not model_id.startswith("anthropic/"):
        candidates.append(f"anthropic/{model_id}")
    if provider == "azure" and not model_id.startswith("azure/"):
        candidates.append(f"azure/{model_id}")

    for key in candidates:
        info = cost_map.get(key)
        if not info:
            continue
        max_in = info.get("max_input_tokens") or info.get("max_tokens")
        max_out = info.get("max_output_tokens")
        in_cost = info.get("input_cost_per_token")
        out_cost = info.get("output_cost_per_token")
        return {
            "context_window": int(max_in) if max_in else None,
            "max_output_tokens": int(max_out) if max_out else None,
            "input_cost_per_1k": (in_cost * 1000) if in_cost else None,
            "output_cost_per_1k": (out_cost * 1000) if out_cost else None,
        }
    return {}


async def _list_openai(api_key: str, base_url: Optional[str]) -> List[str]:
    base = base_url.rstrip("/") if base_url else "https://api.openai.com"
    url = f"{base}/v1/models"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
        resp.raise_for_status()
        data = resp.json().get("data", [])
        return [
            m.get("id")
            for m in data
            if m.get("id") and _is_openai_chat_model(m["id"])
        ]


async def _list_azure(api_key: str, base_url: str, api_version: str) -> List[str]:
    base = base_url.rstrip("/")
    url = f"{base}/openai/deployments?api-version={api_version}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, headers={"api-key": api_key})
        resp.raise_for_status()
        data = resp.json().get("data", [])
        # Each entry has {"id": deployment_name, "model": underlying_model, ...}
        return [m.get("id") for m in data if m.get("id")]


async def _list_anthropic(api_key: str) -> List[dict]:
    url = "https://api.anthropic.com/v1/models"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            url,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", [])


async def list_models(
    provider: Provider,
    api_key: str,
    base_url: Optional[str] = None,
    api_version: Optional[str] = None,
) -> List[ModelInfo]:
    out: List[ModelInfo] = []

    if provider == "openai":
        ids = await _list_openai(api_key, base_url)
        for mid in sorted(set(ids)):
            enrich = _enrich_from_litellm("openai", mid)
            out.append(ModelInfo(id=mid, label=mid, provider="openai", **enrich))

    elif provider == "azure":
        if not base_url or not api_version:
            raise ValueError(
                "Azure requires base_url (e.g. https://<resource>.openai.azure.com) and api_version."
            )
        ids = await _list_azure(api_key, base_url, api_version)
        for mid in sorted(set(ids)):
            # Azure deployments don't reveal the underlying model id, so litellm
            # enrichment is best-effort against the deployment name itself.
            enrich = _enrich_from_litellm("azure", mid)
            out.append(
                ModelInfo(
                    id=mid,
                    label=mid,
                    provider="azure",
                    notes="Azure deployment name; context/cost may be unknown.",
                    **enrich,
                )
            )

    elif provider == "anthropic":
        models = await _list_anthropic(api_key)
        for m in models:
            mid = m.get("id")
            if not mid:
                continue
            display = m.get("display_name") or mid
            enrich = _enrich_from_litellm("anthropic", mid)
            out.append(
                ModelInfo(id=mid, label=display, provider="anthropic", **enrich)
            )

    # Sort: known context first (richest data), then alpha
    out.sort(key=lambda m: (-(m.context_window or 0), m.id))
    return out
