---
name: consult-kilo
description: Get a second opinion from kilo (opencode fork) via its headless CLI. Use when the user says "/consult-kilo", "ask kilo", "kilo second opinion", or wants an outside model's take on a question, plan, or code.
---
# consult-kilo
Query kilo for a second opinion, non-interactively.
## When to use
User asks "ask kilo" / "/consult-kilo" / second opinion from Kilo.
## The one command that works
`powershell -NoProfile -Command 'Set-Location $env:TEMP; kilo run "PROMPT"'`

The model's reply is printed directly to stdout as plain text. The entire
trimmed stdout is the answer.
## Why each flag is mandatory
| Flag | Purpose |
|------|---------|
| `Set-Location $env:TEMP` (via PowerShell) | Runs the CLI from a clean temp directory outside any repository — prevents kilo discovering repo-local config / rules that pollute the opinion or break headless mode. |
| `run "PROMPT"` | One-shot headless execution: sends the message, receives the reply, prints to stdout, exits. |
## Verify alive
`powershell -NoProfile -Command 'Set-Location $env:TEMP; kilo run "reply with exactly: PONG"'`
## Known issues
- **Repo CWD pollution** — starting inside a git repo loads project config/tools. `Set-Location $env:TEMP` is mandatory for an uncontaminated opinion.
- **Authentication required** — if the command returns an auth/permission error, kilo has no model provider configured. Run `kilo` interactively once to set up a provider / API key; subsequent headless calls succeed.
- **May HANG with no output** — like its opencode parent, `kilo run` can block silently if no provider is configured. Run with a timeout (~120s). NOT yet verified working headless on this machine.
- kilo is an opencode fork — the `consult-opencode` skill is its twin.
