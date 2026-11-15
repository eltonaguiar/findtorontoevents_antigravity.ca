# 08 — Evidence Index (final_v5, childlike-airport)

## Primary sources reviewed
| Source | Path / ref | Key facts used |
|---|---|---|
| v4 synthesis (cross-peer) | `final_v4/04_synthesis/SYNTHESIS.md` | Not profitable/testable arc; 2 candidates; 14 bugs B1–B14; 8 open questions; 90-day plan |
| v4 final summary | `final_v4/05_final_summary/00_FINAL_SUMMARY.md` | Convergence, peer-reported shipped fixes/tests, VWAP rejected, “nothing money-ready” |
| v4 finpredict | `final_v4/finpredict_2026-11-14T215013Z/00-summary/SUMMARY.md`, `02-plan/PLAN.md`, `03-subq/SUBQ_COMPARISON.md`, `04-peer-review/REVIEW.md` | Integrity-first plan, EQUITY+CRYPTO ranking, B1–B14 context, scoring/certification framing |
| v4 flaxen-hair | `final_v4/flaxen-hair_2026-11-14T2200/03_plan/IMPROVEMENT_PLAN.md`, `04_subq_comparison/SUBQ_COMPARISON.md`, `05_focus_decision/FOCUS_DECISION.md`, `06_peer_review/PEER_REVIEW.md`, `08_execution_roadmap/EXECUTION_ROADMAP.md` | Go/No-Go gates, 90-day roadmap, candidate focus |
| v4 childlike-airport | `final_v4/childlike-airport-20261114-215046Z/SUMMARY.md`, `05_final_improvement_plan/MASTER_TODO_PLAN.md` | Adjudicated bottom line, master TODOs, MF low-fee subset, promotion gates |
| Prior deliverables (pushed) | `final_v2/childlike-airport/*`, `final_v3/childlike-airport/*` | Per-asset roadmap, validation framework, common themes |
| Repo memory/index | injected `kilo-memory-v1` | Audit facts: regime coverage ~0.25%, stale/zombie rows, freshness, money-ready verdicts, PnL/calc issues |
| Local experiment | `/tmp/kilo/regime_filtered_vwap_v12_results.json` | v12 pooled n=129 WR 44.2% PF 1.210 Sharpe 3.758 Ret 12.699% MDD 9.994% PBO 0.489 DSR/P(SR>0)=1.0; core profitable, DOGE/AVAX/LINK losers |
| ETF data probes | `alpha_engine/data/active_picks_etf.json` (14), `alpha_engine/data/etf_decay_picks.json` (3), `alpha_engine/data/leveraged_etf_decay_picks.json` (4), `non_crypto_agent/data/etf_picks.json` (2) | ETF artifacts exist; performance/money-readiness not established |
| Remote (24h) | `git fetch origin` + `origin/main` log 2026-11-14 | `b0ed9a86f0d`, `2799cc12ee5`, `34f2ee49094`, `2a441906294` (stop-fill/cost-gate merge), refresh commits |

## Key quantitative anchors (caveated)
| Metric | Value | Caveat |
|---|---|---|
| CRYPTO money-ready | n=3705, WR 35.87%, PF 0.9196, expectancy −0.058789 | Not ready; cohort/window-specific |
| ETF verdict | n=44, WR 2.27%, PF 0.0219 | Insufficient/inflation-flag context |
| VWAP v11 | n=65, WR 53.8%, PF 1.435, Sharpe 7.10, MDD 3.5%, PBO 0.4800 | Small n; falsification history |
| VWAP v12 (local) | n=129, WR 44.2%, PF 1.210, Sharpe 3.758, MDD 9.994%, PBO 0.489 | **PBO fails strict <0.3**; 730d cap |
| IT-005 TSMOM | CAGR 23.0%, Sharpe 2.13, PF 1.40, MDD −17.4%, bootstrap CI [1.25,3.25], 7.4y | Candidate; needs net/benchmark/bear/forward proof |
| live_picks.db | 129 rows, stale ~172d, sign/calc issues | Integrity risk |

## Conflicts / uncertainty
- VWAP rejected/refuted vs basic-pass-needs-data → **unproven**.
- MF infra historically referenced vs inspected-state gaps → **build/validate required**.
- Peer-reported tests/fixes/replay metrics not independently re-run this pass.
- No verifiable live SubQ run; comparison treated as coverage-matrix synthesis.

## Reproduction
- Re-run candidates on canonical, net, benchmark-relative data with fixed seeds/hashes and registered `n_trials` (DSR/PBO).
- QA 0%/blank dispositions must cite per-pick market-data sources/timestamps (`05_qa_plan/QA_PLAN.md`).
