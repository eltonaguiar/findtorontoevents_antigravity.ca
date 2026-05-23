# A7 — Cross-Asset COT → CRYPTO Sizing Overlay

**Date:** 2026-05-17
**Author:** autonomous agent (worktree `agent-a7fd071f97854f1c5`, branch `feat/llm7-keyless-2026-05-17`)
**Goal alignment:** Goal #1 — phenomenal performance across all asset classes on `/audit` (CRYPTO is sub-Tier-2 at PF 1.25 / WR 44.6%; a risk-reducing sizing overlay is a candidate lever).
**Hypothesis source:** `DAILY_IDEAS_OLLAMA.MD` O6 / kimi-k2.5.
**Status:** research / backtest deliverable — **NOT wired into production sizing** (per repo Wire-Up Rule).

---

## 1. Hypothesis

When COMMODITY (and BOND) COT **net-speculator** positioning hits an extreme
rolling percentile (`|z| > 2`), scale CRYPTO position sizing **inversely** — a
variance-risk-premium overlay. Premise: extreme cross-asset speculative
crowding precedes broad risk-asset volatility, so de-risk CRYPTO when the COT
z-score is stretched.

This is a **sizing overlay** orthogonal to CRYPTO directional alpha. It does
**not** change which CRYPTO picks fire — only the position weight of picks
that already fired.

---

## 2. Existing COT tooling (investigated first — not rebuilt)

The repo already has a substantial COT/CFTC stack. None of it was rebuilt; the
overlay reuses `cot_fetcher_socrata.fetch_cot` as its live data source.

| File | Role |
|---|---|
| `tools/cot_fetcher_socrata.py` | **Reused.** Free CFTC Socrata feed fetcher (`publicreporting.cftc.gov/resource/6dca-aqww.json`, Legacy COT). Has `fetch_cot(symbol, weeks, app_token)` returning weekly rows with `noncomm_net_pct_of_oi`, plus a `compute_zscore` helper. SYMBOL_MAP covers GC/CL/HG/ZW/ZC/SI/NG/ZC/ZS/PL/PA. |
| `alpha_engine/cot_positioning.py` | FOREX COT contrarian strategy — fetches CFTC live per forex contract code, computes percentile rank, emits BUY/SELL. Has the publication-lag guard (`COT_PUBLICATION_LAG_DAYS=3`) and per-release dedup ledger. |
| `tools/cftc_cot_fetcher.py`, `tools/cftc_cot_forex_fetcher.py` | Other CFTC fetchers (commodity / forex). |
| `tools/cot_lag_corrector.py` | Corrects look-ahead bias from same-day COT emission. |
| `alpha_engine/commodity_cot_contrarian.py`, `baby_strategies/copper_platinum_cot_momentum.py`, `alpha_engine/forex_cot_reversal.py` | COT-based directional strategies. |
| `alpha_engine/strategies/cot_paper_pilot.py` | The CT=F COT paper pilot (later falsified for over-emission / lag leakage). |
| `tools/cot_step7_*` | Risk-of-ruin / friction-adjusted Monte Carlo on COT strategies. |
| `audit_dashboard/data/cot_*.json`, `alpha_engine/data/cot_*.json` | **Signal snapshots / pilot status only — NOT a backtestable positioning time-series.** |

**Key finding on data availability:** all COT tooling fetches from the CFTC
Socrata feed **live**. The repo does **not** persist a historical
**net-speculator positioning time-series**. The stored `cot_*.json` files are
signal snapshots (`cot_signals.json`), paper-pilot status, BTC long/short
account ratios (`cot_btc_latest.json` — Binance retail data, not CFTC COT), and
Monte-Carlo outputs. None is a multi-week commodity/bond net-spec series usable
for a rolling z-score backtest.

The A3 harness (`tools/vol_scalar_backtest.py`) was reused as the cohort-replay
pattern: `PositionSizer.__new__` bypass, per-trade Sharpe = mean/std, equity-curve
MDD, NOCAP-vs-CAP two-arm table.

---

## 3. Overlay design (`tools/cot_crypto_overlay.py`)

**Data-source interface — `load_cot_series()`** (two-tier, no fabrication):
1. **Offline cache** — `audit_dashboard/data/cot_overlay_series.json` if present
   (deterministic, network-free). Absent by default.
2. **Live fetch** — `cot_fetcher_socrata.fetch_cot` across
   `COMMODITY_COT_SYMBOLS = [GC, CL, HG, ZW, ZC]`, averaging `noncomm_net_pct_of_oi`
   per report date. Only when `--allow-live` is passed. `CFTC_API_TOKEN` optional
   (raises the 1k/hr anonymous cap to 50k/hr).
3. Neither → `available=False` → harness reports **INCONCLUSIVE-NO-DATA**. The
   module never fabricates a series.

**`cot_size_scalar(date, z_lookback, series) -> float`** (public API):
- Computes a rolling z-score (`_rolling_zscore_at`) of the most-recent commodity
  (and bond, if available) net-spec value at or before `date`, vs the prior
  `z_lookback` weekly observations (default 52).
- Takes whichever of commodity / bond `|z|` is more extreme (most cautious read).
- `|z| <= 2` → scalar `1.0` (overlay dormant — orthogonal, no effect).
- `|z| > 2` → de-risk linearly from `1.0` down to `0.3`, reaching the floor at
  `|z| = 4.0`. **Clamped to [0.3, 1.0]** as specified.
- No series / no date → `1.0` (fail-safe: the overlay never amplifies risk).

**Backtest — `run_backtest()`** (cohort-replay, mirrors A3):
- Loads `alpha_engine/data/closed_picks.json`, filters `asset_class == CRYPTO`
  with a numeric `pnl_pct` and a derivable pick date (`created_at` →
  `opened_at` → `entry_time` → `generated_at`).
- Two arms, constant base weight `0.05` so the overlay's effect is isolated:
  - **PLAIN:** `return = base_weight * pnl_pct`
  - **OVERLAY:** `return = base_weight * pnl_pct * cot_size_scalar(pick_date)`
- Per-arm: total return, per-trade Sharpe, equity-curve MDD.
- **ρ orthogonality:** Pearson correlation between the OVERLAY return series and
  the PLAIN CRYPTO directional return series.

**Verdict rule:** `OVERLAY-VIABLE` iff `Sharpe lift >= +0.15` **and** `ρ < 0.3`;
`NOT-VIABLE` otherwise; `INCONCLUSIVE-NO-DATA` if no series or the overlay never
bound.

---

## 4. Backtest result

**Cohort:** 6,884 CRYPTO closed picks, window **2026-02-22 → 2026-04-26**.

**Run 1 — offline (`python tools/cot_crypto_overlay.py`):**
No offline COT series cached → `INCONCLUSIVE-NO-DATA` (data-blocked, harness ready).

**Run 2 — live (`python tools/cot_crypto_overlay.py --allow-live`):**
Live CFTC Socrata fetch succeeded — **80 weekly commodity COT rows**, range
2024-11-05 → 2026-05-12 (BOND: 0 rows — the Legacy-report market-name fragment
returned nothing on this run; overlay degraded to COMMODITY-only as designed).

| metric | PLAIN | OVERLAY | delta |
|---|---|---|---|
| total return % | -5284.14 | -5284.14 | 0.0 |
| Sharpe (per-trade) | -0.3273 | -0.3273 | +0.0 |
| max drawdown % | 100.0 | 100.0 | +0.0 |
| picks de-risked | — | **0 / 6884 (0.0%)** | — |
| avg scalar | — | 1.0 | — |
| **ρ (orthogonality)** | — | **1.0** | — |

**Why the overlay never bound:** the 52-week rolling commodity COT z-score over
the closed-picks window peaked at only **+1.879** (2026-04-01) — never breaching
the `±2` trigger. Cross-checked at shorter lookbacks: 26-week peak +1.583,
13-week peak +1.328. Extreme `|z|>2` readings *do* exist in the broader series
(full-series max `|z|`: 3.07 at 13wk, 3.55 at 26wk, 2.91 at 52wk) but those weeks
fall **outside** the Feb–Apr 2026 closed-picks window.

So the overlay correctly returned scalar `1.0` for every pick → the OVERLAY arm
is identical to PLAIN → ρ = 1.0 trivially (same series), Sharpe lift = 0.

---

## 5. ρ orthogonality number

**ρ = 1.0** — but this is **degenerate, not a real orthogonality measurement**.
Because the overlay never bound (0 picks de-risked), the OVERLAY return series
equals the PLAIN series exactly, forcing ρ = 1.0. A meaningful ρ requires at
least some picks to be scaled. **The orthogonality check is not yet answered.**

---

## 6. Verdict

### `INCONCLUSIVE-NO-DATA`

Not because COT data is unavailable — the live CFTC fetch works and returned 80
clean weekly rows — but because **no CRYPTO closed pick falls in a `|z|>2` COT
window**. The closed-picks cohort (Feb–Apr 2026) overlaps a period of *moderate*
commodity speculative positioning (peak z +1.88), so the overlay is dormant
across the entire cohort and the hypothesis cannot be tested on this data.

This is an honest "harness ready, cohort-blocked" outcome. The overlay module
and backtest are fully functional and verified end-to-end against live data.

### What is needed to reach a real verdict

1. **A closed-picks cohort that overlaps an extreme-COT window.** Either
   (a) wait for CRYPTO picks accumulated during a future `|z|>2` commodity COT
   episode, or (b) extend the closed-picks history backwards to cover a past
   extreme (e.g. the full-series `|z|` peaks at 13/26-week lookbacks).
2. **Persist the COT series for deterministic replay.** Write the live-fetched
   series to the offline key so the backtest is reproducible without network:
   - **Offline key:** `audit_dashboard/data/cot_overlay_series.json`
   - **Shape:** `[{"report_date":"YYYY-MM-DD","net_spec_pct_of_oi": <float>}, ...]`
     or `{"COMMODITY":[...],"BOND":[...]}`
   - **Fetch step:** `python tools/cot_crypto_overlay.py --allow-live`
     (uses `tools/cot_fetcher_socrata.fetch_cot`; set `CFTC_API_TOKEN` for the
     50k/hr tier), then save the returned `COMMODITY` series to the offline key.
3. **Optional sensitivity sweep:** re-run with `--z-lookback 13` and `--z-lookback 26`
   — shorter windows breach `±2` more often and may activate the overlay on a
   cohort the 52-week window leaves dormant.
4. **BOND leg:** the live fetch returned 0 BOND rows. Fix the
   `BOND_COT_MARKET` market-name fragment (currently `"10-YEAR U.S. TREASURY"`)
   against the actual CFTC Legacy `market_and_exchange_names` value, or wire a
   Financial-report fetch, to add the bond crowding signal.

---

## 7. Wiring (NOT done — research deliverable)

Per the repo Wire-Up Rule this is a research/backtest deliverable; no production
wiring is performed. **Future caller, if the verdict ever becomes
`OVERLAY-VIABLE`:** the CRYPTO branch of
`alpha_engine/backtest/position_sizing.py::PositionSizer.volatility_target_size`
would multiply its computed `target_weight` by `cot_size_scalar(pick_date)`,
gated behind an opt-in flag exactly like the A3 `vol_scalar_cap` parameter
(default off → unchanged production behaviour).

## 8. Reproducer

```
python tools/cot_crypto_overlay.py                 # offline (NO-DATA without cache)
python tools/cot_crypto_overlay.py --allow-live     # live CFTC fetch
python tools/cot_crypto_overlay.py --allow-live --json
python tools/cot_crypto_overlay.py --allow-live --z-lookback 26
```

**NFA** — research harness; public CFTC positioning data; no real-money sizing.
