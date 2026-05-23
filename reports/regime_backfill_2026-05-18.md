# Regime Backfill — closed_picks.json — 2026-05-18

Backfill of a look-ahead-free `regime` label onto the closed-pick ledger so the
edge-stability harness's regime-conditional path (`evaluate_by_regime`,
`is_admissible(..., regime=True)`) activates. ROADMAP_TO_EDGE Phase 1.

## Premise correction

The task brief said "~3 of ~6000 rows tagged → DATA_GAP". That was stale.
Actual state at start (`alpha_engine/data/closed_picks.json`, 8422 picks):

- **3381** picks already carried a `regime` label (the regime_terminal HMM
  6-label scheme: `Accumulation`, `Crash`, `Chop/Neutral`, `Strong Bear`,
  `Mild Bull`, `Mild Bear`). 5041 were untagged.
- The harness did **not** return DATA_GAP — it returned `REJECTED` with 6
  regimes. The real defect was **resolve-date coverage**: `_windows()` keys on
  `resolved_at`/`exit_date`/`timestamp`, and only 721 of the 3381 tagged picks
  carried one of those, so 2660 tagged picks were silently dropped before
  windowing. Most per-regime cohorts had empty `effs`.

The backfill is still worthwhile: it brings the 5041 untagged picks (1598 of
which carry a resolve-date) into the cohorts and unifies the label vocabulary
to one consistent, reproducible, look-ahead-free scheme.

## Ledger

- **File:** `alpha_engine/data/closed_picks.json` (top-level JSON list, 8422 picks)
- **Backup:** `alpha_engine/data/closed_picks.json.bak` (pre-backfill copy)
- **Date span:** 2026-02-22 .. 2026-05-18
- Date fields present: `entry_date` (2274), `timestamp` (2270), `closed_at`
  (6887), `resolved_at` (1675), `exit_date` (783). 6147 picks have neither
  `entry_date` nor `timestamp`; for those `closed_at` is the only date and
  `hold_days` is absent.

## Classifier (look-ahead-free)

BTC daily OHLC fetched free via the project failover chain — Binance
`api.binance.com` klines `BTCUSDT 1d` succeeded on the first mirror (CoinGecko
range endpoint was the configured fallback). 169 daily candles cached to
`tools/_btc_daily_regime_cache.json`, span 2025-12-01 .. 2026-05-18 — giving
50+ days of SMA warmup before the earliest pick.

For a pick, the **entry date** is resolved by priority
`entry_date → timestamp → closed_at → exit_date → resolved_at`, then the regime
for that date `D` is computed from **BTC daily closes strictly before `D`**:

- `SMA_now` = 50-day SMA of closes < D
- `SMA_prev` = 50-day SMA ending 10 trading days earlier
- `slope` = (SMA_now − SMA_prev) / SMA_prev
- `above` = last close (D−1) ≥ SMA_now
- Label (mapped onto the existing HMM vocabulary so all cohorts share one
  label set):
  - `Mild Bull`   — slope > +1% over 10d **and** price ≥ SMA
  - `Strong Bear` — slope < −1% over 10d **and** price < SMA
  - `Chop/Neutral`— otherwise (mixed / flat)

Look-ahead-free: the regime for date `D` uses only BTC data strictly before `D`.
Every pick also gets `regime_basis = "btc_50d_sma_slope_lookahead_free"`.

All 8422 picks resolved a usable date and got a label (0 skipped — every pick
has at least a `closed_at`, and all dates fall after the 50d warmup window).

## Regime distribution (all 8422 picks)

| Regime        | n    |
|---------------|------|
| Mild Bull     | 4069 |
| Chop/Neutral  | 2853 |
| Strong Bear   | 1500 |

## Harness re-run (`--regime --all`)

Before: cohorts mostly showed empty `effs` (only 721 windowable tagged picks,
6 fragmented HMM labels). After: 3 regimes, every cohort n >> MIN_WINDOW_N (80),
real per-window `eff` values render. The regime-conditional path is **active** —
no longer a no-op DATA_GAP gate.

Per-regime n / windows (CRYPTO + all classes; harness does not filter by class,
the ledger is 6884/8422 CRYPTO so the verdict is CRYPTO-dominated):

| Regime        | n    | windows scored | windows strong |
|---------------|------|----------------|----------------|
| Mild Bull     | 4069 | 2              | up to 2        |
| Chop/Neutral  | 2853 | 2              | 0–1            |
| Strong Bear   | 1500 | 1              | 0–1            |

windows_scored caps at 2–3 per cohort because only ~2300 picks carry a
resolve-date (`_windows()` keys on resolve-date, not entry-date). That is a
ledger resolve-date-coverage limit, independent of the regime backfill.

**Verdict: `REJECTED` for every score field** — no score is regime-admissible.
This is a real result, not DATA_GAP. Notable per-field signal:

- `confidence` flips sign across regimes: −0.48/−0.47 in Mild Bull vs +0.62 in
  Strong Bear — a regime-dependent inversion, exactly the trap the harness
  exists to catch.
- `risk_reward` is consistently negative (−1.15/−0.42 Mild Bull, −0.13/−0.53
  Chop, −0.37 Strong Bear) but never reaches MIN_STABLE_WINDOWS (3) same-sign
  strong windows *within a single regime*.
- `method_a_score` shows +1.23 in one Mild Bull window then −0.00 — unstable.

No score clears regime-conditional admissibility. Consistent with the standing
no-edge verdict (`project_edge_verdict_2026_05_18`).

## Files written / modified

- **Modified:** `alpha_engine/data/closed_picks.json` — added `regime` +
  `regime_basis` to all 8422 picks; no outcome/pnl/status field altered.
- **Created:** `alpha_engine/data/closed_picks.json.bak` — pre-backfill backup.
- **Created:** `tools/_btc_daily_regime_cache.json` — BTC daily OHLC cache.
- **Created:** `reports/regime_backfill_2026-05-18.md` — this report.

`tools/edge_stability_harness.py` was **not** modified.
