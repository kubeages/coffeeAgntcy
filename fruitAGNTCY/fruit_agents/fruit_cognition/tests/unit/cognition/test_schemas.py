from cognition.schemas import Claim, IntentContract, IntentStatus, SSTPMessage


def test_intent_contract_defaults():
    intent = IntentContract(goal="source 500 lb of mangoes")
    assert intent.intent_id.startswith("fruit-intent-")
    assert intent.status is IntentStatus.DRAFT
    assert intent.hard_constraints == {}
    assert intent.soft_constraints == {}
    assert intent.human_approval_required_if == []


def test_intent_contract_with_fields():
    intent = IntentContract(
        goal="source mangoes for next week",
        fruit_type="mango",
        quantity_lb=500.0,
        max_price_usd=1200.0,
        delivery_days=7,
        hard_constraints={"organic": True},
        human_approval_required_if=["price_above_budget"],
        status=IntentStatus.GROUNDING,
    )
    assert intent.fruit_type == "mango"
    assert intent.quantity_lb == 500.0
    assert intent.status is IntentStatus.GROUNDING


def test_intent_contract_round_trip():
    intent = IntentContract(goal="x", fruit_type="apple")
    serialized = intent.model_dump_json()
    restored = IntentContract.model_validate_json(serialized)
    assert restored == intent


def test_claim_defaults():
    claim = Claim(
        intent_id="fruit-intent-abc",
        agent_id="colombia-mango-farm",
        claim_type="inventory",
        subject="mango",
        value={"available_lb": 320, "origin": "colombia"},
    )
    assert claim.claim_id.startswith("claim-")
    assert claim.confidence == 1.0
    assert claim.evidence_refs == []
    assert claim.created_at  # ISO timestamp populated


def test_claim_round_trip():
    claim = Claim(
        intent_id="fruit-intent-abc",
        agent_id="brazil-banana-farm",
        claim_type="price",
        subject="banana",
        value={"unit_price_usd": 1.4},
        confidence=0.85,
        evidence_refs=["price:brazil-banana:2026-04-27"],
    )
    serialized = claim.model_dump_json()
    restored = Claim.model_validate_json(serialized)
    assert restored == claim


def test_sstp_message_defaults():
    msg = SSTPMessage(
        intent_id="fruit-intent-abc",
        sender_agent="colombia-mango-farm",
        conversation_phase="grounding",
        speech_act="claim",
        semantic_payload={"claim_type": "inventory"},
    )
    assert msg.message_id.startswith("sstp-")
    assert msg.sstp_version == "0.1"
    assert msg.receiver_agent is None
    assert msg.evidence_refs == []


def test_sstp_message_round_trip():
    msg = SSTPMessage(
        intent_id="fruit-intent-abc",
        sender_agent="colombia-mango-farm",
        receiver_agent="fruit-exchange",
        conversation_phase="grounding",
        speech_act="claim",
        semantic_payload={
            "claim_type": "inventory",
            "fruit_type": "mango",
            "available_lb": 320,
        },
        evidence_refs=["inventory:colombia-mango-farm:latest"],
    )
    serialized = msg.model_dump_json()
    restored = SSTPMessage.model_validate_json(serialized)
    assert restored == msg
