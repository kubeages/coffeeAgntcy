"""Orchestrate the engine pipeline in the SPEC §4.8 order:

    BeliefBuilder -> ConflictResolver
                  -> CostEngine + WeatherRiskEngine (parallel, but pure)
                  -> PolicyGuardrailEngine

Reads claims (and the intent) from the active fabric, builds beliefs
on the fly, runs the engines, and returns one ``EvaluatedOption`` per
supply_option plus the resolver's conflict list.

All engines are pure; no persistence here.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from cognition.engines.cost_engine import CostEngine, CostEvaluation
from cognition.engines.decision_engine import DecisionEngine
from cognition.engines.policy_guardrail_engine import (
    GuardrailVerdict,
    PolicyGuardrailEngine,
)
from cognition.engines.weather_risk_engine import (
    RiskLevel,
    WeatherRiskEngine,
    WeatherRiskEvaluation,
)
from cognition.schemas.belief import Belief
from cognition.schemas.claim import Claim
from cognition.schemas.conflict import Conflict
from cognition.schemas.decision import Decision
from cognition.schemas.intent_contract import IntentContract
from cognition.schemas.plan import Plan
from cognition.services.belief_builder import BeliefBuilder
from cognition.services.cognition_fabric import get_fabric
from cognition.services.conflict_resolver import ConflictResolver
from cognition.services.split_order_planner import SplitOrderPlanner


_belief_builder = BeliefBuilder()
_resolver = ConflictResolver()
_cost_engine = CostEngine()
_weather_engine = WeatherRiskEngine()
_guardrail = PolicyGuardrailEngine()
_planner = SplitOrderPlanner()
_decision_engine = DecisionEngine()


class EvaluatedOption(BaseModel):
    """A supply_option enriched by the full engine pipeline."""

    intent_id: str
    supplier: str
    subject: str

    # Cost engine fields
    available_lb: float | None = None
    unit_price_usd: float | None = None
    fulfilled_lb: float | None = None
    total_price_usd: float | None = None
    within_budget: bool | None = None
    cost_rank: int

    # Weather risk fields
    origin: str | None = None
    weather_risk_level: RiskLevel = "unknown"
    weather_score: float | None = None
    weather_reason: str | None = None

    # Guardrail verdict
    allowed: bool = False
    requires_human_approval: bool = False
    violations: list[str] = Field(default_factory=list)
    rationale: str | None = None


class EngineEvaluation(BaseModel):
    intent_id: str
    options: list[EvaluatedOption] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)
    plans: list[Plan] = Field(default_factory=list)
    decision: Decision | None = None


def _merge(
    *,
    intent: IntentContract,
    beliefs: list[Belief],
    cost: list[CostEvaluation],
    weather: list[WeatherRiskEvaluation],
    guardrail: list[GuardrailVerdict],
) -> list[EvaluatedOption]:
    cost_by = {c.supplier: c for c in cost}
    weather_by = {w.supplier: w for w in weather}
    guardrail_by = {g.supplier: g for g in guardrail}

    out: list[EvaluatedOption] = []
    for b in beliefs:
        if b.belief_type != "supply_option":
            continue
        c = cost_by.get(b.agent_id)
        w = weather_by.get(b.agent_id)
        g = guardrail_by.get(b.agent_id)
        out.append(
            EvaluatedOption(
                intent_id=intent.intent_id,
                supplier=b.agent_id,
                subject=b.subject,
                available_lb=c.available_lb if c else b.value.get("available_lb"),
                unit_price_usd=c.unit_price_usd if c else b.value.get("unit_price_usd"),
                fulfilled_lb=c.fulfilled_lb if c else None,
                total_price_usd=c.total_price_usd if c else None,
                within_budget=c.within_budget if c else None,
                cost_rank=c.rank if c else 0,
                origin=(w.origin if w else b.value.get("origin")),
                weather_risk_level=w.risk_level if w else "unknown",
                weather_score=w.score if w else None,
                weather_reason=w.reason if w else None,
                allowed=g.allowed if g else False,
                requires_human_approval=g.requires_human_approval if g else False,
                violations=list(g.violations) if g else [],
                rationale=g.rationale if g else None,
            )
        )

    # Sort: allowed first, then by cost_rank, then alphabetical for stability.
    out.sort(key=lambda o: (0 if o.allowed else 1, o.cost_rank or 999, o.supplier))
    return out


def evaluate_intent(intent_id: str) -> EngineEvaluation | None:
    """Run the full engine pipeline for an intent. Returns None if the
    intent is not in the fabric."""
    fabric = get_fabric()
    intent = fabric.get_intent(intent_id)
    if intent is None:
        return None

    claims = fabric.list_claims(intent_id)
    beliefs = _belief_builder.build(intent_id=intent_id, claims=claims)

    conflicts = _resolver.detect(intent=intent, claims=claims, beliefs=beliefs)
    cost = _cost_engine.evaluate(intent=intent, beliefs=beliefs)
    weather = _weather_engine.evaluate(intent=intent, claims=claims, beliefs=beliefs)
    guardrail = _guardrail.evaluate(
        intent=intent, claims=claims, beliefs=beliefs,
        cost=cost, weather=weather,
    )
    options = _merge(
        intent=intent, beliefs=beliefs,
        cost=cost, weather=weather, guardrail=guardrail,
    )

    plans = _planner.plan(intent=intent, beliefs=beliefs)
    decision = _decision_engine.decide(
        intent=intent, plans=plans, cost=cost, weather=weather, guardrail=guardrail,
    )

    return EngineEvaluation(
        intent_id=intent_id,
        options=options,
        conflicts=conflicts,
        plans=plans,
        decision=decision,
    )
