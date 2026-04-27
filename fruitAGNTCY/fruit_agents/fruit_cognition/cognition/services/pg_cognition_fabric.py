from __future__ import annotations

import json
import logging
import threading
from typing import Any

import psycopg
from psycopg_pool import ConnectionPool

from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract


logger = logging.getLogger("fruit_cognition.cognition.pg_fabric")


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS cognition_intents (
    intent_id   TEXT PRIMARY KEY,
    payload     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cognition_claims (
    claim_id    TEXT PRIMARY KEY,
    intent_id   TEXT NOT NULL,
    payload     JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS cognition_claims_intent_idx
    ON cognition_claims (intent_id);
"""


class PgCognitionFabric:
    """Postgres-backed CognitionFabric. Sync interface so it can drop into
    the existing call sites (which already live inside async handlers but
    don't await the fabric)."""

    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 4) -> None:
        self.dsn = dsn
        self._pool = ConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"autocommit": True},
            open=True,
        )
        self._schema_lock = threading.Lock()
        self._schema_ready = False
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        with self._schema_lock:
            if self._schema_ready:
                return
            with self._pool.connection() as conn, conn.cursor() as cur:
                cur.execute(_SCHEMA_SQL)
            self._schema_ready = True
            logger.info("cognition_intents / cognition_claims schema ensured")

    # ----- intents -----

    def save_intent(self, intent: IntentContract) -> None:
        payload = intent.model_dump(mode="json")
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cognition_intents (intent_id, payload)
                VALUES (%s, %s::jsonb)
                ON CONFLICT (intent_id) DO UPDATE
                  SET payload = EXCLUDED.payload,
                      updated_at = NOW()
                """,
                (intent.intent_id, json.dumps(payload)),
            )

    def get_intent(self, intent_id: str) -> IntentContract | None:
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM cognition_intents WHERE intent_id = %s",
                (intent_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return IntentContract.model_validate(_to_dict(row[0]))

    def list_intents(self) -> list[IntentContract]:
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT payload FROM cognition_intents ORDER BY created_at DESC")
            rows = cur.fetchall()
        return [IntentContract.model_validate(_to_dict(r[0])) for r in rows]

    # ----- claims -----

    def save_claim(self, claim: Claim) -> None:
        payload = claim.model_dump(mode="json")
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cognition_claims (claim_id, intent_id, payload)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (claim_id) DO NOTHING
                """,
                (claim.claim_id, claim.intent_id, json.dumps(payload)),
            )

    def list_claims(self, intent_id: str) -> list[Claim]:
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT payload FROM cognition_claims WHERE intent_id = %s ORDER BY created_at ASC",
                (intent_id,),
            )
            rows = cur.fetchall()
        return [Claim.model_validate(_to_dict(r[0])) for r in rows]

    def close(self) -> None:
        try:
            self._pool.close()
        except Exception:
            logger.exception("error closing pg pool")


def _to_dict(value: Any) -> dict:
    """psycopg returns JSONB as already-decoded dicts, but be defensive."""
    if isinstance(value, dict):
        return value
    if isinstance(value, (str, bytes)):
        return json.loads(value)
    raise TypeError(f"unexpected jsonb type: {type(value)}")


def verify_dsn(dsn: str, *, timeout_seconds: float = 3.0) -> tuple[bool, str]:
    """One-shot connection probe used by the admin panel.

    Returns ``(ok, message)``. The message is a one-liner suitable for
    surfacing in the UI (e.g. "connected to Postgres 16.4 as ages on
    fruit_cognition").
    """
    try:
        with psycopg.connect(dsn, connect_timeout=timeout_seconds) as conn, conn.cursor() as cur:
            cur.execute("SELECT current_user, current_database(), version()")
            user, db, version = cur.fetchone()
        short_ver = version.split(",")[0] if version else "Postgres"
        return True, f"connected to {short_ver} as {user} on {db}"
    except psycopg.Error as e:
        return False, f"connection failed: {e.diag.message_primary if hasattr(e, 'diag') and e.diag else e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
