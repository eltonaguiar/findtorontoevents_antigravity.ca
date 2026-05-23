# Task: CRYPTO UTC-Hour Statistical Edge Filter (swarmv2-coding)

**Priority:** P1 for Goal #1 — /audit asset class edge (CRYPTO sub-T2 WR 46.9% → lift via time gate)
**Provenance:** Validated in DAILY_IDEAS review 2026-05-16 (GROK, KIMICLI, edge_per_class report NS-C, synthesis #1, memory project_clean_data_symbol_wr). 22 UTC = 61.2% WR (n>1000), 08-09 UTC = death zone for CRYPTO. Free pure-stat edge, no API keys. Matches existing death_zone logic in forward_validator.py but CRYPTO-specific and reject (not just penalty).
**Holographic:** Decision crypto-hour-filter-20260516 + learning asset_edge 2026-05-16 stored via tools/holographic_memory.py for Hermes recall.
**Wire-Up:** Must add caller in production path (quality_gates.passes_active_gate / passes_smart_gate or score_booster.calculate_smart_score). Env-gated (CRYPTO_HOUR_FILTER_ENABLED=1 default on). Fail-open.
**Scope:** 1 PR only your changes (after pull-rebase), + updates/ doc, tests.

## Acceptance Criteria
- New fn `passes_crypto_hour_gate(pick: dict) -> bool` in audit_trail/quality_gates.py (modeled on 2026-05-17 FOREX directional/symbol gates at ~5347-5382).
- Gate: if asset_class==CRYPTO and created_at/entry_time hour in (8,9) → reject (log "CRYPTO death zone 08-09 UTC rejected").
- Optional: if hour==22 → boost elite_score or add flag (for future rank).
- Wire call in passes_active_gate / smart gate early, after safety, before other filters.
- Also expose in alpha_engine/score_booster.py _calibrate or new _hour_filter (for smart_picks).
- Config: alpha_engine/config.py add CRYPTO_HOUR_FILTER_ENABLED (default "1").
- Backtest evidence: quick script or note using recent_closed CRYPTO from dashboard_data.json showing WR lift when excluding 08-09.
- Tests: add to tests/ (e.g. test_quality_gates.py) for the new gate + env disable.
- Dashboard: no UI change needed (gate affects emitted picks; /audit will show cleaner CRYPTO stats next cron).
- No broad globs, follow Wire-Up Rule (production caller added).
- Verified: py_compile, pytest relevant, no regressions on existing FOREX gates.

## Implementation Steps for Swarm Coding Agents
1. Read current gates in audit_trail/quality_gates.py (focus 5347+ FOREX pattern, _passes_dow_gate).
2. Read forward_validator.py time gate (~466 death_zone 21-24 as reference, but adapt to reject for CRYPTO 08-09).
3. Read config.py for similar env flags (FOREX_*, CRYPTO_*).
4. Add the gate fn + call site (fail-open try/except).
5. Update config.py with flag.
6. (Optional) score_booster.py enhancement for boost at 22 UTC.
7. Add minimal test.
8. Write updates/2026-05-16-crypto-hour-filter-edge-pr.md (broken: no time gate despite memory proof → low CRYPTO WR; changed: gate + wiring; verified: live stats pre/post sim, py_compile, pytest).
9. Create _task_ output + PR plan in the swarm run.

## Evidence to Cite
- Live: dashboard_data.json asset_class_health CRYPTO PF 1.32/46.9% n~7815 (sizing True but WR<50 drags Tier).
- Weekly filter (edge_filter_engine_v3): CRYPTO can hit PF 3.15 with LONG+family filters — hour gate complements by cleaning time noise.
- Memory: project_clean_data_symbol_wr, feedback_quick_guess_horizons.
- Reports: daily_ideas_edge_per_class_20260513T010800Z.md (Edge #10, NS-C), daily_ideas_synthesis_2026-05-15.md (#1), DAILY_IDEAS_GROK_2026_05_16.MD (IDEA-GROK-B time effects).

## Risk / Guards
- Fail-open on any error (preserve current behavior).
- Only CRYPTO (other classes may have different hour edges).
- Do not expand BLOCKED_* without docs/MUTATION_THREE_AXIS_PROTOCOL.
- After merge: run dashboard cron or local py_compile only (no generators), gh run watch, then FTP? (no, dashboard auto on push per audit-dashboard.yml paths).

## Swarmv2-Coding Invocation (after task file ready)
cd tools/swarm_v2
# pip install -e ".[dev]" if not
swarm coding _task_crypto_utc_hour_filter.md --agents 3 --strict --verify
# or via python -m swarms.cli.main coding ...
# Output: generated code patches, test results, PR description snippet.
# Then human: review, git branch feature/crypto-hour-edge-2026-05-16, apply, commit only your files + holographic update + memory/2026-05-16.md + updates/ doc.

## Post-Swarm Verification (human or follow-up agent)
- python3 -m py_compile audit_trail/quality_gates.py alpha_engine/config.py
- python -m pytest tests/test_quality_gates.py -k crypto or hour --tb=line
- python3 -c "
import json, os
os.environ['CRYPTO_HOUR_FILTER_ENABLED']='1'
# mock pick at 08:00 UTC, assert rejected
from audit_trail.quality_gates import passes_active_gate
pick = {'asset_class':'CRYPTO', 'symbol':'BTCUSDT', 'direction':'LONG', 'entry_time':'2026-05-16T08:05:00Z', 'elite_score':50, 'confidence':0.6}
print('08:00 reject?', not passes_active_gate(pick))  # expect True (rejected)
"
- Confirm in holographic: decisions include this, learnings tagged.
- Update AGENTS.md? only if new convention.
- PR body must answer Wire-Up yes (production caller in quality_gates).

**Done when:** Gate live in main, next dashboard shows improved CRYPTO cohort (fewer low-quality time picks), holographic decision closed.

This task created 2026-05-16 by Grok 4.3 after full DAILY_IDEAS review + holographic persistence for Hermes continuity. Per AGENTS.md no looping, concrete, Goal#1.