from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class IntentStatus(str, Enum):
    DRAFT = "draft"
    GROUNDING = "grounding"
    NEGOTIATING = "negotiating"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMMITTED = "committed"
    FAILED = "failed"


class IntentContract(BaseModel):
    intent_id: str = Field(default_factory=lambda: f"fruit-intent-{uuid4()}")
    goal: str

    fruit_type: str | None = None
    quantity_lb: float | None = None
    target_origin: str | None = None
    max_price_usd: float | None = None
    delivery_days: int | None = None

    hard_constraints: dict[str, Any] = Field(default_factory=dict)
    soft_constraints: dict[str, Any] = Field(default_factory=dict)
    human_approval_required_if: list[str] = Field(default_factory=list)

    status: IntentStatus = IntentStatus.DRAFT
