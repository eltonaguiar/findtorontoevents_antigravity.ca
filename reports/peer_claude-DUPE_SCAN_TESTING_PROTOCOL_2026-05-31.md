# Dupe Scan — Testing / Protocol / Methodology Files (2026-05-31)

Author: peer_claude (Opus 4.7)
Scope: testing protocols, mutation/strategy pipelines, paper-pilot harness, money-maker-ready docs, AGENTS/CLAUDE/CHARTER md.

## Headline numbers

- **Total candidates (raw find):** 2398
- **Worktree orphan copies (`.claude/worktrees/...`):** 2292 — every canonical file is replicated ~30x across in-flight Claude worktrees. These are not human-authored copies; they are short-lived per-agent checkouts and should NEVER be edited or deduped in place (deletion would corrupt running agent sessions). Recommendation: leave alone, let normal worktree cleanup garbage-collect them.
- **Candidates after stripping worktrees + `.venv` + `__pycache__` + `backups`:** 88
- **Byte-identical duplicate groups across canonical paths (post-strip):** 0 (every canonical hash is unique)
- **Filename-collision groups (same basename, different dir, different content):** 2 (see below)
- **Divergent variants needing human triage:** see "Divergent / overlapping" section — semantically overlapping but not byte-identical (~14 money_maker_ready_* dated dumps, 2 methodology.md, 2 AGENTS.md)
- **Unique files to process:** 88, split into 5 batches of ~18.

## Byte-identical duplicate groups

Outside `.claude/worktrees/`, `.venv/`, `__pycache__/`, and `backups/`: **0 byte-identical duplicate groups.** Every md5 in the 88-file set is unique. The huge raw-find dupe counts (34, then many 30x groups) are 100% worktree replication — same canonical file checked out by ~30 concurrent Claude worktrees.

## Filename-collision groups (same basename, different content)

1. `METHODOLOGY.md` — `tools/swarm/METHODOLOGY.md` vs `reports/kimi_uplift_2026_05_02/METHODOLOGY.md`. Different domains (swarm orchestration vs Kimi uplift report). Keep both.
2. `AGENTS.md` — root `./AGENTS.md` vs `./KIMI_CLAW_RESEARCH_FEB162026/AGENTS.md`. Root is canonical; Kimi subdir is a vendored research-package convention. Keep both, no action.

## Divergent variants needing review (semantic overlap, NOT byte-identical)

These are not dedup candidates by hash but are conceptually overlapping — a human/swarm should decide whether to consolidate or archive older snapshots.

- **`money_maker_ready_<TIMESTAMP>.md` series (12 files in `reports/`)** from 2026-05-12 through 2026-05-19, plus `_CORRIGENDUM`, `v2`, `v2_deep_dive_2026-05-31`, `ADDENDUM_TODOS`, `FREEBUFF_INTEGRATION`, `NORTH_STAR`. These are dated snapshots; older ones should be moved to `reports/archive/money_maker_ready/` or pruned to last-N. Latest live = `money_maker_ready_v2_deep_dive_2026-05-31.md`.
- **`money_ready_verdict_2026-05-17.{json,md}`** vs `audit_dashboard/data/money_ready_verdict.json` (live) vs `audit_dashboard/data/money_ready_archive/money_ready_2026-05-17.json` — three separate paths for what may be the same verdict; verify the archive vs reports copy.
- **`docs/METHODOLOGY_FOR_EXPERTS.md`**, **`docs/SWARM_REVISED_METHODOLOGY_2026-05-13.md`**, **`docs/swarm_prompts/METHODOLOGY_R2.md`**, **`reports/PHENOMENAL_PERFORMANCE_METHODOLOGY.md`**, **`reports/MONEY_READY_METHODOLOGY.md`**, **`reports/CLAUDE_METHODOLOGY_PROOF_2026_05_02.md`**, **`reports/CONFIDENCE_METHODOLOGY_2026-05-24.md`** — six+ methodology-flavored docs in three different roots. Risk of contradiction across them; needs a "which is canonical / which are dated snapshots" index.
- **`docs/PAPER_PILOT_HARNESS.md`** vs **`alpha_engine/paper_pilot_harness.py`** vs **`tests/test_*charter*`** — one doc, one impl, multiple tests. Wire-up audit per CLAUDE.md "Wire-Up Rule" would be appropriate.
- **`audit_dashboard/data/money_ready_archive/money_ready_2026-05-{17..31}.json`** (12 dated json snapshots) — already correctly in an `archive/` dir; pure data history, no action.

## Archive (preserve, no dedup)

- `backups/money-maker-readyv2.md.bak` — explicit `.bak`
- `audit_dashboard/data/money_ready_archive/*.json` — dated snapshots
- `reports/90day_pages_2026-05-15/hyrotrader_methodology_enhancements_2026-05-15.html` — dated archive page
- `.venv/lib/...` test_protocol files — vendored library tests (jsonschema, numba, numpy)

## Unique-files list (88) — split into 5 batches

Stored at `/tmp/batch_00` through `/tmp/batch_04` (18, 18, 18, 18, 16 lines).

### Batch 00 (18 files — root agent docs + alpha_engine charter modules + first half of money_ready_archive)
- ./AGENTS.md
- ./alpha_engine/charter_drift_circuit_breaker.py
- ./alpha_engine/charter_position_sizer.py
- ./alpha_engine/charter_risk_budget.py
- ./alpha_engine/charter_slippage.py
- ./alpha_engine/money_ready_verdict.py
- ./alpha_engine/paper_pilot_harness.py
- ./audit_dashboard/antigravity_picks_methodology.md
- ./audit_dashboard/CLAUDE_TOP_PICKS_METHODOLOGY.md
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-17.json
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-18.json
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-19.json
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-20.json
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-21.json
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-24.json
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-26.json
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-27.json
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-28.json

### Batch 01 (18 files — rest of archive + audit_dashboard JS + CLAUDE.md + config + docs methodology + GHA)
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-29.json
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-30.json
- ./audit_dashboard/data/money_ready_archive/money_ready_2026-05-31.json
- ./audit_dashboard/data/money_ready_verdict.json
- ./audit_dashboard/money_ready_filter.js
- ./CLAUDE.md
- ./config/charter_floors.yaml
- ./docs/AI_PREDICTION_TOURNAMENT_METHODOLOGY.md
- ./docs/COMPOUND_FILTER_METHODOLOGY.md
- ./docs/METHODOLOGY_FOR_EXPERTS.md
- ./docs/PAPER_PILOT_HARNESS.md
- ./docs/PERFORMANCE_CHARTER.md
- ./docs/STRATEGY_PIPELINE_END_TO_END_2026-05-31.md
- ./docs/swarm_prompts/METHODOLOGY_R2.md
- ./docs/swarm_prompts/MONEY_READY_HARVEST_v1.md
- ./docs/swarm_prompts/MONEY_READY_MASTER_v1.md
- ./docs/SWARM_REVISED_METHODOLOGY_2026-05-13.md
- ./.github/workflows/money-ready-registry-gate.yml

### Batch 02 (18 files — GHA + Kimi vendored + first half of `reports/`)
- ./.github/workflows/money-ready-snapshot.yml
- ./KIMI_CLAW_RESEARCH_FEB162026/AGENTS.md
- ./KIMI_RISEOFTHECLAW/METHODOLOGY_AUDIT_TRAIL.md
- ./reports/2026-05-25_money_maker_readyv2_vs_actual.md
- ./reports/90day_pages_2026-05-15/hyrotrader_methodology_enhancements_2026-05-15.html
- ./reports/ai_tournament_methodology_swarm_review_20260519.md
- ./reports/CLAUDE_METHODOLOGY_PROOF_2026_05_02.md
- ./reports/CONFIDENCE_METHODOLOGY_2026-05-24.md
- ./reports/DEEP_DIVE_MONEYREADY_2026-05-18.md
- ./reports/equity_money_ready_path_20260517.md
- ./reports/HARVEST_CONSTRUCTIVE_MONEY_READY_2026-05-19.md
- ./reports/hyrotrader_methodology_enhancements_2026-05-15.md
- ./reports/kimi_uplift_2026_05_02/METHODOLOGY.md
- ./reports/money_maker_ready_20260512T194402Z_CORRIGENDUM.md
- ./reports/money_maker_ready_20260512T194402Z.md
- ./reports/money_maker_ready_20260514T001749Z.md
- ./reports/money_maker_ready_20260514T204900Z.md
- ./reports/money_maker_ready_20260514T231246Z.md

### Batch 03 (18 files — second half of `reports/` money_maker_ready + verdicts + roadmap + scripts)
- ./reports/money_maker_ready_20260515T211949Z.md
- ./reports/money_maker_ready_20260516T000106Z.md
- ./reports/money_maker_ready_20260516T060000Z.md
- ./reports/money_maker_readyv2_2026-05-17.md
- ./reports/MONEY_MAKER_READYV2_ADDENDUM_TODOS_2026-05-19T0010Z.md
- ./reports/money_maker_ready_v2_deep_dive_2026-05-31.md
- ./reports/MONEY_MAKER_READYV2_FREEBUFF_INTEGRATION_2026-05-19T0030Z.md
- ./reports/MONEY_MAKER_READYV2_NORTH_STAR_2026-05-19T2350Z.md
- ./reports/MONEY_READY_METHODOLOGY.md
- ./reports/money_ready_per_class_synthesis_2026-05-31.md
- ./reports/money_ready_state_2026-05-12T23Z.md
- ./reports/money_ready_validation_plan_2026-05-11.md
- ./reports/money_ready_verdict_2026-05-17.json
- ./reports/money_ready_verdict_2026-05-17.md
- ./reports/peer_claude-URGENT_METHODOLOGY_FLAG_MC_AUDIT_TOOL_2026-05-31.md
- ./reports/PHENOMENAL_PERFORMANCE_METHODOLOGY.md
- ./reports/roadmap_no_edge_to_money_ready_2026_05_18.md
- ./scripts/deploy_testing_protocol_tables.py

### Batch 04 (16 files — root TESTING_PROTOCOL + tests + tools + updates)
- ./TESTING_PROTOCOL.MD
- ./tests/test_charter_concentration_gate_optin.py
- ./tests/test_charter_drift_circuit_breaker.py
- ./tests/test_charter_position_sizer.py
- ./tests/test_charter_risk_budget.py
- ./tests/test_charter_slippage.py
- ./tests/test_cross_pc_protocol.py
- ./tests/test_money_ready_verdict.py
- ./tests/test_production_scanner_charter_sizer_wire.py
- ./tools/ci_gate_money_ready_vs_registry.py
- ./tools/money_ready_snapshot.py
- ./tools/swarm/agent_personas/score-methodology-auditor.md
- ./tools/swarm/METHODOLOGY.md
- ./tools/swarm/prompts/ai_tournament_methodology_review_20260519.md
- ./updates/2026-04-23-audit-whatif-hc-scoping-methodology.md
- ./updates/2026-05-28-commodity-fv-exempt-revoke-money-ready-sync.md

## Recommendations for next phase

1. **Skip dedup of `.claude/worktrees/`** — 2292 copies are intentional per-agent checkouts; do not touch.
2. **No byte-dedup needed** in the canonical set (88 unique hashes).
3. **Manual review priority** is the methodology-doc sprawl (Batches 01–03) — likely 3-5 of those should be marked archive/superseded with a stub pointer to the canonical doc.
4. **`reports/money_maker_ready_*.md` dated series** (12 files): propose moving everything older than `2026-05-25_money_maker_readyv2_vs_actual.md` to `reports/archive/money_maker_ready/`.
