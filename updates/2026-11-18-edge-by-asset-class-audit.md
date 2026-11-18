# Edge by asset class: what `/audit` can prove — 2026-11-18

Built `tools/edge_by_asset_class_audit.py` to answer the only question that matters
for real money: **which asset classes have a demonstrated edge, and which only look
like they do?** It reads the dashboard's own closed ledger
(`audit_dashboard/data/dashboard_data.json`, 3,500 closed picks) and tests each
class against the breakeven win rate implied by its *own* average win and average
loss — not against 50%, because 45% is edge on a 1:2 payoff and ruin on 2:1.

## Method

For each asset class, and then for each strategy inside it with n >= 30:

* win rate, Wilson 95% interval (a small sample cannot look proven)
* **breakeven** win rate = avg_loss / (avg_win + avg_loss), from that class's own fills
* profit factor, expectancy %, one-sided binomial p against breakeven
* **Benjamini-Hochberg at q = 0.10** across every strategy test, because ~24
  strategies are tested at once and a lone p<0.05 is expected by chance

`PROVEN` requires n >= 100 and a Wilson lower bound above breakeven. A strategy is
only called proven if it also survives FDR.

## Result (gross of costs — see the caveat)

| class | n | WR | Wilson 95% low | breakeven | PF | expectancy % | p | verdict |
|---|---|---|---|---|---|---|---|---|
| CRYPTO | 2070 | 46.1% | 44.0% | 39.5% | 1.31 | +0.54 | <0.0001 | **PROVEN** |
| EQUITY | 690 | 47.5% | 43.8% | 43.1% | 1.23 | +0.46 | 0.0107 | **PROVEN** |
| ETF | 503 | 44.3% | 40.1% | 42.7% | 1.07 | +0.08 | 0.237 | NO EDGE |
| FOREX | 199 | 32.2% | 26.1% | 50.6% | 0.66 | −0.13 | 1.000 | NO EDGE |
| BOND | 28 | 35.7% | 20.7% | 51.1% | 0.56 | −0.23 | 0.965 | INSUFFICIENT |
| COMMODITY | 9 | 44.4% | 18.9% | 49.2% | 1.03 | +0.03 | 0.732 | INSUFFICIENT |
| FUTURES | 1 | 0.0% | — | — | — | −0.47 | — | INSUFFICIENT |

**Two classes are provable today: CRYPTO and EQUITY.** CRYPTO is the strong one
(Wilson low 44.0% against a 39.5% breakeven, PF 1.31 over 2,070 fills). EQUITY is
real but marginal — its Wilson low (43.8%) clears breakeven (43.1%) by seven
tenths of a point, so it is one bad week from flipping.

**FOREX is not thin, it is losing**: 199 closed picks, 32.2% win rate against a
50.6% breakeven, PF 0.66. That is a negative-expectancy class, not an under-sampled
one. ETF is the trap: PF 1.07 and positive expectancy look fine, but the win rate
does not clear its own breakeven (p = 0.237) — it is noise with a small positive
drift, i.e. exactly what a coin flip looks like over 503 trades.

## Which strategies carry it (after FDR)

Of 23 strategy tests, **two survive** — both CRYPTO:

* `MomentumEMA` — n=73, WR 57.5% vs 40.4% breakeven, PF 1.99, p=0.0022
* `mega_mutation_macd_rsi_m048` — n=57, WR 68.4% vs 29.8% breakeven, PF 5.11, p<0.0001

EQUITY's class edge is **breadth, not a proven strategy**: `rs-breakout-scout`
(n=45, p=0.021) and `vol-contraction-scout` (n=59, p=0.093) are promising but do
not survive correction. That is a legitimate portfolio claim ("the class is
positive") and a *different* claim from "this strategy is proven".

## Three caveats that would change the verdict

1. **No cost field exists in the ledger.** `after_cost_net_per_trade` is present on
   **0 of 3,500** closed picks, so every number above is gross. A 0.54%/trade
   crypto edge can survive retail fees and slippage; a 0.08%/trade ETF edge cannot.
   Until costs are actually subtracted, no class should be called money-ready.
2. **Picks are not independent.** The Wilson intervals assume independent trades;
   2,070 crypto fills share symbols, regimes and entry hours, so the true interval
   is wider than printed. Treat CRYPTO's "proven" as "positive expectancy,
   confirmed direction", not as a tight bound.
3. **A bucket named after a system is not a strategy.** `strategy == "alpha_engine"`
   (n=33, 13 symbols, every exit a TP/SL hit) is the fallback when nothing was
   recorded. It scored WR 84.8%, PF 11.06, p~0 — and would have "proven" an edge
   that does not exist. The tool now excludes system-name buckets from the family.

## What would put the other five classes on the same footing

* **FOREX** — stop publishing it until a strategy clears breakeven; 199 picks at
  PF 0.66 is enough evidence to retire the current entries, not to keep sampling.
* **ETF** — needs a cost-adjusted re-test: at PF 1.07 the class cannot pay fees.
* **BOND / COMMODITY / FUTURES** — 28 / 9 / 1 closed picks. Nothing can be
  concluded; the target is 100 closed fills per class *with* cost data, which is a
  pipeline-volume problem, not a statistics problem. The dashboard's own
  `money_ready_verdicts.COMMODITY` agrees (`pf_ok: false`, PF 1.028 on n=227).

## Reproduce

```
python3 tools/edge_by_asset_class_audit.py
# -> reports/edge_by_asset_class_2026-11-18.json  (machine readable, per class + per strategy)
# -> reports/edge_by_asset_class_2026-11-18.md    (this table)
```

Re-run it after any ledger change; the JSON carries `fdr.survivors` so a regression
in a previously proven strategy shows up as a shrinking survivor list.
