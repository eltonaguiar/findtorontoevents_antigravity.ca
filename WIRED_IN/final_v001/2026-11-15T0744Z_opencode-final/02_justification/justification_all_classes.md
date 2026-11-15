# 02_PICK_JUSTIFICATION — All Asset Classes

**Date:** 2026-11-15T07:44Z UTC  
**Status:** FINAL — No picks justified for real-money deployment  
**Source:** All per-class specification files in `01_specification/`

---

## Summary Table

| Asset Class | Picks Justified? | Best Candidate | Gates Passed | Deployment Recommendation |
|-------------|-----------------|----------------|--------------|---------------------------|
| EQUITY | No | QQQ DualMA (2 trades) | 4/7* | Research slot only |
| CRYPTO | No | ADA-USD EMA Trend | 4/7 | Conditional — PBO=0.603 blocks |
| ETF | No | None | N/A | Blocked (cohort mismatch) |
| MUTUAL FUNDS | No | None (passive only) | N/A | Passive core allocation |
| FOREX | No | None | N/A | Mutation-before-kill |
| COMMODITY | No | None | N/A | Blocked — all 186 picks force-closed toxic |
| FUTURES | No | None | N/A | Blocked (WR=2.5%) |
| BOND | No | None | N/A | Blocked (insufficient data) |
| PENNY_STOCK | No | None | N/A | Keep blocked |
| MEME | No | None | N/A | Keep blocked |

\* QQQ DualMA 4/7 is statistical artifact (2 trades, PF=999, DSR=0, PBO=0.999).

**No picks are justified for real-money deployment.** The previously claimed COMMODITY copy-trader WR=93.8% edge was debunked — all 186 COMMODITY picks in `closed_picks.json` were force-closed toxic with pnl=0 (zero resolved trades). The claim was formally retracted on 2026-05-16 as a pre-dedup over-emission artifact.

---

## Justification Framework

Each pick was evaluated against 7 money-ready gates:

| Gate | Threshold |
|------|-----------|
| G1 | Profit Factor ≥ 1.15 |
| G2 | Win Rate ≥ 50% |
| G3 | Sharpe Ratio ≥ 1.0 |
| G4 | DSR ≥ 0.95 |
| G5 | PBO ≤ 0.10 |
| G6 | Max Drawdown < 15% |
| G7 | Trades ≥ 50 |

**Rule:** All 7 gates must pass for deployment consideration. Zero asset classes met this bar.

---

## Why No Picks Are Justified

### Primary Reason: No Statistical Edge

- **Information coefficient ≈ 0** — no correlation between predicted and actual returns
- **DSR ≈ 0** for nearly all strategies — no confidence any Sharpe > 0
- **PBO ≈ 0.999** — near-certain that any apparent edge is overfitting
- **Win rates near 40%** — below 50% break-even for most strategies
- **Profit factors < 1.0** for most strategies — gross losses exceed gross profits

### Secondary Reason: Costs Dominate Edge

- Round-trip costs (4 bps in simulation, higher in real markets) exceed average edge for most strategies
- RSI(2) swing rule: doubling costs turns it negative
- ETF: 267% of average PnL is cost
- Commodity: 422% cost ratio

### Tertiary Reason: Structural Incompatibility

- **Mutual funds:** daily NAV, no intraday TP/SL, load/12b-1 costs
- **Bonds:** n=1, insufficient data
- **Commodity:** n=7-229, no contract identity pipeline
- **Meme/Penny Stock:** n=10/n=1, toxic

---

## Per-Class Elimination Detail

### RSI(2) Mean Reversion (Equity)

**Eliminated because:**
- Tested on 7 equity ETFs over 2020-2025 (1,508 daily bars each)
- Net PnL: -118% to -186% across all symbols
- Win rate: 0% to 17% (far below 50% break-even)
- Profit factor: 0.002 to 0.148 (gross losses dwarf gross profits)
- Sharpe: -8.5 to -18.5 (deeply negative risk-adjusted return)
- DSR: 0.000 (no confidence Sharpe > 0)
- PBO: 0.999 (near-certain overfitting)
- Max drawdown: 117% to 180% (catastrophic)

**Previously famous** (Connors, 2008-2020 era) but the edge has completely decayed in the 2020-2025 regime.

### Dual MA Crossover (Equity)

**Eliminated because:**
- Tested on 7 equity ETFs over 2020-2025
- Only 2-5 trades per symbol over 5+ years — insufficient sample
- QQQ and EFA show PF=999 on 2-3 trades — statistical artifact, not tradable edge
- DSR: 0.000 for all symbols
- PBO: 0.999 for all symbols
- Net PnL: -2.9% to +22.3% (the positives are on 2 trades = noise)

### Bollinger Mean Reversion (Equity)

**Eliminated because:**
- Tested on 7 equity ETFs over 2020-2025
- Net PnL: -17.6% to -33.0%
- Win rate: 20% to 43% (below 50%)
- Profit factor: 0.05 to 0.15 (gross losses 7-20× gross profits)
- Sharpe: -1.2 to -2.0
- DSR: 0.000-0.061
- PBO: 0.999

### EMA Trend Crossover (Crypto)

**Eliminated because:**
- Tested on 5 crypto symbols over 2020-2025 (2,092-2,192 daily bars each)
- Net PnL: -18.2% to -130.7%
- Win rate: 33.3% to 46.9% (below 50%)
- Profit factor: 0.315 to 0.889 (below 1.15)
- Sharpe: -3.10 to -0.30 (negative on 4/5 symbols)
- DSR: 0.002 to 0.383 (all below 0.95)
- PBO: 0.979 to 0.999 (all above 0.10)
- Max drawdown: 79% to 153% (catastrophic)

**Best case (ADA-USD):** Passes 4/7 gates but fails Sharpe (-0.30), DSR (0.383), PBO (0.979). Max DD 79% — unacceptable.

### Donchian Channel Breakout (Crypto)

**Eliminated because:**
- Zero trades on all 5 crypto symbols (BTC, ETH, SOL, XRP, ADA) over 5+ years
- Strategy never generated an entry signal
- Not viable

### Donchian Channel Breakout (Crypto)

**Eliminated because:**
- Zero trades on all 5 crypto symbols (BTC, ETH, SOL, XRP, ADA) over 5+ years
- Strategy never generated an entry signal
- Not viable

### All ETF Strategies

**Eliminated because:**
- Cohort mismatch: Official PF 0.022 vs Registry PF 1.788 — 6×+ discrepancy
- Zero live ETF picks
- 267% of average PnL is cost
- 134 TIME_EXIT picks with forced pnl_pct=0
- Only 1 closed pick (QQQ, LOST at -0.01%)

### All Forex Strategies

**Eliminated because:**
- Historical PF 0.27 (sub-floor)
- Recent PF 0.85 (below break-even)
- WR 32-40%
- High n but negative expectancy
- MDD 82%
- Walk-forward OOS PF 0.4829 < 1.0
- Bootstrap CI crosses zero

### All Commodity Strategies

**Eliminated because:**
- COT contrarian gate failed 4/4 (OOS n=30, PF 0.861, mean net -0.45%/trade)
- 422% cost ratio for commodity
- Low n (7-229)
- No contract identity pipeline

### All Bond Strategies

**Eliminated because:**
- n=1 official — cannot support statistical inference
- n=35 registry — below minimum floor
- PF 0.000-0.586 — below break-even
- WR 0-37% — below 50%
- No data pipeline for bond backtesting

### All Meme/Penny Stock Strategies

**Eliminated because:**
- n=10/n=1 — toxic
- WR 0-10%, PF 0.023-0.000
- No legitimate edge

### All Mutual Fund Picks

**Eliminated because:**
- Structurally incompatible: daily NAV only, no intraday TP/SL
- Load/12b-1 costs destroy short-term edges
- Zero production infrastructure
- Class id = -1 (NOT_BUILT)
- `emit_now: False`, "Never promote as an active pick"

---

## Integrated Summary — Why No Asset Class Is Proven Profitable

| Asset Class | Best Candidate | Best PF | Best WR | Best n | Primary Blocker |
|-------------|----------------|---------|---------|--------|-----------------|
| EQUITY | QQQ DualMA | 7.45 (n=10) | 90.00% (n=10) | 10 | SPY gate failed (t=1.05), n < 100 |
| CRYPCO | ADA-USD EMA Trend | 0.889 | 46.67% | 30 | Negative expectancy, DSR=0.383, PBO=0.979 |
| ETF | QQQ Faber Tactical | 0.00 | 0.00% | 1 | Cohort mismatch, resolver bug |
| FOREX | multi_asset_copytrader | 0.6596 | 13.64% | 176 | Negative expectancy, MDD 82% |
| FUTURES | multi_asset_copytrader | undefined | 0.00% | 31 | All force-closed toxic, stale 246d |
| BOND | bond_duration_rotation | 0.000 | 0.00% | 1 | Insufficient data |
| COMMODITY | multi_asset_copytrader | undefined | 0.00% | 186 | All force-closed toxic |
| Mutual Funds | None | N/A | N/A | N/A | Not registered, daily NAV |
| PENNY_STOCK | skyrocket_detector | undefined | 0.00% | 0 | Not wired to production |

**No picks are justified for real-money deployment.** The previously claimed COMMODITY copy-trader WR=93.8% edge was debunked — all 186 COMMODITY picks in `closed_picks.json` were force-closed toxic with pnl=0 (zero resolved trades). The claim was formally retracted on 2026-05-16 as a pre-dedup over-emission artifact.

**The only capital deployment recommendation:** Low-cost index ETF/MF passive allocation (60% US equity, 20% international, 20% bonds/T-bills, ER ≤0.09%, turnover ≤20%, track record ≥10 years, no load, no 12b-1). Two of eight sample mutual funds pass hard gates (FXAIX at 0.015% ER/$0 min, SWTSX at 0.03% ER/$0 min).
