---
name: gha-run-log-deep-scan
description: Run the repo’s GitHub Actions log deep scan (latest run per workflow + prior run when latest failed). Use when the user wants to audit CI logs, check for symbol/quote errors, stale payloads, git push failures, or run /gha-deep-scan-run-logs.
---

# GHA run log deep scan

## What it does

- Discovers workflows from recent activity on `main` (default: last **24h**, **250** newest runs, capped per `--max-workflows`).
- For each workflow: fetches **`gh run list -w … --limit 2`**.
- Always analyzes the **latest** run; if it is **`completed`** and **not** `success`/`skipped`, also analyzes the **previous** run.
- Pulls **`gh run view --log-failed`**; if empty, tails full **`--log`**.
- Highlights lines matching built-in patterns (tracebacks, 404 quote errors, `fatal:`, stale payload, Binance 451, etc.).
- Writes **`docs/GHA_DEEP_SCAN_LATEST_PRIOR.md`** (or shard parts + merge).

## Commands (repo root)

```powershell
python tools/gha_latest_prior_log_scan.py --out docs/GHA_DEEP_SCAN_LATEST_PRIOR.md
```

Parallel shards + merge: see **`.cursor/commands/gha-deep-scan-run-logs.md`**.

## Agent behavior

1. Run the scanner; confirm exit code 0.
2. Summarize findings from the generated Markdown; call out data-loss risk (e.g. quote/symbol not found) and publish blockers (git errors).
3. Do not apply code fixes unless requested.
4. Commit/push the report only if the user asks.

## Files

| Path | Purpose |
|------|---------|
| `tools/gha_latest_prior_log_scan.py` | Main scanner |
| `tools/gha_merge_deep_scan_parts.py` | Merge shard outputs |
| `docs/GHA_DEEP_SCAN_LATEST_PRIOR.md` | Merged report output |
