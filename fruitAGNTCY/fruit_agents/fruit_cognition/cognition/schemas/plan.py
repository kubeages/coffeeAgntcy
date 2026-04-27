from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


PlanType = Literal["single_supplier", "split_order"]


class PlanSupplier(BaseModel):
    supplier: str
    quantity_lb: float
    unit_price_usd: float | None = None
    origin: str | None = None


class Plan(BaseModel):
    """A candidate fulfillment plan for an intent.

    The planner is purely combinatorial — engines decide whether the
    plan is viable. ``feasible`` indicates whether the supplier
    quantities cover ``total_quantity_lb`` (always True in M4; the
    planner skips infeasible candidates).
    """

    plan_id: str = Field(default_factory=lambda: f"plan-{uuid4()}")
    intent_id: str
    plan_type: PlanType
    suppliers: list[PlanSupplier]
    total_quantity_lb: float
    total_price_usd: float | None = None
    feasible: bool = True
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
