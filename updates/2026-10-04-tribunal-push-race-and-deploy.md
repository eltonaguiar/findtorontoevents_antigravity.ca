# /audit `strategy_tribunal_latest.json` 404 — push race + missing deploy

**Date:** 2026-10-04
**Found via:** live Playwright audit of `https://findtorontoevents.ca/audit/`

## Symptom

The `/audit` page fetches `./data/strategy_tribunal_latest.json` (template line
978). The live URL returned **HTTP 404**, the "Strategy Kill Tribunal" panel
rendered its fallback ("No tribunal report yet…"), and the console logged:

```
HTTP 404 https://findtorontoevents.ca/audit/data/strategy_tribunal_latest.json
```

## Root cause (two independent gaps)

1. **The report never reached `main`.** `strategy-tribunal.yml` runs weekly and
   *succeeds* (last run 2026-10-02). Its script writes
   `audit_dashboard/data/strategy_tribunal_latest.json`, and the "Commit report"
   step stages it. But the push used:

   ```bash
   git push || echo "push skipped (race ok)"
   ```

   With this repo's high-frequency auto-committers, that push races constantly
   and **silently discards the commit** on failure. Evidence: neither
   `audit_dashboard/data/strategy_tribunal_latest.json` **nor**
   `reports/strategy_tribunal_*.json` is present on `main` at all — every weekly
   tribunal commit has been lost.

2. **It was never in the deploy set.** Even once committed, nothing uploads it:
   `tools/deploy_audit_files.py` (the 50webs FTPS uploader used by the audit
   pipeline) has no entry for it.

## Fix

- `strategy-tribunal.yml`: replaced the naive push with
  `bash .github/scripts/safe_push.sh` — the repo-standard race-robust pusher
  (fetch `--deepen` + `pull --rebase -X theirs` + exponential backoff) already
  used by 10+ workflows.
- `tools/deploy_audit_files.py`: added
  `audit_dashboard/data/strategy_tribunal_latest.json` →
  `/audit/data/strategy_tribunal_latest.json` (tag `audit_data`; a local-missing
  source is a SKIP, so it's safe when the report hasn't been generated yet).

## Verification

- `python3 -c "import yaml,yaml.safe_load(open('.github/workflows/strategy-tribunal.yml'))"` → parses.
- `python3 -m py_compile tools/deploy_audit_files.py` → OK; the new entry is present.

## Notes

The template already degrades gracefully on a missing file, so the 404 was
non-fatal — but the tribunal panel has effectively never worked on the live site
because of (1). After this change the next Friday run will land the report on
`main` and the following audit-dashboard deploy will publish it.
