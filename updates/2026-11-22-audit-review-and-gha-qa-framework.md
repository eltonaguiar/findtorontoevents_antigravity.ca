# 2026-11-22 - Audit-surface review, 12 asset-class dossiers, GHA QA framework

Program: `plans/2026-11-22-audit-review-and-gha-qa-program.md`.

## What was broken / missing

- The three audit surfaces (`/audit`, `/audit2`, `/audit3`) publish the same class verdicts with
  different populations and no shared glossary, so PF appeared three ways for CRYPTO.
- `/audit/data/audit2_forward.json` was 22 hours stale while `/audit2/audit2_forward.json` was fresh.
- Several payloads referenced by the pages returned 404.
- Verdict labels (`PROMOTED` at n 0, BOND WR 100 pct at n 2, FUTURES PF 1.87 at n 4) outran the data.
- There was no static quality gate over the 375 workflow files: R1-R12 only looks at run history.

## What changed

New, additive only:

- `tools/doc_source_lint.py` + `tools/test_doc_source_lint.py` - enforces the dossier contract
  (8 headings, Provenance, per-section `[SRC]`/`UNMEASURED` coverage, least-survivable answer).
  12 unit tests pass; all 12 dossiers lint clean.
- `tools/gha_quality_framework.py` - Layers A-E: YAML inventory, Q1-Q10 rules, runtime merge,
  scoring, and `--check`/`--dry-run`/`--self-test`/`--baseline`/`--write-baseline`.
  `--self-test` PASS (each rule fires on a bad fixture, silent on a good one).
- `.github/workflows/gha-quality-framework.yml` - dispatch-first, own concurrency group,
  staggered :13 cron commented until the first green dispatch, commits with `[skip ci]`.
- `.github/workflows/audit-review-doc-lint.yml` - read-only lint gate.
- `docs/audit_review_2026-11-22/` - manifest, surface baseline, 12 dossiers, GHA QA design +
  rule catalog, blockers, rejected log.
- `AGENTS.md` path registry updated with the new paths.

## How it was verified

- `python3 -m py_compile tools/gha_quality_framework.py tools/doc_source_lint.py` - OK.
- `python3 tools/gha_quality_framework.py --self-test` - SELF-TEST PASS.
- `python3 tools/gha_quality_framework.py --dry-run` - offline over 375 workflows: 1 parse error,
  aggregate 94.4/100, 103 blocking violations.
- `--check --baseline` exits 0 on the known set; injecting an unpinned third-party action makes it
  exit 1 naming exactly that finding; without a baseline `--check` exits 1.
- `python3 tools/doc_source_lint.py docs/audit_review_2026-11-22/` - 12/12 clean.
- Live smoke: `/audit3/audit3_ledger.json` and `/audit/data/audit3_ledger.json` sha256 both
  `88606e1e...`, `generated_at` identical (delta 0 s), same provenance id `f627a8d579bebe3e`.
- Review-repo PR #4 `git show --stat`: 19 files, all under `26_ASSET_CLASS_DOSSIERS/`.

## Not done (recorded, not hidden)

- AI-drafted dossiers and the mandatory two-model adversarial pass were blocked: only 1 of 14
  providers answered (`--doctor`). See `docs/audit_review_2026-11-22/BLOCKERS.md` B1. No dossier
  claims an AI review it did not receive; provenance footers say `model: none`.
