# QUICK WINS — System-Level Proposed Fixes

**Audit Date:** 2026-11-14
**Worktree:** finpredict-v4
**Target:** `audits/2026-11-14/finpredict-v4_2026-11-14-1555/proposed_fixes/overall/QUICK_WINS.md`

---

## 1. TOP 5 QUICK WINS (< 1 day each)

These are surgical, high-leverage changes that require no architectural redesign and can be deployed within a single day. They address the most severe data-integrity and mislabeling issues.

### QW-1: Fix EXPIRED → WON Mislabeling in `claude_gainer_st`
**What:** The `claude_gainer_st` signal source incorrectly marks expired picks as WON. This single source contributes 91.7% of "Smart Picks CRYPTO" with a headline PF of 9.69 and WR 78.9%, yet the raw DB shows only 3 closed rows. The mislabeling is inflating the best-looking cohort in the entire system.

**File/Location:**
- `alpha_engine/claude_gainer_emitter.py` (or the module that writes `claude_gainer_st` outcomes)
- `audit_trail/universal_pick_resolver.py` — add an explicit guard: `if source == "claude_gainer_st" and status == "EXPIRED": force_status = "LOST"` until the emitter is fixed.

**Expected Impact:** Removes the single largest source of false-positive performance. Smart Picks CRYPTO PF will collapse from 9.69 to its true (likely sub-1.0) level, but the dashboard will finally be honest.

**Effort:** 2-4 hours.

---

### QW-2: Delete 22,947 Ghost Rows (MEMECOIN Duplicates)
**What:** `evidence_db_health.json` shows 22,947 ghost rows, overwhelmingly MEMECOIN duplicates (e.g., DOGEUSDT LONG × 3,569 identical rows, WIFUSDT SHORT × 2,763). These rows bloat the DB, distort aggregate statistics, and waste resolver cycles.

**File/Location:**
- `tools/db_freshness_check.py` — add a deduplication pass.
- SQL: `DELETE FROM trading_picks WHERE asset_class = 'MEMECOIN' AND id NOT IN (SELECT MIN(id) FROM trading_picks WHERE asset_class = 'MEMECOIN' GROUP BY symbol, direction, entry_price, strategy, DATE(created_at));`
- `alpha_engine/ghost_row_cleanup.py` (create if absent) — idempotent nightly cleanup job.

**Expected Impact:** Reduces DB size by ~16%, eliminates phantom n-counts in MEMECOIN/MEME class statistics, and speeds up resolver queries.

**Effort:** 3-6 hours.

---

### QW-3: Wire Up Orphan Backtests — Bond & ETF
**What:** BOND and ETF classes are marked `INSUFFICIENT_DATA` with n=26 and n=45 respectively. The dashboard shows 1,293 bond picks and 1,722 ETF picks, but they are orphaned — backtests exist (see `alpha_engine/bond_duration_rotation.py`, `alpha_engine/etf_scanner.py`) but their outputs never reach `trading_picks` or the resolver.

**File/Location:**
- `alpha_engine/bond_duration_rotation.py` — verify its `emit_pick()` call targets the correct DB table and asset_class label.
- `alpha_engine/etf_scanner.py` — same.
- `audit_trail/build_strategy_registry.py` — ensure BOND and ETF strategy families are registered with `production_wireup = True`.

**Expected Impact:** If the strategies have any edge, this surfaces it. If they don't, we get honest n ≥ 100 within weeks instead of months. Either outcome is valuable.

**Effort:** 4-8 hours.

---

### QW-4: Invert the ML Confidence Filter (Emergency Quarantine)
**What:** ML confidence is inverted — `conf >= 0.90` maps to 14.4% WR, while `conf 0.50–0.60` maps to 60.3% WR. The current `ml_gatekeeper/gatekeeper.py` likely uses confidence as a positive filter (high conf = high quality). This is actively destroying capital.

**File/Location:**
- `ml_gatekeeper/gatekeeper.py` — change the confidence gate from `conf >= threshold` to `conf <= threshold` (or flip the threshold range) as an emergency patch.
- `alpha_engine/money_ready_verdict.py` — the `_ml_enhanced_quarantine_n = 523` field shows a quarantine system exists; route all `conf >= 0.85` picks into it immediately.

**Expected Impact:** Stops the worst-performing picks from reaching production. WR of the remaining cohort should rise toward the 60% observed in the low-confidence bucket.

**Effort:** 2-3 hours.

---

### QW-5: Fix Frozen Prices in Dashboard PnL Calculation
**What:** Cross-market verification shows all active picks have prices frozen at or near `entry_price`, producing false 0% PnL readings (e.g., BTCUSDT SHORT should be +0.97%, shows 0.0%). This makes the dashboard worthless for real-time decision-making.

**File/Location:**
- `audit_dashboard/dashboard_enhancements.js` — the PnL calculation likely caches `current_price` and does not refetch.
- `alpha_engine/active_picks_sync.py` — ensure it pulls live prices from Binance/ Yahoo Finance every cycle and writes `current_price` back to `trading_picks`.
- `audit_trail/dashboard_generator.py` — verify it reads `current_price` from the DB, not from stale JSON.

**Expected Impact:** Dashboard PnL becomes real-time and accurate. Traders can trust the open-position panel.

**Effort:** 4-6 hours.

---

## 2. MEDIUM FIXES (1–3 days)

These require architectural or policy changes and touch multiple files.

### MF-1: Replace Daily-Resolution Labeling with Intrabar-First-Touch Truth
**What:** Daily-resolution labeling inflates PF by 2–3× versus honest intrabar first-touch replay. `evidence_intrabar_truth.json` shows this across all classes (e.g., CRYPTO daily PF 0.26 vs honest PF 0.92; ETF daily PF 1.84 vs honest PF 0.02). The current resolver uses daily OHLC, which ignores whether SL or TP was hit first inside the bar.

**File/Location:**
- `audit_trail/universal_pick_resolver.py` — refactor to use 1h (or 15m) intrabar data for first-touch resolution.
- `alpha_engine/intrabar_replay.py` (create) — standalone module that downloads 1m/5m/15m data for each symbol and replays TP/SL chronologically.
- `alpha_engine/money_ready_verdict.py` — change `sizing_source` default from `policy_clean` to `intrabar_truth` globally.

**Expected Impact:** Honest PF and WR across all classes. Many "winners" will flip to losers. The system will look worse on paper but will be tradable.

**Effort:** 2–3 days.

---

### MF-2: Bonferroni-Correct the Strategy Pipeline
**What:** 100+ strategies across 365 workflows guarantee false positives by chance. The audit shows 83 CRYPTO strategies tested, only 21 pass Bonferroni (threshold 0.0012), and the "top sleeves" are almost all single-source artifacts with absurd PFs (120.0, 56.7, 49.4). The dashboard surfaces these as "best performers."

**File/Location:**
- `alpha_engine/anti_overfit_gate.py` — enforce `bonferroni_threshold = 0.05 / n_strategies` before any strategy is eligible for the live dashboard.
- `alpha_engine/money_ready_verdict.py` — the FDR gate exists but is disabled (`_fdr_gate_enforce = false`); enable it.
- `audit_dashboard/blueprint_generator.py` — stop generating "Top Sleeves" pages for strategies with `n < 100` or `p > bonferroni_threshold`.

**Expected Impact:** Eliminates survivorship-bias artifacts. The "Top Sleeves" list will shrink from dozens to a handful of genuinely robust strategies.

**Effort:** 1–2 days.

---

### MF-3: Repair or Retire the Alpha Engine (Primary Scanner)
**What:** The Alpha Engine is dead — last 10 runs = 9 cancelled + 1 failure (~24h outage). This is why the dashboard shows 0 active picks despite 4,310 open picks in the backlog. Without the scanner, the system cannot generate new signals.

**File/Location:**
- `.github/workflows/alpha-engine.yml` (or equivalent) — inspect runner timeout, memory limits, and dependency installation steps.
- `alpha_engine/production_scanner.py` — add heartbeat logging every 60s so future failures are diagnosable.
- `alpha_engine/scanner.py` — wrap the main loop in a try/except with exponential backoff and Discord/Slack alerting on repeated failure.

**Expected Impact:** Restores the upstream signal pipeline. Without this, the dashboard remains an empty shell regardless of all other fixes.

**Effort:** 1–3 days (depends on root cause; may be a simple runner OOM or a deeper dependency breakage).

---

### MF-4: Resolve the 4,220 TIME_EXIT Limbo Picks
**What:** Only 301 / 4,820 TIME_EXIT picks are resolved (6.2%). The remaining 4,220 have been sitting in limbo for months, artificially inflating "open" counts and distorting duration-based metrics.

**File/Location:**
- `audit_trail/universal_pick_resolver.py` — add a batch resolver for `status = 'TIME_EXIT'` picks older than 48h.
- SQL: `UPDATE trading_picks SET status = 'LOST', exit_price = entry_price, pnl_pct = 0.0 WHERE status = 'TIME_EXIT' AND created_at < NOW() - INTERVAL 7 DAY;`
- `tools/db_freshness_check.py` — add a TIME_EXIT age alarm.

**Expected Impact:** Cleans up the open-pick backlog. Honest accounting of closed trades improves n-counts and removes stale positions from the active panel.

**Effort:** 4–8 hours.

---

### MF-5: Fix the PR #6 FOREX Block Bypass
**What:** FOREX strategies were explicitly blocked in PR #6, yet they still contribute to the `non_crypto_consensus` pipeline. The audit shows FOREX raw DB WR 83.3% but PF 0.108 — many small wins masking catastrophic losses. The bypass makes the block meaningless.

**File/Location:**
- `alpha_engine/non_crypto_consensus.py` — add an asset_class filter that excludes `FOREX` if `policy_blocked = true` in the registry.
- `audit_trail/blocked_registry.json` — verify FOREX strategies are listed with `block_consensus = true`.
- `copy_trader_intel/non_crypto_consensus.py` — same fix.

**Expected Impact:** Stops toxic FOREX signals from contaminating cross-asset consensus. Non-crypto consensus PF should rise as the 0.108-PF drain is removed.

**Effort:** 3–6 hours.

---

## 3. LONG-TERM FIXES (1–2 weeks)

These are fundamental redesigns. They require careful design, testing, and phased rollout.

### LF-1: Rebuild the Dashboard as a Single Source of Truth (SSOT)
**What:** The dashboard currently reads from a patchwork of stale JSON files (`dashboard_data.json` 26 days old, `picks_now.json` 7 days old, `picks_now_live_pnl.json` 45h old). It shows 0 active picks because the Alpha Engine is dead, yet cached data reveals thousands of stale picks. The dashboard is a freshly-painted empty shell sitting on a rotting foundation.

**File/Location:**
- `audit_dashboard/template.html` + `audit_dashboard/dashboard_enhancements.js` — redesign to query the live DB (or a read replica) every 60s instead of reading static JSON.
- `audit_trail/dashboard_generator.py` — convert from a batch JSON generator to a real-time API (`/api/v1/dashboard/live`).
- `alpha_engine/active_picks_sync.py` — ensure it is the **only** writer to the active-pick view.

**Expected Impact:** Eliminates stale-data artifacts. The dashboard becomes a trustworthy real-time view of system health.

**Effort:** 1–2 weeks.

---

### LF-2: Implement Walk-Forward Out-of-Sample (OOS) Gating
**What:** Current "walk-forward" ratios (`wf_oos_ratio`) are suspicious — FOREX shows IS PF 0.58 and OOS PF 1.67, which is the opposite of the expected decay. This suggests data leakage or look-ahead bias in the OOS partition. The gate is effectively a rubber stamp.

**File/Location:**
- `alpha_engine/walkforward_validator.py` — rewrite with strict purged-K-fold cross-validation (no overlapping bars between train and test).
- `alpha_engine/forward_validator.py` — add a "no future data" checksum that verifies the latest timestamp in the training set is strictly < the earliest timestamp in the test set.
- `alpha_engine/money_ready_verdict.py` — require `wf_oos_ratio < 1.2` (OOS must be within 20% of IS) and `oos_n >= 100`.

**Expected Impact:** Prevents overfitted strategies from passing validation. The OOS gate becomes a genuine filter rather than theater.

**Effort:** 1–2 weeks.

---

### LF-3: Retire the 365-Workflow Chaos and Consolidate to a Single Orchestrator
**What:** 365 workflows (361 active) create an unmaintainable blast radius. 28 failed their most recent run; 39 have ≥3 failures in the last 5 runs; 20 never ran; 19 last ran >90 days ago. This is not a trading system — it is a denial-of-service attack on GitHub Actions.

**File/Location:**
- `.github/workflows/` — retire all but 5 core workflows:
  1. `alpha-engine-orchestrator.yml` (the single scanner)
  2. `resolver-nightly.yml` (batch resolution)
  3. `db-freshness-guardian.yml` (already exists)
  4. `audit-dashboard.yml` (already exists, hourly cron)
  5. `ml-retrain-weekly.yml` (consolidated retraining)
- `alpha_engine/orchestrator.py` (create) — a single Python orchestrator that schedules strategy runs, handles retries, and emits unified logs.

**Expected Impact:** Reduces CI noise by 95%. Failures become diagnosable. Compute costs drop dramatically.

**Effort:** 1–2 weeks.

---

### LF-4: Build a Honest Closed-Ledger Benchmark with Random-Entry Nulls
**What:** The current benchmark proof (`audit_dashboard/benchmark_proof.html`) is read-only and does not validate picks. The system needs a true null model: for every real pick, generate a matched random-entry pick (same asset, same direction, random timestamp within the same regime) and compare performance. This is the only way to prove the strategies have edge beyond luck.

**File/Location:**
- `alpha_engine/benchmark_closed_ledger.py` — extend with random-entry MC timing (same-asset, direction-aware nulls).
- `tests/test_benchmark_closed_ledger.py` — add a coin-flip MC gate (already partially implemented; extend to all asset classes).
- `audit_dashboard/data/benchmark_ledger_proof.json` — regenerate with the new null model.

**Expected Impact:** Provides an honest, statistically rigorous answer to "Do we have edge?" If real picks do not beat random-entry nulls by a significant margin (p < 0.05), the system is not tradable.

**Effort:** 1 week.

---

## 4. RECOMMENDED PRIORITY ORDER

### Phase 1: Stop the Bleeding (Days 1–3)
1. **QW-4** — Invert ML confidence filter (emergency quarantine of the worst-performing cohort).
2. **QW-1** — Fix EXPIRED → WON mislabeling (removes the biggest source of false performance).
3. **MF-3** — Repair Alpha Engine (without this, no new picks flow; the dashboard stays empty).
4. **QW-5** — Fix frozen dashboard prices (restores real-time PnL trust).

### Phase 2: Clean the Data (Days 4–7)
5. **QW-2** — Delete ghost rows (reduces DB bloat and false n-counts).
6. **MF-4** — Resolve TIME_EXIT limbo (honest accounting of closed trades).
7. **MF-5** — Fix FOREX block bypass (stops toxic consensus contamination).
8. **QW-3** — Wire up orphan backtests (surfaces honest ETF/BOND data).

### Phase 3: Rebuild Integrity (Weeks 2–4)
9. **MF-1** — Intrabar-first-touch truth (honest PF/WR across all classes).
10. **MF-2** — Bonferroni correction (eliminates survivorship-bias artifacts).
11. **LF-1** — SSOT dashboard (real-time, trustworthy view).
12. **LF-4** — Random-entry benchmark (proves or disproves genuine edge).

### Phase 4: System Redesign (Months 2–3)
13. **LF-2** — Walk-forward OOS gating (prevents future overfitting).
14. **LF-3** — Workflow consolidation (reduces operational chaos).

---

## 5. HONEST REALITY CHECK

### What Is the Probability This System Becomes Genuinely Profitable?

**Honest estimate: 5–15%.**

The system is not "almost there." It is a monument to multiple-testing bias, data-quality rot, and architectural sprawl. Here is why the probability is low:

1. **No asset class passes money-ready gates.** Not one. The best-performing class (COMMODITY) has PF 1.03 — barely breakeven before costs.
2. **The "edge" evaporates under honest labeling.** Intrabar truth collapses PF by 2–3×. The best-looking strategies are single-source artifacts with n < 50.
3. **ML confidence is inverted.** The system has learned the exact wrong thing. This is not a tuning issue; it suggests fundamental feature leakage or label corruption.
4. **The Alpha Engine is dead.** The primary signal generator has been down for ~24 hours. Even if restarted, there is no evidence its outputs are positive-EV.
5. **Ghost rows and stale data are symptoms, not root causes.** They indicate years of technical debt and no data-governance culture.

### What Would Change the Odds?

- **Discovering one genuinely robust sub-strategy** with intrabar-true PF > 1.5, WR > 55%, n > 200, and a passing random-entry benchmark. If such a strategy exists in the 100+ tested, it has been buried under noise.
- **A complete rebuild of the ML pipeline** with proper train/test splits, feature-engineering discipline, and label integrity.
- **Dramatic scope reduction** — pick the 1–2 asset classes with the most data and kill everything else. 100+ strategies is not diversification; it is a statistical death spiral.

### Minimum Viable Evidence Threshold

Before a single dollar of real capital is deployed, the system must demonstrate **ALL** of the following for **at least one asset class** over a **minimum 90-day paper-trading period**:

| Gate | Threshold | Rationale |
|------|-----------|-----------|
| **Intrabar-true PF** | > 1.5 | Daily labeling is fraud. Intrabar first-touch is the only honest metric. |
| **Intrabar-true WR** | > 52% | Below 50% is guaranteed loss after costs. 52% is the bare minimum. |
| **n (closed trades)** | ≥ 200 | Statistical significance. 100 is too small; 200 begins to be convincing. |
| **Random-entry benchmark** | Beat null at p < 0.05 | Proves edge is real, not luck. |
| **Walk-forward OOS PF** | Within 15% of IS PF | Proves no look-ahead bias or overfitting. |
| **Net expectancy after costs** | > 0 | Includes slippage, spread, and financing. |
| **Max drawdown** | < 20% | Survivable for a retail account. |
| **ML confidence correlation** | Positive (high conf → high WR) | Currently inverted. Must be fixed and verified. |

**Until all eight gates are passed simultaneously for 90 consecutive days, this system is a research project, not a trading system.**

---

*Prepared by: Kilo (finpredict-v4 audit worktree)*
*Date: 2026-11-14*
