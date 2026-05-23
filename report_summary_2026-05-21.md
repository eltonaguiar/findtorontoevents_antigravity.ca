# Pick Performance Report — May 16–21, 2026
Generated: `audit_performance_report.html` (interactive, 274KB)
Source: `audit_trail/data/universal_resolved_picks.json` (5,000 total resolved; 1,117 in last 5 days)

## Key Findings (Last 5 Days)

| Metric | Value |
|--------|-------|
| Total Resolved Trades | 1,117 |
| Overall Win Rate | 46.5% |
| Total PnL | ~+49% (capped) |
| Avg PnL/Trade | +0.48% |
| TP Hits / SL Hits / Time Exit | 456 / 556 / 105 |
| Profit Factor | ~0.93 |
| Trades/Day | ~223 |

## Top Performing Symbols
| Symbol | Trades | Win Rate | Total PnL | Top Source |
|--------|--------|----------|-----------|------------|
| BTCUSDT | 81 | 71.6% | +143.8% | aggregated_picks |
| TRX-USD | 30 | 100% | +95.1% | kimi_signal_tracking |
| ENJ-USD | 20 | 100% | +70.0% | kimi_signal_tracking |
| WLDUSDT | 20 | 90.0% | +52.0% | ml_crypto_pred |
| JTOUSDT | 23 | 87.0% | +58.0% | ml_crypto_pred |

## Underperformers
| Symbol | Trades | Win Rate | Total PnL | Issue |
|--------|--------|----------|-----------|-------|
| MANA-USD | 23 | 21.7% | -20.1% | 10 time exits |
| SAND-USD | 17 | 11.8% | -23.0% | All LONG losses |
| UNIUSDT | 21 | 14.3% | -18.3% | SL-heavy |
| DOGEUSDT | 22 | 22.7% | -8.0% | Short side failing |
| SOLUSDT | 38 | 21.1% | -26.4% | 8 time exits |

## Source System Ranking
| Source | Trades | WR | PnL |
|--------|--------|----|----|
| kimi_signal_tracking | 168 | 60.7% | +257.3% |
| aggregated_picks | 58 | 74.1% | +111.0% |
| ml_crypto_pred | 118 | 47.5% | +46.6% |
| ml_crypto_pred_v12 | 88 | 60.2% | +97.0% |
| dna_winner_picks | 96 | 40.6% | +21.7% |
| quan_engine | 123 | 33.3% | +11.3% |
| alpha_engine | 82 | 39.0% | +7.6% |
| claude_gainer_st | 30 | 10.0% | -30.2% |
| copy_trader_highscore | 40 | 20.0% | -41.7% |
| dna_rapid_fire_mutations | 21 | 0.0% | -27.5% |

## Asset Class Health
- CRYPTO: Sub-T2 (avg score 55.1, fwd WR 33.2%, needs score ≥65 & WR ≥62%)
- EQUITY: T2 candidate (WR 69.2% but avg score 13.5, needs score ≥40)
- ETF: Weak (PF 1.33, WR 57.4%, needs PF ≥1.5)
- FOREX: Dead — BLOCKED, 0 active picks
- COMMODITY: Weak — post-dedup artifact
- FUTURES: Dead — WR 5.9%, BLOCKED
- BOND: No Data — only 11 trades, PF 0.66

## Direction Edge
- LONG WR: ~51% overall (slight edge)
- SHORT WR: ~42% overall
- Edge Delta: ~+9pp favoring LONG
- LONG volume dominates (~75% of trades)