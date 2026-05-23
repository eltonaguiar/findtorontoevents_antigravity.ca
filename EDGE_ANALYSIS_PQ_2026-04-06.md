# Quant Alpha & Edge Analysis: Enhancing Score-PnL Correlation
**Date**: 2026-04-06  
**Author**: Antigravity (Quant Subagent)  
**Status**: DRAFT / RECOMMENDATION  

## 1. Executive Summary: The Correlation Problem
A quantitative audit of **1,879 closed crypto trades** demonstrates a structural disconnect between the "Top Scores" and actual PnL outcome:
- **Spearman Rank Correlation (Score vs PnL)**: **0.1541** (Weak Positive).
- **Spearman Rank Correlation (Trust Score vs PnL)**: **0.3523** (Moderate Positive).
- **Agreement Count Paradox**: r = **-0.0753** (Negative). Increasing system consensus slightly *decreases* expected PnL.
- **Top Score Decay**: Picks in the 70-84 score range show a win rate of **37.5%**, significantly lower than the 55-69 range (**59.9%**).

**The Verdict**: Our highest scores are currently overfitted or reflect "crowded" consensus that lacks directional edge. We need to shift from a heuristic-weighted model to a **Bayesian Beta-Adjusted Model**.

---

## 2. Review of FindTorontoEvents.ca/Audit Tracks

### A. Active Picks (The General Feed)
- **Current Logic**: Baseline 50. Penalties for staleness, low R:R, and "toxic combos" (e.g., `enhanced_ml_a_xgboost` + LONG).
- **Core issue**: High volume (97.8% Sandbox) leads to "signal noise." 
- **Performance**: High variance. The -2944% PnL outlier in `TRXUSDT` suggests lack of hard stops at the scanner level.

### B. Verified Alpha (The Elite Tier)
- **Classification**: Only strategies with **n >= 50, WR >= 55%, PF >= 1.3** survive this gate.
- **Top Performers**: `st_fear_greed_contrarian` (CROWN JEWEL), `mastered_pair` (e.g., `claude_gainer` + `SOLUSDT`).
- **Edge**: High reliability but low frequency (only 5 strategies out of 976 currently qualify).

### C. Smart Picks (The Institutional Filter)
- **Classification**: High-conviction picks filtered by `passes_smart_gate`.
- **Thresholds**: 60 (Crypto), 50 (Equity), 75 (Forex).
- **Edge**: Focuses on **preferred pairs** and **cross-asset confluence** (+8 to +10 bonus).

### D. Crypto vs Non-Crypto
- **Crypto**: Dominated by majors (`BTC`, `ETH`) and high-performing alts (`FET`, `ALGO`).
- **Equity**: Strong performance (+65% WR) when filtered for high PF/WR. Stocks like `NFLX`, `ARM`, `GOOG` have shown consistent "Goldmine" edge.
- **Forex**: **Catastrophic** baseline (WR 16%). Forex scoring requires a significant overhaul or extreme restrictive gating (Score > 75).

---

## 3. The Implementation Plan: "Bayesian Alpha Gate"

To make top scores "really correlated" to higher PnL, I propose the following **Quant Edge** implementation in `quality_gates.py`:

### Step 1: Trust-Weighted Feature Blending
Instead of a flat Tech + PnL blend, we use the **Historical Correlation Factor (HCF)** as a multiplier for each field:

| Field | Current r | Prop. Weight |
|---|---|---|
| Trust Score | 0.35 | 0.60 |
| Tech Score | 0.15 | 0.25 |
| Confidence | 0.14 | 0.15 |

### Step 2: The "Crowded Trade" Penalty
Apply a non-linear penalty for excessive agreement:
- `agreement_count > 6`: **-10 score** penalty.
- `agreement_count > 9`: **-20 score** penalty (Signal for "Retail Peak").

### Step 3: Regime Multiplier
Picks that oppose the global regime (`regime_label`) receive a -30% score haircut.
- **Trend-Following**: [BULLISH REGIME] + [LONG PICK] = **1.2x Score**.
- **Mean-Reversion**: [CHOP REGIME] + [RSI2/CONNRSI SIGNAL] = **1.2x Score**.

### Step 4: Symbol Affinity Bonus (Winner Momentum)
Assets currently in a "Mastered" state (e.g., `FETUSDT` with its 88.4% WR) receive a **+12 volatility-adjusted bonus**.

---

## 4. Deep Research: The Hedge Fund Gap (Institutional Path)

To reach consistent hedge-fund-level quality, the following "Remaining Gaps" must be closed in the next cycle:

### A. Beta-Neutral Alpha harvesting
96.5% of our system's PnL is currently tied to a single asset (`TRXUSDT`). This is a **Concentration Risk Failure**. 
- **Action**: Implement **Portfolio Beta Balancing**. Each long position must be offset by a short in a correlated asset to harvest "pure alpha" and survive broad market drawdowns.

### B. Regime-Aware Calibration (Beta Decay)
Our current strategies show a **0% Win Rate in RANGING regimes** and **11.8% in TRENDING_DOWN**. 
- **Action**: Implement **Regime-Specific Gating**. If the `pilot_hmm_regime` detects "CHOP" or "BEAR", trend-following scores must be haircut by -50%.

### C. The "Smart" Pick Bridge
The gap from score 50 (Baseline) to 60 (Smart Gate) is a "valley of death" where most picks are killed. 
- **Action**: Introduce **Bayesian Probability Scaling**. Instead of a hard floor, use a sliding scale weight for position sizing (0.1x at score 50 to 1.0x at score 80).

### D. Concept Drift Detection
Spearman correlation (Score 0.15) indicates our "Top" strategies are **stale**.
- **Action**: Integrate **Kolmogorov-Smirnov (KS) Testing** for signal distribution. If a strategy's output distribution shifts significantly from its backtest baseline, trigger an automatic **SANDBOX DOWNGRADE**.

### E. Symbol Universe Expansion (The Momentum Edge)
Our `universe_expander` is currently disabled in `production_scanner.py`. The system relies on a static set of symbols.
- **Action**: Implement a **Top Gainer/Liquidity Scanner**. Assets with >10% hourly volume spikes or >5% price momentum must be automatically moved from "Off-Scan" to the "Watch" tier for real-time strategy validation.

---

## 5. Institutional Redis Signal Architecture

To ensure the agent fleet is trading "Hedge Fund Quality" picks, we are transitioning to the following **Institutional Alpha v1** schema:

```json
{
  "type": "institutional_alpha_v1",
  "from": "antigrav-quant-edge",
  "symbol": "FETUSDT",
  "direction": "LONG",
  "ag_score": 88.5,
  "metrics": {
    "trust_score": 8.5,
    "wci": 72,
    "regime": "TRENDING_UP",
    "fwd_wr": 62.5
  },
  "risk": {
    "entry": 1.25,
    "tp": 1.45,
    "sl": 1.18,
    "cvar_95": 2.4
  },
  "protocol": "SAFE_TRADING_CLEARED"
}
```

---

## 6. Redis Bus Broadcast Message
I have prepared the following message to be sent to the agent fleet:
> **[QUANT_ALPHA_REPORT]** 
> **Finding**: Spearman score correlation low (0.15) vs Trust correlation (0.35). 
> **Action**: Fleet recommended to prioritize `trust_score` over `agreement_count`. 
> **Gate Alert**: agreement_count > 6 is now considered a "Crowded Trade" (Negative Edge). 
> **Sector Note**: Forex baseline is un-tradeable (16% WR). Only Smart Picks > 75 sanctioned.

---

## 5. Quantitative Summary Table

| Category | Typical WR | Alpha Source | Verdict |
|---|---|---|---|
| **Crypto Majors** | 55% | Confluence | Stable Growth |
| **Crypto Alts** | 40-88% | Symbol Affinity | HCF (High Conviction) |
| **Equities** | 65% | Goldmine-BT | Primary Alpha |
| **Forex** | 16% | N/A | **AVOID / HIGH GATE** |
| **PM Consensus**| 43% | Inverse Edge | Contrarian Asset |

---

## 7. Final Recommendations & Execution

1. **Hard-Gate TRXUSDT**: Immediate block on all TRXUSDT strategies until a 60-day recovery (n>=20, WR>=55%) is established.
2. **Bridge the Smart-Pick Gap**: Lower the Smart Pick floor to 55 **IF** `trust_score` is > 7, allowing high-reliability/low-tech signals to execute.
3. **Kelly Sizing Integration**: All "Institutional Alpha" picks MUST follow the Kelly Criterion position sizing to prevent total account drawdown during high-correlation drift.

---
*End of Report*
