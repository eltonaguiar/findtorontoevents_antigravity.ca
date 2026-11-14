# Archive Index — 2026-11-14 / finpredict-v2

**Subtree:** `finpredict-v2`
**Timestamp:** `2026-11-14T16:02Z` (folder `finpredict-v2_20261114-1602`)
**Audit clock:** 2026-11-14T16:05Z
**Status:** complete; peer cross-referenced; ready for master review

## Deliverables

| File | Purpose |
|---|---|
| `MASTER_AUDIT.md` | **Primary deliverable.** Actions health, active picks per asset class, frozen data, closed picks, verdict, direct answers, peer reconciliation, UNVERIFIED list |
| `PEER_CROSSREF.md` | Side-by-side matrix of `finpredict` v1 / v2 / v3 / v4 + `inspect-wt` transcript |
| `sub/A_actions_health.md` | 365-workflow health, failure clusters, logs |
| `sub/A_workflow_matrix.csv` | Per-workflow last-run matrix |
| `sub/B_dashboard_freshness.md` | Freshness + metric liveness + dead tabs |
| `sub/C_crypto.md` | Crypto per-symbol audit + Binance cross-check |
| `sub/D_non_crypto.md` | EQUITY/FOREX/ETF/BOND/FUTURES/COMMODITY/MF audit |
| `sub/E_statistical.md` | Multiple-testing, PBO/DSR, per-class z, survivorship |
| `sub/F_sources.md` | Kalshi/Polymarket/copy-trader/Hyro authenticity |
| `sub/G_peer_reconciliation.md` | Peer artifact inventory |
| `recommendations/` | Ranked remediation: `QUICK_WINS.md`, `overall/ROADMAP.md`, `overall/DATA_CONTRACT.md`, `overall/CI_GATES.md`, `per_asset_class/*.md`, `patch_plan/*.md` |
| `recommendations/peer_review/` | 4 reviewer memos + `REVIEW_SYNTHESIS.md` (corrections applied) |
| `raw/` | Live JSON, GitHub API JSON, workflow logs, per-symbol extracts |

## Headline verdict

**FAIL.** The system is not genuinely profitable and not statistically sound. Fleet
policy-clean ledger: n=22,941, WR 42.21%, PF 0.2657, z=−23.60. 0/9 asset classes
money-ready. The visible winners are explained by ~32.9 expected false positives at
N=658 tests plus a correlated single-source resolver artifact plus survivorship
(63% of picks never resolve).

## Reproduction (read-only)

```bash
# live payloads (capture ~16:03Z)
for f in dashboard_data dashboard_payload money_ready_verdict pf_registry \
         anti_overfit_audit audit_surface_truth summary_picks db_health \
         hyro_pick_performance hyrotrader_picks ma_strategy_leaderboard; do
  curl -sS "https://findtorontoevents.ca/audit/data/$f.json" -o "raw/$f.json"
done

# GitHub Actions
gh api repos/eltonaguiar/findtorontoevents_antigravity.ca/actions/workflows --paginate > raw/A_workflows.json
gh run list --repo eltonaguiar/findtorontoevents_antigravity.ca --limit 500 \
  --json databaseId,workflowName,status,conclusion,createdAt,updatedAt > raw/A_runs.json

# external quotes
curl -sS "https://api.binance.com/api/v3/ticker/price?symbol=NEARUSDT"
curl -sS "https://open.er-api.com/v6/latest/USD"
```

## Caveats

- `picks.recent_closed` sums and the "flat-3% cohort" count are peer-computed from the
  same live file (attributed in `MASTER_AUDIT.md` §4/§3); they are not fabricated.
- Runs captured as failure and later auto-retried are labelled `UNVERIFIED` for root cause.
- No repo source files were modified by this audit; only this archive folder was added.
