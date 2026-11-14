# 05 — Data Quality Remediation

**Date:** 2026-11-14 | **Priority:** P0 — prerequisite for any credible profitability claim

## 1. Observed Defects (evidence)

| Area | Finding | Impact |
|---|---|---|
| `data/live_picks.db` freshness | 129 picks, **all stale ~172 days** (`last_updated` 2026-05-25T20:50:25.xxx); ACTIVE(69)/OPEN(60) frozen | Performance/positions meaningless; hides losses |
| PnL integrity (DB) | **8 PnL sign contradictions** (`unrealized_pnl_pct` vs `metadata.pnl_pct`), **15 PnL calc mismatches** | Reported PnL untrustworthy |
| Asset coverage (DB) | 6 picks missing `asset_class`; no mutual funds; classes STOCKS 5, CRYPTO 101, FOREX 4, BOND 2, EQUITY 6, COMMODITY 5, UNKNOWN 6 | Misclassification, blind spots |
| Audit trail | `data/audit_trail.db` core tables empty (consensus_picks, feature_edge_snapshots, raw_picks, audit_events, filter_log, bt_backtest_trades = 0) | No lineage/auditability |
| Pick universe quality | 273 active / 16,771 closed (16,176 with pnl) but **~78.6% active_raw EXPIRED zombies** (pnl=0, unresolved) | Inflates counts, masks failure |
| Repricing (deepAI) | **81% open picks fake 0% P/L**; **losses understated ~10x** (claimed −106pp vs real −1,116pp) | System-level PnL fabrication/drift |
| Source fragmentation | `active_picks_bond.json` (6), `active_picks_etf.json` (16) not synced; `stocksunify2_active_picks.json` stale (2026-08-26); `active_picks.json` stale/empty (2026-05-29) | Inconsistent truth |
| Regime layer | ~0.25% coverage (21 with regime vs 8,538 closed without) | Regime-dependent strategies unauditable/mis-gated |
| Commodities/futures | **~98.4% futures zero-P/L bug** / unresolved pricing | Commodity performance invalid |
| Code defects | `sync_all_picks_to_mysql.py`: null/zero `entry_price`, `pnl *= 100` heuristic; `price_realism_check.py`: hardcoded `expected_2026_prices` | Systematic PnL/validation corruption |
| Operations | 7 workflows failing; Unified Audit Dashboard cancelled ~70% of hours | Stale/missing outputs |

## 2. Remediation Actions (ordered)

### P0 — Correctness of PnL & marks
1. **Fix sync logic (`sync_all_picks_to_mysql.py`)**
   - Reject/flag null or zero `entry_price`; never coerce to valid.
   - Remove/replace `pnl *= 100` heuristic with explicit unit handling (pct vs fraction) based on schema contract; add assertions.
   - Recompute PnL deterministically from entry/current/side/size with unit tests.
2. **Fix pricing realism (`price_realism_check.py`)**
   - Remove hardcoded `expected_2026_prices`; use live/reference feeds or bounded sanity checks per symbol/asset class.
3. **Reprice & reconcile**
   - Full repricing pass for open/active picks (ground-truth marks); persist corrected PnL and provenance.
   - Reconcile `unrealized_pnl_pct` vs `metadata.pnl_pct`; resolve 8 sign contradictions and 15 calc mismatches with a single canonical formula.
4. **Futures/commodities**
   - Fix zero-P/L/resolution path (contract mapping, roll/continuous series, mark source); backfill corrected outcomes.

### P0 — Freshness & lifecycle
5. **Unfreeze pipeline**
   - Restore scheduled updates; ensure `last_updated` advances; alert on staleness SLA (e.g. >24h for active).
6. **Zombie resolution**
   - Close/expire or reprice EXPIRED unresolved rows; stop generating pnl=0 placeholders; enforce terminal states with timestamps and exit prices.
7. **Canonical store & sync**
   - Unify JSON/DB sources; sync `active_picks_bond.json`, `active_picks_etf.json`, etc.; de-duplicate; define authoritative table/feed.
8. **Asset class hygiene**
   - Backfill missing `asset_class`; add/propagate `MUTUAL_FUND` where needed; validate mappings.

### P1 — Observability & ops
9. **Audit trail**
   - Re-enable writes to `audit_trail.db` (consensus/raw/features/filters/trades/events); add integrity checks.
10. **Regime layer**
   - Compute and persist regime per pick/bar; target >>0.25% coverage for closed/active where applicable.
11. **Workflow/dashboard stability**
   - Triage/fix 7 failing workflows; prevent mass cancellations; publish run health.

## 3. Verification / Exit Criteria
- [ ] 0 stale active picks beyond SLA; `last_updated` current.
- [ ] 0 sign contradictions, 0 calc mismatches on recompute; PnL units consistent and tested.
- [ ] No fake 0% P/L on positions with known mark moves; repriced sample matches exchange/reference marks within tolerance.
- [ ] Zombies reduced to justified set with explicit status/reason; no silent pnl=0 unresolved rows.
- [ ] Audit trail tables populated for new runs; regime coverage materially increased.
- [ ] CI/workflows green for data/publish jobs; dashboard reliably generated.
- [ ] Independent spot-check (e.g. deepAI-style repricing) agrees with stored PnL.

## 4. Ownership Notes
- Treat as engineering hotfix track; gate any “performance” reporting and strategy promotion on Sections 2–3 completion.
