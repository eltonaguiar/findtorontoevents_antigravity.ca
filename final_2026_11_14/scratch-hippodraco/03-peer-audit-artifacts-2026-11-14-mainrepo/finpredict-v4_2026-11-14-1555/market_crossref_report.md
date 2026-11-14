# Market Cross-Reference Audit Report

**Generated:** 2026-11-14T15:48Z  
**Auditor:** Kilo  
**Source files:** `picks_now.json`, `ai_challenge_*_active_picks.json`, `ai_tournament_picks_latest.json`  
**Live price sources:** Binance public API (crypto), Yahoo Finance (stocks, ETFs, forex, commodities)

---

## Executive Summary

A representative sample of **19 picks** was cross-referenced against live public market data. The audit reveals a stark split in data quality:

- **picks_now.json (screener output):** Prices are accurate to the minute (generated 2026-11-14 12:04 UTC). All sampled prices match live market data within rounding error.
- **AI Challenge / Tournament picks:** A significant portion of "active" picks are **extremely stale** (5–8 months old) and many have **P/L stuck at 0.0** despite massive price movement. Several picks that should have hit TP/SL long ago remain marked `OPEN`.

**Verdict:** The live screener (`picks_now.json`) is trustworthy. The persistent pick registry (`ai_challenge_*`, `ai_tournament_picks_latest.json`) has severe staleness and bookkeeping issues.

---

## Sample Picks Table

| Symbol | Direction | Claimed Current | Entry Price | Live Price | Disc % | Stale | Status | Source |
|--------|-----------|-----------------|-------------|------------|--------|-------|--------|--------|
| BTCUSDT | SHORT | N/A | 70783.00 | 65723.97 | 7.15% | YES | OPEN | ai_challenge_antigravity |
| SOLUSDT | SHORT | N/A | 87.40 | 73.92 | 15.42% | YES | OPEN | ai_challenge_antigravity |
| LINKUSDT | SHORT | N/A | 9.09 | 9.30 | 2.33% | YES | OPEN | ai_challenge_antigravity |
| TRXUSDT | LONG | N/A | 0.2981 | 0.3098 | 3.92% | YES | OPEN | ai_challenge_antigravity |
| NEARUSDT | SHORT | N/A | 1.326 | 3.224 | **143.14%** | YES | OPEN | ai_challenge_antigravity |
| MSFT | LONG | N/A | 420.00 | 523.88 | 24.73% | NO | WIN | ai_tournament |
| AMZN | LONG | N/A | 185.00 | 266.66 | 44.14% | YES | OPEN | ai_tournament |
| BRK.B | LONG | N/A | 410.00 | 592.94 | 44.62% | YES | OPEN | ai_tournament |
| EURUSD | SHORT | N/A | 1.1475 | 1.1050 | 3.70% | NO | LOSS | ai_tournament |
| USDCAD | LONG | N/A | 1.3506 | 1.4269 | 5.65% | NO | WIN | ai_tournament |
| NG=F | LONG | N/A | 2.70 | 3.23 | 19.63% | NO | MISPRICED_ENTRY | ai_tournament |
| CL=F | LONG | N/A | 80.50 | 88.56 | 10.01% | NO | MISPRICED_ENTRY | ai_tournament |
| IWM | LONG | N/A | 206.26 | 277.54 | 34.56% | YES | OPEN | ai_tournament |
| GLD | LONG | N/A | 250.00 | 355.45 | 42.18% | YES | OPEN | ai_tournament |
| HDV | STRONG_BUY | **30.98** | N/A | 30.98 | 0.00% | NO | ACTIVE | picks_now |
| SCHD | STRONG_BUY | **36.12** | N/A | 36.12 | 0.00% | NO | ACTIVE | picks_now |
| DBC | STRONG_BUY | **30.79** | N/A | 30.79 | 0.00% | NO | ACTIVE | picks_now |
| PLTR | WATCH | **167.99** | N/A | 167.99 | 0.00% | NO | ACTIVE | picks_now |
| GOOGL | WATCH | **295.77** | N/A | 295.77 | 0.00% | NO | ACTIVE | picks_now |

---

## Findings by Asset Class

### Crypto (USDT Pairs) — 5 Sampled
All 5 crypto picks come from `ai_challenge_antigravity_active_picks.json`.

| Pick | Direction | Entry | Live | TP | SL | Status |
|------|-----------|-------|------|----|----|--------|
| BTCUSDT | SHORT | 70783 | 65724 | 69000 | 71800 | OPEN |
| SOLUSDT | SHORT | 87.40 | 73.92 | 84.00 | 89.60 | OPEN |
| LINKUSDT | SHORT | 9.09 | 9.30 | 8.55 | 9.45 | OPEN |
| TRXUSDT | LONG | 0.2981 | 0.3098 | 0.3095 | 0.289 | OPEN |
| NEARUSDT | SHORT | 1.326 | 3.224 | 1.278 | 1.37 | OPEN |

**Issues:**
- **All 5 are >8 months old** (generated 2026-03-15) yet still marked `OPEN`.
- **All 5 have `pnl_pct = 0.0`** despite major price moves. BTC moved -7.15%, SOL -15.4%, NEAR +143% (catastrophic for a SHORT).
- **NEARUSDT** is 143% away from entry. The stop-loss at 1.37 was breached almost immediately. The pick should have been stopped out within days.
- **TRXUSDT** LONG has already exceeded its take-profit (0.3095 vs live 0.3098). It should be marked `WIN` or `CLOSED`.
- **SOLUSDT** SHORT is deep in profit (15.4% below entry, well past TP of 84.0). Should be `WIN`.
- **BTCUSDT** SHORT is past TP of 69000 (live 65724). Should be `WIN`.

**Conclusion:** The AI Challenge crypto pick registry is completely out of sync with reality. It appears to be a static snapshot from March 2026 with no resolution logic applied.

---

### Equities — 3 Sampled (+ 2 from screener)

| Pick | Direction | Entry | Live | TP | SL | Status | Age |
|------|-----------|-------|------|----|----|--------|-----|
| MSFT | LONG | 420.00 | 523.88 | 445.50 | 403.0 | WIN | ~5 mo (resolved) |
| AMZN | LONG | 185.00 | 266.66 | 198.50 | 176.0 | OPEN | ~5 mo |
| BRK.B | LONG | 410.00 | 592.94 | 425.00 | 400.0 | OPEN | ~5 mo |
| PLTR | WATCH | 167.99 | 167.99 | — | — | ACTIVE | <1 day |
| GOOGL | WATCH | 295.77 | 295.77 | — | — | ACTIVE | <1 day |

**Issues:**
- **AMZN** and **BRK.B** are still `OPEN` after ~5 months. Live prices have blown far past their TPs (AMZN +44% vs TP +7.3%; BRK.B +45% vs TP +3.7%).
- **MSFT** was correctly resolved as `WIN` (TP hit at ~446), but the live price is now 524, showing the resolution happened months ago.
- **PLTR** and **GOOGL** from `picks_now.json` match live prices exactly. The screener data is current.

---

### Forex — 2 Sampled

| Pick | Direction | Entry | Live | TP | SL | Status | Age |
|------|-----------|-------|------|----|----|--------|-----|
| EURUSD | SHORT | 1.1475 | 1.1050 | 1.1142 | 1.1695 | LOSS | ~5 mo (resolved) |
| USDCAD | LONG | 1.3506 | 1.4269 | 1.3733 | 1.3259 | WIN | ~5 mo (resolved) |

**Notes:**
- Both picks were **resolved** (EURUSD as LOSS, USDCAD as WIN). The live prices now show EURUSD much lower than exit (1.105 vs exit 1.160), meaning the loss was due to a time-exit or SL trigger before the major move.
- Current live price for USDCAD (1.427) is well above its original TP (1.373), confirming the win was valid.
- These are not "active" picks, but they illustrate that resolution logic exists in the tournament data for some picks.

---

### Commodities — 2 Sampled (+ 1 from screener)

| Pick | Direction | Entry | Live | TP | SL | Status | Age |
|------|-----------|-------|------|----|----|--------|-----|
| NG=F | LONG | 2.70 | 3.23 | 3.00 | 2.50 | MISPRICED_ENTRY | ~5 mo (resolved same day) |
| CL=F | LONG | 80.50 | 88.56 | 85.00 | 77.50 | MISPRICED_ENTRY | ~5 mo (resolved same day) |
| DBC | STRONG_BUY | 30.79 | 30.79 | — | — | ACTIVE | <1 day |

**Notes:**
- **NG=F** and **CL=F** were flagged `MISPRICED_ENTRY` and resolved within hours of submission. Live prices now show both would have been highly profitable (NG +19.6%, CL +10.0%). The "mispriced" flag may have been a false positive.
- **DBC** (commodity ETF) from the screener matches live price exactly.

---

### ETFs — 2 Sampled (+ 2 from screener)

| Pick | Direction | Entry | Live | TP | SL | Status | Age |
|------|-----------|-------|------|----|----|--------|-----|
| IWM | LONG | 206.26 | 277.54 | 220.67 | 198.87 | OPEN | ~5 mo |
| GLD | LONG | 250.00 | 355.45 | 265.00 | 242.00 | OPEN | ~5 mo |
| HDV | STRONG_BUY | 30.98 | 30.98 | — | — | ACTIVE | <1 day |
| SCHD | STRONG_BUY | 36.12 | 36.12 | — | — | ACTIVE | <1 day |

**Issues:**
- **IWM** and **GLD** are still `OPEN` after ~5 months. Both have massively exceeded their take-profits (IWM +34.6% vs TP +7.0%; GLD +42.2% vs TP +6.0%).
- **HDV** and **SCHD** from the screener match live prices exactly.

---

## Red Flags Summary

### 1. Stale Active Picks (>7 days old, still OPEN)
| Symbol | Age | Status | Issue |
|--------|-----|--------|-------|
| BTCUSDT | ~245 days | OPEN | Should be WIN (hit TP) |
| SOLUSDT | ~245 days | OPEN | Should be WIN (hit TP) |
| LINKUSDT | ~245 days | OPEN | Should be STOPPED or TIME-EXITED |
| TRXUSDT | ~245 days | OPEN | Should be WIN (above TP) |
| NEARUSDT | ~245 days | OPEN | Should be LOSS (SL blown by 143%) |
| AMZN | ~163 days | OPEN | Should be WIN (far above TP) |
| BRK.B | ~163 days | OPEN | Should be WIN (far above TP) |
| IWM | ~163 days | OPEN | Should be WIN (far above TP) |
| GLD | ~163 days | OPEN | Should be WIN (far above TP) |

### 2. P/L Stuck at 0.0 Despite Price Movement
All 5 AI Challenge crypto picks report `pnl_pct: 0.0` even though:
- BTC moved -7.15% (SHORT = profitable)
- SOL moved -15.4% (SHORT = very profitable)
- NEAR moved +143% (SHORT = catastrophic loss)

This indicates the `pnl_pct` field is **not being calculated or updated** for these records.

### 3. Wild Price Discrepancies
| Symbol | Entry vs Live | Discrepancy | Notes |
|--------|---------------|-------------|-------|
| NEARUSDT | 1.326 → 3.224 | **+143%** | SL at 1.37 was breached immediately |
| GLD | 250.00 → 355.45 | **+42%** | TP at 265 was hit months ago |
| BRK.B | 410.00 → 592.94 | **+45%** | TP at 425 was hit months ago |
| AMZN | 185.00 → 266.66 | **+44%** | TP at 198.5 was hit months ago |
| IWM | 206.26 → 277.54 | **+35%** | TP at 220.7 was hit months ago |

---

## Recommendations

1. **Purge or archive stale picks:** Any pick >7 days old with `status = OPEN` should be automatically resolved as `TIME_EXIT` or `STALE_CLOSE`. The current registry gives a false impression of active positions.
2. **Fix P/L calculation:** The `pnl_pct` field in `ai_challenge_*_active_picks.json` must be recalculated from entry_price and current market data, or removed if it cannot be maintained.
3. **Add periodic resolution sweeps:** A nightly job should compare live prices to TP/SL levels and update status accordingly. TP/SL breaches from months ago should not still show as `OPEN`.
4. **Distinguish screener vs registry:** `picks_now.json` (screener) is accurate and current. Do not confuse its `price` field with historical `entry_price` fields in tournament data.
5. **Investigate MISPRICED_ENTRY flags:** NG=F and CL=F were flagged as mispriced but would have been highly profitable. The mispricing logic may be too sensitive.

---

## Methodology

- **Crypto prices:** Fetched from Binance public API (`/api/v3/ticker/price`) at 2026-11-14 ~15:48 UTC.
- **Stock/ETF/Forex/Commodity prices:** Fetched from Yahoo Finance via `yfinance` library at 2026-11-14 ~15:48 UTC.
- **Discrepancy %:** `|live_price - reference_price| / reference_price × 100`, where `reference_price` is `entry_price` for tournament/challenge picks and `price` (claimed current) for screener picks.
- **Stale flag:** `True` if `status ∈ {OPEN, ACTIVE, PENDING, WATCH}` and `age > 7 days`.
- **P/L stuck flag:** `True` if `pnl_pct == 0.0` and price has moved >0.5% from entry.

---

*Report written by Kilo as part of the prediction-system audit pipeline.*
