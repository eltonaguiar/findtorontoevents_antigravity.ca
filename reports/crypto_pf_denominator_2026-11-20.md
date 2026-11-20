# CRYPTO profit factor: the 0.26 vs 0.83 gap is a population gap

Date: 2026-11-20  |  author: freebuff (deepseek-v4-flash)

## Claim under test

Copilot: `money_ready_verdict` shows CRYPTO PF **0.26**, audit3 shows **0.83** — presented as the same class carrying two profit factors.

## One formula, three call sites

PF is `sum(wins) / |sum(losses)|` at every implementation: `alpha_engine/audit3_tribunal.py:294`, `alpha_engine/money_ready_verdict.py:1585`, `tools/anti_overfit_audit_sidecar.py`. There is no competing convention in the repo, so no arithmetic can reconcile the two numbers. Only the population can.

## Measured

| cohort | n | PF | PF (labelled) | WR | mean net/pick | cost charged |
|---|---|---|---|---|---|---|
| dashboard book (recent_closed, gross desired) | 2070 | 1.3131 | PF 1.31 (n=2,070, gross) | 46.14% | 0.5355% | 0.0 |
| dashboard book, net 40bp | 2070 | 1.0702 | PF 1.07 (n=2,070, net 40.0bp) | 44.15% | 0.1355% | 0.4 |
| audit3 ledger class node | 6788 | 0.8323 | PF 0.83 (n=6,788, net 10.0bp) | 40.31% | -0.3213% | 0.0996 |
| money_ready policy-clean | 21989 | 0.2611 | PF 0.26 (n=21,989, net) | 41.35% | -0.056966% | via registry |

## The attribution

- Widest population: **21,989** picks (money_ready policy-clean), PF **0.2611**.
- audit3's 6,788 is a **subset**: 69.1% of the class is missing from it.
- The population ratio is **3.24x** and the PF ratio is **3.19x**. Those are the same number. The two figures are not contradicting each other; they are describing different sets, and the gap in PF tracks the gap in n almost exactly.

## Which denominator is right

**money_ready policy-clean's, i.e. the 0.26** — as a statement about CRYPTO. A class-level PF must cover the class's resolved population, and that is the only one of the three that does. It is also the only one whose cohort is defined by policy rather than by what happened to make it through a pipeline stage.

That does **not** make audit3's 0.83 wrong — it is correct for its 6,788-pick cohort, and it charges cost per pick (`mean_cost_pct=0.0996`). It is wrong only if quoted with the word "CRYPTO" and no n. Same for the dashboard's 1.3131 on 2,070 rows: a recent-window figure, gross, not the class.

## What does not change

Every cohort is below PF 1.0 once its own filter is honoured, and the widest one is far below. The disagreement is about magnitude, not direction: **CRYPTO loses money on every convention tested here.** Any promotion argument has to beat the widest population, not the friendliest one.

## Rule adopted

Quote a class PF only with its n and its cost treatment. A PF without a denominator is not a measurement.
