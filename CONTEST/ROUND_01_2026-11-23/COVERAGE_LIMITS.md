# COVERAGE LIMITS — what the audit3 ledger actually describes

**Block 57 · 2026-11-23 · label applied at `origin/main` = `ce214306b5caf6e52d231f13930cc99f0b7349d2`**

Source report: [`COVERAGE_BIAS.md`](CONTEST/ROUND_01_2026-11-23/COVERAGE_BIAS.md) (Block 56, verdict BIASED), re-measured here; the only figures that moved are noted in its `## Amendment`.

**Label: `COVERAGE-LIMITED`.**

---

## 1. What each ledger surface actually describes

Every number under `classes[]`, `selection_alpha.by_class`, `selection_alpha.by_slice`,
`selection_alpha.by_strategy`, `selection_alpha.overall`, `selection_alpha.gate`, `segments` and
`cells` is computed over picks that (a) resolved to a determinate outcome and (b) survived the
3,500-row display-universe cap. **It is not a statistic about all closed picks.** Of 14,997 closed
picks, 6,111 have no scoreable outcome, and of the 8,886 that do, 5,386 fall outside the cap; only
3,190 of the 3,500 in the cap also have a price benchmark. A per-class, per-strategy or per-segment
number from this ledger describes that nested remainder, not the closed book.

Affected surfaces, all of them computed on the 3,190-row price-covered subset:

| Surface | Measured row count | Affected |
|---|---|---|
| `classes[]` | 8,886 scored; `alpha_n` sums to 3,190 | yes — per-class aggregates include the price gate |
| `selection_alpha.by_class` | 3,190 | yes |
| `selection_alpha.by_slice` | 3,154 (below 3,190: slices under 20 rows are not emitted) | yes |
| `selection_alpha.by_strategy` | 2,598 across 38 cells (n ≥ 20 only) | yes |
| `selection_alpha.overall` | 3,190 | yes |
| `selection_alpha.gate` | 445 tested, 0 demoted | yes |
| `segments` | 8,880 | yes — display-universe only |
| `cells` | 8,886 | yes — display-universe only |

Not affected in the same way: `coverage.*` (59.25% scoreable) is a statement about the full closed
table; it carries the different limit that 6,111 rows are unscored by outcome.

## 2. Direction of the bias

- **Class skew (measured):** the price-covered set is more balanced than the scoreable population.
  CRYPTO is 78.3% of the 8,886 scoreable rows but 52.7% of the 3,190 covered ones; EQUITY and ETF
  are over-represented. So a cross-class aggregate from `selection_alpha` over-weights non-crypto
  relative to the book, and a CRYPTO verdict is drawn from the class with the lowest price coverage
  (24.2%, `alpha_coverage_ok = false`, alongside FOREX 46.8% and FUTURES 83.3%).
- **Price coverage is clustered by class (measured):** CRYPTO 24.2%, FOREX 46.8%, EQUITY 77.7%,
  FUTURES 83.3%, COMMODITY 88.2%, ETF 92.2%, BOND 100%.
- **Outcome selection among the 6,111 unscoreable rows: `UNMEASURED`.** The exclusion reasons are
  known (auto-expired timeouts with no win/loss, fabricated breakeven fallbacks, cancels, mirror
  duplicates, integrity rejections), and some of them are outcome-determined by construction, but
  the class composition, strategy mix and date distribution of those rows were not shipped, so the
  net direction of that selection on any verdict cannot be stated.
- **Class composition of the excluded rows: now `INSTRUMENTED` (2026-11-24), awaiting its first
  live build.** The generator materialises every dropped row (integrity rejections, mirror
  duplicates, auto-expired) with an `exclude_reason` and a derived `asset_class`, and publishes
  them under `_excluded_cohort_rows` in `dashboard_data.json`; audit3's `coverage.excluded_summary`
  then reports `total`, `by_reason` and `by_class_and_reason` from them. No real count is quoted
  here until that live payload exists. Still genuinely unknown: the **net direction** of the
  selection — whether the retained book is flattered by what was dropped. That needs the
  retained-vs-excluded PnL comparison (`audit_trail.excluded_cohorts.bias_report`), which only the
  live rows can supply.
- **Alpha of the 310 price-missing rows inside the universe: `UNMEASURED`** (no benchmark can be
  computed for them by definition).
- **Date skew (measured):** the universe is recency-filled; 62% of its 3,500 rows closed in
  Oct–Nov 2026, against a closed window starting 2026-02-17. Older picks are under-sampled.

## Machine-readable

```json
{
  "generated": "2026-11-23",
  "source_report": "CONTEST/ROUND_01_2026-11-23/COVERAGE_BIAS.md",
  "coverage": {"covered": 3190, "universe": 3500, "scored_rows": 8886, "total_closed_picks": 14997},
  "rates": {"covered_of_universe": 0.9114, "scored_of_closed": 0.5925, "covered_of_scored": 0.3590, "covered_of_closed": 0.2127},
  "label": "COVERAGE-LIMITED",
  "applies_to": ["classes[]", "selection_alpha.by_class", "selection_alpha.by_slice", "selection_alpha.by_strategy", "selection_alpha.overall", "selection_alpha.gate", "segments", "cells"],
  "class_gate_uncovered": ["CRYPTO", "FOREX", "FUTURES"],
  "unmeasured": [
    "class composition of the 6,111 unscoreable rows: INSTRUMENTED - awaiting first live build after 2026-11-24 (coverage.excluded_summary in dashboard_data.json)",
    "strategy mix of the 6,111 unscoreable rows",
    "date distribution of the 6,111 unscoreable rows",
    "split of invalid_row (5,917) between no-outcome and discarded-outcome branches",
    "net direction of the outcome selection among the 6,111 unscoreable rows",
    "alpha of the 310 price-missing rows inside the display universe",
    "per-row covered-vs-uncovered date split (no per-row covered flag is shipped)"
  ]
}
```

## What would remove the label

The label falls only when the ledger can describe the full closed-pick population instead of a
price-covered remainder of a capped slice. That needs one of two artefacts: a shipped
`resolved_closed_picks_net.json` whose excluded rows keep `exclude_reason` and `asset_class`
(then `audit_trail/excluded_cohorts.summarize_excluded()` can tabulate per-class, per-strategy,
per-date exclusion bias from `origin/main` alone, and the direction in §2 stops being
`UNMEASURED`); or expiry-resolved picks receiving a scored outcome, so that auto-expired timeouts
stop being dropped for having no win/loss. Fixing only price coverage (fresh bars for CRYPTO,
FOREX, FUTURES) would raise `covered_of_universe` but would not remove the label, because the
6,111-row outcome selection is upstream of prices. Until then every verdict drawn from this
ledger is a verdict about 3,190 rows, and must say so.

## Observation log

Append-only record of what was measured on the excluded-cohort path, so nobody
re-derives it. Earlier entries are never edited.

- **2026-11-24T01:29Z — pre-wiring observation.** `coverage.excluded_summary` =
  `total: 0`, `by_class: {}`, all `by_reason` zero, `overlap: false`. Deployed
  payload `repo_sha = 325a7d8f`, no `_excluded_cohort_rows` key.
  `merge-base --is-ancestor 188759ab 325a7d8f` = false. **`total: 0` at this ref
  is indistinguishable from the un-wired default and must not be read as "no
  excluded rows exist"** — the same ledger's `coverage.excluded_cohorts`
  reports **6,025 integrity-excluded + 9,274 auto-expired** rows (overlapping,
  not a partition).
- **Observation method.** `audit_dashboard/data/dashboard_data.json` is
  gitignored ([`.gitignore:222`](.gitignore:222)) and FTP-deployed, so a payload
  refresh never appears as a git commit. Read
  `https://findtorontoevents.ca/audit/data/dashboard_data.json` (or a
  downloaded copy); the tracked observation surfaces are the audit3 ledger
  (`audit_dashboard/data/audit3_ledger.json`) and sibling
  `audit_dashboard/data/*.json` sidecars.
- **One-command check.**
  `python3 tools/check_excluded_summary.py --payload <url-or-path> --ledger <path>`.
  It exits 0 only when the payload carries `_excluded_cohort_rows`, the reported
  total is `>= --expect-min` (default 1), and `by_class` is non-empty; it
  distinguishes an absent key from a zero total instead of conflating them.
- **What flips the label.** A run whose payload has a `repo_sha` descending from
  `188759ab`, carries `_excluded_cohort_rows`, and yields `total > 0` with a
  non-empty real-class `by_class`.
