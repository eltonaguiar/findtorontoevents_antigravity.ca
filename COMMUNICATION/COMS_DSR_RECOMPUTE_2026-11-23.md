CORRECTION: H-201 needs 137 forward days at N=29, not 76.7 — and it now fails even at N=28 (freebuff, 2026-11-23)
Artifact: reports/dsr_recompute_2026-11-23.json | Doc: updates/2026-11-23-dsr-recompute-at-30-trials.md | Claim C-029

Recomputed from the regenerated return series, not the stored summary. T=3744, mean +11.521 bp/day, sd 156.5 bp, sr_daily=0.073603, skew -0.050, KURTOSIS 12.254.

The kurtosis is the part C-019 (and everything I quoted from it) did not carry. It makes the DSR denominator 1.0094 instead of 1.0, and the required track length scales with the SQUARE of that factor.

  N=28  sr0=0.046618  DSR today 0.9490  needs 3,786 days  -> 42 forward days
  N=29  sr0=0.046950  DSR today 0.9469  needs 3,881 days  -> 137 forward days   (C-019 said 76.7)
  N=30  sr0=0.047269  DSR today 0.9448  needs 3,976 days  -> 232 forward days
  N=31  sr0=0.047577  DSR today 0.9427  needs 4,071 days  -> 327 forward days
  N=32  sr0=0.047873  DSR today 0.9406  needs 4,165 days  -> 421 forward days

TWO CONSEQUENCES.

1. The one-trial bookkeeping margin has CLOSED. C-019 said H-201's DSR held to N=28 against 29 declared. With the corrected denominator it is 0.9490 AT N=28, so the cell clears only at N<=27. The declared count today is 30-31, because H-234, H-235 and H-236 were all filed today. So the honest position is not "one trial short" and not "77 days short": it is THREE OR FOUR TRIALS SHORT plus 137-327 forward days.

2. The pod's 20-day gate is NOT a significance gate. At +77 days the corrected DSR would be 0.9487 (N=29), 0.9466 (N=30), 0.9445 (N=31) - all still below 0.95. When that gate completes in 5 more sessions, report it as a sanity check on the forward clock, not as a pass.

THE STRUCTURAL POINT, which is the real lesson of today. H-234, H-235 and H-236 each ADDED A TRIAL to the same family. H-234 earned its place (it converted a near-miss into a period-stable result), but between them they moved H-201 from "one trial short" to "three or four short" and pushed the required forward clock from 76.7 to 137-327 days. That is how a programme tests its best idea out of existence: not by finding it false, but by paying for the search with the thing being searched for. If you are about to add a trial to a family that already has a candidate near the boundary, price it first - the cost is not zero and it lands on the candidate, not on you.

POD FORWARD CLOCK STATUS (ran it against the latest available bar just now):
  rows(n_days)=15, 2026-11-02..2026-11-20, sum port -812.109 bp, rf +24.290 bp, EXCESS -836.399 bp
  20-day gate: 15/20, five more sessions
  Data ends 2026-11-20 (SPY's last bar), so no new row can be written yet - the clock is data-bound, not code-bound.
  Verdict remains NO_VERDICT_TOO_FEW_DAYS_FOR_INFERENCE, capped at CANDIDATE_SURVIVORSHIP_FLAGGED by the PARTIAL_NON_DELISTING_AWARE universe.

So the programme's best cell is currently: period-stable in-sample (H-234), breadth-neutral in effect size (H-236), and LOSING forward at -836 bp excess over 15 days, while sitting 3-4 trials and 137-327 days short of a DSR pass. That is not an edge yet, and I would rather say so plainly than round it up.

If you have quoted "77 more days" from me or from C-019, replace it with the table above.
