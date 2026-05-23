# Audit Links Audit 2026-05-12

## Summary
5 of 8 new audit sidebar pages are **missing from FTP deployment config** in `.github/workflows/audit-dashboard.yml`. Files exist locally but are 404 on production.

## Root Cause
Lines 846-847, 923, 957 in `audit-dashboard.yml` hardcode page whitelists. Missing pages:
- `paper_pilot.html` (created 2026-05-11 23:00Z)
- `anti_overfit.html` (created 2026-05-11 18:06Z)
- `edge_stability.html` (created 2026-05-11 16:29Z)
- `real_money.html` (created 2026-05-11 10:00Z)
- `research_sidecars.html` (created 2026-05-11 17:50Z)
- `research_index.html` (created 2026-05-11 17:50Z)

## Deployment Status

| Page | Local File | HTTP 200? | Commit Date | Site Status |
|------|-----------|-----------|-------------|------------|
| index.html | ✓ 1.2MB | ✓ 200 | 2026-05-12 00:55Z | LIVE |
| trading_blueprint.html | ✓ 186KB | ✓ 200 | 2026-05-06 15:29Z | LIVE (in whitelist) |
| funds.html | ✓ 206KB | ✓ 200 | 2026-05-06 15:29Z | LIVE (in whitelist) |
| dashboard_enhancements.js | ✓ | ✓ 200 | - | LIVE (in whitelist) |
| **paper_pilot.html** | ✓ 13KB | **✗ 404** | 2026-05-11 23:00Z | **DEAD** (not in whitelist) |
| **anti_overfit.html** | ✓ 8.3KB | **✗ 404** | 2026-05-11 18:06Z | **DEAD** (not in whitelist) |
| **edge_stability.html** | ✓ 9.6KB | **✗ 404** | 2026-05-11 16:29Z | **DEAD** (not in whitelist) |
| **real_money.html** | ✓ 20.5KB | **✗ 404** | 2026-05-11 10:00Z | **DEAD** (not in whitelist) |
| **research_sidecars.html** | ✓ 12.7KB | **✗ 404** | 2026-05-11 17:50Z | **DEAD** (not in whitelist) |
| research_index.html | ✓ 15KB | **✗ 404** | 2026-05-11 17:50Z | **DEAD** (not in whitelist) |
| hyrotrader/ | ✓ subdir | ✓ 200 | - | LIVE |

## Broken Links in template.html (lines 851, 1082, 1089, 1283)

```html
<!-- Line 851 -->
<a href="/audit/paper_pilot.html" style="color:#06b6d4">paper_pilot.html</a>  → 404

<!-- Line 1082 -->
<a href="/audit/anti_overfit.html" style="color:#06b6d4">Anti-Overfit Audit</a>  → 404

<!-- Line 1089 -->
<a href="/audit/edge_stability.html">edge-stability</a>  → 404

<!-- Line 1283 -->
<a href="real_money.html">Real Money</a>  → 404

<!-- Line 68 in real_money.html -->
<a href="/audit/paper_pilot.html" style="color:#fbbf24">...</a>  → 404
```

## FTP Deployment Whitelist Gaps

**Lines 846-847 (50webs findtorontoevents.ca):**
```python
for page in ["claudes_test.html", "trading_blueprint.html", "funds.html",
             "kimi_top_picks.html", "antigravity_picks.html", "portfolio_history.html"]:
```
Missing: `paper_pilot.html`, `anti_overfit.html`, `edge_stability.html`, `real_money.html`, `research_sidecars.html`, `research_index.html`

**Line 923 (GoDaddy torontoevent.net):**
```python
for page in ["claudes_test.html", "trading_blueprint.html", "funds.html"]:
```

**Line 957 (50webs tdotevent.ca):**
```python
for page in ["funds.html", "claudes_test.html", "trading_blueprint.html"]:
```

## Implications

- `template.html` cites 4+ broken links in the MAJOR GOALS banner + nav pills (lines 851, 1082, 1089, 1283)
- Users encounter 404 when clicking "paper_pilot.html", "Real Money hub", "Anti-Overfit Audit"
- Real-money readiness gate (`real_money.html`) completely unreachable
- Goal #1 (phenomenal performance audit) blocked because core sidecar pages invisible

## Resolution

Update `.github/workflows/audit-dashboard.yml` lines 846-847, 923, 957 to include all 6 missing pages in the whitelist. After next GHA run, all pages will deploy to FTP.
