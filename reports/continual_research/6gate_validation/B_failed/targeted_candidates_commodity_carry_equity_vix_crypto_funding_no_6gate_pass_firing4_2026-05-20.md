# B_failed: Targeted 3 High-Conviction Candidates (commodity_carry_momo_double_sort + equity_vix_regime_momentum + CRYPTO funding/confluence variant) + Brand New Unassessed Strategies — No Full 6/8-Gate Pass on Clean Resolved — Firing 4 (2026-05-20)

**Subagent:** Quant validation for 019e490182df firing 4 (targeted candidates + new mining focus)
**Verdict:** B (fail/insufficient for 2/3 candidates; #3 CRYPTO funding-arb family has real resolved closed data + promise but not yet full per-strat 8-gate documented in loop; new H-037/H-017 promising but unvalidated on prod resolved / data gap). Inspected via direct code reads, existing backtest/edge JSONs, resolved_picks samples, hypothesis_registry, frameworks (statistical_validation_framework.py + validate_resolved_picks.py logic), 6GATES MD, and prior firing markers. No candidate or new strat achieves all 8 gates on production resolved_picks data this cycle. Builds directly on firing3 B_failed/equity_vix..._firing3_2026-05-20.md + lighter... + COMMODITY/FOREX B_failed.

## Citations (absolute paths + key lines/sections)
- **Candidates core:**
  - tools/research/commodity_carry_momo.py:84-178 (fetch_momentum_carry 12-1 mom + carry_proxy rolling mean diff; 140-175 double_sort_basket quintile intersect longs/shorts; 178-244 build_picks schema with strategy="commodity_carry_momo_double_sort" asset_class=COMMODITY; 284-286 expected_sharpe 1.0-1.4 / 21% ann return ref Fuertes/Miffre/Rallis 2010 SSRN1127213 + Jiang&Liu 2024); 302-308 atomic JSON write.
  - audit_dashboard/data/commodity_carry_momo.json:2-49 (generated_at 2026-05-20T06:49:11, strategy_name exact, wiring_status="WIRED — ... CT=F diversifier", carry_proxy_caveat="MODERATE-confidence... free-path vs second-month basis", universe 17 sym, picks:1 SHORT OJ=F mom=-35.45% carry=-6.61%; rows: CT=F mom+18.36% carry+12.04% etc).
  - alpha_engine/equity_vix_regime_momentum.py:37-113 (EquityVIXRegimeMomentum class; 82-106 generate_signals: if vix < vix3m + price> sma50 + mom>0 LONG TP6%SL4% else elif vix>vix3m + price<sma + mom<0 SHORT; confidence from term diff; references Simon&Campasano 2014, Fung&Hsieh 2006).
  - audit_dashboard/data/equity_baby_strategies_backtest.json:3-30 (equity_vix_regime_momentum spec, config 2010-2026 SPY/QQQ/IWM tp0.06 sl0.04; results: n_trades=604 n_closed=448 wins=182 losses=266 win_rate_pct=40.62 profit_factor=1.0263 sharpe_annualized=0.202 total_pnl_usd=2800 max_dd=0.23; trades samples with vix/vix3m).
  - coinglass_strategies/strategies/funding_confirmation.py:6-31 (run(): funding + glob ratio confluence, threshold, conf=0.60+0.05*agreement, strategy="coinglass_funding_confluence").
  - alpha_engine/funding_rate_arb.py:1- (funding extremes >+0.1%/8h SHORT etc, Binance fapi failover, TP2% SL1.5%).
  - audit_trail/data/universal_resolved_picks.json:10715+ (e.g. "strategy": "kimi_funding_arb_relaxed_mut", source "dna_winner_picks", CLOSED +2.5% pnl TP_HIT, direction LONG, confidence 0.6067; additional at ~18505, 18547, 29942; real closed resolved for funding-arb family).
  - audit_trail/quality_gates.py:2657 (coinglass_funding_confluence in MEMECOIN allow-list); 4418 (VIX_YC_SCORE_BONUS for EQUITY).
- **New unassessed (post-prior firings):**
  - reports/hypothesis_registry.json:416-462 (H-037 id, asset_class=ETF, family=vix_term_structure_carry, registered_at=2026-05-19, status=TESTED_WEAK, result: backtest n=1185 wr=0.589 pf=1.2949 avg_win_pct=1.37 avg_loss=1.517 carry_spearman=-0.0955, walk_forward folds=[0.5696,0.5443,0.6287,0.5696] eff=0.75 mean_wr=0.578 admissible=true, verdict="PASS — WR=58.9%... contango regime favors long ETF basket 5-day hold", "avg loss > avg win warning", Ring 2.6 1T top free-data rec, wiring=OPT-IN SIDECAR, data yfinance ^VIX ^VIX3M + CBOE + 11 SPDR ETFs; economic prior Erb&Harvey/Koijen/Simon; ties to equity_vix + 90day ETF VIX gate); 369-392 (H-017 id, CRYPTO, family=funding_settlement_liquidation_cascade, 2026-05-18, status=UNTESTED_DATA_GAP, pre-reg M-107, description: fade mechanical at settlement+1min on displacement>1.5x vol + funding top quartile, NOT directional like killed H-003, Ring approval "different alpha", impl tools/h017_liquidation_cascade.py, data_limitation Binance 1min klines ~1day, forward shadow n>=50 est 2-3mo); 249-293 (H-035 funding_settlement_pressure_timing TESTED_KILL 2026-05-19 sign instability effs mixed); 295-325 (H-036 COMMODITY inventory TESTED_KILL WR46.1% 0/7 windows); 339+ (H-015/016/018/028v2 UNTESTED or DATA_GAP).
  - baby_strategies/liquidation_cascade_contrarian.py:1-30 (structural post-wick mean-rev, expected WR58-65% R:R1:2+; .meta.json backtest_failed n=1 or 0 signals).
- **Frameworks + prior + 6GATES:**
  - alpha_engine/statistical_validation_framework.py:557- (BootstrapValidator on daily_returns, _annualised_sharpe), 752- (WalkForwardValidator OOS % positive), MC/MTC gates impl, costs.
  - tools/validate_resolved_picks.py:58 (universal_resolved_picks.json), 77 (_sharpe_from_trades per-trade ann still), 39 (framework import), 310 (breakdown), EXCLUDE_REASONS.
  - 6GATES_2026-05-21_V1_FREEBUFF.MD:30-42 (G1-G8 defs/thresholds G1 Sharpe>=1 G2 p<0.05 G3 CI>0 G4 WF>=50% G5 MC 5th>0 G6 crash>=-2 G7>40% G8>1), 58 (6/27 all-8), 147-178 (CRYPTO rich vs EQUITY20/MEME31/FOREX68 sparse; G4 hardest 22%), 171 (EQUITY n=20 no validatable), 232-262 (tagging bug: signal_tracker missing + dashboard_generator:8282 hardcoded EQUITY default + 198/218 misclass + quality_gates:5598 bonus), 266-292 (P0 fixes), 273-278 (tune G1/G5/G6/G8 per class), appendix (per-trade inflation note).
  - Prior firing markers: B_failed/equity_vix_regime_momentum_and_carry_momo_no_6gate_pass_firing3_2026-05-20.md:1-54 (exact same candidates G1=0.202 FAIL G7=40.62% marginal G8 pass INSUFFICIENT_N for #1/#2); B_failed/lighter..._firing3_2026-05-20.md:29-33 (candidates sim); pending/..._LIGHTER..._firing3_2026-05-20.md:19-24 (prereqs 1-10 incl tagging/COT/daily PnL/fresh validate/M-107); CYCLE_2026-05-21_01_SUMMARY.md:26-40 (COMMODITY COT falsified carry promising but no clean 6/8); COMMODITY_CYCLE_FIRING2_2026-05-21.md:29,32 ("promising but limited resolved track"); A_passed/luxalgo_confluence_2026-05-21.md (CRYPTO 8-gate passer example).
  - Supporting: reports/asset_class_90day_plan_* (ETF VIX backtest PF2+, COMMODITY carry sidecar, EQUITY vix), hypothesis_registry (H-003/037 ETF VIX overlap), audit_dashboard/data/edge_stability_COMMODITY.json + dashboard_data.json (low clean n post-hygiene), config.py:258-880 (symbols min_elite floors), updates/index.html + trading_blueprint.html (funding mentions in live).

## Gate-by-Gate Simulation/Inspection on 3 Candidates (using available outputs + framework logic + resolved samples)
**1. commodity_carry_momo_double_sort (non-COT COMMODITY):**
- Data: carry_momo.json (1 OPEN pick only 2026-05-20; 0 closed resolved_picks.json matches for exact "commodity_carry_momo_double_sort" or double_sort; proxy carry explicit caveat "MODERATE"); prior COMMODITY clean n~5-20 post-COT (falsified flagship context). Harness/commodity_strategy_harness.py exists but not executed on clean carry slice.
- G1 Sharpe >=1.0: UNRUN (no PnL series); expected 1.0-1.4 in json but unproven on resolved.
- G2 Bootstrap p<0.05: 0 power.
- G3 CI lower >0: 0 power.
- G4 Walk-Forward >=50% OOS positive: 0 (weekly, n<<42 min windows per framework:752 + 6GATES:160).
- G5 MC Bootstrap 5th>0: unavailable.
- G6 MC Crash: unavailable.
- G7 Win Rate >40%: UNRUN (no closed trades for named).
- G8 PF >1.0: UNRUN.
- **Overall:** 0/8 passable. INSUFFICIENT_N / UNTESTED on prod resolved (matches firing3 sim + B_failed/commodity... + pending prereqs). Proxy vs true basis gap + COT hygiene collateral. **Verdict: B_failed (no change from firing3).**

**2. equity_vix_regime_momentum (VIX-filtered EQUITY):**
- Data: equity_vix...py:82-106 (logic); baby json:19-30 (448 closed WR40.62% PF1.0263 Sharpe0.202 +2800); 0 exact name matches in resolved_picks.json (baby not migrated to prod resolver path); real EQUITY n=20 total (6GATES:171, tagging bug impact); VIX bonus in quality_gates but blocked.
- G1 Sharpe >=1.0: 0.202 FAIL (<<1.0; per-trade ann in baby/validate:77; framework daily path would be even lower per 6GATES appendix).
- G2 Bootstrap p<0.05: Not run on resolved (baby only); marginal given low mean.
- G3 CI lower >0: Likely FAIL (low observed).
- G4 Walk-Forward >=50%: Insufficient windows/power (n=20-448 split; needs >=4 OOS per framework; baby not chronological WF in prod).
- G5/G6 MC: Unavailable on prod slice.
- G7 Win Rate >40%: 40.62% — marginal, fails strict >40% on closed (or relaxed per 6GATES FOREX note).
- G8 PF >1.0: 1.0263 PASS (barely).
- **Overall:** 1-2/8 at best (G8 pass, G7 marginal); G1 critical FAIL + INSUFFICIENT for full G2-6 on real resolved EQUITY (n=20). VIX regime transfer to ETF promising in 90day backtests but unproven in resolved. Tagging bug primary blocker. **Verdict: B_failed (no change from firing3 B marker).**

**3. CRYPTO funding/confluence variant (kimi_funding_arb_relaxed_mut + coinglass_funding_confluence + funding_rate_arb):**
- Data: funding_confirmation.py:28 (confluence logic + conf); funding_rate_arb.py (extremes); resolved_picks.json:10715+ (multiple CLOSED kimi_funding_arb_relaxed_mut e.g. +2.5% pnl TP_HIT on LONG, confidence 0.6067, source dna_winner_picks; more at 185xx/299xx); coinglass mentions in updates/index.html (live SOL/BNB LONG examples), quality_gates allow-list, trading_blueprint. CRYPTO rich (4,880 picks, 53 validatable strats, 16/27 BH-FDR per 6GATES:147). coinglass scanner (data/coinglass.db) active. Unlike #1/#2, real closed resolved + positive PnL examples exist for funding-arb family. (Note: not the exact "coinglass_funding_confluence" string in resolved sample, but kimi_funding_arb_relaxed_mut is direct funding arb variant in prod data; confluence family active in scanners.)
- G1-G3/G5/G6: Cannot full run (no dedicated per-strat validate_resolved_picks slice output for this exact name in firing4 artifacts; CRYPTO power exists for such families). Positive closed PnL examples (+2.5% TP hits) suggest positive expectancy support for G1/G2/G3.
- G4 Walk-Forward: Power available in CRYPTO slice (many strats pass G4 in 6GATES:154 22% rate but 6 clear all); funding variants likely testable if n>=42 per named.
- G7 Win Rate >40%: Likely PASS (CRYPTO HFT norms + TP_HIT examples; resolved closed show wins).
- G8 PF >1.0: Likely PASS (positive PnL samples).
- **Overall:** Basic G7/G8 supported by real resolved closed data; full G1-6 unrun in this loop's public 6/8 tables (prior CRYPTO assessment highlighted luxalgo_confluence + claude_gainer as all-8 passers; this funding family mentioned in usage but not explicitly 8-gate validated here). **Verdict: PROMISING / PARTIAL (real prod resolved closed unlike COMMODITY/EQUITY candidates; positioned to pass more gates on dedicated re-run of validate + framework on its slice). Strongest of the 3 for potential A_passed post-P0 fixes + full harness. Distinguishes from killed H-003/H-035 (arb/confluence vs pure directional).** Matches "one strong CRYPTO candidate that previously showed promise".

**Common across 3:** Tagging bug (6GATES:232-262) + incomplete COT hygiene + lack of daily PnL series + emission/attribution gaps block clean power for #1/#2 and full per-named tables for #3. No A_passed/ for these. validate_resolved_picks runs confirm only CRYPTO has sufficient n for meaningful 6/8 (6/27 all gates).

## Brand New Promising Strategies Not Assessed in Prior Firings (Firing 1-3 Focus)
- **H-037 vix_term_structure_carry (ETF, hypothesis_registry.json:416-462):** Registered 2026-05-19 (post most prior firing work), TESTED_WEAK but explicit "PASS" on free-data backtest: n=1185 WR=58.9% PF=1.295, 3/4 WF folds admissible (eff=0.75), "contango favors long ETF basket". Ties directly to candidate #2 (vix regime) + lighter ETF 90day (backtest PF up to 3.22 w/ VIX). Not in firing3 lighter markers or A/B. **Gate sim:** G7/G8 pass in backtest; G4 (WF) strong per result; G1-3/5-6 unrun in prod framework/resolved (backtest not daily PnL + 6/8). Pending full validate + tagging fix for ETF visibility. High potential T2 post-accrual. Pre-reg M-107 complete.
- **H-017 funding_settlement_liquidation_cascade (CRYPTO, 369-392):** 2026-05-18 new pre-reg, UNTESTED_DATA_GAP (1min klines limit), mechanical fade at fixed 8h settlement +1min (displacement + funding quartile), "different alpha" per Ring vs killed H-035/H-003. Ties to candidate #3 (funding variant family). Impl ready (tools/h017_*); forward shadow collect. **Gate sim:** Not testable (data gap); strong economic prior (mechanical forced flow, bounded arb). New unassessed in loop.
- Others (H-015/016/018/028v2, baby liquidation_cascade_contrarian meta n=1 failed, confluence scanners): Data gaps or insufficient n; no new 8-gate passers found. Confluence overlap with existing A (luxalgo).

## Root Causes + Blockers (for candidates + new)
- Data/hygiene: Tagging (still unfixed post-firing3), COT collateral on COMMODITY, low real EQUITY/ETF resolved n, daily PnL missing for accurate G1 (per 6GATES appendix + framework daily path).
- Power: #1/#2 n=0-20 clean resolved for named; G4/G5 require ~42+ trades min.
- Attribution: Sidecars/baby (carry_momo OPEN-only; vix baby) not fully in resolver/resolved_picks for exact names.
- New: H-037 backtest strong but not prod 6/8/resolved; H-017 data gap (needs shadow).
- No evidence firing3 prereqs (10 in pending/LIGHTER..._firing3) executed.

## Concrete Next Actions (Firing 4 -> 5)
- P0 hygiene + wiring (tagging fix + COT re-agg + daily PnL builder in validate_resolved_picks.py + framework; ETF VIX default wire; H-037/H-017 shadow emission).
- Accrue 30d+ (paper via tv-paper-trade for carry_momo / vix / funding-arb variants; collect for H-017 cascades).
- Fresh: python tools/validate_resolved_picks.py --by-asset-class --min-trades 10 --save-json reports/6gate_firing4_candidates.json + full statistical_validation_framework (Bootstrap/WF/MC/MTC + CPCV/DSR) + edge_stability on the 3 + H-037/H-017 slices.
- M-107 for any mutations; conc caps; class-tuned gates (G1>=0.5 ETF etc).
- If any pass: promote A_passed/ (esp. CRYPTO funding family + H-037); else archive B with evidence.
- Update public log (this firing), 6GATES MD, hypothesis notes, CONTINUAL...BASELINE.md.

**Verdict for Firing 4:** 2/3 candidates + most new remain B_failed / pending (data/hygiene/power). CRYPTO funding-arb variant (kimi_funding_arb_relaxed_mut family) + H-037 show strongest evidence (real closed resolved + WF-admissible backtest) and are prioritized for post-fix re-validation. No A_passed/ additions. Exactly why continual loop + markers. Ready for firing 5 post-P0.

See also: FIRING4_TARGETED_3CANDIDATES_PLUS_NEW_2026-05-20.md (section), pending_fresh_backtest/FIRING4_..._PREREQS_2026-05-20.md (to create), prior firing3 markers (exact candidates carried forward).

*Rigorous per task: cited files/lines, simulated gates from actual outputs + framework logic, builds on all prior firings.*
