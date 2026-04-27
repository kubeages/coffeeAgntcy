from __future__ import annotations

import logging
import os
import threading
from typing import Protocol

from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract


logger = logging.getLogger("fruit_cognition.cognition.fabric")


class CognitionFabric(Protocol):
    """Storage interface shared by the in-memory and Postgres backends."""

    def save_intent(self, intent: IntentContract) -> None: ...
    def get_intent(self, intent_id: str) -> IntentContract | None: ...
    def list_intents(self) -> list[IntentContract]: ...
    def save_claim(self, claim: Claim) -> None: ...
    def list_claims(self, intent_id: str) -> list[Claim]: ...


class InMemoryCognitionFabric:
    """Process-local cognition store. Lost on restart."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.intents: dict[str, IntentContract] = {}
        self.claims: dict[str, list[Claim]] = {}

    def save_intent(self, intent: IntentContract) -> None:
        with self._lock:
            self.intents[intent.intent_id] = intent

    def get_intent(self, intent_id: str) -> IntentContract | None:
        with self._lock:
            return self.intents.get(intent_id)

    def list_intents(self) -> list[IntentContract]:
        with self._lock:
            return list(self.intents.values())

    def save_claim(self, claim: Claim) -> None:
        with self._lock:
            self.claims.setdefault(claim.intent_id, []).append(claim)

    def list_claims(self, intent_id: str) -> list[Claim]:
        with self._lock:
            return list(self.claims.get(intent_id, []))


# ----- backend selection -----
#
# The active fabric is chosen at first access:
#   1. Admin-set runtime DSN (set_active_dsn) wins.
#   2. Else env COGNITION_PG_DSN.
#   3. Else InMemoryCognitionFabric.
#
# set_active_dsn() and reset_fabric() invalidate the singleton so the next
# get_fabric() call rebuilds with the current resolution.

_singleton: CognitionFabric | None = None
_override_dsn: str | None = None
_singleton_lock = threading.Lock()


def _resolve_dsn() -> str | None:
    if _override_dsn:
        return _override_dsn
    return os.getenv("COGNITION_PG_DSN") or None


def _build_fabric(dsn: str | None) -> CognitionFabric:
    if not dsn:
        logger.info("cognition fabric: InMemoryCognitionFabric (no DSN configured)")
        return InMemoryCognitionFabric()
    # Lazy import — keeps psycopg out of code paths that never touch Postgres.
    from cognition.services.pg_cognition_fabric import PgCognitionFabric

    logger.info("cognition fabric: PgCognitionFabric")
    return PgCognitionFabric(dsn)


def get_fabric() -> CognitionFabric:
    """Return the process-wide cognition fabric, building it on first access."""
    global _singleton
    if _singleton is not None:
        return _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = _build_fabric(_resolve_dsn())
    return _singleton


def reset_fabric() -> None:
    """Drop the singleton (closing its pool if present). For tests + DSN changes."""
    global _singleton
    with _singleton_lock:
        if _singleton is not None:
            close = getattr(_singleton, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    logger.exception("error closing cognition fabric")
        _singleton = None


def set_active_dsn(dsn: str | None) -> None:
    """Override the DSN at runtime (used by the admin panel) and refresh."""
    global _override_dsn
    with _singleton_lock:
        _override_dsn = dsn or None
    reset_fabric()


def get_active_dsn() -> str | None:
    """Return the DSN that the next get_fabric() call would use, or None."""
    return _resolve_dsn()
