/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 **/

import { TiWeatherCloudy } from "react-icons/ti"
import { Truck, Calculator } from "lucide-react"
import { Node, Edge } from "@xyflow/react"
import supervisorIcon from "@/assets/supervisor.png"
import farmAgentIcon from "@/assets/Grader-Agent.png"
import {
  FarmName,
  NODE_IDS,
  EDGE_IDS,
  NODE_TYPES,
  EDGE_TYPES,
  EDGE_LABELS,
  HANDLE_TYPES,
  VERIFICATION_STATUS,
} from "./const"
import urlsConfig from "./urls.json"

export interface GraphConfig {
  title: string
  nodes: Node[]
  edges: Edge[]
  animationSequence: { ids: string[] }[]
}

const FruitFarmIcon = (
  <img
    src={farmAgentIcon}
    alt="Fruit Farm Agent Icon"
    className="dark-icon h-4 w-4 object-contain opacity-100"
  />
)

export const PUBLISH_SUBSCRIBE_CONFIG: GraphConfig = {
  title: "Publish Subscribe Fruit Network",
  nodes: [
    {
      id: NODE_IDS.AUCTION_AGENT,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: (
          <img
            src={supervisorIcon}
            alt="Supervisor Icon"
            className="dark-icon h-4 w-4 object-contain"
          />
        ),
        label1: "Auction Agent",
        label2: "Buyer",
        description:
          "Supervisor for the fruit auction. Receives the buyer's request, " +
          "calls each farm's inventory agent in parallel, picks the best " +
          "supply option(s), and confirms the order. Backed by the " +
          "auction-supervisor service running LangGraph.",
        handles: HANDLE_TYPES.SOURCE,
        verificationStatus: VERIFICATION_STATUS.VERIFIED,
        hasBadgeDetails: true,
        hasPolicyDetails: true,
        githubLink: `${urlsConfig.github.baseUrl}${urlsConfig.github.agents.supervisorAuction}`,
        agentDirectoryLink: `${urlsConfig.agentDirectory.baseUrl}${urlsConfig.agentDirectory.agents.supervisorAuction}`,
      },
      position: { x: 527.1332569384248, y: 76.4805787605829 },
    },
    {
      id: NODE_IDS.TRANSPORT,
      type: NODE_TYPES.TRANSPORT,
      data: {
        label: "Transport: ",
        description:
          "The transport layer that carries A2A messages between " +
          "agents. For the publish/subscribe pattern this is typically " +
          "NATS; the agentless edge labels resolve to the actual " +
          "protocol at runtime.",
        githubLink: `${urlsConfig.github.appSdkBaseUrl}${urlsConfig.github.transports.general}`,
      },
      position: { x: 229.02370449534635, y: 284.688426426175 },
    },
    {
      id: NODE_IDS.BRAZIL_FARM,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: FruitFarmIcon,
        label1: "Brazil",
        label2: "Mango Grove",
        description:
          "Brazilian mango farm agent. Reports current inventory, unit " +
          "price, quality and origin when the auction queries it. Intended " +
          "to demonstrate a supplier whose identity verification has not " +
          "completed yet (the auction can still talk to it but the " +
          "guardrail flags it).",
        handles: HANDLE_TYPES.TARGET,
        farmName: FarmName?.BrazilMangoFarm || "Brazil Mango Grove",
        verificationStatus: VERIFICATION_STATUS.FAILED,
        githubLink: `${urlsConfig.github.baseUrl}${urlsConfig.github.agents.brazilFarm}`,
        agentDirectoryLink: `${urlsConfig.agentDirectory.baseUrl}${urlsConfig.agentDirectory.agents.brazilFarm}`,
      },
      position: { x: 232.0903941835277, y: 503.93174725714437 },
    },
    {
      id: NODE_IDS.COLOMBIA_FARM,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: FruitFarmIcon,
        label1: "Colombia",
        label2: "Apple Orchard",
        description:
          "Colombian apple orchard agent. Reports inventory, price and " +
          "quality. Carries a verified AGNTCY identity badge with policies " +
          "attached, so the cognition layer trusts its claims and the " +
          "guardrail engine treats it as an allowed supplier.",
        handles: HANDLE_TYPES.ALL,
        farmName: FarmName?.ColombiaAppleFarm || "Colombia Apple Orchard",
        verificationStatus: VERIFICATION_STATUS.VERIFIED,
        hasBadgeDetails: true,
        hasPolicyDetails: true,
        githubLink: `${urlsConfig.github.baseUrl}${urlsConfig.github.agents.colombiaFarm}`,
        agentDirectoryLink: `${urlsConfig.agentDirectory.baseUrl}${urlsConfig.agentDirectory.agents.colombiaFarm}`,
      },
      position: { x: 521.266082170288, y: 505.38817113883306 },
    },
    {
      id: NODE_IDS.VIETNAM_FARM,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: FruitFarmIcon,
        label1: "Vietnam",
        label2: "Banana Plantation",
        description:
          "Vietnamese banana plantation agent. Reports inventory, price " +
          "and quality on demand. Verified identity but no extra " +
          "policies attached, so the guardrail uses default thresholds " +
          "for budget and quality.",
        handles: HANDLE_TYPES.TARGET,
        farmName: FarmName?.VietnamBananaFarm || "Vietnam Banana Plantation",
        verificationStatus: VERIFICATION_STATUS.VERIFIED,
        hasBadgeDetails: true,
        hasPolicyDetails: false,
        githubLink: `${urlsConfig.github.baseUrl}${urlsConfig.github.agents.vietnamFarm}`,
        agentDirectoryLink: `${urlsConfig.agentDirectory.baseUrl}${urlsConfig.agentDirectory.agents.vietnamFarm}`,
      },
      position: { x: 832.9824511707582, y: 505.08339631990395 },
    },
    {
      id: NODE_IDS.WEATHER_MCP,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: <TiWeatherCloudy className="dark-icon h-4 w-4" />,
        label1: "MCP Server",
        label2: "Weather",
        description:
          "MCP server that exposes weather forecasts per region. The " +
          "cognition layer consumes its responses as weather_risk claims, " +
          "which the WeatherRiskEngine then maps into low / medium / " +
          "high risk levels per supplier origin.",
        handles: HANDLE_TYPES.TARGET,
        githubLink: `${urlsConfig.github.baseUrl}${urlsConfig.github.agents.weatherMcp}`,
        agentDirectoryLink: `${urlsConfig.agentDirectory.baseUrl}${urlsConfig.agentDirectory.agents.weatherMcp}`,
      },
      position: { x: 371.266082170288, y: 731.9104402412228 },
    },
    {
      id: NODE_IDS.PAYMENT_MCP,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: <Calculator className="dark-icon h-4 w-4" />,
        label1: "MCP Server",
        label2: "Payment",
        description:
          "MCP server that authorises and confirms payments for orders " +
          "the auction commits to. Emits payment_status claims back into " +
          "the cognition fabric (status, amount, order_id) so the inbox " +
          "can show whether an approved order has actually settled.",
        handles: HANDLE_TYPES.TARGET,
        verificationStatus: VERIFICATION_STATUS.VERIFIED,
        hasBadgeDetails: true,
        hasPolicyDetails: false,
        githubLink: `${urlsConfig.github.baseUrl}${urlsConfig.github.agents.paymentMcp}`,
        agentDirectoryLink: urlsConfig.agentDirectory.baseUrl,
      },
      position: { x: 671.266082170288, y: 731.9104402412228 },
    },
  ],
  edges: [
    {
      id: EDGE_IDS.AUCTION_TO_TRANSPORT,
      source: NODE_IDS.AUCTION_AGENT,
      target: NODE_IDS.TRANSPORT,
      targetHandle: "top",
      data: { label: EDGE_LABELS.A2A },
      type: EDGE_TYPES.CUSTOM,
    },
    {
      id: EDGE_IDS.TRANSPORT_TO_BRAZIL,
      source: NODE_IDS.TRANSPORT,
      target: NODE_IDS.BRAZIL_FARM,
      sourceHandle: "bottom_left",
      data: { label: EDGE_LABELS.A2A },
      type: EDGE_TYPES.CUSTOM,
    },
    {
      id: EDGE_IDS.TRANSPORT_TO_COLOMBIA,
      source: NODE_IDS.TRANSPORT,
      target: NODE_IDS.COLOMBIA_FARM,
      sourceHandle: "bottom_center",
      data: { label: EDGE_LABELS.A2A },
      type: EDGE_TYPES.CUSTOM,
    },
    {
      id: EDGE_IDS.TRANSPORT_TO_VIETNAM,
      source: NODE_IDS.TRANSPORT,
      target: NODE_IDS.VIETNAM_FARM,
      sourceHandle: "bottom_right",
      data: { label: EDGE_LABELS.A2A },
      type: EDGE_TYPES.CUSTOM,
    },
    {
      id: EDGE_IDS.COLOMBIA_TO_MCP,
      source: NODE_IDS.COLOMBIA_FARM,
      target: NODE_IDS.WEATHER_MCP,
      data: {
        label: EDGE_LABELS.MCP,
        branches: [NODE_IDS.WEATHER_MCP, NODE_IDS.PAYMENT_MCP],
      },
      type: EDGE_TYPES.BRANCHING,
    },
  ],
  animationSequence: [
    { ids: [NODE_IDS.AUCTION_AGENT] },
    { ids: [EDGE_IDS.AUCTION_TO_TRANSPORT] },
    { ids: [NODE_IDS.TRANSPORT] },
    {
      ids: [
        EDGE_IDS.TRANSPORT_TO_BRAZIL,
        EDGE_IDS.TRANSPORT_TO_COLOMBIA,
        EDGE_IDS.TRANSPORT_TO_VIETNAM,
      ],
    },
    {
      ids: [
        NODE_IDS.BRAZIL_FARM,
        NODE_IDS.COLOMBIA_FARM,
        NODE_IDS.VIETNAM_FARM,
      ],
    },
    { ids: [EDGE_IDS.COLOMBIA_TO_MCP] },
    { ids: [NODE_IDS.WEATHER_MCP, NODE_IDS.PAYMENT_MCP] },
  ],
}

export const GROUP_COMMUNICATION_CONFIG: GraphConfig = {
  title: "Secure Group Communication Logistics Network",
  nodes: [
    {
      id: NODE_IDS.LOGISTICS_GROUP,
      type: NODE_TYPES.GROUP,
      data: { label: "Logistics Group" },
      position: { x: 50, y: 50 },
      style: {
        width: 900,
        height: 650,
        backgroundColor: "var(--group-background)",
        border: "none",
        borderRadius: "8px",
      },
    },
    {
      id: NODE_IDS.AUCTION_AGENT,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: (
          <img
            src={supervisorIcon}
            alt="Supervisor Icon"
            className="dark-icon h-4 w-4 object-contain"
          />
        ),
        label1: "Buyer",
        label2: "Logistics Agent",
        description:
          "Buyer-side supervisor in the logistics group. Translates the " +
          "user's natural-language order into a structured request " +
          "(farm + quantity + price), broadcasts it across the group, " +
          "and waits for the shipper and accountant to confirm delivery " +
          "and payment.",
        handles: HANDLE_TYPES.SOURCE,
        githubLink: `${urlsConfig.github.baseUrl}${urlsConfig.github.agents.logisticSupervisor}`,
        agentDirectoryLink: urlsConfig.agentDirectory.baseUrl,
      },
      position: { x: 150, y: 100 },
      parentId: NODE_IDS.LOGISTICS_GROUP,
      extent: "parent",
    },
    {
      id: NODE_IDS.TRANSPORT,
      type: NODE_TYPES.TRANSPORT,
      data: {
        label: "Transport: SLIM",
        compact: true,
        description:
          "SLIM (Shared Lightweight Inter-agent Messaging) is the secure " +
          "group-comm transport from AGNTCY. It moderates the group, " +
          "fans messages out to every member, and keeps the session " +
          "encrypted. The logistics demo runs entirely over it.",
        githubLink: `${urlsConfig.github.appSdkBaseUrl}${urlsConfig.github.transports.group}`,
      },
      position: { x: 380, y: 270 },
      parentId: NODE_IDS.LOGISTICS_GROUP,
      extent: "parent",
    },
    {
      id: NODE_IDS.BRAZIL_FARM,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: (
          <img
            src={farmAgentIcon}
            alt="Farm Agent Icon"
            className="dark-icon h-4 w-4 object-contain opacity-100"
          />
        ),
        label1: "Tatooine",
        label2: "Strawberry Field",
        description:
          "Stand-in farm in the logistics group communication demo. " +
          "Receives orders broadcast over the SLIM transport and " +
          "responds with shipping and inventory acknowledgements that " +
          "the buyer aggregates into the final delivery summary.",
        handles: HANDLE_TYPES.ALL,
        farmName: "Tatooine Strawberry Field",
        githubLink: `${urlsConfig.github.baseUrl}${urlsConfig.github.agents.logisticFarm}`,
        agentDirectoryLink: `${urlsConfig.agentDirectory.baseUrl}/`,
      },
      position: { x: 550, y: 100 },
      parentId: NODE_IDS.LOGISTICS_GROUP,
      extent: "parent",
    },
    {
      id: NODE_IDS.COLOMBIA_FARM,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: (
          <Truck className="dark-icon h-4 w-4 object-contain opacity-100" />
        ),
        label1: "Shipper",
        label2: "Shipper Agent",
        description:
          "Logistics shipper agent. Picks up an accepted order from the " +
          "farm, runs the (mock) customs clearance + transit steps, and " +
          "emits state updates as it goes (HANDOVER_TO_SHIPPER → " +
          "CUSTOMS_CLEARANCE → DELIVERED). The cognition layer turns " +
          "those into shipping_cost and delivery_sla claims.",
        handles: HANDLE_TYPES.TARGET,
        agentName: "Shipper Logistics",
        githubLink: `${urlsConfig.github.baseUrl}${urlsConfig.github.agents.logisticShipper}`,
        agentDirectoryLink: `${urlsConfig.agentDirectory.baseUrl}/`,
      },
      position: { x: 150, y: 500 },
      parentId: NODE_IDS.LOGISTICS_GROUP,
      extent: "parent",
    },
    {
      id: NODE_IDS.VIETNAM_FARM,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: (
          <Calculator className="dark-icon h-4 w-4 object-contain opacity-100" />
        ),
        label1: "Accountant",
        label2: "Accountant Agent",
        description:
          "Logistics accountant agent. Confirms the price the shipper " +
          "and farm agreed on, emits PAYMENT_COMPLETE once funds are " +
          "released. Maps to a payment_status claim in the cognition " +
          "fabric so the order's settlement state stays observable.",
        handles: HANDLE_TYPES.TARGET,
        agentName: "Accountant Logistics",
        githubLink: `${urlsConfig.github.baseUrl}${urlsConfig.github.agents.logisticAccountant}`,
        agentDirectoryLink: `${urlsConfig.agentDirectory.baseUrl}/`,
      },
      position: { x: 500, y: 500 },
      parentId: NODE_IDS.LOGISTICS_GROUP,
      extent: "parent",
    },
  ],
  edges: [
    {
      id: EDGE_IDS.SUPERVISOR_TO_TRANSPORT,
      source: NODE_IDS.AUCTION_AGENT,
      target: NODE_IDS.TRANSPORT,
      targetHandle: "top_left",
      data: { label: EDGE_LABELS.A2A },
      type: EDGE_TYPES.CUSTOM,
    },
    {
      id: EDGE_IDS.FARM_TO_TRANSPORT,
      source: NODE_IDS.BRAZIL_FARM,
      target: NODE_IDS.TRANSPORT,
      sourceHandle: "source",
      targetHandle: "top_right",
      data: { label: EDGE_LABELS.A2A },
      type: EDGE_TYPES.CUSTOM,
    },
    {
      id: EDGE_IDS.TRANSPORT_TO_SHIPPER,
      source: NODE_IDS.TRANSPORT,
      target: NODE_IDS.COLOMBIA_FARM,
      sourceHandle: "bottom_left",
      data: { label: EDGE_LABELS.A2A },
      type: EDGE_TYPES.CUSTOM,
    },
    {
      id: EDGE_IDS.TRANSPORT_TO_ACCOUNTANT,
      source: NODE_IDS.TRANSPORT,
      target: NODE_IDS.VIETNAM_FARM,
      sourceHandle: "bottom_right",
      data: { label: EDGE_LABELS.A2A },
      type: EDGE_TYPES.CUSTOM,
    },
  ],
  animationSequence: [
    { ids: [NODE_IDS.AUCTION_AGENT] },
    { ids: [EDGE_IDS.SUPERVISOR_TO_TRANSPORT] },
    { ids: [NODE_IDS.TRANSPORT] },
    {
      ids: [
        EDGE_IDS.FARM_TO_TRANSPORT,
        EDGE_IDS.TRANSPORT_TO_SHIPPER,
        EDGE_IDS.TRANSPORT_TO_ACCOUNTANT,
        NODE_IDS.BRAZIL_FARM,
        NODE_IDS.COLOMBIA_FARM,
        NODE_IDS.VIETNAM_FARM,
      ],
    },
    { ids: [NODE_IDS.BRAZIL_FARM] },
    { ids: [NODE_IDS.COLOMBIA_FARM] },
    { ids: [NODE_IDS.VIETNAM_FARM] },
    { ids: [NODE_IDS.COLOMBIA_FARM] },
  ],
}

export const DISCOVERY_CONFIG: GraphConfig = {
  title: "On-demand Discovery",
  nodes: [
    {
      id: NODE_IDS.RECRUITER,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: (
          <img
            src={supervisorIcon}
            alt="Recruiter Icon"
            className="dark-icon h-4 w-4 object-contain"
          />
        ),
        label1: "Agentic Recruiter",
        label2: "Discovery and delegation",
        description:
          "Recruiter supervisor used by the on-demand discovery " +
          "pattern. Queries the AGNTCY Directory for agents whose " +
          "capabilities match the user's goal, evaluates the " +
          "candidates, and delegates the actual task to whichever " +
          "ones win. Independent of the auction / logistics flows.",
        handles: HANDLE_TYPES.ALL,
        extraHandles: [
          { id: "target-right", type: "target", position: "right" },
        ],
        selected: true,
        verificationStatus: VERIFICATION_STATUS.VERIFIED,
        githubLink: `${urlsConfig.github.baseUrl}${urlsConfig.github.agents.recruiter}`,
      },
      position: { x: 400, y: 300 },
    },
    {
      id: NODE_IDS.DIRECTORY,
      type: NODE_TYPES.CUSTOM,
      data: {
        icon: (
          <img
            src={supervisorIcon}
            alt="Directory Icon"
            className="dark-icon h-4 w-4 object-contain"
          />
        ),
        label1: "Directory",
        label2: "AGNTCY Agent Directory",
        description:
          "Read-only view of the AGNTCY Agent Directory — a catalogue " +
          "of available agents indexed by capability and by AGNTCY " +
          "identity badge. The recruiter queries it during on-demand " +
          "discovery; the cognition layer doesn't write to it.",
        handles: HANDLE_TYPES.ALL,
        extraHandles: [{ id: "source-left", type: "source", position: "left" }],
        githubLink: `${urlsConfig.agentDirectory.github}`,
        agentDirectoryLink: "place-holder",
      },
      position: { x: 800, y: 100 },
    },
  ],
  edges: [
    {
      id: EDGE_IDS.RECRUITER_TO_DIRECTORY,
      source: NODE_IDS.DIRECTORY,
      target: NODE_IDS.RECRUITER,
      sourceHandle: "source-left",
      targetHandle: "target-right",
      data: { label: EDGE_LABELS.MCP_WITH_STDIO },
      type: EDGE_TYPES.CUSTOM,
    },
  ],
  animationSequence: [
    { ids: [NODE_IDS.RECRUITER] },
    { ids: [EDGE_IDS.RECRUITER_TO_DIRECTORY] },
    { ids: [NODE_IDS.DIRECTORY] },
  ],
}
