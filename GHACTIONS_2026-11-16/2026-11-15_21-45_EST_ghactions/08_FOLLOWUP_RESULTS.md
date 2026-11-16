# 08 — Follow-up Results II (safe_push hardening, feed wiring, R7 re-diagnosis)

**STAMP:** 2026-11-15_21-45_EST_ghactions · work window 04:41–04:50 UTC. Companions: `05`, `06`, `07`
(same folder). All batches: fix + doc together, per-file `git checkout <pre-sha> -- <path>` reverts,
`backup/gha-audit-2026-11-16` anchor.

## 1. safe_push routing (20 sites / 19 workflows) — LANDED

9 bare pull/push sites + 9 `|| echo` success-masks routed through `.github/scripts/safe_push.sh`
(8× pull-rebase-retry); `swarm-sync-v2` deliberately kept its explicit rebase-**abort** guard with a
3-attempt retry loop instead (safe_push's `-X theirs` would defeat its corruption protection);
`continue-on-error` removed from `ai-model-portfolios-daily`'s "Commit PF JSON snapshots" step
(daily PF snapshots can no longer vanish silently). Manifest: `2026-11-16_04-50_EST_ghactions/
safe_push_manifest.tsv`. Post-fix note: `sign-coherence-gate`'s commit step was already on
safe_push; its remaining issue was the timer (§3).

## 2. Prediction-market + theory-tracker feed wiring — LANDED (answers "are our fixes feeding?")

- `pm_polymarket_re_signals` + `pm_kalshi_re_signals` registry entries (alpha_engine reverse-engineered
  feeds — previously deployed-but-never-ingested) + 2 `universal_pick_resolver` SYSTEM_SOURCES entries
  so outcomes settle. Paper-flagged, existing keys untouched (no double-ingest). 195 resolver tests green.
- Theory/hypothesis trackers: `tools/build_theory_tracker_sidecar.py` (strict JSON, NaN-backstopped)
  → `audit_dashboard/data/theory_tracker.json` + freshness tile + "🧪 Theory / Hypothesis Tracker" panel
  + deploy entry + builder wired into `portfolio-trackers.yml` (daily build+commit → hourly deploy ships).
  6 new tests (351 green across the round).

## 3. R7 "external mass-cancel" — RE-DIAGNOSED (correction to 06 §2 R7 + earlier reports)

Run-level attribution (kill points + per-head_sha config verification) **refutes an external
canceller entirely** (zero cancel/delete API calls repo-wide; guardian is rerun-only; janitor is
SQLite-only; no GitHub incident in window). The real mechanics:

| Mechanism | Evidence | Where it hit |
|---|---|---|
| **`timeout-minutes` kills surface as `cancelled`**, not `timed_out` | exact +5m05s/+10m06s/+15m04s lifetimes, repeated daily | blacklist (5m, checkout stall), swarm-pick (10m), **sign-coherence (15m, "Commit JSON report" git-push stall 14m33s nightly)** |
| **Concurrency pending-slot eviction** via shared `dashboard-publish` group | rsi5070 0-jobs-ever-started, killed when audit-dashboard's hourly :10 run arrived | rsi5070 (group already renamed in a prior fix; `operator-review-today` likewise — verified live groups unique now) |
| **Push-wave `cancel-in-progress` stack-kills + PR-close auto-cancel** | true same-second batches (dup-guard 10-run stacks) | branch-push workflows |

**Measurement corrections (important):**
1. The "identical timestamps across unrelated workflows" pattern = victims' **`created_at` cron-herd
   stamps**, NOT cancel stamps. Bucket by `updated_at` + fetch `runs/<id>/jobs` (0 jobs = eviction;
   exactly-N-min = timeout). `06` §2 R7 rule must be re-read this way.
2. **"strategy-tribunal 12/15 cancelled" REFUTED** — run-ID-level API shows 22/22 SUCCESS
   (2026-06-19→11-13). The bad figure traces to the early bulk-window sampling (same class as the
   "235 stale" artifact). Treat the tribunal box as healthy; its `strategy_tribunal_latest.json`
   simply wasn't deployed (fixed in 07 batch).

## 4. This round's residual fix — LANDED

`sign-coherence-gate.yml` `timeout-minutes: 15 → 30` (its nightly 14m33s commit-stall was one
25-second nudge from killing the run; safe_push already in place). `blacklist` checkout left as-is:
`fetch-depth: 0` + `filter: blob:none` is deliberate and its post-timeout-fix runs are green.

## 5. Verification map (what each fix's next run proves)

| Fix | Next-run proof |
|---|---|
| safe_push ×20 | next non-FF race lands data instead of dropping it; no more "green + no push"; watch nightly commit steps (sign-coherence 04:48, blacklist 04:03, swarm-pick 03:48) |
| PM feeds ingest | next `audit-dashboard` regen shows `pm_*_re_signals` rows in active_raw + system cards |
| Theory tracker | `portfolio-trackers` daily run produces sidecar; panel + tile light after hourly deploy |
| sign-coherence 30m | tonight's 04:48 run completes (was dying at 15m) |
| 07 batch (strict-JSON, JS rescue, banner, IC retire) | 05:03 regen + deploy — verified at the 05:07 wakeup |

Watchers: 05:07 wakeup · 08:00 monitor cron · 08:37 first scheduled `gha-health-audit` (its R1–R12
report lands in `GHACTIONS_LIVE/`).
