# `mirror-site` — the merged `_QUARANTINE_*` exclude was a **no-op**; corrected pattern + confirmed local run

**Date:** 2026-11-26
**File changed:** `.github/workflows/mirror-site.yml`
**Severity:** CI reliability (6-hourly job failing at a 50-minute step cap)
**Status:** root cause corrected, pattern fixed, **verified by a full local run end-to-end**

> **Correction notice.** An earlier version of this document (committed as
> `c708814eded8`, PR #1169) claimed the fix landing in that PR resolved the
> 50-minute timeout. It did not. The pattern it shipped,
> `--exclude='(^|/)_QUARANTINE_[^/]*/'`, is a **no-op against the tree that
> actually causes the timeout**. This document supersedes it and records the
> measured proof.

---

## Triage chain

This job has failed for three distinct reasons. Do not conflate them.

| # | Symptom | Real cause | Status |
|---|---------|-----------|--------|
| 1 | Died in **4 s**: `530 Login authentication failed` (run `45675564919`) | Rotated FTP secrets | **Fixed** — secrets refreshed 2026-11-25T20:28:57–59Z; local run authenticated cleanly |
| 2 | `##[error]The action 'Download from findtorontoevents.ca (50webs FTP)' has timed out after 50 minutes` (run `45740915469`) | FTP crawl dominated by a huge `.git_QUARANTINE_*` object store | **This document** |
| 3 | `completed/cancelled` with **zero jobs returned** by the API (run `45746701788`) | Concurrency supersession + queue starvation (11 queued, 10 in progress), cancelled before a runner was assigned | **Not a defect** — do not re-open |

---

## What was actually broken

The source FTP tree at `/findtorontoevents.ca/` contains **two** differently
named quarantine trees:

| Tree | Path | Matched by the *merged* pattern? |
|------|------|--------------------------------|
| A | `/_QUARANTINE_2026-11-25/` | **Yes** |
| B | `WINDOWSFIXER/MiracleBoot_v7_1_1 - Github code/.git_QUARANTINE_2026-11-25/` | **No** |

Tree A is the obvious one. Tree B is the killer: it is a **git object store**
(`.git_QUARANTINE_2026-11-25/objects/<2-hex>/<38-hex>`), i.e. tens of thousands
of tiny files, each costing a full FTP round trip at `--parallel=4`.

### Why the merged pattern never matches tree B

```
--exclude='(^|/)_QUARANTINE_[^/]*/'      # merged in PR #1169
```

That regex requires the **path component to begin with** `_QUARANTINE_`. The
component in tree B is `.git_QUARANTINE_2026-11-25`, which begins with `.git`.
No match.

The pre-existing `--exclude='(^|/)\.git/'` does not save it either: that regex
requires a component equal to exactly `.git`, and `.git_QUARANTINE_2026-11-25`
is a different component.

Verified purely by regex, no network required:

```
merged  fixed   path
------  -----   ----
EXCL    EXCL    _QUARANTINE_2026-11-25/backups/20260131-190426/x.js
keep    EXCL    WINDOWSFIXER/MiracleBoot_v7_1_1 - Github code/.git_QUARANTINE_2026-11-25/objects/7c/2e5882
EXCL    EXCL    _QUARANTINE_2026-11-25/
keep    EXCL    .git_QUARANTINE_2026-11-25/
keep    keep    TORONTOEVENTS_ANTIGRAVITY/index.html
keep    keep    audit_dashboard/template.html
keep    keep    updates/index.html
```

### Measured proof that the merged fix is a no-op

A local replay (`/tmp/mirror_local_replay.py`, log `/tmp/mirror_local_run.log`)
walked the live tree with the merged exclude active (PHASE3) and again with the
control (PHASE4), both under an identical 150 s budget:

```
PHASE3 (merged pattern active): dirs=1334 files=4531 bytes=356,025,052 (356.0 MB) elapsed=150.1s budget_hit=True
PHASE4 (control)              : dirs=1337 files=4536 bytes=356,033,259 (356.0 MB) elapsed=150.1s budget_hit=True
```

Difference: **5 files / 8,207 bytes**. In both phases the walker was still
inside `WINDOWSFIXER/MiracleBoot_v7_1_1 - Github code/.git_QUARANTINE_2026-11-25/objects/`
when the budget expired — the exact place the merged pattern was supposed to
stop it. **The merged exclude saves 0.0 MB of the cost that matters.**

> Honest caveat: PHASE4's control was not a pure control — the replay script's
> `EXC_RE.pop()` removed the trailing `__pycache__` regex rather than the
> quarantine one. The conclusion is unaffected, because both phases were
> demonstrably still crawling `.git_QUARANTINE_*/objects/` at the 150 s mark,
> which is direct evidence the pattern does not stop that crawl.

Tree A, for reference, is large in its own right and was itself the subject of
an earlier time-boxed probe that did not complete:

```
PHASE2 _QUARANTINE_2026-11-25/: dirs=541 files=1801 bytes=551,900,628 (551.9 MB) maxdepth=15 list_errors=0 elapsed=75.0s budget_hit=True
```

---

## What changed

All three `lftp mirror` invocations (the download, and both `--reverse` uploads)
now use a pattern that allows **any** prefix before `_QUARANTINE_`, so both
trees match:

```yaml
--exclude='(^|/)[^/]*_QUARANTINE_[^/]*/' \
```

Applied at workflow lines **117** (download), **208** (GoDaddy `--reverse`
upload), **254** (`/tdotevent.ca` `--reverse` upload). The earlier ineffective
pattern survives on `origin/main` at lines 103 / 194 / 240.

The two `--reverse` uploads must be patched too, not just the download: the
workflow restores a previous mirror tree (`Restore previous mirror tree
(incremental pulls)`) as a download cache, so quarantined content pulled by an
older run can be carried straight onto `torontoevent.net` / `tdotevent.ca`.

Quarantined content is content deliberately removed by the
`security/2026-11-25-phishing-cleanup` work. Mirroring it would **republish** it.

### Pattern test (no network)

```
pattern-test EXCLUDED  _QUARANTINE_2026-11-25/backups/a.js
pattern-test EXCLUDED  WINDOWSFIXER/MiracleBoot_v7_1_1 - Github code/.git_QUARANTINE_2026-11-25/objects
pattern-test EXCLUDED  _QUARANTINE_X/file.js
pattern-test kept      TORONTOEVENTS_ANTIGRAVITY/index.html
pattern-test kept      audit_dashboard/template.html
```

Both quarantine trees pruned, real production content kept.

### Measured cost after the fix

Whole-tree enumeration with the corrected pattern
(`/tmp/mirror_survey2.py`, log `/tmp/mirror_survey2.log`):

```
TOTAL: dirs=948 files=6540 bytes=640,942,545 (640.9 MB)
       list_errors=0  excluded_entries=79  subtrees_budget_capped=0  elapsed=143s
```

`WINDOWSFIXER` — the subtree that previously ate the entire budget — collapses
to a trivial cost:

```
WINDOWSFIXER   dirs=71 files=17 8.2MB depth=5 exc=2 errs=0  10.0s
```

Throughput probe: 25 files / 5,113,364 bytes in 2.94 s = **1,697.8 KB/s**.

---

## Confirmed local run (this is the verification)

Because `lftp` is not installed on this box and `sudo` needs a password, the
download step was reimplemented in Python `ftplib.FTP_TLS`
(`/tmp/mirror_real_download.py`, log `/tmp/mirror_real_download.log`) against
the real server with the corrected exclude set, and run to completion.

```
LOGIN ok (ejaguiar1@ftps2.50webs.com)  /  PROT P ok

enumeration : 142.7s -> 1064 dirs, 6540 files, 670,502,740 bytes (670.5 MB)
excluded    : 36 dirs, 43 files, 72,814 bytes (0.1 MB)
transfer    : 152.8s, 6287/6540 transferred + 253 already present (resume)
              631,816,404 bytes moved, 0 ERRORS, 4037 KB/s

TOTAL       : 295.7s (4.93 min)   vs the 50-minute step cap
```

**10.1x headroom** against the cap that was previously exhausted without
finishing. Note the transfer rate decayed from 17,247 KB/s to ~4,200 KB/s as the
crawl moved from large assets into small files — the small-file tail is the real
cost driver, which is precisely why a git object store of tiny objects is fatal
and why removing tree B is the fix.

### On-disk verification (byte-for-byte)

```
files: 6540        <- exact match to enumeration
dirs : 1065        <- 1064 + root
bytes: 670,502,740 <- exact match to enumeration
_QUARANTINE_ paths downloaded      : 0
.git_QUARANTINE_ paths downloaded  : 0
```

Real production content present, not just an empty shell:

```
TORONTOEVENTS_ANTIGRAVITY/index.html   278,302 bytes
audit_dashboard/template.html        1,321,506 bytes
index.html                             363,266 bytes
```

### Forensic audit of the full 47-line log

Every line was scanned for `##[error]`, `##[warning]`, `Traceback`,
`ModuleNotFoundError` / `ImportError`, `symbol not found` / `undefined symbol` /
`cannot open shared object`, `No such file or directory`, `command not found`,
auth failures (`401/403/429/530`), timeouts, and retries.

```
hard errors            : none
warnings / deprecations: none
symbol / library       : none
auth / network         : none
retries                : none
```

The only regex matches were benign progress lines and byte counters.

---

## Two anomalies double-checked and cleared

**1. `updates/` is empty in the mirror while all three sites serve it.**
`--exclude='^updates/'` is a **pre-existing, deliberate** exclude. `updates/` is
deployed separately by `tools/deploy_audit_files.py --only updates`, not by the
FTP mirror. Confirmed live on all three hosts:

```
findtorontoevents.ca /updates/index.html  200  3,920,399 bytes
torontoevent.net     /updates/index.html  200  3,920,853 bytes
tdotevent.ca         /updates/index.html  200  3,910,424 bytes
```

Benign — no action. Documented so the next reader does not mistake it for the
mirror dropping content.

**2. Quarantined content is not internet-reachable.** Exposure re-check, both
mirrors:

```
torontoevent.net/_QUARANTINE_2026-11-25/  -> 403
tdotevent.ca/_QUARANTINE_2026-11-25/      -> 403
```

Negative. The exclude is **preventive** (stop future republication), not
incident response.

---

## Static verification

```bash
# 1. all three --exclude blocks carry the corrected pattern exactly once
grep -c -- "--exclude='(^|/)\[\^/\]\*_QUARANTINE_" .github/workflows/mirror-site.yml
# -> 3   (lines 117, 208, 254)
# note: the bare pattern string appears a 4th time at line 78, inside the
#       explanatory comment block -- that is prose, not a flag.

# 2. YAML still parses; triggers intact
python3 -c "import yaml;d=yaml.safe_load(open('.github/workflows/mirror-site.yml'));print(list(d))"
# -> ['name', True, 'permissions', 'concurrency', 'jobs']
python3 -c "import yaml;d=yaml.safe_load(open('.github/workflows/mirror-site.yml'));t=d.get('on') or d.get(True);print(list(t))"
# -> ['schedule', 'workflow_dispatch']

# 3. no new lint diagnostics vs the unmodified file
#    (strip path:line:col first — actionlint prints a ../-prefixed name for a
#     file outside the repo, which would otherwise show up as a spurious diff)
actionlint -oneline .github/workflows/mirror-site.yml \
  | sed -E 's/^[^:]+:[0-9]+:[0-9]+: //' | sort > /tmp/after.txt
# 0 new vs /tmp/before.txt; 11 pre-existing SC2086/SC2129 in the
# `Verify mirrors are live` step are untouched by this change
```

---

## Why the pattern is written this way

`[^/]*_QUARANTINE_[^/]*` matches `.git_QUARANTINE_2026-11-25` and
`_QUARANTINE_X` and `foo_QUARANTINE_bar` alike, but is still anchored to a path
**component** (`(^|/)` … `/`), so it cannot accidentally match a file that
merely contains the word in its name outside a directory boundary, and cannot
match `TORONTOEVENTS_ANTIGRAVITY/index.html`.

Deliberately **not** used: a broad `--exclude-glob='*QUARANTINE*'`, which would
also suppress legitimate files whose names mention "quarantine", and
`--exclude='QUARANTINE'`, which is not anchored to a component.
