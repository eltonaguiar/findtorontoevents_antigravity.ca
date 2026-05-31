# CRYPTO Resolver Lag — Root Cause Analysis (2026-05-31)

## Symptom

`audit_dashboard/data/pick_summary_stats_48h.json` reports for CRYPTO:

| field          | value |
|----------------|-------|
| n_touched      | 310   |
| n_active       | 310   |
| n_closed       | 0     |
| n_decisive     | 0     |
| wins / losses  | 0 / 0 |
| top opened_at  | 2026-05-29T06:22:28 (≈48h before snapshot) |

Active picks are clustered tightly on 2026-05-29 — they should be aging
into TP/SL transitions, but zero have resolved in the 48h window.

## Root Cause

Two overlapping defects in `alpha_engine/active_picks_sync.py:fetch_active_picks`
combined to starve the newest CRYPTO cohort of resolver attention:

1. **Window too small (FIXED in PR #87, c2f6326b4).** Default `max_rows=5000`
   against ~39,706 OPEN CRYPTO rows. Workflow runs prior to PR #87 used the
   default. Verified: GHA run `26697883604` (sha `8dd8eada`) command printed
   `python -m alpha_engine.active_picks_sync --asset-class CRYPTO --max-symbols 200 --apply`
   with **no `--max-rows`**, and the log line `# active_rows_fetched=5000`
   confirmed the cap was hit. PR #87 landed at `c2f6326b4` and added
   `--max-rows 20000` to the workflow's `for AC in CRYPTO EQUITY ...` loop.

2. **ORDER BY ASC (NOT YET FIXED on `main` as of this report).**
   `alpha_engine/active_picks_sync.py:114` is `ORDER BY signal_timestamp ASC`,
   so the fetched window is filled oldest-first. With 39,706 OPEN CRYPTO
   rows the 5000 cap cut off around 2026-04-07 — every pick dated after
   that (including the 310 May-29 cohort visible in `pick_summary_stats_48h`)
   was invisible to the resolver. Even with PR #87's `--max-rows 20000` the
   resolver still resolves the oldest 20000 first; if the legacy backlog
   exceeds 20000 the newest picks remain starved.

The workflow YAML comment at `.github/workflows/audit-dashboard.yml:351-352`
explicitly flagged this as the next step:

> follow-up: switch the ORDER BY in alpha_engine/active_picks_sync.py:114
> to DESC so newest picks resolve first. Resolves FINDING_CRYPTO#1.

That follow-up has not been merged. This PR ships it.

## Evidence

- GHA run id: `26697883604` (workflow `audit-dashboard.yml`, head sha
  `8dd8eada`, completed 2026-05-30T23:33:50Z).
- Workflow command echoed in logs:
  `python -m alpha_engine.active_picks_sync --asset-class CRYPTO --max-symbols 200 --apply`
- Resolver self-report from same step:
  `# active_picks_sync DRY-RUN — asset_class=CRYPTO win_threshold=0.001 max_hold_hours=48`
  `# active_rows_fetched=5000`
  `# unique_symbols=177 (capped at 200)`
- 310 active CRYPTO picks dated 2026-05-29 in
  `audit_dashboard/data/pick_summary_stats_48h.json` → all opened_at ≥
  2026-05-29T00:59:32, none in the oldest-5000 window.
- `n_closed=0`, `n_decisive=0` confirms the resolver did not touch a
  single one in the last 48h.

The 5bp / 0.1bp `PNL_WIN_THRESHOLD_BY_CLASS` and the `MAX_HOLD_HOURS=48`
crypto floor are correct and not implicated; this is a *visibility*
defect (which picks reach the resolver), not a *decision* defect (how
the resolver classifies them).

## Fix

`alpha_engine/active_picks_sync.py:114`:
```python
-        ORDER BY signal_timestamp ASC
+        ORDER BY signal_timestamp DESC
```

Combined with PR #87's `--max-rows 20000`, every pick newer than the 20000th
will resolve first on each hourly sync. The legacy ASC-era backlog (older
than ~Apr 7) can be flushed by a one-time backfill (out of scope for this
PR) without blocking the hot path.

## Expected Impact

- 310 active May-29 CRYPTO picks will be fetched by the next hourly run.
- 48h-window `n_closed` should rise from 0 to a non-zero number within
  one resolver cycle (TP/SL transitions for the cohort, plus
  `EXPIRED_MAX_HOLD` for any that have aged past 48h).
- Long term: aligns the resolver with the dashboard's 48h / 14d recency
  panels (which are the panels promoted by `money_ready_verdict` and
  the post-M-067 policy-clean cohort).

## Out-of-Scope (Follow-ups)

- One-time backfill resolver pass for the 39,706 ASC-era backlog (probably
  a `tools/backfill_resolver_oldest.py` invocation outside the hourly
  workflow).
- Concentration gate enforcement before DSR/SPA (P0 open per CLAUDE.md
  — not relevant to this lag).
- Reconcile `78.9% CRYPTO Smart-Picks` vs raw-DB `39% WR / PF 0.37`
  (separate leakage investigation per `c1b977997`).
