---
title: "2-Month .MD Findings/Bugs/Enhancements Sweep — Incident-Ready"
date: 2026-06-10
mode: READ-ONLY (no edits/commits)
scope: canonical repo .md files with mtime >= 2026-04-10 (last ~60 days), worktree copies excluded
dedup: 5,399 recent .md (post worktree-exclude) → 5,215 unique by md5 (kept shortest-path per hash). Full corpus incl. worktrees was 41,512.
priority_families_read:
  - reports/2026-05-27_quick_wins_from_90day_plans.md
  - reports/2026-05-27_remaining_items_from_90day_plans.md
  - reports/90day_gap_analysis_2026-05-15.md
  - reports/SUPREME_PLAN_90days.md
  - reports/asset_class_90day_plan_*_2026-05-15.md (8 classes, referenced via gap analysis + remaining-items dedup)
  - reports/continual_research/6gate_validation/FIRING11_BABY_STRATEGIES_90DAY_EXPANSION_2026-05-21.md
  - DAILY_IDEAS.MD (tail), TESTING_PROTOCOL.MD
verification: each item grepped against current alpha_engine/ audit_trail/ tools/ .github/workflows/ + git log
skepticism: all quantitative WR/PF/n figures below are AS-CITED-IN-SOURCE (UNVERIFIED) unless a live reproducer exists.
---

# How to read this

Two operator examples set the bug-class: "cap on # of non-crypto picks" (now FIXED via per-class cap Option A) and "reverse-split stocks → bad data" (now handled via reverse_split_symbols registry). Both VERIFIED FIXED below — they anchor the FIXED column so the OPEN list can be trusted as genuinely-still-open.

Counts in this sweep: dedup 5,399 recent → 5,215 unique. Worktree duplication was already excluded by path filter (the 41,512→5,399 drop); content-dedup removed a further 184.

---

# OPEN items (file these) — ranked by impact on top-notch picks-per-class

| # | Item | Source | Type | Status | Evidence (grep/log) | Sev |
|---|---|---|---|---|---|---|
| O1 | **CRYPTO ADV/liquidity gate built but NOT wired into production gate path.** `is_liquid_crypto()` exists (`alpha_engine/asset_class.py:315`, $50M altcoin / $500M major thresholds) but its only callers are `tools/coingecko_adv_fetcher.py` + `tests/test_is_liquid_crypto_gate.py` — NOT `scanner.py`, `production_scanner.py`, or `quality_gates.py`. | gap_analysis (CRYPTO "UNADDRESSED"); quick_wins; remaining_items (CRYPTO + PENNY_MEME) | BUG (Wire-Up violation) | OPEN | `grep is_liquid_crypto` → 0 hits in production gate path; gate is dead-ended | P1 |
| O2 | **Cross-provider price reconciliation (A2) unbuilt.** No `data_quality=degraded` divergence flag; no ≥2-provider reconciliation anywhere. Directly affects pick price integrity per class (scale-corrupt history). | remaining_items A2 (P0); gap_analysis 2026-05-24 refresh | ENH/BUG | OPEN | `grep -inE 'price.?reconcil|cross.?provider|data_quality.?=.?degraded'` → 0 hits | P1 |
| O3 | **Lookahead-leakage guard is NOT a pipeline-failing CI gate (A4).** The `entry_ts < signal_ts` check lives only inside research/backtest tools (`tools/*backtest*`, `forward_signal_research.py`, etc.), not in any `.github/workflows/` gate. Production emission can still ship leakage. | remaining_items A4 (P0); gap_analysis 2026-05-24 | BUG | OPEN | `grep` in `.github/workflows/` for entry_ts/signal_ts/lookahead → 0 hits; only tool-level | P1 |
| O4 | **Golden-set regression in CI (G4) unbuilt.** No frozen golden hold-out / "lose >5% PF fails CI" workflow exists. Any emitter change can silently degrade per-class PF. | remaining_items G4; FIRING11 §G4 | ENH | OPEN | `grep -inE 'golden.?set|golden.?hold|frozen.?golden'` in workflows/tools → 0 hits | P2 |
| O5 | **FOREX `carry_yield_diff` is a HARDCODED snapshot, not live FRED rates.** `alpha_engine/config.py:683-695` carries static EUR/GBP/JPY/etc. differentials; `forex_strategies.py` reads them but never fetches FRED. Stale carry signal = wrong-direction FOREX picks. | gap_analysis (FOREX "UNADDRESSED"); remaining_items FOREX; quick_wins | BUG/ENH | OPEN | static dict in config.py; `grep -inE 'fred|fetch.*rate'` in forex_strategies.py → 0 hits | P2 |
| O6 | **FOREX uses price-z-score COT proxy, not real CFTC data (6E/6B/6J).** No real CFTC positioning ingest for FX. | gap_analysis (FOREX); remaining_items FOREX | ENH | OPEN | `cot_positioning_forex` is a proxy; no CFTC FX ingest module | P3 |
| O7 | **FOREX universe not limited to 4 majors for paper phase.** ~20 symbols incl. exotic drags still in universe. | gap_analysis (FOREX); remaining_items FOREX | ENH | OPEN | universe still broad in config | P3 |
| O8 | **COMMODITY single-symbol concentration (CT=F) not structurally diversified.** GC/NG/KC in config but production activity negligible; "73% PnL mass on CT=F" risk per plan. (Concentration-gate-before-DSR/SPA is the related open P0 noted in CLAUDE.md.) | SUPREME_PLAN; gap_analysis (COMMODITY); remaining_items | FINDING/ENH | OPEN | no cross-symbol emit logic across the 25-symbol set | P2 |
| O9 | **COT MATCH gate + DSR≥0.85 block (M-008) shipped but not wired.** `verify_system_pf.py` exists but is not called in `passes_active_gate`. | gap_analysis (COMMODITY M-008); remaining_items COMMODITY | BUG (Wire-Up) | OPEN | per plan; one-line wire never landed | P3 |
| O10 | **FRED_API_KEY economic layer partial.** Key is referenced by 9 workflows (bond-agent, etf-bond-scanner, fred-macro-refresh, etc.) so M-032 appears largely DONE, but BOND/ETF economic-momentum backtests in the plan were "BLOCKED by missing key" — needs confirm the secret is actually set in GH (cannot verify secrets from repo). | gap_analysis (BOND/ETF M-032); SUPREME_PLAN | ENH (verify) | OPEN-PENDING-VERIFY | `FRED_API_KEY` wired in workflows; secret-set status unverifiable here | P3 |
| O11 | **FUTURES↔COMMODITY tile merge + =F misclassification (conf_floor 0.50→0.40) undecided.** Two overlapping tiles; FUTURES produces ~0 quality picks. UI/dashboard + classification change. | gap_analysis (FUTURES); remaining_items FUTURES | FINDING/ENH | OPEN | recommendation never executed | P3 |
| O12 | **BOND research pilots (TIPS MR / curve carry / HYG-LQD credit MR) + TSMOM sidecar (M-024) + WF output (M-020) unbuilt.** n=11 unusable; no sizing path until n≥50. | gap_analysis (BOND); SUPREME_PLAN | ENH | OPEN | modules not created | P3 |

## Notes on the OPEN ranking
- O1–O4 are the highest-impact: they are **gate/CI integrity** gaps that let bad picks through across ALL classes, which is exactly the "top-notch picks per class" axis. O1 (ADV) and O3 (lookahead CI) are concrete Wire-Up-rule violations with a clear single-caller fix.
- O5–O9 are class-specific signal-quality gaps (FOREX carry staleness is the most actionable real edge item).
- O10–O12 are lower priority / verify-only / large-build.

---

# FIXED / SUPERSEDED (do NOT re-file) — verified against current code

| Item | Source | Status | Evidence |
|---|---|---|---|
| Per-class emission cap ("cap on non-crypto picks", Option A) | operator example; quick_wins; remaining_items | **FIXED** | commits `1fe266a660`, `43e86a32eb`, `c76aee18b2` (2026-06-09): per-class sized cap (EQUITY 15/d, others 8/d), forward_test_only bypass, class-normalized count; `alpha_engine/non_crypto_policy.py` + `scanner.py` |
| Reverse-split stocks → bad data (registry) | operator example | **FIXED** | `audit_trail/reverse_split_symbols.py` wired into `universal_pick_resolver.py`, `dashboard_generator.py`, `clean_ingest_v2.py`; commits `f47be5cee1` (GE 1-for-8), `22b2a4407a`, `f880b30117` |
| CRYPTO BTC UTC-hour death-zone filter (M-001 / QW-3) | gap_analysis; quick_wins; SUPREME_PLAN | **FIXED** | `alpha_engine/score_booster.py:538 _apply_crypto_hour_filter` + dedicated `alpha_engine/btc_hour_filter.py`; env kill-switch `CRYPTO_HOUR_FILTER` |
| FOREX_HARD_DISABLE env switch (M-007) | gap_analysis; quick_wins QA-3; remaining_items | **FIXED** | `alpha_engine/config.py:329 FOREX_HARD_DISABLE`; wired in `scanner.py:2606`, `risk_regime_validator.py:304`, `mysql_trading_sync.py:778`, `emit_gate_config.py` |
| CRYPTO on-chain momentum (MVRV-Z) module (QW-4) | quick_wins; gap_analysis | **FIXED (module exists)** | `alpha_engine/crypto_onchain_momentum.py` present (env-gated `CRYPTO_ONCHAIN_MOMENTUM_ENABLED`) |
| FOREX sizing_allowed PF<1.0 bypass bug | gap_analysis (P0) | **FIXED** | `dashboard_generator.py` PF<1.0 gate, commit `aebc51bb16` (per source) |
| PENNY_STOCK class-wide gate (QA-1) | gap_analysis; quick_wins | **FIXED (active, was pending-approval)** | `audit_trail/quality_gates.py:6828 passes_penny_meme_class_gate()` actively called in admission; kill-switch `PENNY_MEME_CLASS_GATE_ENABLED=0` |
| Speculative EQUITY quarantine (GME/AMC/NIO etc., the "remove 8 speculative tickers" item) | gap_analysis; remaining_items EQUITY | **FIXED** | `passes_speculative_equity_gate()` wired in `quality_gates.py` (EAGLE 2026-05-27), kill-switch `EQUITY_SPECULATIVE_GATE_ENABLED=0` |
| MEMECOIN class-wide quarantine (M-038) | gap_analysis; remaining_items | **FIXED** | `quality_gates.py:2713` MEMECOIN class-wide quarantine + `_PENNY_MEME_CLASSES` frozenset; routed through penny/meme gate |
| smart_score Platt/isotonic calibration (A3) | gap_analysis 2026-05-24; remaining_items | **FIXED/wired** | `alpha_engine/confidence_calibrator.py` + `model_calibration.py`; used in `production_scanner.py` + `smart_picks_engine.py`; `monthly-calibrator-refit.yml` |
| Per-pick freshness SLA at the gate (A1) | remaining_items A1 (P0); gap_analysis | **FIXED** | `quality_gates.py` MAX_AGE per class (lines ~1359, 4577-4581 suppress-on-stale) + `db-freshness-guardian.yml`, `asset-class-freshness-watchdog.yml` |
| Circuit-breaker (G2) | remaining_items G2 (P0) | **FIXED (portfolio-DD form)** | `alpha_engine/risk_controls.py:84 check_circuit_breaker` (-10%/-15% DD) + `fx_kill_switch.py`. NOTE: tied to portfolio DD, not literally "Stage-1 gate floor" — close enough to not re-file as P0, but a stricter Stage-1-floor breaker is arguably still missing (folded into O-considerations, low value). |
| Statistical kill-gate (M-055) | SUPREME_PLAN | **FIXED (module)** | `audit_trail/kill_gate.py` (min-n + binomial + Wilson CI); PR #1068 |
| ETF/EQUITY VIX-regime gate (QW-1/QW-2) | quick_wins; gap_analysis | **SUPERSEDED** | original `etf_sector_emitter.py` no longer exists; VIX logic now in dedicated strategy modules `equity_vix_regime_momentum.py`, `etf_vix_regime_rotation.py`, `fx_carry_vix_regime.py`, referenced by `eight_class_flagship_strategies.py` + `academic_strategies_emitter.py`. The specific "wire one line into etf_sector_emitter" task is obsolete. |
| BOND_ELITE_FLOOR 40→33 | gap_analysis (BOND) | **FIXED** | `bond-agent.yml` default `|| '33'` |
| per_source_volume_cap (quan_engine 5% / luxalgo 10%) | gap_analysis "completed this session" | **FIXED** | `per_source_volume_cap.py` + enforce_cap wired to production_scanner |
| FIRING11 baby-strategy candidates (EMA cloud, inverse_goldmine, copper COT, etc.) | FIRING11 | **N/A — research pipeline, not bugs** | These are forward-test candidates gated by hypothesis_registry (M-107), not defects. Several flagged as likely-lookahead (PF 6.95) pending A4 CI = depends on O3. Do not file as incidents. |

---

# Items deliberately NOT re-flagged (context says already done, per task brief)
PR2 entry-anchored resolver LIVE; signal-week dedup LIVE; scale-corrupt + sign-flip quarantine; credential scrub; copy_trader_intel re-blocked; stocks_rsi2_pullback / futures_momentum / forex_rsi2 / luxalgo / CRYPTO-direction-flip REFUTED; PBO 0.822; intrabar_truth live; profitable_filtered_observer wired; 0/9 classes money-ready (honest, by design — not a bug).

---

# Caveats
- All WR/PF/n figures in source files are AS-CITED and UNVERIFIED here (no DB query run; READ-ONLY sweep). Several are explicitly flagged stale/artifact in the sources themselves (e.g. COMMODITY PF 2.36 = pre-dedup over-emission artifact per `cot_paper_pilot_overemission_falsified_20260513.md`).
- O10 (FRED secret) and the Stage-1-floor breaker nuance under the circuit-breaker row cannot be confirmed from the repo alone (GH secrets / runtime).
- DAILY_IDEAS.MD (303KB) was skimmed at the tail only; its actionable items are the same per-class plan items already enumerated above plus brainstorm/no-do rules (not incident-grade).
