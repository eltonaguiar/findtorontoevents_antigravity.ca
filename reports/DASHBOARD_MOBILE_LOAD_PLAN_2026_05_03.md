# Dashboard Mobile Load — Diagnosis + Plan

**Date:** 2026-05-03
**Trigger:** User report — "/audit shows 'No data loaded' on mobile."

## Diagnosis

Live `audit_dashboard/data/dashboard_data.json` is **21.7 MB uncompressed**. Apache serves with NO `Content-Encoding` (verified — `Vary: User-Agent` only, missing `Accept-Encoding`). On mobile cellular this fetch routinely times out before init completes. When init throws, the empty-state at `template.html:16375` fires with the literal message: `No data loaded — Run the generator: python -m audit_trail.dashboard_generator`. The generator instruction is misleading — the generator has been running fine; the problem is wire size, not stale generation.

## Bloat profile (top-level keys)

| Key | Size | % | Notes |
|---|---|---|---|
| `picks` | 17.54 MB | 84.4% | dominated by `recent_closed` |
| `leaderboard` | 1.10 MB | 5.3% | 1639 entries |
| `cross_system_permutations` | 990 KB | 4.7% | |
| `systems` | 413 KB | 1.9% | 131 entries |
| `walkforward` | 153 KB | 0.7% | |
| (28 other keys) | <500 KB combined | <2% | |

Drilling `picks`:

| Sub-key | Size | n |
|---|---|---|
| `recent_closed` | 15.98 MB | 3500 picks (avg 4.7 KB each) |
| `active_raw` | 1.30 MB | 182 |
| `active` | 0.25 MB | 33 |
| `smart_picks` | 0.01 MB | 1 |

Per-pick top fields in `recent_closed`:
- `elite_breakdown` 1267 B
- `_scoreBreakdown` 1267 B — **byte-identical duplicate of `elite_breakdown` in 3500/3500 picks**
- `ml_composite_breakdown` 443 B

## Three tracks (ranked by ship-now leverage)

### Track B-1 — drop `_scoreBreakdown` duplicate (THIS PR)

`audit_trail/dashboard_generator.py:13887` writes `pick["_scoreBreakdown"] = result["elite_breakdown"]`. Pure duplicate. Removed.

JS reads at `audit_dashboard/template.html:7453, 15058, 16759, 17038` patched to prefer `elite_breakdown` with `_scoreBreakdown` fallback (backward-compat for cached payloads).

JS write at `:9447` (`p._scoreBreakdown = computed.breakdown`) left alone — only fires for picks that arrive without breakdown, caches in-memory only.

**Saves ~4.4 MB on the wire (21.7 → 17.3 MB) once the next CI generator cycle runs.**

### Track A — Apache gzip (NEXT PR)

`.htaccess` at `/audit/` enables `mod_deflate` for `application/json` + `text/html`. 50webs supports this. Estimated wire reduction: 60-80% (17 MB → ~3-5 MB gzipped). Combined with Track B-1: 21.7 MB → ~3-4 MB gzipped delivered.

Ship as a tiny PR with the `.htaccess` content for FTP upload. No JSON change.

### Track B-2 — paginate `recent_closed` (FOLLOW-UP)

Generate `dashboard_data.json` with `recent_closed` capped at 1000 most recent (vs current 3500). Save full to `dashboard_data_full.json`. Default fetch lite. Desktop "Load full history" button swaps to full URL.

**Saves another ~10 MB raw / ~1.5 MB gzipped.** Requires generator change + JS state for fetch URL toggle. Defer until Tracks B-1 + A confirm in production.

### Track C — mobile-lite path (OPTIONAL FOLLOW-UP)

After B-1 + A + B-2, if mobile is still slow:
- `audit_dashboard/data/dashboard_data_lite.json` with only `active` picks + `summary` + `asset_class_health` (~500 KB raw / ~80 KB gzipped)
- `audit_dashboard/mobile.html` minimal template
- `.htaccess` UA-detect rewrite to `/audit/mobile-choice.html` decision page (cookie-remembered)

Reviewer agent flagged that this adds FTP-sync burden (mobile.html drifts behind template.html). Recommended alternative: single `template.html` with CSS media-query + JS branch. Decision deferred until B-1 + A measurement.

## Why not run the generator locally per the empty-state instruction

Per CLAUDE.md and memory `feedback_never_test_overwrite_live`: running `python -m audit_trail.dashboard_generator` locally overwrites the live HTML. The instruction in the empty-state message is for CI only. Better path: trigger CI workflow on demand (`gh workflow run audit-dashboard.yml`).

## Verification

After this PR merges + CI runs:

```bash
curl -sI https://findtorontoevents.ca/audit/data/dashboard_data.json | grep -i content-length
# expect: ~17 MB (down from 21.7 MB)
```

After Track A merges + .htaccess uploaded:

```bash
curl -sI -H "Accept-Encoding: gzip" https://findtorontoevents.ca/audit/data/dashboard_data.json | grep -iE "content-encoding|content-length"
# expect: Content-Encoding: gzip, Content-Length: ~3-4 MB
```

## Cross-references

- Live data file: `audit_dashboard/data/dashboard_data.json` (Last-Modified Sun, 03 May 2026 02:04:45 GMT)
- Empty-state literal: `audit_dashboard/template.html:16375`
- Generator duplicate write: `audit_trail/dashboard_generator.py:13887`
- JS read sites: `audit_dashboard/template.html:7453, 15058, 16759, 17038`
- JS write/cache site (unchanged): `audit_dashboard/template.html:9447`
- Reviewer second-opinion: cavecrew-reviewer agent 2026-05-03
