# Technical Specification: Enhancing the Money-Ready Pick Identification System

## 1. Introduction

This document outlines the technical specifications for enhancing the "money-ready" pick identification system. The primary goal is to differentiate between "long-term stable edges" and "high-conviction immediate opportunities" by expanding the existing statistical and fundamental gate framework.

## 2. Goals

- **Differentiate Pick Profiles**: Clearly distinguish between picks with persistent, statistically robust edges ("Long-term") and those representing high-conviction, fundamental- or macro-driven opportunities ("Right Now").
- **Integrate New Data Sources**: Incorporate fundamental valuation metrics and macro regime indicators.
- **Enhance Confidence Scoring**: Develop new gates and scoring modules to refine pick confidence based on the new profiles.
- **Improve System Robustness**: Ensure the system can identify valuable opportunities that may not yet meet traditional statistical thresholds.

## 3. Proposed Enhancements

### 3.1. Pick Profile Definitions

#### 3.1.1. Long-term Stable Edge

- **Definition**: Picks exhibiting persistent, statistically robust edges that demonstrate resilience across various market conditions and walk-forward periods.
- **Key Requirements**:
    - High Walk-Forward Consistency (> 0.7)
    - Low Edge Decay (< 0.2)
    - Regime Robustness (all regimes > 0.6)
    - Sufficient Historical Trades (> 50)
    - DSR > 2.0
    - PBO < 0.05
    - SPA p-value > 0.95
    - MDD < 20%
    - CVaR < 15%
- **Tag**: `long_term: True`
- **Confidence Boost**: Multiplicative, e.g., 1.2x

#### 3.1.2. High-Conviction Immediate Opportunity

- **Definition**: Picks driven by strong fundamental conviction or immediate macro alignment, which may not yet have sufficient historical data to pass stringent statistical gates.
- **Key Requirements**:
    - High Fundamental Strength Score (> 70 for equities, > 1.5σ deviation for crypto)
    - High Macro Alignment Score (> 0.5)
    - Minimum Trades: 5 (for new strategies)
    - Acceptable Risk Profile (MDD < 30%, CVaR < 25%)
- **Tag**: `high_conviction: True`
- **Confidence Boost**: Multiplicative, e.g., 1.3x

### 3.2. New Gates and Scoring Modules

#### 3.2.1. Fundamental Strength Gate

- **Purpose**: Quantify the fundamental attractiveness of a pick.
- **Inputs**:
    - **Equities**: Earnings Momentum (PEAD), Sector Strength, Analyst Sentiment, Valuation Metrics (P/E, EV/EBITDA).
    - **Crypto**: Network Value to Transactions (NVT), Metcalfe’s Law Deviation, Hash Rate, Developer Activity.
- **Scoring**:
    - **Equities**: Composite score (0-100). Threshold: > 70.
    - **Crypto**: Normalized deviation from Power Law/Metcalfe models. Threshold: > 1.5σ.
- **Output**: `fundamental_strength_score` (float)
- **Integration**: Multiplicative boost to `confidence` (capped at 1.5x) if threshold met.

#### 3.2.2. Macro Regime Alignment Score

- **Purpose**: Assess alignment with current macro regimes (USD, Yield Curve, VIX).
- **Inputs**:
    - USD Regime (Strong/Weak/Neutral)
    - Yield Curve Regime (Steep/Inverted/Neutral)
    - VIX Regime (High/Medium/Low)
- **Scoring**:
    - Calculate alignment score based on historical performance of pick's sector/asset class within each regime.
    - Score range: [-1, 1].
- **Output**: `macro_alignment_score` (float)
- **Integration**: Additive boost to `confidence` if score > 0.5; potential gate if score < -0.5.

#### 3.2.3. High-Conviction Immediate Opportunity Gate

- **Purpose**: Identify and promote picks meeting "Right Now" criteria.
- **Logic**:
    - Check if `fundamental_strength_score` and `macro_alignment_score` meet thresholds.
    - Check minimum trade count and risk profile.
- **Output**: Sets `high_conviction: True` tag and applies confidence boost.

#### 3.2.4. Long-Term Edge Stability Gate

- **Purpose**: Identify and elevate picks demonstrating persistent, robust edges.
- **Logic**:
    - Check Walk-Forward Consistency, Edge Decay, Regime Robustness, historical trade count, and core statistical gates (DSR, PBO, SPA, MDD, CVaR).
- **Output**: Sets `long_term: True` tag and applies confidence boost.

## 4. Implementation Details

### 4.1. Code Modifications

#### 4.1.1. `alpha_engine/money_ready_verdict.py`

- **`_canonical_pipeline()`**: Add calls to new gate functions (e.g., `_fundamental_strength_gate`, `_macro_alignment_gate`, `_high_conviction_gate`, `_long_term_gate`).
- **`_verdict()`**: Update to handle new statuses (`HIGH_CONVICTION_RIGHT_NOW`, `LONG_TERM_STABLE_EDGE`) and incorporate confidence adjustments.
- **New Functions**: Implement `_fundamental_strength_gate()`, `_macro_alignment_gate()`, `_high_conviction_gate()`, `_long_term_gate()`. These will likely call helper functions to compute scores and check thresholds.

#### 4.1.2. `alpha_engine/eagle_gates.py`

- **New Functions**: Implement `apply_eagle7_high_conviction(picks)` and `apply_eagle8_long_term(picks)` to apply the respective tags and confidence boosts. These functions will be called after the main verdict is determined.

#### 4.1.3. Supporting Functions/Modules

- **`alpha_engine/fred_macro_context.py`**: Ensure functions like `get_macro_context()` are robust and can be called efficiently.
- **`alpha_engine/fundamental_valuation_strategies.py`**: Refactor or create new functions to expose raw scores for fundamental metrics.
- **`alpha_engine/walk_forward_validator.py`**: Ensure consistency and decay scores are readily available.

### 4.2. Data Requirements

- **FRED API**: Continuous access to relevant macroeconomic data (USD Index, Yield Curve rates, VIX).
- **Historical Price Data**: Sufficient depth for fundamental calculations and walk-forward analysis.
- **Fundamental Data**: Access to earnings data, valuation multiples, network metrics (for crypto).

### 4.3. Dashboard Integration

- **New Columns/Tags**: Add columns or tags to display "High Conviction" and "Long-term" status.
- **UI Highlighting**: Implement distinct visual indicators (e.g., badges, color-coding) for these pick types.

## 5. Future Considerations

- **Adaptive Thresholds**: Dynamically adjust gate thresholds based on market volatility or asset class.
- **Explainability**: Develop methods to explain *why* a pick is classified as "High-Conviction" or "Long-term".
- **Backtesting Framework**: Ensure the backtesting framework can properly evaluate the impact of these new gates.

## 6. Open Questions

- What are the precise thresholds for each metric in the "Long-term" and "High-Conviction" profiles? (To be finalized based on backtesting and expert review).
- How should the confidence boosts be weighted and combined if a pick qualifies for both profiles?
- What is the exact implementation strategy for fetching and processing fundamental data?

## 7. Conclusion

This enhancement aims to create a more nuanced and effective "money-ready" system, capable of identifying both enduring statistical edges and timely, high-conviction opportunities. The proposed gates and scoring modules provide a framework for achieving this differentiation.
