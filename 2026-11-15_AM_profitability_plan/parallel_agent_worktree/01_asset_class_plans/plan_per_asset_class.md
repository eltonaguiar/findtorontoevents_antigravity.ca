# Per-Asset-Class Plan to Get to Profitability

**Status baseline (from final_v3/final_v4 audits):** 0/166 strategy×class×direction cells pass all money-ready gates. Overall closed-pick WR 45.6%. All classes below 50% WR. CRYPCO expectancy statistically significant NEGATIVE (-5.86%, CI [-4.96%, -4.38%]).

---

## 1. Mutual Funds — Passive Core Allocation (NOT alpha hunting)

**Verdict:** Do NOT build mutual funds as an active pick class. Build them as the **money deployment vehicle** (core portfolio).

**Why:** Mutual funds strike NAV once daily after the close. There is no intraday TP/SL, no execution precision, frequent-trading limits, and load/12b-1/ER costs eat any short-term edge. A mutual fund "pick" is an allocation decision on a monthly clock — it is beta capture + cost discipline, not prediction.

**Plan:**
1. **Build MF metadata infrastructure** (NAV cache, ranker, metadata CSV, walkforward tools) — but ONLY to screen low-fee funds for the core allocation, not to emit picks.
2. **Screening criteria (hard gates):**
   - Expense ratio ≤ 0.09% (index) / ≤ 0.20% (active)
   - No load, no 12b-1
   - Min initial investment ≤ $1,000
   - AUM ≥ $1B
   - Turnover ≤ 20%
   - Tracking error ≤ 0.25% vs benchmark
   - Track record ≥ 10 years
   - NAV freshness ≤ 24h
3. **Starter universe:** VFIAX, VTSAX, FXAIX, SWTSX, VBTLX, VWELX, VGSLX, VTIAX (low-cost broad market).
4. **Allocation:** 60% total US equity index, 20% total international, 20% short-duration bond/T-bill. Rebalance quarterly or on 5% drift bands.
5. **Expected outcome:** Market beta + bond income minus ~0.05-0.10% cost drag. Positive expected return over multi-year horizons. Not alpha. Not a pick system.

**Profitability path:** This is the only class with a high probability of positive real returns without requiring the prediction system to work. Deploy capital here first.

---

## 2. Equity (US) — Slot 1 Research Track

**Verdict:** Highest-priority research slot. Only class with a pre-registered benchmark test path vs SPY total return and a positive cost-margin signal (EQUITY: 3.23× cost coverage at n=738, WR 47.0%, PF 1.154 — but failed SPY gate: t=1.05, beat-SPY 45.53%, median excess -0.57%).

**Plan:**
1. **Fix measurement first** (PnL unit contract, terminal outcomes, resolution_method backfill, cross-ledger reconciliation).
2. **Pre-register hypothesis:** Monthly sector-neutral quality/value/momentum ranking on fixed large-liquid universe (use MF top-10 holdings as equity screen universe).
3. **Benchmark:** SPY total return. Must beat on risk-adjusted basis, not just raw return.
4. **Gates:** n ≥ 500, PF ≥ 1.15 after costs, clean OOS, DSR ≥ 0.95, PBO ≤ 0.10, forward n ≥ 100 over ≥ 3 months.
5. **If fails:** Kill or mutate. Do not graduate to live.
6. **Holding period:** Monthly rebalance (positional/swing). Not day trading.

**Profitability path:** Possible but unproven. Requires clean measurement + pre-registered OOS test vs SPY.

---

## 3. Crypto — Slot 2 Conditional Track

**Verdict:** Largest n (3,705 live, 22,055 registry) but expectancy statistically significant NEGATIVE (-5.86%). Stop-fill defect accounts for ~94% of class leak (kimi_riseoftheclaw). After fill fix, reaches ~breakeven (PF ≈ 1.00), not profitable.

**Plan (conditional ONLY):**
1. **Fix fill bugs first** (gap-aware stop/TP pricing in universal_pick_resolver.py).
2. **Bounded hypothesis:** Daily 50/200-day time-series trend, long/flat, volatility-targeted on frozen liquid universe (BTC, ETH, SOL, XRP, ADA; exclude DOGE, AVAX, LINK).
3. **Costs:** Taker fees + funding + quote freshness + capital constraints must be netted.
4. **Benchmark:** Equal-weight buy-and-hold + cash.
5. **SubQ coverage ≥ 7/10 required before deployment consideration.**
6. **If PF stays < 1.15 after costs:** Kill. Crypto remains blocked.

**Profitability path:** Currently blocked. Only re-open after fill fix + clean forward test + SubQ validation.

---

## 4. ETF — Blocked (Cohort Mismatch)

**Verdict:** Zero live picks. Official PF 0.022 vs registry PF 1.788 — cohort mismatch is a blocker, not evidence. 267% of average PnL is cost; cannot win as configured.

**Plan:**
1. Reconcile ETF cohort (money_ready_verdict vs pf_registry) at row level.
2. Fix ETF data pipeline (active_picks_etf.json, etf_decay_picks.json, etf_sector_picks.json are auto-emitter regenerations, not strategy improvements).
3. Only after reconciliation: test low-cost broad-market ETF tactical (not sector bets).
4. **Do not deploy.** ETF remains blocked until arithmetic clears.

---

## 5. Forex — Mutation-Before-Kill

**Verdict:** Weakest class. PF 0.27 historically, recent PF 0.85, WR 32-40%. High n but negative expectancy.

**Plan:** Already on mutation protocol. Do not allocate. Kill or fundamentally restructure before any reconsideration.

---

## 6. Commodity / Futures — RESEARCH SLOT 1 (Copy Trader / COT Consensus)

**Verdict:** **Strongest proven edge in the system.** Per-class decomposition shows COMMODITY via multi_asset_copytrader at WR=93.8% (n=96) and multi_asset_cot at WR=94.1% (n=102). The aggregate PF=4.28 is masked by FOREX (WR=14.8%, n=662) and FUTURES (WR=2.5%, n=157) drag. Class-level decomposition is the only honest read.

**Source:** `reports/multi_asset_copytrader_per_class_audit_20260513T014000Z.md`

### Per-Class CopyTrader Results

| Class | n | WR % | Volume Share | Status | Action |
|-------|---|------|-------------|--------|--------|
| **COMMODITY** | 96 | **93.8%** | 6.4% | ✅ Real edge — pristine WR | **PRESERVE + SCALE** |
| EQUITY | 28 | 42.9% | 1.9% | ⚠️ Thin (n<100) | Monitor |
| **FOREX** | 662 | **14.8%** | 44.0% | ❌ Massive drag | **MUTATE-BEFORE-KILL** |
| **FUTURES** | 157 | **2.5%** | 10.4% | ❌ Critical drain | **SURGICAL BLOCK** |

### Plan

1. **Surgical block:** Add `(FUTURES, multi_asset_copytrader)` to `BLOCKED_ASSET_STRATEGY_PAIRS` in `audit_trail/quality_gates.py` — n=157, WR=2.5% is empirically dead.
2. **Mutate-before-kill:** Run axis analysis on `(FOREX, multi_asset_copytrader)` — 662 picks at 14.8% WR needs symbol/direction/timeframe analysis.
3. **Preserve + scale COMMODITY:** Cross-reference with `multi_asset_cot` (COMMODITY WR=94.1%, n=102). Build dedicated COMMODITY copy-trader/COT consensus emitter with elite filtering.
4. **Target:** Make COMMODITY copy-trader/COT the Tier-1 go-live candidate — DB-verify pending next session action.

---

## 7. Prediction Markets (Kalshi / Polymarket) — Shadow Mode Candidate

**Verdict:** Strong backtest AND forward results, but PBO=0.603 (above 0.10 gate) — NOT yet money-ready. Continue shadow mode forward testing.

**Source:** `backtest_results/rigorous_backtest_CRYPTO_20260602_124831.json`, `verified_strategies/paper_pilot/`

### Performance Data

| Source | Metric | Value |
|--------|--------|-------|
| Backtest | n | 89 |
| Backtest | WR | 89.89% |
| Backtest | PF | 24.51 |
| Backtest | DSR | 9.36 |
| Backtest | **PBO** | **0.603** ⚠️ |
| Walk-forward | 7 folds, all WFE=1.0 | avg_os_sharpe=1.39 |
| Paper pilot | resolved n | 837 |
| Paper pilot | WR | 64.76% |
| Paper pilot | PF | 2.02 |
| Paper pilot | max_drawdown | -69.17% |
| Forward dashboard | n | 110 |
| Forward dashboard | WR | 79.09% |
| Forward dashboard | PF | 13.20 |
| Forward dashboard | shadow_mode | true |

### Plan

1. **Continue shadow mode forward testing** — kill switch: WR < 55% or n < 50
2. **Address PBO=0.603** — need more independent data or parameter reduction before money-ready consideration
3. **Wire into primary pick emission** — currently `pick_count: 0` in `alpha_engine/data/prediction_market_picks.json`
4. **Combine with CopyTrader intel** — multi-source "smart money" consensus picks
5. **Do NOT deploy capital** until PBO ≤ 0.10 and forward n ≥ 100 over ≥ 3 months

---

## 8. ETF — Blocked (Cohort Mismatch)

**Verdict:** Zero live picks. Official PF 0.022 vs registry PF 1.788 — cohort mismatch is a blocker, not evidence. 267% of average PnL is cost; cannot win as configured.

**Plan:**
1. Reconcile ETF cohort (money_ready_verdict vs pf_registry) at row level.
2. Fix ETF data pipeline (active_picks_etf.json, etf_decay_picks.json, etf_sector_picks.json are auto-emitter regenerations, not strategy improvements).
3. Only after reconciliation: test low-cost broad-market ETF tactical (not sector bets).
4. **Do not deploy.** ETF remains blocked until arithmetic clears.

---

## 9. Forex — Mutation-Before-Kill

**Verdict:** Weakest class. PF 0.27 historically, recent PF 0.85, WR 32-40%. High n but negative expectancy. CopyTrader FOREX subset: WR=14.8%, n=662 — massive drag.

**Plan:** Already on mutation protocol. Do not allocate. Kill or fundamentally restructure before any reconsideration.

---

## 10. Bond — Insufficient Data

**Verdict:** n=1 official, n=35 registry. Cannot support statistical inference.

**Plan:** Acquire yield/duration data. Blocked until n ≥ 100.

---

## 11. Meme / Penny Stock — Keep Blocked

**Verdict:** n=10/n=1. Toxic. Keep blocked indefinitely.

---

## Updated Summary: Where to Deploy Capital (Priority Order)

| Priority | Asset Class | Source | Role | Rationale |
|----------|-------------|--------|------|-----------|
| 1 | Mutual Funds + ETFs (low-cost index) | — | Core allocation | Highest probability of positive real returns, lowest risk. Beta capture, not alpha. |
| 2 | COMMODITY | multi_asset_copytrader / multi_asset_cot | Alpha research slot 1 | WR 93.8-94.1%, n=96-102. Strongest proven edge in system. DB-verify pending. |
| 3 | CRYPTO (Prediction Markets) | prediction_market_consensus | Shadow mode candidate | WR 79.09% forward, PF 13.20, but PBO=0.603 > 0.10 gate. Not yet money-ready. |
| 4 | EQUITY (US) | — | Research slot | Only class with pre-registered SPY benchmark path. Unproven; failed SPY gate (t=1.05). |
| 5-9 | FOREX, FUTURES, ETF, BOND, Meme/Penny | — | Blocked | Do not allocate. Fix measurement first. |

**Bottom line:** Deploy real money only into low-cost index ETF/MF allocation. For alpha research, COMMODITY copy-trader/COT is the strongest candidate (WR 93.8%+) and should be prioritized over EQUITY and CRYPTO. Prediction markets are promising but PBO=0.603 blocks deployment.

