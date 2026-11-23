# Dossier citation resolution (Block 53)

## What was broken

Block 48 published the audit-review dossier set to `docs/audit_review_2026-11-22/`
from `origin/m3-cost-triage-2026-11-22`. Its report recorded that the dossiers cite
artefacts that exist on the source branch but not on `main`, and deliberately left
them. A reader of a clean clone of `main` could not follow those citations, so the
dossier set could not be independently audited.

## Measured scope - 14, not 3

The earlier note named three files from one run of `tools/verify_citations.py`. Parsing
every `[SRC: ...]` span, markdown link and backticked path in all 38 markdown files
under the dossier directory at `origin/main` found **14** distinct repository-path
citations that do not resolve on `main` (80 distinct cited paths total, 66 resolved):

| cited path | class of problem |
|---|---|
| `GHACTIONS_LIVE/gha_quality.md` | exists on the source branch only |
| `reports/class_metric_reconciliation_20261122.md` | exists on the source branch only |
| `reports/equity_cost_measurement/class_cost_20261122.json` | exists on the source branch only |
| `reports/equity_cost_measurement/equity_cost_20261122.json` | exists on the source branch only |
| `tools/doc_source_lint.py` | exists on the source branch only |
| `tools/edge_screen.py` | exists on the source branch only |
| `tools/gha_quality_framework.py` | exists on the source branch only |
| `tools/point_in_time_audit.py` | exists on the source branch only |
| `tools/reconcile_class_metrics.py` | exists on the source branch only |
| `reports/class_metric_reconciliation_20261122.json` | on branch, but embeds an absolute local path |
| `audit_dashboard/data/dashboard_data.json` | generated output, gitignored (`.gitignore:222`) |
| `data/pm_market_outcomes.json` | never existed in the tree |
| `reports/forward_observations.json` | cited only as a live-surface 404; committed ledger is `.jsonl` |
| `alpha_agent/validation/sharpe_metrics.py` | typo - the file is `alpha_engine/validation/sharpe_metrics.py` |

The three originally named files were a subset. The rest are tools and reports the
dossiers also lean on (`tools/edge_screen.py` backs `EDGE_SCREEN_RESULT.md`, and so on).

## Decision per file

Published byte-for-byte from `origin/m3-cost-triage-2026-11-22` (each verified with
`git hash-object` against `git rev-parse <branch>:<path>`): `GHACTIONS_LIVE/gha_quality.md`,
`reports/class_metric_reconciliation_20261122.md`, `reports/equity_cost_measurement/class_cost_20261122.json`,
`reports/equity_cost_measurement/equity_cost_20261122.json`, `tools/doc_source_lint.py`,
`tools/edge_screen.py`, `tools/gha_quality_framework.py`, `tools/point_in_time_audit.py`,
`tools/reconcile_class_metrics.py`. None of them contains credentials, connection strings
or absolute personal paths, and `main` already cites several of the cost reports from
`docs/edge_research/`.

Annotated, not published (recorded in `tools/dossier_citation_allowlist.txt`):

- `reports/class_metric_reconciliation_20261122.json` - the blob embeds
  `/home/.../docs/audit_review_2026-11-22/_raw/audit3_audit3_ledger.json`. Regenerate with
  `tools/reconcile_class_metrics.py`; the `.md` sibling is published.
- `audit_dashboard/data/dashboard_data.json` - generated payload, gitignored.
- `data/pm_market_outcomes.json` - never existed; written by `pm_outcome_ingest`.
- `reports/forward_observations.json` - live-surface 404 reference; `reports/forward_observations.jsonl` is the shipped ledger.
- `alpha_agent/validation/sharpe_metrics.py` - citation typo for `alpha_engine/validation/sharpe_metrics.py`, which resolves. The dossier text was not edited to hide it.

## Checker and test

`tools/check_dossier_citations.py` (stdlib only, `subprocess` + `git`): parses markdown
at a ref, extracts repository-path citations, resolves each with `git cat-file -e`, and
exits 1 on any unresolvable citation not in the allowlist. `--ref` (default `origin/main`),
`--docs-dir`, `--allow-missing`. It loads `tools/dossier_citation_allowlist.txt` by default.

`tests/test_check_dossier_citations.py` (6 tests, offline, `tmp_path` git fixtures):
resolvable passes; an unresolvable citation fails; `--allow-missing` exempts; nested
`_reviews/` files are scanned; a bad ref is a usage error; the token filter. RED proof:
against a mutant that treats every citation as resolved, 3 tests fail; restored, 6 pass.

## CI

`.github/workflows/verification-tests.yml` gains the tool, its test, the allowlist and
`docs/audit_review_2026-11-22/**` in both `paths:` lists, and the test file in the pytest
command. The workflow's existing "Expose origin/main ref" step runs
`git fetch --no-tags --depth=1 origin main:refs/remotes/origin/main`, so the checker's
`origin/main` default resolves in the depth-1 checkout; the tests themselves use
`--ref HEAD` inside their own throwaway repos.

## What a reader can now reproduce from a clean clone

The metric reconciliation narrative, the per-class and per-name equity cost measurements,
the edge screen, the point-in-time audit, the GHA quality framework and its measured
output, and the doc-source lint - all cited paths resolve on `main` except the five
documented exceptions above, each of which states why and how to regenerate or that it
never existed.
