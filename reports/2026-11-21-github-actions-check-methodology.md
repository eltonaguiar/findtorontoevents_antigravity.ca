# Methodology: checking GitHub Actions without guessing

**Date:** 2026-11-21 · **Repo:** `eltonaguiar/findtorontoevents_antigravity.ca`
**Context:** 159 workflows, ~488 completed runs, one chronically red gate
(`QA Market Validation`) that turned out to be three separate defects.

## Why a method

"Red" is four different things, and only one of them is a code bug:

| Red looks like | Actually is | Action |
|---|---|---|
| `in_progress` / `queued` with `conclusion: null` | not finished | wait; it is not a failure |
| `cancelled` right after a new push | concurrency supersession | check the run that replaced it |
| failed gate, artifact absent/stale | broken artifact contract | fix the workflow, not the gate |
| failed gate, numbers that do not add up | gate bug | fix the counters/checks |
| failed gate, correct verdict on bad data | data defect | fix the data at its source |

Treating all five the same is how a red job survives for weeks.

## Step 0 — snapshot (UTC, one command)

```bash
gh run list --limit 200 --json workflowName,conclusion,status,createdAt,databaseId,event,headSha \
  --jq 'group_by(.workflowName)
        | map({wf: .[0].workflowName, runs: (sort_by(.createdAt))})
        | map({wf, last: (.runs|last), last_success: ([.runs[]|select(.conclusion=="success")]|last)})
        | map(select(.last.conclusion != "success"))
        | .[] | "\(.wf)\tlast=\(.last.conclusion // .last.status) @\(.last.createdAt[5:16]) last_success=\(.last_success.createdAt[5:16] // "none")"'
```

`conclusion` is `null` while a run is queued or running — filter on
`status` first, or every in-flight run reads as "not success".

## Step 1 — separate in-flight from red

A workflow is **red** only if its latest *completed* run is `failure` and there is
no later success. Count consecutive failures; one flake is not a pattern.

## Step 2 — chronic red: check the artifact contract first

For each workflow that writes a dashboard artifact, ask two questions:

```bash
# a) does the job commit what it advertises?
git show origin/main:.github/workflows/<wf>.yml | grep -n "git add\|git commit\|contents:"
# b) how old is the committed copy compared with the last run?
git log -1 --format='%ad' --date=iso -- audit_dashboard/data/<artifact>.json
```

If the artifact is older than the last run, the gate has been reporting into a
void. **`QA Market Validation` failed this check**: `contents: read`, no commit
step, artifact dated 2026-11-15 (`n_picks 4390`) against 183 printed.

## Step 3 — triage one run, in order

```bash
gh run view <id> --json jobs --jq '.jobs[]|"\(.name): \(.conclusion)"'
gh run view <id> --log-failed | grep -n "##\[error\]\|##\[warning\]" | head
```

Read the step list before the log: a failure in `Run QA ledger` is a verdict; a
failure in `Install dependencies` is infrastructure and means the verdict never
ran. While a run is queued, `--log-failed` returns `404 BlobNotFound`; that is
not a missing log.

## Step 4 — reconcile the numbers the gate prints

Before believing a gate, check that its own summary adds up:

> printed per-class counters must sum to the flag totals, and
> `critical` must equal the count of critical verdicts.

`QA Market Validation` printed `18 flags (12 critical)` with per-class lines
summing to 11: `PNL_OUT_OF_BOUNDS` was flagged but never counted. A gate whose
summary cannot explain its red is a gate bug, independent of the data.

## Step 5 — is the data or the gate wrong?

Pull the artifact the gate read and recompute one flagged row by hand. Then decide:

1. **Gate right, data wrong** → fix the producer. Here: yfinance froze the JPY
   leg (USDJPY 158.512 at 22:26/23:26, 159.707 at 00:43, frozen for two hours
   while every non-JPY pair moved), so the tracker now cross-checks FOREX quotes
   against the failover feed and prefers it beyond 0.25% drift.
2. **Gate wrong** → fix the counter/check, never the tolerance.
3. **Gate impossible** (missing keys, blocked network) → fix the environment or
   mark the step advisory, with the reason in the workflow.
4. **Data genuinely unpriceable** (symbol resolved to a different security:
   `MBS` 8.295 → 58.215) → quarantine it at the producer and have the gate verify
   the quarantine. Do not publish a number you know is wrong, and do not widen
   the bound until it passes.

## Step 6 — prove the fix

```bash
gh workflow run <wf>.yml
gh run watch <new-id>
# then confirm the artifact came from THIS run, not an older one
git pull && python3 -c "import json;d=json.load(open('audit_dashboard/data/<artifact>.json'));print(d['generated_at'], d['n_picks'])"
```

Green is not enough: the artifact must be newer than the fix commit and its
counts must match the run's printed totals. Otherwise the gate passed while
writing nothing.

## Traps worth remembering

- `git pull -X ours` over generated JSON can hybridise artifacts — that is why
  `tools/detect_merge_hybrid.py` gates the commit and the merge.
- A `[skip ci]` data commit is picked up by the next cron, not by a push trigger.
- `cancel-in-progress: false` keeps one pending run per group; a `workflow_dispatch`
  can displace the queued scheduled run.
- Step names describe the triggered commit, but the job re-pulls `main` mid-run,
  so a post-merge step can execute newer code than the name implies.
- Logs expire (and 404 while queued); the committed artifact is the only durable
  record — which is why gates should commit one.

## Result of applying this method on 2026-11-21

| Finding | Diagnosis | Fix |
|---|---|---|
| QA red 8/8 runs | gate summary did not reconcile (11 counted vs 12 critical) | counters added, printed |
| 11 FOREX mismatches | producer used a frozen yfinance JPY tick | FX cross-checked against failover feed |
| `MBS` +601.81% | symbol-resolved to a different security | quarantined at the producer, verified by the gate |
| artifact 6 days stale (4390 vs 183 picks) | workflow never committed it | `contents: write` + `if: always()` commit |
| AUDJPY etc. reported as data drift | actually one bad JPY leg, not 11 bad pairs | same as row 2 |
