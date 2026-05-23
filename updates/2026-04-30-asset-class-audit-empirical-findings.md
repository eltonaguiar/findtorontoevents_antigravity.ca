# 2026-04-30 — Empirical findings from `tools/asset_class_edge_audit.py`

First production run of the audit script merged in PR #541. Pool: 3,500 closed
rows raw, **3,150 after `COMMODITY_BLACKLIST` filter** (350 dropped). Filter
mirrors PR #535's sub-class kill — those rows can no longer be reproduced by
the live gate. Full dump in `reports/ASSET_CLASS_AUDIT_RUN_2026_04_30.md`.

## Top-line by class (post-blacklist filter)

| Class | n | WR | PF | Sum PnL% |
|---|---:|---:|---:|---:|
| CRYPTO | 1524 | 40.6% | 1.051 | +61.9 |
| FOREX | 778 | 49.7% | 1.347 | +11.8 |
| EQUITY | 425 | 50.1% | 1.272 | +188.2 |
| COMMODITY | 315 | 44.8% | 1.161 | +4.9 |
| ETF | 83 | 51.8% | 1.131 | +12.9 |
| BOND | 20 | 50.0% | 1.720 | +3.4 |

EQUITY is the dollar leader. COMMODITY's apparent class-level drag in the
unfiltered view (PF 0.97, -$4) was entirely banned-symbol residue — once
COMMODITY_BLACKLIST is enforced retroactively, the surviving 315 rows print
PF 1.16 and +$4.9. The class is **slightly net-positive after the kill list**,
not net-negative.

## 30-day slumps (regression watch)

| Class | 30d WR | 30d PF | 250d WR | 250d PF |
|---|---:|---:|---:|---:|
| CRYPTO | 33.3% | 0.581 | 42.0% | 1.006 |
| EQUITY | 33.3% | 0.865 | 48.4% | 1.147 |
| ETF | 36.7% | 0.456 | 51.8% | 1.131 |
| FOREX | 43.3% | 1.845 | 53.2% | 2.457 |

CRYPTO recent-30 is the worst short-window damage (-$24 on n=30, WR 33%).
**Action:** hold any HC-floor loosening on CRYPTO/ETF until the 30-row window
recovers. EQUITY's 30-row dip is also notable but the 250-row class PF 1.27
remains the strongest dollar-PnL pocket.

## RETRACTION: `cftc_cot_commercial_signal` is NOT a real pocket

The unfiltered audit showed `cftc_cot_commercial_signal SHORT COMMODITY` as
the smoking-gun pocket: n=24, 66.7% WR, PF 2.99, +30.4%. **This was an
artifact.** Drill-down:
- 27/27 closed rows on now-blacklisted symbols (mostly CT=F cotton, one CL=F
  oil), all banned by PR #535.
- 23/24 trades on a single ticker (CT=F).
- Wins clustered on a single date (2026-04-28) at suspiciously similar
  +5.93% to +6.19% — likely one cotton crash captured 16 times.

After the blacklist filter, **the strategy contributes 0 rows in COMMODITY**
and is not a top-5 pocket in any class. The PR #526 scaffold should remain
default-OFF until either (a) a non-blacklisted COMMODITY symbol set proves
edge, or (b) a fresh forward-test n>=20 lands. **Do not wire to production
based on this dataset.**

Same blacklist contamination found in `cta_cross_asset_tsmom COMMODITY`
(33/33 banned). Its **FOREX** pocket (62/62 clean rows) remains a real signal
— see below.

## Top strategy pockets (post-filter, n>=12, PF>1, +PnL)

| Class | Strategy | Dir | n | WR | PF | Sum PnL | Concentration risk |
|---|---|---|---:|---:|---:|---:|---|
| EQUITY | rs-breakout-scout | LONG | 18 | 77.8% | 6.70 | +46.5 | spot-check pending |
| EQUITY | Breakout Momentum | LONG | 38 | 57.9% | 1.53 | +31.1 | broad |
| EQUITY | Bollinger MR | LONG | 58 | 44.8% | 1.31 | +25.1 | broad |
| EQUITY | quality-minus-junk | LONG | 18 | 61.1% | 1.44 | +8.7 | broad |
| EQUITY | stocks_rsi2_pullback | LONG | 39 | 56.4% | 1.31 | +9.7 | broad |
| CRYPTO | mega_mutation_macd_rsi_m048 | LONG | 17 | 88.2% | 11.5 | +78.9 | **9/15 wins JUP** |
| CRYPTO | atr_percentile_gate | LONG | 22 | 95.5% | 13.5 | +9.3 | **21/22 wins BTC** |
| CRYPTO | st_fear_greed_contrarian | LONG | 17 | 94.1% | 49.0 | +20.1 | diverse (SUI/UNI/LINK) |
| CRYPTO | MeanReversionBB | SHORT | 17 | 64.7% | 3.25 | +22.8 | broad |
| CRYPTO | claude_ml_moderate_mut | LONG | 39 | 59.0% | 2.31 | +31.5 | broad |
| FOREX | cta_cross_asset_tsmom | SHORT | 28 | 64.3% | 4.84 | +3.1 | broad |
| FOREX | non_crypto_consensus | SHORT | 87 | 59.8% | 2.03 | +0.0 | broad |
| FOREX | forex_rsi2_mean_reversion | LONG | 198 | 46.5% | 1.11 | +0.9 | broad |
| COMMODITY | futures_momentum | SHORT | 99 | 41.4% | 1.20 | +5.8 | HG/PL/SI mix |
| COMMODITY | cta_golden_cross_200 | LONG | 25 | 44.0% | 1.21 | +0.0 | broad |
| ETF | intermarket-flow-scout | LONG | 12 | 58.3% | 1.77 | +9.0 | small n |

**Concentration caveats** discovered post-filter:
- `mega_mutation_macd_rsi_m048` LONG: 9 of 15 wins on JUPUSDT (60%). Real edge
  on Jupiter Solana, not class-wide CRYPTO edge.
- `atr_percentile_gate` LONG: 21 of 22 wins on BTCUSDT (95%). Single-symbol
  pocket; do not extrapolate to alts.
- `st_fear_greed_contrarian` LONG: top 3 symbols are 4/3/2 (SUI/UNI/LINK) — a
  more diversified pocket; treat as the strongest credible CRYPTO LONG signal
  in the current cohort.

## Score predictors (rank-tertile cuts, post-filter)

`trust_score` is monotonic on EQUITY/ETF/FOREX/CRYPTO; non-monotonic on
COMMODITY (low > mid).

| Class | low WR | mid WR | high WR |
|---|---:|---:|---:|
| EQUITY | 36.9% | 49.3% | 64.1% |
| ETF | 25.9% | 53.6% | 75.0% |
| FOREX | 42.9% | 50.6% | 55.8% |
| CRYPTO | 29.1% | 38.8% | 53.9% |
| COMMODITY | 48.6% | 38.1% | 47.6% (non-monotonic) |

`strat_fwd_wr` remains the single strongest per-class predictor (EQUITY low
26.2% → high 72.5%; ETF 22.2% → 78.6%; CRYPTO 29.5% → 52.6%; FOREX 39.8% →
59.6%).

`confidence` is **inverted on ETF** (low-conf 77.8% WR vs mid 17.9%, high
60.7%). Best PnL is mid-conf in CRYPTO and FOREX, suggesting calibration
distortion above and below the median. EQUITY shows a "U" shape (low and
high beat mid).

## Active mix vs closed-pocket health

| Class | Active raw | Top active strategy (n) | Active (post-gate) | Closed-pocket status |
|---|---:|---|---:|---|
| CRYPTO | 116 | enhanced_ml_A_xgboost (24) | 19 | NOT in top closed pockets — concentration mismatch |
| EQUITY | 25 | regime_terminal (9) | 2 | NOT in top closed pockets |
| FOREX | 14 | non_crypto_consensus (7) | 5 | matches `non_crypto_consensus` SHORT (87/59.8%/PF 2.03) |
| COMMODITY | 6 | non_crypto_consensus (4), cftc_cot (2) | **0** | gate filters all 6 (all on blacklisted symbols) |
| ETF | 3 | super signal via kimi (2) | 0 | n/a |
| FUTURES | 2 | futures_connors_rsi2 (2) | 0 | n/a |
| SPORTS | 4 | value_bet (4) | 0 | n/a |

**Live-gate enforcement verified:** the 6 raw COMMODITY picks (4 ZC=F/ZS=F/CT=F/ZW=F
from `non_crypto_consensus` + 2 ZS=F/ZW=F from `cftc_cot_commercial_signal`,
all in COMMODITY_BLACKLIST) produce **0** rows in `picks.active`. The gate is
working as designed.

**Upstream waste finding:** both strategies are still emitting candidates on
banned symbols every cycle, only to be rejected downstream. For
`cftc_cot_commercial_signal` this is total — 100% of its closed history is on
banned symbols, and the 2 active-raw emissions are also banned. **The strategy
is functionally dead** until its candidate-symbol universe is updated to the
KEEP set (HG=F, PL=F) or it is removed. Same audit needed on
`non_crypto_consensus` for the COMMODITY branch — its FOREX branch is fine
(63 closed / 59.8% / PF 2.03).

## UEPS / PEAD status (unchanged from raw view)

- `ueps_picks.generated_at`: 2026-04-30T01:25 UTC
- `ueps summary`: 30 long_picks, 0 swing, 0 short
- **Active `long_term_value` rows: 0** — UEPS JSON-to-ledger sync still
  missing.
- Active PEAD-like rows: 0; closed PEAD-like rows: 8
  (`post-earnings-rev-scout`).

## Recommended next moves (revised, highest-EV first)

1. **Retire or rewire `cftc_cot_commercial_signal`** — 100% of closed
   history + both current active-raw emissions are on banned symbols. The
   live gate filters them all so it's safe, but every cycle wastes CPU
   generating candidates that cannot reach the active book. Either (a)
   restrict its candidate universe to `HG=F`/`PL=F` (the KEEP set), or
   (b) remove it from the production scanner. **Verified the live gate IS
   enforcing the blacklist** — earlier draft of this doc raised a false
   alarm on that.
2. **Promote `st_fear_greed_contrarian` LONG CRYPTO** in HC — n=17, WR 94%,
   diverse symbol set (SUI/UNI/LINK). Strongest credible CRYPTO LONG pocket
   without single-symbol concentration.
3. **Promote `rs-breakout-scout`** in EQUITY HC (n=18, WR 77.8%, PF 6.7).
   Spot-check for symbol concentration before flipping.
4. **`futures_momentum` SHORT COMMODITY** is a quietly broad pocket
   (n=99, WR 41%, PF 1.2, +$5.8 across HG/PL/SI). Worth a separate
   per-symbol breakdown to find the carry strategies.
5. **ETF confidence INVERT in HC-gate** (unchanged from previous version of
   this doc — still validated by the post-filter run).
6. **Investigate CRYPTO `enhanced_ml_A_xgboost`** — 24/116 active picks (21%
   of book) but missing from closed pockets.
7. **UEPS active-ledger sync** — JSON exists, ledger empty.
8. **PEAD live cron** — 0 active rows; need cron-during-market-hours fix.

**RETRACTED:** earlier draft recommended wiring `cftc_cot_commercial_signal`
SHORT to production. That pocket was 100% banned-symbol residue and is not a
real pre-blacklist edge.

## Why the audit script needed the blacklist filter

Before this update, the script aggregated closed pockets without enforcing
COMMODITY_BLACKLIST (PR #535). That over-credits trades on now-banned symbols
that **the live gate can no longer reach** — guaranteeing any "edge" found
that way is unreproducible. The fix mirrors the in-tree blacklist (stdlib-only
to keep the script dependency-free) and prints how many rows were dropped, so
operators can see the contamination level.

Out of scope: `kill_list` auto-expiry sweep filter, ETF blacklist (currently
only equities-style), JPY-cross blocks. Add as needed when the next sub-class
kill lands.
