# Commodity COT Edge Triangulation — OpenAI Codex (codex exec) reply

- Engine: OpenAI Codex (codex exec)
- Model: codex-default
- Date: 2026-05-25
- Prompt: /tmp/commodity_edge_prompt.txt
- Candidate edge: top_edges_per_class.json::by_class.COMMODITY (multi_asset_copytrader + cot, n=137, PF 3.274)
- Prior context: H-001 REJECTED 2026-05-20 (M-095 look-ahead leakage, same source+family)

---

1. **Verdict:** `DATA_QUALITY_LEAKAGE`, confidence **90/100**.  
This is not tradable evidence while the tested window includes known-bad pre-fix COT data from the same rejected hypothesis.

2. **Probability residual pre-fix leakage:** **85-95%**.  
Single sanity check: split the exact cell by pick time relative to the 2026-05-20 fix and recompute WR/PF.

```python
cell = df.query("""
source == 'multi_asset_copytrader'
and family == 'cot'
and direction == 'SHORT'
and conf_bin == 'C0.60-0.70'
and rr_bin == 'RR1.0-1.5'
""")

cell.assign(pre_fix=cell.signal_time < "2026-05-20") \
    .groupby("pre_fix") \
    .agg(
        n=("pnl", "size"),
        wr=("pnl", lambda x: (x > 0).mean()),
        pf=("pnl", lambda x: x[x > 0].sum() / -x[x < 0].sum()),
        cotton_share=("underlying", lambda x: (x == "CT=F").mean())
    )
```

If pre-fix drives PF and post-fix collapses, it is disproved as live alpha. If post-fix-only still has adequate `n`, diversified underlyings, and PF > 1.5 net of costs, then it survives first contact.

3. **71/200 Bonferroni passes:**  
Most plausible explanation: **common contamination/leakage across correlated cells**, not 71 independent discoveries. Under the stated alpha, true-null expectation is about `200 * 7.43e-5 = 0.015` false passes. Seventy-one passes means either the test universe is not independent, the labels share leaked information, or both.

4. **Execution slippage / PF degradation:**  
For externally scraped copy-trading commodity futures signals: assume **50-150 bps per round trip equivalent degradation**, potentially worse in thinner contracts or delayed scraping. On PF, I would haircut **3.27 to roughly 1.5-2.2 before further leakage adjustment**. After leakage adjustment, expected PF is likely **<1** until proven otherwise.

5. **Size real money?**  
`PAPER_ONLY`.  
One required pre-trade test: **post-2026-05-20 only, strict publication-lag guarded, forward-paper replay with immutable timestamps**, minimum 50-100 new trades, PF > 1.3 net of realistic slippage, no single underlying > 25% of trades.

6. **Sharpest disambiguating experiment:**  
Freeze the exact rule now and run a timestamp-pure replay using only signals created after 2026-05-20, with COT data unavailable until `as_of_date + 3 calendar days` or the true CFTC release timestamp if available. Recompute WR/PF by pre-fix vs post-fix, and separately by underlying. If the edge disappears post-fix or is mostly CT=F, reject permanently. If it persists post-fix across multiple commodities with net PF > 1.3, keep it on paper only.
