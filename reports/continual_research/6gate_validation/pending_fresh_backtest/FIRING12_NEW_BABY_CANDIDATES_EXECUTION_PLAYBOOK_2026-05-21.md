# Firing 12 New Baby Candidates Execution Playbook — Post-Hygiene Clean Backtest + Wiring for Firing 11 Baby Strategies
**Date:** 2026-05-21 (Firing 12 of the 30m continual 6-gate research loop)  
**Subagent:** Grok Build (Firing 12 prep, delegated from Firing 11 baby expansion task)  
**Focus:** Exact, copy-paste-ready post-hygiene validation + wiring commands for the five new baby candidates surfaced in Firing 11:  
- `multi_timeframe_ema_cloud` (CRYPTO) — **strongest priority** (PF 6.95 / WR 72.4% / Sharpe 7.46 on n=29; promoted ready_for_forward_test)  
- `inverse_goldmine_stocks` (EQUITY) — **strongest priority** (hygiene beneficiary + theoretical inverse PF 2.61 from parent n=85 PF 0.38; 90-day plan alignment)  
- `moving_average_slope_momentum` (CRYPTO) (PF 1.33 / n=94)  
- `rsi_pairs_arbitrage` (CRYPTO) (highest n=130 / PF 1.27)  
- `copper_platinum_cot_momentum` (COMMODITY) (COT-proxy; direct Firing 10 guard beneficiary + 90-day diversification)  

**Purpose:** Consolidated ready-to-execute playbook (mirrors structure and exactness of `FIRING11_POST_HYGIENE_EXECUTION_PLAYBOOK_2026-05-21.md`) that can be run the instant Firing 10 tagging hygiene patch + backfill + COT guard are verified live. All paths M-107 pre-registration compliant. Research-only until 6+/8 gates + edge_stability_harness admissible + cost survival. Outputs target `reports/continual_research/6gate_validation/pending_fresh_backtest/` and sibling A_passed/B_failed.

**Citations (Primary Sources — Must Be Referenced in All Follow-On Work):**
- Firing 11 baby report: `reports/continual_research/6gate_validation/FIRING11_BABY_STRATEGIES_90DAY_EXPANSION_2026-05-21.md` (full mining methodology, 3-5 candidates with meta evidence, 6/8-gate outlines, A/B recs, 90-day plan gaps filled)
- Firing 11 post-hygiene playbook: `reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING11_POST_HYGIENE_EXECUTION_PLAYBOOK_2026-05-21.md` (prereq hygiene steps, exact validate/framework/harness patterns for funding/E-ANON/H-037, promotion checklist, citations)
- Firing 11 COMMODITY guard: `reports/continual_research/6gate_validation/COMMODITY_GUARD_VERIF_SALVAGE_FIRING11_2026-05-21.md` (guard live at `copy_trader_intel/multi_asset_copytrader_scraper.py:1843-1865` + imports 83-94 + schema 1702-1712; simulation pass; non-COT salvage context for copper)
- Cycle summary: `reports/continual_research/6gate_validation/CYCLE_2026-05-21_FIRING11_SUMMARY.md` (baby mining "in flight" at kickoff; playbook + guard completed)
- Hygiene artifacts (Firing 7-10): `pending_fresh_backtest/FIRING10_HYGIENE_MINIMAL_MERGE_DIFF_2026-05-21.md`, `FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py`, `FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py`, `FIRING10_EQUITY_FOREX_EXPANSION_2026-05-21.md`, `FIRING10_H037_WIRING_PR_SCOPE_2026-05-21.md`, `EQUITY_TAGGING_BUG_P0_FIX_PROPOSAL_2026-05-21.md`, `COMMODITY_COT_GUARD_PATCH_firing10_2026-05-21.md`, `FIRING7_TAGGING_HYGIENE_PR_SCOPE_2026-05-21.md` + patched refs (`FIRING8_DASHBOARD_GENERATOR_PATCHED_REFERENCE_2026-05-21.py`)
- Core spec: `6GATES_2026-05-21_V1_FREEBUFF.MD` (8 gates: G1 Sharpe>=1 or class-tuned, G2 p<0.05, G3 CI>0, G4 WF>=50%, G5 MC bootstrap, G6 MC crash, G7 WR>40%, G8 PF>1.0; per-class notes, daily PnL critical vs per-trade inflation, tagging bug §4-5)
- Master baseline: `reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md` + `reports/hypothesis_registry.json` (M-107; no baby entries pre-F12)
- Living public log: `updates/2026-05-21-continual-6gate-asset-class-research/index.html` (baby mining "pending" + F11 playbook/guard markers)
- Baby sources: `baby_strategies/multi_timeframe_ema_cloud.py` + `.meta.json`, `moving_average_slope_momentum.py` + `.meta.json`, `rsi_pairs_arbitrage.py` + `.meta.json`, `copper_platinum_cot_momentum.py`, `inverse_goldmine_stocks.meta.json` + `inverse_wrapper.py`, `backtest_framework_runner.py`, `baby_strategies_backtest.py`
- Harnesses: `tools/validate_resolved_picks.py`, `alpha_engine/statistical_validation_framework.py` (and tools/kimi copy), `alpha_engine/edge_stability_harness.py` (and tools copy), `alpha_engine/edge_stability_harness_enriched.py`
- Wiring sites: `audit_trail/dashboard_generator.py:3589` (JSON_PICK_SOURCES), `alpha_engine/data/*.json` emitters, `paper_trading/strategies/`, `paper_trading/strategies/incubator_strategies.py`, `audit_trail/quality_gates.py`, `alpha_engine/*_strategy_harness.py` (crypto/equity/commodity/etf)
- Prior B_failed context: commodity/forex/equity_vix reports (hygiene unlocks clean slices)

**Status:** Research-only, M-107 compliant, fully cited. No production sizing. Execute after hygiene verification (see §1). Parallel to H-017 accrual / FOREX fixes / COMMODITY re-agg.

---

## 1. Prerequisites & One-Time Setup (MUST COMPLETE BEFORE ANY VALIDATION RUN)

These are **identical** to the Firing 11 post-hygiene playbook §1 (copy-paste from there). Hygiene (tagging patch + backfill) is the critical unblocker for trustworthy `--by-asset-class` slices (prior ~90.8% crypto-in-EQUITY pollution per 6GATES and Firing 10/11 summaries; clean EQUITY n~20 pre-fix; COMMODITY COT now guarded).

### 1.1 Apply/Verify Tagging Hygiene Patch + Backfill (FIRING11_POST_HYGIENE_EXECUTION_PLAYBOOK_2026-05-21.md §1.1-1.2)
See exact minimal diff, `_infer_asset_class` helper, verification via `FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py`, and FIRING9_TAGGING_BACKFILL_SCRIPT commands (dry-run then --apply on `universal_resolved_picks.json`, `dashboard_data.json`, SQL tables). Post-backfill spot-check:

```bash
python tools/validate_resolved_picks.py --by-asset-class --min-trades 5 --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/
# Expect: 0 crypto in EQUITY, XL*→ETF, clean CRYPTO/FOREX/ETF/COMMODITY counts, no -USD in EQUITY buckets
```

### 1.2 Extend validate_resolved_picks.py for Research-Loop Slices (FIRING11_POST_HYGIENE... §1.3)
Current parser (lines ~318-327): only `--min-trades`, `--by-asset-class` (store_true flag), `--output`, `--save-csv`. **Add before F12 runs** (per F11 playbook):
- `--output-dir` (default `reports/continual_research/6gate_validation/`)
- `--strategy-filter "regex"` (post-load filter on strategy name / source_system)
- `--save-json <path>` (per-family clean slices)

After edit + test, re-verify full `--by-asset-class` writes clean reports + slices.

### 1.3 Extend/Use statistical_validation_framework.py + edge_stability_harness (FIRING11... §1.4)
CLI minimal (`--example-run` only at alpha_engine/...:1159). Use programmatic or proposed extended invocation (daily-pnl critical for credible G1 per 6GATES appendix + validate _sharpe_from_trades). Edge harness: `EdgeStabilityHarness().is_admissible(..., windows='14d', eff_floor=0.30, min_stable=3)` (or enriched variant). Import from `alpha_engine.edge_stability_harness`.

### 1.4 Other Standing Prereqs
- M-107 pre-reg in `reports/hypothesis_registry.json` (commit to main **before** any backtest data touch — this playbook's §2 snippets are the exact pre-reg payloads).
- Daily PnL series (framework --daily-pnl or resolver agg; per-trade Sharpe inflates G1).
- Data freshness: yfinance for equity/commodity (HG=F, PL=F), crypto 1h/4h per baby metas.
- Post-guard COMMODITY: copper benefits from live M-095 fail-loud (verified in COMMODITY_GUARD_VERIF...).
- Verify clean slices post-hygiene (as in F11 playbook §1.5).

**Verification command (after full hygiene + backfill + script fixes):**
```bash
python tools/validate_resolved_picks.py --by-asset-class --min-trades 10 --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/
# Manual: no ETH-USD etc in EQUITY; funding/ema symbols clean CRYPTO; copper/platinum COMMODITY; goldmine inverse targets EQUITY only.
```

---

## 2. multi_timeframe_ema_cloud (CRYPTO) — Strongest Priority
**Evidence (FIRING11_BABY... §2.1):** status=ready_for_forward_test, WR=0.7241, sharpe=7.4599, PF=6.9515, total_return=0.0597, n=29 (gate-viable). Promoted 2026-04-14 per TESTING_PROTOCOL Layer 6. Code: 4-layer EMA cloud (8/21/50/200) + MTF (4H for 1H) + expansion + volume + dynamic trail. SYMBOLS=25+ (BTCUSDT...ETCUSDT). Class=CRYPTO. Not in registry or prior firings (baby mining pending at F11 kickoff). High-conviction technical confluence.

**Pre-Registration Note (M-107 — Commit BEFORE any re-backtest or harness):**
Edit `reports/hypothesis_registry.json` (append to hypotheses array or new "firing12_baby" key; use next logical ID or BABY- form per F11 baby report example + E-ANON precedent):

```json
{
  "id": "H-BABY-CRYPTO-EMA-CLOUD-001",
  "asset_class": "CRYPTO",
  "family": "multi_timeframe_ema_cloud",
  "strategy_name": "MultiTimeframeEMACloudStrategy",
  "source_file": "baby_strategies/multi_timeframe_ema_cloud.py",
  "description": "4-layer EMA cloud (8/21/50/200) + MTF alignment (4H for 1H entries) + cloud expansion + volume confirmation + dynamic EMA21 trail. LONG/SHORT on 25+ liquid symbols (BTCUSDT,ETHUSDT,...ETCUSDT). 1H primary. Entry: price above all EMAs + expansion + HTF align. Exit: opposite cloud boundary or EMA50. Prior meta (2026-03/04 yf 6mo 1h): n=29, WR=72.41%, PF=6.9515, Sharpe=7.46, maxDD=0.49%. Promoted ready_for_forward_test 2026-04-14.",
  "test_statistic": "6/8 gates via validate_resolved_picks + statistical_validation_framework (daily PnL) + edge_stability_harness.is_admissible (14d windows, eff>=0.30, min_stable=3) + cost survival >=0.6 (30bps crypto)",
  "acceptance_criteria": {
    "eff_floor": 0.30,
    "min_windows_admissible": 3,
    "same_sign": true,
    "cost_survival_min": 0.6,
    "slippage_bps": 30,
    "min_trades": 20,
    "gates_6_of_8": true,
    "validation": "post-hygiene clean CRYPTO slice only; compare vs scrambled noise; G4 WF power note for small n"
  },
  "economic_prior": "MTF EMA confluence filters noise; cloud expansion signals trend acceleration (stronger than single EMA cross). Volume filter + trail reduces whipsaw. Academic/technical: layered moving averages + momentum confirmation (e.g. extensions of Kaufman, Elder). High Sharpe natural in liquid CRYPTO per 6GATES.",
  "status": "pre-registered",
  "registered_at": "2026-05-21",
  "pre_reg_date": "2026-05-21",
  "prior_evidence": {
    "backtest": {"n":29, "WR":0.7241, "PF":6.9515, "Sharpe":7.4599, "maxDD":0.0049, "total_return":0.0597, "date":"2026-03/04", "meta_path":"baby_strategies/multi_timeframe_ema_cloud.py.meta.json"},
    "promotion": "TESTING_PROTOCOL Layer 6, 2026-04-14"
  },
  "expected_gates": ["all 8 per 6GATES_V1 (G1 daily-PnL critical; G4 may need relaxed windows for n=29)"],
  "tags": ["baby", "technical", "MTF", "ema_cloud", "firing11", "firing12", "CRYPTO", "high-conviction"],
  "wiring": "OPT-IN RESEARCH SIDECAR ONLY. Pre-registered per M-107 BEFORE any data fetch or backtest. Post-admissible: emitter + dashboard + paper shadow.",
  "banned_check": "Distinct from funding_arb family, coinglass carry, H-006/012/035 (killed), cross_sectional_crypto_carry (B_failed PF<1). New MTF technical only."
}
```

**Exact Post-Hygiene Commands (adapt for current validate CLI until §1.2 extensions; use --output + post-filter or manual slice for strategy):**

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca

# 1. (Optional) Fresh backtest via baby framework (or yf 1h/4h on 25 symbols, 180d+; produce resolved-style JSON with asset_class=CRYPTO, strategy="multi_timeframe_ema_cloud|MultiTimeframeEMACloudStrategy")
python baby_strategies/backtest_framework_runner.py \
  --strategy multi_timeframe_ema_cloud \
  --symbols "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT,ADAUSDT,AVAXUSDT,TRXUSDT,DOTUSDT,LINKUSDT,LTCUSDT,BCHUSDT,SHIBUSDT,SUIUSDT,INJUSDT,NEARUSDT,HBARUSDT,ARBUSDT,OPUSDT,FETUSDT,TIAUSDT,SEIUSDT,AAVEUSDT,ETCUSDT" \
  --timeframe 1h --lookback 180d \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING12_EMA_CLOUD_BACKTEST_TRADES_2026-05-21.json
# Or: python baby_strategies/baby_strategies_backtest.py --filter ema_cloud (adapt as needed). Ensure output has entry/exit, pnl_pct, direction, asset_class=CRYPTO, strategy tag.

# 2. Extract / validate clean CRYPTO slice (post-hygiene; use strategy-filter once extended, else full --by-asset-class CRYPTO + manual grep filter or post-process)
python tools/validate_resolved_picks.py \
  --min-trades 20 \
  --by-asset-class \
  --output FIRING12_EMA_CLOUD_VALIDATE.json \
  --save-csv \
  --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/
# Post-process (if needed): jq filter on "per_strategy_results" for ema_cloud|MultiTimeframeEMACloudStrategy into clean slice JSON.

# 3. Full 6/8-gate statistical framework (G1-6 + daily PnL for realistic Sharpe/costs — REQUIRED per 6GATES)
python alpha_engine/statistical_validation_framework.py \
  --input reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING12_EMA_CLOUD_BACKTEST_TRADES_2026-05-21.json \
  --asset-class CRYPTO \
  --framework full \
  --daily-pnl \
  --slippage-bps 30 \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING12_EMA_CLOUD_6GATE_2026-05-21.json
# (If CLI limited: python -c "from alpha_engine.statistical_validation_framework import ...; run_full_framework(...)" )

# 4. Edge stability / admissible check (G4 WF consistency; 14d windows)
python -c "
from alpha_engine.edge_stability_harness import EdgeStabilityHarness
h = EdgeStabilityHarness()
admissible = h.is_admissible(
    'H-BABY-CRYPTO-EMA-CLOUD-001',
    slice_json='reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING12_EMA_CLOUD_BACKTEST_TRADES_2026-05-21.json',
    windows='14d',
    eff_floor=0.30,
    min_stable=3
)
print('Admissible for promotion (multi_timeframe_ema_cloud):', admissible)
" 2>&1 | tee reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING12_EMA_CLOUD_EDGE_ADMISSIBLE_2026-05-21.log

# 5. (Optional) Crypto-specific harness cross-check
# python alpha_engine/crypto_strategy_harness.py --family ema_cloud --input <slice> --costs 0.003 --wf  (extend if needed; else programmatic)
```

**Expected Gate Outcomes (on clean post-hygiene data + prior meta):** High chance G1 (daily +30bps)/G3/G5/G6/G7(72%>40)/G8(6.95>1) pass. G2 critical (p<0.05 on n=29). G4 (WF) power-limited by n — use relaxed windows or more data per F11 baby §3.1 note. Compare vs noise. If 6+/8 + admissible + cost_survival>=0.6 → **A_passed/multi_timeframe_ema_cloud_crypto_2026-05-21.md** (format per luxalgo_confluence in A_passed/).

**Wiring Suggestions (if passes gates + admissible):**  
- Create emitter: `tools/baby_ema_cloud_emitter.py` (or integrate MultiTimeframeEMACloudStrategy.generate_signals into alpha_engine/crypto_*_strategies.py or new baby_technical_emitter; write alpha_engine/data/baby_ema_cloud_picks.json with _infer-compliant CRYPTO tags, regime, confidence). Guarded by BABY_EMA_CLOUD_EMITTER_ENABLED=1.  
- Register in `audit_trail/dashboard_generator.py:3589` JSON_PICK_SOURCES: `("baby_ema_cloud", "alpha_engine/data/baby_ema_cloud_picks.json", None)`.  
- Paper trading shadow (post-wiring): Use tv-paper-trade skill (switch SCALPER/TESTER etc.), load strategy on 1-2 liquid symbols (BTC/ETH), 0.5-1% risk, track in paper_trading/data/ or dedicated verification_state. Or add to `paper_trading/strategies/incubator_strategies.py` + scanner. 14-30d accrual for real G1.  
- Update registry wiring field + 90-day CRYPTO plan. Add to alpha-engine-crypto.yml gated cron if desired.  
- Rollback: zero impact (remove registration, unset env).

---

## 3. inverse_goldmine_stocks (EQUITY) — Strongest Priority (Hygiene Beneficiary)
**Evidence (FIRING11_BABY... §2.2):** .meta only (mutation of goldmine_stocks via inverse_wrapper). Parent n=85 closed (WR 21.2%, PF 0.38, 71.8% SL hit, sum_return=-217%). inverse_theoretical_WR=78.8%, inverse_theoretical_PF=2.61. Config: flip_direction, max_concurrent=5, size 0.5x. status=awaiting_forward_test, created 2026-04-14 (post-PR#207 goldmine bug exposure). 90-day EQUITY plan alignment: mutations/inverses/evidence-first/T2 + hygiene critical (Firing 10 tagging patch fixes pollution; real EQUITY n~20 pre-fix). Not in registry. Highest conviction hygiene + class expansion synergy.

**Pre-Registration Note (M-107):**
```json
{
  "id": "H-BABY-EQUITY-INV-GOLDMINE-001",
  "asset_class": "EQUITY",
  "family": "inverse_goldmine_stocks",
  "strategy_name": "inverse_goldmine_stocks",
  "source_file": "baby_strategies/inverse_goldmine_stocks.meta.json + inverse_wrapper.py (transform on goldmine_* picks)",
  "description": "Inverse (flip_direction + mirrored TP/SL) of goldmine_stocks consensus tiers (goldmine_1x/2x/3x/5x_consensus). Parent: n=85, WR=21.2%, PF=0.38 (heavy SL hits). Theoretical inverse: WR~78.8%, PF~2.61. Half-size (0.5x), max 5 concurrent. Focus fade on exposed names (MARA/PLTR/MSTR etc per parent). Per STRATEGY_INVESTIGATION_BEFORE_KILL + TESTING_PROTOCOL mutation-before-kill. Hygiene unlock: Firing 10 tagging patch + backfill ensures clean EQUITY bucket (no crypto pollution).",
  "test_statistic": "6/8 gates on clean post-hygiene EQUITY slice (validate + framework daily-PnL + edge_stability 14d) + explicit tagging audit (0 crypto symbols in EQUITY)",
  "acceptance_criteria": {
    "eff_floor": 0.30,
    "min_windows_admissible": 3,
    "same_sign": true,
    "cost_survival_min": 0.6,
    "slippage_bps": 15,
    "min_trades": 10,
    "gates_6_of_8": true,
    "promotion": "n>=20 + WR>=60 + PF>=1.5 (per meta); else retire if <40% on n>=20"
  },
  "economic_prior": "Goldmine consensus (exposed post-2026-04-14 loader fix) systematically picks falling equities (21% WR). Symmetric inverse captures the 79% downside. Causal: documented SL-heavy failure mode in parent = reliable fade signal (mutation rule). Aligns EQUITY 90-day 'inverses/mutations/PEAD' + VIX sidecar.",
  "status": "pre-registered",
  "registered_at": "2026-05-21",
  "pre_reg_date": "2026-05-21",
  "prior_evidence": {
    "parent": {"n":85, "WR":0.212, "PF":0.38, "sum_return_pct":-217.74, "sl_hit_pct":0.718, "data":"goldmine/closed_trades.json 2026-04-14"},
    "inverse_theoretical": {"WR":0.788, "PF":2.61},
    "meta_path": "baby_strategies/inverse_goldmine_stocks.meta.json",
    "exposure": "PR#207 / dashboard_generator.py goldmine loader fix"
  },
  "expected_gates": ["6+/8 on clean EQUITY (relax min-trades=10 per sparse EQUITY power in 6GATES); explicit hygiene/tagging verification"],
  "tags": ["baby", "inverse", "mutation", "goldmine", "equity", "firing11", "firing12", "hygiene-beneficiary"],
  "wiring": "OPT-IN RESEARCH SIDECAR. Pre-registered per M-107. Use inverse_wrapper.transform adapter. Post-pass: dashboard registration + paper shadow (0.5x).",
  "banned_check": "NOT parent goldmine (failed). Distinct from E-ANON-001 (short_term_price_momentum), H-028 variants, equity_vix (B_failed). Pure inverse mutation per documented rule."
}
```

**Exact Post-Hygiene Commands:**

```bash
# 1. Backtest / generate inverse signals (use inverse_wrapper on existing goldmine closed/active or dedicated yf backtest of fade logic on parent-exposed symbols: AMD,NVDA,MARA,PLTR,MSTR etc. Produce resolved JSON with asset_class=EQUITY, strategy="inverse_goldmine_stocks", flipped direction)
python -c "
from baby_strategies.inverse_wrapper import transform
# Load goldmine picks (or simulate from parent closed_trades), call transform(..., source_strategy='goldmine_*', new_strategy_name='inverse_goldmine_stocks', ...)
# Write to reports/.../FIRING12_INV_GOLDMINE_TRADES_2026-05-21.json (ensure clean EQUITY tags post-hygiene)
print('Implement adapter call or yf fade backtest here; output resolved-style records')
" > /dev/null
# Alternative: extend equity_strategies or run dedicated backtest_equity... producing the slice.

# 2. Validate clean EQUITY slice (relaxed min-trades per 6GATES sparse note + hygiene verification)
python tools/validate_resolved_picks.py \
  --min-trades 10 \
  --by-asset-class \
  --output FIRING12_INV_GOLDMINE_VALIDATE.json \
  --save-csv \
  --output-dir reports/continual_research/6gate_validation/pending_fresh_backtest/
# Post: assert no crypto symbols in EQUITY results for this strategy; use FIRING10 pollution analyzer pre/post.

# 3. Full framework + daily PnL
python alpha_engine/statistical_validation_framework.py \
  --input reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING12_INV_GOLDMINE_TRADES_2026-05-21.json \
  --asset-class EQUITY \
  --framework full \
  --daily-pnl \
  --slippage-bps 15 \
  --output reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING12_INV_GOLDMINE_6GATE_2026-05-21.json

# 4. Edge stability (14d)
python -c "
from alpha_engine.edge_stability_harness import EdgeStabilityHarness
h = EdgeStabilityHarness()
print('Admissible (inverse_goldmine):', h.is_admissible('H-BABY-EQUITY-INV-GOLDMINE-001', slice_json='...FIRING12_INV_GOLDMINE_TRADES...', windows=14, eff_floor=0.30))
" 2>&1 | tee .../FIRING12_INV_GOLDMINE_EDGE_2026-05-21.log

# 5. Equity harness cross-check (if MomentumFactor or similar adapter exists)
# python alpha_engine/equity_strategy_harness.py --strategy inverse_goldmine --universe ... --input <slice> ...
```

**Wiring (if n>=20 forward confirms theoretical + gates pass):**  
- Adapter in `antigravity_strategies.py` or `alpha_engine/equity_strategies.py` calling inverse_wrapper.transform on goldmine source_system picks (opt-in guard). Emit to alpha_engine/data/inverse_goldmine_picks.json (0.5x sizing per meta).  
- Register in dashboard_generator.py JSON_PICK_SOURCES.  
- Paper: tv-paper-trade on EQUITY account (SCALPER/TESTER), half-size, track verification. Or incubator_strategies registration.  
- Update registry + EQUITY 90-day plan (T2 evidence booster + hygiene case study).  
- Special: explicit post-run tagging audit (FIRING10 pollution analyzer).

**Promotion criteria per meta:** n>=20 + WR>=60% + PF>=1.5 (else retire if <40% on n>=20).

---

## 4. moving_average_slope_momentum (CRYPTO)
**Evidence (FIRING11_BABY...):** status=ready_for_forward_test, WR=0.5638, sharpe=1.8099, PF=1.332, total_return=0.0883, n=94 (best volume among CRYPTO babies). Promoted 2026-04-14. Triple EMA slope (Fib 5/13/34) + hierarchy/acceleration. Same 25+ symbols. Fits CRYPTO volume for G4 power. Borderline WR but solid n.

**Pre-Reg Note:** Similar H-BABY-CRYPTO-SLOPE-MOM-002; cite meta n=94 PF1.332; "best volume baby; post-hygiene retest for G1/G4 credibility."

**Commands (pattern as §2, filter "moving_average_slope|MA_slope_momentum|triple_ema_slope"):**  
validate --by-asset-class CRYPTO --min-trades 20 + strategy-filter once extended + framework daily-pnl 30bps + edge 14d. Use backtest_framework_runner or direct on 94-trade prior.

**Wiring:** Same emitter/dashboard/paper pattern as ema_cloud (lower priority unless G4 strong from n).

**Expectations:** G7/G8 borderline (WR 56%>40, PF>1); G4 benefits from n=94; G1 now credible post-daily. 6+/8 + admissible → A_passed.

---

## 5. rsi_pairs_arbitrage (CRYPTO)
**Evidence:** status=backtest_failed (but metrics present), WR=0.4231, sharpe=1.2934, PF=1.2694, total_return=0.1236, n=130 (highest n — best power). Z-score spread + RSI-timed pairs arb on correlated crypto (BTC/ETH etc). Market-neutral. Complements single-name funding (sibling cross_sectional_crypto_carry in B_failed n=189 PF<1).

**Pre-Reg Note:** H-BABY-CRYPTO-RSI-PAIRS-003; cite highest n=130; "pairs angle for market-neutral diversification; retest post any resolver fixes."

**Commands:** validate CRYPTO min-trades 20 + filter "rsi_pairs_arbitrage|pairs_arb" + framework + edge. Leverage high n for strong G2/G4/G5/G6.

**Wiring:** Market-neutral sidecar emitter (distinct from directional funding family). Register + paper if passes (neutral book test).

**Expectations:** Strongest statistical power from n; G7/G8 pass (PF>1, WR~42% close to 40). If 6+/8 + admissible → A_passed (note failed status in prior meta requires hygiene/repro confirmation).

---

## 6. copper_platinum_cot_momentum (COMMODITY)
**Evidence (FIRING11_BABY... §2.3 + COMMODITY_GUARD...):** No .meta/numeric (proxy logic only). EMA20>EMA50 + 45<=RSI<=60 + price>EMA50 for HG=F/PL=F (whitelisted historically in quality_gates). "COT-proxy" via price (commercials net short in rising mkts). Presets for vol. 90-day: diversification (CT=F 73% violation), HG/PL prior n=168/138 whitelisted, post-clean COT n~5-20, M-021 lag-corrected. **Direct Firing 10 beneficiary** (guard live + tagging hygiene + source_system="cftc_socrata"). Under-tested.

**Pre-Reg Note:** H-BABY-COMMODITY-COT-PROXY-004; cite proxy rationale + guard synergy + 90-day diversification; "re-backtest post-guard + yf futures; add meta on numeric results."

**Commands (yfinance futures + strategy logic → trades JSON; post-guard verification via _is_cot_row_public simulation if extending to real COT):**
validate --by-asset-class COMMODITY --min-trades 5 (small n expected) + filter "copper_platinum|cot_momentum" + framework (daily-pnl, low slippage ~5-10bps futures) + edge. Use COMMODITY_harness_rerun_prereqs patterns from pending/.

**Wiring:** Add to commodity emitters (e.g. extend commodities_strategies.py or new cot_proxy_emitter.py writing audit_dashboard/data/copper_platinum_cot_picks.json). Register in dashboard (already commodity_carry_momo precedent). COMMODITY 90-day diversification + conc cap (CT=F <=25%). Paper via tv on futures if available. Guard assert in emitter.

**Expectations:** Small n initially (power limits); clean post-guard G2/G5 trustworthy. If passes + admissible → A_passed (diversifier). Salvage path per COMMODITY_GUARD... §3.

---

## 7. Post-Run Consolidation & Promotion Checklist (All Five Candidates)
For each (prioritize ema_cloud + inverse first):

1. Create `A_passed/<slug>_2026-05-21.md` (or B_failed/ with gap analysis) — format per luxalgo_confluence_2026-05-21.md in A_passed/.
2. Update `reports/hypothesis_registry.json` (status, result gates/harness_verdict, hygiene_fix_applied=true, wiring/accrual date, tested_at).
3. Append to `reports/CONTINUAL_STRATEGY_RESEARCH_BASELINE.md` (Firing 12 block).
4. Update living public log: `updates/2026-05-21-continual-6gate-asset-class-research/index.html` (Firing 12 Research Log: ✅ Just Finished, baby candidates, links to this playbook + new markers).
5. Move/copy marker to `reports/continual_research/6gate_validation/A_passed/` or B_failed/.
6. If wiring candidate: enable emitter (env guard), register dashboard, add paper_trading shadow (tv-paper-trade skill for SCALPER/TESTER/etc accounts), optional .github workflow.
7. Parallel: Re-run full `validate_resolved_picks.py --by-asset-class` + framework on entire clean set; update edge_stability_*_COMMODITY/EQUITY/CRYPTO.json; continue 90-day plan expansions (CRYPTO fresh technicals, EQUITY inverses T2, COMMODITY diversification).
8. Daily PnL / G1 note: Use framework --daily-pnl for credible Sharpe (target cost_survival >=0.6 on family). 14-30d shadow accrual for real EV before live sizing.
9. Hygiene re-verify (pollution analyzer) on any new resolved slices.

**If all strong passers:** Batch A_passed promotion + 90-day plan updates (CRYPTO 2-3 babies, EQUITY inverses, COMMODITY copper + non-COT).

---

## 8. Citations (Exhaustive — Every Source + Prior Marker)
**Firing 11 Core (this playbook's direct sources):**
- `FIRING11_BABY_STRATEGIES_90DAY_EXPANSION_2026-05-21.md` (exec summary, candidate inventory §2 with exact meta quotes, strongest 1-2 + outlines §3, A/B §4, 90-day expansions)
- `FIRING11_POST_HYGIENE_EXECUTION_PLAYBOOK_2026-05-21.md` (full structure, prereqs, funding/E-ANON/H-037 patterns, checklist §5, citations §6 — mirrored here)
- `COMMODITY_GUARD_VERIF_SALVAGE_FIRING11_2026-05-21.md` (guard verification exact lines, copper context)
- `CYCLE_2026-05-21_FIRING11_SUMMARY.md` (F11 status, baby in-flight)
- `CONTINUAL_STRATEGY_RESEARCH_BASELINE.md`, `updates/2026-05-21-continual-6gate-asset-class-research/index.html`

**Hygiene (F7-10, all referenced):**
- `pending_fresh_backtest/FIRING10_HYGIENE_MINIMAL_MERGE_DIFF_2026-05-21.md`, `FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py`, `FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py`, `FIRING10_EQUITY_FOREX_EXPANSION_2026-05-21.md`, `FIRING10_H037_WIRING_PR_SCOPE_2026-05-21.md`, `EQUITY_TAGGING_BUG_P0_FIX_PROPOSAL_2026-05-21.md`, `COMMODITY_COT_GUARD_PATCH_firing10_2026-05-21.md`, `FIRING7_TAGGING_HYGIENE_PR_SCOPE_2026-05-21.md`, `FIRING8/9_H037_*_2026-05-21.md`, `FIRING5/4/3` prereqs + B_failed (commodity_cot, equity_vix, forex_stressed, lighter, targeted_candidates...)
- Patched refs: `FIRING8_DASHBOARD_GENERATOR_PATCHED_REFERENCE_2026-05-21.py`

**Core Code & Data:**
- `6GATES_2026-05-21_V1_FREEBUFF.MD` (gates, per-class, tagging bug, daily PnL)
- `reports/hypothesis_registry.json` (format + M-107; E-ANON/H-037 precedents)
- `tools/validate_resolved_picks.py` (parser, asset_class_breakdown, gates)
- `alpha_engine/statistical_validation_framework.py` (daily, bootstrap/WF/MC/MTC)
- `alpha_engine/edge_stability_harness.py` (is_admissible, EFF_MIN etc.)
- Baby: `baby_strategies/*.py + *.meta.json` (exact metrics, SYMBOLS, logic, inverse_wrapper.transform)
- `backtest_framework.py`, `baby_strategies_backtest.py`, `backtest_framework_runner.py`
- Wiring: `audit_trail/dashboard_generator.py:3589 JSON_PICK_SOURCES + _infer_asset_class`, `alpha_engine/data/`, `paper_trading/strategies/ + incubator_strategies.py`, `audit_trail/quality_gates.py`, `alpha_engine/*_harness.py` (crypto/equity/commodity/etf), `copy_trader_intel/multi_asset_copytrader_scraper.py:1843-1865` (guard)
- `alpha_engine/cot_positioning.py` (_is_cot_row_public)
- Prior markers: A_passed/luxalgo..., all Firing 2-11 reports in 6gate_validation/ + pending_fresh_backtest/, `PEER_RESEARCH_CANDIDATES_2026-04-20.md` (baby_strategies/)

**Subagent/Loop Context:** Firing 11 subagents (playbook 019e4a4b-55af..., guard 019e4a4b-6b54..., baby in-flight); this F12 closes baby pending item. All traceable to 6GATES V1 + M-107.

All work directly traceable. Ready for autonomous execution the moment hygiene patch + backfill + validate extensions land (or adapt commands to current parser + post-filter).

**End of Firing 12 New Baby Candidates Execution Playbook.**  
Execute (prioritize ema_cloud + inverse), promote passers to A_passed, update markers/baseline/log/registry/90-day plans, continue the 30m loop (H-017, FOREX, COMMODITY re-agg + non-COT salvage, lighter classes). Research mode only. Cite this file + FIRING11_BABY... + FIRING11_POST_HYGIENE... + COMMODITY_GUARD... + all hygiene markers in Firing 12 summary and future work.

*Marker created 2026-05-21 per convention (Firing 12 prep from Firing 11 baby task). Absolute paths within /home/eaguiar2015/findtorontoevents_antigravity.ca/.*
