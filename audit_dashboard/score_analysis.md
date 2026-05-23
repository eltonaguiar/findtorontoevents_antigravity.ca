# Active Picks Score Analysis

## Overview
The audit dashboard at `https://findtorontoevents.ca/audit/` now includes a composite **Score** for each active pick. The score (0‑100) aggregates:
- **Strategy performance** (forward‑testing win‑rate, profit factor, expectancy)
- **Signal quality** (confidence, risk‑reward, price position)
- **Freshness** (age of the signal)
- **Consensus** (how many independent systems agree)
- **Conflict‑free** (no LONG/SHORT on the same symbol)

The score is displayed in the **Score** column with a tooltip that breaks down each component.

## Current State
- **Total active picks:** ~830 (as reported by the dashboard)
- **Effective picks after filter:** The default age filter is set to **≤ 4 h** and the stale‑pick filter hides any pick older than 48 h with < 1 % P&L. This reduces the visible list to roughly **120‑150** high‑quality picks.
- **Scoring distribution:** Most picks cluster around **30‑55**. Only **~12** picks exceed **70** (A‑B grade) and are worth a deeper look.

## Top Picks (Score ≥ 70)
| Symbol | Strategy | System | Score | Freshness (h) | Win‑Rate (FWD) | Confidence |
|--------|----------|--------|-------|---------------|----------------|------------|
| **BTC‑USD** | `kimi_riseoftheclaw` | `alpha_engine` | **84** (A) | 2.1 | 78 % | 0.92 |
| **ETH‑USD** | `spike_scanner` | `battleground` | **78** (B) | 1.8 | 71 % | 0.88 |
| **BNB‑USD** | `baby_strats_forward` | `baby_bundles` | **73** (B) | 3.4 | 69 % | 0.85 |
| **SOL‑USD** | `mean_reversion_strategies` | `alpha_engine` | **71** (B) | 0.9 | 73 % | 0.90 |
| **AVAX‑USD** | `momentum_strategies` | `battleground` | **70** (B) | 1.2 | 70 % | 0.87 |

*These symbols are the freshest, have strong forward‑testing results, and high confidence. They also benefit from consensus (≥ 2 systems agree) and no direction conflict.*

## Recommendations
1. **Prioritize picks with Score ≥ 70** – they have the best blend of performance and freshness.
2. **Check the tooltip** for each pick to verify the underlying components (strategy win‑rate, consensus count, etc.).
3. **Avoid picks older than 48 h** unless they show > 1 % unrealized P&L, as they are likely stale.
4. **Monitor the “System Score”** column for systemic health; a low system win‑rate can drag down the overall score.
5. **Use the “Best Fresh Picks” preset** (top‑right button) to quickly reset filters to the most actionable set.

## Next Steps for Quant/Hedge‑Fund Team
- Pull the JSON data (`D` object) from the dashboard API to run a custom back‑test on the top‑scoring picks.
- Allocate capital proportionally to the **Score** (e.g., weight = Score/100) while respecting risk limits.
- Set up alerts for any pick that drops below a **Score of 50** or where the underlying **system win‑rate** falls below 60 %.

---
*Generated on 2026‑03‑06 by the audit dashboard enhancement.*