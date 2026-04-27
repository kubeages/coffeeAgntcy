"""Admin /cognition/pg/* endpoints — verify, set, clear DSN."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.admin.router import _redact_dsn, create_admin_router
from cognition.services.cognition_fabric import (
    InMemoryCognitionFabric,
    get_active_dsn,
    reset_fabric,
    set_active_dsn,
)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("COGNITION_PG_DSN", raising=False)
    set_active_dsn(None)
    reset_fabric()
    yield
    set_active_dsn(None)
    reset_fabric()


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(create_admin_router(component_name="test-app"))
    return TestClient(app)


# ----- redaction helper -----


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("postgresql://user:secret@host:5432/db", "postgresql://user:***@host:5432/db"),
        ("postgresql://u:p@h/db", "postgresql://u:***@h/db"),
        ("postgresql://nopass@host/db", "postgresql://nopass@host/db"),
        ("postgresql:///socket", "postgresql:///socket"),
    ],
)
def test_redact_dsn(raw: str, expected: str):
    assert _redact_dsn(raw) == expected


# ----- POST /admin/cognition/pg/test (probe only, no swap) -----


def test_pg_test_success(client: TestClient):
    with patch("api.admin.router.verify_dsn", return_value=(True, "connected to PostgreSQL 16.4 as ages on fc")):
        r = client.post("/admin/cognition/pg/test", json={"dsn": "postgresql://x@h/y"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "PostgreSQL" in body["message"]
    assert isinstance(body["latency_ms"], int)
    # Probe must NOT swap the active fabric.
    assert get_active_dsn() is None


def test_pg_test_failure_does_not_raise(client: TestClient):
    with patch("api.admin.router.verify_dsn", return_value=(False, "connection refused")):
        r = client.post("/admin/cognition/pg/test", json={"dsn": "postgresql://x@h/y"})
    assert r.status_code == 200
    assert r.json() == {"ok": False, "message": "connection refused", "latency_ms": pytest.approx(r.json()["latency_ms"])}


# ----- GET /admin/cognition/pg/active (state introspection) -----


def test_active_default_is_in_memory(client: TestClient):
    r = client.get("/admin/cognition/pg/active")
    assert r.status_code == 200
    body = r.json()
    assert body == {"ok": True, "source": None, "dsn_redacted": None, "backend": "in_memory", "message": None}


def test_active_reflects_env_dsn(client: TestClient, monkeypatch):
    monkeypatch.setenv("COGNITION_PG_DSN", "postgresql://u:p@h:5432/db")
    # Patch PgCognitionFabric so the GET doesn't actually try to connect.
    with patch("cognition.services.pg_cognition_fabric.PgCognitionFabric") as PgMock:
        PgMock.return_value = object()
        r = client.get("/admin/cognition/pg/active")
    body = r.json()
    assert body["source"] == "env"
    assert body["dsn_redacted"] == "postgresql://u:***@h:5432/db"
    assert body["backend"] == "postgres"


# ----- POST /admin/cognition/pg/active (verify + swap) -----


def test_set_active_swaps_backend(client: TestClient):
    with patch("api.admin.router.verify_dsn", return_value=(True, "ok")), \
         patch("cognition.services.pg_cognition_fabric.PgCognitionFabric") as PgMock:
        PgMock.return_value = object()
        r = client.post("/admin/cognition/pg/active", json={"dsn": "postgresql://u:p@h/db"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "override"
    assert body["dsn_redacted"] == "postgresql://u:***@h/db"
    assert body["backend"] == "postgres"
    assert body["message"] == "ok"
    assert get_active_dsn() == "postgresql://u:p@h/db"


def test_set_active_rejects_bad_dsn(client: TestClient):
    with patch("api.admin.router.verify_dsn", return_value=(False, "auth failed")):
        r = client.post("/admin/cognition/pg/active", json={"dsn": "postgresql://x@h/y"})
    assert r.status_code == 400
    assert "auth failed" in r.json()["detail"]
    assert get_active_dsn() is None  # not swapped


# ----- DELETE /admin/cognition/pg/active -----


def test_clear_active_falls_back(client: TestClient):
    set_active_dsn("postgresql://x:y@h/db")
    r = client.delete("/admin/cognition/pg/active")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] is None
    assert body["dsn_redacted"] is None
    assert body["backend"] == "in_memory"
    assert get_active_dsn() is None


def test_clear_when_env_dsn_present_falls_back_to_env(client: TestClient, monkeypatch):
    monkeypatch.setenv("COGNITION_PG_DSN", "postgresql://e:e@h/db")
    set_active_dsn("postgresql://o:o@h/db")
    with patch("cognition.services.pg_cognition_fabric.PgCognitionFabric") as PgMock:
        PgMock.return_value = InMemoryCognitionFabric()  # cheat — just to materialize a fabric
        r = client.delete("/admin/cognition/pg/active")
    body = r.json()
    assert body["source"] == "env"
    assert body["dsn_redacted"] == "postgresql://e:***@h/db"
