/**
 * Copyright AGNTCY Contributors (https://github.com/agntcy)
 * SPDX-License-Identifier: Apache-2.0
 *
 * Settings page: enter and verify LLM credentials, then pick a model from the
 * provider's catalog (enriched with context window / per-token cost via the
 * backend's litellm pricing data). Stored in browser localStorage so each user
 * can bring their own key for this demo.
 */

import { useEffect, useMemo, useRef, useState } from "react"
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Container,
  Divider,
  IconButton,
  InputAdornment,
  ListItem,
  ListItemText,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material"
import VisibilityIcon from "@mui/icons-material/Visibility"
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff"
import SaveIcon from "@mui/icons-material/Save"
import RestartAltIcon from "@mui/icons-material/RestartAlt"
import CheckCircleIcon from "@mui/icons-material/CheckCircle"
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline"
import RefreshIcon from "@mui/icons-material/Refresh"
import axios from "axios"
import Navigation from "@/components/Navigation/Navigation"

import {
  type LLMConfig,
  type LLMProvider,
  defaultConfig,
  loadLLMConfig,
  saveLLMConfig,
  clearLLMConfig,
  maskKey,
} from "@/utils/llmConfig"
import { env } from "@/utils/env"

interface TestResult {
  ok: boolean
  message: string
  latencyMs?: number
  echoedReply?: string
}

interface ModelInfo {
  id: string
  label?: string | null
  context_window?: number | null
  max_output_tokens?: number | null
  input_cost_per_1k?: number | null
  output_cost_per_1k?: number | null
  provider: LLMProvider
  notes?: string | null
}

const PROVIDER_HINTS: Record<
  LLMProvider,
  { needsBaseUrl: boolean; needsApiVersion: boolean; modelHint: string }
> = {
  openai: {
    needsBaseUrl: false,
    needsApiVersion: false,
    modelHint: "gpt-4o-mini",
  },
  azure: {
    needsBaseUrl: true,
    needsApiVersion: true,
    modelHint: "your-deployment-name",
  },
  anthropic: {
    needsBaseUrl: false,
    needsApiVersion: false,
    modelHint: "claude-3-5-haiku-latest",
  },
}

function formatContext(n?: number | null): string | null {
  if (!n) return null
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`
  return String(n)
}

function formatCost(n?: number | null): string | null {
  if (n == null) return null
  if (n === 0) return "free"
  if (n < 0.001) return `$${(n * 1000).toFixed(3)}/1M`
  return `$${n.toFixed(3)}/1K`
}

interface PgState {
  source: "override" | "env" | null
  dsn_redacted: string | null
  backend: "postgres" | "in_memory"
}

interface DecisionState {
  mode: "heuristic" | "llm"
  source: "override" | "env"
}

const AdminPage: React.FC = () => {
  const [cfg, setCfg] = useState<LLMConfig>(loadLLMConfig)
  const [savedCfg, setSavedCfg] = useState<LLMConfig>(loadLLMConfig)
  const [revealKey, setRevealKey] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [savedJustNow, setSavedJustNow] = useState(false)

  // Cognition (PG fabric + decision mode) admin state.
  const [pgDsn, setPgDsn] = useState("")
  const [revealDsn, setRevealDsn] = useState(false)
  const [pgState, setPgState] = useState<PgState | null>(null)
  const [pgBusy, setPgBusy] = useState(false)
  const [pgResult, setPgResult] = useState<TestResult | null>(null)
  const [decisionState, setDecisionState] = useState<DecisionState | null>(null)
  const [decisionBusy, setDecisionBusy] = useState(false)
  const [cognitionError, setCognitionError] = useState<string | null>(null)

  const [models, setModels] = useState<ModelInfo[]>([])
  const [loadingModels, setLoadingModels] = useState(false)
  const [modelsError, setModelsError] = useState<string | null>(null)
  const fetchSeq = useRef(0)

  useEffect(() => {
    const t = setTimeout(() => setSavedJustNow(false), 2500)
    return () => clearTimeout(t)
  }, [savedJustNow])

  const apiUrl = useMemo(
    () => env.get("VITE_AGENTIC_WORKFLOWS_API_URL") || "http://127.0.0.1:9105",
    [],
  )

  /** Targets to push the active LLM config to so every supervisor honors it. */
  const propagateTargets = useMemo(
    () =>
      [
        {
          name: "agentic-workflows-api",
          url:
            env.get("VITE_AGENTIC_WORKFLOWS_API_URL") ||
            "http://127.0.0.1:9105",
        },
        {
          name: "auction-supervisor",
          url: env.get("VITE_EXCHANGE_APP_API_URL") || "http://127.0.0.1:8000",
        },
        {
          name: "logistics-supervisor",
          url: env.get("VITE_LOGISTICS_APP_API_URL") || "http://127.0.0.1:9090",
        },
        {
          name: "recruiter-supervisor",
          url: env.get("VITE_DISCOVERY_APP_API_URL") || "http://127.0.0.1:8882",
        },
      ].filter((t) => Boolean(t.url)),
    [],
  )

  const dirty = JSON.stringify(cfg) !== JSON.stringify(savedCfg)
  const hint = PROVIDER_HINTS[cfg.provider]

  const credsReady =
    cfg.apiKey.length > 0 &&
    (cfg.provider !== "azure" || (!!cfg.baseUrl && !!cfg.apiVersion))

  const update = (patch: Partial<LLMConfig>) =>
    setCfg((prev) => ({ ...prev, ...patch }))

  const fetchModels = async () => {
    if (!credsReady) return
    const seq = ++fetchSeq.current
    setLoadingModels(true)
    setModelsError(null)
    try {
      const res = await axios.post(
        `${apiUrl}/admin/llm/models`,
        {
          provider: cfg.provider,
          api_key: cfg.apiKey,
          base_url: cfg.baseUrl || undefined,
          api_version: cfg.apiVersion || undefined,
        },
        { timeout: 25_000 },
      )
      if (seq !== fetchSeq.current) return // stale
      if (res.data?.ok) {
        setModels(res.data.models ?? [])
      } else {
        setModels([])
        setModelsError(res.data?.message || "Failed to list models")
      }
    } catch (err) {
      if (seq !== fetchSeq.current) return
      const ax = axios.isAxiosError(err) ? err : null
      setModels([])
      setModelsError(
        ax?.response?.data?.detail ||
          ax?.response?.data?.message ||
          ax?.message ||
          "Failed to list models",
      )
    } finally {
      if (seq === fetchSeq.current) setLoadingModels(false)
    }
  }

  // Auto-fetch when credentials become sufficient (debounced).
  useEffect(() => {
    if (!credsReady) {
      setModels([])
      setModelsError(null)
      return
    }
    const t = setTimeout(fetchModels, 600)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cfg.apiKey, cfg.provider, cfg.baseUrl, cfg.apiVersion])

  const [propagateResults, setPropagateResults] = useState<
    { component: string; ok: boolean; rebuilt: boolean; message?: string }[]
  >([])
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    saveLLMConfig(cfg)
    setSavedCfg(cfg)
    setSavedJustNow(true)
    setSaving(true)
    setPropagateResults([])

    const payload = {
      provider: cfg.provider,
      api_key: cfg.apiKey,
      model: cfg.model,
      base_url: cfg.baseUrl || undefined,
      api_version: cfg.apiVersion || undefined,
    }

    const settled = await Promise.allSettled(
      propagateTargets.map(async (t) => {
        const res = await axios.post(`${t.url}/admin/active-config`, payload, {
          timeout: 30_000,
        })
        return {
          component: res.data?.component || t.name,
          ok: Boolean(res.data?.ok),
          rebuilt: Boolean(res.data?.rebuilt),
          message: res.data?.message,
        }
      }),
    )

    const results = settled.map((s, i) => {
      if (s.status === "fulfilled") return s.value
      const err = s.reason
      const ax = axios.isAxiosError(err) ? err : null
      return {
        component: propagateTargets[i].name,
        ok: false,
        rebuilt: false,
        message:
          ax?.response?.data?.detail ||
          ax?.response?.data?.message ||
          ax?.message ||
          "Request failed",
      }
    })
    setPropagateResults(results)
    setSaving(false)
  }

  const handleReset = () => {
    clearLLMConfig()
    setCfg({ ...defaultConfig })
    setSavedCfg({ ...defaultConfig })
    setTestResult(null)
    setModels([])
    setModelsError(null)
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    const started = performance.now()
    try {
      const res = await axios.post(
        `${apiUrl}/admin/llm/test`,
        {
          provider: cfg.provider,
          api_key: cfg.apiKey,
          model: cfg.model,
          base_url: cfg.baseUrl || undefined,
          api_version: cfg.apiVersion || undefined,
        },
        { timeout: 30_000 },
      )
      setTestResult({
        ok: Boolean(res.data?.ok),
        message: res.data?.message ?? "OK",
        latencyMs: Math.round(performance.now() - started),
        echoedReply: res.data?.reply,
      })
    } catch (err) {
      const ax = axios.isAxiosError(err) ? err : null
      const status = ax?.response?.status
      const detail =
        ax?.response?.data?.detail ||
        ax?.response?.data?.message ||
        ax?.message ||
        "Request failed"
      setTestResult({
        ok: false,
        message: status ? `HTTP ${status} — ${detail}` : detail,
        latencyMs: Math.round(performance.now() - started),
      })
    } finally {
      setTesting(false)
    }
  }

  const modelOptions = useMemo(() => models.map((m) => m.id), [models])
  const modelById = useMemo(() => {
    const map: Record<string, ModelInfo> = {}
    for (const m of models) map[m.id] = m
    return map
  }, [models])

  // ----- cognition admin: PG + decision mode -----

  const refreshCognitionState = async () => {
    try {
      const [pg, dec] = await Promise.all([
        axios.get<PgState & { ok: boolean }>(
          `${apiUrl}/admin/cognition/pg/active`,
        ),
        axios.get<DecisionState & { ok: boolean }>(
          `${apiUrl}/admin/cognition/decision/active`,
        ),
      ])
      setPgState({
        source: pg.data.source,
        dsn_redacted: pg.data.dsn_redacted,
        backend: pg.data.backend,
      })
      setDecisionState({ mode: dec.data.mode, source: dec.data.source })
      setCognitionError(null)
    } catch (err) {
      const detail = axios.isAxiosError(err)
        ? err.response?.data?.detail || err.message
        : "failed to load cognition state"
      setCognitionError(String(detail))
    }
  }

  useEffect(() => {
    void refreshCognitionState()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onPgTest = async () => {
    setPgBusy(true)
    setPgResult(null)
    const started = performance.now()
    try {
      const r = await axios.post<{
        ok: boolean
        message: string
        latency_ms: number
      }>(`${apiUrl}/admin/cognition/pg/test`, { dsn: pgDsn })
      setPgResult({
        ok: r.data.ok,
        message: r.data.message,
        latencyMs: r.data.latency_ms,
      })
    } catch (err) {
      const ax = axios.isAxiosError(err) ? err : null
      const detail = ax?.response?.data?.detail || ax?.message || "probe failed"
      setPgResult({
        ok: false,
        message: String(detail),
        latencyMs: Math.round(performance.now() - started),
      })
    } finally {
      setPgBusy(false)
    }
  }

  const onPgSave = async () => {
    setPgBusy(true)
    setPgResult(null)
    try {
      await axios.post(`${apiUrl}/admin/cognition/pg/active`, { dsn: pgDsn })
      await refreshCognitionState()
      setPgResult({
        ok: true,
        message: "DSN active. Fabric swapped to Postgres.",
      })
    } catch (err) {
      const ax = axios.isAxiosError(err) ? err : null
      const detail = ax?.response?.data?.detail || ax?.message || "save failed"
      setPgResult({ ok: false, message: String(detail) })
    } finally {
      setPgBusy(false)
    }
  }

  const onPgClear = async () => {
    setPgBusy(true)
    try {
      await axios.delete(`${apiUrl}/admin/cognition/pg/active`)
      await refreshCognitionState()
      setPgResult({ ok: true, message: "Override cleared." })
    } catch (err) {
      const ax = axios.isAxiosError(err) ? err : null
      const detail = ax?.response?.data?.detail || ax?.message || "clear failed"
      setPgResult({ ok: false, message: String(detail) })
    } finally {
      setPgBusy(false)
    }
  }

  const onDecisionMode = async (mode: "heuristic" | "llm") => {
    setDecisionBusy(true)
    try {
      await axios.post(`${apiUrl}/admin/cognition/decision/active`, { mode })
      await refreshCognitionState()
    } catch (err) {
      const ax = axios.isAxiosError(err) ? err : null
      const detail =
        ax?.response?.data?.detail || ax?.message || "set mode failed"
      setCognitionError(String(detail))
    } finally {
      setDecisionBusy(false)
    }
  }

  const onDecisionClear = async () => {
    setDecisionBusy(true)
    try {
      await axios.delete(`${apiUrl}/admin/cognition/decision/active`)
      await refreshCognitionState()
    } catch (err) {
      const ax = axios.isAxiosError(err) ? err : null
      const detail = ax?.response?.data?.detail || ax?.message || "clear failed"
      setCognitionError(String(detail))
    } finally {
      setDecisionBusy(false)
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <Navigation />

      <Container maxWidth="md" sx={{ py: 4 }}>
        <Box sx={{ mb: 3 }}>
          <Typography
            variant="h5"
            sx={{
              fontFamily: '"Merriweather", "Georgia", serif',
              fontWeight: 700,
              letterSpacing: -0.3,
            }}
          >
            Settings
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ maxWidth: 720, mt: 0.5 }}
          >
            Per-browser configuration for the LLM that powers the agents and the
            cognition layer's runtime backends. Credentials and DSNs entered
            here are only stored in this browser; pushing the active config
            propagates it to every supervisor so the next prompt uses it.
            Nothing here modifies cluster Secrets.
          </Typography>
        </Box>
        <Card>
          <CardHeader
            title="Bring-your-own LLM credentials"
            subheader="Stored only in this browser (localStorage). Once saved, all supervisors honor it for new requests (active-config). Cluster Secrets are not modified."
          />
          <Divider />
          <CardContent>
            <Stack spacing={2.5}>
              <TextField
                label="Provider"
                select
                value={cfg.provider}
                onChange={(e) => {
                  update({
                    provider: e.target.value as LLMProvider,
                    model: "", // pick again from the new provider's catalog
                  })
                  setModels([])
                  setModelsError(null)
                }}
                fullWidth
              >
                <MenuItem value="openai">OpenAI</MenuItem>
                <MenuItem value="azure">Azure OpenAI</MenuItem>
                <MenuItem value="anthropic">Anthropic</MenuItem>
              </TextField>

              <TextField
                label="API key"
                value={cfg.apiKey}
                onChange={(e) => update({ apiKey: e.target.value })}
                type={revealKey ? "text" : "password"}
                fullWidth
                autoComplete="off"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        size="small"
                        onClick={() => setRevealKey((v) => !v)}
                        edge="end"
                      >
                        {revealKey ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
                helperText={
                  savedCfg.apiKey
                    ? `Currently saved: ${maskKey(savedCfg.apiKey)}`
                    : "Not saved yet"
                }
              />

              {hint.needsBaseUrl && (
                <TextField
                  label="API base URL"
                  value={cfg.baseUrl ?? ""}
                  onChange={(e) => update({ baseUrl: e.target.value })}
                  placeholder="https://your-resource.openai.azure.com"
                  fullWidth
                />
              )}

              {hint.needsApiVersion && (
                <TextField
                  label="API version"
                  value={cfg.apiVersion ?? ""}
                  onChange={(e) => update({ apiVersion: e.target.value })}
                  placeholder="2024-02-15-preview"
                  fullWidth
                />
              )}

              <Autocomplete<string, false, false, true>
                freeSolo
                options={modelOptions}
                value={cfg.model || ""}
                onChange={(_, value) => update({ model: value || "" })}
                onInputChange={(_, value, reason) => {
                  if (reason === "input") update({ model: value })
                }}
                loading={loadingModels}
                disabled={!credsReady && modelOptions.length === 0}
                renderOption={(props, option) => {
                  const m = modelById[option]
                  const ctx = formatContext(m?.context_window)
                  const inCost = formatCost(m?.input_cost_per_1k)
                  const outCost = formatCost(m?.output_cost_per_1k)
                  return (
                    <ListItem {...props} key={option} dense>
                      <ListItemText
                        primary={m?.label || option}
                        secondary={
                          <Stack
                            direction="row"
                            spacing={0.5}
                            flexWrap="wrap"
                            useFlexGap
                            sx={{ mt: 0.5 }}
                          >
                            {ctx && (
                              <Chip
                                label={`ctx ${ctx}`}
                                size="small"
                                variant="outlined"
                              />
                            )}
                            {inCost && (
                              <Chip
                                label={`in ${inCost}`}
                                size="small"
                                variant="outlined"
                              />
                            )}
                            {outCost && (
                              <Chip
                                label={`out ${outCost}`}
                                size="small"
                                variant="outlined"
                              />
                            )}
                            {m?.notes && (
                              <Chip
                                label={m.notes}
                                size="small"
                                variant="outlined"
                                color="warning"
                              />
                            )}
                          </Stack>
                        }
                        secondaryTypographyProps={{ component: "div" }}
                      />
                    </ListItem>
                  )
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Model"
                    placeholder={hint.modelHint}
                    helperText={
                      modelsError
                        ? `Catalog error: ${modelsError} (you can still type a model id)`
                        : credsReady
                          ? loadingModels
                            ? "Listing models…"
                            : `${modelOptions.length} models available — select or type one`
                          : "Enter API key to list available models"
                    }
                    InputProps={{
                      ...params.InputProps,
                      endAdornment: (
                        <>
                          {loadingModels && (
                            <CircularProgress color="inherit" size={16} />
                          )}
                          {credsReady && (
                            <Tooltip title="Refresh models">
                              <span>
                                <IconButton
                                  size="small"
                                  onClick={fetchModels}
                                  disabled={loadingModels}
                                >
                                  <RefreshIcon fontSize="small" />
                                </IconButton>
                              </span>
                            </Tooltip>
                          )}
                          {params.InputProps.endAdornment}
                        </>
                      ),
                    }}
                  />
                )}
              />

              <Stack
                direction="row"
                spacing={1.5}
                flexWrap="wrap"
                alignItems="center"
              >
                <Button
                  variant="contained"
                  startIcon={
                    testing ? (
                      <CircularProgress size={16} color="inherit" />
                    ) : (
                      <CheckCircleIcon />
                    )
                  }
                  onClick={handleTest}
                  disabled={testing || !cfg.apiKey || !cfg.model}
                >
                  {testing ? "Testing…" : "Test connection"}
                </Button>
                <Button
                  variant="outlined"
                  startIcon={
                    saving ? (
                      <CircularProgress size={16} color="inherit" />
                    ) : (
                      <SaveIcon />
                    )
                  }
                  onClick={handleSave}
                  disabled={!dirty || saving || !cfg.apiKey || !cfg.model}
                >
                  {saving ? "Saving…" : "Save"}
                </Button>
                <Button
                  color="warning"
                  variant="text"
                  startIcon={<RestartAltIcon />}
                  onClick={handleReset}
                >
                  Reset
                </Button>
                {savedJustNow && (
                  <Typography variant="caption" color="success.main">
                    Saved.
                  </Typography>
                )}
              </Stack>

              {propagateResults.length > 0 && (
                <Alert
                  severity={
                    propagateResults.every((r) => r.ok) ? "success" : "warning"
                  }
                >
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    Active config propagated to {propagateResults.length}{" "}
                    component(s).
                  </Typography>
                  <Stack
                    direction="row"
                    spacing={0.5}
                    flexWrap="wrap"
                    useFlexGap
                    sx={{ mt: 0.5 }}
                  >
                    {propagateResults.map((r) => (
                      <Chip
                        key={r.component}
                        size="small"
                        color={r.ok ? "success" : "error"}
                        variant={r.rebuilt ? "filled" : "outlined"}
                        label={`${r.component}${r.rebuilt ? " · rebuilt" : ""}${
                          r.message ? ` · ${r.message}` : ""
                        }`}
                      />
                    ))}
                  </Stack>
                </Alert>
              )}

              {testResult && (
                <Alert
                  severity={testResult.ok ? "success" : "error"}
                  icon={
                    testResult.ok ? <CheckCircleIcon /> : <ErrorOutlineIcon />
                  }
                >
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {testResult.ok ? "Connected." : "Failed"} ·{" "}
                    {testResult.latencyMs ?? "?"} ms
                  </Typography>
                  <Typography variant="body2">{testResult.message}</Typography>
                  {testResult.echoedReply && (
                    <Typography
                      variant="body2"
                      sx={{ mt: 0.5, fontStyle: "italic", opacity: 0.85 }}
                    >
                      Reply: {testResult.echoedReply}
                    </Typography>
                  )}
                </Alert>
              )}
            </Stack>
          </CardContent>
        </Card>

        <Card sx={{ mt: 3 }}>
          <CardHeader
            title="Cognition fabric"
            subheader="Postgres backend and decision-engine mode"
          />
          <CardContent>
            {cognitionError ? (
              <Alert
                severity="error"
                sx={{ mb: 2 }}
                onClose={() => setCognitionError(null)}
              >
                {cognitionError}
              </Alert>
            ) : null}

            <Stack spacing={3}>
              {/* Postgres */}
              <Box>
                <Stack
                  direction="row"
                  alignItems="center"
                  spacing={1}
                  sx={{ mb: 1 }}
                >
                  <Typography variant="subtitle1">Postgres backend</Typography>
                  {pgState ? (
                    <Chip
                      label={`backend: ${pgState.backend}`}
                      size="small"
                      color={
                        pgState.backend === "postgres" ? "success" : "default"
                      }
                    />
                  ) : null}
                  {pgState?.source ? (
                    <Chip
                      label={`source: ${pgState.source}`}
                      size="small"
                      variant="outlined"
                    />
                  ) : null}
                </Stack>
                {pgState?.dsn_redacted ? (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ fontFamily: "monospace", display: "block", mb: 1 }}
                  >
                    Active: {pgState.dsn_redacted}
                  </Typography>
                ) : (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: "block", mb: 1 }}
                  >
                    No DSN configured — cognition state is in-memory only and
                    lost on restart.
                  </Typography>
                )}
                <TextField
                  fullWidth
                  label="DSN"
                  placeholder="postgresql://user:password@host:5432/dbname"
                  size="small"
                  type={revealDsn ? "text" : "password"}
                  value={pgDsn}
                  onChange={(e) => setPgDsn(e.target.value)}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          aria-label="toggle DSN visibility"
                          onClick={() => setRevealDsn((v) => !v)}
                          edge="end"
                          size="small"
                        >
                          {revealDsn ? (
                            <VisibilityOffIcon />
                          ) : (
                            <VisibilityIcon />
                          )}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => void onPgTest()}
                    disabled={pgBusy || !pgDsn}
                    startIcon={
                      pgBusy ? <CircularProgress size={14} /> : <RefreshIcon />
                    }
                  >
                    Test
                  </Button>
                  <Button
                    variant="contained"
                    size="small"
                    onClick={() => void onPgSave()}
                    disabled={pgBusy || !pgDsn}
                    startIcon={<SaveIcon />}
                  >
                    Save active
                  </Button>
                  <Button
                    variant="outlined"
                    color="warning"
                    size="small"
                    onClick={() => void onPgClear()}
                    disabled={pgBusy}
                    startIcon={<RestartAltIcon />}
                  >
                    Clear override
                  </Button>
                </Stack>
                {pgResult ? (
                  <Alert
                    severity={pgResult.ok ? "success" : "error"}
                    icon={
                      pgResult.ok ? <CheckCircleIcon /> : <ErrorOutlineIcon />
                    }
                    sx={{ mt: 1 }}
                    onClose={() => setPgResult(null)}
                  >
                    {pgResult.message}
                    {pgResult.latencyMs != null
                      ? ` · ${pgResult.latencyMs} ms`
                      : ""}
                  </Alert>
                ) : null}
              </Box>

              <Divider />

              {/* Decision engine mode */}
              <Box>
                <Stack
                  direction="row"
                  alignItems="center"
                  spacing={1}
                  sx={{ mb: 1 }}
                >
                  <Typography variant="subtitle1">Decision engine</Typography>
                  {decisionState ? (
                    <Chip
                      label={`mode: ${decisionState.mode}`}
                      size="small"
                      color={
                        decisionState.mode === "llm" ? "primary" : "default"
                      }
                    />
                  ) : null}
                  {decisionState?.source ? (
                    <Chip
                      label={`source: ${decisionState.source}`}
                      size="small"
                      variant="outlined"
                    />
                  ) : null}
                </Stack>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block", mb: 1 }}
                >
                  Heuristic ranks plans by weather risk, then cost, then plan
                  type. LLM mode asks the configured model to pick a plan; falls
                  back to heuristic on any failure.
                </Typography>
                <Stack direction="row" spacing={1}>
                  <Button
                    variant={
                      decisionState?.mode === "heuristic" &&
                      decisionState.source === "override"
                        ? "contained"
                        : "outlined"
                    }
                    size="small"
                    disabled={decisionBusy}
                    onClick={() => void onDecisionMode("heuristic")}
                  >
                    Heuristic
                  </Button>
                  <Button
                    variant={
                      decisionState?.mode === "llm" &&
                      decisionState.source === "override"
                        ? "contained"
                        : "outlined"
                    }
                    size="small"
                    disabled={decisionBusy}
                    onClick={() => void onDecisionMode("llm")}
                  >
                    LLM
                  </Button>
                  <Button
                    variant="outlined"
                    color="warning"
                    size="small"
                    disabled={
                      decisionBusy || decisionState?.source !== "override"
                    }
                    onClick={() => void onDecisionClear()}
                    startIcon={<RestartAltIcon />}
                  >
                    Clear override
                  </Button>
                </Stack>
              </Box>
            </Stack>
          </CardContent>
        </Card>

        <Box sx={{ mt: 3, opacity: 0.7 }}>
          <Typography variant="caption">
            Models endpoint: <code>{apiUrl}/admin/llm/models</code> · Test
            endpoint: <code>{apiUrl}/admin/llm/test</code> · Cognition:{" "}
            <code>{apiUrl}/admin/cognition/pg|decision/active</code>.
          </Typography>
        </Box>
      </Container>
    </Box>
  )
}

export default AdminPage
