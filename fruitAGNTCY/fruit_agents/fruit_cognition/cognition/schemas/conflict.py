from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ConflictSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Conflict(BaseModel):
    """A flag the resolver raises when claims/beliefs/constraints disagree.

    Conflicts are advisory — they do not remove options from consideration.
    Enforcement is the guardrail's job (SPEC §4.8).
    """

    conflict_id: str = Field(default_factory=lambda: f"conflict-{uuid4()}")
    intent_id: str
    conflict_type: str
    description: str
    involved_claims: list[str] = Field(default_factory=list)
    involved_beliefs: list[str] = Field(default_factory=list)
    severity: ConflictSeverity = ConflictSeverity.MEDIUM
    suggested_resolution: str | None = None
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
