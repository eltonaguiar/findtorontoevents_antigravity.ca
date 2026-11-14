# Consolidated Recommendations — After Reviewing Every Peer

Ordered by "unblocks the most other work". Each has an acceptance test that can fail — that is the
point; the peer round produced plenty of fixes that could only succeed.

## P0 — do these before any further profitability claim

**1. Populate `resolution_method` on every closed pick.**
100% of the 3,500-row `recent_closed` ledger has `resolution_method: None`. Until this exists, no PF
in this repo — mine, deepAI's, anyone's — can distinguish TP from SL from timeout, and every
subsequent statistical claim inherits that ambiguity.
*Accept:* 100% of new closures carry `TP|SL|TIME|FORCE`; a query grouping PF by `resolution_method`
returns non-trivial counts in every bucket.

**2. Enforce one PnL unit, with a recomputation assert.**
flaxen-hair proved ratio/percent mixing up to 100× in the same file, same symbol. A 100× error
plausibly explains the 824× EURGBP price anomaly and the `summary_picks` win rates above 100%.
*Accept:* CI recomputes `pnl_pct` from `(exit−entry)/entry×direction` for every row and fails on
`|stored − recomputed| > 1e-6` under either convention; nothing ships until it is green.

**3. Make every pick terminate, and make the denominator auditable.**
`resolved + expired + open = emissions`, published, per class. EXPIRED counts as a non-win at 0%,
never dropped and never rewritten to LOST.
*Accept:* identity holds exactly for 7 consecutive days; zero picks older than 30d without a terminal
state.

## P1 — the gates that would have caught this round's false positives

**4. Annualize Sharpe on a fixed bar clock and reject per-trade ratios.** Kilo's 3.76 implies 1.84%/yr
vol on a 40%-sized crypto book — arithmetically impossible. A units assertion on the reported Sharpe
would have blocked the claim at source.
*Accept:* every reported Sharpe is recomputed as `mean(daily excess)/std(daily excess)×√365` and unit-tested.

**5. Invert the PBO gate.** `PBO < 0.5` is a coin flip, not a pass; the repo's own standard is
PBO ≤ 0.10, DSR ≥ 0.95 deflated by the **cumulative trial count** (not the 4 variants the author
chose to count), BH-FDR q<0.05 as the family screen.
*Accept:* a synthetic iid-null panel is rejected in ≥95% of runs; nothing renders as a candidate otherwise.

**6. Benchmark every backtest against the right null.** Two peer claims fail here in opposite ways:
ITERATION-005 tested mean>0 (buy-and-hold passes too, at Sharpe 2.2 vs its 2.13); deepAI tested
random *selection* from a pool of clones. Require the null to be the benchmark the strategy must beat
— same-asset buy-and-hold for trend, matched random-entry for signals.

## P2 — disposition of this round's work

| Item | Action | Reason |
|---|---|---|
| deepAI variant C | **Paper pilot, pre-registered, no re-tuning** | Only reproduced claim; still PF 1.26 / WR 47.3% / z −0.84 → sub-T2 |
| Kilo VWAP "VALIDATED" | **Reject the certification**, keep the hypothesis | Fatal annualization error + inverted PBO gate + `UNKNOWN → trade` default |
| ITERATION-005 trend | **Reclassify** to "risk-premium harvest, alpha vs benchmark unproven" | Sharpe 2.13 ≈ its own buy-and-hold 2.2; my bear-inclusive null p=0.200 |
| My 0/40 edge search | **Stands** | 40 trials, 0 pass, best p=0.080 — expected ~2 false positives at α=0.05 |
| opencode 0/166 + `wiring` 0/166 | **Land as read-only tooling** | Two independent implementations, same zero; should be reachable, not stranded |
| `fix/audit-p0-truth` | **Close as superseded** by `9765801d4e3` | Branch not an ancestor of `main`; identical fixes already landed |
| PRs #595–#667 | **Close or rebase with a note** | 5 months stale against 20 data commits/hour |
| finpredict v2's veto list | **Adopt** | No fabricated outcomes to clean denominators — correct and non-negotiable |

## P3 — hygiene that shortens the next audit

- Root sprawl: ~700 files; trash the `=2`/`=3`/`5`/`$.*`/`⚠️` redirection residue; move 1 MB chat dumps
  out of the repo root.
- Add `updates/INDEX.md` generated at commit time (122 files today alone).
- Require audit deliverables as PRs; branch-only archives are unreadable to review and rot overnight.

## The single go/no-go metric

> **Lower 95% bootstrap bound of cost-inclusive expectancy > 0, on ≥200 clustered out-of-sample
> trades, after BH-FDR at q<0.05, with DSR ≥ 0.95 deflated by cumulative trials and PBO ≤ 0.10.**

Nothing in this round clears it. deepAI's variant C is the closest and is the right thing to put
forward — as a pilot with a kill rule, not as an edge.
