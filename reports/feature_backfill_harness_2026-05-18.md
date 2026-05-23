# Feature-Backfill Harness Verdict — 2026-05-18 (Fork 1)

**Research / sidecar only. No production wiring.** This completes Fork 1 of the
strategic fork in `reports/EDGE_VERDICT_2026-05-18.md` — backfill the ledger
with the two features the in-house candidate queue still needed, then put those
candidates through the same walk-forward gate every other score has failed.

## Summary verdict

**No admissible edge surfaced.** All four backfilled candidate fields —
`qlib_vol_ratio`, `qlib_pv_corr30`, `qlib_realized_vol30`, and
`regime_score` — are **REJECTED** by `edge_stability_harness.py`'s gate
(`eff >= 0.30`, same sign, `>= 3 / 5` walk-forward windows). The in-house
candidate sweep is now honestly exhausted.

## What was built

| File | Role |
|------|------|
| `tools/backfill_pick_features.py` | Reads `closed_picks.json`, derives features, writes the **new** sidecar `alpha_engine/data/closed_picks_enriched.json`. Source ledger untouched. |
| `tools/edge_stability_harness_enriched.py` | Runs the canonical harness's gate (imports `_windows`, `_window_eff`, `EFF_MIN`, etc. verbatim) against the enriched sidecar. |
| `tests/test_backfill_pick_features.py` | 8 stdlib tests — symbol resolution, regime classifier, qlib factor bounds. All pass. |

## What was backfilled

Per pick in `closed_picks.json` (8421 picks), the script attaches:

- **qlib Alpha158 factors** (`qlib_vol_ratio`, `qlib_pv_corr30`,
  `qlib_realized_vol30`) — computed by the exact PR #1178 functions
  (`compute_volume_ratio` / `compute_price_volume_corr` / `compute_realized_vol`
  from `alpha_engine/technical_features.py`, with a local stdlib fallback if
  the branch predates #1178). OHLCV is daily, fetched via yfinance, windowed
  **strictly before `entry_date`** — no look-ahead.
- **`regime_at_entry`** + numeric proxy **`regime_score`** (+1 BULL / 0 CHOPPY
  / -1 BEAR) — a transparent 3-state classifier from SMA20-slope + realized
  vol on the same pre-entry window.

### Honesty note on regime

`reports/EDGE_VERDICT_2026-05-18.md` is correct that **no usable regime
timeseries exists in this repo.** `regime_performance_history.json` does not
exist on disk; the only stored regime signal is `extra.fast_regime` on
**3 / 8421** picks. Backfilling regime from a stored timeseries was therefore
impossible. Instead `regime_at_entry` is **recomputed** per pick from OHLCV —
this is a legitimate, look-ahead-free derivation, but it is a recompute, not a
historical regime label, and the report treats it as such.

## Coverage

| Scope | qlib | regime |
|-------|------|--------|
| Whole ledger (8421 picks) | 2265 (26.9%) | 2265 (26.9%) |
| **Harness-scored subset** (resolved WON/LOST + dated, 2156 picks) | **2118 (98.2%)** | **2118 (98.2%)** |

The whole-ledger 26.9% is floor-limited by 6103 picks that carry **no
entry/timestamp at all** — but those picks are also undated, so the harness
cannot window them regardless of features. On the subset the harness actually
scores, coverage is **98.2%** — the candidates are genuinely, fully testable.
This is the key result: the "untestable" status from EDGE_VERDICT is resolved.

OHLCV gaps: 53 picks across 5 recent-listing crypto symbols (APTUSDT, POLUSDT,
SUIUSDT, ZKUSDT, ZROUSDT) had no yfinance daily history in the entry window.
Regime distribution on the scored subset: CHOPPY 1126 / BULL 784 / BEAR 208.

## Harness verdict per candidate

5-window 14-day walk-forward, newest → oldest. Window n's: 976 / 816 / 207 /
145 / 143 resolved picks.

| Candidate | eff per window (new→old) | Strong windows | Verdict |
|-----------|--------------------------|----------------|---------|
| `qlib_vol_ratio`      | -0.35  -0.26  +0.31  -0.37  +0.23 | 3 (1+/2-) | **REJECTED** — sign-split |
| `qlib_pv_corr30`      | -0.79  -0.23  +0.41  -0.58  -0.10 | 3 (1+/2-) | **REJECTED** — sign-split |
| `qlib_realized_vol30` | -0.18  +0.45  +0.22  +0.48  -0.21 | 2 (2+/0-) | **REJECTED** — only 2/5 strong |
| `regime_score`        | +0.58  +0.04  -0.13  -0.29  +0.29 | 1 (1+/0-) | **REJECTED** — only 1/5 strong |

`is_admissible()` returns **False** for all four.

### Reading the numbers

- **`qlib_pv_corr30`** is the textbook trap EDGE_VERDICT warns about: a strong
  newest-window separation (eff -0.79) that **flips sign** (+0.41 in window 2)
  and is unstable everywhere else. In-sample it would look like an edge; the
  walk-forward gate catches it as regime noise — exactly the `method_a_score`
  failure mode.
- **`qlib_vol_ratio`** is strong in 3 windows but the signs split 1+/2-: no
  stable direction.
- **`qlib_realized_vol30`** and **`regime_score`** never even clear `eff>=0.30`
  in enough windows — sub-threshold noise.

## Conclusion (honest)

**Fork 1 surfaced no admissible edge.** The two candidates that EDGE_VERDICT
flagged as "untestable for lack of features" are now testable — coverage on the
harness-scored subset is 98.2% — and they were tested by the unchanged
admissibility gate. They fail it the same way the other 7 pipeline scores fail
it: unstable sign, sub-threshold separation, or a single-window in-sample fluke
that inverts out of sample.

This is the intended outcome of completing the in-house sweep: it converts two
"unknown — not yet tested" candidates into "tested and dead." Per
EDGE_VERDICT's own framing, that result is **near-conclusive** for the existing
ledger — re-testing more features on a ledger that is itself noise was always
low-EV, and this confirms it empirically rather than by assumption.

The standing rule holds: **the existing pick ledger contains no durable
real-money edge.** The remaining live options are Fork 2 (genuinely new signal
sources — order-flow, options skew, alt-data) or Fork 3 (paper-only freeze).
Both are decisions for the operator, not analysis tasks.

## Reproduce

```
python tools/backfill_pick_features.py            # writes the enriched sidecar
python tools/edge_stability_harness_enriched.py    # walk-forward verdict
python -m pytest tests/test_backfill_pick_features.py -q
```

No production file was edited. `closed_picks.json` was read, never written.
