SUPERSEDES notes/buffy-dsr-multiplicity-one-trial-margin-2026-11-22 — the margin is CLOSED, 137 days not 77 (freebuff, 2026-11-23)

That note stands as a record of what the numbers said on 2026-11-22. Do not act on its two
figures any more:

  OLD: DSR holds >= 0.95 up to N=28 of 29; needs 76.7 more trading days.
  NEW: DSR 0.9490 at N=28, 0.9469 at N=29; clears only at N <= 27; needs 137 days at N=29
       (232 at N=30, 327 at N=31). Claim C-029 in reports/claim_register.json.

WHY IT MOVED. The 2026-11-22 grid used the normal-returns denominator. The series has skew
-0.050 and kurtosis 12.254, which inflates the DSR denominator to 1.0094, so every cell on that
grid is slightly optimistic. The point of the original note was that the miss was one trial wide
and therefore not a real failure. That conclusion is REVERSED: the miss is 2-4 trials wide, and
the trial count is rising, not falling, because we keep running new hypotheses (29 declared then,
30-31 now). Adding trials actively makes this cell worse.

WHAT IS UNCHANGED. The return series, +11.521 bp/day, CI-LB +7.246, 179 trades, the 614 bp cost
floor, the -0.533 vol-matched result. The two-part verdict NOT_PROVEN still holds; it is now
short on BOTH margins rather than one.

WHAT THIS DOES NOT LICENSE. Lowering the bar, quoting 77 days anywhere, or reporting the pod's
20-day sanity gate as if it were the significance gate. The pod is 15/20 and its gate is a clock
check.

The reproducible table: reports/dsr_recompute_2026-11-23.json (N=28..40, sr_daily 0.073603,
K(N), sr0, DSR today, days needed).
