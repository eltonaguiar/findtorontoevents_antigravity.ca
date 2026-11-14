# MASTER PLAN — Prediction-System Remediation (2026-11-14)

Synthesis of 7 per-asset-class consolidated reviews (`inputs/01..07`) drawn from 5 on-host peer audits (finpredict v1/v2/v3/v4 + ML childlike-airport). Consolidated by `finpredict` (me). Every `file:line` was line-verified by the peer that authored it.

## Verdict (unanimous, 5/5 peers)

**FAIL — not money-ready, not statistically sound.** WR 41.8% / PF 0.94 / Sharpe −1.31 / compounded −99%; policy-clean PF 0.2657; 0/9 classes money-ready; 658 strategies → E[false-positives]≈33 at p=5%. The honest intrabar/raw-DB truth is net-negative. This is a **data-integrity + multiple-testing** failure, not a strategy-tuning failure.

## Guiding principles

1. **Truth before trades.** Phase 0 changes labels/numbers only; no resolver/signal change.
2. **Quarantine, never delete.** Zombies/ghosts/dupes are tagged + archived, not destroyed.
3. **No fabricated marks.** `pnl_pct = null` (or `UNQUOTED`) when there is no live quote; never `current_price = entry_price` backfill, never `0.00%` as a claim.
4. **Flag + rollback.** Every behavior change ships with an env flag default-on and a one-line rollback.
5. **Veto list is binding** (below). Destructive SQL and policy reversals are out of scope.

## Phase 0 — CI unblock + truth contract (≤1 week, no trading change)

Do in this order (each independently revertible):

| # | Fix | Target (`file:line`) | Effort/Risk | Peers |
|---|---|---|---|---|
| P0-1 | Guard FX direction bucket `KeyError: 'LONG'` (93 fails/24h) | `alpha_engine/scanner.py:2937-2942` | S / Low | v2, infra |
| P0-2 | Fix `summary_picks` WR>100% (7 classes) — single terminal population + clamp+assert | `tools/sync_summary_picks_json.py:63-65,161` | S / Low | v2, all |
| P0-3 | Run real Python 3.11: remove `update-environment:false` in failing cluster + assert interpreter | `.github/workflows/{signal_tracking,alpha-engine-fast,forward-test-new-strategies,autonomous_trading,copy-trader-intelligence}.yml` | S / Low | v2, infra |
| P0-4 | Space audit-dashboard cron to ≥p95 runtime (84.5m) | `.github/workflows/audit-dashboard.yml:5` | S / Low | v2 |
| P0-5 | Stop `None→0.0` coercion (XRP entry 0.0) + entry-price sanity gate | `alpha_engine/prediction_market_consensus.py:589-591`; `audit_trail/quality_gates.py:9082` | S / Low-Med | v1, v2, v3, crypto |
| P0-6 | Quote-provenance contract: stamp `quote_status/quote_source/quote_at/quote_age_hours`; `pnl_pct=null` when unquoted; wire Binance/yfinance re-quote | `audit_trail/dashboard_generator.py:1618-1846, 1739-1755, 1179, 1480` | M / Low | all 5 |
| P0-7 | Render `UNQUOTED/STALE/LAST CLOSE` badges (kill green live-dot + `0.00%` + `FLAT`) | `audit_dashboard/template.html:8883-8905, 9134-9145, 9222-9227` | S / Low | v1, v2, v3, crypto, equity |
| P0-8 | Honesty metrics: `n` + Wilson 95% CI + excluded counts + `INSUFFICIENT` at `forward_trades==0` + outlier-clamp count | `audit_trail/dashboard_generator.py` summary block; `dashboard_enhancements.js` | S / Low | v1, v2 |
| P0-9 | Kill vacuous PASS: `activeCount==0 or resolved_n<30 → INSUFFICIENT_DATA` + `NOT_BUILT` status | `audit_trail/dashboard_generator.py:6824-6826`; `template.html:4946` | S / Low | v2, bond |
| P0-10 | Dedup: ID key + economic key `(symbol,strategy,direction,entry_time,entry_price)`; quarantine inverse-mutation zombies (2,267) + EXPIRED from default view | `audit_trail/dashboard_generator.py:9831-9836, 9538, 17481-17485` | M / Low-Med | v2, v3, all |
| P0-11 | Sidecar freshness manifest + hide-if-stale (10+ sidecars 79–245d dead) | `dashboard_freshness.js`; `tools/deploy_audit_files.py:38,59` | M / Low | v1, v2, v4 |
| P0-12 | Security: remove tracked Google API keys, gitignore `dbpasses.txt`, secret-scan CI | `STOCKSUNIFY/*/stock-api-keys.ts` (×2); `MOVIESHOWS2/scroll-fix.js` | S / Low | v2 |

Per-class Phase-0 details (ISO timestamps for futures, BOND price trio + FRED re-enable, FOREX PR#6 enforce + threshold 1→2, COMMODITY `canonical_asset_class=FUTURES` + crypto-proxy labeling, MUTUAL FUNDS `NOT_BUILT` de-advertise) are in `inputs/01..07` and are folded into the above or scheduled in Phase 1.

## Phase 1 — data-consistency gates (1–2 weeks)

- Single canonical BOND emitter; FOREX retire-vs-restart decision; FUTURES retire-vs-restart decision.
- Ledger-level ID integrity (248 dup groups, 55 cross-ledger conflicts) → `id_conflicts.jsonl`.
- Class-health contract (`status`, `activeRawCount`, `data_coverage`) + CI assertions (`tests/test_dashboard_payload_contract.py`).
- `resolution_kind` split (`price_resolved`/`clock_expired`/`never_priced`).
- DB/SQLite divergence: refresh-or-retire `live_picks.db` (172d), `audit_trail.db` (empty), reconcile 3 data stores.
- Reconcile official surfaces (CRYPTO PF 0.29 registry vs 0.95 money-ready; EQUITY n=8 vs 461).

## Phase 2 — resolver/signal (gated, ≥2 weeks, behind flags)

- Server quote pipeline v2 (re-quote every OPEN row, persist `quote_snapshot.json`, fail build <80% coverage).
- BOND promotion gate + 60-day shadow accrual (documented bypass) — returns `BLOCKED` today.
- COMMODITY/FUTURES real feed (never crypto proxies) before any unblock.
- Fix inverted-ML-confidence data bug (code is sound).

## Phase 3 — statistical re-validation (do NOT start until 0+1 green)

- Re-run anti-overfit on the **policy-clean, time-ordered, deduped** ledger with proper Bonferroni/Holm; PBO with T≥1000 (not 21); Reality Check.
- Kill/keep decision per strategy with multiple-testing correction; no sizing until a class clears n≥100 / WR≥50% / PF≥1.5 with CI and single-source-share ≤40%.

## VETO list (binding — do NOT implement)

- v4 `proposed_fixes/**` destructive SQL: `DELETE` ghost rows, `UPDATE TIME_EXIT→LOST, pnl_pct=0.0`, `EXPIRED_FORCE` mass rewrite.
- `current_price = entry_price` backfill (creates the exact frozen-price artifact being fixed).
- Add `MUTUAL_FUND` to canonical classes before an emitter exists; build a live MF pick class (monthly NAV has no intraday mark).
- Invert the ML gate; unblock FUTURES/COMMODITY without a real feed.
- Re-enable audit-dashboard `push:` trigger (2026-05-19 cancel cascade).
- Wire `alpha_engine/forced_resolution.py` for live resolution (research-only, survivorship bias).

## Implementation order for THIS session

1. P0-1 (scanner KeyError) → 2. P0-2 (summary_picks WR) → 3. P0-5 (None→0.0) — pure-Python, self-contained, py_compile + targeted pytest. Then P0-3/P0-4 (workflow YAML). Then P0-6/P0-7/P0-8/P0-9 (generator/template). P0-10/P0-11/P0-12 after the generator contract is stable.

## Verification

- `python -c "import py_compile; py_compile.compile(<file>, doraise=True)"` on every edited Python file.
- Targeted pytest: `tests/test_summary_picks_win_rate.py`, `tests/test_dedup_cross_source.py`, `tests/test_asset_class_status_labels.py`, `tests/test_price_coverage_gate.py` (new), plus existing `tests/test_dashboard_payload_contract.py`.
- Post-build invariants (see v2 `acceptance_tests.md`): no `win_rate_pct>100`; no active row `0.00%` without `quote_status`; BOND `thresholdPass=False`; `unique(ids)==len(rows)`.
