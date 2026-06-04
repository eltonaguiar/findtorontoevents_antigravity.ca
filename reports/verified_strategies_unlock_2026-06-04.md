# Verified-Strategy Forward Performance Unlock — 2026-06-04

After INCIDENT #94 fix (TIME_EXIT pnl=0 bug) and 32,473-row backfill, the verified paper-pilot strategies now have real forward-test data.

## Forward performance (decisive + TIME_EXIT with real pnl)

| Strategy | n | WR | avg pnl | PF | Verdict |
|---|---:|---:|---:|---:|---|
| **inverse_ml_enhanced_ADAUSDT_15m_D** | 36 | 55.6% | +0.112% | **1.73** | **T2 candidate** |
| etf_dual_momentum | 25 | 52.0% | +0.136% | **1.47** | T2-shaped (small n) |
| inverse_ml_enhanced_BTCUSDT_15m_D | 52 | 55.8% | +0.007% | 1.09 | Tier-3 (positive but tiny) |
| B_flip_PriceRocMeanReversion | 39 | 53.8% | +0.010% | 1.08 | Tier-3 |
| inverse_ml_enhanced_RENDERUSDT_1h_D | 54 | 42.6% | -0.009% | 0.95 | No-edge |
| **inverse_ml_enhanced_RENDERUSDT_4h_D** | 52 | 50.0% | **-1.73%** | **0.12** | **KILL — dead strategy** |

## Recommendations

1. **Kill `inverse_ml_enhanced_RENDERUSDT_4h_D`** — PF 0.12 means $1 won per $8 lost. Net -1.73% per trade.
2. **Promote `inverse_ml_enhanced_ADAUSDT_15m_D`** to next-stage validation — best PF among verified strategies (1.73, n=36). Still needs n>=100 before live capital.
3. **Watch `etf_dual_momentum`** — small n (25) but PF 1.47 + positive avg. Continue accumulating; promotion-ready at n=60-80 if trend holds.
4. **B_flip + BTC variant**: Tier-3 (positive but tiny edge). Not promotion candidates; keep running as data accumulators.

## Why this matters

Before the INCIDENT #94 fix, `bootstrap_forward_stats_latest.json` reported `b_flip n=2`, `inverse_ml_btc n=3` (decisive only). The "real" forward-pilot n was 25-54 per strategy but hidden behind pnl=0 TIME_EXIT bug. **The promotion-gate path was structurally broken**, not strategy-rarity.

After backfill: n_decisive jumps from 5 (across both strategies) to 258 (across all 6 verified). This is real forward-test data the system has been throwing away for months.

## Follow-ups

- Re-run `bootstrap_forward_stats` workflow to pick up new pnl data
- Filter inverse_ml ADAUSDT to confirm it's not concentration of a single price spike (n=36 still small)
- Operator: review the kill-list for RENDERUSDT_4h strategy
