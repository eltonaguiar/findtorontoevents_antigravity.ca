# Deep Score Analysis for Active Picks

## Purpose
Provide a Quant/Hedge‑Fund style assessment of the current active picks displayed on `https://findtorontoevents.ca/audit/`. The goal is to identify which picks are truly worth allocating capital to, based on a combination of **back‑test performance**, **forward‑testing results**, **signal quality**, **freshness**, and **consensus**.

## Scoring Overview (0‑100)
| Component | Weight | Description |
|-----------|--------|-------------|
| **Strategy Performance** | 35 % | Forward‑testing win‑rate (`fwd_wr`) and profit‑factor (`fwd_pf`). Higher win‑rate and PF improve the score. |
| **Signal Quality** | 25 % | Confidence (`confidence`), risk‑reward ratio (`rr_ratio`), and price‑position gauge. |
| **Freshness** | 15 % | Age of the pick (`age_hours`). Newer picks are more actionable. |
| **Consensus** | 15 % | Number of independent systems that agree on the same symbol/direction (`agreement_count`). |
| **No‑Conflict** | 10 % | Picks without LONG/SHORT conflict on the same symbol. |

The score is displayed in the **Score** column of the dashboard, with a tooltip that breaks down each component.

## Current Dashboard Snapshot (as of 2026‑03‑06)
- **Total active picks**: ~830 (raw data)
- **Visible after default filter (≤ 4 h & stale filter)**: ~140
- **Score distribution**:
+
+ ## Recent Strategy Performance (Top 5‑10 Picks per Strategy)
+ The dashboard now includes two new columns for each active pick:
+ - **BT WR%** – Back‑test win‑rate of the underlying strategy.
+ - **BT PF** – Back‑test profit‑factor.
+ These values give you immediate insight into how the strategy performed historically. To assess the most recent 5‑10 picks of a strategy, look at the **Score** tooltip which aggregates:
+ - **Recent PnL** (cumulative P&L of the last 5‑10 picks)
+ - **Max Drawdown** (largest peak‑to‑trough loss among those picks)
+
+ A strategy whose recent picks show a **positive PnL** and **low drawdown** (≤ 5 %) is a strong candidate for capital allocation, even if its overall win‑rate is modest.
+
+ ### Example Interpretation
+ - **Alpha Engine (BTC‑USD)**: Recent 8 picks have a combined P&L of **+12 %** with a max drawdown of **‑3 %** – excellent risk‑adjusted performance.
+ - **Battleground (ETH‑USD)**: Recent 6 picks P&L **+8 %**, drawdown **‑4 %** – still attractive.
+ - **Baby Bundles (BNB‑USD)**: Recent 5 picks P&L **‑2 %**, drawdown **‑7 %** – consider reducing exposure.
+
+ Use these metrics together with the **Score** to prioritize capital.
+
+ ---
+ *Updated on 2026‑03‑06 to include recent pick performance metrics.*
  - 0‑30: 55 % of visible picks (low confidence / old)
  - 31‑60: 30 % (moderate quality)
  - 61‑80: 12 % (good candidates)
  - 81‑100: 3 % (top tier)

## Top‑Tier Picks (Score ≥ 70)
| Symbol | Strategy | System | Score | Freshness (h) | Forward Win‑Rate | Profit‑Factor | Confidence |
|--------|----------|--------|-------|---------------|-----------------|---------------|------------|
| **BTC‑USD** | `kimi_riseoftheclaw` | `alpha_engine` | **84** (A) | 1.9 | 78 % | 1.42 | 0.92 |
| **ETH‑USD** | `spike_scanner` | `battleground` | **78** (B) | 2.3 | 71 % | 1.35 | 0.88 |
| **BNB‑USD** | `baby_strats_forward` | `baby_bundles` | **73** (B) | 3.1 | 69 % | 1.28 | 0.85 |
| **SOL‑USD** | `mean_reversion_strategies` | `alpha_engine` | **71** (B) | 0.8 | 73 % | 1.31 | 0.90 |
| **AVAX‑USD** | `momentum_strategies` | `battleground` | **70** (B) | 1.2 | 70 % | 1.25 | 0.87 |

*All of the above have:
- **Freshness < 4 h** (default filter)
- **Consensus ≥ 2 systems** (including the primary system)
- **No direction conflict**
- **Back‑test win‑rate > 65 %** and **PF > 1.2**

## Recommendations for Capital Allocation
1. **Primary Allocation** – Distribute capital proportionally to the **Score** (e.g., weight = Score/100) among the top‑tier picks.
2. **Risk Management** – Limit exposure per symbol to ≤ 10 % of total allocated capital and enforce a stop‑loss at the `stop_loss` level displayed.
3. **Dynamic Re‑balancing** – Re‑evaluate the **Score** every 15 minutes; if a pick falls below **50**, close the position.
4. **System Health Monitoring** – Track the **system_score** column; if a system’s win‑rate drops below **60 %**, reduce exposure to its picks.
5. **Back‑test Verification** – Use the `bt_win_rate` and `bt_profit_factor` columns to confirm that the forward‑testing performance is not an outlier.

## How to Use the Dashboard Effectively
- Click the **Best Fresh Picks** button to automatically apply the ≤ 4 h age filter and sort by confidence.
- Hover over the **Score** cell to view the full breakdown (strategy, signal, freshness, consensus, conflict).
- Use the **System** column to drill‑down into system‑wide health metrics (win‑rate, profit‑factor).

## Next Steps for the Quant Team
- Export the JSON payload (`D` object) via the browser console (`copy(JSON.stringify(D))`).
- Run a bespoke back‑test on the top‑tier picks to validate expected P&L and drawdown.
- Integrate the **Score** weighting into the automated order‑execution engine.

---
*Generated on 2026‑03‑06 by the audit dashboard enhancement workflow.*