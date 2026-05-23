# KIMI_STRATS.MD — Deep Research: 54 Overlooked Institutional Strategies

**Research Date:** 2026-04-18  
**Purpose:** Expand the Antigravity strategy universe beyond the existing ~367 implementations with deep, quantitative research into underrepresented asset classes and alpha sources.  
**Methodology:** Parallel subagent research across five strategy domains, synthesizing institutional practices, academic literature, and executable Python sketches.

---

## Executive Summary

Our existing inventory (documented in `EXISTING_STRATEGIES_INVENTORY.md`, `100_ALGORITHMS_MASTER_CATALOG.md`, and `STRATEGY_INVENTORY_COMPLETE.md`) is heavily concentrated in:

- Crypto/Equity directional & technical strategies  
- ML ensembles (XGBoost, LightGBM, GRU, HMM regimes)  
- Basic statistical arbitrage (pairs, BAB, QMJ)  
- 0DTE options scalping  

**Critical gaps identified:**
- **Options & Volatility surface trading** (skew, term structure, dispersion)
- **Fixed Income & Rates** (yield curve, repo, CDS, inflation breakevens)
- **Commodities** (roll yield, seasonal spreads, processing spreads)
- **Global Macro & Event-Driven** (merger arb, spin-offs, activist tracking, central bank divergence)
- **Market Making & Microstructure** (inventory-aware quoting, tick imbalance, auction dynamics)
- **DeFi-Native** (MEV, liquidation mining, DEX-CEX basis, concentrated LP harvesting)
- **Cross-Asset Risk Premia** (momentum, carry, value, low vol across all asset classes)
- **Behavioral Anomalies** (accruals, issuance, MAX effect, attention reversal)

This document compiles **54 distinct institutional-grade strategies** across those gaps. Each strategy includes its edge, asset applicability, parameters, risk management, Python implementation sketch, and rationale for why it is overlooked.

---

## Table of Contents

1. [Options & Volatility Strategies](#1-options--volatility-strategies)
2. [Fixed Income, Rates & Commodities](#2-fixed-income-rates--commodities)
3. [Global Macro, Event-Driven & Special Situations](#3-global-macro-event-driven--special-situations)
4. [Market Making, Microstructure & DeFi-Native](#4-market-making-microstructure--defi-native)
5. [Cross-Asset Risk Premia & Behavioral Finance](#5-cross-asset-risk-premia--behavioral-finance)

---

# 1. Options & Volatility Strategies

Retail options education overwhelmingly concentrates on directional spreads, naked premium selling, and 0DTE scalping. Institutional volatility desks treat volatility as a standalone asset class and exploit structural mispricings across the volatility surface: term structure, skew, correlation, jump risk, and relative value between related underlyings.

> **Key Principle:** The persistent profitability of these strategies derives from **market structure frictions** (hedging demand, short-sale constraints, regulatory capital requirements) and **behavioral premia** (crashophobia, overreaction to earnings uncertainty), not from directional forecasting.

---

## 1.1 Vertical Skew Dispersion Arbitrage

**Edge:** The volatility smile exhibits localized convexity anomalies driven by dealer hedging (Vanna flows) and strike-clustered open interest. The second derivative of IV with respect to strike mean-reverts.

**Core Metric:**
```
Skew Curvature Score = (IV_25d_put + IV_25d_call - 2 * IV_ATM) / (strike_width)^2
```

**Asset Classes:** Equity indices (SPX, NDX), liquid single-names (AAPL, TSLA, NVDA), crypto options (BTC, ETH on Deribit).

**Parameters:**
| Parameter | Value / Rule |
|-----------|--------------|
| Entry trigger | Z-score > \|1.5\| |
| Structure | 1x ATM Butterfly + offsetting vertical spread |
| Max hold | 5-10 trading days |
| Stop loss | 50% of max profit potential or 2x credit paid |
| Position sizing | 1-2% portfolio per trade |
| Avoid | FOMC, NFP, major earnings dates |

**Python Sketch:**
```python
import numpy as np
from scipy.interpolate import UnivariateSpline

def skew_curvature_zscore(strikes, ivs, atm_iv, atm_strike, history_window=60):
    spline = UnivariateSpline(strikes, ivs, k=3, s=0.01)
    curvature = spline.derivative(n=2)(atm_strike)
    curvature_score = curvature * (atm_strike ** 2) / atm_iv
    history = []  # rolling history of curvature_score
    z = (curvature_score - np.mean(history)) / np.std(history)
    return curvature_score, z
```

**Why Overlooked:** Requires options chain analytics infrastructure and understanding of higher-order Greeks (Vanna, Volga) that retail platforms do not surface.

---

## 1.2 Charm-Accelerated Calendar / Diagonal Harvesting

**Edge:** Exploits higher-order Greek decay (Charm, Vanna) in positive gamma regimes. Calendar spreads profit when near-term IV decays faster than back-month IV, but the true edge comes from directional bias embedded in Charm (delta decay with time).

**Asset Classes:** Equities, ETFs (SPY, QQQ), indices.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Front-month IV > back-month IV by 5%+ AND underlying near short strike |
| Structure | Short front-month ATM call / Long back-month OTM call (diagonal) |
| Max hold | 15-25 days (capture Charm acceleration) |
| Hedge | Delta-hedge with underlying if delta exceeds ±0.30 |
| Risk | Max loss = net debit paid |

**Python Sketch:**
```python
def calendar_score(front_iv, back_iv, underlying_price, short_strike, days_to_front):
    iv_ratio = front_iv / back_iv
    moneyness = underlying_price / short_strike
    charm_proxy = (underlying_price - short_strike) / (short_strike * np.sqrt(days_to_front/365))
    return iv_ratio * 0.6 + abs(charm_proxy) * 0.4
```

**Why Overlooked:** Retail traders avoid calendars due to slow theta and complexity of managing two expirations; institutions automate the Greek management.

---

## 1.3 Realized-Implied Variance Gamma Scalping

**Edge:** Delta-hedged straddle P&L decomposition into gamma (convexity), theta (time decay), and vega (volatility). The edge comes from systematically delta-hedging when realized volatility exceeds implied volatility.

**Asset Classes:** Equities, indices, FX, crypto.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | RV_20d > IV_30d by > 5 vol points |
| Structure | Long ATM straddle, delta-neutral at entry |
| Rebalance | Leland-adjusted frequency: every 1/2 * (σ * sqrt(dt)) threshold |
| Exit | RV falls below IV, or 50% of theta consumed |

**Python Sketch:**
```python
def gamma_scalp_pnl(prices, strike, iv, dt=1/252, rebalance_threshold=0.01):
    position = {'straddle': 1, 'delta_hedge': 0}
    pnl = 0
    for t in range(1, len(prices)):
        delta = calculate_delta(prices[t], strike, iv, time_to_expiry)
        hedge_change = delta - position['delta_hedge']
        if abs(hedge_change) > rebalance_threshold:
            pnl -= hedge_change * prices[t]  # hedge cost
            position['delta_hedge'] = delta
        pnl += position['straddle'] * option_pnl(prices[t], prices[t-1])
    return pnl
```

**Why Overlooked:** Requires continuous delta-hedging, low transaction costs, and accurate realized vol forecasting — prohibitive for retail.

---

## 1.4 VIX Term Structure Carry with Regime Filtering

**Edge:** Systematic contango roll yield harvesting in VIX futures. VIX futures are in contango ~80% of the time, allowing short-VIX strategies to collect roll yield. Regime filtering avoids blowups during backwardation.

**Asset Classes:** VIX futures, E-mini SPX futures (hedge).

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | VIX futures curve slope (M2-M1) > 0 (contango) AND VIX < 25 |
| Structure | Short front-month VIX futures, long E-mini SPX futures (0.3 beta hedge) |
| Regime filter | Exit if VIX > 30 or curve inverts (M2 < M1) |
| Sizing | 2-5% risk, vol-targeted at 10% annualized |

**Python Sketch:**
```python
def vix_carry_signal(vix, m1, m2, spx_beta=0.3):
    contango = (m2 - m1) / m1
    if contango > 0 and vix < 25:
        return {'short_vix': 1, 'long_spx': spx_beta}
    elif vix > 30 or contango < 0:
        return {'flat': True}
    return {'hold': True}
```

**Why Overlooked:** Retail traders remember Feb 2018 (Volmageddon) and avoid VIX; institutions use strict regime filters and sizing.

---

## 1.5 Dynamic VRP Iron Condor with Greeks-Band Management

**Edge:** Harvests the variance risk premium (VRP) — the persistent gap between implied and realized volatility. Dynamic management adjusts wing width based on skew and delta targets.

**Asset Classes:** Equity indices, ETFs.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | VRP > 3 vol points (IV - RV) AND VVIX < 120 |
| Structure | Iron condor with asymmetric wings (wider put side for skew) |
| Delta target | ±0.10 per leg at entry |
| Rebalance | Roll untested side when delta exceeds ±0.15 |
| Circuit breaker | Close all if VVIX > 150 (vol-of-vol spike) |

**Why Overlooked:** Retail sells static iron condors and gets destroyed by tail events; institutions dynamically manage delta and use VVIX as a circuit breaker.

---

## 1.6 Cross-Asset Straddle Relative Value (Pairs Vol Arb)

**Edge:** Vega-neutral straddle spreads between correlated underlyings. When the implied volatility ratio diverges from historical beta-adjusted correlation, it mean-reverts.

**Asset Classes:** XLF vs components, GLD vs GDX, BTC vs ETH, sector ETFs vs SPY.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Z-score of IV ratio > \|2.0\| (beta-adjusted) |
| Structure | Long straddle on cheap underlying, short straddle on expensive (vega-neutral) |
| Beta adjust | Regress 20-day realized vol ratio to find fair value |
| Exit | Z-score reverts to 0.5 |

**Python Sketch:**
```python
def straddle_rv_ratio(iv_a, iv_b, beta, hist_ratio_mean, hist_ratio_std):
    fair_iv_b = iv_a / beta
    z = (iv_b - fair_iv_b) / hist_ratio_std
    return z
```

**Why Overlooked:** Requires simultaneous options pricing on two correlated underlyings and beta-adjusted vol forecasting.

---

## 1.7 Ex-Earnings Term Structure Normalization

**Edge:** Calendar spreads targeting differential IV collapse across expirations after earnings. Front-month IV collapses more than back-month because it embeds the earnings move.

**Asset Classes:** Equities with liquid weekly and monthly options.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | 1-3 days before earnings; front-month IV > back-month by > earnings move implied |
| Structure | Short front-month ATM straddle / Long back-month ATM straddle |
| Exit | 1-2 days after earnings (capture differential crush) |

**Why Overlooked:** Retail trades directional earnings plays; institutions systematically harvest the term structure asymmetry.

---

## 1.8 Jump-Decomposed Variance Premium Harvesting

**Edge:** Decomposes variance swap payoffs into continuous (diffusion) and jump components. The jump-timing risk premium is systematically overpriced because investors overpay for crash protection.

**Asset Classes:** Equity indices, single-names with active options.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Jump risk premium (implied jump variance - realized jump variance) > 80th percentile |
| Structure | Short variance swaps (or replicated with options strips) |
| Hedge | Long deep OTM puts (cheap tail insurance) |

**Why Overlooked:** Requires Aït-Sahalia-style jump detection and variance swap replication knowledge.

---

## 1.9 Put-Call Parity Deviation Shadow Rate Extraction

**Edge:** Put-call parity violations predict funding costs and short-sale constraints. Cremers & Weinbaum (2010) showed that deviations predict future returns.

**Asset Classes:** Equities, ETFs.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | PCP deviation Z-score > \|2.0\| |
| Signal | Positive deviation → synthetic long is cheap → bullish signal |
| Holding | 1 month |

**Python Sketch:**
```python
def pcp_deviation(S, K, T, r, q, call_price, put_price):
    synthetic_forward = call_price - put_price + K * np.exp(-r * T)
    actual_forward = S * np.exp((r - q) * T)
    deviation = synthetic_forward - actual_forward
    return deviation / actual_forward
```

**Why Overlooked:** Requires real-time options data and understanding of dividend/interest rate assumptions in PCP.

---

## 1.10 PCA-Weighted Dispersion Trading

**Edge:** Harvests the correlation risk premium — index implied correlation is systematically higher than realized correlation. PCA selects the most representative constituents.

**Asset Classes:** Equity indices (SPX, NDX, DJIA).

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Implied correlation > realized correlation by > 5 points |
| Structure | Short index variance, long constituent variance (PCA-weighted) |
| Vega neutral | Match total vega of index leg to constituent leg |

**Why Overlooked:** Requires PCA on 50+ stocks and index options infrastructure; Sharpe ~2.47 but capacity-limited.

---

# 2. Fixed Income, Rates & Commodities

Our existing trading architecture is overwhelmingly concentrated in crypto/equity directional strategies with minimal exposure to the deepest, most liquid markets in the world: sovereign bonds, interest rate derivatives, and commodity futures.

---

## 2.1 Yield Curve Steepener / Flattener (2s10s, 5s30s)

**Edge:** The yield curve slope embeds market expectations about monetary policy, growth, and inflation. Post-inversion mean reversion in 2s10s has been one of the most reliable macro trades over decades.

**Instruments:** Treasury futures ZT (2Y), ZF (5Y), ZN (10Y), ZB (30Y); SOFR swaps.

**DV01-Neutral Weighting:**
```
Notional_2Y = Target_DV01 / DV01_per_1mm_2Y
Notional_10Y = Target_DV01 / DV01_per_1mm_10Y
```

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Steepener | 2s10s < 20th percentile of 2-year history AND Fed futures price > 2 cuts in 12 months |
| Flattener | 2s10s > 80th percentile AND CPI accelerating |
| Exit | 50th percentile of historical spread range |
| Stop | 2x DV01 loss or 6 months holding |

**Python Sketch:**
```python
def yield_curve_signal(spread, history, fed_futures_cuts, cpi_momentum):
    p = np.percentile(history, [20, 50, 80])
    if spread < p[0] and fed_futures_cuts > 2:
        return 'steepener'
    elif spread > p[2] and cpi_momentum > 0:
        return 'flattener'
    return 'neutral'
```

**Why Overlooked:** Requires futures account, understanding of DV01, and macro regime analysis — intimidating for equity/crypto natives.

---

## 2.2 Yield Curve Butterfly (2s5s10s)

**Edge:** Curvature mean-reversion around issuance and hedging flows. The butterfly captures the relative cheapness/richness of the belly (5Y) versus the wings (2Y, 10Y).

**Instruments:** Treasury futures or cash bonds.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Butterfly Z-score > \|1.5\| |
| Structure | Long 2Y, Short 2x 5Y, Long 10Y (or reverse) |
| DV01 neutral | Weight by inverse DV01 |

**Why Overlooked:** Three-legged trade with complex weighting; minimal retail education on curve curvature.

---

## 2.3 Bond Futures Basis / CTD Arbitrage

**Edge:** Cash-futures convergence via implied repo vs actual repo. The cheapest-to-deliver (CTD) bond can shift, creating temporary mispricing.

**Instruments:** Treasury futures, CTD bonds, repo markets.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Implied repo < actual GC repo by > 20 bps |
| Structure | Long CTD bond, short futures contract |
| Exit | Basis converges or delivery month |

**Python Sketch:**
```python
def basis_arb_signal(ctd_price, futures_price, conversion_factor, implied_repo, gc_repo):
    implied_futures = ctd_price / conversion_factor
    basis = futures_price - implied_futures
    repo_edge = gc_repo - implied_repo
    return basis, repo_edge
```

**Why Overlooked:** Requires repo market access and understanding of conversion factors and delivery options.

---

## 2.4 Repo Rate Arbitrage (SOFR vs GC vs Specials)

**Edge:** Funding tier dislocations and collateral specialness premium. Special repos (hard-to-borrow bonds) trade at significantly lower rates than GC.

**Instruments:** Repo agreements, SOFR futures.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | GC repo - special repo > 50 bps |
| Structure | Borrow in special repo, lend in GC repo |
| Risk | Collateral recall, counterparty default |

**Why Overlooked:** Requires prime brokerage repo desk access; retail cannot participate.

---

## 2.5 CDS Basis Trade (Single-Name vs Index)

**Edge:** Bond-CDS spread divergence and index convexity mispricing. Single-name CDS often trades wider than the implied spread from the index.

**Instruments:** Single-name CDS, CDX/iTraxx indices.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | CDS basis (CDS spread - bond spread) > 30 bps |
| Structure | Short single-name CDS, long index CDS (beta-adjusted) |
| Hedge | Duration-matched bond basket |

**Why Overlooked:** OTC derivatives with ISDA documentation requirements; retail has no access.

---

## 2.6 Commodity Roll Yield Harvesting

**Edge:** Term structure carry in backwardation vs contango. Long commodities in backwardation (positive roll yield) and short commodities in contango (negative roll yield).

**Instruments:** Commodity futures (oil, nat gas, metals, grains).

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Annualized roll yield > 5th percentile (long) or < 95th percentile (short) |
| Structure | Long futures in backwardation, short futures in contango |
| Rebalance | Monthly roll |

**Python Sketch:**
```python
def roll_yield(f1, f2, days_between):
    return (np.log(f2) - np.log(f1)) / (days_between / 365)

def roll_yield_signal(universe_roll_yields):
    longs = [c for c, ry in universe_roll_yields.items() if ry > np.percentile(list(universe_roll_yields.values()), 95)]
    shorts = [c for c, ry in universe_roll_yields.items() if ry < np.percentile(list(universe_roll_yields.values()), 5)]
    return longs, shorts
```

**Why Overlooked:** Requires futures roll mechanics knowledge; retail often buys commodity ETFs that silently bleed roll costs.

---

## 2.7 Seasonal Commodity Spreads

**Edge:** Biological/weather-driven calendar spreads in grains, nat gas, and softs. Planting/harvest cycles and winter heating demand create predictable seasonal patterns.

**Instruments:** Commodity futures calendar spreads.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Nat Gas | Long winter (Jan), short summer (Jul) — enter August |
| Corn | Long Dec, short Jul — enter planting season (April) |
| Exit | Seasonal window closes or Z-score reverts |

**Why Overlooked:** Requires agricultural and energy market expertise; long holding periods test retail patience.

---

## 2.8 Crack / Crush / Spark Spread

**Edge:** Processing margin mean-reversion in energy and agriculture. Refiners' margins (crack spread) oscillate around long-term averages due to supply/demand imbalances.

**Instruments:** Oil, gasoline, heating oil futures (crack); soybeans, meal, oil futures (crush).

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Crack spread Z-score > \|2.0\| |
| Structure | Long inputs, short outputs (or reverse) |
| 3:2:1 crack | 3 crude, 2 gasoline, 1 heating oil |

**Python Sketch:**
```python
def crack_spread(crude, gasoline, heating_oil):
    return (2 * gasoline + 1 * heating_oil) - 3 * crude
```

**Why Overlooked:** Multi-legged futures spread with specific ratios; retail platforms rarely support native crack spread orders.

---

## 2.9 Inflation Breakeven Trade (TIPS vs Nominals)

**Edge:** Inflation risk premium and liquidity premium dislocations. TIPS often trade with a liquidity discount, and breakeven inflation embeds a risk premium.

**Instruments:** TIPS, nominal Treasury bonds/bond futures.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Breakeven inflation < survey-based inflation forecast by > 30 bps |
| Structure | Long TIPS, short nominal Treasuries (duration-neutral) |
| Exit | Breakeven converges to forecast |

**Why Overlooked:** Requires understanding of real yields, inflation swaps, and duration matching.

---

## 2.10 FX Swap Implied Yield Divergence (CIP Deviations)

**Edge:** Post-Basel balance sheet constraints create persistent deviations from Covered Interest Parity (CIP). The FX swap implied rate diverges from sovereign yield differentials.

**Instruments:** FX forwards, sovereign bonds, OIS swaps.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | CIP deviation > 20 bps |
| Structure | Borrow in low-yield currency via FX swap, invest in high-yield sovereign |
| Risk | Counterparty, collateral calls |

**Why Overlooked:** Requires prime brokerage and cross-border collateral management; purely institutional.


---

# 3. Global Macro, Event-Driven & Special Situations

This section expands the existing strategy suite (PEAD, flash crash reversal, JPY risk-off, DXY correlation, basic sentiment) with catalyst-driven strategies that exploit corporate actions, policy divergence, and structural dislocations.

---

## 3.1 Merger Arbitrage

**Edge:** When a merger is announced, the target trades at a discount to the offer price (the "deal spread") due to completion uncertainty. Branch & Yang (2003) found cash deals close more reliably than stock deals.

**Asset Classes:** Equities (target), options (put protection).

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Spread > (historical break rate × max loss) |
| Cash deals preferred | Lower complexity, higher close rate |
| Stock deals | Short acquirer at announced exchange ratio |
| Max single deal | 5% portfolio |
| Diversification | Minimum 15-30 deals |
| Time stop | 12 months |
| Avoid | FTC/DOJ "second request" deals |

**Python Sketch:**
```python
from dataclasses import dataclass
from enum import Enum

class DealType(Enum):
    CASH = "cash"
    STOCK = "stock"
    MIXED = "mixed"

@dataclass
class MergerDeal:
    target: str
    acquirer: str
    deal_type: DealType
    offer_price: float
    current_price: float
    break_rate: float = 0.08

def merger_spread(deal: MergerDeal):
    return (deal.offer_price - deal.current_price) / deal.current_price

def kelly_size(prob_success, payoff, loss):
    return (prob_success * payoff - (1 - prob_success) * loss) / payoff
```

**Why Overlooked:** Requires real-time deal intelligence (Bloomberg, SharkRepellent) and legal/regulatory risk assessment; one broken deal can wipe out months of gains.

---

## 3.2 Spin-off Tracking

**Edge:** Spin-offs often outperform due to forced selling by parent-company shareholders who don't want the spin-off, and improved focus post-separation. McConnell & Ovtchinnikov (2004) documented significant abnormal returns.

**Asset Classes:** Equities (child + parent).

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Within 30 days of spin-off completion |
| Focus | "Focusing" spin-outs (non-core assets) outperform |
| Hold period | 22 months optimal |
| Sizing | 2-3% per spin-off |

**Why Overlooked:** Requires tracking SEC filings (Form 10-12B) and understanding post-spin capital structures.

---

## 3.3 Activist Investor Tracking

**Edge:** 13D filings disclose activist stakes and often precede value-unlocking events (board changes, buybacks, M&A). Klein & Zur (2009) found significant abnormal returns post-13D.

**Asset Classes:** Equities, CDS.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Within 5 days of 13D filing |
| Filter | Track record: previous campaigns with >20% returns |
| Wolf-pack | Higher conviction if multiple activists present |
| Exit | Settlement agreement or 12 months |

**Why Overlooked:** Requires EDGAR monitoring and activist track-record databases; retail traders don't parse 13D filings systematically.

---

## 3.4 Central Bank Policy Divergence

**Edge:** Interest rate differentials between major central banks (Fed, ECB, BoJ) drive sustained currency trends and bond spread movements.

**Asset Classes:** FX, rates, bonds.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | 2-year sovereign yield spread crosses 50-day MA |
| Structure | Long high-yield currency, short low-yield currency |
| Confirmation | Forward guidance language divergence (NLP on CB statements) |
| Stop | Spread reverses 25% from entry |

**Why Overlooked:** Requires macroeconomic monitoring and understanding of forward guidance; crypto-native traders ignore fiat rates.

---

## 3.5 Geopolitical Risk Premium

**Edge:** Tail-risk assets (gold, VIX, safe-haven currencies) are systematically underpriced before geopolitical escalations and overpriced after.

**Asset Classes:** Energy, gold, VIX, CHF, JPY, UST.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Pre-event | Enter safe-haven basket when geopolitical news sentiment spikes |
| Post-event | Exit 3-5 days after escalation peaks (mean reversion) |
| Hedge | Short energy if long gold (inflation-neutral) |

**Why Overlooked:** Difficult to quantify "geopolitical risk"; requires news analytics and historical event database.

---

## 3.6 Catastrophe Bond / Insurance-Linked Securities (ILS)

**Edge:** Cat bonds offer 10-12% yields with <0.2 correlation to traditional markets. Post-event spread widening creates entry points.

**Asset Classes:** Cat bonds, sidecars, ILS funds.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Post-natural-disaster spread widening > 200 bps |
| Diversification | Perils (wind, earthquake, wildfire) and regions |
| Max single peril | 15% of ILS allocation |

**Why Overlooked:** Illiquid, minimum ticket sizes $250K+, requires insurance risk modeling.

---

## 3.7 Index Rebalancing Arbitrage

**Edge:** Index additions/deletions create forced buying/selling by passive funds. The price impact is predictable around announcement and effective dates.

**Asset Classes:** Equities, index futures.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Announcement date (S&P, Russell, MSCI) |
| Addition | Long added stock, short index futures |
| Deletion | Short deleted stock, long index futures |
| Exit | Effective date + 1 |
| Crowding filter | Avoid if >5 arbitrageurs already positioned (media sentiment proxy) |

**Why Overlooked:** Requires index methodology expertise and fast execution around announcement dates.

---

## 3.8 Closed-End Fund NAV Discount Mean Reversion

**Edge:** CEFs trade at persistent discounts to NAV that mean-revert. CUNY studies found 14.9-18.2% historical alpha with 7.7-month half-life.

**Asset Classes:** CEF shares.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Discount Z-score > 1.5 (deep discount) |
| Filter | Avoid CEFs with >2% annual expense ratios |
| Exit | Discount reverts to 1-year average |
| Sizing | 3-5% per fund |

**Python Sketch:**
```python
def cef_signal(price, nav, history_discounts):
    discount = (nav - price) / nav
    z = (discount - np.mean(history_discounts)) / np.std(history_discounts)
    return z
```

**Why Overlooked:** Retail confuses CEFs with ETFs; NAV data requires manual scraping or CEFConnect access.

---

## 3.9 SPAC Merger Arbitrage & Redemption Plays

**Edge:** SPACs trade near trust value ($10) pre-merger, providing a floor. Post-2021 reset, many trade below trust value, offering asymmetric upside.

**Asset Classes:** SPAC commons, warrants.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Price < trust value + 2% AND merger vote scheduled |
| Redemption play | If merger likely to fail, buy below trust and redeem at $10+ |
| Risk | Deadline extension without deal, trust value erosion |

**Why Overlooked:** Post-2021 SPAC crash damaged retail confidence; requires parsing DEFM14A proxy filings.

---

## 3.10 Rights Offering / Recapitalization Plays

**Edge:** Subscription discount + over-subscription privilege creates risk-free or high-conviction alpha. Markets often overreact to dilution.

**Asset Classes:** Equities, tradable rights.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Rights trade at >10% discount to theoretical value |
| Structure | Buy rights, exercise at subscription price, sell stock |
| Risk | Deal failure, stock suspension |

**Why Overlooked:** Rights are thinly traded and often excluded from retail broker platforms.


---

# 4. Market Making, Microstructure & DeFi-Native

These strategies exploit structural edges in market microstructure, protocol mechanics, and cross-venue latency. The alpha comes from **structural advantages**—being faster, better capitalized, more inventory-aware, or more sophisticated in risk management than the marginal participant.

**Estimated Sharpe Ratios (Institutional Execution):**
| Strategy | Typical Sharpe | Max Drawdown |
|----------|---------------|--------------|
| Avellaneda-Stoikov MM | 2.5–4.0 | 5–12% |
| Tick Imbalance | 1.8–2.8 | 8–15% |
| Auction Dynamics | 1.5–2.5 | 6–10% |
| Latency Arbitrage | 3.0–6.0* | 2–5% |
| MEV Extraction | 2.0–5.0 | 10–30% |
| Delta-Neutral Yield | 1.2–2.0 | 3–8% |
| DEX-CEX Basis | 1.5–3.0 | 5–12% |
| IL Harvesting | 1.0–2.0 | 15–25% |
| Liquidation Mining | 2.0–4.0 | 20–40% |
| AMM Curve Arb | 2.5–5.0 | 5–10% |
| Cross-Chain Bridge | 1.0–2.5 | 10–20% |
| VPIN/Toxic Flow | 1.5–2.5 | 8–15% |

\* Latency arbitrage Sharpe is path-dependent on colocation and feed handler quality.

---

## 4.1 Avellaneda-Stoikov Inventory-Aware Market Making

**Edge:** Solves the stochastic control problem of maximizing terminal wealth while penalizing inventory deviation from zero. Reservation price adjusts based on inventory to create mean-reverting inventory.

**Asset Classes:** Liquid crypto (BTC, ETH, SOL), FX majors, equity ETFs.

**Venues:** Binance, Bybit, OKX, dYdX, Hyperliquid.

**Core Formula:**
```
r(s, q, t) = s - q * γ * σ² * (T - t)
δ^a + δ^b = γ * σ² * (T - t) + (2/γ) * ln(1 + γ/κ)
```

**Parameters:**
| Symbol | Meaning | Typical Value |
|--------|---------|---------------|
| γ (gamma) | Risk aversion | 0.1–2.0 |
| σ | Volatility | Realized or implied |
| T | Time horizon | 1 day |
| q | Inventory | Dynamic |
| κ | Order arrival intensity | Calibrated from tick data |

**Inventory Management:**
- Soft limit: |q| > Q_soft → aggressively skew quotes
- Hard limit: |q| > Q_hard → halt quoting on aggressive side, cross spread to reduce

**Python Sketch:**
```python
class AvellanedaStoikov:
    def __init__(self, gamma, sigma, T, kappa):
        self.gamma = gamma
        self.sigma = sigma
        self.T = T
        self.kappa = kappa

    def reservation_price(self, s, q, t):
        return s - q * self.gamma * (self.sigma ** 2) * (self.T - t)

    def optimal_spread(self, t):
        return self.gamma * (self.sigma ** 2) * (self.T - t) + (2 / self.gamma) * np.log(1 + self.gamma / self.kappa)
```

**Why Overlooked:** Requires stochastic calculus background and low-latency execution infrastructure.

---

## 4.2 Tick Imbalance & Trade Signing (BVC / Lee-Ready)

**Edge:** Informed order flow leaves footprints in tick data. Bulk Volume Classification (BVC) or Lee-Ready algorithm signs trades as buyer/seller-initiated, revealing accumulation/distribution.

**Asset Classes:** Equities, futures, crypto.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Signal | Cumulative tick imbalance Z-score > \|2.0\| |
| Confirmation | Volume-weighted (BVC) vs. tick-test (Lee-Ready) agree |
| Holding | 1-5 days |

**Python Sketch:**
```python
def lee_ready_sign(close, high, low, prev_close):
    if close > (high + low) / 2:
        return 1  # buyer-initiated
    elif close < (high + low) / 2:
        return -1  # seller-initiated
    else:
        return 1 if close > prev_close else -1

def bvc_sign(volume, bar_close, bar_open, bar_high, bar_low):
    if bar_high == bar_low:
        return 0
    return volume * (2 * (bar_close - bar_low) / (bar_high - bar_low) - 1)
```

**Why Overlooked:** Requires tick-level data and significant compute for real-time classification.

---

## 4.3 Opening & Closing Auction Dynamics

**Edge:** Market-on-close (MOC) and opening auction imbalances create predictable price pressure. Index rebalancing flows, options expiry, and earnings releases amplify auction dynamics.

**Asset Classes:** Equities, ETFs.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Auction imbalance > 3x average 20-day imbalance |
| Direction | Trade with the imbalance for opening, fade for closing (mean reversion post-close) |
| Risk | Hard stop if imbalance reverses in final 30 seconds |

**Why Overlooked:** Requires exchange auction imbalance feeds (NYSE OpenBook, NASDAQ TotalView) and sub-second execution.

---

## 4.4 Cross-Venue Latency Arbitrage (Lead-Lag)

**Edge:** Price discovery happens first on one venue (e.g., CME futures) before propagating to another (e.g., spot exchange). Colocated systems capture the lag.

**Asset Classes:** Crypto (perp vs spot), FX (ECN vs ECN), equities (primary vs dark pool).

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Trigger | Venue A price moves > 1x ATR, Venue B hasn't moved yet |
| Holding | < 1 second |
| Risk | Stale quote detection, exchange downtime |

**Python Sketch:**
```python
async def latency_arb(venue_a_price, venue_b_price, atr, latency_ms):
    if abs(venue_a_price - venue_b_price) > atr and latency_ms < 50:
        direction = 1 if venue_a_price > venue_b_price else -1
        return {'venue': 'B', 'side': 'buy' if direction == 1 else 'sell'}
    return None
```

**Why Overlooked:** Requires colocation, microsecond infrastructure, and exchange fee tiers that retail cannot access.

---

## 4.5 MEV Extraction (Sandwich & Liquidation Sniping)

**Edge:** On Ethereum and other chains, transaction ordering is manipulable. Searchers extract value by sandwiching trades (front-run + back-run) or sniping liquidations.

**Asset Classes:** ERC-20 tokens, DeFi positions.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Sandwich | Target trades > $50K in low-liquidity pools; slip victim by 0.5-1% |
| Liquidation | Monitor lending protocols for health factor < 1.05; pre-position gas |
| Gas strategy | Priority fee 2x block base fee to ensure inclusion |

**Why Overlooked:** Requires Solidity expertise, mempool monitoring, and significant ETH for gas wars.

---

## 4.6 Delta-Neutral Yield Farming (Funding + Staking)

**Edge:** Combine perpetual futures funding rate payments with spot staking yield to harvest 10-30% APR with limited directional risk.

**Asset Classes:** Crypto (ETH, SOL, ATOM).

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Structure | Long spot (+ staking yield), short perp (+ positive funding) |
| Rebalance | When delta exceeds ±2% of notional |
| Venue | Binance/BYBIT perp + on-chain staking (Lido, Marinade) |

**Python Sketch:**
```python
def delta_neutral_yield(spot_price, perp_price, funding_rate, staking_apy, size):
    delta = size * (spot_price - perp_price)
    daily_funding = size * perp_price * funding_rate / 365
    daily_staking = size * spot_price * staking_apy / 365
    return daily_funding + daily_staking, delta
```

**Why Overlooked:** Requires managing positions across CEX and on-chain wallets; funding rates can flip negative.

---

## 4.7 DEX-CEX Perpetual-vs-Spot Basis Arbitrage

**Edge:** Perpetual futures on CEXs and spot prices on DEX AMMs diverge due to differing liquidity profiles and participant bases.

**Asset Classes:** Crypto.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Basis (perp - spot) / spot > 0.3% |
| Structure | Short perp, buy spot on DEX |
| Exit | Basis < 0.1% |
| Risk | Gas costs, slippage, withdrawal delays |

**Why Overlooked:** Requires capital on both CEX and DEX; withdrawal friction and gas costs erode edge for small size.

---

## 4.8 Concentrated LP Impermanent Loss Harvesting

**Edge:** Uniswap v3 concentrated liquidity positions experience impermanent loss when price moves out of range. Sophisticated LPs dynamically adjust ranges to capture fees while minimizing IL.

**Asset Classes:** Crypto LP pairs.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Range width | ±5-10% around current price |
| Rebalance | When price crosses 75% of range width |
| Hedge | Short perpetual hedge for the directional exposure |

**Python Sketch:**
```python
def il_estimate(p0, p1, range_lower, range_upper):
    if p1 < range_lower or p1 > range_upper:
        return -1.0  # 100% in single asset
    # Approximate IL for concentrated position
    price_ratio = p1 / p0
    return 2 * np.sqrt(price_ratio) / (1 + price_ratio) - 1
```

**Why Overlooked:** Requires active monitoring and gas costs for rebalancing; passive LPs get harvested by active ones.

---

## 4.9 Predictive Liquidation Mining

**Edge:** Predict which leveraged positions will be liquidated and front-run the liquidation bots by being the liquidator yourself or trading ahead of the cascade.

**Asset Classes:** Crypto perps, DeFi lending.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Trigger | Health factor < 1.10 AND large position size |
| Action | Pre-position liquidation bot or short asset ahead of cascade |
| Gas | Ultra-high priority to win liquidation race |

**Why Overlooked:** Requires on-chain node infrastructure and mempool priority gas auctions.

---

## 4.10 AMM Curve Arbitrage (StableSwap Inefficiencies)

**Edge:** Curve-style StableSwap pools use hybrid constant-product / constant-sum formulas that create localized price deviations from $1.00 during large flows.

**Asset Classes:** Stablecoins, liquid staking tokens.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Pool price deviates from oracle price by > 0.05% |
| Structure | Buy cheap stable on Curve, sell expensive on CEX/DEX |
| Exit | Immediate |

**Why Overlooked:** Requires smart contract interaction and flash loan capital; edge is milliseconds wide.

---

## 4.11 Cross-Chain Bridge Arbitrage

**Edge:** Assets trade at different prices across chains due to bridge liquidity constraints and finality delays.

**Asset Classes:** Bridged assets (ETH, WBTC, USDC).

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | Price delta > 0.5% after bridge fees |
| Structure | Buy on cheap chain, bridge, sell on expensive chain |
| Risk | Bridge hack risk, finality delays (30 min for Bitcoin) |

**Why Overlooked:** Bridge transfers are slow and risky; requires capital fragmented across chains.

---

## 4.12 VPIN / Order Flow Toxicity Detection

**Edge:** Volume-synchronized probability of informed trading (VPIN) predicts short-term volatility and adverse selection. High VPIN means toxic flow → avoid market orders, or trade the volatility spike.

**Asset Classes:** Equities, futures, crypto.

**Parameters:**
| Parameter | Rule |
|-----------|------|
| Entry | VPIN > 0.70 (high toxicity) → enter volatility long (straddle) or pause market making |
| Bucket size | Volume buckets of 1/50th of average daily volume |
| Update | Real-time |

**Python Sketch:**
```python
def vpin_calc(buy_volume, sell_volume, buckets):
    imbalances = [abs(b - s) / (b + s) for b, s in buckets if b + s > 0]
    return np.mean(imbalances)
```

**Why Overlooked:** Requires tick-data volume classification and real-time computation; acts as a filter rather than a standalone strategy.


---

# 5. Cross-Asset Risk Premia & Behavioral Finance

These strategies are grounded in academic finance and exploit persistent anomalies across asset classes. They are particularly valuable because they tend to be **uncorrelated with directional market beta** and with each other.

---

## 5.1 Cross-Sectional Momentum (Jegadeesh & Titman)

**Edge:** Stocks with highest returns over the past 3-12 months continue to outperform those with the worst returns. Jegadeesh & Titman (1993, 2001) found ~12% annualized alpha for the (12-1) strategy.

**Behavioral Drivers:**
- Slow information diffusion (Hong & Stein, 1999)
- Conservatism bias (Barberis, Shleifer & Vishny, 1998)
- Disposition effect (Grinblatt & Han, 2005)

**Asset Classes:** U.S. equities, international equities, country indices, currencies, commodities, corporate bonds.

**Construction:**
| Parameter | Rule |
|-----------|------|
| Formation | 12 months (skip most recent month) |
| Holding | 1 month |
| Universe | All liquid assets in target class |
| Long | Top decile (winners) |
| Short | Bottom decile (losers) |
| Weighting | Equal-weighted or volatility-scaled |

**Risk Management:**
- **Volatility scaling** (Barroso & Santa-Clara, 2015): Scale by inverse realized vol
- **Crash protection** (Daniel & Moskowitz, 2016): Reduce exposure after extended bear markets
- **Max drawdown control:** Hard stop at -15% monthly

**Python Sketch:**
```python
def cross_sectional_momentum(returns_df, formation_months=12, hold_months=1, skip_months=1):
    formation = returns_df.shift(skip_months).rolling(formation_months).apply(lambda x: (1 + x).prod() - 1)
    ranks = formation.rank(axis=1, pct=True)
    longs = ranks >= 0.9
    shorts = ranks <= 0.1
    portfolio = longs.astype(int) - shorts.astype(int)
    return portfolio
```

**Why Overlooked:** Retail chases recent winners without the systematic skip-month, volatility scaling, or short leg.

---

## 5.2 Time-Series Momentum / Trend Following (Moskowitz, Ooi & Pedersen)

**Edge:** Assets with positive past returns continue to trend upward; negative trends continue downward. Moskowitz, Ooi & Pedersen (2012) demonstrated this across 58 liquid instruments.

**Asset Classes:** Equities, bonds, currencies, commodities.

**Construction:**
| Parameter | Rule |
|-----------|------|
| Signal | Sign of past 12-month return |
| Position | Long if positive, short if negative |
| Volatility scaling | Target 10% annualized volatility per instrument |
| Rebalance | Monthly |

**Python Sketch:**
```python
def tsmom_signal(returns, lookback=252):
    past_return = (1 + returns).rolling(lookback).prod() - 1
    sig = np.sign(past_return)
    vol = returns.rolling(63).std() * np.sqrt(252)
    target_vol = 0.10
    weights = sig * (target_vol / vol)
    return weights
```

**Why Overlooked:** Requires cross-asset futures trading and volatility scaling; retail applies static position sizes and gets whip-sawed.

---

## 5.3 Carry Trade Across All Asset Classes

**Edge:** High-yielding assets tend to outperform low-yielding assets on a risk-adjusted basis. Lustig, Roussanov & Verdelhan (2011) showed this in FX; it extends to bonds, commodities, and crypto funding.

**Asset Classes:** FX, bonds, commodities (backwardation), crypto perps.

**Construction:**
| Parameter | Rule |
|-----------|------|
| Signal | Rank by yield / roll yield / funding rate |
| Long | Top 3 deciles |
| Short | Bottom 3 deciles |
| Volatility scaling | Essential — unscaled carry has severe tail risk |

**Python Sketch:**
```python
def carry_signal(yields_df):
    ranks = yields_df.rank(axis=1, pct=True)
    longs = ranks >= 0.7
    shorts = ranks <= 0.3
    return longs.astype(int) - shorts.astype(int)
```

**Why Overlooked:** Crypto funding rate carry is well-known, but bond/commodity carry and cross-asset integration are ignored by crypto-native traders.

---

## 5.4 Value Factor in FX and Commodities (Asness / Della Corte)

**Edge:** Currencies and commodities with low prices relative to fundamentals outperform expensive ones. Asness et al. (2013) and Menkhoff et al. (2017) demonstrated value in FX.

**Asset Classes:** FX, commodities.

**Construction (FX):**
| Parameter | Rule |
|-----------|------|
| Value proxy | Real exchange rate deviation from 5-year average |
| Long | Most undervalued currencies |
| Short | Most overvalued currencies |

**Why Overlooked:** Requires purchasing power parity (PPP) data and long holding periods; crypto traders lack patience for 3-5 year value convergence.

---

## 5.5 Low Volatility Anomaly / Betting Against Beta (Frazzini & Pedersen)

**Edge:** Low-beta/low-volatility stocks outperform high-beta stocks on a risk-adjusted basis. The market's leverage constraints and lottery preferences overprice high-beta assets.

**Asset Classes:** Equities, bonds, FX.

**Construction:**
| Parameter | Rule |
|-----------|------|
| Signal | 1-year realized volatility or estimated beta |
| Long | Lowest vol/beta decile |
| Short | Highest vol/beta decile |
| Weighting | Volatility-scaled or inverse-beta weighted |

**Why Overlooked:** Retail wants "high growth" and ignores the empirical superiority of boring, low-vol compounds.

---

## 5.6 Gross Profitability Premium (Novy-Marx)

**Edge:** Firms with high gross profits-to-assets outperform. Novy-Marx (2013) showed this is as powerful as value and negatively correlated with it.

**Asset Classes:** Equities.

**Construction:**
| Parameter | Rule |
|-----------|------|
| Signal | Gross Profit / Total Assets |
| Long | Top decile |
| Short | Bottom decile |

**Python Sketch:**
```python
def profitability_signal(gross_profit, total_assets):
    gp_ratio = gross_profit / total_assets
    return gp_ratio.rank(pct=True)
```

**Why Overlooked:** Requires fundamental accounting data; retail prefers price-based signals.

---

## 5.7 Investment / Asset Growth Anomaly (Cooper, Gulen & Schill)

**Edge:** Firms with high asset growth underperform. Corporate investment tends to happen at cyclical peaks and destroys shareholder value.

**Asset Classes:** Equities.

**Construction:**
| Parameter | Rule |
|-----------|------|
| Signal | Year-over-year growth in total assets |
| Long | Lowest asset growth decile |
| Short | Highest asset growth decile |

**Why Overlooked:** Counterintuitive — investors assume growth is good; the anomaly requires shorting "growth" companies.

---

## 5.8 Accruals Anomaly (Sloan)

**Edge:** Firms with high accruals (non-cash earnings) have lower future earnings persistence and underperform. Sloan (1996) found ~10% annual spread between low and high accrual firms.

**Asset Classes:** Equities.

**Construction:**
| Parameter | Rule |
|-----------|------|
| Signal | (ΔCurrent Assets - ΔCash) - (ΔCurrent Liabilities - ΔDebt) - Depreciation |
| Standardize | Accruals / Average Total Assets |
| Long | Lowest accrual decile |
| Short | Highest accrual decile |

**Python Sketch:**
```python
def accruals_ratio(current_assets, cash, current_liabilities, debt, depreciation, avg_total_assets):
    accruals = (current_assets.diff() - cash.diff()) - (current_liabilities.diff() - debt.diff()) - depreciation
    return accruals / avg_total_assets
```

**Why Overlooked:** Requires reading financial statements; retail focuses on EPS headlines, not cash flow quality.

---

## 5.9 Net Share Issuance / Buyback Anomaly (Babenko, Ikenberry)

**Edge:** Firms that issue shares underperform; firms that buy back shares outperform. Ikenberry et al. (1995) found 12.1% abnormal returns for buyback firms over 4 years.

**Asset Classes:** Equities.

**Construction:**
| Parameter | Rule |
|-----------|------|
| Signal | Net issuance = shares issued - shares repurchased |
| Long | Negative net issuance (buybacks) |
| Short | Positive net issuance (dilution) |

**Why Overlooked:** Requires tracking share count changes across quarterly filings; SPAC/tech issuance boom masked this recently.

---

## 5.10 Lottery Ticket / MAX Effect (Bali, Cakici & Whitelaw)

**Edge:** Stocks with high maximum daily returns (lottery-like payoff distribution) have lower subsequent average returns. Investors overpay for positive skewness.

**Asset Classes:** Equities.

**Construction:**
| Parameter | Rule |
|-----------|------|
| Signal | MAX = maximum daily return over past month |
| Long | Lowest MAX decile (boring stocks) |
| Short | Highest MAX decile (lottery stocks) |

**Why Overlooked:** Retail loves meme stocks and high-vol lottery tickets; this strategy systematically shorts them.

---

## 5.11 Attention-Induced Return Reversal (Da, Engelberg & Gao)

**Edge:** Stocks with sudden attention spikes (Google Trends, news volume) experience short-term overreaction and subsequent reversal.

**Asset Classes:** Equities.

**Construction:**
| Parameter | Rule |
|-----------|------|
| Signal | Abnormal Google Trends or news volume (Z-score > 2.0) |
| Short | Attention spike stocks (1-week horizon) |
| Cover | 1 week later |

**Python Sketch:**
```python
def attention_reversal(trends, returns, lookback=5):
    trend_z = (trends - trends.rolling(90).mean()) / trends.rolling(90).std()
    signal = -np.sign(returns.shift(1)) * (trend_z > 2).astype(int)
    return signal
```

**Why Overlooked:** Requires alternative data (Google Trends, news APIs); retail is the attention-driven buyer being exploited.

---

## 5.12 Overnight vs. Intraday Return Decomposition (Lou, Polk & Skouras)

**Edge:** Momentum profits accrue disproportionately overnight (close-to-open), while intraday returns exhibit reversal. This has critical implications for execution timing.

**Asset Classes:** Equities.

**Construction:**
| Parameter | Rule |
|-----------|------|
| Overnight return | (Open_t - Close_t-1) / Close_t-1 |
| Intraday return | (Close_t - Open_t) / Open_t |
| Signal | Momentum on overnight returns, reversal on intraday returns |
| Execution | Enter at close, exit at open (for momentum); enter at open, exit at close (for reversal) |

**Python Sketch:**
```python
def overnight_intraday_decomp(opens, closes):
    overnight = (opens - closes.shift(1)) / closes.shift(1)
    intraday = (closes - opens) / opens
    return overnight, intraday

def overnight_momentum(overnight_returns, lookback=20):
    return overnight_returns.rolling(lookback).mean()
```

**Why Overlooked:** Requires understanding of market microstructure and precise execution timing; most retail strategies ignore the open/close decomposition.

---

## Appendix: Implementation Roadmap

### Phase 1 — Immediate (Weeks 1-4)
1. **Options & Volatility:** Implement Skew Curvature Z-score and VIX Term Structure Carry
2. **Behavioral:** Implement Cross-Sectional Momentum and Attention Reversal using existing data feeds
3. **Microstructure:** Integrate VPIN as a toxicity filter for all existing strategies

### Phase 2 — Short Term (Months 2-3)
1. **Fixed Income:** Implement Yield Curve Steepener/Flattener using Treasury futures data
2. **Commodities:** Implement Roll Yield Harvesting for top 10 liquid futures
3. **DeFi:** Implement Delta-Neutral Yield Farming and DEX-CEX Basis Arbitrage

### Phase 3 — Medium Term (Months 4-6)
1. **Event-Driven:** Build SEC EDGAR scraper for Merger Arbitrage and Spin-off Tracking
2. **Market Making:** Deploy Avellaneda-Stoikov prototype on Hyperliquid or dYdX
3. **Global Macro:** Integrate central bank statement NLP for Policy Divergence signals

### Phase 4 — Long Term (Months 6-12)
1. **Advanced Options:** Deploy PCA-Weighted Dispersion Trading and Jump-Decomposed Variance Premium
2. **Fixed Income:** Build CDS Basis and Repo Arbitrage infrastructure
3. **Cross-Asset:** Launch integrated Risk Premia portfolio (momentum + carry + value + low vol)

---

## References & Further Reading

- Aït-Sahalia, Y. (2004). *Disentangling Diffusion from Jumps*. Journal of Financial Economics.
- Asness, C., et al. (2013). *Value and Momentum Everywhere*. Journal of Finance.
- Bali, T., Cakici, N., & Whitelaw, R. (2011). *Maxing Out: Stocks as Lotteries*. Journal of Financial Economics.
- Barberis, N., Shleifer, A., & Vishny, R. (1998). *A Model of Investor Sentiment*. Journal of Financial Economics.
- Barroso, P., & Santa-Clara, P. (2015). *Momentum Has Its Moments*. Journal of Financial Economics.
- Branch, B., & Yang, T. (2003). *Merger Arbitrage*. Financial Analysts Journal.
- Cooper, M., Gulen, H., & Schill, M. (2008). *Asset Growth and the Cross-Section of Stock Returns*. Journal of Finance.
- Cremers, M., & Weinbaum, D. (2010). *Deviations from Put-Call Parity*. Journal of Financial and Quantitative Analysis.
- Daniel, K., & Moskowitz, T. (2016). *Momentum Crashes*. Journal of Financial Economics.
- Da, Z., Engelberg, J., & Gao, P. (2011). *In Search of Attention*. Journal of Finance.
- Frazzini, A., & Pedersen, L. (2014). *Betting Against Beta*. Journal of Financial Economics.
- Grinblatt, M., & Han, B. (2005). *Prospect Theory and Disposition Effect*. Journal of Finance.
- Hong, H., & Stein, J. (1999). *A Unified Theory of Underreaction*. Journal of Finance.
- Ikenberry, D., Lakonishok, J., & Vermaelen, T. (1995). *Market Underreaction to Open Market Share Repurchases*. Journal of Financial Economics.
- Jegadeesh, N., & Titman, S. (1993, 2001). *Returns to Buying Winners and Selling Losers*. Journal of Finance.
- Klein, A., & Zur, E. (2009). *Entrepreneurial Shareholder Activism*. Journal of Finance.
- Lou, D., Polk, C., & Skouras, S. (2019). *A Tug of War: Overnight versus Intraday Expected Returns*. Critical Finance Review.
- Lustig, H., Roussanov, N., & Verdelhan, A. (2011). *Common Risk Factors in Currency Markets*. Review of Financial Studies.
- McConnell, J., & Ovtchinnikov, A. (2004). *Predictability of Long-Term Spinoff Returns*. Journal of Investment Management.
- Menkhoff, L., et al. (2017). *Currency Value*. Review of Financial Studies.
- Moskowitz, T., Ooi, Y., & Pedersen, L. (2012). *Time Series Momentum*. Journal of Financial Economics.
- Novy-Marx, R. (2013). *The Other Side of Value*. Journal of Financial Economics.
- Sloan, R. (1996). *Do Stock Prices Fully Reflect Information in Accruals*. Journal of Accounting and Economics.

---

*Document compiled by Kimi Code CLI subagent research fleet.*  
*For questions or implementation support, refer to the Python sketches in each strategy section.*
