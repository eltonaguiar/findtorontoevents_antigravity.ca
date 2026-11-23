# 2026-11-23 — Blocker: `tools.fx_meanrev_research` is missing on `main`

**Status:** known, already-diagnosed dependency gap. Recorded, not fixed. Informational only.
**Programme surface:** the FX cost-overlap measurement job
[`.github/workflows/fx-cost-overlap.yml`](.github/workflows/fx-cost-overlap.yml) and the tool it runs,
[`tools/fx_cost_sampler.py`](tools/fx_cost_sampler.py).

---

## 1. What is blocked

The FX cost-overlap job's **optional chained strategy re-run** — the FX mean-reversion re-run that
the sampler would perform at the freshly measured cost.

The exact import on `main`:

```
tools/fx_cost_sampler.py:379:    from tools.fx_meanrev_research import run as run_meanrev
```

It lives inside [`run_strategy_chain()`](tools/fx_cost_sampler.py:377) (defined at line 377). The
module [`tools/fx_meanrev_research.py`](tools/fx_meanrev_research.py) **does not exist on `main`**
(proven in §6). When the import is reached, `ModuleNotFoundError` is raised, caught by the
`try/except Exception` at lines 612-615, and recorded as
`{"state": "CHAIN_FAILED", "error": "..."}` at line 615.

## 2. What is NOT blocked

- **The cost measurement itself.** It is produced by the sampling/classification path that runs
  before the chain ([`status` is set at line 607](tools/fx_cost_sampler.py:607)) and is unaffected by
  the import.
- **The artifact write.** `out_json` / `out_md` are written at lines
  [697-698](tools/fx_cost_sampler.py:697), after the chain block, regardless of the chain's state.
  The artifact carries the measured cost and `"strategy_chain": chain` ([line 653](tools/fx_cost_sampler.py:653)).
- **The six crons.** They are listed at
  [`fx-cost-overlap.yml:38-43`](.github/workflows/fx-cost-overlap.yml:38) and are untouched.
- **The workflow itself.** No step fails on a `CHAIN_FAILED` chain; the sampler exits 0.
- **The verdict path.** [`guard_verdict()`](tools/fx_cost_sampler.py:450) is **allowlist-bound** and
  **cannot emit `INVESTABLE`**: the allowlist at
  [lines 74-79](tools/fx_cost_sampler.py:74) contains only `NOT_INVESTABLE`, `HUMAN_REVIEW_REQUIRED`,
  `BLOCKED_NO_REPRESENTATIVE_SESSION`, `UNCHANGED_UNKNOWN`, and
  [`guard_verdict()` raises RuntimeError if handed `INVESTABLE`](tools/fx_cost_sampler.py:453).
  When the chain is not `RAN`, [`decide_strategy_verdict()`](tools/fx_cost_sampler.py:412) returns
  `UNCHANGED_UNKNOWN` ([lines 420-425](tools/fx_cost_sampler.py:420)) with `verdict_changed: False`.
  **No verdict is moved by this blocker.**

## 3. Why it was not fixed

The module exists only on branches this programme **refused to merge**, because merging one of them
would have imported **862 files** and produced **18 conflicts** `[SRC: brief/ESTABLISHED_FACTS]` —
far beyond activating one measurement. Pulling a single tool out of that branch to paper over a
`CHAIN_FAILED` would be a **second unauthorised scope expansion**, and it would silently depend on
code that has **never been reviewed under this programme's tests**. Recording an honest failure is
strictly better than an unreviewed import.

## 4. Exact reopen requirement

All of the following must hold before this blocker is closed:

- **(a)** `tools/fx_meanrev_research.py` is a reviewed, tested, **standalone** commit on `main`, with
  its own tests that run in this programme's suite.
- **(b)** The sampler's docstring records the expected signature of `run(...)` and its return
  contract (the keys `run_strategy_chain()` consumes: `universes.primary.stats.mean_gross_bp`,
  `ci95_net_bp_window_clustered`, `mean_net_bp`, `mean_net_bp_2x`, `ci95_net_bp`, plus the top-level
  `verdict` / `gates` read at [lines 404-405](tools/fx_cost_sampler.py:404)).
- **(c)** `python3 tools/fx_cost_sampler.py --self-test` still exits 0
  ([self-test is invoked at line 826](tools/fx_cost_sampler.py:826)).
- **(d)** A `--dry-run` chain path exercises the import **without network** and reports `RAN` (or a
  named, expected non-`RAN` state) instead of `CHAIN_FAILED`.
- **(e)** The maintainer of that module is named in the commit that lands (a).

## 5. Observable symptom when the blocker bites

The chain's state is written to **two** places, and only one of them is a log:

- **Artifact (the reliable place):** the JSON's `strategy_chain.state` is `CHAIN_FAILED` with an
  `error` string, and the rendered Markdown under `## Chained FX mean-reversion re-run` shows
  `- not run: \`CHAIN_FAILED\` (...)` ([lines 515-520](tools/fx_cost_sampler.py:515)).
- **Job stdout:** the sampler itself does **not** print the chain state; the workflow's "Show verdict"
  step prints only status, decision cost and the strategy verdict
  ([`fx-cost-overlap.yml:91-104`](.github/workflows/fx-cost-overlap.yml:91)). So a literal
  `CHAIN_FAILED` line in the *job log* is not guaranteed.

How to tell it apart from a genuine failure:

- The cost artifact is **still written and non-empty**, and `aggregate.decision_cost_bp` is populated.
- `strategy_decision.strategy_verdict` is **not** `INVESTABLE` (it is `UNCHANGED_UNKNOWN` on a
  `CHAIN_FAILED` chain).
- The job **exits 0**; the sampler is even allowed to exit non-zero without failing the job
  ([`fx-cost-overlap.yml:86-89`](.github/workflows/fx-cost-overlap.yml:86)).

## 6. Verification performed

All line numbers are from the version **on `main`**, not the working tree.

```text
$ git show origin/main:.github/workflows/fx-cost-overlap.yml | grep -n "cron:"
38:    - cron: '48 13 * * 1-5'
39:    - cron: '56 13 * * 1-5'
40:    - cron: '52 14 * * 1-5'
41:    - cron: '57 14 * * 1-5'
42:    - cron: '54 15 * * 1-5'
43:    - cron: '58 15 * * 1-5'

$ ... | grep -n "TIINGO_API_KEY"
21:#    secret TIINGO_API_KEY (same one etf-spread-series / stocks-daily use).
79:          TIINGO_API_KEY: ${{ secrets.TIINGO_API_KEY }}

$ git show origin/main:tools/fx_cost_sampler.py > /tmp/fxcs.py   # exit 0, 836 lines
$ grep -n "fx_meanrev_research" /tmp/fxcs.py
379:    from tools.fx_meanrev_research import run as run_meanrev
387:        "module": "tools/fx_meanrev_research.py",
$ grep -n "run_strategy_chain" /tmp/fxcs.py
377:def run_strategy_chain(cost_bp: float, shuffles: int, seed: int) -> dict:
613:            chain = run_strategy_chain(agg["decision_cost_bp"], args.chain_shuffles, args.seed)
$ grep -n "CHAIN_FAILED" /tmp/fxcs.py
615:            chain = {"state": "CHAIN_FAILED", "error": repr(exc)}
$ grep -n -- "--no-chain" /tmp/fxcs.py
611:    if status == "MEASURED_REPRESENTATIVE" and not args.no_chain and not args.dry_run:
616:    elif args.no_chain:
819:    ap.add_argument("--no-chain", action="store_true",
$ grep -n -- "--dry-run" /tmp/fxcs.py
817:    ap.add_argument("--dry-run", action="store_true",
   (plus uses at 565, 591, 595, 611, 673, 684)
$ grep -n "MEASURED_REPRESENTATIVE" /tmp/fxcs.py
607:        status, block_reason = "MEASURED_REPRESENTATIVE", None
   (plus uses at 25, 414, 611, 678)

$ git cat-file -e origin/main:tools/fx_meanrev_research.py; echo "exit=$?"
fatal: path 'tools/fx_meanrev_research.py' exists on disk, but not in 'origin/main'
exit=128

$ git log --all --oneline -- tools/fx_meanrev_research.py | head -20
991bec31e15 research(block2): FX mean-reversion KILL - real reversal effect (100th pct null, p=0.001) but gross +4.3bp vs 10bp cost; ...

$ git branch -a --contains 991bec31e15
  block-d-session-record-2026-11-22
  closing-edge-programme-2026-11-22
  ... (16 local branches) ...
  remotes/origin/push/m2-forex-cost-2026-11-22
  remotes/origin/research/edge-candidates-2026-11-22
  ... (14 remote branches) ...

$ ls -la tools/fx_meanrev_research.py
-rw-rw-r-- 1 eaguiar2015 eaguiar2015 21120 Nov 22 09:23 tools/fx_meanrev_research.py
$ git ls-files --error-unmatch tools/fx_meanrev_research.py   # exit 0 → TRACKED
tools/fx_meanrev_research.py
```

The branches that contain the introducing commit were **not** checked out and **not** merged.

## 7. Provenance

- Sampler line numbers come from `git show origin/main:tools/fx_cost_sampler.py` (836 lines), grepped as shown in §6. `[SRC: tools/fx_cost_sampler.py:379]` `[SRC: tools/fx_cost_sampler.py:377]` `[SRC: tools/fx_cost_sampler.py:611]` `[SRC: tools/fx_cost_sampler.py:615]` `[SRC: tools/fx_cost_sampler.py:450]` `[SRC: tools/fx_cost_sampler.py:74]`
- Workflow line numbers come from `git show origin/main:.github/workflows/fx-cost-overlap.yml` (116 lines). `[SRC: .github/workflows/fx-cost-overlap.yml:38]` `[SRC: .github/workflows/fx-cost-overlap.yml:79]`
- The **862 files / 18 conflicts** figures are the programme's recorded rationale for refusing the merge, carried from the task's established facts; they were not re-derived here. `[SRC: brief/ESTABLISHED_FACTS]` for the figures; the *refusal* itself is reproducible from the branch list in §6.
- The introducing commit `991bec31e15` and the containing-branch list are from `git log --all` / `git branch -a --contains` on this clone. `[SRC: git:991bec31e15]`
- The local presence of the module (tracked in local `HEAD`, absent from `origin/main`) is from `ls -la` + `git ls-files --error-unmatch` + `git cat-file -e origin/main:...`. `[SRC: git:local-head]`
- **No number in this document is `UNMEASURED`**: every figure is either a grep-verified line number or a figure explicitly attributed above.
