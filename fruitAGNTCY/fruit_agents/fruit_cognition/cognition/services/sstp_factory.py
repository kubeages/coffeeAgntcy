from __future__ import annotations

import os
from typing import Any

from cognition.schemas.sstp_message import SSTPMessage, SpeechAct


def envelope_enabled() -> bool:
    """Read the COGNITION_ENVELOPE_ENABLED env var (default off).

    Iter 3 ships the factory without forcing it on; agents continue to
    send plain A2A messages until later iterations opt in.
    """
    raw = os.getenv("COGNITION_ENVELOPE_ENABLED", "false").strip().lower()
    return raw in ("1", "true", "yes", "on")


class SSTPFactory:
    """Build SSTPMessage envelopes around agent payloads.

    The factory is stateless; instantiate per-agent or use the helper
    `wrap()` directly.
    """

    def __init__(self, *, sender_agent: str, conversation_phase: str) -> None:
        self.sender_agent = sender_agent
        self.conversation_phase = conversation_phase

    def build(
        self,
        *,
        intent_id: str,
        speech_act: SpeechAct,
        semantic_payload: dict[str, Any],
        receiver_agent: str | None = None,
        evidence_refs: list[str] | None = None,
    ) -> SSTPMessage:
        return SSTPMessage(
            intent_id=intent_id,
            sender_agent=self.sender_agent,
            receiver_agent=receiver_agent,
            conversation_phase=self.conversation_phase,
            speech_act=speech_act,
            semantic_payload=semantic_payload,
            evidence_refs=evidence_refs or [],
        )


def wrap(
    *,
    intent_id: str,
    sender_agent: str,
    conversation_phase: str,
    speech_act: SpeechAct,
    semantic_payload: dict[str, Any],
    receiver_agent: str | None = None,
    evidence_refs: list[str] | None = None,
) -> SSTPMessage:
    """One-shot helper for callers that don't need a factory instance."""
    return SSTPMessage(
        intent_id=intent_id,
        sender_agent=sender_agent,
        receiver_agent=receiver_agent,
        conversation_phase=conversation_phase,
        speech_act=speech_act,
        semantic_payload=semantic_payload,
        evidence_refs=evidence_refs or [],
    )
