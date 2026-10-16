# Winner-hunt STA-09 monthly replay — cron spec (2026-06-22)

**Date:** 2026-06-22
**Branch:** ship directly to main (no worktree — the prior operator-review panel was stranded in the gitignored `.claude/worktrees/`, avoid that trap)
**Spec lineage:** sister to `updates/2026-06-22-operator-review-today-panel.md` (daily cadence); close cousin of `updates/2026-06-22-winner-hunt-rsi5070-only.md` (the parent verdict this cron replaces the manual hunt with).

---

## What

A monthly GitHub Actions cron that re-runs the same STA-09 hunt recipe that produced `updates/2026-06-22-winner-hunt-rsi5070-only.md`, and auto-commits the cycle's verdict to `updates/YYYY-MM-DD-winner-hunt-replay.md` (append-only — one new file per monthly run). The hunt itself stays hand-runnable today (until this cron lands on the next month's 1st-of-month); the cron replaces the *manual walk* going forward so the operator doesn't have to re-run + diff + alert when rsi5070 nears the `n >= 150` promotion bar.

Two GHA groupMarkers may fire on each cycle:
- `::error::` — `crypto_rsi5070_us.n >= 150` (the lead crossed the promotion bar)
- `::warning::` — a fresh cell appears net-positive at FDR-pass, NOT in the curated 6, NOT in last cycle's baseline

Either alert is a meaningful event; the operator reviews. The default case is `::notice::` "no alerts; lead still accruing".

---

## Files

| Path | State | What it does |
|---|---|---|
| `.github/workflows/winner-hunt-replay.yml` | NEW | Monthly cron `0 8 1 * *` UTC + workflow_dispatch. Concurrency group `winner-hunt-replay` (sister of `monthly-tournament` + `monthly-calibrator-refit`); cancel-in-progress=false. Steps: checkout + install python + run `stamp_entry_conditions.py --stdout --limit 6000 \| tee /tmp/staff.json` + run `mine_entry_condition_cells.py --limit 6000 > /tmp/mine.json` + run `build_winner_hunt_replay.py --apply` + schema gate on payload + schema gate on verdict doc + commit + 5x retry push loop. |
| `tools/build_winner_hunt_replay.py` | NEW (~15KB) | Reads `/tmp/staff.json` + `/tmp/mine.json` (artifacts the cron just wrote); reads canonical `audit_dashboard/data/crypto_rsi5070_us_forward_status.json` + `entry_conditions_forward.json::conditions`; reads prior `winner_hunt_replay_payload.json` (drift baseline). Computes lead status (`passed_n150` boolean) + fresh cells (cells outside curated 6 + outside prior baseline that pass FDR + net_pf ≥ 1.5 + n ≥ 30) + drift table (added/lost cells vs prior cycle). Writes `audit_dashboard/data/winner_hunt_replay_payload.json` + `updates/YYYY-MM-DD-winner-hunt-replay.md`. Args: `--apply`/`--stdout`/`--strict`/`--skip-md`. |
| `updates/2026-06-22-winner-hunt-replay-cron.md` | NEW (this file) | Sister spec — the cron doc the operator reads when they need to understand what the workflow does. |
| `updates/YYYY-MM-DD-winner-hunt-replay.md` | GENERATED (per cycle) | Append-only verdict doc. Format is fixed by `_render_md()` in the build script: §Alerts · §Lead status · §Fresh cells · §Drift vs prior cycle · §Verdict · §Maintenance. |

The 4th file (`updates/YYYY-MM-DD-winner-hunt-replay.md`) is **generated per cycle**. The cron opens a brand-new MD each month (today's filename would be e.g. `updates/2026-07-01-winner-hunt-replay.md`); old MDs are NEVER overwritten.

---

## Why

Today, the operator's only path to "is rsi5070 still the lone survivor?" is to manually run the two hunt scripts, diff against the prior verdict, decide whether the verdict changed. That's a 10-minute walk per cycle. As `crypto_rsi5070_us.n` accrues toward the `n >= 150` promotion gate (currently `n=108`, ETA `~2026-06-25` per the forward-status verdict note), the cell may cross the bar MONTHLY — at which point the operator needs to:

1. Re-run R1/R2/R3 gates per `tools/crypto_rsi5070_forward_tracker.py`
2. Manually edit `audit_trail/quality_gates.py` to lift the `SHADOW_TRACKING` flag if all gates pass
3. Update the standing verdict doc with the new state

The cron automates the *retrieval* part (steps 1 prep + verdict-doc generation) so the operator walks in to find:

- A new `updates/$TODAY-winner-hunt-replay.md` telling them whether the lead crossed the gate
- A `::error::` groupMarker on the GHA run summary if so
- A drift table showing whether the top-N set changed from last month

…and only then opens the live JSONs to verify.

---

## Cron schedule + sequencing

| Time (UTC, monthly 1st) | Workflow | Concurrency group | Why |
|---|---|---|---|
| 06:00 | `monthly-tournament.yml` | `monthly-tournament` | DNA tournament runs first; winner-mutations + symbol-predictability land on disk. |
| 07:00 | `monthly-calibrator-refit.yml` | — (no concurrency block) | M-060 confidence calibrators refit every class; takes a few minutes. |
| 08:00 | `winner-hunt-replay.yml` | `winner-hunt-replay` | This cron. Runs AFTER both upstream jobs so `audit_dashboard/data/entry_conditions_forward.json::conditions.crypto_rsi5070_us` reflects all upstream state. |
| (hourly `'10 * * * *') | `audit-dashboard.yml` | `dashboard-publish` | Different concurrency group — no contention with this cron. |

The `winner-hunt-replay` concurrency group is separate from `dashboard-publish` to avoid contention with the audit-dashboard hourly cycle which sometimes runs 35-minute-deep mid-month.

**Manual dispatch:**
```bash
# Normal mode: same-cycle rerun; skipped if byte-identical to the prior payload
gh workflow run winner-hunt-replay.yml --ref main
# force=true : smoke-test path; commits even if the payload is byte-identical
gh workflow run winner-hunt-replay.yml --ref main -f force=true
# force=true + time_suffix=<label> : same-day rerun produces a sibling MD
# instead of overwriting; populates WINNER_HUNT_TIME_SUFFIX on the build step
gh workflow run winner-hunt-replay.yml --ref main \
    -f force=true \
    -f time_suffix=test-retry
# Example: smoke-test the cron end of July BEFORE the real 2026-08-01 cycle:
gh workflow run winner-hunt-replay.yml --ref main \
    -f force=true \
    -f time_suffix=smoke-2026-07-15
```

The `time_suffix` input (string, default empty) populates `WINNER_HUNT_TIME_SUFFIX` on the build step; the verdict MD filename becomes `updates/${TODAY}-winner-hunt-replay-${SUFFIX}.md` instead of clobbering the cron cycle's MD. **Without `time_suffix`, a same-day `force=true` rerun overwrites the cron MD verbatim** — operators running `force=true` against a date the cron has already landed MUST add `time_suffix` to keep both records.

---

## Alert detection rules

### Rule 1 — `::error::` PROMOTE THE LEAD (alert_paths.promote)

```python
alert_paths["promote"] = bool(
    lead["n"] is not None and lead["n"] >= 150
)
```

Read the lead's `n` from `audit_dashboard/data/crypto_rsi5070_us_forward_status.json::n` (canonical, refreshed hourly by `tools/crypto_rsi5070_forward_tracker.py`). Fallback: `audit_dashboard/data/entry_conditions_forward.json::conditions.crypto_rsi5070_us.n` (per-cell live, refreshed when `stamp_entry_conditions.py` is run).

When this alert fires, the operator's workflow is:
1. Re-run R1/R2/R3 gates per `reports/entry_conditioning_experiment_2026-06-10.json`
2. If all promotion gates pass (`net_ci_lb > 1.15 AND n_eff >= 80 AND n >= 150 AND OOS >= 1.0 AND conc < 35%`), edit `audit_trail/quality_gates.py` to remove `SHADOW_TRACKING`
3. Update `updates/2026-06-22-winner-hunt-rsi5070-only.md`'s section 2 to record the promotion

### Rule 2 — `::warning::` FRESH LEAD CANDIDATE (alert_paths.new_cell)

```python
for c in mine.fdr_passing_net_pf_ge_1_5:
    if c["cell"] in curated_keys or c["cell"] == LEAD_CELL_KEY: continue
    if c["cell"] in prior_baseline_keys:                    continue
    if c["n"] >= 30 and c["net_pf"] >= 1.5 and c["fdr_pass"]:
        new_cells.append(c)
```

A cell "fresh" means: it appears in `mine.json::fdr_passing_net_pf_ge_1_5` AND it is NOT in today's curated 6 (`staff.json::conditions`, excluding baseline_* keys) AND it is NOT the lead cell AND it was NOT in last cycle's `payload.new_cells` baseline (DRY-undiff against the drift table).

When this alert fires, the operator's workflow is:
1. Pull the cell from `/tmp/mine.json` (or `audit_dashboard/data/winner_hunt_replay_payload.json::new_cells` after commit)
2. Add it to tomorrow's `tools/operator_review_seed.json` as a hand-curated sidecar candidate (visibility only — does NOT bypass M-036 / M-036b)
3. Run `tools/crypto_rsi5070_forward_tracker.py --new-cell=$KEY` to spawn a forward-tracker sibling for it

### Default — `::notice::` no alerts

When neither rule fires, the build script emits only `::notice::` (no color, no escalation). This is the common case for ~6 more months as rsi5070 accrues n toward 150.

---

## Drift vs prior cycle

The payload includes a `drift_table` array listing cells that:
- **added_cell** — in current cycle's `new_cells` but were NOT in prior cycle's `new_cells`
- **lost_cell** — in prior cycle's `new_cells` but NOT in current's

This is the operator's "did the field shift?" signal. If `add_cell` and `lost_cell` are both empty for N months in a row, the field is stable and the operator can move the cron to quarterly or skip a cycle.

Baseline storage: the **prior** cycle's `winner_hunt_replay_payload.json` is read at the start of each cycle; the **current** cycle overwrites it on commit. The MD verdict doc's §4 surfaces the drift table to humans.

---

## Append-only history pattern

| Cycle | File | Lifecycle |
|---|---|---|
| 2026-06-22 | `updates/2026-06-22-winner-hunt-rsi5070-only.md` | MANUAL — the stand-cell that inspired this cron. NOT generated by the cron. |
| 2026-07-01 | `updates/2026-07-01-winner-hunt-replay.md` | First cron-generated cycle. |
| 2026-08-01 | `updates/2026-08-01-winner-hunt-replay.md` | Append-only. |
| ... | ... | ... |
| 2027-06-01 | `updates/2027-06-01-winner-hunt-replay.md` | After 12 months, ~12 small MD files (~5KB each); ~60KB/year. Acceptable. |

Files are NEVER edited retroactively; cron only `git add` for the new file plus the `winner_hunt_replay_payload.json` overwrite. `git diff --cached --quiet` skips the push if both files hash-equal HEAD (= same-cycle rerun with no real change), unless the operator dispatches with `force=true`.

---

## What the cron does NOT do

To preserve DRY + the M-036/M-036b gates, the cron:

- **Never** mutates `audit_dashboard/data/crypto_rsi5070_us_forward_status.json` — owned by `tools/crypto_rsi5070_forward_tracker.py`
- **Never** mutates `audit_dashboard/data/entry_conditions_forward.json` — owned by the live `stamp_entry_conditions.py` cron (hourly-adjacent, not this one)
- **Never** writes to `tools/` — the build script + hunt scripts are read-only from this cron's perspective
- **Never** updates `audit_trail/quality_gates.py` even when `::error::` fires — the promotion is a HUMAN action because lifting `SHADOW_TRACKING` requires R1/R2/R3 re-validation that's out of band for a read-only cron
- **Never** overrides M-036/M-036b — the cron is a discovery lane; if a fresh cell surfaces, it lands on the operator-review sidecar next pass, NOT in the production sizing funnel

---

## References (canonical sources — DO NOT duplicate data here)

| Path | What it is |
|---|---|
| `tools/stamp_entry_conditions.py` | The curated-6 stamper (run with `--stdout --limit 6000`) |
| `tools/mine_entry_condition_cells.py` | The exhaustive + FDR sweep (run with `--limit 6000`) |
| `tools/build_winner_hunt_replay.py` | The build script this cron invokes (`--apply`/`--stdout`/`--strict`/`--skip-md`) |
| `tools/crypto_rsi5070_forward_tracker.py` | Lead-cell forward-tracker; owns `crypto_rsi5070_us_forward_status.json` |
| `audit_dashboard/data/entry_conditions_forward.json::conditions` | Live per-cell cohort stats — `crypto_rsi5070_us` is the lead |
| `audit_dashboard/data/crypto_rsi5070_us_forward_status.json` | Canonical lead verdict trail (n, wr_pct, net_pf, status, failing_gates) |
| `audit_dashboard/data/winner_hunt_replay_payload.json` | This cron's per-cycle payload + the drift baseline for next cycle |
| `updates/2026-06-22-winner-hunt-rsi5070-only.md` | Parent verdict — "rsi5070 is the lone lead"; the cron replaces manual re-runs of this hunt |
| `updates/2026-06-22-operator-review-today-panel.md` | Sister spec — the daily sidecar panel; fresh-cell surface from this cron |
| `.github/workflows/operator-review-today.yml` | Daily sister. Concurrency-template (concurrent-group + cancel-in-progress + 25min timeout) |
| `.github/workflows/monthly-tournament.yml` | Monthly cadence precedent (cron `0 6 1 * *` + concurrency `monthly-tournament`) |
| `.github/workflows/monthly-calibrator-refit.yml` | Monthly cadence precedent (cron `0 7 1 * *`) — defines the 1st-of-month UTC sequencing this cron relies on |
| `reports/entry_conditioning_experiment_2026-06-10.json` | R1/R2/R3 promotion-gate spec — when an `::error::` fires, the operator runs from here |
| `audit_trail/quality_gates.py` | Editable only by humans via promotion workflow (NOT by this cron) |
| `tests/test_no_winner_hunt_replay_consumer.py` | NEW — pre-merge contract: any *.py under tools/ + audit_trail/ + alpha_engine/ that reads winner_hunt_replay_payload.json MUST reference winner_hunt_replay_only OR carry # allowed: winner-hunt-replay consumer. Mirrors the operator-review contract discipline for the alert-data sidecar. |

---

## Maintainer checklist

When updating this file in the future:

1. **Never** inline `/tmp/staff.json` / `/tmp/mine.json` tables — re-sweep and re-link.
2. **Always** cite the canonical live-data path (`audit_dashboard/data/crypto_rsi5070_us_forward_status.json::n` for the lead).
3. **Always** cross-link `updates/2026-06-22-operator-review-today-panel.md` if discussing the daily sidecar.
4. **Always** cross-link `updates/2026-06-22-winner-hunt-rsi5070-only.md` (§6 Forward tracking) — the parent verdict's monthly cadence line.
5. When the lead actually crosses `n >= 150`, *update* section 5 (Alert Rules) of this doc to record the actual gate-cross date; *don't* invent a new spec doc, just edit this one.
6. If a fresh-cell alert fires, the next cycle's MD verdict doc captures the (now non-fresh) cell in its `drift_table` `added_cell` row — promote-by-addition, do not re-write history.
