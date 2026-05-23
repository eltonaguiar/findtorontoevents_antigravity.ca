# H-033 EQUITY residualized overnight-return cross-sectional reversal — 2026-05-19

_Generated 2026-05-19T06:32:52+00:00 by `tools/h033_overnight_xs_reversal.py`._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** Fetches free yfinance data, runs the pre-registered signal through `edge_stability_harness` (imported UNMODIFIED), writes this report.

## Pre-registered hypothesis (registry `tier2_2026_05_19` / H-033)

Each trading day D rank a fixed basket of liquid large/mid-cap US equities by their overnight return `open_D/close_{D-1}-1` RESIDUALIZED against the cross-sectional market overnight move (overnight beta from a strictly-past 60-day regression). LONG the bottom-quintile residuals, SHORT the top-quintile; enter at the open of D, exit at the close of D.

**No-look-ahead:** beta uses only D-61..D-1; the overnight return uses `close_{D-1}` and `open_D` both known at the open of D; entry open_D, exit close_D — no future bar read.

## Data

- yfinance daily OHLCV (raw open + close, `auto_adjust=False`), free, no key. Cached to `tools/cache/h033_overnight_cache.json`.
- Fixed basket tickers with usable history: 40.
- Continuous cross-sectional resolved records: **98080**.
- Of which qualifying top/bottom-quintile picks: **39232**.

## Harness verdict (THE gate — harness imported UNMODIFIED)

- per-window eff (new->old): `-0.08 +0.12 -0.04 -0.06 +0.39 -0.24 +0.10 -0.12 -0.09 +0.01 -0.05 +0.02 -0.20 -0.06 +0.18 +0.08 -0.01 -0.03 -0.12 -0.01 -0.05 -0.05 -0.03 -0.01 -0.08 +0.21 -0.09 +0.00 +0.15 -0.15 -0.21 +0.03 -0.18 +0.03 +0.05 +0.10 +0.06 +0.02 -0.21 -0.16 +0.28 +0.03 +0.21 -0.14 +0.15 -0.17 +0.04 +0.02 -0.02 -0.29 -0.12 +0.03 +0.06 +0.08 -0.00 -0.07 -0.12 -0.25 +0.05 -0.01 -0.18 +0.02 +0.06 -0.18 -0.08 -0.13 -0.09 +0.14 +0.05 +0.16 +0.15 +0.17 +0.14 -0.19 -0.16 -0.07 +0.11 +0.12 +0.20 +0.28 -0.15 -0.08 -0.20 +0.06 -0.03 -0.34 -0.06 -0.16 -0.02 +0.29 -0.11 +0.10 -0.01 -0.09 +0.06 +0.24 +0.01 -0.03 +0.08 -0.35 +0.07 -0.24 +0.32 +0.11 +0.11 +0.04 +0.02 -0.06 -0.33 +0.29 +0.02 +0.15 +0.04 -0.03 +0.00 -0.03 +0.08 +0.23 +0.05 -0.18 +0.27 +0.04 +0.29 -0.05 -0.08 -0.14 -0.02 -0.23 +0.03 +0.22 +0.15 -0.05 -0.00 -0.03 -0.08 -0.07 -0.10 +0.04 -0.03 -0.24 -0.04 -0.15 -0.12 +0.03 +0.04 +0.20 -0.03 -0.00 +0.20 +0.10 -0.18 -0.10 +0.14 +0.11 +0.04 -0.24 +0.03 +0.12 -0.06 +0.14 -0.36 +0.17 +0.18 -0.09 +0.05 -0.14 -0.07 -0.12 +0.28 -0.08 -0.01 -0.00 +0.07 -0.05 -0.00 +0.20 -0.22 -0.02 -0.07 +0.07 +0.04 -0.28 -0.04 -0.07 -0.21 -0.00 -0.07 -0.12 +0.12 -0.06 -0.21 -0.31 -0.31 +0.57 -0.05 +0.35 -0.07 -0.17 +0.22 +0.01 +0.02 +0.04 -0.06 -0.10 -0.03 -0.17 -0.05 +0.00 +0.13 -0.10 +0.02 -0.13 +0.27 +0.04 -0.04 -0.11 +0.15 -0.05 -0.01 +0.01 -0.01 +0.14 -0.10 -0.14 -0.14 +0.10 -0.35 -0.08 +0.20 -0.13 -0.12 +0.11 +0.21 -0.01 +0.09 -0.07 +0.05 +0.01 -0.03 +0.19 -0.10 -0.36 -0.02 +0.21 +0.16 +0.09 -0.19 -0.01 +0.04 +0.05 +0.39 -0.03 +0.01 +0.27 -0.07`
- windows scored: 255  (strong: 13)
- sign: `mixed`  same-sign ok: False
- harness `is_admissible()`: False
- harness reason: REJECTED — strong in 13 windows but signs split (5+/8-); needs 3 same-sign

## Edge & cost survival (over the qualifying quintile picks)

- pooled WR: 51.60%
- gross mean per-trade return: 0.000137
- net mean per-trade return (after 30bps): -0.002863
- cost-survival (|gross| > 30bps): 80.0%  (gate >= 60%: PASS)

## VERDICT: **REJECTED**

Clean kill. The residualized overnight-return cross-sectional reversal does not separate winners from losers with a stable sign across enough 14-day windows (or fails the 30bps cost gate). Do not wire or size. Archive as a tested failure.
