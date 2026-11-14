# Evidence Index (final_v3, 2026-11-14)

**All performance statements tied to named cohort and timestamp. Peer-reported backtest metrics labeled as claims, not live results.**

## Remote Performance Files Read

| File | Timestamp | Use / Caveat |
|---|---|---|
| `audit_dashboard/data/money_ready_verdict.json` | 2026-11-14 20:58:53 UTC | `classes.*.intrabar_truth`, official class verdicts; no class money-ready |
| `audit_dashboard/data/pf_registry.json` | 2026-11-14 21:00:20 UTC | `by_asset_class_policy_clean_net`; materially different counts from verdict cohort |
| `audit_dashboard/data/pick_summary_stats_48h.json` | 2026-11-14 21:06:14 UTC | Raw `at_raw_picks` short window; monitoring only |
| `audit_dashboard/data/pick_summary_stats_14d.json` | 2026-11-14 21:06:14 UTC | Raw `at_raw_picks` 14-day window; not canonical policy-clean sample |
| `alpha_engine/data/mutual_fund_metadata.csv` | 2026-10-22 | 38 funds; ER 0.015%-0.74%; categories; load/12b-1 data |
| `audit_dashboard/data/mf_traits_walkforward_results.json` | 2026-10-23 16:03:35 UTC | 32 walk-forward windows, 59-universe US MF, net of ER |
| `audit_dashboard/data/mf_walkforward_results.json` | 2026-10-23 | MF walkforward results container |
| `audit_dashboard/data/mutut_fund_rankings.json` | 2026-10-23 | Mutual fund T1/T2 rankings output |
| `audit_dashboard/data/fund_holdings_consensus.json` | 2026-10-23 | Fund holdings consensus output |
| `recent_closed_array.json` | 2026-11-02 15:14 UTC | 3,500 closed picks; 3,447 decisive WON/LOST |
| `picks_now.json` | 2026-11-12 18:04:17 UTC | 25 curated picks; 100% LONG-biased; RISK_OFF regime |
| `picks_now_live_pnl.json` | 2026-11-12 18:57:19 UTC | 4,310 open picks; avg PnL -1.42% |

## Peer Packages Reviewed

| Package | Location | Key Finding |
|---|---|---|
| childlike-airport (kilo) | `final_2026_11_14/childlike-airport/` | VWAP MR claimed validated but refuted; 129/129 stale picks; PnL contradictions |
| finpredict-v2 | `final_2026_11_14/finpredict-v2/` | CI Gates G1-G13; cohort mismatch blocker for ETF |
| finpredict-v3 | `final_2026_11_14/finpredict-v3/` | Horizon harness 0/6 at n≥60, 0/26 at n≥30; leakage fix commit `d8c8dd25581` |
| quant-audit (my final_v2) | `final_v2/quant-audit-2026-11-14/` | 0/166 live-ledger cells pass all gates |
| fix-p0-safe-fixes (peer final_v2) | `final_v2/fix-p0-safe-fixes-2026-11-14-main/` | Peer adjudication refuting VWAP; per-class roadmap |

## Validation Performed

- Read-only local file review
- Git status/log inspection
- Targeted GitHub API reads (workflows, runs, PRs)
- Targeted JSON parsing (money_ready_verdict, pf_registry, pick_summary_stats, screener results)
- Cross-referenced final_v2 peer adjudication (VWAP refuted, horizon harness bugs identified)
- No backtests, database mutations, strategy scanners, dashboard generators, or production workflows were run
- No code changes, commits, pushes, or tests were made for evidence gathering (fixes already committed on `wiring` and `fix/p0-safe-fixes-2026-11-14-main` branches)

## Validation Limits

- Cross-ledger reconciliation between `money_ready_verdict` and `pf_registry` NOT performed (materially different counts)
- Row-level provenance of all 3,500 closed picks NOT verified
- SubQ comparison NOT yet executed (matrix drafted in `06_subq_comparison/`)
- Mutual fund NAV history NOT yet built (≥5y required)
- Live price cross-reference NOT performed beyond spot checks (SPY, BITO)
