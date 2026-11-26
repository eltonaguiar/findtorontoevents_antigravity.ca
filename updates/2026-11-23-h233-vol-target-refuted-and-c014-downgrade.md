# H-233 refuted: the vol-target 60/40 return gain does not replicate; the drawdown cut does

**Date:** 2026-11-23 · **Owner:** buffy (freebuff) · **Paper only, zero capital, not advice**

## What was broken

`reports/asset_class_risk_reward_ladder_2026-11-23.md` recommended volatility-targeted 60/40 as the
one "stable rung" a reader could hold today, on the strength of C-014: CAGR 7.85% → 9.28%, Sharpe
0.750 → 0.895, max DD −31.42% → −22.37%. Three defects made that unsafe as a recommendation:

1. **C-014 had `independent_runs: 0`.** One run, one window, no confidence interval, no disjoint
   replication, and it was being put forward as the *only* buyable result in the programme.
2. **The evidence script did not exist on main.** C-014 cites `tools/vol_target_vs_hold.py`; that
   path was absent from the tree, so the claim was not reproducible from main at all. It exists on
   the unmerged branch `research/commodity-tsmom-v3-2026-11-22` at `4daf025ed1d`.
3. **The granularity labels in the memo were wrong.** The −22.37%/−31.42% pair is the
   **monthly**-rebalanced basis, not the daily one. A daily reset gives −21.60%/−26.82%. The memo
   (and the C-020 summary it repeated) had daily and monthly the wrong way round.

## What I changed

- **Pre-registered H-233** before running anything (`plans/2026-11-23-prereg-H-233-vol-target-replication.md`,
  plus an entry in `reports/hypothesis_registry.json`), fixing the split, the statistic, the
  acceptance criteria and a kill rule in advance.
- **Wrote `tools/h233_vol_target_replication.py`**, reusing `vol_target()` and `perf()` from the
  original script so this is the same construction, not a reimplementation, and adding a paired
  **block** bootstrap (block 20) because vol clustering is the effect under test.
- **Restored `tools/vol_target_vs_hold.py` to main** from the unmerged branch, so C-014's cited
  evidence resolves.
- **Wrote `reports/h233_vol_target_replication_2026-11-23.json`** with both windows plus a
  full-sample reproduction diagnostic.
- **Downgraded the ladder memo's tier-0 recommendation** and corrected its granularity attribution.
- **Appended C-026** to `reports/claim_register.json` (append-only; C-014 itself is not edited).

## The measured result

Daily-rebalanced SPY 60 / TLT 40, 10% vol target, yesterday's 60-day realised vol, cap 2x, 5 bp per
unit turnover. Paired block bootstrap, 10,000 resamples.

| window | plain CE | VT CE | ΔCE | 95% CI | plain CAGR → VT | max DD plain → VT |
|---|---|---|---|---|---|---|
| A 2005-01-03..2015-12-31 | 6.70% | 9.07% | +2.3756pp | [−0.2182, +4.9008] | — | −26.82% → −21.60% |
| B 2016-01-01..2026-11-20 | 9.51% | 9.15% | **−0.3549pp** | [−3.3468, +2.6607] | 9.97% → 9.58% | −26.39% → −19.10% |
| FULL (diagnostic) | 8.09% | 9.11% | +1.0178pp | [−1.03, +2.999] | 8.43% → 9.54% | −26.82% → −21.60% |

Criteria: ΔCE positive in B — **FAIL**; CI lower bound > 0 — **FAIL**; max DD not worse — **PASS**;
sign agreement across windows — **FAIL**.

**Verdict: `REFUTED_OOS`**, which is the label the pre-registration reserved for exactly this
outcome. No post-hoc rescue: the monthly basis would have passed (+1.32pp) and switching to it was
excluded in writing before the run.

## What survives and what is withdrawn

- **Survives:** the drawdown reduction, in both windows, by 5.2pp and 7.3pp. That is a real risk
  effect and it is the only part of the claim that replicated on disjoint data.
- **Withdrawn:** "raises CAGR" and the +1.43pp tailwind. In the holdout window vol targeting
  *lowered* CAGR (9.97% → 9.58%) and lowered CE. The full-sample daily ΔCE CI contains zero, so even
  C-014's original point estimate was never statistically distinguishable from no effect.
- **Downgraded:** the ladder's tier 0 is now "risk control only — no demonstrated return gain".

## A defect found in my own tooling during the work, disclosed

The first registry append landed **outside** the `hypotheses` array (in a nested array), so
`json.load` succeeded and `grep` found `H-233` while the gate itself would never have seen it — it
looked filed and was not. My second repair attempt left a trailing comma and produced invalid JSON.
Both were caught by asserting `'H-233' in [h['id'] for h in d['hypotheses']]` after the write path
rather than trusting the grep. Final state verified: 117 hypotheses, `H-233` last, no duplicate ids,
file parses, single occurrence. Lesson: a pre-registration gate must be verified by parsing the
structure the gate reads, never by string presence.

## Verification actually run

- `python3 tools/h233_vol_target_replication.py` → exit 0, wrote
  `reports/h233_vol_target_replication_2026-11-23.json`, printed `VERDICT: REFUTED_OOS`.
- Registry re-parsed after edit: 117 hypotheses, `H-233` present once, status `REFUTED`, zero
  duplicate ids.
- Claim register re-parsed after append: `C-026` present once, no duplicate ids.
- Full-period reproduction run separately (in the worktree) matched the original artifact to 2dp on
  the monthly basis (7.84/10.87/0.749/−31.42/7.55 → 9.28/10.53/0.895/−22.37/8.87), which is how the
  granularity mislabel was found.

## Not verified / limitations

- The holdout is **not virgin**: C-014 already used 2005-2026 in aggregate, so this is a replication
  on a disjoint window, not true out-of-sample evidence. A forward clock is the only stronger test.
- Costs are 5 bp/unit turnover as modelled, not measured for this book.
- Two US funds only; no international replication, no pre-2005 window.
- The bootstrap assumes the block length (20 days) captures the dependence structure; not tested for
  sensitivity to that choice.
