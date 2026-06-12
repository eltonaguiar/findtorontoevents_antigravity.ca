(1) **Per-(symbol, direction, day) dedup is necessary but not sufficient.** It fixes repeated emissions of the same trade, but it does **not** make same-day cross-symbol picks independent. Use **effective-n via clustering**.

Concrete estimator:

- Cluster by `trade_date` at minimum; better: `trade_date + sector / beta bucket / market regime`.
- For win-rate:
  - Let cluster \(c\) have \(m_c\) distinct picks and cluster WR \(p_c\).
  - Estimate \(Var(\hat p)\) by cluster bootstrap or design effect.
  - Compute  
    \[
    n_{eff}=\frac{\hat p(1-\hat p)}{Var_{cluster}(\hat p)}
    \]
- Equivalently estimate intraclass correlation \(\rho\) on binary outcomes:
  \[
  n_{eff}=\frac{n}{1+( \bar m -1)\rho}
  \]
- For PF, use the same clusters and bootstrap gross-profit/gross-loss ratios. Do **not** quote raw n for PF confidence.

If many same-day symbols share the same macro/sector shock, raw n can be 5–10x too high.

(2) **All resolved picks is not automatically “wrong,” but it answers a different question.**

- All resolved picks estimates: “When this condition appears in the traded universe, what happened next?”
- Emitting-strategy-only picks estimates: “When this strategy emitted this condition, what happened next?”

The global lane is useful, but it can be biased for a specific strategy if that strategy emits in different symbols, regimes, directions, or risk states. I would report both:

- **Global condition lane** for robustness.
- **Strategy-conditioned lane** for actual deployment decisions.

For the global lane, weight or stratify by symbol, direction, regime, and condition co-occurrence so it matches the emitting strategy’s eligible distribution.

(3) **Minimum: 8 regime-weeks, preferably 12.** A 30d / ~4-week PF is only diagnostic. Gate believability on:

- \(n_{eff} \ge 80\) resolved trades, or at least 40 winners and 40 losers.
- Cluster-bootstrap PF CI excludes 1.0, preferably lower bound > 1.1.
- No single day, symbol, or sector contributes >10–15% of P/L.
- Stable sign across at least 2 distinct volatility/liquidity regimes.