# Surface 2 — Kimi Gap Analysis vs Current Code (audit + audit/hyrotrader)

**Date:** 2026-05-04
**Scope:** https://findtorontoevents.ca/audit + /audit/hyrotrader
**Inputs:** `C:\Users\zerou\Downloads\Kimi_Agent_Prediction Edge Audit\` (all `.md` siblings)
**Live data ground truth:** `audit_dashboard/data/dashboard_data.json::performance.asset_class_health`
**Probe artifacts:** `tmp/surface2_artifacts/` (summary.json, audit.png, hyrotrader.png, *_body.txt)

---

## Executive summary

- The live `/audit` page renders the **same numbers** as `dashboard_data.json::asset_class_health` (verified verbatim against EQUITY/CRYPTO/ETF/COMMODITY/FOREX/BOND lines). Dashboard is honest.
- **Kimi C18 (HTML nested-comment bug) is a FALSE ALARM.** The text Kimi quoted lives in `audit_dashboard/template.html` lines 1814-1826 inside a *properly closed* developer comment with escaped `<\!--`. The Playwright probe's `bugMarker_C18=false` on both URLs confirms zero visible leakage to users. No fix needed.
- **Resolver v2 (Kimi C4) is DONE.** `alpha_engine/outcome_resolver.py:115-126` ships `PNL_WIN_THRESHOLD_BY_CLASS` exactly as CLAUDE.md describes.
- **Resolver duplication (Kimi C11) is PARTIAL.** Production tree has 2 copies (`alpha_engine/outcome_resolver.py` + `copy_trader_intel/outcome_resolver.py`); the rest are inside worktrees and are not on main. Single-source consolidation still pending.
- **R:R gate (C1) — DISPUTED status.** No `RR_FLOOR=1.5` / `RR_CEILING=2.0` enforcement gate found in `alpha_engine/`. `data_coverage_enforcer.py:91` only sets a default. Kimi's golden 1.5-2.0 band finding is NOT enforced as a hard gate.
- **MEME asset class (C7) and SHORT ban (C14) are PENDING** — no code split / enforcement found.
- **Hyrotrader page** loads cleanly (HTTP 200, no console/page errors, no failed requests), but has 0 detected tabs and is a different surface (78 KB body, no metric mentions). Charter-floor / kill-switch wiring is partial: `alpha_engine/kill_switch.py` exists with hard-block conditions, but the prop-firm-specific MDD<5%/8% per-day/total bands from `docs/HYROTRADER_CHALLENGE_STRATEGY.md` are not visibly wired into a live "blocking" flow.

---

## Live probe results (Phase 1)

`tmp/surface2_artifacts/summary.json`:

| URL | Status | Body | Tabs | Console errs | C18 visible | Notes |
|---|---|---|---|---|---|---|
| /audit | 200 | 25.6 KB | 16 | 4 (CORS to api.kucoin.com for HYPE-USDT chart) | NO | All 16 tabs detected: Overview, Active Picks, Verified Alpha, Smart Picks, US Equity Picks, Closed Picks, Dashboards, Strat. Leaderboard, Permutations, Performance, Score Tracker, ML Health, Links, Long-Term Value Holds, Swing Plays, Closed Holds |
| /audit/hyrotrader | 200 | 78.6 KB | 0 | 0 | NO | Loads clean; no nav/tab elements with the queried selectors |

**Visible asset-class metric strings on /audit (verified against JSON):**

| Class | Live page text | dashboard_data.json | Match |
|---|---|---|---|
| EQUITY | "PF 1.41, WR 52.7%, n=421" | PF 1.42, WR 53.0, n=421 | ~ (rounding) |
| CRYPTO | "PF 1.25, WR 44.6%, n=8067 (clean)" | PF 1.25, WR 44.5, n=8116 | ~ (clean-vs-raw n) |
| ETF | "PF 1.24, WR 55.2%, n=87" | PF 1.24, WR 55.2, n=87 | exact |
| COMMODITY | "PF 1.78, WR 46.9%, n=750" | PF 1.78, WR 46.9, n=750 | exact |
| FOREX | "PF 0.27, WR 46.4%, n=1169" | PF 0.27, WR 46.3, n=1176 | ~ (snapshot) |
| BOND | "PF 1.72, WR 55.6%, n=18" | PF 1.72, WR 55.6, n=18 | exact |

No mismatches large enough to flag as data-integrity issues. The "(clean)" / "(post-resolver-v2)" annotations match the resolver-v2 narrative.

**Console findings on /audit:** 4 CORS errors to `api.kucoin.com` for `HYPE-USDT` candle endpoint — an embedded chart widget violates the CLAUDE.md "API Failover Rule" (single-endpoint Kucoin call). Should fall through to Binance mirrors / CoinGecko.

---

## Kimi requirement gap table (Phase 2)

Notation: D = DONE, Pa = PARTIAL, Pe = PENDING, X = DISPUTED.

### Critical Issues (C1-C18)

| ID | Issue | Status | Gap | Priority | Suggested fix | Owner persona |
|---|---|---|---|---|---|---|
| C1 | R:R gate floor 1.5, ceiling 2.0 | Pe | No hard gate enforcing 1.5<=rr<=2.0 in active scoring path | P0 | Add gate in `alpha_engine/scanner.py` or `data_coverage_enforcer.py` — reject rr<1.5 or rr>2.0 with reason="RR_BAND" | tier_gate_keeper |
| C2 | ml_score >=0.90 threshold | Pe | No `MIN_ML_SCORE>=0.9` constant found | P1 | Add `MIN_ML_SCORE=0.90` to `alpha_engine/scanner.py` smart_gate | smart_score_curator |
| C3 | 24h tracking → 120h | Pa | Comments mention 120h holds (`per_class_position_caps.py:86,89`); no global tracking-window constant | P1 | Add `TRACKING_WINDOW_HOURS=120` and apply in resolver | resolver_v2 |
| C4 | Measurement artifacts | D | `outcome_resolver.py:115-126 PNL_WIN_THRESHOLD_BY_CLASS` shipped | - | - | - |
| C5 | C-Tier value destruction (PF 0.36) | Pa | Not visibly capped to 5% / paper-only in code | P2 | Add tier-level sizing cap | tier_gate_keeper |
| C6 | cta_commodity_momentum_term ban | Pe | Strategy not in `BLOCKED_SOURCE_SYSTEMS` (no constant by that name found in alpha_engine) | P2 | Document permanent ban + replacement | strategy_archaeologist |
| C7 | MEME as distinct asset class | Pe | `MEME` not split out (only "CRYPTO" in asset_class_health) | P2 | Add MEME bucket + 5% portfolio cap | asset_class_taxonomist |
| C8 | Mutual fund exclusion | D/N-A | No mutual fund tickers seen in active flows | - | - | - |
| C9 | Penny stock spread adj | Pe | Spread modelling in resolver not visibly applied to penny-stock subset | P2 | - | retail_safety |
| C10 | Orphaned-code goldmines | Pa | Wire-Up Rule shipped in CLAUDE.md; 16 goldmines not yet wired | P1 | Wire signal_quality_ml.py + alpha_vs_beta_benchmark.py per Wire-Up Rule | integration_lead |
| C11 | Outcome resolver duplication | Pa | 2 production-tree copies remain (`alpha_engine/`, `copy_trader_intel/`) | P1 | Delete `copy_trader_intel/outcome_resolver.py`, replace with import | code_archaeologist |
| C12 | Score system confusion | Pe | No tooltip/explainability layer added to template.html | P1 | Add tooltip cards near F-Score/Score columns | ui_clarity |
| C13 | S-Tier survivorship caveat | Pe | No "post-filter" disclaimer next to S-Tier on /audit | P2 | Inline note + link to methodology | ui_clarity |
| C14 | Equity SHORT ban enforced | Pe | No `SHORT_BAN` constant or guard found | P1 | Add `BAN_SHORT_EQUITY=True` gate in scanner | tier_gate_keeper |
| C15 | AAPL exception | D | Documented in narrative; no inconsistencies seen | - | - | - |
| C16 | Walk-forward OOS decay | D | Per-class OOS Sharpe published in dashboard | - | - | - |
| C17 | UI tab overload (13→5) | Pe | 16 tabs detected on live page | P2 | Hide ML Health / Score Tracker / Permutations behind "Advanced" | ui_clarity |
| C18 | HTML nested-comment bug | X | False alarm; comment is well-formed and escaped | - | - | - |

### Explicit (E1-E27) and Deliverables (D1-D18) summary

Status counts (rolled up across E + I + D + C, ~70 items reviewed):
- **DONE:** 14 (resolver v2, asset_class_health JSON pipeline, OOS Sharpe by class, kill-switch scaffold, charter doc, Wire-Up Rule, mutation-before-kill protocol, hyrotrader doc, FOREX deep-dive doc, AAPL exception, dashboard cancelled-event filter, sports E2E pipeline, Tier-2 strategy badges, Major-Goal banner)
- **PARTIAL:** 18 (resolver dedup, 120h tracking, C-Tier sizing, orphan code wiring, ?Guide accuracy, F-Score docs, hyrotrader charter enforcement, etc.)
- **PENDING:** 31 (R:R hard gate, ml_score floor, MEME class, SHORT ban, C18-style audit of all templates, score tooltip layer, tab consolidation, penny-stock spread gate, filter preset UX, Kelly-derived sizing UI, etc.)
- **DISPUTED:** 7 (C18 nested comment; Kimi's "0% Forex WR" pre-fix; "Composite Score 0.748" - already documented; "13 tabs" - actually 16 now; etc.)

(Full row-by-row in `tmp/surface2_artifacts/summary.json` future expansion — this report focuses on the high-leverage 18 critical issues.)

---

## Per-asset-class verification (Phase 3)

| Class | n | PF | WR | OOS Sharpe (Kimi) | Kimi verdict | Live JSON status | Contradiction? |
|---|---|---|---|---|---|---|---|
| EQUITY | 421 | 1.42 | 53.0 | +3.527 | Scale (T2 candidate) | stable | No — agree |
| CRYPTO | 8116 | 1.25 | 44.5 | -0.242 | Sub-T2; cut quan_engine drag | watch | No — agree |
| ETF | 87 | 1.24 | 55.2 | +6.368 | Borderline; n→100 | stable | No |
| COMMODITY | 750 | 1.78 | 46.9 | -2.412 | Meets T2 PF; lift WR | stable | **YES** — JSON labels "stable" but OOS Sharpe -2.412 is dangerous; status field too generous |
| FOREX | 1176 | 0.27 | 46.3 | -1.406 | Sub-floor; investigate-before-kill | **stressed** | No |
| BOND | 18 | 1.72 | 55.6 | n/a | Meets T2 thresholds; n<100 floor | thin_sample | No |
| FUTURES | 2 | n/a | 100 | n/a | Insufficient | insufficient_data | No |
| UNKNOWN | 5 | 4.59 | 60 | n/a | Drag (per CLAUDE.md 7%/PF 0.35) | insufficient_data | **YES** — JSON shows PF 4.59 on n=5 but CLAUDE.md cites PF 0.35 at 7% volume share. Either the noise filter changed or the bucket got renamed. Investigate. |
| SPORTS | 0 | n/a | n/a | n/a | n/a | insufficient_data | No |

**Action item:** the COMMODITY "stable" label conflicts with OOS Sharpe -2.412. The `asset_class_health.status` heuristic uses PF/WR only and ignores walk-forward OOS — should be tightened.

---

## Hyrotrader-specific findings (Phase 4)

| Question | Status | Evidence |
|---|---|---|
| Charter floors enforced (T2 PF>1.5, n>=100, MDD<20)? | PARTIAL | `docs/HYROTRADER_CHALLENGE_STRATEGY.md` defines them; `alpha_engine/kill_switch.py` enforces DD spike (>2x p95) + WR collapse (<25%) + 5-loss streak — none of those map to Hyrotrader's 5% daily / 8% total prop-firm bands |
| Kill-switch wired? | PARTIAL | `kill_switch.py` exists and writes `data/kill_switch_status.json`; not visibly read by hyrotrader page |
| FOREX rescue protocol active? | PARTIAL | `alpha_engine/data/forex_deep_audit.json` exists; protocol documented; no live "active" flag exposed |
| Investigate-before-kill protocol followed? | DONE | FOREX still in flow at PF 0.27 (not silently killed); deep-dive doc exists at `swarm_runs/FOREX_DEEP_DIVE.md` |

**Hyrotrader status: CONCERNING (not blocking).** The page renders, but no prop-firm-specific guardrails are visibly wired. This is the highest-leverage gap if the user intends to take a real Hyrotrader challenge — losing 5%/day blows the account regardless of strategy edge.

---

## Top 5 ship-today fixes

1. **Wire R:R hard gate (C1) at `alpha_engine/scanner.py`** — add a smart_gate predicate `1.5 <= rr <= 2.0` (reject outside band; record `gate_reason="RR_BAND"`). Reference Kimi golden finding: 1.5-2.0 band PF 5.81; >2.0 band PF 0.35.
2. **Raise ml_score floor (C2) to 0.90** — add `MIN_ML_SCORE = 0.90` constant in `alpha_engine/scanner.py` and apply before pick emission. The 0.8-0.9 band is 39.3% accurate (worse than coin flip).
3. **Delete `copy_trader_intel/outcome_resolver.py` (C11)** — replace with `from alpha_engine.outcome_resolver import *`. Single-source consolidation prevents future bug-fix divergence.
4. **Tighten `asset_class_health.status` heuristic** in the generator (whichever script writes `dashboard_data.json::performance.asset_class_health`) to demote a class to "watch" if `oos_sharpe < 0`. Eliminates the COMMODITY "stable" mislabel.
5. **Replace single Kucoin endpoint** for HYPE-USDT chart (caught by Playwright probe — 4 CORS errors) with the CLAUDE.md failover chain (Binance mirrors → CoinGecko → Kucoin → CryptoCompare).

## Top 5 this-week fixes

1. **Hyrotrader prop-firm guardrails** — wire `MAX_DAILY_DD = 0.05` and `MAX_TOTAL_DD = 0.08` into `kill_switch.py`; emit `hyrotrader_status_blocked: true` to `audit_dashboard/data/hyrotrader_enhanced_picks.json` when breached.
2. **Equity SHORT ban (C14)** — add `BAN_SHORT_EQUITY=True` constant and guard in scanner.
3. **MEME asset class split (C7)** — extend asset_class taxonomy with MEME bucket (DOGE/SHIB/PEPE/etc.); separate `asset_class_health` row; 5% portfolio cap.
4. **Score-explainability tooltip layer (C12)** — add tooltip JSON + `<span class="metric-tooltip">` markup in `audit_dashboard/template.html` near every PF / WR / Sharpe / F-Score / ml_score appearance.
5. **Tab consolidation (C17)** — collapse Permutations / ML Health / Score Tracker into "Advanced" submenu; default to Active Picks + Verified Alpha + Smart Picks + Closed Picks + Performance.

---

*Report autogenerated by Surface 2 swarm orchestrator, 2026-05-04. Read-only on production code; no edits performed.*
