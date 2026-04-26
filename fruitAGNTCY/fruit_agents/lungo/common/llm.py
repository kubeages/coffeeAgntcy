# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging
import os

import litellm
from langchain_litellm import ChatLiteLLM
from langchain_openai import ChatOpenAI

# Modern reasoning models (gpt-5*, o1*, o3*, etc.) reject params they don't
# support (e.g. ``temperature=0``, ``max_tokens`` vs ``max_completion_tokens``).
# Telling litellm to silently drop unsupported params keeps a single get_llm()
# code path working across legacy chat models and reasoning models.
litellm.drop_params = True

logger = logging.getLogger("lungo.common.llm")
import common.chat_lite_llm_shim as chat_lite_llm_shim  # our drop-in client


def _current_model() -> str:
    """Read LLM_MODEL from env at call time so the bring-your-own-key admin
    panel (``common.active_llm_config.apply``) can swap the active model
    without a process restart."""
    return os.getenv("LLM_MODEL", "")


def get_llm(streaming: bool = True):
    """Build an LLM client honoring the LiteLLM proxy if configured, else
    falling back to ChatLiteLLM with the current ``LLM_MODEL`` env var.

    Args:
      streaming: Enable streaming. Set to False with ``with_structured_output()``.
    """
    litellm_proxy_base_url = os.getenv("LITELLM_PROXY_BASE_URL")
    litellm_proxy_api_key = os.getenv("LITELLM_PROXY_API_KEY")

    model = _current_model()

    if litellm_proxy_base_url and litellm_proxy_api_key:
        logger.info(f"Using LLM via LiteLLM proxy: {litellm_proxy_base_url}")
        llm = ChatOpenAI(
            base_url=litellm_proxy_base_url,
            model=model,
            api_key=litellm_proxy_api_key,
            streaming=streaming,
        )
    else:
        llm = ChatLiteLLM(model=model)

    if model.startswith("oauth2/"):
        llm.client = chat_lite_llm_shim
    return llm
