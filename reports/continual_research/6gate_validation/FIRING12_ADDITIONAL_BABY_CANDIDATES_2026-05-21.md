# Firing 12: Additional Baby Candidates Report (Further Mining)
**Date:** 2026-05-21  
**Subagent:** Grok (Firing 12 of 30m continual 6-gate research loop)  
**Focus:** Additional deep dive into `baby_strategies/` (remaining `*.meta.json` + non-`.meta` `.py` files beyond Firing 11's 5 selected + flagged "other") + `reports/hypothesis_registry.json` for any H- entries referencing under-tested families, liquidation, or baby-aligned technicals. Prioritize high-PF or liquidation-related not covered in Firing 11 (multi_timeframe_ema_cloud, moving_average_slope_momentum, rsi_pairs_arbitrage, logistic_microstructure, inverse_goldmine_stocks + copper_platinum_cot_momentum).  

**Builds directly on:**  
- `reports/continual_research/6gate_validation/FIRING11_BABY_STRATEGIES_90DAY_EXPANSION_2026-05-21.md` (F11's meta scan of 49 files, selected 5, "other" small-n CRYPTO flagged, EQUITY inverses + COMMODITY COT)  
- `reports/hypothesis_registry.json` (M-107 pre-regs; H-017 explicitly UNTESTED_DATA_GAP liquidation)  
- `updates/2026-05-21-continual-6gate-asset-class-research/index.html` (living report notes baby meta mining "pending", highlights H-017 as top #2 liquidation candidate)  
- Firing 10/11 hygiene/COT/expansion context + 6GATES_V1 (8 gates)  

**Output:** 3 additional candidates with prior evidence citations. Strongest (vt_pattern_sweep) gets full 6/8-gate run plan outline (M-107 first). A/B recs. All research-only, M-107 compliant path.

---

## 1. Mining Methodology & Scope (Beyond F11)
- Re-scanned all ~49 `baby_strategies/*.meta.json` (via glob + content keys: profit_factor, win_rate, total_trades, sharpe, status, promotion_note) + non-meta `.py` files for inline backtest summaries/docstrings (e.g. "Trades: N", "PF: X", "Backtest validation").
- Cross-checked `hypothesis_registry.json` for H- ids with "liquidation", "under-tested" (UNTESTED/DATA_GAP), "baby"/technical families (EMA/MTF/momentum/regime/pattern/slope), or alignment to F11-flagged gaps (small-n high-PF, liquidation, EQUITY patterns).
- Excluded: F11's explicit 5 + cross_sectional_crypto_carry (B_failed) + heavily killed (H-035 etc.) + 0-trade metas.
- Key new finds: Non-`.meta` `.py` with real evidence missed by F11 meta-centric scan; H-017 (liquidation family, registry only, not in F11 baby list).

**Gaps filled:** F11 living report "baby meta mining pending" + "H-017" callout now has concrete additional candidates + actionable plan.

---

## 2. Additional Promising Candidates (2-3 with Evidence)

### 2.1 vt_pattern_sweep.py (EQUITY) — Strongest overall (fresh deep-dive find)
**Prior evidence (inline in file, 5yr real yfinance backtest):**  
- Window: 2021-04 to 2026-04 (5yr)  
- Symbols: 13 (SPY, QQQ, XLK, XLF, XLE, XLV, XLY, AAPL, MSFT, NVDA, GOOGL, META, AMZN)  
- Trades: 245 (49 signals/yr universe-wide; ~1/week)  
- Sharpe: 0.747  
- PF: 1.479  
- WR: 50.2%  
- MaxDD: -18.1%  
- Return: +60.5% (CAGR +9.9%)  
- Avg hold: 6.4 days  
- Logic: Candlestick composite score (>=1.0 bullish from 15 patterns: hammer/engulfing/morning star etc.) + trend regime (close > SMA50 > SMA200) + mild pullback or strong breakout context + no bearish SMC (BOS/ChoCH+FVG) + harmonic XABCD PRZ filter. Long-only. ATR TP 3x / SL 1.5x. Optional smc lib for structural confirmation.  
- Citation: `baby_strategies/vt_pattern_sweep.py:8-37` (validation block), `:72-73` (class doc), `:234-239` (signal reason embeds 5yr stats). No `.meta.json` (missed F11 glob scan of 49 metas).  

**90day / hygiene fit:** Direct EQUITY T2 evidence-first + mutations/patterns per F11/90day plans. Benefits Firing 10 tagging hygiene (no crypto pollution in EQUITY slice). Under-tested (no H- pre-reg, absent from F11 selected 5 or B_failed). High n=245 excellent for G4 (WF) / G5 (MC) power vs small-n CRYPTO babies.

**Liquidation/high-conviction:** Not liquidation-named, but pattern + SMC confluence is high-conviction structural (Smart Money Concepts).

### 2.2 H-017 (funding_settlement_liquidation_cascade, CRYPTO) — Key liquidation-related H- entry
**Registry evidence:**  
- ID: H-017  
- Family: funding_settlement_liquidation_cascade (mechanical 8h UTC perp settlement fade: displacement >1.5x realized vol + funding top quartile → fade at settlement+1min, exit VWAP reversion or 30min stop).  
- Status: UNTESTED_DATA_GAP (pre-registered M-107 2026-05-18).  
- Result: Data gap (Binance free 1m klines ~1 day only; 0 qualifying events in short window). Ring 2.6 1T 2026-05-19: "confirmed different alpha from H-035" (H-035 killed for sign instability). Forward path: "Shadow implementation: run daily to collect cascade events. Re-test when n>=50 cascade trades accumulated (est. 2-3 months)." Implementation: `tools/h017_liquidation_cascade.py`.  
- Citation: `reports/hypothesis_registry.json:369-392` (full entry).  

**Relation to baby:** Directly extends F11-covered `liquidation_cascade_contrarian.py` (n=1, "entry conditions too strict", PF=999 noise, backtest_failed). H-017 is the formal under-tested pre-reg for the liquidation family (not listed as "candidate" in F11's 3-5 or "other"). Living report already flags as "Top candidate #2 — H-017 funding_settlement_liquidation_cascade".  

**90day fit:** CRYPTO liquidation/basis gaps noted in F11 living report. Post-guard (hygiene) + data collection path ready.

### 2.3 regime_sentinel_composite.py (CRYPTO) — Additional promoted high-PF from remaining metas
**Meta evidence:**  
- Status: ready_for_forward_test (promoted 2026-04-14 per TESTING_PROTOCOL Layer 6).  
- Backtest metrics: WR=0.5, Sharpe=3.7266, PF=2.5552, total_return=0.0522, total_trades=12.  
- Logic (from .py): Meta-regime filter combining F&G extremes, MVRV cycle, multi-SMA (50/200), RSI. Dual use: direct signals (fear/greed + oversold) + regime export for other strats. ACCUMULATION/MARKUP/DISTRIBUTION/MARKDOWN states.  
- Citation: `baby_strategies/regime_sentinel_composite.py.meta.json:2-16`, `.py:1-30` (header + regime states).  

**Why additional/not covered:** F11 noted it only in passing ("Other CRYPTO metas ... regime_sentinel PF=2.55 n=12 ... n too low for reliable G1-G6") but did not select it among the 5 or give run plan. Remaining meta with promotion evidence. MTF/regime family under-tested (no H- entry found for this exact composite).  

**Fit:** High Sharpe/PF (natural in CRYPTO per 6GATES), but n=12 limits (same as F11 small-n warning). Complements MTF EMA cloud (F11 #1).

---

## 3. Strongest Candidate + 6/8-Gate Harness Run Plan
**Strongest: vt_pattern_sweep.py (EQUITY)** — Best evidence (real 5yr n=245 >> small-n babies; PF 1.479 viable; fresh non-meta find; strong EQUITY 90day + post-F10 hygiene synergy; high-conviction pattern/SMC confluence; no prior F11 coverage or registry entry).

### 3.1 Run Outline (Post-Hygiene, M-107 First — Research Only)
1. **Registry Pre-Registration (mandatory M-107 before any re-backtest):**  
   Append to `reports/hypothesis_registry.json` (new H- for this family):  
   ```json
   {
     "id": "H-BABY-EQUITY-VT-PATTERN-SWEEP-001",
     "hypothesis": "Composite candlestick pattern score + SMA50/200 trend regime + SMC/harmonic structural filter delivers PF>1.4 / positive edge on liquid US mega-cap equities & sector ETFs (13 symbols) over multi-year holds.",
     "asset_class": "EQUITY",
     "strategy_name": "VTPatternSweepStrategy",
     "source_file": "baby_strategies/vt_pattern_sweep.py",
     "prior_evidence": {
       "backtest": {
         "period": "2021-04 to 2026-04 (5yr)",
         "n_trades": 245,
         "WR": 0.502,
         "PF": 1.479,
         "Sharpe": 0.747,
         "CAGR": 0.099,
         "MaxDD": -0.181,
         "symbols": 13,
         "source": "vibe-trading engine + yfinance"
       },
       "file": "baby_strategies/vt_pattern_sweep.py:8-37,72-73"
     },
     "pre_reg_date": "2026-05-21",
     "status": "pre-registered",
     "expected_gates": ["all 8 per 6GATES_V1 (relax G1 Sharpe>=0.7 for EQUITY per sparse notes)"],
     "tags": ["baby", "EQUITY", "pattern", "SMC", "harmonic", "firing12", "vt"]
   }
   ```
   (Follow hypothesis-registry skill + M-107 rule.)

2. **Backtest Refresh (hygiene-aware, post Firing 10 patch):**  
   ```bash
   # Adapt to baby harness or equity framework (ensure post-tagging hygiene: no crypto in EQUITY tags via FIRING10_CURRENT_POLLUTION_ANALYZER)
   python baby_strategies/backtest_framework_runner.py \
     --strategy vt_pattern_sweep \
     --symbols "SPY,QQQ,XLK,XLF,XLE,XLV,XLY,AAPL,MSFT,NVDA,GOOGL,META,AMZN" \
     --timeframe 1d --lookback 5y \
     --output backtest_results/firing12_vt_pattern_sweep_trades.json
   # Or integrate generate_signals() into tools/validate_resolved_picks or six_gate harness.
   # Capture: resolved picks with asset_class=EQUITY, direction, pnl, entry/exit.
   ```
   Verify hygiene: assert no ETH/BTC symbols in EQUITY slice.

3. **6/8-Gate Validation (core harnesses, EQUITY relaxations per 6GATES):**  
   ```bash
   python tools/validate_resolved_picks.py \
     --min-trades 20 \
     --by-asset-class EQUITY \
     --strategy-filter "vt_pattern_sweep|VTPatternSweep" \
     --input backtest_results/firing12_vt_pattern_sweep_trades.json \
     --output reports/continual_research/6gate_validation/firing12_vt_pattern_validate.json

   python tools/kimi_research_2026_05_20/six_gate_validated_strategy.py \
     --picks-file .../firing12_vt_pattern_validate.json \
     --asset-class EQUITY \
     --min-n 20 \
     --run-all-gates \
     --bootstrap-iters 1000 \
     --wf-windows 5 \
     --output reports/continual_research/6gate_validation/firing12_vt_pattern_8gate.json
   ```
   - G1 (Sharpe): target >=0.7 (EQUITY tolerance per F11/6GATES sparse data).  
   - G2 (p<0.05), G3 (CI>0), G5/G6 (MC), G7 (WR>40%), G8 (PF>1.0).  
   - G4 (WF>=50%): n=245 supports multiple windows well.  
   - Compare vs scrambled noise + post-cost (15-30bps roundtrip for equities).  
   - Explicit hygiene gate: pollution analyzer pre/post.

4. **Post-Run:** Update registry verdict + living report + Firing 12 section. If 6+/8 + edge_stability >50% + no regime leak: promote as EQUITY T2 sidecar or wire (0.5x sizing per similar inverses). Add to EQUITY 90day tracking. If fails: archive with rationale (B_failed).

**Adaptations:** Optional smc lib (graceful fallback per code). Long-only bias per 5yr bullish sample — test short filter if needed. 5yr evidence already strong prior; new run confirms on clean data.

---

## 4. A/B Placement Recommendations & Next Steps
**A_passed (proceed to wiring/shadow after gates + hygiene):**  
- **vt_pattern_sweep (EQUITY)** — If 6+/8 + WF stable: high-priority T2 evidence booster for EQUITY 90day (mutations/patterns). Strong n/PF/prior + hygiene synergy. Top rec for immediate pre-reg + run.  

**B_failed / refresh (needs work, more data, or small n):**  
- **H-017 (CRYPTO liquidation)** — B until n>=50 collected via daily shadow (`tools/h017_liquidation_cascade.py`). Then re-test with baby liquidation_cascade_contrarian relaxed variant. Synergistic with F11's attempt.  
- **regime_sentinel_composite (CRYPTO)** — B (small n=12 limits G4/G5 power per F11 flag). Aggregate as regime filter for other A candidates (e.g. multi_ema_cloud) rather than standalone. High PF/Sharpe interesting but under-powered.  
- Other remaining metas (vol_scaled_keltner PF~21 n=8, keltner_rsi n=3, price_roc variants 0 trades, prop_scalper/hoffman 0-2 signals): small-n or insufficient evidence; ignore for gates or relax/aggregate only. FOREX/COMMODITY rehab (e.g. xag_ensemble, forex_ensemble) cite prior high-PF on crypto but no own numeric — low priority.  

**90-Day Plan Expansions Enabled:**  
- **EQUITY:** Add vt_pattern_sweep + F11 inverses as pattern/mutation evidence (T2 push).  
- **CRYPTO:** H-017 + baby liquidation as dedicated liquidation family track (post-data collection); regime_sentinel as filter sidecar.  
- **General:** All benefit from F10/F11 hygiene (tagging patch + COT guard + backfill). Update living report + CYCLE_FIRING12_SUMMARY with this report link.  

**Citations (full):**  
- Firing 11 baby report (for "beyond 5" baseline + 90day refs).  
- `baby_strategies/vt_pattern_sweep.py` (primary evidence).  
- `reports/hypothesis_registry.json:369-392` (H-017).  
- `baby_strategies/regime_sentinel_composite.py*` + F11 "other" para.  
- `updates/2026-05-21-continual-6gate-asset-class-research/index.html` (H-017 + baby pending).  
- `6GATES_2026-05-21_V1_FREEBUFF.MD`, `FIRING11_POST_HYGIENE_EXECUTION_PLAYBOOK_2026-05-21.md`, `FIRING10_HYGIENE...`.  
- `PEER_RESEARCH_CANDIDATES_2026-04-20.md` (context for baby seeding).  

All work M-107 pre-reg compliant, cited, production-grade research. Loop continues to execution on A candidates post-hygiene.

**End of Firing 12 Additional Baby Report.**  
(Next: integrate into living report teaser + spawn execution subagent per playbook.)