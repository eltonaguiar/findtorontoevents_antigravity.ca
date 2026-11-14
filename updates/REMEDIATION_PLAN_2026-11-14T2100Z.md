# Remediation Plan: Profitable, Statistically Sound Pick Pipeline
**Repo:** eltonaguiar/findtorontoevents_antigravity.ca  
**Branch:** wiring  
**Generated:** 2026-11-14T21:00:00Z (date-time stamped)  
**Author:** Quantitative auditor / investment manager (opencode)  
**Status:** Draft for review — not yet committed to main

---

## 1. Executive Summary (verdict: FAIL)

The prediction system across stocks, crypto, forex, bonds, ETFs, and mutual funds is **not genuinely profitable and not statistically sound**.

Key findings (all sourced from repo data files, not guessed):

| Asset class | Realized WR (decisive) | Expectancy | PF | MDD | Money-ready verdict |
|-------------|------------------------|------------|----|-----|---------------------|
| CRYPTO | 45.7% (n=2,070) | −5.86% (CI [−4.96%, −4.38%]) | 0.92 | ~100% | NOT_READY |
| EQUITY | 48.2% (n=690) | +0.86% (CI crosses 0) | 0.93 | ~100% | NOT_READY |
| FOREX | 40.3% (n=199) | −0.21% | 0.66 | 82% | NOT_READY |
| ETF | 44.3% (n=503) | +0.08% | 0.02 | n/a | INSUFFICIENT_DATA |
| BOND | 33.3% (n=28) | −0.23% | 0.39 | n/a | INSUFFICIENT_DATA |
| COMMODITY | 50.0% (n=9) | +0.03% | 1.03 | 18% | WATCH |
| FUTURES | 0.0% (n=1) | −0.47% | n/a | n/a | INSUFFICIENT_DATA |
| MUTUAL FUND | n/a | n/a | n/a | n/a | INSUFFICIENT_DATA |
| MEME | 10.0% (n=10) | −6.58% | 0.02 | 49% | INSUFFICIENT_DATA |

- **0 of 9 asset classes** meet Tier-2 money-ready criteria (`money_ready_verdict.json`: `money_ready: []`).
- CRYPCO expectancy is **statistically significantly negative** (bootstrap CI does not cross zero).
- The dashboard's "Smart Picks" CRYPTO cohort (WR 78.93%, PF 9.69) is an artifact: dominated by one strategy (70%), one source (91.7%), and EXPIRED picks mislabeled as WON. DB-side raw `at_raw_picks` 90d tells the opposite story: WR 39.38%, PF 0.371.
- **Multiple testing:** 84 crypto strategies tested with PBO=0 / SPA p=0 — classic look-elsewhere artifact. Fewer than 2 strategies with n≥20 in most classes means PBO/SPA/FDR cannot even run.
- **Direction/regime mismatch:** curated active picks (`picks_now.json`) are 100% LONG-biased (25/25) in a declared RISK_OFF regime. CRYPTO LONG is explicitly blocked in config as "the largest PnL leak in book" (WR 30.1%, Σ−503%).
- **Survivorship bias:** EXPIRED/unresolved picks counted as WON; 54 closed picks frozen at pnl_pct=0%.
- **Data frozen/stale:** `recent_closed.json` is 0 bytes; `db_freshness.json` is ~5.5 months stale (RED); `at_signal_outcomes` RED (~80 days stale); hyrotrader journal has 0 trades; no closed picks in ~26 days.
- **Actions health:** 365 workflows; 30 failures, 11 cancelled, 20 never-run, 4 disabled; `audit-dashboard.yml` itself was in_progress at snapshot time. `CI Tests` failing.

**Conclusion:** No asset class clears a statistically sound bar for real-money allocation. The few positive readings are artifacts of running so many strategies that some win by chance, amplified by single-source concentration, EXPIRED→WON mislabeling, and long-bias regime mismatch.

---

## 2. Root Causes (with file:line evidence)

### A. Outcome resolver mislabels EXPIRED as WON (survivorship bias)
- `tools/relabel_crypto_expired.py` — relabels EXPIRED/TIME_EXIT/MAX_HOLD picks that were tagged WON/LOST/CLOSED/FLAT.
- `tools/resolver_hygiene_check.py:25` — `_TERMINAL_NONWIN = {"EXPIRED",...}`; flags "EXPIRED status tagged WON, or pnl sign disagreeing with outcome".
- `tests/test_pick_data_quality_gate.py:24` — asserts EXPIRED→WON mislabel fails the gate.
- `tools/audit_pick_funnel/build_recency_summary.py:118-129` — `EXPIRED_pos_pnl_share > 55%` → caveat "likely_mislabeled_WON".
- `reports/SMOKING_GUN_ASSET_CLASS_2026_04_30.md:95` — outcome-resolver bug at `alpha_engine/outcome_resolver.py:97` (PNL_WIN_THRESHOLD=0.00001 = 0.1bp) mislabeled ~1,700 non-crypto picks historically; converted spread noise into "WIN" labels for FOREX/COMMODITY.
- `money_ready_verdict.py:214-221` — CRYPTO Smart-Picks 78.9% WR cell driven by single source `claude_gainer_st` (91.7%) which EXPIRED→WON mislabeled.

### B. Multiple testing / overfitting not corrected
- `alpha_engine/walkforward_validator.py` — rolling train/test + Sharpe + bootstrap CI + t-test; **no PBO, no SPA, no FDR**.
- `alpha_engine/forward_validator.py:333-397` — White's Reality Check only (multiple hypothesis across strategies); no PBO/SPA/FDR beyond that.
- `money_ready_verdict.py:894` (`_pbo_gate`), `:947` (`_spa_gate`), `:1004` (`_fdr_gate`) — PBO/SPA/FDR gates exist but require ≥2 strategies with n≥20 and ≥5 strategies for PBO power; most classes have <2, so gates return `ok=None` (unenforced).
- `money_ready_verdict.py:164` `MIN_STRATEGIES_FOR_PBO=5`, `:166` `MIN_N_STRATEGY=20`, `:178` `FDR_Q=0.10`.
- Default enforcement OFF: `_FDR_GATE_ENFORCE` OFF (env `MONEY_READY_FDR_GATE`), `_SINGLE_SOURCE_GATE_ENFORCE` OFF (env `MONEY_READY_SINGLE_SOURCE_GATE`).

### C. Single-source concentration
- `money_ready_verdict.py:248` `MAX_SOURCE_CONCENTRATION=0.40`; `:202` `MAX_SYMBOL_CONCENTRATION=0.60`. Applied in `_verdict` (:1160-1170) — caps verdict at WATCH but does not block.
- CRYPCO top-source share 0.9847; FOREX 0.8597; EQUITY 1.0; ETF 1.0 — all far above caps.
- CRYPCO "top sleeves" (ADX Trend Confirmation n=213 WR 97.18%, mega_mut_macd_rsi_m084 n=124 WR 90.32%, etc.) are single-source, flagged "artifact edge".

### D. Data pipeline frozen / stale
- `tools/db_freshness_check.py:36-61` — thresholds: live_picks GREEN<120min, signal_outcomes GREEN<360min, backtests GREEN<2880min.
- `audit_dashboard/data/db_freshness.json` — generated 2026-05-23; `signal_outcomes` RED (115,782 min stale, last resolved 2026-03-04, n_resolved_today=0); `backtests` YELLOW (no timestamp column, n_total=0).
- `recent_closed.json` = 0 bytes (no script writes it; unrelated to `recent_closed_array.json`).
- `audit_dashboard/data/hyrotrader_journal.json` — `trades: []`; `hyrotrader_picks.json` — 7 `pending_entry` with null prices; account snapshot `last_session_date: 2026-04-08`, equity −1.41%.
- No closed picks since 2026-10-19 (~26 days).

### E. Price refresh broken
- `.github/workflows/daily-price-refresh.yml` — hits `fetch_prices.php` which returns HTTP 404 (dead since 2026-04-29).
- `.github/workflows/daily-prices-yf-refresh.yml` (yfinance replacement) — also in FAILURE per CI.
- `tools/live_pnl_tracker.py` writes `picks_now_live_pnl.json` hourly (:48) via yfinance+Binance; works but source data (picks_now_tracker MySQL) may be stale.

---

## 3. Remediation Plan — 5 Stages

### Stage 1 — Data Hygiene (fix frozen/stale data; prerequisite for all downstream gates)
Goal: restore a trustworthy, current closed-picks ledger with correct outcomes.

1. **Fix `recent_closed.json`** (0 bytes). Either remove or regenerate from `dashboard_data.json::picks.recent_closed` / `recent_closed_array.json`.
2. **Fix EXPIRED→WON mislabeling.** Apply `tools/relabel_crypto_expired.py --apply` after verifying dry-run; enforce `tools/resolver_hygiene_check.py` in CI so EXPIRED is never counted as WON. Add a CI test asserting no `status==WON` with `exit_reason in {EXPIRED,TIME_EXIT,MAX_HOLD}`.
3. **Restart signal_outcomes resolution.** The `at_signal_outcomes` table is ~80 days stale (RED). Investigate why `outcome_resolver.py` / `backfill_local_sources.py` stopped writing; resume hourly resolution so `db_freshness.json` signal_outcomes returns GREEN (<360 min).
4. **Fix price refresh.** Replace the dead `fetch_prices.php` endpoint; confirm `daily-prices-yf-refresh.yml` and `daily-price-refresh.yml` pass CI. Verify `crypto-ohlcv-refresh.yml` latest bar < 8h old.
5. **Hyrotrader journal.** Seed `hyrotrader_journal.json` only from real fills via `tools/hyrotrader_log_trade.py` (CLI); do not invent PnL. Currently 0 trades — do not fabricate.

Exit criteria for Stage 1: `db_freshness.json` overall GREEN; zero EXPIRED→WON mislabels; `recent_closed.json` non-empty and current; price-refresh workflows green.

### Stage 2 — Strategy Universe Pruning (PBO/SPA/FDR)
Goal: eliminate curve-fit / multiple-testing artifacts before any pick is emitted.

1. **Enable and harden the PBO/SPA/FDR gates** in `money_ready_verdict.py`:
   - Set `_FDR_GATE_ENFORCE=1` and `_SINGLE_SOURCE_GATE_ENFORCE=1` by default (remove shadow-only).
   - Require ≥2 strategies with n≥20 before a class can be considered; if fewer, class = INSUFFICIENT_DATA (do not promote).
   - PBO threshold ≤ 0.55 (`PBO_THRESHOLD` line 161); require `compute_pbo(mat)` via `tools/pbo_cscv.py` (CSCV per Bailey & López de Prado 2014, S=16 buckets).
   - SPA: `family_p_spa <= SPA_ALPHA (0.10)` via `tools/whites_reality_check.py`; require per-strategy p_marginal <= alpha.
   - FDR: Benjamini-Hochberg at `FDR_Q=0.10` on binomial p-values (H0: WR=50%); require ≥1 surviving strategy (`n_fdr_pass >= 1`).
2. **Run across full universe** (all strategies × asset classes), not just CRYPCO. Prune any strategy failing PBO/SPA/FDR.
3. **Document** which strategies survive per class and their n, WR, PF, PBO, SPA p, FDR q.

Exit criteria for Stage 2: every promoted strategy passes PBO + SPA + FDR; ≥2 strategies per class with n≥20; single-source concentration < 40% (target) / < 60% (hard cap).

### Stage 3 — Out-of-Sample / Walk-Forward Validation
Goal: confirm edge generalizes to unseen data, net of costs.

1. **Use CPCV / walk-forward** (not in-sample backtest on the same data). `alpha_engine/walkforward_validator.py` exists but is a simple rolling split — extend with embargo/purge at IS/OOS boundary and recompute on a fixed schedule (weekly/monthly), not continuously.
2. **OOS gates (all must hold, net of slippage + fees):**
   - PF ≥ 1.5
   - MDD < 20%
   - Expectancy > 0 with bootstrap 95% CI lower bound > 0 (`_bootstrap_expectancy_ci`, `money_ready_verdict.py:1323`, n_boot=1000)
   - n ≥ 100 decisive trades (TP/SL hit only; EXPIRED excluded)
   - Recency: data/picks < 48h old
3. **Apply transaction costs:** slippage 5–15 bps per class (`SLIPPAGE_BPS`, `money_ready_verdict.py:257-265`) on both entry and exit; net expectancy must remain > 0. Report gross and net expectancy.
4. **Regime filter (hard gate):** classify regime (RISK_ON / RISK_OFF / NEUTRAL / TREND / RANGE); suppress LONG in RISK_OFF; allow SHORT when regime supports it. CRYPCO LONG is already blocked in `config.py:447` (`CRYPTO_BLOCKED_DIRECTIONS`) — keep and extend to all classes as appropriate.

Exit criteria for Stage 3: ≥1 strategy per class passes all OOS gates net of costs; CI lower bound strictly positive.

### Stage 4 — Paper Trading (forward validation)
Goal: prove the edge live before risking capital.

1. Paper-trade surviving strategies for a minimum observation period.
2. Require forward-validation on n ≥ 100 clean post-noise trades (no parameter tuning during the window).
3. Monitor in real time: regime-direction consistency, source concentration, expectancy CI crossing zero, MDD breach.
4. Log every fill to `hyrotrader_journal.json` via `tools/hyrotrader_log_trade.py`; reconcile `closed_picks.json` against broker/paper fills.

Exit criteria for Stage 4: forward WR ≥ 50%, net expectancy > 0 (CI > 0), MDD < 20%, no gate flips for the full observation period.

### Stage 5 — Real Money (only after Stage 4 clears every Stage-7 gate)
Goal: allocate capital only to strategies that have proven an edge out of sample, net of costs, with multiple-testing correction.

1. Allocate only to classes/strategies that cleared Stage 4.
2. Position sizing per `config.py` per-class risk (SL/TP/hold), max 5% per trade, max 10% per symbol, 20% per direction.
3. Continuous monitoring: if any gate fails live (expectancy CI crosses zero, MDD ≥ 20%, source concentration > 60%), halt and return to Stage 2/3.

---

## 4. Money-Ready Gate Contract (Stage-7 thresholds)

A strategy/pick is money-ready only if ALL hold simultaneously:

| Gate | Threshold | Source |
|------|-----------|--------|
| Decisive trades (n) | ≥ 100 (TP/SL only; EXPIRED excluded) | `MIN_N_CLASS=100` line 155 |
| Win Rate | ≥ 50%, bootstrap CI not crossing 50% | `MIN_WR=0.55` fallback line 156; class floors lines 281-289 |
| Profit Factor | ≥ 1.5 | `MIN_PF=1.5` line 159 |
| Max Drawdown | < 20% | `MDD_GATE_THRESHOLD=0.20` line 103 |
| Expectancy | > 0, bootstrap CI lower bound > 0 | `_expectancy_gate` line 1210; `_bootstrap_expectancy_ci` line 1323 |
| PBO | ≤ 0.55 (not overfit) | `PBO_THRESHOLD` line 161; `tools/pbo_cscv.py` |
| SPA | corrected p < 0.10 | `SPA_ALPHA=0.10` line 165; `tools/whites_reality_check.py` |
| FDR | ≥1 strategy survives BH at q=0.10 | `FDR_Q=0.10` line 178; `tools/fdr_control.py` |
| Recency | < 48h | money_ready_verdict recency gate |
| Multi-source | no source > 40% (target) / > 60% (hard cap); ≥2 independent confirmations | `MAX_SOURCE_CONCENTRATION=0.40` line 248 |
| Regime-direction | no LONG in RISK_OFF; direction matches regime | `production_scanner.py:3048-3054`; `config.py:447` |
| Net of costs | expectancy > 0 after slippage+fees | `SLIPPAGE_BPS` lines 257-265 |

Fail any one → stay in paper trading or reject. No exceptions.

---

## 5. Immediate Next Steps (this session)

1. Write this document to `updates/REMEDIATION_PLAN_<datetime>.md` (this file).
2. Commit + push to GitHub remote `origin` (branch `wiring` or a new remediation branch).
3. Open issues/PRs for:
   - Enable `_FDR_GATE_ENFORCE` and `_SINGLE_SOURCE_GATE_ENFORCE` by default.
   - Add CI test: no EXPIRED→WON mislabels.
   - Fix dead `fetch_prices.php` / restore price-refresh CI green.
   - Add PBO/SPA/FDR to Stage-2 pruning job.
   - Regime-direction hard gate enforcement in `production_scanner.py`.
4. Do NOT allocate real money until all gates pass.

---

## 6. Files referenced (source of truth)

- `audit_dashboard/data/money_ready_verdict.py` — actually `alpha_engine/money_ready_verdict.py` (1,789 lines): thresholds, verdict waterfall, PBO/SPA/FDR/expectancy/bootstrap/walk-forward gates.
- `audit_dashboard/data/db_freshness.json` — freshness (RED overall; signal_outcomes RED).
- `audit_dashboard/data/picks_now.json` — 25 curated picks, 100% LONG, 2026-11-12.
- `audit_dashboard/data/picks_now_live_pnl.json` — 4,310 open picks, avg PnL −1.42%.
- `recent_closed_array.json` — 3,500 closed picks, Feb–Oct 2026; overall WR 45.6%.
- `alpha_engine/config.py` — `CRYPTO_BLOCKED_DIRECTIONS` (line 447), `COMMODITY_SHORT_ONLY`, per-class risk.
- `alpha_engine/production_scanner.py` — quality gates (:2819-3429), regime LONG block (:3048-3054), SHORT tiered gate (:3062-3096), EAGLE-4/6 (:386-5811), portfolio cap (:5841-5856).
- `alpha_engine/walkforward_validator.py` — walk-forward + bootstrap CI + t-test; no PBO/SPA/FDR.
- `alpha_engine/forward_validator.py` — White's Reality Check (:333-397); outcome resolution.
- `tools/pbo_cscv.py`, `tools/pbo.py`, `tools/whites_reality_check.py`, `tools/fdr_control.py` — multiple-testing tools.
- `tools/relabel_crypto_expired.py`, `tools/resolver_hygiene_check.py` — outcome-hygiene fixes.
- `.github/workflows/` — 365 workflows; 30 failures incl. CI Tests, Live Trading Bot, Daily Price Refresh, Daily Prices yfinance Refresh.

---

*End of plan. To be committed and pushed to GitHub as a date-time-stamped .MD in updates/.*
