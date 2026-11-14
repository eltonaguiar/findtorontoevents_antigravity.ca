# TODO — Find & prove a profitable approach (iterated)

Goal: either (a) find a strategy/cohort that PASSES the T2 charter with multiple-testing
correction (n≥100, PF≥1.5, WR≥50%, MDD<20%, z>1.96, edge persists out-of-sample), or
(b) prove with the same rigor that none exists in current data and specify the forward pilot
that could create one.

- [x] V0 baseline: 4 strategies have n≥100; zero pass n≥100 + PF>1.3 + z>1.96 (done)
- [x] V1 cell search: 8 source / 12 source×class / 26 strategy cells — NONE passed uncorrected z>1.96 (best z=1.45)
- [x] V2 split-sample: single-split p=0.006–0.038 across 3 split points; alive-filter variant FAILED (PF 0.80) → fragility noted
- [x] V3 cost: pnl already net of M-069 slippage; breakeven EXTRA cost margins: variant-C 0.416%/trade (healthy)
- [x] V4 walk-forward of the selection PROCEDURE: variant C n=237 PF 1.26 +98.7pp p<0.0013 (0/800 random), maxDD -64pp, 1/4-Kelly sizing computed
- [x] V5: 4 pre-specified variants tested & ALL reported (A/B/C/D table) — only C survives Bonferroni
- [ ] V6 deliver PROFITABLE_APPROACH_vN.md — proof or honest negative + forward pilot spec
