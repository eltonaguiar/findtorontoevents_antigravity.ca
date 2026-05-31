# Capping vs Intrabar Replay — Two Worked Examples (2026-05-31)

Canonical reference for future sessions: why **winsorization / capping** of closed `pnl_pct` to SL/TP range is an UPWARD-BIASED estimator of post-tightening PF, and why only **intrabar OHLC replay** can validate an SL/TP edge claim.

This document is the consolidation of two refuted Monte-Carlo edge claims surfaced in a Kilo-parallel session on 2026-05-31. It is the second time in one session the same pitfall has been demonstrated (the first being `reference-sl-optimization-needs-pricepath` memory + `reports/rr_backtest_validation_2026-05-31.md`).

## The pitfall in one sentence

> Capping a closed trade's realized `pnl_pct` at `-SL` (for losses) and at `+TP` (for wins) treats the SL/TP as if the price went straight there — it ignores that on a noisy tape the SL is usually hit FIRST, closing the trade for a loss, after which the move into the TP never accrues.

## The math

Let a closed trade have realized return `r` (sign and magnitude both from the data).

**Capping estimator** (the one the bad MC runs used):
- If `r < -SL`: counterfactual return = `-SL` (clip downside to stop).
- If `r > +TP`: counterfactual return = `+TP` (clip upside to take-profit).
- Else: counterfactual return = `r` (no change).

This is monotone in the direction of "tighter SL ⇒ less downside, same upside" — so PF can only go up as SL tightens. That is mathematical: `sum(wins) / sum(|losses|)` where `sum(|losses|)` is non-increasing as SL tightens, and `sum(wins)` is non-decreasing (winners are never truncated until TP also tightens).

**Result:** capping estimator predicts edges that do not exist. It cannot whipsaw, because in its model the price travels in a straight line to its destination.

**Intrabar replay estimator** (the only correct one):
- Pull 1m OHLC for `[entry_ts, exit_ts]` from Binance (or the asset's source).
- Walk forward bar-by-bar; record the first of `{SL_hit, TP_hit, exit_ts_reached}`, direction-aware.
- This trade's counterfactual return = whichever hit first.

Because real candles wick, a tight SL is hit before the TP on a meaningful fraction of intended-winners. Those winners become losses. PF often DROPS as SL tightens, not rises.

## Example 1 — FOREX SHORT @ -0.5% / +0.7% (PR #347)

**Capping claim:** PF 3.43, WR 38.71%.

**Verbatim verification result:**
- Real PF (raw closed `pnl_pct`, no transformation): **1.087**.
- Real WR (sign of `pnl_pct`): **46.39%** (not 38.71%).
- The claimed WR 38.71% is itself an artifact of the capping logic, not the underlying data.

**Methodology of the bad run:** the MC computed `min(pnl_pct, -0.5)` for losses and `max(pnl_pct, +0.7)` for wins. No intrabar fetch.

**What an intrabar replay would do differently:** for any FOREX SHORT with `pnl_pct = +0.4%` and a 0.5% TP target, the cap leaves it at +0.4%. But the candle path may have wicked to -0.5% (hit SL) BEFORE the +0.4% close — meaning intrabar would mark it a -0.5% loss. There is no way to recover that information from `pnl_pct` alone.

## Example 2 — COMMODITY LONG @ -0.5% / +5.7% (PR #343)

**Capping claim:** PF 4.43.

**Verbatim verification result:**
- Real raw PF: **0.685** (strategy is below break-even on the underlying data).
- PF only if you reapply the same capping methodology: **3.56** (still below the 4.43 claim, and only "true" under the same upward-biased estimator).
- **96% concentration in HG=F + PL=F + SI=F** — three correlated industrial-metals contracts. No diversification.
- **4 red flags**: capping methodology, concentration, `cta_replicator` survivorship bias (the strategy backfills only contracts that survived to today), and the +5.7% TP being well outside the strategy's realized win distribution (out-of-sample TP-tuning).

**REFUTED** — closed.

## Acceptance rule for future SL/TP edge claims

Before any PR sizes up or whitelists a strategy on the strength of an SL/TP geometry MC:

1. The MC run MUST fetch intrabar OHLC for each closed trade's `[entry_ts, exit_ts]`.
2. The MC run MUST replay first-touch direction-aware (SL vs TP vs time-exit).
3. The PR body MUST cite the OHLC source (Binance mirror used, or asset-class equivalent), the bar resolution, and the number of trades that had intrabar coverage vs the number that were dropped for missing OHLC.
4. If the MC report only describes `pnl_pct` transformations (capping, winsorization, clipping, "if loss > -SL then -SL"), it is **capping-not-replay** and the claim is auto-flagged for refutation.

## Why this matters

17 candidate fabrications were caught in this session via verbatim+round-trip discipline. The capping-not-replay pitfall is now the dominant failure mode for MC-based SL/TP edge proposals — more common than fabricated PF numbers, fabricated WR numbers, or fabricated line citations. Future agents should recognize the pattern on sight.

## Refs

- Memory: `reference-sl-optimization-needs-pricepath` (proven on `crypto_liquidity_wick_reversal_v1` + `atr_percentile_gate` earlier 2026-05-31)
- Validation tool: `tools/rr_backtest_validation.py`
- First-wave report: `reports/rr_backtest_validation_2026-05-31.md`
- PR #347 (FOREX SHORT refutation)
- PR #343 (COMMODITY LONG refutation)
- Cross-PC broadcast: `logs/cross_pc_protocol/broadcast_drain.jsonl` 2026-05-31T22:43Z (METHODOLOGY_WARNING from claude-opus-4-7-desktop, deprecate `tools/monte_carlo_edge_audit.py` for promotion)
