# H-008 BOND 2s10s — Continuous-Position Redesign — 2026-05-18

_Generated 2026-05-18T02:52:02+00:00 by `tools/h008_bond_research.py`._

**Status: OPT-IN RESEARCH SIDECAR. No production wiring.** No caller in `quality_gates.py`, `dashboard_generator.py`, or any pick-generation / scoring path. Reads market data, writes this report — nothing else.

## Why a redesign

Fork 2 (`tools/new_signal_research.py`) left H-008 **UNTESTED**, not failed: it modelled the 2s10s slope-momentum signal as sparse discrete picks (one per `|z|>=1` crossing). The 2s10s slope moves slowly, so those crossings cluster — the harness's 14-day windows could not gather the >= 80 resolved events (>= 15 winners + >= 15 losers) they need and it scored < 3 windows. That is a backtest-*design* limit, not a data limit: FRED DGS2/DGS10 carries 40+ years of daily data.

## The redesign

- **Continuous-position book.** Every trading day the strategy holds a directional position in *each* bond instrument, driven by the slope-momentum signal. No `|z|` threshold, no sparse event filter — every instrument-day is a resolved record, so the record stream is dense and uniform in time and the harness's fixed 14-day windows fill.
- **Cross-sectional breadth.** A Treasury duration ladder (futures + duration-laddered Treasury ETFs) so each 14-day window (~10 trading days) collects ~10 instruments x ~10 days of records — past the `MIN_WINDOW_N=80` / 15-W + 15-L floor.
- **Strict no-look-ahead.** The slope-momentum z for a position dated D is computed from 2s10s slope observations *strictly before* D (yields settle with a one-day lag). The realised return is close(D)->close(D+1).

## Signal

- 2s10s slope = `DGS10 - DGS2` (FRED, daily).
- slope-momentum = 10-day change of the slope.
- `signal_z` = rolling 60-observation z-score of slope-momentum, strictly-past window.
- direction: steepening momentum (z>0) -> SHORT bonds (rising yields / falling prices); flattening (z<0) -> LONG bonds.
- harness score field = `|signal_z|` (conviction magnitude — a real edge makes high-conviction days separate winners from losers).

## Data

- **Yields:** FRED DGS2 / DGS10 (daily, 40+ yr requested from 1980).
- **Prices:** yfinance daily close — Treasury futures + duration ETFs.
- **Sample:** 57117 instrument-day resolved records.

| instrument | records | wins | WR |
|---|---|---|---|
| ZT=F | 6507 | 3087 | 47.4% |
| ZF=F | 6453 | 3112 | 48.2% |
| ZN=F | 6441 | 3123 | 48.5% |
| ZB=F | 6447 | 3116 | 48.3% |
| SHY | 5987 | 2780 | 46.4% |
| IEI | 4866 | 2364 | 48.6% |
| IEF | 5987 | 2924 | 48.8% |
| TLH | 4866 | 2385 | 49.0% |
| TLT | 5987 | 2963 | 49.5% |
| GOVT | 3576 | 1652 | 46.2% |

## In-sample Sharpe (sanity figure ONLY — not the verdict)

Equal-weight daily book annualised Sharpe: **0.04**. This is reported for honesty/context. Per `EDGE_VERDICT_2026-05-18.md` a gaudy in-sample Sharpe is **not** a pass — only the harness walk-forward verdict below counts.

## Harness verdict (THE gate)

- per-window eff (new->old): `-0.77 -0.06 -0.54 -0.49 +0.89 +1.02 -0.62 -0.51 +0.18 -0.13 -0.57 -0.08 +0.60 -0.23 -0.14 -0.00 +0.21 -0.33 -0.48 +1.15 +0.96 -1.24 -0.88 +0.72 +1.40 -0.69 +0.39 +0.20 -0.82 +0.28 +0.26 +0.44 -1.28 +0.23 +0.73 +0.25 +0.42 -0.58 -0.62 -0.09 -0.44 -0.11 +0.68 -0.44 -1.08 +1.06 +0.62 -1.34 -0.79 +0.22 +0.93 -0.28 +0.27 -0.17 -0.21 +0.35 -0.30 -0.47 +0.73 -0.37 -0.47 +0.97 +0.68 +0.43 -0.34 -0.20 -0.13 -0.20 -0.41 -0.18 -1.04 +0.36 -1.04 -0.91 +0.53 -0.26 -0.29 +0.55 +0.36 +1.30 -0.14 +0.74 -0.47 +0.75 +0.68 -0.91 -0.20 -0.85 -0.20 -1.29 -0.55 +0.62 -0.33 -1.70 -0.03 +0.09 +0.17 -0.85 -0.58 -0.93 +0.40 +1.40 +0.80 +0.71 -0.83 -0.17 +0.09 +0.05 -1.00 -1.38 -0.39 -0.31 -0.10 -0.65 -0.05 -0.90 +0.34 -0.26 +0.52 +0.53 -0.49 -0.13 -0.04 +0.37 -0.49 -1.01 -1.13 -0.33 -0.46 -0.05 -0.31 -0.27 -0.18 +1.05 +0.95 -0.17 -0.19 -0.19 +0.44 +0.37 +0.54 +0.48 +0.40 -0.74 -0.51 -1.40 +0.70 -1.01 +0.73 -1.18 +0.91 -0.20 -0.23 +0.29 -0.40 +0.31 +0.02 +0.34 -0.04 -0.31 -0.70 -1.05 +1.16 -0.86 n/a -1.32 -0.93 +0.32 +0.22 +0.06 -0.12 -0.00 +0.04 -0.45 +0.89 -0.50 +0.94 +0.27 -0.66 -0.15 +0.25 -0.17 -0.75 +1.05 -0.26 -0.21 -1.04 +0.12 -0.41 +0.14 -0.25 +0.14 -1.10 -0.71 +0.54 -1.45 +0.06 +0.75 -0.92 -0.06 -0.62 +0.18 +0.41 +0.85 -0.47 +0.56 -0.44 -0.56 +0.39 +0.09 -1.34 +0.18 +0.19 -0.76 -0.16 +0.14 -0.39 +0.33 +1.09 -0.28 -0.73 +0.39 +0.25 +0.38 -1.17 -0.12 -0.07 +0.30 -0.10 -0.67 -0.74 +0.41 -0.04 -0.85 +0.00 +0.70 -0.06 +1.05 +1.01 +0.10 -0.39 -1.44 -0.93 +0.30 +0.61 +0.59 -1.17 -0.06 +0.94 -0.64 -0.57 +0.25 -0.75 -0.07 +0.77 -0.14 -0.06 -0.07 +0.34 -0.31 +0.52 -0.63 -0.44 +0.09 +1.07 -0.54 -0.00 -0.77 +0.02 -0.17 +0.27 -0.68 +0.13 +0.57 -0.39 -0.44 -0.47 +0.88 +0.51 +0.70 -0.08 -0.81 +0.41 n/a -0.25 -1.15 +0.90 -0.21 +0.54 +0.36 -0.34 +0.31 -0.89 +0.14 +0.57 -0.67 +0.36 -0.07 +0.36 +0.78 -0.22 +0.13 -0.70 -0.15 -0.51 +0.25 -0.22 +0.08 +0.19 +0.72 -0.00 +0.17 -1.23 +0.15 -0.18 -0.08 -0.31 -0.50 +0.58 +0.67 -0.31 -0.92 -0.13 +0.26 +0.34 -0.15 -0.36 -0.38 +0.29 +0.36 -0.21 +0.11 -0.16 -0.10 -1.01 -0.11 -0.25 +0.35 +0.39 -0.72 +0.57 -0.67 -0.38 -0.44 -0.50 +0.84 +0.32 -1.00 -0.17 -0.31 -0.20 -0.52 -0.20 +0.46 +0.09 +0.80 -0.58 +0.35 -0.79 +0.63 -0.59 +0.11 +0.62 -0.70 -1.07 -0.14 +0.98 -0.56 +0.59 -0.76 +0.96 +0.10 -0.03 -0.95 -0.55 -0.92 +0.35 +0.96 -0.08 -0.10 +0.81 +0.36 -0.82 -0.16 +0.51 -0.31 -0.26 -0.86 -0.48 -0.12 +0.68 +0.23 -0.12 -1.29 +0.50 -1.25 +0.83 -0.01 +0.98 -0.46 -0.06 +0.03 -0.03 -0.98 -0.87 -0.10 -0.94 +0.17 -1.18 +0.57 +0.68 -0.44 +0.18 -0.07 -0.36 +0.10 -0.27 +0.33 +1.09 -0.73 -0.06 -1.30 -0.60 +0.64 +0.35 -0.60 -0.07 -0.02 -0.55 +0.09 -0.56 -1.09 +0.82 -0.34 -0.59 -0.35 -1.08 +0.68 +0.56 +0.19 -0.35 -0.88 -0.99 +0.47 -0.46 -0.68 +0.12 -0.09 +0.08 -0.54 -0.32 -1.04 -0.95 +1.54 +0.07 -0.81 +0.59 +0.68 -0.43 +0.48 +0.06 +0.62 -0.26 -0.22 +0.84 +1.47 +0.56 +0.77 -0.07 -0.26 -0.10 -0.75 +0.65 -0.00 +0.23 -0.48 -0.76 -0.68 +0.78 n/a -1.03 -0.46 +0.57 -0.30 +0.65 -0.08 -1.54 +0.68 +0.35 +0.10 -1.05 -0.35 +0.91 -0.91 +0.01 -0.41 -1.15 +0.70 +0.14`
- windows scored: 496  (strong 326: +144/-182)
- `is_admissible()`: False
- **REJECTED** — REJECTED — strong in 326 windows but signs split (144+/182-); needs 3 same-sign

- **classification: TESTED — the harness rendered a real eff-stability verdict.** The continuous-position redesign achieved the window density Fork 2 could not.

## Honest conclusion

**H-008 was TESTED and REJECTED.** The continuous-position redesign succeeded at its job — it gave the harness the window density Fork 2 could not, so the harness rendered a *real* eff-stability verdict. The verdict is a fail: the slope-momentum signal does not separate winners from losers with a stable sign across enough 14-day windows. This is a clean kill, not a data-coverage gap — the fifth in the EDGE_VERDICT kill-loop. The economic prior (slope momentum proxies the rate regime) is reasonable, but a sound prior is not an edge. BOND 2s10s does **not** clear the harness; nothing is wired or sized.
