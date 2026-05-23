---
name: tv-eval-bridge
description: Execute complex JavaScript on TradingView Desktop reliably — the fix for "ui eval / ui_evaluate quoting errors", "PowerShell mangles my JS", "SyntaxError missing ) after argument list", and the habit of asking a human to paste commands. Use whenever a TV automation step needs more than a trivial one-liner. Aliases - tv-quoting-fix, tv-ui-eval, tv-bridge, stop-asking-human.
---

# tv-eval-bridge — run complex JS on TradingView without quoting hell

> **MCP server:** [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp) — the `mcp__tradingview-desktop__*` tool family.

If you are fighting "the PowerShell bridge mangles my JS", getting
`SyntaxError: missing ) after argument list`, writing temp `.ps1` files to
sneak JS through, or **asking a human to paste commands** — stop. This skill
is the fix. The problem is never the JS or TradingView. It is the shell
quoting layer. There are exactly two correct ways to run JS on TV, and a
human-paste relay is not one of them.

## Rule 0 — you execute it, not a human

If you can emit a `ui_evaluate` / `ui eval` call at all, you HAVE a working
execution channel. Asking a human to copy-paste your commands is a failure
mode, not a workaround. The human is not your terminal. Self-execute every
time. If a trivial command (click a button) works but a complex one fails,
the channel is fine — only your *payload encoding* is wrong. Fix the encoding
(below); do not escalate to a human.

## Method 1 — call the MCP tool directly (preferred, zero quoting)

The `tradingview-desktop` MCP exposes `ui_evaluate`. Call it as a **native
tool call**. The JavaScript goes in the `expression` parameter as a normal
JSON string — the agent harness serializes it. There is **no shell, no
PowerShell, no escaping, no temp file**:

```
mcp__tradingview-desktop__ui_evaluate(expression="<any JS, any length, newlines fine>")
```

If you have been *quoting* `ui_evaluate` in messages or docs, the tool is in
your toolset — invoke it directly. Do NOT shell out to a CLI wrapper that
then runs it. The CLI/PowerShell path is the ONLY path that has quoting pain.

## Method 2 — base64 the JS (when you only have a shell)

If the only channel is a CLI (`node src/cli/index.js ui eval ...`), never
pass multi-line JS as a quoted argument — newlines and nested quotes get
mangled. Instead **base64-encode the JS once** so the payload becomes a
single flat token with no quotes, no newlines, no special characters:

1. Minify the JS to one line (it does not have to be pretty).
2. Base64-encode that string → `B64`.
3. The command becomes exactly:

```
<cli> ui eval "eval(atob('B64'))"
```

The outer **double** quotes wrap `eval(atob('...'))`; the inner **single**
quotes wrap the base64. Base64 output is `[A-Za-z0-9+/=]` only — it contains
no quote characters, so nothing collides and the shell has nothing to mangle.

Encoder (any language, run once per JS payload):

```python
import base64; print(base64.b64encode(JS.encode()).decode())
```
```bash
printf '%s' "$JS" | base64 -w0
```
```powershell
[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($js))
```

Every complex `ui eval` — toggle clicks, native-setter price fills, table
reads — gets the same treatment: encode once, send as `eval(atob('B64'))`.

## Anti-patterns (these are why you are stuck)

| Symptom | Cause | Fix |
|---|---|---|
| `SyntaxError: missing ) after argument list` | multi-line JS passed as a quoted shell arg | Method 2 (base64) or Method 1 |
| "PowerShell quoting pain", escaping `\"` everywhere | nested double/single quotes in the payload | base64 has no quotes — collision gone |
| Writing temp `.ps1` files to run JS | working around quoting the hard way | base64 one-liner needs no temp file; or use Method 1 |
| Asking a human to paste / "run this block" | treating the human as your terminal | Rule 0 — self-execute |
| Trivial click works, complex eval fails | payload encoding, not the channel | the channel is fine — encode the payload |

## Verify the channel once

`mcp__tradingview-desktop__tv_health_check` → `cdp_connected:true` means the
channel works. If it is true and a command still fails, it is 100% payload
encoding — apply Method 1 or 2. Do not relaunch TV, do not involve a human.

## Companion skills

- `/tv-protect-position` — attach TP/SL to an open position (uses this skill's encoding)
- `/tv-paper-trade` — full placement flow
- `/tv-debug` — TV failure-mode matrix
