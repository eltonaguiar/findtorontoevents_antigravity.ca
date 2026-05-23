# Audit Mobile Load Fix Verification — 2026-05-03

**Session:** 2026-05-03T03:48 UTC  
**PRs verified:** #717 (drop _scoreBreakdown duplicate), #718 (Apache gzip .htaccess)  
**Overall verdict: PARTIAL — Track A (gzip) pending cron deploy; Track B-1 (_scoreBreakdown) INEFFECTIVE for existing stored picks**

---

## 1. CI Status

### PR #717 check runs (head: `ec535dbe`)
| Job | Status | Completed |
|-----|--------|-----------|
| scan | ✅ success | 2026-05-03T02:45:35Z |
| drift | ✅ success | 2026-05-03T02:45:29Z |

### PR #718 check runs (head: `db7fec1a`)
| Job | Status | Completed |
|-----|--------|-----------|
| scan | ✅ success | 2026-05-03T02:47:40Z |
| drift | ✅ success | 2026-05-03T02:48:00Z |

### Post-merge audit-dashboard.yml run
The push trigger fired immediately on PR #717 merge (02:43 UTC) because `audit_trail/dashboard_generator.py` and `audit_dashboard/template.html` are both in the path filter. The run completed and committed:

```
5a6fdc90 chore(audit-dashboard): refresh payload [skip ci]
committed: 2026-05-03T03:22:40Z  (39 min after merge — consistent with 30-35 min runtime)
```

**PR #718's path changes (`.htaccess`, `.github/workflows/audit-dashboard.yml`) are NOT in the push trigger path filter.** The .htaccess will be uploaded to production via FTP in the next scheduled cron run (04:10 UTC).

---

## 2. Track B-1: _scoreBreakdown Dedup Fix (PR #717)

### Code fix: CONFIRMED
`audit_trail/dashboard_generator.py` line ~13887 — the duplicate write is removed. Comment at line 13974 confirms removal date:
```python
# _scoreBreakdown was a byte-identical duplicate of elite_breakdown
# adding ~4.4 MB to dashboard_data.json (1267 B/pick * 3500 picks).
# Removed 2026-05-03 to cut mobile load times.
```

Fallback path at line 14107 still writes `{_fallback: True}` for un-enriched picks — correct behaviour per PR description.

### Runtime effect: INEFFECTIVE (fix did not reduce file size)

Expected: `dashboard_data.json` ~17 MB  
Actual (post-03:22 CI run): **21,893,568 bytes (20.9 MB)**

Root cause — the `_scoreBreakdown` field is persisted in the source data, not computed on-the-fly:

```
Measurement: audit_trail/data/dashboard_payload.json (30.8 MB, regenerated at 03:22)
  picks.recent_closed: 3500 picks, _scoreBreakdown count = 3500
  picks.active:         27 picks, _scoreBreakdown count = 23
  picks.active_raw:    215 picks, _scoreBreakdown count = 201

  _scoreBreakdown total bytes across 3500 recent_closed picks: 4,872,934 (~4.65 MB)
  elite_breakdown total bytes (same picks):                      4,872,934 (~4.65 MB)
  Are they byte-identical in pick[0]? True
  _fallback key in pick[0]._scoreBreakdown? False  ← real data, not fallback
```

**The removed line (`pick["_scoreBreakdown"] = result["elite_breakdown"]`) was writing `_scoreBreakdown` to NEW picks during a scoring sub-step in the generator. The 3500 picks already in `dashboard_payload.json` (the intermediate file that feeds `dashboard_data.json`) had `_scoreBreakdown` persisted from previous runs. When the generator regenerates `dashboard_data.json`, it reads `dashboard_payload.json` pick-by-pick and copies ALL fields, including the already-stored `_scoreBreakdown`.**

The fix prevents `_scoreBreakdown` from being written to picks that are scored after 2026-05-03, but does not strip it from the 3500+ already-stored picks. The ~4.65 MB field stays in the payload until those picks age out of `recent_closed`.

### Recommended follow-up fix
Add an explicit strip in the generator's assembly step when building the final `dashboard_data.json` output. Example (generator read path, wherever picks are assembled for the output dict):
```python
# Strip legacy duplicate field — already in elite_breakdown
pick.pop("_scoreBreakdown", None)
```
This would immediately recover ~4.65 MB on the next CI run without waiting for pick rotation.

---

## 3. Track A: Apache Gzip via .htaccess (PR #718)

### Code fix: CONFIRMED
`audit_dashboard/.htaccess` exists locally (2433 bytes, committed 2026-05-03 in merge commit `cdaf1a71`). Content is correct:
- `<IfModule mod_deflate.c>` block with `AddOutputFilterByType DEFLATE application/json` (and html/js/css/xml/svg)
- `Header append Vary Accept-Encoding`
- Cache-Control 5-min must-revalidate for `.json` and dashboard HTML files

FTP upload wired at `.github/workflows/audit-dashboard.yml:708`:
```python
ftp_upload(ftp, "audit_dashboard/.htaccess", f"/{SITE_ROOT}/audit", ".htaccess", label)
```
Wrapped in try/except (non-fatal on upload failure).

### Deployment status: PENDING (not yet in production)

The 03:22 CI run was triggered by PR #717's merge commit `a8bb42e7` (02:43 UTC). PR #718 merged 2 minutes later at 02:45 UTC. The runner checked out at `a8bb42e7`, which predates the `.htaccess` addition — the file was not present in that checkout and was not FTP-uploaded.

PR #718's push did NOT trigger a new audit-dashboard run (neither `.htaccess` nor `.github/workflows/audit-dashboard.yml` are in the path filter).

**Next opportunity: cron run at 04:10 UTC.** That run will check out the latest main (which includes PR #718) and upload `.htaccess` to `/audit/` via FTP. Gzip headers will be live from that point if `mod_deflate` is enabled on the 50webs vhost.

### Live gzip verification: BLOCKED by CDN

All curl probes from this environment return `403 host_not_allowed` from an upstream proxy/CDN — not an Apache response:

```
curl -sI -H 'Accept-Encoding: gzip' https://findtorontoevents.ca/audit/data/dashboard_data.json
HTTP/2 403
x-deny-reason: host_not_allowed
content-length: 21
```

This is a CDN IP allowlist blocking the probe environment — not a server misconfiguration. **Cannot directly confirm `Content-Encoding: gzip` from this environment.** Verification must be done from a browser or non-blocked IP after 04:10 UTC.

---

## 4. .htaccess Visibility Check

```
curl -s -o /dev/null -w '%{http_code}' https://findtorontoevents.ca/audit/.htaccess
→ 403
```

Result is 403 (not 200), which is the expected safe result. However, this 403 may be from the CDN block rather than Apache's own protection. Consider re-verifying from a clean IP after 04:10.

---

## 5. Summary Table

| Check | Expected | Actual | Status |
|-------|----------|--------|---------|
| PR #717 CI checks | all green | scan ✅ / drift ✅ | PASS |
| PR #718 CI checks | all green | scan ✅ / drift ✅ | PASS |
| audit-dashboard.yml ran post-merge | yes | ✅ 03:22 UTC | PASS |
| dashboard_data.json shrunk to ~17 MB | ~17 MB | 20.9 MB (unchanged) | **FAIL** |
| _scoreBreakdown absent from payload | 0 picks | 3500 picks still have it | **FAIL** |
| .htaccess deployed to production | yes | not yet (next cron 04:10) | **PENDING** |
| Content-Encoding: gzip live | yes | unverifiable (CDN block) | **BLOCKED** |
| .htaccess returns 403/404 | 403 or 404 | 403 | PASS (ambiguous) |

---

## 6. Action Items

1. **[P0 — PR #717 follow-up]** Open a new PR to add `pick.pop("_scoreBreakdown", None)` in the generator's assembly step (wherever `recent_closed` picks are written to the final output dict). This strips the 4.65 MB field from existing stored picks on the next CI run and completes the Track B-1 savings.

2. **[After 04:10 UTC]** Verify gzip is live from a non-blocked IP:
   ```bash
   curl -sI -H 'Accept-Encoding: gzip' https://findtorontoevents.ca/audit/data/dashboard_data.json
   # expect: Content-Encoding: gzip
   ```
   If `Content-Encoding: gzip` is absent, 50webs may have `mod_deflate` disabled at the vhost level (see PR #718 body for this known risk). If so, open an issue noting the curl evidence.

3. **[After step 1 + 2]** Verify the combined fix: post-strip + post-gzip payload should be ~1–2 MB on the wire (4.65 MB `_scoreBreakdown` gone → ~16.3 MB raw → ~1.6–2.5 MB gzipped).
