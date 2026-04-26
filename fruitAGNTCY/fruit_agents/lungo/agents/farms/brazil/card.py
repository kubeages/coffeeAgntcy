# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import os
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill
)
from config.config import SLIM_SERVER, NATS_SERVER

PORT = os.getenv("FARM_AGENT_PORT", "9999")
AGENT_ID = "brazil_mango_farm"

AGENT_SKILL = AgentSkill(
    id="get_yield",
    name="Get Mango Yield",
    description="Returns the mango farm's yield in lb.",
    tags=["mango", "farm"],
    examples=[
        "What is the yield of the Brazil mango farm?",
        "How much mango does the Brazil farm produce?",
        "What is the yield of the Brazil mango farm in pounds?",
        "How many pounds of mango does the Brazil farm produce?",
    ]
)

AGENT_CARD = AgentCard(
    name='Brazil Mango Farm',
    description='An AI agent that returns the yield of mangoes in pounds for the Brazil farm.',
    version='1.0.0',
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[AGENT_SKILL],
    supportsAuthenticatedExtendedCard=False,
    preferred_transport="slimrpc",
    url=f"slim://{SLIM_SERVER}/lungo/agents/{AGENT_ID}",
    additional_interfaces=[
        # point-to-point transport for direct client-agent communication
        AgentInterface(transport="slimrpc", url=f"slim://{SLIM_SERVER}/lungo/agents/{AGENT_ID}"),
        # slim-based group comm and pub/sub transport
        AgentInterface(transport="slim", url=f"slim://{SLIM_SERVER}/lungo/agents/{AGENT_ID}"),
        # nats-based pub/sub transport for broadcasting to multiple subscriber
        AgentInterface(transport="nats", url=f"nats://{NATS_SERVER}/lungo/agents/{AGENT_ID}"),
        # jsonrpc endpoint for direct client-agent communication over http
        AgentInterface(transport="jsonrpc", url=f"http://0.0.0.0:{PORT}"),
    ],
)
