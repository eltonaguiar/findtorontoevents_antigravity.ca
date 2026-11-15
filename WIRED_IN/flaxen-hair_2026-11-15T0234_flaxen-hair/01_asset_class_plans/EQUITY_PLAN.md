# EQUITY Asset Class Trading Plan — P0 Proof-First Protocol

**Worktree:** flaxen-hair_2026-11-15T0234_flaxen-hair
**Date:** 2026-11-15T02:34:00Z
**Repo:** findtorontoevents_antigravity.ca
**Path:** `WIRED_IN/flaxen-hair_2026-11-15T0234_flaxen-hair/01_asset_class_plans/EQUITY_PLAN.md`
**Author:** Kilo (senior quant researcher)
**Status:** DRAFT — pre-registered, not money-ready

---

## 0. Executive Summary

**No asset class is proven profitable.** 0/23 hypotheses across 4 protocol versions survived clean out-of-sample, effective-N, capital, and execution gates. All 9 classes return `sizing_allowed: false`.

**EQUITY is the #1 research candidate** — the only class with a positive cost margin (3.23x), positive mean return (+0.323% per trade), and the best aggregate metrics (PF=1.52, WR=56.92%, Sharpe=1.19, n=130 trades across backtests). But n=130 is still below the n≥500 bar for promotion, and per-strategy breakdowns are not yet available. EQUITY is **not** money-ready today.

This document is the pre-registered plan to take EQUITY from "unproven candidate" to "live capital eligible" — or to kill it definitively. It contains:

1. Asset Class Analysis — why equity is #1
2. Strategy Inventory — all equity strategies from `alpha_engine/equity_strategies.py` and `multi_asset/equity_strategies.py` with parameters, expected edge, status
3. P0-First Rule — proof gates with code snippets (no live capital until all pass)
4. Forward-Test Plan — specific picks, entry/exit rules, position sizing (max 2% risk per trade)
5. Kill Gates — when to kill a strategy
6. Ranking of strategies to test first — ranked by backtest PF, then WR, then Sharpe

**Zero live capital is deployed under this plan until every P0 gate passes.**

---

## 1. Asset Class Analysis — Why EQUITY Is the #1 Candidate

### 1.1 Current State of All Asset Classes (Audit Result)

| Rank | Asset Class | Cost Margin | Mean Return | Best PF | Best Sharpe | n | Status |
|------|-------------|-------------|-------------|---------|-------------|---|--------|
| 1 | **EQUITY (US)** | **3.23x** | **+0.323%** | **1.52** | **1.19** | **738 closed picks / 130 backtest trades** | **#1 candidate, not proven** |
| 2 | CRYPTO | Negative | Negative | <1.0 | <0.5 | 1154 clean | Blocked (fill bug) |
| 3 | ETF Tactical | N/A (allocation) | N/A | N/A | 0.88 (validated) | N/A | Smart-beta, not alpha |
| 4 | FOREX | Negative | Negative | 0.29 | <0.5 | N/A | Blocked |
| 5 | COMMODITY/BOND | Negative | Negative | <1.0 | <0.5 | n<60 | Blocked |
| 6 | FUTURES | Negative | -96% | <1.0 | <0.5 | N/A | Retired |
| 7 | MEMECOIN/PENNY | Negative | Negative | 0.50 | <0.5 | N/A | Quarantined |
| 8 | PREDICTION MARKETS | Zero-sum | Negative | <1.0 | <0.5 | N/A | Structurally rejected |
| 9 | MUTUAL FUNDS | N/A | N/A | N/A | N/A | N/A | No infrastructure |

**Key numbers (from audit, repo-verified):**
- **Cost margin: 3.23x** — gross edge exceeds transaction costs by 3.23×. This is the only class where expected profit after costs is positive.
- **Mean return: +0.323%** per closed pick — positive expectancy before slippage.
- **n = 738 closed picks** — the largest clean sample of any class, though per-strategy n is still small.
- **Best Sharpe: 1.19** — above the 1.0 "good equity fund" reference point, but on n=130 (statistically weak).
- **Best PF: 1.52** — above the 1.5 P0 gate, but again on small n.
- **WR: 56.92%** — above the 55% P0 gate, but again on small n.
- **t=1.52, p=0.12** — NOT statistically significant (p > 0.05). The edge could be luck.
- **Second-half PF degradation: 1.342 → 0.977** — regime risk; edge decays in the second half of the sample.

### 1.2 Why Equity Wins Over Alternatives

| Factor | Equity | Crypto | Forex | Commodity | Prediction Markets |
|--------|--------|--------|-------|-----------|-------------------|
| Cost margin | **Positive 3.23x** | Negative | Negative | Negative (422%) | Zero-sum - fees |
| Benchmark clarity | SPY total return | BTC buy-and-hold | None clean | None | None |
| Data quality | Clean, split/dividend adjusted | Broken entry_price (~29% clean) | Spread-heavy | COT data missing | N/A |
| Academic rationale | Momentum, value, mean reversion (Jegadeesh & Titman 1993, Asness et al. 2019, Connors & Alvarez 2008) | Weak | Weak | CTA carry | None (zero-sum) |
| Short-selling constraints | Borrow constraints exist but manageable | N/A | N/A | N/A | N/A |
| Survivorship bias risk | Manageable with point-in-time universe | High | Medium | High | N/A |

### 1.3 What Must Be True Before Equity Gets Capital

1. **Per-strategy n ≥ 100** (currently only aggregate n=130 known; per-strategy breakdown TBD).
2. **PF ≥ 1.5** per strategy, not just aggregate.
3. **WR ≥ 55%** per strategy.
4. **Sharpe ≥ 0.5** per strategy (annualized, net of costs).
5. **MaxDD ≤ 15%** per strategy.
6. **Deflated Sharpe Ratio ≥ 0.95** (multiple-testing correction across all equity strategies).
7. **Bootstrap CI for mean return excludes zero** (95% CI).
8. **Stability: first-half PF / second-half PF ≥ 0.95** (no regime decay).
9. **Beats SPY total return** after costs on clean out-of-sample / forward data.
10. **PnL normalization fixed** (ratio format, not percent — no 100× bug).

If ANY gate fails → EQUITY stays blocked; hold SPY/QQQ index or low-cost ETFs instead.

---

## 2. Strategy Inventory — All Equity Strategies

### 2.1 File: `alpha_engine/equity_strategies.py` (16 strategies + community)

**Path:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/flaxen-hair/alpha_engine/equity_strategies.py`

**Signature:** `(data: dict[str, pd.DataFrame]) -> list[dict]` — receives all equity OHLCV DataFrames, returns signal list.

| # | Strategy | Universe | Entry Condition | Exit / TP / SL | Position Sizing | Expected Edge | Status |
|---|----------|----------|-----------------|----------------|-----------------|---------------|--------|
| 1 | `momentum_factor_12m` | All EQUITY_SYMBOLS (top quartile by 12m mom, skip last 21d) | 12m return (skip last month) > 0.05, above 50d SMA, RSI(14) ≤ 70 | TP = entry + 3×ATR; SL = entry - 1.5×ATR | CATEGORY_RISK per category | Jegadeesh & Titman 1993; Sharpe ~0.9-1.3 | Unproven |
| 2 | `penny_volume_breakout` | Penny stocks only | Close > 20d high AND volume > 4× avg | TP = entry + 4×ATR; SL = high_20d × 0.97 | Penny risk (-6%, +12%, 10d) | Penny breakout momentum | Unproven |
| 3 | `meme_social_velocity` | Meme stocks only | 3d consecutive volume increase, vol > 3× avg, close > 10d high | TP = entry + 5×ATR; SL = entry - 2×ATR | Meme risk | Behavioral (Barber & Odean 2008) | Unproven |
| 4 | `quality_value_composite` | Stock category only | Composite score (stability 30% + trend R² 40% + value 30%), above 200d SMA, RSI ≤ 75 | TP = entry + 3×ATR; SL = entry - 1.5×ATR | Stock risk (-6%, +12%, 10d) | Asness/Frazzini/Pedersen 2019 QMJ | Unproven |
| 5 | `intermarket_risk_on` | High-beta tech: NVDA, TSLA, AMD, COIN, MSTR | SPY & QQQ above 20d SMA, SPY 20d vol declining | TP = entry + 3.5×ATR; SL = entry - 1.5×ATR | Per-category risk | Cross-asset momentum (Asness 2013) | Unproven |
| 6 | `support_resistance_bounce` | All EQUITY_SYMBOLS | Price within 0-2.5% of support, close > prev close, vol ≥ 1×, RSI ≤ 60 | TP = nearest resistance or entry + 3×ATR; SL = support × 0.97 | Per-category risk | Classical charting (Edwards & Magee 1948) | Unproven |
| 7 | `connors_rsi2_scanner` | SPY, QQQ, IWM, AAPL, MSFT, NVDA, AMD, AMZN, TSLA, META, GOOGL, COIN, MSTR, ES=F, NQ=F | RSI(2) < 5, close > SMA(200), RSI(14) ≥ 25 | TP = entry + 3×ATR; SL = entry - 1.5×ATR | Stock/futures risk | **PROVEN sleeve:** SPY 75.7% WR p=6e-6 (5yr); QQQ 75.3% WR p=8e-6 | **SHADOW ONLY — n<50 forward** |
| 8 | `connors_rsi2_short_scanner` | SPY, QQQ, IWM only | RSI(2) > 95, close < SMA(200), RSI(14) < 75 | TP = entry - 1.5×ATR; SL = entry + 0.75×ATR | Stock risk | Symmetric mirror of #7; confidence capped 0.65 | Shadow only; n<50 rule |
| 9 | `equity_two_bar_rsi_reversal` | MSFT, META, ADBE, AAPL, GOOGL, AMZN, NVDA, SPY, QQQ, IWM | 2 consecutive down closes, RSI(2) < 25, close > EMA(200) | TP = entry + 1.8×ATR; SL = entry - 1.0×ATR | Stock risk | **Backtest:** META PF=1.83 WR=51% n=243; MSFT PF=1.54 WR=52% n=230; ADBE PF=1.66 WR=57% n=173 | **Opt-in shadow** (EQUITY_RSI2_TWOBAR_ENABLED=1, default OFF) |
| 10 | `triple_rsi_scanner` | SPY, QQQ, AAPL, MSFT, NVDA, AMD | RSI(2)<10 AND RSI(5)<20 AND RSI(10)<30, close > SMA(200) | TP = entry + 3.5×ATR; SL = entry - 1.5×ATR | Stock risk | Published: 90% WR, PF=5.0 (20yr SPY, QuantifiedStrategies); Our 5yr: SPY 75% WR (12 trades) | Unproven (tiny n) |
| 11 | `vix_spike_reversal_scanner` | SPY | VIX close > 28 AND (VIX spike >15% OR sustained >30 for 2d) | TP = entry + 4×ATR; SL = entry - 2×ATR | Stock risk | **PROVEN:** 10yr backtest 72% WR, avg +2.24%, Sharpe 6.20, p=0.022 | Shadow only |
| 12 | `turn_of_month_scanner` | SPY, QQQ, ES=F, NQ=F | Last biz day of month + first 3 biz days of next month | TP = entry + 2.5×ATR; SL = entry - 1.2×ATR | Stock/futures risk | Lakonishok & Smidt 1988: +0.23% avg, p<0.01, 90yr | Unproven |
| 13 | `earnings_gap_reversal_scanner` | Sector ETFs (XLK, XLV, XLF, XLY, XLI, XLE, XLP, XLB, XLU, XLRE, XLC) | Gap down >4% on 2× volume | TP = entry × 1.03; SL = entry × 0.98 | Stock risk | Ball & Brown 1968: +2.3% mean reversion 5d | Unproven |
| 14 | `gap_reversal_tech_stocks` | AAPL, MSFT, NVDA, TSLA, AMD, AMZN, META, GOOGL, COIN, MSTR | Gap down >3% on >1.5× volume, RSI(14) 20-65, close > 90% of SMA200 | TP = entry + 3×ATR; SL = entry - 1.5×ATR | Stock risk | Bremer & Sweeney 1991 JF: +8.1% avg 5d, 75% WR (n=132) | Unproven |
| 15 | `optimized_stock_momentum` | GOOGL, MSFT, NVDA, AAPL, AMD, META, TSLA | RVOL(20) > 1.5, close > EMA9 & EMA20 & SMA50, ADX(14) > 20 | TP = entry + 3×ATR; SL = entry - 2×ATR | Stock risk | Mar 2026 backtest: GOOGL 100% WR, MSFT 66% WR | Unproven |
| 16 | `regime_filtered_momentum` | (conditional import) | See `alpha_engine/regime_filtered_momentum.py` | TBD | TBD | TBD | Conditional — module may not import |
| + | `COMMUNITY_EQUITY_STRATEGIES` | (from `community_strategies` module) | TBD | TBD | TBD | TBD | TBD — review `community_strategies.py` |

**Registration:** All strategies in `_RAW_EQUITY_STRATEGIES` are wrapped by `_wrap_with_factor_model` (applies `equity_factor_model.enhance_equity_confidence` if available) and exported as `EQUITY_STRATEGIES`. `regime_filtered_momentum` is added only if the module imports successfully.

### 2.2 File: `multi_asset/equity_strategies.py` (7 strategies)

**Path:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/flaxen-hair/multi_asset/equity_strategies.py`

**Signature:** `(df: pd.DataFrame, symbol: str, info: dict, **kwargs) -> list[dict]` — per-symbol, per-strategy. Orchestrated by `run_all_equity_strategies(data, vix_data, spy_data)`.

**Symbol universes:**
- `BLUE_CHIPS` (24): AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, JPM, V, JNJ, PG, UNH, HD, MA, KO, PEP, MRK, ABBV, CRM, COST, WMT, DIS
- `SECTOR_ETFS` (11): XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLB, XLRE, XLC
- `INDEX_ETFS` (4): SPY, QQQ, IWM, DIA
- `LEVERAGED_ETFS_3X` (43): TQQQ, SQQQ, SPXL, SPXS, UPRO, SPXU, TNA, TZA, UDOW, SDOW, FAS, FAZ, SOXL, SOXS, ERX, ERY, LABU, LABD, CURE, DRN, DRV, DPST, WDRW, RETL, NAIL, NUGT, DUST, JNUG, JDST, GUSH, DRIP, UVXY, SVXY, VIXY, YINN, YANG, EDC, EDZ
- `DIVIDEND_ARISTOCRATS` (19): PG, JNJ, KO, PEP, MMM, ABT, ABBV, T, XOM, CVX, MCD, WMT, CL, EMR, SHW, ADP, BDX, ITW, ED, GPC
- `GROWTH_BASKET` (13): NVDA, TSLA, META, AMZN, CRM, AMD, SNOW, NET, SHOP, SQ, DDOG, CRWD

**Risk parameters (`EQUITY_RISK`):**
| Category | Stop Loss | Take Profit | Max Hold Days |
|----------|-----------|-------------|---------------|
| stock | -6% | +12% | 10 |
| blue_chip | -4% | +8% | 7 |
| etf | -5% | +10% | 15 |
| sector_etf | -5% | +10% | 20 |
| aristocrat | -4% | +8% | 20 |

| # | Strategy | Universe | Entry Condition | TP / SL | Expected Edge | Status |
|---|----------|----------|-----------------|---------|---------------|--------|
| 1 | `earnings_momentum_pead` | stock, etf cats | Gap up >3% on >2× volume in last 10d, price held above gap, above SMA50, RSI ≤ 75, earnings gate (in window or unknown) | TP = entry + 3×ATR; SL = max(gap_open×0.97, entry - 2×ATR) | Ball & Brown 1968; Bernard & Thomas 1989 PEAD | Unproven |
| 2 | `sector_rotation` | Sector ETFs only | Bottom 30% by 20d return, RSI turning up from <35, above SMA200 | TP = entry + 3×ATR; SL = entry × (1 - 0.05) | Faber 2007; Moskowitz & Grinblatt 1999 | Unproven |
| 3 | `blue_chip_mean_reversion` | BLUE_CHIPS only | LONG: RSI(2) < 10, close > SMA200, 6m return > 0. SHORT: RSI(2) > 95, close < SMA200, 6m return < 0 | TP = SMA5 (or entry×1.04); SL = entry ± 2×ATR | Connors & Alvarez 2009; Connors 2009 | Unproven |
| 4 | `vix_market_timing` | INDEX_ETFS only | Regime 1: VIX>30 dropping >5%. Regime 2: VIX 20-30 crossing below 20d SMA. Regime 3: VIX<12 rising, price below SMA10 (SHORT) | Regime 1: TP=entry+4×ATR, SL=entry-2.5×ATR. Regime 2: TP=entry+3×ATR, SL=entry-2×ATR. Regime 3: TP=entry-2.5×ATR, SL=entry+1.5×ATR | Ang et al. 2006; Whaley 2000 | Unproven |
| 5 | `dividend_aristocrat_defense` | Aristocrats + Growth basket | BEAR regime: aristocrat above SMA200, RSI ≤ 70. BULL regime: growth above SMA50, RSI < 45, bouncing | Aristocrat: TP=entry+2.5×ATR, SL=entry-1.5×ATR. Growth: TP=entry+3.5×ATR, SL=entry-2×ATR | Ang 2014; O'Shaughnessy 2012 | Unproven |
| 6 | `gap_fill_reversion` | stock, etf cats | Gap down -2% to -5% on <2× volume, above SMA200 | TP = prev_close (gap fill); SL = entry - 1.5×ATR | Doran/Peterson/Wright 2008 overnight gap anomaly | Unproven |
| 7 | `etf_relative_strength` | ETF cat only | Top 30% by 1m return, positive momentum, RSI(14) 30-55, above SMA50 | TP = entry + 3×ATR; SL = entry - 2×ATR | Antonacci 2012 Dual Momentum | Unproven |

### 2.3 Strategies Requiring Cross-Asset Data

| Strategy | Required Kwargs | Source |
|----------|----------------|--------|
| `sector_rotation` | `sector_data` (dict of sector ETF DataFrames) | Built in `run_all_equity_strategies` |
| `etf_relative_strength` | `etf_data` (dict of all ETF DataFrames) | Built in `run_all_equity_strategies` |
| `vix_market_timing` | `vix_data` (^VIX DataFrame) | Passed from caller |
| `dividend_aristocrat_defense` | `spy_data` (SPY DataFrame), `vix_data` | Passed from caller |
| `vix_spike_reversal_scanner` | `^VIX` in data dict | Fetches via yfinance if missing |

### 2.4 Strategies with Opt-In / Shadow Status

| Strategy | Opt-In Mechanism | Default | Reason |
|----------|-----------------|---------|--------|
| `equity_two_bar_rsi_reversal` | `EQUITY_RSI2_TWOBAR_ENABLED=1` env var | OFF | 14-day shadow period; backtested PF=1.54-1.83 but needs forward validation |
| `connors_rsi2_short_scanner` | None (always registered) | Active but confidence-capped | n<50 rule; confidence capped 0.65; raise to 0.78 after n≥50 forward |
| `regime_filtered_momentum` | Module import success | Conditional | May not import; review if needed |

### 2.5 Strategy Inventory — Data Gaps to Fill Before Testing

For each strategy, the following must be computed from closed-pick ledger before ranking:

| Strategy | Backtest PF | Backtest WR | Backtest Sharpe | Backtest n | Forward n | Status |
|----------|-------------|-------------|-----------------|------------|-----------|--------|
| momentum_factor_12m | TBD | TBD | TBD | TBD | TBD | Measure |
| penny_volume_breakout | TBD | TBD | TBD | TBD | TBD | Measure |
| meme_social_velocity | TBD | TBD | TBD | TBD | TBD | Measure |
| quality_value_composite | TBD | TBD | TBD | TBD | TBD | Measure |
| intermarket_risk_on | TBD | TBD | TBD | TBD | TBD | Measure |
| support_resistance_bounce | TBD | TBD | TBD | TBD | TBD | Measure |
| connors_rsi2_scanner | TBD (SPY 75.7% WR published) | TBD | TBD | TBD | TBD | Shadow |
| connors_rsi2_short_scanner | TBD | TBD | TBD | TBD | TBD | Shadow |
| equity_two_bar_rsi_reversal | 1.54-1.83 | 51-57% | TBD | 173-243 | TBD | Opt-in shadow |
| triple_rsi_scanner | 5.0 (published) | 90% (published) | TBD | 12 (our 5yr) | TBD | Measure |
| vix_spike_reversal_scanner | TBD | 72% (10yr published) | 6.20 (10yr published) | TBD | TBD | Shadow |
| turn_of_month_scanner | TBD | TBD | TBD | TBD | TBD | Measure |
| earnings_gap_reversal_scanner | TBD | TBD | TBD | TBD | TBD | Measure |
| gap_reversal_tech_stocks | TBD | ~70% (published) | TBD | TBD | TBD | Measure |
| optimized_stock_momentum | TBD | GOOGL 100%, MSFT 66% | TBD | TBD | TBD | Measure |
| regime_filtered_momentum | TBD | TBD | TBD | TBD | TBD | Measure (if imports) |
| earnings_momentum_pead | TBD | TBD | TBD | TBD | TBD | Measure |
| sector_rotation | TBD | TBD | TBD | TBD | TBD | Measure |
| blue_chip_mean_reversion | TBD | TBD | TBD | TBD | TBD | Measure |
| vix_market_timing | TBD | TBD | TBD | TBD | TBD | Measure |
| dividend_aristocrat_defense | TBD | TBD | TBD | TBD | TBD | Measure |
| gap_fill_reversion | TBD | TBD | TBD | TBD | TBD | Measure |
| etf_relative_strength | TBD | TBD | TBD | TBD | TBD | Measure |

**Action:** Run `backtest_framework.py` or equivalent on each strategy, record results, then rank (Section 6).

---

## 3. P0-First Rule — Proof Gates (No Live Capital Until All Pass)

### 3.1 The Eight Gates

| Gate | Requirement | Current Equity Status | Pass/Fail |
|------|-------------|----------------------|-----------|
| G1 | n ≥ 100 closed trades (per strategy) | Aggregate n=130; per-strategy TBD | **MEASURE** |
| G2 | Profit Factor ≥ 1.5 (net of costs) | Aggregate PF=1.52; per-strategy TBD | **MEASURE** |
| G3 | Win Rate ≥ 55% | Aggregate WR=56.92%; per-strategy TBD | **MEASURE** |
| G4 | Sharpe ≥ 0.5 (annualized, net) | Aggregate Sharpe=1.19; per-strategy TBD | **MEASURE** |
| G5 | Max Drawdown ≤ 15% | TBD per strategy | **MEASURE** |
| G6 | Deflated Sharpe Ratio ≥ 0.95 | TBD | **MEASURE** |
| G7 | Bootstrap 95% CI for mean return excludes zero | TBD | **MEASURE** |
| G8 | Stability: first-half PF / second-half PF ≥ 0.95 | Aggregate: 1.342 → 0.977 (ratio 0.728, FAILS) | **FAILS** |

**Aggregate G8 already fails** (0.728 < 0.95). This means even if per-strategy metrics pass, the class-level regime decay is a red flag. Per-strategy stability must still be verified.

### 3.2 Code Snippets — Metric Computation (Ratio Format, Not Percent)

**CRITICAL: PnL must be stored as a ratio (decimal), not a percent.** A 2% gain is `0.02`, not `2.0`. The repo has had a 100× PnL normalization bug; this document fixes it by mandating ratio format everywhere.

```python
# =========================================================================
# PnL COMPUTATION — RATIO FORMAT (decimal, not percent)
# =========================================================================

def compute_trade_pnl(entry_price: float, exit_price: float, direction: str,
                      commission_bps: float = 1.0, slippage_bps: float = 1.0) -> float:
    """
    Compute PnL as a RATIO (decimal), e.g. 0.02 = +2%.
    
    Args:
        entry_price: entry price
        exit_price: exit price (TP, SL, or time-exit price)
        direction: "LONG" or "SHORT"
        commission_bps: commission in basis points per side (default 1bp = 0.01%)
        slippage_bps: slippage in basis points per side (default 1bp)
    
    Returns:
        PnL ratio (positive = profit, negative = loss)
    """
    if entry_price <= 0 or exit_price <= 0:
        return 0.0  # invalid trade
    
    # Gross PnL ratio
    if direction == "LONG":
        gross_pnl = (exit_price - entry_price) / entry_price
    else:  # SHORT
        gross_pnl = (entry_price - exit_price) / entry_price
    
    # Costs: commission + slippage on entry AND exit (2 sides)
    total_cost_bps = 2 * (commission_bps + slippage_bps)  # e.g. 4 bps round trip
    cost_ratio = total_cost_bps / 10000.0  # 4 bps = 0.0004
    
    net_pnl = gross_pnl - cost_ratio
    return net_pnl


def compute_trade_pnl_from_json(pick: dict, exit_price: float,
                                commission_bps: float = 1.0,
                                slippage_bps: float = 1.0) -> float:
    """Compute PnL from a pick JSON dict."""
    return compute_trade_pnl(
        entry_price=pick["entry_price"],
        exit_price=exit_price,
        direction=pick["direction"],
        commission_bps=commission_bps,
        slippage_bps=slippage_bps,
    )
```

```python
# =========================================================================
# PROFIT FACTOR
# PF = Gross Profit / Gross Loss (using absolute values of losses)
# =========================================================================

def compute_profit_factor(pnls: list[float]) -> float:
    """
    Profit Factor = sum of winning PnLs / abs(sum of losing PnLs).
    
    Args:
        pnls: list of PnL ratios (decimal format)
    
    Returns:
        PF >= 0. inf if no losses.
    """
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    return gross_profit / gross_loss
```

```python
# =========================================================================
# WIN RATE
# =========================================================================

def compute_win_rate(pnls: list[float]) -> float:
    """Win rate = number of winning trades / total trades."""
    if not pnls:
        return 0.0
    wins = sum(1 for p in pnls if p > 0)
    return wins / len(pnls)


def compute_loss_rate(pnls: list[float]) -> float:
    """Loss rate = number of losing trades / total trades."""
    if not pnls:
        return 0.0
    losses = sum(1 for p in pnls if p < 0)
    return losses / len(pnls)
```

```python
# =========================================================================
# SHARPE RATIO (annualized, daily returns assumed)
# =========================================================================

import numpy as np

def compute_sharpe(pnls: list[float], periods_per_year: int = 252,
                   risk_free_daily: float = 0.0) -> float:
    """
    Annualized Sharpe ratio.
    
    Args:
        pnls: list of PnL ratios per trade (treated as per-period returns)
        periods_per_year: 252 for daily, 52 for weekly, 12 for monthly
        risk_free_daily: daily risk-free rate as ratio (e.g. 0.0001 for ~2.5%/yr)
    
    Returns:
        Annualized Sharpe ratio
    """
    if len(pnls) < 2:
        return 0.0
    
    excess = np.array(pnls) - risk_free_daily
    mean_excess = np.mean(excess)
    std_excess = np.std(excess, ddof=1)
    
    if std_excess == 0:
        return 0.0
    
    sharpe = (mean_excess / std_excess) * np.sqrt(periods_per_year)
    return float(sharpe)
```

```python
# =========================================================================
# MAX DRAWDOWN
# =========================================================================

def compute_max_drawdown(pnls: list[float], starting_capital: float = 1.0) -> float:
    """
    Max drawdown = worst peak-to-trough decline in cumulative equity curve.
    
    Args:
        pnls: list of PnL ratios per trade
        starting_capital: initial capital (1.0 = 100%)
    
    Returns:
        Max drawdown as positive decimal (0.15 = 15% drawdown)
    """
    if not pnls:
        return 0.0
    
    equity = starting_capital
    peak = starting_capital
    max_dd = 0.0
    
    for pnl in pnls:
        equity *= (1.0 + pnl)  # compound
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak
        if dd > max_dd:
            max_dd = dd
    
    return float(max_dd)
```

```python
# =========================================================================
# DEFLATED SHARPE RATIO (DSR) — multiple testing correction
# =========================================================================
# Reference: Bailey & Lopez de Prado (2012), "The Deflated Sharpe Ratio"
# DSR adjusts Sharpe for: number of trials (N), skewness, kurtosis,
# and the specific SR being tested.
# =========================================================================

from scipy import stats as _stats
from scipy.special import erfc as _erfc

def compute_deflated_sharpe(pnls: list[float], trials: int = 1,
                            benchmark_sr: float = 0.0) -> float:
    """
    Deflated Sharpe Ratio — probability that the true Sharpe > benchmark_sr
    after correcting for multiple testing (trials).
    
    Args:
        pnls: list of PnL ratios per trade
        trials: number of independent strategies/backtests tried (N)
        benchmark_sr: Sharpe ratio to test against (usually 0.0)
    
    Returns:
        DSR in [0, 1]. >= 0.95 means 95% confident true SR > benchmark.
    """
    if len(pnls) < 2:
        return 0.0
    
    pnls = np.array(pnls, dtype=float)
    sr = compute_sharpe(pnls.tolist())  # annualized Sharpe
    
    # Skewness and kurtosis of returns
    skewness = _stats.skew(pnls)
    kurtosis = _stats.kurtosis(pnls, fisher=True)  # excess kurtosis
    
    n = len(pnls)
    
    # Bailey & Lopez de Prado formula for the standard error of Sharpe
    # adjusted for non-normality and multiple trials
    # Var(SR) ≈ (1 + sr^2/2 - skewness*sr + (kurtosis-3)*sr^2/4) / n
    # Multiple testing: effective trials reduce confidence
    var_sr = (1.0 + 0.5 * sr**2 - skewness * sr +
              0.25 * (kurtosis - 3) * sr**2) / n
    
    if var_sr <= 0:
        return 0.0
    
    se_sr = np.sqrt(var_sr)
    
    # Probability that true SR > benchmark_sr given observed SR
    # Using normal approximation
    z = (sr - benchmark_sr) / se_sr
    
    # Multiple testing correction: adjust for N trials
    # Probability that at least one of N trials exceeds benchmark by chance
    p_single = 1.0 - _stats.norm.cdf(z)  # one-sided p-value
    
    # DSR = probability this is not a false discovery among N trials
    # Approximation: DSR ≈ 1 - (1 - (1 - p_single))^N ... simplified:
    # Use the Bailey-Lopez de Prado erfc formulation:
    # DSR = erfc((sr - benchmark) / (se_sr * sqrt(2))) adjusted for trials
    # Simpler practical form:
    p_multi = 1.0 - (1.0 - p_single) ** trials  # family-wise error rate
    dsr = 1.0 - p_multi
    
    return float(max(0.0, min(1.0, dsr)))
```

```python
# =========================================================================
# BOOTSTRAP CI FOR MEAN RETURN (excludes zero?)
# =========================================================================

def bootstrap_mean_ci(pnls: list[float], n_bootstrap: int = 10000,
                      confidence: float = 0.95, seed: int = 42) -> tuple[float, float]:
    """
    Bootstrap confidence interval for mean PnL.
    
    Args:
        pnls: list of PnL ratios
        n_bootstrap: number of bootstrap resamples
        confidence: confidence level (0.95 = 95% CI)
        seed: random seed for reproducibility
    
    Returns:
        (lower_bound, upper_bound) of the CI.
        If lower_bound > 0, mean return is significantly positive.
    """
    rng = np.random.default_rng(seed)
    pnls = np.array(pnls, dtype=float)
    n = len(pnls)
    
    if n < 2:
        return (0.0, 0.0)
    
    bootstrap_means = []
    for _ in range(n_bootstrap):
        resample = rng.choice(pnls, size=n, replace=True)
        bootstrap_means.append(np.mean(resample))
    
    bootstrap_means = np.sort(bootstrap_means)
    alpha = 1.0 - confidence
    lower_idx = int(alpha / 2 * n_bootstrap)
    upper_idx = int((1 - alpha / 2) * n_bootstrap)
    
    return (float(bootstrap_means[lower_idx]),
            float(bootstrap_means[upper_idx]))


def mean_return_excludes_zero(pnls: list[float], **kwargs) -> bool:
    """True if bootstrap 95% CI for mean PnL excludes zero (lower > 0)."""
    lower, _ = bootstrap_mean_ci(pnls, **kwargs)
    return lower > 0
```

```python
# =========================================================================
# STABILITY: FIRST-HALF vs SECOND-HALF PF RATIO
# =========================================================================

def compute_stability_ratio(pnls: list[float]) -> float:
    """
    Stability = PF(first half) / PF(second half).
    
    A ratio >= 0.95 means the edge is stable across time.
    A ratio < 0.95 means regime decay (second half performs much worse).
    
    Args:
        pnls: list of PnL ratios in chronological order
    
    Returns:
        Stability ratio (>= 0.95 is required)
    """
    if len(pnls) < 10:
        return 0.0  # not enough data to split
    
    mid = len(pnls) // 2
    first_half = pnls[:mid]
    second_half = pnls[mid:]
    
    pf_first = compute_profit_factor(first_half)
    pf_second = compute_profit_factor(second_half)
    
    if pf_second == 0:
        return 0.0 if pf_first == 0 else float('inf')
    
    return pf_first / pf_second
```

### 3.3 Complete Gate Evaluation Script

```python
# =========================================================================
# EQUITY P0 GATE EVALUATION — run once per strategy
# =========================================================================

from typing import NamedTuple


class GateResult(NamedTuple):
    gate: str
    passed: bool
    value: float
    threshold: float
    detail: str


def evaluate_p0_gates(pnls: list[float], strategy_name: str,
                      trials: int = 1) -> list[GateResult]:
    """
    Evaluate all P0 gates for a single strategy's trade PnLs.
    
    Args:
        pnls: PnL ratios in chronological order
        strategy_name: strategy identifier
        trials: number of independent strategies tested (for DSR)
    
    Returns:
        List of GateResult, one per gate.
    """
    results = []
    n = len(pnls)
    
    # G1: n >= 100
    results.append(GateResult(
        gate="G1_sample_size",
        passed=n >= 100,
        value=float(n),
        threshold=100.0,
        detail=f"{n} closed trades (need >= 100)"
    ))
    
    # G2: Profit Factor >= 1.5
    pf = compute_profit_factor(pnls)
    results.append(GateResult(
        gate="G2_profit_factor",
        passed=pf >= 1.5,
        value=pf,
        threshold=1.5,
        detail=f"PF={pf:.4f} (need >= 1.5)"
    ))
    
    # G3: Win Rate >= 55%
    wr = compute_win_rate(pnls)
    results.append(GateResult(
        gate="G3_win_rate",
        passed=wr >= 0.55,
        value=wr,
        threshold=0.55,
        detail=f"WR={wr*100:.2f}% (need >= 55%)"
    ))
    
    # G4: Sharpe >= 0.5
    sharpe = compute_sharpe(pnls)
    results.append(GateResult(
        gate="G4_sharpe",
        passed=sharpe >= 0.5,
        value=sharpe,
        threshold=0.5,
        detail=f"Sharpe={sharpe:.4f} (need >= 0.5)"
    ))
    
    # G5: Max Drawdown <= 15%
    max_dd = compute_max_drawdown(pnls)
    results.append(GateResult(
        gate="G5_max_drawdown",
        passed=max_dd <= 0.15,
        value=max_dd,
        threshold=0.15,
        detail=f"MaxDD={max_dd*100:.2f}% (need <= 15%)"
    ))
    
    # G6: Deflated Sharpe Ratio >= 0.95
    dsr = compute_deflated_sharpe(pnls, trials=trials)
    results.append(GateResult(
        gate="G6_deflated_sharpe",
        passed=dsr >= 0.95,
        value=dsr,
        threshold=0.95,
        detail=f"DSR={dsr:.4f} (need >= 0.95, trials={trials})"
    ))
    
    # G7: Bootstrap CI excludes zero
    ci_excludes_zero = mean_return_excludes_zero(pnls)
    lower, upper = bootstrap_mean_ci(pnls)
    results.append(GateResult(
        gate="G7_bootstrap_ci",
        passed=ci_excludes_zero,
        value=lower,
        threshold=0.0,
        detail=f"95% CI for mean: [{lower:.6f}, {upper:.6f}] (lower must be > 0)"
    ))
    
    # G8: Stability ratio >= 0.95
    stability = compute_stability_ratio(pnls)
    results.append(GateResult(
        gate="G8_stability",
        passed=stability >= 0.95,
        value=stability,
        threshold=0.95,
        detail=f"PF first-half / second-half = {stability:.4f} (need >= 0.95)"
    ))
    
    return results


def all_gates_pass(gate_results: list[GateResult]) -> bool:
    """True only if every gate passes."""
    return all(r.passed for r in gate_results)


def print_gate_report(gate_results: list[GateResult]) -> None:
    """Human-readable gate report."""
    print(f"{'Gate':<30} {'Pass':<6} {'Value':<12} {'Threshold':<12} Detail")
    print("-" * 90)
    for r in gate_results:
        status = "PASS" if r.passed else "FAIL"
        print(f"{r.gate:<30} {status:<6} {r.value:<12.4f} {r.threshold:<12.4f} {r.detail}")
    
    overall = all_gates_pass(gate_results)
    print("-" * 90)
    print(f"OVERALL: {'ALL GATES PASS — eligible for paper trading' if overall else 'GATES FAIL — no capital'}")
```

### 3.4 What "Pass" Means

- **All 8 gates pass** for a strategy → eligible for paper trading (Tier 3).
- **Paper trading n ≥ 100 forward picks with all gates still passing** → eligible for live capital (Tier 4).
- **ANY gate fails** → strategy stays in shadow / blocked. No live capital.
- **Aggregate G8 already fails at class level** (0.728) — this is a regime-decay warning. Per-strategy stability must be measured independently; if per-strategy G8 also fails, the strategy is regime-dependent and should not be sized.

---

## 4. Forward-Test Plan

### 4.1 Test Design

| Parameter | Specification |
|-----------|---------------|
| Horizon | Forward (paper) trading only, no backtest |
| Minimum duration | 3 months clean forward data |
| Minimum trades per strategy | n ≥ 100 closed trades |
| Benchmark | SPY total return, same window |
| Cost assumption | 1 bp commission + 1 bp slippage per side (2 bps round trip) |
| Position sizing | Max 2% risk per trade (see formula below) |
| Max concurrent positions | 5 (diversify across uncorrelated names) |
| Data | Split/dividend-adjusted daily OHLCV, no survivorship bias |
| Entry basis | Next-bar open (NOT same-bar close — avoids lookahead leakage) |
| Exit | TP hit, SL hit, or time-stop (max hold days per strategy) |

### 4.2 Position Sizing Formula (Max 2% Risk Per Trade)

**Risk per trade = 2% of account equity.** The number of shares is determined by the distance from entry to stop loss, not by a fixed dollar amount.

```python
# =========================================================================
# POSITION SIZING — MAX 2% RISK PER TRADE
# =========================================================================

def compute_position_size(account_equity: float, entry_price: float,
                          stop_loss: float, direction: str,
                          max_risk_pct: float = 0.02) -> dict:
    """
    Compute position size so that a stop-out loses at most max_risk_pct
    of account equity.
    
    Args:
        account_equity: total account value in dollars
        entry_price: entry price per share
        stop_loss: stop loss price per share
        direction: "LONG" or "SHORT"
        max_risk_pct: maximum fraction of equity to risk (default 0.02 = 2%)
    
    Returns:
        dict with shares, risk_dollars, risk_pct, position_value
    """
    if entry_price <= 0 or stop_loss <= 0:
        return {"shares": 0, "risk_dollars": 0.0, "risk_pct": 0.0, "position_value": 0.0}
    
    # Risk per share (absolute dollar amount)
    if direction == "LONG":
        risk_per_share = entry_price - stop_loss  # entry > stop for long
    else:  # SHORT
        risk_per_share = stop_loss - entry_price  # stop > entry for short
    
    if risk_per_share <= 0:
        return {"shares": 0, "risk_dollars": 0.0, "risk_pct": 0.0, "position_value": 0.0}
    
    # Maximum dollars we can risk
    max_risk_dollars = account_equity * max_risk_pct  # 2% of equity
    
    # Number of shares = max risk dollars / risk per share
    shares = int(max_risk_dollars / risk_per_share)
    
    # Round down to whole shares (can't buy fractional shares in most brokers)
    shares = max(0, shares)
    
    # Actual risk and position value
    actual_risk_dollars = shares * risk_per_share
    actual_risk_pct = actual_risk_dollars / account_equity
    position_value = shares * entry_price
    
    return {
        "shares": shares,
        "risk_dollars": round(actual_risk_dollars, 2),
        "risk_pct": round(actual_risk_pct, 6),
        "position_value": round(position_value, 2),
    }


# Example: $100,000 account, LONG AAPL at $200, stop at $194 (6% below)
# Risk per share = $6. Max risk = $2,000 (2%). Shares = 2000 / 6 = 333 shares.
# Position value = 333 * $200 = $66,600. Actual risk = 333 * $6 = $1,998 (1.998%).
# Result: {"shares": 333, "risk_dollars": 1998.0, "risk_pct": 0.01998, "position_value": 66600.0}
```

**Position sizing rules:**
1. Risk per trade is capped at 2% of account equity.
2. If the computed position value exceeds 20% of account equity, cap position value at 20% (concentration limit).
3. If stop distance is very tight (<1% of price), increase shares but still cap position value at 20%.
4. If stop distance is very wide (>10% of price), reduce shares; if even 1 share risks >2%, skip the trade.
5. Max 5 concurrent positions; total portfolio heat (sum of all open risks) ≤ 10%.

### 4.3 Entry/Exit Rules Per Strategy (Forward Test)

Each strategy in the forward test uses its native entry condition (from Section 2) but with these standardized rules:

| Rule | Specification |
|------|---------------|
| Entry bar | Next bar OPEN after signal (not same-bar close) — prevents lookahead |
| Entry price | Recorded at next-bar open, not signal close |
| TP exit | Limit order at take_profit price |
| SL exit | Stop order at stop_loss price |
| Time exit | Max hold days per strategy category (see EQUITY_RISK) |
| Partial exits | None (all-or-nothing at TP or SL) |
| Re-entry | Allowed after exit if signal re-triggers |

**Per-strategy forward-test parameters:**

| Strategy | Universe | Entry Signal | TP | SL | Max Hold | Max Concurrent |
|----------|----------|-------------|-----|-----|----------|----------------|
| connors_rsi2_scanner | SPY, QQQ, IWM + large caps | RSI(2)<5, >SMA200 | entry + 3×ATR | entry - 1.5×ATR | 10 days | 3 |
| equity_two_bar_rsi_reversal | MSFT, META, ADBE + index ETFs | 2 down bars, RSI(2)<25, >EMA200 | entry + 1.8×ATR | entry - 1.0×ATR | 10 days | 3 |
| vix_spike_reversal_scanner | SPY | VIX>28 + spike/sustained | entry + 4×ATR | entry - 2×ATR | 10 days | 1 |
| triple_rsi_scanner | SPY, QQQ, AAPL, MSFT, NVDA, AMD | RSI(2)<10 & RSI(5)<20 & RSI(10)<30, >SMA200 | entry + 3.5×ATR | entry - 1.5×ATR | 10 days | 2 |
| momentum_factor_12m | Top quartile by 12m mom | 12m mom > 5%, >SMA50, RSI≤70 | entry + 3×ATR | entry - 1.5×ATR | 10 days | 3 |
| quality_value_composite | Stock category | Composite score top quartile, >SMA200 | entry + 3×ATR | entry - 1.5×ATR | 10 days | 3 |
| gap_reversal_tech_stocks | Large-cap tech | Gap down >3% on >1.5× vol | entry + 3×ATR | entry - 1.5×ATR | 5 days | 3 |
| blue_chip_mean_reversion | BLUE_CHIPS | RSI(2)<10, >SMA200, 6m>0 | SMA5 or entry×1.04 | entry - 2×ATR | 7 days | 3 |
| sector_rotation | Sector ETFs | Bottom 30% 20d return, RSI turning up | entry + 3×ATR | entry × 0.95 | 20 days | 4 |
| etf_relative_strength | ETF cat | Top 30% 1m return, RSI 30-55, >SMA50 | entry + 3×ATR | entry - 2×ATR | 15 days | 4 |
| gap_fill_reversion | Stock/ETF | Gap down -2% to -5% on <2× vol | prev_close (gap fill) | entry - 1.5×ATR | 5 days | 3 |
| vix_market_timing | INDEX_ETFS | VIX regime-based | see strategy spec | see strategy spec | 15 days | 2 |
| dividend_aristocrat_defense | Aristocrats + Growth | Regime-based | see strategy spec | see strategy spec | 20 days | 3 |
| earnings_momentum_pead | Stock/ETF | Gap up >3% on >2× vol | entry + 3×ATR | max(gap×0.97, entry-2×ATR) | 10 days | 3 |
| intermarket_risk_on | High-beta tech | Risk-on confirmed | entry + 3.5×ATR | entry - 1.5×ATR | 10 days | 2 |
| support_resistance_bounce | All equity | Near support, bouncing | nearest resistance | support × 0.97 | 10 days | 3 |
| penny_volume_breakout | Penny stocks | 20d breakout, vol >4× | entry + 4×ATR | high_20d × 0.97 | 7 days | 2 |
| meme_social_velocity | Meme stocks | Vol accelerating, 10d breakout | entry + 5×ATR | entry - 2×ATR | 7 days | 2 |
| turn_of_month_scanner | SPY, QQQ, ES=F, NQ=F | TOM window | entry + 2.5×ATR | entry - 1.2×ATR | 4 days | 2 |
| earnings_gap_reversal_scanner | Sector ETFs | Gap down >4% on 2× vol | entry × 1.03 | entry × 0.98 | 5 days | 3 |
| connors_rsi2_short_scanner | SPY, QQQ, IWM | RSI(2)>95, <SMA200 | entry - 1.5×ATR | entry + 0.75×ATR | 10 days | 2 |
| optimized_stock_momentum | Tech large caps | RVOL>1.5, EMA confluence, ADX>20 | entry + 3×ATR | entry - 2×ATR | 10 days | 3 |

### 4.4 Exact Pick JSON Structure Required

Every forward-test pick must be emitted as JSON with **all** fields below. Missing or null fields cause immediate kill (Tier 1 QA).

```json
{
  "id": "wired_in_flaxen_hair::AAPL::2026-11-15::connors_rsi2_scanner",
  "symbol": "AAPL",
  "asset_class": "EQUITY",
  "category": "stock",
  "direction": "LONG",
  "signal_type": "BUY",
  "strategy": "connors_rsi2_scanner",
  "entry_price": 225.50,
  "take_profit": 234.25,
  "stop_loss": 220.75,
  "confidence": 0.75,
  "ml_score": 0.75,
  "risk_reward": 2.0,
  "status": "OPEN",
  "outcome": "PENDING",
  "pnl_pct": 0.0,
  "pnl_ratio": 0.0,
  "timestamp": "2026-11-15T09:30:00+00:00",
  "generated_at": "2026-11-15T09:30:00+00:00",
  "entry_date": "2026-11-15",
  "timeframe": "1d",
  "source_system": "alpha_engine/equity_strategies.py",
  "paper_trade": true,
  "sizing_allowed": false,
  "trust_tier": "UNPROVEN",
  "price_source": "yfinance daily close 2026-11-13",
  "atr14": 4.25,
  "reason": "Connors RSI-2=3.2 (<5), above 200d SMA=$210.00, RSI14=45 -- published 75.7% WR (Connors & Alvarez 2008)",
  "max_hold_hours": 240,
  "horizon_hours": 240,
  "signal_asof": "2026-11-13T21:00:00+00:00",
  "entry_basis": "next_bar_open",
  "leakage": "NONE",
  "benchmark": "SPY",
  "promotable": false,
  "root_cause_note": "",
  "commission_bps": 1.0,
  "slippage_bps": 1.0,
  "risk_pct": 0.02,
  "position_size_shares": 0,
  "position_value_usd": 0.0
}
```

**Field-by-field specification:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique: `{source}::{symbol}::{date}::{strategy}` |
| `symbol` | string | Yes | Ticker symbol |
| `asset_class` | string | Yes | Must be `"EQUITY"` |
| `category` | string | Yes | `stock`, `etf`, `penny`, `meme`, `futures`, `leveraged_etf` |
| `direction` | string | Yes | `"LONG"` or `"SHORT"` |
| `signal_type` | string | Yes | `"BUY"`, `"STRONG_BUY"`, `"SELL"`, `"STRONG_SELL"` |
| `strategy` | string | Yes | Exact strategy function name |
| `entry_price` | float | Yes | Entry price (next-bar open) |
| `take_profit` | float | Yes | Limit exit price |
| `stop_loss` | float | Yes | Stop exit price |
| `confidence` | float | Yes | 0.0-1.0, capped per strategy spec |
| `ml_score` | float | Yes | Must equal confidence (no hidden coupling) |
| `risk_reward` | float | Yes | (TP-entry)/(entry-SL) for LONG |
| `status` | string | Yes | `"OPEN"`, `"CLOSED"`, `"EXPIRED"`, `"KILLED"` |
| `outcome` | string | Yes | `"PENDING"`, `"WIN"`, `"LOSS"`, `"BREAKEVEN"` |
| `pnl_pct` | float | Yes | DEPRECATED — use pnl_ratio; must be 0.0 until closed |
| `pnl_ratio` | float | Yes | PnL as decimal ratio (0.02 = +2%) |
| `timestamp` | string | Yes | ISO 8601 UTC |
| `generated_at` | string | Yes | ISO 8601 UTC |
| `entry_date` | string | Yes | YYYY-MM-DD |
| `timeframe` | string | Yes | `"1d"` |
| `source_system` | string | Yes | File path of strategy |
| `paper_trade` | boolean | Yes | `true` until live-approved |
| `sizing_allowed` | boolean | Yes | `false` until all P0 gates pass |
| `trust_tier` | string | Yes | `"UNPROVEN"`, `"PAPER"`, `"LIVE"` |
| `price_source` | string | Yes | Data source + timestamp |
| `atr14` | float | Yes | ATR(14) at entry (for position sizing audit) |
| `reason` | string | Yes | Human-readable entry rationale |
| `max_hold_hours` | int | Yes | Max hold time (days × 24) |
| `horizon_hours` | int | Yes | Same as max_hold_hours |
| `signal_asof` | string | Yes | When signal was computed |
| `entry_basis` | string | Yes | `"next_bar_open"` or `"same_bar_close"` (latter flagged) |
| `leakage` | string | Yes | `"NONE"` or `"SAME_BAR_ENTRY"` (latter = QA flag) |
| `benchmark` | string | Yes | `"SPY"` for equity |
| `promotable` | boolean | Yes | `false` until gates pass |
| `root_cause_note` | string | Yes | Explanation if kill/expire |
| `commission_bps` | float | Yes | Commission in bps per side |
| `slippage_bps` | float | Yes | Slippage in bps per side |
| `risk_pct` | float | Yes | Risk fraction (0.02 = 2%) |
| `position_size_shares` | int | Yes | Computed by position sizing formula |
| `position_value_usd` | float | Yes | shares × entry_price |

### 4.5 Pick Generation Pipeline (Python)

```python
# =========================================================================
# FORWARD TEST PICK GENERATOR — emits one JSON per pick
# =========================================================================

import json
from datetime import datetime, timezone

def emit_pick(strategy: str, symbol: str, category: str, direction: str,
              signal_type: str, entry_price: float, take_profit: float,
              stop_loss: float, confidence: float, atr14: float, reason: str,
              max_hold_days: int, benchmark: str = "SPY",
              account_equity: float = 100000.0) -> dict:
    """
    Build a forward-test pick dict with all required fields.
    Computes position size via the 2% risk formula.
    """
    from position_sizing import compute_position_size  # local module
    
    now = datetime.now(timezone.utc)
    entry_date = now.strftime("%Y-%m-%d")
    
    # Position sizing
    sizing = compute_position_size(
        account_equity=account_equity,
        entry_price=entry_price,
        stop_loss=stop_loss,
        direction=direction,
        max_risk_pct=0.02,
    )
    
    # Risk-reward
    if direction == "LONG":
        rr = (take_profit - entry_price) / (entry_price - stop_loss)
    else:
        rr = (entry_price - take_profit) / (stop_loss - entry_price)
    
    pick = {
        "id": f"wired_in_flaxen_hair::{symbol}::{entry_date}::{strategy}",
        "symbol": symbol,
        "asset_class": "EQUITY",
        "category": category,
        "direction": direction,
        "signal_type": signal_type,
        "strategy": strategy,
        "entry_price": round(entry_price, 2),
        "take_profit": round(take_profit, 2),
        "stop_loss": round(stop_loss, 2),
        "confidence": round(confidence, 2),
        "ml_score": round(confidence, 2),
        "risk_reward": round(rr, 2),
        "status": "OPEN",
        "outcome": "PENDING",
        "pnl_pct": 0.0,
        "pnl_ratio": 0.0,
        "timestamp": now.isoformat(),
        "generated_at": now.isoformat(),
        "entry_date": entry_date,
        "timeframe": "1d",
        "source_system": "alpha_engine/equity_strategies.py",
        "paper_trade": True,
        "sizing_allowed": False,
        "trust_tier": "UNPROVEN",
        "price_source": f"yfinance daily close {entry_date}",
        "atr14": round(atr14, 4),
        "reason": reason,
        "max_hold_hours": max_hold_days * 24,
        "horizon_hours": max_hold_days * 24,
        "signal_asof": now.isoformat(),
        "entry_basis": "next_bar_open",
        "leakage": "NONE",
        "benchmark": benchmark,
        "promotable": False,
        "root_cause_note": "",
        "commission_bps": 1.0,
        "slippage_bps": 1.0,
        "risk_pct": sizing["risk_pct"],
        "position_size_shares": sizing["shares"],
        "position_value_usd": sizing["position_value"],
    }
    return pick


def write_picks(picks: list[dict], path: str) -> None:
    """Write picks to JSON file."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_system": "equity_forward_test",
        "worktree": "flaxen-hair_2026-11-15T0234_flaxen-hair",
        "paper_only": True,
        "sizing_allowed": False,
        "trust_tier": "UNPROVEN",
        "disclaimer": "Shadow monitoring cards. Not money-ready. sizing_allowed=false.",
        "picks": picks,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
```

### 4.6 Forward-Test Execution Schedule

| Week | Action |
|------|--------|
| Week 1 | Fix PnL normalization (ratio vs percent) across all equity pick emission |
| Week 1 | Backfill `asset_class`='EQUITY' for UNK equity picks |
| Week 2 | Run per-strategy backtests; record PF, WR, Sharpe, n |
| Week 2 | Rank strategies (Section 6); select top 3 for forward test |
| Week 3 | Begin paper forward test on top 3 strategies |
| Weeks 3-12 | Track picks daily; apply kill gates (Section 5) |
| Week 12 | Evaluate P0 gates; promote or kill each strategy |

---

## 5. Kill Gates — When to Kill a Strategy

A strategy is killed immediately if **any** of the following triggers fire. Kill is permanent for the current cycle; re-entry requires re-pre-registration and new backtest.

| Kill Gate | Threshold | Action |
|-----------|-----------|--------|
| KG1 | Any drawdown > 10% from peak equity | Kill immediately |
| KG2 | Any 5-day drawdown > 2% | Kill immediately |
| KG3 | Sharpe < 0 after 10 trades | Kill immediately |
| KG4 | 5 consecutive losses | Kill immediately |
| KG5 | PnL = 0 while price moved (exit ≠ entry but pnl = 0) | Kill immediately (fill bug) |
| KG6 | Duplicate pick ID detected | Kill immediately |
| KG7 | ml_score ≠ confidence (>90% of picks) | Kill immediately (coupling bug) |
| KG8 | Blank required fields (entry_price, direction, symbol) | Kill immediately |
| KG9 | Stale open position > 72 hours with no price update | Mark EXPIRED |
| KG10 | Same-bar entry (entry_basis = "same_bar_close") | Kill immediately (lookahead) |
| KG11 | Forward n ≥ 50 but PF < 1.0 | Kill (no edge) |

```python
# =========================================================================
# KILL GATE EVALUATION — run after every trade close
# =========================================================================

from typing import NamedTuple


class KillResult(NamedTuple):
    killed: bool
    gate: str | None
    reason: str


def check_kill_gates(pnls: list[float], recent_5d_pnls: list[float],
                     consecutive_losses: int, peak_equity: float,
                     current_equity: float, trade_count: int,
                     sharpe: float) -> KillResult:
    """
    Check all kill gates. Returns KillResult with killed=True if any gate fires.
    
    Args:
        pnls: all PnL ratios in chronological order
        recent_5d_pnls: PnL ratios for the last 5 trading days
        consecutive_losses: current streak of losing trades
        peak_equity: highest equity level reached
        current_equity: current equity level
        trade_count: total number of closed trades
        sharpe: current Sharpe ratio
    
    Returns:
        KillResult
    """
    # KG1: Any drawdown > 10%
    if peak_equity > 0:
        dd = (peak_equity - current_equity) / peak_equity
        if dd > 0.10:
            return KillResult(True, "KG1_drawdown_10pct",
                              f"Drawdown {dd*100:.2f}% > 10%")
    
    # KG2: Any 5-day drawdown > 2%
    if len(recent_5d_pnls) >= 1:
        five_day_pnl = sum(recent_5d_pnls)
        if five_day_pnl < -0.02:
            return KillResult(True, "KG2_five_day_drawdown_2pct",
                              f"5-day PnL {five_day_pnl*100:.2f}% < -2%")
    
    # KG3: Sharpe < 0 after 10 trades
    if trade_count >= 10 and sharpe < 0:
        return KillResult(True, "KG3_negative_sharpe",
                          f"Sharpe {sharpe:.4f} < 0 after {trade_count} trades")
    
    # KG4: 5 consecutive losses
    if consecutive_losses >= 5:
        return KillResult(True, "KG4_consecutive_losses",
                          f"{consecutive_losses} consecutive losses")
    
    return KillResult(False, None, "No kill gates triggered")
```

---

## 6. Ranking of Strategies to Test First

**Ranking methodology:**
1. Primary sort: Backtest Profit Factor (highest first)
2. Secondary sort: Backtest Win Rate (highest first)
3. Tertiary sort: Backtest Sharpe (highest first)
4. Only strategies with backtest n ≥ 10 are eligible for ranking
5. Strategies with published/backtested proof (connors_rsi2, vix_spike, equity_two_bar) get priority for forward testing

**Backtest-validated strategies (priority tier):**

| Rank | Strategy | Backtest PF | Backtest WR | Backtest Sharpe | n | Proof Source | Forward Priority |
|------|----------|-------------|-------------|-----------------|---|--------------|------------------|
| 1 | `equity_two_bar_rsi_reversal` | 1.54-1.83 | 51-57% | TBD | 173-243 | baby_strategies backtest (META n=243, MSFT n=230, ADBE n=173) | **P0 — start first** |
| 2 | `connors_rsi2_scanner` | TBD | 75.7% (SPY) | TBD | TBD | Published Connors & Alvarez 2008; repo backtest p=6e-6 | **P0 — shadow active** |
| 3 | `vix_spike_reversal_scanner` | TBD | 72% | 6.20 | TBD | 10yr backtest p=0.022 | **P0 — shadow active** |
| 4 | `triple_rsi_scanner` | 5.0 (published) | 90% (published) | TBD | 12 (repo 5yr) | QuantifiedStrategies 20yr | P1 — small n, verify |
| 5 | `gap_reversal_tech_stocks` | TBD | ~70% (published) | TBD | TBD | Bremer & Sweeney 1991 JF n=132 | P1 |
| 6 | `optimized_stock_momentum` | TBD | GOOGL 100%, MSFT 66% | TBD | TBD | Mar 2026 backtest | P1 |
| 7 | `momentum_factor_12m` | TBD | TBD | TBD | TBD | Jegadeesh & Titman 1993 | P2 |
| 8 | `quality_value_composite` | TBD | TBD | TBD | TBD | Asness et al. 2019 QMJ | P2 |
| 9 | `support_resistance_bounce` | TBD | TBD | TBD | TBD | Edwards & Magee 1948 | P2 |
| 10 | `intermarket_risk_on` | TBD | TBD | TBD | TBD | Asness 2013 | P2 |
| 11 | `turn_of_month_scanner` | TBD | TBD | TBD | TBD | Lakonishok & Smidt 1988 | P2 |
| 12 | `earnings_gap_reversal_scanner` | TBD | TBD | TBD | TBD | Ball & Brown 1968 | P2 |
| 13 | `earnings_momentum_pead` | TBD | TBD | TBD | TBD | Ball & Brown 1968; Bernard & Thomas 1989 | P2 |
| 14 | `sector_rotation` | TBD | TBD | TBD | TBD | Faber 2007 | P2 |
| 15 | `blue_chip_mean_reversion` | TBD | TBD | TBD | TBD | Connors & Alvarez 2009 | P2 |
| 16 | `vix_market_timing` | TBD | TBD | TBD | TBD | Ang et al. 2006 | P2 |
| 17 | `dividend_aristocrat_defense` | TBD | TBD | TBD | TBD | Ang 2014; O'Shaughnessy 2012 | P2 |
| 18 | `gap_fill_reversion` | TBD | TBD | TBD | TBD | Doran et al. 2008 | P2 |
| 19 | `etf_relative_strength` | TBD | TBD | TBD | TBD | Antonacci 2012 | P2 |
| 20 | `penny_volume_breakout` | TBD | TBD | TBD | TBD | Empirical | P3 — high risk |
| 21 | `meme_social_velocity` | TBD | TBD | TBD | TBD | Barber & Odean 2008 | P3 — high risk |
| 22 | `connors_rsi2_short_scanner` | TBD | TBD | TBD | TBD | Symmetric mirror of connors_rsi2 | P3 — short side |
| 23 | `regime_filtered_momentum` | TBD | TBD | TBD | TBD | TBD — module may not import | P3 — conditional |

**Recommended forward-test sequence:**
1. **Week 1-2:** Measure all 23 strategies' backtest metrics; fill the TBD column.
2. **Week 3:** Start forward testing the top 3 (`equity_two_bar_rsi_reversal`, `connors_rsi2_scanner`, `vix_spike_reversal_scanner`).
3. **Week 6:** Add next 3 if top 3 pass interim checks (n ≥ 25, PF ≥ 1.2, no kill gates).
4. **Week 12:** Full P0 gate evaluation; promote or kill.

---

## 7. Immediate Next Steps

1. **Create this file** at `WIRED_IN/flaxen-hair_2026-11-15T0234_flaxen-hair/01_asset_class_plans/EQUITY_PLAN.md` (done).
2. **Fix PnL normalization** — search for all `pnl_pct` usage in equity pick emission; ensure ratio format (decimal, not percent × 100).
3. **Backfill asset_class** — run `alpha_engine/asset_class.py` to tag UNK equity picks as `EQUITY`.
4. **Run per-strategy backtests** — use `backtest_framework.py` on each of the 23 strategies; record PF, WR, Sharpe, n.
5. **Populate the TBD ranking table** (Section 6) with measured values.
6. **Begin forward test** on top 3 strategies with the exact pick JSON structure (Section 4.4).
7. **Apply kill gates** (Section 5) after every trade close.
8. **Re-evaluate P0 gates** at n=100 per strategy; go/no-go on live capital.

---

## 8. Go/No-Go Decision

**NO-GO for live capital today.** All 9 asset classes return `sizing_allowed: false`. EQUITY is the best candidate but unproven.

**Conditions to revisit (all must be true):**
1. Per-strategy n ≥ 100 closed trades
2. Per-strategy PF ≥ 1.5, WR ≥ 55%, Sharpe ≥ 0.5, MaxDD ≤ 15%
3. Per-strategy DSR ≥ 0.95
4. Bootstrap 95% CI for mean return excludes zero
5. Stability ratio ≥ 0.95 (first-half PF / second-half PF)
6. Beats SPY total return after costs on clean forward data
7. PnL normalization fixed (ratio format, no 100× bug)

If EQUITY fails pre-registered tests, hold SPY/QQQ index or low-cost ETFs as the core allocation. EQUITY remains a research candidate, not a capital deployment vehicle.

---

**End of document.**
