# HyroTrader Dashboard Edge Failures – 2026‑04‑21

**Branch:** `fix/hedge-fund-performance-optimization-plan`  
**Author:** Roo (agent)  
**Date:** 2026‑04‑21  

## Objective

Examine `findtorontoevents.ca/audit/hyrotrader` for edge failures and propose fixes, as requested by the user alongside the hedge‑fund performance improvements.

## Current State

The HyroTrader dashboard is a dedicated challenge‑tracking UI that displays:

1. **Challenge parameters & account snapshot** – from `hyrotrader_picks.json`.
2. **QuanEngine Edge Tracker** – consensus voting from `hyro_quan_bridge.json`.
3. **Live playbook signals (1h)** – client‑side scanner (`hyro_live_signals.js`) that pulls Binance candles and evaluates strategy entry rules.
4. **Pick list** – curated trade plan (`hyrotrader_picks.json`).
5. **Signal strength & pick performance** – from `hyro_pick_performance.json`.

## Edge Failures Identified

### 1. **Stale Data**

| File | Generated At | Age (approx) | Impact |
|------|--------------|--------------|--------|
| `hyro_quan_bridge.json` | 2026‑04‑18T22:18:59Z | 3 days | Consensus votes outdated, may not reflect current market regime. |
| `hyro_pick_performance.json` | 2026‑04‑19T14:50:13Z | 2 days | Strategy strength scores based on older price action. |
| `hyrotrader_picks.json` | unknown | unknown | Pick list may not have been refreshed with latest backtest results. |

**Consequence:** Traders relying on stale signals may enter positions that are no longer aligned with the market.

### 2. **Low Consensus Activity**

Example from `hyro_quan_bridge.json`:
- **BTCUSDT**: 4 active votes (2 BUY, 2 SELL) out of 18 total; consensus not met.
- Many strategies **ABSTAIN** (confidence = 0.0), reducing overall signal strength.

**Root cause:** The QuanEngine’s consensus threshold (`0.45`) may be too high for current market conditions, or the underlying strategies are not firing due to lack of recent data.

### 3. **Missing Real‑Time Price Integration**

- The pick list (`hyrotrader_picks.json`) contains empty `entry_price`, `stop_loss`, `take_profit` fields until manually filled.
- No automatic bridging between the live signal scanner and the pick list.

**Consequence:** Manual entry introduces latency and human error; the dashboard does not provide a seamless “click‑to‑trade” workflow.

### 4. **Performance Validation Gaps**

- `hyro_pick_performance.json` shows **461 signals** with overall win‑rate **65.2%** (good).
- However, **116 signals expired** (no TP/SL hit within lookback), indicating possible overly tight TP/SL settings.
- Some strategies have **strength score 0** (grade F) due to insufficient data (1 trade) or total loss.

**Edge failure:** Strategies with low scores are still displayed in the live scanner, leading to potential low‑quality entries.

### 5. **Client‑Side Scanner Limitations**

- `hyro_live_signals.js` runs in the browser, dependent on Binance API availability and CORS.
- No fallback if Binance fails; the scanner may show “No setup” for all symbols.
- No integration with the audit dashboard’s quality gates (score thresholds, forward win‑rate gates).

## Proposed Fixes

### Immediate (1–2 days)

1. **Automate Data Refresh**
   - Modify the existing GitHub Actions workflow (`tools/hyro_quan_bridge.py`) to run **hourly** instead of on‑demand.
   - Add a cron job for `tools/hyro_pick_performance_validator.py` to regenerate performance data every 6 hours.
   - Update the dashboard’s UI to show “Last updated” timestamps prominently.

2. **Increase Consensus Sensitivity**
   - Lower the consensus threshold from `0.45` to `0.35` in `tools/hyro_quan_bridge.py` (temporary measure).
   - Adjust strategy confidence thresholds to reduce abstentions.

3. **Real‑Time Price Bridge**
   - Extend `hyro_live_signals.js` to automatically populate `entry_price` (last closed candle) and calculate TP/SL based on ATR when a signal is validated.
   - Add a “Fill Prices” button that copies the live signal’s suggested levels into the pick list JSON (with manual confirmation).

4. **Filter Low‑Strength Strategies**
   - In `hyro_live_signals.js`, hide strategies with strength score < 40 (grade D or F) by default.
   - Add a toggle to show/hide weak strategies.

5. **Add Audit‑Dashboard Quality Gates**
   - Import the same score‑threshold logic from `audit_trail/quality_gates.py` into the HyroTrader scanner.
   - Reject signals that would not pass the SMART_PICKS_MIN_SCORE for the relevant asset class.

### Medium‑Term (1 week)

1. **Server‑Side Signal Generation**
   - Move the live scanner to a server‑side script (`tools/hyro_live_signal_generator.py`) that runs every 15 minutes and writes results to `hyro_live_signals_latest.json`.
   - The dashboard then reads the pre‑computed file, eliminating browser‑side API calls and CORS issues.

2. **Integration with Audit Dashboard**
   - Merge HyroTrader picks into the main audit dashboard’s “HIGH CONVICTION” filter (already partially done via cross‑referencing).
   - Use the same forward‑win‑rate gates for HyroTrader strategies.

3. **Performance Decay Detection**
   - Add a rolling window (last 20 trades) win‑rate monitor; if WR < 40%, temporarily demote the strategy in the scanner.

4. **Alerting for Stale Data**
   - Dashboard warning when any source JSON is older than 24 hours.

## Implementation Steps

1. **Create a new branch** `fix/hyrotrader‑edge‑failures`.
2. **Update workflow schedules** in `.github/workflows/`.
3. **Modify `hyro_quan_bridge.py`** consensus threshold.
4. **Enhance `hyro_live_signals.js`** with strength filtering and price bridging.
5. **Add “Last updated” display** to `audit_dashboard/hyrotrader/index.html`.
6. **Test** with local server (`python tools/serve_local.py`).
7. **Create PR** linking to this analysis.

## Expected Outcomes

- **Fresher signals** (hourly updates) → higher edge.
- **Stronger consensus** (more active votes) → clearer directional bias.
- **Reduced low‑quality entries** (filter weak strategies) → improved win‑rate.
- **Seamless price integration** → faster, more accurate trade planning.

## Next Actions

The user can decide whether to implement these fixes immediately or prioritize other enhancements. The hedge‑fund performance PR (#290) already raises score thresholds, which will indirectly improve HyroTrader signals if the integration step is completed.

---
**Signed:** Roo (agent) – 2026‑04‑21