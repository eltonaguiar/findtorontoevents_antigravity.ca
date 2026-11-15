# Negative result diagnosis

Date: YYYY-MM-DD
Repo SHA:
Parent audit:

## 1. Decision rule

Dead if it fails shuffle control, walk-forward stability, or temporal discipline.
Near-miss only if it passes temporal discipline, shuffle control, walk-forward, and the friction model, and fails significance or Monte Carlo because n is small.
Actionable only if all ten proof steps pass.

Near-misses are not deployed. They may be re-tested by adding history or lengthening the paper clock. They may not be re-run with a new parameter on the same sample.

## 2. Classification matrix

| ID | Candidate | Assets | Timeframe | Proven steps / 10 | Failed at | Verdict | Root cause | Pivot | Next action |
|---|---|---|---|---|---|---|---|---|---|
| H-103 | ETF dual momentum | ETF | monthly | | forward n | NEAR-MISS if rungs 1, 2, 5, 8 hold | scored trades = 0 | LONGER_PAPER | Score the 4 logged months. Do not backfill August. |

Proven-step order: 1 temporal, 2 walk-forward, 3 multiple testing, 4 Monte Carlo, 5 friction, 6 significance, 7 regime, 8 shuffle, 9 forward test, 10 reproducibility.

## 3. Failure signature to pivot

| Failed hurdle | Meaning | Allowed pivot | Stop if |
|---|---|---|---|
| Significance, CI includes zero | Noise | A different signal family, new id | This family already failed 3 times |
| Friction | Edge smaller than cost | Lower turnover or a cheaper instrument, new id | Still dead after one cost redesign |
| Walk-forward | Overfit or regime drift | Fewer parameters, new id | Same family fails walk-forward twice |
| Shuffle control | Leak or bug | Fix the code, then re-test the same id | Leak not fixed |
| Monte Carlo, wide paths | n too small | Longer paper test if rungs 1, 2, 5, 8 passed | Still under 60 independent trades |
| Regime split | Conditional only | Pre-register the regime rule before fitting it | Trigger is not auditable |

## 4. Near-miss register

| ID | Trades so far | What is missing | Fix | Paper horizon |
|---|---|---|---|---|
| H-103 | 4 month stamps, 0 scored | August absent. n>=100 required | Score logged months only | Monthly until n=100 |

Do not extend the backtest window after seeing the result. That is a new trial. Extend the paper test.

## 5. Combination

A blend of weak signals is a new hypothesis. It needs its own id, a correlation cap, and a deflated Sharpe on the blend, not on the members.

## 6. Verdict (check one)

- [ ] Proven edge. Forward test per PROOF_PROTOCOL.md.
- [ ] Near-miss only. Paper clock, frozen parameters.
- [ ] Clean negative. Trial count: ___. Deflated Sharpe bar: ___. Shuffle control showed the pipeline is not leaking: yes/no.

## 7. Sign-off

| Role | Name | Date |
|---|---|---|
| Lead | | |
| Statistics | | |
| Governance | | |
