# Next Steps — Backtest Summary (2026-10-23)

## TL;DR (plain English)

We ran two big "let's find a winning strategy" experiments. Both came to the same
honest conclusion:

- **We could not find any single strategy that reliably beats the market.** Of 599
  tested strategies, **zero** passed the strict quality gates (0 ELITE, 0 SURVIVOR).
- **Boring, cheap, broadly diversified index funds won.** In the mutual-fund test,
  the best performers were plain index funds — **XEQT** (Canada, all-in-one equity)
  at **14.25% net CAGR** and **TDB902** (TD US Index) at **17.08% net CAGR**.
- **The smartest next move is not to hunt for a magic stock-picking strategy.**
  It is to build a low-cost, diversified index portfolio and — if we want an edge —
  add a *validated* tactical rotation layer on top.

---

## 1. Winner-Hunt Backtest — No ELITE / SURVIVOR Strategies

### What we did
We screened **599 strategies** from the strategy registry (`pf_registry.json`)
against four strict quality gates, then applied a statistical correction (FDR) to
avoid "false winners":

| Gate | Requirement |
|------|-------------|
| Trades | `n >= 100` (enough data to be meaningful) |
| Profit Factor (net) | `>= 1.5` |
| Lower-bound confidence | 95% CI lower bound on PF `>= 1.2` |
| Max drawdown | `<= 20%` |

### What we found
- **8 strategies** passed all four raw gates — but **all 8 were flagged as
  single-source artifacts** (implausibly high profit factors like PF ≈ 156 that
  almost certainly come from a data/selection quirk, not real edge).
- After excluding those artifacts, the honest result is:
  - **ELITE: 0**
  - **SURVIVOR: 0**
  - **FAILED: 599**
- Benchmark ledger coverage was sparse (20/599 strategies had excess-return data),
  so even the raw gate-passers couldn't be corroborated against a benchmark.

### ELI5
Imagine you test 599 different "recipes" for picking stocks. 8 look amazing at
first — but when you check, they all have a hidden flaw (they only "work" because
of a data mistake). After removing the flawed ones, **none** of the 599 recipes
actually beat a coin-flip benchmark reliably. The honest answer is: we don't have
a proven winner yet, and forcing one would be fooling ourselves.

---

## 2. Mutual-Fund Walk-Forward Backtest — Index Funds Win

### What we did
We walked forward year by year (2004–2025, 22 windows, net of fees/MER) to see
whether any active fund-selection rule could beat simply holding a broad index fund.

### Results (net CAGR — the amount you'd actually keep after fees)

| Option | Net CAGR | What it is |
|--------|----------|------------|
| **TDB902** | **17.08%** | TD US Index — a cheap US equity index fund |
| **XEQT.TO** | **14.25%** | All-in-one Canadian equity ETF (MER 0.19%) |
| Active "picker" portfolio | 11.89% | Selection rules picking funds each year |

### Key takeaways
- **The active picker (11.89%) lost to the plain index funds (14.25% / 17.08%).**
- This matches the industry reality (SPIVA): the large majority of active Canadian
  funds underperform their index over 1–10 year horizons.
- Lower fees and broader diversification beat clever selection — consistently.

### ELI5
Imagine two people investing for 20 years. Person A pays an "expert" to pick which
funds will win next year. Person B just buys a cheap fund that owns a little bit of
the whole market. At the end, Person B has more money — the expert's picks cost
more in fees and were often wrong. **The cheapest, most diversified fund won.**

---

## 3. What This Means — The Actionable Summary

1. **Stop hunting for a single "secret" stock/crypto/forex pick strategy.** The
   data says per-symbol pick engines have no honest, statistically-sized edge.
2. **Core portfolio = cheap, broad, diversified index funds.**
   - Canada: **XEQT.TO** (or VEQT.TO) as the all-in-one core.
   - US: low-fee broad funds (e.g. FZROX / FNILX / BKLC / FXAIX).
   - These are the "least-bad," evidence-backed choices — not because they're
     exciting, but because they reliably keep more of what the market returns.
3. **If we want an edge, use the one validated overlay:** the **tactical
   multi-asset rotation family** (Sharpe ~0.88–1.21, drawdown roughly 2.5× smaller
   than SPY, validated 2007–2026). Productize this as a fund wrapper on top of an
   index core — rather than chasing single-symbol picks.
4. **Keep monitoring, don't promote.** FOCPX (US) is a *candidate* (style-adjusted
   +2.2%/yr) — not a proven winner. It deserves watch-list status, not a buy signal.
5. **Measure forward.** Continue the walk-forward / forward-testing loop so any
   future strategy earns its place through out-of-sample results, not hindsight.

---

## 4. Proposed Next Steps (Actionable Checklist)

- [ ] **Adopt the low-cost index core as the default posture** (XEQT/VEQT in
      Canada; FZROX/FXAIX class in US) for any paper or real portfolio baseline.
- [ ] **Wrap the validated tactical rotation family** as a fund-style product
      (paper first) layered over the index core; track it alongside the indexes.
- [ ] **Retain FOCPX on a watch list** with pre-registered out-of-sample criteria;
      only escalate if it clears them.
- [ ] **Treat the winner-hunt result as a gate, not a dead end:** no single-symbol
      pick engine is promoted unless it demonstrates real, out-of-sample, net-of-cost
      edge that survives FDR and benchmark corroboration.
- [ ] **Maintain the backtest harness** (`tools/winner_hunt_backtest.py`,
      `tools/mf_walkforward_backtest.py`) so future strategies get the same
      rigorous battery before any capital is risked.

---

**⚠ NOT FINANCIAL ADVICE** — This is research documentation. Past performance does
not predict future results. Any fund or strategy mentioned is for analysis purposes
only, not a recommendation to buy or sell. Always consult the fund's official
prospectus and a qualified financial advisor before making investment decisions.
