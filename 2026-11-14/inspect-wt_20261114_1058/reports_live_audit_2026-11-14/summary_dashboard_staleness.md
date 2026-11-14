# Dashboard staleness map (findtorontoevents.ca/audit + /audit/hyrotrader) — 2026-11-14 ~15:45Z

Sources: live site data files (all fetched), `.github/workflows/*.yml` from GitHub API + worktree, GitHub Actions runs API.

**VERDICT: FAIL — the core dashboard refreshes hourly and its freshness claims on the main panel are TRUE, but multiple supporting surfaces are dead, stale, or 404, and the /audit/hyrotrader performance panel is 6.6 days stale despite its workflow "succeeding" daily.**

## File-level freshness (verified timestamps)

| File | generated_at (UTC) | Age | Verdict |
|---|---|---|---|
| dashboard_data.json | 2026-11-14T14:30:07 | 1.4h | FRESH |
| dashboard_payload.json | 2026-11-14T14:30:07 | 1.4h | FRESH |
| pf_registry.json | 2026-11-14T14:30:05 | 1.4h | FRESH |
| money_ready_verdict.json | 2026-11-14T14:29:00 | 1.4h | FRESH |
| summary_picks.json | 2026-11-14T14:30:06 | 1.4h | FRESH |
| ma_strategy_leaderboard.json | 2026-11-14T14:25:04 | 1.5h | FRESH |
| anti_overfit_audit.json | 2026-11-14T14:22:00 | 1.5h | FRESH |
| db_health.json | 2026-11-14T14:13:42 | 1.6h | FRESH |
| stock_prices.json | 2026-11-14T14:13:38 | 1.6h | FRESH |
| audit_surface_truth.json | 2026-11-14T04:52:51 | 11h | AGING (should be hourly?) |
| **hyro_pick_performance.json** | **2026-11-08T02:14:09** | **157h** | **STALE 6.6 days** |
| hyrotrader_picks.json | (no timestamp field) | unknown | SUSPECT STATIC |
| pick_funnel_snapshot.json | (served 404 HTML) | — | BROKEN |

## Key findings

1. **"Crypto 1.9h ago" is TRUE** on the visible Active Picks panel (`.picks.active` newest rows 1.5–3.6h per class). The staleness is hidden in `.picks.active_raw` (median age 89d for crypto) — the visible panel is a curated top layer.
2. **hyro_pick_performance.json stale 157h while the "Hyro daily (filter+backtest)" workflow succeeded 2026-11-14T13:37** — the workflow runs and reports success but the deployed file doesn't update. Either it writes a different file/path than the FTP deploy uploads, or its output upload is silently failing. This is a silent pipeline break; the /audit/hyrotrader page is showing week-old performance as if current. **Root cause UNVERIFIED** (needs workflow log access / repo admin).
3. **hyrotrader_picks.json has no generated_at** and contains static strategy templates ("hyro-v2-btc-cci" etc. with embedded backtest stats) — consistent with a never-regenerated template file.
4. **pick_funnel_snapshot.json is a 404 page** — any dashboard section sourcing it renders nothing/broken.
5. **GitHub Actions health (same day):** audit-dashboard hourly run cancelled-while-queued 3 of last 10 (0 jobs executed); ALPHA ENGINE Live Scanner failing; Daily Prices yfinance failing 2 nights; CI Tests failing. Deploys land ~70% of hours.
6. **data_freshness self-report:** present in payload; the dashboard has freshness JS (dashboard_freshness.js) — main-panel ages are computed from real timestamps and are honest for the visible panel.
7. **audit_surface_truth.json 11h old** — the "0/9 money-ready" headline users see may be half a day behind the hourly payload.

## Not verified from these files
- Exact tab-by-tab render mapping in template.html (18,974 lines) — requires the frontend trace; the five planned subagent deep-dives (crypto / equity-ETF-bond / forex-futures-commodity / staleness / statistical) were interrupted and remain for the review agent.
- Funds page (`funds.html`) internals; ai_leaderboard internals.
