# Firing 14 Sub-Report: EQUITY vt_pattern_sweep + Thematic Restore + Inverses Post-Patch Playbook Slice
**Date:** 2026-05-21 (Firing 14 of the 30m continual 6/8-gate asset-class strategy research loop)  
**Subagent:** Grok Build (delegated Primary Focus: EQUITY — vt_pattern_sweep + thematic restore + inverses prep for post-patch, building directly on F13 subagent #1 output)  
**Job Context:** Continues from F13 vt_pattern_sweep EQUITY sub-report (FIRING13_VT_PATTERN_SWEEP_EQUITY_SUBREPORT_2026-05-21.md). Hygiene patch (F9/F10 tagging + dashboard_generator + backfill _infer) assumed landed or ready for post-verify. All research-only, production-grade citations, M-107 compliant (H-BABY-EQUITY-VT-PATTERN-SWEEP-001 pre-reg in F13). No production sizing or live execution.

**Primary Deliverable:** This sub-report is formatted for direct inclusion in the Firing 14 CYCLE summary (CYCLE_2026-05-21_FIRING14_SUMMARY.md), living public research log (updates/...), A_passed/B_failed folders, and consolidated EQUITY playbook slices for F14/F15 execution.

---

## Executive Summary (for CYCLE inclusion)
- **Wiring Hygiene (antigravity_strategies.py primary):** Reviewed F13 partial wiring for `ag_vt_pattern_sweep` (hardcoded lowercase "etf"/"equity"). Completed for **clean emission**: added shared `_infer_asset_class()` (hygiene-grade, mirrors FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py exactly + adaptive_tp_sl coverage for thematic ETFs); updated `ag_vt_pattern_sweep` + `ag_vt_thematic_etf_momentum` to use it; explicit `d["asset_class"] = "ETF"|"EQUITY"` (UPPER) emitted for post-patch resolved_picks / validate --by-asset-class integrity. Also minor vt_baby_strategies.py thematic alignment. Consistent UPPER naming with _infer + no pollution vectors.
- **Thematic Restore (Scope #2):** High-signal `vt_thematic_etf_momentum.py` (n=178, PF=2.14, Sharpe=1.02, WR=51.1%, +148pp excess vs SPY, 6.3yr) **recovered from git history** (commit 7ca7f3d8a92 / vibe-trading session; referenced in antigravity_strategies:483+, vt_baby_strategies:114+, forward_signal_scanner:2199, config.py, CHANGELOG). File was missing on disk (ImportError in wrappers); reconstructed + enhanced with column normalization (robust to yf 'Close' vs 'close'), UNIVERSE export for vt_baby compat, full docstring preserved. **Isolated smoke test: PASSED** (synthetic data_map, 3 signals on random, no crash, import + rank + generate full path).
- **Additional EQUITY / Inverses Mined (Scope #3):** 
  - `vt_thematic_etf_momentum` (restored, highest-Sharpe vt_* ship, ETF/EQUITY hygiene beneficiary).
  - F11/F12 inverses family (all EQUITY, "awaiting_forward_test", wired_in_scanner=false in metas): `inverse_goldmine_stocks` (theo PF=2.61 from parent n=85 PF=0.38 WR=21.2%), `inverse_earnings_drift` (theo PF=2.07), `inverse_consecutive_beats`, `inverse_value_quality`. Benefit directly from post-patch clean EQUITY parents (no crypto bleed in goldmine/earnings closed trades). Use `baby_strategies/inverse_wrapper.py` + meta configs for transform.
  - Other EQUITY mentions (weaker numeric): equity_earnings_drift_pead.py (academic PEAD), equity_sector_rotation_momentum.py, equity_two_day_rsi_reversal.py, equity_vix_regime_momentum.py (prior B_failed). vt_pattern remains strongest for n=245 + positive standalone.
- **Post-Patch Playbook Slice:** Exact commands for 13-symbol vt_pattern_sweep universe (SPY/QQQ/XL*/AAPL/.../AMZN) + thematic (9 ETFs) + inverses prep. Ready after: (a) tagging patch + backfill verified (0 crypto in EQUITY via pollution_analyzer + validate --by-asset-class), (b) our wiring landed (asset_class emitted), (c) M-107 (done F13).
- **A/B Readiness:** vt_pattern_sweep: high-n (245), 6+/8 gates probable on prior (G7/G8 clear, G4 WF strong); post-clean re-run + daily-pnl + edge_stability → **A_passed candidate** for EQUITY T2 (patterns/mutations, 90d). Thematic: strong Sharpe but MaxDD -32.9% (exceeds baby gate; cap weight or B_failed with note). Inverses: theoretical high PF, require forward n≥20-50 via wrapper to confirm symmetry (A if confirmed_pf >1.5 else B). H-BABY-EQUITY-VT-PATTERN-SWEEP-001 cited for vt_pattern.
- **Citations:** F13 sub-report (full), FIRING9_TAGGING_BACKFILL..._2026-05-21.py:46 (_infer), alpha_engine/antigravity_strategies.py (post-edit), baby_strategies/vt_thematic... (new), hypothesis_registry.json (H- entry), FIRING12_ADDITIONAL_BABY... + NEW_BABY_PLAYBOOK, 6GATES_2026-05-21_V1_FREEBUFF.MD, forward_signal_scanner.py:2186+, inverse_*.meta.json files, CYCLE_FIRING13/14 summaries.

**Wiring Diffs / PR Scope (Minimal, Hygiene-Only):** 
- New: `baby_strategies/vt_thematic_etf_momentum.py` (126 lines, git-recovered + 10-line robustness patches for columns/UNIVERSE).
- Edited: `alpha_engine/antigravity_strategies.py` (+~55 LOC: _infer def + 2 wrapper updates for infer+map+asset_class emission; exact diff captured via `git diff`).
- Edited: `alpha_engine/vt_baby_strategies.py` (+5 LOC: thematic now emits asset_class via shared infer for parity).
- No behavior change to crypto paths; EQUITY/ETF only. No new deps. Smoke verified (pattern+thematic+infer+vt_baby all PASS on synth). Ready for small hygiene PR or direct merge to main before post-patch execution.

---

## 1. Wiring Status Review & Completion (Builds on F13 §1.2)
**Pre-F14 State (from F13 sub-report):** 
- `ag_vt_pattern_sweep` (antigravity_strategies:444-477): functional for generate_signals path, but hardcoded `asset_class = "etf" if ... else "equity"` (lowercase, per-symbol list). No explicit "asset_class" key. No _infer.
- `ag_vt_thematic...` (483-517): stub + broken API (called single-df generate_signals(df, symbol) but class expects data_map; ImportError pre-restore).
- Registration: STRATEGIES dict:695 (ok), config.py:1981 "structure" (ok), forward scanner + vt_baby (partial).
- Smoke (F13): isolated VTPatternSweepStrategy PASS.

**F14 Completion (Clean Emission via _infer + Consistent UPPER Naming):**
- Added `_infer_asset_class(symbol)` (lines ~104-148 in antigravity_strategies.py) — full hygiene logic from F9 backfill script (crypto markers + exempt, FOREX =X, COMMODITY =F, ETF explicit list including all 13+9 thematic, EQUITY alpha fallback). Returns UPPER ("ETF", "EQUITY", ... "UNKNOWN" fail-loud).
- Updated `ag_vt_pattern_sweep`: `ac = _infer_asset_class(sym)`; `category = ac.lower() if ...`; `d["asset_class"] = ac` (explicit emission).
- Updated `ag_vt_thematic_etf_momentum`: now builds `md` map (correct for rotation/rank logic), calls `generate_signals(md)` once, uses infer + emits "asset_class".
- vt_baby thematic: added try-import _infer + d["asset_class"] = ... (parity).
- Result: All EQUITY/ETF vt_* emissions now carry **asset_class via _infer** (UPPER, consistent with post-patch resolved_picks, validate --by-asset-class EQUITY, backfill, quality_gates). No more lowercase drift or hardcoded lists vulnerable to new symbols. Synthetic smoke: pattern (0 signals, correct), thematic (3 signals, asset_class=ETF), infer (SPY→ETF, AAPL→EQUITY, BTC-USD→CRYPTO) all PASS.

**Files Touched (Absolute Paths):**
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/antigravity_strategies.py`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/alpha_engine/vt_baby_strategies.py`
- `/home/eaguiar2015/findtorontoevents_antigravity.ca/baby_strategies/vt_thematic_etf_momentum.py` (new, restored)

**No other missing pieces for emission:** config/registration/STRATEGIES consumption unchanged; downstream (equity_strategy_harness, dashboard, paper) will now see clean tags once patch lands.

---

## 2. Thematic Restore Results (Scope Item 2)
**Recovery:** `git show 7ca7f3d8a92:baby_strategies/vt_thematic_etf_momentum.py` (present in vibe-trading commit tree that restored vt_pattern; never landed to working tree — hence missing on disk despite wrapper/docstring/forward refs/CHANGELOG:129 precedent).
- Full 126-line source recovered (docstring metrics + logic + class VTThematicETFMomentumStrategy + rank_universe + generate_signals(data_map) + Signal dataclass).
- **Enhancements for robustness (minimal, no logic change):** 
  - `UNIVERSE = SYMBOLS` export (vt_baby_strategies.py:116 `from ... import UNIVERSE` compat).
  - `_normalize_df()` helper + calls in rank/generate (handles yfinance 'Close'/'close' case-insens; mirrors vt_pattern_sweep.py:164 pattern).
- **Isolated Smoke Test (no yf, synthetic 100-bar data_map on XBI/ARKK/SMH):** Import OK, instantiate OK, generate_signals → 3 BUY signals (top-N on random walk), no exceptions, full path exercised. **PASSED 2026-05-21**.
- Wrapper now functional in both ag_ (map path) and vt_ (with asset_class emission).
- DD Warning preserved in extra (historical -32.9% > baby -25% gate; allocator cap required if promoted).

**Status:** File restored + wired clean. Ready for post-patch backtest (weekly rebal, 9 thematic universe) + 6/8 gates (high prior Sharpe suggests strong G1/G8).

---

## 3. Additional High-PF EQUITY Babies / Inverses Mined
- **vt_thematic...** (above): top priority for F14/F15 alongside vt_pattern (Sharpe 1.02 > vt_pattern 0.747; n=178 solid).
- **Inverses (F11/F12 EQUITY family, hygiene synergy):** All parent goldmine/earnings etc. are EQUITY-tagged in metas/closed_trades; post-patch will ensure no crypto pollution in forward parents → trustworthy inverse signals via `inverse_wrapper.transform()`.
  - inverse_goldmine_stocks.meta.json: parent n=85, WR 21.2%, PF 0.38; **inverse_theoretical_pf=2.61**, wr~78.8%; status=awaiting_forward_test, wired_in_scanner=false; config for flip_direction + tp_sl_from_parent.
  - inverse_earnings_drift.meta.json: parent n=19 PF=0.30 → theo inverse PF=2.07.
  - inverse_consecutive_beats.meta.json + inverse_value_quality.meta.json: similar SHORT fade on poor parents.
  - Implementation: `baby_strategies/inverse_wrapper.py:79+` (transform flips direction/prices, sets new_strategy_name, extra.inverted_from).
  - Playbook note: Run via equity harness or custom (load parent closed/resolved, transform, export with clean asset_class=EQUITY from parents).
- **Other:** equity_earnings_drift_pead.py (PEAD anomaly, academic 8-9% drift 60d, no 5yr numeric in header), equity_sector_rotation_momentum.py, etc. Lower priority vs vt_ numeric evidence.
- Recommendation (F14/F15): Parallel A/B on vt_pattern (n-power) + thematic (Sharpe) + 1-2 top inverses (goldmine first, wrapper + n=20 min forward). All benefit from F14 post-patch clean EQUITY slices.

---

## 4. Exact Post-Tagging-Patch Command Block (13-Symbol + Thematic + Inverses Prep for F14/F15)
Execute **only after**:
- Tagging hygiene patch + backfill applied/verified (FIRING9_TAGGING_BACKFILL_SCRIPT... + dashboard_generator diffs + EQUITY_TAGGING_BUG_P0_FIX...).
- `python reports/.../FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py ...` shows 0 crypto in EQUITY; validate --by-asset-class shows clean ~real EQUITY count.
- This wiring (our F14 edits) merged (asset_class emitted UPPER via _infer).
- M-107 pre-reg (H-BABY-EQUITY-VT-PATTERN-SWEEP-001 done F13; add for thematic if new hyp).

```bash
# 0. Hygiene verify (pollution + clean EQUITY slice) — MANDATORY first
python reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py --input audit_trail/data/universal_resolved_picks.json || true
python tools/validate_resolved_picks.py --by-asset-class --min-trades 5 --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/
# Expect: 0 crypto (-USD/USDT etc) tagged EQUITY; XL* / XBI/ARKK etc → ETF; AAPL etc → EQUITY; rising real EQUITY n.

# 1. Fresh backtest / emitter run for vt_pattern (13-symbol universe, 5yr yf or framework)
python baby_strategies/backtest_framework_runner.py \
  --strategy vt_pattern_sweep \
  --symbols "SPY,QQQ,XLK,XLF,XLE,XLV,XLY,AAPL,MSFT,NVDA,GOOGL,META,AMZN" \
  --timeframe 1d --lookback 5y \
  --output backtest_results/firing14_vt_pattern_sweep_trades.json

# (Optional thematic parallel; requires yf or custom runner for rotation)
# python ... --strategy vt_thematic_etf_momentum --symbols "XBI,ARKK,SMH,SOXX,XHB,IBB,XRT,XOP,XME" ...

# 2. Focused validate slice (post-validate.py extensions for --strategy-filter)
python tools/validate_resolved_picks.py \
  --min-trades 20 \
  --by-asset-class \
  --strategy-filter "vt_pattern_sweep|VTPatternSweep|ag_vt_pattern_sweep|vt_thematic|VTThematic" \
  --input backtest_results/firing14_vt_pattern_sweep_trades.json \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/firing14_vt_pattern_validate.json \
  --save-csv

# 3. Full 6/8-gate framework (daily-pnl MANDATORY per 6GATES + F13)
python alpha_engine/statistical_validation_framework.py \
  --input reports/continual_research/6gate_validation/pending_fresh_backtest/firing14_vt_pattern_validate.json \
  --asset-class EQUITY \
  --framework full \
  --daily-pnl \
  --slippage-bps 25 \
  --bootstrap-iters 1000 \
  --wf-windows 5 \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/firing14_vt_pattern_6gate.json

# 4. Edge stability harness (admissible per EdgeStabilityHarness:543)
python -c "
from alpha_engine.edge_stability_harness import EdgeStabilityHarness
h = EdgeStabilityHarness()
print('vt_pattern admissible:', h.is_admissible(
    'H-BABY-EQUITY-VT-PATTERN-SWEEP-001',
    slice_json='reports/continual_research/6gate_validation/pending_fresh_backtest/firing14_vt_pattern_6gate.json',
    windows='14d', eff_floor=0.30, min_stable=3
))
# Repeat/adapt for thematic (new H- if registered) + inverses (use wrapper-transformed slice)
"

# 5. Inverses prep (post-clean parents)
# python baby_strategies/inverse_wrapper.py ... (or harness integration) on goldmine/earnings closed picks
# Then validate --strategy-filter "inverse_goldmine|inverse_earnings" --by-asset-class EQUITY

# 6. Post-run
# - Update registry verdict(s) for H-BABY-EQUITY-VT-PATTERN-SWEEP-001 + new for thematic/inverses
# - mv to A_passed/ (if 6+/8 + admissible + cost>=0.6) or B_failed/ with rationale (e.g. thematic DD)
# - Wire further (paper_trading/strategies, equity_strategy_harness explicit, 14-30d shadow)
# - Re-run full pollution + EQUITY slice
# - Log to CYCLE_FIRING14 + 10_RUN_MILESTONE + public updates
```

**Inverses Forward Harness Note:** Use existing `alpha_engine/equity_strategy_harness.py` or `tools/kimi...` + inverse_wrapper on parent outputs; asset_class inherits from clean parents post-patch.

---

## 5. 6/8-Gate + A/B Assessment (Updated with F14 Wiring)
- vt_pattern_sweep: Unchanged from F13 (G7 50.2% clear, G8 1.479 clear, n=245 WF/MC strong, Sharpe 0.747 borderline-relaxed EQUITY). Now with clean emission: trustworthy re-execution post-patch. **A_passed if edge_stable + daily-pnl confirms.**
- Thematic: Prior metrics strong (Sharpe 1.02 highest vt_*); post-restore + clean tags unlock. **Risk: MaxDD -32.9% — recommend weight cap or B_failed if gate strict.**
- Inverses: Theoretical high PF from parent failure symmetry. **A if forward n>=20 confirms >1.5 PF / WR>50% else B (falsifies inverse hyp).**
- Overall EQUITY slice: Post-patch unlocks real power (previously 90.8% polluted). vt family + inverses = diversified T2 candidates for 90d EQUITY (vs crypto dominance).

---

## 6. Registry / M-107 Status
- H-BABY-EQUITY-VT-PATTERN-SWEEP-001: PRE_REGISTERED (F13, hypothesis_registry.json:738+); status notes include F14 wiring + restore. Ready for verdict post-commands.
- Recommend new H- entries for vt_thematic (or reuse) + one inverse (goldmine) before their runs.
- All citations production (paths, line nums, prior F11-13 reports).

---

**End of Firing 14 EQUITY vt + Thematic + Inverses Sub-Report.**  
Wiring complete for clean emission; thematic file restored + smoked; playbook slice copy-paste ready; additional babies mined with citations. Direct input for CYCLE_FIRING14, A/B decisions, F15 execution, and living 6gate reports. Loop continues.

**Subagent Sign-off:** Scope complete, no creep. All changes verified (smokes + imports + infer). Ready for user / F14 swarm integration. Absolute paths and git diff cited for audit.

**References (Key Files Updated/Used):**
- F13 base: reports/continual_research/6gate_validation/FIRING13_VT_PATTERN_SWEEP_EQUITY_SUBREPORT_2026-05-21.md
- Wiring: alpha_engine/antigravity_strategies.py (post F14 edit), vt_baby_strategies.py
- Restored: baby_strategies/vt_thematic_etf_momentum.py (git 7ca7f3d8a92 + F14 patches)
- Hygiene: reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py:46
- Inverses: baby_strategies/inverse_*.meta.json + inverse_wrapper.py
- Registry: reports/hypothesis_registry.json (H-BABY-EQUITY-VT-PATTERN-SWEEP-001)
- Commands adapted from: FIRING12_NEW_BABY_CANDIDATES_EXECUTION_PLAYBOOK_2026-05-21.md + F13 report §6 + F11 playbook
- Scanner: incubator/backtest_team/forward_signal_scanner.py:2199
- 6GATES: 6GATES_2026-05-21_V1_FREEBUFF.MD

**Git Status Note (for PR):** New untracked baby file + 2 edited alpha_engine/ files. Recommend `git add baby_strategies/vt_thematic_etf_momentum.py alpha_engine/antigravity_strategies.py alpha_engine/vt_baby_strategies.py` + hygiene commit message citing F14 + F9 backfill.