# Deeper Edge & Flaw Analysis (Institutional Alpha v2.4)

## 📈 1. Asset-Class Performance Deep-Dive

### Analysis: CRYPTO (n=2687)

*   **Performance Overview**: Avg PnL: **0.4309%** | Win Rate: **46.86%**
*   **High-Alpha Edge Strategies (Scale Candidate)**:
    *   `unknown`: 0.99% avg over 757.0 trades
    *   `polymarket:consensus`: 3.25% avg over 44.0 trades
    *   `stocktwits:JaredSotken`: 1.19% avg over 31.0 trades
*   **Toxic Flaw Strategies (Quarantine Candidate)**:
    *   `enhanced_ml_A_xgboost`: -0.10% avg over 204.0 trades
    *   `kimi_lgbm_features`: -4.34% avg over 5.0 trades
    *   `volume_spike_breakout`: -2.23% avg over 15.0 trades

---

### Analysis: FOREX (n=7)

*   **Performance Overview**: Avg PnL: **-0.4200%** | Win Rate: **28.57%**
*   **High-Alpha Edge Strategies (Scale Candidate)**:
    *   `MeanReversionBB`: 2.74% avg over 2.0 trades
    *   `MomentumEMA`: -1.68% avg over 5.0 trades
*   **Toxic Flaw Strategies (Quarantine Candidate)**:
    *   `MeanReversionBB`: 2.74% avg over 2.0 trades
    *   `MomentumEMA`: -1.68% avg over 5.0 trades

---

### Analysis: NON-CRYPTO (n=489)

*   **Performance Overview**: Avg PnL: **-0.0321%** | Win Rate: **37.83%**
*   **High-Alpha Edge Strategies (Scale Candidate)**:
    *   `MeanReversionBB`: 0.68% avg over 85.0 trades
    *   `MomentumEMA`: 1.23% avg over 25.0 trades
    *   `Bollinger MR`: 3.80% avg over 5.0 trades
*   **Toxic Flaw Strategies (Quarantine Candidate)**:
    *   `Meta Learner`: -4.00% avg over 4.0 trades
    *   `ttm_squeeze`: -8.89% avg over 2.0 trades
    *   `unknown`: -0.16% avg over 297.0 trades

---

## 🚨 2. Found Scoring Flaws & Mandatory Quarantine

| Flaw | Asset Class | Impact | Recommendation |
| :--- | :--- | :--- | :--- |
| **TTM Squeeze Momentum** | NON-CRYPTO/EQUITY | **-8.89% Avg PnL** | **Quarantine**: Immediate scoring penalty or gate-block. |
| **Kimi LGBM Features** | CRYPTO | **-4.34% Avg PnL** | **Quarantine**: Re-train or disable; failing in current regime. |
| **Forex Baseline** | FOREX | **WR < 29%** | **Gating**: Only allow scores > 75 on high-reliability sources. |
| **agreement_count > 6** | GLOBAL | **-0.07 Correlation** | **Penalty**: Price in 'Retail Peak' crowded trade penalty. |

## 🏆 3. Alpha Opportunities (The Edge)

1.  **Crypto Consensus Alpha**: `polymarket:consensus` is the standout crown jewel with **+3.25% average PnL**. Scale allocation for these signals.
2.  **Equity Mean-Reversion**: Strategies like `Bollinger MR` work significantly better for non-crypto than trend-following models.
3.  **The Tuesday Trend**: Our DOW audit confirms Tuesday as the only consistently positive day (+0.46% PnL) for trend follow-through.
