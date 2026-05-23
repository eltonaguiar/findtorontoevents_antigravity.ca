# Round 3 — Citadel Review of Merged Synthesis (2026-05-12)

Lens: multi-asset / risk-parity / capacity-aware portfolio construction.

## 1. Over-weighted — per-strategy edge claims, no portfolio covariance layer

The merge's prioritization table (lines 81-89) and the "Real-money allocation"
sleeves (lines 191-204) treat each class/strategy as an additive line item
("$5k EQUITY sleeve + $5k BOND sleeve..."). That is single-strategy thinking
dressed as a portfolio. CT=F, EQUITY momo, FOREX SHORT, and crypto curated
all load on the same risk-off / dollar-strength axis — in a 2008/2020-style
shock they correlate to 1 and the "diversified" $25k envelope draws down
like a single 4x-levered macro bet. No covariance matrix, no marginal-risk
contribution, no Kelly-cap by cluster.

## 2. Under-weighted — capacity, market impact, and execution slippage

Nothing in the merge prices the **CT=F 1-contract → N-contract scaling
curve**, the EQUITY top-100 PEAD sleeve's ADV constraint, or the FOREX
SHORT-only book's overnight-roll cost. CT=F open interest is ~150k contracts;
a $25k book is invisible, but the same edge at $2.5M starts moving the
mid. There is also zero discussion of borrow cost / short-availability
for EQUITY market-neutral pair construction (Month-2 plan, line 109).

## 3. Blind spot across all 7 personas — correlation regime shift + cross-sleeve liquidity contagion

Every persona scoped its edge inside one asset class and one regime. None
modeled what happens when the **inter-class correlation matrix re-prices**
mid-trade. The 2026-06-to-2026-11 ramp assumes today's COMMODITY-vs-CRYPTO
ρ ≈ 0.1 persists; in a USD-funding squeeze that ρ jumps to 0.6+ and the
"diversified" sleeve becomes one trade. Compounding this: the live monitor
and the gatekeeper share infrastructure, so a CRYPTO-side incident (exchange
halt, stablecoin de-peg) freezes the EQUITY and COMMODITY emission paths
simultaneously — that is operational correlation the swarm never named.
Add a portfolio-level correlation-regime monitor (rolling 60d cross-class
ρ matrix + breakpoint alarm) before any second sleeve goes live.
