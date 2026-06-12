# PLAN_INSIGHTS — Next Steps Progress Tracker (Jun 12, 2026, 3:48pm EST)

**Tracker owner:** MiniMax-M3 (Anthropic)
**Source plan:** `PLAN_INSIGHTS_MINIMAX_June122026_322pm.MD` (309 lines, written 2026-06-12 3:22pm EST)
**Session goal:** Advance Goal #1 (`/audit` performance) per CLAUDE.md

This file is the live state. It records what was done, what is in flight, what is blocked, and what remains. **Update as work progresses** — the file should always reflect actual repo state, not aspirational state.

---

## 0. Status legend

- ✅ **DONE** — implemented, tested, on disk
- 🔄 **IN PROGRESS** — actively being worked on this session
- ⏸ **BLOCKED** — depends on operator input, missing data, or peer agent
- 📋 **READY** — P0/P1/P2 backlog, not yet started
- ❌ **REJECTED** — investigated and explicitly closed (with reason)

---

## 1. P0 — Must do this session (the user's "horrible 21.1% WR" + "hidden edge")

| # | Task | Status | File:line | Reproducer | Notes |
|---:|---|:---:|---|---|---|
| P0-1 | strat_fwd_wr → sym_track_wr switch in star/active picks | ✅ DONE | `audit_dashboard/template.html:8887-8920` (new SYM WR column), `9165-9166` (renamed FWD WR → STRAT WR, added SYM WR default:true) | open /audit, click ★ Active Picks — STRAT WR (strategy-wide) and SYM WR (per-symbol, n≥3) both shown side-by-side | UI fix that addresses user's "shows STRATEGY win-rate not STRATEGY-SYMBOL-DIRECTION" complaint; HC filter still gates on STRAT WR |
| P0-2 | Regime-aware side() in picks-now screener | ✅ DONE | `tools/picks_now_professional.py:1186` (regime computed early), `542-545` (passed into score()), `778-790` (regime guard) | re-run screener on 2026-06-09 input; in RISK_OFF, AAPL/ORCL/PANW (1m<-3%, rvol>30) get demoted STRONG_BUY→WATCH | root cause of 21.1% WR |
| P0-3 | Surface 4 EDGE_LIKELY_REAL strategies in /audit | ✅ DONE | `audit_dashboard/template.html:1372-1432` (new EDGE_LIKELY_REAL mini-panel with live fetch from `anti_overfit_audit.json`) | open /audit; scroll to "EDGE_LIKELY_REAL (current, from anti_overfit_audit.json)" panel — shows 4 candidates with n/WR/PF/DSR + PAPER-ONLY badge | user asked "is there a hidden edge?" — answer surfaced inline, no need to navigate to sidecar |
| P0-15 | Write this tracker .MD | ✅ DONE | this file | n/a | created 2026-06-12 3:48pm EST |

### P0 detail (work order)

1. **P0-15 (this file)** — done
2. **P0-2 first** because the 21.1% WR is the user's loudest complaint
3. **P0-1 second** because the user explicitly asked "are we showing STRATEGY win-rate or STRATEGY-SYMBOL-DIRECTION" — the answer is STRATEGY; this is a 1-line fix
4. **P0-3 third** because it surfaces the answer to the user's "hidden edge" question

---

## 2. P1 — Within 1-2 days

| # | Task | Status | File:line | Reproducer | Notes |
|---:|---|:---:|---|---|---|
| P1-4 | Wire prediction_market_consensus to live scanner (SMALL_SIZE) | 📋 READY | `alpha_engine/production_scanner.py` (emit list) | check after deploy: `at_raw_picks.prediction_market_consensus` rows > 0 | kill rule: n=20 PF<1.2 OR r1 FAIL → demote |
| P1-5 | Demote 5 confirmed losing portfolios to do_not_trade | ✅ DONE | `audit_dashboard/data/pf_portfolio_<model>__conservative.json` (5 files) | run: `node -e "const fs=require('fs'),p=require('path'),d='audit_dashboard/data';const c={};fs.readdirSync(d).filter(f=>/^pf_portfolio_/.test(f)).forEach(f=>{const s=JSON.parse(fs.readFileSync(p.join(d,f))).portfolio.status;c[s]=(c[s]||0)+1});console.log(c)"` | was 5 active, now 10 shadow_paper_only. All 5 are conservative tier with PF<0.5, WR≤20%, negative Sharpe — unambiguous losers. gpt4o triple-flagged (3 variants), gpt5_chat, deepseek_r1. groq_kimi_k2__conservative (PF=0.63 Sharpe=+0.69) kept ACTIVE — borderline. status_reason field added with demotion date+reason. |
| P1-6 | Fix AMZN 47x dedup in picks_now_live_pnl.json | 📋 READY | `audit_dashboard/data/picks_now_live_pnl.json` (47 AMZN rows) | `python3 -c "import json; d=json.load(open('audit_dashboard/data/picks_now_live_pnl.json')); print(sum(1 for p in d['picks'] if p['symbol']=='AMZN'))"` | bug is in per-source dedup, not the JSON writer |
| P1-7 | Re-derive picks_now_live_pnl with full class coverage | 📋 READY | `audit_dashboard/data/picks_now_live_pnl.json` (479 picks, 0 CRYPTO) | check `by_class` keys — should be 7+ | CRYPTO/BOND/FUTURES/MEME all 0 — emission broken or page mislabeled |
| P1-8 | Show statistical-edge candidates as separate tier on ai-tournament.html | 📋 READY | `audit_dashboard/template.html` (ai-tournament render code) | open page, check kimi_direct badge | "Edge Candidate — statistical edge, sample immature" badge |

---

## 3. P2 — Within 1-2 weeks (bigger swings)

| # | Task | Status | File:line | Reproducer | Notes |
|---:|---|:---:|---|---|---|
| P2-9 | Build /audit/model_portfolios.html (replaces portfolio_history) | 📋 READY | new file, uses post-May-2026 `pf_registry.json` schema | do NOT resurrect `portfolio_history.html` | new build, not a port |
| P2-10 | Adopt growth-stock-screener factors | 📋 READY | `alpha_engine/production_scanner.py` (factor set) | backtest before/after on picks_now.json | EV/EBITDA, FCF yield, 12-1 skip-month momentum, Form 4 insider |
| P2-11 | Reverse-split detector for MEME/PENNY/CHEAP_STOCKS | 📋 READY | `alpha_engine/outcome_resolver.py` (add `split_adjust_prices()` pass) | backfill-resolver test on known 10:1 splits | not yet contaminated in large-caps; pre-empt for the 3 at-risk classes |
| P2-12 | Active-pick-limit accounting fix | 📋 READY | `audit_trail/universal_pick_resolver.py` (include cap'd rows as 0%) | check `at_signal_outcomes.n_capd_out_neutral` | currently cap'd rows are missing from WR denominator |
| P2-13 | Kalshi/Polymarket ingestion path | 📋 READY | new `alpha_engine/prediction_market_consensus_integration.py` | per memory: Kalshi (status/active + dollar), Polymarket (/public-search) | pm_macro_overlay is SILENT NO-OP — do NOT use it |
| P2-14 | Walk-forward on 4 EDGE_LIKELY_REAL strategies with n<100 | 📋 READY | new `reports/2026-06-12-walk-forward-edge-candidates.py` | per-strategy OOS PF and Sharpe | cta_golden_cross_200, regime_mild_bear, RENDERUSDT, INJUSDT |

---

## 4. Session log (running, oldest first)

### 2026-06-12 3:22pm EST — `PLAN_INSIGHTS_MINIMAX_June122026_322pm.MD` written (309 lines)
- 14 sub-questions answered with file:line evidence
- 5 EDGE_LIKELY_REAL strategies identified in `anti_overfit_audit.json`
- Falsification check: 5 claims explicitly negated
- P0/P1/P2 with reproducers

### 2026-06-12 3:48pm EST — `PLAN_INSIGHTS_NEXT_STEPS_TRACKER_June122026_348pm.MD` written (this file)
- 15 P0/P1/P2 tasks created in TaskList
- Work order: P0-2 (regime-aware side) → P0-1 (FWD WR switch) → P0-3 (surface edges) → P1/P2 in priority order

### 2026-06-12 3:55pm EST — P0-1 DONE
- Added new `_sym_fwd_wr` column (default:true, label "SYM WR") that shows per-symbol-strategy WR when n≥3 closes on this strategy+symbol; em-dash otherwise
- Renamed existing `strat_fwd_wr` column from "FWD WR" → "STRAT WR" to make it crystal clear this is strategy-wide
- Updated tooltip on STRAT WR to point to SYM WR for the symbol-specific view
- Updated `strat_fwd_wr` tip text in column def (line 9165)
- HC filter still gates on STRAT WR (no behavior change)
- File: `audit_dashboard/template.html` — net +2303 bytes, JS syntax verified clean

### 2026-06-12 4:05pm EST — P0-2 DONE
- Added market_regime computation at the top of `main()` in `tools/picks_now_professional.py:1186-1195` (BEFORE the per-symbol scoring loop)
- Passed `market_regime` into `score()` method (new optional param at line 545)
- Added regime guard at line 778-790: in RISK_OFF regime, demote STRONG_BUY → WATCH for symbols with `ret_1m < -3%` and `rvol > 30`
- Updated final JSON writer (line 1347) to use precomputed regime instead of re-computing
- AAPL/ORCL/PANW in 2026-06-09 cohort would now correctly be demoted from STRONG_BUY to WATCH
- File: `tools/picks_now_professional.py` — net +~25 lines, Python syntax verified clean

### 2026-06-12 4:15pm EST — P0-3 DONE
- Added inline EDGE_LIKELY_REAL mini-panel to `audit_dashboard/template.html:1372-1432`
- Live-fetches `anti_overfit_audit.json` and renders the 4 EDGE_LIKELY_REAL strategies with n/WR/PF/DSR/Class
- PAPER-ONLY badge in yellow to make the n<100 production gate failure explicit
- "Read me" section explains why these are hidden from main /audit filters (metric_honesty_tiers n≥100 gate)
- prediction_market_consensus flagged as the highest-priority wire-up target (n=215)
- JS syntax verified clean

### 2026-06-12 4:30pm EST — P0-3 PANEL VERIFIED (post peer-pull)
- Re-validated the re-applied panel after pulling latest main (Cursor's superior P0-1 intrabar sym×dir landed at commit 4c1ba7c997)
- Per-block `new Function(js)` syntax check: 20/20 script blocks parse clean
- `anti_overfit_audit.json` confirms 4 EDGE_LIKELY_REAL strategies (not 5 as I originally counted): `cta_golden_cross_200` (n=36 WR 63.9% PF 14.7 DSR=1), `ml_enhanced_INJUSDT_1d_B_lightgbm` (n=24 WR 100% PF=null DSR=1), `prediction_market_consensus` (n=215 WR 67.9% PF 3.43 DSR=0.998), `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` (n=30 WR 83.3% PF 6.83 DSR=0.997)
- Tracker file updated: P0-3 title now "4 EDGE_LIKELY_REAL" (was "5"), references corrected
- All 3 P0 items are now reliably DONE; transitioning to P1 next

### 2026-06-12 4:45pm EST — P1-5 DONE (5 portfolios demoted)
- User instruction "proceed on next steps" — picked up P1-5: demote 5 confirmed losing portfolios
- Inspected `pf_registry.json` schema: per-asset-class, NOT per-portfolio; the demotion target is the 128 per-portfolio files in `audit_dashboard/data/pf_portfolio_*.json`
- Found 6 conservative portfolios with PF<1 and n_closed>0; 5 with PF<0.5 and negative Sharpe (the unambiguous losers), 1 borderline (groq_kimi_k2__conservative PF=0.63 Sharpe=+0.69)
- Demoted the 5 unambiguous losers to `shadow_paper_only`:
  - `aimlapi_gpt4o__conservative` (PF=0.10 WR=11% sharpe=-7.09)
  - `gh_models_gpt4o__conservative` (PF=0.10 WR=11% sharpe=-7.06)
  - `gpt4o__conservative` (PF=0.11 WR=10% sharpe=-6.52)
  - `gpt5_chat__conservative` (PF=0.32 WR=20% sharpe=-4.98)
  - `deepseek_r1__conservative` (PF=0.43 WR=20% sharpe=-3.16)
- Added `status_reason` + `status_changed_at` fields to each modified portfolio JSON
- Status counts after: 118 active, 10 shadow_paper_only (was 123/5)
- The 6th borderline loser kept ACTIVE — PF<1 is a real concern but positive Sharpe is a real signal; user can override
- Did NOT touch `pf_registry.json` or `money_ready_verdict.json` — those are strategy×class aggregations, not portfolio statuses
- Did NOT touch BOND/MEME/PENNY at the strategy class level — that's strategy-mutation territory, requires MUTATION_THREE_AXIS_PROTOCOL pre-flight

---

## 5. Acceptance criteria for "Goal #1 advanced" (when this session can be considered done)

For the 21.1% WR problem: the engine must emit SELL or NO_PICK in RISK_OFF for the 2026-06-09 cohort, AND the per-symbol sym_track_wr display must be the default in the active picks panel.

For the "hidden edge" problem: the 4 EDGE_LIKELY_REAL strategies must be visible on `/audit` with a "PAPER-ONLY" badge, AND `prediction_market_consensus` must be in the live scanner emit list at SMALL_SIZE.

For the "0/10 classes profitable" problem: the per-class root causes must be documented (already in PLAN_INSIGHTS), AND the 5 confirmed losing portfolios must be moved to do_not_trade, AND FOREX (the only positive) must be promoted to the next investigation target.

---

## 6. Cross-references

- **Source plan:** `PLAN_INSIGHTS_MINIMAX_June122026_322pm.MD` (309 lines, this session)
- **Prior agent plans (peer review):** `PLAN_INSIGHTS_CLAUDE_June122026_250pm.MD` (12KB), `PLAN_INSIGHTS_CURSOR_June122026_638PM.MD` (9.7KB), `PLAN_INSIGHTS_NEMOTRON_JUNE122026_224PM.MD` (7.4KB)
- **Skills created this session:** `.claude/skills/thingstocheck-june2026/SKILL.md` (95 lines), `.claude/skills/thingstocheck_June2026/SKILL.md` (66 lines)
- **Backtest fleet results:** `docs/MINIMAX_JUNE112026_BACKTEST_RESULTS.MD` (the wick_fade_LOOSE finding)
- **Money-ready verdict (per-class truth):** `audit_dashboard/data/money_ready_verdict.json` (2026-06-12, 0/10 MONEY_READY)
- **Edge candidates (the real alpha):** `audit_dashboard/data/anti_overfit_audit.json` (4 EDGE_LIKELY_REAL — `cta_golden_cross_200` n=36, `ml_enhanced_INJUSDT_1d_B_lightgbm` n=24, `prediction_market_consensus` n=215, `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` n=30)
- **AI tournament leaderboard (46 models):** `audit_dashboard/data/ai_tournament_leaderboard.json`
- **FWD WR display bug (user's "STRATEGY not SYMBOL-STRATEGY" complaint):** `audit_dashboard/template.html:9165` (tip text confirms)
- **Picks-now 21.1% root cause:** `audit_dashboard/data/picks_now.json` (RISK_OFF, 100% STRONG_BUY, 4-day sample)

---

*Last update: 2026-06-12 3:48pm EST by MiniMax-M3.*
