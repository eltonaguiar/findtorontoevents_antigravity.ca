# Session Summary — /audit data-integrity + incident sweep

**Agent:** claude-opus-4-8 (desktop) · **Date:** 2026-05-31 · **Branch end:** main

This session started from "review the latest picks by asset class + fix the
`DATA INTEGRITY FAILURE — DO NOT TRADE` banner on findtorontoevents.ca/audit
ASAP" and expanded into a broader incident sweep.

## Shipped to main
| PR | Status | What |
|----|--------|------|
| **#210** | ✅ merged | Sign-based `pnl_integrity` (leverage-agnostic) + canonical-status writer → cleared the false DATA INTEGRITY banner |
| **#262** | open | Incident #34 (CI tests): 2 stale time-exit tests fixed + 2 operator-gated AB tests skipped |
| **#284** | ✅ merged | Incident #1: walk-forward gate for ML "edge" claims (`ml_enhanced_*` proven boost) |
| #207 | closed | superseded by #210 |

## 1. DATA INTEGRITY banner — FALSE alarm, cleared durably
The banner fires on `db_health.json` `any_red`. The live `--quick` set's RED
drivers were **check bugs, not corruption**:
- `pnl_integrity` (33%): recomputed PnL long-only + unleveraged → flagged every
  SHORT (sign flip) + every leveraged `quan_engine` perp (stored pnl already
  includes ~100-130× leverage). Rewrote to **SIGN consistency** (direction +
  leverage agnostic) → **0.54%** true mismatch (GREEN). Verified live.
- `open_bloat`: count_suspect bug (fixed by peer #208).
- The banner text in `dashboard_enhancements.js:668` is hardcoded — it always
  blames "ghost rows + forward-validator" regardless of which checks are red.
- Live `db_health.json` re-deployed GREEN from merged main (`any_red=False`).

## 2. Pick review — bug not on incidents.html, FIXED
**31 corrupted >100× price-ratio rows** in `trading_picks` (FETUSDT exit=$68,277
= BTC price leak) that faked `ml_enhanced_FETUSDT_1d_B` to 100% WR. Backed up +
neutralized. No new ones since 2026-05-29 (incident #48 code fix is holding).

## 3. Resolver (COMMODITY/FOREX) — backfill + 2 root-cause findings
- **Backfilled 23 `RESOLVE_FAILED` picks** via the real resolver's intrabar
  OHLC replay (correct percent units). Backed up.
- **Finding A:** non-crypto exit resolution is single-source on yfinance, which
  Yahoo IP-blocks on GH Actions → `RESOLVE_FAILED` phantoms starve
  COMMODITY/FOREX of resolved `n` (the "INSUFF-N" status). **Stooq is non-viable**
  (no CME futures). Durable fix = residential runner / OHLC cache (CI block not
  reproducible locally). Hand-off documented.
- **Finding B (NEW BUG):** `outcome_resolver._sync_resolved_to_mysql_trading_picks`
  writes `pnl_pct` as a **fraction** (no ×100) while the dashboard expects
  **percent** → non-crypto resolver outcomes understated 100×. Flagged for the
  resolver owner (needs care to avoid double-scaling crypto).

## 4. Incident #34 (CI tests) — partial, SAFE
17 pre-existing failures, mostly stale tests lagging intended behavior. PR #262
fixed the unambiguous subset (time-exit `WON/LOST`→`EXPIRED`; skipped
operator-gated AB-default). m098/m096/quality_gates deferred — production-gate
semantics, not blind-fixable.

## 5. Incident #41 (at_signal_outcomes SL_HIT+positive) — RESOLVED
"24%" claim was stale; live = 7/30,228 (0.023%). Fixed all 7 (2
cross-asset-corruption → neutralized, 5 profitable-exit mislabels → TP_HIT).
Backed up. INCIDENT_OVERALL #41 → RESOLVED.

## 6. Incident #1 (ML PF 99-1094 leakage) — gate landed (PR #284)
`ml_enhanced_*` were auto-credited as "proven winners" (+8..+15 boost) with no
out-of-sample validation. Added a walk-forward gate in `score_pick()`: the
proven boost is withheld unless `wf_verdict ∈ {ELITE,STRONG,VIABLE,PASS}` AND
`n≥100`; otherwise stamped `_ml_edge_status=UNVALIDATED_AWAITING_WF_N100`.
Default-on, env-reversible. 7 new tests + 51 existing green.

## Backups (ejaguiar1_backups)
- `trading_picks_corrupt_ratio_pre_neutralize_20260531`
- `trading_picks_resolve_failed_pre_backfill_20260531`
- `trading_picks_won_pre_canonical_20260531`
- `at_signal_outcomes_slhit_positive_pre_fix_20260531`

## Reports
- `peer_claude-audit-data-integrity-banner_result_2026-05-31.md`
- `peer_claude-noncrypto-resolver-yfinance-singlepoint_2026-05-31.md`
- `peer_claude-incident41-slhit-positive_result_2026-05-31.md`

## Still open (need operator/owner direction)
- #2 P0 COMMODITY strategy rebuild · #6 P0 EQUITY strategy rebuild (strategy R&D)
- #3 P1 meta_strategy explosion (needs STRATEGY_INVESTIGATION_BEFORE_KILL protocol)
- Resolver durable yfinance-CI fix + the pnl_pct fraction/percent unit bug (Finding B)
- #34 remainder (m098/m096/quality_gates) + #1 broader feature-pipeline leakage audit
