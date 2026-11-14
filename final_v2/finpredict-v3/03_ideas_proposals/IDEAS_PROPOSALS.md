# Ideas & Proposals to Achieve Profitability (final_v2)

Concrete, actionable proposals from the closing review. Each is tagged by asset class,
effort, and the gate it unlocks.

## Proposal 1 — Build the CRYPTO vol-targeted trend as the flagship strategy
- **Method:** 50d/200d SMA time-series momentum, long-only/flat, 20% vol target,
  0.1% cost/side, equal-weight 10 assets (ITERATION-005).
- **Evidence:** net Sharpe 2.13, t=5.56, CI [1.25,3.25], OOS 2.06→2.33, 10/10
  assets positive, maxDD −17.4%.
- **Changes before go-live:** restate vs **buy-and-hold** (it under-returns B&H in
  bull; its value is risk-adjusted/drawdown); add a survivorship-adjusted universe;
  add taker-cost stress; add a live execution thread.
- **Effort:** M. **Unlocks:** first real PnL stream.

## Proposal 2 — Add the ETF multi-asset trend (diversifier)
- **Method:** same vol-targeted trend extended to 20–50 liquid ETFs across equity /
  credit / commodity / FX, risk-parity weighted.
- **Why:** multi-asset trend is the most robust documented risk premium; it reduces
  single-class dependence and gives the drawdown control the equity book lacks.
- **Effort:** L (needs ETF price feed + roll handling). **Unlocks:** cross-class.

## Proposal 3 — BTC funding/carry sleeve
- **Method:** fund-rate spread carry, capital-capped at 10–15% of book, DSR 1.0.
- **Caveat:** capital-intensive; only BTC clears cash at 1.5× capital (real ~3.7–4.8%).
- **Effort:** S–M. **Unlocks:** low-vol income sleeve.

## Proposal 4 — Fix price-freshness FIRST (prerequisite)
- Wire `alpha_engine/universal_price_enricher.py` (Binance + yfinance) into the
  dashboard build so every class's `current_price` is live; label `UNQUOTED` (never
  fabricated 0%) when unquoted; purge/quarantine FROZEN_CLOSED_PHANTOM rows.
- **Why:** no PnL, trend, or funding claim is trustworthy until prices are real.
- **Effort:** M. **Unlocks:** all measurement.

## Proposal 5 — Enforce the horizon-harness release gate
- A strategy may be shipped as "profitable" only after the harness passes
  (n≥60; 95% CI excludes 50% on the profitable side; PF>1.05; win-majority ≥66% of
  windows; multiple-testing-adjusted; capital-adjusted).
- Ship the harness as a CI gate (exit code 1 on any claim failing it).
- **Effort:** S (harness already exists: `pi_horizon_validation.py`).

## Proposal 6 — Adopt the unified data contract (carry from v2)
- quote status `LIVE/LAST_CLOSE/STALE/UNQUOTED/PLACEHOLDER`; `pnl_pct=null` when
  unquoted; dedup key `(symbol,strategy,direction,entry_time,entry_price)`; single
  terminal population for `summary_picks`; `class_canonical`/`class_raw`/
  `class_mismatch`.
- **Effort:** M. **Unlocks:** trustworthy cross-class aggregation.

## Proposal 7 — Re-test VWAP MR correctly (optional)
- The 3.76 claim is rejected, but regime-filtered mean-reversion may still hold
  value. Re-run with correct annualization, a real PBO gate (CSCV), and intrabar
  stops; only adopt if it then passes the harness.

## Priority order
1. P4 (price freshness) → 2. P1 (crypto trend) → 3. P5 (harness gate) →
   4. P3 (funding sleeve) → 5. P2 (ETF trend) → 6. P6 (data contract) → 7. P7 (VWAP re-test).
