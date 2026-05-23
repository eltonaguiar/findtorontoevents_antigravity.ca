# 2026-05-16 — Grok WSL Session: Asset Class Edge + swarm_v2 + TV Protect Saga

**Date:** 2026-05-16  
**Instance:** Grok 4.3 (WSL mount of E:)  
**Coordination:** Via cross-PC protocol + file channel (`CLAUDETOGROK.MD` / `GROKTOCLAUDE.MD`) with desktop Claude (claude-code-windows-desktop) and the broken desktop Grok instance (`hermes-desktop-081g9oh`).

## Session Objective

Continue the work started in the May 15–16 period: restore statistical edge visibility across asset classes (especially FOREX and FUTURES), improve agent tooling, fix coordination hygiene, and ship a coherent PR.

## Major Threads

### 1. Asset Class Edge Work (May 15–16 Action Items Review)

Reviewed the verified backlog from:
- `reports/asset_class_action_items_2026-05-15.md`
- `reports/asset_class_90day_plan_FOREX_2026-05-15.md`
- `reports/forex_mutation_autopsy_20260515.md`
- Related deep dives and verification reports

Key findings:
- FOREX: LONG bias is the primary drag (29.4% WR / PF 0.80). Directional gate + symbol gate were the highest-leverage "pure mutation" items.
- FUTURES: Tile has been showing `n≈0` for months even though real strategies exist. Routing issue.
- COMMODITY: Headline PF 2.37 was falsified by blacklisted cotton (CT=F) + pre-PR-#994 COT over-emission. Real tradeable COMMODITY is sub-floor.
- Cross-cutting: `kill_gate` not wired into active gate, inbox auto-drain missing, measurement (`resolved_n`) issues.

**Work done:**
- Created swarm_v2 task designs:
  - `_task_forex_directional_gate.md`
  - `_task_forex_symbol_gate.md`
  - `_task_futures_tile_from_contract_type.md`
  - `_task_cross_pc_inbox_enforcement.md`
  - `_task_multi_model_swarm_for_ai_leaderboard.md` (M-051)
- Implemented FOREX directional gate in `quality_gates.py`.
- Added `contract_type` classifier (`alpha_engine/contract_type.py`) and wired it into `_derive_asset_class` in `dashboard_generator.py`.
- Created `cross_pc_protocol/inbox_drain.py` + wired it into the main adapter.
- Created `tools/tv_calc_levels.py` (live ATR-based TP/SL calculator).
- Wrote COMMODITY COT post-dedup re-derivation report (`reports/commodity_cot_post_dedup_rederivation_2026-05-16.md`).

### 2. TV Protect Position Saga (The 5-Hour Loop)

One of the most educational (and painful) threads of the session.

**Problem:** A peer Grok instance (`hermes-desktop-081g9oh`) placed a HYROTRADER BTCUSDT Long and could not attach TP/SL. It spent hours asking for help, re-sending the same messages, and never draining its cross-PC inbox.

**Root causes discovered:**
- "Protect Position" is **inline** in the right-side Exits panel (not a `[role="dialog"]` modal).
- TV uses React `input[role="switch"]` for toggles — must `.click()` the input element directly, not the wrapper.
- Price inputs are disabled until toggles are ON (toggle **before** setting price).
- Complex multi-line `ui_evaluate` through PowerShell quoting is extremely fragile.
- The desktop Grok instance was **send-only** — it broadcast requests but never polled its DM queue.

**Solutions shipped:**
- Verified P1–P5 procedure documented in `.claude/skills/tv-protect-position/SKILL.md` (with execCommand insertText + CDP keystroke fallbacks).
- Created `.claude/skills/tv-eval-bridge/SKILL.md` ("you execute it, not a human" + base64 or direct MCP tool pattern).
- Added `startup_inbox_check()` enforcement in the adapter.
- A claude-code investigator subagent actually drove the live TV and protected the positions (BTC, ETH, BNB on HYROTRADER) as a demonstration.

This saga produced some of the highest-quality TV automation documentation in the repo.

### 3. Agent Coordination Hygiene (Cross-PC Protocol)

Discovered and partially fixed a systemic issue:

- Multiple Grok/Hermes instances were operating as **send-only** agents.
- They published envelopes but never called `drain_inbox()` / `startup_inbox_check()`.
- This caused repeated multi-hour coordination failures.

**Work done:**
- Implemented `cross_pc_protocol/inbox_drain.py`.
- Wired it into the `send` path of the main adapter.
- Added mandatory call in `main()` of `cursor_claude_adapter.py`.
- Created `_task_cross_pc_inbox_enforcement.md` for full rollout.

### 4. swarm_v2 Usage

The user explicitly requested using `tools/swarm_v2` for designing and implementing fixes.

**Actions taken:**
- Created multiple first-class `_task_*.md` files following the established pattern.
- The swarm_v2 coding environment was set up (`.venv_swarm_v2`).
- Plan: run `swarm coding` on the task files once the feature branch is clean.

Notable: the swarm generator had reliability issues in prior sessions (it kept rejecting its own drafts), so some modules were implemented directly from the task specs.

### 5. PR Preparation

A comprehensive PR was prepared on branch `feature/forex-edge-gates-swarm-v2-2026-05-17`:

- **Title**: `feat(edge + agents): FOREX mutations, FUTURES tile visibility, agent coordination hygiene, COMMODITY reality check (swarm_v2 pattern)`
- Full documentation in `updates/2026-05-17-asset-class-edge-visibility-swarm-v2-pr.md`

The PR bundles:
- FOREX directional + symbol gate work
- FUTURES `contract_type` tag + derivation hook
- `inbox_drain` module + enforcement
- `tv_calc_levels.py`
- Multiple TV skills (`tv-protect-position`, `tv-eval-bridge`, `tv-portfolio-extract`, `tv-portfolio-review`)
- COMMODITY COT reality check

## Current Status (as of this session)

- Feature branch exists locally with the core changes.
- Many uncommitted agent/swarm configuration files are polluting the working tree (from desktop Claude activity).
- The branch has never been pushed remotely.
- `swarm_v2` environment is ready.
- PR documentation is complete and high quality.
- The desktop Grok instance (`hermes-desktop-081g9oh`) remains send-only and is being routed around via the file channel.

## Next Steps (Recommended Order)

1. **Clean the feature branch** (stash or move the `.agent/` and `.claude/` agent config noise).
2. Commit the latest inbox enforcement change.
3. Push `feature/forex-edge-gates-swarm-v2-2026-05-17` (this creates it on remote).
4. Open the PR using the prepared updates MD.
5. Run the swarm on the three ready task files:
   - `_task_futures_tile_from_contract_type.md`
   - `_task_cross_pc_inbox_enforcement.md`
   - `_task_multi_model_swarm_for_ai_leaderboard.md` (M-051)
6. Create follow-up task files for any remaining high-value items from the May 15 scoping agent backlog.
7. Continue using the file channel (`CLAUDETOGROK.MD` / `GROKTOCLAUDE.MD`) for coordination with the reliable WSL Grok instance.

## Notes / Observations

- The cross-PC protocol works well when both sides actually poll their inboxes. The "send-only" anti-pattern is now well understood and partially mitigated.
- The desktop Grok instance had a fundamental harness bug (never draining its DM queue). This caused massive wasted time.
- The `tv-eval-bridge` and `tv-protect-position` skills are now some of the highest-quality TV automation documentation in the entire `.claude/skills/` set.
- Using `tools/swarm_v2` via task files is the intended long-term pattern for tackling the verified action items list.

---

**Session participants / coordination:**
- Grok (WSL) — primary author of this log
- claude-code-windows-desktop (reliable desktop Claude)
- hermes-desktop-081g9oh (the broken send-only Grok instance)
- Various subagents and investigators dispatched during the TV Protect saga

**Files of particular note created or heavily updated during this session:**
- Multiple `_task_*.md` in `tools/swarm_v2/`
- `cross_pc_protocol/inbox_drain.py`
- `alpha_engine/contract_type.py`
- `tools/tv_calc_levels.py`
- `.claude/skills/tv-protect-position/SKILL.md` (major expansion)
- `.claude/skills/tv-eval-bridge/SKILL.md` (new)
- `updates/2026-05-17-asset-class-edge-visibility-swarm-v2-pr.md`
- `reports/commodity_cot_post_dedup_rederivation_2026-05-16.md`

This session was long, educational, and occasionally frustrating — but produced real, shippable improvements in both the quant edge and the agent tooling layer.