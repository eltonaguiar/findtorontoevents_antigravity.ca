# Negative-result diagnosis

Generated: YYYY-MM-DD
Repo SHA:
Rule: record the first failed rung. Do not retune a dead candidate. A parameter change after seeing the result is a new hypothesis and re-enters pre-registration.

## Sweep verdict

One sentence. If nothing is PROVEN, say that here.

Configurations tried, project-wide:
Deflated-Sharpe or Reality-Check threshold used:
Bug sweep done: yes/no. Shuffle-control failures are code bugs until proven otherwise.

## Ladder

| Rung | Fail means | Allowed next move | Forbidden next move |
|---|---|---|---|
| 1 Temporal / next-bar | Lookahead or same-bar entry | Fix the clock, then re-register | Keep the same-bar fill |
| 2 Walk-forward | Parameters drift or the OOS window dies | Simpler, fewer parameters, new id | Pick the best window |
| 3 Multiple testing | The hit is inside the search | Stop the family | Add another variant on the same sample |
| 4 Block bootstrap | Too few trades, or the 5th percentile is negative | Longer forward test if rungs 1, 2, 5, 8 passed | Deploy on the mean path |
| 5 Friction | Gross edge, net dead | Lower turnover or a cheaper instrument, new id | Ignore costs |
| 6 Significance | CI includes zero | Stop the signal class | Chase a cousin of the same signal |
| 7 Regime split | Only one regime pays | Pre-register "trade only in regime X" before defining X from this sample | Call it unconditional |
| 8 Shuffle control | Pipeline leak | Fix the code. Do not trade | Blame the market |
| 9 Forward protocol | No live clock | Start the paper log. Do not size | Backfill missing months |
| 10 Reproducibility | Cannot rerun | Publish the command | Quote a chart |

## Per candidate

Copy this block once per dead or near-miss rule.

### Name — DEAD or NEAR-MISS

- Registry id:
- Class / timeframe:
- First failed rung:
- Number, n, and path:
- Signature: noise | cost | overfit | leak | sample-size | regime-only | not-reproducible
- Near-miss: yes only if rungs 1, 2, 5, and 8 passed and the only fail is 4 or 6 from small n
- Pivot: one of STOP_FAMILY, FIX_CODE, LOWER_TURNOVER, LONGER_PAPER, REGIME_PREREGISTER, PASSIVE
- Do not:

## Family rollup

| Signal family | Candidates | Dominant signature | Pivot |
|---|---|---|---|
| | | | |

## What this sweep does not authorize

- Lowering a gate so a row turns green
- Re-running the same sample with a new stop, lookback, or universe
- Treating a paper flag as registration
- Calling a monthly hold stamp a closed trade
