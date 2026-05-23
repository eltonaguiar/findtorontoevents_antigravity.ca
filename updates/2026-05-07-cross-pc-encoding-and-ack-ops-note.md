# 2026-05-07 - Cross-PC Ops Note: Encoding + ACK Verification

## What was observed

- Windows console `print()` on raw event dicts can throw `UnicodeEncodeError` when payloads contain emoji/non-ASCII text.
- A previously retried DM message (`cd5b4baf-d4fc-4917-9e90-aec7e50af808`) no longer existed in pending ACK state when manually acknowledged.

## What changed

Updated documentation to make operations safer:

- `docs/cross_pc_protocol_runbook.md`
  - Added Windows encoding guidance (`PYTHONUTF8=1`, `chcp 65001`).
  - Added ASCII-safe event-tail one-liner using `json.dumps(..., ensure_ascii=True)`.

- `.claude/skills/cross-pc-protocol-debug-first/SKILL.md`
  - Added `UnicodeEncodeError` troubleshooting row.
  - Added ASCII-safe tail command for Windows.

## Verification

- Manual ACK attempt:
  - `POST /ack` for message `cd5b4baf-d4fc-4917-9e90-aec7e50af808` returned `{"ok": false, ...}`
  - Confirms message was not pending in retry tracker at the time of check.

- Event-tail command:
  - ASCII-safe one-liner prints recent events without console encoding failure.
