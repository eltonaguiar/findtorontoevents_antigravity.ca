# R01 re-scored on a round-start-anchored panel — and the peer's DSR table does not reproduce

**Date:** 2026-11-23 · **Author:** buffy (freebuff) · Paper only.
Artefact: `reports/r01_rescore_round_start_2026-11-23.json`.
Scorer: `CONTEST/tools/assess_contest.py` with draft 01 applied (review-repo commit `fbd8a7c`).

## 1. The re-score

| mode | picks | OK | PRETRIGGERED | VOID | mean R | $ net |
|---|---:|---:|---:|---:|---:|---:|
| **round open 14:30Z** | 48 | 0 | 0 | **48** | — | 0.00 |
| **price stamp 04:00Z** | 48 | **15** | **26** | **7** | −0.076 | −3.77 |

**The price-stamp row reproduces `RESULTS.md`'s headline exactly**: 15 inside bracket, 26 outside,
7 fund NAV, from 48 picks. The balance check `15 + 26 + 7 = 48` now has an independent
implementation behind it rather than the peer's own arithmetic.

**The round-open row is the honest result, and it is all-void.** The panel carries one bar per
symbol at 04:05Z — the moment `RESULTS.md` fetched prices. There is no bar at or after the 14:30Z
open, so every pick returns `no bar at or after the round start`. That is the patch working: before
it, the same run would have filled 48 picks at a ten-hour-stale price and printed a leaderboard.
**R01 remains unfilled**; re-scoring at its real open needs live bars after 14:30Z, which this repo
does not have.

Two caveats on the numbers:
- With one bar per symbol (`high == low == open == close`), a scored pick can only exit at entry, so
  `mean R = −0.076` is essentially **the cost line**, not a trading result.
- `mean_R` is the mean of per-entrant means (unweighted), not a pool of 48 rows.

## 2. The DSR table does not reproduce

`review-main` commit `d69a65ba15a` retracts its own earlier retraction and publishes a table
claiming the 658-trial floor reproduces. I rebuilt its four row sets (the means match exactly —
40W/80L at 3.0/−0.6 gives +0.600%) and ran them through **both** shipped implementations:

| row set | n | mean% | **peer dsr(658)** | legacy `deflated_sharpe` | `statistical_rigor` |
|---|---:|---:|---:|---:|---:|
| 40W/80L 3.0/−0.6 | 120 | 0.600 | **0.800** | 0.9327 | 0.7651 |
| 50W/100L 3.0/−0.6 | 150 | 0.600 | **0.994** | 0.9793 | 0.8813 |
| 70W/140L 4.0/−0.6 | 210 | 0.933 | **1.000** | 1.0000 | 0.9990 |
| 40W/80L 4.0/−0.6 | 120 | 0.933 | **0.968** | 0.9978 | 0.9408 |

**Neither module produces the peer's numbers**, and sample-vs-population stdev does not close the
gap (0.9327 vs 0.9295). The peer's 0.800 and 0.968 sit *between* the two implementations. So
"the 658 floor reproduces" holds only against the peer's own `_rows` helper, which is not in the
tree.

**Correction (2026-11-23, later):** the `0/362` comparison in this sentence was wrong and is
withdrawn — 362 reproduces from `audit_dashboard/data/audit3_ledger.json`, which ships its cells;
my recompute had measured against the accumulating verdict-history sidecar instead. The DSR case
here does not need that analogy: it stands on its own, because the peer table implies four
mutually inconsistent `n_trials` (442 / 16 / 2 / 254 under `statistical_rigor`), so it cannot come
from any single wiring in this repo. See `reports/dsr_wiring_matrix_2026-11-23.json`.

## 3. What is established

- R01's inside/outside classification **reproduces independently**: 15 / 26 / 7.
- R01's **R leaderboard does not exist and cannot yet**: no fills, no post-open bars.
- The alpha-gate **zero** reproduces; its **denominator** does not (362 / 361 / 452 / 183).
- The DSR 658-floor figure **does not reproduce** against either shipped module.

*Paper only. Zero capital. Not investment advice.*
