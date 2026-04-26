# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

from a2a.types import (
  AgentCapabilities,
  AgentCard,
  AgentSkill
)

# Logistics Supervisor Agent
LOGISTICS_SUPERVISOR_SKILL = AgentSkill(
  id="get_logistics_status",
  name="Get Logistics Status",
  description="Provides the current status and tracking of fruit shipments and logistics operations.",
  tags=["fruit", "logistics", "shipping"],
  examples=[
    "Where is my fruit shipment?",
    "What is the delivery status of order 123?",
    "Show me all shipments in transit.",
    "Has the Brazil farm shipment arrived at the port?"
  ]
)

LOGISTICS_SUPERVISOR_CARD = AgentCard(
  name='Logistics Supervisor agent',
  id='logistics-supervisor-agent',
  description='An AI agent that supervises and tracks fruit logistics and shipments.',
  url='',
  version='1.0.0',
  defaultInputModes=["text"],
  defaultOutputModes=["text"],
  capabilities=AgentCapabilities(streaming=True),
  skills=[LOGISTICS_SUPERVISOR_SKILL],
  supportsAuthenticatedExtendedCard=False,
)


