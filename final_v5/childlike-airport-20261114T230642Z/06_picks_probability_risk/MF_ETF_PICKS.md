# 06 — MF/ETF “Solid Picks” (Viability, Probability, Risk, Risk-Adjusted, Methodologies)

**Status:** **Not money-ready / not proven in-system.** Treat below as **candidate baseline/overlay sleeves** contingent on data/mark/cost plumbing and passing gated validation (see `02_finalized_plan`). Probabilities are **illustrative, evidence-conditioned ranges** (not guarantees) given diversified, low-cost, long-horizon behavior and current absence of validated in-house edge.

## Evidence & constraints
- MF metadata/ranker artifacts referenced historically (`alpha_engine/data/mutual_fund_metadata.csv`, `audit_dashboard/data/mutut_fund_rankings.json`, `alpha_engine/mutual_fund_ranker.py`) but **MF class/wiring and closed, net-of-fee evidence reported incomplete/misaligned** in inspected state; must rebuild/verify.
- ETF: active/sector/decay pick files exist (e.g. `alpha_engine/data/active_picks_etf.json` 14 picks) but **money-ready verdict: ETF insufficient (n=44, WR 2.27%, PF 0.0219, inflation-flag context)** — no current proven edge.
- Therefore: **no “solid pick” claim from live system performance**; selections prioritize accessibility ($0-min/no-load where applicable), ultra-low cost, diversification, and transparent methodology, to be validated net-of-fee vs benchmark.

## Candidate sleeves (low-capital, low-fee)

### A. Mutual funds (baseline core; verify $0-min/no-load/ER at time of use)
| Candidate | Role | ER (reported) | Min/Load | Methodology | P(success)* | Risk (qual.) | Risk-adjusted view |
|---|---|---|---|---|---|---|---|
| **FXAIX** (Fidelity 500 Idx) | US large-cap core | ~0.015% | $0 / no-load | Passive market-cap beta | 55–65% (1y vs cash; higher multi-yr) | Med-High (equity DD) | Exp. Sharpe ~0.3–0.6 long-run beta; cost drag minimal |
| **FSKAX** (Total US Mkt) | Broad US core | ~0.015% | $0 / no-load | Passive total-market beta | 55–65% | Med-High | Similar; more diversification than S&P-only |
| **SWPPX / SWTSX** (Schwab) | US large/total core | ~0.02% / 0.03% | $0 / no-load | Passive beta | 55–65% | Med-High | Low-fee beta sleeve |
| **FXNAX** (US Bond Idx) | Defensive ballast | ~0.025% | $0 / no-load | Passive agg-like duration | 50–60% (risk-reduction role) | Low-Med (rate/credit) | Lowers portfolio vol/DD; Sharpe contribution via diversification |
| **FSGGX / SWISX** (Intl) | Diversifier | ~0.055% / 0.06% | $0 / no-load | Passive ex-US | 50–60% | Med-High (FX/geo) | Diversification benefit; cyclical |

\*P(success) = illustrative probability of positive real/nominal total return over a 1y horizon conditioned on diversified hold and no adverse timing; **not a system edge signal**. Multi-year holding generally increases probability but not guaranteed.

### B. ETFs (intraday-liquidable baseline/overlay; verify spreads/costs)
| Candidate | Role | ER (typ.) | Methodology | P(success)* | Risk (qual.) | Risk-adjusted view |
|---|---|---|---|---|---|---|
| **VTI / ITOT / SCHB** | Broad US equity | ~0.03% | Passive total-market | 55–65% | Med-High | Core beta; efficient implementation |
| **VOO / SPY** | S&P 500 | ~0.03% / 0.095% | Passive large-cap | 55–65% | Med-High | SPY higher ER/spread tradeoffs |
| **BND / AGG** | US bond core | ~0.03% | Passive agg duration | 50–60% | Low-Med | Ballast; rate-sensitive |
| **SGOV** | Cash-like T-bill | ~0.09% | Ultra-short gov’t | 60–70% (nominal, carry-regime dep.) | Very Low | Capital preservation/yield proxy; benchmark for carry |
| **VXUS** | ex-US equity | ~0.07% | Passive intl | 50–60% | Med-High | Diversifier |

## Portfolio/risk construction (methodology)
- **Allocation (example, not advice):** risk-matched core (e.g. 60/40 equity/bond or vol-targeted) using only validated, low-cost instruments; SGOV as cash/risk-off buffer.
- **Sizing:** max position/correlation caps; vol targeting; rebalance bands (avoid churn/costs). MF trades at NAV (next-NAV) — no intraday timing edge assumed.
- **Costs:** include ER, spreads/commissions (ETF), any loads/short-term fees (avoid), tax drag awareness.
- **Benchmarks:** compare net-of-fee to risk-matched benchmark (e.g. 60/40, SPY/AGG blend) over same window.

## What would make a pick “solid” here (acceptance)
1. Clean data & marks (NAV/close), correct class wiring, reconciled PnL.
2. Net-of-fee walk-forward/OOS vs risk-matched benchmark with controlled MDD.
3. Stability across subperiods/regimes; no leakage; reproducible.
4. Paper-forward with live marks/NAV and monitored drift/kill-switch.

## Key risks
- **Market/drawdown:** equity sleeves can lose >30–50% peak-to-trough in crises.
- **Rate/duration:** bond funds lose when yields rise (duration risk).
- **Tracking/liquidity/cost:** spreads, premiums/discounts (ETF), fee/tax drag.
- **Model/process:** false confidence from insufficient/tainted in-house evidence; regime shifts.
- **Implementation:** next-NAV execution (MF), stale marks, data gaps (current blocker).

**Conclusion:** Prefer low-cost indexed MF/ETF sleeves as **baseline/overlay candidates** only after plumbing + validation; do not treat as proven alpha.
