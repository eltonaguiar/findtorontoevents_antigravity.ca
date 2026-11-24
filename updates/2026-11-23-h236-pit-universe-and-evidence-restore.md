# H-236: breadth does not destroy H-201, but 5 years cannot certify it — and the evidence sweep was wrong

**Date:** 2026-11-23 · **Owner:** buffy (freebuff) · **Paper only, zero capital, not advice**

## H-236 — H-201 on the 44-name PIT universe: `REFUTED`

Pre-registered (`plans/2026-11-23-prereg-H-236-h201-pit-universe.md`), same rule throughout — 126-day
lookback, top 3, 21-day rebalance, 10 bp/unit turnover, SPY benchmark. Window 2021-11-30..2026-11-20
taken from the PIT artifact so membership is defined rather than assumed.

| book | n | mean | 95% CI | excess vs SPY | verdict |
|---|---|---|---|---|---|
| PIT 44 names | 1,254 | **+9.407 bp** | **[−3.147**, +22.199] | +4.901 | **fails** CI-LB > 0 |
| MEGA 10, same window | 1,254 | +9.540 bp | [+1.072, +18.428] | +5.033 | passes |

This is the most informative kind of failure. The **point estimate is essentially identical**
(9.41 vs 9.54 bp/day; excess 4.90 vs 5.03), so breadth does not dilute the effect, and the null
"momentum only works on the 10 mega caps" is not supported. What fails is the **interval**: a wider
universe spreads outcomes, and 5 years cannot certify an effect that 15 years of the narrow book
could (H-234, CI-LB +7.246).

The pre-registered label is `REFUTED` and I am not relabelling it. What it bounds: attribution to
period+universe jointly cannot be established from this sample. What it does **not** do: overturn
H-234.

## The evidence sweep was wrong, and that is the bigger finding

My earlier sweep reported **6 genuinely missing evidence files** and told COMS that five claims
(C-001, C-003, C-005, C-006, C-008) had no reachable evidence and needed regeneration. That was
false. `reports/horizon_backtest_2026-11-22.json`, `reports/2026-11-22-horizon-allocation-review.md`
and `tools/horizon_backtest.py` all exist — on **my own PR #1067 branch**, which I had checked for
`/tmp/cv` but not `/tmp/prmain`.

Corrected sweep: main + both worktrees → **15 OK / 55 in PR branch / 0 missing / 2 non-paths**, then
the 55 were copied to main → **70 OK / 0 missing / 2 non-paths**. Every file-based evidence path in
the claim register now resolves from main.

The lesson is the same one as the missing vol-target script, one level up: a checker that only knows
about the tree it is standing in will call everything else "missing". Both failures were **my
checker's scope**, not someone's deleted file — and in both cases the claim was true and the
evidence existed.

## Verification

- `tools/h236_h201_pit_universe.py` → exit 0, wrote
  `reports/h236_h201_pit_universe_2026-11-23.json`, printed `VERDICT: REFUTED`.
- Registry re-parsed: 120 hypotheses, `H-236` present once, status `REFUTED`.
- Claim register re-parsed: 28 claims, `C-028` present once.
- Sweep re-parsed: 70 OK, 0 MISSING, 2 NOT_A_FILE_PATH.

## Limitations

- 5-year window and a 44-name universe that is `PARTIAL_NON_DELISTING_AWARE`; a pass would still not
  have been survivorship-free.
- The MEGA-10 comparison shares 10 of the 44 names, so the two books are not independent.
- Adds another trial; the deflation bar moves again.
