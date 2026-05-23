---
name: consult-grok
description: Get a second opinion from xAI Grok via its headless CLI (`grok -p`). Use when the user says "/consult-grok", "ask grok", "grok second opinion", or wants an outside model's take on a question, plan, or code.
---
# consult-grok
Query xAI Grok for a second opinion, non-interactively, via the Grok Build CLI.

## When to use
User says "ask grok" / "/consult-grok" / wants a second opinion from Grok.

## The one command that works
```
wsl bash -lc 'mkdir -p /tmp/grok-cwd && grok -p "PROMPT" --cwd /tmp/grok-cwd --output-format json'
```

Output is one JSON object; the answer is the **`.text`** field. `.thought` holds
the model's reasoning trace (usually skip it).

Verified working 2026-05-18 on this machine — grok 0.1.211, `/usr/local/bin/grok`
-> `/root/.grok/bin/grok`. Round-trip ~30-90s.

## Why each piece is mandatory
| Piece | Purpose |
|-------|---------|
| `wsl bash -lc '...'` | Grok lives in WSL. Invoking `wsl grok` **directly** inherits the Windows `%TEMP%` via WSLENV — Grok then fails with `Failed to set working directory to "C:/Users/.../Temp"`. A login shell (`bash -lc`) gives a clean POSIX env. |
| `mkdir -p /tmp/grok-cwd &&` | `--cwd` requires a directory that **already exists** — Grok does not create it. Joined with `&&`, not `;`. |
| `--cwd /tmp/grok-cwd` | A fixed temp dir **outside the repo**. Inside `findtorontoevents_antigravity.ca` the repo `.mcp.json` (Windows `E:/`/`C:/` paths + `uv`/redis) makes Grok print `Failed to spawn MCP server 'tradingview-desktop'` and return an empty body. `/tmp/grok-cwd` skips all project config. |
| `-p "PROMPT"` | Non-interactive single-shot mode. Without it the CLI opens an interactive REPL and never exits. |
| `--output-format json` | One machine-readable JSON object — the only reliably-parseable format. Answer is `.text`. |

## Hard gotcha — no command substitution
The Windows Bash-tool -> `wsl` quoting layer **silently eats `$(...)`**. Do NOT use
`mktemp -d` or `$(cat file)`:
```
wsl bash -lc 'D=$(mktemp -d); grok -p "..." --cwd "$D" ...'   # FAILS: $D empty
                                                              # -> "a value is required for '--cwd'"
```
Always use the **fixed literal** `/tmp/grok-cwd` with `mkdir -p`.

## Long / special-character prompts
Keep the prompt as a direct double-quoted arg. If it contains double quotes or
newlines, write it to a file with the Write tool first, then:
```
wsl bash -lc 'mkdir -p /tmp/grok-cwd && grok -p "$(cat /mnt/c/path/to/prompt.txt)" --cwd /tmp/grok-cwd --output-format json'
```
NOTE: `$(cat ...)` may be eaten by the quoting layer (see gotcha above). If the
file-substitution form returns `prompt is empty`, fall back to inlining the
prompt directly and escaping internal `"` as `\"`.

## Verify alive
```
wsl bash -lc 'mkdir -p /tmp/grok-cwd && grok -p "Reply with exactly the word: VERIFIED" --cwd /tmp/grok-cwd --output-format json'
```
Expect `{"text": "VERIFIED", "stopReason": "EndTurn", ...}`.

## Known issues
- **Repo CWD pollution / empty body** — running with a CWD inside the repo loads
  `.mcp.json`, Grok fails to spawn 4 non-portable MCP servers and returns empty.
  `--cwd /tmp/grok-cwd` is mandatory. Repo-root `.grok/config.toml` (gitignored)
  can also disable those MCP servers for Grok only.
- **`wsl grok` direct invocation** — inherits Windows `%TEMP%`; `--cwd` breaks.
  Always wrap in `wsl bash -lc '...'`.
- **`$(...)` substitution eaten** — the Windows -> wsl layer drops command
  substitution. Use the fixed `/tmp/grok-cwd` literal.
- **Auth** — if the call returns an auth error, Grok was never logged in. Run
  `wsl grok` interactively once to complete login (SuperGrok subscription).

## Related
- Memory: `reference-grok-headless`
- Sibling skills: consult-codex, consult-gemini, consult-kilo, consult-opencode, consult-cursor-agent
