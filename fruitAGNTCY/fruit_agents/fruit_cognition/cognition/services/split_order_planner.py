"""Split-order planner: compose candidate plans from supply_option beliefs.

Pure function. Output a small bounded set of feasible plans:

  * Every supplier with enough inventory becomes a single-supplier plan.
  * If no single supplier covers the demand, all 2-supplier pairs whose
    combined inventory covers the demand become split_order plans.
  * If 2-supplier splits also fail to cover, falls back to greedy
    multi-supplier (3+) using cheapest-first allocation. Hard cap at
    ``MAX_SUPPLIERS_PER_PLAN`` to bound combinatorics.

The DecisionEngine (iter 14) ranks the candidate plans; the planner
itself stays unaware of policy / weather / cost preferences.
"""

from __future__ import annotations

from itertools import combinations
from typing import Iterable

from cognition.schemas.belief import Belief
from cognition.schemas.intent_contract import IntentContract
from cognition.schemas.plan import Plan, PlanSupplier


MAX_SUPPLIERS_PER_PLAN = 4


def _supply_options(beliefs: Iterable[Belief]) -> list[Belief]:
    return [
        b for b in beliefs
        if b.belief_type == "supply_option"
        and b.value.get("available_lb") is not None
    ]


def _belief_to_supplier(b: Belief, qty: float) -> PlanSupplier:
    return PlanSupplier(
        supplier=b.agent_id,
        quantity_lb=float(qty),
        unit_price_usd=(
            float(b.value["unit_price_usd"])
            if b.value.get("unit_price_usd") is not None else None
        ),
        origin=b.value.get("origin"),
    )


def _total_price(suppliers: list[PlanSupplier]) -> float | None:
    if any(s.unit_price_usd is None for s in suppliers):
        return None
    return round(
        sum(float(s.quantity_lb) * float(s.unit_price_usd) for s in suppliers),  # type: ignore[arg-type]
        2,
    )


def _make_plan(intent_id: str, plan_type: str, suppliers: list[PlanSupplier]) -> Plan:
    return Plan(
        intent_id=intent_id,
        plan_type=plan_type,  # type: ignore[arg-type]
        suppliers=suppliers,
        total_quantity_lb=round(sum(s.quantity_lb for s in suppliers), 4),
        total_price_usd=_total_price(suppliers),
        feasible=True,
    )


def _greedy_split(
    intent_id: str,
    target_qty: float,
    options: list[Belief],
) -> Plan | None:
    """Cheapest-first allocation across up to MAX_SUPPLIERS_PER_PLAN suppliers."""
    # Sort by price ascending; unpriced go last.
    def _key(b: Belief) -> tuple[int, float]:
        p = b.value.get("unit_price_usd")
        return (0 if p is not None else 1, float(p) if p is not None else 0.0)

    ordered = sorted(options, key=_key)
    chosen: list[PlanSupplier] = []
    remaining = target_qty
    for b in ordered[:MAX_SUPPLIERS_PER_PLAN]:
        if remaining <= 0:
            break
        avail = float(b.value["available_lb"])
        take = min(remaining, avail)
        if take <= 0:
            continue
        chosen.append(_belief_to_supplier(b, take))
        remaining -= take

    if remaining > 0 or not chosen:
        return None
    return _make_plan(intent_id, "split_order", chosen)


class SplitOrderPlanner:
    def plan(
        self,
        *,
        intent: IntentContract,
        beliefs: Iterable[Belief],
    ) -> list[Plan]:
        options = _supply_options(beliefs)
        if not options:
            return []

        intent_id = intent.intent_id
        target_qty = intent.quantity_lb

        # No quantity target — single-supplier plans for whatever each supplier has.
        if target_qty is None:
            return [
                _make_plan(
                    intent_id, "single_supplier",
                    [_belief_to_supplier(b, float(b.value["available_lb"]))],
                )
                for b in options
            ]

        # 1) Single-supplier plans for any supplier with full coverage.
        singles = [
            _make_plan(
                intent_id, "single_supplier",
                [_belief_to_supplier(b, target_qty)],
            )
            for b in options
            if float(b.value["available_lb"]) >= target_qty
        ]

        # 2) 2-supplier splits for any pair whose combined inventory covers demand.
        pairs: list[Plan] = []
        for a, b in combinations(options, 2):
            avail_a = float(a.value["available_lb"])
            avail_b = float(b.value["available_lb"])
            if avail_a + avail_b < target_qty:
                continue
            # Greedy: cheaper-first up to its inventory, rest from the other.
            ap = a.value.get("unit_price_usd")
            bp = b.value.get("unit_price_usd")
            cheaper, dearer = (a, b) if (ap or 0) <= (bp or 0) else (b, a)
            cheaper_avail = float(cheaper.value["available_lb"])
            take_cheaper = min(cheaper_avail, target_qty)
            take_dearer = target_qty - take_cheaper
            if take_dearer <= 0:
                # Cheaper alone covers; this is a single_supplier already in `singles`.
                continue
            pairs.append(
                _make_plan(
                    intent_id, "split_order",
                    [
                        _belief_to_supplier(cheaper, take_cheaper),
                        _belief_to_supplier(dearer, take_dearer),
                    ],
                )
            )

        # 3) Greedy multi-supplier fallback if 2-supplier splits couldn't cover demand
        #    AND no single supplier covers it either.
        if not singles and not pairs:
            greedy = _greedy_split(intent_id, target_qty, options)
            return [greedy] if greedy is not None else []

        # Sort: singles first, then by total_price ascending (None to the end).
        all_plans = singles + pairs

        def _plan_key(p: Plan) -> tuple[int, int, float, str]:
            type_rank = 0 if p.plan_type == "single_supplier" else 1
            price_rank = 0 if p.total_price_usd is not None else 1
            price = p.total_price_usd if p.total_price_usd is not None else 0.0
            sup = ",".join(s.supplier for s in p.suppliers)
            return (type_rank, price_rank, price, sup)

        all_plans.sort(key=_plan_key)
        return all_plans
