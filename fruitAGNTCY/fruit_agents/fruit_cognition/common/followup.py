# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0
"""
Conversational follow-up condensation.

The auction/logistics supervisors are LangGraph task-routers: each turn is routed
to a worker node that only reads the latest human message. On its own, a stable
``thread_id`` (checkpointer) persists history but the workers ignore it, so
follow-ups like "Brazil", "that one", or "compare it to Vietnam" lose context.

``condense_prompt`` closes that gap: before the graph runs, it reads the prior
conversation already persisted in the checkpointer for this thread and rewrites
the latest message into a single self-contained request. The rewritten prompt
then flows through the existing graph unchanged. First turn (no history) is a
no-op, so there is zero extra cost on the first message.
"""

import logging

from langchain_core.messages import SystemMessage, HumanMessage

from common.llm import get_llm

logger = logging.getLogger("fruit_cognition.followup")

_CONDENSE_SYS = SystemMessage(content=(
    "You rewrite a user's latest message into ONE self-contained request, using "
    "the earlier conversation only to resolve references. Replace pronouns and "
    "bare references (e.g. 'it', 'that one', a lone farm name like 'Brazil') with "
    "the explicit thing they refer to. Keep the user's intent and any numbers "
    "exactly. Do NOT answer the request. Return ONLY the rewritten request text "
    "with no preamble. If the latest message is already self-contained, return it "
    "unchanged."
))


async def condense_prompt(graph, prompt: str, config: dict) -> str:
    """Rewrite ``prompt`` into a standalone request using this thread's history.

    ``graph`` is the compiled LangGraph (with a checkpointer); ``config`` carries
    the ``thread_id``. Returns the original prompt unchanged on the first turn or
    if anything goes wrong (fail-open).
    """
    try:
        snapshot = await graph.aget_state(config)
        prior = (snapshot.values or {}).get("messages", []) if snapshot else []
    except Exception as e:
        logger.warning(f"condense_prompt: could not read prior state: {e}")
        return prompt

    # Earlier user turns are the cleanest signal; include the assistant's last
    # reply too (e.g. "please specify which farm") to resolve the follow-up.
    human_turns = [
        m.content for m in prior
        if getattr(m, "type", None) == "human" and getattr(m, "content", None)
    ]
    if not human_turns:
        return prompt  # first turn in this conversation -> nothing to condense

    last_ai = next(
        (m.content for m in reversed(prior)
         if getattr(m, "type", None) == "ai" and getattr(m, "content", "")),
        None,
    )

    context = "Earlier user messages:\n" + "\n".join(f"- {h}" for h in human_turns[-6:])
    if last_ai:
        context += f"\n\nAssistant's last reply:\n{str(last_ai)[:500]}"

    try:
        llm = get_llm(streaming=False)
        resp = await llm.ainvoke([
            _CONDENSE_SYS,
            HumanMessage(content=(
                f"{context}\n\nLatest user message:\n{prompt}\n\n"
                "Rewrite the latest message as a standalone request."
            )),
        ])
        rewritten = (getattr(resp, "content", "") or "").strip()
        if rewritten and rewritten.lower() != prompt.strip().lower():
            logger.info(f"condense_prompt: '{prompt}' -> '{rewritten}'")
        return rewritten or prompt
    except Exception as e:
        logger.warning(f"condense_prompt: LLM rewrite failed, using raw prompt: {e}")
        return prompt
