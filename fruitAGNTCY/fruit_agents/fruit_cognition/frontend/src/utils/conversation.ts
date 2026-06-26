/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 *
 * Stable per-chat conversation id. Sent to the agents on every turn as
 * `conversation_id` (LangGraph thread_id for auction/logistics) and
 * `session_id` (ADK session for discovery) so the supervisors keep context
 * across turns. Reset whenever the user starts a new chat.
 **/

import { v4 as uuid } from "uuid"

let currentConversationId = uuid()

/** Current conversation id (stable until resetConversationId is called). */
export function getConversationId(): string {
  return currentConversationId
}

/** Start a fresh conversation (called on "new chat" / clear conversation). */
export function resetConversationId(): string {
  currentConversationId = uuid()
  return currentConversationId
}
