---
name: consult-gemini
description: Get a second opinion from Google Gemini via its headless CLI. Use when the user says "/consult-gemini", "ask gemini", "gemini second opinion", or wants an outside model's take on a question, plan, or code.
---
# consult-gemini
Query Google Gemini for a second opinion, non-interactively.
## When to use
User asks "ask gemini" / "/consult-gemini" / second opinion from Gemini.
## The one command that works
`powershell -NoProfile -Command 'Set-Location $env:TEMP; gemini -p "PROMPT" --output-format json -y --skip-trust'`

Output is one JSON object; the answer is the `.response` field (Gemini puts the
model reply there; fall back to scanning the object if absent).
## Why each flag is mandatory
| Flag | Purpose |
|------|---------|
| `Set-Location $env:TEMP` (via PowerShell) | Runs the CLI from a clean temp directory outside any repository — prevents Gemini discovering repo-local `.gemini/` settings, `GEMINI.md`, rules, or MCP servers that pollute the second opinion or break headless mode. |
| `-p "PROMPT"` | Non-interactive prompt mode. Without it the CLI starts an interactive REPL instead of exiting after one reply. |
| `--output-format json` | Returns one machine-readable JSON object instead of TTY/streaming text, enabling reliable parsing. |
| `-y` (or `--approval-mode yolo`) | Auto-approves every tool call. Without an auto-approve flag the headless process blocks forever waiting for terminal confirmation. |
| `--skip-trust` | **Required.** Gemini refuses to run headless in an "untrusted directory" (even `$env:TEMP`) — it errors `Gemini CLI is not running in a trusted directory`. `--skip-trust` (or env `GEMINI_CLI_TRUST_WORKSPACE=true`) bypasses the trusted-folder gate. |
## Verify alive
`powershell -NoProfile -Command 'Set-Location $env:TEMP; gemini -p "reply with exactly: PONG" --output-format json -y --skip-trust'`
## Known issues
- **Trusted-directory gate** — without `--skip-trust` Gemini aborts before answering. Verified failure on this machine 2026-05-17.
- **Repo CWD pollution** — starting inside a git repo loads project settings/tools. `Set-Location $env:TEMP` is mandatory for an uncontaminated opinion.
- **Authentication required** — if the command returns an auth/permission error, the CLI was never logged in. Run `gemini` interactively once to complete login / API-key setup; subsequent headless calls succeed.
