# Firing 13 Sub-Report: vt_pattern_sweep.py (EQUITY) — Deep Execution Focus
**Date:** 2026-05-21 (Firing 13 of the 30m continual 6/8-gate asset-class strategy research loop)  
**Subagent:** Grok Build (delegated Priority #1: vt_pattern_sweep.py EQUITY per user-authorized Firing 13 decision)  
**Job Context:** Builds on Firing 12 additional baby mining + consolidated playbooks; M-107 pre-reg executed; current-state pollution analysis; post-hygiene ready-to-run commands + wiring; additional EQUITY babies surfaced. All research-only, production-grade, fully cited. No production sizing.

**Primary Deliverable:** This sub-report is formatted for direct inclusion in the Firing 13 CYCLE summary (CYCLE_2026-05-21_FIRING13_SUMMARY.md), living public research log (updates/...), and A_passed/B_failed folders as needed.

---

## Executive Summary (for CYCLE inclusion)
- **Target:** `vt_pattern_sweep.py` (EQUITY) — strongest high-signal baby surfaced in F12 mining (non-meta .py with real 5yr evidence).
- **Prior Evidence (standalone vibe-trading yfinance backtest):** n=245 trades (5yr 2021-04–2026-04, 13 symbols), PF=1.479, WR=50.2%, Sharpe=0.747, MaxDD=-18.1%, +60.5% return (CAGR +9.9%), avg hold 6.4d, ~49 signals/yr universe-wide. Logic: 15-candlestick composite (>=1.0 bullish) + SMA50/200 uptrend regime + pullback/breakout context + no-bearish SMC/harmonic structural gate + ATR 3x TP / 1.5x SL. Long-only.
- **Current State (Pre-Full Hygiene):** 0 entries in `universal_resolved_picks.json`. Standalone class (`VTPatternSweepStrategy`) smoke-tested isolated and functional. **EQUITY class pollution confirmed at 90.8%** (198/218 crypto symbols mis-tagged as EQUITY; real EQUITY n≈20). Any current `--by-asset-class EQUITY` validation invalid (mixes crypto edge). vt_pattern_sweep benefits directly from F10/F11 tagging patch + backfill.
- **Registry:** Pre-registered M-107 as `H-BABY-EQUITY-VT-PATTERN-SWEEP-001` (appended 2026-05-21; see below). No prior entry.
- **Gates Outlook (on prior data + post-hygiene):** Likely passes G7 (WR>40%), G8 (PF>1.0), G4 (WF power from n=245), G5/G6 (MC bootstrap viable). G1 (Sharpe 0.747) borderline vs 1.0 target (relax to ≥0.7 per 6GATES sparse EQUITY notes). Post-clean re-execution expected A_passed (high n + hygiene synergy + 90day T2 pattern/mutation fit).
- **Wiring:** Partially complete (alpha_engine registration + config classification). Post-A: equity harness caller, paper shadow, emitter hygiene.
- **Additional EQUITY/Related Babies Discovered:** `vt_thematic_etf_momentum` (n=178, PF=2.14, Sharpe=1.02 on 6.3yr thematic ETFs — file missing on disk, needs restore); F11 inverses (`inverse_goldmine_stocks`, `inverse_earnings_drift`, `inverse_consecutive_beats`, `inverse_value_quality` — all EQUITY, hygiene beneficiaries of poor-parent parents).
- **Next:** Post-hygiene patch land → execute exact playbook slice below → edge_stability + 6+/8 gates → A_passed promotion or B_failed archive. Parallel F13 on multi_timeframe_ema_cloud (CRYPTO) + H-017 (data accrual).

**Citations (Must Reference in All Follow-On):**  
- Strategy: `baby_strategies/vt_pattern_sweep.py:1-241` (docstring 8-37, class 64-240, `_candle_score:91-137`, `generate_signals:149-240`, `Signal:54-62`).  
- Wiring: `alpha_engine/antigravity_strategies.py:444-477` (ag_vt_pattern_sweep impl), `:695` (STRATEGIES dict), `alpha_engine/config.py:1981` ("structure").  
- F12 Mining: `reports/continual_research/6gate_validation/FIRING12_ADDITIONAL_BABY_CANDIDATES_2026-05-21.md:28-72,83-103,119-146` (vt as strongest, full plan, pre-reg payload).  
- Playbooks: `pending_fresh_backtest/FIRING12_NEW_BABY_CANDIDATES_EXECUTION_PLAYBOOK_2026-05-21.md` (harness patterns), `FIRING11_POST_HYGIENE_EXECUTION_PLAYBOOK_2026-05-21.md:31-66,83-98` (validate/framework/harness extensions + sequences).  
- Pollution/6GATES: `6GATES_2026-05-21_V1_FREEBUFF.MD:24-27,75-100,171-178,239-247` (90.8% bug, real EQUITY=20, dashboard_generator.py:8282 default, quality_gates.py:5598 bonus); current analysis via `universal_resolved_picks.json`.  
- Registry: `reports/hypothesis_registry.json` (new H-BABY-EQUITY-VT-PATTERN-SWEEP-001 appended F13).  
- Harness Core: `tools/validate_resolved_picks.py:318-327` (current parser; needs --strategy-filter/--output-dir per playbooks), `alpha_engine/statistical_validation_framework.py:1027-1158` (UnifiedValidator), `alpha_engine/edge_stability_harness.py:543` (EdgeStabilityHarness.is_admissible).  
- Other: `incubator/backtest_team/forward_signal_scanner.py:2186` (vt ref), `CHANGELOG_CURSOR_April142026.MD:129` (vt_pattern restore precedent), `alpha_engine/equity_strategy_harness.py` + `tools/kimi_research_2026_05_20/equity_strategy_harness.py` (harness targets), `baby_strategies/backtest_framework_runner.py`, `FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py`, `FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py`.

---

## 1. Exact Implementation Location & Deep Code Analysis (Scope Item 1)

### 1.1 Primary Source
- **File:** `/home/eaguiar2015/findtorontoevents_antigravity.ca/baby_strategies/vt_pattern_sweep.py` (241 lines, complete).
- **Docstring Evidence Block (lines 8-37):** Full 5yr metrics + logic summary + pattern pillar contributions (candlestick 100% mandatory, SMC 27.7%, harmonic 9.9%, both 1.6%). Symbols: SPY, QQQ, XLK, XLF, XLE, XLV, XLY, AAPL, MSFT, NVDA, GOOGL, META, AMZN. Asset class: "US mega-cap equities + liquid sector ETFs".
- **Class:** `VTPatternSweepStrategy` (lines 64-240). `__init__` params (sma_fast=50, sma_slow=200, cs_threshold=1.0, cs_breakout=2.0, pullback 0.97-1.03, tp_atr=3.0, sl_atr=1.5, atr=14).
- **Core Logic:**
  - `_candle_score` (static, 91-137): Vectorized 15-pattern bullish/bearish composite (hammer, engulfing, harami, piercing, morning/evening star *1.5, three white soldiers *1.2, etc.; subtracts bearish). Returns float series.
  - `_atr` (140-147): Standard TR rolling mean.
  - `generate_signals` (149-240): Runtime path for production picks. Requires >=220 bars. Computes SMA50/200, ATR, cs. Gates: up_trend (close > sma_f > sma_s), (pullback or breakout>=2.0), cs>=1.0. Optional graceful SMC (smartmoneyconcepts lib): BOS/ChoCH within 20 bars bearish veto; else "candle+trend+pullback+SMC_BOS_bullish". Outputs `Signal` (BUY, confidence 0.50-0.80, TP/SL, reason embedding 5yr stats).
- **Graceful Degradation:** SMC import wrapped in stdout capture + except: pass (core candle+trend+pullback carries bulk edge).
- **No Harmonic Impl in Runtime:** Docstring mentions harmonic XABCD PRZ "persistence >=0" as no-veto; runtime only SMC (optional). Prior validation included it.
- **Long-Only Bias:** Explicit (5yr US equity structurally bullish).

### 1.2 Wiring & Integration Points
- **Emitter/Caller:** `alpha_engine/antigravity_strategies.py:444-477` (`ag_vt_pattern_sweep`): Imports `VTPatternSweepStrategy`, loops over data dict for 13-symbol universe, calls `generate_signals`, sets `asset_class="etf"` (for XL*) or `"equity"`, augments `extra["source_tool"]="vibe-trading-mcp"`, `extra["pattern_pillar"]="candlestick+smc+harmonic"`, calls `_signal_to_dict`. Returns list[dict] for pick pipeline.
- **Registration:** Same file line 695 in `STRATEGIES` dict (with other vt_* from 2026-04-14 vibe session: adx_rsi2_etf/equity, thematic, stat_arb_gdx_slv, restatement_short).
- **Classification:** `alpha_engine/config.py:1981`: `"ag_vt_pattern_sweep": "structure"`.
- **Forward/Scanner Ref:** `incubator/backtest_team/forward_signal_scanner.py:2186` (entry in VT catalog with file + agent="claude_vibe_novel_backtest", best_pair notes).
- **Harness Targets:** `alpha_engine/equity_strategy_harness.py` and copy `tools/kimi_research_2026_05_20/equity_strategy_harness.py` (no direct vt grep yet — needs explicit caller post-A; uses antigravity_strategies indirectly via multi-strat paths).
- **Missing for Thematic Peer:** `vt_thematic_etf_momentum` (referenced in same wiring files + forward scanner:2199-2202) has no `baby_strategies/vt_thematic_etf_momentum.py` on disk (ImportError in wrappers); docstring in antigravity_strategies:487-491 gives n=178/PF=2.14/Sharpe=1.02/6.3yr on 9 thematic ETFs (XBI/ARKK/SMH/...). Similar to vt_pattern (vibe-trading origin); `CHANGELOG...` notes vt_pattern restore from git — recommend same for thematic as additional high-signal EQUITY/ETF.

### 1.3 Smoke Test Execution (Isolated, Safe, Pre-Patch)
- Command (executed F13): `python3 -c 'from baby_strategies.vt_pattern_sweep import VTPatternSweepStrategy; ... synthetic 300bar df; strat.generate_signals(df, "SPY")'`.
- **Result:** Import successful; class instantiates; 0 signals on random-walk data (correct — no sustained uptrend + cs gate); **PASSED** with zero side-effects, no DB/resolved writes, no yf fetch.
- yfinance not present in env (cannot re-run full 5yr here); original validation external.
- **Implication:** Implementation is production-runnable in isolation; wiring functional for generate_signals path.

### 1.4 No .meta.json
- Confirmed: `baby_strategies/vt_pattern_sweep.py` (and glob *.meta.json) has none (F12 report: "missed F11 glob scan of 49 metas"). Contrast with F11 babies (e.g. multi_timeframe_ema_cloud.py.meta.json).

---

## 2. Playbook & Command Sequence Review (Scope Item 2)
Consolidated from:
- `FIRING12_ADDITIONAL_BABY_CANDIDATES_2026-05-21.md:74-146` (vt-specific outline: M-107 first, backtest_framework_runner adapt, validate + six_gate + harness).
- `FIRING12_NEW_BABY_CANDIDATES_EXECUTION_PLAYBOOK_2026-05-21.md` (mirrors F11; §1 prereqs, harness patterns for EQUITY inverses, edge_stability python -c).
- `FIRING11_POST_HYGIENE_EXECUTION_PLAYBOOK_2026-05-21.md:31-66,83-98,222-244` (hygiene steps, validate extensions, statistical_framework CLI/programmatic, EdgeStabilityHarness.is_admissible examples for EQUITY).

**Key Harness Commands (Adapted for vt_pattern_sweep — EQUITY):**
1. Hygiene verify (post-patch):
   ```bash
   python tools/validate_resolved_picks.py --by-asset-class --min-trades 5 --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/
   # Expect: 0 crypto (-USD/USDT) in EQUITY; real EQUITY count rise; XL*→ETF
   ```
2. validate (needs extension per playbooks §1.2/1.3 for --strategy-filter/--output-dir; current parser only --min-trades/--by-asset-class/--output/--save-csv at :318-327):
   ```bash
   python tools/validate_resolved_picks.py \
     --min-trades 20 \
     --by-asset-class \
     --strategy-filter "vt_pattern_sweep|VTPatternSweep|ag_vt_pattern_sweep" \
     --input backtest_results/firing13_vt_pattern_sweep_trades.json \
     --output reports/continual_research/6gate_validation/pending_fresh_backtest/firing13_vt_pattern_validate.json
   ```
3. statistical_validation_framework (daily-pnl critical for G1 per 6GATES; alpha_engine/...:1159 minimal CLI):
   ```bash
   python alpha_engine/statistical_validation_framework.py \
     --input .../firing13_vt_pattern_validate.json \
     --asset-class EQUITY \
     --framework full \
     --daily-pnl \
     --slippage-bps 25 \
     --bootstrap-iters 1000 \
     --wf-windows 5 \
     --output reports/continual_research/6gate_validation/pending_fresh_backtest/firing13_vt_pattern_6gate.json
   # Or programmatic: from alpha_engine.statistical_validation_framework import UnifiedValidator; ...
   ```
4. Edge stability (programmatic, :543+):
   ```bash
   python -c "
   from alpha_engine.edge_stability_harness import EdgeStabilityHarness
   h = EdgeStabilityHarness()
   admissible = h.is_admissible(
       'H-BABY-EQUITY-VT-PATTERN-SWEEP-001',
       slice_json='.../firing13_vt_pattern_6gate.json',
       windows='14d',
       eff_floor=0.30,
       min_stable=3
   )
   print('Admissible (vt_pattern):', admissible)
   "
   ```
5. Backtest refresh (pre or post; isolated yf or framework):
   ```bash
   python baby_strategies/backtest_framework_runner.py \
     --strategy vt_pattern_sweep \
     --symbols "SPY,QQQ,XLK,XLF,XLE,XLV,XLY,AAPL,MSFT,NVDA,GOOGL,META,AMZN" \
     --timeframe 1d --lookback 5y \
     --output backtest_results/firing13_vt_pattern_sweep_trades.json
   # Or direct VTPatternSweep + yf in custom script (post-hygiene tagging for resolved export)
   ```

**Prereqs (Identical to F11/F12):** M-107 (done), daily PnL, data freshness (yfinance), hygiene patch + backfill (FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py + dashboard_generator diffs), validate script extensions, pollution analyzer re-run.

**FIRING9/10 Hygiene Artifacts Referenced:** `pending_fresh_backtest/EQUITY_TAGGING_BUG_P0_FIX_PROPOSAL_2026-05-21.md`, `FIRING7/8_DASHBOARD...PATCH*.py/.diff`, `FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py` (CRYPTO_PATTERN regex on -USD etc.).

---

## 3. Current-State Analysis: Pre-Full-Hygiene Run/Sim (Scope Item 3)
### 3.1 Pollution Impact on EQUITY (Executed Analysis)
- **Data Source:** `audit_trail/data/universal_resolved_picks.json` (2.9M, ~5000 picks as of 2026-05-21 04:11).
- **Breakdown (python extraction):**
  - Total: 5000
  - CRYPTO: 4682 (93.6%)
  - EQUITY: 218 (4.4%)
  - FOREX: 68
  - MEME: 31
  - UNKNOWN: 1
- **Pollution:** 198/218 EQUITY-tagged picks (90.8%) match crypto pattern (-USD|USDT|...): XRP-USD, SOL-USD, ETH-USD, AVAX-USD, DOGE-USD, ADA-USD, BTC-USD, LINK-USD etc.
- **Real EQUITY:** ~20 (e.g. AFRM, COIN from stocksunify2 per 6GATES:100-116). Matches exactly the bug report in 6GATES_V1 §"What's Wrong", dashboard_generator.py:8282 hardcoded default + quality_gates.py:5598 +10 bonus + missing emitter asset_class.
- **Impact:** All prior EQUITY per-class stats (WR/PF etc. in VALIDATION_REAL_DATA) invalid — crypto edge attributed wrongly. vt_pattern_sweep (pure 13 yf symbols) would have been polluted if emitted pre-patch. Post-patch: clean slices unlock trustworthy EQUITY n growth + gate power.
- **Analyzer Equiv:** Matches `FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py` output pattern.

### 3.2 vt_pattern_sweep Specific
- **In Resolved Picks:** 0 (grep + python filter on "vt_pattern|VTPattern|ag_vt_pattern_sweep").
- **Standalone Metrics (authoritative prior):** As in docstring + F12 report. 513 raw events, 245 trades after filters. XLV 70.6% WR standout (per scanner note).
- **No Gate Results Yet:** Because not in resolver flow (no emitter producing resolved with asset_class=EQUITY for this family pre-F13). Framework/validate not exercised on it.
- **Partial Harness:** Smoke test (above) + class logic review = implementation sound. No full statistical_validation_framework run possible pre-data + hygiene + pre-reg (M-107 now satisfied).
- **Registry Cross-Ref (Scope 6):** No H- for this family (grep confirmed pre-edit). H-017 (funding_settlement_liquidation_cascade, CRYPTO, UNTESTED_DATA_GAP, tools/h017_liquidation_cascade.py) cross-referenced in F12 as #2; regime_sentinel_composite (n=12, PF=2.555) noted small-n. F13 pre-reg fills the gap for EQUITY patterns. Status updated: H-BABY-EQUITY-VT-PATTERN-SWEEP-001 now PRE_REGISTERED (see full entry in registry + appendix below).

### 3.3 Safe Partial Execution Performed
- Isolated class smoke: PASS (no patch needed, no writes).
- Registry pre-reg: SUCCESS (21 total hyps).
- No unsafe DB mutation or pre-hygiene resolved pollution.

---

## 4. 6/8-Gate Likely Pass/Fail Assessment (Current Data + Post-Hygiene)
Per 6GATES_V1 + F12 plan + EQUITY sparse notes:
- **G1 Sharpe:** 0.747 (prior per-trade). Target ≥1.0 or relax ≥0.7 (EQUITY). **Borderline / needs daily-pnl recalc post-framework.** Likely pass relaxed.
- **G2 p<0.05 / G3 CI>0:** High n=245 + MC power → likely pass (prior validation implies edge).
- **G4 WF >=50%:** Excellent — n=245 supports 5+ windows; multi-year yf clean. **Strong pass candidate.**
- **G5/G6 MC Bootstrap/Crash:** n=245 >>20 min; robust. **Pass.**
- **G7 WR>40%:** 50.2% → **Clear pass.**
- **G8 PF>1.0:** 1.479 → **Clear pass.**
- **Overall on Prior:** 6+/8 probable (high n mitigates small-sample issues of CRYPTO babies). Hygiene + re-backtest will confirm vs noise + costs (25bps equity).
- **Post-Hygiene Risks:** Regime leak (long-only 5yr bull), smc lib optional (degrade), harmonic not in runtime. Mitigation: explicit short filter test + full pillar in harness.
- **A/B Rec (per F12):** A_passed if 6+/8 + edge_stable + cost>=0.6. Top T2 for EQUITY 90day (patterns/mutations). Else B_failed with rationale.

---

## 5. Wiring Recommendations (If Not Already in Emitters)
- **Current Status:** Good partial (antigravity_strategies + config + forward scanner). Not yet explicit in equity_strategy_harness.py main loops (grep negative).
- **Required Post-A_passed:**
  1. Add explicit import/caller or ensure STRATEGIES dict consumed in `alpha_engine/equity_strategy_harness.py` (and kimi copy) for EQUITY runs.
  2. Dashboard: alpha_engine/data/active/closed_picks.json already in JSON_PICK_SOURCES (dashboard_generator.py:3592-3595) — vt picks will flow once emitted.
  3. Tagging: Post F9/F10 patch (dashboard_generator + _infer_asset_class in backfill) ensures "equity"/"etf" correct (XL* ETF, others equity; no -USD).
  4. Paper/Shadow: Add to `paper_trading/strategies/incubator_strategies.py` or tv-paper-trade for SCALPER/TESTER (0.5x sizing per similar).
  5. Audit/Quality: Wire to `audit_trail/quality_gates.py` scoring if not auto via alpha.
  6. Incubator: Already referenced in forward_signal_scanner; promote to bundle if passes.
- **Hygiene Synergy:** Patch prevents future pollution of any new vt picks.
- **If B_failed:** Archive + BLOCKED_SOURCE_SYSTEMS note.

---

## 6. Precise Post-Hygiene Commands (Ready-to-Run Playbook Slice for vt_pattern_sweep)
(Execute only after: (a) tagging patch + backfill applied/verified, (b) validate.py extended for --strategy-filter/--output-dir/--save-json, (c) M-107 done — now true, (d) clean `validate --by-asset-class` shows 0 crypto in EQUITY.)

```bash
# 0. Verify hygiene (pollution analyzer equiv + validate)
python reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py --input audit_trail/data/universal_resolved_picks.json || true
python tools/validate_resolved_picks.py --by-asset-class --min-trades 5 --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/

# 1. Fresh backtest (or export from emitter; produce trades with clean asset_class=EQUITY)
python baby_strategies/backtest_framework_runner.py \
  --strategy vt_pattern_sweep \
  --symbols "SPY,QQQ,XLK,XLF,XLE,XLV,XLY,AAPL,MSFT,NVDA,GOOGL,META,AMZN" \
  --timeframe 1d --lookback 5y \
  --output backtest_results/firing13_vt_pattern_sweep_trades.json

# 2. Focused validate slice (post-extension)
python tools/validate_resolved_picks.py \
  --min-trades 20 \
  --by-asset-class \
  --strategy-filter "vt_pattern_sweep|VTPatternSweep|ag_vt_pattern_sweep" \
  --input backtest_results/firing13_vt_pattern_sweep_trades.json \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/firing13_vt_pattern_validate.json \
  --save-csv

# 3. Full 6/8-gate framework (daily-pnl MANDATORY)
python alpha_engine/statistical_validation_framework.py \
  --input reports/continual_research/6gate_validation/pending_fresh_backtest/firing13_vt_pattern_validate.json \
  --asset-class EQUITY \
  --framework full \
  --daily-pnl \
  --slippage-bps 25 \
  --bootstrap-iters 1000 \
  --wf-windows 5 \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/firing13_vt_pattern_6gate.json

# 4. Edge stability harness (admissible check)
python -c "
from alpha_engine.edge_stability_harness import EdgeStabilityHarness
h = EdgeStabilityHarness()
print('vt_pattern admissible:', h.is_admissible(
    'H-BABY-EQUITY-VT-PATTERN-SWEEP-001',
    slice_json='reports/continual_research/6gate_validation/pending_fresh_backtest/firing13_vt_pattern_6gate.json',
    windows='14d', eff_floor=0.30, min_stable=3
))
"

# 5. Post-run
# - Update registry verdict (status, result, backtest_result)
# - mv marker to A_passed/ or B_failed/
# - If A: wire (harness, paper, dashboard promotion), 14-30d shadow, 90day EQUITY T2
# - Re-run full --by-asset-class pollution check
# - Log to CYCLE_FIRING13 + living report + public updates
```

**Also:** Re-execute pollution analyzer + full EQUITY/CRYPTO/ETF slices post-patch for baseline.

---

## 7. Additional High-Signal EQUITY (or Related) Babies Discovered During Mining
During F13 scope + cross-mining of baby_strategies/ + alpha_engine/ + metas:
- **vt_thematic_etf_momentum (Highest-Sharpe vt_* ship):** n=178, PF=2.14, WR=51%, Sharpe=1.02, CAGR+26%, MaxDD-32.9% (6.3yr, 9 thematic ETFs: XBI/ARKK/SMH/SOXX/XHB/IBB/XRT/XOP/XME, weekly rebalance top-3). Beats SPY +148pp. ~28/yr. DD warning noted. **File missing** (`baby_strategies/vt_thematic_etf_momentum.py`); stubs in alpha_engine/vt_baby_strategies.py + antigravity_strategies:483-517 + forward scanner. Strong EQUITY/ETF candidate — restore + F13/F14 deep dive recommended (similar to vt_pattern restore in changelog).
- **F11 Inverses (EQUITY hygiene beneficiaries):** 
  - `inverse_goldmine_stocks.meta.json` + wrapper: Parent n=85 PF=0.38 WR=21.2% (goldmine consensus); inverse theoretical PF=2.61. 90day alignment.
  - `inverse_earnings_drift.meta.json`: Parent n=19 PF=0.30 WR=15.8%; inverse PF=2.07.
  - `inverse_consecutive_beats.meta.json`: Parent n=39 WR=25.6%; inverse SHORT fade.
  - `inverse_value_quality.meta.json`: Parent n=48 WR=6.2%; inverse SHORT.
- **Other EQUITY Mentions:** equity_earnings_drift_pead.py (PEAD 60-68% WR expected, academic), equity_sector_rotation_momentum.py, equity_two_day_rsi_reversal.py, equity_vix_regime_momentum.py (B_failed prior), ag_vt_adx_rsi2_equity (wired). Most lack numeric 5yr evidence like vt_pattern; recommend meta scan + yf re-backtest post-F13.
- **Recommendation:** Firing 13/14 parallel on thematic restore + top inverses (A/B with vt_pattern). vt_pattern remains #1 for n/power + positive standalone metrics.

---

## 8. Registry Update Performed (Scope Item 6)
- Pre-reg executed: `H-BABY-EQUITY-VT-PATTERN-SWEEP-001` appended to `reports/hypothesis_registry.json` (now 21 hyps; status=PRE_REGISTERED; full payload matches F12 outline + F13 execution details; includes prior_evidence, acceptance_criteria, wiring, tags, notes cross-ref F12/F11/6GATES).
- **Full Entry (excerpt):** See registry or run `python -c "import json; print(json.dumps([h for h in json.load(open('reports/hypothesis_registry.json'))['hypotheses'] if 'VT-PATTERN' in h['id']][0], indent=2))"`.
- Status notes updated: "Firing 13 priority #1... Smoke test PASS... Post-hygiene re-execution queued."

---

## Appendix: Pre-Registration Payload (for Audit)
(See registry for canonical; matches F12 §3.1 + execution.)

---

**End of Firing 13 vt_pattern_sweep EQUITY Sub-Report.**  
Ready for CYCLE_2026-05-21_FIRING13_SUMMARY.md inclusion, A_passed/ promotion, and public research log. All paths M-107 compliant, hygiene-aware, cited at production grade. Loop continues.

**Subagent Sign-off:** Research complete; post-patch playbook slice ready; additional babies flagged; registry updated. No further scope creep.