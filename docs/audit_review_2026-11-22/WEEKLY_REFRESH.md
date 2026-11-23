# Weekly refresh design (proposal, not built)

Goal: a class verdict change becomes a reviewable diff, and a NEW contradiction fails CI instead of
silently updating a page.

## Pipeline (proposed)

1. **Regenerate the frozen payload.** Phase 0 again: `curl` the three surfaces + the payloads,
   `sha256` each, write `_MANIFEST.json` (the script `scripts/build_manifest.py` already does this
   deterministically from `_raw/`).
2. **Regenerate the table.** Rebuild the cross-class verdict table from the ledger's
   `classes[]`, `/audit` `readiness.by_class`, and `money_ready_verdict.classes` - no free text.
3. **Diff against the committed table.** `VERDICT_DIFF.json` = per class per surface
   `{from, to}`. A class moving e.g. `WEAK` to `KILL` is a diff line, not a page refresh.
4. **Fail on a NEW contradiction.** A contradiction is new when two surfaces disagree on a class
   that previously agreed, or when an existing disagreement changes sign or population. Exit 1.
5. **Open a PR, never push to main.** The diff PR carries the regenerated `_MANIFEST.json`, table,
   and `VERDICT_DIFF.json`; a human or the review repo merges it.

## Gate thresholds

| Change | Action |
|---|---|
| same verdicts, numbers moved within CI | no-op (report only) |
| a class verdict changes on any surface | PR + require review |
| two surfaces newly disagree | fail CI (P0) |
| a ledger `input_sha256` no longer equals the live payload | fail CI (provenance broken) |
| `/audit3` and `/audit/data` ledger copies differ | fail CI (same check as the live smoke today) |

## Wiring (when built)

- A workflow on a weekly staggered cron (not :00) that runs steps 1-4 and opens the PR.
- Reuse `tools/doc_source_lint.py` on the regenerated dossiers so a refresh cannot publish a bare number.
- Register the generator path in the AGENTS.md registry in the same PR.

Not implemented in this pass; this is the cadence proposal the program asked for.
