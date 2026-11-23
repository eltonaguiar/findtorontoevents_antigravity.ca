# H-236: the momentum effect size is universe-insensitive, the certification is not; and two sweep errors of mine

**Date:** 2026-11-23 · **Owner:** buffy (freebuff) · **Paper only, zero capital, not advice**

## H-236 result — `REFUTED` on the pre-registered criterion

Pre-registered (`plans/2026-11-23-prereg-H-236-h201-pit-universe.md`), same rule as H-234
(`xsmom(126, 3, 10bp, 21d)`), on the 44-name PIT universe over the artifact's own window, with the
10 mega caps run over the **identical** window for comparison.

| book | symbols | n | mean net | 95% CI | excess vs SPY | passes |
|---|---|---|---|---|---|---|
| PIT_44 | 44 | 1,254 | **+9.407 bp** | [−3.147, +22.199] | +4.901 | **no** |
| MEGA_10 (same window) | 10 | 1,254 | **+9.540 bp** | [+1.072, +18.428] | +5.033 | yes |

The point estimates are **within 0.13 bp of each other**. Breadth does not move the effect; it moves
the *interval*. A top-3 portfolio drawn from 44 names is far more dispersed than one drawn from 10
mega caps, so its CI is roughly 2.5x wider, and a 5-year window cannot certify it.

**What this does and does not establish.** It bounds H-234's universe dependence: the effect is not
a mega-cap artefact, because it shows up at almost exactly the same size on a 9x wider universe. It
does **not** certify H-201 on a wide universe, and the label stays `REFUTED` because the CI criterion
was written before the run and it failed. Relabelling it "supported" would be exactly the move this
programme keeps having to withdraw.

## Two errors in my own evidence-path sweep

The first version reported **58 of 68 missing**. Both numbers were wrong:

1. **v1 — fragments treated as paths.** Entries like `reports/foo.json#e2_vol_scaling` are file plus
   JSON pointer, so the whole string never exists. 52 of the 58 were false positives.
2. **v2 — searched the wrong trees.** It checked main and `/tmp/cv` only. Six files
   (`reports/horizon_backtest_2026-11-22.json`, `reports/2026-11-22-horizon-allocation-review.md`,
   `tools/horizon_backtest.py`, and others) live on **PR #1067's** worktree `/tmp/prmain`, so
   "genuinely missing" — which I published to COMS — was wrong.
3. **v3 (correct)** checks main plus both worktrees: **15 resolve on main, 55 exist only on unmerged
   branches, 2 are COMS topics, 0 genuinely missing.**

**The real finding is the v3 one and it matters more than the false alarm:** 81% of the claim
register's evidence is not on main. Those claims are unreproducible for anyone reading main, which is
where a claim is normally read. The fix is a merge decision, not a rebuild.

I also copied those 55 files into the working tree to make paths resolve, then **removed them again**:
they came from branches carrying other agents' commits, and AGENTS.md forbids pushing files I did not
create. Copying them would have smuggled 55 foreign files into a push branch. Reported instead of
smuggled.

## Verification

- `tools/h236_h201_pit_universe.py` → exit 0, `VERDICT: REFUTED`, wrote
  `reports/h236_h201_pit_universe_2026-11-23.json`.
- Sweep v3 written to `reports/evidence_path_sweep_2026-11-23.json` with all three correction notes.
- Registry re-parsed: `H-236` present once, status `REFUTED`. Claim register re-parsed: `C-028` once.
- The 55 copied files were removed; `git status` for `reports/` shows no leftover copies.

## Limitations

- H-236's window is 5 years and the PIT artifact is `PARTIAL_NON_DELISTING_AWARE`, so a pass would
  not have been survivorship-free either.
- Costs modelled at 10 bp/unit, not measured.
- H-236 adds a trial; the deflation bar moves again.
