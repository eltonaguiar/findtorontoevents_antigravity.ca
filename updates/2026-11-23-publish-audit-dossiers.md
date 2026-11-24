# Publish the 12-class audit dossier set to main

**Date:** 2026-11-23
**Scope:** `docs/audit_review_2026-11-22/**` (publishing only)

## What was missing

The 12-asset-class audit review set (`00_SURFACE_BASELINE.md`, `01_CRYPTO.md` …
`12_SPORTS.md`, `README.md`, `BLOCKERS.md`, `PROOF_METHODOLOGY.md`, `_reviews/*`,
the `_raw/` captures, and `scripts/build_manifest.py`) existed on **14 remote
branches** and in the separate mirror repo
`eltonaguiar/antigravity_review_Nov192026` under `26_ASSET_CLASS_DOSSIERS/`,
but it had **never been on the default branch**.

The literal goal "every audit page has an asset MD" is ill-posed: the audit
surfaces are cross-class dashboards, not per-asset pages. The honest boundary
adopted here is **every asset class the surfaces display has a dossier on main**.

## Source ref chosen, and the evidence

All 14 carrying branches hold the same 52 files, but they resolve to three
distinct tree states:

| Group | Branches (examples) | Tree SHA | Latest subtree commit |
|-------|--------------------|----------|------------------------|
| A (latest) | `m3-cost-triage-2026-11-22`, `block-d-session-record-2026-11-22`, `research/edge-candidates-2026-11-22`, `tally-drift-fix-2026-11-22`, … (10 branches) | `357595e9` | `87a2e0c` 2026-11-22 23:02 UTC |
| B | `push/phase2-round-2026-11-22`, `push/m2-forex-cost-2026-11-22`, `m2-residual/fx-cost-overlap-scheduler` | `c1ec5752` | `b5f21cb` 2026-11-22 12:00 UTC |
| C | `m1-equity-cost-measurement` | `deb6eba2` | `3f76b10` 2026-11-22 22:51 UTC |

The three groups differ in 10 of 52 files (the rest are identical). The
divergence is **linear, not a fork** — `git merge-base --is-ancestor` confirms
`b5f21cb` (B) → `3f76b10` (C) → `87a2e0c` (A), and each step is purely additive
(`3f76b10`: +3/−1 across `02_EQUITY.md`, `03_ETF.md`; `87a2e0c`: +8 across 7
dossiers). Group A is therefore both the **most complete** (superset) and the
**most recent**.

**Copied from:** `origin/m3-cost-triage-2026-11-22` (`87a2e0c`), which holds the
same tree as the other nine Group-A branches. The mirror repo was used only as
corroboration (it has different filenames, so it is not a byte source).

## File count and byte-identity

- **52 files** copied via `git checkout <source> -- docs/audit_review_2026-11-22/`.
- Byte-identity verified per file with `git hash-object` vs
  `git rev-parse <source>:<path>`: **52/52 match, 0 mismatches.**
- `git status --porcelain` shows only paths under `docs/audit_review_2026-11-22/`.

## Quality of what was published (from recon)

These are **published as-is**, not re-reviewed or rewritten:

- **9 of 12** dossiers are genuine reviews with measured numbers and provenance.
- `11_INDEX.md` and `12_SPORTS.md` are **stub-like**.
- `08_MUTUAL_FUND.md` is **thin**.

## Honest caveat: this publishes, it does not validate

The numbers inside are **as of 2026-11-22** and were **not re-measured** in this
block. Copying a record to main does not make its figures fresh or correct; it
makes them findable and intact. Any factual error inside a dossier is the
record's, and was deliberately left untouched.

## Findings (reported, not fixed)

- `tools/verify_citations.py` (a swarm-prompt citation guard, argument = a
  prompt file; not wired to `docs/` or to CI) reports 3 cited artifacts that the
  dossiers reference but that do not exist on `main`:
  `reports/class_metric_reconciliation_20261122.md`,
  `reports/equity_cost_measurement/class_cost_20261122.json`,
  `reports/equity_cost_measurement/equity_cost_20261122.json`.
  All three **do** exist on the source branch — they are part of the same
  unpublished work. They were not copied here (out of scope: `docs/**` only).
- `tests/test_edge_research_tally_consistency.py` passes **25/25** with the
  dossier set present; no dossier states a programme tally, so no exemption was
  needed and none was added.

## AGENTS.md registry decision

**No row added.** The dossier set is documentation: nothing imports, executes,
or reads it at runtime, so it is not a pipeline dependency of the audit-dashboard
graph. The `docs/audit_review_2026-11-22/**` path already appears in the
registry's last-audited table for the doc-lint gate, which is where a consumer,
if one is ever added, would be recorded.

## What remains

- The missing **PREDICTION_MARKET** class dossier (next block).
- The **6 stubs** in `docs/asset_classes/`.
- The **uncommitted `docs/edge_research/00-21`** material.
- The three `reports/` artifacts cited above, still unpublished.
