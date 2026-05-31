# VERIFY: FOREX SHORT MC EDGE CLAIM (SL=-0.5% / TP=+0.7%)

**Date:** 2026-05-31
**Claim source:** kilo transcript referencing parallel-MC by Claude
**Claimed:** FOREX SHORT SL=-0.5% / TP=+0.7% → **PF 3.43, WR 38.71%**

## Verdict: **METHODOLOGY_ARTIFACT_CAPPING + DOESNT_REPRODUCE**

The numbers do **not** reproduce against raw closed picks regardless of
methodology, AND no in-repo MC tool actually simulates SL/TP via OHLC replay.

## 1. MC tool inventory

```
tools/monte_carlo_edge_audit.py     (15894 bytes, 2026-05-31)
tools/monte_carlo_equity_inverse.py (6950 bytes)
```

`monte_carlo_edge_audit.py` is a **bootstrap PF/WR CI tool only** — grep for
`OHLC|intrabar|price_path|stop_loss|take_profit` returns 0 matches in the
simulation body. It cannot have produced a "PF 3.43 at SL=-0.5/TP=+0.7"
result because it does not parameterize SL/TP at all. It just resamples
`pnl_pct` from closed trades.

The only FOREX-SHORT-adjacent artifact under
`alpha_engine/data/monte_carlo_results/` is
`mc_forex_rsi2_mean_reversion.json` (n=19, verdict OVERFIT, PF mean 0.41).
No file with PF≈3.43 / WR≈38.7% exists.

## 2. Independent verification (capping = same as winsorization)

Pulled `trading_picks` where `category='FOREX' AND direction='SHORT' AND
closed_at IS NOT NULL`. n=1011 (1015 incl. all statuses).

Status breakdown:
- TP_HIT 451 (avg +0.765%)
- LOST 494 (avg -0.399%)
- EXPIRED 62 (avg +0.067%)
- TIME_EXIT 8 (avg -0.006%)

Applied closed-pnl **capping** to [-0.5%, +0.7%] (this is what an MC
without bar data would do; same fallacy as winsorization that we flagged
this morning per `reference-sl-optimization-needs-pricepath`):

| Filter | n | WR | PF |
|---|---|---|---|
| All closed, cap -0.5/+0.7% | 1011 | 46.39% | **1.087** |
| Excl EXPIRED + pnl=0, cap | 926 | 48.06% | **0.958** |
| Excl EXPIRED + pnl=0, RAW (uncapped) | 926 | 48.06% | 1.750 |

None of these match the claimed **PF 3.43 / WR 38.71%**. The claimed WR
38.71% is *below* the actual win rate (46-48%) — implausible for a tighter
TP that should *raise* WR, not lower it.

## 3. Methodology critique

Even if some other artifact produced PF 3.43, capping closed PnL is a
**known-broken proxy** for SL/TP optimization. Per
`reference-sl-optimization-needs-pricepath`:
- Tightening SL on capped historical pnl makes the result look better
  monotonically (no whipsaw cost modeled)
- Real intrabar replay shows the OPPOSITE direction (tightening SL
  collapses PF due to noise stops, demonstrated 2026-05-31 on the
  CRYPTO winners)

A defensible FOREX SHORT SL/TP audit requires 1m-5m OHLC for each open
position, walking bar-by-bar to detect whichever level hits first. The
repo does not appear to have this datastream for FOREX symbols.

## 4. Recommendation

- **Do not** wire SL=-0.5% / TP=+0.7% into FOREX SHORT production based
  on this claim.
- If the original claimant has a tool that does intrabar replay, they
  should commit it under `tools/monte_carlo_edge_v2_intrabar.py` with
  the OHLC source documented before any verdict is accepted.
- Until then: claim is REFUTED on both reproducibility and methodology.

## Raw outputs

```
total FOREX SHORT n: 1011
raw pnl_pct stats: min=-100.0000 max=79.5557 mean=0.1502
INTERP_A (pnl in percent, cap -0.5/+0.7%): n=1011 WR=46.39% PF=1.087
INTERP_B (pnl as fraction, cap -0.005/+0.007): n=1011 WR=46.39% PF=1.296
non-EXPIRED non-zero n=926
cap -0.5/+0.7 (excl EXPIRED, excl pnl=0): n=926 WR=48.06% PF=0.958
raw uncapped: WR=48.06% PF=1.750
```
