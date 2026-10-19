# sync_dark_audit_sidecar_scan.py — 2026-06-22

**One-shot CLI that runs all 5 STRONG + 2 mirrored audit-dashboard sidecar contract tests in a single invocation, and PRIOR to any pass/fail verdict, directly enumerates on-disk sidecar drift + unguarded-reader state in the source tree.**

The orphan-papercut (a sidecar missing its `<X>_only` flag; a consumer reading a sidecar without the gate-flag reference or the `# allowed: <kebab>-consumer` marker) surfaces here **before review**, not after a regression slips through `pytest.skip()`.

---

## What it does

For each of the 7 mirrored contracts (operator_review_today, winner_hunt_replay, audit_surface_truth, anti_overfit_audit, blacklist_reconciliation, blocked_registry, btc_scalping_investigation), it runs 4 sequential checks and renders a per-contract verdict table.

Contract manifest (the SSOT for which sidecars this CLI scans) lives inside `_build_contracts()` at the top of the file. Adding a new mirror = add one entry + the corresponding `tests/test_no_<foo>_consumer.py` file.

---

## When to run it

| When | Why |
|---|---|
| **Before opening a PR that touches an audit-dashboard sidecar** | Proves the flag + marker state is intact; surfaces the orphan BEFORE code-review reads your diff. |
| **Before opening a PR that adds a new reader to `tools/`, `audit_trail/`, `alpha_engine/`** of one of the 7 sidecars | The reader-scan enumerates *every* `.py` under those scan roots, exposing unguarded consumers as a list, not as a pytest blob. |
| **On cron host, after every cron cycle that rebuilds the sidecars** | Set `ALL_SIDECAR_CRON_MODE=1` to flip the dev-friendly "missing on disk is OK in dev" default into a HARD failure — the same cron-mode fail-closed pattern the test files use. |
| **One-shot dev iteration on a single contract** | `--contract <name>` scopes the scan to one contract for fast feedback. |
| **CI integration** | `--json` emits a machine-readable envelope with 4 top-level keys + `global_summary` for direct embedding in a CI job. |

**Don't run it as a hot loop** — Section C spawns one pytest per contract in a `ThreadPoolExecutor` (max-workers=7), so ~7s minimum per invocation. Fine for review-gate, but use `--no-pytest` (A+B+D only) for fast iteration on writer-code-only edits.

---

## Exit-code legend

| Code | Meaning |
|---|---|
| `0` | All contracts green — every sidecar carries `_schema_note` + `<X>_only: True`, no unguarded readers under the 3 scan roots, all pytests passed. |
| `1` | One or more contracts violated — Section B found unguarded readers OR Section C's pytest failed OR (in cron mode) Section A found a missing sidecar. The output lists every violation by contract + file. |
| `2` | The scan itself errored — `--contract <bogus-name>` was passed, registry typo, JSON-load of a sidecar raised an unhandled exception, etc. Inspect stderr. |

In cron mode (`ALL_SIDECAR_CRON_MODE=1`), a missing sidecar on the cron host is exit-1, not a soft "missing in dev checkout". This mirrors the FAIL-CLOSED contract-test pattern and makes the cron wrapper reliable.

---

## The 4 sections

### A — Sidecar flag-on-disk check

For each contract, parse the sidecar JSON and verify it carries BOTH:
- `_schema_note` (free-text prose explaining what the sidecar is)
- The per-contract gate flag (`<X>_only: True`) — strict boolean, not truthy

States: `OK`, `FLAG_MISSING`, `MISSING`, `MISSING_CRON_HARD_FAIL`, `UNPARSEABLE`.

### B — Live reader scan

Walk `tools/`, `audit_trail/`, `alpha_engine/`, find every `.py` that opens the sidecar (filename substring AND a loader-intent pattern BOTH present — pure prose mentions don't qualify). For each such consumer, verify it EITHER:
- References the `<X>_only` flag in its source (i.e., knows it's not for sizing), OR
- Carries the `# allowed: <kebab>-consumer` allow-marker

Anything that opens without one of those two signals is an **unguarded reader** and is added to the section's violation list — sorted, with a count.

For BTC, the marker regex accepts either `btc-scalping-investigation` OR `investigation-audit-entry` (alt-kebab) per the BTC contract-test.

### C — Pytest contract-test summary

Spawn `python3 -m pytest tests/test_no_<foo>_consumer.py --tb=line -q --no-header` per contract in parallel and parse the summary line for `passed` / `failed` / `skipped` counts. On failure, capture up to 10 violation lines for the cross-reference.

This is the authoritative cross-check against Section B — if B says "no violations" but C fails (or vice-versa), the cross-reference surfaces the mismatch.

### D — Cross-reference

Per contract, combine A+B+C findings into a single verdict:
- `OK` = all three green
- `MISSING` = A says sidecar missing but B+C clean (typical for a fresh clone)
- `FAIL` = at least one of A/B/C red

Renders as a table: `contract` / `A:flag` / `B:readers (count)` / `C:pytest` / `VERDICT`.

---

## CLI flags

| Flag | Effect |
|---|---|
| (default) | Human-readable text report, color when stdout is a TTY. |
| `--json` | JSON envelope — 4 top-level section keys + `global_summary`. For CI ingestion. |
| `--contract NAME` | Scope to a single contract (e.g., `anti_overfit_audit`). Exit-2 if unknown. |
| `--no-pytest` | Skip Section C; pure pre-flight scan (A+B+D). Fast for writer-code iterations. |
| `--quiet` | Suppress all output; rely solely on exit code. |
| `--timeout SEC` | Per-pytest timeout, default 60s. |

---

## Verification (2026-06-22)

- `py_compile` passes ✅
- Default text-mode run exits 1 and surfaces 2 real orphans (the CLI's whole value-add):
  - `audit_trail/quality_gates.py` + `audit_trail/dashboard_generator.py` consume `anti_overfit_audit.json` without the gate flag or marker
  - `tools/deploy_audit_files.py` + `tools/money_ready_top_notch_picks.py` consume `audit_surface_truth.json` without the gate flag or marker
- `--json`, `--no-pytest`, `--contract winner_hunt_replay` (exit 0, clean), `--contract bogus` (exit 2), `--quiet` (exit 1, no output) — all paths verified ✅
- A pre-fix `SyntaxError` on the first run (line ~648, f-string-with-inner-`:` format-spec pitfall) was repaired by precomputing the verdict cell outside the outer f-string; a comment block documents the gotcha.

---

## Related files

- `tools/sync_dark_audit_sidecar_scan.py` — the CLI itself (~500 lines)
- `tests/test_no_<foo>_consumer.py` ×7 — the 7 contract tests this script orchestrates
- `audit_dashboard/data/*.json` ×5 + `audit_trail/*.json` ×2 — the 7 sidecars
- `tests/test_no_sizing_consumer.py` — the canonical pattern the other 6 mirror

---

## Suggested cron wiring (not yet committed)

Add a half-hourly sister workflow that runs `python3 tools/sync_dark_audit_sidecar_scan.py --quiet --json` with `ALL_SIDECAR_CRON_MODE=1` in the env and posts the envelope to the audit-dashboard's stderr feed. Exits 0 only when all 7 contracts are simultaneously green.
