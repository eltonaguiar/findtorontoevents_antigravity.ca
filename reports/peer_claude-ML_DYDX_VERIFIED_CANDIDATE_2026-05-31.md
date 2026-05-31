# ML-Enhanced DYDXUSDT LONG — Verified Candidate (2026-05-31)

**Status:** SURVIVED 6-parallel verifier swarm (wiha77fnj). Strongest single-candidate found today by Wilson lower-bound measure.

**NOT YET EDGE.** Add to 30-day forward paper-pilot tracker. Do not size up.

---

## 1. Headline numbers

| Metric             | Value     |
|--------------------|-----------|
| Strategy           | `ml_enhanced_DYDXUSDT` LONG |
| Symbol scope       | DYDXUSDT only (single-symbol) |
| Closed trades (n)  | 34        |
| Win rate (p_hat)   | 0.9412 (32/34) |
| Profit factor      | 10.36     |
| Top-3 trade share  | 18.3 %    |
| Wilson 95 % LB     | **0.8091** |

## 2. Wilson lower-bound computation

Wilson score interval for a binomial proportion, n = 34, p_hat = 32/34 = 0.94118, z = 1.96:

```
denom   = 1 + z^2/n                       = 1 + 3.8416/34       = 1.11299
center  = (p_hat + z^2/(2n)) / denom      = (0.94118 + 0.05649)/1.11299 = 0.89638
margin  = (z/denom) * sqrt(p_hat*(1-p_hat)/n + z^2/(4 n^2))
        = (1.96/1.11299) * sqrt(0.001628 + 0.000831)
        = 1.7611 * 0.04959                = 0.08732
LB      = center - margin                 = 0.89638 - 0.08732   = 0.80906
```

→ **Wilson 95 % LB = 0.809.** Comfortably above the 0.50 random-coin gate.

## 3. Concentration check (artifact filter)

Top-3 winning trade contribution to total profit: **18.3 %.**
Comparison — `ig_contrarian` SHORT (rejected today as artifact): top-3 share = **93.2 %.**
DYDX is clean — profit is spread across the trade book, not driven by 1-3 fluke wins.

## 4. Required forward sample size to confirm at n=100

Conservative carry-forward: assume p_hat dips toward the historical edge. For combined n_total = 34 (historical) + 100 (forward) = 134, the Wilson LB stays above **0.50** if forward WR remains **>= 0.65**, and above **0.55** if forward WR remains **>= 0.70**.

Decision rule recommended for the paper-pilot tracker:
- Forward WR >= 0.70 at n_fwd = 100 → graduate to shadow-pilot, then live consideration
- Forward WR 0.50 - 0.69 → keep tracking, do not size up
- Forward WR < 0.50 → demote, treat as artifact

## 5. Comparison to today's other candidates

| Candidate                              | n  | WR     | Wilson LB | Verdict        |
|----------------------------------------|----|--------|-----------|----------------|
| **ml_enhanced_DYDXUSDT LONG**          | 34 | 94.12% | **0.8091**| **SURVIVED**   |
| CRYPTO volatility_breakout             | 85 | 61.2%  | 0.5057    | Borderline     |
| EQUITY stocks_rsi2_pullback            | 39 | 59.0%  | 0.4344    | REFUTED        |
| prediction_market_consensus LONG/SHORT | —  | —      | —         | RETIRED (PR #182) |
| mega_mutation                          | —  | —      | —         | ARITHMETIC ARTIFACT |
| ml_RENDER                              | —  | —      | —         | STATS WRONG    |
| ig_contrarian SHORT                    | —  | —      | —         | CONCENTRATION (top-3 = 93.2 %) |

## 6. Caveats (must read before promoting)

1. **Small n** — 34 closed trades has wide intrinsic standard error even with strong p_hat.
2. **Single-symbol** — DYDXUSDT only. Could be one-ticker overfit / coincidence on a DYDX rally window.
3. **CRYPTO bull bias** — verify the window does not coincide with broad CRYPTO uptrend that lifted all longs.
4. **Survivorship bias risk** — 1 of 6 surviving the verifier swarm is plausibly Type-I error at the swarm level.
5. **No regime filter** — strategy may not work in CRYPTO drawdown regimes.

## 7. Operator recommendation

- **NOT yet edge.** Do not size up.
- **Add to 30-day forward paper-pilot tracker** alongside CRYPTO `volatility_breakout`.
- **Day-30 interim**: re-compute Wilson LB on (historical 34 + forward n) combined.
- **Day-60 graduation gate**: Bonferroni-corrected significance + forward WR >= 0.65.
- **Day-90 size-up decision**: requires operator personal sign-off.

## 8. Peer work acknowledged (parallel)

- **kilo** — 8-agent truth-layer audit at `/tmp/truth-layer-audit` (branch `truth-layer-audit-20260531`). Overlaps with PR #285 (edge_stability automation).
- **qwen** — audit-pick-funnel worktree (`.qwen/worktrees/`); DB cross-check found 3.7 M row mismatch between `ejaguiar1_stocks` vs `ejaguiar1_backtests` on `bt_backtest_trades`. See `db_crosscheck_report.json`.
- **zoo** — `audit-truth-layer-worktree` AGENT 7 pick_funnel reconciliation.
- **freebuff** — money_maker_ready_v2 deep dive; mega_mutation arithmetic artifact + concentrated forex flagged.

## 9. Reproduction

Source data: `alpha_engine/data/monte_carlo_results/mc_ml_enhanced_*.json`
Verifier swarm id: `wiha77fnj`

---

*Generated 2026-05-31 by Claude Opus 4.7 subagent following verifier-swarm fan-out.*
