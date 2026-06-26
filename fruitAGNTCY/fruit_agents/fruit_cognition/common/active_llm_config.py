# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

"""Process-level "active LLM config" for the bring-your-own-key admin panel.

When the user saves credentials in the UI, each supervisor's
``/admin/active-config`` endpoint hands them off to ``apply()`` here. We:

1. Update the relevant ``OPENAI_API_KEY`` / ``AZURE_*`` / ``ANTHROPIC_API_KEY``
   environment variables so the next call into ``litellm`` picks them up.
2. Set ``LLM_MODEL`` to the chosen model id (with the appropriate provider
   prefix for Azure / Anthropic so litellm dispatches correctly).
3. Cache the active config so it can be returned by GET (with the secret
   masked).

This is intentionally process-level, not persistent. Restarting the pod
reverts to whatever the cluster Secret/ConfigMap supplied.
"""

from __future__ import annotations

import os
import threading
from typing import Literal, Optional

from pydantic import BaseModel, Field

# vllm + ollama are OpenAI-compatible endpoints (no key required); they are
# routed through litellm's ``openai/`` provider with a custom ``base_url``.
Provider = Literal["openai", "azure", "anthropic", "vllm", "ollama"]


class ActiveLLMConfig(BaseModel):
    provider: Provider
    api_key: str = ""  # optional: vllm/ollama need no key
    model: str = Field(min_length=1)
    base_url: Optional[str] = None
    api_version: Optional[str] = None


class ActiveLLMConfigPublic(BaseModel):
    """Same shape as ``ActiveLLMConfig`` but with the secret masked."""

    provider: Provider
    api_key_preview: str
    model: str
    base_url: Optional[str] = None
    api_version: Optional[str] = None


_lock = threading.Lock()
_current: Optional[ActiveLLMConfig] = None


def _mask(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}{'*' * max(8, len(key) - 8)}{key[-4:]}"


def get_active() -> Optional[ActiveLLMConfig]:
    with _lock:
        return _current


def get_active_public() -> Optional[ActiveLLMConfigPublic]:
    cur = get_active()
    if cur is None:
        return None
    return ActiveLLMConfigPublic(
        provider=cur.provider,
        api_key_preview=_mask(cur.api_key),
        model=cur.model,
        base_url=cur.base_url,
        api_version=cur.api_version,
    )


def _model_with_prefix(provider: Provider, model: str) -> str:
    if provider == "azure" and not model.startswith("azure/"):
        return f"azure/{model}"
    if provider == "anthropic" and not model.startswith("anthropic/"):
        return f"anthropic/{model}"
    # vllm/ollama: drive them through litellm's OpenAI-compatible path.
    if provider in ("vllm", "ollama") and not model.startswith("openai/"):
        return f"openai/{model}"
    return model


def apply(cfg: ActiveLLMConfig) -> ActiveLLMConfig:
    """Atomically swap the process's active config + relevant env vars.

    Returns the stored config so callers can echo it back (often via the
    masked variant).
    """
    global _current
    resolved_model = _model_with_prefix(cfg.provider, cfg.model)
    with _lock:
        _current = cfg
        os.environ["LLM_MODEL"] = resolved_model

        if cfg.provider in ("openai", "vllm", "ollama"):
            # vllm/ollama are OpenAI-compatible; an empty key still needs a
            # non-empty placeholder so the OpenAI client sends a header.
            os.environ["OPENAI_API_KEY"] = cfg.api_key or "EMPTY"
            if cfg.base_url:
                os.environ["OPENAI_API_BASE"] = cfg.base_url
            else:
                # don't leak a previous provider's custom base into plain OpenAI
                os.environ.pop("OPENAI_API_BASE", None)
            os.environ.pop("AZURE_API_KEY", None)
            os.environ.pop("ANTHROPIC_API_KEY", None)
        elif cfg.provider == "azure":
            os.environ["AZURE_API_KEY"] = cfg.api_key
            if cfg.base_url:
                os.environ["AZURE_API_BASE"] = cfg.base_url
            if cfg.api_version:
                os.environ["AZURE_API_VERSION"] = cfg.api_version
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("ANTHROPIC_API_KEY", None)
        elif cfg.provider == "anthropic":
            os.environ["ANTHROPIC_API_KEY"] = cfg.api_key
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("AZURE_API_KEY", None)

    return cfg


def clear() -> None:
    """Forget the active config. Env vars are left in place — callers that
    want to restore the original cluster Secret values must restart the pod.
    """
    global _current
    with _lock:
        _current = None
