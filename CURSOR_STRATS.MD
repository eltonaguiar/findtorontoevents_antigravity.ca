# CURSOR_STRATS — Strategy landscape beyond the current registry

**Purpose:** Consolidate deep research (parallel subagents + repo audit) on **strategy archetypes** that are commonly used in institutional/systematic literature or crypto market structure, but are **easy to under-weight** next to a large candle-indicator registry.

**Scope note:** `alpha_engine/config.py` maps on the order of **~347** strategy IDs in `STRATEGY_FAMILIES` across `INDICATOR_FAMILIES` (momentum, trend, volume, sentiment, on_chain, structure, volatility, carry, regime, mean_reversion, community, earnings). This document does **not** duplicate that list; it highlights **blind spots**, **thin families**, and **adjacent** strategy classes worth deliberate exploration.

**Disclaimer:** No performance numbers below—only mechanism classes, data requirements, and implementation risks. Anything here requires independent validation against your execution model and costs.

---

## 1. Snapshot: what the codebase already covers well

The registry already includes substantial coverage of:

- **Trend / momentum / MR** on OHLCV (EMA stacks, Donchian, Connors-style RSI2, Bollinger/Keltner, Hurst, statistical MR).
- **Crypto-specific:** funding, basis-style hooks, on-chain metrics, liquidation/cascade narratives, dominance/seasonality.
- **Microstructure (partial):** e.g. `order_book_imbalance`, `obi_microstructure`, `vpin_informed_flow`, `perpetual_basis_ms`, `coinbase_premium_index`.
- **Options-adjacent (spotty naming):** skew, IV reversion, expiry anomalies—**not** full greeks-based portfolio machinery under explicit `gamma`/`dispersion` IDs.
- **Cross-asset / ETF / macro:** CTA-style blends, sector/ETF rotation, some risk-parity naming (`etf_risk_parity_rotation`).
- **Baby / lab code:** `baby_strategies/` has ~200 modules; several **parallel experiments** (e.g. `kimi_*`, `rl_adaptive_strategy.py`, `ml_ensemble_strategy.py`) are **not** mirrored as first-class keys in `STRATEGY_FAMILIES`.

---

## 2. Gaps vs strategy *IDs* (naming & wiring)

From a static audit of `STRATEGY_FAMILIES` and `baby_strategies/`:

| Theme | In registry? | Comment |
|--------|----------------|--------|
| VPIN / flow toxicity | Yes (`vpin_informed_flow`) | Deep implementation quality varies by venue data |
| LOB imbalance | Yes (`order_book_imbalance`, `obi_microstructure`) | Often under-exploited vs pure OHLCV stacks |
| Funding term structure | Yes (`funding_term_structure`) | Crypto-perp curve mechanics still deserve first-class research |
| Dispersion / corr trades | Thin / absent as explicit IDs | No `dispersion` / `corr_swap` style keys found |
| Options gamma / dealer positioning | Not explicit | Skew/expiry exist; **gamma/OI maps** not named as first-class strategies |
| RL policies | Not in `STRATEGY_FAMILIES` | `rl_adaptive_strategy.py` exists in baby_strategies |
| Kimi / bespoke ML stacks | Not in `STRATEGY_FAMILIES` | Multiple `kimi_*.py` files (e.g. VPIN+LGBM) not wired as IDs |
| Pure ensemble / meta-model | Sparse | `vt_ml_rf_commodity` etc.; broad `ml_ensemble_*` naming rare |
| HFT / auction / latency | Not named | May be intentional—edges are capacity-bound |

**Interpretation:** The gap is often **not** “no related idea,” but **depth, data fidelity, and explicit portfolio-level** treatment (options surface, cross-section, execution).

---

## 3. Institutional archetypes often underrepresented vs “indicator mash”

These are **distinct** from stacking lagging indicators on one symbol. They assume specific **data** and usually **portfolio or execution** infrastructure.

### 3.1 Microstructure & flow

1. **Signed trade aggression / OFI (order flow imbalance)**  
   - *Hypothesis:* Net aggressive buying/selling moves short-horizon price; continuation vs reversion depends on liquidity replenishment.  
   - *Data:* Time & sales with aggressor flags; quotes; not reliable from coarse OHLCV.  
   - *Fit:* Liquid equities, FX, crypto perps with clean tape.  
   - *Risk:* Venue-specific; decays fast; costs dominate if mis-modeled.

2. **VPIN-style toxic flow**  
   - *Hypothesis:* Volume-time imbalance predicts adverse-selection regimes for liquidity providers.  
   - *Data:* Bucketed volume/trade classification.  
   - *Risk:* Bucket thresholds are easy to overfit.

3. **LOB depth, queue dynamics, microprice**  
   - *Hypothesis:* Depth asymmetry and refill behavior predict near-term pressure.  
   - *Data:* L2/L3; not OHLCV.  
   - *Risk:* Fragile to fee/rebate and matching engine changes.

4. **Microstructure mean reversion (sub-minute to minutes)**  
   - *Hypothesis:* Transitory pressure fades as liquidity returns—different from daily MR.  
   - *Data:* Trades + quotes.  
   - *Risk:* Look-ahead bias in quote data; slippage dominates backtests.

### 3.2 Volatility as an asset class

5. **Dispersion / correlation trades**  
   - *Hypothesis:* Mispricing of **correlation** (single-name vs index vol) creates relative-value opportunities.  
   - *Data:* Options chains; implied correlation; not perps-only.  
   - *Risk:* Parameter-heavy; event-clustered.

6. **Volatility risk premium (VRP) / variance harvesting**  
   - *Hypothesis:* Implied vol often exceeds realized over long samples; systematic vol selling with tail controls.  
   - *Data:* Options IV + realized vol; macro tail hedges.  
   - *Risk:* Left-tail dominates PnL; sample skew from crisis days.

7. **Vol surface RV: skew, smile, wings**  
   - *Hypothesis:* Edge in **relative** mispricing within the surface, not direction.  
   - *Data:* Full chains; stable calibration.  
   - *Risk:* Model risk (SVI/SABR) can swamp signal.

### 3.3 Cross-section & allocation (not single-ticker TA)

8. **Equity style premia (value, quality, low-vol, BAB)**  
   - *Hypothesis:* Characteristic-sorted portfolios capture long-horizon premia.  
   - *Data:* Fundamentals; universe; risk model.  
   - *Risk:* Factor crowding and data mining.

9. **Risk parity / vol-targeted multi-asset allocation**  
   - *Hypothesis:* Stable risk contributions + diversification.  
   - *Data:* Covariance of many return streams.  
   - *Risk:* Covariance estimation error → turnover; look-ahead in “risk-managed” backtests.

10. **Curve / forward structure (rates, FX forwards, bond futures)**  
    - *Hypothesis:* Carry and shape of curves—not reducible to one price series without context.  
    - *Data:* Multiple tenors, auction/supply info.  
    - *Risk:* Macro regime breaks; small effective sample across cycles.

### 3.4 Implementation & structural arbitrage

11. **Dealer gamma / OI “pin” proxies**  
    - *Hypothesis:* Aggregate hedging flows around strikes affect drift and vol.  
    - *Data:* Options OI/gamma maps; spot path.  
    - *Risk:* Aggregate models are approximate; event-driven.

12. **ETF premium/discount vs NAV**  
    - *Hypothesis:* Stress-driven deviations and AP mechanics create convergence trades.  
    - *Data:* ETF vs constituents; borrow.  
    - *Risk:* Halts and borrow unavailability break naive backtests.

13. **Optimal execution / market impact (Almgren–Chriss lineage)**  
    - *Hypothesis:* Implementation shortfall is a first-class problem; participation and scheduling matter as much as “signal.”  
    - *Data:* LOB, volume profile, fills.  
    - *Risk:* Capacity-bound; size changes the game.

14. **Liquidity provision / market-making**  
    - *Hypothesis:* Spread + rebates − adverse selection − inventory risk.  
    - *Data:* LOB, fills, fees, inventory.  
    - *Risk:* Fee tier and latency sensitivity.

15. **Convertible / capital-structure RV**  
    - *Hypothesis:* Mispricing between debt, equity, and embedded optionality.  
    - *Data:* Credit, equity, vol, terms.  
    - *Risk:* Illiquidity and corporate actions.

16. **Structured event alpha (rigorous PEAD-style)**  
    - *Hypothesis:* Post-event drift conditioned on surprise and liquidity—not generic sentiment buzz.  
    - *Data:* Event timestamps, surprises, fundamentals.  
    - *Risk:* Multiple testing across event windows.

17. **Macro stress overlays (“dollar beta,” liquidity)**  
    - *Hypothesis:* Systematic tilts from real yields, USD, credit, vol of vol.  
    - *Data:* Macro series; multi-asset returns.  
    - *Risk:* Short macro history; structural breaks.

---

## 4. Crypto perpetuals & market-structure strategies (beyond chart TA)

General TA under-models **funding, basis, margin systems, liquidation feedback, and oracle/DEX mechanics**. Classes to study:

1. **Funding term structure / curve carry** — cross-time or cross-contract funding vs expected path; mean-reverts violently around squeezes.  
2. **Spot–perp basis (cash-and-carry / reverse)** — convergence trades vs **forced** flow and credit constraints.  
3. **Cross-venue basis** — same underlier, different marks/funding/fees; transfer and wallet risk.  
4. **Inventory / MM skew inference** — unobservable true inventory; proxy via microprice and imbalance; spoofing risk.  
5. **Liquidation clusters** — feedback and convexity; levels are uncertain (hidden leverage, cross-margin).  
6. **OI × price joint dynamics** — rising OI with price vs OI fade; aggregate OI is not directional.  
7. **Mark / index / auction mechanics** — oracle windows vs tradable spot; basis to **where you fill**.  
8. **Cross-margin contagion** — portfolio margin shocks; ADL and insurance fund tail governance.  
9. **L2 imbalance / microprice** — short-horizon; adverse selection and flicker.  
10. **Toxic flow detection** — aggressor classification; crypto has bursty non-information flow (liquidations, rebalances).  
11. **Crowded funding / squeeze risk framework** — positioning diagnostic, not a standalone holy grail.  
12. **DEX perps vs CEX perps** — oracle lag, vAMM curvature, bridge/MEV, insurance—basis reflects **infrastructure**, not just “mispricing.”  
13. **ADL / insurance fund / socialized loss** — tail resolution rules as part of the payoff.  
14. **Stablecoin / collateral rail stress** — depeg and friction change effective basis and funding interpretation.

---

## 5. Suggested prioritization (research → implementation)

| Priority | Direction | Why |
|----------|-----------|-----|
| **A** | Enrich **existing** microstructure IDs with venue-honest cost/latency models | Already partially in map; biggest lift is **data quality**, not new names |
| **B** | Explicit **dispersion / surface** research track (equities/crypto options where liquid) | High institutional relevance; thin explicit coverage in IDs |
| **C** | Systematic **baby_strategies** audit: wire or retire `kimi_*`, `rl_*`, ensembles | Avoid parallel unmaintained labs |
| **D** | **Execution** layer metrics (impact, participation) as first-class telemetry | Aligns with real PnL drivers at size |
| **E** | **Macro overlay** discipline for crypto sleeves | Cheap structurally; avoids overfitting single-name indicators |

---

## 6. Falsifiability (how to avoid fooling yourself)

For any candidate archetype above, define **in advance**:

- What **data** must exist (not proxied by OHLCV if the theory needs tape/LOB/options).  
- What **would disprove** the edge (regime change, fee change, venue rule change).  
- Minimum **economic mechanism** (not just in-sample curve fit).

---

## 7. Document history

| Date | Change |
|------|--------|
| 2026-04-18 | Initial synthesis from parallel research subagents + `STRATEGY_FAMILIES` / `baby_strategies` audit. |
