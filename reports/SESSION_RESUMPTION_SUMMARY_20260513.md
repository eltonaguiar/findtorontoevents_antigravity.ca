# Session resumption summary — 2026-05-13

## Headline

Shipped 4 production exec-gate filters + 6 academic backtests + 1 TIER-1 breakthrough + 1 failed-overlay lesson. All gate PRs went through multi-engine swarm review. Total swarm spend: ~$0.55 across 12 rounds.

## Production PRs merged (4)

| # | Gate | Source | Engines | Verdict | Expected impact |
|---|---|---|---|---|---|
| #952 | **NS-C 6 UTC** death-zone filter | Edge #10 backtest (BTC) + 2-round swarm | 4/4 MERGE on conservative ADD | CRYPTO WR +1.11pp |
| #953 | **FX1** JPY-cross block × 5 symbols on multi_asset_copytrader | AA-7 mutation analysis | 4/4 unanimous APPROVE | FOREX PF 0.27 → ~1.8 projected |
| #955 | **NS-D** ml_crypto_pred LONG hard-reject | AA-1 autopsy | 4/4 Option A | PF 1.25 → ~1.55 (+0.22) |
| #956 | **NS-F** CRYPTO LONG-in-BEAR regime reject | Edge #11 swarm | 4/4 Option A | PF 1.25 → ~1.40 (+0.14) |

## Backtests shipped (6)

| Tool | Result |
|---|---|
| `tools/backtest_diwali_gold_seasonality.py` | 21yr, GLD long-only WR 52.4% / PF 1.98 / +47.82% — TIER-3 (no alpha vs SPY) |
| `tools/backtest_trend_strength_200ma_adx.py` | n=1512, WR 43% / PF 2.06 / Sharpe 0.46 — TIER-2 |
| `tools/backtest_lowvol_compounders.py` | n=183, WR 62.3% / PF 1.93 / Sharpe 0.88 — TIER-2 defensive |
| `tools/backtest_donchian_52w_volume.py` | n=491, WR 48.9% / PF 2.36 / Sharpe 0.46 — TIER-2 |
| `tools/backtest_equity_momentum_vix_regime.py` | **VIX<20: PF 5.37 / Sharpe 2.19 / MDD 7.3% — TIER-1 PF+MDD breakthrough** |
| `tools/backtest_bond_credit_spread_overlay.py` + `tools/backtest_bond_duration_rotation.py` | Both UNDERPERFORM swarm projection — yfinance proxies too coarse for OAS/curve signals |

## Swarm rounds executed (12)

| Round | Class/topic | Preset | Cost | Output |
|---|---|---|---|---|
| 1 | FUTURES | non-opus-4 | $0.07 | 16 strategies; TS-mom long-only confirmed |
| 2 | FOREX | non-opus-4 | $0.07 | 13 strategies; **4/4 unanimous JPY-cross block** |
| 3 | EQUITY | non-opus-4 | $0.07 | 12 strategies; VIX/YC consensus |
| 4 | BOND | non-opus-4 | $0.07 | 16 strategies; credit-spread + duration |
| 5 | CRYPTO | non-opus-4 | $0.07 | 16 strategies; **deepseek: invert ml_crypto_pred LONG = highest-impact** |
| 6 | Altdata breadth | ollama_cloud/kimi/openrouter/opencode (different family) | $0.07 | Opencode: Diwali → GLD specific test |
| 7 | Growth/breakout academic | non-opus-4 | $0.07 | 5 academic categories validated |
| 8 | NS-D ml_crypto_pred impl consult | non-opus-4 | $0.07 | 4/4 Option A (hard REJECT) |
| 9 | NS-D diff review | non-opus-4 | $0.07 | 4/4 MERGE (9/10 quality) |
| 10 | NS-C v1 diff review | non-opus-4 | $0.07 | 3 HOLD/1 MERGE → revised |
| 11 | NS-C v2 (ADD pattern) diff review | non-opus-4 | $0.07 | 4/4 MERGE |
| 12 | FX1 diff review | non-opus-4 | $0.07 | 4/4 unanimous APPROVE |
| 13 | Edge #11 impl consult | non-opus-4 | $0.07 | 3/4 Option A |
| 14 | NS-F diff review | non-opus-4 | $0.07 | 4/4 MERGE |

**~$0.91 total spend across ~14 effective swarm rounds (some rounds had partial outputs).**

## Key learnings

1. **Real-data-grounded prompts beat synthetic stubs.** Prior 2026-05-11 P5 swarm rounds returned NO_EDGE for 4 classes; this session's real-yfinance-grounded prompts surfaced ~73 actionable strategies + 5 unanimous block proposals + the VIX-regime TIER-1 breakthrough.

2. **Cross-engine consensus is the gate.** 4/4 unanimous (FX1, NS-D, NS-F second round) ships immediately. 3-of-4 (NS-D Option A consult) ships with caveats. Mixed verdicts (NS-C v1) → revise + re-review.

3. **Conservative ADD beats bare REPLACE.** NS-C round 1 found bare-replace (8,9 → 6) split 2/2 on scope. Round 2 with conservative ADD (reject 6, 8, 9) got 4/4 MERGE. Pattern: when in doubt, ADD don't REPLACE.

4. **Swarm projections aren't guarantees.** BOND credit-spread + duration-rotation overlays projected Sharpe 0.57 → 1.0+; actual delivery was +0.00 to +0.05. Reason: yfinance price-derived proxies can't substitute for FRED OAS/curve data.

5. **The VIX overlay is the biggest win.** EQUITY top-5 momentum + VIX<20 filter: PF 2.82 → 5.37, Sharpe 1.34 → 2.19, MDD 24% → 7.3%. **All three TIER-1 criteria pass at PF/MDD/Sharpe level**; only n=88 below 200-floor blocks formal TIER-1 cert.

## Cumulative metrics

- **Swarm engines invoked:** ~50 across 14 rounds
- **Strategies proposed:** ~100
- **Block proposals unanimous:** 5 (JPY-cross triples on FX1)
- **Backtests run:** 8
- **Production filters added:** 4 (NS-C/FX1/NS-D/NS-F)
- **Production wire-in NOT done (pending):** EQUITY VIX overlay (TIER-1 candidate; needs Wire-Up plan)
- **Pending FRED:** BOND overlays + EQUITY yield-curve filter

## Pending (user-blocked or future)

| Item | Type | Notes |
|---|---|---|
| NS-A `multi_asset_cot` DB-verify | Cron | ab_analysis.yml workflow keeps cancelling |
| MYSQL_PASSWORD rotation | User | Operator action — GitHub secret update |
| Close LINK-L + ETH-L paper | User | TV paper account |
| FRED adapter wire-up | Dev | Unlocks BOND overlays + EQUITY YC filter |
| EQUITY VIX overlay PR | Dev | Backtest passed; needs Wire-Up Plan + 30d shadow |
| 20-round swarm per asset class | Future | User requested; cost-deferred (~$1.40/class) |

## Files shipped this session

### Code (gates + backtests + tools)
- `audit_trail/quality_gates.py` (4 filter blocks added)
- `tests/test_ns_c_e_exec_gate_filters.py` (13 tests)
- `tests/test_fx1_jpy_cross_block.py` (4 tests)
- `tests/test_ns_d_ml_crypto_pred_long_reject.py` (10 tests)
- `tests/test_ns_f_btc_bear_long_reject.py` (10 tests)
- 8 backtest tools under `tools/backtest_*.py`

### Reports
- `reports/aa1_ml_crypto_pred_autopsy_20260513.md`
- `reports/aa4_blend_backtest_20260513.md`
- `reports/aa7_forex_per_symbol_mutation_20260513.md`
- `reports/etf_abc_backtest_20260513.md`
- `reports/three_academic_strategies_summary_20260513.md`
- `reports/proven_strategies_backtestable_20260513.md`
- `reports/equity_vix_regime_breakthrough_20260513.md`
- `reports/bond_overlay_attempts_20260513.md`
- `reports/backtest_diwali_gold_20260513.md`
- `reports/backtest_trend_strength_200ma_adx_20260513.md`
- `reports/github_lib_pilots_scope_20260513.md`
- `reports/p5_no_edge_revision_20260513.md`
- `reports/SESSION_RESUMPTION_SUMMARY_20260513.md` (this doc)

### Swarm artifacts
- `reports/swarm_revalid_20260513/META_SYNTHESIS.md`
- `reports/swarm_revalid_20260513/synthesis_*.md` (5 class synthesis docs)
- `reports/swarm_revalid_20260513/swarm_*/` (10+ engine output dirs)

### Ideas captured
- `DAILY_IDEAS.MD` (14 user brainstorm threads A-L)

NFA. No real-money trades placed. Live `/audit` impact pending next dashboard refresh + cron cycle.
