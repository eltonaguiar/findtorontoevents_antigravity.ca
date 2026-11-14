# PEER REVIEW — finpredict-v4 Audit Archive

**Reviewed:** 2026-11-14T17:55Z
**Archive:** `audits/2026-11-14/finpredict-v4_2026-11-14-1555/`
**Role:** Read-only peer review of v4's output.

---

## 1. Inventory

**Files present (17):**
- `INDEX.md` (consolidated), `actions_health_report.md`, `dashboard_data_report.md`, `dashboard_metrics_sources.md`, `crypto_deep_dive.md`, `noncrypto_deep_dive.md`, `forex_deep_dive.md`, `market_crossref_report.md`
- `peer_review/2026-11-14-ML-AUDIT-childlike-airport.md` + `peer_review/PEER_REVIEW_INTEGRATION.md`
- Evidence: `evidence_db_health.json`, `evidence_intrabar_truth.json`, `evidence_money_ready_verdict.json`, `evidence_pick_summary_stats.json`

**proposed_fixes/ subfolders (9 exist):**
| Folder | QUICK_WINS.md | Content |
|---|---|---|
| overall | YES | system-level (QW1-5/MF1-5/LF1-4) |
| infra | YES | CI/GHA/MySQL/JSON freshness |
| crypto | YES | live fetcher, 5x PF, zombies |
| equity | YES | EQUITY+ETF+BOND |
| forex | YES | blacklist/hard-disable/dedup |
| commodity | YES | COMMODITY+FUTURES |
| bond | **EMPTY** | covered inside equity doc |
| etf | **EMPTY** | covered inside equity doc |
| futures | **EMPTY** | covered inside commodity doc |

Empty `bond/etf/futures` folders: NOT FOUND as standalone; their content is merged into equity/commodity docs.

**Evidence freshness:**
- `evidence_db_health.json` generated 2026-11-14T14:13Z (today) — ghost_rows total 22,947, top DOGEUSDT LONG n=3,569.
- `evidence_intrabar_truth.json` 14:25Z; `evidence_money_ready_verdict.json` 14:29Z (today).
- `evidence_pick_summary_stats.json` **generated 2026-05-25T05:46Z (≈173 days old)** — STALE, reused, not regenerated for this audit.

---

## 2. Key Claims + Numbers

**Actions health (actions_health_report.md):** 365 workflows (361 active/4 disabled); 28 failed last run; 39 with ≥3 failures/cancels in last 5; 20 never ran; 19 last ran >90d. Alpha Engine `ALPHA ENGINE - Live Autonomous Scanner`: last 10 runs = 9 cancelled + 1 failure (~24h outage).

**Per-class honest (intrabar) verdicts (INDEX.md / dashboard_data_report.md §2.2):**
- CRYPTO: WR 35.9%, PF 0.92, n=3,705 → FAIL
- EQUITY: WR 59.0/59.2%, PF 0.93, n=249-250 → FAIL
- FOREX: WR 32.2%, PF 0.66, n=612 → FAIL
- COMMODITY: WR 40.2%, PF 1.026, n=229 → FAIL (WATCH)
- ETF: WR 2.2-2.3%, PF 0.022, n=44 → INSUFFICIENT_N
- BOND: WR 7.7%, PF 0.391, n=26 → INSUFFICIENT_N
- FUTURES: WR 42.3%, PF 1.094, n=52 → INSUFFICIENT_N
- MEMECOIN: WR 29.4%, PF 0.661, n=102 → FAIL
- **0/9 classes money-ready.**

**Market crossref (market_crossref_report.md):** NEARUSDT SHORT entry 1.326 vs live 3.224 = **+143% discrepancy**, SL 1.37 breached, still OPEN. All 5 AI-challenge crypto picks >8 months old, `pnl_pct=0.0`, still OPEN. AMZN/BRK.B/IWM/GLD OPEN ~5mo far past TP. MSFT resolved WIN. `picks_now` screener prices (HDV/SCHD/DBC/PLTR/GOOGL) match live exactly.

**Crypto (crypto_deep_dive.md):** 20 total active picks system-wide; 3 crypto, all SHORT, all `_backfilled:true`, all `forward_validated=false`. NEAR PnL understated 2.74% vs live 3.46%; XRP/BTC frozen at entry show 0.0% vs live +1.46%/+0.97%. RSI5070 condition net PF 1.113, CI LB 0.916, fails promotion gate.

**Forex (forex_deep_dive.md):** USDCAD=X & NZDUSD=X both show `current≈entry` at -0.0% while live yields +0.061%/+0.0385%. PR #6 "all blocked" claim **bypassed** via `non_crypto_consensus`; `forex_rsi2_mean_reversion` blacklisted yet still votes in consensus. FX aggregate PF 0.48, WR 36.6%, PnL -27.78%.

**Dashboard metrics (dashboard_metrics_sources.md):** active-picks table EMPTY (0); all metric columns empty. `db_freshness.json` 175d old; `hourly_update_last_run.json` 44.6h; `feature_signals_latest.json` 79.5h; `hyro_quan_bridge.json` ~46h. Copy Trader + Claude Gainer pipelines LIVE but output orphaned.

**Proposed fixes:** overall QW-1 EXPIRED→WON mislabel (claude_gainer_st 91.7% of Smart Picks PF 9.69 on 3 closed rows); QW-2 delete 22,947 ghost rows; QW-4 invert ML confidence filter; MF-3 repair Alpha Engine; MF-1 intrabar first-touch; MF-2 Bonferroni; MF-4 resolve 4,220 TIME_EXIT. Infra QW-1 cancel-in-progress→false; QW-2 surface `|| non-fatal` (58 instances); MF-2 boot intrabar `at_signal_outcomes`. Crypto/equity/forex/commodity docs give file-level locations + effort.

---

## 3. Strengths

- **Live price verification** against Binance + Yahoo for crypto/forex/screener — the strongest methodical contribution (frozen-price proof is reproducible).
- **Peer integration** brought SQLite `live_picks.db` (128/129 stale, 8 PnL sign contradictions), empty `audit_trail.db`, and empty `consensus_active_picks.json` into the picture — three-layer (MySQL/JSON/SQLite) divergence is new.
- **File-level fix proposals** with effort estimates + priority phases (P0-P3) — directly actionable for a master plan.
- **Honest verdict** (NOT money-ready; survivorship/multiple-testing artifact framing) with concrete numeric thresholds and a 90-day evidence gate.

---

## 4. Weaknesses / Gaps

- **STALE re-used evidence:** `evidence_pick_summary_stats.json` is dated 2026-05-25 (~173d) yet treated as current. Any claim sourced from it (e.g., Smart Picks PF 9.69 / 91.7% claude_gainer_st) reflects May data, not Nov 14.
- **Two conflicting FOREX PF figures within v4:** dashboard recent_closed PF 2.02 vs raw DB PF 0.108 (dashboard_data_report §4.3) vs honest intrabar PF 0.66 (INDEX). Needs reconciliation/relabel before master plan.
- **June-vs-live confusion:** several "live" claims rest on May/June artifacts (`db_freshness.json` May; `picks_now.json` Nov-12; `dashboard_data.json` Oct-19). The audit acknowledges this but some conclusions mix layers.
- **ML-confidence inversion conflicts with peer:** childlike-airport found `ml_ranker_fixed.py`/`ml_gatekeeper.py` *mathematically sound*; v4's "invert the filter" fix should be relabeled a data/label bug, not a model inversion.
- **Empty fix folders** for bond/etf/futures (content merged elsewhere) — organizational gap, not content gap.
- **Unverified code locations** in many fixes (e.g., `ml_gatekeeper/gatekeeper.py` line refs) are best-effort guesses.
- Crypto active picks served from a separate endpoint "not located" — v4 itself flags this unverified corner. AI-tournament pipeline gated off, unverifiable.

---

## 5. Recommended Merge / Adjust for Master Plan

**Adopt (P0):**
1. Alpha Engine cancel/cascade fix (infra QW-1 / overall MF-3) — root cause of empty dashboard.
2. PnL sign bug fix (peer: 8 rows) + frozen-price fix (crypto QW-1 / overall QW-5).
3. Refresh 172-day-stale SQLite picks; purge 22,947 ghost rows (overall QW-2 / infra QW-5).
4. Resolve 4,220 TIME_EXIT limbo (overall MF-4 / infra MF-1).
5. FOREX block enforcement — honor `BLACKLISTED_STRATEGIES` + `FOREX_HARD_DISABLE` in `non_crypto_consensus` (forex QW-1/QW-2, overall MF-5).
6. Intrabar first-touch default for money-ready (overall MF-1) — supported by evidence_intrabar_truth.

**Adopt with caution / relabel:**
- "Invert ML confidence" → relabel as **data/label bug** (per peer finding code is sound); fix data not model.
- `evidence_pick_summary_stats.json` claims must be re-verified from current data before adoption.
- Reconcile the 3 FOREX PF figures (dashboard vs raw vs honest) and label each.

**Drop / de-scope:**
- Standalone bond/etf/futures folders (empty) — merge into equity+commodity tracks in master plan.
- Clad "metric inflation" headlines that mix May evidence with Nov audit — re-run on current payloads.

**Conflicts with other peers:** v4's inverted-confidence finding conflicts with childlike-airport's "ML code sound" — reconcile as schema/label bug. The 5x crypto PF inflation (dashboard 1.80 vs raw 0.37) is a data-integrity claim unique to v4 and should be validated against the fresh DB before merging.

**Net:** v4 is the strongest *live-market-verification* and *fix-prioritization* contributor. Its systemic verdict (0/9 money-ready; not profitable; artifact-driven) is well-supported. Carry forward its P0 fixes; re-verify its stale-evidence-derived numbers; resolve FOREX PF ambiguity and the ML-confidence contradiction before final synthesis.
