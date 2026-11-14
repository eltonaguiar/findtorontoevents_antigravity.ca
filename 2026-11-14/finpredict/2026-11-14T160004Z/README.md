# Archive — finpredict audit session (2026-11-14)

Agent subtree: `finpredict`
Archive stamp: `2026-11-14T160004Z`
Source: findtorontoevents.ca/audit live dashboard (`dashboard_data.json` generated 2026-11-14T14:30Z), GitHub Actions API, Binance/Frankfurter live quotes, repo source inspection.

## Deliverable

- `updates/2026-11-14-prediction-system-audit.md` — the full quantitative audit (Actions health, active picks per asset class, frozen data, closed-pick performance, and the multiple-testing/survivorship verdict). This document is the merged result of this session plus peer `finpredict-v3`'s data-hygiene findings (reconciled and cross-referenced below).

## Peer cross-reference (what changed after reading peers)

Two parallel audit agents reached the same verdict and added specifics I adopted and re-verified against the same payload.

**Peer `finpredict-v3`** (`2026-11-14/finpredict-v3/2026-11-14T155500Z/`) — data-hygiene guardian + remediation plan:

| # | Peer v3 finding | My independent confirmation |
|---|---|---|
| 1 | Crypto `current_price` pinned to entry (XRPUSDT, BTCUSDT) | Confirmed (Binance live): BTC 65,839 vs dashboard 66,300; XRP 0.9742 vs 0.9842. |
| 2 | "1.9h ago" = signal age, not price freshness | Confirmed: newest crypto signal 13:54Z; prices not re-quoted at 14:30Z build. |
| 3 | 11 frozen closed FOREX phantoms (exit UNKNOWN, exit==entry, Mar 2026) | Confirmed: EURUSD/USDCHF/USDJPY/AUDUSD/GBPUSD/NZDUSD + SOFI, all pnl 0.0. |
| 4 | Futures `ES=F` "no date" = date-only signal_time | Confirmed: 2,546 date-only seeds (incl. the Mar-19 expired copy-trader batch); active `ES=F` signal_time is `"2026-11-14"` (bare date). |
| 5 | Bond class dead (n=1 closed) | Confirmed: 15 OPEN bond seeds ~25h old, most current_price null. |
| 6 | Survivorship: 7,914/16,126 (49%) pass integrity; 8,888 auto-expired | Confirmed from `summary`. |
| 7 | Metrics not alive (FWD ~48% zero; strong_signals stale/404; kalshi ~7mo stale) | Confirmed; `strong_signals.json` present on disk but 213d stale (peer saw 404 on a phase-2 path). |

## Unique additions from this session (not in peer v3)

- **Frozen "verified strategies" batch:** 127 OPEN picks seeded 2026-11-12 12:15–12:19 (PercentileRankMr, VolumeDivergence_Reversal, DrawdownRecoveryRSI*, Hoffman*, BettingAgainstBeta, VolScaledTsmom, HurstRegimeFilter, ComboVolscaledTight, CTREND, IchimokuCloudBreakout, CCIDivergence…) — **123/127 (96.9%) frozen at pnl 0 with current==entry**.
- **Fabricated flat-3% cohort:** `signal_validation` (117), `macd_rsi_confluence` (138), `meanreversionbb` (111) + 7 more — every "win" is **exactly 3.00% with zero losers** (placeholder P/L, not real).
- **Metric-liveness table:** `history_*` and `profile_crypto_wr` are 0% populated (dead); `forward_wr/forward_trades/strat_fwd_*/sym_track_*` are 88–97% empty/zero.
- **Repo source verification:** every strategy name (kalshi_mtf_consensus, tsmom_volscaled, non_crypto_consensus, etf_*, commodity_*, futures_connors_rsi2, ueps, bond_*, the verified batch) maps to **real code + a real feed**, but the feeds are not reaching the dashboard (stale snapshots / null prices). "Phantom" is data, not code.
- **EQUITY reconciliation:** headline "75% WR / PF 8.86" is n=8 (95% CI ≈ [0.41, 0.93]); the larger samples are 46.1% (n=759) / 47.0% (n=738) — roughly breakeven, not an edge.

**Peer `inspect-wt`** (June-snapshot worktree, transcript 2026-11-14) — additional findings folded into the updates doc (§10): mutual funds are UNBUILT (`mutual_fund_ranker.py` / `/audit/mutual-funds.html` don't exist); spot-flicker 61% + `FORCE_CLOSED_TOXIC` 3,509; CRYPTO z=−7.1 / EQUITY z=+1.39 / ~260 lucky PF>1.5 survivors expected at p=5%; official surfaces disagree (CRYPTO PF 0.29 registry vs 0.95 money-ready); June 14d closed ≈ −1.4%; hyro surface 6.6d stale. External price quotes (Binance/Frankfurter) that `inspect-wt`'s sandbox blocked were **verified in this session**.

## Investment verdict (unchanged, agreed with peer)

Not money-ready. Aggregate closed book negative: WR 41.8%, PF 0.94, equal-weight compounded −99%, Sharpe −1.31 annualized. `money_ready_verdict` is empty for every asset class. This is a multiple-testing/survivorship artifact (126 systems, 365 workflows, 112+ strategies), not a demonstrable edge.

## Reproducibility

All numbers in the updates doc are derived from `/tmp/kilo/audit_data/dashboard_data.json` and the live APIs named inline. Nothing was modified in the live pipeline; this archive is analysis + evidence only.
