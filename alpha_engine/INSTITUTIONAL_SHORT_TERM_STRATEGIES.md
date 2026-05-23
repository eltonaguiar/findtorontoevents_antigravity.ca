# Institutional-Grade Short-Term Trading Strategies (5m–1h)

**Target:** Crypto & Forex | **Horizon:** 2-hour windows | **Data:** OHLCV + volume (public)

Research synthesis from institutional frameworks (Citadel, Two Sigma, Renaissance, Jump, Jane Street–style) and published quant work. Each strategy has **exact, codeable rules**, TP/SL, edge thesis, and Python pseudocode.

---

## Strategy 1: Opening Range Breakout (ORB) with ATR Stops

| Field | Value |
|-------|--------|
| **Name** | 5-Minute Opening Range Breakout (ORB) + Dynamic ATR |
| **Asset class** | Forex, Crypto (both) |
| **Timeframe** | 5-minute; first candle = opening range |

### Entry

- **Long:** Price closes **above** opening range high (ORH). ORH = high of first 5m candle after session open (e.g. 00:00 UTC for crypto; 09:30 ET for US).
- **Short:** Price closes **below** opening range low (ORL). ORL = low of first 5m candle.
- **Filter (optional):** Volume of breakout candle > 1.2× average volume of prior 20 bars.

### Exit

- **Stop loss:** Entry − 1× ATR(14) for long; Entry + 1× ATR(14) for short. ATR on same 5m series.
- **Take profit:** Entry ± 1.5× ATR(14) → **risk:reward = 1:1.5**.
- **Time stop:** Flat at end of 2-hour window if neither TP nor SL hit.

### Edge

- Opening range captures overnight/off-hours information; breakouts often continue in the direction of the break. ATR aligns risk with current volatility.

### Risk management

- Max 1 position per symbol per session. Risk per trade ≤ 1% of equity. Position size = (Account × 0.01) / (1 × ATR).

### Python pseudocode

```python
def orb_atr_strategy(ohlcv_5m, session_start_idx):
    # Opening range = first 5m bar after session start
    or_high = ohlcv_5m.high[session_start_idx]
    or_low = ohlcv_5m.low[session_start_idx]
    atr = atr_14(ohlcv_5m.close, ohlcv_5m.high, ohlcv_5m.low)

    for i in range(session_start_idx + 1, min(session_start_idx + 24, len(ohlcv_5m))):  # 2h = 24 bars
        close, high, low = ohlcv_5m.close[i], ohlcv_5m.high[i], ohlcv_5m.low[i]
        atr_i = atr[i]

        # Long: close above ORH
        if close > or_high:
            entry = close
            sl = entry - atr_i
            tp = entry + 1.5 * atr_i
            return ("long", entry, sl, tp)

        # Short: close below ORL
        if close < or_low:
            entry = close
            sl = entry + atr_i
            tp = entry - 1.5 * atr_i
            return ("short", entry, sl, tp)

    return None  # no signal in 2h window
```

---

## Strategy 2: Order Book Imbalance (OBI) / Order Flow Imbalance

| Field | Value |
|-------|--------|
| **Name** | Order Flow Imbalance (OFI) Z-Score Signal |
| **Asset class** | Crypto (best), Forex (where L2 is available) |
| **Timeframe** | 1-second to 1-minute buckets; trade resolution 1–5 minutes |

### Entry

- **OFI formula (per bucket):**  
  `e_n = I{P_bid_n >= P_bid_{n-1}} * q_bid_n - I{P_bid_n <= P_bid_{n-1}} * q_bid_{n-1} - I{P_ask_n <= P_ask_{n-1}} * q_ask_n + I{P_ask_n >= P_ask_{n-1}} * q_ask_{n-1}`  
  Sum `e` over bucket (e.g. 60 seconds) → raw OFI.
- **Normalize:** OFI_z = (OFI − rolling_mean_5min(OFI)) / sqrt(rolling_var_5min(OFI)).
- **Long:** OFI_z > +1.5 (or use linear predictor: predicted_return = β × OFI_z, β ≈ 0.14–0.15 from literature).
- **Short:** OFI_z < −1.5 (or sign(predicted_return) < 0).

### Exit

- **TP/SL:** 1× ATR(14) on 1m; or fixed horizon (e.g. next 1–5 minutes). R:R at least 1:1.
- **Time stop:** 2-hour window; close at end of window.

### Edge

- Order book imbalance reflects supply/demand before price; positive OFI predicts positive short-horizon returns (documented R² ~3% out-of-sample, ~53% hit rate in 1s backtests). Exploits microstructure lead-lag.

### Risk management

- Filter: trade only when |OFI_z| > 1.5 to reduce noise. Position size by ATR. Cap round-trips to control fees (OFI is HFT-ish; costs matter).

### Python pseudocode

```python
def ofi_signal(bbo_ticks):  # bbo = best bid/offer (price, size) per tick
    e = []
    for n in range(1, len(bbo_ticks)):
        pb, qb = bbo_ticks[n].bid, bbo_ticks[n].bidsize
        pa, qa = bbo_ticks[n].ask, bbo_ticks[n].asksize
        pb_1, qb_1 = bbo_ticks[n-1].bid, bbo_ticks[n-1].bidsize
        pa_1, qa_1 = bbo_ticks[n-1].ask, bbo_ticks[n-1].asksize
        en = (1 if pb >= pb_1 else 0) * qb - (1 if pb <= pb_1 else 0) * qb_1
        en -= (1 if pa <= pa_1 else 0) * qa - (1 if pa >= pa_1 else 0) * qa_1
        e.append(en)

    # Bucket into 60-second windows, sum e -> OFI per bucket
    ofi_buckets = bucket_sum(e, window_seconds=60)
    ofi_avg = rolling_mean(ofi_buckets, 5 * 60)   # 5 min
    ofi_std = rolling_std(ofi_buckets, 5 * 60)
    ofi_z = (ofi_buckets - ofi_avg) / (ofi_std + 1e-8)

    # Signal: threshold or linear predictor
    if ofi_z[-1] > 1.5:
        return "long"
    if ofi_z[-1] < -1.5:
        return "short"
    return None
```

---

## Strategy 3: Funding Rate Arbitrage (Delta-Neutral)

| Field | Value |
|-------|--------|
| **Name** | Cross-Exchange / Single-Venue Funding Rate Arbitrage |
| **Asset class** | Crypto only |
| **Timeframe** | Hold 8h–24h+; entry/exit on funding timestamps (e.g. 00:00, 08:00, 16:00 UTC). |

### Entry

- **Condition:** Funding rate (or rate differential) **after fees** > threshold. Example: net funding (received − paid) > 0.01% per 8h (≈ 0.03%/day) for single-venue; or cross-exchange spread > 0.02% per 8h.
- **Execution:** Long spot + short perp (same notional), or short high-funding venue + long low-funding venue (equal notionals). Rebalance at each funding to stay delta-neutral.

### Exit

- **TP:** None (yield strategy). Exit when funding rate converges or flips (e.g. rate on short side turns negative).
- **SL:** Drawdown or basis risk limit (e.g. exit if spot–perp basis moves against position by > 2%).
- **Time:** Can run for days/weeks; 2-hour “window” = decision window to enter/exit before next funding.

### Edge

- Perps trade rich vs spot; longs pay shorts. Being short perp + long spot harvests funding. Cross-exchange arbitrage exploits 5.98%–23% APR spreads (documented). Inefficiency: funding is sticky and cross-venue dispersion persists.

### Risk management

- Margin = max(margin_A, margin_B) × 1.3 buffer. Position size so that margin usage < 50%. Monitor basis risk; exit if correlation breaks.

### Python pseudocode

```python
def funding_arb_entry(rate_venue_a, rate_venue_b, fee_per_side=0.0002):
    # rate = funding rate per 8h (e.g. 0.0001 = 0.01%)
    net_a = rate_venue_a - fee_per_side  # short perp, receive funding
    net_b = -rate_venue_b - fee_per_side  # long perp, pay funding
    spread = net_a - net_b
    if spread > 0.0001:  # 0.01% per 8h minimum
        return "short_venue_a_long_venue_b", spread
    return None, 0

def position_size(capital, margin_rate_a, margin_rate_b, buffer=1.3):
    margin_per_unit = max(margin_rate_a, margin_rate_b) * buffer
    return (capital * 0.5) / margin_per_unit  # use 50% capital for margin
```

---

## Strategy 4: Z-Score Pairs (Mean Reversion) Intraday

| Field | Value |
|-------|--------|
| **Name** | Z-Score Pairs Trading (Cointegration + Z-Score Bands) |
| **Asset class** | Crypto (pairs: BTC/ETH, major alts), Forex (e.g. EUR/USD vs EUR/GBP) |
| **Timeframe** | 5m or 15m; hold 1–2 hours. |

### Entry

- **Spread:** `spread = log(P_A) - β * log(P_B)` or price ratio; β from rolling cointegration (e.g. Engle–Granger) over 20–60 bars.
- **Z-score:** `z = (spread - rolling_mean(spread, 60)) / rolling_std(spread, 60)`.
- **Long pair (long A, short B):** Z ≤ −2.0.
- **Short pair (short A, long B):** Z ≥ +2.0.
- **Optional:** Hurst < 0.5 for spread (mean-reverting regime); correlation > 0.8.

### Exit

- **TP:** Z crosses back toward 0 (e.g. Z in [-0.5, +0.5] or opposite position open).
- **SL:** Z exceeds ±3.0 (add or stop out); or 2-hour time stop.
- **Stop loss in price:** 1× ATR of spread (in price terms) from entry.

### Edge

- Cointegrated pairs temporarily diverge; z-score identifies statistically extreme divergence. Mean reversion in spread is documented; intraday often better than daily (faster resolution). Retail-driven crypto enhances short-term mean reversion.

### Risk management

- Equal dollar exposure long and short. Max 2–3 pairs at once. Risk per pair ≤ 1% (size by spread ATR).

### Python pseudocode

```python
def zscore_pairs_signal(price_a, price_b, lookback=60):
    spread = np.log(price_a) - hedge_ratio(price_a, price_b, lookback) * np.log(price_b)
    mu = rolling_mean(spread, lookback)
    sigma = rolling_std(spread, lookback)
    z = (spread - mu) / (sigma + 1e-8)

    if z[-1] <= -2.0:
        return "long_a_short_b", z[-1]
    if z[-1] >= 2.0:
        return "short_a_long_b", z[-1]
    return None, z[-1]

def exit_condition(z_current, z_entry, hold_bars_max=24):
    if abs(z_current) <= 0.5:
        return "take_profit"
    if abs(z_current) >= 3.0:
        return "stop_loss"
    return None  # else time-based exit at hold_bars_max
```

---

## Strategy 5: VWAP Deviation Bands (Mean Reversion)

| Field | Value |
|-------|--------|
| **Name** | VWAP Deviation with ±2σ Bands |
| **Asset class** | Crypto, Forex (both) |
| **Timeframe** | 5m or 15m; session = 2-hour window (or daily VWAP reset). |

### Entry

- **VWAP** = cumulative(price × volume) / cumulative(volume), reset at session start.
- **Bands:** Upper/Lower = VWAP ± 2 × rolling_std(price, 20) (or std of residuals around VWAP).
- **Long (H1/H2 style):** Price opens **below** lower band and **closes above** lower band (bullish rejection). Signal strength = (close − low) / (high − low) > 0.7.
- **Short (L1/L2 style):** Price opens **above** upper band and **closes below** upper band. Signal strength > 0.7.
- **Filter:** Band width > 3× ATR(14) (avoid low-volatility chop).

### Exit

- **TP:** Price touches VWAP (mean reversion target).
- **SL:** Bar low − buffer (long) or bar high + buffer (short); buffer = 1–5 ticks or 0.1× ATR.
- **Safety:** Exit after 3 consecutive opposing bars (close < open for long; close > open for short).

### Edge

- Institutions trade around VWAP; large deviations tend to revert. Exploits temporary mispricing vs volume-weighted fair value.

### Risk management

- One position per symbol per session. Stop always on. Max risk 1% per trade.

### Python pseudocode

```python
def vwap_deviation_signal(ohlcv, session_start_idx):
    vwap = cumulative(ohlcv.close * ohlcv.volume) / cumulative(ohlcv.volume)
    std = rolling_std(ohlcv.close, 20)
    upper = vwap + 2 * std
    lower = vwap - 2 * std
    atr = atr_14(ohlcv)

    for i in range(session_start_idx + 1, len(ohlcv)):
        o, h, l, c = ohlcv.open[i], ohlcv.high[i], ohlcv.low[i], ohlcv.close[i]
        band_width = upper[i] - lower[i]
        if band_width < 3 * atr[i]:
            continue

        # Long: open below lower, close above lower
        if o < lower[i] and c > lower[i] and c < upper[i]:
            strength = (c - l) / (h - l + 1e-8)
            if strength > 0.7:
                return "long", c, l - 0.1 * atr[i], vwap[i]

        # Short: open above upper, close below upper
        if o > upper[i] and c < upper[i] and c > lower[i]:
            strength = (h - c) / (h - l + 1e-8)
            if strength > 0.7:
                return "short", c, h + 0.1 * atr[i], vwap[i]
    return None
```

---

## Strategy 6: RSI + EMA Momentum (5-Minute Momo)

| Field | Value |
|-------|--------|
| **Name** | 5-Minute EMA Crossover + RSI Filter |
| **Asset class** | Forex, Crypto (both) |
| **Timeframe** | 5-minute; hold 30m–2h. |

### Entry

- **Bullish:** EMA(5) crosses **above** EMA(20) within last 5 bars; RSI(14) > 50 and < 70; close > EMA(20).
- **Bearish:** EMA(5) crosses **below** EMA(20) within last 5 bars; RSI(14) < 50 and > 30; close < EMA(20).
- **Optional:** Only when daily volatility (e.g. ATR(14)/close on daily) > 1%; trend strength (e.g. ADX(14)) ≤ 25 for mean-reversion regime, or > 25 for trend.

### Exit

- **TP:** Entry ± 1.4× risk (1.4:1 R:R from backtests). Or trail: exit when close crosses EMA(20) against position.
- **SL:** Below recent swing low (long) or above recent swing high (short); or 1× ATR(14) from entry.
- **Time stop:** 2 hours.

### Edge

- Short-term momentum (EMA cross) with overbought/oversold filter (RSI) reduces false breakouts. Documented backtest (e.g. GBP/USD 2011–2015): ~46% win rate, 1.4:1 R:R, positive expectancy.

### Risk management

- Risk per trade 1%. Position size = (0.01 × equity) / (1 × ATR). No new trade if already in position.

### Python pseudocode

```python
def momo_5m_signal(close, high, low, period=14):
    ema5 = ema(close, 5)
    ema20 = ema(close, 20)
    rsi = rsi_14(close)
    atr = atr_14(close, high, low)

    # Cross in last 5 bars
    cross_up = (ema5[-6] <= ema20[-6]) and (ema5[-1] > ema20[-1])
    cross_dn = (ema5[-6] >= ema20[-6]) and (ema5[-1] < ema20[-1])

    if cross_up and 50 < rsi[-1] < 70 and close[-1] > ema20[-1]:
        entry = close[-1]
        sl = entry - atr[-1]
        tp = entry + 1.4 * atr[-1]
        return "long", entry, sl, tp

    if cross_dn and 30 < rsi[-1] < 50 and close[-1] < ema20[-1]:
        entry = close[-1]
        sl = entry + atr[-1]
        tp = entry - 1.4 * atr[-1]
        return "short", entry, sl, tp

    return None
```

---

## Strategy 7: Book Skew (Bid/Ask Depth Imbalance) – Retail HFT-Style

| Field | Value |
|-------|--------|
| **Name** | Book Skew / Bid-Ask Depth Imbalance |
| **Asset class** | Crypto, Forex (where L2 is available) |
| **Timeframe** | 1–5 minute bars; hold 5–30 minutes. |

### Entry

- **Imbalance:** `skew = (bid_depth_5 - ask_depth_5) / (bid_depth_5 + ask_depth_5)` where depth = sum of size in top 5 levels (or top 1 level for speed).
- **Long:** skew > +0.25 (bid depth >> ask depth).
- **Short:** skew < −0.25.
- **Confirmation:** Price not already extended (e.g. distance from VWAP < 1× ATR).

### Exit

- **TP:** 0.5× ATR(14) or skew reverts to [-0.1, +0.1].
- **SL:** 1× ATR(14). R:R ≥ 1:2 (e.g. SL = 1 ATR, TP = 0.5 ATR with higher win rate, or TP = 1 ATR and accept lower win rate).
- **Time stop:** 30 minutes.

### Edge

- Order book imbalance predicts short-term direction (institutional flow); retail implementation at 1–5m avoids sub-second costs. Exploits information in depth, not just last price.

### Risk management

- Small size (high turnover); account for fees. Only trade when spread is tight (e.g. spread < 0.05% of mid).

### Python pseudocode

```python
def book_skew_signal(bid_depth_5, ask_depth_5, vwap, atr, close):
    skew = (bid_depth_5 - ask_depth_5) / (bid_depth_5 + ask_depth_5 + 1e-8)
    if abs(close - vwap) > atr:
        return None  # price already extended

    if skew > 0.25:
        return "long", 0.5 * atr, 1.0 * atr
    if skew < -0.25:
        return "short", 0.5 * atr, 1.0 * atr
    return None
```

---

## Summary Table

| # | Strategy              | Asset   | Entry trigger              | TP/SL              | Edge source                    |
|---|------------------------|---------|----------------------------|--------------------|--------------------------------|
| 1 | ORB + ATR              | FX/Crypto | Close beyond ORH/ORL       | 1 ATR SL, 1.5 ATR TP | Breakout + volatility scaling  |
| 2 | Order Flow Imbalance   | Crypto  | OFI_z > 1.5 / < -1.5       | 1 ATR or 1–5m      | Microstructure lead-lag       |
| 3 | Funding Rate Arb       | Crypto  | Funding spread > fee+min   | Convergence / basis | Funding stickiness, cross-venue |
| 4 | Z-Score Pairs          | Both    | Z ≤ -2 / Z ≥ +2            | Z → 0, ±3 SL       | Cointegration mean reversion  |
| 5 | VWAP Deviation Bands   | Both    | Close through ±2σ band     | VWAP / 3-bar       | Institutional VWAP reversion  |
| 6 | 5m EMA + RSI Momo      | Both    | EMA5×EMA20 + RSI filter    | 1.4R TP, 1 ATR SL  | Momentum + filter              |
| 7 | Book Skew              | Crypto/FX | skew ±0.25                | 0.5 ATR TP, 1 ATR SL | Depth imbalance               |

---

## Data & Implementation Notes

- **OHLCV + volume:** Strategies 1, 4, 5, 6 can run on standard 5m/15m OHLCV.
- **Order book / L2:** Strategies 2 and 7 need best bid/offer and depth (and optionally tick data). Crypto: Binance, Coinbase, etc. Forex: depends on broker.
- **Funding:** Strategy 3 needs funding rates from exchanges (e.g. Binance, Bybit, Hyperliquid); cross-venue needs multiple APIs.
- **2-hour windows:** Implement as a session (e.g. 00:00–02:00 UTC) and disable new entries after 2h; time-stop all open trades at session end.
- **Statistical edge:** ORB, OFI, pairs (z-score), and funding arb have published or documented backtests; RSI+EMA has reported 1.4:1 R:R. Always re-backtest on your universe and costs.

---

*References: FXNX institutional order flow; Dean Markwick OFI; FMZ/Medium 5m ORB & VWAP; Z-score pairs (FasterCapital, QuantStock); funding arb (Polynomial, Sharpe AI, Boros); book skew (IBKR Quant, Databento); RSI/EMA (FX Helpline, MQL5).*
