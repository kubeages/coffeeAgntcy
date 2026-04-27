/**
 * Decisions inbox: lists intents whose current decision requires human
 * approval, and lets the operator approve, reject, or request an
 * alternative. Designed per the M1 kickoff decision: chat stays
 * synchronous, decisions are reviewed here.
 */

import axios from "axios"
import { useCallback, useEffect, useRef, useState } from "react"
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Divider,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material"
import CheckCircleIcon from "@mui/icons-material/CheckCircle"
import CancelIcon from "@mui/icons-material/Cancel"
import RefreshIcon from "@mui/icons-material/Refresh"
import ChangeCircleIcon from "@mui/icons-material/ChangeCircle"
import Navigation from "@/components/Navigation/Navigation"

import {
  approveIntent,
  fetchApprovals,
  getCognitionApiUrl,
  rejectIntent,
  requestAlternativeIntent,
} from "@/utils/cognitionApi"
import { fruitIcon } from "@/utils/fruitIcons"
import { fruitImage, stateImage } from "@/utils/illustrations"
import type { ApprovalRequest, Plan } from "@/types/cognition"

type ActionFn = (intentId: string, note?: string) => Promise<unknown>

const PlanSummary = ({ plan }: { plan: Plan | null }) => {
  if (!plan) {
    return (
      <Typography variant="body2" color="text.secondary">
        No plan selected.
      </Typography>
    )
  }
  return (
    <Box>
      <Stack direction="row" spacing={1} alignItems="center" mb={0.5}>
        <Chip
          label={
            plan.plan_type === "single_supplier"
              ? "single supplier"
              : "split order"
          }
          size="small"
          color={plan.plan_type === "single_supplier" ? "default" : "primary"}
        />
        <Typography variant="body2">
          {plan.total_quantity_lb} lb ·{" "}
          {plan.total_price_usd === null
            ? "unpriced"
            : `$${plan.total_price_usd.toFixed(2)}`}
        </Typography>
      </Stack>
      <Stack direction="row" flexWrap="wrap" spacing={0.5}>
        {plan.suppliers.map((s) => (
          <Chip
            key={s.supplier}
            label={`${s.supplier} · ${s.quantity_lb} lb${s.unit_price_usd != null ? ` @ $${s.unit_price_usd}` : ""}`}
            size="small"
            variant="outlined"
            sx={{ fontFamily: "monospace" }}
          />
        ))}
      </Stack>
    </Box>
  )
}

const ApprovalCard = ({
  item,
  onAction,
  busy,
}: {
  item: ApprovalRequest
  onAction: (action: ActionFn, label: string) => Promise<void>
  busy: boolean
}) => {
  const intent = item.intent
  const decision = item.decision
  const fields: Array<[string, unknown]> = [
    ["Fruit", intent.fruit_type ?? "—"],
    ["Quantity", intent.quantity_lb ?? "—"],
    ["Max price", intent.max_price_usd ?? "—"],
    ["Delivery", intent.delivery_days ?? "—"],
  ]
  const { Icon: FruitIconCmp, color: fruitColor } = fruitIcon(intent.fruit_type)
  const fruitImg = fruitImage(intent.fruit_type)

  return (
    <Paper
      variant="outlined"
      sx={{ p: 2, borderLeft: `4px solid ${fruitColor}` }}
    >
      <Stack direction="row" alignItems="center" spacing={1.5} mb={1.5}>
        {fruitImg ? (
          <Box
            component="img"
            src={fruitImg}
            alt={intent.fruit_type ?? ""}
            sx={{
              width: 56,
              height: 56,
              borderRadius: 1,
              objectFit: "cover",
              flexShrink: 0,
            }}
          />
        ) : (
          <FruitIconCmp size={26} color={fruitColor} strokeWidth={1.75} />
        )}
        <Typography
          variant="subtitle1"
          sx={{
            fontFamily: "monospace",
            flexGrow: 1,
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {intent.intent_id}
        </Typography>
        <Chip
          label={`mode: ${decision.mode}`}
          size="small"
          variant="outlined"
        />
        <Chip
          label={`confidence ${decision.confidence.toFixed(2)}`}
          size="small"
          color="primary"
        />
      </Stack>

      <Stack direction="row" flexWrap="wrap" spacing={3} rowGap={1} mb={2}>
        {fields.map(([k, v]) => (
          <Box key={k}>
            <Typography variant="caption" color="text.secondary">
              {k}
            </Typography>
            <Typography variant="body2">
              {v == null ? "—" : String(v)}
            </Typography>
          </Box>
        ))}
      </Stack>

      <Box mb={2}>
        <Typography variant="caption" color="text.secondary">
          Proposed plan
        </Typography>
        <PlanSummary plan={decision.selected_plan} />
      </Box>

      <Box mb={2}>
        <Typography variant="caption" color="text.secondary">
          Why approval is needed
        </Typography>
        <Stack direction="row" spacing={0.5} flexWrap="wrap" mt={0.5}>
          {decision.approval_violations.length === 0 ? (
            <Typography variant="body2">—</Typography>
          ) : (
            decision.approval_violations.map((v) => (
              <Chip key={v} label={v} size="small" color="warning" />
            ))
          )}
        </Stack>
      </Box>

      <Typography variant="body2" sx={{ mb: 2 }}>
        {decision.rationale}
      </Typography>

      <Divider sx={{ my: 1 }} />

      <Stack direction="row" spacing={1}>
        <Button
          startIcon={<CheckCircleIcon />}
          color="primary"
          variant="contained"
          size="small"
          disabled={busy}
          onClick={() => void onAction(approveIntent, "approve")}
        >
          Approve
        </Button>
        <Button
          startIcon={<CancelIcon />}
          color="error"
          variant="outlined"
          size="small"
          disabled={busy}
          onClick={() => void onAction(rejectIntent, "reject")}
        >
          Reject
        </Button>
        <Button
          startIcon={<ChangeCircleIcon />}
          color="secondary"
          variant="outlined"
          size="small"
          disabled={busy}
          onClick={() =>
            void onAction(requestAlternativeIntent, "request_alternative")
          }
        >
          Request alternative
        </Button>
      </Stack>
    </Paper>
  )
}

const POLL_INTERVAL_MS = 3000

const DecisionsPage = () => {
  const [items, setItems] = useState<ApprovalRequest[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  // Refs let the polling tick read latest state without re-creating the timer.
  const busyIdRef = useRef<string | null>(null)
  const inFlightRef = useRef<boolean>(false)

  const reload = useCallback(async (signal?: AbortSignal) => {
    if (inFlightRef.current) return
    inFlightRef.current = true
    setLoading(true)
    setError(null)
    try {
      setItems(await fetchApprovals(signal))
    } catch (e: unknown) {
      if (axios.isCancel(e)) return
      setError(e instanceof Error ? e.message : "failed to load approvals")
    } finally {
      setLoading(false)
      inFlightRef.current = false
    }
  }, [])

  useEffect(() => {
    busyIdRef.current = busyId
  }, [busyId])

  useEffect(() => {
    const ctrl = new AbortController()
    void reload(ctrl.signal)

    // Poll every POLL_INTERVAL_MS, skipping ticks when an action is mid-flight
    // so a user-driven approve/reject doesn't race with the background fetch.
    const id = window.setInterval(() => {
      if (busyIdRef.current !== null) return
      void reload()
    }, POLL_INTERVAL_MS)

    return () => {
      window.clearInterval(id)
      ctrl.abort()
    }
  }, [reload])

  const handleAction = async (
    intentId: string,
    fn: ActionFn,
    label: string,
  ) => {
    setBusyId(intentId)
    try {
      await fn(intentId)
      setInfo(`${label.replace("_", " ")}: ${intentId.slice(0, 24)}…`)
      await reload()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : `${label} failed`)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <Navigation />

      <Container maxWidth="md" sx={{ py: 3 }}>
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
              Decisions inbox
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ maxWidth: 720 }}
            >
              When the cognition layer recommends a plan that trips a policy
              listed in the intent's <code>human_approval_required_if</code>{" "}
              (e.g. high weather risk or above-budget price), it lands here and
              waits for a human. Approve to commit the recommended plan, reject
              to drop the intent, or request an alternative to send the request
              back through the engines and produce a different recommendation.
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Tooltip
              title={`Reading from ${getCognitionApiUrl()}/cognition/approvals`}
            >
              <Typography variant="caption" color="text.secondary">
                polling {POLL_INTERVAL_MS / 1000}s
              </Typography>
            </Tooltip>
            <Button
              startIcon={<RefreshIcon />}
              size="small"
              variant="outlined"
              onClick={() => void reload()}
              disabled={loading}
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
        {info ? (
          <Alert
            severity="success"
            sx={{ mb: 2 }}
            onClose={() => setInfo(null)}
          >
            {info}
          </Alert>
        ) : null}

        {loading && items.length === 0 ? (
          <CircularProgress />
        ) : items.length === 0 ? (
          <Box sx={{ textAlign: "center", py: 4 }}>
            {(() => {
              const url = stateImage("no_decisions")
              if (url) {
                return (
                  <Box
                    component="img"
                    src={url}
                    alt=""
                    sx={{
                      width: "100%",
                      maxWidth: 280,
                      height: "auto",
                      borderRadius: 1,
                      mb: 2,
                    }}
                  />
                )
              }
              const { Icon, color } = fruitIcon(null)
              return <Icon size={56} color={color} strokeWidth={1.5} />
            })()}
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              Nothing to approve right now.
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: "block", mt: 0.5 }}
            >
              Plans that trip a policy in{" "}
              <code>human_approval_required_if</code> show up here.
            </Typography>
          </Box>
        ) : (
          <Stack spacing={2}>
            {items.map((it) => (
              <ApprovalCard
                key={it.intent.intent_id}
                item={it}
                busy={busyId === it.intent.intent_id}
                onAction={(fn, label) =>
                  handleAction(it.intent.intent_id, fn, label)
                }
              />
            ))}
          </Stack>
        )}
      </Container>
    </Box>
  )
}

export default DecisionsPage
