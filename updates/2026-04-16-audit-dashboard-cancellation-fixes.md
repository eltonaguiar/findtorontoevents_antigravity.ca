# Fix: Audit Dashboard Chronic Cancellation — Three Targeted Fixes

**Date:** 2026-04-16  
**Author:** Codebuff (Buffy)  
**Based on:** Claude's investigation (`updates/2026-04-16-audit-dashboard-cancellation-investigation.md`)  
**Status:** Fixes applied; YAML validated; human review (Claude + Cursor) for factual accuracy  

---

## Problem

Every audit-dashboard run in the 24 hours prior was cancelled. The `/audit` site was stale for ~23 hours. Contributing factors: push storms on `main`, fragile git sync during the commit step, and **extra workflow runs** when the workflow file itself changed.

---

## Fix 1 (CRITICAL): Removed self-reference from push path triggers

**File:** `.github/workflows/audit-dashboard.yml` (comment block ~lines 64–68)

```yaml
# REMOVED from paths:
# - '.github/workflows/audit-dashboard.yml'
# Replaced with an explicit comment: do not list this workflow — self-trigger
# stacked queued runs and contributed to contention with cron + other pushes.
```

**Why:** Pushing a change that only touched `audit-dashboard.yml` used to **enqueue another** dashboard run. With `concurrency.group: dashboard-publish` and `cancel-in-progress: false`, GitHub keeps the running job but **limits queued work**; stacking self-triggered runs still wastes queue slots and competes with the hourly cron. Dropping the workflow from `paths` stops that. Cron + `workflow_dispatch` remain enough to ship workflow edits after merge.

---

## Fix 2 (HIGH): Removed `2>/dev/null` from the `git pull` merge command

**File:** `.github/workflows/audit-dashboard.yml` (~line 506)

The important change is **`git pull --no-rebase ...` no longer redirects stderr to `/dev/null`**, so merge failures show real errors in Actions logs. (`git merge --abort` may still be noisy; that is secondary.)

---

## Fix 3 (MEDIUM): Exponential backoff with jitter, capped at 120s

**File:** `.github/workflows/audit-dashboard.yml` (~lines 510, 535) — **inline push loop only**, not `.github/scripts/safe_push.sh` (that script keeps its own doubling backoff).

```bash
# Before (linear; pre-merge-strategy parent of commit 28a2890112):
delay=$((i * 10 + RANDOM % 15))

# After (exponential with jitter, capped at 120s + jitter):
delay=$((2 ** i + RANDOM % 10)); [ $delay -gt 120 ] && delay=$((120 + RANDOM % 10))
```

**Why:** Under heavy concurrent pushes, longer tails on later attempts help. Cap avoids burning the job `timeout-minutes`.

**Worst-case total sleep if every attempt hits the maximum delay (upper bound):**  
For attempt index `i`, delay is at most `min(2**i + 9, 120 + 9)` seconds (worst jitter). Summing `i = 1..10`:  
`11 + 13 + 17 + 25 + 41 + 73 + 129 + 129 + 129 + 129 = 696` seconds (~11.6 minutes) of backoff alone (four capped steps for `i = 7..10`, each `120 + 9` max).  
(The loop has separate merge-failure and push-failure sleeps; this is the scale if one side fails repeatedly.) Earlier drafts (~4.5 min, or `120*3`) understated this; ~9.6 min also understated by omitting the fourth capped step (`i = 7..10`).

---

## Fix 4 (documented): `tools/stamp_audit_deploy.py` on push paths

**File:** `.github/workflows/audit-dashboard.yml` line ~59  

The same commit that shipped the cancellation fixes **added** `'tools/stamp_audit_deploy.py'` to `on.push.paths` so edits to the deploy-stamp helper trigger a dashboard run. This was easy to miss in summaries because the commit title emphasized forward_test + cancellation. It is **intentional**: keep stamp logic and publish pipeline in sync.

---

## Additional Findings (not fixed yet)

### Workflows lacking `[skip ci]`

Many workflows commit to `main` without `[skip ci]`, which increases push races. Example list: `alpha-engine-fast.yml`, `alpha-engine-live.yml`, `alpha-gainer-capture.yml`, `battle_test.yml`, `breakout-arena.yml`, `2hour_challenge.yml`, `backfill.yml`, `backfill-features.yml`, `coinglass-scanner.yml`, `cross-aggregator.yml`, `claude-gainer-ml-live.yml`, `copytrader-tracker.yml`.

**Recommendation:** Add `[skip ci]` to data-only bot commits where appropriate.

### Forward Test Daily

`STOCKS/competition/forward_test.py` `KeyError: 'ticker'` — see `updates/2026-04-16-forward-test-keyerror-ticker-fix.md`.

---

## Verification

- YAML: `python -c "import yaml; yaml.safe_load(open('.github/workflows/audit-dashboard.yml'))"` → OK  
- Old backoff confirmed: `git show 28a2890112~1:.github/workflows/audit-dashboard.yml` shows `delay=$((i * 10 + RANDOM % 15))`  
- **Review:** Corrections above reflect Claude + Cursor pass; an automated `code-reviewer-lite` run was **cancelled** in an earlier session and must not be cited as “approved.”

**Note:** Backoff in **`audit-dashboard.yml`** is separate from **`safe_push.sh`** (`INITIAL_BACKOFF=2`, `MAX_BACKOFF_SLEEP=120`). Aligning them is optional.

**Note:** `python3 .github/scripts/verify_dashboard_publish_consistency.py || true` remains non-fatal by design (best-effort gate).

---

## Errata (original MD draft — do not resurrect)

1. **Date:** Draft said 2026-04-19 while workspace calendar was 2026-04-16.  
2. **Old backoff:** Draft mis-quoted `i * 3 + RANDOM % 5`; actual pre-change was `i * 10 + RANDOM % 15`.  
3. **Worst-case sleep:** Draft ~4.5 min then ~9.6 min; upper bound is **~11.6 min** (see formula above).  
4. **“Code reviewer approved”:** Draft implied a completed automated review; **code-reviewer-lite was cancelled** mid-flight — misleading.  
5. **Conflict-hatch generator:** Prefer **not** hiding stderr during recovery. Workflow uses `python -m audit_trail.dashboard_generator 2>&1 || true` (stderr merged to stdout for CI logs) instead of `2>/dev/null`.
