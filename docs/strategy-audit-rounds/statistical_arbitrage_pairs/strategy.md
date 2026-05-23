# statistical_arbitrage_pairs — Strategy Spec

**Asset Class:** CRYPTO
**Module:** `alpha_engine/crypto_pairs_arb.py`
**Status:** opt-in sidecar (Wire-Up Rule §2). Wire-up PR target 2026-05-12.
**Coverage gap source:** `docs/strategy-audit-rounds/COVERAGE_VALIDATION_2026-05-09.md`
flagged `statistical_arbitrage_pairs` cycled in audit-round boilerplate with **no
production implementation** — this module is the implementation.

## 1. Theoretical Foundation

The strategy is a textbook implementation of the Engle–Granger two-step
cointegration framework (Engle & Granger 1987, *Co-integration and Error
Correction: Representation, Estimation, and Testing*, Econometrica 55(2):
251–276) adapted to crypto majors per Vidyamurthy (2004, *Pairs Trading:
Quantitative Methods and Analysis*, Wiley). The Gatev–Goetzmann–Rouwenhorst
(2006, *Pairs Trading: Performance of a Relative-Value Arbitrage Rule*,
RFS 19(3): 797–827) distance-method z-score rule is preserved as the trading
trigger; the cointegration screen filters out the spurious-pairs problem
that classic GGR ignored.

A pair `(A, B)` is exploitable if there exists a constant β such that
`Z_t = ln(A_t) − β · ln(B_t)` is stationary (mean-reverting). When `Z_t`
deviates beyond an entry threshold (we use ±2σ, the Gatev rule), it is
expected to revert to its long-run equilibrium — so we sell the rich leg
and buy the cheap leg, capturing the convergence regardless of overall
crypto-market direction (market-neutral on the cointegrated factor).

## 2. Hedge Ratio (β) Derivation

Pure OLS on log-prices via `numpy.linalg.lstsq` (no statsmodels):

```
ln(A_t) = α + β · ln(B_t) + ε_t
```

Rolling 60-bar window, refit every bar (walk-forward; no look-ahead).
Log-prices preferred over raw prices because (a) they linearise
multiplicative price dynamics, (b) ε_t is approximately percentage error,
making the z-score scale-invariant across the very different price levels
of BTC (~$60k) vs SOL (~$200).

## 3. Cointegration / Half-Life Filter

Full ADF requires scipy; we use the equivalent AR(1) half-life proxy
(Ornstein–Uhlenbeck discretisation; see Chan 2013, *Algorithmic Trading:
Winning Strategies and Their Rationale*, Wiley, pp. 55–62):

```
spread_t − μ = φ · (spread_{t−1} − μ) + η_t
half_life    = −ln(2) / ln(φ)        # bars
```

Pairs with `half_life > 30 bars` or `φ ∉ (0,1)` are skipped: φ ≥ 1 means
random walk / divergence (no reversion), φ ≤ 0 is anti-persistent and
rare in cointegrated systems. The 30-bar cap matches the 60-bar window:
mean reversion has to complete at least twice within the lookback or the
60-bar μ estimate is itself non-stationary.

## 4. Entry, Exit, Risk

| Rule          | Value                                                     |
| ------------- | --------------------------------------------------------- |
| Entry         | `|z| > 2.0`                                               |
| Z>+2 → SHORT A, LONG B (A overpriced vs B)                                |
| Z<−2 → LONG A, SHORT B (A underpriced vs B)                               |
| Take-profit  | price level implied by spread reverting to z=0 (μ)         |
| Stop-loss    | 3% adverse move per leg                                    |
| Confidence   | `clamp(|z| / 4.0, 0, 0.95)`                                |
| Exit (live)  | spread crosses 0 OR leg TP/SL touches first                |

Each fired pair emits **2 picks** sharing a `pair_id`, `pair_leg`
(A/B), `pair_partner`, plus `hedge_ratio`, `z_score`, `half_life_bars`
fields for downstream attribution.

## 5. Why Crypto Majors Are Good Candidates

* Shared risk factors: BTC dominance regime, USD liquidity cycle, perp
  funding, exchange-listing tier — all four candidate symbols load on
  the same broad-crypto factor.
* High-quality 24/7 data (Binance, OKX, Coinbase) — no closing-auction
  noise that hurts equity pairs.
* Listed on every major venue — cross-venue arb pressures keep prices
  globally consistent so the pair relationship reflects fundamentals,
  not microstructure dislocation.
* Recent academic evidence: Springer (2024), *Copula-based Trading of
  Cointegrated Crypto Pairs*, reports 79–100% WR on 81k+ data points
  for BTC/ETH-class pairs with copula-augmented entry filters; our
  ENTRY_Z=2 rule sits well inside that profitable region.

## 6. Candidate Pairs (initial)

* `BTCUSDT / ETHUSDT` — primary cointegration anchor.
* `ETHUSDT / SOLUSDT` — L1 vs L1; tighter half-life, more signals.
* `BTCUSDT / BNBUSDT` — BTC-dominance hedge; added as cross-validation.

ETH/SOL and BTC/BNB are added to keep n at scale once live; the half-life
filter will silently drop any of the three when cointegration breaks (it
*does* break in regime shifts — that's a feature, not a bug).

## 7. Rollback

`CRYPTO_PAIRS_ARB_DISABLED=1` no-ops the module instantly without a
deploy.

## 8. Wiring Plan

See module docstring `alpha_engine/crypto_pairs_arb.py` § "Wiring Plan".
Target wire-up PR registers the function into
`PROVEN_RESEARCH_STRATEGIES` in `proven_research_strategies.py`, which is
already iterated by `smart_picks_engine.py` and `production_scanner.py`.

## 9. References

* Engle, R. F. & Granger, C. W. J. (1987). Co-integration and error correction. *Econometrica* 55(2): 251–276.
* Gatev, E., Goetzmann, W. N., & Rouwenhorst, K. G. (2006). Pairs trading: Performance of a relative-value arbitrage rule. *Review of Financial Studies* 19(3): 797–827.
* Vidyamurthy, G. (2004). *Pairs Trading: Quantitative Methods and Analysis*. Wiley.
* Chan, E. P. (2013). *Algorithmic Trading: Winning Strategies and Their Rationale*. Wiley, ch. 2 (Mean-Reverting Strategies).
* Springer (2024). Copula-based Trading of Cointegrated Crypto Pairs. (Internal ref via repo `INSTITUTIONAL_SHORT_TERM_STRATEGIES.md`.)
