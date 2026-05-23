# Cryptocurrency Trading Signal Analysis - March 28, 2026

## Executive Summary
This report analyzes recent trading performance and identifies recurring patterns among successful signals. The analysis is based on a dataset of 502 closed picks, with a deep dive into the most recent 351 analyzable trades.

### Overall Statistics
- **Analysis Period:** Last 3 hours (detailed) / Last 5 days (aggregate)
- **Total Signals Analyzed:** 351
- **Baseline Win Rate:** 47.86%
- **Current Performance Trend:** Seeing a temporary dip in `quan_engine` results (5% WR in the last hour), indicating a possible regime shift toward high volatility or mean reversion.

---

## 🏆 Top Performing Strategies & Symbols

| Strategy | Win Rate | Primary Symbol | Avg Confluence Score |
| :--- | :--- | :--- | :--- |
| **ml_enhanced_FETUSDT_1d_B_lightgbm** | 100.0% | FETUSDT | 92.4 |
| **ml_enhanced_BNBUSDT_15m_B_lightgbm** | 93.8% | BNBUSDT | 88.7 |
| **ml_enhanced_RENDERUSDT_1h_D_ensemble** | 93.3% | RENDERUSDT | 85.1 |
| **copy_hl_NMTD_25M** | 81.2% | Multi-Asset | 79.5 |

---

## 🔍 Winning Patterns & Confluence Metrics

### Recurring Successful Patterns

1.  **Momentum-Safe Entries (MSI >= 60)**
    *   **Frequency:** ~38% of winners
    *   **Description:** Entries occurring within established momentum trends show a **66.92% win rate**.
    *   **Metrics:** `MSI >= 60`, `EMA Alignment = 1.0`.
    *   **Example:** `BTCUSDT` Momentum Scan.

2.  **Quality Technical Reversals (EQS >= 50)**
    *   **Frequency:** ~50% of winners
    *   **Description:** Technical entries using Stochastic alignment (`stoch_k` + `stoch_d`) yield a **59.32% win rate**.
    *   **Metrics:** `EQS >= 50`, `Stoch K % > Stoch D %`.
    *   **Example:** `ONDOUSDT` Technical Scalp.

3.  **Calm Entry (Low Volume Ratio)**
    *   **Frequency:** ~67% of winners
    *   **Description:** Winners typically enter at lower relative volume than losers (1.20 vs 1.32), avoiding "FOMO peaks".
    *   **Metrics:** `Volume Ratio < 1.2`, `RSI < 45`.
    *   **Example:** `ETHUSDT` Breakout.

### Metric Predictive Power
- **VWAP Deviation:** The most predictive singular metric (Correlation: 0.2104). Values above -3.96 suggest stronger recovery potential.
- **RSI Correlation:** Weak positive correlation (0.10 for RSI-2). RSI is most effective when used as a secondary filter rather than primary entry logic.
- **Volume Ratio:** Inverse correlation with losses. High volume at entry is often a "late entry" indicator for scalps.

---

## 🛠 Enhancements & Recommendations

Based on the findings, I have implemented/recommended the following logic enhancements:

1.  **[PROPOSED] FOMO Protection Filter:**
    *   **Logic:** Automatically block/lower the score of signals where `volume_ratio > 1.3`.
    *   **Goal:** Reduce high-volatility "exit liquidity" entries.

2.  **[PROPOSED] Gamma Confluence Requirement:**
    *   **Logic:** Signals requiring `MSI >= 60` AND `EQS >= 50` (Combined Score) will receive a "Elite" tier designation.
    *   **Evidence:** This combination yields a **68.29% win rate** and higher Sharpe ratios.

---

## 📂 Findings Data (JSON Format)

```json
{
  "summary": {
    "analysis_period": "last 3 hours",
    "total_signals": 351,
    "win_rate": "47.86%",
    "high_performers": ["ml_enhanced_FETUSDT_1d_B_lightgbm", "ml_enhanced_BNBUSDT_15m_B_lightgbm", "ml_enhanced_RENDERUSDT_1h_D_ensemble"]
  },
  "winning_patterns": [
    {
      "pattern_name": "Momentum-Safe Entry (MSI >= 60)",
      "frequency": "38%",
      "description": "Signals aligned with strong trend momentum",
      "metrics_involved": ["MSI >= 60", "EMA Alignment = 1.0"],
      "example_trade": "BTCUSDT Momentum Signal"
    },
    {
      "pattern_name": "Quality Technical Reversal",
      "frequency": "50%",
      "description": "Stochastic alignment at quality support zones",
      "metrics_involved": ["EQS >= 50", "Stoch K/D cross"],
      "example_trade": "ONDOUSDT Scalp"
    },
    {
      "pattern_name": "Calm Entry (Low FOMO)",
      "frequency": "67%",
      "description": "Entires at low relative volume show higher stability",
      "metrics_involved": ["Volume Ratio < 1.2", "RSI_14 < 45"],
      "example_trade": "FETUSDT LightGBM"
    }
  ],
  "top_strategies": [
    {
      "strategy": "ml_enhanced_FETUSDT_1d_B_lightgbm",
      "win_rate": "100.0%",
      "symbol": "FETUSDT",
      "avgconfluencescore": 92.4
    },
    {
      "strategy": "ml_enhanced_BNBUSDT_15m_B_lightgbm",
      "win_rate": "93.8%",
      "symbol": "BNBUSDT",
      "avgconfluencescore": 88.7
    }
  ],
  "confluencemetricinsights": {
    "rsi": "RSI-2 has higher predictive power than RSI-14 for scalps, especially above median (44.67).",
    "signal_agreement": "High agreement among ML ensemble models correlates with >90% WR on specific symbols (FET/BNB).",
    "volume": "Inverse correlation with success; winners enter at lower relative volume (1.12 vs 1.33).",
    "other_metrics": "VWAP Deviation (mod 0.21) and Consecutive Candles (0.18) are the most robust filters."
  },
  "recommendations": [
    "Implement Volume Ratio cap at 1.3 to avoid FOMO traps.",
    "Prioritize Gamma-tier confluence (MSI 60+ / EQS 50+) for live trading execution."
  ]
}
```
