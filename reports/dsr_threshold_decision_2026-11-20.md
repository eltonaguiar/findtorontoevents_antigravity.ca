# DSR threshold: decided at 0.95, because lowering it buys almost nothing

Date: 2026-11-20
Author: freebuff (deepseek-v4-flash)
Subject: the gate added in #1017 fails 74/80 strategies. Should the threshold move?

## The measurement

`audit_dashboard/data/anti_overfit_audit.json`, generated 2026-11-20T01:09Z,
80 strategies with a DSR value (`--min-n 10`):

| DSR floor | pass | fail | pass rate |
|---|---|---|---|
| 0.99 | 6 | 74 | 7.5% |
| **0.95** (AFML / current gate) | **6** | **74** | **7.5%** |
| 0.90 | 7 | 73 | 8.8% |
| 0.85 | 7 | 73 | 8.8% |
| 0.80 | 7 | 73 | 8.8% |
| 0.75 | 7 | 73 | 8.8% |
| 0.70 | 7 | 73 | 8.8% |
| 0.50 (module's "reject" line) | 10 | 70 | 12.5% |
| 0.25 | 16 | 64 | 20.0% |
| 0.10 | 21 | 59 | 26.3% |

Distribution: median **0.0033**, mean 0.1563, p75 **0.0000**. Only 37 of 80
strategies have a positive Sharpe at all; of those, 6 clear 0.95 and 10 clear 0.50.

## Decision: keep 0.95. Do not tune the gate to a green tick.

Moving the floor from 0.95 to 0.50 — the module's own "almost certainly overfit"
line, the loosest defensible cut — converts **4 of the 74 failures** into passes.
That is not a threshold problem, and re-pointing the gate at 0.50/0.80/0.90 would
be choosing the bar to fit the book rather than measuring the book against the
bar. 0.95 is also already a multiple-testing-corrected quantity: `deflated_sharpe`
takes `n_trials` = the number of strategies scored (80), so the correction is
inside the number, not layered on top.

## Consequence, stated plainly

The audit-dashboard job will report failure every hour until the book changes.
That is the honest signal: **74 of 80 published strategies have not survived a
multiple-testing correction.**

The lever is not the threshold. It is publication: demote or probation-list the
strategies that cannot clear DSR instead of showing them beside the 6 that can.
Once the registry and the dashboard publish only certified cells, the same gate
goes green *because the claim got smaller*, which is the only reason it should.

## Where the margin actually is

The 6 survivors are: `cta_golden_cross_200` (n=36), `forex_rsi2_mean_reversion`
(n=1,487), `ml_enhanced_INJUSDT_1d_B_lightgbm` (n=24),
`vt_equity_two_day_rsi_reversal` (n=131), `prediction_market_consensus` (n=215),
`ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` (n=30). Three of the six are under
n=40 — DSR at n=24 is a weak certificate, not a licence to size. So even the 7.5%
pass rate overstates the book's certified edge.

## Reproduce

```
python3 - <<'PY'
import json, statistics as st
d = json.load(open('audit_dashboard/data/anti_overfit_audit.json'))
rows = [r for r in d['strategies'] if isinstance(r.get('dsr'), (int, float))]
dsr = sorted((r['dsr'] for r in rows), reverse=True)
for t in (0.99, 0.95, 0.90, 0.50):
    print(t, sum(1 for v in dsr if v >= t), '/', len(dsr))
print('median', st.median(dsr))
PY
python3 tools/anti_overfit_audit_sidecar.py --check-only --gate   # exit 2
```

## Limit

This decides the *statistical* floor, not the *CI policy* of failing a job whose
purpose is publishing data. If a red hourly run becomes noise the team stops
reading, the honest fix is a separate blocking workflow that judges the artifact
and leaves the publishing job green — not `continue-on-error` on this step, and
not a lower threshold.
