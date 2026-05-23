# Score-PnL Calibration Report
**Generated:** 2026-04-19 17:27

## 1. Data Architecture: Two Populations in closed_picks.json
| Population | Count | Score Fields | Outcome Type |
|------------|-------|--------------|--------------|
| **A (ML-scored)** | 11 | ml_score, confluence_score | WON/LOST/EXPIRED |
| **B (Non-ML)** | 4,650 | confidence | CLOSED |

### Score Field Coverage (closed_picks.json)
| Field | Non-Null | Coverage | Notes |
|-------|----------|----------|-------|
| confidence | 4,538 | 97.4% | Only Pop B (Pop A = NaN) |
| ml_score | 11 | 0.2% | Only Pop A |
| confluence_score | 3 | 0.1% | Always 1.0, no variance |
| elite_score | 500 | 10.7% |  |
| ml_composite_score | 500 | 10.7% |  |
| method_a_score | 500 | 10.7% |  |
| entry_timing_score | 4 | 0.1% | Essentially non-existent |

## 2. Population A: ml_score (n=11)
**Correlation with PnL:** `-0.5786`

| Decile | Score Range | n | WR | Avg PnL | Total PnL |
|--------|-------------|---|----|---------|-----------|

## 3. Population B: confidence (n=4,650)
**Correlation with PnL:** `+0.0432`
> :warning: `confidence` has essentially **zero** correlation with PnL across 4,650 trades.

| Decile | Score Range | n | WR | Avg PnL | Total PnL |
|--------|-------------|---|----|---------|-----------|
| D 1 | 0.451-0.570 | 453 | 33.1% | -0.217% | -98.37% |
| D 2 | 0.570-0.589 | 453 | 37.1% | -0.124% | -56.24% |
| D 3 | 0.589-0.604 | 452 | 38.1% | -0.088% | -40.00% |
| D 4 | 0.604-0.619 | 453 | 34.7% | -0.154% | -69.61% |
| D 5 | 0.619-0.635 | 453 | 34.0% | -0.193% | -87.35% |
| D 6 | 0.635-0.650 | 452 | 30.3% | -0.078% | -35.40% |
| D 7 | 0.650-0.670 | 453 | 27.6% | -0.118% | -53.38% |
| D 8 | 0.670-0.675 | 452 | 7.3% | -0.125% | -56.28% |
| D 9 | 0.675-0.690 | 453 | 13.9% | -0.090% | -40.67% |
| D10 | 0.690-0.880 | 453 | 39.5% | -0.021% | -9.59% |

**High-Confidence Losers:** Top 10% (≥0.690) = 514 trades, 335 losers (65.2%). Total PnL: -18.74%

| Symbol | Dir | Trades | Avg PnL | Total | Avg Conf |
|--------|-----|--------|---------|-------|----------|
| TAOUSDT      | BUY  | 33 | -0.82% | -27.20% | 0.713 |
| BTCUSDT      | BUY  | 41 | -0.43% | -17.66% | 0.726 |
| MATICUSDT    | BUY  | 101 | -0.15% | -15.15% | 0.690 |
| RENDERUSDT   | BUY  | 15 | -1.00% | -14.96% | 0.713 |
| KASUSDT      | BUY  | 18 | -0.79% | -14.21% | 0.709 |
| HYPEUSDT     | BUY  | 14 | -0.64% | -8.99% | 0.714 |
| DOTUSDT      | BUY  | 14 | -0.62% | -8.67% | 0.708 |
| ICPUSDT      | BUY  | 15 | -0.55% | -8.23% | 0.719 |

## 4. Dashboard recent_closed (n=3,500)
All score fields populated. 181 unique strategies.

- `score` vs PnL: **+0.0011** (n=3,500)
- `elite_score` vs PnL: **-0.1144** (n=3,500)
- `ml_composite_score` vs PnL: **-0.0020** (n=3,500)
- `method_a_score` vs PnL: **+0.0274** (n=3,500)
- `confidence` vs PnL: **-0.0481** (n=3,500)

### Worst Strategies (dashboard, min 20 trades)
| Strategy | n | WR | Avg PnL | Total PnL |
|----------|---|----|---------|-----------|
| st_fear_greed_contrarian            | 532 | 24.8% | -0.402% | -213.90% |
| copy_hl_lb_None                     | 278 | 32.0% | -2.901% | -806.39% |
| unknown                             | 59 | 30.5% | -0.584% | -34.45% |
| macd_rsi_confluence                 | 43 | 30.2% | -1.022% | -43.95% |
|                                     | 26 | 38.5% | -2.022% | -52.58% |

## 5. Near-Miss Analysis (SL hits within 1% of TP)
- Total SL hits: **86**
- Near-misses (within 1% of TP): **0** (0.0%)
- Median TP distance for SL hits: **6.25%**

## 6. Recommendations

| Priority | Action | Evidence |
|----------|--------|----------|
| P0 | Fix `confidence` scoring logic | r=+0.043 across 4,650 trades |
| P0 | Deprecate `confluence_score` | Always 1.0, zero variance |
| P0 | Block `volume_spike_breakout` from live | 11.6% WR, -80% total (Pop B) |
| P1 | Investigate D10 `ml_score` drop | D9 86.4% WR → D10 56.7% WR |
| P1 | Populate elite/ml_composite/method_a across ALL trades | Currently 1 trade only |
| P1 | Add TAOUSDT/BTCUSDT to loss watchlist | High-confidence repeated losers |
| P2 | Unify scoring pipeline | Two disjoint populations prevent comparison |
