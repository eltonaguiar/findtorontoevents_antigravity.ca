# Money-Ready Tiering Framework

To bridge the gap between research and real-money deployment, we define the following tiers based on statistical rigor and performance stability.

## Tier 1: Institutional/Mutual Fund Ready
- **Criteria:**
    - **Sample Size:** N > 100 realized trades.
    - **Performance:** Sharpe Ratio ≥ 1.0 (net of costs), Profit Factor ≥ 2.0.
    - **Consistency:** Edge persists across ≥ 3 of 4 market regimes.
    - **Risk:** Max Drawdown ≤ 20% monthly.
    - **Validation:** Passed purged-embargoed walk-forward testing (OOS PF ≥ 80% of IS PF).
    - **Data Integrity:** Provenance-tagged, resolver-verified, zero ghost-row artifacts.
- **Status:** 0/9 asset classes currently meet this.

## Tier 2: High Conviction (Aggressive)
- **Criteria:**
    - **Sample Size:** N > 30 realized trades.
    - **Performance:** Sharpe Ratio ≥ 0.7, Profit Factor ≥ 1.5.
    - **Validation:** Passed initial paper-pilot (4-8 weeks).
    - **Risk:** Max Drawdown ≤ 25% monthly.
- **Status:** ETF Dual Momentum (Lab-only), selected CRYPTO ML sleeves (Paper-pilot).

## Tier 3: Research/Experimental
- **Criteria:**
    - **Sample Size:** N < 30.
    - **Performance:** High volatility, unverified edge.
    - **Validation:** Purely for data gathering and refinement.
- **Status:** Majority of current strategies.

---

## Trustworthiness Findings (Summary)
- **CRYPTO:** Largest volume, but currently Kelly-negative (PF 1.25, WR 44.34%). Requires gating/concentration fixes.
- **COMMODITY:** High potential (PF 2.26, Sharpe 5.81), but currently paper-pilot only.
- **EQUITY:** Currently failing (PF 0.25, negative expectancy). Requires fundamental research (value/momentum).
- **FOREX:** High WR, but PF dragged by poor strategy selection. Requires isolation of high-conviction sleeves.
- **ETF:** Best lab candidate (PF 1.60), but insufficient forward data.
