# Phase 0 Implementation Kickoff — Profitable Market System

**Date:** 2026-11-20
**Canonical plan:** [`plans/2026-11-20-market-profit-system-plan.md`](2026-11-20-market-profit-system-plan.md) (Zoo)
**Todos:** [`plans/2026-11-20-profit-program-todos.json`](2026-11-20-profit-program-todos.json)
**Hypotheses:** [`plans/2026-11-20-residual-mean-reversion-hypotheses.md`](2026-11-20-residual-mean-reversion-hypotheses.md)
**Research synthesis:** [`PROFITABLE_SYSTEM_PLAN.md`](../PROFITABLE_SYSTEM_PLAN.md) (root)
**COMS:** topic `profit-system/plan` (retained) — broadcast 2026-11-20 with full plan per asset class, repo files, SQL setup, GHA setup.

---

## What was done this session

1. **COMS broadcast sent** (retained, topic `profit-system/plan`): full plan per asset class (equities, ETFs, futures/commodities, fixed income, crypto, FX, prediction markets, alt-data), the repo files to modify, the SQL DB setup, and the GitHub Actions setup.
2. **SQL schema created:** `sql/profit_program_schema.sql` — 8 tables: `premia_pods`, `premia_picks`, `forward_rows`, `cost_benchmark_gates`, `trial_counter`, `regime_log`, `liquidity_metrics`, `premia_verdicts`. Seeded with H-144..H-148 pods and per-class cost/benchmark defaults (v1.0). Idempotent, MySQL 5.7+/8.0 compatible.
3. **Cost-implied trade gate implemented:** `alpha_engine/cost_implied_trade_gate.py` (P2-h / H-146) — hard gate: change position only when |forecast| > round-trip cost. Measures turnover reduction and gross-alpha retention separately. Smoke test: 63.1% turnover reduction, 71.0% gross-alpha retention at 20 bps round-trip cost. JSON export supported.
4. **Research synthesis doc updated:** `PROFITABLE_SYSTEM_PLAN.md` (root) now points to the canonical Zoo plan and incorporates the documented-evidence-base (stat-arb 1.44→0.9, calendar-spread Sharpe>2, crypto cost collapse, etc.).

---

## Three cheap high-information actions (do these FIRST, before any pattern search)

From the 2026-11-20 free-data/alt-data synthesis:

1. **Establish real risk capacity before return target.** Decide max drawdown you could watch without selling, then size to it (50% loss needs 100% gain to recover; 75% needs 300%). Costs nothing; determines everything downstream. Record in `risk_management/risk_capacity.md`.
2. **Look at free alt-data with a known mechanism, not chart patterns:** USAspending contract awards, congressional disclosures (5-7%), consumer transaction panels, job-listing "Jobs Active" (6-8%), trade-credit data (6-7%). Free sources: EDGAR, USAspending.gov, Senate LDA, OpenFEC, CFTC COT, FRED/ALFRED. Test with point-in-time + placebo + cost survival.
3. **Paper trade before funding.** 60-90 days on Thinkorswim paperMoney / TradingView paper trading (free, real-time). Compare live fills vs backtest assumptions; the gap is the real answer. Scale in gradually only if edge is within 15-20% of backtest.

**Free data stack (production):** Binance public WS (crypto tick), Finnhub free (US eq/forex RT), CME/Cboe (futures/VIX, ~15-min delay), SEC EDGAR, USAspending.gov, CFTC COT, Senate LDA/OpenFEC, FRED/ALFRED, QuantConnect/TradingView free tiers. **Do NOT use yfinance in production** (survivorship bias, no licence).

**Warning:** symbol-specific strategy mining is a multiple-testing trap (1,285 variants tested with real costs/OOS/pre-registration/deflated-Sharpe: best solo transparent 12-yr track record ~0.8 Sharpe; LLM agent 2.12 in-sample → +0.18 OOS). Even real edges are regime-dependent (single aggregate numbers hide negative sub-periods). Diversification across return drivers (commodity futures negative corr to stocks/bonds) beats picking a side.

## Phase 0 — next concrete actions (in priority order)

From `plans/2026-11-20-profit-program-todos.json` (P0) and Zoo plan §3 Phase 0:

### P0.0 — DATA INTEGRITY FIRST (before anything else)

Grok external review (2026-11-20): the system is destroying capital. 55,510 resolved trades: WR 11.13%, avg −3.56%/trade, Sharpe ~−2.3, PF ~0.46, ML ~33% (worse than random), calibration inverted, ~69% zero PnL, backtest WR ~4× live, dashboard claims (+949% PnL, 35-40% WR) don't match DB. Classic overfitting + data-quality failure.

- [x] **P0.0a** Purge/quarantine zero-PnL rows (69% of resolved) — genuinely zero or un-resolved/placeholder? **DONE**: `tools/purge_zero_pnl_picks.py` created + tested (6 tests pass). Dry-run: 144 zero-PnL in closed_picks.json (all genuine), 1112 zero/null in universal_resolved_picks.json (1110 null + 2 zero). Quarantines to separate file, idempotent, dry-run by default.
- **P0.0b** Outlier handling: winsorize/exclude outlier-driven PF; reconcile gross vs net.
- [x] **P0.0c** Point-in-time correctness: audit every feature for look-ahead (COT leakage precedent M-095). **DONE**: `tools/point_in_time_audit.py` created + report written to `reports/point_in_time_audit_report.json`. Scanned alpha_engine (91 findings, 48 production) and tools (172 findings, 14 production). Key findings: 26 SIGNAL-class files with forward indexing (.iloc[i+1], .shift(-1), .iloc[t+21]); COT leakage in forex_cot_reversal.py (no lag correction, DEFAULT-OFF); earnings features in growth.py and factory.py lack lag/pub-date handling; ml_engine_v2.py uses shift(-horizon) for target (training-only, acceptable). Report identifies specific files and line numbers for remediation.
- **P0.0d** Dashboard ↔ DB reconciliation: every published number traces to a DB row; fix or remove +949% PnL / 35-40% WR claims.
- [x] **P0.0e** Wire PBO / CPCV / DSR as HARD gates (not advisory); enforce walk-forward before any promotion. **DONE**: Added `_DSR_GATE_ENFORCE` and `_PBO_GATE_ENFORCE` env vars (default ON) to `alpha_engine/money_ready_verdict.py`. Modified `_verdict()` to make DSR/PBO conditions conditional on enforce flags. Added `_dsr_gate_enforce` and `_pbo_gate_enforce` to verdict output metadata. Follows same pattern as MDD/FDR/single-source gates. Tests pass (6/6).
- **P0.0f** Record real n_trials for every DSR claim incl. 700-strategy catalog (effective N).

Only after 0.0 passes does 0.1 (price freshness) and beyond make sense.

### P0.1 — Price freshness per class + SLA + CI gate
- **File:** `tools/db_freshness_check.py` (extend) + new `.github/workflows/price-freshness-guardian.yml`
- **Task:** Add equity/FX/futures price-vintage checks (equity ≤2d, FX ≤2d, futures ≤3d) with GREEN/YELLOW/RED and CI fail on RED. Make `audit_dashboard/data/db_freshness.json` internally consistent (currently FX stale since 2026-02-09, equity 2026-06-18, futures 2026-06-21).
- **Deliverable:** `db_freshness.json` with per-class vintage + SLA; CI gate.

### P0.2 — Backfill FX + fix AUDJPY mapping; retire EURUSDT from FOREX
- **Files:** FX price fetcher (find `fetch_*fx*` / `fx_prices`), `alpha_engine/` FX universe config.
- **Task:** Backfill FX 2026-02→11; fix `AUDJPY=X`/`AUD-USD` mapping; retire `EURUSDT` from FOREX class (it's a crypto instrument, not FX).
- **Deliverable:** FX coverage report showing continuous daily bars for all G10 pairs.

### P0.3 — Publish MDE per asset class
- **File:** `alpha_engine/money_ready_verdict.py` (add `mde` block) + dashboard tile.
- **Task:** Compute minimum detectable effect from real n and vol per class; publish alongside selection alpha.
- **Deliverable:** `money_ready_verdict.json` with `mde` block per class.

### P0.4 — Selection alpha vs same-instrument hold as per-class headline
- **File:** `tools/asset_class_edge_review.py` (or audit3 selection alpha module) + dashboard tile.
- **Task:** Publish selection alpha (per trade, %) with CI per class, headline on `/audit`, not buried.
- **Deliverable:** `/audit` tile + CI.

### P0.5 — Global trial counter threaded into deflated_sharpe
- **Files:** `alpha_engine/deflated_sharpe.py`, `research/profitability/HYPOTHESES.md`, `reports/hypothesis_registry.json`.
- **Task:** Single source of truth for cumulative trials; DSR uses true N (including 700-strategy catalog). Append-only guard.
- **Deliverable:** `dsr_n_trials == cumulative trials` invariant test.

### P0.6 — Publish pf_gross, pf_net, expectancy_net separately; delete bare pf
- **File:** `alpha_engine/money_ready_verdict.py` schema.
- **Task:** Split profit factor into gross/net; add expectancy_net. Remove ambiguous `pf`.

### P0.7 — Fix policy_clean_* invariant (clean_n <= n_resolved)
- **Files:** `alpha_engine/money_ready_verdict.py`, `tests/`.
- **Task:** Assert `clean_n <= n_resolved` for policy-clean subsets; add invariant test.

### P0.8 — Pin canonical population `resolved_closed_picks_net`
- **File:** dashboard/pipeline publisher; remove or lag-mark the second publisher.
- **Task:** One population, one provenance triple everywhere.

### P0.9 — Bound exclusion bias (41.2% unscored book)
- **Task:** Publish what the unscored book would have to look like to flip the conclusion.

### P0.10 — Record real n_trials for every DSR claim (incl. 700-strategy catalog)
- **Task:** Backfill trial counter from historical runs.

---

## Meta-strategy (mandatory preconditions — hand to every agent)

Do NOT search for new signals until the validation layer is mandatory. Every candidate must pass these gates before any capital or dashboard promotion:

1. Point-in-time data only (no survivorship, no look-ahead).
2. Walk-forward analysis (WFA) with ≥5 splits, WFE > 60%.
3. Combinatorial purged cross-validation (CPCV) with PBO < 0.05.
4. Deflated Sharpe Ratio (DSR) > 0.95 after accounting for number of trials.
5. Net of realistic costs (min 5–10 bps round-trip liquid; higher for crypto/forex).
6. Paper-trade / forward OOS ≥ 60–90 days matching backtest assumptions within ~20%.
7. Hard kill switches: residual half-life rising, IC turning negative, costs exceeding model, or max drawdown breach.

Force agents to pre-register the hypothesis, the exact parameter space, and the success criteria BEFORE running anything. Run one asset class at a time. Wire the existing PBO/CPCV/DSR code before any new signal work. Fix the zero-PnL pipeline first.

### LLM agent prompt template

"Investigate the following pre-registered strategy for [ASSET CLASS]: [exact description].
Universe: [list].
Parameters allowed to vary: [narrow list].
You must implement point-in-time data, walk-forward with ≥5 splits, CPCV, and compute PBO and DSR.
Report only results that survive realistic costs.
If the strategy fails the gates, document why and stop. Do not retune until the equity curve looks good."

---

## Per-asset-class investigation targets (Phase 1)

### Equities / ETFs — Residual mean-reversion (Avellaneda–Lee)
- For each stock, regress daily returns on sector ETFs OR top 5–10 PCA eigenportfolios of the liquid universe.
- Fit residual as Ornstein–Uhlenbeck over rolling 60-day window.
- Compute s-score (distance from equilibrium in std devs).
- Enter when |s| ≥ 1.25, exit at 0.5; hedge with beta-weighted basket of factors → market-neutral book.
- Test PCA vs sector-ETF factor versions; vary window (40–90 days) and entry thresholds only inside pre-registered range; report WFE, PBO, DSR.
- Strongest published multi-year evidence of any retail-accessible equity approach.

### Crypto — Cost-aware residual or funding-rate carry (liquid pairs only: BTC, ETH, SOL + major perps)
- Residual/OU s-score on 4h or 1h bars vs BTC or market-cap-weighted basket.
- OR pure funding-rate carry: long under-funded side when 8h funding in extreme percentile and basis stretched.
- Mandatory cost gate: only trade when expected residual move > 2× measured round-trip cost (spread + taker fee + slippage). Model 10 bps round-trip minimum.
- High-turnover pure directional models have repeatedly failed here.

### Forex — Selective residual MR on majors only (EURUSD, USDJPY, GBPUSD, AUDUSD)
- Residuals vs small set of cross-rates or simple USD factor; same s-score entry/exit.
- OR short-term carry + MR when rate differential and recent residual both stretched.
- Treat "no edge after costs" as a valid and expected outcome; document retry conditions (e.g., higher vol regime).

### Commodities / Futures — Front-vs-second-month calendar-spread MR (energy CL, NG; metals GC)
- Compute spread; Bollinger bands or OU s-score on the spread itself.
- Kalman filter or rolling OLS for dynamic hedge ratio.
- Entry on band breach, exit at mean.
- Multi-decade published evidence after costs in some energy markets. Start CL+NG only; require bootstrap significance + realistic roll costs.

### Bonds / Fixed Income — Liquidity and relative-value (not pure price prediction)
- Same bond across venues; on-the-run vs off-the-run spread; corporate vs Treasury duration-matched.
- OR simple term-structure MR on liquid Treasury futures.
- Expand universe with FRED + TRACE-style data first (samples tiny).

### Memecoins / Penny stocks — EXCLUDE
Do not pursue. Worst performers in our data. Exclude from all production universes.

---

## Key technical finding from peer review (H-2026-11-20-01 / H-146)

The cost gate (H-146) comparison was **inflated by ~67%**: it compared the FULL reversion distance (|s_entry|*sigma_eq) against cost, but only CAPTURED reversion ((|s_entry|-0.5)*sigma_eq) is tradeable since exit is at |s|=0.5. At entry |s|=1.25, captured edge is 0.75*sigma_eq, not 1.25*sigma_eq. This explains why the gate filtered only 1 of 154 entries. Fix: compare (|s_entry|-0.5)*sigma_eq*100 against cost. Re-run at varying cost levels (0.4%, 1.0%, 2.0%) and entry thresholds (1.25, 1.0, 0.75).

Also: full-sample OU fit returns None (rho>=1) — residual is non-stationary; rolling 60d fits likely manufacture mean-reversion via Dickey-Fuller small-sample bias. 65% of trades exited on time cap. H-2026-11-20-01 → NOT_PROVED. Move to H-145 (energy calendar spreads) next.

## Critical findings from peer (copilot-cli-deepseek-flash, 2026-11-20)

### Anti-informative cost gate (H-146 redesign needed)
The cost gate as designed is **value-destroying**, not just non-binding. It removes trades with 3.1x HIGHER mean gross than the ones it keeps (total net -0.1284% ungated -> -0.1499% gated, PF 0.623->0.605). Mechanism: gating on expected_pct = (|s|-0.5)*sigma_eq <= cost gates on LOW sigma_eq, but low sigma_eq = quiet residual = MORE reliable mean reversion. The gate screens on absolute forecast magnitude, penalizing exactly the regime where the model works. **Redesign: condition on sigma_eq (trade only when sigma_eq is above median AND expected_pct > cost), not filter on it.** The paired_gate_compare harness is still the right test — but the gate logic inside must change.

### H-01 with hedge booked: clearly negative
mean_gross +0.0716% (was +0.1997% unhedged = directional beta mirage). mean_net -0.1284%. win_rate 24.18%. PF 0.623. 64.7% time-cap exits. Gross alpha +7.2bp vs 20bp cost. Needs <7bp round-trip to survive — not available on two-leg residual trade. H-01 -> NOT_PROVED confirmed. Do not retune.

Cost arithmetic corrected: 0.2% base case (COST_BPS=5.0 default), 0.4% sensitivity. BOTH negative. At 10 bps, unprofitable by more than entire gross edge. The verdict does not flip with cost assumption.

Registry integrity: all six H-2026-11-20 entries still PRE_REGISTERED despite H-01 carrying populated result block; H-01 has data_sample_lock: null. Pre-registered-but-already-run is a process defect.

### Exit geometry is the real finding (stronger than NOT_SUPPORTED)
Three independent surfaces, one signature:
  simulated time-cap            64.7%
  at_signal_outcomes TIME_EXIT  84.1%  (43,006 / 51,143)
  ledger TP-first rate          36.3%  vs geometry-predicted 37%
The ledger TP-first rate lands within 0.7pp of the geometry-only prediction. The signal contributes approximately nothing to which branch fires. Any future edge claim in this family must explain why it would survive a geometry-only null. Required check for all future candidates: "does the signal change outcomes beyond what exit geometry alone predicts?"

### Regime clustering: UNIFORM (P3-c DROPPED)
Time-cap exits by half_life_at_entry quartile: 0.673/0.588/0.778/0.667. By |entry_s| quartile: 0.684/0.579/0.615/0.711. By direction: LONG 0.639 vs SHORT 0.657. No clustering. P3-c (regime module) DROPPED — do not build. The residual simply does not revert.

### DSR defect A fix (validation-layer)
tools/run_anti_overfit_audit.py:119 computed _annualized_sharpe(flat) and passed to deflated_sharpe. Fixed with _per_period_sharpe helper. Absolute-magnitude guard structurally wrong: zero-edge daily series -> per-period SR +0.0322, annualised +0.5108, slips under |SR|>1.0 guard, yet DSR returned 1.0000 (PASS) where correct answer is 0.0350 (reject). Replaced with ratio test against per-period Sharpe implied by returns array (mu/sd), probing sqrt(4|12|52|252) with +/-15% tolerance.

### Rule: every test must be able to fail
A test that cannot fail is not a test. A gate that cannot fail a build is not a gate. Applied to: test_simulate_is_point_in_time (only asserts "is not None"), CI gates (continue-on-error), probabilistic_sharpe_engine (DSR 1.0282 on pure noise).

### Bug: expected_pct not persisted to trade dict
computed in simulate() but not in trade dict -> gate unauditable after the fact. Two lines to fix. Auditability is non-negotiable (P5-a).

### Validation-layer audit: ZERO CI ENFORCEMENT (highest leverage)
Grok asked for gates to be WIRED. Peer found they are not even INVOKED:
- **(a) Three DSR implementations, one broken:** probabilistic_sharpe_engine reports DSR 1.0282 on pure noise (zero edge) — would PASS "DSR>0.95" on a strategy with provably zero edge. Root cause: _calculate_expected_max_sharpe uses sqrt(2/n*log(n)) with n=sample length (not trial count); output is Sharpe-unit difference not probability. No importers in main tree (harmless today, live trap). DEPRECATE or delegate to the two correct ones (anti_overfit_validator.deflated_sharpe=0.4181, research/profitability/backtest.deflated_sharpe=0.4159).
- **(b) ZERO CI ENFORCEMENT:** grep over .github/workflows/ for cpcv_overfit_detector, run_anti_overfit_audit, tools/wfe.py returns NOTHING. Gates tested (32 passed, 1 skipped) but never invoked in CI. A gate never run is not a gate. **Highest-leverage fix. Fix before any new signal work.**
- **(c) evaluate_strategy() PBO against synthetic zero-mean peers ("degraded mode"):** pure-noise returns pbo in {0.578, 0.467, 0.844, 0.222, 0.333, 0.822}; honest 40-col noise matrix gives 0.333 where wrapper gives 0.267. Not a valid PBO. Either require real candidate matrix or return nan.
- **(d) NO TRUE CPCV:** pbo_cscv/cpcv_pbo implement CSCV block splitting, not combinatorial purged CV with purge+embargo. Gate 3 (PBO<0.05) partially unmet.

### Revised ordering (non-negotiable) — UPDATED
(0) ONE BLOCKING GATE in CI (promoted from (b) to first). Every gate in CI is currently continue-on-error. Until at least one gate can fail a build, all statistical correctness is decorative. Smallest change with largest effect.
(a) Fix expected_pct persistence bug (2 lines) — auditability prerequisite.
(b) Enforce gates in CI (highest leverage — Grok's actual ask).
(c) Fix/deprecate probabilistic_sharpe_engine (DSR trap) — DSR 1.0282 on pure noise; Defect A (annualised input) was LIVE not latent; fixed with _per_period_sharpe helper + ratio test.
(d) Fix evaluate_strategy PBO (return nan in degraded mode; currently invents synthetic zero-mean peer strategies, so PBO is fabricated).
(e) Redesign cost gate to condition on sigma_eq (not filter on it); re-run paired comparison with corrected comparison (captured reversion not full reversion).
(f) Then H-145 (energy calendar spreads) — strongest published evidence.
P3-c (regime module) DROPPED — uniform clustering, no regime filter needed.
No new signal work until (0)-(e) exist.

### Regime clustering of time-cap exits: UNTESTED
Peer measuring next (conditional on half_life_at_entry and sigma_eq buckets). If time-cap exits concentrate in high-vol/trending regimes -> regime filter (P3-c) case. If uniform -> residual simply not reverting. Report when done.

## Phase 1 — first concrete actions (after Phase 0 exit test)

From Zoo plan §3 Phase 1 and todos P1:

1. **P1-a/b:** Implement RSI(2) long-only on SPY/QQQ in our own engine (lag 1, costs, cash leg, time-matched benchmark); run through audit3 tribunal unmodified. Should pass. Run same code on BTC/SOL to calibrate against a known failure.
2. **P1-c:** `alpha_per_exposed_day` and `time_in_market` as first-class metrics.
3. **P1-d:** overlay-vs-standalone decision memo from utilization finding.

## Phase 2 — first concrete actions (after Phase 1 exit test)

1. **P2-a/b/c:** Flip discovery objective to mean forward return net of cost; mandatory direction check; variance-artifact verdict.
2. **P2-d/e/f:** per-feature coverage; explicit inconclusive records; persistent trial counter.
3. **P2-g:** re-run per-class review on refreshed prices → per-class verdict (edge/artifact/inconclusive).
4. **P2-h (H-146):** Cost-implied trade gate — **DONE** (`alpha_engine/cost_implied_trade_gate.py`). Next: wire into order gateway; measure turnover reduction + gross-alpha retention on real picks.

## Phase 3 — first concrete actions

1. **P3-f:** Residual-book construction (point-in-time universe, rolling factor regression, OU fit with half-life, beta-weighted hedge, inverse-vol sizing with caps outside model). H-144 (sector ETFs) + H-145 (energy calendar spreads).
2. **P3-g (H-147):** Selection-alpha decomposition — hedge each pick's market-factor exposure over holding window; re-measure selection alpha. Cheapest decisive test.

## Phase 4-5 — later

Promotion gate, portfolio construction, reconciliation/calibration/decay. See canonical plan.

---

## Exit criteria (Phase 0)

A stranger can read `/audit` and know, per class: rows, price vintage, MDE, net alpha vs hold, cost model version. No number lacks a denominator. `dsr_n_trials` equals cumulative trials. `clean_n <= n_resolved` invariant holds.

## Notes

- No new strategy generation while P0/P1 open (rule from todos JSON).
- No real capital until Phase 4 gates met.
- Negative result is a valid, publishable outcome (PROTOCOL §1).
- This kickoff doc will be updated as items complete; each item's evidence artifact is named in the todos JSON.