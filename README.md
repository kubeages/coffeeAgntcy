# fruitCognition

A multi-agent reference application built on the AGNTCY Internet of Agents stack
(SLIM, NATS, A2A, MCP, LangGraph, Observe SDK), demonstrating how distributed
agents can collaborate inside a fruit-trading business: per-country fruit farms
(Mango / Apple / Banana / Strawberry), an auction supervisor, a logistics group
(shipper, accountant, helpdesk), an MCP weather tool, an MCP payment tool, and
a recruiter that discovers agents through the AGNTCY directory.

## Layout

| Path | What lives there |
|---|---|
| [`fruitAGNTCY/fruit_agents/lungo`](fruitAGNTCY/fruit_agents/lungo) | Full demo: 3 farms + auction supervisor + group-comm logistics + recruiter + UI. |
| [`fruitAGNTCY/fruit_agents/recruiter`](fruitAGNTCY/fruit_agents/recruiter) | Standalone recruiter agent backed by a Google ADK agent + AGNTCY `dirctl` tool. |
| `.github/workflows` | CI: per-service container builds → `ghcr.io/kubeages/fruit-agntcy/*`. |

## Quick links

- Container images: `ghcr.io/kubeages/fruit-agntcy/<service>:<tag>` (public).
- License: [Apache-2.0](LICENSE).
- Built with: [AGNTCY App SDK](https://github.com/agntcy/app-sdk),
  [SLIM](https://github.com/agntcy/slim),
  [LangGraph](https://github.com/langchain-ai/langgraph),
  [A2A](https://github.com/a2aproject/a2a-python),
  [MCP](https://github.com/modelcontextprotocol/python-sdk).
