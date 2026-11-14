# Per-Class Priority Matrix — final_v2

**Purpose:** rank the realistic paths to profitability by evidence, feasibility, data availability,
and expected net-of-cost Sharpe. No class is currently proved. This is a prioritization for the
next program, not a claim.

| Class | Priority | Realistic edge | Best next experiment | Data needed | Expected net Sharpe | Main blocker |
|---|---|---|---|---|---|---|
| **FUTURES** | **HIGH** | TSMOM + curve carry risk premia (documented, modest, crowded) | Vol-targeted 12-month TSMOM on 16 continuous financial futures, benchmark-relative, true DSR/PBO/SPA | Continuous contracts (CME/ICE/Refinitiv), roll schedule | 0.3–0.7 | Gate-blocked; no continuous data; ETF proxies invalid |
| **CRYPTO** | **HIGH (feasibility), LOW return** | Funding/basis carry (real, low-vol, capacity-limited) | Capital-adjusted cross-venue funding+basis carry, ROC vs T-bill, 1.5× capital, block null | Binance/OKX/Bybit funding, basis, fee tiers, margin | 0.2–0.6 (ROC) | 3.7–4.8% ROC vs 4.5% cash; no options/L2 |
| **BOND** | **HIGH** | UST curve carry + roll-down, DV01-neutral; credit-spread mean reversion | Mechanical roll-down on ZT/ZF/ZN/ZB with Treasury/FRED yields, no forecast | Treasury/FRED curve, futures prices | 0.3–0.6 | n=1 policy-clean; no curve harness |
| **EQUITY** | **MEDIUM** | PEAD/SUE and value/quality (untested cross-section) | SUE event study from SEC XBRL filed dates; beta-neutral, t+2 execution, 2× cost | SEC XBRL, Nasdaq prices, earnings dates | 0.2–0.6 | No fundamentals/earnings pipeline |
| **FOREX** | **MEDIUM** | G10 carry via CIP forwards/currency ETFs; 12m TSMOM | Long high-forward-discount / short low, via FX futures or currency ETFs | Policy rates, forwards, ETF prices | 0.2–0.5 | Retail spot/CFD disqualified; below 1.0 gate |
| **ETF** | **LOW** | Volatility-risk-premium overlay (covered calls/put-writing); low-vol/risk parity | SPY buy-write (~2% OTM 30-DTE), beta-matched benchmark, total-return data | Options chains, BXM/PUT histories | 0.0–0.4 | All price families failed; crash-convex |
| **COMMODITY** | **LOW** | Roll-yield/curve carry (real but capacity-limited) | Long backwardation / short contango on 20 real curves after purging crypto proxies | Licensed futures curves | 0.0–0.4 | Gate-blocked; no curve data; proxy rows |
| **MUTUAL FUNDS** | **LOW / NOT_BUILT** | Fee arithmetic + allocation (beta, not alpha) | Expense-ratio selection + low-cost allocation sleeve; de-advertise the signal class | Survivorship-free NAV, expense ratios | n/a (beta) | Not a tradable signal class; no NAV/resolver |

## How to read the priorities

- **HIGH** = a documented mechanism + accessible data + a plausible path to a defensible sleeve; not
  a guarantee of >1.0 Sharpe.
- **MEDIUM** = real but likely below the 1.0 gate on available data; worth one pre-registered test.
- **LOW** = likely absent or untestable without new data; do not spend another sweep.
- **NOT_BUILT** = do not advertise or fabricate a class; a product sleeve is a separate decision.

## The only positive candidates worth one more test

1. **Crypto funding/basis carry** (capital-adjusted, cross-venue) — real but marginal; measure ROC.
2. **Futures TSMOM + carry** — strongest academic basis; needs continuous data.
3. **Bond curve carry/roll-down** — low-vol, capacity-limited; clean accrual.
4. **Equity PEAD/SUE** — untested cross-section; event-driven.
5. **ETF covered-call/VRP** — only untested ETF family with an economic mechanism.

## What not to do

- No more parameter sweeps on the same 730-day window.
- No post-hoc regime filters.
- No symbol cherry-picking after OOS.
- No "all other classes negative" claims without checking `recent_closed` (EQUITY 1.154, ETF 1.036).
- No enabling mega_mutation (`production_enable=true`) on the current evidence.
- No MUTUAL_FUND build to fill a dashboard gap.
