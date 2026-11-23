# 2026-11-23 — H-242 deflated Sharpe, cost-of-record + ETF replication, audit2 Graveyard and prereg hashes

## What was asked

Four things in one round: compute H-242's deflated Sharpe at the raised trial count and say whether it
clears 0.95; re-run H-242's rule at the reconciled 4.01 bp cost and on the ETF universe; add the
Graveyard panel and the published pre-registration hash to audit2; and check COMS.

## Results

| question | answer |
|---|---|
| Does H-242 clear DSR 0.95? | **No.** 0.687 at N=121 (canonical cross-trial σ), 0.799 under the SE convention, and 0.922 at best anywhere (N=26, permissive basis). Fails at every trial count in the reconciled range. |
| Does the pass survive the record cost? | **Yes** — H-243: 16.598 bp/day, CI [8.033, 25.317] at 4.0124 bp RT, versus 16.345 at 10 bp/side. The saving is **0.252 bp/day** at ≈7.9× notional turnover per year. |
| Is the effect US-equity-specific? | **No** — H-244: 10-ETF universe gives 5.581 bp/day, CI [1.134, 10.239] over the same decade. Same sign, about one third the magnitude. |

## The two things worth keeping

1. **The cost argument is now quantitatively dead.** Halving the round trip from 20 bp to 4 bp moves
   the mean by 0.25 bp/day — 1.5%. Anyone still arguing "the edge dies on costs" is arguing about
   0.25 bp/day.
2. **Multiplicity is the only live objection, and it is not close.** At N=121 the expected maximum
   daily Sharpe from zero-skill trials is 0.0592; the book delivers 0.0690. It clears 17% of the
   hurdle. The CI gate and the DSR gate are not contradicting each other — they answer different
   questions, and the programme has now spent enough trials that the second question dominates.

## Honesty notes

- **Two σ scales exist in this repo and they are not the same object.** Cross-trial scatter is
  0.022798 (`reports/dsr_multiplicity_2026-11-22.json`; `effective_trials_2026-11-22.json` agrees at
  0.022799). The SE-of-SR convention that `alpha_engine.deflated_sharpe` is fed is derived from the
  sample. They differ by up to 0.11 in DSR, so both are reported and neither is presented alone as
  "the" answer. This is the same ambiguity `reports/TRIAL_N_RECONCILIATION_2026-11-23.md` flagged for
  the programme's SR*.
- **A unit slip in my own run was caught and corrected before commit.** The implied-turnover field
  first printed `0.0x/yr` because I annualised a daily mean by dividing by n as well; the correct
  figure is 7.94×/yr, and the artifact now carries `turnover_note` recording the fix.
- **The earlier H-242 report said DSR "likely fails".** It is now a measured failure, and that section
  of the report has been corrected in place rather than left standing.

## audit2

- New **Graveyard** section: seven counted deaths, each with the number that killed it and the
  artifact it came from (top-gainer CRYPTO/EQUITY, H-242-as-candidate, the 80%→0.6% attribution
  claim, two 404 hub links, the 1.75%→1.5% FX correction).
- New **Pre-registration ledger**: sha256 of each plan file as filed before its run — H-239/240,
  H-241, H-242, H-243/244 — with the verdict alongside, and a note that a mismatch means the plan
  moved after the result.
- Both are static snapshots embedded in `audit2.js`, matching the existing pod-registry pattern,
  because `reports/` is not web-served. No new files, so no deploy-list change.

## Verification

- `node --check audit_dashboard/audit2.js` — clean.
- JSON validity for `reports/h242_dsr_2026-11-23.json`, `reports/h243_h244_cost_and_etf_2026-11-23.json`
  and the registry; H-243/H-244 statuses written from the measured verdicts.
- Embedded sha256 strings re-checked against `sha256sum` of the plan files at commit time.
- **Not run:** no browser render of audit2 (the page fetches a ledger sidecar that is not present in
  this clone, so the two new tables were verified structurally, not visually).

## COMS

Replied on `notes/freebuff-push-demand-sha-location-2026-11-23` to the demand that I push
`69cd7943ea7`: the commit is real, authored by `github-actions[bot]`, exists only on the local shared
branch `push/phase2-round-2026-11-22`, and GitHub returns 422 for it while that branch's remote tip is
a different commit. I declined to push it — it is not my commit, the branch is shared and explicitly
off-limits — and offered a clean single-author branch instead if the owner approves.
