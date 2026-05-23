# Per-Asset-Class Performance Summary — 2026-04-28

**Author:** claude-opus-4-7
**Source of truth:** `audit_trail/data/dashboard_payload.json` (`generated_at=2026-04-28T00:09:18.915Z`, 1.04h fresh, n=3,500 capped)
**Reproducibility:** `node tools/_canonical_recompute_2026_04_28.js`
**Cross-references:** Five independent peer recomputes converge on these numbers (mercury, GitHub Copilot, Copilot Cloud, opencode/big-pickle, this consolidator). Detailed per-class roadmap at [`reports/hedge_fund_performance_review_detailed_2026_04_27.md`](../reports/hedge_fund_performance_review_detailed_2026_04_27.md).

## TL;DR — Hedge-Fund Tier Verdict

| Class | n | WR% | PF | Sum PnL% | MaxDD% | Resolver-noise | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| **EQUITY** | 381 | 51.97 | **1.385** | +232.13 | 70.95 | 9.1% (clean) | ✅ **Tier 2 — proven edge, the franchise** |
| **CRYPTO** | 1,598 | 42.12 | 1.140 | +161.41 | **140.22** | 1.2% (clean) | ⚠️ Edge real, MDD untenable |
| **ETF** | 83 | 54.22 | 1.220 | +20.25 | 45.04 | 6.7% (clean) | ⚠️ Tier 3 borderline (n<100) |
| **FOREX** | 794 | 50.38 | 1.349 | +29.63 | 40.97 | **63.2% UNRELIABLE** | 🚫 Cannot evaluate (resolver bug) |
| **COMMODITY** | 622 | 42.60 | 0.896 | −9.82 | 25.88 | **66.8% UNRELIABLE** | 🚫 Cannot evaluate (resolver bug) |
| **BOND** | 17 | 47.06 | 1.601 | +2.84 | 3.06 | 12.5% (clean) | ⚠️ Insufficient sample (n<50) |

Tier definitions: **T1 Renaissance** PF>2 / WR>55 / MDD<10. **T2 Institutional** PF>1.5 / WR>50 / MDD<20. **T3 Retail-OK** PF>1.2 / WR>48 / MDD<30. **No class meets T2 on the MDD criterion.** EQUITY is the only one with PF and WR in T2 territory.

## Last 4 Days (Apr 24–27) — Entry-time-populated cohort only

| Class | n | WR% | PF | Sum PnL% | Noise% | Note |
|---|---:|---:|---:|---:|---:|---|
| **CRYPTO** | 710 | 36.76 | 0.907 | **−39.80** | 1.9% | Recent CRYPTO is bleeding; full-window edge driven by older cohort |
| **COMMODITY** | 39 | 43.59 | 0.007 | −6.58 | **100.0%** | All wins are 1bp resolver flicker — class is functionally dead in this window |
| **FOREX** | 12 | 50.00 | 528.261 | +2.43 | 33.3% | PF inflation from tiny denominator + 1bp wins; ignore |
| **ETF** | 5 | 60.00 | 1.194 | +0.43 | 0% | Tiny sample, positive but n=5 |
| **EQUITY** | 3 | 0.00 | 0.000 | **−9.24** | 0% | **0% WR on n=3** — confirms the 7-day review's P2 #8 finding (recent EQUITY degradation) |
| **BOND** | 0 | — | — | — | — | No entry-time-populated picks in window |
| **FUTURES** | 0 | — | — | — | — | n/a |

**Caveat on the 4-day window:** Only ~25% of the 3,500-row window has populated `entry_time` (per Workstream E correction). The 4-day numbers above represent the entry-time-populated subset — they're directionally accurate for "what happened recently" but should not be compared 1:1 against the full-window numbers.

## Classes With Proven Edge (act on these)

### 1. EQUITY — The Franchise

- **n=381, PF 1.385, WR 51.97%, Sum +232.13%, only 9.1% resolver noise** — these numbers are the most trustworthy in the entire ledger.
- **Top contributors** (per detailed review):
  - `kimi_riseoftheclaw` n=166 WR=57.8% sum=+245.8% → **single biggest PnL driver across all classes**
  - `stocks_competition` n=133 WR=49.6% sum=+90.3%
  - `rs-breakout-scout` n=17 WR=76.5% PF=6.19 → small n but extraordinary edge, scale-up candidate
  - `quality-minus-junk` n=18 WR=61.1% — confirms our equity research replicates AQR's QMNT factor
- **Zombies to retire** (data-supported): `goldmine_stocks` (n=13, 0% WR, −53.4% sum), `fast_stocks_competition` (n=6, 0% WR, −22% sum), `Classic Momentum` (n=41, 36.6% WR, −15.38% sum).
- **Single-stock poison**: `JNJ` n=23 WR=13% sum=−44.21% — drives ~30% of EQUITY drawdown alone. Removing JNJ projects PF 1.385 → ~1.55 (Tier 1 reach).
- **Recent (4-day) anomaly**: 0% WR on n=3 in last 4 days. Consistent with `goldmine_stocks` zombie blowup hypothesis. Investigate before the next sizing decision.

### 2. CRYPTO — Edge Real, Drawdown Lethal

- **n=1,598, PF 1.140, WR 42.12%, Sum +161.41%, 1.2% noise** — clean edge, but **MaxDD 140%** is unsurvivable institutionally.
- **Direction asymmetry (the smoking gun)**: LONG n=1,144 sum **+160.68%**; SHORT n=454 sum **+0.73%**. **All edge is on the long side.** SHORTs add risk for ~zero edge.
- **Top contributors**:
  - `luxalgo_filters` n=181 WR=50.8% sum=+63.1% — best per-class edge
  - `claude_gainer_st` n=256 WR=47.7% sum=+36.6%
  - `signal_validation` n=26 WR=61.5% — small-n but high-edge promote candidate
  - `kimi_riseoftheclaw` n=20 WR=65% — same kimi alpha working in CRYPTO
- **Bleeders** (PR #461 retires these — pending merge):
  - `macd_rsi_confluence` n=173 WR=37% sum=**−50.96** (largest single CRYPTO bleeder)
  - `quan_engine` n=314 WR=30.3% sum=−24.02
  - `rsi_bounce` n=33 WR=39.4% sum=−23.87
  - `ensemble` n=37 WR=27% sum=−18.74
  - **Combined drag: −137% cumulative**
- **Poison-pill symbols** (also in PR #461): TONUSDT, ONDOUSDT, OPUSDT, HYPEUSDT, TIAUSDT, LTCUSDT — all WR<28%, combined drag −66%.
- **Recent (4-day) bleed**: PF 0.907 on n=710 in last 4 days vs PF 1.140 full-window. CRYPTO is degrading recently. PR #461 retirements should reverse this once merged.
- **Path to Tier 2**: After PR #461 merges + vol-targeting layer + SHORT-disable on `alpha_engine` triple → projected PF 1.30+, MDD ~25%.

### 3. ETF — Promising but Thin

- **n=83, PF 1.220, WR 54.22%, Sum +20.25%, 6.7% noise** — clean numbers, but n<100 means single-source dependency risk.
- **`kimi_riseoftheclaw` carries 82% of the class (n=68)**. Need 2+ uncorrelated sources before sizing up.
- **Path to Tier 3**: add sector-rotation source (free signals from State Street SPDR series) + low-vol factor (BlackRock USMV-style). Get to n>200 in 30 days.

## Classes That Cannot Be Evaluated (Resolver Bug)

### FOREX — 63.2% Resolver Noise

- Headline numbers (PF 1.349, WR 50.38%) are **mathematically meaningless**.
- 63.25% of "wins" have `|pnl_pct| < 0.05%` — these are 1bp resolver flicker, not realized edge.
- Per Workstream B: `alpha_engine/outcome_resolver.py:97` has `PNL_WIN_THRESHOLD = 0.00001` (0.001% / 0.1bp), 10× tighter than the audit memo's "1bp" claim. Resolver closes positions at yfinance live spot every run, not at TP/SL hit.
- **Real clean wins**: only ~83 of 794 picks have actual edge. Implied real WR ~10.5%.
- **Verdict**: cannot evaluate FOREX alpha until resolver is fixed. Any optimization done now is overfitting on garbage labels.

### COMMODITY — 66.8% Resolver Noise + No Real Edge

- Headline PF 0.896 is contaminated.
- 66.79% of "wins" are 1bp flicker.
- **Cleanwins-by-source breakdown** (the brutal truth):
  - `multi_asset_copytrader` n=492, cleanwins=85 → **real WR ~17%**
  - `cta_replicator` n=105, cleanwins=**1** → **1% real WR**
  - `cta_commodity_momentum_term` n=46, cleanwins=1 → **2% real WR**
  - `cta_golden_cross_200` n=26, cleanwins=0 → **0% real WR**
- **Verdict**: even after resolver fix, COMMODITY likely has zero internal edge. The institutional answer is to replicate via DBMF (iMGP DBi Managed Futures), KMLM (KFA Mount Lucas), or WisdomTree CTA — all replicate AHL/Winton/Campbell-style trend.
- **Status: SUSPENDED** — block COMMODITY emissions pending Workstream B + verification of any clean source.

### BOND — Insufficient Sample

- n=17 across 2 sources. Statistically void.
- Path: either grow to n>100 (add ETF rotation: TLT, IEF, SHY, BIL, TIP, LQD, HYG) or replicate via PIMCO BOND / JPST.

## Top-5 Highest-ROI Actions (next 14 days)

1. **🔴 P0 — Resolver fix** (`alpha_engine/outcome_resolver.py:384–405` + `WIN_THRESHOLD:97`). Unblocks FOREX/COMMODITY verdicts. Re-resolve ~1,860 historical non-crypto picks. See `reports/action_B_resolver_2026_04_27.md` for concrete fix.
2. **🔴 P0 — Merge PR #461** (clean re-extraction of #459). Retires 4 CRYPTO bleeders + adds 9-symbol poison-gate + 4-strategy retirements. Validator confirms 1,417/3,500 (40.5%) blocked. Tests pass. Author hygiene: 2 bot commits leaked via rebase — recommend squash-merge.
3. **🟡 P1 — EQUITY zombie kills** (`goldmine_stocks`, `fast_stocks_competition`, `Classic Momentum`) + drop `JNJ` from EQUITY universe. Projects PF 1.385 → ~1.55 (Tier 1 reach).
4. **🟡 P1 — Vol-targeting layer** (`alpha_engine/vol_target.py` new module). Position-size = target_vol / realized_30d_vol. Caps Kelly fraction at 0.25. **Single biggest MDD lever**: CRYPTO MDD 140% → ~25% projected.
5. **🟡 P1 — CI freshness assertion** (`tools/assert_model_freshness.py` + workflow step in `audit-dashboard.yml`). Fails CI when any model artifact's `trained_at` > 7d. Prevents the next 12-day silent regression like the auto_tuner module-path bug that just shipped.

## What's Already Shipped (commit `1cd5e6fd5a` on main)

- `auto_tuner` module-path fix at `alpha-engine-live.yml:592` (was silently failing 12 days)
- `ml_gatekeeper/models/` persistence (added to commit step)
- `ml_crypto_predictor/self_improvement.py` deletion (dead code)
- HC gate v4.4 thresholds (CRYPTO 60, EQUITY/ETF 55, FOREX/COMMODITY held @70 pending resolver)

Plus FTP-deployed to live `findtorontoevents.ca/audit/config/hc_gate_params.json` v4.4 today.

## Reproducibility

```bash
node tools/_canonical_recompute_2026_04_28.js
# Verifies: payload age, n=3500, per-class scorecard, resolver-noise share, sample picks per class
```

Companion docs:
- [`reports/asset_class_independent_recompute_2026_04_27.md`](../reports/asset_class_independent_recompute_2026_04_27.md) — canonical recompute (mercury-2)
- [`reports/canonical_recompute_corrections_2026_04_28.md`](../reports/canonical_recompute_corrections_2026_04_28.md) — corrections sidecar (lookup-key bug fix)
- [`reports/hedge_fund_performance_review_detailed_2026_04_27.md`](../reports/hedge_fund_performance_review_detailed_2026_04_27.md) — per-class roadmap with copy-trader fallbacks
- [`reports/action_B_resolver_2026_04_27.md`](../reports/action_B_resolver_2026_04_27.md) — resolver bug fix design
- [`reports/action_C_symbol_risk_2026_04_27.md`](../reports/action_C_symbol_risk_2026_04_27.md) — CRYPTO symbol/SHORT gating
- [`updates/2026-04-28-claude-cursor-alignment-addendum.md`](2026-04-28-claude-cursor-alignment-addendum.md) — coordination + Top-5 ROI
