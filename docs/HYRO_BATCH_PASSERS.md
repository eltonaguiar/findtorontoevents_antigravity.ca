# Hyro backtest — batch passers (44 strategies tested)

**Source:** Batch 1 (`tools/hyro_backtest.py` + `tools/hyro_backtest_extended.py`) and Batch 2 (`tools/hyro_backtest_batch2.py`). **6m** = six calendar months of Binance **1h** candles unless noted.

**Summary:** **23** symbol×strategy combos **PASS** the Hyro-style sim among **44** strategies exercised (6m, **0.75%** risk/trade). Numbers are **research only** — not live fills or Hyro perps.

---

## All passing combos — 6 month (23)

Sorted by PnL% (your run).

| # | Symbol | Strategy | PnL% | PF | WR | Max DD | Trades | Risk | Source |
|---|--------|----------|------|-----|-----|--------|--------|------|--------|
| 1 | ETHUSDT | Volume Breakout | **+26.3** | 1.52 | 43.2 | $247 | 118 | 0.75% | B1-6m |
| 2 | ETHUSDT | Heikin-Ashi Trend | **+24.8** | 1.43 | 41.7 | $198 | 132 | 0.75% | B1-6m |
| 3 | BTCUSDT | CCI Divergence | **+22.5** | **2.15** | 51.9 | $97 | 54 | 0.75% | B2-6m |
| 4 | BTCUSDT | ATR Volatility Breakout | **+17.2** | 1.23 | 38.0 | **$46** | 163 | 0.75% | B2-6m |
| 5 | ETHUSDT | True Strength Index | **+15.4** | 1.64 | 39.6 | $240 | 53 | 0.75% | B2-6m |
| 6 | ETHUSDT | Three White Soldiers | **+13.5** | 1.21 | 37.5 | $206 | 136 | 0.75% | B2-6m |
| 7 | SOLUSDT | CCI Divergence | **+12.8** | 1.49 | 42.6 | $168 | 61 | 0.75% | B2-6m |
| 8 | ETHUSDT | Vol-Scaled Momentum | **+12.4** | 1.25 | 33.3 | $308 | 99 | 0.75% | B2-6m |
| 9 | SOLUSDT | Multi-EMA Stack | **+12.0** | **1.89** | 48.6 | $112 | 35 | 0.75% | B2-6m |
| 10 | BTCUSDT | BB Squeeze Breakout | **+12.0** | 1.29 | 38.7 | $172 | 93 | 0.75% | B2-6m |
| 11 | BTCUSDT | Donchian Breakout | **+12.0** | 1.16 | 36.6 | $327 | 161 | 0.75% | B1-6m |
| 12 | BTCUSDT | TTM Squeeze | **+11.3** | 1.41 | 41.3 | **$89** | 63 | 0.75% | B2-6m |
| 13 | SOLUSDT | VWAP SD Reversion | **+11.2** | 1.36 | 47.4 | $218 | 78 | 0.75% | B2-6m |
| 14 | SOLUSDT | Three White Soldiers | **+10.9** | 1.21 | 37.5 | $299 | 112 | 0.75% | B2-6m |
| 15 | ETHUSDT | TTM Squeeze | **+10.5** | 1.44 | 41.8 | $232 | 55 | 0.75% | B2-6m |
| 16 | ETHUSDT | OBV Divergence | **+7.9** | 1.13 | 31.6 | $341 | 117 | 0.75% | B2-6m |
| 17 | SOLUSDT | Fisher Transform | **+7.9** | 1.17 | 37.4 | $178 | 99 | 0.75% | B2-6m |
| 18 | BTCUSDT | Multi-EMA Stack | **+7.1** | 1.35 | 41.3 | $203 | 46 | 0.75% | B2-6m |
| 19 | ETHUSDT | Multi-EMA Stack | **+6.0** | 1.31 | 38.6 | $282 | 44 | 0.75% | B2-6m |
| 20 | BTCUSDT | True Strength Index | **+5.6** | 1.17 | 31.3 | $254 | 67 | 0.75% | B2-6m |
| 21 | ETHUSDT | Justin Bravo EMA-9 | **+4.5** | 1.06 | 34.7 | $379 | 144 | 0.75% | B2-6m |
| 22 | BTCUSDT | VWAP Bounce | **+3.0** | 1.05 | 34.5 | $394 | 119 | 0.75% | B2-6m |
| 23 | BTCUSDT | CMF Cross | **+2.6** | 1.05 | 35.0 | $419 | 103 | 0.75% | B2-6m |

---

## 12-month passes — Batch 1 extended (3)

| # | Symbol | Strategy | PnL% | PF | WR | Max DD | Trades |
|---|--------|----------|------|-----|-----|--------|--------|
| 24 | AVAXUSDT | Volume Breakout | **+28.3** | 1.29 | 39.2 | **$16** | 217 |
| 25 | AVAXUSDT | Donchian Breakout | **+31.2** | 1.25 | 38.5 | $85 | 270 |
| 26 | BNBUSDT | Connors RSI(2) | **+11.1** | 1.27 | **66.7** | $174 | 162 |

Run extended 12m from repo root, e.g.:

`python tools/hyro_backtest_extended.py --strategy volume --symbol AVAXUSDT --months 12 --risk 0.75`

---

## Top 5 by return / max DD (6m highlights)

1. AVAX × Volume Breakout (12m): +28.3% with **$16** max DD  
2. BTC × ATR Vol Breakout: +17.2% with **$46** DD  
3. BTC × TTM Squeeze: +11.3% with **$89** DD  
4. BTC × CCI Divergence: +22.5% with **$97** DD  
5. SOL × Multi-EMA Stack: +12.0% with **$112** DD  

---

## Map: display name → Python key

| Strategy (table) | Module | CLI `--strategy` key |
|------------------|--------|----------------------|
| Volume Breakout | `hyro_backtest.py` | `volume` (base script) or extended registry |
| Heikin-Ashi Trend | `hyro_backtest_extended.py` | `heikin_ashi` |
| Donchian Breakout | `hyro_backtest_extended.py` | `donchian` |
| Connors RSI(2) | `hyro_backtest_extended.py` | `connors_rsi2` |
| CCI Divergence | `hyro_backtest_batch2.py` | `cci_divergence` |
| ATR Volatility Breakout | `hyro_backtest_batch2.py` | `atr_vol_breakout` |
| True Strength Index | `hyro_backtest_batch2.py` | `tsi` |
| Three White Soldiers | `hyro_backtest_batch2.py` | `three_soldiers` |
| Vol-Scaled Momentum | `hyro_backtest_batch2.py` | `vol_scaled_mom` |
| Multi-EMA Stack | `hyro_backtest_batch2.py` | `multi_ema_stack` |
| BB Squeeze Breakout | `hyro_backtest_batch2.py` | `bb_squeeze` |
| TTM Squeeze | `hyro_backtest_batch2.py` | `ttm_squeeze` |
| VWAP SD Reversion | `hyro_backtest_batch2.py` | `vwap_sd_reversion` |
| OBV Divergence | `hyro_backtest_batch2.py` | `obv_divergence` |
| Fisher Transform | `hyro_backtest_batch2.py` | `fisher` |
| Justin Bravo EMA-9 | `hyro_backtest_batch2.py` | `justin_ema9` |
| VWAP Bounce | `hyro_backtest_batch2.py` | `vwap_bounce` |
| CMF Cross | `hyro_backtest_batch2.py` | `cmf_cross` |

Extended catalog keys: `EXTENDED_STRATEGIES` in `tools/hyro_backtest_extended.py`. Batch 2 keys: `BATCH2_STRATEGIES` in `tools/hyro_backtest_batch2.py`.

---

## Full grid (extended + Batch 2)

One command runs **all** extended strategies and **all** Batch 2 strategies on the same symbol list (writes JSON under `audit_dashboard/data/`):

```powershell
python tools/hyro_backtest_sweep.py --symbols BTCUSDT ETHUSDT SOLUSDT AVAXUSDT BNBUSDT XRPUSDT ADAUSDT --months 6 --risk 0.75
```

Outputs: `hyro_backtest_extended_results.json`, `hyro_batch2_results.json`.

---

## 12-month on Batch 2 winners

Worth running: longer windows stress regime changes and can flip PASS/FAIL vs 6m. Batch 2 already supports `--months`:

```powershell
python tools/hyro_backtest_batch2.py --strategy cci_divergence --symbol BTCUSDT --months 12 --risk 0.75
python tools/hyro_backtest_batch2.py --strategy ttm_squeeze --symbol BTCUSDT --months 12 --risk 0.75
```

To sweep all Batch 2 keys on selected symbols:

```powershell
python tools/hyro_backtest_batch2.py --symbols BTCUSDT ETHUSDT SOLUSDT --months 12 --risk 0.75 --save --output hyro_batch2_12m_results.json
```

---

## Live dashboard

Only strategies with matching evaluators in `audit_dashboard/hyrotrader/hyro_live_signals.js` and rows in `audit_dashboard/data/hyro_live_strategies.json` appear on the Hyro live page. Batch 2 passers are backtest-only until wired there.

See also: `docs/HYRO_WINNING_STRATEGIES.md`, `docs/HYRO_AGENT_BACKTEST_GUIDE.md`.
