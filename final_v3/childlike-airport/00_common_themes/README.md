# 00 — Common Themes, Bugs & Deeper Investigation

**Date:** 2026-11-14 | **Reviewer:** Kilo (childlike-airport)  
**Reviewed:** today’s `origin/main` commits/log, locally modified files, all repo `final_v2/*` packages, `2026-11-14/finpredict*` trees, `research/profitability/SCORECARD.md`, pre-existing `final_v3/quant-audit-2026-11-14`, and untracked financial-prediction artifacts (`alpha_engine/*mutual_fund*`, `fund_holdings_deriver.py`, `audit_dashboard/data/mf*`, rankings).

## A. Cross-Cutting Themes (high agreement across peers)

| Theme | What peers/reviews converge on | Evidence / sources |
|---|---|---|
| **Not money-ready** | No asset class/strategy proven profitable end-to-end in live system; 0/166 live-ledger cells pass money-ready gates. | `final_v2/quant-audit-2026-11-14/05_final/VERDICT.md`, `final_v2/fix-p0-safe-fixes-2026-11-14-main/00_summary/VERDICT.md` |
| **Data/PnL integrity is broken** | Stale snapshots, fake 0% P/L, understated losses, sign/calc mismatches, frozen/unresolved picks dominate outcomes. | childlike-airport ML audit (129 picks stale ~172d, 8 sign contradictions, 15 calc mismatches), deepAI (81% fake 0% P/L, losses ~10x understated) |
| **Pipeline/audit gaps** | Audit trail near-empty; resolution provenance missing; regime coverage ~0.25%; dashboard/workflow instability. | `data/audit_trail.db` empty-core findings, stale outcomes reports, 7 failing workflows/cancellations cited |
| **Overfitting / benchmark issues** | Many “edges” fail OOS, are benchmark-explainable, or fail strict stats (PBO/DSR/effective-N/multiple testing). | `research/profitability/SCORECARD.md` (23 candidates, 0 proved), VWAP falsification/validation, IT-005 bear/OOS caveats |
| **Single-source / concentration** | Live cells effectively single-source; multi-source confirmation absent. | peer adjudications, quant-audit verdict context |
| **Remediation before claims** | Fix correctness + observability, then reproduce/validate, then paper, then gated live. | consensus across `final_v2/*` docs |

## B. Concrete Bugs / Defects

| ID | Bug/Defect | Impact | Status / note |
|---|---|---|---|
| B1 | `sync_all_picks_to_mysql.py`: null/zero `entry_price`, `pnl *= 100` heuristic | Systematic PnL corruption/wrong units | **Open** |
| B2 | `price_realism_check.py`: hardcoded `expected_2026_prices` | False validation / drift | **Open** |
| B3 | PnL sign contradictions & calc mismatches (8 sign, 15 calc in DB sample) | Untrustworthy returns | **Open** |
| B4 | Stale/frozen picks (129/129 ~172d) & 53+ frozen at `pnl_pct=0%` | Masks losses, blocks learning | **Open** |
| B5 | EXPIRED→WON relabeling / ~78.6% EXPIRED zombies unresolved | Survivorship & PnL bias | **Open** |
| B6 | Futures/commodity ~98.4% zero-P/L / unresolved pricing | Commodity performance invalid | **Open** |
| B7 | `audit_trail.db` core tables empty; `recent_closed.json` 0 bytes; outcomes stale | No lineage/feedback loop | **Open** |
| B8 | Dead price refresh (`fetch_prices.php` 404 since 2026-04-29, per peers) | Stale marks | **Open** (verify) |
| B9 | After-cost net dead (`after_cost_net_per_trade=None`) for closed rows | Net performance unknown | **Fixed today (local mod)** `audit_trail/dashboard_generator.py` |
| B10 | Gap-fill pricing: SL understated on gap-downs, TP overstated on gap-ups | Optimistic marks | **Fixed today (local mod)** `audit_trail/universal_pick_resolver.py` |
| B11 | No per-class cost gate (costs > avg PnL in some classes cited) | Negative-expectancy emissions | **Fixed today (local mod)** `tools/hc_gates_python.py` |
| B12 | Validation harness: `MIN_WINDOWS` not enforced, gap-split windows, no multiple-testing correction, PnL not netted, missing `resolution_method` | False positives | **Open** |
| B13 | Source fragmentation: unsynced `active_picks_bond.json`/`active_picks_etf.json`, stale JSONs | Inconsistent truth | **Open** |
| B14 | Regime layer ~0.25% coverage | Regime-gated strategies unauditable | **Open** |
| B15 | Mutual fund capability not wired to live picks | High-accessibility class unused | **Open (build)** |

## C. Deeper Investigation Needed

| ID | Investigation | Why | Suggested method |
|---|---|---|---|
| D1 | VWAP-MR replication on >730d exchange data | PBO ~0.48-0.49 & n capped by yfinance; core profitable, pool diluted | Binance/OKX 4h 2y+, rerun core-only, cost stress 20/30/50bps |
| D2 | VWAP intrabar/stop realism & PBO correctness | Conflicting falsification claims | Conservative fills, proper CSCV/PBO, independent impl |
| D3 | TSMOM benchmark & bear-regime alpha | Buy-and-hold/selection & bear-OOS concerns | Risk-matched benchmark, bear/subperiods, costs, block bootstrap CI |
| D4 | Variant C reproduction | Pilot PF 1.26 n=237 p<0.0013; cloning/cost critiques | Raw emissions, net costs, OOS walk-forward, no leakage |
| D5 | mega_mutation_macd_rsi / ema_momentum | Very high PF; selection/synthetic/leakage risk | Independent OOS, path-confirmed fills, full costs |
| D6 | Cross-ledger reconciliation | Verdict/registry/recent_closed/raw counts diverge | Row-level join & publish diff |
| D7 | Resolution provenance & label validity | Missing `resolution_method`; EXPIRED relabel bias | Enforce schema, backfill, audit transitions |
| D8 | Benchmark-relative & effective-N stats | Carry/effective-N can erase apparent edge | Risk-matched benchmark, effective sample size, carry split |
| D9 | Mutual fund live viability | Infra exists but no live validated allocation class | Define signal, wire class, NAV walk-forward + paper |
| D10 | Workflow/dashboard root causes | 7 failures/cancellations; freshness impact | Triage logs/permissions/timeouts, add SLAs/alerts |

## D. Synthesis
1. **Integrity first:** fix PnL math/units, marks, lifecycle, provenance, sync before trusting metrics.
2. **Validation discipline:** net-of-cost OOS, benchmark-relative, PBO/DSR/effective-N, multiple-testing control, leakage checks.
3. **Narrow deployment:** few diversified, low-turnover, low-fee strategies over signal zoo.
4. **Observability:** restore audit trail, regime coverage, workflow health, reconciliation.
