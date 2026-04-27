from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


SpeechAct = Literal[
    "request",
    "claim",
    "proposal",
    "counter_proposal",
    "approval_request",
    "decision",
    "rejection",
    "question",
    "evidence",
]


class SSTPMessage(BaseModel):
    sstp_version: str = "0.1"
    message_id: str = Field(default_factory=lambda: f"sstp-{uuid4()}")
    intent_id: str
    sender_agent: str
    receiver_agent: str | None = None
    conversation_phase: str
    speech_act: SpeechAct
    semantic_payload: dict[str, Any]
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
