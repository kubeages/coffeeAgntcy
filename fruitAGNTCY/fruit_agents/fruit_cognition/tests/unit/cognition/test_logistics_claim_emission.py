"""Logistics-supervisor claim emission helper.

Validates that _record_logistics_claims maps a completed order into the
existing shipping_cost / delivery_sla / payment_status claim types and
writes them to the active fabric.
"""

from __future__ import annotations

import os
import sys

import pytest

# The supervisor module imports a couple of env-driven configs at import time.
os.environ.setdefault("LLM_MODEL", "openai/gpt-4o-mini")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

sys.path.insert(
    0,
    "/home/ages/apps/Dev/Cisco/fruitCognition/fruitAGNTCY/fruit_agents/fruit_cognition",
)

from agents.supervisors.logistics.graph.graph import (  # noqa: E402
    _record_logistics_claims,
)
from cognition.services.cognition_fabric import get_fabric, reset_fabric  # noqa: E402


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("COGNITION_PG_DSN", raising=False)
    monkeypatch.setenv("COGNITION_CLAIM_EXTRACTION", "true")
    reset_fabric()
    yield
    reset_fabric()


def test_no_claims_without_intent_id():
    _record_logistics_claims(
        None, farm="brazil", quantity=100, price=2.5, tool_result="DELIVERED",
    )
    assert get_fabric().list_claims("any") == []


def test_extraction_disabled_emits_nothing(monkeypatch):
    monkeypatch.setenv("COGNITION_CLAIM_EXTRACTION", "false")
    _record_logistics_claims(
        "i-1", farm="brazil", quantity=100, price=2.5, tool_result="DELIVERED",
    )
    assert get_fabric().list_claims("i-1") == []


def test_delivered_order_emits_shipping_and_payment_claims():
    intent_id = "fruit-intent-test"
    tool_result = (
        "Order f4ab2db6-5e5b-4a1e-9b7d-9c1ddef0bd23 from Brazil for 100 units "
        "at $2.5. ETA 6 days. DELIVERED."
    )
    _record_logistics_claims(
        intent_id, farm="brazil", quantity=100, price=2.5, tool_result=tool_result,
    )
    claims = get_fabric().list_claims(intent_id)
    types = sorted(c.claim_type for c in claims)
    # Mapper produces shipping_cost (from quantity * price) + delivery_sla (eta_days from text)
    # + payment_status (status + order_id from text).
    assert "shipping_cost" in types
    assert "payment_status" in types
    # delivery_sla optional — depends on whether the regex picked up "ETA 6 days".
    assert "delivery_sla" in types

    by_type = {c.claim_type: c for c in claims}
    assert by_type["shipping_cost"].agent_id == "logistics-shipper"
    assert by_type["shipping_cost"].value["shipping_cost_usd"] == pytest.approx(250.0)
    assert by_type["delivery_sla"].value.get("eta_days") == 6
    assert by_type["payment_status"].agent_id == "logistics-accountant"
    assert by_type["payment_status"].value["status"] == "delivered"
    assert by_type["payment_status"].value["amount_usd"] == pytest.approx(250.0)
    # order_id parsed from the freeform text
    assert by_type["payment_status"].value["order_id"] == "f4ab2db6-5e5b-4a1e-9b7d-9c1ddef0bd23"


def test_pending_status_when_not_delivered():
    intent_id = "fruit-intent-test-2"
    _record_logistics_claims(
        intent_id, farm="vietnam", quantity=200, price=1.0,
        tool_result="Order accepted; in transit.",
    )
    claims = get_fabric().list_claims(intent_id)
    payment = next(c for c in claims if c.claim_type == "payment_status")
    assert payment.value["status"] == "pending"
    assert payment.value["order_id"] == "unknown"  # no UUID in text


def test_route_propagated_into_claim_subject():
    intent_id = "fruit-intent-test-3"
    _record_logistics_claims(
        intent_id, farm="colombia", quantity=50, price=3.0, tool_result="DELIVERED",
    )
    shipping = [c for c in get_fabric().list_claims(intent_id) if c.claim_type == "shipping_cost"]
    assert shipping[0].subject == "colombia"
