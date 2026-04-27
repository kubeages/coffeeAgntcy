import pytest

from cognition.schemas.belief import Belief
from cognition.schemas.claim import Claim
from cognition.schemas.conflict import ConflictSeverity
from cognition.schemas.intent_contract import IntentContract
from cognition.services.conflict_resolver import ConflictResolver


@pytest.fixture
def resolver() -> ConflictResolver:
    return ConflictResolver()


def _intent(**overrides) -> IntentContract:
    return IntentContract(
        goal="fulfil_fruit_order",
        fruit_type=overrides.get("fruit_type", "mango"),
        quantity_lb=overrides.get("quantity_lb", 500.0),
        max_price_usd=overrides.get("max_price_usd", 1200.0),
        delivery_days=overrides.get("delivery_days", 7),
        hard_constraints=overrides.get("hard_constraints", {}),
    )


def _supply_option(agent: str, **value) -> Belief:
    return Belief(
        intent_id="i", belief_type="supply_option", subject="mango",
        agent_id=agent, value=value,
    )


def _claim(agent: str, claim_type: str, subject: str = "mango", **value) -> Claim:
    return Claim(intent_id="i", agent_id=agent, claim_type=claim_type, subject=subject, value=value)


# ----- inventory -----


def test_per_supplier_inventory_shortfall(resolver: ConflictResolver):
    intent = _intent(quantity_lb=500)
    beliefs = [_supply_option("colombia-farm", available_lb=320)]
    conflicts = resolver.detect(intent=intent, claims=[], beliefs=beliefs)
    types = [c.conflict_type for c in conflicts]
    assert types.count("insufficient_inventory") == 2  # per-supplier + aggregate
    per_supplier = [c for c in conflicts if c.severity == ConflictSeverity.MEDIUM]
    assert "320" in per_supplier[0].description
    assert "500" in per_supplier[0].description
    aggregate = [c for c in conflicts if c.severity == ConflictSeverity.HIGH]
    assert "Total available" in aggregate[0].description


def test_supply_meets_demand_across_suppliers_no_aggregate_conflict(resolver: ConflictResolver):
    intent = _intent(quantity_lb=500)
    beliefs = [
        _supply_option("colombia-farm", available_lb=300),
        _supply_option("brazil-farm", available_lb=400),
    ]
    conflicts = resolver.detect(intent=intent, claims=[], beliefs=beliefs)
    # Each supplier is short individually -> 2 medium per-supplier flags, no HIGH aggregate.
    assert sum(1 for c in conflicts if c.conflict_type == "insufficient_inventory") == 2
    assert all(c.severity == ConflictSeverity.MEDIUM for c in conflicts)


def test_no_inventory_conflict_when_all_meet_demand(resolver: ConflictResolver):
    intent = _intent(quantity_lb=500)
    beliefs = [_supply_option("colombia-farm", available_lb=600)]
    conflicts = resolver.detect(intent=intent, claims=[], beliefs=beliefs)
    assert all(c.conflict_type != "insufficient_inventory" for c in conflicts)


# ----- price -----


def test_price_above_budget(resolver: ConflictResolver):
    intent = _intent(quantity_lb=500, max_price_usd=1000)
    beliefs = [_supply_option("colombia-farm", unit_price_usd=2.5, available_lb=600)]
    conflicts = resolver.detect(intent=intent, claims=[], beliefs=beliefs)
    pa = [c for c in conflicts if c.conflict_type == "price_above_budget"]
    assert len(pa) == 1
    assert "$1250.00" in pa[0].description
    assert pa[0].severity == ConflictSeverity.HIGH


def test_price_within_budget_no_conflict(resolver: ConflictResolver):
    intent = _intent(quantity_lb=500, max_price_usd=2000)
    beliefs = [_supply_option("colombia-farm", unit_price_usd=2.5, available_lb=600)]
    conflicts = resolver.detect(intent=intent, claims=[], beliefs=beliefs)
    assert all(c.conflict_type != "price_above_budget" for c in conflicts)


# ----- weather -----


def test_weather_risk_high_threshold(resolver: ConflictResolver):
    intent = _intent()
    claims = [
        _claim("weather-mcp", "weather_risk", subject="colombia",
               weather_risk_score=0.8, region="colombia", forecast="storms"),
    ]
    conflicts = resolver.detect(intent=intent, claims=claims, beliefs=[])
    wr = [c for c in conflicts if c.conflict_type == "weather_risk_high"]
    assert len(wr) == 1
    assert wr[0].severity == ConflictSeverity.HIGH
    assert "storms" in wr[0].description


def test_weather_risk_low_no_conflict(resolver: ConflictResolver):
    intent = _intent()
    claims = [_claim("weather-mcp", "weather_risk", subject="x", weather_risk_score=0.2)]
    conflicts = resolver.detect(intent=intent, claims=claims, beliefs=[])
    assert all(c.conflict_type != "weather_risk_high" for c in conflicts)


# ----- delivery SLA -----


def test_delivery_sla_at_risk(resolver: ConflictResolver):
    intent = _intent(delivery_days=5)
    claims = [_claim("shipper", "delivery_sla", eta_days=9)]
    conflicts = resolver.detect(intent=intent, claims=claims, beliefs=[])
    sla = [c for c in conflicts if c.conflict_type == "delivery_sla_at_risk"]
    assert len(sla) == 1
    assert "9 days" in sla[0].description
    assert "5-day" in sla[0].description


def test_delivery_sla_within_window(resolver: ConflictResolver):
    intent = _intent(delivery_days=10)
    claims = [_claim("shipper", "delivery_sla", eta_days=6)]
    conflicts = resolver.detect(intent=intent, claims=claims, beliefs=[])
    assert all(c.conflict_type != "delivery_sla_at_risk" for c in conflicts)


# ----- quality -----


def test_quality_below_default_threshold(resolver: ConflictResolver):
    intent = _intent()
    beliefs = [_supply_option("colombia-farm", quality_score=0.45, available_lb=600)]
    conflicts = resolver.detect(intent=intent, claims=[], beliefs=beliefs)
    qb = [c for c in conflicts if c.conflict_type == "quality_below_threshold"]
    assert len(qb) == 1
    assert qb[0].severity == ConflictSeverity.MEDIUM


def test_quality_uses_intent_constraint_threshold(resolver: ConflictResolver):
    intent = _intent(hard_constraints={"min_quality_score": 0.95})
    beliefs = [_supply_option("colombia-farm", quality_score=0.9, available_lb=600)]
    conflicts = resolver.detect(intent=intent, claims=[], beliefs=beliefs)
    qb = [c for c in conflicts if c.conflict_type == "quality_below_threshold"]
    assert len(qb) == 1
    assert "0.95" in qb[0].description


# ----- contradictions -----


def test_contradictory_claims_same_agent_diff_inventory(resolver: ConflictResolver):
    intent = _intent()
    claims = [
        _claim("colombia-farm", "inventory", available_lb=300),
        _claim("colombia-farm", "inventory", available_lb=500),
    ]
    conflicts = resolver.detect(intent=intent, claims=claims, beliefs=[])
    cc = [c for c in conflicts if c.conflict_type == "contradictory_claims"]
    assert len(cc) == 1
    assert cc[0].severity == ConflictSeverity.LOW


def test_no_contradiction_when_values_agree(resolver: ConflictResolver):
    intent = _intent()
    claims = [
        _claim("colombia-farm", "inventory", available_lb=300),
        _claim("colombia-farm", "inventory", available_lb=300),
    ]
    conflicts = resolver.detect(intent=intent, claims=claims, beliefs=[])
    assert all(c.conflict_type != "contradictory_claims" for c in conflicts)


# ----- empty case -----


def test_no_conflicts_when_intent_has_no_constraints(resolver: ConflictResolver):
    intent = IntentContract(goal="x")  # all fields None
    conflicts = resolver.detect(intent=intent, claims=[], beliefs=[])
    assert conflicts == []
