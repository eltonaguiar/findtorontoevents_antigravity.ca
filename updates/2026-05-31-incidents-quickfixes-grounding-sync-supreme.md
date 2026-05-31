# Incidents Quick-Fix Batch — 2026-05-31

## Summary

Four fixes addressing open incidents from `findtorontoevents.ca/audit/incidents.html` that were NOT covered by existing open PRs.

## Fixes

### 1. P1: Multi-AI panel grounding failure — programmatic leakage injection

**Incident:** 5/5 NIM models converged on false COMMODITY alpha (2026-05-25) because consult prompts omitted leakage evidence from `hypothesis_registry.json`.

**What changed:**
- `tools/swarm/worker_runner.py`: Added `_load_grounding_context()` function that reads `reports/hypothesis_registry.json`, extracts REJECTED/KILLED/FAILED_ARCHIVED/TESTED_KILL entries, and formats a grounding block. Modified `_read_prompt()` to append this block to every swarm prompt automatically.
- `.claude/skills/consult-cloudflare-models/SKILL.md`: Added mandatory leakage-context block template (mirroring `consult-nvidia-models/SKILL.md`) with when-to-include rules and post-fan-out cross-check guidance.
- `.claude/skills/consult-cloudflare/SKILL.md`: Added grounding note to Notes section referencing the new auto-injection and manual consult requirements.

**How it works:** Prompts dispatched through `worker_runner.py` that match financial keywords (54 trading/asset-class terms) automatically get a "KNOWN FALSIFIED / REJECTED HYPOTHESES" section appended. Non-financial prompts (code reviews, docs, etc.) are unaffected. The context is cached per-process so repeated calls don't re-read the file.

**Verification:** `python3 -c "from worker_runner import _load_grounding_context; ctx = _load_grounding_context(); assert 'H-001' in ctx"` — confirmed H-001 (COT look-ahead) and other rejected hypotheses are injected.

### 2. Enhancement: MySQL sync critical silent-fail removal

**Incident:** `alpha-engine-live.yml` line 772 swallowed `sync_all_picks_to_mysql.py` failures with `|| echo "non-fatal"`, hiding data-integrity issues for hours.

**What changed:**
- `.github/workflows/alpha-engine-live.yml`: Replaced `|| echo "non-fatal"` with explicit `exit 1` on failure, emitting a `::error::` annotation. Added `continue-on-error: true` + `id: mysql_sync` so the workflow doesn't abort — scan results still get committed even if DB is temporarily unreachable. Added a follow-up warning step that fires on sync failure.

**Verification:** YAML parses cleanly via `yaml.safe_load()`.

### 3. P1: Cloudflare SKILL.md grounding instructions

**Incident:** `consult-cloudflare-models/SKILL.md` and `consult-cloudflare/SKILL.md` had zero guidance on hypothesis registry context or leakage signals, unlike `consult-nvidia-models/SKILL.md` which had the full template.

**What changed:** Both CF skill files now include the mandatory leakage-context block template, when-to-include rules, and post-fan-out cross-check guidance.

### 4. P0: SUPREME EDGE banner enhancement

**Incident:** The SUPREME EDGE section on `/audit/` had caveats buried inside individual entries but no prominent top-of-section warning that the entire block is research-only.

**What changed:**
- `audit_dashboard/template.html`: Added a red-bordered "RESEARCH ONLY — NOT ACTIONABLE FORWARD SIGNALS" banner at the top of the SUPREME EDGE div, citing the post-hoc segment warning, over-emission artifacts, and small-sample DSR inflation risks.

## Files modified

| File | Change |
|------|--------|
| `tools/swarm/worker_runner.py` | +80 lines: grounding context loader + financial-keyword heuristic + injection in `_read_prompt()` |
| `.github/workflows/alpha-engine-live.yml` | Line 772: `|| echo` → `exit 1` with `continue-on-error` + commit-salvage |
| `.claude/skills/consult-cloudflare-models/SKILL.md` | +38 lines: mandatory leakage-context block section |
| `.claude/skills/consult-cloudflare/SKILL.md` | +2 lines: grounding note in Notes section |
| `audit_dashboard/template.html` | +4 lines: RESEARCH ONLY banner at top of SUPREME EDGE div |

## Incidents addressed

| ID | Severity | Title | Status |
|----|----------|-------|--------|
| P1 OVERALL | P1 | Multi-AI panel reached wrong COMMODITY consensus on ungrounded prompt | FIXED (programmatic injection) |
| Enhancement | HIGH | MySQL sync workflow silent-fail removal | FIXED (critical path) |
| P1 OVERALL | P1 | Cloudflare SKILL.md missing grounding | FIXED |
| P0 OVERALL | P0 | Cherry-picked SUPREME EDGE stats | IMPROVED (prominent banner added) |
