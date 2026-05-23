# FOREX HARD_DISABLE — Rationale & Audit Trail

**Ticket:** M-007 (MASTER_ACTION_PLAN_2026-05-18.md F-003)
**Date enabled:** 2026-05-15
**Approved by:** User (verbal approval session 2026-05-15)
**Code location:** `audit_trail/quality_gates.py:7849-7854`

---

## Decision

FOREX emissions are globally disabled (`FOREX_HARD_DISABLE=1`, default ON) until the
carry-trade backtest passes acceptance criteria (see Re-enable Criteria below).

## Evidence That Triggered Disable

| Metric | Value | Source |
|--------|-------|--------|
| All-time WR (post-resolver-v2) | 46.4% | `asset_class_health` 2026-05-03T00:06Z |
| All-time PF (post-resolver-v2) | 0.27 | `asset_class_health` 2026-05-03T00:06Z |
| n (post-noise-filter) | 1,169 | `closed_picks.json` |
| LONG-direction WR | ~29% | `reports/forex_mutation_autopsy_20260515.md` |
| SHORT-direction PF | 8.11 (transient) | did not survive walk-forward |

PF=0.27 is catastrophically below Tier 2 floor (PF≥1.5). Every $1 risked returned $0.27.
The mutation protocol (`docs/MUTATION_THREE_AXIS_PROTOCOL.md`) was applied across
directional, symbol, and time-of-day axes — no viable sub-slice found with WR≥50% and PF≥1.5
on n≥30 clean picks.

## Mutation Protocol Results

- **Directional filter:** LONG is the dominant drag (WR≈29%). SHORT showed transient PF=8.11
  but n<10 and failed walk-forward validation (OOS WR 34% vs BT 61% — 27pp gap).
- **Symbol filter:** JPY-crosses blocked (M-063). EUR/USD, GBP/USD SHORT monitor proposed
  (M-007 F-007) but not yet validated with n≥30.
- **Time-of-day filter:** London + NY session gates partially wired (M-078 FOREX session gate,
  2026-05-17). Still in shadow mode; insufficient n to promote to enforce.

## Why Not Kill (Source: `docs/MUTATION_THREE_AXIS_PROTOCOL.md`)

HARD_DISABLE is a **temporary suspension**, not a permanent kill. The gate preserves
all FOREX signal infrastructure and stamping while zeroing emissions:
- Pickers still generate FOREX picks; they are rejected at `passes_active_gate` with reason
  `ns_e_forex_hard_disable`
- The FOREX session gate (M-078, shadow mode) continues accumulating data for future analysis
- All FOREX-related gates (M-078, M-063, M-065 White's RC/SPA) remain active for monitoring

## Re-enable Criteria (M-007)

Remove or override `FOREX_HARD_DISABLE=1` **only after ALL of these are satisfied**:

1. G10 carry-trade backtest (AUD/NZD long, JPY/CHF short) achieves **PF>1.0 / WR>45% / n≥30**
   on 10-year OOS data (task F-004, due 2026-05-28).
2. Trend overlay (carry in direction of 20DMA) verified to improve PF (task F-005, due 2026-05-30).
3. Walk-forward validation via `tools/edge_stability_harness.py` shows non-negative Sharpe
   over 3 OOS windows.
4. Explicit user approval to re-enable.

To re-enable: set `FOREX_HARD_DISABLE=0` in GitHub Secrets or `.env`.

## Exempt Paths

- `FOREX_COPYTRADER_ENABLE=1`: would bypass this gate for `source_system=multi_asset_copytrader`
  ONLY. **Do NOT enable** — all-time closed picks show WR=16.5%, PF=0.23, n=696.
  Prior erroneous WR=64.7% claim in code comments corrected 2026-05-17 (Session AT).

## References

- `reports/MASTER_ACTION_PLAN_2026-05-18.md` — F-001 through F-008
- `reports/forex_mutation_autopsy_20260515.md` — full directional/symbol axis analysis
- `reports/asset_class_90day_plan_FOREX_2026-05-15.md` — 30/60/90-day rescue plan
- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` — protocol applied before disable
- `audit_trail/quality_gates.py:7835-7854` — implementation
