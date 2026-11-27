# The three chronic-red workflows: what each one actually dies of

Date: 2026-11-27 · Owner: Buffy · Scope: `.github/workflows/2hour_challenge.yml`,
`.github/workflows/db-sync-to-mirror.yml`, `.github/workflows/clear-channel-command.yml`

All three were carried as "chronic red" in
`updates/2026-11-27-gha-coverage-plan.md`. Each dies of a different cause, and only
one of them was a code bug. Two are blocked on a permission grant on a machine this
repo cannot reach, and are documented as such rather than silenced.

---

## 1. `2hour_challenge` — the workflow's own 30-minute job cap

**Not an external canceller, and not concurrency.** The earlier suspicion (something
outside the repo cancelling runs ~30 minutes in) is wrong, and the arithmetic says so.

| run | workflow file at that commit | job start | job end | duration |
|---|---|---|---|---|
| `45818757485` schedule | `timeout-minutes: 30` | 12:20:38Z | 12:50:53Z | **30m15s** |
| `45740875661` dispatch | `timeout-minutes: 30` | 02:12:40Z | 02:42:54Z | **30m14s** |
| `45746788181` dispatch | `timeout-minutes: 30` | 03:21:58Z (queued from 03:06:42Z) | 03:52:12Z | **30m14s** |
| `45771014231` dispatch | `timeout-minutes: 30` | 08:24:27Z (queued from 06:50:39Z) | 08:54:43Z | **30m16s** |

Job duration is the cap to the second. The two runs that "both died at 08:54" only
look like a batch cancel because two dispatches were queued at different times and
each hit its own 30-minute limit on the runner.

`real_2hour_challenge.py` runs `run_challenge(duration_minutes=120)`, so a 30-minute
cap guaranteed a kill a quarter of the way in. GitHub reports a job that hits
`timeout-minutes` as **`cancelled`**, not `failure` — the same masking documented in
`updates/2026-11-25-gha-cancellation-root-cause-and-failure-digest.md` — which is why
this never appeared in a failure triage.

**Ruled out, with evidence:**

* Concurrency — `cancel-in-progress: false`, group `${{ github.workflow }}-${{ github.ref }}`.
  No other workflow file in the repo names this workflow or shares its group string.
* An in-repo canceller — no workflow among the 419 in `.github/workflows` calls the
  cancel endpoint. `tools/gha_browser/delete_runs.py` is manual, takes explicit run
  ids, and only *deletes*. `scripts/actions_failure_guardian.py` only reruns failed
  jobs (`POST /rerun-failed-jobs`).
* A stuck push — the commit step never ran; the kill was inside the challenge step.

**Fix (already in `main`):** commit `87a6fbe4` — *fix(2hour-challenge): raise the cap
above the challenge's real 120-minute runtime* — raised the job to
`timeout-minutes: 150` (120-minute loop plus setup and commit), with a comment
recording why. `main` was verified to carry 150.

**Verification:** dispatched `45921032225` (2026-11-27T01:10:25Z) against the fixed
file. The proof is that it survives past 30 minutes; the job is expected to run to
~2h, so its conclusion is only meaningful after that.

---

## 2. `db-sync-to-mirror` — missing MySQL grants on the target, 5 of 6 databases

Run `45887584284` (2026-11-26T19:58Z) reaches the import step with six dumps on disk
and gets, per database:

```
ERROR 1044 (42000): Access denied for user '***'@'localhost' to database '***_events'
PDO connect failed: SQLSTATE[HY000] [1044] Access denied for user '***'@'localhost' to database '***_events'
```

`***_tvmoviestrailers` imports fine (`method=exec`, 5,254,922 bytes) with the same
user, host and password. So the connection, the dump format, the FTP hop and the PHP
runner all work; the target user simply has no privilege on the other five databases.
`1044` (not `1049`) means the databases exist — the grant is what is missing.

Two related findings:

* The export step only produced 6 of 8 dumps: `favcreators` and `stocks` never
  appeared in `dump_files`, so they cannot import either way.
* `scripts/db_import_runner.php` carries a 2026-11-26 comment claiming the switch to
  `'localhost'` "avoids ERROR 1044 on 5 of 8 databases". It does not — this log is
  from a run *after* that change, on `localhost`, still 1044 on exactly 5. The
  comment is wrong and should not be trusted by the next triage.
* The sibling `db-sync-bidirectional.yml` is green, but it only syncs
  `ejaguiar1_favcreators` and `ejaguiar1_tvmoviestrailers` — the two databases that
  do have grants. Its green is not evidence that the other five can import.

**Operator action (cannot be done from this repo):** in cPanel on torontoevent.net,
*MySQL Databases → Add User To Database*, add `TORONTOEVENT_DB_USER` to the five
failing databases with ALL PRIVILEGES. Until that happens the workflow is correctly
red; the failure is real and no dump is landing.

**Repo change:** the import step now classifies `1044`/`Access denied` failures as a
single permission blocker, names the affected databases and the exact fix in the
step summary and the log, instead of five opaque per-database lines. Exit status is
unchanged (still non-zero) — the failure is reported, not suppressed.

---

## 3. `clear-channel-command` — Discord `MANAGE_MESSAGES` missing in one channel

Run `45875893722` job log, one line:

```
ERROR:__main__:Bot lacks permission to delete messages in channel 1476311595977150779
##[error]Process completed with exit code 1.
```

Manual-only utility (`workflow_dispatch`, no cron), so its red status is only ever
produced by someone invoking it. The bot can *post* to that channel through its
webhook but may not moderate it — the webhook's permissions are independent of the
bot role's channel overwrites, which is what made this look like a code fault.

**Repo change (`signal_aggregator/clear_channel_command.py`):** a genuine bug
alongside the grant, fixed:

* `get_messages()` returned `[]` for both "channel is empty" and "403, cannot read".
  `clear_channel()` then took the `not messages` branch and set
  `success = True` — so a *read* permission failure was reported as a successful
  clear with zero deletions. It now returns `None` on failure, and a read denial is
  a failure that names the two grants needed (`VIEW_CHANNEL`,
  `READ_MESSAGE_HISTORY`).
* The bulk-delete 403 now names the grant and where to set it, instead of just
  "lacks permission".
* A zero-deletion run over a non-empty channel adds an explicit
  "most likely lacks MANAGE_MESSAGES" note to the result.

**Operator action:** give the bot role **Manage Messages** on channel
`1476311595977150779`. The utility then works unchanged.

---

## Summary

| workflow | cause | status |
|---|---|---|
| `2hour_challenge` | own `timeout-minutes: 30` vs a 120-minute script | **fixed** in `87a6fbe4`, verification run dispatched |
| `db-sync-to-mirror` | target MySQL user lacks grants on 5 DBs | code now names the blocker; **needs a cPanel grant** |
| `clear-channel-command` | bot lacks `MANAGE_MESSAGES` in one channel | masking bug **fixed**; **needs a Discord grant** |

Two of the three cannot be made green by changing this repository. They are left red
on purpose, with the exact grant named in the log and step summary, because a green
run that silently synced nothing (or cleared nothing) is worse than an honest red.
