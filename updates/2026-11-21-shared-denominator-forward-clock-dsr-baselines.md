# Shared population sidecar, forward-clock join, DSR trial baselines

Follow-up to `reports/2026-11-21-audit123-collective-review.md` (PR #1043).

## 1. Every surface quoted a different "closed picks" total

**Broken:** `/audit` hardcoded "n=4,618" (and "1,927 closed picks") with no
scope; `audit3_ledger.coverage` carried `total_closed_picks 16,372`,
`valid_closed_picks 7,942`, `scored_rows 8,769`, and declared
`scored_share_of_valid_pct` **`not_comparable`** because the ratio came out at
110.41%. Any win rate, PF or kill rate on those pages divided by a population
the reader could not identify — five numbers for one concept.

**Changed:**
- `alpha_engine/denominator.py` — `build(dashboard, ledger)` produces the shared
  artifact: `canonical_sha256`, `n_canonical`, `n_total_closed`,
  `exclusion_reasons[]`, plus `n_valid_closed`, `n_unscored`, `complete`,
  `notes`, `population_label`, `canonical_source` and per-input timestamps.
  Precedence is the publisher's own `resolved_closed_picks_net`; the ledger's
  `coverage.denominator` is the named fallback.
- `tools/build_denominator.py` — CLI; writes
  `audit_dashboard/data/denominator.json` and prints `::warning` for every note.
- `/audit` (`audit_dashboard/template.html`): the hardcoded "n=4,618" became
  "historical analysis cohort, n≈4,618", and the live population is fetched
  from `data/denominator.json` next to the section title and in the edge panel.
- `/audit2` (`audit2.html`, `audit2.js`): prints the same population under the
  ledger banner and in the footer.
- `.github/workflows/audit3-ledger.yml` builds the sidecar (with a
  `continue-on-error` so a missing input never reds the ledger job), commits it
  with the ledger, and uploads it to `/audit/data/`.

**Never coerced:** a missing canonical count is `null` + "unknown, not zero".
Two inputs from different runs produce a *note* ("input snapshots differ: …, so
compare surfaces by hash, not by percentage") instead of a ratio of two
different books.

## 2. The forward clock tracked an orphan and mislabelled three counters

**Broken:** `audit2_forward.json` held one hypothesis, `H-119`, `n: 430`,
`pods: []`, while all six registered pods had zero forward rows. The page
rendered `Benchmark leg 343` beside `Forward rows 430` as if both were counts,
`Intrabar first-touch 430` as if 430 intrabar events had occurred (the ledger's
field is `intrabar_first_touch_all: true`), and a "Status" column that no data
file provided.

**Changed:** `tools/audit2_forward_summary.py` now joins `audit2_pods.json`
(pod → hypothesis) and the ledger's `forward_gate`. Per hypothesis it emits
`benchmark_coverage_pct`, `intrabar_all`, `registered_owner_pods`,
`owned_by_pods`, `gate_ready`, `status`, `reasons`, and top-level
`orphan_hypotheses[]` / `pods_without_rows[]`. Legacy keys are preserved.
`audit2` renders **Owner pod**, `343 of 430 (79.8%)`, `all 430`, and a note
naming orphans and pods with zero rows.

**Regenerated sidecar shows:** `H-119` → 430 rows, 79.8% benchmark coverage,
`intrabar_all: true`, `owned_by_pods: false`, status
"orphan — no pod owns this hypothesis"; orphans `H-119` and
`H-2026-11-19-06`; several registered pods still at zero rows.

## 3. DSR baselines for the classes that could not be deflated

**Broken:** the same-day fix made a missing `NB_TRIALS_BY_CLASS` entry a *skip*
(not a pass), which left EQUITY / ETF / BOND / FUTURES permanently unassessable.

**Changed:** `NB_TRIALS_BY_CLASS` gains measured values — EQUITY 19, ETF 12,
BOND 2, FUTURES 3 — the number of distinct strategy cells each class has been
tested on in `pf_registry.json::by_asset_class_strategy_policy_clean_net`, i.e.
the same book the verdict reads. `tools/dsr_trial_baseline_report.py` prints the
map beside the measurement and enforces `2 <= mapped <= cells` (`--strict`
exits 1 otherwise).

**Deliberately unchanged:** COMMODITY 3 / CRYPTO 14 / FOREX 6 predate this
measurement and are lower bounds (the registry now shows 9 / 629 / 18 cells).
Raising them would flip live verdicts, so that needs its own sign-off; the
report tool prints the gap. MUTUAL_FUND has zero tested cells, so it stays
absent and its DSR stays explicitly skipped — nothing to deflate is not a pass.

## Verification

- `python3 -m pytest -q tests/test_denominator_sidecar.py tests/test_audit2_forward_clock.py tests/test_dsr_trial_baselines.py tests/test_dsr_baseline_skip.py tests/test_audit2_page_deploy.py` → **26 passed**
- `node --check audit_dashboard/audit2.js` → ok
- `yaml.safe_load` on `audit-dashboard.yml` + `audit3-ledger.yml` → ok; `json.load` on both regenerated artifacts → ok
- `python3 tools/dsr_trial_baseline_report.py --strict` → rc 0, every measured class `ok`
- `python3 tools/build_denominator.py` → `audit.denominator.v1 -- 8,733 of 14,811 closed picks scored (59.0%) · sha ef2f8f81cff8`
- `python3 tools/audit2_forward_summary.py` → `orphans=['H-119', 'H-2026-11-19-06']`

## Limits

- Nothing here is deployed yet; the hourly `audit3-ledger` run publishes
  `denominator.json` and the rebuilt `audit2_forward.json`.
- `/audit`'s older inline cohort claims (82% WR / PF 11+) are untouched — only
  their population label is now honest.
- The 4,618 cohort is labelled historical; it is not reproducible from the
  current book, which is why it is no longer presented as "the" population.
