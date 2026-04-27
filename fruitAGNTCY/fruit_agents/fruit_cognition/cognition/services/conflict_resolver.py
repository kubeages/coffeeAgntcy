"""Detect conflicts between an intent's constraints and the claims/beliefs
captured for it. Pure function: no I/O, no side effects.

Per SPEC §4.8 the resolver only **records** conflicts. The
PolicyGuardrailEngine (iter 12) decides whether the conflict actually
blocks an option from being selected.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from cognition.schemas.belief import Belief
from cognition.schemas.claim import Claim
from cognition.schemas.conflict import Conflict, ConflictSeverity
from cognition.schemas.intent_contract import IntentContract


# Tunables. Conservative defaults — easy for tests to reason about.
WEATHER_RISK_HIGH_THRESHOLD = 0.5
QUALITY_LOW_THRESHOLD = 0.6


class ConflictResolver:
    """Pure rule-based conflict detection."""

    def detect(
        self,
        *,
        intent: IntentContract,
        claims: Iterable[Claim],
        beliefs: Iterable[Belief],
    ) -> list[Conflict]:
        claims = list(claims)
        beliefs = list(beliefs)
        out: list[Conflict] = []

        out.extend(self._check_insufficient_inventory(intent, beliefs))
        out.extend(self._check_price_above_budget(intent, beliefs))
        out.extend(self._check_weather_risk_high(intent, claims))
        out.extend(self._check_delivery_sla_at_risk(intent, claims))
        out.extend(self._check_quality_below_threshold(intent, beliefs))
        out.extend(self._check_contradictory_claims(intent, claims))
        return out

    # ----- inventory -----

    def _check_insufficient_inventory(
        self, intent: IntentContract, beliefs: list[Belief]
    ) -> list[Conflict]:
        if intent.quantity_lb is None:
            return []
        supply_options = [b for b in beliefs if b.belief_type == "supply_option"]
        if not supply_options:
            return []

        out: list[Conflict] = []
        # Per-supplier flag — informational, MEDIUM severity.
        for b in supply_options:
            avail = b.value.get("available_lb")
            if avail is None or avail >= intent.quantity_lb:
                continue
            out.append(
                Conflict(
                    intent_id=intent.intent_id,
                    conflict_type="insufficient_inventory",
                    description=(
                        f"{b.agent_id} has {avail} lb available, but the intent "
                        f"requires {intent.quantity_lb} lb."
                    ),
                    involved_beliefs=[b.belief_id],
                    severity=ConflictSeverity.MEDIUM,
                    suggested_resolution="Split the order across multiple farms.",
                )
            )

        # Aggregate flag if even the union of all suppliers cannot cover the demand.
        total = sum(
            float(b.value.get("available_lb", 0) or 0)
            for b in supply_options
        )
        if total < intent.quantity_lb:
            out.append(
                Conflict(
                    intent_id=intent.intent_id,
                    conflict_type="insufficient_inventory",
                    description=(
                        f"Total available across all suppliers ({total} lb) is below "
                        f"the intent requirement ({intent.quantity_lb} lb)."
                    ),
                    involved_beliefs=[b.belief_id for b in supply_options],
                    severity=ConflictSeverity.HIGH,
                    suggested_resolution="Reduce quantity or extend delivery window.",
                )
            )
        return out

    # ----- price / budget -----

    def _check_price_above_budget(
        self, intent: IntentContract, beliefs: list[Belief]
    ) -> list[Conflict]:
        if intent.max_price_usd is None or intent.quantity_lb is None:
            return []
        out: list[Conflict] = []
        for b in beliefs:
            if b.belief_type != "supply_option":
                continue
            unit = b.value.get("unit_price_usd")
            if unit is None:
                continue
            total = float(unit) * float(intent.quantity_lb)
            if total <= float(intent.max_price_usd):
                continue
            out.append(
                Conflict(
                    intent_id=intent.intent_id,
                    conflict_type="price_above_budget",
                    description=(
                        f"{b.agent_id} would cost ${total:.2f} for {intent.quantity_lb} lb, "
                        f"above the ${intent.max_price_usd:.2f} budget."
                    ),
                    involved_beliefs=[b.belief_id],
                    severity=ConflictSeverity.HIGH,
                    suggested_resolution="Increase budget or pick a cheaper supplier.",
                )
            )
        return out

    # ----- weather -----

    def _check_weather_risk_high(
        self, intent: IntentContract, claims: list[Claim]
    ) -> list[Conflict]:
        out: list[Conflict] = []
        for c in claims:
            if c.claim_type != "weather_risk":
                continue
            score = c.value.get("weather_risk_score")
            if score is None or float(score) < WEATHER_RISK_HIGH_THRESHOLD:
                continue
            region = c.value.get("region", c.subject)
            forecast = c.value.get("forecast", "")
            out.append(
                Conflict(
                    intent_id=intent.intent_id,
                    conflict_type="weather_risk_high",
                    description=(
                        f"Weather risk for {region} is {score:.2f}"
                        + (f" ({forecast})" if forecast else "")
                    ),
                    involved_claims=[c.claim_id],
                    severity=ConflictSeverity.HIGH,
                    suggested_resolution=(
                        "Prefer a supplier from a different region or extend the delivery window."
                    ),
                )
            )
        return out

    # ----- delivery SLA -----

    def _check_delivery_sla_at_risk(
        self, intent: IntentContract, claims: list[Claim]
    ) -> list[Conflict]:
        if intent.delivery_days is None:
            return []
        out: list[Conflict] = []
        for c in claims:
            if c.claim_type != "delivery_sla":
                continue
            eta = c.value.get("eta_days") or c.value.get("sla_days")
            if eta is None or int(eta) <= int(intent.delivery_days):
                continue
            out.append(
                Conflict(
                    intent_id=intent.intent_id,
                    conflict_type="delivery_sla_at_risk",
                    description=(
                        f"{c.agent_id} ETA is {eta} days, beyond the {intent.delivery_days}-day window."
                    ),
                    involved_claims=[c.claim_id],
                    severity=ConflictSeverity.MEDIUM,
                    suggested_resolution="Pick a closer supplier or accept later delivery.",
                )
            )
        return out

    # ----- quality -----

    def _check_quality_below_threshold(
        self, intent: IntentContract, beliefs: list[Belief]
    ) -> list[Conflict]:
        threshold = float(
            intent.hard_constraints.get("min_quality_score", QUALITY_LOW_THRESHOLD)
            if isinstance(intent.hard_constraints, dict) else QUALITY_LOW_THRESHOLD
        )
        out: list[Conflict] = []
        for b in beliefs:
            if b.belief_type != "supply_option":
                continue
            q = b.value.get("quality_score")
            if q is None or float(q) >= threshold:
                continue
            out.append(
                Conflict(
                    intent_id=intent.intent_id,
                    conflict_type="quality_below_threshold",
                    description=(
                        f"{b.agent_id} quality score {q} is below threshold {threshold}."
                    ),
                    involved_beliefs=[b.belief_id],
                    severity=ConflictSeverity.MEDIUM,
                    suggested_resolution="Pick a higher-quality supplier.",
                )
            )
        return out

    # ----- contradictions -----

    def _check_contradictory_claims(
        self, intent: IntentContract, claims: list[Claim]
    ) -> list[Conflict]:
        # Same (agent_id, claim_type, subject) but different value keys disagreeing.
        groups: dict[tuple[str, str, str], list[Claim]] = defaultdict(list)
        for c in claims:
            groups[(c.agent_id, c.claim_type, c.subject)].append(c)
        out: list[Conflict] = []
        for (agent_id, claim_type, subject), group in groups.items():
            if len(group) < 2:
                continue
            # Look for divergent scalar values.
            scalar_keys = {"available_lb", "unit_price_usd", "quality_score", "eta_days"}
            for key in scalar_keys:
                vals = {c.value.get(key) for c in group if c.value.get(key) is not None}
                if len(vals) > 1:
                    out.append(
                        Conflict(
                            intent_id=intent.intent_id,
                            conflict_type="contradictory_claims",
                            description=(
                                f"{agent_id} reported {key}={sorted(map(str, vals))} for {subject} "
                                f"({claim_type})."
                            ),
                            involved_claims=[c.claim_id for c in group],
                            severity=ConflictSeverity.LOW,
                            suggested_resolution="Re-query the agent or trust the most recent claim.",
                        )
                    )
                    break  # one conflict per group is enough
        return out
