# 2026-11-23 — Monthly gainers run (H-239/H-240) + 10-year replication (H-242)

## What was asked

Proceed: run the equity monthly top-gainer test now that the 48-observation bar is registered, extend
the 44-name panel so H-201's interval can actually narrow, and port the hub's Graveyard + pre-registration
hash to the audit surface.

## What changed

- **`tools/monthly_top_gainer.py`** (new) — the pre-registered runner for H-239 (CRYPTO) and H-240
  (EQUITY): features frozen to `dollar_vol`+`vol1m` and `dollar_vol`+`volratio`, signals shifted one
  session so nothing uses same-month data, benchmark = universe mean, cost 20/0.98 bp RT with the
  registered stress cases, moving-block bootstrap (block 3 months, 4,000 resamples).
- **`tools/h242_pit_10y.py`** (new) + `plans/2026-11-23-prereg-H-242-pit-10y-extension.md` (registered
  before the run) — the same 44-name universe and rule over the **pre-registered** 10-year window, with
  the 5-year slice re-run as a control that had to reproduce H-236.
- **`reports/hypothesis_registry.json`** — H-239, H-240 verdicts and H-242 added with its result.
- Reports: `reports/monthly_top_gainer_results_2026-11-23.md`, `reports/h242_pit_10y_2026-11-23.md`.

## Results

| hypothesis | bar met? | result |
|---|---|---|
| **H-240 EQUITY monthly** | 68 periods (need 48), breadth 115 | excess **+67.61 bp/mo**, CI **[−30.76, +187.48]** → **REFUTED**; IC 0.0083; cost survival 0.994 |
| **H-239 CRYPTO monthly** | 69 periods, breadth 29 | excess **+41.28 bp/mo**, CI **[−247.81, +361.74]** → **REFUTED**; IC **0.1431**; cost survival 0.923 |
| **H-242 EQUITY 44-name 10y** | control reproduced H-236 exactly | W10 mean **16.345 bp/day**, CI **[7.800, 25.069]**, width 68.1% of W5 → **WIDENS_OR_HOLDS** |

The two findings that matter:

1. **The monthly horizon was never going to save the top-gainer family.** Cost drag falls to 0.6%
   (equity) and 7.7% (crypto) and the excess is still indistinguishable from zero. Crypto's IC of 0.143
   is the largest cross-sectional signal recorded in this sweep and still cannot be expressed as a
   3–4 name book with a positive lower bound.
2. **H-236's REFUTED on 44 names was a short-sample artifact, not universe dependence.** Over ten years
   the broad universe gives CI-LB **+7.800 bp/day**, almost exactly the 10-name book's +7.246 over
   fifteen years. That closes the question H-241 opened: the binding constraint was sample length, and
   it is now fixed. Multiplicity is still binding — the DSR for H-242 is **not** computed, N has risen,
   and nothing here is investable.

## A bug caught in the run

The first crypto pass returned a mean excess of **−19,783 bp/month**, which is arithmetically impossible
for a long-only close-to-close book. Twelve bad Yahoo prints (split-like jumps, stale quotes) were the
cause. The runner now rejects and **counts** name-periods outside (−95%, +500%) — 12 rejected for crypto,
0 for equity — rather than winsorising silently. The guard can only remove bad data, never flip a sign.

## Verification

- `python3 tools/monthly_top_gainer.py` → exit 0, both classes scored above the registered bar.
- `python3 tools/h242_pit_10y.py` → exit 0, `control reproduced=True` (H-236 mean 9.407 / CI-LB −3.147
  recovered exactly), W10 CI-LB +7.800.
- Registry re-validated as JSON; H-239/H-240/H-242 statuses updated from UNTESTED to their verdicts.
- Both tools `py_compile` clean.
- **Not done, deliberately:** the audit2 Graveyard/hash port. It edits a deployed dashboard whose data
  pipeline regenerates `audit_dashboard/data/*`, and doing it half-way is worse than not doing it.
  Recommendation and design are in `reports/investment_hub_portability_2026-11-23.md`.

No capital decision changes: **0 of 10 classes investable**, before and after.
