# 2026-11-27 — verification-tests' hidden CR damage, gha-quality green + cron, and the 2hour proof

Seat: ELTON2026 laptop (Buffy). Window 01:10Z–02:30Z. Follows
`updates/2026-11-27-chronic-red-root-causes.md`.

## 1. `2hour_challenge` — the timeout fix is now PROVEN, not assumed

Previous doc proved the cause (job-level `timeout-minutes: 30` against a 120-minute script,
reported by GitHub as `cancelled`). What was missing was a run that survives the old cap.

Verification run **45921032225** (dispatch 01:10:25Z, job started 01:10:28Z, step
"Run 2-hour trading challenge" started 01:11:19Z):

| clock | job state | elapsed |
|---|---|---|
| 01:15:52Z | in_progress (reported mid-run) | 5m |
| 02:02:40Z | in_progress | **52m** |
| 02:10:11Z | in_progress | **60m** |

Every pre-fix run died at 30m14s–30m16s. This one passed 30 minutes with the step still
`in_progress`, which is the assertion the cap fix had to satisfy. Expect completion around
03:11Z (120-minute loop + commit/notify steps); the 30-minute question is already settled.

## 2. `verification-tests` — the red was 488 stray CR bytes, not 25 broken tests

Run 45875941675 (2026-11-26T18:26Z) reported `25 failed, 7534 passed` — but this workflow is
supposed to run ten named suites (~135 tests), not the repo. The log shows why:

```
configfile: pytest.ini
testpaths: tests
collected 7622 items / 10 skipped
tests/strategy_tests/test_new_strategies.py ........     <- never named on the command line
```

`.github/workflows/verification-tests.yml` on main has **185 CRLF line endings plus 488 lone
CR characters** — the line ends are literally `\r\r\r\r\n`. YAML tolerates that in a scalar, so
the workflow still parses and runs. Bash does not: in

```
python3 -m pytest \␍␍␍
  tests/test_verify_peer_claims.py \␍␍␍
```

the backslash is followed by CR, not by a newline, so it is **not a line continuation**. Every
argument was dropped, `python3 -m pytest` ran bare, and `pytest.ini`'s `testpaths = tests`
pulled in the whole 7,622-test monorepo. The 25 failures were real repo-wide drift, but they
have nothing to do with the verification invariants this gate exists to protect.

Fix: `d5328710` normalises the file to LF (9,369 B → 8,696 B, 0 lone CR, YAML re-parsed).

Verification: run **45926307480** (dispatch, 02:05:47Z) → **success**, log line
`135 passed in 5.00s`. Same command, same tree, focused gate restored. A push-triggered run
45926297646 was `cancelled` by the workflow's own `cancel-in-progress: true` concurrency (my
dispatch superseded it six seconds later) — expected, not a fault.

Only this one workflow was damaged: `sign-coherence-gate.yml`, `weekly-filter.yml`,
`2hour_challenge.yml`, `gha-quality-framework.yml`, `db-sync-to-mirror.yml` and
`forward-observations-ingest.yml` all read back with 0 stray CR. Worth checking any workflow
that suddenly "runs the whole test suite" for the same byte-level cause.

## 3. `gha-quality-framework` — from 103 blocking violations to green, cron now on

The gate's `--check` mode is a delta against `GHACTIONS_LIVE/gha_quality_baseline.json`, so 103
known violations are not the wall — **new** ones are. Run 45921369405 said
`2 NEW blocking violation(s) of 103 total`:

1. `Q2 Secret Scan (M-043)`: `gitleaks/gitleaks-action@v2` referenced by a floating major tag.
2. `Q7 Forward-Test New Strategies Tracker`: `Enforce strategy-generation freeze (P0 gate)`
   is gate-shaped and its run block contains `|| true`.

Both were fixed without changing behaviour:

- `b616212a` pins the action to `ff98106e4c7b2bc287b24eaf42907196329070c7` (# v2.3.9, the tag's
  commit, verified against the tags API). A moved major tag silently changes what runs inside
  the very scanner meant to catch supply-chain compromise.
- `ffecf1f0` replaces `cat freeze.err >&2 || true` with
  `if [ -s freeze.err ]; then cat freeze.err >&2; fi`. The swallow was only ever on the stderr
  echo; the gate's real contract (rc=1 → `frozen=true`, rc>1 → hard fail) is untouched. The
  `|| true` remaining in "Commit results" is not a Q7 hit — `NON_GATE_ACTION_RE` exempts
  commit steps by design.

Verification — run **45926705290** (dispatch, 02:09:54Z) → **success**:
`--check (baseline): 0 NEW blocking violation(s) of 101 total`, aggregate score 94.9/100.
That is the first green dispatch of this workflow.

It also exercised the third fix from the previous batch: the commit step wrote
`[main 08bfe0d0] chore(gha-quality): refresh Q1-Q10 report [skip ci]` and `safe_push.sh`
reported `Push attempt 1/8 (budget 270s)` and landed it. The bounded-push replacement for the
old bare `git push` is now proven on a real commit, not just present in the file.

All three documented enablement conditions are met, so `4a21e119` uncomments the cron
(`13 */6 * * *`) and records the evidence inline. The gate now runs on a schedule; if it ever
drifts, `--check` names the new violation instead of a wall of 103.

## 4. `forward-observations-ingest` — red, correctly, and self-clearing

Runs 45924089994 (01:42Z) and 45924764585 (01:49Z) failed in `Forward-growth watchdog (B3)`:

```
no_eligible_rows: no admissible cohort rows this run (ledger rows=456)
  note: 448 of 448 admissible rows were already in the ledger - 0 new row(s) could have been written
  FAIL POD-EQUITY-BREAKOUT has 0 forward rows 8.1d after pre-registration (grace 7.0d) — the emitter never landed
```

Timeline matters here, and it is all from tonight:

- 01:21:24Z `hermes-agent` retired the pod as declined ("emitter never scheduled, structural
  zero forward rows").
- 01:38:12Z the manifest was rewritten to `pre_registered` and the emitter scheduled.
- 01:41:54Z the emitter actually wrote: `applied donchian-stock-breakout: 35 row(s) touched;
  trading_picks now has 59 rows for donchian-stock-breakout`.

So the emitter has landed data, but a pick can only enter the forward ledger once it **closes**.
The watchdog measures grace from `registered_at` (2026-11-19), so it fails on a pod whose
emitter has existed for under an hour. This is a transitional red, not a code defect and not a
reason to decline the pod a second time. It should clear on its own once the first emitted picks
close.

If it is still red 7 days from now, the honest fix is a manifest field (`emitter_live_at`) that
starts the grace clock no earlier than the date emission became possible — NOT a raised
`--grace-days` and NOT a baseline edit. Not applied here because the pod's owner is actively
editing that manifest.

## 5. `sign-coherence-gate` — one real corrupt row, operator purge required

Run 45756493227: `Sign-flips found: 1`, `Baseline (max allowed): 0`
(`vars.SIGN_FLIP_BASELINE=0`), scanned 32,970 closed picks.

```
genome  AVAXUSDT  LONG  entry=8.74  exit=8.656  stored=+6.97%  recomputed=-0.96%  status=WON
```

A LONG that exited below entry cannot be +6.97%. This is one row of resolver corruption, not a
scanner bug and not a baseline problem. The remediation is the operator-gated tool, which
defaults to dry-run and backs the rows up first:

```
python3 -m audit_trail.sign_flip_purge --source genome            # dry-run, review
python3 -m audit_trail.sign_flip_purge --source genome --apply    # backup + correct
```

Deliberately not run from here: it writes `at_pick_outcomes` in production, and its own
docstring reserves the apply step for the operator. **`SIGN_FLIP_BASELINE` must stay 0** — moving
it to 1 would hide the next flip too.

## 6. PRs left open, with sharper reasons than before

- **#1181** `fix(audit-dashboard): stop hyro scoring dying on a silent numpy downgrade` — now
  `MERGEABLE`/`CLEAN` with all checks passing, and the audit-dashboard hunk is a good fix
  (wheel-only pin plus a loud ABI probe). It is still not mergeable as-is: the branch also
  carries a stale `1000_TODOS.{json,md}` regeneration that reverts **19 cells** from
  done/killed back to claimed (`done_or_killed` 107 → 88) and reassigns them to KILO. Landing it
  would erase closed work. Merge only the workflow hunk.
- **#1195** `fix(ci): production runner + push hardening, freeze-gate signalling` —
  `CONFLICTING`. Its `forward-test-new-strategies.yml` hunk covers the same freeze-gate region
  fixed here in `ffecf1f0`, and `safe_push.sh` is already exercised on main (commit 08bfe0d0),
  so the surviving value is the runner/push hardening in the other six workflows. Rebase needed.

## Outstanding operator actions (unchanged + new)

- cPanel `torontoevent.net`: grant `TORONTOEVENT_DB_USER` on `ejaguiar1_deals`, `_events`,
  `_memocoin`, `_news`, `_sportsbet` — db-sync-to-mirror stays red until then.
- Discord: bot role needs **Manage Messages** on channel `1476311595977150779`.
- `at_pick_outcomes`: purge the one `genome/AVAXUSDT` sign-flip row (section 5).
