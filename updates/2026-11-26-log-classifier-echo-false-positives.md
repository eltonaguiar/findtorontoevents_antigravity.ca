# The log classifiers counted source code as errors (2026-11-26)

## What was broken

Three self-hosted debug runs concluded `success` and were still scored `ERRORS`
by `tools/gha_selfhosted_batch.py::classify()`:

| Run | Workflow | Real state | Classifier said |
|-----|----------|-----------|-----------------|
| 45762289378 | `swarm-sync-v2.yml` | success, "No effective changes — nothing to push" | `ERRORS ['4x ERROR line']` |
| 45762068793 | `strategy-funnel-hourly.yml` | success, pushed on attempt 2 | `ERRORS ['1x ERROR line']` |
| 45759735232 | `gha-queue-audit.yml` | success, 400 runs scanned | (correctly `ERRORS` — real 403s) |

All four `swarm-sync-v2` matches were the literal text of **unexecuted** handlers:

```
echo 'ERROR: rebase conflict — aborting sync to avoid corrupting state files'
echo 'ERROR: push failed after 3 attempts'
```

GitHub prints the whole `run:` block into the log *before* executing it, so
`echo '...ERROR...'` lands in the log as source. The pattern
`(?:^|\W)ERROR(?:\W|$)` cannot tell that from an emitted error. The same naive
pattern sits in `tools/gha_latest_run_log_audit.py` (`ERRORS` table), which is
what produced the fleet-wide `ERRORS` verdicts — **17 workflows had "ERROR line"
as their only error kind**, so a material part of the "72 ERRORS" headline was
"this workflow echoes the word ERROR".

The second case is different and also wrong: a push rejected non-fast-forward
followed by `Pushed successfully on attempt 2` is `safe_push.sh` working as
designed. A retry that heals should not be an error.

## What changed

`tools/gha_selfhosted_batch.py`:

* `_ECHO_SOURCE = re.compile(r"(?<![\w.\-/])echo\s+['\"]", re.I)` — command-echo
  lines are dropped before matching. The lookbehind keeps `echo` inside a word
  (for example `xecho`) from matching. An unquoted `echo ERROR` is deliberately
  **not** filtered; it is rarer and ambiguous.
* If the log contains `Pushed successfully on attempt`, `Nothing to push` or
  `Already up to date`, the `failed to push` / `Updates were rejected` /
  `non-fast-forward` lines from the failed attempt are dropped.

`tools/gha_latest_run_log_audit.py`: the same `_ECHO_SOURCE` filter is applied in
`bucket()`, so fleet-wide counts stop counting source as output.

## Effect on the numbers

Re-scoring the 361 cached logs (`python3 tools/gha_latest_run_log_audit.py --resume`,
no new API calls):

| | Before | After |
|---|---|---|
| Logs audited | 304 | **361** |
| `ERRORS` | 72 | 86 |
| `SUSPICIOUS` | 24 | 31 |
| `AUDIT_INCOMPLETE` (no log) | 58 | **8** |
| Workflows needing investigation (`reports/GHA_USAGE_TRIAGE.md`) | 191 | **160** |

`ERRORS` rose because coverage rose by 57 workflows; the echo filter removed the
false ones inside that larger set. The triage total fell because "no log to read"
collapsed from 58 to 8 once the previously in-progress runs had logs.

## How it was verified

`python3 -m pytest tests/test_gha_log_classifier_echo.py tests/test_gha_usage_triage.py -q`
→ **13 passed**. The tests pin: echo-only log is CLEAN; a real uppercase `ERROR:`
is still ERRORS; a healed push retry is CLEAN; an unhealed one is ERRORS;
`##[error]` annotations are never filtered; and `bucket()` returns 0 on an
echo-only log while still counting real output.

False negatives were checked explicitly: `##[error]`, traceback, `fatal:`,
`command not found` and uppercase `ERROR` in output all still classify as errors
(the inline case above shows `ERROR: disk full` → `1x ERROR line`).
