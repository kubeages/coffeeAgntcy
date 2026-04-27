from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from cognition.schemas.plan import Plan


class DecisionMode(str, Enum):
    HEURISTIC = "heuristic"
    LLM = "llm"


class Decision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"decision-{uuid4()}")
    intent_id: str
    decision_type: str = "recommended_supply_plan"
    selected_plan: Plan | None = None
    rationale: str = ""
    confidence: float = 0.0
    requires_human_approval: bool = False
    mode: DecisionMode = DecisionMode.HEURISTIC
    # Suppliers from the selected plan that triggered approval-redeemable
    # violations (so the inbox can show *why* approval is needed).
    approval_violations: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
