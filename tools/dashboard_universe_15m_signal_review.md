# Dashboard universe — 15m signal review (TA scan)

**Generated:** 2026-04-08 04:49 UTC
**Source:** `tools/scan_multi_symbol_15m.py` on **bybit** (spot), timeframe **15m**.
**Universe note:** Symbols match your dashboard screenshots (deduped). `RENDER/USDT` is used for the old RNDR ticker on Bybit spot. Some bases (e.g. ZEC) may not list on Bybit spot — that row will show **ERROR**; use another exchange or drop the symbol.

## How to use this for later review

1. **Anchor:** Each row records the **last closed 15m close** (approximate scan-time price) under **Anchor price**.
2. **Implied direction** is **not** a trade recommendation: it aggregates (a) latest-bar candlestick patterns, (b) EMA9/21/50 stack, (c) price vs SMA200.
3. **Certainty** reflects **how many of those three agree** in the same direction; conflicts are labeled LOW.
4. When you ask for a review, provide **current price** (or ask the assistant to fetch it): compare vs anchor to judge whether **follow-through** matched the implied bias (LONG = higher, SHORT = lower, NEUTRAL = no strong edge).

## Summary table

| Symbol | Patterns (latest bar) | Trend / macro | Implied direction | Certainty | Anchor price |
|--------|------------------------|---------------|-------------------|-----------|--------------|
| APT/USDT | Candle patterns lean LONG (1 bull vs 0 bear) | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **HIGH** | 0.874 |
| ATOM/USDT | No candlestick pattern on latest bar | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 1.79 |
| ALGO/USDT | Candle patterns lean SHORT (2 bear vs 1 bull) | Bullish EMA9>21>50; Price above SMA200 (macro long) | **NEUTRAL / WAIT** | **LOW** | 0.1208 |
| BNB/USDT | Candle patterns lean LONG (1 bull vs 0 bear) | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **HIGH** | 615.7 |
| BTC/USDT | No candlestick pattern on latest bar | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 71670 |
| DOGE/USDT | No candlestick pattern on latest bar | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 0.09477 |
| DOT/USDT | Candle patterns lean SHORT (1 bear vs 0 bull) | Bullish EMA9>21>50; Price above SMA200 (macro long) | **NEUTRAL / WAIT** | **LOW** | 1.318 |
| ETC/USDT | No candlestick pattern on latest bar | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 8.736 |
| ETH/USDT | No candlestick pattern on latest bar | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 2250.12 |
| FET/USDT | No candlestick pattern on latest bar | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 0.2494 |
| HBAR/USDT | No candlestick pattern on latest bar | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 0.0933 |
| INJ/USDT | No candlestick pattern on latest bar | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 3.027 |
| NEAR/USDT | No candlestick pattern on latest bar | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 1.306 |
| RENDER/USDT | Candle patterns lean LONG (1 bull vs 0 bear) | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **HIGH** | 2.046 |
| SHIB/USDT | No candlestick pattern on latest bar | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 0.000006 |
| SOL/USDT | Candle patterns lean SHORT (2 bear vs 0 bull) | Bullish EMA9>21>50; Price above SMA200 (macro long) | **NEUTRAL / WAIT** | **LOW** | 84.77 |
| SUI/USDT | No candlestick pattern on latest bar | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 0.9626 |
| TIA/USDT | Patterns mixed (1 bull, 1 bear) | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **MEDIUM** | 0.3096 |
| WLD/USDT | Candle patterns lean SHORT (2 bear vs 0 bull) | Mixed/choppy MA stack; Price above SMA200 (macro long) | **NEUTRAL / WAIT** | **LOW** | 0.2628 |
| XRP/USDT | Candle patterns lean LONG (1 bull vs 0 bear) | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **HIGH** | 1.3772 |
| ZEC/USDT | — | — | **ERROR** | — | `  Error: bybit does not have market symbol ZEC/USDT` |
| ZIL/USDT | Candle patterns lean LONG (1 bull vs 0 bear) | Bullish EMA9>21>50; Price above SMA200 (macro long) | **LONG** | **HIGH** | 0.004003 |

## Per-symbol detail

### APT/USDT

- **Implied direction:** LONG (component score sum: 3)
- **Certainty:** HIGH — All 3 components align LONG.
- **Anchor price (15m close at scan):** 0.874
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** Candle patterns lean LONG (1 bull vs 0 bear)
- **Pattern lines:**
  - `[BULLISH] Doji (signal: 100)`

### ATOM/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 1.79
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** No candlestick pattern on latest bar

### ALGO/USDT

- **Implied direction:** NEUTRAL / WAIT (component score sum: 1)
- **Certainty:** LOW — Conflict: 2 long-leaning vs 1 short-leaning among non-neutral signals.
- **Anchor price (15m close at scan):** 0.1208
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** Candle patterns lean SHORT (2 bear vs 1 bull)
- **Pattern lines:**
  - `[BULLISH] Doji (signal: 100)`
  - `[BEARISH] Harami (Bullish) (signal: -80)`
  - `[BEARISH] Harami Cross (signal: -80)`

### BNB/USDT

- **Implied direction:** LONG (component score sum: 3)
- **Certainty:** HIGH — All 3 components align LONG.
- **Anchor price (15m close at scan):** 615.7
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** Candle patterns lean LONG (1 bull vs 0 bear)
- **Pattern lines:**
  - `[BULLISH] Doji (signal: 100)`

### BTC/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 71670.0
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** No candlestick pattern on latest bar

### DOGE/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 0.09477
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** No candlestick pattern on latest bar

### DOT/USDT

- **Implied direction:** NEUTRAL / WAIT (component score sum: 1)
- **Certainty:** LOW — Conflict: 2 long-leaning vs 1 short-leaning among non-neutral signals.
- **Anchor price (15m close at scan):** 1.318
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** Candle patterns lean SHORT (1 bear vs 0 bull)
- **Pattern lines:**
  - `[BEARISH] Engulfing (Bullish) (signal: -80)`

### ETC/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 8.736
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** No candlestick pattern on latest bar

### ETH/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 2250.12
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** No candlestick pattern on latest bar

### FET/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 0.2494
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** No candlestick pattern on latest bar

### HBAR/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 0.0933
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** No candlestick pattern on latest bar

### INJ/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 3.027
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** No candlestick pattern on latest bar

### NEAR/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 1.306
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** No candlestick pattern on latest bar

### RENDER/USDT

- **Implied direction:** LONG (component score sum: 3)
- **Certainty:** HIGH — All 3 components align LONG.
- **Anchor price (15m close at scan):** 2.046
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** Candle patterns lean LONG (1 bull vs 0 bear)
- **Pattern lines:**
  - `[BULLISH] Doji (signal: 100)`

### SHIB/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 6e-06
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** No candlestick pattern on latest bar

### SOL/USDT

- **Implied direction:** NEUTRAL / WAIT (component score sum: 1)
- **Certainty:** LOW — Conflict: 2 long-leaning vs 1 short-leaning among non-neutral signals.
- **Anchor price (15m close at scan):** 84.77
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** Candle patterns lean SHORT (2 bear vs 0 bull)
- **Pattern lines:**
  - `[BEARISH] Engulfing (Bullish) (signal: -80)`
  - `[BEARISH] Marubozu (signal: -100)`

### SUI/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 0.9626
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** No candlestick pattern on latest bar

### TIA/USDT

- **Implied direction:** LONG (component score sum: 2)
- **Certainty:** MEDIUM — 2 component(s) align LONG; no opposing votes.
- **Anchor price (15m close at scan):** 0.3096
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** Patterns mixed (1 bull, 1 bear)
- **Pattern lines:**
  - `[BULLISH] Doji (signal: 100)`
  - `[BEARISH] Hanging Man (signal: -100)`

### WLD/USDT

- **Implied direction:** NEUTRAL / WAIT (component score sum: 0)
- **Certainty:** LOW — Conflict: 1 long-leaning vs 1 short-leaning among non-neutral signals.
- **Anchor price (15m close at scan):** 0.2628
- **Trend:** Mixed/choppy MA stack
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** Candle patterns lean SHORT (2 bear vs 0 bull)
- **Pattern lines:**
  - `[BEARISH] Engulfing (Bullish) (signal: -80)`
  - `[BEARISH] Marubozu (signal: -100)`

### XRP/USDT

- **Implied direction:** LONG (component score sum: 3)
- **Certainty:** HIGH — All 3 components align LONG.
- **Anchor price (15m close at scan):** 1.3772
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** Candle patterns lean LONG (1 bull vs 0 bear)
- **Pattern lines:**
  - `[BULLISH] Doji (signal: 100)`

### ZEC/USDT

- **Fetch error:**   Error: bybit does not have market symbol ZEC/USDT

### ZIL/USDT

- **Implied direction:** LONG (component score sum: 3)
- **Certainty:** HIGH — All 3 components align LONG.
- **Anchor price (15m close at scan):** 0.004003
- **Trend:** Bullish EMA9>21>50
- **Macro:** Price above SMA200 (macro long)
- **Patterns:** Candle patterns lean LONG (1 bull vs 0 bear)
- **Pattern lines:**
  - `[BULLISH] Doji (signal: 100)`
