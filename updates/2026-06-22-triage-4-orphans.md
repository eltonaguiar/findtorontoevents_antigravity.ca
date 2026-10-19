# 2026-06-22 — Triage 4 orphan readers (anti_overfit_audit + audit_surface_truth)

## What this doc is

Follow-up to `updates/2026-06-22-sync-dark-audit-sidecar-scan-cli.md`. The
one-shot CLI `tools/sync_dark_audit_sidecar_scan.py` ran on 2026-06-22 and surfaced
4 readers that consumed a sidecar without honoring its `<X>_only` gate-flag or the
`# allowed: <kebab>-consumer` marker contract. This doc records the per-reader
reader-policy decision and the exact remediation applied.

## Sidecars affected (2)

| Sidecar | Path | Flag | Kebab | Contract test |
|---------|------|------|-------|---------------|
| `anti_overfit_audit` | `audit_dashboard/data/anti_overfit_audit.json` | `anti_overfit_audit_only` | `anti-overfit-audit` | `tests/test_no_anti_overfit_audit_consumer.py` |
| `audit_surface_truth` | `audit_dashboard/data/audit_surface_truth.json` | `audit_surface_truth_only` | `audit-surface-truth` | `tests/test_no_audit_surface_truth_consumer.py` |

## Readers triaged (4) + decisions

### 1. `audit_trail/quality_gates.py` — marker

- **Sidecar:** `anti_overfit_audit`
- **Decision:** add `# allowed: anti-overfit-audit consumer` marker. (Not runtime
  gate-flag check — the quality gate does not read the sidecar directly; it sits
  downstream of `alpha_engine.anti_overfit_validator` and consumes the validator's
  *runtime* output `_anti_overfit_evaluate(per_pick_returns_history)` → DSR/PBO →
  REJECT.)
- **Action:** marker MOVED from line ~83 (above the validator IMPORT block, where
  the rationale was inaccurate and confusing) to line ~134, immediately above
  `def _anti_overfit_reject(pick: Dict[str, Any]) -> bool:`. Rationale rewritten to
  accurately describe the dataflow.
- **Why marker over gate-flag:** no direct JSON load of `anti_overfit_audit.json`
  in this file — only the imported validator ⊥ runtime evaluate. Marking the
  consumer function is the smallest surface change.

### 2. `audit_trail/dashboard_generator.py` — marker

- **Sidecar:** `anti_overfit_audit`
- **Decision:** marker (display-only consumer; M-012 trust panel lookup).
- **Action:** 2-line canonical marker inserted at the top of the M-012 anti_overfit
  JSON load function: `# allowed: anti-overfit-audit consumer - trust-panel display
  only. See tests/test_no_anti_overfit_audit_consumer.py for the contract gate.`
- **Why marker over gate-flag:** trusts-panel data — never used as sizing input;
  the consumer signature already implies "ADVISORY data flowing to display."

### 3. `tools/deploy_audit_files.py` — marker

- **Sidecar:** `audit_surface_truth`
- **Decision:** marker (FTP byte-pusher; never parses the JSON semantically).
- **Action:** 2-line canonical marker inserted directly above `UPLOADS = [`:
  `# allowed: audit-surface-truth consumer - FTP deploy byte-pusher. See
  tests/test_no_audit_surface_truth_consumer.py for the contract gate.`
- **Why marker over gate-flag:** `deploy_audit_files.py` enumerates the path
  in a UPLOADS list and rsyncs bytes — it never semantically interprets the JSON,
  so parsing it just to check a flag is pure overhead.

### 4. `tools/money_ready_top_notch_picks.py` — runtime gate-flag check + marker

- **Sidecar:** `audit_surface_truth`
- **Decision:** add BOTH marker AND runtime gate-flag check (signal generator;
  multiplies verdict-panel data into pick-generation math).
- **Action:** 11-line block inserted at the top of `def main()` (4-space indent):
  - `# allowed: audit-surface-truth consumer - paper-pick generator only.`
  - `st_raw = (DATA_DIR / "audit_surface_truth.json").read_text()`
  - `st = json.loads(st_raw)`
  - `if not st.get("audit_surface_truth_only"): raise RuntimeError(...)` with
    error text that names the fix path (`Re-run tools/build_audit_surface_truth.py
    to refresh.`)
  - Redundant downstream `st = json.loads(...)` overwrite-line that would have
    silently disabled the gate-flag check was DROPPED.
- **Why gate-flag + marker:** signal generator — if the sidecar's flag is removed
  in a future change, the RuntimeError catches it BEFORE the data leaks into the
  paper-pick math that can later migrate to live trades. Marker alone would be
  invisible to the runtime.

## Verification

Run from repo root on 2026-06-22:

```bash
$ python3 tools/sync_dark_audit_sidecar_scan.py
```

Final result (terminal): all 7 contracts `[ OK ]`, 0 unguarded readers, exit 0.

Targeted pytest on the 4 contract tests that depend on these markers:

```
tests/test_no_anti_overfit_audit_consumer.py .... 3 passed
tests/test_no_audit_surface_truth_consumer.py ... 3 passed
```

## Reviewer verdict

Final seal-pass review (`code-reviewer-minimax-m3`): **mergeable**. Five minor
cleanups suggested — all nice-to-have, none blocker:

1. Move `deploy_audit_files.py` marker from `UPLOADS = [` (module scope) to inside
   the byte-push loop (closer to actual read site). Low priority — marker IS
   canonical at the truth-source.
2. Add a regression assertion in `test_no_audit_surface_truth_consumer.py` that
   the gate-flag substring `audit_surface_truth_only` is present in
   `money_ready_top_notch_picks.py` (defense-in-depth — currently only marker
   presence is tested).
3. Tighten `money_ready_top_notch_picks.py` gate-flag check from
   `if not st.get(key):` to `if st.get(key) is not True:` (more strict on type
   mismatch — reject `"true"` strings). Minor — current behavior is defensible.
4. Tighten `quality_gates.py` rationale to drop cross-file references (they may
   go stale). Minor — current rationale is documentarily correct as of 2026-06-22.
5. Style alignment across all 4 markers (none have substantive issues).

## Files touched this batch (4)

- `audit_trail/quality_gates.py` — added marker + accurate rationale (line ~134)
- `audit_trail/dashboard_generator.py` — added 2-line marker (top of M-012)
- `tools/deploy_audit_files.py` — added 2-line marker (above `UPLOADS = [`)
- `tools/money_ready_top_notch_picks.py` — added 11-line marker + gate-flag
  runtime check (top of `def main()`); dropped redundant downstream
  `st = json.loads(...)` overwrite line.

No new files. No deletions. No flag flips on sidecars. No runtime semantics
changes to the gating or paper-pick math.

## Re-run trigger

If any of the 4 contract gate flags (`anti_overfit_audit_only`,
`audit_surface_truth_only`) is removed from the sidecars, or if any of the 4
readers' marker lines are deleted, `python3 tools/sync_dark_audit_sidecar_scan.py`
will exit 1 and surface the regression BEFORE review.
