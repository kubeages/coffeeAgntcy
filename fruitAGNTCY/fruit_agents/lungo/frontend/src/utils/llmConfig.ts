/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 *
 * Per-session LLM credential storage. Lives in browser localStorage so a key
 * never leaves the user's machine; supervisors can opt to honor it via a
 * future X-LLM-* header layer.
 */

export type LLMProvider = "openai" | "azure" | "anthropic"

export interface LLMConfig {
  provider: LLMProvider
  apiKey: string
  model: string
  baseUrl?: string
  apiVersion?: string
}

const STORAGE_KEY = "fruitAgntcy.llmConfig.v1"

export const defaultConfig: LLMConfig = {
  provider: "openai",
  apiKey: "",
  model: "gpt-4o-mini",
  baseUrl: "",
  apiVersion: "",
}

export function loadLLMConfig(): LLMConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { ...defaultConfig }
    const parsed = JSON.parse(raw) as Partial<LLMConfig>
    return { ...defaultConfig, ...parsed }
  } catch {
    return { ...defaultConfig }
  }
}

export function saveLLMConfig(cfg: LLMConfig): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg))
}

export function clearLLMConfig(): void {
  localStorage.removeItem(STORAGE_KEY)
}

export function maskKey(key: string): string {
  if (!key) return ""
  if (key.length <= 8) return "•".repeat(key.length)
  return `${key.slice(0, 4)}${"•".repeat(Math.max(8, key.length - 8))}${key.slice(-4)}`
}
