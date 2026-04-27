import pytest

from cognition.schemas.sstp_message import SSTPMessage
from cognition.services.sstp_factory import SSTPFactory, envelope_enabled, wrap


def test_envelope_enabled_default_false(monkeypatch):
    monkeypatch.delenv("COGNITION_ENVELOPE_ENABLED", raising=False)
    assert envelope_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
def test_envelope_enabled_truthy(monkeypatch, value: str):
    monkeypatch.setenv("COGNITION_ENVELOPE_ENABLED", value)
    assert envelope_enabled() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "anything-else"])
def test_envelope_enabled_falsy(monkeypatch, value: str):
    monkeypatch.setenv("COGNITION_ENVELOPE_ENABLED", value)
    assert envelope_enabled() is False


def test_factory_build_minimal():
    factory = SSTPFactory(sender_agent="colombia-mango-farm", conversation_phase="grounding")
    msg = factory.build(
        intent_id="fruit-intent-abc",
        speech_act="claim",
        semantic_payload={"available_lb": 320},
    )
    assert isinstance(msg, SSTPMessage)
    assert msg.intent_id == "fruit-intent-abc"
    assert msg.sender_agent == "colombia-mango-farm"
    assert msg.receiver_agent is None
    assert msg.conversation_phase == "grounding"
    assert msg.speech_act == "claim"
    assert msg.semantic_payload == {"available_lb": 320}
    assert msg.evidence_refs == []
    assert msg.message_id.startswith("sstp-")


def test_factory_build_with_receiver_and_evidence():
    factory = SSTPFactory(sender_agent="brazil-banana-farm", conversation_phase="negotiating")
    msg = factory.build(
        intent_id="fruit-intent-xyz",
        speech_act="proposal",
        semantic_payload={"unit_price_usd": 1.4},
        receiver_agent="fruit-exchange",
        evidence_refs=["price:brazil-banana:2026-04-27"],
    )
    assert msg.receiver_agent == "fruit-exchange"
    assert msg.evidence_refs == ["price:brazil-banana:2026-04-27"]


def test_wrap_helper():
    msg = wrap(
        intent_id="fruit-intent-abc",
        sender_agent="vietnam-strawberry-farm",
        conversation_phase="grounding",
        speech_act="claim",
        semantic_payload={"quality_score": 0.92},
    )
    assert msg.sender_agent == "vietnam-strawberry-farm"
    assert msg.semantic_payload == {"quality_score": 0.92}
    assert msg.evidence_refs == []
