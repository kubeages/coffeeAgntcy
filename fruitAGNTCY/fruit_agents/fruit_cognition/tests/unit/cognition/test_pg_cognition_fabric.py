"""Mock-based unit tests for PgCognitionFabric (SQL shape + payload round-trip).

Live-Postgres coverage lives in the integration suite; this file only
exercises the methods' SQL emission and payload (de)serialization with
psycopg.ConnectionPool patched out.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract


@contextmanager
def _ctx(value):
    yield value


def _make_pool(rows_by_query: dict[str, list[tuple]] | None = None):
    """Create a MagicMock that mimics psycopg_pool.ConnectionPool."""
    rows_by_query = rows_by_query or {}
    cursor = MagicMock()
    cursor.__enter__ = lambda self: cursor
    cursor.__exit__ = lambda self, *a: None

    captured: list[tuple[str, tuple | None]] = []

    def execute(sql, params=None):
        captured.append((sql, params))
        # Pick rows for the most recent SELECT by substring match.
        for key, rows in rows_by_query.items():
            if key in sql:
                cursor._rows = list(rows)
                return
        cursor._rows = []

    cursor.execute = execute
    cursor.fetchone = lambda: cursor._rows[0] if cursor._rows else None
    cursor.fetchall = lambda: list(cursor._rows)

    conn = MagicMock()
    conn.cursor = lambda: cursor

    pool = MagicMock()
    pool.connection = lambda: _ctx(conn)
    pool.close = MagicMock()
    return pool, captured


@pytest.fixture
def fabric():
    """A PgCognitionFabric with the connection pool patched to a mock."""
    from cognition.services import pg_cognition_fabric as mod

    with patch.object(mod, "ConnectionPool") as PoolCls:
        pool, captured = _make_pool()
        PoolCls.return_value = pool
        f = mod.PgCognitionFabric("postgresql://test/db")
        f._captured = captured  # expose for assertions
        f._pool_mock = pool
        yield f


def test_init_runs_schema_creation(fabric):
    sqls = [s for s, _ in fabric._captured]
    assert any("CREATE TABLE IF NOT EXISTS cognition_intents" in s for s in sqls)
    assert any("CREATE TABLE IF NOT EXISTS cognition_claims" in s for s in sqls)


def test_save_intent_upsert(fabric):
    intent = IntentContract(goal="x", fruit_type="mango")
    fabric._captured.clear()
    fabric.save_intent(intent)
    sql, params = fabric._captured[-1]
    assert "INSERT INTO cognition_intents" in sql
    assert "ON CONFLICT (intent_id) DO UPDATE" in sql
    assert params[0] == intent.intent_id
    assert json.loads(params[1])["fruit_type"] == "mango"


def test_get_intent_returns_typed_object():
    from cognition.services import pg_cognition_fabric as mod

    intent = IntentContract(goal="x", fruit_type="apple")
    payload = intent.model_dump(mode="json")
    with patch.object(mod, "ConnectionPool") as PoolCls:
        pool, _ = _make_pool({"FROM cognition_intents WHERE intent_id": [(payload,)]})
        PoolCls.return_value = pool
        f = mod.PgCognitionFabric("postgresql://test/db")
        got = f.get_intent(intent.intent_id)
    assert isinstance(got, IntentContract)
    assert got == intent


def test_get_intent_missing_returns_none(fabric):
    assert fabric.get_intent("nope") is None


def test_save_claim_inserts_with_intent_fk(fabric):
    claim = Claim(
        intent_id="i1", agent_id="a1", claim_type="inventory",
        subject="mango", value={"available_lb": 5},
    )
    fabric._captured.clear()
    fabric.save_claim(claim)
    sql, params = fabric._captured[-1]
    assert "INSERT INTO cognition_claims" in sql
    assert "ON CONFLICT (claim_id) DO NOTHING" in sql
    assert params == (claim.claim_id, "i1", json.dumps(claim.model_dump(mode="json")))


def test_list_claims_returns_typed_objects():
    from cognition.services import pg_cognition_fabric as mod

    c1 = Claim(intent_id="i", agent_id="a", claim_type="inventory", subject="mango", value={"x": 1})
    c2 = Claim(intent_id="i", agent_id="a", claim_type="price", subject="mango", value={"y": 2})
    rows = [(c1.model_dump(mode="json"),), (c2.model_dump(mode="json"),)]
    with patch.object(mod, "ConnectionPool") as PoolCls:
        pool, _ = _make_pool({"FROM cognition_claims WHERE intent_id": rows})
        PoolCls.return_value = pool
        f = mod.PgCognitionFabric("postgresql://test/db")
        got = f.list_claims("i")
    assert [c.claim_type for c in got] == ["inventory", "price"]


def test_list_intents_returns_typed_objects():
    from cognition.services import pg_cognition_fabric as mod

    a = IntentContract(goal="x", fruit_type="mango")
    b = IntentContract(goal="x", fruit_type="apple")
    rows = [(a.model_dump(mode="json"),), (b.model_dump(mode="json"),)]
    with patch.object(mod, "ConnectionPool") as PoolCls:
        pool, _ = _make_pool({"FROM cognition_intents ORDER BY": rows})
        PoolCls.return_value = pool
        f = mod.PgCognitionFabric("postgresql://test/db")
        got = f.list_intents()
    assert {i.intent_id for i in got} == {a.intent_id, b.intent_id}


def test_close_releases_pool(fabric):
    fabric.close()
    fabric._pool_mock.close.assert_called_once()


def test_verify_dsn_handles_connection_failure():
    from cognition.services import pg_cognition_fabric as mod
    import psycopg

    with patch.object(mod, "psycopg") as pg_mock:
        pg_mock.Error = psycopg.Error
        pg_mock.connect.side_effect = psycopg.OperationalError("nope")
        ok, msg = mod.verify_dsn("postgresql://x@h/y", timeout_seconds=0.1)
    assert ok is False
    assert "nope" in msg or "failed" in msg.lower()


def test_verify_dsn_returns_human_readable_summary_on_success():
    from cognition.services import pg_cognition_fabric as mod

    cur = MagicMock()
    cur.__enter__ = lambda self: cur
    cur.__exit__ = lambda self, *a: None
    cur.fetchone.return_value = ("ages", "fruit_cognition", "PostgreSQL 16.4 on linux")
    conn = MagicMock()
    conn.__enter__ = lambda self: conn
    conn.__exit__ = lambda self, *a: None
    conn.cursor = lambda: cur

    with patch.object(mod, "psycopg") as pg_mock:
        pg_mock.connect.return_value = conn
        ok, msg = mod.verify_dsn("postgresql://x@h/y")
    assert ok is True
    assert "PostgreSQL 16.4" in msg
    assert "ages" in msg
    assert "fruit_cognition" in msg
