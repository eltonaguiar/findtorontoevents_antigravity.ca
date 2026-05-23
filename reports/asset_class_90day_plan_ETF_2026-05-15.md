# Asset Class 90-Day Plan — ETF — 2026-05-15

**Senior Quant Audit** using `money-maker-continual-improve` skill (7-step process).  
**Focus**: Current live performance (n=106, PF 1.48, WR 58.5% — now past charter floor) vs exceptional backtested sector-rotation + VIX-regime edge (PF 2.05→3.22 on 11y SPDR 11-sector momentum); data quality (yfinance + dedicated etf_strategies.py); whether sector rotation, VIX regime, or other ETF-specific edges (Faber TAA, Antonacci Dual Momentum, economic) justify targeted investment vs COMMODITY/EQUITY priority; realistic 0.1% pilot sizing recommendation.  
**Data sources**: `audit_dashboard/data/dashboard_data.json` (2026-05-15T02:06Z), `reports/MASTER_ACTION_PLAN_2026-05-15.md`, `reports/SUPREME_PLAN_90days.md`, `alpha_engine/etf_strategies.py`, `alpha_engine/config.py` (ETF_SYMBOLS + etf_sector_momentum weight), `tools/etf_sector_emitter.py`, `tools/etf_emitter_spike.py`, `audit_trail/vix_regime_gate.py`, `tools/backtest_etf_sector_rotation.py`, `tools/backtest_etf_rotation_vix_regime.py`, `tools/backtest_etf_sector_rotation_slippage.py`, `tools/backtest_etf_economic.py`, `reports/etf_vix_regime_breakthrough_20260513.md`, `reports/etf_sector_rotation_backtest_20260513T020800Z.md`, `reports/etf_abc_backtest_20260513.md`, `reports/backtest_etf_economic_2026_05_12_0615Z.md`, `reports/fix_ETF_20260505T005402Z.md`, `reports/audit_asset_feedback_2026-05-05T0121Z_ETF.md`, `reports/expanded_enhancement_plan_2026-05-14.md`, `reports/asset_class_research_EQUITY_2026_05_12_0438Z.md` (VIX transfer), recent etf_sector_picks.json.

**Current Charter context** (from CLAUDE.md / master plan / supreme): ETF borderline but improving (May-3: PF 1.24 / WR 55.2% / n=87; May-5 feedback: n=88 PF1.20; today: PF 1.48 / WR 58.5% / n=106 resolved, sizing_allowed=true, sample_tier=stable). M-023 `sector_dual_momentum_12_1` (Antonacci, 9 SPDR) PENDING; M-036 ETF universe expansion (XLF/XLE/XLK) to n→150 PENDING. ETF Pilot target 2026-06-01 **NEEDS-EVIDENCE-FIRST** — "n=87-107 just past floor; PF 1.24 below T2 by 0.26. Pilot acceptable but only at 0.1% per Rung-5 sizing." Per SUPREME_PLAN: tertiary track (parallel, lower effort), sector rotation + macro regime models; only scale post-COMMODITY success. T2 target: PF>1.5 / WR>50 / MDD<20 / n≥100. Backtests show clear path via existing code.

---

## Step 1: Establish Brutal Baseline (ETF)

**Live performance** (`dashboard_data.json::performance.asset_class_health.ETF` + `by_asset_class.ETF` + concentration):
- Resolved n=106 (closed:116, active:7) — just crossed charter min n=100 floor (was 87-88 May 3-5). Resolved_n=106.
- WR: 58.5% (wins 62 / losses 44 on closed).
- PF: 1.48 (by_asset_class), total_pnl_pct +50.59, expectancy +0.48 (positive), avg_win 2.52 / avg_loss 2.4.
- Sizing allowed: true; status: stable; circuit_breaker: cold_start (n=0<30 30d realized) but no breach.
- Concentration (OK tier, no warn/block): top_symbol XLE (Energy Select) 20.55% share / 53.74% of PnL mass; top_strategy "intermarket-flow-scout" 16.71% share / 43.69% PnL mass. honest_label: "ETF edge = intermarket-flow-scout on XLE (21% of class PnL)".
- vs prior: clear lift (PF +0.24, WR +3-5pp, n+19 since early May) — some cleanup + natural samples + possible new emissions.
- System context: EQUITY (1.57 PF / 51.9% WR / n=420), COMMODITY (2.49 / 61.5% / 322) lead; ETF now competitive on WR/PF with small n but far below their volume/edge maturity.

**ETF-specific edges in production vs backtest**:
- **Live drivers**: Mixed (intermarket-flow-scout dominant on XLE; some vt_baby_strategies vt_adx_rsi2_etf / vt_thematic_etf_momentum; etf_sector_momentum / etf_dual_momentum from etf_strategies). Emitter `etf_sector_emitter.py` (Faber) last ran 2026-05-15T01:12Z but produced **0 picks** (no sectors above 200d SMA with positive 3m momo today).
- **Backtest-proven (Tier-2 / near Tier-1)**: 
  - `tools/backtest_etf_sector_rotation.py` (11y 2015-05-13, 122 monthly periods, 11 SPDR sectors XLK/XLE/XLF/XLV/XLI/XLY/XLP/XLU/XLB/XLRE/XLC, 12-1m momentum top-3 equal-weight long-only): PF **2.05**, WR **70.49%**, Sharpe ann. **0.97**, MDD 16.10%, total +283.71% (beats SPY ~3x window). Tier-2 confirmed (PF>1.5/WR>50/n=100/MDD<20); Tier-1 candidate (MDD 1.8pp short of ≤10%).
  - VIX overlay (`backtest_etf_rotation_vix_regime.py` + `etf_vix_regime_breakthrough_20260513.md`): VIX<25 gate (skip ~16% high-vol months): PF **3.22**, Sharpe **1.63**, MDD **11.8%**, n=102 periods, total +395% (vs baseline +284%). **Tier-1 PF + Sharpe; Tier-2 MDD + n**. VIX<22: PF3.91 / Sharpe1.93 / MDD8.1% n=88. Pattern transfers exactly from EQUITY VIX success (second class with this result).
  - Friction robustness (`backtest_etf_sector_rotation_slippage.py`): realistic 2.5bp total/leg (monthly rebalance ~6 trades/mo): PF 2.03 (naive 2.05); even 10bp stress PF1.99. Edge survives costs.
  - Long-short (top3/bottom3): PF 0.937 / negative Sharpe — **REJECT** (bottom sectors mean-revert in recoveries; long-only correct form).
  - Black-Litterman (PyPortfolioOpt): failed (LinAlgError on rolling cov) — deferred (needs Ledoit-Wolf + ridge).
- **Code assets**: `alpha_engine/etf_strategies.py` (etf_dual_momentum Antonacci absolute+relative 12m; etf_sector_momentum Faber 10mo SMA + 3m momo + ADX; tailored _etf_tp_sl ATR 2.5/1.5 capped 10%/6% for baskets); `config.py:ETF_SYMBOLS` (19+ liquid names incl full 11 sectors + SPY/QQQ/IWM/GLD/SLV/SMH/ARKK/EEM/EFA/VNQ/DBC + recent expansions); `etf_sector_emitter.py` (yfinance 13mo OHLCV, normalizes to pick schema, opt-in sidecar wire-up, ETF_SECTOR_EMITTER_ENABLED flag); `vix_regime_gate.py` (already covers asset_class ETF + EQUITY; YC too); `quality_gates.py` references etf_sector_momentum.
- Other attempted: `backtest_etf_economic_2026_05_12_0615Z.md` — **DATA_GAP** (no FRED key, yfinance proxy failed). Economic momentum not yet live.

**Data quality assessment**:
- **Strengths**: yfinance (free, auto_adjust=True, clean for liquid ETFs); dedicated module with academic citations (Faber 2007 TAA, Antonacci 2014 Dual Momentum); recent fixes (2026-05-14 MMR audit in etf_strategies.py for TLT/HYG BOND_SYMBOLS union + wanted filter — fixed prior 5-sector drop); ATR risk model ETF-specific; emitter + backtest tools mature; resolver-v2 noise filter applied; concentration OK (no block); n now meets floor with positive expectancy.
- **Weaknesses**: Small live n=106 (noisy stats, cold_start 30d); emitter 0 picks today (regime-dependent — sectors not all above SMA); XLE/energy concentration (sector bias risk, though rotation should mitigate); live edge currently "intermarket-flow-scout" (generic? not pure rotation — dilutes vs backtest purity); FRED economic data access gap (no key in env for backtests/pipeline); some broader ETFs (SPY etc) historically mis-tagged to EQUITY (fixed); yf fetch can fail gracefully but no fallback cache in emitter; no full slippage/ADV model wired for ETF emissions yet (PR #1026 scaffolds exist); modest volume vs CRYPTO/EQUITY.
- **Quality verdict**: **Good foundation, under-exploited**. The academic rotation + VIX edge is high-quality (friction-robust, regime-aware, transferable), but production relies on mixed/generic sources + incomplete wiring of proven backtests. Data pipeline (yfinance) reliable for these names; outcome tracking part of general system (no ETF-specific resolver gaps flagged unlike CRYPTO ML). Universe expanded well (config 19+), but emitter not firing consistently.

**GitHub Actions / Data flow**: ETF via etf_sector_emitter (alpha-engine-etf.yml workflow per dashboard_generator), production_scanner / multi_asset/scanner (category tagging), scoring (elite_scorer etc), quality_gates (passes_active_gate includes ETF), dashboard. Recent direct commits + PRs touched ETF (sector momo, VIX). GHA audit-dashboard.yml covers.

**Summary baseline**: Live ETF now viable (n=106 / PF1.48 / WR58.5% / sizing true) but small-sample + mixed sources lag the clean Tier-2/near-Tier-1 rotation edge proven in 11y backtests (PF2.05→3.22 w/ VIX). XLE concentration + 0 active rotation picks today highlight wiring gap. Data quality solid (yfinance + academic strats) but economic extension blocked + emitter underused. Matches "borderline but improving" in master; clear path to T2 via existing tools without new paid data.

---

## Step 2: Identify the Single Best Pilot Candidate (within ETF)

**Filters applied**: Live PF>1.4 + WR>55% + n≥100 on sub-strat; explainable academic edge; backtest Tier-2+ with costs; low dev cost (reuse etf_strategies + vix_gate + emitter); feasible paper validation in 30-60d; diversifies COMMODITY cotton risk.

- **Recommended Pilot**: **SPDR Sector Rotation + VIX Regime (Faber TAA + Antonacci Dual Momentum on 11-sector universe XLK/XLE/XLF/XLV/XLI/XLY/XLP/XLU/XLB/XLRE/XLC + IWM)** powered by:
  - `etf_sector_momentum` (Faber 10mo SMA filter + 3m momo + ADX; top-3 long-only) + `etf_dual_momentum` (12m absolute+relative).
  - VIX<25 (or <22) regime gate (skip rebalance in high-vol; already coded for ETF in vix_regime_gate.py + backtest tool).
  - Emitter `etf_sector_emitter.py` (daily yfinance, writes alpha_engine/data/etf_sector_picks.json; opt-in sidecar).
  - Friction model (2.5-5bp realistic) + existing ATR TP/SL.
  - Strict long-only (short leg falsified).
- Justification: Backtest PF 2.05 (baseline) / 3.22 (VIX) on 122/102 periods beats live mixed 1.48 by 0.57-1.74 PF; WR 70%+; MDD compressed to 11.8% (T2); Sharpe 1.63 competitive with COMMODITY; 11y incl 2020/2022 crashes robust; monthly cadence low turnover (friction <2% annual drag); external replication (AQR QMOM/IMOM, Faber TAA funds, sector ETFs like XLY etc). XLE concentration today is symptom of non-rotation sources — pure rotation diversifies across sectors. Matches supreme "sector rotation + macro regime". Low risk: no new data feeds (yfinance already used), Wire-Up compliant (sidecar).
- Secondary: Add 1-2 macro (EEM/EFA/DBC/VNQ) or style (SCHD) for broader rotation once core fires; economic (FRED yield-curve / macro) as P2 after FRED key wired (M-032).
- Not full class pilot (COMMODITY #1; EQUITY secondary). ETF pilot conditional per 2026-06-01 schedule + 0.1% Rung-5 sizing until 30d+ paper PF>1.6 post-costs.

**Why this over intermarket-flow-scout or baby ETF?** Backtest purity + academic + VIX lift (proven transfer from EQUITY) + existing code (no rewrite) > opaque generic scout on single XLE. Rotation naturally solves concentration.

---

## Step 3: Gap Analysis (ETF)

| Gap Type                  | Diagnostic (data-backed)                                                                 | Severity | Typical Fix |
|---------------------------|------------------------------------------------------------------------------------------|----------|-------------|
| Wiring / Emission gap (0 picks today) | etf_sector_emitter ran 2026-05-15 but picks=[] (no sectors >200d SMA + positive 3m); M-023 dual_momentum_12_1 + M-036 expansion still PENDING in master; vix_regime_gate supports ETF but not default-enforced on ETF emissions (only EQUITY-heavy in some paths); etf_sector_picks.json empty. Live edge = intermarket-flow-scout (not rotation). | **P0** | Enable ETF_SECTOR_EMITTER_ENABLED=1 default; wire VIX gate default for ETF (env + quality_gates); implement/activate M-023 sector_dual_momentum_12_1 as opt-in sidecar (alpha_engine/strategies/ or extend etf_strategies); update dashboard_generator + alpha-engine-etf.yml; shadow 14d per Wire-Up. |
| Live n small + mixed sources dilute | n=106 just floor; XLE 54% PnL mass from non-rotation "intermarket-flow-scout"; baby vt_*_etf low volume; no pure rotation contributing to recent_closed. Backtest n=102-122 periods >> live. | **P1** | Prune/reweight intermarket-flow-scout if its ETF contrib PF<1.4 (check hf_stats or recent_closed slice); promote etf_sector_momentum / dual as primary ETF source (config STRATEGY_WEIGHT_OVERRIDES, passes_active_gate); target 30-50% ETF volume from rotation within 30d. |
| Economic / macro data gap | backtest_etf_economic.py failed (no FRED key); yield-curve / macro regime (M-032) not wired for ETF (only EQUITY VIX+YC combos shipped). | **P2** | Add FRED key to env + fred_data_fetcher.py usage in new etf_economic_momentum sidecar (or combine with VIX); test on DBC / VNQ / TIP. Low priority until core rotation live. |
| Friction / execution realism for rotation | Backtests include slippage variants (PF holds); but no production tx_costs.py call for ETF emitter/picks; slippage_validator (PR #1026) not yet wired for ETF. | **P1** | Wire transaction_costs + slippage_validator for ETF in resolver/quality_gates (0.05-0.15% roundtrip monthly realistic); add to emitter backtest path. |
| Outcome tracking / small-sample noise | n=106 limits DSR/stat sig; resolver general (no ETF-specific exclusion like CRYPTO ML); paper TV accounts active but ETF volume low. | **P2** | Enforce 30d paper on rotation before any sizing; add per-class DSR in statistical_rigor.py for ETF; dashboard tile for ETF rotation PF vs mixed. |
| Universe / concentration risk | Config has 19+ good names (full sectors + macro); but live skewed to XLE; TLT/HYG now correctly routed via recent etf_strategies fix. | **P1** | Enforce rotation emitter as primary (auto-diversifies); add concentration cap <25% per symbol for ETF in sizer; monitor XLE share. |

**Why live lags backtest?** Mixed generic sources (intermarket on XLE) + incomplete rotation wiring/emission + no VIX gate enforcement on ETF path. Rotation is regime-dependent (0 signals some days — normal for trend filter). Data quality not root cause — execution gap is.

---

## Step 4: Decision Framework for Strategies (live >60d)

- **Statistically significant negative alpha (PF<1.0 or WR<45% sustained, n>30 on ETF contrib)**: Delete or hard quarantine (BLOCKED_SOURCE_SYSTEMS + probation). E.g. if intermarket-flow-scout ETF slice <1.3 PF or drags XLE concentration, quarantine or invert.
- **Positive but fragile / concentrated (PF 1.3-1.5, high single-symbol share)**: Tighten + volume cap. Keep intermarket-flow-scout only if ETF-specific and not >25% class vol; promote pure rotation.
- **Only keep if survives walk-forward + live paper with real costs + VIX gate**: Promote etf_sector_momentum (Faber), etf_dual_momentum (Antonacci), vt_thematic_etf_momentum / vt_adx_rsi2_etf (if ETF-tagged), any baby rotation. VIX overlay mandatory for momentum variants.
- **Per master (M-023/M-036)**: Activate sector dual + universe expansion as opt-in sidecars with Wiring Plan.
- **Delete/invert vs promote (file paths)**:
  - Quarantine/delete low-PF ETF contrib: `alpha_engine/strategy_blocklist.py`, `audit_trail/quality_gates.py` (extend ETF source rules), BLOCKED_SOURCE_SYSTEMS.
  - Promote/wire: `alpha_engine/etf_strategies.py` (already good), `tools/etf_sector_emitter.py` (enable + schedule), `audit_trail/vix_regime_gate.py` (ETF default), `alpha_engine/config.py` (weights + ETF_SYMBOLS clean), new or extend `strategies/etf_sector_rotation_momentum.py` per backtest recs.
  - Reference: `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (rehab not silent kill); no mutation needed — backtests already strong.

**Strategies to prioritize for ETF pilot**: etf_sector_momentum + VIX gate (highest backtest conviction), etf_dual_momentum (secondary), existing vt_*_etf if they pass VIX filter.

---

## Step 5: Leverage AI Keys Intelligently — High-ROI Prompt Templates (tailored to gaps)

**1. Rotation Emitter Activation + VIX Integration**:
```
Given etf_sector_emitter.py (Faber, currently 0 picks 2026-05-15), etf_strategies.py (etf_sector_momentum + etf_dual_momentum), vix_regime_gate.py (supports ETF), and backtest results (PF 3.22 VIX<25 on 102 periods), produce: (a) exact env + code change to make VIX<25 default for all ETF asset_class emissions (quality_gates + dashboard_generator), (b) fix for emitter to always emit (or log why 0), (c) 14-day shadow validation plan + Wiring Plan section for PR, (d) pseudocode to combine dual_momentum fallback when sector_momentum empty. Target: rotation contributing ≥40% ETF volume within 30d.
```

**2. FRED Economic + Macro Regime for ETF**:
```
Design low-cost FRED integration (yield curve 10y-2y, CPI, unemployment) for ETF rotation (e.g. gate EEM/DBC during inversion or high inflation). Exact free FRED API usage (fred_data_fetcher.py exists), cache, backtest on historical (2015+), expected PF/MDD lift on sector + macro ETFs (VNQ/DBC/TIP). Include in new etf_macro_regime.py sidecar (opt-in). Reference M-032 and equity_yc_regime_breakthrough.
```

**3. Live vs Backtest Reconciliation + Concentration Fix**:
```
Analyze why live ETF PF 1.48 / XLE 54% PnL vs backtest PF 2.05-3.22 on pure rotation. Recommend: exact recent_closed slice query for ETF sources/PF by symbol (XLE vs XLK etc), prune plan for intermarket-flow-scout ETF contrib if <1.4 PF, rotation volume target, and dashboard tile showing "ETF Rotation (VIX-gated) vs Mixed" PF/WR/n. Cite dashboard_data + hf_stats.
```

---

## Step 6: Low-Cost Data & Validation Stack

- **Cache everything**: yfinance responses (daily JSON in alpha_engine/data/ like etf_sector_picks); VIX (^VIX) + YC (^TNX-^FVX) cached in vix_regime_gate.py (already has _VIX_CACHE / _YC_CACHE + TTL).
- **Walk-forward / rolling OOS mandatory**: On 11-sector SPDR only (already in backtests); extend with CPCV for VIX thresholds. Re-run backtests monthly.
- **Monte-Carlo / bootstrap**: For CI on PF/MDD post-friction (target 95% CI PF>1.8 for rotation).
- **Truth source**: Live paper trading (tv-paper-trade accounts) on rotation signals vs backtest. 30d rolling WR/PF post 5-10bp costs + slippage_validator. 7d soak before any gate.
- **Resolver/DB**: General resolver-v2 sufficient; add ETF rotation source tag for tracking. DB freshness guardian (M-002) covers emitter runs.
- **External cheap**: yfinance only (no paid); FRED free tier once key added; VIX/YC public. No Glassnode etc needed.
- **Anti-overfit**: DSR/PSR (statistical_rigor.py), trust_score ≥0.55 for ETF, elite_score per-class, anti_overfit_audit_sidecar. VIX gate itself is regime anti-overfit.
- **Validation**: Reproduce backtests (`python tools/backtest_etf_rotation_vix_regime.py`); 14d shadow emitter; compare paper vs dashboard ETF tile.

---

## Step 7: Focused Output — 30/60/90-Day Execution Recommendation

**Pilot**: SPDR 11-Sector Rotation + VIX<25 Regime (Faber + Dual Momentum long-only). Target post-90d: PF ≥1.8 / WR ≥58% / n≥80 clean resolved on rotation signals (quality > mixed volume), VIX gate active on ≥70% ETF emissions, XLE concentration <25% class PnL, 0.1%→0.5% sizing if gates passed. Contributes to "phenomenal performance across ALL asset classes" (Goal #1) as low-effort Tier-2 candidate behind COMMODITY.

**30 Days (P0 — Wire the proven edge, stop dilution)**:
- Activate + schedule `etf_sector_emitter.py` (ETF_SECTOR_EMITTER_ENABLED=1 default; add to GHA alpha-engine-etf.yml or cron); ensure daily run produces rotation picks when conditions met (log skips).
- Wire VIX regime gate default for ETF: update `audit_trail/quality_gates.py`, `audit_trail/vix_regime_gate.py` (env VIX_REGIME_GATE_ETF_ENABLED=1), `audit_dashboard/template.html` (ETF tile shows VIX filter status), dashboard_generator. Reference backtest sweet spot VIX<25.
- Activate M-023: ship `sector_dual_momentum_12_1` (or map to existing etf_dual_momentum) as opt-in sidecar with full Wiring Plan + 14d shadow (per CLAUDE.md).
- Prune / cap: if intermarket-flow-scout ETF contrib PF<1.4 or >30% vol, reduce weight in config / quality_gates; target rotation ≥30% ETF volume.
- Paper: 0.1% risk shadow on all new rotation + VIX-gated signals (target n≥15-20 in 30d, PF>1.6 post simulated costs).
- Data: Add FRED key (if available) + stub etf_economic sidecar; fix any yf fetch in emitter.
- Docs: Update `reports/MASTER_ACTION_PLAN_2026-05-15.md` Section 21 + M-023/M-036 status (evidence-backed); create this `reports/asset_class_90day_plan_ETF_2026-05-15.md`; add to supreme plan ETF track.
- Success: Dashboard ETF tile shows rotation source active + VIX filter; emitter producing >0 picks on avg days; XLE PnL share dropping; paper PF>1.5.

**60 Days (P1 — Validate + scale paper)**:
- Full 30-45d paper pilot: 0.2-0.3% risk on rotation book (all 11 sectors + VIX gate + dual fallback); rolling metrics target PF>1.7 / WR>58 / MDD<15 / n≥40 clean. Journal every deviation.
- Walk-forward re-backtest + MC on live data window; add slippage_validator + tx_costs for ETF path.
- Expand universe slightly (M-036): ensure full 19+ in ETF_SYMBOLS + emitter (EEM/EFA/DBC etc for macro rotation); test international tilt.
- Economic layer: wire FRED yield-curve / inflation gate for defensive sectors (XLP/XLU/XLV) during inversion (combine with VIX).
- Prune remaining drags; promote 2-3 rotation variants only for ETF.
- External: Compare paper to public sector rotation (e.g. Faber TAA funds, XL sector perf); Hyperliquid or futures analogs if relevant.
- GHA + monitoring: ETF freshness in db-freshness badge; concentration alerts.
- Success: Paper meets T2 thresholds (PF≥1.6 / WR≥52 / n≥60 / MDD<18 on 45d+); M-023/M-036 closed with repro; rotation >50% ETF PnL.

**90 Days (P2 — Go/No-Go for micro-sizing + T2 candidate)**:
- If paper pilot passes (clean 60d rolling PF>1.8 / WR>58 / n≥80 post real costs/slippage, DSR>0.85, corr<0.6 with COMMODITY/EQUITY, no VIX-regime failure in live, XLE<25%): promote to 0.3-0.5% live micro sleeve (skin-in-game per M-061), full dashboard integration, update master institutional schedule ETF pilot date. Consider 2nd leg (risk-parity or quarterly rebalance variant).
- Else: Maintain 0.1% max, double down on VIX + rotation purity (drop any remaining generic scout), further universe filter (drop ARKK/KWEB if volatile), consider "ETF research-only" if no lift. Re-eval vs BOND thin sample.
- Master plan updates: Close M-023/M-036/M-0xx (VIX-ETF) with paper logs + dashboard delta + backtest repro; add M-0xx for FRED ETF macro if successful. All via clean PRs + swarm per AGENTS.md + Wire-Up Rule.
- Overall: ETF moves from "borderline T3 / mixed" to "Tier-2 candidate on rotation + VIX" (2nd class after COMMODITY). Diversifies single-symbol commodity risk. Contributes to phenomenal /audit performance across classes. If succeeds, ETF becomes reliable parallel sleeve (low capital, high edge clarity).
- If COMMODITY pilot fails gate, de-prioritize ETF further.

**Risks / Anti-patterns avoided**: No heavy capital before 30-60d paper + VIX gate live (avoids small-n overfit); no complex BL/risk-parity before basic rotation fires (BL falsified in backtest); prune mixed sources > add volume; no silent promotion (evidence-first per master); no new paid data (yfinance + FRED free); respect "only scale if COMMODITY succeeds" from supreme; follow MUTATION_THREE_AXIS if any rehab needed.
- Anti: Do not force daily signals (momentum is regime-gated — 0 picks normal); do not ignore XLE concentration without rotation emitter.

**Files to touch (Wire-Up compliant, small focused PRs, opt-in/sidecar where possible)**: `tools/etf_sector_emitter.py` (enable + logging), `alpha_engine/etf_strategies.py` (minor if dual expansion), `audit_trail/vix_regime_gate.py` + `quality_gates.py` (ETF default + source rules), `alpha_engine/config.py` (weights, ETF_SYMBOLS), `audit_dashboard/template.html` + `dashboard_generator.py` (tiles + emitter source), `alpha_engine/production_scanner.py` / `scanner.py` (category/ETF hints), `tools/backtest_etf_rotation_vix_regime.py` (repro + update), new `strategies/etf_sector_rotation_momentum.py` (if separate from emitter per backtest rec), `reports/MASTER_ACTION_PLAN_2026-05-15.md` (Section 21 + M-023 status). Reference `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

**Expected impact**: +0.3-0.8 PF lift on ETF class (rotation purity + VIX compression); n growth to 150-200 clean rotation samples; XLE concentration normalized (<25%); path to T2 (PF>1.6 / WR>52 / MDD<18) within 90d at 0.1-0.5% sizing. Low dev cost (reuse 90% existing), high edge clarity, diversifies platform. Positions ETF as reliable 3rd/4th asset class post-COMMODITY/EQUITY.

**Next**: Spawn deep-dive subagent only if FRED economic or specific source (intermarket autopsy) needed; otherwise execute 30d wiring immediately. Re-run backtests + paper monitor weekly. Update supreme + master only on evidence. All changes via clean branches + PRs per AGENTS.md.

**References** (absolute paths):
- Data: `/mnt/e/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json`
- Master/Supreme: `/mnt/e/findtorontoevents_antigravity.ca/reports/MASTER_ACTION_PLAN_2026-05-15.md`, `/mnt/e/findtorontoevents_antigravity.ca/reports/SUPREME_PLAN_90days.md`
- Code: `/mnt/e/findtorontoevents_antigravity.ca/alpha_engine/etf_strategies.py`, `config.py`, `tools/etf_sector_emitter.py`, `audit_trail/vix_regime_gate.py`, `quality_gates.py`
- Backtests/Reports: `/mnt/e/findtorontoevents_antigravity.ca/reports/etf_vix_regime_breakthrough_20260513.md`, `etf_sector_rotation_backtest_20260513T020800Z.md`, `etf_abc_backtest_20260513.md`, `fix_ETF_20260505T005402Z.md`, `audit_asset_feedback_2026-05-05T0121Z_ETF.md`, `backtest_etf_economic_2026_05_12_0615Z.md`, `expanded_enhancement_plan_2026-05-14.md`

This plan is ruthless, data-driven, focused on compounding the clean academic rotation edge while eliminating mixed-source dilution. ETF is worth targeted (not heavy) investment in the next 90 days — high conviction on VIX-augmented sector momentum as the path to T2.

---
*Generated 2026-05-15 per money-maker-continual-improve skill invocation. Pilot asset class for system remains COMMODITY; this is ETF-specific 90d wiring + validation plan (tertiary parallel track).*