# My Findings (already merged to `main`)

These three documents are the Freebuff contribution to the 2026-11-14 audit round. Copies are kept
here so this folder is self-contained; the canonical versions live in `updates/` on `main`.

| File | Merged as | What it is |
|---|---|---|
| `2026-11-14-quant-audit-multitest.md` (75,664 B) | PR #767 → `109d827412c` | The quantitative audit of findtorontoevents.ca/audit: 365 workflows, active vs tracked picks, closed-ledger win rate and PF, field completeness, per-emitter multiple-testing verdict, Appendix A with all 365 workflows |
| `2026-11-14-quant-remediation-plan.md` (12,150 B) | PR #768 → `91c97a04aa3` | Sequenced remediation C1–C5 with falsifiable acceptance tests, the DSR/PBO/BH-FDR enforcement point, denominator-integrity rules, kill list, 4-week plan, single go/no-go metric |
| `2026-11-14-edge-search-results.md` (8,122 B) | PR #768 | The empirical edge search: 40 pre-committed trials over five families on Binance public data, IS to 2024-06-30 / untouched OOS after, 10 bps/side, matched random-entry nulls. **0/40 pass.** |

## The one-paragraph version

The deployed system is not profitable and not statistically sound: closed pick win rate 41.8% at
binomial p=1.00, 30-day PF 0.804, Σ −443.1pp, zero emitters clearing the Bonferroni threshold of
2.82e-4. I then asked whether a *simple honest rule* could be found from scratch on clean public data,
and tested five families across four iterations (trend, cross-sectional momentum, residual momentum,
RSI(2) mean reversion, correlated pairs, funding carry). None survived the matched null: best was
RSI(2)+regime at p=0.080, and funding carry's spectacular Sharpe turned out to be a volatility
artifact once I replaced a turnover-altering shuffle null with a run-length-preserving block null
(p 0.002 → 1.000). The negative is published in full, including my own invalidated first null.

## Relationship to this round's peers

- DeepAI's variant C is the only peer profitability claim that reproduces (I re-ran it), and it is a
  *selection* procedure, not a market edge — consistent with my finding that no price rule survives.
- Kilo's VWAP "VALIDATED" claim is refuted on its own numbers (`01_peer_reviews/kilo_childlike_airport/`).
- ITERATION-005's trend result is the same family as my TSMOM test; theirs is bull-windowed and
  benchmark-unaware, mine is bear-inclusive and null-tested. Both point at "risk premium, unproven alpha".
