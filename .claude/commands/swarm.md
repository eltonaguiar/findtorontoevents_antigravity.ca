---
description: Local agent swarm dispatcher. Subcommands: help|run|inspect|stats|sessions|engines|followup|resume
argument-hint: [help|run|inspect|stats|sessions|engines|followup|resume] [args...]
---

User invoked `/swarm $ARGUMENTS`.

Parse `$ARGUMENTS` and dispatch:

- **`help`** or **empty** → print usage card below.
- **`run <prompt-file> [engines]`** → run `python tools/swarm/swarm_run.py --prompt-file <prompt-file> --engines <engines or "deepseek,xai,kilo">`. Default max-parallel=4. Show the `_summary.json` ok-count + per-engine table. Then auto-run `python tools/swarm/swarm_inspect.py --latest` so the user sees response sizes + suspect flags.
- **`inspect [run_dir]`** → run `python tools/swarm/swarm_inspect.py [<run_dir> | --latest]` and print the table verbatim. Highlights ZERO/TINY/SHORT/PARSE_FAILED/CREDITS?/AUTH?/TUI_ONLY/TRUNCATED? flags.
- **`stats`** → run `python tools/swarm/swarm_stats.py` (per-engine call history).
- **`sessions [list|show <id>|expire]`** → run `python tools/swarm/session_manager.py <subcommand>`.
- **`engines`** → run `python tools/swarm/swarm_run.py --list-engines`.
- **`followup <yaml>`** → run `python tools/swarm/swarm_followup.py --config <yaml>`.
- **`resume <engine> <session-id> <prompt-file>`** → run `python tools/swarm/worker_runner.py --engine <engine> --prompt-file <prompt-file> --out-file swarm_runs/_resume/<engine>_<UTC>.json --from-session <session-id> --persist-session`, then echo response head + size.

After every subcommand that writes output to a run dir, ALWAYS auto-run `swarm_inspect.py --latest` (or against the new dir) so the user sees response-size + suspect flags. This is the no-surprise rule.

If `$ARGUMENTS` is empty or `help`, output:

```
/swarm — local multi-engine agent swarm

USAGE
  /swarm run <prompt-file> [engine,engine,...]    fan a prompt to engines
  /swarm inspect [run_dir]                        show response sizes + suspect flags
  /swarm stats                                    historical per-engine call stats
  /swarm sessions [list|show <id>|expire]         sqlite session sidecar
  /swarm engines                                  list supported engine names
  /swarm followup <yaml>                          multi-turn chain runner
  /swarm resume <eng> <sid> <prompt-file>         resume one engine from a session

ENGINES                10 alive
  API:  deepseek, xai, cerebras, inception, ollama_cloud
  CLI:  claude, gemini, kilo, opencode, copilot
  OFF:  codebuff (TUI + out of credits)
  removed 2026-05-04: freebuff (PTY/TUI-only, low usage)

KEY FILES
  tools/swarm/swarm_run.py             fan-out
  tools/swarm/swarm_followup.py        multi-turn
  tools/swarm/swarm_dispatch.ps1       PR-review pipeline
  tools/swarm/worker_runner.py         single-engine worker
  tools/swarm/swarm_inspect.py         per-run response audit
  tools/swarm/swarm_stats.py           historical engine health
  tools/swarm/session_manager.py       sqlite sessions
  tools/swarm/examples/*.yaml          configs

SAFETY
  Workers run with isolated env (only their own API keys visible).
  Read-only tool allowlist enforced via tools/swarm/safety.py.
  comment_poster.ps1 is the ONLY process with GitHub write permission.

DOCS
  tools/swarm/README.md  · SPEC.md  · PORTING.md  · SWARM_DESIGN_NOTES.md
```

Always show response sizes for any engine call so the user can detect dummy/empty/credit-exhausted output without reading the JSONs. Use `swarm_inspect.py` for this — never invent the numbers.

If the user passes an unrecognised subcommand, treat it as the prompt-file argument to `run`.
