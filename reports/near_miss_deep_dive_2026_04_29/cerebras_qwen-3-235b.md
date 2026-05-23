1. **Prioritize**: Strategy A (luxalgo_confluence) â€” high n, proven volume, symmetric edge, currently blocked despite active pipeline.

2. **1-line fixes**:
   - A: Remove from `_PAPER_ONLY_STRATEGIES` and kill_list entries.
   - B: Trigger manual emit check; validate Kimi source trust tier or reclassify.
   - C: Override score gate for high-WR strats with n>20 or backtest extension.

3. **Fragility concerns**:
   - A: Low fragility â€” n=205, diversified symbols, symmetric performance.
   - B: High fragility â€” n=23, rare setup, untrusted source, concentrated in tech ETFs.
   - C: Extreme fragility â€” n=22, 2-day burst, BTC-only, tiny PnL scale, low confidence.

4. **Score/confidence floor**: Keep rigid â€” floors prevent overfitting; relax only with n>200 *and* WR>55 *and* MDD<15 (C fails all).

5. **Symmetric LONG/SHORT + 50/50 TP/SL**: **FOR** â€” suggests balanced, non-noise edge; not curve-fit to one direction or exit type.