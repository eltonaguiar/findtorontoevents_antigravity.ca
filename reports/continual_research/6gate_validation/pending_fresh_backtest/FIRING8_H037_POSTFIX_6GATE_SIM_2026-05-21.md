# Firing 8: Post-Fix 6/8-Gate Simulation on H-037 (ETF VIX Term Structure Carry) — 2026-05-21

**Task (subagent for 30m loop firing 8):** Perform post-fix 6/8-gate simulation on H-037 under the assumption that Firing 6/7/8 tagging hygiene patches (_infer_asset_class logic) are in place. Use registry backtest stats (n=1185, WR 58.9%, PF 1.295, WF eff 0.75, 3/4 folds admissible). Provide clear assessment, gates likely passed, additional work for real admission, wiring recommendations. Output structured section for direct addition to public research log or master baseline. All citations exhaustive.

**Status:** Proxy simulation only (no fresh validate run or resolved accrual for H-037; 0 entries in universal_resolved_picks.json as it remains OPT-IN RESEARCH SIDECAR). Analysis uses locked hypothesis_registry.json backtest evidence + framework logic + prior Firing 5 proxy + post-fix tagging assumptions from Firing 7/8 patches. Strengthens case vs Firing 5 sim now that ETF tagging + crypto hygiene is "in place" per task assumptions.

## Sources / Citations (Exhaustive)
- **hypothesis_registry.json:416-462**: Full H-037 entry (id, asset_class:"ETF", family:"vix_term_structure_carry", description of VIX futures contango/backwardation on 11 SPDR sector ETFs XLF/XLK/etc via free yfinance ^VIX/^VIX3M + CBOE futures; test_statistic walk_forward eff via edge_stability_harness.is_admissible(); acceptance_criteria eff_floor 0.3 / min_windows_admissible 3 / same_sign / cost_survival 0.6 / slippage 5bps; economic_prior Erb & Harvey/Koijen/Simon; status:"TESTED_WEAK"; registered_at:"2026-05-19"; ring_recommendation top free-data; result: backtest_status PASS, n:1185, wr:0.589, pf:1.2949, avg_win_pct:1.37, avg_loss_pct:1.517 (note loss>win mag), carry_spearman:-0.0955, walk_forward:{folds:[0.56962,0.54430,0.62869,0.56962], eff:0.75, mean_wr:0.578, admissible:true}, sample_window 2021-05-19 to 2026-05-11, verdict:"PASS — WR=58.9%, PF=1.295, n=1185, 3/4 walk-forward folds admissible. Contango regime favors long ETF basket 5-day hold.", notes on win-rate driven edge + live-shadow recs (10% Kelly when VIX<VIX3M; stop if live WR<52% after n=50); wiring:"OPT-IN RESEARCH SIDECAR"; tested_at:"2026-05-19".
- **reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING5_VALIDATION_ATTEMPT_H037_HYGIENE_2026-05-21.md**: Prior proxy 6/8 sim (G7 PASS 58.9%>40, G8 PASS 1.295>1, G4 PARTIAL-PASS eff0.75 3/4 admissible; G1 unknowable w/o daily-PnL+framework; 0 H-037 in resolved; blocked by tagging (90.8% EQUITY pollution) + no wiring/accrual; created this hygiene P0 proposal with exact cites (KIMI_RISEOFTHECLAW/signal_tracker.py, audit_trail/dashboard_generator.py:8282, audit_trail/quality_gates.py:5598 etc.); tools/validate_resolved_picks.py:59 OUTPUT_DIR hardcoded + arg mismatches.
- **reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md:42-43,20,49,56,60**: ETF section calls out H-037 as "Brand new unassessed... high potential pending tagging/accrual/full 6/8 on resolved"; Firing5 proxy sim details (G7/G8/WF partial; G1 unknown); "No named strategy passes full 6/8 gates on clean resolved data"; tagging bug 90.8% root cause; next firing prereqs include H-037 re-validate post-hygiene; public log link.
- **updates/2026-05-21-continual-6gate-asset-class-research/index.html** (multiple sections): Firing4/5 status on H-037 (proxy sim strong G7/G8/WF; needs wiring + daily PnL + tagging fix); ETF card blocked pre-fix; Research Log Firing4/5 entries cite hypothesis_registry H-037 + Firing5 sim; "T2-potential"; next actions shadow + accrue + re-run 6/8 post-hygiene.
- **6GATES_2026-05-21_V1_FREEBUFF.MD** (core methodology doc, referenced throughout e.g. 73-178/232-262 tagging root, 266-272 P0 recs, appendix on per-trade Sharpe inflation vs daily PnL, gate defs): Source of 6/8-gate framework (Sharpe, stat sig, WF, MC, FDR, WR, PF) + real resolved picks validation pipeline.
- **reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING7_TAGGING_HYGIENE_PR_SCOPE_2026-05-21.md + EQUITY_TAGGING_BUG_P0_FIX_PROPOSAL_2026-05-21.md + FIRING8_DASHBOARD_GENERATOR_PATCHED_REFERENCE_2026-05-21.py + FIRING7_DASHBOARD_GENERATOR_FIXED_REFERENCE_2026-05-21.py**: The Firing 6/7/8 patches — exact _infer_asset_class() implementation (crypto -USD/USDT patterns → CRYPTO; =X/forex pairs → FOREX; SPY/QQQ/XL* sector ETFs → ETF; else UNKNOWN fail-loud); replaces dashboard_generator.py:8254/8282 hardcoded "EQUITY"/"FOREX" defaults; scope for emitters/quality_gates backfill; post-fix assumption for this Firing 8 task (enables clean ETF labels for H-037 XLF/XLK/etc + unblocks overall EQUITY/ETF slices).
- **tools/validate_resolved_picks.py:58-59,77-100,306-311 (asset_class_breakdown),316-327,446,472-479**: Framework runner (imports statistical_validation_framework); per-trade _sharpe_from_trades (inflation caveat); --by-asset-class support; OUTPUT_DIR=reports/ (hygiene note); used for all real 6/8 runs (e.g. 27 validated in latest).
- **alpha_engine/statistical_validation_framework.py:162-164 (SHARPE_MIN=1.0, PVALUE_MAX=0.05, MAX_DRAWDOWN_MAX=0.20),196+ (BootstrapValidator), ~320 (MonteCarloStressTester passes_stress 5th>0), ~1045 (StrategyValidator.validate: checks sharpe_above_min, p_value_significant, max_dd, walk_forward_robust/consistency_score>=0.5, monte_carlo_passes, ci_lower_positive), 1092+ (batch + MTC/BH-FDR), 557 (daily_returns support)**: Core impl of G1-G6 (and FDR); daily path available but validate still defaults per-trade in some paths (prereq).
- **tools/edge_stability_harness.py:41-43 (EFF_MIN=0.30, MIN_WINDOW_N=80, MIN_STABLE_WINDOWS=3),164-197 (evaluate: admissible iff |eff|>=EFF_MIN same-sign in >=3 windows),277 (is_admissible)**: Matches H-037 registry WF criteria (eff 0.75 >>0.3, 3/4 admissible); used for score stability + cited in registry for H-037 test_statistic.
- **tools/h037_vix_carry.py (backtest harness), paper_trading/strategies/h037_vix_carry.py (live template), reports/h037_vix_carry_verdict_2026-05-20.md, reports/H037_CANONICAL_HARNESS_AUDIT_2026-05-19T2200Z.md, reports/h037-paper-trading-kimi-review-emergency-fixes-2026-05-20.md**: Implementation details, prior verdicts/audits, paper trading status (not yet prod wired).
- **Other prior markers**: FIRING4_TARGETED_3CANDIDATES_PLUS_NEW_2026-05-20.md, B_failed/targeted_candidates..._firing4_2026-05-20.md, LIGHTER..._FIRING3 etc (H-037 first mined as unassessed high-conviction; equity_vix sibling); A_passed/luxalgo_confluence_2026-05-21.md (example of full 8-gate passer format: "PF ~1.5, WR 42.2% ... passes BH-FDR + WF + Sharpe + p-value + WR>40% + PF>1.0").
- **Related code**: audit_trail/{universal_pick_resolver.py, quality_gates.py:5598 (EQUITY bonus), dashboard_generator.py:8282 (old default)}, KIMI_RISEOFTHECLAW/signal_tracker.py (emitter gaps), alpha_engine/config.py (ETF_SYMBOLS mentions).

All absolute paths + lines/sections for auditability. No new backtest executed this firing (data/hygiene still transitional per task; proxy on pre-registered locked registry evidence per M-107 spirit).

## 6/8-Gate Framework Definition (from 6GATES MD + framework + markers)
**Core 6-gate (statistical validation, framework-driven on returns series):**
- G1: Sharpe ≥ 1.0 (annualized; daily PnL path preferred over per-trade inflation in _sharpe_from_trades)
- G2: p-value < 0.05 (t-test or BootstrapValidator)
- G3: CI lower > 0 (bootstrap) + Max DD within limit (≤20% per MAX_DRAWDOWN_MAX)
- G4: Walk-forward robustness (consistency_score ≥0.5 or eff/admissible folds per edge_stability_harness or WalkForwardValidator; ≥3 stable windows)
- G5: Monte Carlo stress passes (passes_stress: 5th percentile Sharpe >0)
- G6: BH-FDR / MultipleTestingCorrector passes (q<0.05 after correction across batch; or equivalent MC crash test)

**Additional 2 for full 8-gate (real resolved picks emphasis):**
- G7: Win Rate >40% on resolved/CLOSED trades
- G8: Profit Factor >1.0

(Exact thresholds/criteria cross-validated from statistical_validation_framework.py constants + validate runs + A_passed/B_failed markers + Firing5 H-037 sim + 6GATES MD. Real admission requires clean resolved n≥20+ per strat slice + preferably daily series.)

## Post-Fix 6/8-Gate Proxy Simulation Assessment (H-037)
**Assumptions (per task):** 
- Firing 6/7/8 patches applied: _infer_asset_class() live in dashboard_generator.py (and emitters/quality_gates/resolver) → crypto no longer defaults to EQUITY; XL*/sector ETF symbols (XLF, XLK, XLE etc per H-037 universe) correctly → "ETF"; clean resolved data for ETF symbols.
- H-037 backtest stats (hypothesis_registry.json:436-458) serve as high-fidelity proxy for what wired + accrued resolved outcomes would produce (same free yfinance/CBOE VIX term data + 11-ETF basket logic; 5-20d horizons).
- No actual resolved picks or full framework re-run yet (0 H-037 attributions pre-wiring; sidecar only).

**Gate-by-Gate (proxy using n=1185 WR=58.9% PF=1.295 WF eff=0.75 3/4 admissible from registry; framework logic applied):**

- **G7 (Win Rate >40%):** **PASS** (58.9% >> 40%; robust sample; win-rate driven edge per registry notes "avg loss (+1.52%) > avg win (+1.37%)" — still strongly positive WR).
- **G8 (Profit Factor >1):** **PASS** (1.295 > 1.0; positive expectancy confirmed in backtest verdict "PASS").
- **G4 (Walk-Forward / stability / admissible):** **STRONG PASS on proxy** (eff=0.75 >> EFF_MIN=0.30; 3/4 folds admissible exactly matching MIN_STABLE_WINDOWS=3 + same_sign; mean_wr stable 57.8% across folds [56.96%, 54.43%, 62.87%, 56.96%]; aligns with edge_stability_harness.is_admissible() and registry "walk_forward eff ... admissible true"; framework consistency_score would likely clear ≥0.5). Best gate for H-037.
- **G1 (Sharpe ≥1.0 daily):** **UNKNOWN — REQUIRES FULL RUN** (No Sharpe reported in registry; prior sibling equity_vix baby 0.202 FAIL even inflated per-trade. Framework daily_returns path exists but H-037 backtest used per-rotation spread returns, not daily equity curve. Risk: WR-only asymmetric edge may deliver sub-1.0 risk-adjusted after costs/slippage 5bps. Per Firing5: "G1 unknown without daily-PnL + framework run".)
- **G2 (p<0.05 / bootstrap sig):** **LIKELY PASS** (n=1185 large over 5yr; 58.9% WR binomial p extremely low; positive PF + stable WF folds imply mean return >0 with tight CI. BootstrapValidator on accrued series would confirm; framework ready).
- **G3 (CI lower >0 + Max DD ≤20%):** **PARTIAL / UNKNOWN** (CI lower >0 likely from G2 power; Max DD unreported — VIX carry on diversified ETF basket expected low-DD in contango (economic prior: low-vol regime outperformance), but needs _max_drawdown_from_trades or daily curve on resolved. Framework would compute post-wiring.)
- **G5 (MC stress 5th pctile >0 / passes_stress):** **LIKELY PASS** (WF stability across 4 folds + large n + positive edge suggest path-independence; MonteCarloStressTester on its returns series would validate per framework).
- **G6 (BH-FDR / MTC passes):** **LIKELY / CONDITIONAL PASS** (Pre-registered single hypothesis per M-107 reduces multiple-testing burden vs data-mined; when batched in validate --by-asset-class on ETF slice post-accrual, MTC would evaluate q-value. Precedent: 6/27 strats including luxalgo passed full in recent run. Single-hypothesis power high.)

**Overall Post-Fix Proxy Verdict:** 
**T2 / Strong Potential for Admission (clears or likely clears 5-7/8 gates on evidence; G4/G7/G8 definitive on proxy; G2/G5/G6 probable; G1/G3 pending daily resolved framework application).** 

Better positioned than most B_failed lighter/ETF candidates (e.g. equity_vix_regime G1=0.202 FAIL + n=20 pollution pre-fix). Post-fix tagging removes the primary blocker (clean "ETF" labels + no CRYPTO pollution in aggregate data), making H-037 the highest-conviction un-wired ETF/ lighter-class seed. Matches/enhances Firing5 sim (now "post-fix" per Firing 8 context). Would promote to A_passed or SHADOW_LIVE upon real validation + wiring. Registry "TESTED_WEAK" + "PASS" verdict + Ring rec + free data + diversification value support fast-track shadow.

**Gates it would likely pass (post-fix assumption):** G4 (strong), G7, G8 (full/clear); G2, G5, G6 (high probability on framework application to clean series); G1/G3 (requires confirmation — primary remaining uncertainty).

**Gates needing real data/framework (not simulatable via registry proxy alone):** G1, G3 (daily PnL/equity curve for Sharpe/DD); full G2/G5/G6 batch context for precise p/q values.

## Additional Work Needed for Real Admission
1. **Apply/Verify Firing 6/7/8 Hygiene Patches:** Merge _infer_asset_class into audit_trail/dashboard_generator.py (replace 8254/8282), emitters (signal_tracker), quality_gates (remove 5598 EQUITY bonus), resolver (add ETF/crypto guards); one-time backfill ~198 polluted rows in universal_resolved_picks.json / at_raw_picks. Verify: re-run validate --by-asset-class shows clean ETF growth + CRYPTO correction (no -USD in EQUITY).
2. **Wiring + Consistent Emission (see Recommendations below):** Make H-037 emit attributed picks (strategy="h037_vix_term_structure_carry" or equiv) with asset_class="ETF" (or via _infer post-fix). Shadow/paper first.
3. **Accrual (30-60d+ or n≥50 resolved):** Run shadow (tv-paper-trade or integrated emitter) to populate real CLOSED/resolved outcomes with PnL_pct, dates, regimes. Target sufficient power for gates (n=20 min per validate, >> for WF/MC stability).
4. **Daily PnL Extension + Framework Run:** Ensure/ use daily equity curve attribution (framework supports; validate still leans per-trade — extend per Firing4/5 prereqs). Execute corrected validate_resolved_picks.py (fix OUTPUT_DIR:59 or add --output-dir for continual_research/6gate_validation/ target) --by-asset-class --min-trades 20 on post-accrual data. Full statistical_validation_framework + edge_stability on ETF/H-037 slice.
5. **Output + Documentation Hygiene:** Write results to continual_research/6gate_validation/ (A_passed/ or B_failed/ + new FIRING8 marker). Update hypothesis_registry.json (status e.g. "SHADOW_LIVE" or "ADMITTED", new "result" with real resolved stats, implementation_note).
6. **Create Promotion Marker:** If full 8/8 or 6+/8 on clean data: A_passed/h037_vix_term_carry_2026-05-21.md (format per luxalgo); else B_failed with gaps + prereqs. Tie to equity_vix candidate.
7. **Live Monitoring Setup:** Per registry notes: 10% Kelly shadow when VIX < VIX3M; kill if live WR <52% post n=50. Add regime tags for evaluate_by_regime.

Without steps 1-4 (especially wiring + accrual + daily), remains proxy-only (as in Firing5). Real admission = measurable proof on production resolved pipeline.

## Recommendations for Wiring H-037
- **Priority:** Highest among lighter/ETF seeds — free zero-cost data (yfinance + CBOE CSV), M-107 pre-reg, strong backtest (n=1185 power, WF admissible 3/4 eff=0.75, WR/PF positive), Ring 2.6 1T "top free-data" + "diversifies crypto/forex/commodity cluster" (vol-regime / carry signal orthogonal to funding/COT/momo), ETF basket (11 liquid SPDR sectors) matches existing lighter ETF work + equity_vix_regime_momentum sibling (VIX term structure family).
- **Wiring Pattern:** Start as OPT-IN RESEARCH SIDECAR (update registry wiring note). Template from paper_trading/strategies/h037_vix_carry.py + tools/h037_vix_carry.py backtest logic (contango: long ETF basket / sell vol; backwardation: reverse; 5-20d holds). Emit via existing ETF paths or new h037 emitter in audit_trail/alpha_engine. Use _infer_asset_class post-fix for XL* symbols → "ETF". Consistent strategy name for resolver attribution.
- **Integration Ties:** Bundle with equity_vix_regime_momentum / equity_vix_reversion (same VIX term logic); add as ETF overlay in etf_strategy_harness or alpha_engine/etf_strategies.py; cross-ref H-003 (ETF CS mom) for portfolio construction.
- **Safeguards:** Shadow-only until 30d+ real resolved + re-6/8 pass. Enforce pre-reg slippage 5bps + cost_survival 60%. Monitor carry_spearman decay. Per registry: live stop rule if WR<52% n=50. Add VIX contango/backwardation regime tag at emission for stability harness.
- **Risks/Caveats:** Asymmetric payoffs (loss size > win size — edge purely frequency); potential regime shifts (contango decay in vol spikes); low Spearman in backtest; ensure no leakage (free data timestamps ok per pre-reg). Post-wire: re-validate exactly on resolved (not backtest) to avoid M-107 violation.
- **Go-Live Path:** (1) Merge tagging patches. (2) Shadow wire + accrue. (3) Full 6/8 on clean ETF slice. (4) If pass: promote + small Kelly shadow live. (5) Update all logs/registry/public report.
- **If Admitted:** High value for diversification; low data cost; easy to monitor vs high-frequency CRYPTO. Cap volume initially.

**Firing 8 Summary:** Post-fix simulation (tagging patches assumed live) materially improves H-037 outlook vs Firing 5 — ETF slice now cleanly addressable. Proxy evidence supports admission-track (G4/G7/G8 + probable others). Immediate action: apply patches, wire shadow, accrue, full framework re-run targeting continual_research output. Highest-conviction pending ETF hypothesis.

**New Marker Created:** This file (`pending_fresh_backtest/FIRING8_H037_POSTFIX_6GATE_SIM_2026-05-21.md`).

**Recommended Updates:** Append equivalent structured section to `updates/2026-05-21-continual-6gate-asset-class-research/index.html` (new "Current Cycle (Firing 8)" Research Log subsection) + `reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md` (ETF / H-037 / Firing 8 summary para). Promote to A_passed or B_failed post real run.

*For continual loop task 019e490182df (Firing 8). All research-only, fully cited with absolute paths + lines. No data re-test on locked sample.*

## Structured Section for Direct Addition (Public Log or Baseline)
```
### Firing 8: Post-Fix 6/8-Gate Simulation — H-037 (ETF VIX Term Structure Carry) [2026-05-21]
**Proxy Assessment (hypothesis_registry.json:416-462 stats under Firing 6/7/8 _infer_asset_class() + clean ETF resolved assumptions):** 
- Likely passes: G4 (WF eff=0.75, 3/4 admissible — STRONG), G7 (WR 58.9% >40 — PASS), G8 (PF 1.295 >1 — PASS).
- Probable: G2 (sig), G5 (MC), G6 (FDR).
- Unknown/pending daily resolved framework: G1 (Sharpe), G3 (DD/CI).
**Overall:** T2 high-potential (5-7/8 likely); unblocks post-tagging hygiene (FIRING8_DASHBOARD...py _infer + ETF tagging for XL*); 0 resolved entries yet (sidecar). See full FIRING8_H037_POSTFIX_6GATE_SIM_2026-05-21.md + prior Firing5 marker for gate table, citations (6GATES MD, validate.py, statistical_validation_framework.py, edge_stability_harness.py:41-43, baseline:42-43, public log Firing4/5, h037_*.py + verdict md).
**Additional for admission:** Wiring (paper_trading/strategies/h037_vix_carry.py → emitter, asset_class=ETF), 30-60d accrual (real resolved n), daily PnL validate run (OUTPUT_DIR hygiene), full G1-6 on clean series, registry update, marker promote.
**Wiring rec:** Highest priority lighter/ETF seed (free data, Ring rec, WF strong, diversifies cluster). Shadow first; tie to equity_vix; opt-in sidecar; live kill if WR<52% n=50. Post-patch + accrue → re-6/8.
Cites: hypothesis_registry:416-462; FIRING5...H037_HYGIENE:23-30 (prior sim); FIRING7/8 tagging PR scope + patched ref ( _infer_asset_class); CONTINUAL...BASELINE:42; public log:162,185,192; 6GATES MD; framework + harness files.
```
(Insert under Research Log "Current Cycle (Firing 8)" or ETF section + baseline ETF para.)
```

*End of Firing 8 H-037 post-fix marker. Update logs/baseline + execute wiring/accrual next.*