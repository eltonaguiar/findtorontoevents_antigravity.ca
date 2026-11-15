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

## 6. Commodity / Futures — BLOCKED (Copy Trader Claims Debunked)

**Verdict:** BLOCKED. No proven edge. The previously claimed COMMODITY copy-trader WR=93.8% (n=96) was **debunked on 2026-05-16** as a pre-dedup over-emission artifact (46× over-emission on CT=F cotton).

**Source:** `alpha_engine/data/closed_picks.json` (ground truth), `reports/commodity_deep_dive_swarm_2026-05-16.md` (retraction)

### Ground Truth from closed_picks.json

| Metric | Value |
|--------|-------|
| multi_asset_copytrader COMMODITY picks | 186 |
| Resolved wins | 0 |
| Resolved losses | 0 |
| All statuses | "CLOSED" (force-closed toxic) |
| All pnl_pct | 0.0 |
| All exit_reason | "FORCE_CLOSED_TOXIC" |
| Effective WR | 0% (0/0 resolved) |

**The 93.8% claim does NOT hold up.** All 186 COMMODITY copy-trader picks were force-closed with zero PnL — none were ever resolved with an actual trading outcome. The claim was formally retracted on 2026-05-16 (post-dedup WR collapsed to ~40%, PF to 0.17). DB-level data shows n=635 WR=34.3% PF=0.74 — a consistent loser.

### Per-Class CopyTrader Results (Ground Truth)

| Class | n | WR | Status | Action |
|-------|---|-----|--------|--------|
| **COMMODITY** | 186 | 0% (unresolved) | ❌ All force-closed toxic | **BLOCKED** |
| EQUITY | 28 | 42.9% | ⚠️ Thin (n<100) | Monitor |
| **FOREX** | 160 | 12.5% (win/total) | ❌ Massive drag | **MUTATE-BEFORE-KILL** |
| **FUTURES** | 31 | 0% (unresolved) | ❌ All force-closed toxic | **SURGICAL BLOCK** |

### Plan

1. **Surgical block:** Add `(FUTURES, multi_asset_copytrader)` to `BLOCKED_ASSET_STRATEGY_PAIRS` in `audit_trail/quality_gates.py` — WR=0% n=31, all force-closed toxic.
2. **Mutate-before-kill:** Run axis analysis on `(FOREX, multi_asset_copytrader)` — 160 picks at 12.5% WR needs symbol/direction/timeframe analysis.
3. **COMMODITY:** Blocked — no resolved trades, all force-closed toxic. Do not allocate.
4. **Target:** No commodity copy-trader candidate is viable for deployment.

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
| 2 | CRYPTO (Prediction Markets) | prediction_market_consensus | Shadow mode candidate | WR 79.09% forward, PF 13.20, but PBO=0.603 > 0.10 gate. Not yet money-ready. |
| 3 | EQUITY (US) | — | Research slot | Only class with pre-registered SPY benchmark path. Unproven; failed SPY gate (t=1.05). |
| 4-9 | COMMODITY, FOREX, FUTURES, ETF, BOND, Meme/Penny | — | Blocked | COMMODITY copy-trader claims debunked (all 186 picks force-closed toxic). Do not allocate. Fix measurement first. |

**Bottom line:** Deploy real money only into low-cost index ETF/MF allocation. No alpha source has passed all money-ready gates. COMMODITY copy-trader claims (WR=93.8%) were debunked — all 186 picks were force-closed toxic with zero PnL. Prediction markets are promising but PBO=0.603 blocks deployment.

