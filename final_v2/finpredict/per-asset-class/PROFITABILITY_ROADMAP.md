# Profitability roadmap — per asset class (last-chance synthesis)

For each asset class: the **documented risk premium** that actually has evidence, the **realistic Sharpe**, what is **blocking** it in this system, and the **concrete path** to harvest it. Honest principle throughout: target the premia that survive cost + OOS + benchmark-relative testing, not the overfit signal zoo.

---

## CRYPTO

- **Real premia:** time-series momentum (trend) — the strongest evidence here (my ITERATION-004/005 + quant-audit's independent run). Also short-term reversal (weak) and funding-rate carry (real but capacity-limited, ~4.8% vs 4.5% cash per v2).
- **Realistic Sharpe:** 0.5 (bear-inclusive) to 2.1 (bull-flattered); drawdown −17% to −27%.
- **Blocking:** frozen prices, PnL-unit bug, zero-entry rows, single-source concentration (94–98% one source), 683-strategy overfitting.
- **Path:** (1) fix quote-provenance + PnL units; (2) run **one** diversified vol-targeted trend sleeve (50d+200d blend, 20% vol target, 0.1% cost) across 20–40 liquid pairs; (3) **measure excess-of-benchmark** (paired bootstrap vs equal-weight B&H), not absolute Sharpe; (4) pre-register a forward run on a bear-inclusive window. Expect: drawdown-controlled positive expectancy, NOT raw-alpha.

## EQUITY / ETF

- **Real premia:** cross-sectional momentum (12-1), value (HML), quality, low-volatility — decades of peer-reviewed support.
- **Realistic Sharpe:** ~0.4–0.8 for a diversified factor portfolio, net of costs.
- **Blocking:** v2's ETF cross-sectional momentum test failed (Sharpe 0.98 vs 1.18 benchmark; SPA p=0.488); EQUITY headline is n=8 (meaningless); "last close" marks not labeled.
- **Path:** replace single-name scouts with a **broad diversified factor portfolio** (momentum + value + quality + low-vol, equal-risk-weight across 50+ names), rebalanced monthly, cost-adjusted; test **risk-matched vs the benchmark**, not raw. deepAI's "walk-forward Variant C PF 1.26, p<0.0013" is a lead to reproduce independently.

## FOREX

- **Real premia:** carry (documented, real but low Sharpe ~0.5) and time-series momentum.
- **Realistic Sharpe:** ~0.3–0.6.
- **Blocking:** 11 frozen phantoms, `stock_forex_prices.json` 217d stale, consensus threshold=1 (single-source), FOREX hard-disabled (PR#6 has 0 call sites).
- **Path:** build a **carry basket** (long high-yield, short low-yield, equal-risk) + a trend overlay; fix the price feed and phantom resolver first. Expect low, capacity-limited return — a diversifier, not a headline edge.

## FUTURES

- **Real premia:** time-series momentum (the canonical managed-futures CTA strategy).
- **Realistic Sharpe:** ~0.5–1.0.
- **Blocking:** 0 closed ever; date-only timestamps; class in `BLOCKED_ASSET_CLASSES`; no real feed (commodity generator uses crypto proxies).
- **Path:** unblock only with a **real futures feed**; run CTA trend across liquid futures (ES, NQ, CL, GC, ZN), vol-targeted. Do NOT unblock without the feed (vetoed).

## BOND

- **Real premia:** duration/trend + carry.
- **Realistic Sharpe:** ~0.3–0.6.
- **Blocking:** n=1 policy-clean; vacuous PASS (0 picks → green); price backfill absent.
- **Path:** backfill real yfinance/FRED marks (never `current=entry`); run a **rate-trend/duration-rotation** sleeve; or mark `NOT_BUILT`/`INSUFFICIENT_DATA` until n≥100.

## COMMODITY

- **Real premia:** carry + momentum (documented).
- **Realistic Sharpe:** ~0.3–0.7.
- **Blocking:** 44/44 rows are `=F` futures mislabeled; generator uses crypto proxies (RNDR/ARB/XLM/DOT for silver/oil); blocked.
- **Path:** label `canonical_asset_class=FUTURES`; use a **real GC=F/SI=F/CL=F feed** + staleness guard; harvest commodity carry/momentum, never crypto proxies.

## MUTUAL FUNDS

- **No intraday edge is possible** (monthly NAV, no mark-to-market). **De-advertise** (`NOT_BUILT`) and do not build a live pick class. If ever built: only a monthly tactical-rotation backtest vs a risk-matched benchmark.

---

## Cross-cutting (applies to every class)

1. **Benchmark-relative, not absolute.** Every "edge" claim must be excess-of-benchmark with a paired bootstrap; absolute Sharpe in a bull window is beta, not alpha.
2. **One strategy per class, not 683.** The zoo is the enemy; a single clean, diversified, cost-adjusted, pre-registered risk-premium sleeve per class.
3. **Risk premia are modest and capacity-limited.** Expect Sharpe 0.3–1.0 net across classes; do not chase the PF 10–56 fantasies.
4. **Fix data first.** quote-provenance, PnL units, dedup, phantom/frozen exclusion — no gate can pass on broken data (0/166 money-ready is the direct symptom).
