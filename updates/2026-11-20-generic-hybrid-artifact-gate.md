# Make the refresh job detect a hybridised artifact generically

## What was broken

The PROBATION-label drift was repaired for one payload
(`audit_dashboard/data/anti_overfit_audit.json`): `apply_dsr_probation_labels.py`
re-stamps and re-checks it after the merge. Nothing checked the other ~262 generated
JSON files the same job commits every hour, so the next artifact a line-based
`git pull -X ours` collided would be pushed exactly the same way -- and if it had no
labels to lose, no test would notice.

## What changed

* **`tools/detect_merge_hybrid.py`** -- a payload is hybridised when it contradicts
  itself: a count that names its array disagrees with that array's length by 1-5 rows,
  or a row appears byte-identically twice. Works on `--staged`, on a commit range
  (`--rev-range`), or on explicit paths, with `--under` to bound it to directories.
* **`.github/workflows/audit-dashboard.yml`** -- two blocking gates:
  * before `git commit -m "chore(audit-dashboard): refresh payload"`, over `--staged`;
  * after the merge, immediately before the push, over `--rev-range HEAD^..HEAD`
    bounded to the directories the job commits (so another bot's payload cannot block
    a clean run).
* **`tests/test_detect_merge_hybrid.py`** -- 9 tests: clean payload, count naming its
  array, subset tally ignored, wide difference ignored, verbatim duplicate, repeated
  name needing a count problem, list-valued identity, nested array, CLI exit codes.

## How verified

* Clean `origin/main`: **0 of 251** artifacts trip.
* `c4a0acd`: **1** trips -- the anti-overfit payload, with `n_strategies_audited=80
  but holds 81 rows` and the duplicated `regime_mild_bear`.
* 9 new tests plus the 11 publication-label tests pass; workflow YAML parses.
* Full scan and the false-positive study: `reports/2026-11-20-generated-artifact-hybrid-scan.md`.

## Known limits

* The 1-5 row window is deliberate: a merge duplicates a row or resurrects a stale
  header, it does not double the file. A grosser inconsistency is not caught.
* Files over 12 MB (the tool) and 4 MB (the scan) are skipped rather than streamed.
* Subset tallies are out of scope by design -- see the report for why.
