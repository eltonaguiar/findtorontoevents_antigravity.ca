# URL audit: the five reported redirects and 404s

Checked 2026-11-17T09:31Z with `curl -A audit-check`.

| URL | Result | Why |
|---|---|---|
| `https://findtorontoevents.ca/` | 301 → `/index.html` | Intentional host rule. `/index.html` returns 200, 363,266 bytes. Not an error. |
| `https://findtorontoevents.ca/audit` | 301 → `/audit/` | Trailing-slash canonicalization for a directory. Not an error. |
| `https://findtorontoevents.ca/audit/` | 200, 1,313,441 bytes | Healthy. |
| `https://findtorontoevents.ca/grok_top_picks.json` | 404 | Wrong path. The file is published under `/audit/`. |
| `https://findtorontoevents.ca/data/grok_top_picks.json` | 404 | The public web root does not publish the repo `data/` tree. |
| `https://findtorontoevents.ca/aggregated_picks.json` | 404 | Never published to the site at all. |

## grok_top_picks.json is deployed, just not at the root

`audit_dashboard/data/grok_top_picks.json` is uploaded to `_site/audit/data/grok_top_picks.json` by `.github/workflows/deploy-riseoftheclaw.yml` (lines ~504-517). Live and working:

- https://findtorontoevents.ca/audit/data/grok_top_picks.json — 200, `application/json`, 1,686 bytes
- https://findtorontoevents.ca/audit/data/grok_top_picks_phase2.json — 200, 2,549 bytes

The deploy workflow still runs (run `44055272109` succeeded 2026-11-17T09:24Z). The root and `/data/` copies do not exist because the public docroot only carries `audit/` plus the root HTML pages. `/data/db_health.json` is also 404 for the same reason, which confirms it is a docroot layout fact rather than a broken deploy.

## aggregated_picks.json exists but is not published

- Repo file: `data/aggregated_picks.json` (tracked, 8,321 bytes locally, updated by `.github/workflows/cross-aggregator.yml`, which `git add`s it).
- Live raw: https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/data/aggregated_picks.json — 200, 11,813 bytes.
- Live site path: 404. No workflow copies it into `_site/`. `cross_aggregator` writes and commits it; it never deploys it.

## Canonical URLs to use instead

| Need | Use |
|---|---|
| Main site | `https://findtorontoevents.ca/index.html` (or `/` and follow the redirect) |
| Audit page | `https://findtorontoevents.ca/audit/` (with the slash) |
| grok picks | `https://findtorontoevents.ca/audit/data/grok_top_picks.json` |
| aggregated picks | `https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/data/aggregated_picks.json` |
| Audit JSON | `https://findtorontoevents.ca/audit/data/dashboard_data.json` (200, 25,106,456 bytes) |

## Optional fix, not done here

If a site-hosted aggregated picks file is actually wanted, add one copy step to `deploy-riseoftheclaw.yml`:

```
cp data/aggregated_picks.json _site/audit/data/aggregated_picks.json 2>/dev/null || true
```

That is a deploy change. It belongs with the GHA seat, not this note. Until someone asks for it, the raw GitHub URL is the supported path and every consumer that reads the repo path already works.
