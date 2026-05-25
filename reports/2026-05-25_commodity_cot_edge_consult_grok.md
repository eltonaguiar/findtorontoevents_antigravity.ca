# Commodity COT Edge Triangulation — xAI Grok CLI reply

- Engine: xAI Grok CLI
- Model: grok-default
- Date: 2026-05-25
- Prompt: /tmp/commodity_edge_prompt.txt
- Candidate edge: top_edges_per_class.json::by_class.COMMODITY (multi_asset_copytrader + cot, n=137, PF 3.274)
- Prior context: H-001 REJECTED 2026-05-20 (M-095 look-ahead leakage, same source+family)

---

**1. Verdict: DATA_QUALITY_LEAKAGE. 87**

Exact same source+family as H-001 (rejected 2026-05-20 for COT pub-lag leakage). 90-day window straddles the fix; pre-fix 78% WR / post-fix 30% 0.51 PF. 71/200 cells passing + near-dupe with identical stats + 85% cotton concentration in prior audit = systemic contamination, not edge. train_n=36 is meaningless.

**2. Probability residual leakage: 75-85%.**

Pre-fix regime likely supplies most of the 96 wins; post-fix edge was already negative. Aggregate 0.70 WR and 3.27 PF are weighted averages of two regimes.

**Single sanity check (pandas):**
```python
cell_trades.assign(
    pre_fix = trades.signal_gen_ts < '2026-05-20',
    lag_days = (trades.entry_ts - trades.cot_asof).dt.days
).groupby(['pre_fix', lambda x: x.lag_days < 3])[['win','pnl']].agg(['size','mean','sum'])
```
If pre-fix or lag<3 buckets drive >60% of wins, leakage confirmed.

**3. 71/200 cells passing Bonferroni (α=7.43e-5) means the independence assumption is false.**

200 × 7.43e-5 ≈ 0.015 expected false positives. 71× excess occurs only when cells share the identical leakage vector (same scraper, same COT feed, same cotton bias, overlapping feature bins). Effective number of independent tests is probably <10, not 200. Most plausible: one data-processing artifact (pub-lag look-ahead) contaminates the entire multi_asset_copytrader + cot family.

**4. Realistic slippage: 150-300 bps PF degradation.**

External scraper + copy-trader introduces hours-to-days latency on weekly COT. Commodity futures (esp. CT=F) add 10-30 bps spread + slippage outside liquid hours. The post-3d-guard version already printed 0.51 PF; live execution of the reported 3.27 would land at 1.1-1.6 before costs, frequently <1.0.

**5. Size up with real money: NO.**

This is recycled leakage from a hypothesis rejected three days after registration on the identical source. No capital until (a) leakage vector is isolated and removed, (b) strict 3-day lag is enforced at signal *receipt* time, and (c) fresh post-fix trades are tested live on paper for 60+ days with timestamp audit.

**6. Sharpest disambiguating experiment (fast/cheap):**

One SQL: for every trade in the exact cell, pull `signal_gen_ts`, `cot_asof`, `underlying`, `entry_ts`. Histogram lag_days and pre/post 2026-05-20 flag. Compute PF/winrate in the four buckets. If pre-fix or lag<3 buckets contain >65% of the 96 wins and post-fix/lagged PF <1.3, reject immediately. 45 minutes of analyst + DBA time.
