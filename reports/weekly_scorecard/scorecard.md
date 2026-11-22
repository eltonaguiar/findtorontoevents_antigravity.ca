# Weekly scorecard

_generated 2026-11-22 22:05 UTC by `tools/weekly_scorecard.py`_

T-bill hurdle used throughout: **3.50%/yr**

## Verdicts

| item | verdict | evidence | class |
|---|---|---|---|
| Harness certification | **PASS** | 6 harnesses (5 deterministic, 1 live); drift vs baseline is checked by tools/harness_certification.py --rerun | deterministic |
| Integrity lint | **NOT RUN** | run tools/integrity_lint.py | - |
| Live ledger net expectancy | **-15.24 bp** | n=10,968  PF=0.904  CI-LB=0.852  t=-3.91 | observed |
|   CRYPTO | **FAIL** | net -18.17 bp  PF 0.885 (LB 0.829)  n=9,099 | observed |
|   EQUITY | **pf>1 but CI includes 1** | net 18.60 bp  PF 1.088 (LB 0.885)  n=936 | observed |
|   ETF | **FAIL** | net -0.32 bp  PF 0.997 (LB 0.802)  n=590 | observed |
|   FOREX | **FAIL** | net -15.13 bp  PF 0.668 (LB 0.420)  n=252 | observed |
|   COMMODITY | **FAIL** | net -346.51 bp  PF 0.120 (LB 0.033)  n=44 | observed |
|   BOND | **FAIL** | net -18.22 bp  PF 0.657 (LB 0.268)  n=35 | observed |
|   FUTURES | **INSUFF-N** | net 57.09 bp  PF 1.556 (LB 0.341)  n=12 | observed |
| Funding carry, net of fees | **REFUTED** | gross 3.555%/yr  halves 5.96 -> 1.24%/yr  blocks>cash 18/28 | observed |
| Vol risk premium (existence) | **ESTABLISHED** | mean 357.9 bp  t=46.50 | observed |
|   short-vol harvest | **RUINED** | worst period -102.9% | observed |
|   GDX/SLV pairs | **REFUTED** | ADF OOS 0.15  net 2.228%/yr | observed |
| Prediction market calibration | **ESTABLISHED** | Brier skill 0.4956  n=362  buckets flagged 2/10 | observed |
| Execution capacity | **CAPPED** | largest size clearing the cliff: $500,000 | observed |
|   breakout gross edge | **UNMEASURED cost** | 0bp 22.43 bp (t 7.32) -> 24bp -1.57 bp | observed |
|   fill-convention premium | **INFLATION** | lag-0 fill is worth 2.54 bp/trade | observed |
|   turnover frequency | **cost dial** | best Sharpe 0.81 at monthly | observed |

## State notes

- L1 48 rows are WON on gross but LOSS on net (1.0% of gross wins). Any WR computed from the won flag overstates by this much.
- L2 48 status-label conflicts (0.44% of rows).
- L3 src 'luxalgo_filters' is 36.7% of the ledger; any ledger-wide stat is mostly that one emitter.
- NOT RUN: integrity lint (selection-on-DV, provenance, n_trials) (`reports/integrity_lint/latest.json`)

## What this scorecard deliberately does not do

- It does not rank strategies. Ranking is how an unmeasured candidate
  gets promoted; labels are set by evidence class, not by return.
- It does not print a number it could not measure. Absent artifacts
  read NOT RUN, and unmeasured cost blocks promotion
  (`docs/PROMOTION_GATE_2026-11-22.md` gate 1).
- It does not report gross without net.

---
No capital deployed. Not investment advice. UNMEASURED means unmeasured, not zero.