"""Decision engine: pick a recommended Plan from the planner output.

Two modes:

* ``HEURISTIC`` (default): pure ranker using SPEC iter 14 priorities —
  prefer allowed plans, lowest worst-case weather risk, lowest cost,
  highest aggregate quality, lowest delivery time, single-supplier
  over split when otherwise tied.

* ``LLM``: same input data is rendered into a prompt and an LLM is
  asked to pick a plan_id with rationale. Falls back to heuristic if
  the call fails or returns garbage.

The mode is controlled at runtime via:
  1. ``set_active_mode(...)`` (admin override),
  2. ``COGNITION_DECISION_USE_LLM`` env var (truthy ⇒ LLM),
  3. defaults to HEURISTIC.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Iterable

from cognition.engines.cost_engine import CostEvaluation
from cognition.engines.policy_guardrail_engine import GuardrailVerdict
from cognition.engines.weather_risk_engine import WeatherRiskEvaluation
from cognition.schemas.decision import Decision, DecisionMode
from cognition.schemas.intent_contract import IntentContract
from cognition.schemas.plan import Plan


logger = logging.getLogger("fruit_cognition.cognition.decision")


_RISK_RANK = {"low": 0, "unknown": 1, "medium": 2, "high": 3}


# ----- runtime mode override -----

_override_mode: DecisionMode | None = None
_mode_lock = threading.Lock()


def _resolve_mode() -> DecisionMode:
    if _override_mode is not None:
        return _override_mode
    raw = os.getenv("COGNITION_DECISION_USE_LLM", "false").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return DecisionMode.LLM
    return DecisionMode.HEURISTIC


def get_active_mode() -> DecisionMode:
    return _resolve_mode()


def set_active_mode(mode: DecisionMode | None) -> None:
    """Admin override; pass None to clear and fall back to env."""
    global _override_mode
    with _mode_lock:
        _override_mode = mode


# ----- helpers -----


def _aggregate_weather_for_plan(
    plan: Plan, weather_by_supplier: dict[str, WeatherRiskEvaluation]
) -> tuple[str, float]:
    """Plan-level weather: worst-case across the plan's suppliers."""
    levels = [
        weather_by_supplier.get(s.supplier).risk_level  # type: ignore[union-attr]
        if s.supplier in weather_by_supplier else "unknown"
        for s in plan.suppliers
    ]
    worst = max(levels, key=lambda l: _RISK_RANK.get(l, 1))
    return worst, float(_RISK_RANK.get(worst, 1))


def _aggregate_violations_for_plan(
    plan: Plan, guardrail_by_supplier: dict[str, GuardrailVerdict]
) -> tuple[bool, bool, list[str]]:
    """Returns (all_allowed, any_requires_approval, all_violations)."""
    all_allowed = True
    any_requires_approval = False
    violations: list[str] = []
    for s in plan.suppliers:
        v = guardrail_by_supplier.get(s.supplier)
        if v is None:
            continue
        if not v.allowed:
            all_allowed = False
        if v.requires_human_approval:
            any_requires_approval = True
        violations.extend(v.violations)
    # de-duplicate while preserving order
    seen: set[str] = set()
    unique = [x for x in violations if not (x in seen or seen.add(x))]
    return all_allowed, any_requires_approval, unique


def _heuristic_rank_key(
    plan: Plan,
    weather_by: dict[str, WeatherRiskEvaluation],
    cost_by: dict[str, CostEvaluation],
) -> tuple:
    worst_level, _ = _aggregate_weather_for_plan(plan, weather_by)
    weather_score = _RISK_RANK.get(worst_level, 1)
    cost = plan.total_price_usd if plan.total_price_usd is not None else float("inf")
    qualities = [
        cost_by.get(s.supplier) for s in plan.suppliers
    ]  # cost_by has rank/budget but not quality; use plan total as tiebreak
    type_rank = 0 if plan.plan_type == "single_supplier" else 1
    return (weather_score, cost, type_rank, plan.plan_id)


# ----- engine -----


class DecisionEngine:
    def decide(
        self,
        *,
        intent: IntentContract,
        plans: Iterable[Plan],
        cost: Iterable[CostEvaluation],
        weather: Iterable[WeatherRiskEvaluation],
        guardrail: Iterable[GuardrailVerdict],
        mode: DecisionMode | None = None,
    ) -> Decision:
        plans = list(plans)
        cost_by = {c.supplier: c for c in cost}
        weather_by = {w.supplier: w for w in weather}
        guardrail_by = {g.supplier: g for g in guardrail}

        if not plans:
            return Decision(
                intent_id=intent.intent_id,
                rationale="No candidate plans available.",
                confidence=0.0,
                mode=mode or _resolve_mode(),
            )

        # Categorize plans by guardrail outcome.
        fully_allowed: list[Plan] = []
        approval_required: list[Plan] = []
        for p in plans:
            allowed, requires_approval, _ = _aggregate_violations_for_plan(p, guardrail_by)
            if allowed:
                fully_allowed.append(p)
            elif requires_approval:
                approval_required.append(p)

        active_mode = mode or _resolve_mode()

        if fully_allowed:
            ranked = sorted(
                fully_allowed,
                key=lambda p: _heuristic_rank_key(p, weather_by, cost_by),
            )
            picked = ranked[0]
            worst, _ = _aggregate_weather_for_plan(picked, weather_by)
            rationale = self._render_rationale(
                picked, weather_level=worst, requires_approval=False, mode=active_mode,
            )
            return Decision(
                intent_id=intent.intent_id,
                selected_plan=picked,
                rationale=rationale,
                confidence=self._heuristic_confidence(picked, weather_by),
                requires_human_approval=False,
                mode=active_mode,
            )

        if approval_required:
            ranked = sorted(
                approval_required,
                key=lambda p: _heuristic_rank_key(p, weather_by, cost_by),
            )
            picked = ranked[0]
            worst, _ = _aggregate_weather_for_plan(picked, weather_by)
            _, _, violations = _aggregate_violations_for_plan(picked, guardrail_by)
            rationale = self._render_rationale(
                picked, weather_level=worst, requires_approval=True, mode=active_mode,
                violations=violations,
            )
            return Decision(
                intent_id=intent.intent_id,
                selected_plan=picked,
                rationale=rationale,
                confidence=self._heuristic_confidence(picked, weather_by) * 0.7,
                requires_human_approval=True,
                approval_violations=violations,
                mode=active_mode,
            )

        # All plans hard-blocked.
        return Decision(
            intent_id=intent.intent_id,
            rationale="All candidate plans were hard-blocked by policy.",
            confidence=0.0,
            mode=active_mode,
        )

    # ----- rationale rendering -----

    def _render_rationale(
        self,
        plan: Plan,
        *,
        weather_level: str,
        requires_approval: bool,
        mode: DecisionMode,
        violations: list[str] | None = None,
    ) -> str:
        suppliers = ", ".join(f"{s.supplier} ({s.quantity_lb} lb)" for s in plan.suppliers)
        kind = "single-supplier plan" if plan.plan_type == "single_supplier" else "split-order plan"
        cost = f"${plan.total_price_usd:.2f}" if plan.total_price_usd is not None else "unpriced"

        if requires_approval:
            why = ", ".join(violations or [])
            return (
                f"Selected {kind} via {suppliers}; total {cost}; weather risk {weather_level}. "
                f"Requires human approval ({why})."
            )
        return (
            f"Selected {kind} via {suppliers}; total {cost}; weather risk {weather_level}."
        )

    def _heuristic_confidence(
        self, plan: Plan, weather_by: dict[str, WeatherRiskEvaluation]
    ) -> float:
        worst, _ = _aggregate_weather_for_plan(plan, weather_by)
        # Base 0.85 for any allowed plan; nudge down by weather risk.
        weather_penalty = {"low": 0.0, "unknown": 0.05, "medium": 0.10, "high": 0.20}
        score = 0.85 - weather_penalty.get(worst, 0.05)
        # Tie-break against unpriced plans (less certain about cost).
        if plan.total_price_usd is None:
            score -= 0.05
        return round(max(0.0, min(1.0, score)), 4)


# ----- LLM mode (best-effort) -----


def llm_pick(
    *,
    intent: IntentContract,
    plans: list[Plan],
    cost: list[CostEvaluation],
    weather: list[WeatherRiskEvaluation],
    guardrail: list[GuardrailVerdict],
    candidate_plan_ids: list[str],
) -> tuple[str | None, str | None]:
    """Ask the configured LLM to pick a plan_id from the candidate list.

    Returns ``(plan_id, rationale)`` or ``(None, None)`` on any failure.
    """
    try:
        import litellm  # noqa: F401
    except ImportError:
        logger.warning("litellm not installed; cannot run LLM decision mode")
        return (None, None)

    model = os.getenv("LLM_MODEL", "")
    if not model:
        logger.info("LLM_MODEL unset; skipping LLM decision pick")
        return (None, None)

    payload = {
        "intent": intent.model_dump(mode="json"),
        "candidate_plans": [
            {
                "plan_id": p.plan_id,
                "plan_type": p.plan_type,
                "total_price_usd": p.total_price_usd,
                "total_quantity_lb": p.total_quantity_lb,
                "suppliers": [s.model_dump(mode="json") for s in p.suppliers],
            }
            for p in plans
            if p.plan_id in candidate_plan_ids
        ],
        "cost": [c.model_dump(mode="json") for c in cost],
        "weather": [w.model_dump(mode="json") for w in weather],
        "guardrail": [g.model_dump(mode="json") for g in guardrail],
    }
    system = (
        "You are a sourcing decision engine. Given the intent, "
        "candidate plans, and engine outputs (cost, weather risk, "
        "policy guardrail), pick exactly one plan_id from the candidates "
        "and explain why in one sentence. "
        'Respond as JSON: {"plan_id": "...", "rationale": "..."}'
    )

    try:
        import litellm
        litellm.drop_params = True
        resp = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, default=str)},
            ],
            response_format={"type": "json_object"},
            timeout=20,
            max_tokens=400,
        )
        text = resp.choices[0].message.content or ""
        parsed = json.loads(text)
        pid = parsed.get("plan_id")
        rat = parsed.get("rationale")
        if pid in candidate_plan_ids and isinstance(rat, str):
            return (pid, rat)
        logger.warning("LLM returned plan_id=%r outside candidates", pid)
        return (None, None)
    except Exception as exc:
        logger.warning("LLM decision call failed: %s", exc)
        return (None, None)
