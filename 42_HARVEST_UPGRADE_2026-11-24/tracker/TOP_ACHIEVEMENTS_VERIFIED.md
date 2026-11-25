# Top achievements of the programme, independently verified

Written 2026-11-25T15:41Z. Every entry below was enumerated from artifacts on `origin/main`
(`2d84166f2a9397ec6f0fce168cc2977904ab7ee1`) using `git show`/`git ls-tree` only. The live
site was not read, and no draft by kilo or anyone else was opened while compiling this list.

**Verification rule used here.** `VERIFIED` means the artifact is on `origin/main` and the stated
number can be read out of it. `UNSUPPORTED` means the claim is commonly made but no artifact on
`origin/main` carries the number. An artifact that exists only in a local worktree or on a side
branch is treated as `UNSUPPORTED` for this purpose, and the entry says so.

Line numbers (`:NN`) are given where I read them; binary or generated JSON is cited by path and
by the field name that holds the number.

---

## A. Achievements that hold up

1. **Claim: a multi-asset evidence ledger exists over 8,991 scored closed picks, with zero proven cells.**
   - Artifact: `audit_dashboard/data/audit3_ledger.json` (`schema: audit3.v1`, `generated_at 2026-11-25T06:39:03Z`)
   - Number: `summary.n_rows = 8991`, `summary.n_cells_tested = 67`, `summary.n_proven = 0`, `summary.n_kill = 7`, `summary.n_weak = 60`
   - **VERIFIED**

2. **Claim: the scored denominator is reconciled to a single canonical hash rather than drifting between pages.**
   - Artifact: `audit_dashboard/data/denominator.json` (`schema: audit.denominator.v1`)
   - Number: `n_canonical = 8991`, `n_total_closed = 15110`, `complete = true`, `canonical_sha256` prefix `f2ab4924dd2b`
   - Cross-check: the same hash `f2ab4924…` appears in `audit3_ledger.json` `coverage.denominator.canonical_rows_sha256`
   - **VERIFIED**

3. **Claim: the 8,991 rows are 100% of valid closed picks, and the 41% shortfall is unscored rows that are named and accounted for.**
   - Artifact: `audit_dashboard/data/audit3_ledger.json` `coverage`
   - Number: `scored_share_of_valid_pct = 100.0`, `scored_share_of_total_pct = 59.5`; excluded-by-reason counts `invalid_row 5924`, `mirror_duplicate 101`, `non_performance_exit 43`, `resolver_breakeven_fallback 51` (5924+101+43+51 = 6119 = `15110 − 8991`)
   - **VERIFIED**

4. **Claim: selection alpha is negative and significant: the picks lost to buy-and-hold.**
   - Artifact: `audit_dashboard/data/audit3_ledger.json` `selection_alpha.overall`
   - Number: `alpha_pct = -0.2863`, `alpha_ci = [-0.4962, -0.0782]` (CI entirely below zero), `n = 3131` of `n_universe = 3500`
   - **VERIFIED**

5. **Claim: the forward gate is enforced and keyed to a fingerprinted ledger.**
   - Artifact: `audit_dashboard/data/audit3_ledger.json` `forward_gate`
   - Number: `enforced = true`, `n_rows = 453`, `fingerprint = 8aaa718c1c226e78`, `read_errors = []`; the same `453` rows are `reports/forward_observations.jsonl` (453 lines)
   - **VERIFIED**

6. **Claim: verdict churn is tracked and low, so the verdicts are not noise.**
   - Artifact: `audit_dashboard/data/audit3_ledger.json` `verdict_churn`
   - Number: `n_tracked = 451`, `n_flipped = 1`, `churn_rate = 0.0022` against `alert_threshold = 0.3`, `alert = false`
   - **VERIFIED**

7. **Claim: 170 strategy ledgers were benchmarked with a paired bootstrap and a random-entry Monte-Carlo timing null, and almost nothing survived it.**
   - Artifact: `audit_dashboard/data/benchmark_ledger_proof.json` (`summary`, `n_boot = 10000`, `n_perm = 10000`, `seed = 42`)
   - Number: `n_ledgers = 170`, `n_full_proof = 67`, `n_pass_95 = 4`, `n_mc_top_decile = 9`
   - **VERIFIED**

8. **Claim: that benchmark module is covered by a deterministic test suite of the documented size.**
   - Artifact: `tests/test_benchmark_closed_ledger.py`
   - Number: 33 `def test_` functions (the "33 deterministic tests" figure is true)
   - **VERIFIED**

9. **Claim: the programme's own headline answer is "nothing makes money net of cost", and it is the same tally in three separate documents.**
   - Artifact: `docs/edge_research/23_DEFINITIVE_ANSWER_2026-11-22.md:195`, `docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md:177`, `docs/edge_research/28_PROGRAMME_STATUS_INDEX_2026-11-23.md:7`
   - Number: `TALLY: 0 INVESTABLE / 11 NOT_INVESTABLE / 3 UNKNOWN (14 rows)` in all three; `:39` says "0 of 14 rows is investable … 11 are killed, and 3 are still open"
   - **VERIFIED**

10. **Claim: nine strategies were tested in the first round and none cleared the hurdle.**
    - Artifact: `docs/edge_research/15_PROGRAMME_SCOREBOARD_2026-11-22.md:14`
    - Number: "Nine strategies were tested. One survived (MARGINAL). Seven were killed. One was blocked on data." followed by "Nothing cleared the hurdle."
    - **VERIFIED**

11. **Claim: the money-ready verdict gate has never returned READY for any asset class.**
    - Artifact: `audit_dashboard/data/money_ready_archive/` (190 daily files, `index.json` spans 2026-05-17 … 2026-11-25)
    - Number: `"verdict": "READY"` occurs **0** times; `NOT_READY` occurs 543 times; the latest file `money_ready_2026-11-25.json` has 0 READY across 11 classes (4 `NOT_READY`, 7 `INSUFFICIENT_DATA`)
    - **VERIFIED** (this is a verified negative result: no "money-ready" achievement exists to claim)

12. A tally-consistency test guards that claim, so the number cannot silently drift.
    - Artifact: `tests/test_edge_research_tally_consistency.py`
    - Number: 9 `def test_` functions, per `:139` and `:168`
    - **VERIFIED** (that the test exists and is on main; I did not run it in this session)

13. **Claim: a deliberately adversarial external review of the audit surfaces has been done, with the blemishes written down rather than suppressed.**
    - Artifact: `docs/audit_review_2026-11-22/README.md` + `_MANIFEST.json` (`frozen_at_utc 2026-11-22T06:39:03Z`, `captured_by "Phase 0 Measurer (curl + sha256, no inference)"`)
    - Number: three P0s stated (P0-1 selection alpha −0.3696 pct per trade, CI [−0.5673, −0.1674]; P0-2 stale/broken data paths; P0-3 verdict labels at n 0 / n 2 / n 4). The manifest records `not_found` HTTP 404s and byte-identical `consistency_checks`.
    - **VERIFIED** as an artifact; note the P0-1 figure here (−0.3696) differs from the current ledger's −0.2863 in entry 4 because the review is a frozen 2026-11-22 snapshot. Both are honest for their date; do not quote them as the same measurement.

14. **Claim: measured round-trip cost spreads exist for ETF/INDEX/MEME from real intraday bars, with the upper-bound caveat and the commission gap stated.**
    - Artifact: `reports/equity_cost_measurement/class_cost_20261122.json` (`generated_utc 2026-11-22T22:59:06Z`, yfinance 1-min bars 2026-11-16..20)
    - Number: ETF median-of-medians **6.7122 bp** RT over 14 names; INDEX (alias of ETF) **8.0325 bp** over 4; MEME **3.3969 bp** over 3; PENNY_STOCK 0 names; `commission.status = COMMISSION_UNKNOWN`
    - **VERIFIED** as an upper bound only. The file itself says "This is an UPPER BOUND, not the NBBO."

15. **Claim: the repository has a long-running automation fleet.**
    - Artifact: `.github/workflows/` on `origin/main`
    - Number: 379 workflow `.yml` files
    - **VERIFIED**

16. **Claim: a health audit of that fleet was run over the last eight days, and it reports the bad news as well as the good.**
    - Artifact: `GHACTIONS_LIVE/gha_health.json` (`generated_at 2026-11-25T12:53:07Z`, window 2026-11-17 → 2026-11-25)
    - Number: `runs_scanned = 1000`, `workflows_scanned = 386`; rule R1 lists failing workflows with `class: "broken"`
    - **VERIFIED** (that the audit ran and its counts). The audit is not evidence that the fleet is healthy: it finds broken workflows.

17. **Claim: a static quality framework scores the workflows.**
    - Artifact: `GHACTIONS_LIVE/gha_quality.md`
    - Number: 375 workflows scanned (1 parse error), aggregate score 94.4/100, **103 blocking violations**, including 21 `Q5 duplicate-producer` (P0) and 40 `Q7 silent-failure` (P0)
    - **VERIFIED**. The "94.4/100" is a score, not a pass: 103 blocking violations is the number that matters.

18. **Claim: a paper-trading pilot exists across many strategies with real logged rows.**
    - Artifact: `verified_strategies/paper_pilot/*_paper_log.jsonl` (11 logs)
    - Number: 418 total rows (largest: `prediction_market_consensus` 110, `equity_pead_drift` 76, `mega_mutation` 63, `macd_rsi_m048` 62)
    - **VERIFIED** that the logs and rows exist. The row count is small; see entry 31 on profitability.

19. **Claim: forward observations are recorded as a machine-readable ledger.**
    - Artifact: `reports/forward_observations.jsonl`
    - Number: 453 lines
    - **VERIFIED** (count only; this proves the ledger exists, not that it holds an edge)

20. **Claim: the programme is large and has a long documented history.**
    - Artifacts: `updates/` and `docs/` on `origin/main`
    - Number: 1,066 `.md` fix notes under `updates/`; 1,285 files under `docs/`
    - **VERIFIED** as activity. Volume is not achievement: see entries 26 and 27.

---

## B. Commonly claimed achievements that are UNSUPPORTED on `origin/main`

These are the most useful entries. Each is a claim a reader might reasonably assume is proven, with no artifact on `origin/main` behind it.

21. **Claim: "the cost measurements are committed, so the programme's cost basis is reproducible."**
    - Artifact searched: `reports/cost_measurement_20261122.json`, `reports/cost_measurement_forex/FOREX_COST_20261122.md`
    - Number: neither is on `origin/main`. The only provenance is the commit message `87a2e0cbe2f`, which is not on main.
    - **UNSUPPORTED**. Both files are present in a local worktree but were never merged into main.

22. **Claim: "the 14-row tally is backed by the per-strategy machine-readable reports it cites."**
    - Artifact searched: `reports/programme_scoreboard_20261122.json`, `reports/verification_20261122.json`, `reports/funding_carry_20261122.json`, `reports/fx_carry_20261122.json`, `reports/cross_venue_basis_20261122.json`, `reports/momentum_12_1_20261122.json`, `reports/crypto_meanrev_intraday_20261122.json`, `reports/commodity_momentum_20261122.json`, `reports/bond_momentum_20261122.json`, `reports/forex_carry_trend_20261122.json`, `reports/low_turnover_20261122.json`, `reports/no_trade_counterfactual_20261122.json`
    - Number: **all 12 are absent from `origin/main`**. The tally (entry 9) is verifiable as a *statement*; its underlying JSON is not.
    - **UNSUPPORTED**. The documents are on main; the data behind them is not.

23. **Claim: "the second-round class-cost corrections are in the repo."**
    - Artifact searched: `reports/cost_measurement_new_classes/class_cost_new_20261123.json`
    - Number: the directory does not exist on `origin/main`.
    - **UNSUPPORTED**, even though `docs/edge_research/22_FINAL_SYNTHESIS_2026-11-22.md` cites it inline as the source for the BOND 1.2125 bp and COMMODITY 6.3182 bp corrections.

24. **Claim: "the edge screen was run over 22,219 rows and 25 cells."**
    - Artifact: `docs/audit_review_2026-11-22/EDGE_SCREEN_RESULT.md` (on main)
    - Number: the doc states 22,219 rows, 25 cells, and cites `reports/edge_screen_20261122.{json,md}` as its output; **both files are absent from `origin/main`.**
    - **UNSUPPORTED** as a reproducible result. The narrative is on main; its output artifacts are not.

25. **Claim: "the edge-research document set is complete and self-contained."**
    - Artifact: `docs/edge_research/`
    - Number: 9 files on `origin/main`, but the local set is 42. Docs 22, 23 and 28 cite files that are **not on main**: `07_HURDLE_RATES`, `03_P0_FORWARD_CLOCK_STRUCTURAL_BLOCK`, `05_REAL_COST_MEASUREMENT`, `10_SURVIVORSHIP_AUDIT`, `19_HONEST_VERDICT`, `21_VERIFICATION_AND_CI_GUARD`, `14_CRYPTO_INTRADAY_MEANREV`, `18_CAPACITY_COMBINED_BOOK_COUNTERFACTUAL` (all `_2026-11-22.md`).
    - **UNSUPPORTED**. The register on main is a subset of the documents it references.

26. **Claim: "the programme found an edge."**
    - Artifacts: `audit3_ledger.json`, `benchmark_ledger_proof.json`, `money_ready_archive/`, `docs/edge_research/23…`
    - Number: `n_proven = 0`; `n_pass_95 = 4` of 170; 0 READY verdicts ever; `0 INVESTABLE` of 14.
    - **UNSUPPORTED.** Every artifact that could carry this claim says the opposite. The strongest candidate on record (`mega_mutation`/CRYPTO, WR 66.96%, net PF 3.33 in `EDGE_SCREEN_RESULT.md`) is labelled "a lead, not a result" and is stale since 2026-06-11.

27. **Claim: "the paper-trading pilot is profitable."**
    - Artifact: `verified_strategies/paper_pilot/*_paper_log.jsonl`
    - Number: only 132 of 418 rows carry a numeric `pnl_pct`. Of 11 logs, 6 have no numeric pnl at all (`equity_pead_drift` 76 rows, `equity_vix_regime_rotator` 49, `macd_rsi_m048` 62, `mega_mutation` 63, …). The sums are dominated by one strategy: `prediction_market_consensus` +258.604 of 110 rows, while `faber_taa` is −6.5724. Excluding that one strategy the net is negative.
    - **UNSUPPORTED.** Sample sizes are far below any promotion threshold, and half the logs are unmeasured.

28. **Claim: "the benchmark proof passes the timing test."**
    - Artifact: `audit_dashboard/data/benchmark_ledger_proof.json`
    - Number: `n_ledgers = 170` but `n_pass_95 = 4` and `n_mc_top_decile = 9`; the first ledger's `random_entry_mc.percentile = 0.5682` (coin flip) with `paired_bootstrap.frac_positive = 0.521`, `pass_95 = false`.
    - **UNSUPPORTED.** The artifact proves the *method* (entry 7), not a timing edge.

29. **Claim: "the GHA quality workflow runs in CI with a baseline gate."**
    - Artifact searched: `.github/workflows/gha-quality-framework.yml`, `GHACTIONS_LIVE/gha_quality_baseline.json`
    - Number: both are absent from `origin/main`. `GHACTIONS_LIVE/` contains exactly 3 files (`gha_health.json`, `gha_health_summary.md`, `gha_quality.md`).
    - **UNSUPPORTED** as "wired in CI". `tools/gha_quality_framework.py` is on main and `gha_quality.md` is on main, so the *framework* and one *run output* are real (entry 17); the workflow and baseline gate are not on main.

30. **Claim: "the audit-review document lint gate runs in CI."**
    - Artifact searched: `.github/workflows/audit-review-doc-lint.yml`, `tools/test_doc_source_lint.py`
    - Number: both absent from `origin/main` (`tools/doc_source_lint.py` is present).
    - **UNSUPPORTED** as "gated in CI".

31. **Claim: "the 12 asset-class dossiers are exactly the 12 classes."**
    - Artifact: `docs/audit_review_2026-11-22/`
    - Number: `README.md:8` says "`01_CRYPTO.md` … `12_SPORTS.md` - twelve class dossiers", but 14 numbered documents exist (`01`…`13_PREDICTION_MARKET.md` plus `BLOCKERS`, `CLASS_INDEX`, `CROSSCHECK_MATRIX`, …). The 13th class, PREDICTION_MARKET, appears in the README's own verdict table.
    - **UNSUPPORTED** as stated. The work is larger than the claim, but the claim as written is wrong about its own artifact.

32. **Claim: "the programme is profitable on crypto" (the 3,733-row CRYPTO book).**
    - Artifact: `audit_dashboard/data/money_ready_archive/money_ready_2026-11-25.json` `classes.CRYPTO`
    - Number: `verdict = NOT_READY`, `n_resolved = 3733`, `wr = 0.408`, `pf = 0.2617`
    - **UNSUPPORTED.** The largest book in the system has a profit factor of 0.26.

33. **Claim: "the forward clock is accumulating forward evidence."**
    - Artifact: `audit_dashboard/data/forward_clock.json`
    - Number: `generated_utc 2026-11-25T08:54:16Z`, `ledger_rows = 0`; `FABER10_SPY` shows `trades = 0`, `windows = 0`, `note "0 trades in 10d"`
    - **UNSUPPORTED.** The clock exists (VERIFIED as an artifact) but has zero ledger rows. The 453 forward observations in entry 19 live in a different ledger, so do not merge the two counts.

---

## C. What this list says about the programme

Only one of the 33 entries above is a positive performance claim, and it is not supported: no artifact on `origin/main` shows a strategy beating its hurdle after cost. What is verifiably achieved is **rigour**: a canonical denominator with a hash, a ledger that names its own exclusions, a benchmark null that most ledgers fail, a money-ready gate that has never said READY, and an external review that publishes its own P0s. That is a real achievement and a different one from profitability. Any summary that reports "N strategies validated" or "money-ready" without naming one of these artifacts should be treated as unsupported until it does.
