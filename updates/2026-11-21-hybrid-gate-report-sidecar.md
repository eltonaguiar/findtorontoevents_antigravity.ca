# Commit the gate's coverage, not just its verdict

## What was missing

A passing hybrid gate produced exactly one line of stdout:

```
no hybridised artifacts (47 inspected)
```

That line lives in a 60-minute job log, which GitHub expires, and which can only be
fetched once the job is over (`404 BlobNotFound` while it runs -- verified on
2026-11-21). So "was the 2026-11-21 01:57 refresh gated, and how much of it?" was
unanswerable from the repository: the run went green and left no evidence of what
it had checked.

## What changed

`tools/detect_merge_hybrid.py` gained `--report PATH`, which writes:

```json
{
  "schema": 1,
  "tool": "tools/detect_merge_hybrid.py",
  "entries": [
    {
      "run_id": "44845277959",
      "phase": "rev-range",
      "rev_range": "8f01ba22ce7c^..8f01ba22ce7c",
      "inspected": 43,
      "skipped": [],
      "findings": 0,
      "verdict": "clean"
    }
  ]
}
```

* `phase` is `staged`, `rev-range` or `paths` depending on how the gate was called.
* `skipped` names every artifact that was **not** gated, with its size, so the
  15.9 MB `pf_registry.json` skip is recorded rather than inferred.
* `verdict` is `clean` or `hybridised`; `findings` is the contradiction count.
* Entries are keyed by `(GITHUB_RUN_ID, phase, rev_range)` and capped at 50. They
  carry **no timestamp**, on purpose: a retry that observes the same numbers
  rewrites identical bytes, so the workflow's `git diff --quiet` guard does not
  manufacture a commit per attempt.

Workflow changes:

* the pre-commit gate is `--staged --report audit_dashboard/data/hybrid_gate_report.json`,
  and the report is `git add`ed before `git commit` so it lands in the refresh
  commit alongside the payload it describes;
* the post-merge gate reports to the same file, then commits it **inside the retry
  loop, before the push**, so the trail describes this run rather than the next one.

Also fixed while in there: the summary line counted `len(files)`, which included
skipped and missing files, so a run that skipped one artifact still claimed to have
inspected it. It now reports files actually parsed.

## How verified

* `pytest tests/test_detect_merge_hybrid.py` -- 19 pass, including: a clean entry,
  a recorded skip, a hybridised verdict, retry byte-identity, staged vs rev-range
  kept apart, and the report file itself not tripping the gate.
* Workflow YAML parses; both invocations carry `--report`; the commit guard is
  present.
* A real entry produced from the 2026-11-21 01:57 refresh commit
  (`8f01ba22ce7c`): `inspected: 43, skipped: [], findings: 0, verdict: clean` --
  matching the job log's `no hybridised artifacts (43 inspected)` for that commit.

## Limits

* The report records **how many** artifacts were inspected and which were skipped,
  not the list of paths. Naming every path would roughly double the file each hour.
* Entries are capped at 50 (~2 days at 2 entries/run), so it is a rolling window.
* A run whose staged set is unchanged exits before the gate ("No changes to
  commit"), so that run writes no entry -- accurate, since nothing was gated.
* The first entry appears only after the next hourly run; this PR does not backfill.
