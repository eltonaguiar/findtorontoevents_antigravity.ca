# Stop-Loss Optimization Validation — Real Price-Path Backtest

**Date:** 2026-05-31
**Type:** READ-ONLY analysis. No production strategy code modified.
**Goal context:** Goal #1 (phenomenal performance across asset classes on `/audit`) — CRYPTO edge tuning via SL optimization.
**Reproducer:** `python3 tools/rr_backtest_validation.py`
**Data source for picks:** `battleground/data/closed_picks.json` (both target strategies live here; field is `strategy`, not `algorithm`).
**Price data:** Binance 1-minute klines (`api/api1/api2/api3.binance.com` failover). All endpoints reachable from this host (HTTP 200 on binance, kucoin, cryptocompare, coingecko at run time).

## TL;DR Verdict

**The winsorization counterfactual is REFUTED for both strategies.** On real intrabar
price paths, tightening the stop-loss does NOT raise PF toward the winsorized upper
bound — it COLLAPSES PF because tighter stops get whipsawed out before the trade can
work. The winsorization was misleading exactly as suspected: it assumed a tight SL
exits at -cap without first being stopped out on noise and missing the subsequent
recovery into a win.

- `crypto_liquidity_wick_reversal_v1`: **Do NOT tighten.** Baseline PF 1.50 is far better than any tighter SL (best tighter = 0.64 @ 0.8%). Recommended SL: keep current / consider looser.
- `atr_percentile_gate`: **Do NOT tighten below baseline.** Tightening to 0.4-0.5% pushes PF below 1.0. Only LOOSENING toward 0.8% modestly helps (PF 1.28). The winsorized "tighten to 0.4%" recommendation is wrong-signed.

## Method

1. Loaded all closed picks for the two strategies. **Both are 100% BTCUSDT** (43 and 29 picks). Rows carry `symbol, direction, entry_price, entry_time, exit_price, exit_time, pnl_pct, exit_reason, status` — but **NOT** explicit `take_profit` / `stop_loss` fields (contrary to the task brief). TP/SL were inferred (see Limitations).
2. Verified data is REAL: e.g. pick #1 entry 62902.10 @ 2026-02-24T13:00Z; real Binance 1m bar that minute is O=62969 / H=63027 / L=62969 / C=63012 — entry sits in/near the bar. `pnl_pct` equals the signed entry→exit price move exactly (no fee/slippage modeled in stored data).
3. For each pick fetched 1m OHLC from entry_time through exit_time (inclusive of the exit minute).
4. Replayed the path forward. The first of {candidate tighter SL, original take-profit, exit_time} to be touched determines the simulated exit. Direction-aware (BUY: SL below / TP above; SELL: inverse). Within-bar ties broken SL-first (worst case); a TP-first sensitivity run gave **identical** numbers, so the conclusion is tie-break-independent.
5. Candidate SL levels swept: 0.4%, 0.5%, 0.6%, 0.8% from entry. Baseline = stored realized pnl.

## Coverage / Data Quality

| Strategy | n_total | klines fetched | n_no_data | n_api_fail | TP-exit count (for median-TP inference) |
|---|---|---|---|---|---|
| crypto_liquidity_wick_reversal_v1 | 43 | 43 | 0 | 0 | 10 (median TP 0.91%) |
| atr_percentile_gate | 29 | 29 | 0 | 0 | 10 (median TP 0.46%) |

**100% coverage. Zero skips, zero API failures.** Because both strategies are BTCUSDT (the most liquid Binance symbol with the deepest 1m history), the JUPUSDT/WIFUSDT-style data-gap risk from the brief never materialized. Date range: 2026-02-24 → 2026-05-25 (well within Binance 1m retention; data is not stale for these windows).

## Results — crypto_liquidity_wick_reversal_v1

| SL level | n | WR % | PF | avg_win % | avg_loss % |
|---|---|---|---|---|---|
| **BASELINE (stored)** | 43 | **58.1** | **1.498** | +0.787 | -0.730 |
| SL 0.4% | 43 | 11.6 | 0.218 | +0.662 | -0.400 |
| SL 0.5% | 43 | 18.6 | 0.308 | +0.667 | -0.494 |
| SL 0.6% | 43 | 23.3 | 0.375 | +0.719 | -0.581 |
| SL 0.8% | 43 | 37.2 | 0.638 | +0.765 | -0.711 |
| *(winsorized claim @0.5%)* | — | — | *2.47* | — | — |
| *(winsorized claim @0.4%)* | — | — | *2.96* | — | — |

Real PF goes the OPPOSITE direction from the winsorized estimate. At SL 0.4% the win
rate craters from 58% to 12% — the strategy's edge lives in giving BTC room to wiggle
before reverting; a tight stop converts ~46% of trades from wins/time-exits into
forced losses. The winsorized 2.47-2.96 was pure fantasy of the upper bound.

## Results — atr_percentile_gate

| SL level | n | WR % | PF | avg_win % | avg_loss % |
|---|---|---|---|---|---|
| SL 0.4% | 29 | 48.3 | 0.934 | +0.399 | -0.398 |
| SL 0.5% | 29 | 55.2 | 1.068 | +0.413 | -0.476 |
| **BASELINE (stored)** | 29 | **58.6** | **1.105** | +0.419 | -0.537 |
| SL 0.6% | 29 | 58.6 | 1.174 | +0.415 | -0.501 |
| SL 0.8% | 29 | 62.1 | 1.282 | +0.433 | -0.553 |
| *(winsorized claim @0.5%)* | — | — | *1.47* | — | — |
| *(winsorized claim @0.4%)* | — | — | *1.67* | — | — |

Tightening to the winsorized "sweet spots" (0.4-0.5%) pushes PF below or to ~baseline,
not up to 1.47-1.67. The monotonic trend is the reverse of the hypothesis: PF *rises*
as the stop *loosens* (0.4%→0.8% takes PF 0.93→1.28). This is a low-vol scalp on BTC;
sub-0.5% stops sit inside ordinary 1m noise.

## Verdict

### crypto_liquidity_wick_reversal_v1 — REJECT tighter SL
The winsorization was badly misleading. Real-path PF at every candidate tighter level
(0.218–0.638) is well below the 1.498 baseline. **Recommended action: do not tighten.**
If anything, the upward PF trend with looser stops suggests the strategy tolerates /
wants wide stops; a follow-up sweep at 1.0–2.0% SL is the right next experiment, not
tightening. No tighter SL improves PF.

### atr_percentile_gate — REJECT tighter SL; tightening is wrong-signed
Winsorization claimed PF 1.47/1.67 at 0.5%/0.4%; real paths give 1.07/0.93. Tightening
below baseline (~0.5-0.6% effective) destroys the edge. The only direction that helps is
LOOSENING: SL 0.8% → PF 1.28 (WR 62%), the best level tested. **Recommended SL if any:
~0.8% (realized PF 1.28)** — but note this is still sub-Tier-2 (PF<1.5) and n=29 is below
the n>=100 "proven" bar in CLAUDE.md, so this is a tuning hint, not a promotion.

## Why the winsorization lied (mechanism)

Winsorization caps each realized loss at -SL and leaves wins untouched, implicitly
assuming the price went straight to the stop. In reality a tight stop is hit FIRST on
intrabar noise, the trade is closed for a loss, and the subsequent reversal into the
original take-profit (a win in the baseline) never accrues. The path replay captures
exactly these "whipsaw-then-recover" trades that winsorization silently converts from
wins to capped-losses-that-don't-happen. For mean-reversion/wick strategies on a noisy
1m BTC tape this is the dominant effect, which is why both strategies degrade rather
than improve.

## Limitations

- **Inferred TP/SL.** Rows lack `take_profit`/`stop_loss` fields. Original TP price was
  taken as the realized exit for TP-exit picks, and the per-strategy median TP% (0.91%
  wick / 0.46% atr) applied to entry for SL/TIME-exit picks. This is the best available
  inference; if the true production TP differs materially the absolute PF could shift,
  but the *direction* of the effect (tighter SL hurts) is robust and tie-break-independent.
- **No fees/slippage** in stored pnl or simulation — adding them would lower all PFs
  uniformly and does not change the verdict ordering.
- **n is small** (43 / 29) and below the n>=100 clean-trade promotion bar. Treat as a
  hypothesis-refutation, not a sized-up trading decision.
- Within-bar a tighter SL and the TP could both lie inside one 1m bar; we tested both
  SL-first and TP-first ordering and got identical numbers, so this assumption is moot
  at this granularity.
