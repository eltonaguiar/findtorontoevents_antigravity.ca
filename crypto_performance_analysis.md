# Crypto Performance Analysis Report

**Date:** 2026-03-10

---

## 1. Executive Summary
- **Overall Rating:** **B+ (Good with caveats)** – Crypto prediction performance is solid, but still has room for improvement.
- **Top‑performing Engine:** **Battleground** – 64.1% forward win‑rate (WR) on 334 closed trades, +1357% PnL.
- **Ensemble Engine:** 68% avg WR, Sharpe proxy 1.8 – strong but not yet world‑class.
- **Alpha Engine:** 35.9% WR, positive PnL (+12.2% per win) – respectable for a newer engine.
- **Key Issues:** Direction conflicts on the same asset, tight R:R on proven‑winner longs, missing indicator context in UI.

---

## 2. Latest Forward‑Facing Picks (as of 2026‑03‑09)
| Symbol | Direction | Confidence | Top Sources | Bias |
|--------|-----------|------------|-------------|------|
| **BTCUSDT** | SHORT | 0.85 | GP (35%), alpha_engine (25%) | -1.2 |
| **ETHUSDT** | SHORT | 0.72 | quan_engine, ml_bg_system_b | -0.9 |
| **SOLUSDT** | SHORT | 0.88 | battleground, rapid_fire | -1.1 |
| **AVAXUSDT** | LONG | 0.65 | mercury2, predictions | 0.7 |
| **DOGEUSDT** | LONG | 0.92 | alpha_engine_fast, GP | 1.4 |

*These picks are derived from `ae_active_picks.json` proxy used by the ensemble engine.*

---

## 3. Back‑testing Performance (Source Historical Proxy)
- **Average Weighted WR:** **68%** (weighted recent closed picks)
- **Sharpe Proxy:** **1.8** (mean/std PnL)
- **Trade Count:** 50+ per source average
- **Edge:** Diversity bonus reduces single‑source risk

---

## 4. Engine‑by‑Engine Breakdown
### 4.1 Battleground (Superpowers Arena)
- **WR:** 64.1% (334 closed trades)
- **PnL:** +1357% (cumulative)
- **Status:** **BEST** – proven survivors avg 63.7% WR.
- **Strengths:** High win‑rate, strong Sharpe, diverse strategy set.
- **Weaknesses:** Some conflicting signals (e.g., BTCUSDT LONG vs SHORT) – see Issue 1 below.

### 4.2 Alpha Engine (`/alpha/`)
- **WR:** 35.9% (156 closed trades)
- **PnL:** Positive ($ per win ≈ 12.2%)
- **Status:** **OK** – positive PnL despite modest WR.
- **Weaknesses:** Low WR, many paused strategies (7 of 20).

### 4.3 Baby Strats Forward (Retired)
- **WR:** 41.8% (1975 closed trades)
- **PnL:** -5433% (massive loss)
- **Status:** **DESTROYED** – removed from production.

---

## 5. MySQL Audit Database Summary
The platform stores forward‑test outcomes in the MySQL database `ejaguiar1_stocks`.

**Key Tables**
- `at_raw_picks` – every signal from every system.
- `at_signal_outcomes` – forward trade results (wins/losses, PnL, timestamps).
- `bt_backtest_trades` – historical backtest trades imported from SQLite.
- `strategy_registry` – master strategy catalog.
- `at_strategy_symbol_performance` – per‑strategy × per‑symbol statistics.
- `at_discord_sent` – Discord push history.

**Recent Query Insights (as of 2026‑03‑09)**
```sql
SELECT strategy_name,
       COUNT(*) AS trades,
       AVG(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) AS win_rate,
       SUM(pnl_pct) AS total_pnl
FROM at_signal_outcomes
WHERE entry_time >= '2026-02-01'
GROUP BY strategy_name
ORDER BY win_rate DESC
LIMIT 10;
```
Result highlights the **Battleground** family leading with >60% WR and strong PnL, while **Alpha Engine** shows a modest but positive edge.

---

## 6. Validation Against Active Picks Dashboard
The live dashboard (`https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/audit_dashboard/portfolio_history.html`) reports **906 active picks** with two advanced filters applied. A snapshot of the top rows includes:
- **BTCUSDT SHORT** (Battleground, 62.4% WR)
- **ETHUSDT LONG** (Battleground, 62.4% WR)
- **XRPUSDT LONG** (Battleground, 62.4% WR)
- **AUDJPY=X SHORT** (Alpha Engine Fast, 39.1% WR)
- **BTC‑USD SHORT** (Alpha Engine Fast, 39.1% WR)
- …

Our internal JSON source (`audit_trail/data/prop_firm_picks.json`) contains **12 total picks** (both active and closed). Notably:
- **BTCUSDT LONG** (prop_firm) – direction **conflicts** with the dashboard’s SHORT.
- **ETHUSDT SHORT** (prop_firm) – again opposite to the dashboard’s LONG.
- Other symbols (SOLUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, AVAXUSDT, etc.) appear with directions that **match** the dashboard.

**Conclusion of Validation:**
- The majority of symbols and directions are consistent across sources, confirming the overall health of the pick generation pipeline.
- The **direction conflicts** for BTCUSDT and ETHUSDT highlight a data‑integrity issue that must be resolved (e.g., by de‑duplicating or enforcing net‑exposure logic).

---

## 7. Identified Issues & Recommendations
| Issue | Description | Impact | Recommendation |
|-------|-------------|--------|----------------|
| **1. Conflicting Signals** | Same asset (e.g., BTCUSDT) has both LONG and SHORT positions simultaneously from different strategies. | Net‑neutral exposure, wasted commission, PnL noise. | Implement portfolio‑level net‑exposure logic; gate conflicting directions in `cross_aggregation/freshpicks_gate.py`.
| **2. Weak R:R on Proven Winners** | Long picks often have tight R:R (e.g., 1.33:1). | Small adverse moves wipe edge. | Introduce ATR‑scaled TP/SL (2.5 × ATR TP, 1.5 × ATR SL) – see Section 8.2.
| **3. Missing Indicator Context in UI** | `/audit/` table lacks RSI, HMA slope, volume confirmation, last‑10‑trade WR, current PnL. | Users cannot assess signal quality. | Add columns to `at_raw_picks` (see Section 8.1) and update UI accordingly.
| **4. Over‑leveraged Position Sizing** | 65 open positions × $500 each = $32.5K required, but only $10K capital exists. | Unrealistic simulation. | Reduce position count to 20‑25 or increase capital simulation; enforce max‑exposure rule.
| **5. Loading… States** | `/findstocks2_global/miracle.html` never resolves. | Potential broken data feeds. | Investigate API keys and network connectivity; add fallback data source.

---

## 8. Actionable Enhancements
### 8.1 Dashboard Column Additions
Add the following columns to `at_raw_picks` MySQL table:
```sql
ALTER TABLE at_raw_picks
  ADD COLUMN rsi_1h DECIMAL(5,2),
  ADD COLUMN hma_slope TINYINT,          -- +1, 0, -1
  ADD COLUMN volume_ratio DECIMAL(5,2),
  ADD COLUMN pnl_pct_current DECIMAL(8,4),
  ADD COLUMN hours_open INT,
  ADD COLUMN strategy_last10_wr DECIMAL(5,2);
```
Update the audit UI to display these fields.

### 8.2 ATR‑Scaled TP/SL Filters
Replace fixed % TP/SL with ATR‑adjusted values (example for long):
```python
atr_val = atr(high, low, close, 14).iloc[-1]
if signal == 'LONG':
    take_profit = entry + 2.5 * atr_val
    stop_loss   = entry - 1.5 * atr_val   # R:R ~1.67:1
elif signal == 'SHORT':
    take_profit = entry - 2.5 * atr_val
    stop_loss   = entry + 1.5 * atr_val
```
This aligns with the suggestions in `AUDIT_VARIATIONS_2026‑03‑08.md`.

### 8.3 HMA Trend Filter
Implement Hull Moving Average slope filter to ensure trend alignment:
```python
def hma(series, period):
    wma1 = series.ewm(span=period//2, adjust=False).mean() * 2
    wma2 = series.ewm(span=period, adjust=False).mean()
    raw = wma1 - wma2
    sqrt_n = int(period**0.5)
    return raw.ewm(span=sqrt_n, adjust=False).mean()

def hma_slope(series, period=21):
    h = hma(series, period)
    return np.sign(h.diff())
```
Only allow LONG when `hma_slope > 0`, SHORT when `< 0`.

### 8.4 Conflict Detection Banner
Add a UI banner highlighting assets with both LONG and SHORT exposure:
```
⚠️ BTCUSDT: [LONG × 3] vs [SHORT × 2] — NET NEUTRAL — 5 systems conflicting
```

---

## 9. Performance Assessment
- **Battleground** is **world‑class** for crypto forward‑testing (WR > 60% and high Sharpe). It consistently outperforms the Alpha Engine.
- **Ensemble** (68% WR, Sharpe 1.8) is **exceptional** but still short of the 70%+ WR threshold that would be considered elite across all asset classes.
- **Alpha Engine** shows **promising** PnL but needs higher win‑rate and tighter risk controls.
- **Overall**, the crypto prediction platform is **good with caveats** – the win‑rate is strong, but R:R, conflict handling, and UI transparency need work.

---

## 10. Recommendations & Next Steps
1. **Deploy the ATR‑scaled TP/SL and HMA trend filter** across all live strategies (high priority). 
2. **Update the audit dashboard** to include the new indicator columns and conflict banner.
3. **Reduce portfolio exposure** to realistic capital levels (≤ 25 active positions).
4. **Continue DNA‑driven mutation** – run additional backtests on the new variations (e.g., Keltner+HMA Squeeze) and promote any with WR ≥ 55% and ≥ 15 trades.
5. **Monitor forward‑test results** for at least 50 resolved picks before declaring any new strategy production‑ready.
6. **Schedule a research sprint** to explore multi‑timeframe RSI alignment and volume expansion filters (see Section 6.1 of `AUDIT_VARIATIONS_2026‑03‑08.md`).

---

## 11. Conclusion
The crypto prediction system is **performing at an above‑average level** with a clear path to become world‑class. Immediate focus should be on **risk‑adjusted exits, conflict resolution, and richer UI data**. Continued DNA evolution and disciplined forward‑testing will further solidify the edge.
