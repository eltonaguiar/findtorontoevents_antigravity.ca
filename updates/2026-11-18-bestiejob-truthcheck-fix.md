# BESTIEJOB `truth-check` — gated-domain ingest gate + paywall row purge

**Date:** 2026-11-18 · **Author:** buffy (Freebuff) · **Target repo:** `eltonaguiar/bestiejob`
**Status:** implemented and verified in a local clone; **not pushed** (no PR opened — see "Landing this").

> **Scope note.** This fixes gate #1 of **three** currently-red, unowned BESTIEJOB
> gates. The other two, confirmed still failing after this work: **`Gap channels`**
> (run 44211439366 — step 11/11 `Commit and push`, publish contention) and
> **`board invariants`** (run 44123817042, 2026-11-17T16:16Z — published-board audit
> vs `reports/board_invariants_baseline.json`). No seat has claimed any of the three.

## What was broken

`Job Source Truth Check` (`truth-check.yml`, hourly at `:17`) had failed **15
consecutive runs**, 2026-11-17 13:21Z → 2026-11-18 02:25Z.

Two causes, and the second is the one that kept it red:

1. **13 gated rows in `README.md`** (11 `www.jobleads.com`, 2
   `www.theladders.com`) + 11 in `jobs.json` + 11 in `FRESH_JOBS.md`. These are
   real ServiceNow/Salesforce roles whose only published link is a
   signup/paywall aggregator.
2. **Nothing prevented new ones.** `tools/jobs_merge_inbox.py` filtered sales
   job functions (`EXCL`) and listing pages (`is_listing_url`) but **never
   imported `job_source_truth`**. Only `tools/build_site.py` consulted it
   (line 37) — and merely *labelled* the row `gated` and swapped in a cross-ref
   alternate at render time. So the next harvest that carried a jobleads row
   re-merged it and the gate went red again.

The gate's exit rule is `return 1 if report["gated"] and args.check else 0`,
over README.md + FRESH_JOBS.md + jobs.json — so a single gated row anywhere in
those three artifacts fails the whole hourly job.

## What changed

### 1. `tools/jobs_merge_inbox.py` — drop gated rows at ingest

- `from job_source_truth import domain_is_gated` (same module `build_site.py`
  uses; `tools/` is already on `sys.path` at line 46).
- New counter `gated` in the per-file loop, checked **after**
  `is_listing_url()` and **before** the `EXCL` title filter, so a gated URL is
  never added to `incoming` / `known`.
- Per-file line prints `…, N signup-gated link(s)`; the run summary prints
  `skipped: N rows on signup-gated/paywall domains (see tools/job_source_truth.py)`.
  Visible in CI logs — not a silent drop.

### 2. `config/gated_domains.txt` — the documented-but-missing override file

`_extra_domains()` has always read `config/gated_domains.txt` and silently
no-ops when absent. The file did not exist, so the blocklist was frozen at the
4-host `CORE_GATED_DOMAINS` set with no data-driven extension path. Created it
(mirrors the core set, with the "only add after you have seen it gate a real
posting" instruction preserved).

### 3. `scripts/purge_gated_rows.py` — one-shot purge that keeps the ROLE

Removes gated rows from `README.md`, `FRESH_JOBS.md`, `jobs.json` and retains
each role in **`PAYWALL_ROLES.md`** with cross-ref search links
(Google Jobs / LinkedIn / Indeed / Adzuna) built by
`job_source_truth.annotate()` → `xref`. The role is not lost; the paywall link
is, because it never reaches the employer's posting.

## Verification (actually run)

```
$ python3 scripts/purge_gated_rows.py
README : purged 13 gated rows (8038 -> 8025 lines)
FRESH  : purged 11 lines
json   : purged 11 entries (2858 -> 2847)
ledger : wrote PAYWALL_ROLES.md with 13 roles + cross-refs

$ python3 tools/job_source_truth.py --check
scanned=3 total=13581 gated=0
truth-check exit=0          <-- was exit 1 for 15 hours

$ node scripts/check_readme_sort.mjs
OK: 4 Posted-column tables are newest-first
exit=0
```

Gate behaviour, proven with a synthetic inbox submission containing one
jobleads row and one clean LinkedIn row:

```
$ python3 tools/jobs_merge_inbox.py --dry-run
testagent--2026-11-18--v1.md: +1 new, 0 duplicate, 1 signup-gated link(s)
  will add [servicenow] 2026-11-18 ServiceNow Admin — Beta Corp
```

The gated row is dropped and counted; the clean row survives. (An existing
inbox file, `round11-cached--2026-11-05--v62.md`, also reports **8
signup-gated links** that were previously being merged — the gate is finding
live traffic, not just the 13 historical rows.)

## Landing this

The work is in a local clone at `/tmp/bj-inspect` (shallow, HEAD of
`eltonaguiar/bestiejob` @ 2026-11-18T02:18Z). Patch and changed files are copied
to `updates/2026-11-18-bestiejob-truthcheck-fix/` in this repo so nothing is
lost:

| File | Change |
|---|---|
| `tools/jobs_merge_inbox.py` | + import, + gated counter, + drop branch |
| `config/gated_domains.txt` | new |
| `scripts/purge_gated_rows.py` | new |
| `PAYWALL_ROLES.md` | new (13 roles + xrefs) |
| `README.md` | −13 rows |
| `jobs.json` | −11 entries |
| `FRESH_JOBS.md` | −11 lines |

To land: apply the patch on a branch, push, and let `truth-check.yml` run on the
push trigger (`paths:` includes `README.md`, `jobs.json`,
`tools/job_source_truth.py`) or dispatch it manually.

## Caveats

- `scripts/board_invariants.py` on the clone still reports its pre-existing
  ratchet breaches (location-ambiguous 1111>821, non-canada 1113>1108, …) and a
  header/tables count disagreement (`header claims 7588 live postings, tables
  hold 7856`). Both predate this change — the tables held 7869 before the purge,
  so the mismatch was 281 rows and is now 268. The purge did not create it.
- Table header counts ("Show 1325 postings") are not re-rendered by the purge;
  the next scheduled scan re-renders them.
- The 13 roles keep real values in `PAYWALL_ROLES.md`, but their `Company`
  column was often `Unknown` in the source rows — that is the aggregator's
  data, not a parsing bug.
