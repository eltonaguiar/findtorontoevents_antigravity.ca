# Kimi Agent Swarm — Prediction Edge Audit Response

**Source:** `swarm_runs/kimi_prediction_edge_audit_2026_05_03/` (17,500 words, 12 dimensions, 91 citations)
**Authors:** Kimi Agent Swarm (verbatim import; this doc is YY-KIMI-COMMIT's synthesis only)
**Date received:** 2026-05-03
**Subagent:** YY-KIMI-COMMIT
**Companion fix:** template.html:1813-1825 nested-comment bug — separate subagent assigned

---

## TL;DR — 9 Key Verdicts

1. **Equity is the ONLY genuine edge.** OOS Sharpe +3.527, PF 1.72, n=136+, all 5 gates passed. Crown jewel.
2. **Best UI filter = Verified Alpha + High Conviction (+ R:R 1.5+).** 65-68% WR (triple-filter pushes 66-70%). Currently surfaces 0-2 picks/day. Empty result is a feature, not a bug.
3. **Composite scoring system is BROKEN.** ml_score r=-0.012 (noise), regime_bonus r=-0.115 (anti-predictive), 4/9 deciles invert vs realized PF. Repair before trust.
4. **HTML bug confirmed at template.html:1813-1825** (nested comments leaking text on US Equity Picks tab). Fix = single `<!-- UEPS mount point -->`. Owned by separate subagent.
5. **Strategies — Ban / Invert / Scale:**
   - **BAN:** `unknown` source-system (18% WR, dragging crypto), `quan_engine` MATIC ghost rows
   - **INVERT (paper first):** myfxbook_retail_contrarian, futures_momentum, goldmine_1x_consensus, MomentumEMA
   - **SCALE:** signal_validation (PF 2.58), Equity Verified Alpha + HC stack
6. **Penny stocks: NO.** Avg returns -24% to -27% annual; median -37%; institutional firms exclude. Max 5% if ever.
7. **Meme coins: NO.** 99.7% risk of ruin, 0.4% Pump.fun profitable, Kelly = -244%. Exclude entirely.
8. **Hedge-fund 6-gate MVP ($1,500, 90 days):** PSR > 0.95, DSR > 0.95, n >= 200, cost-modeled (slippage + vig + fees), single-source-of-truth files, correlation-guard. Full institutional transform = $32K-$78K / 12mo.
9. **Real-money safe stack: Equity + Verified Alpha + High Conviction + R:R 1.5-2.0 + Quarter-Kelly + -5% stop = honest 15-25% annual.** Anything outside this is experimental.

### THE GOLDEN FINDING — R:R 1.5-2.0 Band

The single highest-impact operational fix that requires **zero retraining, zero new data, zero new code**:

> **Filter every pick down to R:R between 1.5 and 2.0.**
> Realized PF in this band: **5.81**. Kelly fraction: **+47.2%**. Avg PnL per trade: **+4.98%**.
> All other R:R buckets are flat-to-negative.

Hard floor at 1.5, hard ceiling at 2.0. (Above 2.0, picks are reach-trades; below 1.5, vig eats the edge.)

---

## Asset-Class Verdict Matrix

| Class      | OOS Sharpe | PF   | n     | Verdict     | Note |
|------------|------------|------|-------|-------------|------|
| EQUITY     | +3.527     | 1.72 | 136+  | **SAFE**    | Only true edge. Scale within Quarter-Kelly. |
| ETF        | +6.368     | 1.24 | 87    | **CAUTION** | Sharpe is artifact of n=12 folds; DSR would deflate to 2.0-3.0; 10.8 decay. |
| CRYPTO B   | mixed      | 1.28 | large | **CAUTION** | Workhorse. After cutting `unknown` + `quan_engine` drag. |
| CRYPTO S   | negative   | 6.80 | 27    | **CAUTION** | Survivorship illusion. Don't scale until n>=50. |
| BOND       | n/a        | 1.72 | 18    | **CAUTION** | PF/WR pass but n far below charter floor. |
| COMMODITY  | weak       | 1.78 | 750   | **DANGEROUS** | 58% flat exits = strategy finds no real setups. WR 46.9% sub-floor. |
| FOREX      | -1.406     | 0.27 | 1169  | **DANGEROUS** | Resolver fix revealed (didn't cause) the loss. HALT, reassess June 1. |
| PENNY      | n/a        | <1   | n/a   | **DANGEROUS** | Wealth-destruction baseline. Exclude. |
| MEME       | n/a        | n/a  | 41    | **DANGEROUS** | 99.7% risk of ruin. Exclude. |

---

## Kimi 12 Dimensions — One-Line Summaries

| # | Dimension | Bottom Line |
|---|-----------|-------------|
| 01 | Per-Asset-Class Edge | Only Equity passes 5/5 gates; ETF Sharpe is small-n artifact; Forex/Commodity/Meme/Penny fail. |
| 02 | F-Score vs Score vs Composite | Composite has 4/9 decile inversions; ml_score r=-0.012 is noise; regime_bonus r=-0.115 is anti-predictive. |
| 03 | Optimal UI Path | Verified Alpha + High Conviction + R:R 1.5+ -> 66-70% WR but only 0-2 picks/day; empty is correct. |
| 04 | Strategy Failure & Inverse | 4 strategies are profitably invertible (myfxbook_retail_contrarian, futures_momentum, goldmine_1x_consensus, MomentumEMA); paper-trade first. |
| 05 | Backtesting Methodology | Need DSR/PSR + walk-forward + 90-day regime coverage; current pipeline lacks survivorship-bias-free data. |
| 06 | Penny Stock Profitability | -24% to -27% avg annual; survivorship-biased OTC data; institutional exclusion is correct prior. |
| 07 | Meme Coin Predictability | 99.7% risk of ruin, Kelly=-244%, social APIs lag pumps by 15-60 min. Exclude. |
| 08 | Risk & Position Sizing | Quarter-Kelly only; R:R 1.5-2.0 band Kelly +47.2%; all other bands ~0%. |
| 09 | HTML Bug & Technical | template.html:1813-1825 nested comments visible on US Equity Picks tab; trivial fix. |
| 10 | Recent Code Change Impact | 6 days post-resolver-v2 is statistically meaningless; need 200-500 trades or 3-8 weeks. |
| 11 | User Safety Guide | Honest 15-25% annual achievable on Equity + HC + R:R 1.5-2.0 + Quarter-Kelly + -5% stop. |
| 12 | Hedge Fund Transformation | Platform has ~5% of institutional infrastructure despite 119K commits; $1.5K MVP vs $32K-78K full transform. |

---

## Cross-Verification Status (from `research/quant_audit_cross_verification.md`)

**HIGH confidence (2+ agents, independent sources):**
- HC-1 Equity is only genuine edge
- HC-2 R:R 1.5-2.0 is the only profitable zone
- HC-3 Composite scoring is broken
- HC-4 Meme coins must be excluded
- HC-5 Penny stocks are wealth-destruction
- HC-6 HTML nested-comment bug exists at template.html:1813-1825
- HC-7 6 days insufficient to assess resolver fix
- HC-8 Verified Alpha + High Conviction is optimal UI

**MEDIUM confidence (single authoritative source):**
- MC-1 ETF Sharpe 6.368 = tiny-sample artifact (needs DSR)
- MC-2 4 strategies profitably invertible (needs paper-trade)
- MC-3 ~5% institutional infrastructure (estimate)
- MC-4 ml_score >= 0.90 is optimal threshold (CONFLICT — see C-1)

**Conflict zones:**
- C-1 Optimal ml_score threshold: 0.90 (Action Plan) vs 0.70-0.79 (Dim02 Calibration). Resolution: prefer trust_score >= 5 over any ml_score gate.
- C-2 Forex HALT vs MONITOR: Dim01 says HALT (PF 0.27), Action Plan T3 candidate (PF 3.59 trusted subset). Resolution: HALT until June 1.
- C-3 Crypto S-Tier SCALE vs ABANDON: PF 6.80 with n=27 is meaningless. Resolution: CAUTION; require n>=50 before any size-up.

---

## Action Queue (ranked)

**HIGH (do this week):**
1. Apply R:R 1.5-2.0 hard floor/ceiling to all gating logic — biggest no-retrain win in the whole audit (PF 5.81, Kelly +47.2%).
2. Fix `template.html:1813-1825` nested-comment leak — separate subagent assigned, blocks UEPS render correctness.
3. Ban `unknown` source-system (18% WR) and quarantine `quan_engine` MATIC ghost rows — restores crypto aggregate trustworthiness.
4. HALT Forex live exposure; reassess June 1 with >=200 post-resolver-v2 closed trades.

**MEDIUM (do this month):**
5. Replace composite score in UI gating with `trust_score >= 5` until composite is recalibrated (isotonic regression / Platt scaling).
6. Paper-trade the 4 invertible strategies (myfxbook_retail_contrarian, futures_momentum, goldmine_1x_consensus, MomentumEMA) for 30 days before any live capital.
7. Stand up the 6-gate MVP ($1,500, 90 days): PSR > 0.95, DSR > 0.95, n >= 200, cost-modeled, single-source-of-truth, correlation-guard.

**LOW (queue for next quarter):**
8. Replace yfinance free tier with Polygon.io / CCData for survivorship-bias-free data (~$150-500/mo).
9. Decide retail-vs-institutional lane (Dim12 binary): no middle path is viable.
10. De-emphasize n<50 strategies in dashboard ranking (sort by statistical confidence, not raw PF).

---

## Files Imported

- 5 final reports (md + 3 docx)
- 1 outline + 4 plan/structure docs
- 7 section drafts (sec01 through sec09_10)
- 12 dimension research files + cross-verification + insight + file-analysis
- 5 supporting CSVs (btc/doge/pepe/shib daily + meme_prices)

All under `swarm_runs/kimi_prediction_edge_audit_2026_05_03/`. See that directory for verbatim Kimi authorship; this RESPONSE.md is the only synthesis layer.
