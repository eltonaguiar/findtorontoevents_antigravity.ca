# Clean-Bar Archetype Scorecard — 8 archetypes, one gate-stack (2026-06-04)

All built on the identical clean-bar pipeline (real yfinance daily, walk-forward, fixed textbook
params, gated by #111 attribution vs a real benchmark + bootstrap PF CI + cost-drag + Sharpe/MDD).
Latest 3 (crypto momentum, ETF sector-rotation, ETF inverse-vol risk-parity) built by a parallel
agent swarm 2026-06-04. VALIDATED requires attribution t>=2.0 AND IR>=0.10 AND bootstrap PF lower>1
AND Sharpe>=1.0 AND MDD<=20%.

| Archetype | n | PF | Sharpe | MDD | attr t | beta | bootstrap lo | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **ETF dual-momentum (cross-asset)** | 48 | 3.57 | 1.62 | -12% | **2.36** | 0.34 | 1.64 | ✅ **VALIDATED** (H-103) |
| ETF sector-rotation | 48 | 2.78 | 1.37 | -10% | 0.82 | 0.85 | 1.34 | MIXED (raw strong, alpha n.s.) |
| ETF inverse-vol risk-parity | 57 | 2.02 | 0.99 | -17% | 1.00 | 0.43 | 1.08 | REJECTED (low-vol beta) |
| EQUITY mega-cap momentum | 48 | 3.53 | 1.65 | -15% | 1.98 | 1.13 | 1.73 | MIXED (beta>1 + survivorship) |
| CRYPTO momentum (top-2, 6m) | 54 | 1.51 | 0.48 | -47% | 0.60 | 0.88 | 0.69 | REJECTED (BTC beta, deep DD) |
| Commodity TSMOM | 48 | 1.69 | 0.67 | -34% | 0.84 | 0.72 | 0.78 | REJECTED |
| FX trend | 48 | 1.42 | 0.42 | -7% | 2.13 | -0.61 | 0.63 | MIXED (alpha real, weak) |
| BOND duration-timing | 48 | 1.08 | 0.10 | -5% | -0.63 | 0.50 | 0.53 | REJECTED (negative alpha) |

## Read
**1 VALIDATED of 8.** ETF cross-asset dual-momentum (H-103) is still the only archetype clearing the
full gate-stack with genuine low-beta significant alpha. Everything else is beta-in-disguise (high
beta + insignificant alpha), too weak, survivorship-biased, or negative. The pattern is consistent
and discriminating: raw PF/Sharpe can look great (sector 2.78/1.37, equity 3.53/1.65) yet **fail
attribution** once regressed on the right benchmark — exactly the KTD-Fin warning (alpha vs beta).

## Implication
Stop hunting more momentum variants on this data — they all collapse to market beta. The honest path
forward is the H-103 forward-paper clock (monthly cron, n→100) + genuinely orthogonal signal sources,
not more re-skins of trend/momentum. money_ready stays [].
