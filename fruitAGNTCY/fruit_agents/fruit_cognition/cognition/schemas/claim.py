from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Claim(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"claim-{uuid4()}")
    intent_id: str
    agent_id: str
    claim_type: str
    subject: str
    value: dict[str, Any]
    confidence: float = 1.0
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
