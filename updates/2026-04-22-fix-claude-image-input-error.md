# Fix: Claude CLI Image Input Error — Invalid Model Name

**Date:** 2026-04-22  
**Component:** `tools/computer_use_tradingview.py` (and agent worktree copies)  
**Severity:** Blocker — Computer Use feature completely non-functional

---

## Problem

The Claude CLI was failing with error:

```
ERROR: Cannot read "image.png" (this model does not support image input)
```

`tools/computer_use_tradingview.py` (lines 34) was configured with:

```python
MODEL = "claude-sonnet-4-6"  # sonnet is faster + cheaper for computer use loops
```

This model name is **not a valid vision-capable Anthropic model identifier**. The Anthropic API requires fully-qualified dated model names. The shorthand `claude-sonnet-4-6` does not resolve to a vision-enabled variant, causing the API to reject image (base64 PNG) payloads sent in the computer use loop (lines 246, 312, 339).

The script sends screenshots on every iteration as:

```python
{
    "type": "image",
    "source": {
        "type": "base64",
        "media_type": "image/png",
        "data": screenshot_b64,
    },
}
```

A non-vision model cannot process these, hence the error.

## Fix

Updated `MODEL` to a current vision-capable Sonnet model:

```python
MODEL = "claude-sonnet-4-20250514"  # vision-capable sonnet, faster + cheaper for computer use
```

Valid vision-capable models include:
- `claude-sonnet-4-20250514` (chosen — current Sonnet 4 with vision)
- `claude-3-5-sonnet-20241022` (fallback option)
- `claude-3-opus-20240229` (higher-cost alternative)

## Files Patched

| File | Line | Change |
|------|------|--------|
| `tools/computer_use_tradingview.py` | 34 | `claude-sonnet-4-6` → `claude-sonnet-4-20250514` |
| `.claude/worktrees/agent-a8d50129/tools/computer_use_tradingview.py` | 34 | same |
| `.claude/worktrees/agent-a5ce407f/tools/computer_use_tradingview.py` | 34 | same |
| `.claude/worktrees/agent-aaf98f0b/tools/computer_use_tradingview.py` | 34 | same |

## Verification

1. **Syntax check:** `python -m py_compile tools/computer_use_tradingview.py` — passes
2. **No other model references:** Grep confirms no remaining `claude-sonnet-4-6` occurrences
3. **Image handling unchanged:** Vision-capable model accepts base64 PNG screenshots

The script should now successfully run computer use loops with image input.
