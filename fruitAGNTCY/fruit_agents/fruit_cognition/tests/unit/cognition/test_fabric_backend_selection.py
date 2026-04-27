"""Backend selection rules for get_fabric().

Verifies admin-set DSN beats env, env beats absence, and reset_fabric()
plus set_active_dsn() correctly invalidate the cached singleton.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cognition.services.cognition_fabric import (
    InMemoryCognitionFabric,
    get_active_dsn,
    get_fabric,
    reset_fabric,
    set_active_dsn,
)


@pytest.fixture(autouse=True)
def _clean():
    set_active_dsn(None)
    reset_fabric()
    yield
    set_active_dsn(None)
    reset_fabric()


def test_no_dsn_uses_in_memory(monkeypatch):
    monkeypatch.delenv("COGNITION_PG_DSN", raising=False)
    assert get_active_dsn() is None
    fabric = get_fabric()
    assert isinstance(fabric, InMemoryCognitionFabric)


def test_env_dsn_uses_pg(monkeypatch):
    monkeypatch.setenv("COGNITION_PG_DSN", "postgresql://x@h/y")
    assert get_active_dsn() == "postgresql://x@h/y"
    with patch(
        "cognition.services.pg_cognition_fabric.PgCognitionFabric"
    ) as PgMock:
        PgMock.return_value = object()  # placeholder fabric
        fabric = get_fabric()
        PgMock.assert_called_once_with("postgresql://x@h/y")
    assert fabric is PgMock.return_value


def test_override_dsn_beats_env(monkeypatch):
    monkeypatch.setenv("COGNITION_PG_DSN", "postgresql://from-env/db")
    set_active_dsn("postgresql://from-admin/db")
    assert get_active_dsn() == "postgresql://from-admin/db"
    with patch(
        "cognition.services.pg_cognition_fabric.PgCognitionFabric"
    ) as PgMock:
        PgMock.return_value = object()
        get_fabric()
        PgMock.assert_called_once_with("postgresql://from-admin/db")


def test_set_active_dsn_invalidates_cache(monkeypatch):
    monkeypatch.delenv("COGNITION_PG_DSN", raising=False)
    a = get_fabric()
    assert isinstance(a, InMemoryCognitionFabric)

    set_active_dsn("postgresql://x@h/y")
    with patch(
        "cognition.services.pg_cognition_fabric.PgCognitionFabric"
    ) as PgMock:
        PgMock.return_value = object()
        b = get_fabric()
        assert b is not a
        PgMock.assert_called_once()


def test_clearing_override_falls_back(monkeypatch):
    monkeypatch.delenv("COGNITION_PG_DSN", raising=False)
    set_active_dsn("postgresql://x@h/y")
    with patch(
        "cognition.services.pg_cognition_fabric.PgCognitionFabric"
    ) as PgMock:
        PgMock.return_value = object()
        get_fabric()  # PG mock used
    set_active_dsn(None)
    fabric = get_fabric()
    assert isinstance(fabric, InMemoryCognitionFabric)


def test_reset_fabric_calls_close_when_present(monkeypatch):
    monkeypatch.setenv("COGNITION_PG_DSN", "postgresql://x@h/y")
    with patch(
        "cognition.services.pg_cognition_fabric.PgCognitionFabric"
    ) as PgMock:
        instance = PgMock.return_value
        instance.close = lambda: setattr(instance, "_closed", True)
        get_fabric()
        reset_fabric()
        assert getattr(instance, "_closed", False) is True
