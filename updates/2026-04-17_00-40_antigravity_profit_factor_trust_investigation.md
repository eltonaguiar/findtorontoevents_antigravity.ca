# Investigation: Reliability of Non-Crypto Asset Profit Factors & Win Rates

**Agent:** Antigravity  
**Date/Time:** 2026-04-17 00:40 EST  

## The Anomaly
The data indicates that non-crypto assets (Equities/Stocks, Forex, Commodities, ETFs, Bonds) exhibit a Win Rate (WR) of < 50%, yet several show theoretically positive Profit Factors (PF):
*   **Stocks:** 1.47 PF
*   **Forex:** 1.11 PF
*   **Commodities:** 1.18 PF
*   **Bonds:** 1.60 PF
*   **ETFs:** 0.86 PF (Negative, but worth investigating)

Despite positive Profit Factors, we **cannot trust this data** to deploy real capital. Here is the investigation into the systemic data and calculation flaws producing these misleading metrics.

---

## 1. The "Tiny N" (Sample Size) Illusion
A Profit Factor of 1.60 for Bonds sounds exceptional, but a previous audit revealed that Bonds only have **8 closed trades** total. ETFs only have 19 closed trades.
*   **Why it's untrustworthy:** In quantitative trading, a sample size (N) under 100 is statistically insignificant. A single lucky trade in a pool of 8 will skew the Gross Profit massively, creating a high PF that will instantly collapse in live forward-trading.

## 2. Inconsistent "Flat" Pick Accounting
Our recent WR audits discovered that "flat" picks (trades that expired at entry or didn't trigger) are being counted as **losses** in the Win Rate calculation.
*   **The Disconnect:** While WR punishes flats (driving the WR < 50%), the Profit Factor formula (`Gross Profit / Gross Loss`) likely **ignores** flats entirely because they have a 0% return.
*   **Result:** You get a heavily penalized WR paired with a seemingly healthy PF, masking the fact that the system is failing to actually execute trades properly.

## 3. Stale Data & Invisible Intraday Drawdowns (The "Frankfurter" Problem)
For Forex and Commodities, the pipeline relies on low-resolution or daily settlement data (e.g., daily rates from Frankfurter).
*   **Why it's untrustworthy:** The Profit Factor calculations evaluate the entry vs. the close price at the end of the day. However, typical Forex ATR on a 4H chart is ~0.3%. Intraday price swings would absolutely trigger the tight 0.5% stop-losses in live trading.
*   **Result:** The system records a "Win" and pads the Gross Profit because it didn't see the intraday dip that would have stopped the trade out. The Profit Factor is a ghost metric based on price action that a live broker would not allow.

## 4. Outlier Bias & Catastrophic R:R Inversion
A Profit Factor > 1.0 implies profitability, but the aggregate PnL for Forex was recently audited at **-1,121.5%**.
*   **How is this mathematically possible?** If PF is calculated purely on average % win vs. average % loss without weighting by trade frequency, a strategy with 90 losers of -1% and 10 winners of +10% might show a decent PF, but suffer catastrophic consecutive drawdowns that would margin-call an account.
*   **Result:** The R:R (Risk:Reward) is inverted on a per-trade basis in real-world conditions, making the theoretical PF entirely dangerous to rely on.

## 5. Overfitting & The Forward-Test Gap
For assets like Forex (e.g., USDJPY, GBPJPY), strategies showed a 100% Backtest WR that immediately degraded to 69% (and dropping) in forward tests.
*   **Why it's untrustworthy:** The Profit Factor is heavily anchored by historically overfit backtest data. As these strategies hit out-of-sample live data, the PF will rapidly revert to the mean (likely < 0.8).

---

## Actionable Conclusion & Next Steps
We cannot trust the 1.11 - 1.60 Profit Factors for non-crypto assets. They are mathematical artifacts caused by tiny sample sizes, missing intraday stop-loss triggers, and misaligned "flat" trade accounting.

**Remediation Required Before Trading:**
1.  **Enforce N ≥ 50:** Do not display or calculate Profit Factor on the dashboard unless the asset class has at least 50 *decided* (non-flat) trades.
2.  **Migrate Data Feeds:** Transition Forex/Commodities from daily settlement data to high-resolution (5m/1H) data providers (e.g., TwelveData, OANDA) to expose hidden intraday stop-loss triggers.
3.  **Standardize Metrics:** Unify how "flat" trades are handled between WR and PF calculations so the dashboard doesn't display conflicting realities.
