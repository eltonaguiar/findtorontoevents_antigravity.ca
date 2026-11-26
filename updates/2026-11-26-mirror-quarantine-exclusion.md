# `mirror-site` — exclude `_QUARANTINE_*` from the lftp mirror (download **and** both uploads)

**Date:** 2026-11-26
**File changed:** `.github/workflows/mirror-site.yml`
**Severity:** CI reliability (6-hourly job failing) + prospective content-republication risk
**Status:** fixed, statically verified, not yet run end-to-end

---

## What was broken

`Mirror: findtorontoevents.ca ⇄ torontoevent.net` failed its download step by
**timing out at the step's own 50-minute cap**.

Run `45740915469` (`workflow_dispatch`, triggered 2026-11-26T02:13:00Z):

```
JOB: mirror => failure
    success   Set up job
    success   Install lftp
    success   Restore previous mirror tree (incremental pulls)
    failure   Download from findtorontoevents.ca (50webs FTP)
    skipped   Upload to torontoevent.net (GoDaddy FTP)
    skipped   Upload to tdotevent.ca (50webs FTP, /tdotevent.ca)
    skipped   Deploy fc/api/.env to GoDaddy
    skipped   Verify mirrors are live
    skipped   Summary
```

Final log line:

```
##[error]The action 'Download from findtorontoevents.ca (50webs FTP)' has timed out after 50 minutes.
```

### This is a *different* failure than the previous one

The 2026-11-25T18:28 run died in 4 seconds with:

```
mirror: Login failed: 530 Login authentication failed
```

That was an FTP credential problem and it has been resolved — the repo secrets
`FTP_HOST` / `FTP_USER` / `FTP_PASS` were all refreshed at
**2026-11-25T20:28:57Z–20:28:59Z**, and the run above authenticated fine and
transferred files for ~50 minutes before hitting the timeout. So the 530 is
gone; do not re-open it.

### Root cause: the source FTP tree contains a quarantine backup

The download was spending its entire budget inside `_QUARANTINE_2026-11-25/`,
a backup tree created during the 2026-11-25 phishing cleanup
(branch `security/2026-11-25-phishing-cleanup`). Sampled paths from the log:

```
Making directory `_QUARANTINE_2026-11-25/backups/20260131-204057/MOVIESHOWS/MOVIESHOWS'
Transferring file `_QUARANTINE_2026-11-25/tmp/social_brett.json'
Transferring file `_QUARANTINE_2026-11-25/backups/20260131-190426/luxcal/pages/login.php'
Transferring file `_QUARANTINE_2026-11-25/backups/20260131-223728/TORONTOEVENTS_ANTIGRAVITY/
                   _next/static/chunks/turbopack-e39e7815aef87c1e.js'
```

It contains **pathologically nested duplicates** — note the repeated segments:

```
_QUARANTINE_2026-11-25/backups/20260131-190426/TORONTOEVENTS_ANTIGRAVITY/
  TORONTOEVENTS_ANTIGRAVITY/next/next/static/TORONTOEVENTS_ANTIGRAVITY/next/static/chunks/
  4b09812c2128d8d8.js
```

So a handful of original backup directories were recursively re-copied into
themselves. The path depth and file count grow multiplicatively, which is why
the transfer never finishes.

### Why the existing excludes did not catch it

The mirror already excludes a lot of ballast:

```yaml
--exclude='^backups/' \
--exclude='^tmp/' \
--exclude='^genome/' \
```

These are **anchored with `^`**, so they only match directories at the *root of
the FTP tree*. `_QUARANTINE_2026-11-25/backups/...` and
`_QUARANTINE_2026-11-25/tmp/...` begin with `_QUARANTINE_`, so they slipped
through every one of them. The quarantine tree was never accounted for because
it did not exist when the exclude list was written.

---

## What changed

`_QUARANTINE_*` directories are now excluded from **all three** `lftp mirror`
invocations:

```yaml
--exclude='(^|/)_QUARANTINE_[^/]*/' \
```

The `(^|/)` prefix makes it match the tree at the FTP root *and* anywhere nested,
which is what the log showed. `[^/]*/` keeps it to a single path segment so it
cannot accidentally match a file whose name merely starts with `_QUARANTINE_`.

### The two `--reverse` upload steps had to be patched too

This is the non-obvious part. The job starts with:

```yaml
- name: Restore previous mirror tree (incremental pulls)   # actions/cache of /tmp/site_mirror
```

The cache restores a `/tmp/site_mirror` from earlier runs. If any prior run
downloaded `_QUARANTINE_*` before the download step failed, those files are
**already sitting in the cached tree** — and the two `--reverse` upload steps
would then push them to `torontoevent.net` and `tdotevent.ca` without ever
re-downloading anything.

So excluding only at download would have been an incomplete fix. All three
invocations now carry the exclude:

| Line | Step | Direction |
|------|------|-----------|
| 103 | Download from findtorontoevents.ca | source → `/tmp/site_mirror` |
| 194 | Upload to torontoevent.net (GoDaddy) | `--reverse` `/tmp/site_mirror` → `/` |
| 240 | Upload to tdotevent.ca (50webs) | `--reverse` `/tmp/site_mirror` → `/tdotevent.ca` |

A comment block above `timeout-minutes: 50` records the run ID, the offending
paths, and the republication rationale so the next reader does not "clean up"
the exclude.

---

## Public-exposure check (done, negative)

Because quarantine directories hold *removed* content, mirroring them would
republish it. Earlier successful runs on 2026-11-25 could in principle have
uploaded the tree before it got large. Checked all three domains:

```
403  https://findtorontoevents.ca/_QUARANTINE_2026-11-25/tmp/social_brett.json
403  https://torontoevent.net/_QUARANTINE_2026-11-25/tmp/social_brett.json
403  https://tdotevent.ca/_QUARANTINE_2026-11-25/tmp/social_brett.json
403  https://findtorontoevents.ca/_QUARANTINE_2026-11-25/
403  https://torontoevent.net/_QUARANTINE_2026-11-25/
```

All `403` — the tree is not publicly reachable on source or either mirror.
**No live exposure.** The exclude is therefore preventive, not incident
response. (The 02:13 run uploaded nothing: both upload steps were `skipped`.)

---

## How it was verified

Static only — the workflow has not been re-run end-to-end yet.

```bash
# 1. all three blocks patched exactly once
grep -c "_QUARANTINE_\[" .github/workflows/mirror-site.yml     # -> 3
awk '/mirror \\$/{blk++} /_QUARANTINE_\[/{print "block "blk}' .github/workflows/mirror-site.yml

# 2. YAML still parses; triggers intact
python3 -c "import yaml; d=yaml.safe_load(open('.github/workflows/mirror-site.yml')); \
  print(list(d.keys())); print(list((d.get('on') or d.get(True)).keys()))"
# -> ['name', True, 'permissions', 'concurrency', 'jobs']
# -> ['schedule', 'workflow_dispatch']

# 3. no new lint diagnostics vs the unmodified file
#    (strip path:line:col first — actionlint prints a ../-prefixed name for a
#     file outside the repo, which would otherwise show up as a spurious diff)
git show origin/main:.github/workflows/mirror-site.yml > /tmp/base_workflows_mirror-site.yml
actionlint -oneline .github/workflows/mirror-site.yml   | sed -E 's/^[^:]+:[0-9]+:[0-9]+: //' | sort > /tmp/al_new.txt
actionlint -oneline /tmp/base_workflows_mirror-site.yml | sed -E 's/^[^:]+:[0-9]+:[0-9]+: //' | sort > /tmp/al_base.txt
wc -l /tmp/al_base.txt /tmp/al_new.txt    # -> 11 and 11
diff /tmp/al_base.txt /tmp/al_new.txt     # -> no output
```

Result: `3` excludes, YAML parses, triggers unchanged, and diagnostics are
**byte-identical to baseline** — `11` shellcheck notes at `mirror-site.yml:315`
(step `Verify mirrors are live`, `SC2086`/`SC2129`, all pre-existing) and
**`0` real workflow errors**.

## Remaining caveat — first run after merge may still be slow

`actions/cache` still holds a `/tmp/site_mirror` containing quarantine files
from deleted earlier runs. The exclude stops *new* transfers, but the first run
after this merges will still have those files on disk. They cannot reach the
mirrors (both uploads exclude them), and they age out of the cache naturally.
If the first run is still slow, delete the cache entry for
`site-mirror-*` — no code change needed.

## Not addressed here

- Job-level `timeout-minutes: 90` and the 50/15/15 step caps are unchanged. If
  the source tree legitimately needs more than 50 minutes *after* the quarantine
  exclude, raising the download cap is a separate decision — the volume, not the
  cap, was the problem here.
- `db-secret-scan.yml`, `battle_test.yml`, `ai-tournament-pipeline.yml` and the
  five `sports-*.yml` workflows remain `disabled_manually`. Enabling them is a
  product decision and is not touched by this change.
