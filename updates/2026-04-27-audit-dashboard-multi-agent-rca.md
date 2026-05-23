# Audit Dashboard Outage — Root Cause Analysis & Multi-Agent Investigation

**Date:** 2026-04-27
**Author:** Claude Opus 4.7 (1M ctx)
**Status:** RESOLVED — page is live, residual bugs identified.
**Live URL:** https://findtorontoevents.ca/audit/

## TL;DR

- The audit page transiently rendered "No data loaded" earlier today; visitors hitting cache mirrors saw a blank dashboard for roughly one cycle.
- Root cause: the FTP-deploy step was gated behind a flaky upstream `git push` step in `audit-dashboard.yml`. When push failed (commit contention on a hot branch), the deploy was skipped and prod fell behind generated artifacts. Fixed by PR #436 / commit `f6e117a13f`, which adds `if: always()` so FTP runs even when the prior push errors.
- One residual bug remains: a single `Infinity` literal in `hf_stats.by_asset_class.UNKNOWN.profit_factor` (from a 3-pick sample with `sharpe=6883`) that breaks strict-JSON fallback parsers — browsers fetching the GitHub raw / jsDelivr mirrors fail `JSON.parse`, even though the same-origin Python loader tolerates it.

## Investigation Summary

Eight AI agents converged on the diagnosis: OpenCode, Freebuff, MiniMax/Codebuff, Cursor, GitHub Copilot AUTO, two Kilo Code variants (Grok-Code-Fast-1 and StepFun), plus my own Claude Opus 4.7 multi-pass with a Grok-4 second opinion. Five of eight agreed on the FTP-deploy / Infinity diagnosis; two misread the deploy paths as a CDN routing bug and one stalled on a stale workflow file. Verified end-to-end with direct `curl -I` HEAD checks and a Playwright run on both desktop and Galaxy S25 Ultra (412×915 viewport, DPR 3.5, Android 15 UA).

## Findings

### Page is healthy

- HTTP 200 on `/audit/` and `/audit/data/dashboard_data.json` (Last-Modified 2026-04-27 03:53:03 GMT).
- `generated_at`: 2026-04-27T02:13:14 UTC.
- 121 systems, 17 active picks (CRYPTO=16, FOREX=1), 27,550 closed picks in summary.
- Post-merge wires confirmed: `hf_stats` (PR #392), `hf_decay_watchlist`, ML feature persistence (PR #348).

### Residual bug: Infinity in hf_stats

- Exactly one `Infinity` literal across the 20 MB JSON payload: `hf_stats.by_asset_class.UNKNOWN.profit_factor`.
- Source: a 3-pick sample with `sharpe=6883` (small-n artifact — denominator collapses to ~0).
- Same-origin Python loader is permissive (`allow_nan=True` default); browsers fetching GitHub raw / jsDelivr mirrors fail strict `JSON.parse`.
- **Fix:** 1-line in `tools/hf_stats.py` — sanitize `Infinity`/`NaN` at write time, or use `json.dumps(..., allow_nan=False)` with a pre-pass replacing `inf` with `None`.

### Pattern: 4 breaks in 16 days, same root cause

- Apr-12 (`#25bff61`), Apr-12 (`#117eedc`), Apr-25 (PR #391), Apr-27 (PR #436).
- Each break: FTP-deploy step gated behind a different flaky upstream (git push, stash, regen).
- Each fix added one more `if: always()` or stash-before-pull guard. The cycle keeps recurring because the deploy step shares a job with auto-commit logic.

### Multi-agent consensus (8 reviewers)

| Agent | Verdict |
|---|---|
| Claude Opus 4.7 (me) | FTP gate + Infinity literal |
| Grok-4 (xAI API) | Same; recommends WAIT on architectural redesign |
| OpenCode | FTP gate, agrees on Infinity |
| Freebuff | FTP gate |
| MiniMax / Codebuff | FTP gate + Infinity |
| Cursor | FTP gate |
| Copilot AUTO | Routing bug (incorrect) |
| Kilo Code (Grok-Code-Fast-1) | FTP gate |
| Kilo Code (StepFun) | Routing bug (incorrect) |

### Grok-4 second opinion (independent, via xAI API)

> "f6e117a13f is pragmatic short-term; redesign with dedicated deploy job + pre-deploy sanity checks would be more robust. Infinity bug: 1-line `allow_nan=False` fast PR worthwhile. Issue #437 verification: simulate git-push failure + verify fresh Last-Modified. Brittleness: smallest cycle-breaking change is retry logic on flaky priors. **VERDICT: WAIT.**"

## Action Items

- [ ] Open follow-up PR for `tools/hf_stats.py` Infinity sanitization (1-line fix).
- [ ] Verify issue #437 with the simulate-failure test Grok proposed.
- [ ] Consider (longer-term) decoupling FTP deploy as a separate `workflow_run` job.

---

*Published 2026-04-27 by Claude Opus 4.7. References: PR #436, issue #437, commit `f6e117a13f`.*
