/**
 * Cognition view: read-only browser for intents, claims and beliefs
 * captured by the cognition fabric (in-memory or Postgres backend).
 */

import axios from "axios"
import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Divider,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material"
import RefreshIcon from "@mui/icons-material/Refresh"
import Navigation from "@/components/Navigation/Navigation"

import {
  fetchIntents,
  fetchIntentState,
  getCognitionApiUrl,
} from "@/utils/cognitionApi"
import { fruitIcon } from "@/utils/fruitIcons"
import { fruitImage, originImage, stateImage } from "@/utils/illustrations"
import type {
  Belief,
  Claim,
  Conflict,
  ConflictSeverity,
  EvaluatedOption,
  IntentStateResponse,
  IntentSummary,
  WeatherRiskLevel,
} from "@/types/cognition"

const statusColor = (
  status: string,
): "default" | "primary" | "secondary" | "info" | "warning" | "error" => {
  switch (status) {
    case "approved":
    case "committed":
      return "primary" // theme green = "ready to ship"
    case "approval_required":
      return "secondary" // theme orange = "awaiting picker"
    case "rejected":
    case "failed":
      return "error"
    case "grounding":
    case "negotiating":
      return "info"
    default:
      return "default"
  }
}

const formatValue = (v: unknown): string => {
  if (v === null || v === undefined) return "—"
  if (typeof v === "number")
    return Number.isInteger(v) ? String(v) : v.toFixed(2)
  if (typeof v === "object") return JSON.stringify(v)
  return String(v)
}

const ClaimsTable = ({ claims }: { claims: Claim[] }) => {
  if (claims.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No claims have been recorded for this intent yet.
      </Typography>
    )
  }
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Type</TableCell>
            <TableCell>Subject</TableCell>
            <TableCell>Agent</TableCell>
            <TableCell>Value</TableCell>
            <TableCell align="right">Confidence</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {claims.map((c) => (
            <TableRow key={c.claim_id}>
              <TableCell>
                <Chip label={c.claim_type} size="small" />
              </TableCell>
              <TableCell>{c.subject}</TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {c.agent_id}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {formatValue(c.value)}
                </Typography>
              </TableCell>
              <TableCell align="right">{c.confidence.toFixed(2)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

const BeliefsTable = ({ beliefs }: { beliefs: Belief[] }) => {
  if (beliefs.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No beliefs derived yet — beliefs require at least one of inventory /
        price / quality / origin claims.
      </Typography>
    )
  }
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Type</TableCell>
            <TableCell>Subject</TableCell>
            <TableCell>Supplier</TableCell>
            <TableCell>Aggregated value</TableCell>
            <TableCell align="right">Confidence</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {beliefs.map((b) => (
            <TableRow key={b.belief_id}>
              <TableCell>
                <Chip label={b.belief_type} size="small" color="primary" />
              </TableCell>
              <TableCell>{b.subject}</TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {b.agent_id}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {formatValue(b.value)}
                </Typography>
              </TableCell>
              <TableCell align="right">{b.confidence.toFixed(2)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

const severityColor = (
  s: ConflictSeverity,
): "default" | "info" | "warning" | "error" => {
  switch (s) {
    case "low":
      return "default"
    case "medium":
      return "info"
    case "high":
      return "warning"
    case "critical":
      return "error"
  }
}

const weatherColor = (
  l: WeatherRiskLevel,
): "default" | "success" | "warning" | "error" => {
  switch (l) {
    case "low":
      return "success"
    case "medium":
      return "warning"
    case "high":
      return "error"
    default:
      return "default"
  }
}

const ConflictsTable = ({ conflicts }: { conflicts: Conflict[] }) => {
  if (conflicts.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No conflicts detected.
      </Typography>
    )
  }
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Severity</TableCell>
            <TableCell>Type</TableCell>
            <TableCell>Description</TableCell>
            <TableCell>Suggested resolution</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {conflicts.map((c) => (
            <TableRow key={c.conflict_id}>
              <TableCell>
                <Chip
                  label={c.severity}
                  size="small"
                  color={severityColor(c.severity)}
                />
              </TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {c.conflict_type}
                </Typography>
              </TableCell>
              <TableCell>{c.description}</TableCell>
              <TableCell>
                <Typography variant="body2" color="text.secondary">
                  {c.suggested_resolution ?? "—"}
                </Typography>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

const OptionsTable = ({ options }: { options: EvaluatedOption[] }) => {
  if (options.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No supplier options yet — claims need to be aggregated into a
        supply_option belief first.
      </Typography>
    )
  }
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Verdict</TableCell>
            <TableCell>Supplier</TableCell>
            <TableCell align="right">Rank</TableCell>
            <TableCell align="right">Total cost</TableCell>
            <TableCell align="right">Budget</TableCell>
            <TableCell>Weather</TableCell>
            <TableCell>Violations</TableCell>
            <TableCell>Rationale</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {options.map((o) => (
            <TableRow key={o.supplier}>
              <TableCell>
                {o.allowed ? (
                  <Chip label="allowed" size="small" color="success" />
                ) : o.requires_human_approval ? (
                  <Chip label="needs approval" size="small" color="warning" />
                ) : (
                  <Chip label="blocked" size="small" color="error" />
                )}
              </TableCell>
              <TableCell>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {o.supplier}
                </Typography>
                {o.origin ? (
                  <Typography variant="caption" color="text.secondary">
                    {o.origin}
                  </Typography>
                ) : null}
              </TableCell>
              <TableCell align="right">{o.cost_rank}</TableCell>
              <TableCell align="right">
                {o.total_price_usd === null
                  ? "—"
                  : `$${o.total_price_usd.toFixed(2)}`}
              </TableCell>
              <TableCell align="right">
                {o.within_budget === null ? (
                  "—"
                ) : o.within_budget ? (
                  <Chip label="under" size="small" color="success" />
                ) : (
                  <Chip label="over" size="small" color="error" />
                )}
              </TableCell>
              <TableCell>
                <Chip
                  label={o.weather_risk_level}
                  size="small"
                  color={weatherColor(o.weather_risk_level)}
                />
              </TableCell>
              <TableCell>
                {o.violations.length === 0 ? (
                  "—"
                ) : (
                  <Stack direction="row" spacing={0.5} flexWrap="wrap">
                    {o.violations.map((v) => (
                      <Chip key={v} label={v} size="small" variant="outlined" />
                    ))}
                  </Stack>
                )}
              </TableCell>
              <TableCell>
                <Typography variant="caption" color="text.secondary">
                  {o.rationale ?? ""}
                </Typography>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

const IntentDetail = ({ data }: { data: IntentStateResponse }) => {
  const intent = data.intent
  const fields: Array<[string, unknown]> = [
    ["Goal", intent.goal],
    ["Fruit", intent.fruit_type ?? "—"],
    ["Quantity (lb)", intent.quantity_lb ?? "—"],
    ["Max price (USD)", intent.max_price_usd ?? "—"],
    ["Delivery (days)", intent.delivery_days ?? "—"],
  ]
  return (
    <Stack spacing={3}>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction="row" alignItems="flex-start" spacing={2} mb={1}>
          {(() => {
            const url = fruitImage(intent.fruit_type)
            if (url) {
              return (
                <Box
                  component="img"
                  src={url}
                  alt={intent.fruit_type ?? ""}
                  sx={{
                    width: 72,
                    height: 72,
                    borderRadius: 1,
                    objectFit: "cover",
                    flexShrink: 0,
                  }}
                />
              )
            }
            const { Icon, color } = fruitIcon(intent.fruit_type)
            return <Icon size={28} color={color} strokeWidth={1.75} />
          })()}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Stack direction="row" alignItems="center" spacing={1.5}>
              <Typography
                variant="h6"
                sx={{
                  fontFamily: "monospace",
                  flex: 1,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {intent.intent_id}
              </Typography>
              <Chip
                label={intent.status}
                size="small"
                color={statusColor(intent.status)}
              />
            </Stack>
            {(() => {
              const originUrl = originImage(
                (intent.target_origin as string | null) ?? null,
              )
              return originUrl ? (
                <Box
                  component="img"
                  src={originUrl}
                  alt=""
                  sx={{
                    width: "100%",
                    maxHeight: 110,
                    objectFit: "cover",
                    borderRadius: 1,
                    mt: 1,
                    opacity: 0.9,
                  }}
                />
              ) : null
            })()}
          </Box>
        </Stack>
        <Stack
          direction="row"
          flexWrap="wrap"
          spacing={3}
          rowGap={1}
          divider={<Divider orientation="vertical" flexItem />}
        >
          {fields.map(([k, v]) => (
            <Box key={k}>
              <Typography variant="caption" color="text.secondary">
                {k}
              </Typography>
              <Typography variant="body2">{formatValue(v)}</Typography>
            </Box>
          ))}
        </Stack>
        {intent.human_approval_required_if.length > 0 ? (
          <Box mt={2}>
            <Typography variant="caption" color="text.secondary">
              Approval required if
            </Typography>
            <Stack direction="row" spacing={0.5} flexWrap="wrap" mt={0.5}>
              {intent.human_approval_required_if.map((tag) => (
                <Chip key={tag} label={tag} size="small" variant="outlined" />
              ))}
            </Stack>
          </Box>
        ) : null}
      </Paper>

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Options ({data.options.length})
        </Typography>
        <OptionsTable options={data.options} />
      </Box>

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Conflicts ({data.conflicts.length})
        </Typography>
        <ConflictsTable conflicts={data.conflicts} />
      </Box>

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Beliefs ({data.beliefs.length})
        </Typography>
        <BeliefsTable beliefs={data.beliefs} />
      </Box>

      <Box>
        <Typography variant="subtitle1" gutterBottom>
          Claims ({data.claims.length})
        </Typography>
        <ClaimsTable claims={data.claims} />
      </Box>
    </Stack>
  )
}

const CognitionPage = () => {
  const [intents, setIntents] = useState<IntentSummary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<IntentStateResponse | null>(null)
  const [loadingList, setLoadingList] = useState(false)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const cognitionUrl = useMemo(getCognitionApiUrl, [])

  const reloadList = useCallback(async (signal?: AbortSignal) => {
    setLoadingList(true)
    setError(null)
    try {
      const data = await fetchIntents(signal)
      setIntents(data.items)
      // Auto-select the first intent if none chosen yet.
      if (data.items.length > 0 && selectedId === null) {
        setSelectedId(data.items[0].intent_id)
      }
    } catch (e: unknown) {
      if (axios.isCancel(e)) return
      setError(e instanceof Error ? e.message : "failed to load intents")
    } finally {
      setLoadingList(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const reloadDetail = useCallback(
    async (intentId: string, signal?: AbortSignal) => {
      setLoadingDetail(true)
      try {
        const data = await fetchIntentState(intentId, signal)
        setDetail(data)
      } catch (e: unknown) {
        if (axios.isCancel(e)) return
        setError(e instanceof Error ? e.message : "failed to load intent state")
      } finally {
        setLoadingDetail(false)
      }
    },
    [],
  )

  useEffect(() => {
    const ctrl = new AbortController()
    void reloadList(ctrl.signal)
    return () => ctrl.abort()
  }, [reloadList])

  useEffect(() => {
    if (!selectedId) return
    const ctrl = new AbortController()
    void reloadDetail(selectedId, ctrl.signal)
    return () => ctrl.abort()
  }, [selectedId, reloadDetail])

  const refreshAll = () => {
    void reloadList()
    if (selectedId) void reloadDetail(selectedId)
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <Navigation />

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ xs: "flex-start", sm: "flex-end" }}
          justifyContent="space-between"
          spacing={2}
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography
              variant="h5"
              sx={{
                fontFamily: '"Merriweather", "Georgia", serif',
                fontWeight: 700,
                letterSpacing: -0.3,
              }}
            >
              Cognition
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ maxWidth: 720 }}
            >
              Read-only browser for the cognition fabric. Each chat order
              creates an <strong>intent</strong>; each agent response feeds
              <strong> claims</strong> back into the fabric, which the engine
              pipeline aggregates into <strong>beliefs</strong>,{" "}
              <strong>options</strong>, and <strong>conflicts</strong>. Pick an
              intent on the left to inspect everything the system knows about
              it.
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Tooltip title={`Reading from ${cognitionUrl}/cognition`}>
              <Typography variant="caption" color="text.secondary">
                {cognitionUrl.replace(/^https?:\/\//, "")}
              </Typography>
            </Tooltip>
            <Button
              startIcon={<RefreshIcon />}
              onClick={refreshAll}
              size="small"
              variant="outlined"
            >
              Refresh
            </Button>
          </Stack>
        </Stack>
        {error ? (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        ) : null}

        <Stack direction={{ xs: "column", md: "row" }} spacing={3}>
          <Paper
            variant="outlined"
            sx={{ width: { xs: "100%", md: 320 }, flexShrink: 0 }}
          >
            <Box sx={{ p: 2, display: "flex", alignItems: "center" }}>
              <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                Intents ({intents.length})
              </Typography>
              {loadingList ? <CircularProgress size={16} /> : null}
            </Box>
            <Divider />
            {intents.length === 0 && !loadingList ? (
              <Box sx={{ p: 3, textAlign: "center" }}>
                {(() => {
                  const url = stateImage("no_intents")
                  if (url) {
                    return (
                      <Box
                        component="img"
                        src={url}
                        alt=""
                        sx={{
                          width: "100%",
                          maxWidth: 200,
                          height: "auto",
                          borderRadius: 1,
                          mb: 1.5,
                        }}
                      />
                    )
                  }
                  const { Icon, color } = fruitIcon(null)
                  return <Icon size={48} color={color} strokeWidth={1.5} />
                })()}
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 1 }}
                >
                  No fruit orders yet.
                </Typography>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: "block", mt: 0.5 }}
                >
                  Send a chat prompt to start one.
                </Typography>
              </Box>
            ) : (
              <List dense disablePadding>
                {intents.map((it) => {
                  const { Icon, color } = fruitIcon(it.fruit_type)
                  return (
                    <ListItemButton
                      key={it.intent_id}
                      selected={selectedId === it.intent_id}
                      onClick={() => setSelectedId(it.intent_id)}
                      sx={{ gap: 1.5 }}
                    >
                      <Icon size={22} color={color} strokeWidth={1.75} />
                      <ListItemText
                        primary={
                          it.fruit_type
                            ? it.fruit_type[0].toUpperCase() +
                              it.fruit_type.slice(1)
                            : it.goal
                        }
                        secondary={`${it.quantity_lb ?? "?"} lb · ${it.intent_id.slice(0, 18)}…`}
                        primaryTypographyProps={{ fontWeight: 600 }}
                      />
                      <Chip
                        label={it.status}
                        size="small"
                        color={statusColor(it.status)}
                      />
                    </ListItemButton>
                  )
                })}
              </List>
            )}
          </Paper>

          <Box sx={{ flexGrow: 1 }}>
            {selectedId === null ? (
              <Typography variant="body2" color="text.secondary">
                Pick an intent from the list to see its claims and beliefs.
              </Typography>
            ) : loadingDetail && detail === null ? (
              <CircularProgress />
            ) : detail ? (
              <IntentDetail data={detail} />
            ) : (
              <Typography variant="body2" color="text.secondary">
                No data for this intent.
              </Typography>
            )}
          </Box>
        </Stack>
      </Container>
    </Box>
  )
}

export default CognitionPage
