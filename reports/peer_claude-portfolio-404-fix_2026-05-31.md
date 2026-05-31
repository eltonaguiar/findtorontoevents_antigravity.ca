# Portfolio Mix 404 Investigation — 2026-05-31

## TL;DR

**FALSE ALARM.** The 5 portfolio_mix JSONs are deployed and serving 200 with full
JSON bodies. The verification wave `wohr9rm0x` curled the **wrong URL pattern**
(`/audit/data/pf/portfolio_mix__*.json` — subdir form) rather than the actual
URL pattern that `pf.html` fetches (`/audit/data/pf_portfolio_portfolio_mix__*.json`
— flat form with `pf_portfolio_` prefix).

No FTP re-deploy required. Verification wave's URL pattern needs to be
corrected.

## Pre-fix curl table (verification wave's URL — WRONG path)

| Key | URL | Status |
|---|---|---|
| conservative_top1 | /audit/data/pf/portfolio_mix__conservative_top1.json | 404 |
| balanced_top3 | /audit/data/pf/portfolio_mix__balanced_top3.json | 404 |
| aggressive_top5 | /audit/data/pf/portfolio_mix__aggressive_top5.json | 404 |
| diversified_per_class | /audit/data/pf/portfolio_mix__diversified_per_class.json | 404 |
| sharpe_optimized | /audit/data/pf/portfolio_mix__sharpe_optimized.json | 404 |

## Root cause diagnosis

`audit_dashboard/pf.html` line 363 fetches:

```js
var resp = await fetch('./data/pf_portfolio_' + safe + '.json?' + Date.now());
```

…where `safe = safeKey(key)` and `key` is `portfolio_mix__<variant>`. The
constructed URL is therefore:

  `/audit/data/pf_portfolio_portfolio_mix__<variant>.json`

(flat file under `audit/data/`, with prefix `pf_portfolio_`).

PR #218 wrote files at exactly this path:

```
audit_dashboard/data/pf_portfolio_portfolio_mix__aggressive_top5.json
audit_dashboard/data/pf_portfolio_portfolio_mix__balanced_top3.json
audit_dashboard/data/pf_portfolio_portfolio_mix__conservative_top1.json
audit_dashboard/data/pf_portfolio_portfolio_mix__diversified_per_class.json
audit_dashboard/data/pf_portfolio_portfolio_mix__sharpe_optimized.json
```

Confirmed via `git ls-tree origin/main audit_dashboard/data/`.

The verification wave (`wohr9rm0x`) constructed its check URLs by assuming a
nonexistent `pf/` subdirectory and stripping the `pf_portfolio_` prefix. This
mismatch produced 5 false 404s against the live site, while the dashboard's
own loader works fine.

## Action taken

None on FTP. The files are already deployed correctly at the URL pattern that
`pf.html` actually fetches. Only this diagnostic report is added.

## Post-fix curl table (correct URL pattern — what pf.html actually fetches)

| Key | URL | Status | Bytes |
|---|---|---|---|
| conservative_top1 | /audit/data/pf_portfolio_portfolio_mix__conservative_top1.json | 200 | 138,646 |
| balanced_top3 | /audit/data/pf_portfolio_portfolio_mix__balanced_top3.json | 200 | 315,686 |
| aggressive_top5 | /audit/data/pf_portfolio_portfolio_mix__aggressive_top5.json | 200 | 569,401 |
| diversified_per_class | /audit/data/pf_portfolio_portfolio_mix__diversified_per_class.json | 200 | 98,634 |
| sharpe_optimized | /audit/data/pf_portfolio_portfolio_mix__sharpe_optimized.json | 200 | 279,468 |

## Recommendation

Update verification harness `wohr9rm0x` to derive check URLs from
`pf.html`'s actual fetch pattern (line 363) rather than guessing
`/data/pf/<key>.json`. Suggest reading the fetch template directly out of
the HTML so the harness stays in sync with future loader changes.
