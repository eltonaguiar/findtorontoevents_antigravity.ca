# A check that refuses to call a branch-only feature "live"

## The failure it prevents

On 2026-11-22 the forward paper book was built, seeded, wired into
`audit3-ledger.yml`, pushed — and reported as deployed. Every commit lived on
`fix/dsr-baselines-h146-key-scrub-2026-11-21`, which was never merged.
`origin/main` had no `tools/forward_book.py`, so the resolve step did not exist
there and could never run. The evidence:

- `/audit3/forward_book.json` → 404
- `/audit/audit3.html` → 404
- `/audit3/index.html` → 200 but zero `forward_book` markup
- scheduler: run 44994305292, **success**, 06:34Z — running main's older code

The scheduler was healthy. The claim was wrong. "Pushed" was being used as if it
meant "merged", and "merged" as if it meant "deployed".

## What this adds

`tools/verify_live_claim.py` takes the two claims separately and fails on either:

```
python3 tools/verify_live_claim.py \
    --path tools/forward_book.py \
    --url https://findtorontoevents.ca/audit3/forward_book.json \
    --expect forward_book
```

- `--path` checks the file via `git cat-file -e origin/main:<path>` — the tree the
  workflow checks out, **not** the working copy, which is exactly the confusion
  that caused the original mistake.
- `--url` requires HTTP 200 and, with `--expect`, the expected content, so a 200
  serving a stale page still fails.

Exit 0 only when every claim holds. On any failure it prints `REFUSING: N of M
claim(s) are unsupported. This feature is NOT live — do not report it as
shipped.` to stderr and exits 1.

## Verification

- Used for real on this branch: `--path tools/forward_book.py` → OK (merged in
  PR #1047), `--path` of a nonexistent file → FAIL / exit 1, `--url` of the live
  `audit3_ledger.json` → OK.
- `python3 -m pytest tests/test_verify_live_claim.py -q` → 5 tests.
- `py_compile` → OK.

## Limits

It checks that the file is on the ref and that a URL answers; it cannot know
whether a *page* renders the feature or whether an entry in a JSON file is
actually shown. It makes the cheap part of the claim mechanical, not the whole
of it.
