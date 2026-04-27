"""HTTP-level checks that the cognition layer is wired into both supervisors.

Mocks the LangGraph at app.state and asserts:
  - /agent/prompt and /agent/prompt/stream return 200,
  - the response carries intent_id (and the full intent payload for sync),
  - the same intent_id is threaded into graph.serve / graph.streaming_serve,
  - the intent lands in the in-memory cognition fabric.

These tests don't need a real LLM, transport, or agent — just the FastAPI app
and the cognition wiring around graph.serve.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient

# Set env required by config.config before any supervisor module is imported.
os.environ.setdefault("LLM_MODEL", "openai/gpt-4o-mini")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("HOT_RELOAD_MODE", "false")

_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


from cognition.services.cognition_fabric import get_fabric, reset_fabric  # noqa: E402


SUPERVISORS = [
    pytest.param("agents.supervisors.auction.main", "exchange_graph", id="auction"),
    pytest.param("agents.supervisors.logistics.main", "logistic_graph", id="logistics"),
]


@pytest.fixture(autouse=True)
def _clean_fabric():
    reset_fabric()
    yield
    reset_fabric()


@pytest.fixture
def fake_graph():
    """A graph stand-in that records the intent_id it was invoked with."""

    class FakeGraph:
        def __init__(self) -> None:
            self.last_intent_id: str | None = None
            self.last_stream_intent_id: str | None = None

        async def serve(self, prompt: str, intent_id: str | None = None) -> str:
            self.last_intent_id = intent_id
            return f"served: {prompt}"

        async def streaming_serve(self, prompt: str, intent_id: str | None = None) -> AsyncIterator[str]:
            self.last_stream_intent_id = intent_id
            yield "chunk-1"
            yield "chunk-2"

    return FakeGraph()


def _client_for(module_path: str, graph_attr: str, fake_graph) -> TestClient:
    mod = importlib.import_module(module_path)
    setattr(mod.app.state, graph_attr, fake_graph)
    return TestClient(mod.app)


PROMPT = "I need 250 lb mango within 5 days under $700"


@pytest.mark.parametrize("module_path,graph_attr", SUPERVISORS)
def test_sync_prompt_creates_intent_and_threads_id(module_path, graph_attr, fake_graph):
    client = _client_for(module_path, graph_attr, fake_graph)

    resp = client.post("/agent/prompt", json={"prompt": PROMPT})

    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["intent_id"].startswith("fruit-intent-")
    assert body["intent"]["fruit_type"] == "mango"
    assert body["intent"]["quantity_lb"] == 250.0
    assert body["intent"]["max_price_usd"] == 700.0
    assert body["intent"]["delivery_days"] == 5

    # Graph received exactly the same intent_id we returned to the caller.
    assert fake_graph.last_intent_id == body["intent_id"]

    # And it landed in the fabric.
    saved = get_fabric().get_intent(body["intent_id"])
    assert saved is not None
    assert saved.fruit_type == "mango"


@pytest.mark.parametrize("module_path,graph_attr", SUPERVISORS)
def test_stream_prompt_threads_intent_id_into_chunks(module_path, graph_attr, fake_graph):
    client = _client_for(module_path, graph_attr, fake_graph)

    resp = client.post("/agent/prompt/stream", json={"prompt": PROMPT})

    assert resp.status_code == 200, resp.text
    chunks = [json.loads(line) for line in resp.text.strip().splitlines() if line]
    assert len(chunks) == 2
    intent_ids = {c["intent_id"] for c in chunks}
    assert len(intent_ids) == 1
    intent_id = intent_ids.pop()
    assert intent_id.startswith("fruit-intent-")
    assert fake_graph.last_stream_intent_id == intent_id


@pytest.mark.parametrize("module_path,graph_attr", SUPERVISORS)
def test_each_request_gets_a_fresh_intent_id(module_path, graph_attr, fake_graph):
    client = _client_for(module_path, graph_attr, fake_graph)

    a = client.post("/agent/prompt", json={"prompt": PROMPT}).json()["intent_id"]
    b = client.post("/agent/prompt", json={"prompt": PROMPT}).json()["intent_id"]
    assert a != b
    # Both persisted independently.
    assert get_fabric().get_intent(a) is not None
    assert get_fabric().get_intent(b) is not None
