# S0.5 Data Integrity Baseline — 2026-04-19

**Input:** `alpha_engine/data/closed_picks.json` (4,420 rows)
**Tool:** `tools/s05_data_integrity_audit.py`
**Report JSON:** `audit_trail/data/s05_integrity_report.json`
**Spec:** `docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md` §3

## Summary

| # | Check | Status |
|---|---|---|
| 1 | Completeness | FAIL |
| 2 | Outlier detection (±5σ on pnl_pct per symbol) | PASS |
| 3 | Timestamp integrity | PASS |
| 4 | Stationarity (ADF per asset class) | WARN (environment) |
| 5 | Survivorship-bias (MATICUSDT reference) | WARN |
| 6 | Schema consistency (direction vocabulary) | FAIL |
| 7 | Source-system attribution | PASS |
| 8 | Forward-looking bias (pnl realized-delta) | FAIL |

**Critical fails:** `completeness`, `schema_consistency`, `forward_looking_bias`.

---

## 1. Completeness — FAIL

Critical field missing rates (n=4,420):

| Field | Missing | Rate |
|---|---|---|
| symbol | 0 | 0.00% |
| direction | 0 | 0.00% |
| **strategy** | **3,809** | **86.18%** |
| opened_at | 7 | 0.16% |
| closed_at | 0 | 0.00% |
| pnl_pct | 0 | 0.00% |
| status | 0 | 0.00% |

**19** `(symbol, direction, strategy)` combos exceed the 1% threshold. All 19 violations are on the `strategy` field with 100% missing — the same root cause as the overall field miss rate.

**Root cause hypothesis:** `strategy` is written only on a subset of ETL paths (e.g. `quan_engine` emissions via `strategies_agreed`) but not denormalized into `strategy` for most older rows. `strategies_agreed` and `source_system` ARE populated — `strategy` specifically is the missing denormalization.

**Remediation:** ETL patch to derive `strategy` from `strategies_agreed[0]` (or a hash of the set) as a backfill. Rerun this audit after backfill. Do NOT purge rows.

## 2. Outlier detection — PASS

0 of 4,420 `pnl_pct` values flagged at ±5σ per symbol (threshold 3%). Distributions are narrow — consistent with capped stop-loss / take-profit behavior.

## 3. Timestamp integrity — PASS

- Future `opened_at`: 0
- Future `closed_at`: 0
- `closed_at < opened_at`: 0
- Unparseable timestamps: 0
- Non-UTC timestamps: 0
- Duplicate `pick_id`s (the `id` field): 0

Timestamps are naive ISO-8601 — treated as UTC per project convention.

## 4. Stationarity — WARN (environment)

`statsmodels` is not installed in the active Python environment, so ADF cannot run. `scipy` is present (`1.17.1`) but does not ship `adfuller`. The tool logs this as WARN and provides the series-building pipeline — ADF will run as soon as `statsmodels` is available.

**Environment issues:** `statsmodels` missing. `pandas 3.0.2`, `numpy 2.4.4`, `scipy 1.17.1` are present.
**Action:** add `statsmodels` to the environment used by the factory gate runner. Until then, stationarity is unverified.

## 5. Survivorship-bias — WARN

- Total rows tagged `rebrand_artifact` or `status=delisted`: **891**
- MATICUSDT rows: **895**; tagged: **891**; **4 untagged MATICUSDT rows** remain.

Cross-ref: MATIC purge/tagging work in commit `2d11245829` (and recent `8b97852fcd` peer-review actions). 4 stragglers suggest the purge missed a small tail — possibly inserted after the purge run or filtered by a slightly different predicate.

**Remediation:** rerun MATIC tagger against current `closed_picks.json`; verify count hits 895/895. Also: full survivorship check requires a current-universe snapshot — not available in this audit.

## 6. Schema consistency (direction) — FAIL

```
BUY   : 4,207
SELL  :    95
LONG  :    97
SHORT :    21
```

Four distinct raw values, two canonical classes. Matches the prior audit finding flagged in the spec.

**Root cause hypothesis:** different emitters write different vocabularies — `quan_engine` writes BUY/SELL; newer/rapid-fire paths write LONG/SHORT. No ETL normalization step.

**Remediation:** Add `normalize_direction()` at the ingestion boundary (map BUY→LONG, SELL→SHORT); migrate existing rows in place. Critical blocker for any long/short edge analysis.

## 7. Source-system attribution — PASS

`source_system` is non-null on 100.00% of rows (4,420/4,420).

Distribution:
- `quan_engine`: 4,302
- `rapid_fire`: 111
- `multi_asset_copytrader`: 5
- `prediction_market_agents`: 2

Prior audit's "many rows with null source_system" is NOT reproduced on the current snapshot — appears to have been remediated.

## 8. Forward-looking bias — FAIL

- `closed_at < opened_at`: 0 — clean.
- `pnl_pct` recomputed vs `(exit_price - entry_price)/entry_price * direction_sign` with tolerance 0.01%: **4,314 / 4,420 mismatches (97.6%)**.

Looking at the ratio `stored_pnl / recomputed_pct` across all rows: median ≈ 1.16, p25 ≈ 0.85, p75 ≈ 1.32. That is consistent with fees/slippage being folded into stored `pnl_pct` — not a pure scale error. **However** specific outliers exist:

- `id=192` TAOUSDT: stored −0.0376, recomputed −3.61% → ratio ~0.01 (likely a units/scale bug on one row or a batch).
- `id=484` MATICUSDT: stored −0.15, entry==exit → recomputed 0. Fee-only row, OK.

**Two distinct issues:**
1. **(Cosmetic / tolerance)** Stored `pnl_pct` is net-of-cost, raw is gross. Tolerance of 0.01% is too tight for this data. Recommend two-tier: ±0.5% WARN, ±2σ on the ratio-distribution FAIL.
2. **(Real bug)** A minority of rows (TAOUSDT id=192 and similar) have stored `pnl_pct` at 1/100 the realized delta — classic fraction-vs-percent mixing. These silently bias any aggregate backtest.

**Remediation:** patch `check_forward_looking` thresholds; then run again and the remaining FAILs are the real scale-mismatch rows to fix in ETL. Do NOT compute strategy edge off raw `pnl_pct` until this is resolved.

---

## Top 3 data-integrity blockers

1. **`strategy` field 86% null** (completeness). Blocks any per-strategy edge attribution — currently impossible to compute forward-WR/Sharpe by strategy from `closed_picks.json` alone; must join on `strategies_agreed` or rebuild.
2. **Mixed `direction` vocabulary** (schema). Any long/short separation today double-counts or drops rows. Breaks L/S P&L, hedge ratios, and direction-conditioned backtests.
3. **`pnl_pct` scale inconsistency** (forward-looking). A subset of rows stores pnl as fraction (−0.037) while most store percent (−3.7); aggregate means are biased and regime-sensitive.

## Strategies invalidated by these blockers

- **`quan_engine_scalp` per-strategy edge rankings** — rely on `strategy` field which is null for the majority of rows; current concentration penalties in `elite_breakdown` are computed off `source_system` as a proxy.
- **Any long/short market-neutral or hedge strategy** — direction vocabulary fork means L/S bucketing is wrong for 21+97 rows (LONG/SHORT branch).
- **Rapid-fire / multi-asset-copytrader backtests** — small row counts (111, 5) amplify the pnl-scale inconsistency when aggregated.
- **Stationarity-dependent regime strategies** — cannot be validated until `statsmodels` is installed and ADF runs.

## Cross-references

- MATIC purge / tagging: `2d11245829`
- Peer-review actions (MATIC purge, hygiene, V3.1 rerun): `8b97852fcd`
- A-Tier inversion + ETF edge analysis: `28144891db`
- Spec: `docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md` §3
- Mutation / kill protocol: `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`, `docs/MUTATION_THREE_AXIS_PROTOCOL.md`

## Environment issues

- `statsmodels` not installed — ADF stationarity check deferred.
- `pandas 3.0.2`, `numpy 2.4.4`, `scipy 1.17.1` confirmed present.
