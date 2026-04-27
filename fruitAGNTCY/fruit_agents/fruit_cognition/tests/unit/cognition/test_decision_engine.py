import pytest

from cognition.engines.cost_engine import CostEvaluation
from cognition.engines.decision_engine import (
    DecisionEngine,
    get_active_mode,
    set_active_mode,
)
from cognition.engines.policy_guardrail_engine import GuardrailVerdict
from cognition.engines.weather_risk_engine import WeatherRiskEvaluation
from cognition.schemas.decision import DecisionMode
from cognition.schemas.intent_contract import IntentContract
from cognition.schemas.plan import Plan, PlanSupplier


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("COGNITION_DECISION_USE_LLM", raising=False)
    set_active_mode(None)
    yield
    set_active_mode(None)


@pytest.fixture
def engine() -> DecisionEngine:
    return DecisionEngine()


def _intent() -> IntentContract:
    return IntentContract(goal="x", quantity_lb=500.0, max_price_usd=2000)


def _single_plan(supplier: str, qty: float, unit: float, origin: str | None = None) -> Plan:
    return Plan(
        intent_id="i",
        plan_type="single_supplier",
        suppliers=[PlanSupplier(supplier=supplier, quantity_lb=qty, unit_price_usd=unit, origin=origin)],
        total_quantity_lb=qty,
        total_price_usd=qty * unit,
    )


def _split_plan(*pairs: tuple[str, float, float]) -> Plan:
    return Plan(
        intent_id="i",
        plan_type="split_order",
        suppliers=[
            PlanSupplier(supplier=s, quantity_lb=q, unit_price_usd=u)
            for (s, q, u) in pairs
        ],
        total_quantity_lb=sum(q for (_, q, _) in pairs),
        total_price_usd=sum(q * u for (_, q, u) in pairs),
    )


def _allow(supplier: str) -> GuardrailVerdict:
    return GuardrailVerdict(supplier=supplier, allowed=True, requires_human_approval=False)


def _approval(supplier: str, *vs: str) -> GuardrailVerdict:
    return GuardrailVerdict(
        supplier=supplier, allowed=False, requires_human_approval=True,
        violations=list(vs), rationale="needs approval",
    )


def _block(supplier: str, *vs: str) -> GuardrailVerdict:
    return GuardrailVerdict(
        supplier=supplier, allowed=False, requires_human_approval=False,
        violations=list(vs), rationale="hard block",
    )


def _weather(supplier: str, level: str = "low") -> WeatherRiskEvaluation:
    return WeatherRiskEvaluation(supplier=supplier, origin="x", risk_level=level)


def _cost(supplier: str, total: float = 0) -> CostEvaluation:
    return CostEvaluation(supplier=supplier, subject="mango", rank=1, total_price_usd=total)


# ----- mode resolution -----


def test_default_mode_is_heuristic():
    assert get_active_mode() is DecisionMode.HEURISTIC


def test_env_var_switches_to_llm(monkeypatch):
    monkeypatch.setenv("COGNITION_DECISION_USE_LLM", "true")
    assert get_active_mode() is DecisionMode.LLM


def test_set_active_mode_overrides_env(monkeypatch):
    monkeypatch.setenv("COGNITION_DECISION_USE_LLM", "true")
    set_active_mode(DecisionMode.HEURISTIC)
    assert get_active_mode() is DecisionMode.HEURISTIC


# ----- heuristic decisions -----


def test_no_plans_means_no_decision(engine):
    d = engine.decide(intent=_intent(), plans=[], cost=[], weather=[], guardrail=[])
    assert d.selected_plan is None
    assert d.confidence == 0.0
    assert "No candidate" in d.rationale


def test_picks_lowest_weather_risk(engine):
    safe = _single_plan("safe-farm", 500, 2.0)
    risky = _single_plan("risky-farm", 500, 1.0)  # cheaper but risky
    decision = engine.decide(
        intent=_intent(),
        plans=[safe, risky],
        cost=[_cost("safe-farm", 1000), _cost("risky-farm", 500)],
        weather=[_weather("safe-farm", "low"), _weather("risky-farm", "high")],
        guardrail=[_allow("safe-farm"), _allow("risky-farm")],
    )
    assert decision.selected_plan.suppliers[0].supplier == "safe-farm"
    assert decision.requires_human_approval is False
    assert "weather risk low" in decision.rationale


def test_among_equal_weather_picks_cheapest(engine):
    cheap = _single_plan("cheap", 500, 1.0)
    pricey = _single_plan("pricey", 500, 5.0)
    decision = engine.decide(
        intent=_intent(),
        plans=[cheap, pricey],
        cost=[_cost("cheap", 500), _cost("pricey", 2500)],
        weather=[_weather("cheap"), _weather("pricey")],
        guardrail=[_allow("cheap"), _allow("pricey")],
    )
    assert decision.selected_plan.suppliers[0].supplier == "cheap"


def test_prefers_single_supplier_when_otherwise_tied(engine):
    single = _single_plan("solo", 500, 2.0)
    split = _split_plan(("a", 250, 2.0), ("b", 250, 2.0))
    # Same weather and cost
    decision = engine.decide(
        intent=_intent(),
        plans=[split, single],
        cost=[_cost("solo", 1000), _cost("a", 500), _cost("b", 500)],
        weather=[_weather("solo"), _weather("a"), _weather("b")],
        guardrail=[_allow("solo"), _allow("a"), _allow("b")],
    )
    assert decision.selected_plan.plan_type == "single_supplier"


def test_falls_back_to_approval_required_when_no_fully_allowed(engine):
    plan = _single_plan("risky", 500, 2.0)
    decision = engine.decide(
        intent=_intent(),
        plans=[plan],
        cost=[_cost("risky", 1000)],
        weather=[_weather("risky", "high")],
        guardrail=[_approval("risky", "weather_risk_high")],
    )
    assert decision.selected_plan.suppliers[0].supplier == "risky"
    assert decision.requires_human_approval is True
    assert "weather_risk_high" in decision.approval_violations
    assert "Requires human approval" in decision.rationale


def test_all_blocked_yields_no_selection(engine):
    plan = _single_plan("bad", 500, 99.0)
    decision = engine.decide(
        intent=_intent(),
        plans=[plan],
        cost=[_cost("bad", 49500)],
        weather=[_weather("bad")],
        guardrail=[_block("bad", "quality_below_threshold")],
    )
    assert decision.selected_plan is None
    assert "hard-blocked" in decision.rationale


def test_split_plan_inherits_worst_supplier_weather(engine):
    split = _split_plan(("good", 200, 2.0), ("bad", 300, 2.0))
    safe_single = _single_plan("solo", 500, 2.5)  # slightly more expensive but safe
    decision = engine.decide(
        intent=_intent(),
        plans=[split, safe_single],
        cost=[_cost("good", 400), _cost("bad", 600), _cost("solo", 1250)],
        weather=[
            _weather("good", "low"),
            _weather("bad", "high"),  # poisons the split's aggregate
            _weather("solo", "low"),
        ],
        guardrail=[_allow("good"), _allow("bad"), _allow("solo")],
    )
    # Split has worst weather "high", solo has "low" -> solo wins on weather rank.
    assert decision.selected_plan.plan_type == "single_supplier"
    assert decision.selected_plan.suppliers[0].supplier == "solo"


def test_confidence_respects_weather_penalty(engine):
    plan = _single_plan("colombia", 500, 2.0)
    safe = engine.decide(
        intent=_intent(), plans=[plan],
        cost=[_cost("colombia", 1000)],
        weather=[_weather("colombia", "low")],
        guardrail=[_allow("colombia")],
    )
    risky = engine.decide(
        intent=_intent(), plans=[plan],
        cost=[_cost("colombia", 1000)],
        weather=[_weather("colombia", "medium")],
        guardrail=[_allow("colombia")],
    )
    assert safe.confidence > risky.confidence
