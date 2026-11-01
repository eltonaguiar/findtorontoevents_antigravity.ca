# bestiejob — README job-row guard (2026-11-01)

Closes the loop on the two truncations. Both looked like ordinary edits, and neither tripped
anything because the repo had no check on `README.md` at all.

| Incident | Title said | Actually did |
|---|---|---|
| `8c25626` | "README: add … CGI … and Cognizant … rows" | **+6 / −508**, deleted 210 posting rows and five documentation sections |
| earlier peer commit | (unspecified) | README 583 lines → 85 |

## What was added

`.github/scripts/readme_job_row_guard.py` + `.github/workflows/readme-guard.yml`, pushed as
`bestiejob@90c4574`.

The guard reads `README.md` at a base and a head revision, extracts posting rows, and keys them by
**normalised URL** — scheme, `www.`, query string and trailing punctuation stripped. Working on sets
of URLs rather than lines matters here: this README legitimately replaces rows with the same posting
on a different mirror (`jobs.ca` ↔ Workopolis ↔ Adzuna), and a line-based diff would call that a
loss.

Fails when:

- net loss (`removed − added`) exceeds **3 rows**, or
- duplicate posting URLs grow by more than **5**.

Override for a genuinely intended bulk deletion: `[allow-readme-removals]` in the commit message
(the workflow reads it and passes `--allow-removals`).

Triggers on push to `main` and on any PR touching `README.md`, plus `workflow_dispatch` with an
optional base ref.

## Verification (run locally against real history, not fixtures)

| Test | Base → head | Result |
|---|---|---|
| The actual truncation | `8c25626^` → `8c25626` | **FAIL as designed** — 299 rows/213 postings → 57/57, removed 158, added 2, **net loss 156**, exit 1 |
| My restore commits | `b39ee81` → `a44556f` | PASS — removed 0, added 22, net −22 |
| jobs.json-only commit | `40dc265` → `89766b2` | PASS — 315 → 315 rows, net 0 |
| Override flag | same as test 1 + `--allow-removals` | PASS — exit 0 |

`py_compile` clean, workflow YAML parses, both files return HTTP 200 on `main`.

## Known limits

- Only counts rows that mention ServiceNow or Salesforce. Every posting here is one of those two, so
  coverage is complete in practice; a generic "CRM Developer" row with neither word would be invisible.
- Net-loss tolerance of 3 means someone deleting one or two postings by accident still passes. That is
  deliberate — too tight a limit would fail on legitimate tidy-ups and get the check disabled.
- Requires `fetch-depth: 0` so the base SHA exists; already set in the workflow.
