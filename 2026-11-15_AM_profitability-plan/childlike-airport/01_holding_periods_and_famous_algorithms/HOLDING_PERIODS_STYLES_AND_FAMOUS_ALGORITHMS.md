# 01 — Holding Periods, Trading Styles, and “Proven/Famous” Algorithms (Fact-Checked)

**Purpose:** map each asset class to viable holding periods/styles and to well-known algorithms/contest exemplars — with grounded caveats. “Famous” or “contest-winning” ≠ proven edge in *this* system; every idea must clear net, benchmark-relative, leak-safe, forward gates.

## A. Style × holding-period matrix (practical viability, retail/this-repo context)

| Style | Typical holding | Best-fit classes (if edge exists) | Structural headwinds | Viability here (today) |
|---|---:|---|---|---|
| **Buy & hold / allocation** | Years | Broad ETFs, mutual funds, quality equities/bonds | Behavioral drawdowns, concentration | **Highest probability (beta)**; not prediction alpha |
| **Tactical asset allocation (TAA) / rotation** | Weeks–months (rebalance monthly/quarterly) | ETFs, mutual funds, equity indices, some commodities/bonds | Whipsaw, regime shifts, taxes/costs | Promising as **risk-managed smart-beta** if forward-validated (e.g. momentum/dual-momentum style) |
| **Position / trend-following** | Weeks–months | Futures/commodities, FX majors, liquid crypto, indices/ETFs | Trend breaks, funding/roll, gap risk | Plausible for diversified trend (TSMOM/CTA-style) **only net & robust** |
| **Swing** | Days–weeks | Equities, ETFs, liquid crypto/FX, commodities | Overnight/gap risk, news shocks | Research candidate; requires intrabar-realistic exits & costs |
| **Day trading** | Intraday (flat EOD) | Liquid futures, FX, large-cap equities/ETFs, top crypto | Spread/slippage/fees, latency, PDT/margin rules, adverse selection | **Low probability** until intrabar-honest net proof at scale |
| **Scalping / HFT-like** | Seconds–minutes | Microstructure-rich venues only | Costs dominate, infra/latency arms race, queue priority | **Not viable** for this stack/retail assumptions |

## B. Per-asset-class analysis

### 1) CRYPTO
- **Holding/styles:** position/swing trend or regime-filtered mean-reversion most plausible; day/scalp structurally costly and fill-sensitive (repo shows stop-fill/expiry/0% issues).
- **Proven/famous algorithm families (grounded):**
  - **Time-series momentum (TSMOM):** Moskowitz, Ooi & Pedersen (2012) show persistent trend across assets/timeframes; crypto implementations must include funding/fees/slippage and bear-regime tests.
  - **Mean-reversion / VWAP/band reversion:** works conditionally in ranges; fails in trends — requires regime filter and conservative fills (v12 PBO failure illustrates overfit risk).
  - **Funding/carry & basis:** documented anomalies exist but capacity/fee/slippage/exchange risk matter; treat as carry, not free alpha.
  - **Volatility breakout / Donchian-style:** classic Turtle/trend breakout concept; profitability depends on diversification, costs, and drawdown control.
- **Contest note:** TradingView “The Leap”/strategy contests reward short-window performance and can be overfit/survivorship-biased — **not proof** without OOS/forward net replication.

### 2) EQUITY (US)
- **Holding/styles:** long-term buy/hold & factor/quality tilts (beta) highest probability; swing/position for systematic signals; intraday only with strong execution evidence.
- **Proven/famous families:**
  - **Fama–French factors (value/size/profitability/investment) & momentum (Carhart):** academically documented premia (time-varying, can underperform for years; implementation/costs matter).
  - **Connors RSI(2) short-term mean-reversion:** popularized by Larry Connors/Cesar Alvarez (e.g. *Short Term Trading Strategies That Work*); historically tested on liquid indices/ETFs — edge can decay and is regime/transaction-cost sensitive.
  - **Dual momentum (absolute + relative):** Gary Antonacci; widely cited for TAA/rotation — reduces drawdowns in some regimes, not guaranteed.
  - **Trend following / moving-average overlays (e.g. Faber 10-month):** Meb Faber; documented risk-reduction/whipsaw tradeoffs.
  - **Earnings momentum/PEAD (post-earnings announcement drift):** Bernard & Thomas (1989) and large literature; requires timely data and cost-aware execution.
  - **CAN SLIM / growth-momentum:** William O’Neil; discretionary/systematized variants exist — survivorship and regime dependence high.

### 3) ETF
- **Holding/styles:** ideal for long-term core, rebalanced allocation, and monthly/quarterly TAA/momentum rotation; tactical swing possible on liquid ETFs.
- **Proven/famous families:** same as equity/factor/TAA/dual-momentum applied to diversified baskets; **cost/turnover** is decisive. Sector/relative-strength rotation is common in contests but must be net-of-cost OOS.

### 4) MUTUAL FUNDS
- **Holding/styles:** **long-term buy & hold / periodic rebalance** (next-NAV pricing, trading restrictions/fees in many funds) — **not** suitable for day/swing “picks” with intrabar stops.
- **“Proven” approach:** low-cost, diversified index funds capturing market/bond premia; persistence of active alpha is weak after fees (SPIVA-style evidence broadly shows many active funds underperform benchmarks over long horizons — treat as strong prior, verify per fund/class).
- **System implication:** evaluate as **allocation sleeve** (NAV-based, net-of-ER) vs risk-matched benchmark, not as intraday prediction.

### 5) BOND / RATES
- **Holding/styles:** long-term ballast or duration/credit allocation; trend/risk-parity overlays are institutional (AQR/bridgewater-style concepts) but require careful carry/duration/rate-regime modeling.
- **Famous families:** carry, duration, value, defensive/quality in FI factor research; trend-following on bond futures — sensitive to regime shifts (e.g. inflation transitions).

### 6) FOREX
- **Holding/styles:** position/swing on liquid majors if any; scalping/day-trade extremely cost/edge sensitive.
- **Proven/famous families:** **carry trade** (UIP deviations documented but crash risk), **trend/momentum** in FX (documented in some samples), **value (PPP/REER)** long-horizon — all require spread/roll modeling and drawdown controls.

### 7) COMMODITY / FUTURES
- **Holding/styles:** position/swing trend-following (months) and seasonal/carry where appropriate; diversified portfolios standard.
- **Proven/famous families:**
  - **CTA/trend-following (TSMOM, breakout, moving-average):** large academic/practitioner literature (e.g. Moskowitz et al.; AQR/managed-futures research) — works over long samples but cyclical with deep drawdowns.
  - **Turtle trading (Donchian breakout):** Richard Dennis/William Eckhardt — rules-based breakout with strict risk; performance varies by era/portfolio.
  - **Carry/roll & term-structure strategies:** basis/curve effects documented; contract-specific and roll-sensitive.
  - **COT/positioning signals:** useful context; mixed predictive power and easy to overfit (repo notes COT issues).

### 8) Prediction markets (Kalshi/Polymarket) — copy-trading surface
- **Holding/styles:** event-time to resolution (hours–months); not traditional OHLC “scalping” in the same way — edge is probabilistic mispricing vs fees/spread/limits.
- **“Proven/famous” approaches:** market-making, arbitrage (cross-venue/related contracts), information/timing edges — require fast/accurate resolution modeling and strict cost/limit handling (see `02_current_state_and_risk_reality`).

## C. Contest exemplars (inspiration, not validation)
- **TradingView:** “The Leap” and community strategy contests highlight risk-adjusted/creative rules on limited windows — **selection bias/overfit risk**; replicate on independent data with costs.
- **Rob Hoffman (IRB/Hoffman Inventory Retracement Bar):** popular price-action/retracement methodology taught widely; discretionary/context-dependent — **no guarantee** and must be codified/tested objectively to count as system edge.
- **Other noted names in quant/trading culture:** Ed Seykota (trend), Larry Williams (volatility/breakout concepts), Jim Simons/Renaissance (not publicly reproducible) — useful as principles, not copyable proof.

## D. Fact-check principles (apply to every “winner” claim)
1. **Edge vs beta:** beating cash ≠ beating SPY/buy-and-hold on a risk-adjusted, net basis.
2. **Costs & frictions:** include spread, slippage, fees, funding, roll, borrow, taxes/turnover.
3. **Multiple testing & overfit:** many trials inflate Sharpe/PF (require DSR/PBO, pre-registration).
4. **Non-stationarity:** edges decay; require subperiod/regime stability and forward paper.
5. **Reproducibility:** bar-by-bar, no look-ahead, next-bar/NAV realism, auditable fills.

*Sources/principles: Moskowitz-Ooi-Pedersen (TSMOM, 2012); Fama-French/Carhart factor literature; Connors & Alvarez (RSI(2)); Antonacci (Dual Momentum); Faber (TAA); Bernard & Thomas (PEAD); managed-futures/CTA research; SPIVA-style active-vs-index findings (general). Contest/method mentions are descriptive, not endorsements.*
