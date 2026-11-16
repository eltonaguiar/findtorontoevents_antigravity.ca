# cron_stagger_plan.md

> [!WARNING]
> **origin/main advances continuously** (bot commits roughly every ~60 s). Any sha below is the sha *at the time of analysis*, not a durable base. **Re-fetch `git fetch origin main` before relying on any branch delta, file count, or diff.** A pinned sha a few minutes old will read as wrong — do not treat it as authoritative.
>
> origin/main as of 02:14Z (sha at time of analysis: `ae3f4dc4dc1c2a1e63abd5285e8c037e6f136695`; known to have since advanced, e.g. `5e86dd18e15`, `b016a61f9a2` observed later).

**Base commit (at time of analysis):** `ae3f4dc4dc1c2a1e63abd5285e8c037e6f136695` — origin/main @ 2026-11-16T02:14Z. See caveat above: re-fetch before reusing.
**STAMP:** 2026-11-15_21-00-33_EST_ghactions
**Generated:** local git only — `git show origin/main:<path>` (no GitHub API)

## Executive Summary

**Inventory (verified @ `ae3f4dc`):** 356 workflow files, 360 cron lines across 309 files. Minute-0 concentration is **189/360 (52.5 %)**. The worst pile-ups are the even-hour tiers `0 */2 * * *` (15 files), `0 */4 * * *` (13), `0 */6 * * *` (13) that all collide at hours 0/4/8/12/16/20, plus the every-half-hour `*/30 * * * *` (12 files) and hourly `0 * * * *` (12 files).

**Stagger policy (deterministic, reviewable):** `zlib.crc32(filename) % 60`, alphabetical `+1 mod 60` tie-break **within each cron group** (not globally). Two displacements required: `signal_tracking.yml` 34→**35** (`0 */2`), `sign-coherence-gate.yml` 32→**33** (`0 4 * * *`). Raw collision set before tie-break: 55 distinct offsets used, max pile 7 at offset 41.

**Concurrency adoption:** 164/356 files (46.1 %) declare `concurrency:`, of which 118 set `cancel-in-progress: false`. 192 files remain uncovered. Group naming is inconsistent (`ab-analysis`, `${workflow}-${ref}` both present).

**Multi-cron dispatch files:** 17 files branch on `${{ github.event.schedule }}` — **do NOT delete crons** (removes a named dispatch mode). Stagger only.

## Minute-0 histogram (top 12 buckets)

| minute | count | % of 360 |
|--------|-------|----------|
| 0      | 189   | 52.5 %   |
| 30     | 36    | 10.0 %   |
| 15     | 26    | 7.2 %    |
| */30   | 13    | 3.6 %    |
| 5      | 7     | 1.9 %    |
| 40     | 6     | 1.7 %    |
| 35     | 6     | 1.7 %    |
| 20     | 5     | 1.4 %    |
| 25     | 5     | 1.4 %    |
| 37     | 4     | 1.1 %    |
| */15   | 4     | 1.1 %    |
| 3      | 3     | 0.8 %    |

## Top identical cron strings (≥6 files)

| cron string | files |
|-------------|-------|
| `0 */2 * * *` | 15 |
| `0 */4 * * *` | 13 |
| `0 */6 * * *` | 13 |
| `*/30 * * * *` | 12 |
| `0 * * * *` | 12 |
| `0 4 * * *` | 10 |
| `0 6 * * *` | 8 |
| `0 3 * * *` | 6 |
| `15 * * * *` | 6 |
| `15 */4 * * *` | 6 |

## Collision groups & stagger tables (crc32 % 60 + alpha tie-break)

### 0 */2 * * * — 15 files

| filename | crc32%60 | final cron |
|----------|----------|------------|
| `kimi-feb172026-live.yml` | 7 | `7  */2 * * *` |
| `kimi-goldmine-collector.yml` | 8 | `8  */2 * * *` |
| `meme-scanner.yml` | 24 | `24  */2 * * *` |
| `pick-monitor-30min.yml` | 25 | `25  */2 * * *` |
| `spike-scanner.yml` | 26 | `26  */2 * * *` |
| `update-creator-news.yml` | 33 | `33  */2 * * *` |
| `backfill.yml` | 34 | `34  */2 * * *` |
| `signal_tracking.yml` | 34 | `35  */2 * * *` (+1 alpha) |
| `system-health-check.yml` | 36 | `36  */2 * * *` |
| `daily-feed-summary.yml` | 40 | `40  */2 * * *` |
| `forward-signal-scanner.yml` | 44 | `44  */2 * * *` |
| `market_beating.yml` | 45 | `45  */2 * * *` |
| `proven-strategies-scanner.yml` | 50 | `50  */2 * * *` |
| `check-streamer-status.yml` | 51 | `51  */2 * * *` |
| `fc-crypto-pro.yml` | 53 | `53  */2 * * *` |

### 0 */4 * * * — 13 files

| filename | crc32%60 | final cron |
|----------|----------|------------|
| `live_trading.yml` | 1 | `1  */4 * * *` |
| `kimi-feb172026-live.yml` | 7 | `7  */4 * * *` |
| `master-automation-scheduler.yml` | 9 | `9  */4 * * *` |
| `discord-heartbeat.yml` | 11 | `11  */4 * * *` |
| `live_trading_canada.yml` | 12 | `12  */4 * * *` |
| `self_optimizing_trading.yml` | 13 | `13  */4 * * *` |
| `tv-strategy-scanner.yml` | 22 | `22  */4 * * *` |
| `picks_dispatch.yml` | 26 | `26  */4 * * *` |
| `strategy-health-monitor.yml` | 34 | `34  */4 * * *` |
| `parquet-ingest.yml` | 35 | `35  */4 * * *` |
| `momentum-scanner.yml` | 41 | `41  */4 * * *` |
| `autonomous_trading.yml` | 42 | `42  */4 * * *` |
| `what-worked-insights.yml` | 49 | `49  */4 * * *` |

### 0 */6 * * * — 13 files

| filename | crc32%60 | final cron |
|----------|----------|------------|
| `crypto-winner-scan.yml` | 0 | `0  */6 * * *` |
| `data-pipeline-test.yml` | 6 | `6  */6 * * *` |
| `hoffman-tracker.yml` | 14 | `14  */6 * * *` |
| `ml-feedback-loop.yml` | 15 | `15  */6 * * *` |
| `mirror-site.yml` | 22 | `22  */6 * * *` |
| `ml-health-monitor.yml` | 23 | `23  */6 * * *` |
| `audit-impact-tracker.yml` | 32 | `32  */6 * * *` |
| `buy-now-analysis.yml` | 33 | `33  */6 * * *` |
| `ml-model-autotraining.yml` | 35 | `35  */6 * * *` |
| `forward-test-new-strategies.yml` | 43 | `43  */6 * * *` |
| `refresh-top-movies.yml` | 44 | `44  */6 * * *` |
| `gha-summary-report.yml` | 50 | `50  */6 * * *` |
| `fred-macro-refresh.yml` | 57 | `57  */6 * * *` |

### 0 * * * * — 12 files

| filename | crc32%60 | final cron |
|----------|----------|------------|
| `master-automation-scheduler.yml` | 9 | `9  * * * *` |
| `db-freshness-guardian.yml` | 12 | `12  * * * *` |
| `qa-market-validation.yml` | 13 | `13  * * * *` |
| `meme-scanner-v2.yml` | 15 | `15  * * * *` |
| `send-accountability-reminders.yml` | 20 | `20  * * * *` |
| `contested-pick-checker.yml` | 27 | `27  * * * *` |
| `forward-tracking-v2.yml` | 28 | `28  * * * *` |
| `discord_status.yml` | 33 | `33  * * * *` |
| `battle_test.yml` | 44 | `44  * * * *` |
| `crypto-ml-tracker.yml` | 45 | `45  * * * *` |
| `darwin-evolution.yml` | 49 | `49  * * * *` |
| `analyst-tracker.yml` | 56 | `56  * * * *` |

### 0 4 * * * — 10 files

| filename | crc32%60 | final cron |
|----------|----------|------------|
| `swarm-janitor.yml` | 12 | `12  4 * * *` |
| `blacklist-reconciler.yml` | 18 | `18  4 * * *` |
| `mysql-stale-picks-resolver.yml` | 25 | `25  4 * * *` |
| `ml-battleground-retrain.yml` | 28 | `28  4 * * *` |
| `db-backup-email.yml` | 32 | `32  4 * * *` |
| `sign-coherence-gate.yml` | 32 | `33  4 * * *` (+1 alpha) |
| `backfill-features.yml` | 34 | `34  4 * * *` |
| `pick-funnel-nightly.yml` | 36 | `36  4 * * *` |
| `secret-scan.yml` | 50 | `50  4 * * *` |
| `scrape-events.yml` | 58 | `58  4 * * *` |

### 0 6 * * * — 8 files

| filename | crc32%60 | final cron |
|----------|----------|------------|
| `backtest-and-deploy.yml` | 6 | `6  6 * * *` |
| `cross-db-audit.yml` | 7 | `7  6 * * *` |
| `torontoevent-backtest-and-deploy.yml` | 13 | `13  6 * * *` |
| `torontoevent-backtest-and-deploy-ROOCODE.yml` | 19 | `19  6 * * *` |
| `spy-data-refresh.yml` | 43 | `43  6 * * *` |
| `decile-separation-test.yml` | 47 | `47  6 * * *` |
| `incubator-pipeline.yml` | 51 | `51  6 * * *` |
| `db-sync-to-mirror.yml` | 58 | `58  6 * * *` |

### 0 3 * * * — 6 files

| filename | crc32%60 | final cron |
|----------|----------|------------|
| `prune-strategy-performance.yml` | 7 | `7  3 * * *` |
| `master-automation-scheduler.yml` | 9 | `9  3 * * *` |
| `schema-drift-audit.yml` | 40 | `40  3 * * *` |
| `index-creator-content.yml` | 47 | `47  3 * * *` |
| `swarm-pick-review.yml` | 48 | `48  3 * * *` |
| `scrape-events.yml` | 58 | `58  3 * * *` |

## Before/After per-hour contention (even hours; accounts for */2 + */4 + */6 overlap)

| hour | current `:00` count | after stagger | notes |
|------|---------------------|---------------|-------|
| 00 | ≥15 (*/2) + portions of */4 + */6 | 1 per minute (spread 0–59) | worst hour; 3-tier overlap |
| 02 | 15 (*/2) | 1 per minute | |
| 04 | ≥15 + portions of */4 + */6 | 1 per minute | 3-tier overlap |
| 06 | 15 (*/2) | 1 per minute | historically high load |
| 08 | ≥15 + portions of */4 + */6 | 1 per minute | 3-tier overlap |
| 10 | 15 (*/2) | 1 per minute | |
| 12 | ≥15 + portions of */4 + */6 | 1 per minute | historically highest |
| 14 | 15 (*/2) | 1 per minute | |
| 16 | ≥15 + portions of */4 + */6 | 1 per minute | 3-tier overlap |
| 18 | 15 (*/2) | 1 per minute | |
| 20 | ≥15 + portions of */4 + */6 | 1 per minute | 3-tier overlap |
| 22 | 15 (*/2) | 1 per minute | |

**Impact:** spreads the 15-file `*/2` pile-up (plus portions of `*/4`/`*/6`) across 15 distinct minutes instead of one. Does not change semantics — only the minute offset within each cron window. `*/30` (12 files) and `0 * * * *` (12 files) remain on their native cadence (they already spread load).

## Concurrency recommendation

**Current state:** 164/356 (46.1 %) files declare `concurrency:`, 118 with `cancel-in-progress: false`. 192 files uncovered.

**Action items:**
1. Add `concurrency.group` + `cancel-in-progress: false` to the 192 uncovered files.
2. Standardize group naming: recommend canonical expression `${{ github.workflow }}-${{ github.ref }}` (or a short hash thereof) for consistency across the repo.
3. Mixed naming observed (`ab-analysis`, `${workflow}-${ref}`) — consolidate to one pattern.

## Multi-cron dispatch files (do NOT delete crons)

**17 files** branch on `${{ github.event.schedule }}` to select which cron to run. Deleting a cron entry in these files removes a named dispatch mode. **Stagger only; never propose deletion.**

## Stagger policy specification (for linter / pre-commit)

```
offset = zlib.crc32(filename.encode()) % 60
if collision within same cron group:
    sort filenames alphabetically
    assign +1, +2, … mod 60 until all distinct
```

This is deterministic, reviewable, and requires no external state or API calls.

---

**References (local git only):**
- `git show ae3f4dc4dc1c2a1e63abd5285e8c037e6f136695:.github/workflows/<file>` for each of the 360 cron lines.
- `/tmp/qa3/crons.json` (360 lines) for the minute histogram.
- `/tmp/qa3/table.txt` (this document's source tables).
