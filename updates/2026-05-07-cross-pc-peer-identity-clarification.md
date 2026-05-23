# 2026-05-07 - Cross-PC Peer Identity Clarification

## Problem

Cross-PC envelopes showed `from=claude-main` for messages that were intended to represent Cursor. This was caused by operator command usage (`--peer-id claude-main`) rather than transport failure.

## Fix

Updated adapter behavior and docs to reduce identity mistakes:

1. `tools/adapters/cursor_claude_adapter.py`
   - `--peer-id` is now optional.
   - Added `--runtime` (`cursor|claude|hermes|freebuff|agent`).
   - Sender identity resolution order:
     1. explicit `--peer-id`
     2. `CROSS_PC_PEER_ID`
     3. inferred `<runtime>-<hostname>` (from `--runtime` / `CROSS_PC_RUNTIME`)

2. `docs/cross_pc_protocol_runbook.md`
   - Added "Peer identity rules (critical)" section.
   - Added recommended naming convention per runtime.
   - Updated examples to use runtime-based identity when explicit peer IDs are not needed.

3. `.claude/skills/cross-pc-protocol-debug-first/SKILL.md`
   - Added identity resolution and anti-mislabel guidance.
   - Updated quickstart/examples to avoid forcing `claude-main` style IDs.

## Outcome

Message ownership in logs now maps correctly to runtime intent by default, while still allowing explicit peer IDs when needed.
