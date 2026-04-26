# fruitCognition — Internet of Cognition Evolution Spec

## 1. Purpose

This document defines the progressive evolution of `fruitCognition` from an **Internet of Agents** demo into an **Internet of Cognition** demo.

The current application demonstrates multi-agent collaboration across fruit farms, logistics, payment, weather, and orchestration using AGNTCY building blocks such as A2A, SLIM, NATS, MCP, LangGraph, Directory, Identity, and observability.

The target evolution is to add cognition-oriented capabilities:

- Shared intent
- Shared context
- Semantic state transfer
- Cognition fabric
- Beliefs and conflicts
- Decision engines
- Human-in-the-loop approvals
- Cognitive observability
- Historical memory and belief revision

The goal is not to replace the existing agentic architecture, but to extend it with a cognition layer that allows agents to reason over a common state, negotiate trade-offs, preserve context, and produce auditable decisions.

---

## 2. Current Baseline

The current baseline is assumed to follow this high-level flow:

```text
User / UI
  ↓
Fruit Exchange / Auction Supervisor
  ↓
LangGraph workflow
  ↓
A2A over SLIM / NATS
  ↓
Fruit farm agents
  ↓
MCP tools: weather, payment, etc.
  ↓
Logistics / accounting / support agents
  ↓
Observability / MCE / traces
```

The current system is agentic because agents can communicate and cooperate.

The target system should become cognitive because agents can share:

```text
intent → context → claims → beliefs → conflicts → decisions → memory
```

---

## 3. Target Conceptual Model

The evolved architecture introduces a cognition layer around the existing agent workflow.

```text
                              ┌───────────────────────────┐
                              │            UI             │
                              │ Chat + Cognition View     │
                              └─────────────┬─────────────┘
                                            │
                              ┌─────────────▼─────────────┐
                              │ Fruit Exchange Supervisor │
                              │ Existing LangGraph flow   │
                              └─────────────┬─────────────┘
                                            │
                              ┌─────────────▼─────────────┐
                              │     Intent Manager        │
                              │ Shared Intent Contract    │
                              └─────────────┬─────────────┘
                                            │
              ┌─────────────────────────────┼─────────────────────────────┐
              │                             │                             │
    ┌─────────▼─────────┐         ┌─────────▼─────────┐         ┌─────────▼─────────┐
    │ Fruit Farm Agents │         │ Logistics Agents  │         │ MCP Tools         │
    │ Mango/Apple/etc.  │         │ Shipper/Accountant│         │ Weather/Payment   │
    └─────────┬─────────┘         └─────────┬─────────┘         └─────────┬─────────┘
              │                             │                             │
              └─────────────────────┬───────┴───────────────┬─────────────┘
                                    │                       │
                          ┌─────────▼─────────┐   ┌─────────▼─────────┐
                          │ SSTP Envelope     │   │ Claims Extractor  │
                          └─────────┬─────────┘   └─────────┬─────────┘
                                    │                       │
                                    └───────────┬───────────┘
                                                │
                                    ┌───────────▼───────────┐
                                    │   Cognition Fabric    │
                                    │ intents/claims/beliefs│
                                    │ conflicts/decisions   │
                                    └───────────┬───────────┘
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 │                              │                              │
       ┌─────────▼─────────┐          ┌─────────▼─────────┐          ┌─────────▼─────────┐
       │ Cost Engine       │          │ Conflict Resolver │          │ Policy Guardrails │
       └─────────┬─────────┘          └─────────┬─────────┘          └─────────┬─────────┘
                 │                              │                              │
                 └──────────────────────────────┼──────────────────────────────┘
                                                │
                                    ┌───────────▼───────────┐
                                    │    Decision Engine    │
                                    │ recommendation + why  │
                                    └───────────┬───────────┘
                                                │
                                    ┌───────────▼───────────┐
                                    │ Human Approval / Order│
                                    └───────────────────────┘
```

---

## 4. Internet of Cognition Concepts Used

### 4.1 Shared Intent

A user request is transformed into a structured `IntentContract`.

This gives all participating agents a common understanding of:

- Goal
- Constraints
- Preferences
- Budget
- Quantity
- Risk thresholds
- Human approval conditions

### 4.2 Shared Context

Agents no longer just exchange plain messages. Their outputs are mapped into explicit claims that become part of a shared context.

Examples:

- Inventory claims
- Price claims
- Quality claims
- Weather claims
- Shipping claims
- Payment claims
- Compliance claims

### 4.3 Semantic State Transfer Protocol

The first practical implementation should be an SSTP-like envelope over the existing A2A messages.

This provides semantic metadata around messages:

- Intent ID
- Sender
- Receiver
- Conversation phase
- Speech act
- Semantic payload
- Evidence references
- Confidence

### 4.4 Cognition Fabric

A persistence layer that stores and versions cognitive state:

- Intents
- Claims
- Beliefs
- Conflicts
- Decisions
- Evidence
- Historical memories

### 4.5 Cognition Engines

Specialised services that operate over the cognition fabric:

- Cost Engine
- Weather Risk Engine
- Logistics Engine
- Policy Guardrail Engine
- Conflict Resolver
- Decision Engine

### 4.6 Human-in-the-Loop Cognition

The system should request human approval when:

- The selected option violates a hard constraint
- The selected option exceeds risk threshold
- The decision has low confidence
- The system finds unresolved conflicts
- A guardrail blocks autonomous execution

### 4.7 Cognitive Observability

The system should expose not only agent traces, but cognition traces:

```text
intent created
→ claims received
→ beliefs generated
→ conflicts detected
→ engines evaluated
→ decision produced
→ human approved/rejected
→ order committed
```

### 4.8 Resolver / Guardrail / Decision Engine Boundary

These three components share predicates (`price_above_budget`, `weather_risk_high`, etc.) but play distinct roles in the pipeline. To prevent overlap, each owns exactly one verb:

| Component                | Role          | Output                                               | Can it block? |
|--------------------------|---------------|------------------------------------------------------|---------------|
| `ConflictResolver`       | **Detect**    | `Conflict` records describing what's wrong, with severity and a suggested fix. Never suppresses options. | No |
| `PolicyGuardrailEngine`  | **Enforce**   | For each candidate option: `allowed: bool`, `requires_human_approval: bool`, list of violated policies. | Yes |
| `DecisionEngine`         | **Pick**      | A single recommended option, drawn only from those the guardrail marked `allowed`. Can require human approval if the guardrail flagged it. | No |

Pipeline order is fixed: **Resolver → Engines (Cost, Weather, …) → Guardrail → DecisionEngine**. Resolver and the cost/weather engines can run in parallel — the guardrail must run last because it consumes their outputs.

This means iter 9 (Resolver) and iter 12 (Guardrail) both check `price_above_budget`, but with different semantics: the resolver *flags it as a Conflict for visibility*, the guardrail *removes the option from consideration*. Both behaviours are intentional.

---

## 5. Design Principles

1. **Do not replace the existing AGNTCY architecture**
   - Keep A2A, SLIM, NATS, MCP, LangGraph and existing agents.
   - Add cognition as an extension layer.

2. **Start with SSTP, not LSTP**
   - Do not attempt latent state sharing.
   - Use model-agnostic semantic payloads.

3. **Make cognition inspectable**
   - Every claim, belief, conflict and decision should be visible in the UI.

4. **Make decisions auditable**
   - Every decision should include rationale, evidence and policy status.

5. **Keep iterations small**
   - First implement schemas and in-memory state.
   - Add persistence later.
   - Add vector memory later.

6. **Preserve demo stability**
   - The existing fruit ordering flow should continue to work after each iteration.

---

## 6. Proposed Directory Structure

```text
fruitAGNTCY/
  fruit_agents/
    lungo/
      cognition/
        __init__.py

        schemas/
          __init__.py
          intent_contract.py    # iter 1
          claim.py              # iter 1
          sstp_message.py       # iter 1
          evidence.py           # iter 4 (companion of claim)
          belief.py             # iter 8
          conflict.py           # iter 9
          decision.py           # iter 14 (after split-order planner)
          approval.py           # iter 15

        services/
          __init__.py
          intent_manager.py
          claim_mapper.py
          cognition_fabric.py
          belief_builder.py
          conflict_resolver.py
          decision_engine.py
          approval_service.py

        engines/
          __init__.py
          cost_engine.py
          weather_risk_engine.py
          logistics_engine.py
          policy_guardrail_engine.py

        api/
          __init__.py
          routes.py

        observability/
          __init__.py
          cognition_tracing.py
          cognition_metrics.py

        tests/
          test_intent_contract.py
          test_sstp_message.py
          test_claim_mapper.py
          test_conflict_resolver.py
          test_policy_guardrail_engine.py
          test_decision_engine.py
```

Frontend additions:

```text
fruitAGNTCY/
  fruit_agents/
    lungo/
      frontend/
        src/
          types/
            cognition.ts

          components/
            cognition/
              IntentCard.tsx
              ClaimTable.tsx
              ConflictPanel.tsx
              DecisionPanel.tsx
              EngineTracePanel.tsx
              ApprovalPanel.tsx

          pages/
            CognitionPage.tsx

          stores/
            cognitionStore.ts
```

---

## 6.1 Integration Map

The cognition layer is **additive**: it sits alongside the existing lungo agents, not in front of them. This subsection names the concrete files and entry points each iteration touches in the existing codebase, so the wiring is unambiguous before iteration 1 begins.

### Hook points in existing code

| Hook | Existing file | What gets added | First used in |
|---|---|---|---|
| Chat entry point | `lungo/agents/agentic-workflows-api/...` (FastAPI app that receives user prompts) | Call `IntentManager.create_from_prompt()` and propagate `intent_id` into the supervisor invocation context. | iter 2 |
| Auction supervisor | `lungo/agents/supervisors/auction/graph/graph.py` (LangGraph) | Add a "claim mapping" node after the farm-aggregation step. | iter 4 |
| Logistics supervisor | `lungo/agents/supervisors/logistics/graph/graph.py` (LangGraph) | Same: claim mapping node post-aggregation. | iter 4 |
| Outbound A2A messages | App SDK send-points in farms and supervisors | Optional SSTP envelope wrapper, gated by `COGNITION_ENVELOPE_ENABLED`. | iter 3 |
| Read API | `lungo/agents/agentic-workflows-api/api/routes.py` (or sibling) | New `/cognition/...` routes mounted on the same FastAPI app. | iter 6 |
| Frontend | `lungo/frontend/src/` | New `cognition/` page + components, no changes to existing chat. | iter 7 |
| Persistence | Existing lungo Postgres deployment | New `cognition_*` tables in the same database. Migrations live under `cognition/db/migrations/`. | iter 16 |
| Observability | `lungo/common/llm.py` and existing `ioa_observe` integration | Cognition-specific spans + metrics. Note: under OCP we currently set `OTEL_SDK_DISABLED=true` to dodge the ioa_observe NonRecordingSpan crash — re-enabling tracing for cognition spans will require either pinning the SDK to a working version or using a separate exporter. | iter 17 |

### Process layout

The cognition layer runs **in-process inside each supervisor** during iters 1–7. This keeps the demo simple: no new pods, no new service mesh entries. The in-memory fabric (iter 5) lives as a singleton in the `agentic-workflows-api` process and is passed by reference to supervisors.

Once Postgres lands (iter 16), supervisors stop sharing the singleton and each reads/writes via the database. At that point the cognition services *could* be split into their own pod, but the spec intentionally does not require it. Splitting is captured in §13 Future Enhancements.

### Recruiter

The standalone recruiter agent (`fruitAGNTCY/fruit_agents/recruiter`) is **out of scope for cognition** in iters 1–20. Capability discovery is a cognition concern in principle, but folding the recruiter in would add a second supervisor surface that the demo can do without. Revisit after iter 20.

### Per-iteration integration notes

Where the integration is non-obvious, individual iterations include an **Integration** subsection naming the exact file and function being modified.

---

# 7. Iteration Plan

---

## Iteration 1 — Add Core Cognition Schemas

### Goal

Introduce the **minimum** data structures required to start wiring up the cognition layer without changing runtime behaviour.

### Scope

Add Pydantic schemas only for the three types that get used in iters 2–6:

- `IntentContract`
- `Claim`
- `SSTPMessage`

The remaining schemas (`EvidenceRef`, `Belief`, `Conflict`, `Decision`, `ApprovalRequest`) are deliberately deferred so each ships in the iteration that introduces its owning service. This keeps each commit reviewable.

### Files

```text
cognition/schemas/__init__.py
cognition/schemas/intent_contract.py
cognition/schemas/claim.py
cognition/schemas/sstp_message.py
```

### Example: IntentContract

```python
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class IntentStatus(str, Enum):
    DRAFT = "draft"
    GROUNDING = "grounding"
    NEGOTIATING = "negotiating"
    APPROVAL_REQUIRED = "approval_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMMITTED = "committed"
    FAILED = "failed"


class IntentContract(BaseModel):
    intent_id: str = Field(default_factory=lambda: f"fruit-intent-{uuid4()}")
    goal: str

    fruit_type: str | None = None
    quantity_lb: float | None = None
    target_origin: str | None = None
    max_price_usd: float | None = None
    delivery_days: int | None = None

    hard_constraints: dict[str, Any] = Field(default_factory=dict)
    soft_constraints: dict[str, Any] = Field(default_factory=dict)
    human_approval_required_if: list[str] = Field(default_factory=list)

    status: IntentStatus = IntentStatus.DRAFT
```

### Acceptance Criteria

- All schemas can be imported without runtime errors.
- Unit tests can instantiate each schema.
- Existing application behaviour is unchanged.
- No database dependency is introduced.
- No frontend changes are required.

### Commit Suggestion

```text
feat(cognition): add core cognition schemas
```

---

## Iteration 2 — Add Intent Manager

### Goal

Transform user prompts into structured intent contracts.

### Scope

Add `IntentManager` service and integrate it at the start of the supervisor workflow.

### Files

```text
cognition/services/intent_manager.py
```

### Behaviour

When a user sends a request such as:

```text
I need 500 lb of premium mango delivered within 7 days under $1,200.
Prefer low weather risk and low-carbon shipping.
```

The system should create an intent similar to:

```json
{
  "intent_id": "fruit-intent-...",
  "goal": "fulfil_fruit_order",
  "fruit_type": "mango",
  "quantity_lb": 500,
  "max_price_usd": 1200,
  "delivery_days": 7,
  "hard_constraints": {
    "delivery_days": 7,
    "max_price_usd": 1200
  },
  "soft_constraints": {
    "prefer_low_weather_risk": true,
    "prefer_low_carbon_shipping": true
  },
  "human_approval_required_if": [
    "price_above_budget",
    "weather_risk_high",
    "delivery_sla_at_risk"
  ],
  "status": "draft"
}
```

### Implementation Notes

Start with heuristics and regular expressions. Add LLM-based structured extraction later.

### Example

```python
import re

from cognition.schemas.intent_contract import IntentContract


class IntentManager:
    def create_from_prompt(self, prompt: str) -> IntentContract:
        fruit_type = self._extract_fruit_type(prompt)
        quantity_lb = self._extract_quantity_lb(prompt)
        max_price_usd = self._extract_max_price_usd(prompt)
        delivery_days = self._extract_delivery_days(prompt)

        return IntentContract(
            goal="fulfil_fruit_order",
            fruit_type=fruit_type,
            quantity_lb=quantity_lb,
            max_price_usd=max_price_usd,
            delivery_days=delivery_days,
            hard_constraints={
                "delivery_days": delivery_days,
                "max_price_usd": max_price_usd,
            },
            soft_constraints={
                "prefer_low_weather_risk": "weather" in prompt.lower(),
                "prefer_low_carbon_shipping": "carbon" in prompt.lower(),
            },
            human_approval_required_if=[
                "price_above_budget",
                "weather_risk_high",
                "delivery_sla_at_risk",
            ],
        )

    def _extract_fruit_type(self, prompt: str) -> str | None:
        for fruit in ["mango", "apple", "banana", "strawberry"]:
            if fruit in prompt.lower():
                return fruit
        return None

    def _extract_quantity_lb(self, prompt: str) -> float | None:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(lb|lbs|pounds)", prompt.lower())
        return float(match.group(1)) if match else None

    def _extract_max_price_usd(self, prompt: str) -> float | None:
        match = re.search(r"(?:under|max|maximum|budget)\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)", prompt.lower())
        if not match:
            return None
        return float(match.group(1).replace(",", ""))

    def _extract_delivery_days(self, prompt: str) -> int | None:
        match = re.search(r"within\s+(\d+)\s+days?", prompt.lower())
        return int(match.group(1)) if match else None
```

### Integration

- Single hook point: the FastAPI handler in `lungo/agents/agentic-workflows-api/...` that receives user prompts. Add a call to `IntentManager.create_from_prompt(prompt)` immediately after the prompt is parsed and **before** the supervisor is invoked.
- Pass the resulting `intent_id` into the supervisor's invocation context (LangGraph state) so downstream nodes can attach it to outbound messages.
- No changes to the supervisor graphs themselves in this iteration — they only need to *carry* the `intent_id`, not act on it yet.

### Acceptance Criteria

- Every user request gets an `intent_id`.
- The existing workflow receives the `intent_id` as part of execution context.
- The normal chat response still works.
- The API response can optionally include `intent_id`.

### Commit Suggestion

```text
feat(cognition): create intent contract from user prompt
```

---

## Iteration 3 — Add SSTP Message Envelope

### Goal

Wrap agent communications and responses in a semantic envelope.

### Scope

Add `SSTPMessage` and helper functions to create semantic envelopes around agent messages.

### Files

```text
cognition/schemas/sstp_message.py
cognition/services/sstp_factory.py
```

### Example Schema

```python
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


SpeechAct = Literal[
    "request",
    "claim",
    "proposal",
    "counter_proposal",
    "approval_request",
    "decision",
    "rejection",
    "question",
    "evidence",
]


class SSTPMessage(BaseModel):
    sstp_version: str = "0.1"
    message_id: str = Field(default_factory=lambda: f"sstp-{uuid4()}")
    intent_id: str
    sender_agent: str
    receiver_agent: str | None = None
    conversation_phase: str
    speech_act: SpeechAct
    semantic_payload: dict[str, Any]
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

### Example Payload

```json
{
  "sstp_version": "0.1",
  "intent_id": "fruit-intent-123",
  "sender_agent": "colombia-mango-farm",
  "receiver_agent": "fruit-exchange",
  "conversation_phase": "grounding",
  "speech_act": "claim",
  "semantic_payload": {
    "claim_type": "inventory",
    "fruit_type": "mango",
    "available_lb": 320,
    "unit_price_usd": 2.1,
    "quality_score": 0.92,
    "origin": "colombia"
  },
  "evidence_refs": [
    "inventory:colombia-mango-farm:latest"
  ]
}
```

### Acceptance Criteria

- Agent responses can be represented as SSTP messages.
- Existing A2A transport remains unchanged.
- The envelope is optional at first.
- Logs include `intent_id` and `message_id`.

### Commit Suggestion

```text
feat(cognition): add semantic state transfer envelope
```

---

## Iteration 4 — Map Agent Outputs into Claims

### Goal

Convert farm, logistics, weather and payment responses into explicit claims.

### Scope

Add a `ClaimMapper` service. Each agent response can fan out into multiple claims (e.g. one farm response → an `inventory` claim + a `price` claim + a `quality` claim), so the mapper produces N claims per source message.

### Files

```text
cognition/schemas/evidence.py    # EvidenceRef helper, used by Claim
cognition/services/claim_mapper.py
```

### Example Schema

```python
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Claim(BaseModel):
    claim_id: str = Field(default_factory=lambda: f"claim-{uuid4()}")
    intent_id: str
    agent_id: str
    claim_type: str
    subject: str
    value: dict[str, Any]
    confidence: float = 1.0
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

### Claim Types

```text
inventory
price
quality
origin
weather_risk
shipping_capacity
shipping_cost
delivery_sla
payment_status
policy
```

### Example Claim

```json
{
  "claim_id": "claim-...",
  "intent_id": "fruit-intent-123",
  "agent_id": "colombia-mango-farm",
  "claim_type": "inventory",
  "subject": "mango",
  "value": {
    "available_lb": 320,
    "origin": "colombia",
    "fruit_type": "mango"
  },
  "confidence": 0.91,
  "evidence_refs": [
    "inventory:colombia-mango-farm:latest"
  ]
}
```

### Integration

- Add a new LangGraph node `claim_mapping` in both supervisor graphs:
  - `lungo/agents/supervisors/auction/graph/graph.py`
  - `lungo/agents/supervisors/logistics/graph/graph.py`
- Position: **after** the farm/MCP/logistics tool aggregation node, **before** any response synthesis. The node reads the aggregated tool results from graph state, runs them through `ClaimMapper`, and writes the resulting `Claim[]` back into graph state.
- ClaimMapper is per-agent-type pluggable: a farm response → fan out to inventory + price + quality claims; a weather MCP response → one weather_risk claim; a logistics response → shipping_cost + delivery_sla claims.
- Existing supervisor output (the chat response) is unchanged in this iteration. Claims are produced silently; iter 5 stores them, iter 6 exposes them.

### Acceptance Criteria

- Farm outputs produce inventory, price and quality claims.
- Weather MCP outputs produce weather risk claims.
- Logistics outputs produce shipping cost and delivery SLA claims.
- Payment outputs produce payment status claims.
- All claims include `intent_id`.
- Existing output format remains compatible with the current UI.

### Commit Suggestion

```text
feat(cognition): map agent responses to cognitive claims
```

---

## Iteration 5 — Add In-Memory Cognition Fabric

### Goal

Store intents and claims during a single process lifetime.

### Scope

Add a lightweight in-memory cognition fabric before introducing Postgres.

### Files

```text
cognition/services/cognition_fabric.py
```

### Example

```python
from cognition.schemas.claim import Claim
from cognition.schemas.intent_contract import IntentContract


class InMemoryCognitionFabric:
    def __init__(self) -> None:
        self.intents: dict[str, IntentContract] = {}
        self.claims: dict[str, list[Claim]] = {}

    def save_intent(self, intent: IntentContract) -> None:
        self.intents[intent.intent_id] = intent

    def get_intent(self, intent_id: str) -> IntentContract | None:
        return self.intents.get(intent_id)

    def save_claim(self, claim: Claim) -> None:
        self.claims.setdefault(claim.intent_id, []).append(claim)

    def list_claims(self, intent_id: str) -> list[Claim]:
        return self.claims.get(intent_id, [])
```

### Acceptance Criteria

- Intents are saved in memory.
- Claims are saved in memory.
- A request can return the current intent and claims.
- No external service is required.
- Unit tests validate save and retrieval.

### Commit Suggestion

```text
feat(cognition): add in-memory cognition fabric
```

---

## Iteration 6 — Add Read-Only Cognition API

### Goal

Expose cognition state to the frontend.

### Scope

Add API endpoints for reading intent and claims.

### Endpoints

```text
GET /cognition/intent/{intent_id}
GET /cognition/intent/{intent_id}/claims
```

Optional combined endpoint:

```text
GET /cognition/intent/{intent_id}/state
```

### Example Response

```json
{
  "intent": {
    "intent_id": "fruit-intent-123",
    "goal": "fulfil_fruit_order",
    "fruit_type": "mango",
    "quantity_lb": 500,
    "max_price_usd": 1200,
    "delivery_days": 7,
    "status": "grounding"
  },
  "claims": [
    {
      "claim_id": "claim-001",
      "agent_id": "colombia-mango-farm",
      "claim_type": "inventory",
      "subject": "mango",
      "value": {
        "available_lb": 320
      },
      "confidence": 0.91
    }
  ]
}
```

### Acceptance Criteria

- Frontend can fetch cognition state by `intent_id`.
- API returns 404 for unknown intent.
- API does not expose internal stack traces.
- Existing chat endpoints remain unchanged.

### Commit Suggestion

```text
feat(cognition): expose intent and claims API
```

---

## Iteration 7 — Add Frontend Cognition View MVP

### Goal

Add a read-only UI for shared intent and claims.

### Scope

Add a new page or side panel named `Cognition View`.

### Frontend Files

```text
frontend/src/types/cognition.ts
frontend/src/components/cognition/IntentCard.tsx
frontend/src/components/cognition/ClaimTable.tsx
frontend/src/pages/CognitionPage.tsx
frontend/src/stores/cognitionStore.ts
```

### UI Sections

```text
Shared Intent
  - Goal
  - Fruit type
  - Quantity
  - Budget
  - Delivery deadline
  - Hard constraints
  - Soft constraints

Shared Context
  - Agent
  - Claim type
  - Subject
  - Value
  - Confidence
  - Evidence
```

### Acceptance Criteria

- User can see the latest `intent_id`.
- User can inspect intent details.
- User can inspect claims grouped by agent.
- UI handles no-claims state gracefully.
- UI does not block existing chat.

### Commit Suggestion

```text
feat(ui): add cognition view for intents and claims
```

---

## Iteration 8 — Add Belief Builder

### Goal

Aggregate claims into higher-level beliefs.

### Scope

Add a `BeliefBuilder` service.

### Files

```text
cognition/schemas/belief.py
cognition/services/belief_builder.py
```

### Example Schema

```python
from uuid import uuid4

from pydantic import BaseModel, Field


class Belief(BaseModel):
    belief_id: str = Field(default_factory=lambda: f"belief-{uuid4()}")
    intent_id: str
    belief_type: str
    subject: str
    value: dict
    confidence: float
    supporting_claims: list[str]
    contradicted_by: list[str] = Field(default_factory=list)
```

### Example Beliefs

```json
{
  "belief_type": "supply_option",
  "subject": "colombia-mango-farm",
  "value": {
    "fruit_type": "mango",
    "available_lb": 320,
    "unit_price_usd": 2.1,
    "quality_score": 0.92,
    "weather_risk": "medium",
    "delivery_days": 6
  },
  "confidence": 0.86,
  "supporting_claims": [
    "claim-001",
    "claim-002",
    "claim-003"
  ]
}
```

### Acceptance Criteria

- Related claims can be grouped into supply option beliefs.
- Beliefs include supporting claim IDs.
- Beliefs include confidence score.
- API can return beliefs for an intent.

### Commit Suggestion

```text
feat(cognition): build beliefs from claims
```

---

## Iteration 9 — Add Conflict Resolver

### Goal

Detect conflicts between claims, beliefs and constraints.

### Scope

Add `ConflictResolver`.

### Files

```text
cognition/schemas/conflict.py
cognition/services/conflict_resolver.py
```

### Conflict Types

```text
insufficient_inventory
price_above_budget
weather_risk_high
delivery_sla_at_risk
quality_below_threshold
payment_required
contradictory_claims
missing_required_evidence
```

### Example Schema

```python
from uuid import uuid4

from pydantic import BaseModel, Field


class Conflict(BaseModel):
    conflict_id: str = Field(default_factory=lambda: f"conflict-{uuid4()}")
    intent_id: str
    conflict_type: str
    description: str
    involved_claims: list[str]
    severity: str
    suggested_resolution: str | None = None
```

### Example Conflict

```json
{
  "conflict_id": "conflict-001",
  "intent_id": "fruit-intent-123",
  "conflict_type": "insufficient_inventory",
  "description": "Colombia Mango Farm has 320 lb available, but the intent requires 500 lb.",
  "involved_claims": [
    "claim-001"
  ],
  "severity": "medium",
  "suggested_resolution": "Split the order across multiple farms."
}
```

### Acceptance Criteria

- Resolver detects inventory shortage.
- Resolver detects budget violations.
- Resolver detects high weather risk.
- Resolver detects delivery SLA risk.
- Conflicts are visible through API.
- Conflicts are visible in the UI.
- Resolver only **records** conflicts — it must not remove options from consideration. Enforcement is the guardrail's job (see §4.8 and iter 12).

### Commit Suggestion

```text
feat(cognition): detect conflicts across claims and constraints
```

---

## Iteration 10 — Add Cost Engine

### Goal

Evaluate candidate supply options against price and budget constraints.

### Scope

Add `CostEngine`.

### Files

```text
cognition/engines/cost_engine.py
```

### Inputs

- Intent
- Claims
- Beliefs

### Outputs

- Candidate options
- Total cost
- Budget status
- Margin if applicable
- Ranking metadata

### Example Output

```json
{
  "engine": "cost_engine",
  "intent_id": "fruit-intent-123",
  "options": [
    {
      "supplier": "colombia-mango-farm",
      "quantity_lb": 320,
      "unit_price_usd": 2.1,
      "total_price_usd": 672,
      "within_budget": true
    }
  ]
}
```

### Acceptance Criteria

- Engine evaluates price claims.
- Engine calculates total price.
- Engine marks options as within or outside budget.
- Engine output can be stored as evidence or engine trace.

### Commit Suggestion

```text
feat(cognition): add cost evaluation engine
```

---

## Iteration 11 — Add Weather Risk Engine

### Goal

Evaluate weather-related risk for supply options.

### Scope

Add `WeatherRiskEngine`.

### Files

```text
cognition/engines/weather_risk_engine.py
```

### Risk Levels

```text
low
medium
high
unknown
```

### Example Output

```json
{
  "engine": "weather_risk_engine",
  "intent_id": "fruit-intent-123",
  "risks": [
    {
      "supplier": "colombia-mango-farm",
      "origin": "colombia",
      "risk": "medium",
      "reason": "Rain probability is 48% during the delivery window."
    }
  ]
}
```

### Acceptance Criteria

- Engine consumes weather claims.
- Engine calculates risk level.
- Engine can explain why risk was assigned.
- High risk can trigger human approval or conflict.

### Commit Suggestion

```text
feat(cognition): add weather risk engine
```

---

## Iteration 12 — Add Policy Guardrail Engine

### Goal

Evaluate options against hard constraints and human approval rules.

### Scope

Add `PolicyGuardrailEngine`.

### Files

```text
cognition/engines/policy_guardrail_engine.py
```

### Policies

Initial policies:

```text
price_above_budget
weather_risk_high
delivery_sla_at_risk
quality_below_threshold
missing_payment_authorization
```

### Example Output

```json
{
  "engine": "policy_guardrail_engine",
  "intent_id": "fruit-intent-123",
  "allowed": false,
  "violations": [
    "weather_risk_high"
  ],
  "requires_human_approval": true,
  "rationale": "Selected option has high weather risk."
}
```

### Acceptance Criteria

- Engine checks hard constraints.
- Engine checks human approval triggers.
- Engine can block autonomous decision (overlap with Resolver is intentional — see §4.8: Resolver flags, Guardrail enforces).
- Engine emits a per-option `allowed`/`requires_human_approval` verdict; the DecisionEngine only picks from `allowed: true` options.
- Engine explains violations.

### Commit Suggestion

```text
feat(cognition): add policy guardrail engine
```

---

## Iteration 13 — Add Split-Order Planner

### Goal

Compose multi-supplier candidate plans for cases where no single supplier satisfies all constraints. The planner produces candidate plans (single-supplier or split-order); the DecisionEngine in iter 14 picks among them.

### Scope

Add a planner that emits both single-supplier and split-order candidate plans. The DecisionEngine consumes these as its option set.

### Files

```text
cognition/services/split_order_planner.py
```

### Example

```json
{
  "plan_type": "split_order",
  "suppliers": [
    {
      "supplier": "colombia-mango-farm",
      "quantity_lb": 320,
      "unit_price_usd": 2.1
    },
    {
      "supplier": "brazil-mango-farm",
      "quantity_lb": 180,
      "unit_price_usd": 2.4
    }
  ],
  "total_quantity_lb": 500,
  "total_price_usd": 1104,
  "max_delivery_days": 6,
  "aggregate_weather_risk": "medium"
}
```

### Acceptance Criteria

- Planner emits at least one single-supplier candidate per supplier with sufficient inventory.
- Planner emits split-order candidates when no single supplier covers the requested quantity.
- Each plan satisfies the quantity requirement (or is marked infeasible).
- Each plan calculates total price.
- Each plan aggregates weather risk across suppliers (worst-case wins).
- Planner output is consumable by the guardrail and decision engines (iter 12 and iter 14).

### Commit Suggestion

```text
feat(cognition): add split-order planning
```

---

## Iteration 14 — Add Decision Engine

### Goal

Select a recommended option based on beliefs, conflicts and engine outputs. The candidate set comes from the SplitOrderPlanner (iter 13), filtered by the PolicyGuardrailEngine (iter 12).

### Scope

Add `DecisionEngine`.

### Files

```text
cognition/schemas/decision.py
cognition/services/decision_engine.py
```

### Decision Strategy

Initial decision ranking:

1. Satisfy all hard constraints.
2. Avoid high weather risk.
3. Stay within budget.
4. Maximise quality score.
5. Minimise delivery time.
6. Prefer lower carbon shipping if available.
7. Prefer single supplier unless split order improves feasibility.

### Example Decision

```json
{
  "decision_id": "decision-001",
  "intent_id": "fruit-intent-123",
  "decision_type": "recommended_supply_plan",
  "selected_option": {
    "plan_type": "split_order",
    "suppliers": [
      {
        "supplier": "colombia-mango-farm",
        "quantity_lb": 320
      },
      {
        "supplier": "brazil-mango-farm",
        "quantity_lb": 180
      }
    ],
    "total_price_usd": 1128,
    "delivery_days": 6,
    "weather_risk": "medium"
  },
  "rationale": "The split order satisfies quantity, delivery and budget constraints while avoiding high weather risk.",
  "confidence": 0.84,
  "requires_human_approval": false
}
```

### Acceptance Criteria

- Engine produces one recommended decision.
- Engine selects only from planner outputs that the guardrail (iter 12) marked `allowed`.
- Decision includes rationale.
- Decision references supporting beliefs and claims.
- Decision states whether human approval is required.
- UI can display decision.

### Commit Suggestion

```text
feat(cognition): recommend decisions from shared context
```

---

## Iteration 15 — Add Human Approval Flow

### Goal

Allow humans to approve, reject or request alternative decisions.

### Scope

Add approval schema, service, API endpoints and UI panel.

### Files

```text
cognition/schemas/approval.py
cognition/services/approval_service.py
frontend/src/components/cognition/ApprovalPanel.tsx
```

### API Endpoints

```text
POST /cognition/intent/{intent_id}/approve
POST /cognition/intent/{intent_id}/reject
POST /cognition/intent/{intent_id}/request-alternative
```

### Approval Request Example

```json
{
  "intent_id": "fruit-intent-123",
  "decision_id": "decision-001",
  "approval_reason": "weather_risk_high",
  "summary": "The recommended option violates the preferred weather risk threshold.",
  "options": [
    "approve_anyway",
    "reject",
    "request_lower_risk_option",
    "request_cheaper_option"
  ]
}
```

### Integration

- The existing chat flow is synchronous: prompt in, response out, no human-in-the-loop pause. Approval breaks that pattern, so this iteration introduces a **pause/resume** mechanism:
  - When the DecisionEngine returns `requires_human_approval: true`, the supervisor's terminal node writes the decision into the cognition fabric with status `APPROVAL_REQUIRED` and **returns immediately** to the user with a "pending approval" payload (containing the `intent_id` and the proposed decision).
  - The frontend's `CognitionPage` polls (or subscribes to) `GET /cognition/intent/{intent_id}/state` until status changes.
  - When the human posts to one of the new endpoints (`/approve`, `/reject`, `/request-alternative`), the API updates the intent status. A separate "commit" path (out of scope for this iteration) is what eventually triggers the order/payment.
- Demo-grade: **no auth on these endpoints**. Approval is open to anyone who can reach the API. Production hardening (RBAC, signed approvals) is captured in §13 Future Enhancements.
- No LangGraph interruption/resumption is required — the supervisor simply ends its run early. Persisting state across the pause is what iter 16 (Postgres) is for; until then the in-memory fabric must outlive the request, which means it has to be a process-level singleton (already true from iter 5).

### Acceptance Criteria

- Decisions requiring approval do not auto-commit.
- UI displays approval reason.
- User can approve or reject.
- Approval/rejection is recorded.
- Final response reflects approval status.
- Endpoints are unauthenticated (demo-grade); this is documented, not a bug.

### Commit Suggestion

```text
feat(cognition): add human approval workflow
```

---

## Iteration 16 — Add Postgres Cognition Fabric

### Goal

Persist cognition state beyond process lifetime.

### Scope

Replace or complement the in-memory fabric with Postgres.

### Tables

```sql
CREATE TABLE IF NOT EXISTS cognition_intents (
    intent_id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cognition_claims (
    claim_id TEXT PRIMARY KEY,
    intent_id TEXT NOT NULL REFERENCES cognition_intents(intent_id),
    agent_id TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    value JSONB NOT NULL,
    confidence DOUBLE PRECISION DEFAULT 1.0,
    evidence_refs JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cognition_beliefs (
    belief_id TEXT PRIMARY KEY,
    intent_id TEXT NOT NULL REFERENCES cognition_intents(intent_id),
    belief_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    value JSONB NOT NULL,
    confidence DOUBLE PRECISION DEFAULT 1.0,
    supporting_claims JSONB DEFAULT '[]',
    contradicted_by JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cognition_conflicts (
    conflict_id TEXT PRIMARY KEY,
    intent_id TEXT NOT NULL REFERENCES cognition_intents(intent_id),
    conflict_type TEXT NOT NULL,
    description TEXT NOT NULL,
    involved_claims JSONB NOT NULL,
    severity TEXT NOT NULL,
    suggested_resolution TEXT,
    resolution_status TEXT DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cognition_decisions (
    decision_id TEXT PRIMARY KEY,
    intent_id TEXT NOT NULL REFERENCES cognition_intents(intent_id),
    decision_type TEXT NOT NULL,
    selected_option JSONB NOT NULL,
    rationale TEXT NOT NULL,
    confidence DOUBLE PRECISION DEFAULT 1.0,
    requires_human_approval BOOLEAN DEFAULT false,
    approved_by_human BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### Acceptance Criteria

- Cognition state survives process restart.
- Existing in-memory implementation can still be used for tests.
- API reads from Postgres when enabled.
- Database migrations are repeatable.

### Commit Suggestion

```text
feat(cognition): persist cognition state in postgres
```

---

## Iteration 17 — Add Cognitive Observability

### Goal

Instrument cognition-specific spans and metrics.

### Scope

Add tracing and metric helpers.

### Files

```text
cognition/observability/cognition_tracing.py
cognition/observability/cognition_metrics.py
```

### Spans

```text
cognition.intent.created
cognition.claim.received
cognition.belief.created
cognition.conflict.detected
cognition.conflict.resolved
cognition.engine.cost.evaluated
cognition.engine.weather.evaluated
cognition.engine.policy.evaluated
cognition.decision.created
cognition.human.approval_requested
cognition.human.approved
cognition.human.rejected
```

### Metrics

```text
SharedIntentCompleteness
ClaimCoverage
ConflictResolutionRate
DecisionExplainabilityScore
HumanApprovalRate
PolicyViolationRate
CognitionFabricWrites
BeliefRevisionCount
```

### Acceptance Criteria

- Each intent has a traceable cognition lifecycle.
- Spans include `intent_id`.
- Engine evaluations are visible in traces.
- Approval flow is visible in traces.
- Existing observability remains unchanged.

### Commit Suggestion

```text
feat(observability): add cognition lifecycle tracing
```

---

## Iteration 18 — Add Historical Memory

### Goal

Enable the system to remember prior decisions and outcomes.

### Scope

Add memory storage and retrieval.

### Storage Options

MVP:

```text
Postgres table: cognition_memories
```

Later:

```text
pgvector or Qdrant for semantic retrieval
```

### Table

```sql
CREATE TABLE IF NOT EXISTS cognition_memories (
    memory_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    memory_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    confidence DOUBLE PRECISION DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### Example Memory

```json
{
  "memory_type": "supplier_performance",
  "subject": "colombia-mango-farm",
  "payload": {
    "historical_weather_delays": 2,
    "average_quality_score": 0.91,
    "delivery_reliability": 0.82
  },
  "confidence": 0.79
}
```

### Acceptance Criteria

- Previous supplier outcomes can be stored.
- Decision engine can read relevant memories.
- Historical risk can influence future recommendations.
- UI can show memory-based rationale.

### Commit Suggestion

```text
feat(cognition): add historical memory for supplier decisions
```

---

## Iteration 19 — Add Belief Revision

### Goal

Update confidence based on new evidence and past outcomes.

### Scope

Add basic belief revision logic.

### Rules

Examples:

```text
If a supplier repeatedly misses delivery windows, reduce delivery confidence.
If weather risk predictions were accurate, increase weather evidence confidence.
If payment failures recur, increase payment risk.
If quality score remains stable, increase quality confidence.
```

### Acceptance Criteria

- Beliefs can be updated after outcome feedback.
- Confidence can increase or decrease.
- Revision history is preserved.
- UI can display belief revision events.

### Commit Suggestion

```text
feat(cognition): add belief revision from outcomes
```

---

## Iteration 20 — Add Demo Script and Scenario Fixtures

### Goal

Make the cognition demo repeatable.

### Scope

Add sample prompts, deterministic farm data and expected outcomes.

### Files

```text
demo/
  scenarios/
    mango_budget_weather.json
    banana_inventory_shortage.json
    strawberry_high_quality_high_cost.json
    apple_low_risk_low_margin.json

  scripts/
    run_cognition_demo.sh
```

### Example Prompt

```text
I need 500 lb of premium mango delivered within 7 days.
Keep total cost under $1,200.
Prefer low weather risk and low-carbon shipping.
If the best option breaks any constraint, ask me before committing.
```

### Expected Demo Output

```text
Shared Intent:
  500 lb premium mango, 7 days, max $1,200

Claims:
  Colombia: 320 lb, high quality, medium weather risk
  Brazil: 250 lb, medium-high quality, low weather risk
  Vietnam: 700 lb, low cost, delivery SLA risk

Conflict:
  No single supplier satisfies all constraints.

Decision:
  Split order between Colombia and Brazil.

Human approval:
  Not required.
```

### Acceptance Criteria

- Demo can be run consistently.
- Scenario data is deterministic.
- Output demonstrates shared intent, shared context, conflict and decision.
- Demo can be presented without relying on external unpredictable APIs.

### Commit Suggestion

```text
feat(demo): add repeatable internet of cognition scenarios
```

---

# 8. Final Target Demo Flow

## User Prompt

```text
I need 500 lb of premium mango delivered within 7 days.
Keep total cost under $1,200.
Prefer low weather risk and low-carbon shipping.
If the best option breaks any constraint, ask me before committing.
```

## System Behaviour

```text
1. Intent Manager creates shared intent.
2. Supervisor discovers and invokes relevant fruit agents.
3. Farms return inventory, price and quality.
4. Weather MCP returns weather risk.
5. Logistics returns delivery and shipping cost.
6. Claim Mapper creates cognitive claims.
7. Cognition Fabric stores claims.
8. Belief Builder creates supplier beliefs.
9. Conflict Resolver detects that no single supplier satisfies all constraints.
10. Cost Engine and Weather Risk Engine evaluate options.
11. Decision Engine proposes a split-order plan.
12. Policy Guardrail Engine checks whether approval is required.
13. UI displays intent, claims, conflicts, engine outputs and decision.
14. Human approves if required.
15. Order/payment workflow continues.
```

---

# 9. Example End-to-End Cognitive State

```json
{
  "intent": {
    "intent_id": "fruit-intent-123",
    "goal": "fulfil_fruit_order",
    "fruit_type": "mango",
    "quantity_lb": 500,
    "max_price_usd": 1200,
    "delivery_days": 7,
    "soft_constraints": {
      "prefer_low_weather_risk": true,
      "prefer_low_carbon_shipping": true
    }
  },
  "claims": [
    {
      "agent_id": "colombia-mango-farm",
      "claim_type": "inventory",
      "subject": "mango",
      "value": {
        "available_lb": 320
      },
      "confidence": 0.91
    },
    {
      "agent_id": "colombia-mango-farm",
      "claim_type": "price",
      "subject": "mango",
      "value": {
        "unit_price_usd": 2.1
      },
      "confidence": 0.94
    },
    {
      "agent_id": "weather-mcp",
      "claim_type": "weather_risk",
      "subject": "colombia",
      "value": {
        "risk": "medium",
        "rain_probability": 0.48
      },
      "confidence": 0.78
    }
  ],
  "beliefs": [
    {
      "belief_type": "supply_option",
      "subject": "colombia-mango-farm",
      "value": {
        "available_lb": 320,
        "unit_price_usd": 2.1,
        "weather_risk": "medium",
        "quality_score": 0.92,
        "delivery_days": 6
      },
      "confidence": 0.86
    }
  ],
  "conflicts": [
    {
      "conflict_type": "insufficient_inventory",
      "description": "Colombia Mango Farm has 320 lb available, but the intent requires 500 lb.",
      "severity": "medium",
      "suggested_resolution": "Split the order across multiple farms."
    }
  ],
  "decision": {
    "decision_type": "recommended_supply_plan",
    "selected_option": {
      "plan_type": "split_order",
      "suppliers": [
        {
          "supplier": "colombia-mango-farm",
          "quantity_lb": 320
        },
        {
          "supplier": "brazil-mango-farm",
          "quantity_lb": 180
        }
      ],
      "total_price_usd": 1128,
      "delivery_days": 6,
      "weather_risk": "medium"
    },
    "rationale": "The split order satisfies quantity, delivery and budget constraints while avoiding high weather risk.",
    "confidence": 0.84,
    "requires_human_approval": false
  }
}
```

---

# 10. Definition of Done

The Internet of Cognition evolution is considered complete when the demo can show:

- A user request transformed into a shared intent.
- Multiple agents contributing claims.
- Claims persisted in a cognition fabric.
- Beliefs generated from claims.
- Conflicts detected and explained.
- Engines evaluating cost, weather, logistics and policy.
- A final decision with rationale and evidence.
- Human approval when required.
- Cognitive state visible in the UI.
- Cognitive lifecycle visible in observability.
- Historical memory influencing future decisions.

---

# 11. Recommended Commit Sequence

```text
feat(cognition): add core cognition schemas
feat(cognition): create intent contract from user prompt
feat(cognition): add semantic state transfer envelope
feat(cognition): map agent responses to cognitive claims
feat(cognition): add in-memory cognition fabric
feat(cognition): expose intent and claims API
feat(ui): add cognition view for intents and claims
feat(cognition): build beliefs from claims
feat(cognition): detect conflicts across claims and constraints
feat(cognition): add cost evaluation engine
feat(cognition): add weather risk engine
feat(cognition): add policy guardrail engine
feat(cognition): add split-order planning
feat(cognition): recommend decisions from shared context
feat(cognition): add human approval workflow
feat(cognition): persist cognition state in postgres
feat(observability): add cognition lifecycle tracing
feat(cognition): add historical memory for supplier decisions
feat(cognition): add belief revision from outcomes
feat(demo): add repeatable internet of cognition scenarios
```

---

# 12. Non-Goals for the First Version

The first version should not attempt to implement:

- Latent State Transfer Protocol
- Direct model activation sharing
- Model-specific tensor state exchange
- Full distributed knowledge graph
- Formal theorem proving
- Complex multi-party negotiation protocols
- Production-grade policy-as-code
- Production-grade supply-chain optimisation
- Enterprise identity federation beyond the existing demo scope

These may be considered later after the SSTP-style semantic cognition flow is working.

---

# 13. Future Enhancements

Potential future improvements:

```text
CSTP-style compressed state
  Summaries, embeddings and semantic compression of dialogue state.

Vector cognition memory
  Qdrant or pgvector retrieval for prior decisions and supplier outcomes.

Policy-as-code
  OPA/Rego or Cedar-based guardrail policies.

Graph cognition fabric
  Neo4j, Memgraph or RDF-based knowledge graph.

Multi-objective optimiser
  Optimise cost, quality, weather risk, delivery SLA and emissions.

Network-change version
  Adapt the same cognition model to Cisco/telco infrastructure change workflows.

Cognition replay
  Replay decision traces step by step for demo and audit.

Counterfactual mode
  “What would change if budget increased by 10%?”
  “What would change if weather risk became high?”
```

---

# 14. Suggested Presentation Narrative

The demo should be explained as follows:

```text
Traditional agentic systems connect agents.

fruitCognition shows the next step:
agents do not only exchange messages;
they build shared intent, shared context and shared decisions.

The system can explain:
- what the user wanted,
- what each agent claimed,
- which claims conflicted,
- which policies were triggered,
- which decision was selected,
- why the decision was selected,
- whether a human had to approve it.
```

This is the practical bridge from Internet of Agents to Internet of Cognition.
