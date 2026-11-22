# `/audit/audit3.html` 404: the page was published to a different path — 2026-11-22

## What was broken

`https://findtorontoevents.ca/audit/audit3.html` returns **404**, which peers read
as "/audit3 is not deployed". It is deployed — at a different URL:

| URL | before |
|---|---|
| `https://findtorontoevents.ca/audit3/` | **200** |
| `https://findtorontoevents.ca/audit3/audit3_ledger.json` | **200** |
| `https://findtorontoevents.ca/audit3/audit3_evidence.json` | **200** |
| `https://findtorontoevents.ca/audit/data/money_ready_verdict.json` | **200** |
| `https://findtorontoevents.ca/audit/audit3.html` | **404** |

`audit3.html` is uploaded only by `audit3-ledger.yml` / `audit3-evidence.yml`, and
both map it to `/audit3/index.html`. Nothing ever wrote `/audit/audit3.html`, so
"the /audit surface is missing audit3" was a path expectation, not a publish
failure. The peer report also claimed `money_ready_verdict.json` was 404 at
`/audit/data/` — that is stale; it returns 200.

## What changed

1. `audit_dashboard/audit3.html`: the two data fetches were **relative**
   (`audit3_ledger.json`, `audit3_evidence.json`). A copy at `/audit/audit3.html`
   would therefore have requested `/audit/audit3_ledger.json`, which is 404. Both
   are now absolute (`/audit3/...`), which resolves from either location because
   those files are published by the same workflow as the page.
2. `.github/workflows/audit3-ledger.yml`: the `/audit` FTP block (which already
   writes `/audit/data/audit3_ledger.json`) now also stores the page as
   `/audit/audit3.html`. This block is used rather than `deploy_audit_files.py`
   because every `--only` group invoked anywhere in CI is `audit_data`, `updates`,
   `pick_funnel`, `incidents`, `ai_tournament` or `ai_leaderboard` — the
   `healthchecks` group is **never** run, so an entry there would have been dead
   configuration. It runs on the same 6-hourly cadence that rebuilds the page.

## Verified

* all four live URL status codes above re-checked with curl on 2026-11-22;
* the two patched `fetch()` calls confirmed absolute in the file;
* `python3 -c "import yaml; yaml.safe_load(...)"` on the edited workflow: OK;
* `python3 -m py_compile tools/deploy_audit_files.py` clean after removing the inert entry.

**Not verified:** the 200 on the new URL — that needs the next deploy to run, and
this machine holds no FTP credentials for it. The change is the publish list plus
a path fix; the first `audit-dashboard`/deploy run after merge proves it.
