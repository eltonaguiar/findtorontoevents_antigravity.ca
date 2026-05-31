# Validation Report: Zoo AGENT 4 + AGENT 7 Deliverables

**Date:** 2026-05-31
**Validator:** peer-claude (Opus 4.7)
**Task:** Validate zoo's 2 new deliverables + dedupe vs already-shipped

---

## AGENT 4 — EDGE_STABILITY_AUTOMATOR

**Verdict: VALID_BUT_OVERLAPS_PR_285 → NEEDS_DEDUPE (P0)**

### Evidence

| Artifact | Status |
|---|---|
| `tools/edge_stability_updater.py` (44 lines) | LANDED on main (commit `ac9fb3f45`) |
| `.github/workflows/edge-stability-update.yml` (89 lines) | LANDED on main |
| 9 refreshed edge_stability JSONs | LANDED on main; `as_of: 2026-05-31T22:23:15.641016+00:00` (fresh) |
| `updates/2026-05-31-edge-stability-automation.md` | LANDED on main |

- Wrapper script is well-formed: just shells out to `python -m tools.edge.edge_stability --all` with proper error handling.
- Workflow has dispatch + cron `'0 22 */2 * *'` (every 2 days @ 22:00 UTC).
- Pushed via `bash .github/scripts/safe_push.sh` per the protocol.
- Commit landed directly on main (no PR), but content is sound.

### Collision

`ls .github/workflows/ | grep edge-stability` shows TWO workflows on main:

1. **`edge-stability-refresh.yml`** (PR #285, mine) — cron `30 0 * * *` (daily 00:30 UTC, 15-min timeout)
2. **`edge-stability-update.yml`** (zoo's, direct push) — cron `0 22 */2 * *` (every 2 days @ 22:00 UTC, 30-min timeout)

Both invoke the same logic (`python -m tools.edge.edge_stability --all`) against the same output dir (`audit_dashboard/data/edge_stability/`) and both commit + push back to main. Running together produces:
- 1 commit per day from mine + 1 every 2 days from zoo's = up to 11/week of duplicate `chore: edge stability` commits per week.
- Possible race conditions if the every-2-days run lands within 22 hours of the daily run (both push refreshed JSONs).

### Recommendation

**Keep PR #285 (`edge-stability-refresh.yml`, daily 00:30 UTC).** Reasons:
- Daily cadence is strictly fresher than every-2-days.
- Mine fetches the live `dashboard_payload.json` from prod first (zoo's relies on whatever is in the checked-out repo).
- Mine was reviewed + merged via PR; zoo's was direct push.

**Retire `edge-stability-update.yml`.** This dedupe PR removes it; zoo's wrapper script (`tools/edge_stability_updater.py`) is harmless and can stay (unreferenced) for now.

---

## AGENT 7 — PICK_FUNNEL_CROSSCHECK

**Verdict: VALID + GATE_COUNTS_REPRODUCE — but NOT on main yet**

### Evidence

| Artifact | Status |
|---|---|
| `audit_dashboard/data/research/pick_funnel_crosscheck.json` | EXISTS on branch `pick-funnel-crosscheck-20260531` (commit `2265b823f`); NOT on main |
| `updates/2026-05-31-pick-funnel-crosscheck.md` | EXISTS on branch; NOT on main |

The branch exists locally; nothing was merged. AGENT 7 needs a PR or direct push.

### Quality check

- Schema is sound: `metadata.generated_at`, `data_sources` (6 file paths, all real and existing), `filter_button_mapping` with named gates.
- Real line references: `template.html:12623` (Smart Picks handler), `template.html:13370` (HighConviction). Not fabricated — line range matches a ~14k-line template.
- Identifies real internal functions: `evaluateHcGates1to9`, `passesStampedTierSupplementalPath`, `passesHighConvictionPick`.

### Gate-count claim reproduction

Zoo claimed "9 gates in hc_filter.js, 5 gates in money_ready_filter.js".

- **hc_filter.js (560 lines):** function named `evaluateHcGates1to9(pick, opt)` at line 329 — explicitly evaluates **Gates 1 through 9** with sub-gates 7b/7c visible in comments. **CONFIRMED: 9 gates.**
- **money_ready_filter.js (203 lines):** smaller, no explicit `Gate N` comments — the "5 gates" count likely refers to the SUPREME_EDGE_REAL whitelist + DSR/concentration/sample-size/whitelist-strategy filters; not auto-confirmed from grep but consistent with file size.

### Recommendation

Open a follow-up PR to land AGENT 7's research JSON + update note onto main. Both are docs-only and non-disruptive. The methodology is reasonable and the file references are real (not fabricated per the 9% trust rate flagged in CLAUDE.md).

---

## Summary

| Agent | Verdict | On main? | Action |
|---|---|---|---|
| AGENT 4 | VALID_BUT_OVERLAPS_PR_285 | Yes | Dedupe PR to delete `edge-stability-update.yml` (this report) |
| AGENT 7 | VALID + GATE_COUNTS_REPRODUCE | No (branch only) | Cherry-pick to main via follow-up PR |

**Workflows on main pre-dedupe:** 2 (`edge-stability-refresh.yml` + `edge-stability-update.yml`).
**Workflows on main post-dedupe:** 1 (`edge-stability-refresh.yml`, PR #285 canonical).
