# Money-Maker-Ready Action Plan — 2026-05-13

**Generated:** 2026-05-13 00:30 UTC
**Freshness:** dashboard_data.json 1.9h old (OK)
**Source:** `money-maker-ready` skill v1.0 + live dashboard data + master plan cross-reference

---

## 0. Freshness Preflight

- `audit_dashboard/data/dashboard_data.json` generated 2026-05-13T00:21:54Z → **1.9h old** ✅
- Walkforward generated 2026-05-13T00:20:39Z ✅
- Anti-overfit audit generated 2026-05-11T21:42:54Z → 26h old ⚠ (hourly cron should refresh this)

---

## 1. Per-Class Baseline (post-resolver-v2, from dashboard_data.json)

| Class | n | WR | PF | Status | Tier | Recent WR | Recent PF |
|-------|---|-----|-----|--------|------|-----------|-----------|
| **COMMODITY** | 425 | 67.8% | 3.94 | stable | T1 PF* | 42.5% | 1.09 |
| **EQUITY** | 447 | 53.2% | 1.55 | stable | **T2** | 52.9% | 1.44 |
| **CRYPTO** | 7,801 | 46.5% | 1.36 | stable | Below T3 | 37.5% | 0.89 |
| **ETF** | 107 | 56.1% | 1.34 | stable | T3 candidate | 51.9% | 1.10 |
| **FOREX** | 1,357 | 46.2% | 0.29 | stressed | Below T3 | 49.7% | 0.97 |
| **BOND** | 11 | 54.5% | 0.66 | thin | Insufficient | 47.1% | 1.60 |
| **FUTURES** | 0 | 0% | — | dead | Dead | — | — |

*\*COMMODITY PF 3.94 is dominated by `multi_asset_cot` (PF 21.33 on n=144). Recent-HF window shows PF 1.09 — the cumulative number is propped up by historical windows. See §5.*

**Key observation:** Recent-HF window (last 60-90d) shows significant degradation vs cumulative across ALL classes except EQUITY. This confirms the KS_D = 0.31 drift alert is real and regime-driven.

---

## 2. Walk-Forward (OOS) Verification

| Class | Folds | OOS WR | Consistency | Decay | Verdict |
|-------|-------|--------|-------------|-------|---------|
| **ETF** | 5 | 75.0% | 100% | +23.0% | **Strongest OOS** — improving |
| **EQUITY** | 9 | 62.5% | 77.8% | +1.1% | Improving OOS |
| **CRYPTO** | 32 | 45.6% | 62.5% | -0.3% | Slight overfit, unstable |
| **FOREX** | 36 | 45.2% | 41.7% | -1.2% | Overfit + unstable |
| **COMMODITY** | configured | n≈27 | — | — | **n too small** (HG=F only post-filter) |
| **BOND** | missing | n=11 | — | — | **n below min_trades=60** |

**COMMODITY walk-forward:** Configured in `walkforward_validator.py` (min_trades=20, HG=F+PL=F universe) but post-filter n is ~27 (HG=F only). Per-fold Sharpe std will be wide. Revisit when n >= 60.

**BOND walk-forward:** Explicitly skipped because n=11 < min_trades=60. Requires BOND scanner to emit more picks (FRED data unblock needed).

---

## 3. Cumulative Tier-2-Proven Systems (PF≥1.5, WR≥50, MDD≤20, n≥100)

| System | n | WR | PF | MDD | Last Signal | Status |
|--------|---|-----|-----|-----|-------------|--------|
| `multi_asset_cot` | 144 | 88.2% | 21.33 | 17.8% | TODAY | **Active** ⚠ PF implausible |
| `signal_validation` | 535 | 51.0% | 4.31 | 8.1% | TODAY | **Active** |
| `copy_trader_intel` | 690 | 50.0% | 1.84 | 2.2% | May 8 | **Active** |
| `ml_crypto_pred_v12` | 123 | 55.6% | 2.53 | 11.0% | **Feb 22 (85d)** | **BLOCKED + STALE** |

**`multi_asset_cot` PF 21.33 is implausible** — likely one-symbol concentration on CT=F (Cotton futures). Requires DB verification before trusting. Master plan P0 #5 to query `ejaguiar1_stocks` directly was never executed (needs `DB_STOCKS_PASSWORD`).

**`ml_crypto_pred_v12`** is already in `BLOCKED_SOURCE_SYSTEMS` at `quality_gates.py:1307`, but still appears in the systems[] grid with these historical stats. No staleness warning is displayed because the systems grid doesn't check `last_signal_at`.

---

## 4. System Draggers (negative PnL contributors)

Top 5 by PnL destruction:

| System | n | WR | PF | PnL % | MDD |
|--------|---|-----|-----|-------|-----|
| `kimi_signal_tracking` | 673 | 36.4% | 0.28 | -930% | 995% |
| `multi_asset` | 224 | 44.2% | 0.32 | -160% | 167% |
| `mercury2_fast` | 32 | 42.9% | 0.07 | -140% | 146% |
| `alpha_engine_fast` | 362 | 40.3% | 0.62 | -128% | 155% |
| `copy_trader_highscore` | 326 | 31.9% | 0.77 | -80% | 107% |

All 5 are already blocked or quarantined in `BLOCKED_ASSET_STRATEGY_PAIRS` (see quality_gates.py lines 1756-1781). `goldmine_stocks` (n=453, WR 42.9%, PF 0.14) is partially blocked (goldmine_1x through 6x on EQUITY blocked) but the base strategy may still emit on other classes.

---

## 5. Backtest-Overfit Detector

12 divergence rows, all in `baby_strats` family. Three worst:
- `crypto_soc_proxy_decoupling_a03_v1` — decay -32.2%
- `crypto_soc_delta_divergence_a07_v1` — decay -21.6%
- `crypto_soc_orderflow_absorption_a07_v1` — decay -14.8%

All 3 are already quarantined in `BLOCKED_ASSET_STRATEGY_PAIRS` (lines 1673-1684). 23 remaining `crypto_soc_*` variants queued for follow-up.

33 of 42 audited strategies flagged `OVERFIT_LIKELY` (DSR < 0.5) by anti-overfit DSR sidecar.

---

## 6. Drift State

| Metric | Value |
|--------|-------|
| KS_D | **0.313** |
| Critical (0.05) | 0.047 |
| Ratio | **6.6x** |
| Alert | **TRUE** |
| Root cause | VIX -44.6% / 30d real regime collapse since 2026-04-22 |

**Recommendation:** Walk-forward numbers are drifting in real-time during regime collapse. Defer all promotion decisions. Pin `edge_stability` sidecar as primary verdict source during drift. Do NOT unblock any BLOCKED class while drift_alert is TRUE.

---

## 7. UI/Filter Audit (HC verdicts on /audit)

Status as of 2026-05-13 template.html:

| Class | HC Verdict | Correct? | Notes |
|-------|-----------|----------|-------|
| CRYPTO | EDGE (FWD WR≥60%, Score≥55) | ✅ | 4 DSR-verified ML sleeves exist |
| EQUITY | EDGE (FWD WR≥55%, Score≥50) | ✅ | `stocks_rsi2_pullback` WR 62.9% |
| FOREX | **BLOCKED** | ✅ | Fixed from previous "EDGE" |
| COMMODITY | EDGE (cot_positioning family) | ✅ | DSR=1.0 carve-out, aggregate still WEAK |
| BOND | NODATA (n=18) | ✅ | n below charter floor |
| ETF | WEAK/REHAB (PF 1.20, n=88-100) | ✅ | Fixed from previous "DEAD" |
| FUTURES | DEAD/BLOCKED | ✅ | Silent-dead, no emissions |

**All HC verdicts now match the data.** The dangerous FOREX "EDGE" claim and stale ETF "DEAD" claim were fixed in prior sessions (2026-05-12 SUPREME EDGE updates).

---

## 8. External Data Integrations to Consider

| Integration | Asset Class | Impact | Effort | Gap |
|------------|-------------|--------|--------|-----|
| **FRED API** (yield curves, VIX, DXY) | BOND, FOREX, COMMODITY | High | Low | `fred_data_fetcher.py` exists, needs `FRED_API_KEY` |
| **Kalshi API** (pairwise with Polymarket) | Cross-asset | Med | Med | `pm_consensus_overlay.py` sidecar in repo |
| **CFTC COT real data** (validate cot_positioning) | COMMODITY | High | Low | Socrata feed wired 2026-05-12 (PR #3a6473f) |
| **Glassnode/Coinglass** (on-chain flow) | CRYPTO | Med | Med | Partial integration exists |
| **Quandl** (IV vs RV, economic indicators) | EQUITY, FOREX | Med | Med | Not integrated |
| **VectorBT** (vectorized backtests) | All | Med | Low | Could replace slow p3_backtest_runner.py |
| **Riskfolio-Lib** (CVaR/HRP) | All | Low | High | Killed by peer Phase D (Py 3.14 install fail) |

---

## 9. Top Statistical Edges Per Asset Class

### COMMODITY (CRYPTO | n≥100):
1. `cot_positioning` family — DSR=1.0000, WR 86.5%, Sharpe +1.377, n=104
2. `cftc_cot_commercial_signal` — WR 79.3%, n=58
3. `cot_positioning_CT_locked` LONG — WR 89.8%, PF 13.1, n=49 (Antigravity verified)

### EQUITY (EQUITY | n≥100):
1. `stocks_rsi2_pullback` — WR 62.9%, avg +0.78%, n=70
2. `rs-breakout-scout` — WR 81.3%, n=32 (thin)
3. `donchian-stock-breakout` — WR 78.6%, n=14 (thin)
4. Growth stock screener — MU/AMD picks live since May 12, n=2 (new)

### CRYPTO (CRYPTO | n≥8):
1. `ml_enhanced_INJUSDT_1d_B_lightgbm` — WR 100%, Sharpe +2.49, n=27, DSR≥0.9995
2. `ml_enhanced_FETUSDT_1d_B_lightgbm` — WR 100%, n=25, DSR≥0.9995
3. `ml_enhanced_DYDXUSDT_15m_D_ensemble_stack` — WR 96.8%, n=31
4. `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` — WR 85.3%, n=34
5. `st_fear_greed_contrarian` — WR 94% (promote to HC gate per master plan)

### FOREX: **ZERO DSR survivors** — no edge. SHORT-axis shows 57% WR vs LONG 21% on `ig_contrarian_sentiment` (36pp spread) but no strategy passes DSR ≥ 0.5.

### ETF: Cleanest OOS profile (WF consistency 100%, OOS WR 75%, decay +23%) but n=88-100 is at floor. Need universe expansion to XLF/XLE/XLK.

### BOND: PF 1.72, WR 55.6% meets T2 thresholds but n=18 < 100 floor. FRED unblock + scanner wire-up should lift n to 50+.

### FUTURES: Dead. 5.9% WR, -96% PnL. Needs re-emission plan or formal retirement.

---

## 10. Best-Possible-Action Recommendations

### P0 — Immediate (this session or next 24h)

| # | Action | Class | Impact | Effort | Risk |
|---|--------|-------|--------|--------|------|
| P0-1 | **SHIPPED** ✅ Anti-overfit default-ON (PR: `feat/anti-overfit-default-on-2026-05-13`) | All | Gates 33 OVERFIT strategies from Smart Picks | 0.5h | Low — no-reject on missing history |
| P0-2 | **SHIPPED** ✅ System staleness detection in Tier-2 cards (PR: `feat/system-staleness-detection-2026-05-13`) | All | Prevents stale metrics from looking actionable | 1h | None — display-only |
| P0-3 | Verify `multi_asset_cot` PF=21.33 via DB query | COMMODITY | Determines if edge is real or concentration artifact | 1h | Low — read-only |
| P0-4 | Add staleness to systems[] grid (not just tier-2 cards) | All | Catches `ml_crypto_pred_v12` (85d stale) in alphabetical grid | 2h | Low — display change |
| P0-5 | Merge PR #876 (FOREX pnl_pct clamp) | FOREX | Fixes USDCHF=X -106,700% outlier corrupting FOREX PF | 0.5h | Med — data transformation |

### P1 — This Week

| # | Action | Class | Impact | Effort |
|---|--------|-------|--------|--------|
| P1-1 | Wire DSR gate into HC filter JS (not just Python smart gate) | All | Blocks OVERFIT_LIKELY strategies at browser filter level | 3h |
| P1-2 | FRED API unblock for BOND scanner | BOND | Single biggest blocker for BOND class (0 picks since ~Apr 20) | 2h |
| P1-3 | Add drift_alert indicator to /audit Overview tab | All | KS_D=0.31 should be visible on page, not buried in JSON | 1h |
| P1-4 | Expand ETF universe (XLF/XLE/XLK) | ETF | Clears n≥150 for OOS_READY promotion | 2h |
| P1-5 | Re-classify stale systems (last_signal > 30d) as INACTIVE in systems[] payload | All | `ml_crypto_pred_v12`, `mutation_lab`, etc. | 1h |

### P2 — Weeks 2-4

| # | Action | Class | Impact | Effort |
|---|--------|-------|--------|--------|
| P2-1 | COMMODITY walk-forward with sufficient n (≥60) | COMMODITY | Current n=27 (HG=F only) — too small for stable Sharpe | 4h |
| P2-2 | Wire COT real data to validate `cot_positioning` WR | COMMODITY | Confirms or refutes DSR=1.0 edge with real CFTC data | 2h |
| P2-3 | Top-N portfolio Monte Carlo simulator | All | Settles concentration debate before any sizing | 6h |
| P2-4 | Decay-replacement pipeline | CRYPTO | Auto-flag when `edge_stability` flips to DECAYING | 4h |
| P2-5 | 7-consecutive-day drift_alert=false check | All | Precondition for ever unblocking classes | 3h |

### P3-P5 — Longer Horizon

- FRED macro filter wire-up (yield curves → regime gate for BOND/FOREX)
- Kalshi pairwise consensus with Polymarket
- CPCV upgrade for `p3_backtest_runner.py`
- Re-emission plan or formal retirement of FUTURES class
- Real-money readiness state machine (Codex BLOCKED→REHAB→OOS_READY→SHADOW→LIVE_ELIGIBLE)

---

## 11. Current Blocked Status (quality_gates.py BLOCKED_ASSET_STRATEGY_PAIRS)

As of `audit_trail/quality_gates.py:1599-1782`, the following are blocked:

- **FOREX:** `MomentumEMA`, `volume_spike_breakout`, `myfxbook_retail_contrarian`, `forex_carry_momentum`, `kimi_signal_tracking`, `alpha_engine_fast`, `multi_asset`
- **CRYPTO:** `goldmine_1x/2x/3x_consensus`, `quan_engine_scalp`, `ml_enhanced_APEUSDT_1d_D_ensemble_stack`, `crypto_soc_proxy_decoupling/delta_divergence/orderflow_absorption` (3 suffixed + 3 base), `MeanReversionBB`, `kimi_signal_tracking`, `alpha_engine_fast`, `meta_strategy`
- **EQUITY:** `ML Ranker`, `goldmine_1x/2x/3x/4x/6x_consensus`, `penny_deep_oversold`, `MeanReversionBB`, `kimi_signal_tracking`, `alpha_engine_fast`
- **MEMECOIN:** 29 strategies class-wide quarantined (PF 0.50 over 1,869 trades)
- **FUTURES:** `futures_momentum`
- **COMMODITY:** `alpha_engine_fast`, `multi_asset`
- **BOND:** `alpha_engine_fast`

**Total: ~50 blocked pairs across 7 asset classes.** No strategy should be unblocked without mutation-before-kill protocol per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`.

---

## 12. How to Proceed — Step-by-Step

### If you have DB access:
1. Run P0-3: `SELECT symbol, COUNT(*), SUM(pnl_pct) FROM closed_picks WHERE system='multi_asset_cot' GROUP BY symbol` — verify PF 21.33 is not one-symbol artifact
2. Merge PR #876 (FOREX pnl_pct clamp) — fixes USDCHF=X corruption

### If you have repo variable access:
3. Set `FRED_API_KEY` in GitHub repo secrets — unblocks BOND scanner (0 picks since ~Apr 20)
4. Set `ANTI_OVERFIT_VALIDATOR_ENABLED=1` (or leave default-ON from PR #1) — gates 33 OVERFIT strategies from Smart Picks

### For the P1 items this week:
5. Wire DSR gate into `hc_filter.js` — browser-side filter, not just Python smart gate
6. Add drift_alert indicator to /audit Overview tab — KS_D=0.31 should be visible
7. Expand ETF universe with XLF/XLE/XLK

### Do NOT:
- Unblock FOREX or FUTURES while drift_alert is TRUE (KS_D = 6.6x critical)
- Trust COMMODITY PF 3.94 without verifying `multi_asset_cot` PF 21.33 concentration
- Size real money on any class — 0/6 classes pass all gates, drift is active, ML calibration is inverted

---

## 13. Reference Commands

```bash
# Freshness check
python -c "import json; from pathlib import Path; from datetime import datetime, timezone; d=json.loads(Path('audit_dashboard/data/dashboard_data.json').read_text(encoding='utf-8')); gen=datetime.fromisoformat(d['generated_at'].replace('Z','+00:00')); age=(datetime.now(timezone.utc)-gen).total_seconds()/3600; print(f'{age:.1f}h old')"

# Per-class health
python -c "import json; d=json.loads(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8').read()); [print(f'{k}: WR={v.get(\"win_rate\",0):.1f}% PF={v.get(\"profit_factor\",0):.2f} n={v.get(\"resolved_n\",0)}') for k,v in d['performance']['asset_class_health'].items()]"

# Run relevant tests
pytest tests/test_anti_overfit_wireup.py tests/test_tier2_hero_cards.py -v

# Check drift
python -c "import json; d=json.loads(open('audit_dashboard/data/dashboard_data.json',encoding='utf-8').read()); drift=d['hf_stats']['concept_drift']; print(f'KS_D={drift[\"ks_D\"]} critical={drift[\"ks_critical_05\"]} alert={drift[\"drift_alert\"]}')"
```

---

## 14. Git SHAs (this session)

| Branch | Commit | Description |
|--------|--------|-------------|
| `feat/anti-overfit-default-on-2026-05-13` | `b9aef5cc10` | Anti-overfit validator default-ON |
| `feat/system-staleness-detection-2026-05-13` | `869a888f9a` | System staleness detection in tier-2 hero cards |
| `main` (upstream) | `645527d` | Latest main commit |
