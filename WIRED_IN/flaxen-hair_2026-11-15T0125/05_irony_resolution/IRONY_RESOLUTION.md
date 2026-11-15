# Irony Resolution — Forward-Test Picks vs. Unproven Asset Classes

**Worktree:** flaxen-hair_2026-11-15T0038 | **Date:** 2026-11-15 | **Repo:** findtorontoevents_antigravity.ca
**Location:** `05_irony_resolution/IRONY_RESOLUTION.md` (WIRED_IN documentation folder)

---

## 1. The Irony Stated

**The system says "NO asset class is proven profitable," yet it emits 5 forward-test picks.**

These two statements sit side by side throughout the repository's current state, and at first glance they appear to contradict each other:

| Statement | Source | Evidence |
|-----------|--------|----------|
| "No asset class is proven profitable" | `2026-11-15_12AM_plan/flaxen-hair/README.md:9` | "0/23 hypotheses across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates. All 9 classes return `sizing_allowed: false`." |
| "No asset class is proven profitable" | `research/profitability/SCORECARD.md:5` | "Outcome: **NOT PROVED** (honest negative) after 23 candidates across four versions." |
| "No asset class is proven profitable" | `research/profitability/HYPOTHESES.md:83-86` | "**No approach is PROVED.** The search now covers 23 candidates across crypto, ETFs, countries, sector rotation, trend, reversal, momentum, and funding carry... v3 (breadth) produced no edge; v4 (funding carry) is a real but low-vol, capital-intensive carry that does not beat cash after realistic capital." |
| "5 forward-test picks emitted" | `2026-11-15_12AM_plan/flaxen-hair/README.md:56-64` | 5 picks tabled under "Forward-Test Picks — 5 Active Paper Tests": SPY connors_rsi2, XLF keltner_compression_v2, GLD ema_stack, GLD funding_sentiment, SPY funding_sentiment — all flagged `PAPER TEST`. |

**The irony:** If no asset class is proven profitable and all 9 classes return `sizing_allowed: false`, why is the system emitting picks at all — especially picks on SPY, XLF, and GLD, which live inside those same unproven classes?

---

## 2. The Resolution

**The picks are not "buy recommendations." They are forward-test hypotheses — hypothesis containers, not profit engines.**

The contradiction dissolves once you recognize that the system operates two entirely separate tracks:

1. **Asset class profitability (the "money" track):** The question "Is any asset class proven profitable?" is answered by running pre-registered, benchmark-relative, clean-out-of-sample tests across the full class universe. The answer today is **no** — 0/23 hypotheses survived. This determines whether *capital* may be deployed to a class. All 9 classes are blocked: `sizing_allowed: false`.

2. **Forward-test picks (the "research" track):** The question "Should we observe these specific strategy-symbol pairs in live market conditions?" is answered by emitting small, time-boxed, paper-only picks that serve as **hypothesis generators**. These picks do not imply profitability. They imply *observability*: "We want to see how this strategy behaves on real price action, with real slippage, real fill mechanics, and real clock time — at zero capital risk."

A pick is a **container for a forward-test hypothesis**, not an instruction to buy. The five picks currently emitted are:

| # | Symbol | Strategy | Asset Class | Direction | Entry | TP | SL | R:R | Status |
|---|--------|----------|-------------|-----------|-------|-----|-----|-----|--------|
| 1 | SPY | connors_rsi2 | EQUITY | LONG | 450.00 | 463.50 | 441.00 | 1.5 | PAPER TEST |
| 2 | XLF | keltner_compression_v2 | ETF | LONG | 42.00 | 43.26 | 41.16 | 1.5 | PAPER TEST |
| 3 | GLD | ema_stack | COMMODITY | LONG | 2650.00 | 2729.50 | 2597.00 | 1.5 | PAPER TEST |
| 4 | GLD | funding_sentiment | COMMODITY | LONG | 2650.00 | 2729.50 | 2597.00 | 1.5 | PAPER TEST |
| 5 | SPY | funding_sentiment | EQUITY | LONG | 450.00 | 463.50 | 441.00 | 1.5 | PAPER TEST |

Source: `2026-11-15_12AM_plan/flaxen-hair/README.md:58-64` ("Forward-Test Picks — 5 Active Paper Tests").

Critical metadata flags on every pick:
- `forward_test_only: true` — the pick exists only to generate forward-test data; it is not eligible for any capital path.
- `forward_validated: false` — no forward-test evidence has yet been accumulated; the pick has not passed any forward gate.
- All 5 picks derive from backtests where `n < 10 trades` — statistically insignificant by every gate in the protocol.

These picks are emitted **despite** — not because of — the absence of proven profitability. Their emission is a research activity, not a deployment activity.

---

## 3. The Gating System That Prevents Capital Deployment

The system is explicitly designed so that pick emission and capital deployment are **decoupled**. Emitting a pick does not authorize spending money on it. The gating system enforces this separation at every tier.

### 3.1 Tiered Promotion Ladder

Defined in `2026-11-15_12AM_plan/flaxen-hair/README.md:98-105` (mirrored in `BACKTEST_AND_TRACKING_PROTOCOL.md:104-112`):

| Tier | Name | Gate Requirements | Capital Allowed? |
|------|------|-------------------|------------------|
| Tier 1 | Immediate Elimination (Kill Fast) | Stale data, confidence-coupling, PnL=0 with price movement, blank fields, negative PnL after 20 trades, Sharpe < 0 after 20 trades | No — kill |
| Tier 2 | Watch List (Hold Up to 30 Days) | n < 50, PF 0.8-1.5, WR 40-50%, Sharpe 0-0.5 | No — watch only |
| Tier 3 | Promotion Candidate (Paper Trading Eligible) | n ≥ 50, PF ≥ 1.5, WR ≥ 50%, Sharpe ≥ 0.5, MaxDD < 15% | Paper only — zero live capital |
| Tier 4 | Live Capital Eligible | n ≥ 100 forward picks, PF ≥ 1.5 forward, WR ≥ 55% forward, DSR ≥ 0.95 forward, 3+ months clean forward | Live capital — conditional on all gates |

The 5 current picks sit at **pre-Tier 2**: n < 10 on every single one. They have not passed any gate. They are not paper-trading-eligible, much less live-capital-eligible.

### 3.2 Per-Asset-Class `sizing_allowed: false`

All 9 asset classes return `sizing_allowed: false`. This is enforced at the asset-class level, independent of any individual pick. Even if a pick looked attractive, the class-level block prevents position sizing from being computed for it. The block is documented across:

- `2026-11-15_12AM_plan/flaxen-hair/README.md:9` — "All 9 classes return `sizing_allowed: false`."
- `2026-11-15_12AM_plan/flaxen-hair/01_asset_class_plans/ASSET_CLASS_PROFITABILITY_PLANS.md:9` — "Zero asset classes are currently proven profitable... All 9 classes return `sizing_allowed: false`."
- `2026-11-14_12AM_plan/flaxen-hair/01_asset_class_plans/ASSET_CLASS_PROFITABILITY_PLANS.md:184` — ranking table where every class except passive ETF/MF allocation carries a blocker.

### 3.3 Money-Ready Verdict Gates (Fail-Closed Design)

The runtime gating layer lives in `alpha_engine/money_ready_verdict.py`. Key mechanics:

| Gate | File | Line(s) | Behavior |
|------|------|---------|----------|
| DSR + PBO/CSCV + SPA per-class verdict | `alpha_engine/money_ready_verdict.py` | 1-28 (docstring), 19 | Verdicts: MONEY_READY \| WATCH \| NOT_READY \| INSUFFICIENT_DATA |
| FDR gate (fail-closed when enabled) | `alpha_engine/money_ready_verdict.py` | 163 | `MONEY_READY_FDR_GATE` env var — defaults OFF (fail-open today, but designed to fail-closed) |
| Single-source gate (fail-closed when enabled) | `alpha_engine/money_ready_verdict.py` | 178 | `MONEY_READY_SINGLE_SOURCE_GATE` env var — defaults OFF |
| Cost gate fail-open paths | `alpha_engine/per_class_cost_gate.py` | Referenced in `PROFITABILITY_FRAMEWORK.md:231` | After-cost errors currently suppressed — a known defect to fix before any capital |
| Promotion gates | `alpha_engine/money_ready_verdict.py` | Referenced throughout | Fail-closed design; currently default OFF |

As documented in `README.md:129-130`, the preconditions to revisit live capital are:

1. Measurement gates pass (cohort_id, filter hash, source timestamp, row-level denominator reconciled).
2. Promotion gates **fail closed** (`MONEY_READY_FDR_GATE` and `MONEY_READY_SINGLE_SOURCE_GATE` enabled).
3. EQUITY pre-registered test passes vs SPY (n≥500, OOS Sharpe ≥ SPY Sharpe, PF ≥ 1.15, stability both halves).
4. CRYPTO post-fix forward test passes (POSITION horizon n≥100, PF ≥ 1.3, WR ≥ 55%, after `kimi_riseoftheclaw` fill fix).
5. CI failures resolved (Python 3.11/3.12 test failures diagnosed and fixed).

**None of these conditions are met today.** Therefore no capital may be deployed to any pick, on any class, under any circumstance.

---

## 4. Beta vs. Alpha: Two Separate Tracks

The repository's standing position is that there are two fundamentally different ways to make money, and they must not be conflated:

### 4.1 Beta Capture — The Money Deployment Vehicle (Proven)

**ETF Tactical Asset Allocation (TAA)** is the only validated approach in the entire research program. It is **smart-beta, not alpha**:

- Source: `2026-11-15_12AM_plan/flaxen-hair/README.md:11-14`, `PROFITABILITY_FRAMEWORK.md:195-203`, `ASSET_CLASS_PROFITABILITY_PLANS.md:93-110`
- Universe: Top-5 asset-class ETFs by 6-month momentum, monthly rebalance, abs-momentum filter → bonds. 14 liquid free ETFs (yfinance): SPY, QQQ, IWM, EFA, EEM, TLT, IE, SHY, GLD, XLF, XLE, XLV, XLY, XLC.
- 2007-2026 (incl. 2008 GFC): Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs SPY −51%, Calmar 0.48 vs 0.21.
- All 16 grid cells (top-N × lookback) cut MaxDD to −12/−17% vs SPY −24%. Positive all 3 time-thirds (both-halves stability).
- Explicitly: "**Smart-beta, NOT alpha** — matches market return with ~half the drawdown."

This is where actual money goes. Beta capture works because it harvests the equity risk premium and diversifies across uncorrelated asset classes. It does not require a proven alpha strategy. It requires low-cost index funds/ETFs held long-horizon — which remains the baseline long-horizon path per project constraint (`active_strategy_benchmark_requirement`: every active strategy must beat buy-and-hold after costs on clean data).

### 4.2 Alpha Generation — The Pick Research Track (Unproven)

The 5 forward-test picks are **alpha hunt** — attempts to discover a repeatable edge that beats beta. None has been found:

- 0/23 hypotheses across 4 protocol versions survived clean OOS + effective-N + capital + execution gates (`SCORECARD.md:5`, `HYPOTHESES.md:83-86`).
- Best notional results (e.g., SPY connors_rsi2 PF 76.92, n=6) are explicitly flagged as "clearly inflated due to tiny n" (`BACKTEST_AND_TRACKING_PROTOCOL.md:244`).
- EQUITY — the only class with positive cost margin (3.23×, mean +0.323%, n=738) — has t=1.52, p=0.12: **not statistically significant** (`SCORECARD.md`, `PROFITABILITY_FRAMEWORK.md:205-209`).
- CRYPTO — 700+ strategies tested, ALL fail clean-cohort screen; entry_price ~29% clean, ~90% positions never resolve (`PROFITABILITY_FRAMEWORK.md:211-216`).

**Beta capture deploys money. Alpha research emits picks.** These are different activities with different gate requirements and different capital rules.

---

## 5. The Five Picks — Why Each Was Emitted Despite Not Being "Proven"

Each pick was chosen because it occupies a specific research niche, not because it is profitable. The selection logic is documented in `README.md:36-52` (Top 5 by Profit Factor and Top 5 by Sharpe tables) and `ASSET_CLASS_PROFITABILITY_PLANS.md`.

### Pick 1: SPY connors_rsi2 (EQUITY)
- **Backtest:** n=6, WR 83.3%, PF 76.92, Sharpe 1.14, P-value 0.1094 — FAIL (n<50) (`BACKTEST_AND_TRACKING_PROTOCOL.md:23`).
- **Why emitted:** EQUITY is the only class with positive cost margin (3.23×). Connors RSI2 is the **sole proven sleeve** within EQUITY (WR 75.7% per `ASSET_CLASS_PROFITABILITY_PLANS.md:36`). SPY connors_rsi2 is the best-risk-adjusted symbol-strategy combo in the backtest table despite n<10. It is the natural first EQUITY forward-test candidate because it is the only sleeve with any empirical support at all — however weak.
- **Research question:** Does Connors RSI2 on SPY hold up under live execution with real fills, or does it decay like H7/H10 did in OOS?

### Pick 2: XLF keltner_compression_v2 (ETF / Smart-Beta Test)
- **Backtest:** n=5, WR 100.0%, PF 10.00, Sharpe 0.74, P-value 0.0312 — FAIL (n<50) (`BACKTEST_AND_TRACKING_PROTOCOL.md:52`).
- **Why emitted:** ETF tactical is the validated money track. XLF is part of the ETF TAA universe (`ASSET_CLASS_PROFITABILITY_PLANS.md:104`). Keltner compression is being tested as a **smart-beta timing overlay** within the ETF universe — not as alpha, but as a potential entry/exit refinement for the beta sleeve. Sharpe 0.74 is close to SPY's 0.74 benchmark, making it a plausible-but-unproven tactical test.
- **Research question:** Can keltner_compression_v2 add timing value to an ETF TAA framework without degrading the validated beta profile?

### Pick 3: GLD ema_stack (COMMODITY)
- **Backtest:** n=10, WR 80.0%, PF 4.51, Sharpe 0.62, P-value 0.0547 — FAIL (n<50) (`BACKTEST_AND_TRACKING_PROTOCOL.md:41`).
- **Why emitted:** COMMODITY is blocked (n≈27 post-filter, below min_trades=60, cost/PnL ratio 422% per `ASSET_CLASS_PROFITABILITY_PLANS.md:113-119`). GLD ema_stack is the highest-PF commodity backtest (4.51) but with n=10 — far below the 60-trade floor. The pick exists to test whether commodity futures/ETF momentum has any live edge at all, acknowledging the class is currently blocked from sizing.
- **Research question:** Is there any reproducible commodity edge, or is the class permanently blocked by cost and thin samples?

### Pick 4: GLD funding_sentiment (COMMODITY / Sentiment Test)
- **Backtest:** n=6, WR 83.3%, PF 4.15, Sharpe 0.66, P-value 0.1094 — FAIL (n<50) (`BACKTEST_AND_TRACKING_PROTOCOL.md:42`).
- **Why emitted:** Tests whether funding-rate sentiment signals (the v4 funding-carry domain) transfer to commodity ETFs. Funding carry is a real but capital-intensive return stream (`SCORECARD.md:37-38`, `HYPOTHESES.md:28-30`). GLD funding_sentiment probes whether sentiment-based timing works on gold — a different market microstructure than crypto perps.
- **Research question:** Does funding sentiment carry any predictive power for GLD, or is it a crypto-specific artifact?

### Pick 5: SPY funding_sentiment (EQUITY / Sentiment Test)
- **Backtest:** n=6, WR 83.3%, PF 3.09, Sharpe 0.43, P-value 0.1094 — FAIL (n<50) (`BACKTEST_AND_TRacking_PROTOCOL.md:26`).
- **Why emitted:** Mirrors pick 4 but in the equity domain. SPY is the core EQUITY benchmark. Funding sentiment on SPY tests whether short-term sentiment flows have any edge on the most liquid equity ETF — the natural proving ground for any equity sentiment hypothesis.
- **Research question:** Is there a repeatable funding-sentiment edge on SPY, or does it wash out after costs?

**Common thread across all 5:** Each has n < 10 trades, `forward_test_only: true`, `forward_validated: false`, and lives in an asset class with `sizing_allowed: false`. None is a recommendation. Each is a small, time-boxed observation.

---

## 6. Explicit Kill Criteria for Each Pick

Kill criteria are drawn from `BACKTEST_AND_TRACKING_PROTOCOL.md:74-83` (Tier 1 Immediate Elimination), `BACKTEST_AND_TRACKING_PROTOCOL.md:152-171` (Auto-Expire + Manual Review), and `README.md:72-79` (Forward-Test Tracking Protocol). Each pick is subject to all of the following; any single trigger kills the pick.

### Universal kill criteria (apply to all 5 picks)

| # | Condition | Threshold | Action | Source |
|---|-----------|-----------|--------|--------|
| K1 | Stale data | entry_price mismatch > 5% from live feed | Kill immediately | `BACKTEST_AND_TRACKING_PROTOCOL.md:78` |
| K2 | Confidence-coupling | ml_score == confidence on >90% of picks | Kill immediately | `BACKTEST_AND_TRACKING_PROTOCOL.md:79` |
| K3 | PnL = 0% with price movement | exit_price ≠ entry_price but pnl_pct = 0 | Kill immediately | `BACKTEST_AND_TRACKING_PROTOCOL.md:80` |
| K4 | Blank fields | >3 missing fields (entry_price, direction, symbol, status) | Kill immediately | `BACKTEST_AND_TRACKING_PROTOCOL.md:81` |
| K5 | Negative PnL after 20 trades | cumulative PnL < 0 | Kill immediately | `BACKTEST_AND_TRACKING_PROTOCOL.md:82` |
| K6 | Sharpe < 0 after 20 trades | | Kill immediately | `BACKTEST_AND_TRACKING_PROTOCOL.md:83` |
| K7 | Stale OPEN | > 72 hours with no price update | Mark EXPIRED, pnl_pct = 0 | `BACKTEST_AND_TRACKING_PROTOCOL.md:158` |
| K8 | Stale OPEN | > 168 hours (1 week) | Mark EXPIRED, pnl_pct = 0, flag for review | `BACKTEST_AND_TRACKING_PROTOCOL.md:159` |
| K9 | Forward test limit | > 30 days open | Mark EXPIRED, pnl_pct = 0 | `BACKTEST_AND_TRACKING_PROTOCOL.md:160` |
| K10 | PnL freeze | entry_price == current_price for > 48h | Flag data issue, resolve or expire | `BACKTEST_AND_TRACKING_PROTOCOL.md:161` |
| K11 | Max hold exceeded | > max_hold_days for strategy type | Mark EXPIRED, pnl_pct = current | `BACKTEST_AND_TRACKING_PROTOCOL.md:162` |
| K12 | Consecutive losses | 3 losses in a row | Pause strategy, review | `BACKTEST_AND_TRACKING_PROTOCOL.md:168` |
| K13 | Weekly drawdown | > 5% weekly | Pause all strategies, review | `BACKTEST_AND_TRACKING_PROTOCOL.md:169` |
| K14 | Monthly drawdown | > 10% monthly | Halt all trading, full review | `BACKTEST_AND_TRACKING_PROTOCOL.md:170` |
| K15 | PnL anomaly | pnl_pct = 0 with price movement | Immediate investigation | `BACKTEST_AND_TRACKING_PROTOCOL.md:171` |

### Per-pick forward-test kill thresholds (Tier 2 watch-list)

Each pick enters Tier 2 (watch list, no capital) because n < 50. It remains there until either killed or promoted:

| Condition | Threshold | Source |
|-----------|-----------|--------|
| n < 50 trades | Keep tracking, do not allocate capital | `BACKTEST_AND_TRACKING_PROTOCOL.md:89` |
| PF between 0.8-1.5 | Watch, do not allocate | `BACKTEST_AND_TRACKING_PROTOCOL.md:90` |
| WR between 40-50% | Watch, do not allocate | `BACKTEST_AND_TRACKING_PROTOCOL.md:91` |
| Sharpe between 0-0.5 | Watch, do not allocate | `BACKTEST_AND_TRACKING_PROTOCOL.md:92` |

### Per-pick promotion-kill boundary (Tier 3 → Tier 4)

A pick can only graduate toward live capital if it clears **all** of:

| Gate | Threshold | Source |
|------|-----------|--------|
| n ≥ 100 forward picks | | `BACKTEST_AND_TRACKING_PROTOCOL.md:108` |
| PF ≥ 1.5 forward | | `BACKTEST_AND_TRACKING_PROTOCOL.md:109` |
| WR ≥ 55% forward | | `BACKTEST_AND_TRACKING_PROTOCOL.md:110` |
| DSR ≥ 0.95 forward | | `BACKTEST_AND_TRACKING_PROTOCOL.md:111` |
| 3+ months clean forward | | `BACKTEST_AND_TRACKING_PROTOCOL.md:112` |

Failing any one of these keeps the pick in Tier 3 (paper only) or kills it. No pick may skip tiers.

---

## 7. Graduation Path — What Would Need to Happen for Any Pick to Trade Live Capital

For any of the 5 picks (or any strategy-symbol pair derived from them) to graduate to live capital, the following must occur in sequence:

### Step 1: Fix measurement infrastructure (prerequisite for all)

All current PnL/WR numbers are untrustworthy due to measurement defects. Per `PROFITABILITY_FRAMEWORK.md:224-237` (Phase 1):

| # | Fix | File | Priority |
|---|-----|------|----------|
| 1 | Enable promotion gates (FDR + single-source) | `alpha_engine/money_ready_verdict.py` | P0 |
| 2 | Close cost gate fail-open paths | `alpha_engine/per_class_cost_gate.py` | P0 |
| 3 | Stop suppressing after-cost errors | `audit_trail/dashboard_generator.py` | P0 |
| 4 | Add weekly/monthly loss limits | `alpha_engine/risk_controls.py` | P0 |
| 5 | Fix entry_price integrity (~29% clean) | `alpha_engine/risk_controls.py` | P0 |
| 6 | Re-resolve entries from bar-aligned NEXT-bar | `tools/reresolve_intrabar.py` | P0 |
| 7 | Fix PnL unit normalization (ratio vs percent, 100×) | `quick_wins/shared/normalize_pnl_units.py` | P0 |
| 8 | Fix pick ID uniqueness | `quick_wins/shared/validate_pick_ids.py` | P0 |

Until these are fixed, no forward-test result can be trusted, and no pick can graduate.

### Step 2: The pick must accumulate clean forward-test data

Each pick must survive Tier 2 observation and reach Tier 3 eligibility:

- n ≥ 50 forward trades (currently n < 10 on all 5)
- PF ≥ 1.5 forward
- WR ≥ 50% forward
- Sharpe ≥ 0.5 forward
- MaxDD < 15% forward

Source: `BACKTEST_AND_TRACKING_PROTOCOL.md:96-102`, `README.md:89-96`.

### Step 3: The pick must clear Tier 4 live-capital gates

- n ≥ 100 forward picks
- PF ≥ 1.5 forward
- WR ≥ 55% forward
- DSR ≥ 0.95 forward
- 3+ months clean forward

Source: `BACKTEST_AND_TRACKING_PROTOCOL.md:104-112`, `README.md:98-105`.

### Step 4: The asset class must be unblocked

Even a perfect pick cannot trade if its class is blocked. Per `ASSET_CLASS_PROFITABILITY_PLANS.md`:

| Class | Blocker | Action Required to Unblock |
|-------|---------|---------------------------|
| EQUITY | n≥500, PF≥1.15, clean OOS, stability both halves vs SPY | Run pre-registered benchmark test vs SPY total return (`ASSET_CLASS_PROFITABILITY_PLANS.md:43-50`) |
| CRYPTO | Fix `kimi_riseoftheclaw` fill bug, then forward-test n≥100 | Fix entry_price integrity (`alpha_engine/risk_controls.py`), re-resolve from NEXT-bar entries (`tools/reresolve_intrabar.py`), then POSITION horizon forward test (`ASSET_CLASS_PROFITABILITY_PLANS.md:72-88`) |
| COMMODITY / BOND | Low n, cost/execution issues | Enable CFTC COT fetcher, populate data, add freshness guard (`ASSET_CLASS_PROFITABILITY_PLANS.md:119-125`) |

### Step 5: Pass the go/no-go decision

Per `README.md:124-135` and `PROFITABILITY_FRAMEWORK.md:362-373`:

**NO-GO for live capital deployment today.** Conditions to revisit:
1. Measurement gates pass.
2. Promotion gates fail closed (both env vars enabled).
3. EQUITY pre-registered test: vs SPY, n≥500, OOS Sharpe ≥ SPY Sharpe AND PF ≥ 1.15.
4. CRYPTO post-fix forward test: POSITION horizon n≥100, PF ≥ 1.3, WR ≥ 55%.
5. CI failures resolved.

**If both EQUITY and CRYPTO fail pre-registered tests, keep both blocked and preserve passive benchmark sleeve (ETF TAA).** (`README.md:135`, `PROFITABILITY_FRAMEWORK.md:373`)

### Bottom line on graduation

None of the 5 picks is on a path to live capital today. All 5 are pre-Tier-2 (n < 10), all classes are `sizing_allowed: false`, promotion gates are default OFF, and measurement infrastructure is known-defective. The earliest any pick could approach live capital is after Steps 1-5 complete — which, on the current roadmap (`ASSET_CLASS_PROFITABILITY_PLANS.md:173-181`), is a 90-day program whose success criterion is explicitly **not** "profitable" but rather "one class with a pre-registered, benchmark-relative result and known trial count."

---

## 8. Key Distinctions (Reference Table)

| Distinction | What It Means | Where Documented |
|-------------|---------------|------------------|
| Paper trading ≠ live trading | Paper picks use simulated positions with zero capital at risk. Live trading requires Tier 4 clearance. | `README.md:56-64`, `BACKTEST_AND_TRACKING_PROTOCOL.md:94-112` |
| Backtest ≠ forward test | Backtests are historical simulations (42 combinations, all failed). Forward tests are live-market observations (5 picks, all unvalidated). | `README.md:22-54`, `BACKTEST_AND_TRACKING_PROTOCOL.md:19-46` |
| Asset class coverage ≠ pick emission | The system covers 9 asset classes for research tracking; pick emission is a research activity independent of class profitability. All 9 classes are `sizing_allowed: false` regardless of picks. | `ASSET_CLASS_PROFITABILITY_PLANS.md:9`, `README.md:9` |
| Beta capture ≠ alpha generation | ETF TAA is validated smart-beta (the money track). Picks are unproven alpha hunt (the research track). | `PROFITABILITY_FRAMEWORK.md:195-203`, `ASSET_CLASS_PROFITABILITY_PLANS.md:93-110` |
| Research infrastructure ≠ money engine | The system emits picks, tracks performance, and runs gates — but is explicitly "a research infrastructure, not a money-ready engine." | `ASSET_CLASS_PROFITABILITY_PLANS.md:9` |

---

## 9. File References and Line Numbers

### Primary sources for the irony

| File | Lines | Relevance |
|------|-------|-----------|
| `2026-11-15_12AM_plan/flaxen-hair/README.md` | 9 | "No asset class is proven profitable. 0/23 hypotheses... All 9 classes return `sizing_allowed: false`." |
| `2026-11-15_12AM_plan/flaxen-hair/README.md` | 56-64 | Forward-Test Picks table — the 5 picks, all flagged PAPER TEST. |
| `2026-11-15_12AM_plan/flaxen-hair/README.md` | 72-79 | Forward-Test Tracking Protocol — kill fast / hold longer tiers. |
| `2026-11-15_12AM_plan/flaxen-hair/README.md` | 98-105 | Tier 4 Live Capital Eligible gates. |
| `2026-11-15_12AM_plan/flaxen-hair/README.md` | 124-135 | Go/No-Go decision — NO-GO today, conditions to revisit. |
| `research/profitability/SCORECARD.md` | 5 | "Outcome: NOT PROVED (honest negative) after 23 candidates across four versions." |
| `research/profitability/HYPOTHESES.md` | 83-86 | "No approach is PROVED... v3 (breadth) produced no edge; v4 (funding carry)... does not beat cash after realistic capital." |
| `2026-11-15_12AM_plan/flaxen-hair/02_holding_period_analysis/BACKTEST_AND_TRACKING_PROTOCOL.md` | 9 | "All backtests failed to produce a profitable strategy. 42 strategy-symbol combinations tested... None met the minimum gate." |
| `2026-11-15_12AM_plan/flaxen-hair/02_holding_period_analysis/BACKTEST_AND_TRACKING_PROTOCOL.md` | 23-62 | Full backtest results table — all 42 combinations FAIL, all n < 50. |
| `2026-11-15_12AM_plan/flaxen-hair/02_holding_period_analysis/BACKTEST_AND_TRACKING_PROTOCOL.md` | 74-83 | Tier 1 Immediate Elimination kill conditions. |
| `2026-11-15_12AM_plan/flaxen-hair/02_holding_period_analysis/BACKTEST_AND_TRACKING_PROTOCOL.md` | 85-103 | Tier 2 Watch List / Tier 3 Promotion Candidate gates. |
| `2026-11-15_12AM_plan/flaxen-hair/02_holding_period_analysis/BACKTEST_AND_TRACKING_PROTOCOL.md` | 104-112 | Tier 4 Live Capital Eligible gates. |
| `2026-11-15_12AM_plan/flaxen-hair/02_holding_period_analysis/BACKTEST_AND_TRACKING_PROTOCOL.md` | 152-171 | Auto-expiration and manual review triggers. |
| `2026-11-15_12AM_plan/flaxen-hair/01_asset_class_plans/ASSET_CLASS_PROFITABILITY_PLANS.md` | 9 | "Zero asset classes are currently proven profitable... All 9 classes return `sizing_allowed: false`. The system is a research infrastructure, not a money-ready engine." |
| `2026-11-15_12AM_plan/flaxen-hair/01_asset_class_plans/ASSET_CLASS_PROFITABILITY_PLANS.md` | 17-27 | Asset class priority ranking with blockers per class. |
| `2026-11-15_12AM_plan/flaxen-hair/01_asset_class_plans/ASSET_CLASS_PROFITABILITY_PLANS.md` | 31-60 | EQUITY plan — connors_rsi2 sole proven sleeve, t=1.52 p=0.12, pre-registered test vs SPY. |
| `2026-11-15_12AM_plan/flaxen-hair/01_asset_class_plans/ASSET_CLASS_PROFITABILITY_PLANS.md` | 63-90 | CRYPTO plan — fill bug `kimi_riseoftheclaw`, forward-test n≥100 post-fix. |
| `2026-11-15_12AM_plan/flaxen-hair/01_asset_class_plans/ASSET_CLASS_PROFITABILITY_PLANS.md` | 93-110 | ETF TAA — validated smart-beta, Sharpe 0.88 vs SPY 0.74, MaxDD −19% vs SPY −51%. |
| `2026-11-14_12AM_plan/flaxen-hair/01_asset_class_plans/ASSET_CLASS_PROFITABILITY_PLANS.md` | 184 | Class ranking table — ETF TAA primary track, all others blocked/conditional. |
| `final_v4/flaxen-hair_2026-11-15T0020/PROFITABILITY_FRAMEWORK.md` | 195-216 | ETF TAA as only validated approach; EQUITY secondary; CRYPTO conditional. |
| `final_v4/flaxen-hair_2026-11-15T0020/PROFITABILITY_FRAMEWORK.md` | 224-237 | Phase 1 measurement fixes (8 P0 items). |
| `final_v4/flaxen-hair_2026-11-15T0020/PROFITABILITY_FRAMEWORK.md` | 288-296 | Phase 3 benchmark tests — EQUITY vs SPY, CRYPTO vs BTC. |
| `final_v4/flaxen-hair_2026-11-15T0020/PROFITABILITY_FRAMEWORK.md` | 362-373 | Part 6 Go/No-Go decision — NO-GO today. |
| `alpha_engine/money_ready_verdict.py` | 18-22 | Verdict definitions: MONEY_READY / WATCH / NOT_READY / INSUFFICIENT_DATA. |
| `alpha_engine/money_ready_verdict.py` | 163 | `MONEY_READY_FDR_GATE` env var (defaults OFF). |
| `alpha_engine/money_ready_verdict.py` | 178 | `MONEY_READY_SINGLE_SOURCE_GATE` env var (defaults OFF). |

### Pick data files

| File | Relevance |
|------|-----------|
| `dashboard/live_picks.json` | Active picks dashboard output — contains the forward-test pick records with `forward_validated: false`, `forward_test_only: true` flags on research picks. |
| `multi_asset/data/multi_asset_picks.json` | Multi-asset forward-test picks — all entries carry `forward_test_only: true`, `forward_validated: false`, `forward_trades: 0`. |

---

## 10. Conclusion

The irony is resolved by recognizing that **pick emission and capital deployment are different activities governed by different gates.**

- **No asset class is proven profitable** — this is true and remains the system's standing position. 0/23 hypotheses across 4 protocol versions. All 9 classes `sizing_allowed: false`. ETF TAA is validated smart-beta, not alpha. EQUITY has a positive but statistically insignificant cost margin. CRYPTO is blocked by a fill bug. This determines where money may go: nowhere (except passive beta).
- **5 forward-test picks are emitted** — this is also true and does not contradict the first statement. The picks are hypothesis containers for forward-test observation at zero capital risk. All 5 have n < 10, `forward_test_only: true`, `forward_validated: false`. They are research instruments, not recommendations.

The gating system (P0-P4 promotion ladder, `sizing_allowed: false` per class, `MONEY_READY_FDR_GATE` / `MONEY_READY_SINGLE_SOURCE_GATE` fail-closed design) ensures that **no pick can reach live capital until it clears every gate** — and today, no pick has cleared even the first one.

Beta (mutual funds / ETF TAA) is the money deployment vehicle. Picks are the alpha hunt. The two tracks must never be conflated.
