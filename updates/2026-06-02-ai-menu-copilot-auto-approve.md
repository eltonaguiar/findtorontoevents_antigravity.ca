# AI_MENU + Copilot CLI auto-approve (2026-06-02)

## Problem

`tools/agent_run.sh copilot` launched without `--allow-all`. YOLO flags were
duplicated between `ai_menu.sh` and an unused include file.

## Fix

- **`tools/ai_menu_yolo.inc.sh`** — single map; `ai_menu_yolo_flags` / `ai_menu_yolo_env`
- **`tools/ai_menu.sh`** — sources include; Copilot gets `--allow-all` + `COPILOT_ALLOW_ALL=1`
- **`tools/agent_run.sh`** — same injection for all AI menu keys

## Verified

```bash
bash tools/ai_menu.sh --yolo-info | grep copilot   # --allow-all
bash -n tools/ai_menu.sh tools/agent_run.sh tools/ai_menu_yolo.inc.sh
```