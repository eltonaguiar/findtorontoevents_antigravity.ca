# GHA Workflow Integrity Sweep — 2026-11-26

**Scope:** Exercise every unique workflow on `main` / `gh-pages`, triage the
failures, and fix the ones that are genuine repo defects (as opposed to
environment or credential problems).

**Method:** 383 `*.yml` files statically validated (YAML parse, `bash -n` on
every `run:` block, `actionlint -oneline`, workflow-masking lint), then 386
registered workflows classified by live health, then 20 workflows dispatched
via `workflow_dispatch` on `main` and their logs read.

---

## Static baseline (before)

| Check | Result |
|---|---|
| `*.yml` under `.github/workflows/` | 383 |
| YAML parse | 383 / 383 OK |
| `run:` blocks through `bash -n` | 1,936 blocks, 0 failures |
| `actionlint -oneline` diagnostics | 325 total (321 shellcheck info + **4 real errors**) |
| Workflow-masking lint | rc=0 — `73 with continue-on-error; 38 silent, 38 baselined, 0 NEW` |
| Dispatchable (`workflow_dispatch` present) | 376 / 383 |

Live health (386 registered): 349 success · 21 never-run · 7 in_progress ·
5 failure · 3 cancelled · 1 pending.

---

## Defects fixed in this PR

### 1. `dna_strategy_pipeline.yml` — `Generate Active Picks` hard-timeout at 30m

**Broken:** run `45730970357`, job `Generate Active Picks` started
`2026-11-26T00:46:22Z` and completed `01:16:38Z` = **30m16s**, i.e. it hit the
`timeout-minutes: 30` cap mid-write. 4 of the 6 runs before this date were
cancelled the same way (`45695769471`, `45654835612`, `45615258591`,
`45577220514`), so the overrun was a coin-flip per cycle, not a one-off.

**Changed:** `generate-picks` timeout `30` → `45`, matching the
`evolve-strategies` job budget already in the same file, plus a comment citing
the measured run.

### 2. `won-pnl-contradiction-backfill.yml` — `unrecognized arguments: false`

**Broken:** run `45740864308` → `audit_won_picks_auto.py: error: unrecognized
arguments: false`. The step did `APPLY="false"` and then invoked
`python tools/audit_won_picks_auto.py $APPLY ...`. Because `$APPLY` was
unquoted, `false` was passed as a positional argument. The companion
`DRY_RUN="--dry-run-only"` variable was **dead code** — `tools/audit_won_picks_auto.py`
only defines `--apply` and `--report` (lines 88-89).

**Changed:** `APPLY=""` by default, corrected the dry-run echo text, and
deleted the entire dead `DRY_RUN` branch. Corrections are already opt-in via
`--apply`, so "no flag" *is* the dry run. The invocation line is unchanged.

### 3. `closed-picks-command.yml` — `No module named 'signal_aggregator'`

**Broken:** run `45740823581` → `ERROR:__main__:Error: No module named
'signal_aggregator'`. `signal_aggregator/closed_picks_command.py:45` does
`from signal_aggregator.picks_router import PicksRouter`, but the workflow runs
it as `python signal_aggregator/closed_picks_command.py`, which puts
`./signal_aggregator` on `sys.path` instead of the repo root.

**Changed:** added `PYTHONPATH: ${{ github.workspace }}` to the step env so the
repo root is importable regardless of how the script is invoked.

### 4. `pod-h201-forward-clock.yml` — `No module named 'scipy'`

**Broken:** run `45740844705` → `ModuleNotFoundError: No module named 'scipy'`,
raised from `tools/per_class_edge_harness.py:28`
(`from scipy import stats as sps`), imported by `tools/pod_forward.py:53`. The
install step only did `pip install pandas numpy yfinance`.

**Changed:** added `scipy` to the install line.

### 5. `weekly-scorecard.yml` — `! [rejected] main -> main (fetch first)`

**Broken:** run `45740861437` → the `Commit scorecard` step used a bare
`git push`. That loses the race whenever any other workflow commits to `main`
in the same window.

**Changed:** `git push` → `bash .github/scripts/safe_push.sh`, the repo
standard already used by 200+ workflows (rebases with retry/backoff).

### 6. `concurrency.queue: max` — invalid key in 4 workflows

`queue:` is not a valid child of `concurrency:` in GitHub Actions. It is
silently ignored, but it makes `actionlint` report a hard error on each file.
Removed from:

- `crypto-ohlcv-refresh.yml`
- `daily-prices-yf-refresh.yml`
- `db-freshness-guardian.yml`
- `stocks-daily.yml`

`group:` and `cancel-in-progress:` are untouched, so runtime behaviour is
identical. This takes the repo from **4 real actionlint errors to 0**.

### Bonus: 4 markdown files recovered from PR #1149

PR #1149 was closed as "code already merged" (squash `21a47251f6b7`), but 4 of
its 12 files never landed. Recovered verbatim from commit `6542e7382e60`:

- `reports/emitter-mute-kill-proposal-2026-11-25.md` (508 lines)
- `reports/supply-bottleneck-analysis-2026-11-25.md` (240 lines)
- `reports/wired-pm-classification-2026-11-25.md` (240 lines)
- `updates/2026-11-25-open-backlog-resolver-fixes.md` (112 lines)

---

## Verification

```bash
# 1. YAML parses
python3 -c "
import glob, yaml
bad = 0
for p in sorted(glob.glob('.github/workflows/*.yml')):
    try: yaml.safe_load(open(p))
    except Exception as e: bad += 1; print('FAIL', p, e)
print(f'{len(glob.glob(\".github/workflows/*.yml\"))} files, {bad} parse failures')
"
# -> 381 files, 0 parse failures

# 2. Every run: block is valid bash
python3 - <<'PY'
import yaml, subprocess
files = ['dna_strategy_pipeline','won-pnl-contradiction-backfill',
         'closed-picks-command','pod-h201-forward-clock','weekly-scorecard']
bad = n = 0
for f in files:
    d = yaml.safe_load(open(f'.github/workflows/{f}.yml'))
    for j in d['jobs'].values():
        for s in j.get('steps', []):
            r = s.get('run')
            if not r: continue
            n += 1
            if subprocess.run(['bash','-n'], input=r, text=True).returncode:
                bad += 1; print('FAIL', f, s.get('name'))
print(f'{n} blocks, {bad} failures')
PY
# -> 31 blocks, 0 failures

# 3. actionlint — zero real errors repo-wide
actionlint -oneline .github/workflows/*.yml 2>&1 | grep -v shellcheck | grep -c ':'
# -> 0

# 4. Masking policy not weakened
python3 scripts/lint_workflow_masking.py --fail-on-new
# -> rc=0, 0 NEW
```

Diff: **9 workflow files, 31 insertions(+), 14 deletions(-)** — no generated
data, no dashboard HTML, no credentials.

---

## Known-broken but NOT fixed here (need a human decision or external config)

1. **10 workflows are `disabled_manually`**, including the **entire 5-workflow
   sports pipeline** (`sports-betting-refresh`, `sports-data-snapshots`,
   `sports-forensics-weekly`, `sports-prediction-market-sync`,
   `sports-smoke-and-e2e`) plus `ai-tournament-pipeline`, `battle_test`,
   `db-secret-scan`, `mirror-site` (since re-enabled and dispatched as run
   `45740915469`), and `mermaid-test-deploy`. The sports pipeline being off is a
   **Goal #2 blocker**; enabling it is a product decision, not a code fix.
2. **`mermaid-test-deploy.yml` is `disabled_manually` on GitHub but no longer
   exists on `origin/main`** — an orphan registration on GitHub's side.
3. **`db-freshness-guardian.yml:63` is `continue-on-error: true`**, which
   masks an exit-2 RED from the freshness gate. Un-masking is a policy call.
4. **`POD-EQUITY-BREAKOUT` emitter never landed** —
   `forward-observations-ingest.yml` run `45741022038` correctly reports
   `has 0 forward rows 7.1d after pre-registration (grace 7.0d)`. The watchdog
   is working; the emitter is genuinely missing.
5. **`clear-channel-command.yml`** run `45740820521` — `Bot lacks permission to
   delete messages in channel 1476311595977150779`. Discord role config, not code.
6. **`wsl-runner-manager.yml`** run `45740866986` — `WSL_E_DISTRO_NOT_FOUND`.
   Self-hosted runner image drift, not code.
7. **Resolver no-op** — `Outcome Resolver  Validate Unresolved Picks` is green
   while committing `resolved 0 picks (WR=0%)`. This is the mechanical cause of
   the "CRYPTO 0 closed in 48h / 322 still active" symptom in `CLAUDE.md`.
   **Goal #1 blocker**, tracked separately.

---

## Notes for future maintainers

- `actionlint -format` is broken in 1.7.7 (`can't evaluate field File`) — use
  `actionlint -oneline`.
- PyYAML parses `on:` as boolean `True`; read `d.get('on') or d.get(True)`.
- A `gh workflow run` HTTP 422 has two very different causes — *disabled
  workflow* vs *missing required input*. They look identical in a truncated
  log; always print the full error.
- Before "fixing" a secret-dependent workflow, check `gh secret list`
  `updated_at` — a peer may already have rotated the secret and the fix is only
  a re-run. That was the case for `mirror-site.yml` (`FTP_HOST`/`FTP_USER`/
  `FTP_PASS` were bumped ~2h after the failure).
- When inserting a comment block into a YAML `run: |`, the comment lines must be
  indented to **at least** the block's first-line indent. A shallower line
  silently terminates the block scalar and YAML then fails with "expected
  `<block end>`, but found `<scalar>`". This bit twice while writing this PR —
  always re-run the YAML parse after editing a `run:` body.
