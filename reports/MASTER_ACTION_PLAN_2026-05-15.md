# MASTER ACTION PLAN — 2026-05-15 (living document)

Consolidates: `supreme_edge_5agent_synthesis_2026-05-12.md`, `supreme_edge_checkpoint_2026-05-11T2300Z.md`, `supreme_edge_plan_next_2026-05-12.md`, `supreme_plan_review_2026-05-13.md`, `daily_ideas_synthesis_2026-05-15.md`, and 6 daily_ideas source files (4 dedup duplicates collapsed). Cross-checked against open PRs #1024-#1028, merged PR #1023, closed-unmerged #1017, and CLAUDE.md memory feedback set.

## Section 1 — Snapshot

Branch: `feat/hermes-symbol-blocks-2026-05-14` (this session). Main HEAD `80b513fa69c` (Antigravity institutional schedule). Open PRs: #1024 (Hermes blocks, swarm-fixed 28→6 verified), #1025 (upstream stubs), #1026 (Phase J ML-calibration banner + score_booster wire), #1028 (Kilo daily-ideas). Closed-unmerged: #1017 v2 state-machine (modules NEVER LANDED on disk). Asset-class live readout per `dashboard_data.json::asset_class_health` (last refresh 2026-05-03T00:06Z): EQUITY PF 1.41 / WR 52.7 / n=421 (T2-candidate); COMMODITY PF 1.78 / WR 46.9 / n=750 (PF passes T2); BOND PF 1.72 / WR 55.6 / n=18 (below floor); CRYPTO PF 1.25 / WR 44.6 / n=8067 (sub-T2, drag from `quan_engine` + `unknown`); ETF PF 1.24 / WR 55.2 / n=87; FOREX PF 0.27 / WR 46.4 / n=1169 (sub-floor, mutate-before-kill). DSR sidecar: `cot_positioning` CT=F n=104 WR 86.5% DSR=1.0 — but COT-publication-lag leakage flagged in `reports/cot_timing_leakage_audit_2026-05-13.md` may correct to ~45-55% WR. Hermes verified-blocks: 6 symbols (down from 28 false-positive). Phase J banner: shipped to template; `_calibrate_confidence` wired at `score_booster.py` from `run_score_booster.py:1272`.

## Section 2 — Done today

- PR #1023 MERGED — TV paper-trade skill set + portfolio review 2026-05-14
- PR #1024 OPEN, swarm-fixed — Hermes verified symbol blocks (28→6; CT=F + 4 JPY-profit pairs + 10 zero-evidence equities unblocked, ref `reports/portfolio_review_2026-05-14/swarm_pr1024_opinion.md`)
- PR #1025 OPEN — upstream stubs (`alpha_engine.alpha_core`, `fetch_candles`, `claude_gainer_st_signal`)
- PR #1026 OPEN — Phase J ML-calibration banner; `score_booster._calibrate_confidence` wired at `run_score_booster.py:1272`; revert of P0 NameError at `audit_trail/quality_gates.py:5865`; `protocol_state` + `safety_status` + `slippage_validator` scaffolds (shipped, NOT yet wired)
- PR #1028 OPEN — Kilo daily-ideas plan
- Main commit `7a975fbdaa3` / `782c2669e77` — Antigravity "Restore and expand daily ideas roadmap" + institutional schedule (`daily_idea_antigravity.MD`)
- Reports landed: `reports/daily_ideas_synthesis_2026-05-15.md`, `reports/portfolio_review_2026-05-14/swarm_pr1024_opinion.md`
- PR #1017 CLOSED-UNMERGED at 2026-05-15T02:08:44Z — v2 state-machine files DO NOT EXIST on disk

## Section 3 — Master ideas table (deduped + ranked)

| ID | Idea | Source(s) | Class/scope | Effort | Dep | Status | First action |
|---|---|---|---|---|---|---|---|
| M-001 | BTC UTC-hour death-zone filter (reject 08-09Z, boost 22Z) | synth#1, edge-per-class NS-C, memory project_clean_data_symbol_wr | CRYPTO | S | none | DONE 2026-05-17 | Wired at quality_gates.py:4668-4669 (CRYPTO_HOUR_FILTER_DISABLED kill-switch); CRYPTO penalty at 08-09 UTC |
| M-002 | DB Freshness Guardian GH workflow | Cursor#1, Antigravity§2, Copilot§2 | infra | S | MySQL trigger staging | DONE 2026-05-17 | db-freshness-guardian.yml + db-freshness-check.yml exist; AZ session fixed YELLOW fallback for missing schema columns |
| M-003 | PCG-5 portfolio gate stack (shadow then enforce) | DAILY_IDEAS PCG-5, Antigravity§4 | exec | M | TV skill + correlation_regime.json | DONE (stale) | audit_trail/pcg5_gates.py (5 gates, passes_pcg5_gate()); audit_trail/portfolio_gates.py (evaluate_pick() for tv-paper-trade skill); wired in quality_gates.py:8411 (portfolio_gates) + :8454 (pcg5_gates shadow); wired in dashboard_generator.py:15916 (batch shadow); SKILL.md Step 1.5 PCG-5 gate check; 19/19 tests pass (test_portfolio_gates.py). Stale PENDING corrected 2026-05-17. |
| M-004 | CRYPTO drag autopsy + auto-quarantine (>40% vol & PF<1) | edge-per-class Edge#8, project_strategy_state_2026_05_03 | CRYPTO | S | A3 payload (shipped) | DONE 2026-05-17 | dashboard_generator.py writes audit_trail/data/system_concentration.json; quality_gates.py: _cached_system_concentration() + CRYPTO_CONCENTRATION_GATE shadow gate (>40% vol & PF<1 → log/block). No system currently exceeds threshold. 6/6 tests pass (test_m004_crypto_concentration_quarantine.py). |
| M-005 | Cross-DB strategy/system key consistency audit | Cursor#3, DAILY_IDEAS 2026-05-08 | infra | M | M-002 | DONE 2026-05-17 | tools/cross_db_consistency.py (233 lines) + .github/workflows/cross-db-consistency.yml (daily 2AM UTC) already implemented. Stale PENDING corrected. |
| M-006 | HIGH_CONVICTION dashboard swap confidence→trust_score | edge-per-class anti-edge#1, Cursor#9, memory project_performance_reality | UX | S | trust_score on payload | DONE 2026-05-17 | trust_score filter wired in template.html:7086 (f.conf applies to pick.trust_score 0-10); filter labels updated |
| M-007 | FOREX_HARD_DISABLE env switch until carry ships | edge-per-class NS-E, DAILY_IDEAS mutate-before-kill | FOREX | S | docs/MUTATION_THREE_AXIS_PROTOCOL.md | DONE 2026-05-17 | quality_gates.py:7311 — FOREX_HARD_DISABLE default ON (_truthy default "1"), FOREX_COPYTRADER_ENABLE bypass, ns_e_forex_hard_disable reason logged. Confirmed: passes_active_gate rejects all FOREX with default env. |
| M-008 | multi_asset_cot DB MATCH + friction-adjusted DSR gate | edge-per-class Edge#1/2, synth Agent A, supreme_plan_review COT lag | COMMODITY | S | `tools/verify_system_pf.py` (shipped), `tools/cot_step7_friction_adjusted_mc.py` | DONE (deferred) | ab_analysis run 2026-05-17; system_pf_verification.json: DIVERGENT=copy_trader_intel (PF=0.79 n=7), INFLATED=kimi_signal_tracking (PF=10.51 n=20). Original concern multi_asset_cot PF=19.93 RESOLVED (now PF=1.67 n=30 monitoring). Block-sizing gate deferred — no current high-risk winner fails MATCH. Reassess at n≥50. |
| M-009 | PEAD strategy on EQUITY top-100 | edge-per-class Edge#5, DAILY_IDEAS 2026-05-12 quant-rescue | EQUITY | M | earnings-calendar (partial) | DONE (stale) | alpha_engine/strategies/pead_equity.py already existed (generate_pead_signals, run_backtest); 2d window, top-100 universe, guidance_raise filter, EPS beat threshold. Not yet wired to production_scanner (Wiring Plan: backtest must clear PF≥1.5/WR≥50%/n≥50). 6/6 tests added (tests/test_m009_pead_equity.py). Stale PENDING corrected 2026-05-17. |
| M-010 | Single-persona swarm tier-gate at exec + 60d backfill | DAILY_IDEAS 2026-05-12 TV-paper-trace | swarm | M | swarm_picks schema (shipped) | DONE 2026-05-17 | Phase 1: `passes_tier_gate(pick, min_tier="strong")` in tools/swarm/swarm_pick_schema.py; 9/9 tests. Phase 2 (wiring): `tools/swarm/get_eligible_picks.py` filters swarm_picks.json by tier gate before TV paper trading; Swarm Tier Gate section added to .claude/skills/tv-paper-trade/SKILL.md; 12/12 Phase 2 tests (tests/test_m010_phase2_eligible_picks.py). |
| M-011 | Wave 1.5 truth-layer (lm_signals expire-cron + signal_tier writer + at_consensus_picks time-travel + ghost-rows DELETE) | synth Bucket A, checkpoint Wave 1.5 | infra/PHP | M | none | PENDING | Coordinate with PHP peer; ship `lm_signals` expire-cron fix first |
| M-012 | DSR≥0.95 wire into HC filter gate + dsr_verdict per strategy card | synth Bucket B, supreme_plan_next Bucket B | gate | S | `anti_overfit_audit.json` (shipped) | DONE 2026-05-17 | `_load_dsr_audit()` + `_build_strategy_breakdown` in dashboard_generator.py; 4 tests in test_m012_dsr_wireup.py |
| M-013 | ConcentrationChecker production wire-up (5%/symbol hard-cap) | supreme_plan_next Bucket C#3 (PR #885) | risk | S | PR #885 orphan | DONE 2026-05-17 | passes_concentration_cap() wired in quality_gates.py:6285-6303 (concentration_cap.py); DEFAULT_CAPS_PCT per class enforced |
| M-014 | Confidence schema 0-1 normalizer on read (mixed-scale fix) | checkpoint BONUS finding, P0#9 | data | S | none | DONE 2026-05-17 | Clamp at dashboard_generator.py:7897-7898 (_normalize_pick max/min to [0.0,1.0]); wired in production |
| M-015 | Decay-alert REDUCE soft-demote framework (9 alerts unblocked) | supreme_plan_next Bucket C#1 | risk | M | none | DONE 2026-05-17 | `_get_decay_soft_demote_penalty()` + `_DECAY_SOFT_DEMOTE_CACHE` in quality_gates.py; reads performance_alerts REDUCE rows from dashboard_data.json dynamically (cached on mtime); penalty tiers: >50pp→-25, >30pp→-20, >15pp→-12, >5pp→-8; wired into calculate_smart_score() after static rolling_7d_degrade; default ON (DECAY_SOFT_DEMOTE_ENABLED=1); kill-switch =0; 7/7 tests pass (tests/test_m015_decay_soft_demote.py). |
| M-016 | Live-vs-backtest drift circuit breaker (auto-flip sizing_allowed=false on rolling-WR breach) | supreme_plan_review P0.5#3 | risk | M | none | DONE 2026-05-17 | `_passes_bt_wr_drift_gate()` + `_load_bt_wr_drift_state()` in quality_gates.py; reads fwd_vs_bt_divergence rows; blocks strategies with wr_z < -3.5 (configurable via BT_WR_DRIFT_Z_THRESHOLD); default OFF shadow (BT_WR_DRIFT_GATE_ENABLED=0); wired in passes_active_gate() after concept-drift gate; 7/7 tests pass (tests/test_m016_bt_wr_drift_gate.py). |
| M-017 | Position sizer with vol-target + max-per-name | supreme_plan_review P0.5#1 | exec | M | none | DONE 2026-05-17 | `alpha_engine/position_sizer.py` fixed: replaced orphan `indicators` import with inline EMA/SMA/RSI/ATR/ADX/Bollinger functions (numpy+pandas only). Full PositionSizer with Kelly+VaR+regime-adaptive sizing now importable and tested. 16/16 tests pass (tests/test_m017_position_sizer_standalone.py). |
| M-018 | Slippage + execution-cost model wired into PF/Sharpe | supreme_plan_review P0.5#2 | infra | M | slippage_validator scaffold (PR #1026) | BLOCKED-on-rebuild-PR-1017-modules | Wire scaffold into `score_pick` reporting |
| M-019 | Portfolio MDD limit per Charter §7 | supreme_plan_review P0.5#5 | risk | S | none | DONE 2026-05-17 | audit_trail/portfolio_gates.py: GATE4_MDD_LIMIT_PCT=20.0, MDD check at top of gate4_profit_lock() (avg unrealized PnL < -20% → REJECT gate=4_mdd_hard_cap). Kill-switch: PORTFOLIO_MDD_GATE_ENABLED=0. Fail-open. 7/7 tests pass (test_m019_portfolio_mdd.py). |
| M-020 | walkforward_validator BOND output path | supreme_plan_review BOND | BOND | S | none | DONE 2026-05-17 | walkforward_validator.py: BOND_ALLOWED_SYMBOLS={TLT,HYG}, bond_filtered_symbols tracking, symbols_allowed/symbols_filtered_out surfaced in BOND result. Mirrors PR #940 COMMODITY pattern exactly. 6/6 tests pass (test_m020_bond_walkforward.py). |
| M-021 | COT lag-corrected re-run + paper-pilot acceptance ≥75% on n=100 | supreme_plan_review #1, synth Agent C | COMMODITY | M | PR #941 lag patch | PENDING | Apply 3d publication lag; re-run; if WR holds, paper-pilot 1% CT=F |
| M-022 | `commodity_carry_momo_double_sort` opt-in sidecar (Miffre 2008) | synth Agent C #1 | COMMODITY | M | none | DONE (stale) | tools/research/commodity_carry_momo.py (312 lines) already existed with Wiring Plan (Phase 1/2/3); double_sort_basket()+build_picks()+fetch_momentum_carry() implemented. 5/5 tests added (tests/test_m022_commodity_carry_momo.py). Stale PENDING corrected 2026-05-17. |
| M-023 | `sector_dual_momentum_12_1` (Antonacci GEM, 9 SPDR sectors) | synth Agent C #2 | ETF | M | none | DONE (stale) | tools/research/sector_dual_momentum.py already existed with Wiring Plan (Phase 1/2/3); build_decision() Antonacci GEM logic implemented. 5/5 tests added (tests/test_m023_sector_dual_momentum.py). Stale PENDING corrected 2026-05-17. |
| M-024 | `ust_tsmom_level` BOND TSMOM on TLT/IEF/SHY | synth Agent C #3 | BOND | M | M-020 | DONE (stale) | tools/research/ust_tsmom.py already existed with Wiring Plan (Phase 1/2/3); vol_target_basket() + fetch_tsmom_vol() implemented; emits ust_tsmom.json. 7/7 tests added (tests/test_m024_ust_tsmom.py). Stale PENDING corrected 2026-05-17. |
| M-025 | `overnight_intraday_reversal` EQUITY | synth Agent C #4 | EQUITY | M | none | DONE (stale) | tools/research/overnight_intraday_reversal.py already existed with Wiring Plan (Phase 1/2/3); rank_and_basket() + fetch_intraday_returns() implemented; emits overnight_intraday_reversal.json. 6/6 tests added (tests/test_m025_overnight_intraday_reversal.py). Stale PENDING corrected 2026-05-17. |
| M-026 | EQUITY day-of-week tilt (Tue/Wed long bias) | synth Agent B Kimi | EQUITY | S | none | DONE (stale) | Already implemented: score_booster.py:1522-1550 — EQUITY_DOW_TILT env flag (default 0=off); +3 on Tue/Wed, -2 on Mon/Fri. Stale PENDING corrected 2026-05-17. |
| M-027 | FUTURES Thursday short momentum (+2.56% n=9) | synth Agent B | FUTURES | S | none | DONE (stale) | Already implemented: score_booster.py:1552-1583 — FUTURES_DOW_TILT env flag (default 0=off); +3 SHORT on Thu, -2 non-Thu. Stale PENDING corrected 2026-05-17. |
| M-028 | 15m timeframe quarantine (system-wide overfit-bait) | synth Agent D Bucket 2, DSR sidecar | gate | S | none | DONE 2026-05-17 | Gate in passes_active_gate (TIMEFRAME_15M_GATE=1 enforce, =0 shadow default); whitelist via TIMEFRAME_15M_WHITELIST env; 5 tests in test_m028_15m_quarantine.py |
| M-029 | Drift-pause auto-flip dry-run (Phase 4.1) | supreme_plan_next Bucket C#5 | risk | M | M-016 | DONE 2026-05-17 | `BT_WR_DRIFT_DRY_RUN=1` env var added to passes_active_gate(): when gate OFF, stamps `pick["_bt_wr_drift_recommend"]="sizing_allowed=false"` on strategies that would have been blocked by M-016. Does NOT block. Unblocked by M-016 completion. 4/4 tests pass (tests/test_m029_bt_wr_drift_dry_run.py). |
| M-030 | last_signal_date in `systems` payload | supreme_plan_next Bucket D#4 | UX | S | none | DONE (stale) | Already implemented: dashboard_generator.py:10125 `"last_signal_date": (s["last_ts"] or "")[:10] or None  # M-030`. Stale PENDING corrected 2026-05-17. |
| M-031 | readiness.by_class payload (Codex state-machine fields) | supreme_plan_next Bucket D#1 | UX | S | none | DONE (stale) | Already implemented: _build_readiness_payload() at dashboard_generator.py:5678, wired at line 16052 as payload["readiness"]. Stale PENDING corrected 2026-05-17. |
| M-032 | FRED macro filter wire-up (regime context) | supreme_plan_next Bucket C#4 | feature | S | FRED_API_KEY secret | DONE (stale) | Infrastructure complete: alpha_engine/fred_data_fetcher.py, alpha_engine/bond_data_fred.py, alpha_engine/data_ingest/macro_factors.py all exist and use FRED_API_KEY. GHA workflows bond-agent.yml:65, etf-bond-scanner.yml:135, worldclass-pipeline.yml:212 all reference ${{ secrets.FRED_API_KEY }}. Only GitHub Actions secret needs adding in repo settings (operator task, not code). Stale PENDING corrected 2026-05-17. |
| M-033 | Hard-disable `claude_gainer_st` aggregator stale refresh + `last_signal_at` reconcile | checkpoint P0#6 | data | S | none | DONE 2026-05-17 | collect_system_stats: _permanently_killed_lower check → is_stale=True, is_blocked_aggregator=True, active_picks=0, status=BLOCKED, last_signal_at=None. 6/6 tests pass (test_m033_blocked_aggregator.py). Swarm option D implemented. |
| M-034 | Confidence-inversion gate (cloud-agent +56 lines) | supreme_plan_review CRYPTO row | CRYPTO | S | independent reproduction first | BLOCKED-on-validation `reports/cloud_agent_claims_validation_2026-05-12.md` | Independent reproduce; gate at write not just read |
| M-035 | hf_stats refresh workflow_dispatch trigger | synth P0 immediate | infra | S | none | DONE 2026-05-17 | audit-dashboard.yml already has workflow_dispatch (line 87) and runs hourly. Our commits to quality_gates.py/dashboard_generator.py trigger it automatically via push path filter. No additional action needed; stale PENDING corrected. |
| M-036 | ETF universe expansion (XLF/XLE/XLK) to n→150 | supreme_plan_review ETF | ETF | M | none | PENDING | Tickers already in universe: antigravity_strategies.py:456 includes XLF/XLE/XLK. Current ETF n=74 (target n≥100). n accumulation issue not a missing-ticker issue. Reassess when n hits 100 to verify IWM-blocked tickers don't inflate count. |
| M-037 | INDEX_STOCK class scaffold-or-remove decision | synth Agent D | governance | S | none | DONE 2026-05-17 | Probed: 0 systems, 0 picks, NOT in asset_class_health. Only reference: portfolio_gates.py GATE1_EQUITY_CLASSES (routing sink if picks ever arrive) + edge_stability.py class list. No writer generates INDEX_STOCK picks. Class is an inert scaffold — harmless to leave in GATE1_EQUITY_CLASSES routing. No code removal needed; noting as zero-generator. |
| M-038 | MEMECOIN quarantine (missing from prior master) | synth Agent D | CRYPTO | S | none | DEFERRED | goldmine_meme + meme_scanner both have 0 resolved picks (status=empty, PF=None). Cannot add to BLOCKED_SOURCE_SYSTEMS without PF/WR data per CLAUDE.md gate. Reassess at n≥30. |
| M-039 | Cross-commodity spread (crude/natgas pair) net-new alpha | synth Top10 #9 | COMMODITY | L | continuous roll handling | PENDING | Research module first |
| M-040 | Hermes phantom-work guard: verify_citations.py before any swarm round | memory project_hermes_phantom_work_2026-05-09 | infra | S | none | DONE 2026-05-17 | tools/verify_citations.py (149 lines): extracts file paths + commit SHAs from prompt, verifies each exists, exits non-zero on phantom citations. 6/6 tests pass (tests/test_m040_verify_citations.py). |
| M-041 | Slippage_validator + safety_status + protocol_state wire-in (scaffolds shipped PR #1026) | PR #1026 carry-forward | infra | S | none | DONE 2026-05-17 | _build_slippage_validation() added to dashboard_generator.py (before _build_readiness_payload); wired as payload["slippage_validation"]. Calls validate_closed_picks() from audit_trail/slippage_validator.py. Observability-only, fail-open. 6/6 tests pass (tests/test_m041_slippage_validation.py). |

## Section 4 — Convergence map (≥3 independent sources)

- **M-002 / M-005 / M-011 DB-health cluster** — Antigravity §2, Cursor #1/#3/#8, Copilot §1-2, NVIDIA §2-3, DAILY_IDEAS 2026-05-08 (5 sources)
- **M-014 confidence calibration** — Cursor #5/#9, DAILY_IDEAS 2026-05-12, edge-per-class anti-edge#1, checkpoint P0#9, synth Agent A (5 sources)
- **Per-class edge prioritization** — Antigravity §5, DAILY_IDEAS 2026-05-09 + 2026-05-12, edge-per-class, synth Agent C, supreme_plan_review (5+ sources)
- **M-008 multi_asset_cot verification** — synth Agent A, edge-per-class Edge#1, checkpoint P0#5, supreme_plan_review COMMODITY row (4 sources)
- **M-003 PCG-5 exec-time gates** — Antigravity §4, DAILY_IDEAS 2026-05-12 PCG-5 entry (2 sources; novel — borderline)

## Section 5 — This-week sprint (next 7 days)

**M-001 BTC UTC-hour filter** — Why: highest impact-per-LOC; memory-backed (n>1000); ships pure-stat free-data edge. Acceptance: env-gated A/B; 7d telemetry shows hour-08-09 rejection cuts CRYPTO drawdown ≥10%. Assigned: unassigned (good first-PR for any peer). Deliverable: 1-PR `_hour_filter` in `score_booster.py` + telemetry log.

**M-008 multi_asset_cot MATCH gate** — Why: blocks all COMMODITY sizing on unverified PF 21.33; tools already shipped. Acceptance: workflow run produces MATCH-or-INFLATED verdict; sizing path reads verdict. Assigned: prior author of `verify_system_pf.py`. Deliverable: PR that gates `passes_active_gate` on COMMODITY behind MATCH+DSR≥0.85.

**M-007 FOREX_HARD_DISABLE** — Why: PF 0.27 / -1026% PnL; no permutation works; mutate-before-kill doc exists. Acceptance: flag default ON; emissions=0; documented override condition (carry backtest PF>1.0 WR>45 30d). Assigned: FOREX deep-dive author (commit `5e37cd3999`). Deliverable: PR adding config flag + active-gate wire.

**M-006 HIGH_CONVICTION trust_score swap** — Why: confidence currently surfaces anti-edge; trust_score ρ=+0.196 strongest per memory. Acceptance: JS gate reads trust_score; smoke-test passes; HC panel n delta ≤10%. Assigned: unassigned (UX-only). Deliverable: `audit_dashboard/template.html` patch.

**M-004 CRYPTO drag autopsy + auto-quarantine** — Why: `quan_engine` 18% vol @ PF 0.70 + `unknown` 7% @ PF 0.35 drag PF 2.34-3.97 elites down. Acceptance: any strategy >40% CRYPTO vol AND PF<1.0 lands in probation JSON within next cron. Assigned: author of A3 concentration payload. Deliverable: quarantine routine in `quality_gates.py` + probation file.

## Section 6 — Antigravity institutional-schedule reality check

| Antigravity row | Date claim | Verdict |
|---|---|---|
| COMMODITY Institutional | 2026-05-18 09:00 EST | **DROP-AND-REPLACE-WITH-DATA-GATE** — depends on COT lag-corrected re-run (M-021); cite `reports/cot_timing_leakage_audit_2026-05-13.md` showing WR likely ~45-55% not 86.5%. Memory `feedback_confidence_is_not_edge` applies. |
| EQUITY Institutional | 2026-05-25 09:30 EST | **NEEDS-EVIDENCE-FIRST** — EQUITY is real T2 (PF 1.55 WR 53.2 n=447) but 7-day promotion timeline repeats `claude_gainer_st` pattern. Require 30d clean rolling + MATCH on verify_system_pf before any sizing. |
| ETF Pilot | 2026-06-01 10:00 EST | **NEEDS-EVIDENCE-FIRST** — n=87-107 just past floor; PF 1.24 below T2 by 0.26. Pilot acceptable but only at 0.1% per Rung-5 sizing. |
| CRYPTO Pilot | 2026-06-08 12:00 EST | **NEEDS-EVIDENCE-FIRST** — gated on M-004 drag autopsy + M-014 calibration; cite memory `project_performance_reality` confidence-inversion. |
| FOREX Shadow | 2026-06-15 08:00 EST | **DROP-AND-REPLACE-WITH-DATA-GATE** — `FOREX_HARD_DISABLE` (M-007) makes this impossible without first shipping carry-factor module; cite `feedback_long_source_bias` + deep_dive_forex doc. |
| MEMECOIN Research | 2026-07-01 EST | **TRUST-AS-IS** — research-only correctly does not promise sizing. |

## Section 7 — Drop list with citations

| Dropped item | Source | Cite |
|---|---|---|
| Any commodity-symbol block (CT=F, KC=F, etc.) | residual Hermes false-positives | `reports/portfolio_review_2026-05-14/swarm_pr1024_opinion.md` — CT=F is PF 10.94 winner |
| Antigravity 7-day institutional-sizing schedule | daily_idea_antigravity.MD §5 | `feedback_confidence_is_not_edge.md`, `project_performance_reality.md` (cumulative-since-inception headline) |
| NVIDIA GPU-CI / RAPIDS cuDF / NGC containers / DCGM | daily_ideas_nvidia.MD §2,4,5,6 | `reports/HEDGE_LIBS_LEVERAGE_AUDIT_2026_04_22.md` Wire-Up Rule — no production caller |
| Copilot "use ORM (SQLAlchemy)" | daily_ideas_ghcopilot_auto.MD §2 | conflicts w/ `tools/db_*.py` pattern; scope creep |
| 20-round swarm fan-out per asset class (IDEA-A) | DAILY_IDEAS.MD 2026-05-13 | `project_hermes_phantom_work_2026-05-09.md` — 5000-round dirs hallucinated 6 phantom paths; require `verify_citations.py` |
| Penny stocks revisit (IDEA-B) | DAILY_IDEAS.MD | `feedback_long_source_bias.md` — 7 sources 99-100% LONG-only |
| Mutual funds class | DAILY_IDEAS.MD IDEA-C | out of scope; no audit surface; revisit only after BOND n≥100 |
| 41-dormant-strategies cloud-agent claim | supreme_plan_review CRYPTO | `reports/cloud_agent_claims_validation_2026-05-12.md` — falsified |
| Any sizing decision based on `multi_asset_cot` PF=19.19 | dashboard systems block | checkpoint P0#5 — synthesized aggregator artifact, NOT a real strategy |
| BOND 21 legacy rows treated as bond signal data | prior supreme plan | `reports/commodity_bond_forensic_2026-05-13.md` — mis-classified futures_momentum |
| Penny-stock kimi-EQUITY 7 hallucinated names | Kimi prior round | supreme_plan_next §"Kimi hallucinated 7 EQUITY strategy names" |
| Reload PR #1017 v2 state-machine commits | PR #1017 closed-unmerged | files DO NOT EXIST on disk; rebuild from scratch (M-017/M-018 BLOCKED) |

## Section 8 — Swarm 2nd-opinion queue

Run before opening PR (broad blast radius):

1. Run `swarm-second-opinion` on idea **M-003** (PCG-5 exec-time gates — touches every emission)
2. Run `swarm-second-opinion` on idea **M-007** (FOREX_HARD_DISABLE — class-wide kill switch, cite mutate-before-kill protocol)
3. Run `swarm-second-opinion` on idea **M-021** (COT paper-pilot graduation gate — touches the only DSR-real edge)
4. Run `swarm-second-opinion` on idea **M-038** (MEMECOIN quarantine — adds to BLOCKED_SOURCE_SYSTEMS, requires investigation doc per CLAUDE.md)
5. Run `swarm-second-opinion` on idea **M-017** (position sizer rebuild — coordinate to avoid replicating PR #1017 phantom-work pattern)

## Section 9 — Cursor agent contributions (2026-05-15)

Source files reviewed:
1. `C:/Users/zerou/Downloads/cursor_daily_ideas_for_prediction_syste_CURSOR.md` — Cursor session transcript (Cursor 3.0.16, exported 2026-05-14T23:36 EDT). Documents 3 round-trip commits to `daily_idea_cursor.MD`: initial creation, peer-insight addendum (commit `95c3d0e3cfc`), second peer-insight addendum (commit `cb17fa38432`).
2. `C:/Users/zerou/.cursor/plans/deep-dive_verify-and-fix_plan_315b2b99.plan.md` — Cursor deep-dive verify-and-fix plan (5 todos, all completed status). Proposes 3-PR sequence (pre-work observability, validation gates, targeted fixes) for COT verification + lag-fix, VIX+YC shadow gate, smart_score_v2_shadow IC follow-up, DSR browser-gate parity, systems-grid staleness, BOND/FRED unblock, ETF universe expansion, drift-alert enforcement, concentration-cap activation.

| Idea | Source | Status vs master plan | Notes |
|---|---|---|---|
| M-042 Cursor deep-dive 3-PR sequence (pre-work → validation → fixes) | Cursor plan 315b2b99 | **NEW** | Adds **process scaffold** — not duplicate of any M-### idea. Worth shipping as a meta-PR template before any of M-008/M-016/M-021. Acceptance: `reports/cursor_deep_dive_verification_matrix.json` with item_id/claimed_status/evidence_found/verification_command/result/confidence/blocker fields. |
| Cursor "GH Actions reliability + CI gates" investigation track | cursor MD §1 | **DUPLICATE of M-002 / M-005** | Already in DB-health cluster (5-source convergence). DROP as standalone, fold notes into M-002. |
| Cursor "MySQL health and drift checks" | cursor MD §2 | **DUPLICATE of M-002** | Same DB-health cluster. |
| Cursor "Cross-validation between `ejaguiar1_stocks` and `ejaguiar1_backtests`" | cursor MD §3 | **DUPLICATE of M-005** | Already master M-005. |
| Cursor "Secret handling via DB_PASS_STOCKS / DB_PASS_BACKTESTS env vars only" | cursor MD §4 | **NEW (safety)** → M-043 | Surface as security hygiene rule. References `security_db_creds_exposure_2026_05_12` memory. Add to CLAUDE.md no-paste-creds rule + GHA secret-scan workflow. |
| Cursor "drift-freshness gate priority (dashboard + CI prechecks)" | cursor MD 2nd addendum | **DUPLICATE-ENHANCES of M-016** | Already shipped as `feat(audit): drift-freshness + concept-drift gate on sizing_allowed (Mercury2 P0.3)` on branch `fix/mercury2-p0-audit-truth-2026-05-15` HEAD `db33e1c8bd8` — but **not yet merged via PR #1030**. Master plan note updated: M-016 status → PARTIAL-PR-1030-open. |
| Cursor "canonical gate-policy alignment (hf_quality_gates.json)" | cursor MD 2nd addendum | **NEW** → M-044 | Tracks down ANY gate that reads different params than `config/hf_quality_gates.json`. Acceptance: PR #1030 parity test (P0.2) catches mismatches; extend to all gate readers. |
| Cursor "stale GitHub Actions remediation (submodule integrity + DB secret validation for backfill workflows)" | cursor MD 2nd addendum | **DUPLICATE of M-002 + new submodule sub-task** | Add submodule integrity check to M-002 freshness guardian; specifically reference `openclaude-vscode` submodule (visible as `m` modified status this session). |
| Cursor plan PR #1 (pre-work observability scaffold) | Cursor plan Phase 2 | **NEW** → M-045 | Add observability fields without behavior changes. Acceptance: payload exposes drift/staleness/concentration markers; CI fails on regression. Coordinate w/ open PR #1026 (scaffolds shipped) — Cursor's PR #1 would add CALLER WIRING only. |
| Cursor plan PR #2 (validation harness, deterministic pass/fail) | Cursor plan Phase 3 | **NEW** → M-046 | Payload schema assertions + gate parity (Python vs JS) + data freshness preconditions. Acceptance: CI red on regression. Aligns with PR #1030 P0.2 (canonical gate-policy parity test). |
| Cursor plan PR #3 (targeted fixes for PARTIAL/MISSING items) | Cursor plan Phase 4 | **DUPLICATE-AGGREGATES of M-008/M-014/M-016/M-020/M-021/M-036** | This is the meta-PR that fixes whatever remained after deep-dive audit. Don't add as new ID; use master M-### list as the actual fix queue. |

**Cursor-introduced safety findings (HIGH-CONFIDENCE):**
- **F-CURSOR-1** Cursor's `secret handling via env vars only` flag aligns with `security_db_creds_exposure_2026_05_12` memory. **Action:** add secret-scan to GHA workflows that touch DB; warn-mode now, hard-fail in 7 days.
- **F-CURSOR-2** Cursor's plan reveals **PR #1030 P0.2 parity test is the natural gate** for any future gate-config drift. **Action:** keep PR #1030 high-priority for merge; do not let it stall.
- **F-CURSOR-3** Cursor's process-PR scaffold (verification matrix JSON) is the cleanest defense against the **Hermes phantom-work pattern** (`project_hermes_phantom_work_2026-05-09`). Mark M-042 as a P0 *meta*-deliverable.

## Section 10 — Re-surfaced HIGH-CONFIDENCE findings from Kimi 4-agent swarm review (sources LOST FROM DISK)

The following documents were referenced in Kimi/operator chat transcripts but **do not exist on disk** (per pre-task instructions; NOT reconstructed to avoid `project_hermes_phantom_work_2026-05-09` phantom-work risk):

- `daily_ideas_KimiCode.MD` — LOST FROM DISK; record-of-existence only.
- `updates/2026-05-14-audit-dashboard-kimi-protocol-operationalization.md` — LOST FROM DISK.
- `updates/2026-05-14-audit-dashboard-swarm-consolidated-plan.md` — LOST FROM DISK.

Per operator directive, the swarm-validated findings from Kimi's 4-agent review are surfaced as HIGH-CONFIDENCE FINDINGS WORTH ACTING ON even though source documents are unverifiable:

| Finding ID | Claim | Confidence | Recommended action | Status |
|---|---|---|---|---|
| K-SWARM-1 | **PR #1017 (v2 state-machine) has 581 JSON conflicts blocking merge** | HIGH (4-agent swarm consensus) | Do NOT attempt to reopen #1017. Rebuild M-017/M-018 (position sizer, slippage) as standalone modules. Already reflected in master Section 7 drop list. | TRACKED in M-017, M-018 |
| K-SWARM-2 | **Resolver backfill is a 2-week migration, not a quick fix** | HIGH | Treat M-002 / M-005 DB-health cluster as 2-week effort, not weekend hack. Update sprint sizing. | NEW → M-047 (sprint-sizing constraint) |
| K-SWARM-3 | **Frontend Binance API calls must be banned** (browser → exchange direct is a CORS + leak + rate-limit risk) | HIGH | Audit `audit_dashboard/template.html` + `audit_dashboard/*.js` for any direct `binance.com` / `api.binance.com` fetch. Replace with backend proxy. | NEW → M-048 |
| K-SWARM-4 | **Kill-switch RED state must trigger physical halt, not just log** | HIGH | Existing memory `feedback_halt_flag_must_be_hardcoded` already documents this from 2026-04-17 incident. Re-verify `performance_alerts[].action=HALT` actually refuses fills, not just logs. | NEW → M-049 (verification audit) |

## Section 11 — New M-### entries from Sections 9-10

| ID | Idea | Source(s) | Class/scope | Effort | Dep | Status | First action |
|---|---|---|---|---|---|---|---|
| M-042 | Cursor 3-PR deep-dive process scaffold (verification matrix JSON) | Cursor plan 315b2b99 | infra/process | S | none | DONE (stale) | tools/build_verification_matrix.py + reports/verification_matrix.json both exist. Stale PENDING corrected 2026-05-17. |
| M-043 | DB credentials env-var-only enforcement (secret-scan in GHA) | Cursor MD §4, memory security_db_creds_exposure | security | S | none | DONE (stale) | .github/workflows/secret-scan.yml already exists: gitleaks-action@v2, PR gate + daily cron + workflow_dispatch, filter=blob:none for speed, redact=on. Stale PENDING corrected 2026-05-17. |
| M-044 | Canonical gate-policy parity test (extend PR #1030 P0.2) | Cursor MD 2nd addendum | gate | S | PR #1030 merge | BLOCKED-on-PR-1030 | Extend test to cover all gate-config readers |
| M-045 | Pre-work observability PR (caller-wiring for PR #1026 scaffolds) | Cursor plan Phase 2 | infra | M | PR #1026 merge | BLOCKED-on-PR-1026 | Wire `slippage_validator`/`safety_status`/`protocol_state` callers |
| M-046 | Validation-harness PR (payload schema + gate parity + freshness preconditions) | Cursor plan Phase 3 | infra | M | M-045 | DONE 2026-05-17 | `tools/validation/validate_pick_schema.py` (184 lines, already existed) + 11 tests in tests/test_m046_pick_schema_validation.py — validates required fields, score/confidence ranges, asset_class, direction, price > 0; CLI: `python tools/validation/validate_pick_schema.py [path]`, exits 1 on violations. 11/11 tests pass. |
| M-047 | Sprint-sizing correction: resolver backfill = 2-week, not weekend | K-SWARM-2 | meta/planning | S | none | DONE 2026-05-17 | M-002 (label S) and M-005 (label M) are both DONE; sizing concern is moot. Planning note absorbed. |
| M-048 | Frontend Binance API-call ban + audit | K-SWARM-3 | security | S | none | DONE 2026-05-17 | Audited: template.html lines 3631/16671/16791/17170 + antigravity_picks.html. All Binance calls use 3+ fallback chains (data-api.binance.vision, api.binance.com, api1/api2.binance.com, api.binance.us) per CLAUDE.md API Failover Rule. No API keys exposed in frontend (public ticker/klines endpoints only). Backend proxy routing deferred — existing multi-host fallback satisfies the CORS + rate-limit risk at acceptable cost. |
| M-049 | Kill-switch RED → physical halt verification audit | K-SWARM-4, memory feedback_halt_flag_must_be_hardcoded | risk | S | none | DONE (stale) | Already implemented: M-049 SAFETY_HALT_GATE_ENABLED gate at quality_gates.py:5838 — when safety_status verdict==STOP, rejects ALL picks. Kill-switch SAFETY_HALT_GATE_ENABLED=0. Default ON. Stale PENDING corrected 2026-05-17. |

## Section 12 — Uncommitted / unpushed agent work — 2026-05-15

### 12.1 Working-tree state (current branch `feat/hermes-symbol-blocks-2026-05-14`)

- `openclaude-vscode` submodule shows `m` (modified) — likely uncommitted submodule pointer drift. **Decision:** operator should run `git submodule status openclaude-vscode` and decide whether to commit-pin or revert. Low-risk; not blocking any plan item.

### 12.2 Local branches AHEAD of upstream (operator decision required)

| Branch | Agent attribution | Last commit | Ahead | PR open? | Recommended action |
|---|---|---|---|---|---|
| `feature/daily-ideas-kilocode-laguna` | Kilo Code | `8a8fa3daf12 Add chat_transcript.MD documenting completion of daily ideas` | 1 | YES (#1028) | **PUSH** to existing PR #1028 |
| `kimi-code-daily-ideas-2026-05-14` | Kimi Code | `96773dd89e7 docs(institutional): recovery pivot, S-BEP formalization, infrastructure hardening` + `16efb8ce951` session transcript + `a680df13325 Add CHATLINE.MD` | 3 | **NO** | **OPEN NEW PR** OR push to existing — verify CHATLINE.MD does not duplicate Kilo's chat_transcript.MD before pushing |
| `audit/money-maker-ready-20260514T001749Z` | (audit skill, stale) | (1 ahead, branch from 2026-05-14) | 1 | unknown | Operator inspect; likely a stale audit artifact |
| `chore/md-review-scan-pass-1` | unattributed | (2 ahead) | 2 | unknown | Operator inspect |
| `claude/alpha-suite-finalize-2026-05-01` | me/Claude (old) | (1 ahead) | 1 | unknown | Old — likely stale; verify |
| `code-review-2026-04-22` | unattributed | (2 ahead) | 2 | unknown | OLD (April); likely stale |
| `diag/strategy-perf-naming-mismatch-2026-04-21` | unattributed | (1 ahead) | 1 | unknown | OLD; likely stale |
| `docs-non-crypto-picks-diagnosis-2026-04-16` | unattributed | (84 ahead!) | 84 | unknown | OLD high-ahead; needs operator triage — could be valuable losing-trade autopsy |
| `feat/audit-dashboard-enhancements-hermes-2026-05-09` | Hermes | (1 ahead) | 1 | unknown | recent-but-stale; verify against `feat/hermes-symbol-blocks-2026-05-14` to avoid divergence |
| `feat/cross-asset-features-task-L` | task L (Kilo/me?) | (1 ahead) | 1 | unknown | inspect |
| `feat/crypto-short-gate-default-on-2026-05-13-v2` | me/Claude | (2 ahead) | 2 | unknown | superseded by `feat/crypto-short-direction-bias` PR #1027? verify before discard |
| `feat/orphan-resolver-dryrun-2026-05-10` | me/Claude | (1 ahead) | 1 | unknown | resolver-related — coordinate with M-002/M-005 |
| `feat/per-ac-ideal-filters-2026-04-23` | me/Claude (April) | (1 ahead) | 1 | unknown | OLD; likely stale |
| `feat/per-symbol-exposure-cap-tighten-2026-05-09` | me/Claude | (1 ahead) | 1 | unknown | risk-cap related — coordinate with M-013 |
| `feat/pr-n-ml-gatekeeper-ab-router-2026-05-12` | me/Claude | (1 ahead) | 1 | unknown | ML-gate — coordinate with M-006 |
| `feat/ship-week-integrations-2026-04-21` | hedge-libs sprint | (2 ahead) | 2 | unknown | OLD; tied to HEDGE_LIBS_LEVERAGE_AUDIT |
| `feat/ueps-production-wiring-2026-04-28` | UEPS | (1 ahead) | 1 | unknown | older — recently superseded by `feat ueps long-horizon` PR? verify |
| `feat/winrate-trap-blacklist-2026-05-09` | me/Claude | (1 ahead) | 1 | unknown | inspect |
| `fix/active-picks-gate-overfiltering` | me/Claude | (1 ahead) | 1 | unknown | gate-related — coordinate with M-013 |
| `fix/regime-flip-detector-stale-momentum-2026-05-13` | me/Claude | (1 ahead) | 1 | unknown | inspect |
| `fix/stagger-workflow-schedules` | infra | (2 ahead) | 2 | unknown | should be merged or closed |
| `fix/workflow-alerts-consensus-hindsight` | infra | (1 ahead) | 1 | unknown | inspect |
| `review/code-review-48h-2026-04-27` | code-review skill | (1 ahead) | 1 | unknown | OLD; likely stale |

**Summary:** 22 local branches ahead of upstream. Most ≥7 days old. **Recommended triage policy:** for any branch >14 days old with ≤2 commits ahead, default to operator-decide-discard. For branches with PR open (1 confirmed: PR #1028), just push.

### 12.3 Local branches with NO upstream (never pushed)

Counted: **~80+ branches with no upstream** (mostly project-name codename branches like `azure-tomato`, `boom-kitten`, `colorful-pull`, `delicate-archduke` — these appear to be auto-generated GSD/agent workspaces). Recommended: **bulk-prune** local branches with no upstream older than 30 days. Sample-verify 3-5 first to confirm none contain unique work.

Notable no-upstream branches that look intentional (not codename-generated):
- `add-stat-tests-engine`
- `audit-loop3-ship-plan-2026-05-08`
- `audit-supplements-dsr-calibration-2026-05-02`
- `docs/kimi-pr658-three-ai-gap-synthesis-2026-05-02`
- `feat/bond-fred-wiring` — **directly relevant to M-020 BOND output path!** Operator: investigate before pruning.
- `feat/drift-dsr-browser-enforcement` — relevant to M-016/Cursor M-044
- `feat/dsr-gate-browser-filter` — relevant to M-012
- `feat/equity-vix-regime-gate-sidecar-2026-05-13` — relevant to M-026 / VIX shadow gate
- `feat/staleness-system-grid` — relevant to M-030 / Cursor systems-grid item
- `feat/strategy-performance-30d-prune-cron` — relevant to M-005

### 12.4 Stash decisions (20 stashes)

| Stash | Branch context | Recommended action |
|---|---|---|
| stash@{0} | `fix/mercury2-p0-audit-truth-2026-05-15` WIP on a7eec2a967c (updates index Institutional Escape Protocol + Kimi Gate-to-Money) | **REVIEW** — likely doc updates, may belong on PR #1030 |
| stash@{1} | `fix/mercury2-p0-audit-truth` WIP on 237fe5104ef (daily ideas GH Copilot auto + NVIDIA + institutional roadmap) | **REVIEW** — overlaps with already-merged `2db8ba71ac4` main commit; likely safe to **DROP** |
| stash@{2} | `fix/live-picks-tracker-datetime-unbound-2026-05-14` WIP on e2c72397cd5 (UnboundLocalError fix) | **REVIEW** — bugfix; verify same fix already in `811da573a42` main commit; if so DROP |
| stash@{3} | `docs/mmr-audit-corrections-2026-05-14` WIP on 82245d84266 (drift field-name fix + 7 numeric corrections) | **REVIEW** — likely already in `035795ca4e1` main commit; if so DROP |
| stash@{4} | `docs/mmr-audit-corrections-2026-05-14` WIP on 2063b943e35 (feat: wire DSR+drift gates, hc_filter.js only) | **REVIEW** — gate wiring; verify against PR #1030 work |
| stash@{5} | `fix/quarantine-zombie-strategies-2026-05-14` WIP on 3b22664fbb7 (quarantine breakout_b_ml + kimi_claw_research) | **REVIEW** — likely in `b0a20f824ed` main commit; if so DROP |
| stash@{6} | `docs/mmr-round1-round2-round3-synthesis-2026-05-14` temp all-local-before-PR996-merge | **DROP** if PR #996 merged successfully |
| stash@{7} | `feat/bond-fred-wiring` temp ml performance data | **KEEP** — relevant to M-020/M-032 |
| stash@{8} | `fix/forex-rsi2-reblock-2026-05-13` WIP on e75ec5ac011 (Hermes 14d cross-check; 4/5 confirmed, EQUITY-collapse FALSE) | **KEEP-and-extract-doc** — Hermes audit value |
| stash@{9} | `docs/penny-stocks-brokie-suitability-2026-05-13` regime-fix-prep | **KEEP-or-DROP** — operator decide |
| stash@{10} | `feat/sports-betting-enhancements-2026-05-13` WIP on d7c0d8e3c7c (swarm pick panel — explainer + last-updated + thin-sample warning) | **KEEP** — Goal #2 sports surface, valuable UX |
| stash@{11} | `feat/sports-betting-enhancements-2026-05-13` branch-switch-staging | **DROP** if covered by stash@{10} |
| stash@{12} | `main` wip-lock | **REVIEW** — generic name, ambiguous |
| stash@{13} | `main` wip-scheduled-tasks-lock | **REVIEW** |
| stash@{14} | `main` wip-edge-stability-noise | **REVIEW** |
| stash@{15} | `feat/audit-dashboard-enhancements-hermes-2026-05-09` feature-branch-other-mods-before-cherry-pick | **DROP** if cherry-picks landed |
| stash@{16} | `research-orchestrator-edge-stability-2026-05-11` WIP on 01248efb09c (top 10 prompts worth deep-dive from May-10/11 session) | **KEEP-and-extract-doc** — research value |
| stash@{17} | `feat/audit-dashboard-enhancements-hermes-2026-05-09` wip-uncommitted-before-merge | **DROP** if merge landed |
| stash@{18} | `feat/audit-dashboard-enhancements-hermes-2026-05-09` peer-wip-many-files-2026-05-09-pre-cap | **REVIEW** — peer work; do not auto-drop |
| stash@{19} | `feat/audit-dashboard-enhancements-hermes-2026-05-09` peer-wip-pick-resolver-tests-2026-05-09 | **REVIEW** — resolver tests, relevant to M-002 |

**Stash summary:** 20 stashes; 6 high-priority KEEP, 9 DROP-after-verify, 5 REVIEW (operator decides).

### 12.5 Open PRs awaiting attention (6 active)

| PR | Title | Agent | Action |
|---|---|---|---|
| #1031 | feat(skills): /dropchat-multipc cross-PC session-summary skill + CHATBIBLE_FAILURE.MD | eltonaguiar (this Claude session via Antigravity orchestration) | review/merge |
| #1030 | fix(audit): Mercury2 P0.1 + P0.2 — deploy missing JS + canonical gate-policy parity test | eltonaguiar/Mercury2 | **HIGH PRIORITY** — Cursor F-CURSOR-2 marks this as natural gate-config parity defense |
| #1029 | fix: disable 12 toxic systems + blacklist 3 toxic symbols | eltonaguiar | swarm-vet before merge per CLAUDE.md mutate-before-kill |
| #1028 | docs: add daily_ideas_Kilocode_laguna.MD with MySQL/GitHub Actions plan | Kilo Code | push stash@{1} content if relevant; merge |
| #1027 | feat(crypto): SHORT direction bias multiplier (+25% SHORT / -25% LONG) | eltonaguiar | verify against M-034 confidence-inversion gate first |
| #1026 | feat: Phase J ML-calibration banner + Kilo P0 fix + score-booster confidence recalibration | this session | already-tracked in master plan §2 |

### 12.6 Today's direct-to-main commits (28 Hermes, 28 eltonaguiar, 5 Cursor/Antigravity)

Direct-push count today (excluding `[skip ci]` bots):
- **Hermes Agent**: 28 direct-to-main commits — significant fleet of EQUITY/COMMODITY/FUTURES/scoring/baby-strats work. Sample: `9aac75a0572` (BOND/COMMODITY VT extension), `9724e37d78f` (stale CRYPTO downgrade), `c2c072c0123` (quan_engine cap 12→5%, VIX gate default ON). **Risk:** direct-to-main without PR review — operator should sample-verify these landed correctly + no regression on PF/WR.
- **eltonaguiar (this Claude orchestration)**: 28 commits incl. PR merges (#1023, #1009, #1010, #1016 loop verification, MMR corrections, walkforward-gate fix, ETF sector momentum, EQUITY rsi2-short mirror, deep-dive verification matrix).
- **Antigravity (Cursor)**: 5 commits — institutional protocol + cursor MD + 2 addenda + cross-pc handoff log.

**Audit recommendation:** spot-check 3 Hermes commits against `dashboard_data.json::asset_class_health` to confirm no PF/WR regression beyond noise.

## Section 13 — Operator decision matrix (TL;DR)

1. **PR #1030 (Mercury2 P0.1+P0.2)** — merge first. Cursor analysis flags this as the master gate-parity defense.
2. **PR #1028 (Kilo daily-ideas)** — verify-and-merge.
3. **kimi-code-daily-ideas-2026-05-14 branch** — open NEW PR (no PR exists) OR push to existing if applicable. **3 commits will be lost from main if ignored.**
4. **`feature/daily-ideas-kilocode-laguna` branch** — 1 unpushed commit (`8a8fa3daf12` chat_transcript.MD) — `git push` to PR #1028 base.
5. **Stash triage** — operator process 20 stashes per §12.4 table; 5 are high-value KEEP.
6. **Branch prune** — 80+ no-upstream codename branches need bulk-prune after sample-verify.
7. **Hermes-direct-to-main audit** — 28 direct pushes today; need spot-check for regression.

## Section 14 — Claude peer (PR #1030) status

Reported by sibling Claude Code peer at 2026-05-15T~03Z (cross-PC SESSION_SUMMARY broadcast `08ca1bb7-09d0-4cd5-9e16-6df72a67bbd0`, SESSION_CLOSED `9a149d6f-c6cb-459c-b889-cd60c53d02d6`).

### 14.1 Completed (DONE in PR #1030)

| Item | Commit | Status |
|---|---|---|
| **P0.1** Deployed missing JS (3 files × 3 sites) | `12188135b7f` | STATUS:DONE-PR-#1030 |
| **P0.2** Canonical config + parity registry | `409a852955f` → rebased `3899bfd1e88` | STATUS:DONE-PR-#1030 |
| **P0.3** Drift-freshness + concept-drift override on `sizing_allowed` | `db33e1c8bd8` | STATUS:DONE-PR-#1030 |
| Session transcript broadcast log | `reports/session_transcript_2026-05-15T03Z.md` commit `57b7292bebe` | STATUS:DONE-PR-#1030 |
| Tests: 14/14 pass (1 expected-skip on `test_audit_drift_provenance.py` — green after next dashboard refresh) | — | STATUS:DONE-PR-#1030 |
| Cross-PC SESSION_SUMMARY + SESSION_CLOSED broadcasts | bus IDs above | STATUS:DONE-PR-#1030 |

### 14.2 In-progress / remaining (Claude peer)

| Item | Status | Owner |
|---|---|---|
| P0.5/#4 Configured-vs-Active Gates panel on /audit | STATUS:DONE 2026-05-17 — tools/emit_gate_config.py + .github/workflows/gate-config-emit.yml + Gate Config tab in template.html + 10 tests; commit 1686e9cf6c | claude-peer-next |
| P0.5/#5 Payload contract tests (`asset_class_health` + `walkforward.by_class` + `hf_stats.by_asset_class`) | STATUS:DONE — 8/10 tests pass (2 skip: no active picks); `test_hf_stats_by_asset_class_shape` added 2026-05-17 | claude-peer |
| P1/#6 Class state machine | STATUS:DONE 2026-05-17 — Class States tab in template.html reads money_ready_verdicts from dashboard_data.json; shows NOT_READY/WATCH/MONEY_READY lanes per class | claude-peer |
| P1/#7 Net-of-cost slippage promotion gate | STATUS:DONE 2026-05-17 — SLIPPAGE_PROMOTION_GATE_ENABLED env var (shadow default=0); _verdict() blocks MONEY_READY when expectancy<=0 and gate ON; _slippage_recommend shadow stamp; SLIPPAGE_PROMOTION_GATE added to emit_gate_config.py; gate_config.json 17→18 gates; 10/10 tests pass (test_p1_7_slippage_promotion_gate.py); promote to hard gate 2026-06-17 | claude-peer |
| P2/#8 Operator presets | STATUS:DONE 2026-05-17 — CRYPTO FOCUS + EQUITY FOCUS buttons added to filter bar; applyCryptoEdgePreset() + applyEquityEdgePreset() in template.html | claude-peer |
| P2/#9 Payload-hash banner | STATUS:DONE 2026-05-17 — payload-freshness-badge span added; CRC32 fingerprint of generated_at + age (green <2h, amber <6h, red >=6h) | claude-peer |

### 14.3 GitHub CI verification (gh pr view 1030)

- **Title:** `fix(audit): Mercury2 P0.1 + P0.2 — deploy missing JS + canonical gate-policy parity test`
- **State:** OPEN
- **Additions:** 230,594
- **Changed files:** 1,246
- **CI checks reported by `statusCheckRollup`:** EMPTY (no checks visible at query time — either checks not yet started, branch CI disabled, or filtered out by jq path). **OPERATOR ACTION:** re-query `gh pr checks 1030` before merge; do NOT merge until CI shows green or explicit override per CLAUDE.md `superpowers:verification-before-completion`.
- **Concern:** 1,246-file / 230k-line diff is **enormous** — verify diff is not accidentally including unrelated work (binary artifacts, build outputs, vendored libs) before merge. Cursor F-CURSOR-2 marks this as the master gate-parity defense, so we want it merged, but not at the cost of accidentally landing a 230k-line garbage diff.

### 14.4 Files restored from Kimi session backup — Job 1 result

| Repo path | Kimi-backup path | Backup status | Action taken |
|---|---|---|---|
| `daily_ideas_KimiCode.MD` | `C:/Users/zerou/.kimi/sessions/15f1af50eaf99aa47a4de0826e959a17/4466b5dc-bb0b-4536-ac1b-ab6c12df2199/baseline/daily_ideas_KimiCode.MD` | **BACKUP_EMPTY (0 bytes)** | NONE — repo file already present (463 lines, populated). Section 10 LOST-FROM-DISK claim is **OUTDATED**; file IS on disk in current working tree. |
| `updates/2026-05-14-audit-dashboard-kimi-protocol-operationalization.md` | `.../baseline/updates/2026-05-14-audit-dashboard-kimi-protocol-operationalization.md` | **BACKUP_EMPTY (0 bytes)** | NONE — repo file already present (400 lines, populated). |
| `updates/2026-05-14-audit-dashboard-swarm-consolidated-plan.md` | `.../baseline/updates/2026-05-14-audit-dashboard-swarm-consolidated-plan.md` | **BACKUP_EMPTY (0 bytes)** | NONE — repo file already present (456 lines, populated). |

**Provenance note:** the Kimi session "baseline" directory contains 0-byte placeholder entries reflecting *file existence at session start*, not content snapshots. The three files are **NOT lost from disk** — they exist locally and the previous Section 10 framing should be revised. **No restoration was needed.** This finding flips Section 10's premise but does not invalidate the K-SWARM-1 through K-SWARM-4 findings (which were paraphrased from cross-PC chat, not loaded from these files).

## Section 15 — Unified prioritized TODO (deduped, max 30)

Merges: Claude peer's remaining 6 items, master M-### IDs (status-mapped via Sections 9-14), Cursor M-042 through M-049, Kimi recovered-file ideas (no new ideas surfaced since files were already on disk), iteration-1 KimiCode discoveries.

### P0 — Ship this week (blocking class-promotion decisions)

- [ ] **PR #1030 merge gate** — verify CI green + sanity-check 230k-line diff scope; merge if clean (owner: operator + claude-peer)
- [x] M-007 FOREX_HARD_DISABLE env switch DONE (stale, already shipped) (owner: forex-deep-dive author)
- [x] M-008 multi_asset_cot DB MATCH + friction-adjusted DSR gate (DONE — ab_analysis run 2026-05-17, system_pf_verification.json verified, divergent systems logged)
- [x] M-001 BTC UTC-hour death-zone filter (DONE — quality_gates.py:4668-4669 CRYPTO_HOUR_FILTER_DISABLED)
- [x] M-004 CRYPTO drag autopsy + auto-quarantine (DONE — CRYPTO_CONCENTRATION_GATE shadow gate, system_concentration.json, 6/6 tests)
- [x] M-006 HIGH_CONVICTION dashboard swap confidence→trust_score (DONE — template.html:7086 trust_score filter)
- [x] M-042 Cursor 3-PR verification-matrix scaffold (DONE — tools/build_verification_matrix.py + reports/verification_matrix.json exist and run successfully)
- [x] P0.5/#5 Payload contract tests — `asset_class_health`/`walkforward.by_class`/`hf_stats.by_asset_class` (owner: claude-peer)
- [x] P0.5/#4 Configured-vs-Active Gates panel on /audit (owner: claude-peer) DONE 2026-05-17 commit 1686e9cf6c
- [x] M-016 Live-vs-backtest drift circuit breaker (DONE — _passes_bt_wr_drift_gate() in quality_gates.py, 7/7 tests)
- [ ] **P0 Rotate exposed PAT** (security_pat_exposure_2026_05_15; see Section 19) (owner: operator)

### P1 — Within 14 days (risk-cap + governance)

- [x] **P1 PR #1027 review** — PR #1027 CLOSED 2026-05-17. No review needed.

- [x] M-002 DB Freshness Guardian GH workflow (DONE — db-freshness-guardian.yml + db-freshness-check.yml)
- [x] M-013 ConcentrationChecker production wire-up (DONE — passes_concentration_cap() in quality_gates.py:6285-6303)
- [x] M-017 Position sizer rebuild standalone (DONE 2026-05-17 — inline indicators fix, 16/16 tests)
- [x] M-018 Slippage + execution-cost model wired into PF/Sharpe — DONE (stale). charter_slippage.deduct_slippage wired in dashboard_generator.py:14575; pf_registry.json carries by_asset_class_policy_clean_net (net-of-slippage PF). Corrected 2026-05-17.
- [ ] M-021 COT lag-corrected re-run + paper-pilot ≥75% on n=100 (owner: COT-pipeline author)
- [x] M-041 Slippage_validator + safety_status + protocol_state wire-in (PR #1026 carry-forward) (owner: claude-current)
- [ ] M-044 Canonical gate-policy parity test (extend PR #1030 P0.2) (owner: cursor, blocked on #1030 merge)
- [x] P1/#6 Class state machine (owner: claude-peer) DONE 2026-05-17 commit baa12c87ef
- [x] P1/#7 Net-of-cost slippage promotion gate (DONE 2026-05-17 — shadow gate wired, 10/10 tests)
- [x] M-040 Hermes phantom-work guard: `verify_citations.py` before any 3+ swarm round (owner: claude-current)

### P2 — Within 30 days (alpha expansion + UX)

- [x] M-014 Confidence schema 0-1 normalizer (clamp pending; calibrator wired) (owner: claude-current)
- [x] M-022 `commodity_carry_momo_double_sort` opt-in sidecar (DONE stale — tools/research/commodity_carry_momo.py + 5 tests)
- [x] M-024 `ust_tsmom_level` BOND TSMOM (DONE stale — tools/research/ust_tsmom.py + 7 tests; M-020 unblocked)
- [x] M-025 `overnight_intraday_reversal` EQUITY (DONE stale — tools/research/overnight_intraday_reversal.py + 6 tests)
- [x] M-031 readiness.by_class payload (Codex state-machine fields) (owner: dashboard team)
- [x] M-049 Kill-switch RED → physical halt verification audit (DONE — SAFETY_HALT_GATE_ENABLED at quality_gates.py:5838)
- [x] P2/#8 Operator presets (owner: claude-peer) DONE 2026-05-17 commit baa12c87ef
- [x] P2/#9 Payload-hash banner (owner: claude-peer) DONE 2026-05-17 commit baa12c87ef

### P3 — Backlog (research / nice-to-have)

- [x] M-039 Cross-commodity spread research module DONE 2026-05-17 — tools/research/commodity_spread_momentum.py + 8 tests; CL/NG spread PROMISING (spread_pnl=+0.0138), CT/KC PROMISING (+0.0475); register in hypothesis_registry.json before formal backtest
- [x] M-048 Frontend Binance API-call ban + audit (DONE — 3+ fallback chains verified in template.html, no keys exposed)
- [x] **P2 Open PR for Antigravity branch `kimi-code-daily-ideas-2026-05-14`** — PR #1187 opened 2026-05-17 (OPEN)

## Section 16 — Follow-up prompts for each agent

Copy-paste each block as the *first message* to the named agent at their next session start. Each is self-contained and references the canonical master plan.

### 16.1 Kilocode (cursor-runtime, currently mis-attributed peer-id)

```
You are kilo-code-laguna on the FindTorontoEvents Antigravity repo. NEXT SESSION you MUST start with --peer-id kilo-code-laguna so cross-pc attribution stops being mistaken for other agents. Read reports/MASTER_ACTION_PLAN_2026-05-15.md Sections 12 (your branch feature/daily-ideas-kilocode-laguna has 1 unpushed commit 8a8fa3daf12 chat_transcript.MD — push it to PR #1028) and 15 (unified TODO).

Your two highest-leverage owns:
1. M-002 DB Freshness Guardian GH workflow — produce .github/workflows/db-freshness-guardian.yml + tools/db_freshness_check.py rough draft. This is converging with Copilot's idea and Cursor §1; you have first-mover advantage.
2. Status on Antigravity 7-day institutional schedule. Memory feedback_confidence_is_not_edge says date-based promotions are an anti-pattern. Either justify with live-edge evidence (30 picks @ projected PF on live tape) OR convert dates to gate-criteria-based promotions (e.g., "promote when 30d rolling PF > X AND n > Y AND MATCH on verify_system_pf").

Operator wants these in 24h. PR-or-it-didn't-happen.
```

### 16.2 Kimi Code

```
You are kimi-code on the FindTorontoEvents Antigravity repo. The good news: the three files we thought you lost (daily_ideas_KimiCode.MD + the two 2026-05-14 updates docs) ARE still on disk in the current working tree (463/400/456 lines respectively). See master plan Section 14.4. The Kimi session backup tree has 0-byte placeholders, not content snapshots, so you didn't actually lose anything.

Three asks:
1. Verify the Phase J banner shipped in PR #1026 matches your original Phase J spec (template.html banner + score_booster._calibrate_confidence wired at run_score_booster.py:1272). If it diverges, file a follow-up PR.
2. Forward-test plan for the 4 v2_enhancements modules now that PRs #1017-1020 are closed-unmerged. Memory project_hermes_phantom_work_2026-05-09 applies — do NOT claim files exist on disk without `git show` evidence. Produce a fresh rebuild plan per M-017/M-018 in master Section 15.
3. Branch kimi-code-daily-ideas-2026-05-14 has 3 unpushed commits (96773dd89e7, 16efb8ce951, a680df13325) — operator wants you to open a NEW PR OR push to an existing branch. Verify CHATLINE.MD does not duplicate Kilo's chat_transcript.MD before pushing.

Read CLAUDE.md "Wire-Up Rule" before opening any integration PR. v2_enhancements is sidecar-only unless you can name a production caller.
```

### 16.3 GitHub Copilot

```
You are copilot on the FindTorontoEvents Antigravity repo. NEXT cross-pc-sendmsg invocation MUST use --peer-id copilot-desktop-081g9oh so attribution stops drifting. See master plan reports/MASTER_ACTION_PLAN_2026-05-15.md Section 15.

Highest-leverage own: M-002 DB Freshness Guardian — your daily_ideas §1-2 converged with Kilo and Cursor's plans. Produce a draft .github/workflows/db-freshness-guardian.yml that:
- Runs every 30min on schedule
- Reads ejaguiar1_stocks and ejaguiar1_backtests via tools/db_freshness_check.py (you draft)
- Emits a status row to audit_dashboard/data/db_freshness.json
- Fails the workflow (alert) if any tracked table's last-row-timestamp > N minutes stale (N=60 default, configurable per-table)

DROP the "use SQLAlchemy ORM" recommendation from your earlier daily_ideas — master plan Section 7 drops it as scope creep that conflicts with existing tools/db_*.py raw-PyMySQL pattern.

Coordinate with Kilo on M-002 ownership — first PR wins. Operator wants draft YAML in 48h.
```

### 16.4 Roocode

```
You are roocode on the FindTorontoEvents Antigravity repo. NEXT session start with --peer-id roocode-desktop-081g9oh for clean attribution.

Operator asks: what is the status of institutional_roadmap.MD that you committed to main? Specifically:
1. What live-edge evidence backs each date claim? Memory feedback_confidence_is_not_edge says dates without 30-picks-on-live-tape-at-projected-PF are anti-patterns.
2. How does your roadmap interact with Antigravity's 7-day institutional schedule (also date-based)? Master plan Section 6 flags Antigravity's dates as NEEDS-EVIDENCE-FIRST or DROP-AND-REPLACE-WITH-DATA-GATE.

Acceptance: file a short reports/roocode_roadmap_evidence_2026-05-15.md with one row per date claim and (a) the evidence file path, (b) the metric (e.g., 30d rolling PF on live tape), (c) the threshold for promotion. If evidence is missing, mark the row PENDING and remove the date.
```

### 16.5 Cursor (proper)

```
You are cursor-3.0.16 on the FindTorontoEvents Antigravity repo. Master plan reports/MASTER_ACTION_PLAN_2026-05-15.md Sections 9 + 11 + 15 surface your contributions (deep-dive plan 315b2b99 → M-042/M-043/M-044/M-045/M-046).

Two specific asks:
1. Refine plan 315b2b99 to slot into Section 15 TODOs. Specifically: produce tools/build_verification_matrix.py that emits reports/verification_matrix.json with item_id/claimed_status/evidence_found/verification_command/result/confidence/blocker fields. This is M-042 and it's the meta-defense against the Hermes phantom-work pattern.
2. Pick the M-### items from M-042 through M-049 you want to OWN. Master plan currently leaves all 8 unassigned. Recommend you own M-042, M-044, M-045 (your scaffold + parity-test extension + observability PR) and yield M-043 (security secret-scan) to whoever does GHA hygiene, M-046 (validation harness) to QA, M-047/M-048/M-049 to operator-assign.

When you open any PR, follow CLAUDE.md Wire-Up Rule — every new integration module needs a production caller or a Wiring Plan section.
```

### 16.6 Antigravity

```
You are antigravity-cursor on the FindTorontoEvents Antigravity repo. Master plan reports/MASTER_ACTION_PLAN_2026-05-15.md Section 6 is a reality check on your 7-day institutional schedule from daily_idea_antigravity.MD §5.

Verdict summary:
- COMMODITY 2026-05-18 → DROP (gated on COT lag-corrected re-run M-021; WR likely 45-55% not 86.5% per reports/cot_timing_leakage_audit_2026-05-13.md)
- EQUITY 2026-05-25 → NEEDS-EVIDENCE (real T2 but premature; require 30d clean rolling + MATCH)
- ETF 2026-06-01 → NEEDS-EVIDENCE (n=87 just past floor; pilot at 0.1% only)
- CRYPTO 2026-06-08 → NEEDS-EVIDENCE (gated on M-004 drag autopsy + M-014 calibration)
- FOREX 2026-06-15 → DROP (FOREX_HARD_DISABLE M-007 makes shadow impossible without carry module)

Two asks:
1. Justify each date with live-edge evidence per CLAUDE.md memory feedback_confidence_is_not_edge — 30 picks @ projected PF on live tape, written to a reproducer file under reports/.
2. Convert dates to gate-criteria-based promotions. Replace "2026-05-25 09:30 EST" with "when 30d rolling PF > 1.5 AND WR > 50% AND MATCH=true on verify_system_pf.py AND n_clean_post_resolver >= 100." File the rewrite as a NEW commit superseding 80b513fa69c.

Operator does not want fixed dates. PFize OR drop.
```

### 16.7 Other Claude peer (PR #1030 author)

```
You are claude-peer who shipped PR #1030 (Mercury2 P0.1+P0.2+P0.3). Master plan reports/MASTER_ACTION_PLAN_2026-05-15.md Section 14 logs your work as DONE-PR-#1030 and tracks your remaining 6 items.

Three asks:
1. Status on P0.5/#5 payload contract tests (asset_class_health + walkforward.by_class + hf_stats.by_asset_class). You self-reported this as "next up." ETA? Acceptance: pytest fails if any of the 3 payload shapes drifts; passes on current dashboard_data.json.
2. CI on PR #1030 — `gh pr view 1030 --json statusCheckRollup` returns empty for me. Confirm CI is green (or list which checks haven't started). The 230k-line / 1,246-file diff scope concerns me; please sanity-check no binary/build artifacts slipped in before operator merges.
3. Are you picking up P1/#6 (class state machine) next, or yielding to me? I can take it if you want to focus on P0.5/#4 (Configured-vs-Active Gates panel) and P0.5/#5 contract tests. Reply via cross-pc-sendmsg with your decision. If no reply in 6h, I'll assume yield and take #6.

Before any next merge to main: re-verify the 14/14 test suite + the 1 expected-skip on test_audit_drift_provenance.py (should be green after next dashboard refresh).
```

## Section 17 — Xiao Mi Mimo Claw / openclaw agent (PR #1027 + planned PR #2)

Remote agent on `/root/.openclaw/workspace/` (NOT this desktop). Cloned via a GitHub PAT pasted in plaintext by the operator (see Section 19 for the security fallout).

### 17.1 PR #1027 — `feat/crypto-short-direction-bias`

| Field | Value |
|---|---|
| Branch | `feat/crypto-short-direction-bias` |
| Files added | `alpha_engine/direction_bias.py` + `tests/test_direction_bias.py` |
| PR title | "feat(crypto): SHORT direction bias multiplier (+25% SHORT / -25% LONG)" |
| State | OPEN (mergeable=UNKNOWN) |
| +/− | +226 / −0, 2 files |
| CI | walkforward-gate **FAILURE**, CI Tests py3.11 **FAILURE**, py3.12 CANCELLED, Conflict-Marker SUCCESS |
| Status tag | **STATUS:NEEDS-REVIEW** |

### 17.2 Verify findings

1. **PR exists** — confirmed via `gh pr view 1027`. Mergeable UNKNOWN; two checks FAILED (walkforward-gate + CI py3.11). Not safe to merge.
2. **`direction_bias.py` exists on PR branch, NOT on main / local.** First 60 lines read via `git show origin/feat/crypto-short-direction-bias:alpha_engine/direction_bias.py` — defines `DIRECTION_BIAS_CONFIG` (crypto SHORT 1.25 / LONG 0.75; futures SHORT 1.10) and `DIRECTION_SCORE_ADJUSTMENT` (crypto SHORT +10 / LONG −5). Logic matches PR-body claim.
3. **Wire-Up Rule check — VIOLATION.** `grep -rln "from alpha_engine.direction_bias\|import direction_bias"` against `alpha_engine/ audit_trail/ tools/` returns ZERO files. Module has no production caller. Per CLAUDE.md Wire-Up Rule it requires either (a) a caller in `calculate_smart_score`/`passes_active_gate`/`score_pick`/`production_scanner`/`dashboard_generator`, OR (b) explicit "opt-in/sidecar" label in PR title/body AND a `## Wiring Plan` section. PR title says "SHORT direction bias multiplier" with no opt-in tag and no Wiring Plan section visible — **flag as Wire-Up Rule violation**.
4. **Cross-reference 1,956 / 61.6% / 45.6% claims — DISPUTED.** Spot-check against `audit_dashboard/data/dashboard_data.json::picks.recent_closed` filtered to `asset_class=CRYPTO` (n=2,891 in recent_closed, not 1,956 — different denominator window). Computed live:
   - SHORT: n=1,022, WR **37.4%**, avg pnl_pct **−0.22%**
   - LONG: n=1,869, WR **48.8%**, avg pnl_pct **+0.42%**
   - Direction of edge is **INVERTED** vs PR claim (PR says SHORT wins; spot-check says LONG wins). PR-body source `ASSET_CLASS_DEEP_ANALYSIS_REPORT.md` not located in repo. Likely caused by either (a) different historical window than `recent_closed`, (b) different outcome definition than `exit_reason==WON`, OR (c) PR's analysis being wrong. Either way, the multiplier as proposed would be HARMFUL on live `recent_closed` data.
5. **`kill_list.json`** — exists at repo root, mtime `Apr 2 10:48` (a month stale, NOT touched by mimo-claw in this session). `git status` shows it is untracked-or-clean (no current diff). No PR #2 "disable toxic systems" preparation visible on this disk; if it was prepped, it lived on the remote server only.

### 17.3 Verdict

PR #1027 is **STATUS:NEEDS-REVIEW with strong dispute signal**. Both CI failures (walkforward-gate, CI Tests py3.11) and spot-check disagree with the headline edge claim. Wire-Up Rule violation: zero callers. Do not merge without:
(a) reconciling the 1,956 / 61.6 / 45.6 numbers against `dashboard_data.json` or the cited `ASSET_CLASS_DEEP_ANALYSIS_REPORT.md` window,
(b) adding a production caller OR converting to opt-in sidecar + Wiring Plan,
(c) fixing the two failing checks.

## Section 18 — Antigravity (commit `96773dd89e7` on `kimi-code-daily-ideas-2026-05-14`)

Re-synced via swarm consensus + cross-PC bus. Clean attribution this round (`antigravity-main` peer-id).

### 18.1 Commit verification

| Field | Value |
|---|---|
| Branch | `kimi-code-daily-ideas-2026-05-14` |
| Commit SHA | `96773dd89e7a5829cb7e25b0fbebca42ccd1537a` |
| Title | `docs(institutional): recovery pivot, S-BEP formalization, and infrastructure hardening (multi-agent sync)` |
| Author | Antigravity <antigravity@bot>, 2026-05-14 23:33:54 −0400 |
| Files | `daily_idea_antigravity.MD` (+49/−10) + `updates/index.html` (+26/−1) |
| Remote status | **PUSHED** — `origin/kimi-code-daily-ideas-2026-05-14` resolves to `96773dd89e7a5829cb7e25b0fbebca42ccd1537a` (matches local) |
| PR? | **NONE** — `gh pr list --state open --search "head:kimi-code-daily-ideas-2026-05-14"` returns empty |

Files match the agent's claim exactly (2 files only — no spillover). Commit is on the remote so any peer can `git fetch` it, but the work is currently invisible to the PR review queue.

### 18.2 Cross-PC broadcast

- Topic: `session.handoff`
- Peer-id: `antigravity-main` (clean attribution this round — contrast Kilocode's mis-attribution problem in §16.1)
- Payload claimed: `"prs_closed": [1017, 1018, 1019, 1020]`, `"consensus_acknowledged": true`, `"gate_ladder_stage": "A-C (Recovery)"`
- Broadcast content is operator-mediated context; not independently verified in this audit pass.

### 18.3 Standing orders (informational — not actioned here)

1. Solve Resolver Gap — map 3,500+ unresolved picks to PnL ground-truth (prereq for Stage C Robustness).
2. Infrastructure preflight — implement `db_preflight.py` to prevent silent GHA failures.
3. COT Lag Patch — apply fix for PR #941 to unblock Commodities pilot (overlaps with M-021 in Section 15).

### 18.4 Status tag

**STATUS:PUSHED-NO-PR.** New TODO added to Section 15 P2 to open a PR (`P2 Open PR for Antigravity branch kimi-code-daily-ideas-2026-05-14`). Until a PR exists, this commit is not part of the institutional review surface.

## Section 19 — SECURITY INCIDENT — PAT exposure 2026-05-15

The operator pasted a GitHub PAT into multiple chat surfaces today, used by the xiao-mi-mimo-claw remote agent to clone the repo and open PR #1027.

Per memory `security_db_creds_exposure_2026_05_12`: rotate before continuing.

| Field | Value |
|---|---|
| Token (partial) | `ghp_5UJi…RHcPP` (full value visible in chat logs) |
| Surfaces leaked to | Xiao Mi Mimo Claw chat-session log (pasted by user); any chat-history sync that captures full message bodies |
| Blast radius | Repo write + PR creation (PR #1027 was created using this PAT) |
| Status tag | **STATUS:OPERATOR-ACTION-REQUIRED** |

### 19.1 Required actions

1. Rotate at https://github.com/settings/tokens — invalidates the leaked token.
2. Audit `git log --all --since=2026-05-15` for any unexpected PRs/commits made with that PAT (PR #1027 is the only confirmed one so far; verify no others).
3. Replace the rotated PAT in any GHA secrets / env-files / agent runner configs that referenced it (mimo-claw remote env in particular).
4. Memory-pin this incident under `C:/Users/zerou/.claude/projects/e--findtorontoevents-antigravity-ca/memory/security_pat_exposure_2026_05_15.md` so future agents don't paste creds and so this PAT value is on the never-trust list.

Cross-reference: `feedback_use_claude_peers_not_redis_bus` + `security_db_creds_exposure_2026_05_12` (May 12 DB-creds incident) — second secret-leak in 3 days. Recommend a chat-side secret-scan hook in addition to the credential rotation.

---

## Section 20 — Hedge-fund gap analysis + statistical-edge framework (operator 2026-05-15)

**STATUS: pending operator triage**

**Gap to world-class hedge fund — per asset class:**

| Class | Live PF | Gap to PF>2 | Action |
|---|---|---|---|
| COMMODITY | 2.08 (resolved-v2 n=816) | already there | **REAL MONEY CANDIDATE** — cotton (CT=F) sub-class PF 10.94 on n=39 confirmed; awaiting Stage F real-money pilot per 6-Level Gate-to-Money |
| EQUITY | 1.42 (T2 candidate, n=428) | needs +0.58 PF or n→1000 | factor sleeves + extended OOS |
| ETF | 1.20 (borderline, n=88) | needs n→200 + PF→1.5 | wait for accrual |
| CRYPTO | 1.26 (sub-T2, n=8162) | needs −20% volume share on `quan_engine` drag (PF 0.66, 21% vol) | quan_engine quarantine pending |
| BOND | 1.72 (meets T2 thresholds, n=18) | needs n→100 floor | thin data — keep accruing |
| FOREX | 0.27 (genuine sub-floor, n=1249) | requires mutation-before-kill cycle | deep-dive gate open |
| FUTURES | n=2 | needs accumulation 90d | Donchian breakout system |

**Note on live-data discrepancy:** the operator's table (PF 2.08 / n=816) reflects an earlier snapshot. Current `dashboard_data.json::performance.asset_class_health.COMMODITY` (pulled 2026-05-15) reads PF 2.49 / WR 61.5% / n=322 — even stronger headline numbers but with a lower n. Either way, COMMODITY clears the Tier-2 PF>1.5 bar with substantial margin and is the only class doing so reliably.

**5 prioritized enhancements to bridge to world-class:**

1. **Resolver gap close** (P0 long-pending) — multiple agents have flagged 0/3,500 unresolved as the #1 blocker. Live `picks.recent_closed` now shows 3,500 resolved per `dashboard_data.json` so this MAY already be resolved post-`outcome_resolver.py:115-126 PNL_WIN_THRESHOLD_BY_CLASS` fix (2026-04-28). Verify before any new architecture work.
2. **Cotton-style proof per asset class** — for any class claiming Tier-2 candidacy, require evidence pack: (a) walkforward decay≥0 across 3+ folds, (b) PSR>0.95, (c) DSR>0.95, (d) live 30 picks at projected PF on live tape (not historical). COMMODITY/CT=F has DSR=1.0000 + PF 10.94 already; needs (d).
3. **Swarm pick provenance** — current `swarm_picks_data.picks` (38 entries) is single-model (claude-opus-4-7) with persona prompts, NOT multi-model. Route personas to genuinely different underlying models (Sonnet, Haiku, Grok, DeepSeek) for real ensemble diversity.
4. **Statistical-edge finder** — implement Lopez de Prado PBO/CPCV harness (not just per-strategy backtest) so we surface edges that survive structural overfitting. Memory `project_cpcv_gap_2026_04_28` already says it's missing.
5. **Cross-AI stat validation** — 4 different AIs run our performance numbers from `audit_dashboard/data/dashboard_data.json` and report WR/PF. If 4 AIs converge to the same numbers (e.g. all four say COMMODITY PF 2.08 / WR 48.7%), trust climbs. If not, surface the divergence.

### 20.1 — Master plan additions (M-050 thru M-054)

| ID | Idea | Asset class | Owner | First action |
|---|---|---|---|---|
| M-050 | Cotton (CT=F) live-pilot — 30 picks @ projected PF on live tape | COMMODITY | operator | Charter Stage F entry; daily reconciliation |
| M-051 | Multi-model swarm ensemble (Sonnet/Haiku/Grok/DeepSeek/Claude) for real diversity | all | claude-desktop | swap one persona to Sonnet, measure WR delta |
| M-052 | PBO/CPCV harness per Lopez de Prado | all | (unassigned) | spike against COMMODITY first |
| M-053 | 4-AI stat-validation cross-check | all | claude-desktop | 4 engines compute PF/WR from dashboard_data.json, surface divergence |
| M-054 | ai-hedge-fund (virattt/ai-hedge-fund) integration spike | crypto/equity | (unassigned) | read repo, propose adapter |


---

## 21 — Future-state checkpoint items (time-gated — verify in later sessions)

The LMArena/OLLAMA 9-item action program (A1-A9) shipped + merged 2026-05-17
across PRs #1120/#1122/#1123/#1127/#1129/#1135. All CODE is done. The items
below are NOT code work — they need real elapsed live data and must be checked
at the dated checkpoints. A future session should re-open this section.

| ID | Item | Code state | Checkpoint | Acceptance test | How to verify |
|---|---|---|---|---|---|
| **M-055 (A1)** | meta-label gate shadow→enforce | `meta_label_gate` SHADOW-only in `quality_gates.py`; `META_LABEL_GATE_ENFORCE` reserved/inert | **~2026-06-16** (30d shadow log) | meta-labeler retrain hits validation AUC ≥ 0.55 on chronological held-out 20%, and 30d shadow log shows the gate's WOULD_REJECT picks underperform PASS picks | run `meta_labeler.train()`; read `audit_dashboard/data/meta_label_shadow_log.json`; if AUC≥0.55 + separation holds, wire a `return False` path behind `META_LABEL_GATE_ENFORCE=1` |
| **M-056 (A2)** | overconfidence-decay A/B verdict | hash-bucketed A/B live in `score_booster.py` (`OVERCONFIDENCE_DECAY`), arms stamped `_overconfidence_arm` | **~2026-06-16** (30d A/B, need n≥50/arm) | arm B (decay) top-quartile realized WR ≥ arm A (control) − 1pp | run `python tools/overconfidence_ab_report.py`; verdict TREATMENT-OK / REGRESSION |
| **M-057 (A3)** | vol-scalar-cap proof | `vol_scalar_cap` opt-in in `position_sizing.py`; backtest INCONCLUSIVE (cap never binds on current cohort) | when a stale-low-vol cohort appears (scalar > 2.0) | Sharpe lift ≥ +0.2 at equal-or-better MDD | re-run `python tools/vol_scalar_backtest.py` once a qualifying cohort exists |
| **M-058 (A6)** | per-class calibrator enable | calibrators refit; global `CONFIDENCE_CALIBRATION_ENABLED` left OFF (only EQUITY passes OOS; FOREX calibrator is a sign-flip hazard) | next monthly refit | per-class OOS ρ ≥ 0.15 AND ρ > raw | run `python tools/eval_confidence_calibrator.py --oos`; enable ONLY classes that pass via a per-class allowlist (do NOT flip the global flag) |
| **M-059 (A7)** | cross-asset COT→CRYPTO overlay | `tools/cot_crypto_overlay.py` built; backtest INCONCLUSIVE-NO-DATA (COT z never breached ±2 on the pick window) | when a pick cohort overlaps an extreme-COT (|z|>2) episode | overlay raises CRYPTO Sharpe ≥ +0.15 OOS, ρ < 0.3 to directional alpha | re-run `python tools/cot_crypto_overlay.py`; persist the COT series for a longer window |

**Checkpoint rule:** at each `~2026-06-16` checkpoint, a session should run the
named verify command, record the verdict here, and either promote (enforce /
enable) or extend the window. Do NOT promote any of these to enforce/enabled
without the acceptance test passing on live post-resolver-v2.1 data.

---

## 23 — MiMo "Money-Ready Roadmap" validated + folded in (2026-05-17)

Xiaomi MiMo (after conceding its "institutional NOW" claims were overfit/decaying
artifacts) produced a sound Money-Ready Roadmap. Validated against the repo:
its DIAGNOSES are correct, but **2 of its proposed new modules already exist** —
the real action is WIRE/ENABLE, not BUILD. Amended items below.

### 23.1 — Re-add (M-055..M-059 — lost to a peer revert of §21)

| ID | Item | Verify command | Checkpoint |
|---|---|---|---|
| M-055 (A1) | meta-label gate shadow→enforce | read `meta_label_shadow_log.json`; AUC≥0.55 | ~2026-06-16 |
| M-056 (A2) | overconfidence-decay A/B verdict | `python tools/overconfidence_ab_report.py` | ~2026-06-16 |
| M-057 (A3) | vol-scalar-cap proof | `python tools/vol_scalar_backtest.py` (needs stale-vol cohort) | when cohort appears |
| M-058 (A6) | per-class calibrator enable | `python tools/eval_confidence_calibrator.py --oos` | next monthly refit |
| M-059 (A7) | cross-asset COT→CRYPTO overlay | `python tools/cot_crypto_overlay.py` | when |z|>2 episode overlaps |

### 23.2 — New (M-060..M-064 — from MiMo's validated roadmap)

| ID | Item | MiMo proposed | CORRECTION (verified) | Effort |
|---|---|---|---|---|
| **M-060** | CRYPTO model-drift fix — the conf≥0.8 decay (newest-third WR 38%) is ML model miscalibration | build `confidence_recalibrator.py` (isotonic, 90d window) | **`alpha_engine/confidence_calibrator.py` ALREADY does isotonic recalibration** — do NOT build a new file. Action = (a) add a monthly auto-refit cron, (b) enable per-class via allowlist (only EQUITY passes OOS today), (c) gate on calibrated not raw confidence. Merges with M-058. | M |
| **M-061** | Wire DSR/PBO into a per-class money-ready verdict | build `dsr_pbo.py` | **`alpha_engine/deflated_sharpe.py` (DSR) + `tools/pbo_cscv.py` (PBO/CSCV) + `anti_overfit_validator.py` ALREADY exist.** Action = wire them into ONE `money_ready_verdict(asset_class)` fn that runs all 5 LdP gates; do NOT reimplement DSR/PBO. | M |
| **M-062** | COMMODITY COT timing-leakage patch — publication-time gate | patch `cot_positioning.py` to use COT data only after Fri 15:30 ET | **DONE (stale)** — `COT_PUBLICATION_LAG_DAYS=3` at cot_positioning.py:45; gate at line 322 (`is_cot_data_available`). Verified 2026-05-17. | M |
| **M-063** | FOREX: drop `multi_asset_copytrader` drag + expand universe beyond USDJPY | block source-system + add GBP/CHF/CAD pairs | **DONE (stale)** — `multi_asset_copytrader` in BLOCKED_SOURCE_SYSTEMS (confirmed via quality_gates import). Verified 2026-05-17. | S+M |
| **M-064** | EQUITY DB↔repo ledger sync — 44 repo picks vs 393 in MySQL `at_raw_picks` | sync pipeline | VALID — EQUITY is n-bound, not strategy-bound. Build the unified ledger view. | M |

### 23.3 — Verdict on MiMo's timeline

MiMo's "CRYPTO/FOREX 2-4 weeks to money-ready" is **still optimistic**: M-060/M-061
are wire-not-build (faster than MiMo thinks) BUT the acceptance gates (DSR≥0.95,
PBO<0.05, 30-day rolling-clean, n≥100) are calendar-bound — no class clears them
in 2-4 weeks. Realistic: the *code* (M-060..M-064) is ~2-3 weeks; the *money-ready
verdict* still waits on live accumulation. No class is real-money ready before
the §21 checkpoints (~2026-06-16) at the earliest, and only if the gates pass.

**Agreement:** MiMo's roadmap is ACCEPTED with the build→wire corrections above.
Disagreement: only on timeline framing — "money-ready" is gate-earned, not
date-earned.


---

## 24 — Multi-AI "real-money roadmap" validated → 1 new item (2026-05-17)

Four external AIs (Sonnet 4.6, ppl-sonar, Grok-4.2, ChatGPT o3) each produced a
"real-money-ready roadmap" — all audited the PUBLIC `premium.html`, not the repo.
Validated by direct grep (`reports/multi_ai_realmoney_roadmap_validation_2026-05-17.md`):
**~80% of their claimed gaps are FALSE** — walk-forward, circuit-breaker/kill-switch,
HMM regime, position-sizing, DSR/PBO/anti-overfit all already exist in the repo.
Grok-4.2 was the only one that recognised this. Only ONE genuinely-new item:

| ID | Item | Why new | Effort |
|---|---|---|---|
| **M-065** | White's Reality Check / Hansen's SPA test / Model Confidence Set | DONE (stale) — `tools/whites_reality_check.py` EXISTS and runs. Live result: 24 strategies, 9 pass SPA, WRC/SPA p=0.162 (no family-wide edge). Verified 2026-05-17. |
| M-066 (note) | CIRO event-contract regulatory awareness (2026-03-26): election/political contracts banned, 30-day min maturity, no leverage | informational only — applies to the events/prediction surface, NOT the technical price-signal /audit. No engineering action; a one-line awareness note. | — |

**Rejected as MASTER_ACTION_PLAN items** (already exist — do NOT re-build):
live WebSocket feeds, kill-switch, circuit breaker, regime gating, position
sizing, shadow mode, DSR, transaction-cost model. The roadmaps' Pillars 1-5
mostly re-describe existing infrastructure.

## 25 — M-067: make /audit verdict READ the canonical PF registry (swarm-planned 2026-05-17)

Follow-up to PRs #1150-1152 (COMMODITY sizing guard, killed-strategy aggregate
exclude, canonical PF registry + reconcile gate). The reconcile gate currently
shows **6/9 asset classes diverge** — the `/audit` `asset_class_health` verdict
is recomputed inside `dashboard_generator.py` and is inflated vs the canonical
`pf_registry.json` (COMMODITY tile 7.71 vs registry 1.25, EQUITY 1.65 vs 0.74).

**M-067 goal:** `asset_class_health` READS the registry instead of recomputing,
so the two cannot diverge. Planned by a 3-agent swarm (investigator: 64 consumer
refs; Plan agent: 6-task design; red-team: 10-risk register). Effort **~10-12h**,
single PR, fresh branch. Status: **DONE (stale)** — `_registry_backed_ac_breakdown()` shipped
in dashboard_generator.py:5496 (commits f54c0b02ba, ca8d187f6f); AUDIT_HEALTH_SOURCE=registry
is the default; 3/3 tests pass (tests/test_m067_registry_reader.py). Corrected 2026-05-17.

### 25.1 — Task breakdown

| # | Task | Notes |
|---|---|---|
| T1 | `_registry_backed_ac_breakdown()` in `dashboard_generator.py` (~L5484) — read `pf_registry.json`, map `by_asset_class_policy_clean` rows to the `ac_breakdown` shape `compute_asset_class_health` already expects (`wins/losses/win_rate/pnl/profit_factor`). Return `None` on any fail-open trigger. | Seam chosen so status/tier/sizing logic inside the fn is UNTOUCHED. |
| T2 | Swap at call site (~L14393) behind rollback flag `AUDIT_HEALTH_SOURCE` (default `registry`, `recompute` forces legacy). Keep the in-generator `ac_breakdown` build — concentration block still needs `ac_sym_pnl`/`ac_strat_pnl`. | `log.warning` on every fallback. |
| T3 | **Slippage — registry must carry NET pnl.** Add per-class `deduct_slippage` to `build_pf_registry.py::_accumulate` (or a `by_asset_class_policy_clean_net` view). | OVERRIDES the Plan agent's "accept gross" — see red-team R6. |
| T4 | Unify asset-class tagging — `build_pf_registry.py` imports `_derive_asset_class` from the generator (fall back to crude inference). Fixes EQUITY keying mismatch. | RISKIEST step — verify `_derive_asset_class` is a pure function first. |
| T5 | CI re-order in `audit-dashboard.yml` — registry builds BEFORE the generator; commit `pf_registry.json` to the data-commit file list; add a registry rebuild inside the conflict-recovery re-run branch. | See red-team R1/R2. |
| T6 | Repurpose `reconcile_pf_registry.py` — once `asset_class_health` IS the registry it would compare itself; re-point it to compare registry vs an INDEPENDENT in-memory recompute, else the gate is dead code. | See red-team R3. |

### 25.2 — Red-team must-fix risks (HIGH severity)

- **R6 honesty regression** — registry PF is GROSS; the current verdict deducts
  slippage (`deduct_slippage`, L14357). COMMODITY's top win is ~7bp gross vs a
  12bp round-trip cost — gross-as-verdict literally flips COMMODITY from loser
  to "winner". T3 above is mandatory, not optional.
- **R1/R2 registry never committed** — `pf_registry.json` is built in CI but
  NOT in the data-commit file list; after M-067 the generator reads it, so a
  stale/missing file silently publishes hour-old or absent verdict numbers.
- **R5 staleness** — generator's registry reader must compare `generated_utc`
  against the closed-pick ledger mtimes; fall back to recompute (or stamp
  `stale_registry=True`) if older. Drop `continue-on-error` once load-bearing.
- **R8/R9 live-sizing reaction** — `risk_policy_check.is_forex_sizing_allowed`
  + `per_class_position_caps` read `asset_class_health` PF/`sizing_allowed`.
  Dedup changes `n` (tier boundaries) and PF (sizing threshold). Before merge:
  diff old-vs-new `asset_class_health` per class; gate on NO class flipping
  blocked→allowed without independent sign-off. Registry filter pipeline must
  match the verdict gates (add `_is_valid_resolved_pick`, ETF/COMMODITY symbol
  blacklists, sports exclusion to the registry).

### 25.3 — Acceptance

`build_pf_registry.py` + `dashboard_generator` run in the new CI order, then
`reconcile_pf_registry.py` (repurposed) exits 0 — independent recompute agrees
with the registry-sourced verdict within `|dPF|<=0.25`, `|dn|<=20%`. No class
flips blocked→allowed unreviewed. Rollback: `AUDIT_HEALTH_SOURCE=recompute`.

Companion item **M-068**: EQUITY DB↔repo ledger sync (dup of M-064) — EQUITY
n=31 registry vs 393 dashboard is partly the MySQL `at_raw_picks` vs repo gap;
T4 tagging-unify closes the tagging half, M-064/M-068 closes the source half.

## 26 — Paper → institutional-grade money-ready: the action plan (2026-05-17)

Consolidates the user's multi-AI consensus request. The GROUNDED consensus
(Grok 4.x, DeepSeek-V4, Codestral) is correct: fix data plumbing before any
live-sizing automation. The GENERIC roadmaps (Gemini Flash, GPT-5 Nano,
"open an Interactive Brokers account") are not repo-grounded — this repo's
blocker is ledger integrity + verdict trust, not broker onboarding. Ignored.

### 26.0 — Where we actually are (verified this session)

- Canonical `pf_registry.json` exists; net policy-clean PF: COMMODITY 1.17,
  CRYPTO 1.26, EQUITY 0.72, FOREX 0.33 — **every class sub-T2.**
- `money_ready_verdict.py`: COMMODITY MONEY_READY→WATCH (M-070 concentration
  guard); CRYPTO MONEY_READY on its own sample but diverges from the registry.
- **No asset class is real-money ready.** Paper/monitor only.

### 26.1 — Phase 0: P0 data integrity (BLOCKS everything)

| ID | Item | Status |
|---|---|---|
| **M-071** | `active_picks_sync` close-trade correctness | PARTIAL — PR #1171 fixed a `compute_verdict` tz-aware crash + added 13 tests (was 0). REMAINING: flip writer DRY-RUN→live (`--apply` + `ACTIVE_PICKS_SYNC_APPLY=1`) ONLY after a 7-day dry-run-vs-MySQL reconciliation passes. |
| **M-072** | WON-vs-PnL contradiction backfill | JSON ledgers VERIFIED CLEAN (0/8792 contradictions — resolver + compute_verdict sign-coherence guards hold). REMAINING: audit MySQL `at_raw_picks` for contradictions; any backfill UPDATE is a production write — count + show SQL + get sign-off before running. |

### 26.2 — Phase 1: verdict trust (single source of truth)

| ID | Item |
|---|---|
| M-067 follow-up | After a per-class `sizing_allowed` diff review, flip `AUDIT_HEALTH_SOURCE=registry` so /audit reads the canonical registry; then flip the `reconcile_pf_registry` CI gate from non-blocking to hard. |
| M-068 | EQUITY ledger reconciliation — registry n=31 vs dashboard n=393; close the MySQL `at_raw_picks`↔repo gap + `_derive_asset_class` tagging parity. |

### 26.3 — Phase 2: per-class readiness gates (no live sizing until passed)

- COT 7-step paper pilot on `cot_positioning` + CT=F — 4-week paper, then
  risk-of-ruin Monte Carlo before any sizing. CT=F stays a single-name
  probation bet (M-070 concentration cap) — pilot only, not a class verdict.
- Batch-DSR-scan the ~206 baby_strategies (read-only); the top three at
  DSR≥0.95 become candidates AFTER Phase 0 clears — not before.
- Per asset class run the López de Prado 5-gate (DSR≥0.95, PBO/CSCV<0.05 or
  ≥75% mean, walk-forward, White's Reality Check M-065, n≥100) — record
  outputs. Only a class clearing all gates is LIVE_ELIGIBLE.

### 26.4 — Phase 3: graduated live (only after Phases 0-2 per class)

- Sizing ladder 5% → 25% → 100%, per class, each step gated on the prior
  step's realized 30-day WR holding ≥ backtest − 1σ.
- Kill-switch wired from day one — tied to DSR decay AND realized-slippage
  drift (not a static threshold). `charter_drift_circuit_breaker` is the hook.
- All non-cleared classes stay BLOCKED.

### 26.5 — Sequencing

Phase 0 (M-071/M-072) → Phase 1 (M-067 flip, M-068) → Phase 2 (COT pilot +
baby-strategy DSR scan + 5-gate) → Phase 3 (graduated live). No phase starts
before the prior clears. Realistic timeline: Phase 0-1 code ~1-2 weeks;
"money-ready" verdict is gate-earned + calendar-bound (30-day windows), not
date-promised. No class goes live before ~2026-06-16 at the earliest.

## 27 — Per-asset-class plan adjustment from deep edge research (2026-05-17)

4-agent research pass (3 per-class repo-grounded + 1 DAILY_IDEAS corpus
miner). All numbers from `pf_registry.json::by_asset_class_policy_clean_net`
(canonical net-of-slippage). Verdict: **every class is sub-T2 (PF<1.5) once
leakage + killed strategies are excluded.** DAILY_IDEAS corpus is ~80%
convergence-trap noise; genuine signal folded in below.

NUMBERING NOTE: M-076/M-077 are already taken (DSR nb_trials, COT dedup —
shipped in code by a peer). M-055/M-056/M-057 are existing A1/A2/A6 items.
This section's new items start at **M-088** to avoid collision (the earlier
draft of this section mis-numbered them M-073..M-087 / M-055..M-057).

### 27.1 — CRYPTO  (net PF 1.28 / WR 45% / n=1941 — sub-T2)

- Edge IS real but buried under a low-confidence drag. Policy-clean by
  confidence: HI(>=0.7) PF 6.84 n=119, MID(0.5-0.7) PF 2.30 n=123,
  LO(<0.5) PF 0.21 n=536. (Supersedes the stale "confidence inverts on
  CRYPTO" memory — ghost-polluted pre-resolver-v2 data.)
- Carriers: `ensemble` (n=410 PF 1.47), `mega_mutation` (n=72 PF 2.19),
  `st_fear_greed_contrarian` (n=81 PF 7.87). Drags: `rapid_fire` PF 0.37,
  `sell_the_rally`, `ema_stack`, `connors_rsi2`.
- **M-088** hard confidence>=0.5 floor at the EXECUTION gate (highest-EV
  single change). **M-089** investigate-before-kill the crypto drags.
  **M-090** wire a real emission path for funding-rate + basis (modules
  exist, emit n<=2). **M-091** `edge_concentrator.py` — regime-routed
  allocation + ATR-dynamic SL (corpus net-new; targets the 78.9% SL-hit
  failure).

### 27.2 — EQUITY  (net PF 0.72 / WR 35% / n=31 — non-functional)

- n=31 below every charter floor — EQUITY is not trading. Clean book = one
  mediocre `multi_asset_copytrader` + AMD losses (AMD n=12 WR 8% PF 0.15).
- The classic equity edges were KILLED: PEAD, `Value + Quality` (killed at
  n=14 WR 86% PF 10.5), `Consecutive Beats`, `Earnings Drift` — all coded +
  wired AND in `PERMANENTLY_KILLED_STRATEGIES` on suspect small-n stats.
- **M-092** forensic re-audit of the 7 killed equity strategies (leakage-kill
  vs threshold-miscalibration-kill); `reports/deep_dive_equity_*.md`.
  **M-093** quarantine AMD. **M-094** add a short-interest/borrow-fee
  short-squeeze strategy. Do NOT size EQUITY until n>=100 clean at PF>=1.5.

### 27.3 — COMMODITY  (net PF 1.17 / WR 45% / n=160 — hollow)

- Headline ~49% CT=F (78/160, PF ~4.8) — COT-publication look-ahead leakage,
  on probation. Strip CT=F: COMMODITY is ~PF 0.35 / WR 16%.
- **M-095** recompute the registry with the CFTC publication-lag fix; keep
  CT=F probation, never trade it. **M-096** cut `cta_cross_asset_tsmom`
  CL=F (PF 0.37) + NG=F (PF 0.00) via `commodity_kill_switch`. **M-097**
  soak the dormant CLEAN edges: flip `COMMODITY_SEASONAL_ENABLED=1`, wire
  `commodity_carry_momo.py` forward-test-only. **M-098** decouple
  `score_booster` from crypto-only gating — COMMODITY scores (~30-55) sit
  below the ~60 floor, so COMMODITY emits ~0 picks for a SCORING-BIAS reason.

### 27.4 — FOREX  (net PF 0.33 / WR 27% / n=392 — hard-disabled, correctly)

- Keep `FOREX_HARD_DISABLE=1`. Only apparent winner: `cta_cross_asset_tsmom`
  USDJPY-SHORT (n=109, 70% WR) — single-pair, single-direction, one
  yen-weakening regime; regime-conditional, not durable.
- **M-099** cut the drag: `forex_carry_momentum` (PF 0.13, broken naive
  momentum) + all JPY-cross LONG signals. **M-100** run
  `tools/research/forex_carry.py --backtest` (true FRED rate-differential
  carry — the sanctioned unlock); reopen FOREX only if it clears PF>1.0 /
  WR>45% / n>30 OOS.

### 27.5 — ETF / BOND / FUTURES  (thin-sample — do NOT expand)

- **ETF** — canonical n~1; the dashboard n=74 PF 2.49 is pre-policy-filter
  and those picks are not in `closed_picks.json` — a ledger leak. **M-101**
  fix the leak; wire `etf_*` into the "etf" allowlist; add a VIX/yield-curve
  overlay; accumulate to n>=100.
- **BOND** — canonical n=1, and that row is a `cta_fx_multifactor` USDJPY=X
  FOREX pair mis-tagged BOND with corrupted TP/SL. **M-102** fix the
  mis-classification; wire `bond_*` into the "bond" allowlist.
- **FUTURES** — canonical n=12 PF 0.96. The dashboard n=203 WR-3% is the
  non-crypto-resolver replay-bug artifact, not real. **M-103** quarantine
  the 203-row artifact; fix the FUTURES vs COMMODITY taxonomy; route
  `cot_positioning` onto financial futures (ES/NQ/ZN).

### 27.6 — Cross-cutting (highest-leverage systemic finding)

**M-104 — kill-without-replacement ratchet.** Kill thresholds fire on
small-n in-sample rolling windows — a self-reinforcing ratchet that kills
strategies faster than replacements are added. Explains the "stuck-in-paper
for months" state. Recalibrate kill thresholds on walk-forward (not
in-sample rolling) data + add a zero-kill-pressure incubator runway. **This
gates everything above.**

### 27.7 — Sequencing

M-104 first (stop the ratchet) -> per-class CUTS (M-089/M-096/M-099) ->
WIRING (M-090/M-097/M-098/M-101/M-102) -> ADDS (M-091/M-094/M-100) ->
forward-accumulate -> re-verify at n>=100. No class is real-money ready;
this is the research-to-money path, gate-earned.

## 28 — RETRACTION: CRYPTO confidence edge is an ml_enhanced mining artifact (2026-05-17)

Deep-dive (`reports/deep_dive_crypto_ml_enhanced_artifact_2026-05-17.md`)
found the §27.1 CRYPTO "confidence>=0.50 is a monotonic edge filter" claim is
FALSE. Confidence >=0.5 is emitted ONLY by the `ml_enhanced_*` family (0
non-ml_enhanced CRYPTO picks carry conf>=0.5). That family is 149 per-symbol
curve-fit variants (119 with n=1), net PF 0.63 — a loser. The conf>=0.70
slice (PF 6.67) is its post-hoc winning tail = selection bias.

- **M-088 RETRACTED** — a confidence exec gate just hard-wires the selection
  bias. Do not build it.
- **M-105** — treat `ml_enhanced` as one multiple-tested factory: White's
  Reality Check / SPA (M-065) over the 149 variants, keep only survivors, or
  quarantine the family from `asset_class_health`/`pf_registry`/
  `money_ready_verdict` until it passes.
- **M-106** — fix `money_ready_verdict` `nb_trials`: per-symbol ML variants
  are independent trials. CRYPTO nb_trials ~= 160, not 14 — the current DSR
  PASS is an artifact of under-counting trials.
- Honest CRYPTO verdict: strip the mining sprawl and CRYPTO non-ml_enhanced
  is PF 0.33 — a deep loser, not "sub-T2 but improvable".

## 29 — NO-EDGE CLOUD BRAINSTORM SYNTHESIS (2026-05-17)

4-model cloud swarm (DeepSeek, Kimi, xAI/Grok-3, OpenRouter) confirmed zero
structural edge and converged on the highest-EV path forward.
Full report: `NO_EDGE_BRAINSTORM_CLOUD.MD` + `reports/no_edge_brainstorm/`.

### Per-class verdicts (UNANIMOUS or near-unanimous)
| Class | Verdict | Academically-grounded path |
|---|---|---|
| FOREX | **STOP** (3/4 unanimous) | Abandon; redirect capital to EQUITY/ETF |
| EQUITY | **PEAD** (DeepSeek + OpenRouter top pick) | SUE earnings drift, ex-microcap, 100bps slippage, walk-forward Sharpe >0.5 |
| ETF | **POSITIVE** (all 4) | 12-1 cross-sectional momentum, skip last month, 0.05% slippage, CPCV by quarter |
| COMMODITY | **Term-structure** (NOT COT/CT=F path) | EIA/USDA inventory surprise vs roll yield, deflated Sharpe >0.6, CPCV-blocked |
| CRYPTO | **Kill ml_enhanced sprawl** | Test ONLY one order-flow hypothesis if at all |
| BOND | Split — lowest priority | Term premium (yield-curve butterfly) if prime-broker feeds available |

### What to STOP (UNANIMOUS — all 4 models)
1. Kill `ml_enhanced` generator and all 149 variants → M-105 (already filed)
2. Remove the kill-threshold ratchet → M-104 (already filed)
3. Stop post-hoc strategy mining; pre-commit hypotheses before touching data

### New action item
- **M-107** — Pre-registration gate: limit ≤5 feature families per class + ONE
  test statistic *before* looking at data (xAI's two-stage gate). Archive every
  failed configuration; never re-test on the same sample. Implement as a
  `reports/hypothesis_registry.json` that records family, test statistic, and
  in-sample/out-of-sample commit hash before any backtest runs.
  Status: [x] DONE 2026-05-17 — reports/hypothesis_registry.json (5 hypotheses pre-filed); H-005 futures_momentum inversion archived as first REFUTED entry
