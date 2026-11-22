# H-008 BOND 2s10s — Continuous-Position Redesign — 2026-05-18

_Generated 2026-11-22T08:33:14+00:00 by `tools/h008_bond_research.py`._

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
- **Sample:** 58423 instrument-day resolved records.

| instrument | records | wins | WR |
|---|---|---|---|
| ZT=F | 6637 | 3151 | 47.5% |
| ZF=F | 6583 | 3170 | 48.1% |
| ZN=F | 6571 | 3182 | 48.4% |
| ZB=F | 6577 | 3173 | 48.2% |
| SHY | 6118 | 2840 | 46.4% |
| IEI | 4997 | 2425 | 48.5% |
| IEF | 6118 | 2987 | 48.8% |
| TLH | 4997 | 2449 | 49.0% |
| TLT | 6118 | 3021 | 49.4% |
| GOVT | 3707 | 1713 | 46.2% |

## In-sample Sharpe (sanity figure ONLY — not the verdict)

Equal-weight daily book annualised Sharpe: **0.029**. This is reported for honesty/context. Per `EDGE_VERDICT_2026-05-18.md` a gaudy in-sample Sharpe is **not** a pass — only the harness walk-forward verdict below counts.

## Harness verdict (THE gate)

- per-window eff (new->old): `+1.10 -0.12 +0.18 -0.04 -0.67 +1.22 +0.41 -0.94 +0.62 +0.07 +0.25 -0.37 +0.62 -0.68 -0.28 -0.80 +0.22 +0.30 -0.15 -0.61 -0.49 -0.34 +0.10 +0.01 -0.62 +1.30 -0.87 -0.05 +0.16 +0.02 +0.29 -0.62 +0.60 +1.04 +0.17 -1.19 +0.70 +0.50 -1.44 -0.07 +0.26 +0.86 +0.33 +0.30 -0.47 -0.15 -0.33 +0.54 +0.84 +0.45 -0.80 -0.54 -0.48 +0.41 -0.13 +0.84 -0.28 -1.42 +0.19 +1.17 -0.10 -0.91 -0.94 +0.49 +0.03 +0.65 -0.48 -0.27 +0.71 -0.29 +0.10 +0.67 +0.02 -0.46 +1.20 +0.86 +0.61 +0.33 +0.24 -0.33 -0.21 -0.51 -0.95 -0.58 -0.55 -0.25 -1.29 +0.39 +0.11 -0.40 +0.52 -0.62 +1.07 -0.04 +0.82 -0.42 -0.14 +0.07 -0.38 -1.15 -0.01 +0.43 +0.33 -0.30 -0.96 +0.78 -1.44 -0.31 -0.37 +0.06 -0.64 -0.92 -0.98 -0.60 -0.34 +1.36 +0.62 +0.80 -0.82 +0.46 +0.11 -0.10 -1.04 -0.60 -0.64 -0.14 -0.67 +0.94 -0.49 -0.71 -0.33 +0.87 +0.38 +1.21 +0.23 -1.17 +0.75 -0.59 -0.74 -0.64 -0.64 +0.44 +0.07 -0.13 +0.31 -0.01 +0.51 +0.44 -0.06 -0.49 -0.07 +0.08 +0.23 -0.04 +0.41 +1.12 +0.30 +0.08 -0.63 +0.21 -0.48 -0.33 +0.92 -0.51 +1.28 +0.15 -0.60 +0.31 -0.66 +0.30 +0.29 -0.25 -0.68 +0.14 -1.32 -1.28 +1.08 -0.07 -1.08 -1.62 +0.67 -0.23 +0.58 -0.54 +0.09 +0.23 -0.67 -0.60 +0.33 +0.57 -0.27 -0.00 -0.19 +0.40 -0.17 +0.41 +0.71 +0.13 +0.55 -0.75 -0.12 -0.47 -0.53 -0.90 +0.25 -0.85 -0.40 +0.10 -1.08 +1.50 +0.74 -0.17 -0.46 +0.29 -0.79 +1.08 +0.47 +0.38 +0.29 +0.41 -0.40 -0.17 +0.24 -1.13 -0.69 +0.28 -0.36 -0.06 -0.59 -0.18 -0.67 +1.11 +0.18 -0.35 -0.38 -0.16 +0.77 +0.19 -0.15 -0.48 +0.85 -0.29 -0.17 -1.17 +0.20 +0.28 -0.84 +0.25 +0.18 +0.55 -0.97 +0.43 +1.13 -0.77 -1.02 -0.99 -0.78 +0.67 +1.32 -0.12 -0.45 n/a +0.05 -0.54 -0.48 +0.34 +0.12 +0.62 +0.34 +0.17 +0.04 -0.82 +0.10 +0.20 -0.14 -0.29 -0.89 -0.14 +0.27 +0.11 -0.72 -0.46 -0.69 -0.13 +0.21 -0.73 -0.12 +0.15 -0.57 -0.20 -0.12 +0.76 +1.20 +0.37 +0.07 -0.65 -0.36 +0.25 -0.31 -0.05 -0.29 +0.61 -0.51 +0.47 +0.05 -0.68 +0.74 +0.10 -0.69 -0.31 +0.78 -0.93 -1.27 +0.30 -0.34 +0.08 +0.40 -0.11 +0.19 +0.40 -0.11 +0.55 +0.04 +0.75 -0.12 -0.68 -0.87 +0.81 +0.46 -0.99 +0.20 +1.10 +0.12 -0.06 -0.48 -0.30 +0.80 +0.30 +0.31 -0.50 -0.04 -0.14 +0.84 -0.18 -0.61 +0.72 -0.10 -0.33 -0.76 -0.47 +0.83 +0.45 -0.02 +0.17 -0.31 -0.91 -0.23 -0.57 -0.41 +0.03 +0.55 -0.99 -0.17 -0.69 +0.39 +1.27 -0.08 +0.75 -0.40 +0.22 -0.53 -0.16 -0.11 -0.13 -0.56 +1.31 +0.18 -0.77 -0.46 -0.11 +0.89 -0.56 +0.21 +0.57 -0.20 -0.01 -0.83 -0.40 +0.24 +0.89 -0.55 -0.70 +0.22 +0.41 -0.52 -0.78 n/a -0.01 -0.10 -0.73 -0.53 -0.59 +0.29 +0.34 -0.16 -0.47 -0.29 -0.58 -0.55 +0.93 -0.07 +1.16 -0.05 -0.04 -0.66 +0.44 -0.72 -0.43 -0.10 +0.21 -1.13 -1.04 +0.57 -0.47 +0.06 -0.43 +0.02 +0.51 -0.45 -0.66 +1.41 -0.06 -0.28 -1.15 -0.61 -0.67 +0.77 -0.12 -0.50 +0.62 -0.08 -0.75 +0.71 -0.99 -0.26 -0.27 +0.48 -1.16 +0.83 -1.42 -1.03 n/a -0.69 -0.06 -0.15 -0.91 +0.34 +0.87 +0.28 -0.66 -0.29 +0.37 -0.37 -0.58 -1.20 -0.04 -0.67 +0.23 +0.44 -0.98 -0.20 +0.34 +0.38 +0.15 -0.22 +0.79 +0.10 +0.46 -0.25 +0.18 +0.87 +0.17 -0.01 +0.28 +0.69 -0.07 -0.12 -0.80 +0.88 -0.12 +0.49 -0.07 -0.85 -1.01 -0.62 +1.06 +0.34 -0.34 -0.94 +0.93 +0.23 +0.40 +0.40 +0.16 -0.65 +0.90 -0.18 -0.46 +0.87 +0.80 -0.33 +0.07 -0.34 -0.13 -0.11 -0.26 -0.13`
- windows scored: 514  (strong 327: +140/-187)
- `is_admissible()`: False
- **REJECTED** — REJECTED — strong in 327 windows but signs split (140+/187-); needs 3 same-sign

- **classification: TESTED — the harness rendered a real eff-stability verdict.** The continuous-position redesign achieved the window density Fork 2 could not.

## Honest conclusion

**H-008 was TESTED and REJECTED.** The continuous-position redesign succeeded at its job — it gave the harness the window density Fork 2 could not, so the harness rendered a *real* eff-stability verdict. The verdict is a fail: the slope-momentum signal does not separate winners from losers with a stable sign across enough 14-day windows. This is a clean kill, not a data-coverage gap — the fifth in the EDGE_VERDICT kill-loop. The economic prior (slope momentum proxies the rate regime) is reasonable, but a sound prior is not an edge. BOND 2s10s does **not** clear the harness; nothing is wired or sized.
