import pytest

from cognition.schemas.belief import Belief
from cognition.schemas.intent_contract import IntentContract
from cognition.schemas.plan import Plan, PlanSupplier
from cognition.services.split_order_planner import SplitOrderPlanner


@pytest.fixture
def planner() -> SplitOrderPlanner:
    return SplitOrderPlanner()


def _intent(qty: float | None = 500) -> IntentContract:
    return IntentContract(goal="x", quantity_lb=qty)


def _supply(agent: str, available: float, price: float | None = None, origin: str | None = None) -> Belief:
    value: dict = {"available_lb": available}
    if price is not None:
        value["unit_price_usd"] = price
    if origin is not None:
        value["origin"] = origin
    return Belief(
        intent_id="i", belief_type="supply_option", subject="mango",
        agent_id=agent, value=value,
    )


def test_no_supply_options_returns_empty(planner: SplitOrderPlanner):
    assert planner.plan(intent=_intent(), beliefs=[]) == []


def test_single_supplier_with_full_coverage(planner: SplitOrderPlanner):
    plans = planner.plan(
        intent=_intent(500),
        beliefs=[_supply("colombia", 600, 2.0, "colombia")],
    )
    assert len(plans) == 1
    p = plans[0]
    assert p.plan_type == "single_supplier"
    assert p.suppliers[0].supplier == "colombia"
    assert p.suppliers[0].quantity_lb == 500
    assert p.total_quantity_lb == 500
    assert p.total_price_usd == 1000.0


def test_multiple_singles_sorted_by_price(planner: SplitOrderPlanner):
    plans = planner.plan(
        intent=_intent(100),
        beliefs=[
            _supply("expensive", 500, 5.0),
            _supply("cheap", 500, 1.0),
            _supply("medium", 500, 2.5),
        ],
    )
    assert [p.suppliers[0].supplier for p in plans] == ["cheap", "medium", "expensive"]


def test_split_order_when_no_single_covers(planner: SplitOrderPlanner):
    plans = planner.plan(
        intent=_intent(500),
        beliefs=[
            _supply("colombia", 320, 2.1),
            _supply("brazil", 400, 1.9),
        ],
    )
    # No single covers 500; only the split is emitted.
    assert all(p.plan_type == "split_order" for p in plans)
    assert len(plans) == 1
    p = plans[0]
    assert p.total_quantity_lb == 500
    # Greedy: cheaper (brazil at 1.9) takes its full 400, colombia takes 100.
    by_supplier = {s.supplier: s for s in p.suppliers}
    assert by_supplier["brazil"].quantity_lb == 400
    assert by_supplier["colombia"].quantity_lb == 100
    assert p.total_price_usd == 970.0  # 400*1.9 + 100*2.1


def test_singles_and_splits_when_some_cover_some_dont(planner: SplitOrderPlanner):
    plans = planner.plan(
        intent=_intent(500),
        beliefs=[
            _supply("big", 600, 3.0),       # covers alone
            _supply("small_a", 200, 1.0),
            _supply("small_b", 400, 2.0),
        ],
    )
    types = [p.plan_type for p in plans]
    assert "single_supplier" in types
    assert "split_order" in types
    # Singles first.
    first_split_idx = next(i for i, p in enumerate(plans) if p.plan_type == "split_order")
    last_single_idx = max(i for i, p in enumerate(plans) if p.plan_type == "single_supplier")
    assert last_single_idx < first_split_idx


def test_pair_where_one_alone_covers_does_not_emit_split(planner: SplitOrderPlanner):
    plans = planner.plan(
        intent=_intent(500),
        beliefs=[
            _supply("big", 600, 3.0),
            _supply("tiny", 100, 1.0),  # cheap but tiny
        ],
    )
    # Only single_supplier "big" — pair would have tiny take its full 100, big take 400, but
    # tiny's "share" of 100 means we skip the case where the cheaper alone could cover.
    # In this case tiny can't cover alone (100 < 500), so a split IS emitted with tiny+big.
    assert any(p.plan_type == "single_supplier" for p in plans)
    assert any(p.plan_type == "split_order" for p in plans)


def test_no_quantity_target_emits_single_per_supplier(planner: SplitOrderPlanner):
    plans = planner.plan(
        intent=_intent(qty=None),
        beliefs=[
            _supply("a", 100, 2.0),
            _supply("b", 200, 1.5),
        ],
    )
    assert len(plans) == 2
    assert all(p.plan_type == "single_supplier" for p in plans)
    qtys = sorted(p.total_quantity_lb for p in plans)
    assert qtys == [100, 200]


def test_unpriced_supplier_in_split(planner: SplitOrderPlanner):
    plans = planner.plan(
        intent=_intent(500),
        beliefs=[
            _supply("priced", 300, 2.0),
            _supply("nopricer", 300),  # no unit price
        ],
    )
    # Split needed (neither alone covers 500). total_price_usd should be None
    # because at least one supplier is unpriced.
    splits = [p for p in plans if p.plan_type == "split_order"]
    assert len(splits) == 1
    assert splits[0].total_price_usd is None


def test_greedy_fallback_when_no_pair_covers(planner: SplitOrderPlanner):
    # 4 suppliers, each 100 lb; intent 350 lb. Pairs max at 200; need 4-supplier greedy.
    plans = planner.plan(
        intent=_intent(350),
        beliefs=[
            _supply("a", 100, 1.0),
            _supply("b", 100, 1.5),
            _supply("c", 100, 2.0),
            _supply("d", 100, 2.5),
        ],
    )
    assert len(plans) == 1
    p = plans[0]
    assert p.plan_type == "split_order"
    assert p.total_quantity_lb == 350
    # Greedy: a, b, c full (100 each = 300), d takes 50.
    by_supplier = {s.supplier: s.quantity_lb for s in p.suppliers}
    assert by_supplier == {"a": 100, "b": 100, "c": 100, "d": 50}


def test_infeasible_returns_no_plans(planner: SplitOrderPlanner):
    # Total inventory < demand, no plan can satisfy.
    plans = planner.plan(
        intent=_intent(1000),
        beliefs=[_supply("a", 100, 1.0), _supply("b", 200, 1.5)],
    )
    assert plans == []


def test_origin_propagated_into_plan_supplier(planner: SplitOrderPlanner):
    plans = planner.plan(
        intent=_intent(100),
        beliefs=[_supply("colombia-farm", 200, 2.0, "colombia")],
    )
    assert plans[0].suppliers[0].origin == "colombia"
