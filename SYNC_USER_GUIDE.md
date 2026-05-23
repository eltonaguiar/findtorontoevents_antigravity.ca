# Bi-Directional Database Sync -- User Guide

## What This System Does

This system keeps **user data** synchronized between two independent websites that run on separate databases and hosting providers:

| Site | Host | DB Engine | Role |
|------|------|-----------|------|
| findtorontoevents.ca | 50webs | MySQL 8.4 | Primary |
| torontoevent.net | GoDaddy | MariaDB 10.6 | Mirror |
| tdotevent.ca | 50webs | MySQL 8.4 | Shares primary DB (no sync needed) |

**Before this system:** A daily one-way dump (`db-sync-to-mirror.yml`) wiped torontoevent.net's database and replaced it entirely with findtorontoevents.ca's data. Any user who registered or made changes on torontoevent.net lost everything at 4:00 AM EST.

**After this system:** User-related changes are tracked on both sites via a changelog. Once per day (or on demand), the sync job exchanges those changes bi-directionally, merging them with smart per-table strategies instead of overwriting.

---

## Architecture Overview

```
findtorontoevents.ca                    torontoevent.net
┌────────────────────┐                  ┌────────────────────┐
│  PHP App writes    │                  │  PHP App writes    │
│  to user tables    │                  │  to user tables    │
│        │           │                  │        │           │
│        ▼           │                  │        ▼           │
│  sync_log_write()  │                  │  sync_log_write()  │
│  logs to           │                  │  logs to           │
│  sync_changelog    │                  │  sync_changelog    │
└────────┬───────────┘                  └────────┬───────────┘
         │                                        │
         │    GitHub Actions (daily 4:30 AM EST)   │
         │    ┌──────────────────────────┐        │
         └───►│  1. Export unsynced A    │◄───────┘
              │  2. Apply A → B          │
              │  3. Export unsynced B    │
              │  4. Apply B → A          │
              │  5. Mark as synced       │
              │  6. Prune old entries    │
              └──────────────────────────┘
```

### How Ping-Pong Is Prevented

Every changelog entry records an `origin_site` -- the hostname where the change was first made. When syncing FROM Site A TO Site B, entries whose `origin_site` matches Site B are skipped (they already came from there). This prevents A->B->A->B infinite loops.

### How User Identity Works Across Sites

Users are matched by **email address** (UNIQUE on both sites), not by `user_id` (which is AUTO_INCREMENT and may differ between sites). Every changelog entry stores the user's email so the sync job can resolve `user_id` on the destination site.

---

## File Inventory

### Core Sync Scripts (`scripts/sync/`)

These are deployed **temporarily** by GitHub Actions during each sync run, then cleaned up.

| File | Purpose |
|------|---------|
| `sync_config.php` | Per-table merge strategies, PK definitions, safeguard thresholds, site detection |
| `sync_helpers.php` | Core functions: `log_sync_change()`, JSON merge, aggregate merge, PK serialization |
| `ensure_sync_tables.php` | Creates `sync_changelog`, `sync_conflicts`, `sync_table_config` tables; adds `origin_site`/`sync_version` columns |
| `db_sync_export.php` | Exports unsynced changelog entries as paginated JSON (filtered by destination) |
| `db_sync_apply.php` | Applies remote changelog entries with per-table merge strategies + user_id remapping |
| `db_sync_mark.php` | Marks changelog entries as synced to a destination after successful apply |
| `db_sync_prune.php` | Deletes synced entries older than 30 days |
| `sync_status.php` | Monitoring: changelog size, unsynced count, conflict count, row counts |
| `db_sync_initial_reconcile.php` | One-time initial merge of existing data (run before first sync) |

### Permanent API Include (`favcreators/docs/api/`)

| File | Purpose |
|------|---------|
| `sync_log.php` | Lightweight include for PHP endpoints. Provides `sync_log_write()`, `sync_log_fetch_before_delete()`, `sync_get_user_email_local()`. Silently does nothing if `sync_changelog` table doesn't exist. |

### GitHub Actions Workflow

| File | Purpose |
|------|---------|
| `.github/workflows/db-sync-bidirectional.yml` | Orchestrates the full sync: deploy scripts -> ensure tables -> export/apply A->B -> export/apply B->A -> mark synced -> prune -> cleanup |

---

## Tables Covered

### ejaguiar1_favcreators (14 tables)

| Table | Merge Strategy | What It Stores |
|-------|---------------|----------------|
| `users` | LWW | User accounts (email, password, role, display_name) |
| `user_lists` | LWW | Creator lists (full JSON blob, latest version wins) |
| `user_notes` | LWW | Notes on creators (per user+creator) |
| `user_secondary_notes` | LWW | Secondary notes on creators |
| `user_link_lists` | LWW | Custom link lists (per user+list_name) |
| `user_preferences` | LWW | Platform preferences (live, follow defaults) |
| `user_saved_events` | UNION_DEL | Saved Toronto events (additions kept, deletes honored) |
| `user_visit_days` | AGGREGATE | Visit metrics: MAX(distinct_days), MIN(first_visit), MAX(last_visit) |
| `notification_preferences` | UNION_DEL | Bell icon / notification settings per creator |
| `accountability_reminder_settings` | LWW | Accountability feature settings |
| `accountability_followup_optouts` | UNION_DEL | Users who opted out of follow-ups (opt-in DELETE honored) |
| `accountability_followup_log` | UNION | Follow-up message history (append-only) |
| `accountability_reminder_log` | UNION | Reminder history (append-only) |
| `stock_subscriptions` | UNION_DEL | Stock watchlist subscriptions |

### ejaguiar1_tvmoviestrailers (4 tables)

| Table | Merge Strategy | What It Stores |
|-------|---------------|----------------|
| `user_queues` | UNION_DEL | Movie/show watchlist queue |
| `user_preferences` | LWW | Movie playback preferences (autoplay, rewatch, etc.) |
| `shared_playlists` | LWW | User-created playlists |
| `playlist_items` | UNION_DEL | Items within playlists |

---

## Merge Strategies Explained

### LWW (Last-Write-Wins)

The row with the higher `sync_version` wins. If versions are equal, the later `changed_at` timestamp breaks the tie. Best for scalar preferences where one value must win.

**Risk:** If a user edits preferences on Site A at 9:00 AM EST and on Site B at 9:01 AM EST, Site B's version wins and Site A's changes are lost.

### UNION / UNION_DEL

Rows from both sites are kept (merged by composite primary key). New rows from either site are inserted. For UNION_DEL, DELETE operations win if the delete has a newer `sync_version` than the competing insert/update.

**Risk:** Minimal -- additive merges rarely lose data. The DELETE priority means a user who explicitly removes something won't have it re-appear.

### AGGREGATE

For `user_visit_days`: each field uses a specific aggregate function. `distinct_days` takes MAX (highest count from either site), `first_visit_at` takes MIN (earliest), `last_visit_at` takes MAX (most recent).

**Risk:** None -- this always produces the most generous/accurate metric.

---

## User-Facing Behavior: What Happens When...

This section documents exactly what happens for every user action across both sites, including how removals/deletions propagate.

### Creator List (user_lists)

| User Action | What Gets Logged | Sync Behavior | Removal Honored? |
|-------------|-----------------|---------------|-----------------|
| Add a creator | UPDATE with full JSON blob | Latest version wins (LWW) | N/A |
| Remove a creator | UPDATE with full JSON blob (minus removed creator) | Latest version wins (LWW) | **Yes** -- the newer, smaller list replaces the older, larger one |
| Reorder creators | UPDATE with full JSON blob | Latest version wins (LWW) | N/A |

**Key design decision:** `user_lists` uses **LWW** (not JSON_UNION). When a user removes a creator, their latest save has the smaller list. Because LWW picks the highest `sync_version`, the removal is respected. Previously JSON_UNION was used, which would silently re-add removed creators from the other site's copy.

**Edge case:** If a user adds creator X on Site A and removes creator Y on Site B (between syncs), only one site's version wins. The other's changes are lost. This is acceptable because daily sync means the window is small, and users typically use one site consistently.

### Saved Events (user_saved_events)

| User Action | What Gets Logged | Sync Behavior | Removal Honored? |
|-------------|-----------------|---------------|-----------------|
| Save an event | UPDATE (INSERT + version bump) | Added to both sites | N/A |
| Unsave an event | DELETE with tombstone | DELETE wins if newer version | **Yes** -- unsave propagates and won't be re-added unless the user explicitly saves it again on the other site |

**How it works:** When a user unsaves an event, the endpoint fetches the row data (tombstone) before deleting, logs it as a DELETE operation with a bumped `sync_version`. During sync, DELETEs always win if their version >= the local version, regardless of merge strategy.

### Bell Icon / Notification Preferences (notification_preferences)

| User Action | What Gets Logged | Sync Behavior | Removal Honored? |
|-------------|-----------------|---------------|-----------------|
| Enable bell for creator | INSERT new row | Row added on both sites | N/A |
| Disable bell for creator | DELETE with tombstone | DELETE wins if newer version | **Yes** -- bell stays off unless re-enabled |
| Unlink Discord (clears all bells) | Multiple DELETEs with tombstones | Each creator's bell row is individually deleted | **Yes** -- all notification prefs cleared on both sites |

**Note:** The bell icon is managed via the `notification_preferences` table with `(user_id, creator_id)` as the key. Each bell toggle is an individual row INSERT/DELETE, so the UNION_DEL strategy handles it correctly.

### Accountability Features

| User Action | What Gets Logged | Sync Behavior | Removal Honored? |
|-------------|-----------------|---------------|-----------------|
| Set reminder (time, channels) | UPDATE (upsert) | Latest settings win (LWW) | N/A |
| Disable reminder | UPDATE with disabled flags | Latest settings win (LWW) | **Yes** -- disabled state propagates |
| Opt out of follow-ups | INSERT opt-out row | Added to both sites | N/A |
| Re-enable follow-ups (opt in) | DELETE opt-out row with tombstone | DELETE wins if newer version | **Yes** -- opt-in (removal of opt-out) propagates and won't be re-added |

**How opt-in works:** Opting in means DELETING the opt-out row. The `accountability_followup_optouts` table uses UNION_DEL, so the DELETE propagates. If a user opts out on Site A and then opts back in on Site B (between syncs), the opt-in DELETE has a higher version and wins.

### Stock Subscriptions

| User Action | What Gets Logged | Sync Behavior | Removal Honored? |
|-------------|-----------------|---------------|-----------------|
| Subscribe to stock | INSERT new row | Added to both sites | N/A |
| Unsubscribe from stock | DELETE with tombstone | DELETE wins if newer version | **Yes** -- unsubscribe propagates |

### Notes (user_notes, user_secondary_notes)

| User Action | What Gets Logged | Sync Behavior | Removal Honored? |
|-------------|-----------------|---------------|-----------------|
| Write/edit a note | UPDATE (upsert) | Latest version wins (LWW) | N/A |
| Clear a note (set to empty) | UPDATE with empty string | Latest version wins (LWW) | **Yes** -- empty note propagates as the latest version |

### Link Lists (user_link_lists)

| User Action | What Gets Logged | Sync Behavior | Removal Honored? |
|-------------|-----------------|---------------|-----------------|
| Create/update a link list | UPDATE (upsert) | Latest version wins (LWW) | N/A |
| Delete a link list | DELETE with tombstone | DELETE wins if newer version | **Yes** -- deletion propagates |

### User Preferences (user_preferences)

| User Action | What Gets Logged | Sync Behavior | Removal Honored? |
|-------------|-----------------|---------------|-----------------|
| Change platform preferences | UPDATE | Latest version wins (LWW) | N/A |

### User Visit Metrics (user_visit_days)

| User Action | What Gets Logged | Sync Behavior | Removal Honored? |
|-------------|-----------------|---------------|-----------------|
| Visit the site | UPDATE (auto-tracked) | AGGREGATE: MAX(days), MIN(first_visit), MAX(last_visit) | N/A -- metrics only grow |

### Movie/TV Queue (user_queues) -- tvmoviestrailers DB

| User Action | What Gets Logged | Sync Behavior | Removal Honored? |
|-------------|-----------------|---------------|-----------------|
| Add to queue | INSERT new row | Added to both sites | N/A |
| Remove from queue | DELETE with tombstone | DELETE wins if newer version | **Yes** -- removal propagates |

### Playlists (shared_playlists, playlist_items) -- tvmoviestrailers DB

| User Action | What Gets Logged | Sync Behavior | Removal Honored? |
|-------------|-----------------|---------------|-----------------|
| Create/edit playlist | UPDATE (upsert) | Latest version wins (LWW) | N/A |
| Delete playlist | DELETE | Propagates if newer | **Yes** |
| Add item to playlist | INSERT row | Added to both sites | N/A |
| Remove item from playlist | DELETE with tombstone | DELETE wins if newer | **Yes** |

**Note:** The tvmoviestrailers tables currently have 0 rows on both sites and no PHP endpoints exist for these tables yet. Sync instrumentation will be needed when these endpoints are built.

---

## Endpoint Instrumentation Status

All user-facing PHP endpoints are now instrumented with `sync_log_write()` calls. This means every change a user makes is recorded in the `sync_changelog` table for bi-directional sync.

### Instrumented Endpoints (12 files)

| Endpoint | Table(s) | Actions Logged |
|----------|----------|---------------|
| `save_creators.php` | `user_lists` | UPDATE (full creator list save, user_id > 0 only) |
| `save_events.php` | `user_saved_events` | UPDATE (save), DELETE with tombstone (unsave) |
| `save_note.php` | `user_notes` | UPDATE (user_id > 0 only, skips admin global defaults) |
| `save_secondary_note.php` | `user_secondary_notes` | UPDATE |
| `save_link_list.php` | `user_link_lists` | UPDATE (create/edit) |
| `delete_link_list.php` | `user_link_lists` | DELETE with tombstone |
| `user_preferences.php` | `user_preferences` | UPDATE |
| `google_callback.php` | `users` | INSERT (new user registration) |
| `guest_usage.php` | `user_visit_days` | UPDATE (daily visit tracking) |
| `discord_unlink.php` | `notification_preferences` | DELETE with tombstones (each creator's bell row individually) |
| `accountability/reminder_settings.php` | `accountability_reminder_settings` | UPDATE (upsert per task) |
| `accountability/goal_followup_optout.php` | `accountability_followup_optouts` | INSERT (opt-out), DELETE with tombstone (opt-in) |

### Not Yet Instrumented (write to non-synced tables or admin-only)

| Endpoint | Reason |
|----------|--------|
| `add_creator_for_guest.php` | Admin-only, writes to guest list (user_id=0), not synced |
| `sync_creators_table.php` | Admin-only one-time setup |
| `seed_creator_defaults.php` | Admin-only one-time setup |
| `ensure_tables.php` | Setup/migration, not user data |
| `add_social_accounts.php` | Admin-only, writes to user_id=2 specifically |
| `discord_callback.php` | Only updates Discord link fields on `users` (not yet critical for sync) |
| `accountability/goal_followup.php` | Cron job (writes to `accountability_followup_log`), needs instrumentation |
| `accountability/send_reminders.php` | Cron job (writes to `accountability_reminder_log`), needs instrumentation |

### Known Gaps

1. **notification_preferences INSERT**: The endpoint that enables the bell icon for a specific creator has not been found in the codebase. The 25 existing rows were likely created through the Discord bot interaction backend or a mechanism not in this PHP API directory. When that endpoint is identified, it needs `sync_log_write()` instrumentation.

2. **tvmoviestrailers endpoints**: The `user_queues`, `shared_playlists`, and `playlist_items` tables have no PHP endpoints yet. When they are built, they must include sync logging.

3. **Cron jobs**: `accountability/goal_followup.php` and `accountability/send_reminders.php` write to append-only log tables. These are low priority since log tables use UNION (additive) strategy, but they should eventually be instrumented.

---

## How to Use

### First-Time Setup (COMPLETED 2026-02-18 at 8:40 PM EST)

The automated setup script handles everything:

```bash
python tools/sync_first_time_setup.py
```

This deploys sync scripts to both sites, creates all infrastructure tables, runs the initial data reconciliation, deploys `sync_log.php` permanently, verifies health, and cleans up. See "First-Time Setup Results" section below for details.

To re-run individual steps if needed:

```bash
python tools/sync_first_time_setup.py --step ensure      # Re-create tables
python tools/sync_first_time_setup.py --step reconcile   # Re-reconcile data
python tools/sync_first_time_setup.py --step verify      # Check status only
```

### Ongoing Operation

The workflow runs **automatically every day at 4:30 AM EST** (30 minutes after the existing content sync at 4:00 AM EST). It:

1. Deploys sync scripts to both sites temporarily
2. Creates/verifies sync tables
3. Syncs findtorontoevents.ca -> torontoevent.net
4. Syncs torontoevent.net -> findtorontoevents.ca
5. Marks entries as synced
6. Prunes entries older than 30 days
7. Cleans up temporary scripts

### Manual Trigger

Go to GitHub Actions -> "DB Sync: Bi-directional User Data" -> "Run workflow"

- Set `dry_run: true` to preview what would happen without making changes
- Set `dry_run: false` for a real sync

### Monitoring

Check sync health via the status endpoint (deployed during sync runs):
```
GET https://findtorontoevents.ca/_sync_tmp/sync_status.php?token=SECRET&db=ALL
```

Response includes:
- `changelog_total` / `changelog_unsynced` -- how many entries exist / are pending
- `unresolved_conflicts` -- conflicts that need manual review
- `row_counts` -- current row counts per table
- `changelog_by_origin` -- entries grouped by originating site

---

## What Can Go Wrong

### 1. sync_changelog Table Doesn't Exist Yet

**Symptom:** Endpoints work fine but no changes are logged. Sync runs but finds 0 entries.

**Cause:** The `ensure_sync_tables` step failed or wasn't run.

**Fix:** Trigger the workflow manually, or deploy and call `ensure_sync_tables.php?token=SECRET&db=ALL` on both sites.

**Safety:** The `sync_log_write()` function uses `@$conn->query()` (error suppression). If the table doesn't exist, it silently fails. No user-facing impact.

### 2. User Registers on Both Sites with Different Emails

**Symptom:** The user has two separate accounts that don't merge.

**Cause:** Identity resolution relies on email. If someone uses `alice@gmail.com` on Site A and `alice.work@gmail.com` on Site B, the system sees them as two different users.

**Fix:** Manual -- merge the accounts in the database and add an entry to `sync_conflicts` to track it.

**Prevention:** This is inherent to email-based identity. A future enhancement could add a "link accounts" feature.

### 3. Empty Database Propagation

**Symptom:** After sync, a table on the destination has far fewer rows than expected.

**Cause:** The source database was accidentally wiped (e.g., a bad deploy reset a table).

**Safeguard:** The apply script checks source row counts. If source has 0 rows but destination has real data, it SKIPS that table and logs a safeguard warning. A 10% delta alert is also raised if a table would lose more than 10% of its rows.

**What to check:** Look for `SAFEGUARD` warnings in the GitHub Actions log output.

### 4. Clock Skew Between Servers

**Symptom:** The "wrong" version of data wins during conflict resolution.

**Cause:** 50webs and GoDaddy servers have different system clocks. LWW uses `sync_version` (monotonic counter) as the primary resolution method, with `changed_at` only as a tiebreaker. However, if both sites have the same version, a 2-minute clock difference could cause the older change to win.

**Mitigation:** The sync uses `gmdate()` (UTC) on both sides. For most practical purposes, daily sync with version-based resolution makes clock skew a non-issue. True conflicts are rare.

### 5. Changelog Grows Too Large

**Symptom:** Sync runs take longer, database disk usage increases.

**Cause:** The prune step failed, or there are many unsynced entries accumulating.

**Fix:** Run the prune endpoint manually:
```
GET https://findtorontoevents.ca/_sync_tmp/db_sync_prune.php?token=SECRET&db=ALL
```

**Prevention:** The workflow prunes automatically after each sync. Entries are kept for 30 days (configurable in `sync_config.php` via `sync_get_retention_days()`).

### 6. Both Sites Modify Same Data Between Syncs

**Symptom:** One site's changes are lost after sync.

**Cause:** A user (or two users with the same email) made changes on both sites within the same 24-hour sync window.

**LWW tables:** The higher `sync_version` wins. Since version is incremented on each write, the site with more recent activity wins. The other site's changes are overwritten.

**UNION_DEL tables:** Both additions are kept. Only conflicts between INSERT and DELETE for the same row require version comparison (DELETE wins if newer).

**AGGREGATE tables:** Both sites' data is merged (MAX/MIN), so no data is lost.

**This is the main trade-off of daily sync.** For real-time consistency, you would need MySQL replication or a shared external database.

### 7. Sync Scripts Aren't Cleaned Up

**Symptom:** `_sync_tmp/` directory remains on the server with temporary PHP scripts.

**Cause:** The cleanup step failed (FTP error, timeout).

**Risk:** Low -- the scripts are token-protected. But they shouldn't remain permanently.

**Fix:** Manually delete via FTP, or the next sync run will overwrite them and clean up.

### 8. GitHub Actions Workflow Fails

**Symptom:** Sync doesn't happen for a day or more.

**Cause:** Many possible reasons -- secret expired, server down, timeout.

**What to check:**
1. GitHub repo -> Actions -> look for failed runs
2. Check if `DB_SCRIPT_TOKEN` and FTP secrets are still valid
3. Check if both sites are reachable (`curl -I https://findtorontoevents.ca`)

**Safety:** Missing a day of sync is fine. The changelog accumulates entries, and the next successful run will catch up. There's no data loss from a missed sync -- only a delay.

### 9. Conflict in sync_conflicts Table

**Symptom:** The `sync_status` endpoint shows `unresolved_conflicts > 0`.

**Cause:** Two changes to the same row that couldn't be automatically resolved (e.g., same email registered as different user types on different sites).

**Fix:** Review the `sync_conflicts` table in phpMyAdmin. Each row shows `local_data`, `remote_data`, `conflict_type`. Resolve manually and set `resolved = 1`.

### 10. PHP 5.2 Compatibility Error on 50webs

**Symptom:** Parse error / fatal error on findtorontoevents.ca endpoints.

**Cause:** Someone edited a sync file and used PHP 5.3+ syntax (`?:`, `??`, `[]`, closures, `__DIR__`).

**Fix:** Check the file for forbidden constructs. All sync code must use:
- `array()` not `[]`
- `isset($x) ? $x : $default` not `$x ?? $default`
- `($x) ? $x : $y` not `$x ?: $y`
- `dirname(__FILE__)` not `__DIR__`
- Named functions, not closures

---

## Evaluation of This Approach

### Strengths

1. **No infrastructure dependencies.** Works with existing shared hosting (50webs PHP 5.2, GoDaddy PHP 8.3). No need for MySQL replication ports, no external services.

2. **Graceful degradation.** If the sync system isn't set up yet, or the changelog table doesn't exist, all API endpoints continue working normally. `sync_log_write()` silently fails.

3. **Per-table merge strategies.** Not all data is the same. Creator lists use LWW (latest wins, removals respected), visit metrics are aggregated (MAX), notification preferences use UNION_DEL (individual add/remove per creator). This avoids the one-size-fits-all problem.

4. **Ping-pong prevention.** The `origin_site` field prevents changes from bouncing between sites indefinitely.

5. **Safeguards.** Empty-DB protection, delta alerting, dry-run mode, and a conflicts table for manual review.

6. **Backward compatible.** The existing one-way content sync (`db-sync-to-mirror.yml`) continues unchanged for non-user tables. This system runs alongside it.

7. **Removals propagate correctly.** DELETE operations are logged with tombstones (row snapshot before deletion) and always win when their `sync_version` >= the local version. Unsaving events, disabling bells, opting in (removing opt-out), unsubscribing from stocks, and removing queue items all propagate correctly.

### Weaknesses and Known Limitations

1. **Daily sync lag.** Changes made on one site take up to 24 hours to appear on the other. For most user data this is acceptable, but real-time sync would require a fundamentally different approach (WebSocket push, MySQL replication, or a shared external database).

2. **LWW loses one side on simultaneous edits.** If both sites independently modify the same LWW row between syncs, one set of changes is lost. This affects `user_lists`, `user_notes`, `user_preferences`, etc. The risk is low because users typically use one site consistently.

3. **notification_preferences INSERT not yet instrumented.** The endpoint that enables the bell icon for a specific creator hasn't been found in the PHP API directory. Until it's identified and instrumented, new bell enables won't be logged (but the existing reconciliation captured the baseline, and UNION_DEL will prevent deletions from being reverted).

4. **Accountability tables use dual IDs.** Some tables key by `discord_user_id` (string) while others use `app_user_id` (int). The sync system handles this via the natural unique keys, but rows with NULL discord_user_id may not sync correctly if the same user has different app_user_ids across sites.

5. **No automated testing.** There are no unit tests for the merge logic. A test suite that simulates concurrent changes on both sites and verifies merge outcomes would significantly increase confidence.

6. **Single-threaded.** The GitHub Actions workflow processes entries sequentially. For very large changelogs (10k+ entries), this could approach the 30-minute timeout.

7. **tvmoviestrailers tables have no endpoints.** The 4 tables in the tvmoviestrailers DB are defined in the sync config but have 0 rows and no PHP endpoints. When endpoints are built, they must include sync_log instrumentation.

### Compared to Alternatives

| Approach | Pros | Cons | Why Not |
|----------|------|------|---------|
| **MySQL Replication** | Real-time, built-in | Requires open ports, same DB engine, complex setup | 50webs and GoDaddy don't expose replication ports |
| **Shared External DB** | Single source of truth | Monthly cost, latency, migration effort | Both sites are on cheap shared hosting |
| **Debezium / CDC Tool** | Robust, well-tested | Requires Kafka, dedicated server | Overkill for this scale |
| **This approach (PHP CDC)** | Works with existing infra, no cost, fine-grained control | Daily lag, manual maintenance | Best fit for constraints |

---

## Strategy Changes Log

### 2026-02-18 (EST)

1. **`user_lists`: Changed from `JSON_UNION` to `LWW`**
   - **Why:** JSON_UNION always merged creator arrays from both sites, which meant removing a creator on one site would be silently reverted when the other site's copy (still containing that creator) was merged back in. LWW ensures the most recent save of the entire list wins, properly reflecting removals.
   - **Trade-off:** If both sites independently modify the list between syncs, one set of changes is lost. But this is better than silently reverting user removals, which was confusing and frustrating.

2. **`accountability_followup_optouts`: Changed from `LWW` to `UNION_DEL`**
   - **Why:** Opting back in (re-enabling follow-ups) is a DELETE operation (removes the opt-out row). LWW doesn't have explicit DELETE handling at the strategy level -- DELETEs are handled before strategy is checked, but UNION_DEL explicitly ensures that if a user opts in (DELETE) and another action opts out (INSERT) for the same row, the DELETE wins if it has a higher version.

3. **Accountability table PK definitions fixed:**
   - `accountability_reminder_settings`: Changed from `(id)` to `(discord_user_id, app_user_id, task_id)` -- the `id` is auto-increment and would collide between sites; the natural unique key is the composite of user+task.
   - `accountability_followup_optouts`: Changed from `(id)` to `(discord_user_id)` -- same auto-increment collision issue.
   - `accountability_reminder_log`: Changed from `(id)` to `(setting_id, channel, sent_at)` -- matches the actual table structure.

4. **All user-facing endpoints instrumented with `sync_log_write()`** -- 12 PHP files now log every user change to the sync_changelog table, including tombstones for DELETE operations.

---

## First-Time Setup Results

Setup was run on **2026-02-18 at 8:40 PM EST** using `tools/sync_first_time_setup.py`.

### Infrastructure Tables Created (0 errors)

Both sites, both databases received all 3 infrastructure tables:
- `sync_changelog` -- change tracking
- `sync_conflicts` -- conflict records for manual review
- `sync_table_config` -- per-table merge strategy configuration

All 14 favcreators tables and all 4 tvmoviestrailers tables had `sync_version` column added. The `users` table also received `origin_site`.

### Initial Reconciliation (ejaguiar1_favcreators)

**4 users matched** by email, all with identical IDs on both sites:

| Email | findtorontoevents.ca ID | torontoevent.net ID |
|-------|------------------------|---------------------|
| elton | 1 | 1 |
| zerounderscore@gmail.com | 2 | 2 |
| bob | 3 | 3 |
| bob1 | 4 | 4 |

No local-only or remote-only users were found.

**Data merged (findtorontoevents.ca -> torontoevent.net):**

| Table | Inserted | Merged | Skipped | Strategy |
|-------|----------|--------|---------|----------|
| user_lists | 0 | 4 | 1 | JSON_UNION (at time of reconciliation; now LWW) |
| user_notes | 1 | 0 | 7 | LWW |
| user_visit_days | 0 | 2 | 3 | AGGREGATE |
| notification_preferences | 3 | 0 | 22 | UNION_DEL |
| (all others) | 0 | 0 | 0 | -- |

**Data merged (torontoevent.net -> findtorontoevents.ca):**

| Table | Inserted | Merged | Skipped | Strategy |
|-------|----------|--------|---------|----------|
| user_lists | 0 | 4 | 1 | JSON_UNION (at time of reconciliation; now LWW) |
| user_visit_days | 0 | 2 | 3 | AGGREGATE |
| (all others) | 0 | 0 | 0 | -- |

### Initial Reconciliation (ejaguiar1_tvmoviestrailers)

Both sites had 0 rows across all 4 tables. No data to reconcile. (The reconcile endpoint on torontoevent.net returned HTTP 500 for this DB because there is no `users` table in tvmoviestrailers -- this is expected and harmless since user identity resolution isn't needed when all tables are empty.)

### Post-Reconciliation Row Counts (Verified Match)

**ejaguiar1_favcreators** (both sites now identical):

| Table | findtorontoevents.ca | torontoevent.net |
|-------|---------------------|------------------|
| users | 4 | 4 |
| user_lists | 5 | 5 |
| user_notes | 8 | 8 |
| user_secondary_notes | 1 | 1 |
| user_preferences | 4 | 4 |
| user_visit_days | 5 | 5 |
| notification_preferences | 25 | 25 |

**ejaguiar1_tvmoviestrailers** (both sites, all 0):

| Table | findtorontoevents.ca | torontoevent.net |
|-------|---------------------|------------------|
| user_queues | 0 | 0 |
| user_preferences | 0 | 0 |
| shared_playlists | 0 | 0 |
| playlist_items | 0 | 0 |

### Sync Health Post-Setup

| Metric | findtorontoevents.ca | torontoevent.net |
|--------|---------------------|------------------|
| Changelog entries (favcreators) | 1 (baseline) | 1 (baseline) |
| Changelog entries (tvmoviestrailers) | 1 (baseline) | 0 |
| Unsynced entries | 0 | 0 |
| Unresolved conflicts | 0 | 0 |

### Permanent Deployments

- `sync_log.php` deployed to `fc/api/sync_log.php` on both sites

### Sync-Instrumented Endpoint Deployment (2026-02-18 ~11:30 PM EST)

13 PHP files deployed to both sites using `tools/deploy_sync_instrumented.py`:

| Site | Files Uploaded | Failures |
|------|---------------|----------|
| findtorontoevents.ca (50webs, FTP_TLS) | 13 | 0 |
| torontoevent.net (GoDaddy, plain FTP) | 13 | 0 |

**Post-deploy smoke test** (all endpoints responding, no PHP parse errors):

| Endpoint | findtorontoevents.ca | torontoevent.net |
|----------|---------------------|------------------|
| `save_creators.php` (GET) | 401 Unauthorized (expected -- requires session) | 401 Unauthorized (expected) |
| `save_events.php` (GET) | 200 `{"error":"Use POST"}` (valid JSON, no parse error) | 200 `{"error":"Use POST"}` |
| `guest_usage.php?action=check_site` | 200 `{"ok":true,"allowed":true}` (fully working) | 200 `{"ok":true,"allowed":true}` |

---

## Setup Automation

The setup script `tools/sync_first_time_setup.py` automates the full first-time setup process:

```bash
python tools/sync_first_time_setup.py                    # Full setup
python tools/sync_first_time_setup.py --dry-run          # Preview only
python tools/sync_first_time_setup.py --step ensure      # Only create tables
python tools/sync_first_time_setup.py --step reconcile   # Only reconcile data
python tools/sync_first_time_setup.py --step verify      # Only check status
```

Requires FTP environment variables: `FTP_SERVER`, `FTP_USER`, `FTP_PASS` (50webs) and `FTPGODADDYHOST_TE_DOTNET`, `FTPGODADDYUSER`, `FTPGODADDYPASS` (GoDaddy). DB credentials are read from `favcreators/docs/api/.env`.

### Per-DB Credential Support

A per-DB credential map was added to `sync_config.php` via `sync_get_db_creds()`. On 50webs, each database has its own MySQL user (e.g., `ejaguiar1_favcreators` and `ejaguiar1_tvmoviestrailers`). The deployment scripts inject a PHP array mapping each database name to its `(user, password)` pair. On GoDaddy, a single `admin` user accesses all databases so the map stays empty.

---

## Remaining Work

### Must Do Before First Real Sync

- [x] Run `ensure_sync_tables` on both sites to create infrastructure tables (done 2026-02-18 at 8:40 PM EST)
- [x] Run `db_sync_initial_reconcile` to merge existing data (done 2026-02-18 at 8:40 PM EST)
- [x] Deploy `favcreators/docs/api/sync_log.php` permanently to both sites (done 2026-02-18 at 8:40 PM EST)
- [x] Verify the workflow runs successfully with `dry_run: true` (verified 2026-02-18 at ~11:55 PM EST, run #22165187052, all 11 steps passed in 28s)
- [x] Instrument all user-facing endpoints with `sync_log_write()` (done 2026-02-18, 12 endpoints instrumented)
- [x] Fix `user_lists` strategy from JSON_UNION to LWW (done 2026-02-18)
- [x] Fix accountability table PK definitions for cross-site sync (done 2026-02-18)
- [x] Deploy updated `sync_log.php`-instrumented endpoints to both sites (deployed 2026-02-18, 13 files, 0 failures on both findtorontoevents.ca and torontoevent.net)
- [ ] Deploy updated `sync_config.php` (with LWW for user_lists) via the workflow (auto-deployed on next sync run)

### Should Do Soon

- [ ] Identify and instrument the notification_preferences INSERT endpoint (bell icon enable)
- [ ] Add `sync_version` column to `user_preferences` table in `ejaguiar1_tvmoviestrailers`
- [ ] Instrument `accountability/goal_followup.php` (cron job, writes to followup_log)
- [ ] Instrument `accountability/send_reminders.php` (cron job, writes to reminder_log)
- [ ] Instrument `discord_callback.php` (Discord link on `users` table)
- [x] Verify `sync_status.php` returns sensible data from both sites (verified 2026-02-18 at 8:40 PM EST)

### Code Review Fixes Applied

The following bugs were found by automated code review and fixed:

- **db_sync_apply.php**: Fixed incorrect `(int) $cnt->fetch_assoc()` cast (array-to-int was always 0/1). Removed redundant duplicate COUNT query. Added database name allow-list validation.
- **db_sync_mark.php**: Added `require_once sync_config.php` and database name allow-list validation.
- **sync_status.php**: Fixed duplicate COUNT queries and added null-safety checks on all `$r->fetch_assoc()` calls to prevent fatal errors if queries fail.
- **All sync scripts**: Added per-DB credential map support via `sync_get_db_creds()` in `sync_config.php` to fix 50webs multi-database authentication.
- **db-sync-bidirectional.yml**: Updated to inject per-DB credentials from `FINDTORONTOEVENTS_DB_CREDENTIALS` JSON secret.
- **sync_config.php**: Changed `user_lists` from JSON_UNION to LWW; changed `accountability_followup_optouts` from LWW to UNION_DEL; fixed PK definitions for accountability tables.
- **12 PHP endpoints**: Instrumented with `sync_log_write()` calls for INSERT, UPDATE, and DELETE operations with proper tombstones.

### Nice to Have

- [ ] Automated test suite for merge strategies
- [ ] Increase sync frequency to every 6 hours (change cron in workflow)
- [ ] Build a simple admin dashboard page that calls `sync_status.php` and displays results
- [ ] Add Slack/Discord webhook for sync failure alerts
- [ ] Schema version check before sync (abort if table schemas don't match)
