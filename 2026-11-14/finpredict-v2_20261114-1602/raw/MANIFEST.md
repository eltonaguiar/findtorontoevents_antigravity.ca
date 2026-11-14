# Raw evidence manifest

**Captured:** 2026-11-14T16:03–16:06Z
**Live base:** `https://findtorontoevents.ca/audit/data/`

## Retained (small, reviewable)

- `summary_picks.json`, `audit_surface_truth.json`, `db_health.json`,
  `money_ready_verdict.json`, `hyro_pick_performance.json`, `hyrotrader_picks.json`,
  `anti_overfit_audit.json`, `ma_strategy_leaderboard.json`
- `A_workflows.json`, `A_runs500.json`, `A_fail48.json` — GitHub Actions API captures
- `per_strategy_agg.csv` — per-strategy PF/WR/n aggregate used in `sub/E_statistical.md`
- `binance_1d_{BTC,ETH,SOL,XRP,NEAR}USDT.json` — external price cross-check candles
- `representative_picks.json`, `symbol_stats*.json`, `zombie_flags.txt`,
  `page_audit.html`, `page_audit_hyrotrader.html`, `js_dashboard_enhancements.js`

## Pruned to keep the archive commit small (all reproducible)

| Removed | Size | Reproduce from |
|---|---:|---|
| `logs/*.log` (incl. 795 MB run log) | ~799 MB | `gh run view <id> --log` |
| `dashboard_data.json`, `live_data_dashboard_data.json` | 48 MB | `https://findtorontoevents.ca/audit/data/dashboard_data.json` |
| `dashboard_payload.json`, `live_data_dashboard_payload.json` | 66 MB | `https://findtorontoevents.ca/audit/data/dashboard_payload.json` |
| `pf_registry.json`, `pf_registry.json.json` | 30 MB | `https://findtorontoevents.ca/audit/data/pf_registry.json` |
| `A_all7d_runs.json`, `A_rows.json`, `A_aggregate.json` | 24 MB | GitHub Actions API |
| `wf/`, `wf7d_full/` | 11 MB | `gh api .../actions/workflows/<id>/runs` |

The full payloads were `generated_at = 2026-11-14T14:30:07Z`. Re-fetching them after the
next hourly rebuild returns newer data, so the retained **reports** (`../sub/`, `../MASTER_AUDIT.md`
and `../recommendations/`) are the stable evidence for this audit.

## Probe commands used

```bash
curl -sS "https://findtorontoevents.ca/audit/data/<name>.json"
gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows --paginate
gh run list --repo eltonaguiar/findtorontoevents_antigravity.ca --limit 500 \
  --json databaseId,workflowName,status,conclusion,createdAt,updatedAt
curl -sS "https://api.binance.com/api/v3/klines?symbol=NEARUSDT&interval=1d&limit=30"
curl -sS "https://open.er-api.com/v6/latest/USD"
```
