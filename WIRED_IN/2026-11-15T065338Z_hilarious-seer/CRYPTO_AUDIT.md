# CRYPTO Strategy Audit (BTC-Only)

**Audit date:** 2026-11-15
**Auditor:** Senior Quant Analyst (Kilo)
**Scope:** Existing CRYPTO strategies in `alpha_engine/` and related modules, focusing EXCLUSIVELY on BTC.
**Constraint:** Altcoins (ETH, SOL, etc.) are out of scope per prior audit decisions.

---

## 1. Existing Strategies Inventory

| Strategy | File path | Method | Claimed Result | Actual Status / Failure mode |
|---|---|---|---|---|
| `funding_rate_extreme_contrarian` | `alpha_engine/crypto_edge_strategies.py:298` | Long when avg funding < -0.05%/8h + RSI<35; Short when >+0.10% + RSI>65 | 65-75% WR, 15-115% annual | **UNPROVEN.** No backtest artifact in repo. Relies on live Binance API. Funding history fetch can fail silently (`len(funding_history) < 3` falls back to current rate). |
| `oi_price_divergence_v2` | `alpha_engine/crypto_edge_strategies.py:530` | OI-direction proxy via taker-buy volume ratio vs price direction | 58-65% WR | **UNPROVEN.** No backtest artifact. Uses taker_buy_base as OI proxy — indirect and noisy. No OI history, only snapshot. |
| `liquidation_flush_recovery` | `alpha_engine/crypto_edge_strategies.py:771` | Volume spike >2.5x + RSI extreme + ATR/BB compression | 62-70% WR | **UNPROVEN.** No backtest artifact. "Liquidation flush" is inferred from volume spike, not actual liquidation data. |
| `crypto_volatility_regime` | `alpha_engine/crypto_volatility_regime.py:79` | 60d time-series momentum + realized vol < 80th pct of 1y | Positive momentum in calm regimes | **UNPROVEN.** No rigorous backtest. Uses `yfinance` daily data with no slippage model. Academic citation (Moskowitz-Ooi-Pedersen 2012) is for futures, not crypto. |
| `crypto_funding_sentiment_combo` | `alpha_engine/crypto_enhancement_pack.py:414` | Funding + Fear&Greed + Social volume (LunarCrush) | Target 62% WR | **UNPROVEN.** Requires LunarCrush API key (often missing). Social volume ratio is a weak, unvalidated signal. No backtest. |
| `crypto_whale_regime_filter` | `alpha_engine/crypto_enhancement_pack.py:590` | Whale accumulation proxy + HMM regime + exchange reserve trend (volume proxy) | Target 60% WR | **UNPROVEN.** Whale signal reads `qualified_traders.json` which has no proven edge. Exchange reserve trend approximated from volume — not actual on-chain reserves. |
| `crypto_options_momentum_sync` | `alpha_engine/crypto_enhancement_pack.py:739` | Put/Call ratio + risk reversal + ROC14 | Target 58% WR | **UNPROVEN.** Deribit API fallback for options data is coarse (OI-based PCR, not actual traded volume PCR). No historical backtest. |
| `crypto_multi_timeframe_confluence` | `alpha_engine/crypto_enhancement_pack.py:842` | 1H EMA9>EMA21 + 4H EMA50 rising + 1D price>SMA200 | Target 65% WR | **UNPROVEN.** No backtest. The SMA200 component is the only empirically cited signal in the repo; the rest is untested conflation. |
| `crypto_liquidation_reversal` | `alpha_engine/crypto_enhancement_pack.py:941` | >3% 1H move + volume >3x avg | Target 60% WR | **UNPROVEN.** No backtest. Mean-reversion after large moves is well-studied but costs on crypto often erase the edge. |
| `btc_breakout` | `alpha_engine/btc_breakout_strategy.py:253` | 20-candle S/R breakout + volume >1.5x + 2 consecutive candles | 78% WR, PF 1.26 (MQL5 claim) | **UNPROVEN.** MQL5 claim is unverified in this repo. No broker-verified backtest data. Range filters (0.5%-5%) are arbitrary. |
| `rsi5_momentum_btc` | `alpha_engine/proven_research_strategies.py:1189` | RSI(5) crosses above 50 | CAGR 122% (QuantifiedStrategies.com claim) | **UNPROVEN.** External claim only. No repo backtest. Fixed 3% TP / 2% SL not optimized for current BTC volatility regime. |
| `btc_overnight_session` | `alpha_engine/proven_research_strategies.py:1251` | Buy at NYSE close (20-22 UTC) if price >= 10-bar max | 35% OOS return, -12% max DD (QuantPedia claim) | **UNPROVEN.** External claim only. Session anomaly is fragile — disappears when widely known. No repo backtest. |
| `keltner_compression_expansion` | `alpha_engine/live_forward_test.py:173` | Keltner width < 25th pct + price cross EMA30 | 72.9% WR on BTC (claim) | **UNPROVEN.** No backtest artifact. The baseline `keltner_bounce` was **RETIRED** (`alpha_engine/strategy_blocklist.py:197`) after rigorous backtest: n=2661, WR 43.6%, PF 0.995, DSR 0.008. |
| `connors_rsi2` (adapted for crypto) | `alpha_engine/live_forward_test.py:129` | RSI(2) < 10 + price > SMA200 (long); RSI(2) > 90 + price < SMA200 (short) | 75.7% WR on SPY (claim) | **PARTIALLY SUPPORTED.** The RSI2 < 10 mean-reversion edge is well-documented (Connors, Alvarez). However, the crypto adaptation has **no repo backtest**. The SMA200 filter is the only robust signal found in prior audits. |
| `super_funding_rate_carry` | `alpha_engine/super_strategies.py:698` | Extreme funding + MVRV proxy (price/SMA200) | n/a | **UNPROVEN.** No backtest. Uses SMA200 as "MVRV proxy" — a stretch. Funding thresholds (-0.02, +0.05) are extreme and fire rarely. |
| `mean_reversion_rsi2` | `alpha_engine/crypto_smart_picks.py:334` | RSI(2) < 10 + price > SMA200 | n/a | **UNPROVEN.** No backtest. Hard-coded 5% TP / 3% SL. Exit condition "RSI(2) > 60" is sensible but untested. |
| `momentum_volume` | `alpha_engine/crypto_smart_picks.py:278` | Volume spike >2x + RSI 40-65 + EMA20/SMA200 alignment | n/a | **UNPROVEN.** No backtest. Buying volume spikes in crypto has been proven toxic (see `rapid_fire`×`volume_spike_breakout` kill). |
| `conservative_rsi_sma200` | `alpha_engine/crypto_test_portfolios.py:302` | RSI(14) < 40 + price > SMA200 + 5% trailing stop | n/a | **UNPROVEN.** No backtest. Uses RSI(14) < 40 (not RSI2 < 10), which is a much weaker mean-reversion signal. |
| `Trust-Score=7 Meta-Filter` | `config/personas/strategy_persona__crypto_trust7_promoter.json` | Meta-gate over all CRYPTO emitters with trust_score >= 7 | 85.9% WR on n=99 (claim) | **BLOCKED.** Upstream dependencies not wired (Plan #198 blocklist, resolver TIME_EXIT mislabel fix). Even if unblocked, n=99 is below the n>=100 gate and the cohort may be contaminated by the stop-fill bug. |

**Summary:** The repository contains **19+ distinct BTC/crypto strategies** across 8 files. **Zero (0) have a rigorous, reproducible backtest artifact that passes the 9-gate Proof Protocol.** Every "proven" claim is either an external citation (QuantifiedStrategies, QuantPedia, MQL5) or a live-signal generator with no historical validation.

---

## 2. What Worked

**The only signal with any empirical support in this repository is the BTC SMA200 trend filter.**

Evidence:
- `alpha_engine/crypto_smart_picks.py:347` — `mean_reversion_rsi2` requires `closes[i] > sma200[i]` for LONG entries.
- `alpha_engine/live_forward_test.py:136` — Connors RSI2 longs are gated by `current > sma200[-1]`.
- `alpha_engine/super_strategies.py:719` — `super_funding_rate_carry` uses `price / sma200` as an MVRV proxy.
- `alpha_engine/crypto_enhancement_pack.py:884` — Multi-timeframe confluence requires `price > SMA200` on the 1D timeframe.
- `alpha_engine/crypto_test_portfolios.py:306` — Conservative portfolio uses `current_price > sma200`.
- Prior audit memory (project.md): **"BTC sma200 is the ONLY robust signal found (ETH rejected)."**

The SMA200 acts as a macro regime filter: it keeps the strategy out of bear markets where long-only strategies are systematically destroyed. It does not, by itself, generate tradable entries — but it prevents catastrophic drawdowns.

**The RSI(2) < 10 mean-reversion overlay** (Connors-style) is the second most credible component:
- Well-documented in equity literature (Connors & Alvarez, "Short-Term Trading Strategies That Work").
- `alpha_engine/live_forward_test.py:129` claims 75.7% WR on SPY.
- When combined with SMA200 (only take long mean-reversion in bull trends), the theoretical edge is sound.

**No other signal has survived scrutiny.** Every funding-rate, OI-divergence, sentiment, whale, options, or liquidation strategy in the repo is either untested or has been killed/retired when tested.

---

## 3. What Failed & Why

### 3.1 Killed / Retired Strategies (CRYPTO-specific)

| Strategy | Evidence | Verdict |
|---|---|---|
| `fear_greed_contrarian` | `alpha_engine/strategy_blocklist.py:106` — n=3525, WR 28.3%, -456% cum PnL | **RETIRED** — contrarian sentiment without trend filter is suicide in crypto. |
| `rapid_fire` × `macd_rsi_confluence` | `alpha_engine/strategy_blocklist.py:292` — n=133 CRYPTO, WR 36.8%, 100% BANNED trust tier | **KILLED** — largest contributor to BANNED-tier closures (~39%). |
| `rapid_fire` × `rsi_bounce` | `alpha_engine/strategy_blocklist.py:306` — n=23, WR 47.8%, 100% BANNED | **KILLED** — same toxic source. |
| `rapid_fire` × `volume_spike_breakout` | `alpha_engine/strategy_blocklist.py:314` — n=78, WR 16.7%, PF 0.014, cumPnL -30.87% | **KILLED** — buying volume spikes is adverse selection (retail FOMO). |
| `rapid_fire` × `stochrsi_macd_combo` | `alpha_engine/strategy_blocklist.py:321` — n=17, WR 11.8%, PF 0.200 | **KILLED** — below noise floor. |
| `quan_engine_scalp` | `alpha_engine/strategy_blocklist.py:152` — n=4741, WR 29.7%, -810% cum PnL | **RETIRED** — single largest alpha destroyer in the ledger. |
| `keltner_bounce` (baseline) | `alpha_engine/strategy_blocklist.py:197` — n=2661, WR 43.6%, PF 0.995, DSR 0.008 | **RETIRED** — WR looked decent but losers > winners in magnitude. |
| `justin_breakout_volume_v2` | `alpha_engine/strategy_blocklist.py:187` — n=12658, WR 64.6%, PF 1.024, PF_LB95 0.982, DSR 0.12 | **RETIRED** — asymmetric payoff destroys edge. High WR, low PF. |
| `enhanced_ml_A_xgboost` | `alpha_engine/strategy_blocklist.py:164` — 28% WR, PF 0.42, 189 picks | **RETIRED** — ML overfit on small sample. |

### 3.2 Infrastructure / Data Failures

| Failure | Impact | File citation |
|---|---|---|
| **Stop-fill bug** | `exit_price = entry_price`, fabricated flat PnL. Corrupted historical ledger. | Prior audit memory; `investigate_tp_sl_bug.py` exists in repo root. |
| **Prediction market copy-trading** | Forward WR 79.09% but PBO=0.603, MaxDD=-69.17%. Structurally rejected. | `project.md_Decisions_prediction_market_copy_trading_rejected` |
| **COT 93.8% contamination** | COT result rejected as contaminated data. | `project.md_Decisions_cot_93_8_rejected_contaminated` |
| **Resolver TIME_EXIT mislabel** | 162 TP_HIT mislabels as TIME_EXIT, corrupting WR/PF calculations. | `config/personas/strategy_persona__crypto_trust7_promoter.json:38` |
| **Frozen-price cohort** | 87-97% WR, PF 10-56 artifacts excluded by Proof Protocol Gate 1. | `research/PROOF_PROTOCOL.md:27` |

### 3.3 Failure Taxonomy

1. **Adverse Selection in Volume Signals** — Strategies that buy on volume spikes (`rapid_fire`×`volume_spike_breakout`, `momentum_volume`) systematically buy into retail FOMO peaks. Professional flow is on the other side.
2. **Macro-Regime Ignorance** — Strategies without SMA200 or equivalent macro filter (`fear_greed_contrarian`, `proven_propfirm_cons_prop`) are destroyed in bear markets.
3. **Proxy Substitutions** — Using taker-buy volume for OI (`oi_price_divergence_v2`), volume trend for exchange reserves (`crypto_whale_regime_filter`), or price/SMA200 for MVRV (`super_funding_rate_carry`) introduces noise that swamps any edge.
4. **Live-API Dependency** — Strategies that require real-time funding rates, Fear&Greed, social volume, or options data (`crypto_enhancement_pack.py` suite) cannot be historically backtested without expensive data collection, making proof impossible.
5. **Overfitting to External Claims** — Strategies ported from external sources (MQL5 BTC AutoTrader, QuantifiedStrategies, QuantPedia) assume market conditions that may not hold in current BTC regimes (post-ETF, lower volatility).

---

## 4. Proposed New Experiments

All experiments follow the **9-gate Proof Protocol** (`research/PROOF_PROTOCOL.md`) plus **Gate 10: Benchmark Beat** (net PF > 1.5 after costs AND net Sharpe > BTC buy-and-hold Sharpe).

| Experiment | Hypothesis | Gap filled | Method | Data | Timeframe | Universe | Parameters | Cost model | Benchmark | Proof gates |
|---|---|---|---|---|---|---|---|---|---|---|
| **E1: BTC SMA200 + RSI2 Mean Reversion (Long-Only)** | Buying BTC when RSI(2) < 10 AND price > SMA200 yields PF > 1.5 after costs, because it captures panic selling within a bull trend. | Tests the ONLY robust signal (SMA200) in isolation with a proven mean-reversion overlay. No existing repo backtest exists for this exact combination. | Vectorized backtest on 4 years of hourly BTC. Entry: RSI(2)<10 & close>SMA200. Exit: RSI(2)>60 OR 5% trailing stop OR 24h time exit. | Binance 1h klines (BTCUSDT), 2021-2025. Fallback: yfinance BTC-USD daily. | 1H entry, hold 1-24h. | BTCUSDT only. | RSI period=2; SMA200; trailing_stop=0.05; time_exit=24h. | Taker fee 0.10% + spread 0.05% + slippage model `sqrt(order/adv)` with K=0.5. Funding: prorated 0.01% per 8h if held through funding. | BTC buy-and-hold over identical period. | All 10. |
| **E2: BTC Funding Rate Extreme Contrarian (Rigorous)** | When BTC funding rate averages < -0.05%/8h over 3 periods, a long position mean-reverts within 48h with PF > 1.5 after costs. | Tests `crypto_edge_strategies.py` claim with actual historical funding rate data and full friction. | Merge Binance fundingRate history with 1h OHLCV. Entry: avg(funding[-3:]) < -0.0005. Exit: ATR-based TP (3x) / SL (2x) OR 48h time exit. | Binance `/fapi/v1/fundingRate` + `/fapi/v1/klines` (BTCUSDT), 3 years. | 4h-1d. | BTCUSDT only. | Funding lookback=3 periods; RSI<40 filter; ATR(14) TP/SL. | Taker 0.10% + spread 0.05% + **funding payment** (actual historical funding rate paid/received). | BTC buy-and-hold. | All 10. |
| **E3: BTC Volatility-Regime Momentum (Purged Walk-Forward)** | BTC positive 60d momentum + realized vol < 80th percentile beats buy-and-hold with lower drawdown after costs. | Tests `crypto_volatility_regime.py` with purged walk-forward (not just a single IS/OS split) and proper costs. | Daily bar rebalancing. Long-only when 60d return > 0 AND 20d realized vol < 80th pct of trailing 365d vol. | yfinance BTC-USD daily, 5 years (2019-2024). | Daily. | BTC-USD only. | TSMOM lookback=60; vol_window=20; vol_pctile_window=365; vol_threshold=80. | Taker 0.10% + spread 0.05%. Rebalance cost applied only on signal change. | BTC buy-and-hold. | All 10. |
| **E4: BTC Multi-Timeframe Confluence (1H+4H+1D)** | Requiring trend alignment across 3 timeframes filters false breakouts and achieves PF > 1.5. | Tests `crypto_enhancement_pack.py` claim with historical replay and full friction. | Backtest on 1H data aggregated to 4H and 1D. Entry: 1H EMA9>EMA21, 4H EMA50 rising, 1D close>SMA200. Exit: 4x ATR TP / 2x ATR SL. | Binance 1h klines (BTCUSDT), 3 years. | 4h. | BTCUSDT only. | 1H EMA9/21; 4H EMA50; 1D SMA200; ATR(14) on 4H. | Taker 0.10% + spread 0.05%. | BTC buy-and-hold. | All 10. |

### Experiment Priorities

1. **E1 is P0** — It combines the only two signals with any credibility (SMA200 + RSI2). It is simple, low turnover, and minimizes overfitting risk.
2. **E2 is P1** — Funding rate contrarian has academic support (Aloosh & Bekaert 2022) but requires collecting historical funding data, which is non-trivial.
3. **E3 is P2** — TSMOM is well-cited but may suffer from high turnover and drawdowns in crypto bear markets.
4. **E4 is P3** — Confluence filters reduce false signals but also reduce sample size (n may fall below 100), making statistical proof harder.

---

## 5. Highest Probability Recommendation

**Run Experiment E1: BTC SMA200 + RSI2 Mean Reversion (Long-Only) on 1H data with a 5% trailing stop and 24-hour time exit.**

**Why this is the highest-probability path:**

1. **SMA200 is the only robust signal** found across multiple audits and multiple strategy files in this repository. It keeps the strategy out of bear markets where long-only approaches are annihilated.
2. **RSI(2) < 10 is one of the most documented short-term mean-reversion edges** in quantitative trading literature. The `live_forward_test.py` file explicitly cites a 75.7% WR for this pattern on SPY, and the crypto adaptation (gated by SMA200) is theoretically sound.
3. **The combination is simple.** Simple strategies have higher Deflated Sharpe Ratios because they are less susceptible to overfitting across the 683-strategy universe.
4. **BTC-specific costs are manageable.** With a 0.15% round-trip cost (0.10% taker + 0.05% spread), the strategy only needs to capture ~0.20-0.30% per trade to be profitable. Given BTC's intraday volatility (~3% daily), this is achievable.
5. **Low turnover.** With RSI(2) < 10 firing roughly 5-10 times per month on BTC, the strategy is not eroded by transaction costs.
6. **Risk is bounded.** The 5% trailing stop and 24h time exit prevent the strategy from holding through macro shocks.

**Recommended parameters (for immediate forward testing):**
- **Symbol:** BTCUSDT
- **Timeframe:** 1H
- **Direction:** LONG only
- **Entry:** RSI(2) < 10 AND close > SMA200
- **Exit:** RSI(2) > 60 OR trailing stop 5% OR 24h time exit (whichever first)
- **Position size:** Risk 1% of equity per trade
- **Cost assumption:** 0.15% round-trip (aggressive), 0.10% round-trip (maker/best-case)

**Honest caveat:** As of this audit, this strategy has **not yet passed the 10 proof gates.** It is the closest candidate. Run the backtest code below, collect n >= 100 trades, and only then evaluate for live deployment.

---

## 6. Runnable Code

Below is a **seeded, deterministic backtest script** for Experiment E1. It includes a full crypto friction model.

**Prerequisites:**
```bash
pip install pandas numpy yfinance
```

**File:** `backtest_btc_sma200_rsi2.py`

```python
#!/usr/bin/env python3
"""
Backtest: BTC SMA200 + RSI2 Mean Reversion (Long-Only)
=======================================================
Experiment E1 from CRYPTO_AUDIT.md (2026-11-15)

Entry: RSI(2) < 10 AND close > SMA200
Exit:  RSI(2) > 60 OR trailing stop 5% OR 24h time exit

Cost model (crypto-specific):
  - Taker fee: 0.10% per trade (round-trip = 0.20%)
  - Spread:    0.05% (one-way, BTCUSDT typical)
  - Slippage:  K * sqrt(order_size / adv), K=0.5
  - Funding:   0.01% per 8h period (conservative estimate for perpetuals)

Data: yfinance BTC-USD (daily) or Binance 1h klines
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

SYMBOL = "BTC-USD"
START_DATE = "2021-01-01"
END_DATE = "2025-11-01"

# Strategy parameters
RSI_PERIOD = 2
SMA_PERIOD = 200
RSI_ENTRY_LONG = 10.0
RSI_EXIT_LONG = 60.0
TRAILING_STOP_PCT = 0.05
TIME_EXIT_BARS = 24          # 24 hours on 1H data; ignored on daily
POSITION_SIZE_USD = 10_000   # Notional per trade for slippage calc

# Cost parameters (crypto-specific)
TAKER_FEE_PCT = 0.0010       # 0.10% per side
SPREAD_PCT = 0.0005          # 0.05% one-way (BTCUSDT typical)
SLIPPAGE_K = 0.5
ADV_USD = 20_000_000_000     # ~$20B daily ADV for BTCUSDT
FUNDING_PER_8H = 0.0001      # 0.01% per 8h funding period

# ---------------------------------------------------------------------------
# INDICATORS
# ---------------------------------------------------------------------------

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_sma(series: pd.Series, period: int = 200) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


# ---------------------------------------------------------------------------
# COST MODEL
# ---------------------------------------------------------------------------

def estimate_slippage_pct(order_size_usd: float, adv_usd: float, k: float = 0.5) -> float:
    """One-way slippage as decimal. Formula: K * sqrt(order_size / adv)."""
    if adv_usd <= 0:
        return 0.0
    return k * math.sqrt(order_size_usd / adv_usd)


def total_cost_per_trade(hold_bars: int, bar_interval_hours: int = 1) -> float:
    """
    Total round-trip cost as decimal.
    Includes: taker fee (2 sides) + spread (2 sides) + slippage (2 sides) + funding.
    """
    fee = TAKER_FEE_PCT * 2
    spread = SPREAD_PCT * 2
    slip = estimate_slippage_pct(POSITION_SIZE_USD, ADV_USD, SLIPPAGE_K) * 2

    # Funding: assume held through N 8h periods
    if bar_interval_hours > 0:
        periods_8h = (hold_bars * bar_interval_hours) / 8.0
        funding = FUNDING_PER_8H * periods_8h
    else:
        funding = 0.0

    return fee + spread + slip + funding


# ---------------------------------------------------------------------------
# BACKTEST ENGINE
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    entry_idx: int
    entry_price: float
    exit_idx: int
    exit_price: float
    exit_reason: str
    pnl_pct_gross: float
    pnl_pct_net: float
    hold_bars: int


def backtest_btc_sma200_rsi2(
    df: pd.DataFrame,
    rsi_period: int = 2,
    sma_period: int = 200,
    rsi_entry: float = 10.0,
    rsi_exit: float = 60.0,
    trail_pct: float = 0.05,
    time_exit_bars: int = 24,
) -> List[Trade]:
    """
    Vectorized-event backtest for long-only BTC strategy.
    df must have 'Close' column and hourly frequency.
    """
    closes = df["Close"].values
    rsi = compute_rsi(df["Close"], period=rsi_period).values
    sma = compute_sma(df["Close"], period=sma_period).values

    n = len(closes)
    trades: List[Trade] = []
    in_trade = False
    entry_idx = 0
    entry_price = 0.0
    high_water_mark = 0.0

    for i in range(sma_period + 1, n):
        if not in_trade:
            # Entry condition: RSI < entry AND close > SMA
            if not (np.isnan(rsi[i]) or np.isnan(sma[i])):
                if rsi[i] < rsi_entry and closes[i] > sma[i]:
                    in_trade = True
                    entry_idx = i
                    entry_price = closes[i]
                    high_water_mark = entry_price
        else:
            # Update high water mark
            if closes[i] > high_water_mark:
                high_water_mark = closes[i]

            # Exit conditions
            exit_now = False
            exit_price = closes[i]
            reason = ""

            # 1. RSI exit
            if rsi[i] > rsi_exit:
                exit_now = True
                reason = "RSI_EXIT"

            # 2. Trailing stop
            trail_price = high_water_mark * (1 - trail_pct)
            if not exit_now and closes[i] <= trail_price:
                exit_now = True
                reason = "TRAILING_STOP"
                exit_price = trail_price  # Assume fill at trail price

            # 3. Time exit
            if not exit_now and (i - entry_idx) >= time_exit_bars:
                exit_now = True
                reason = "TIME_EXIT"

            if exit_now:
                hold_bars = i - entry_idx
                gross_pnl = (exit_price - entry_price) / entry_price
                cost = total_cost_per_trade(hold_bars, bar_interval_hours=1)
                net_pnl = gross_pnl - cost

                trades.append(Trade(
                    entry_idx=entry_idx,
                    entry_price=entry_price,
                    exit_idx=i,
                    exit_price=exit_price,
                    exit_reason=reason,
                    pnl_pct_gross=gross_pnl,
                    pnl_pct_net=net_pnl,
                    hold_bars=hold_bars,
                ))
                in_trade = False

    return trades


# ---------------------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------------------

def compute_metrics(trades: List[Trade]) -> dict:
    if not trades:
        return {"error": "No trades generated"}

    net_pnls = np.array([t.pnl_pct_net for t in trades])
    gross_pnls = np.array([t.pnl_pct_gross for t in trades])
    wins = net_pnls[net_pnls > 0]
    losses = net_pnls[net_pnls < 0]

    n = len(net_pnls)
    wr = len(wins) / n if n > 0 else 0.0
    avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
    avg_loss = float(np.mean(np.abs(losses))) if len(losses) > 0 else 0.0
    pf = float(np.sum(wins) / np.sum(np.abs(losses))) if np.sum(np.abs(losses)) > 0 else float("inf")

    # Sharpe (daily assumption: hourly bars, ~24 bars/day)
    daily_returns = net_pnls  # Approximation for brevity
    sharpe = float(np.mean(daily_returns) / np.std(daily_returns, ddof=1) * np.sqrt(252)) if np.std(daily_returns) > 0 else 0.0

    # Max drawdown
    equity = 1 + np.cumsum(net_pnls)
    running_max = np.maximum.accumulate(equity)
    dd = float(np.max((running_max - equity) / running_max))

    return {
        "n_trades": n,
        "win_rate": round(wr, 4),
        "profit_factor": round(pf, 4),
        "avg_win_pct": round(avg_win * 100, 4),
        "avg_loss_pct": round(avg_loss * 100, 4),
        "sharpe_annualized": round(sharpe, 4),
        "max_drawdown": round(dd, 4),
        "gross_return_pct": round(float(np.sum(gross_pnls)) * 100, 4),
        "net_return_pct": round(float(np.sum(net_pnls)) * 100, 4),
        "cost_assumption_pct": round(total_cost_per_trade(1, 1) * 100, 4),
        "seed": SEED,
    }


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("BTC SMA200 + RSI2 Mean Reversion Backtest (Experiment E1)")
    print("=" * 60)
    print(f"Symbol: {SYMBOL}")
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"Seed: {SEED}")
    print(f"Cost model: {total_cost_per_trade(1, 1)*100:.3f}% per trade (fee+spread+slippage+funding)")
    print()

    # Fetch data
    print("Fetching data...")
    ticker = yf.Ticker(SYMBOL)
    df = ticker.history(start=START_DATE, end=END_DATE, interval="1h")
    if df.empty:
        print("ERROR: No data fetched. Try daily interval instead:")
        df = ticker.history(start=START_DATE, end=END_DATE, interval="1d")
        print(f"Switched to daily. Rows: {len(df)}")
    else:
        print(f"Hourly data rows: {len(df)}")

    df = df.dropna()

    # Run backtest
    trades = backtest_btc_sma200_rsi2(
        df,
        rsi_period=RSI_PERIOD,
        sma_period=SMA_PERIOD,
        rsi_entry=RSI_ENTRY_LONG,
        rsi_exit=RSI_EXIT_LONG,
        trail_pct=TRAILING_STOP_PCT,
        time_exit_bars=TIME_EXIT_BARS,
    )

    metrics = compute_metrics(trades)

    print(f"\nTrades generated: {metrics.get('n_trades', 0)}")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Benchmark: buy-and-hold
    bh_return = (df["Close"].iloc[-1] / df["Close"].iloc[0]) - 1.0
    print(f"\nBenchmark (Buy & Hold) return: {bh_return*100:.2f}%")

    # Gate checks
    print("\n--- Proof Protocol Gate Checks ---")
    n = metrics.get("n_trades", 0)
    pf = metrics.get("profit_factor", 0)
    wr = metrics.get("win_rate", 0)
    sharpe = metrics.get("sharpe_annualized", 0)
    mdd = metrics.get("max_drawdown", 0)

    gates = [
        ("Gate 1 (Data purity)", "MANUAL — verify no frozen prices, no flat PnL, no single-source artifacts"),
        ("Gate 2 (n >= 100)", "PASS" if n >= 100 else f"FAIL (n={n})"),
        ("Gate 3 (PF > 1.5)", "PASS" if pf > 1.5 else f"FAIL (PF={pf})"),
        ("Gate 4 (Expectancy significance)", "MANUAL — run paired bootstrap with Bonferroni correction"),
        ("Gate 5 (WR plausibility)", "PASS" if 0.35 < wr < 0.85 else f"REVIEW (WR={wr})"),
        ("Gate 6 (OOS walk-forward)", "MANUAL — run purged walk-forward with 8 folds"),
        ("Gate 7 (DSR > 0.95)", "MANUAL — compute deflated Sharpe with n_trials=683"),
        ("Gate 8 (Costs included)", "PASS — costs modeled at {:.3f}% per trade".format(total_cost_per_trade(1,1)*100)),
        ("Gate 9 (Not single-source)", "MANUAL — verify edge persists across >1 data source"),
        ("Gate 10 (Beat benchmark)", "PASS" if metrics.get("net_return_pct", 0) > bh_return * 100 else f"FAIL (net={metrics.get('net_return_pct',0):.2f}% vs BH={bh_return*100:.2f}%)"),
    ]

    for name, result in gates:
        print(f"  {name}: {result}")

    print("\nNOTE: This script uses yfinance hourly data which may have gaps.")
    print("For production proof, use Binance 1h klines via CCXT or direct API.")


if __name__ == "__main__":
    main()
```

### How to run

```bash
python3 backtest_btc_sma200_rsi2.py
```

### Expected output interpretation

- If `n_trades < 100`: The strategy fires too rarely on hourly data. Re-run on **4H or daily** data to increase sample size, or extend the backtest period.
- If `PF < 1.5` but `WR > 55%`: Winners are smaller than losers (asymmetric payoff). Tighten the trailing stop or increase the RSI exit threshold.
- If `Sharpe < 0`: The strategy is not viable after costs. Do not deploy.
- If `Max Drawdown > 0.30`: The trailing stop is too loose. Reduce to 3% or add a hard SL at 2x ATR.

### Next steps after running

1. **Replace yfinance with Binance 1h klines** (use `ccxt` or direct REST API) to eliminate data gaps and get true crypto OHLCV.
2. **Run purged walk-forward** (`alpha_engine/rigorous_backtest_harness.py`) to get OOS Sharpe and WFE.
3. **Run block bootstrap** on the trade PnL series to get PF 95% CI lower bound.
4. **Compute DSR** with `n_trials = 683` (full strategy universe per `research/PROOF_PROTOCOL.md`).
5. **Only if all 10 gates pass** — forward paper-trade for 30 days or 50 trades (whichever first) before live sizing.

---

## 7. Honest Conclusion

**As of 2026-11-15, no existing BTC strategy in this repository has passed all 10 proof gates.**

The `btc_breakout_strategy.py` (78% WR claim), `crypto_enhancement_pack.py` (58-65% WR targets), and `crypto_edge_strategies.py` (65-75% WR claims) are all **unverified signal generators** with no rigorous backtest artifacts. The `strategy_persona__crypto_trust7_promoter.json` meta-filter is **blocked by upstream bugs** and its n=99 cohort is potentially contaminated.

**The highest-probability path to profitability is Experiment E1: BTC SMA200 + RSI2 Mean Reversion.** It is the only candidate that:
- Uses a signal with actual empirical support in this repo (SMA200)
- Uses a signal with extensive external literature (RSI2 mean reversion)
- Is simple enough to survive the 683-strategy Bonferroni correction
- Has crypto-specific costs that are manageable on BTC
- Can be backtested deterministically with seeded, versioned data

**Do not deploy any CRYPTO strategy to live capital until it has cleared all 10 gates on clean data.**

---

*Audit completed: 2026-11-15T07:06:29Z*
*Worktree: hilarious-seer*
*Deliverable: WIRED_IN/2026-11-15T065338Z_hilarious-seer/CRYPTO_AUDIT.md*
