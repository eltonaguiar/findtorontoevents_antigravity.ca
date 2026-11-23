# FOREX cost-sampling cron pre-flight (weekday overlap)

**Date:** 2026-11-23 (written 03:0x UTC)
**Scope:** READ-ONLY diagnosis of `.github/workflows/fx-cost-overlap.yml` on `origin/main`.
**Base commit:** `2ea66184320dc70fd836e697a8619e61668c783a` (clean worktree at `/tmp/fxpreflight`).
**Nothing was modified, triggered, or posted.** No code, workflow, or branch changes for a fix.

Labels: **OBSERVED** = I ran the production invocation path and report real output/exit
codes. **CODE-READ** = traced by reading `origin/main` source (no network/API available
for that step).

---

## 1. Schedule and next fire

From [`.github/workflows/fx-cost-overlap.yml`](../../.github/workflows/fx-cost-overlap.yml) lines 34-43 (CODE-READ):

```yaml
  schedule:
    - cron: '48 13 * * 1-5'
    - cron: '56 13 * * 1-5'
    - cron: '52 14 * * 1-5'
    - cron: '57 14 * * 1-5'
    - cron: '54 15 * * 1-5'
    - cron: '58 15 * * 1-5'
```

Six weekday runs inside the London/NY overlap (13:00-16:00 UTC), two per hour at 13, 14, 15.

**Next fire: Mon 2026-11-23 ~13:48Z** (2026-11-23 is a Monday; the `:48 13` line fires first).
This is ~10h45m after this document was written. GitHub's scheduler is best-effort and can
delay runs by minutes under load, but the window is 13:00-16:00Z so a delay still lands in-session.

---

## 2. Call-order trace: sampling vs the strategy chain

All line numbers verified against `origin/main` @ `2ea66184` in `tools/fx_cost_sampler.py`.

| # | Where | What happens |
|---|-------|--------------|
| 1 | `fx_cost_sampler.py:557` | `run_overlap(args)` starts. |
| 2 | `:561` | `token = os.environ.get("TIINGO_API_KEY")` |
| 3 | `:565-572` | Gate: dry-run / off-session / no-token each print a reason and skip polling. |
| 4 | `:574-575` | **`sampled = sample_loop(...)`** - the spread sampling. `sample_loop` (`:183-252`) "never raises" by design (`:186`); API errors are recorded per-poll (`:206-214`). |
| 5 | `:577-583` | Samples -> `per_pair_stats` -> `classify` -> `aggregate`. |
| 6 | `:587-607` | Status decided (`MEASURED_REPRESENTATIVE` only if a representative pair exists). |
| 7 | `:610-617` | **Strategy chain** - only `if status == "MEASURED_REPRESENTATIVE" and not args.no_chain and not args.dry_run`. |
| 8 | `:612-613` | `chain = run_strategy_chain(agg["decision_cost_bp"], ...)`. |
| 9 | `:614-615` | `except Exception as exc: chain = {"state": "CHAIN_FAILED", "error": repr(exc)}`. |
| 10 | `:619` | `decision = guard_verdict(decide_strategy_verdict(status, chain))`. |
| 11 | `:625-670` | Payload assembled, including `"strategy_chain": chain` and the sampled aggregate. |
| 12 | `:684-699` | Artifact written (`out_json`, `out_md`, raw samples). |
| 13 | `:706-717` | Console summary printed; `return 0`. |

`run_strategy_chain` (`:377-409`) does `from tools.fx_meanrev_research import run as run_meanrev`
at `:379`. `tools/fx_meanrev_research.py` **does not exist on `origin/main`** (verified:
`ls` -> No such file), so that import raises `ModuleNotFoundError`.

**Sampling is strictly before the chain** (step 4 vs step 7-8). The chain consumes the already
computed `agg["decision_cost_bp"]`; it cannot affect the samples.

---

## 3. Answers

### (a) Does `CHAIN_FAILED` abort the spread sampling, or is sampling recorded first?

**OBSERVED - sampling completes first; `CHAIN_FAILED` does not touch it.**

- Code order: `sample_loop` at `:574` -> aggregate `:583` -> chain `:613` (after).
- Observed with a no-network harness that stubs only `sample_loop` with synthetic plausible
  quotes (40 per pair, spread ~2.2 bp, all REPRESENTATIVE) and runs the real `run_overlap`:
  - `rc=0 status=MEASURED_REPRESENTATIVE cost=2.175`
  - `strategy_chain={'state': 'CHAIN_FAILED', 'error': 'ModuleNotFoundError("No module named \'tools.fx_meanrev_research\'")'}`
  - `strategy_verdict=UNCHANGED_UNKNOWN`
  - artifact written: JSON and MD both present.

The measured spread survives intact; only the chained mean-reversion verdict is missing.

### (b) Is there a single point where the chain failure destroys the artifact?

**OBSERVED - no.** The chain call is wrapped by a broad `except Exception` (`:614`) that converts
any failure into a dict. There is no `raise`/`sys.exit` after `:615`; `guard_verdict` (`:450-465`)
only raises on an *unallowlisted verdict*, and `UNCHANGED_UNKNOWN` is allowlisted (`:78`).
`run_overlap` returns `0` at `:717`; `main()` returns it (`:828-829`) and `SystemExit(main())`
(`:836`) exits 0.

Observed: both `chain_default` and `chain_disabled` runs exited `rc=0` and wrote their artifacts.
The only uncaught-exception surface left is the artifact write itself (`:697-698`), which is
unrelated to the chain.

### (c) Does the GitHub Actions job log show the failure?

**OBSERVED - no. This is the finding.**

- The only `CHAIN_FAILED` write is into the payload at `:615`. The console summary (`:706-716`)
  prints status, per-pair stats, decision cost and the (allowlisted) verdict - it never prints
  `chain["state"]` or `chain["error"]`.
- In the harness, the entire captured stdout/stderr contained **no** mention of the chain,
  `meanrev`, or any error. The last line was
  `decision cost: 2.175 bp | verdict: UNCHANGED_UNKNOWN`.
- `CHAIN_FAILED` appears only in the artifact JSON and its rendered `.md` -
  `render_md` at `:515-520` emits `- not run: \`CHAIN_FAILED\` (ModuleNotFoundError(...))`
  (observed in the generated MD).
- The workflow's "Show verdict" step (`.github/workflows/fx-cost-overlap.yml:91-104`) prints only
  `status`, `decision_cost_bp`, and `strategy_decision.strategy_verdict` - not the chain state.

So a maintainer reading the Actions UI sees a **green run** with a normal cost line and
`verdict: UNCHANGED_UNKNOWN`, and no indication that the chained mean-reversion subsystem failed.
`UNCHANGED_UNKNOWN` is a legitimate-looking value, which is what makes it silent.

### (d) Does the artifact get uploaded/committed on the `CHAIN_FAILED` path?

**OBSERVED (code + repo state) - yes, committed by the normal path; there is no upload-artifact step.**

- `grep upload-artifact .github/workflows/fx-cost-overlap.yml` -> **NONE**. The only persistence
  is the "Commit artifact" step (`:106-116`): `git add reports/cost_measurement_forex/` then
  `git commit` + `git push` if anything changed.
- That step is **not gated** on success (`if:` / `continue-on-error` absent); it runs after the
  measure step. `reports/cost_measurement_forex/` is **not gitignored**
  (`git check-ignore` -> not ignored) and currently has **0 tracked files** on main, so the first
  artifact will be added.
- Since the measure step exits 0 on the `CHAIN_FAILED` path, the commit step runs and pushes the
  artifact (the push uses the workflow's `contents: write` permission, `:51-52`).
- Caveat (CODE-READ): if a blocked run occurs and no file changes, `git diff --cached --quiet` is
  true and nothing is committed - correct behaviour. On the measured path a new JSON/MD is
  always produced, so it commits.

### (e) Does the workflow require `TIINGO_API_KEY`? What happens if it is missing?

**OBSERVED - a missing secret produces a blocked artifact, not a spread measurement, and exits 0.**

- Workflow passes `TIINGO_API_KEY: ${{ secrets.TIINGO_API_KEY }}` (`:79`) and warns if empty
  (`:82-84`), then runs the sampler.
- Code: `token = os.environ.get("TIINGO_API_KEY")` (`:561`); no token -> `:570-572` prints
  `TIINGO_API_KEY not set - not polling; writing a BLOCKED artifact` and skips `sample_loop`.
- Status at `:595-596` becomes `BLOCKED_NO_REPRESENTATIVE_SESSION` / `NO_TIINGO_API_KEY`.
- Observed locally (`env -u TIINGO_API_KEY python3 tools/fx_cost_sampler.py --overlap --ignore-session`):
  exit `0`; artifact `status=BLOCKED_NO_REPRESENTATIVE_SESSION block_reason=NO_TIINGO_API_KEY
  decision_cost=None chain=None strategy=BLOCKED_NO_REPRESENTATIVE_SESSION`.
- It does **not** fail earlier with a different error and does **not** crash - it silently writes a
  blocked artifact (also silent in the Actions log apart from the `::warning::`).
  The workflow's `|| echo "::notice::..."` (`:88-89`) would only fire on a non-zero exit, which does
  not happen here.

(For this pre-flight, `TIINGO_API_KEY` is set in the local shell, but I had no network access to
Tiingo, so I did not make a live API call. The missing-secret behaviour above is fully local and
was executed.)

### (f) Is the chain step skippable? Are `--no-chain` / `--dry-run` available and used?

**OBSERVED - both flags exist; the workflow uses neither.**

- `--dry-run` at `:817-818`; `--no-chain` at `:819-820` (confirmed in `--help` output).
- Observed: `--no-chain` yields `strategy_chain={'state': 'SKIPPED_NO_CHAIN_FLAG'}` and still
  `MEASURED_REPRESENTATIVE`, `rc=0`, artifact written.
- The workflow's run line (`:86-88`) passes only `--overlap --until-samples --interval --max-minutes
  --chain-shuffles 200`. **Neither `--no-chain` nor `--dry-run` is passed.**

**One-line remediation available (NOT applied):** add `--no-chain` to the command at
`.github/workflows/fx-cost-overlap.yml:86-88`. That makes the chain state an explicit
`SKIPPED_NO_CHAIN_FLAG` instead of a silently swallowed `CHAIN_FAILED`. (It does not restore the
missing chain - the real fix is restoring `tools/fx_meanrev_research.py` on main.)

---

## 4. Verdict

**PARTIALLY - the Monday run will produce a usable weekday spread measurement, but not a usable
strategy verdict, and the failure will be invisible.**

- The spread sample (the number that matters for cost) is taken first, survives the chain
  failure, and is written and committed. That is the evidence the programme actually needs, and
  it will be produced if the API responds inside the window.
- The chained FX mean-reversion re-run will fail on every one of the six weekday runs, because
  `tools/fx_meanrev_research.py` is absent from `main`. The strategy verdict will be
  `UNCHANGED_UNKNOWN` - i.e. no new verdict information - and nothing in the Actions UI will say so.

## 5. Green run while a subsystem failed?

**Yes.** The job color is green (exit 0) and the log shows a normal cost line and
`verdict: UNCHANGED_UNKNOWN`. The only trace of the failure is `strategy_chain.state ==
"CHAIN_FAILED"` in the committed JSON and the `## Chained FX mean-reversion re-run` section of the
`.md`. A maintainer would have to open the artifact and read that section to notice.

## 6. What the measurement will and will not prove

If the weekday run succeeds, a representative spread sample at ~13:00-16:00Z proves:
- **Cost:** a real weekday round-trip spread (bp) for the probe pairs, replacing the Sunday-reopen
  upper bound - the one input capable of closing the 3.23 bp gap (measured 7.533 bp vs 4.3038 bp
  break-even).
- Whether the measured cost is above or below the documented break-even.

It does **not** prove:
- **Edge.** A spread sample is a cost input, not evidence the FX mean-reversion strategy is
  profitable. The strategy still needs its own forward evidence (window-clustered CI excluding
  zero at that cost), which is exactly the chain that currently cannot run.
- Anything about commissions - the artifact records `COMMISSION_UNKNOWN` (`:644-647`); the number is
  spread-only.
- A verdict move: the tool can write `NOT_INVESTABLE` or `HUMAN_REVIEW_REQUIRED`, never
  `INVESTABLE` (`guard_verdict`, `:450-465`), and it never edits the programme tally.

---

## Provenance

- Base: `origin/main` = `2ea66184320dc70fd836e697a8619e61668c783a`, clean worktree `/tmp/fxpreflight`.
- Observed commands (all in the clean worktree unless noted):
  - `python3 tools/fx_cost_sampler.py --help` -> exit 0 (flags `--dry-run`, `--no-chain` present).
  - `python3 tools/fx_cost_sampler.py --self-test` -> exit 0, 7/7 PASS.
  - `python3 -c "import tools.fx_meanrev_research"` -> exit 1,
    `ModuleNotFoundError: No module named 'tools.fx_meanrev_research'`.
  - `python3 tools/fx_cost_sampler.py --overlap --dry-run` -> exit 0, `BLOCKED_NO_REPRESENTATIVE_SESSION`/`OFF_SESSION_OUTSIDE_OVERLAP`.
  - `env -u TIINGO_API_KEY python3 tools/fx_cost_sampler.py --overlap --ignore-session` -> exit 0,
    `BLOCKED_NO_REPRESENTATIVE_SESSION`/`NO_TIINGO_API_KEY`.
  - Stubbed-`sample_loop` harness (real `run_overlap`) with and without `--no-chain` -> both exit 0,
    `MEASURED_REPRESENTATIVE` cost 2.175 bp, chain `CHAIN_FAILED` vs `SKIPPED_NO_CHAIN_FLAG`,
    artifacts written, no chain text in captured stdout/stderr.
- Not observed: a live Tiingo API poll (no network access in this environment) - those parts are
  CODE-READ.
