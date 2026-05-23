# FOREX Asset-Class Deep-Dive — 2026-05-12

Investigator `a1d9ac39ae02d1a47` output. FOREX = sub-floor on /audit
(stressed status, PF 0.29, WR 45.6%, PnL -1029.57% on n=1343 resolved).
Class is BLOCKED per hedge_fund_sprint set in
`audit_trail/quality_gates.py`.

## Current state

- Status `stressed`, `sizing_allowed: false`
- Resolved n=1343, WR 45.6%, PF 0.29, cumulative PnL -1029.57%
- Charter thresholds: min_stable_n=100, min_candidate_n=50

**Currently BLOCKED strategies** (`quality_gates.py:1530-1742`):
- `signal_validation`, `MomentumEMA`, `volume_spike_breakout`,
  `myfxbook_retail_contrarian`, `forex_carry_momentum`
- `quan_engine_swing` LONG-only

**Temp-unblocked** (expiry 2026-05-22): `ig_contrarian_sentiment` (Sharpe 5.87,
phantom-data gate)

## Symbol coverage (19 pairs at config.py:515)

- **Majors (7):** EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, NZDUSD, USDCHF
- **JPY crosses (5):** EURJPY, GBPJPY, AUDJPY, NZDJPY, CADJPY
- **Minor crosses:** EURGBP, EURAUD, GBPAUD, AUDNZD, EURCHF, GBPCHF, USDSGD
- **No emerging-market exotics** — correct call given current PF 0.29 (exotic spreads would kill small wins)

## Root cause analysis

1. **Primary culprit** (now FIXED): resolver v1 live-close bug
   (`outcome_resolver.py:384-405`) mislabeled ~1700 non-crypto picks across
   15 strategies. Fixed v2 2026-04-28.

2. **Secondary** (post-fix): **direction-axis edge** — SHORT side is healthy,
   LONG side is anti-edge:
   - `ig_contrarian_sentiment`: SHORT 57.1% WR vs LONG 20.9% (36pp spread)
   - `myfxbook_retail_contrarian`: SHORT 46.2% vs LONG 10.5% (36pp)
   - `cta_cross_asset_tsmom`: SHORT 60.0% vs LONG 35.3% (25pp)
   - `forex_rsi2_mean_reversion`: SHORT 27.3% vs LONG 2.7% (25pp)

3. **Tertiary:** fixed-pip stops too tight in volatile sessions; no ATR
   adjustment.

4. **Symbol hotspot:** `kimi_signal_tracking` (n=177, PF 0.26, MDD 994.95%)
   was a USDCHF-dependency disaster — already BLACKLISTED commit 4a2d337a5dc.

## External-model candidates

| Library | Verdict |
|---|---|
| **stefan-jansen/machine-learning-for-trading** | Ch. 12-18 deep-RL for FX; worth if time-series regime models beat HMM. Data-hungry. |
| **polyrabbit/forex-quantitative-trading** | Classical MA/RSI/MACD — skip, we have these + mutation protocol. |
| **QuantConnect/Lean** | FX algos in C# + history. Worth for backtesting validation; regime-terminal already covers similar ground. |
| **AI4Finance-Foundation/FinRL** | DRL + FX env. High-merit; rolling Sharpe softmax ensemble proven in FinRL 2024 (R004: Sharpe +0.21). |
| **hudson-and-thames/mlfinlab** | Already integrated (`alpha_engine/integrations/`); CPCV/PBO not yet leveraged — queue after orphan backlog. |

## 5-step rehab plan

- **Step A** — Unblock `ig_contrarian_sentiment` SHORT-only (kill LONG; 57.1% WR vs 20.9%). 14-day observation window, exit at 20 trades if WR ≥50%.
- **Step B** — Scout pair: EURUSD + USDJPY only (tight spreads, high liquidity). Block exotics, JPY crosses (spread drag at PF 0.29). Session gate: London/NY overlap 07:00-17:00 UTC.
- **Step C** — 30-day forward observation + regime filter. Use existing `bayesian_regime_reference.py` or HMM state from `hmm_regime.json`. Gate: only initiate trades in TRENDING (not RANGING) regime. Cross-check vs DXY regime.
- **Step D** — Expand to 2 more pairs (GBPUSD, AUDUSD) if Step C ≥50% WR. n≥50 requirement before promotion.
- **Step E** — Graduation criterion: WR ≥50% on expanded universe (n≥100 clean post-noise-filter); PF ≥1.2 (vs current 0.29); MDD <15% on live paper.

## Expected impact on /audit

- **Short term (14d):** Step A SHORT-only emission could add 10-20 SHORT picks/week if `ig_contrarian_sentiment` unblocks cleanly.
- **Medium term (30-60d):** EURUSD + USDJPY paired with regime-gate could lift FOREX WR from 45.6% → 50-55%, PF from 0.29 → 1.0+ on a curated subset.
- **Long term (3-6mo):** If Step D clears, FOREX can graduate from BLOCKED back to T2-CANDIDATE.

## Refs

- `audit_trail/quality_gates.py:1530-1742`
- `alpha_engine/config.py:515`
- `reports/deep_dive_FOREX_mutation_2026_05_04.md` (existing)
- `feedback_noncrypto_resolver_live_close_bug.md` memory
- `fix_FOREX_20260505T005402Z.md` (session gating)
- Investigator `a1d9ac39ae02d1a47` 2026-05-12

## NFA

Research surface only. The direction-axis SHORT edge is the most evidence-rich
path; do NOT generalize to LONG-side until Step C clears.
