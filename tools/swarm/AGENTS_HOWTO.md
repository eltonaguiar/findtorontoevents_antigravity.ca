# AGENTS_HOWTO — Using Our Swarm From Another AI Agent

**Purpose:** point other AI agents (Claude, Cursor, Copilot, GPT, Kimi, etc.) at the right files so they can drive our local agent swarm without trial-and-error.

If you are a human, you can also follow this — it's the canonical onboarding doc.

---

## TL;DR

Our swarm lives in `tools/swarm/`. It fans out one prompt across N AI engines in parallel, optionally cross-critiques across rounds, and synthesizes a single ranked output. 16 engines registered, 13+ live (depending on env keys + CLI auth). 7 agent personas + a multi-specialist debugging strategy.

To use it from another agent:

| Goal | Read | Then run |
|---|---|---|
| One-shot fan-out review of a prompt | `README.md` §Quickstart | `python tools/swarm/swarm_run.py --prompt-file p.md --engines deepseek,xai,nous,cerebras` |
| PR review with diff embedded | `swarm_dispatch.ps1` header | `pwsh tools/swarm/swarm_dispatch.ps1 -Prs N -Engines claude,gemini,deepseek` |
| Multi-turn deep-dive | `examples/forex_deep_dive.yaml` | `python tools/swarm/swarm_followup.py --config <yaml>` |
| Multi-specialist debug (race/dom/datetime) | `agent_personas/multi_specialist_debugging_strategy.md` | spawn 3 specialists in parallel + coordinator |
| Need novel personas for a new problem | `agent_personas/INVENT_PERSONAS_PROTOCOL.md` | `python tools/swarm/invent_personas.py --problem-file p.md` |
| Inspect what an engine returned | `README.md` §Inspect any run | `python tools/swarm/swarm_inspect.py --latest` |
| Engine health / drift over time | — | `python tools/swarm/swarm_stats.py` |

---

## Files to read first (in order, ~10 min total)

1. **`tools/swarm/README.md`** — engine matrix (which engines / auth / status / caveats), 4 use modes, all 9 slash commands. **Start here.**
2. **`tools/swarm/SPEC.md`** — JSON contract every engine response is validated against. Read if you're adding a new engine or worried about schema-fail rates.
3. **`tools/swarm/AGENTS_HOWTO.md`** — this file. Onboarding for non-Claude agents.
4. **`tools/swarm/agent_personas/INDEX.md`** — registry of personas. Mention persona name in `--persona <name>` to inject the persona's system prompt into a worker call.
5. **`tools/swarm/agent_personas/multi_specialist_debugging_strategy.md`** — when to fan out 3 specialists vs 1 general reviewer. Frontend bugs that touch click-handlers + dates + DOM should ALWAYS go through this pattern.
6. **`tools/swarm/agent_personas/INVENT_PERSONAS_PROTOCOL.md`** — how to bootstrap NEW personas + a test blueprint for a problem domain you don't have existing personas for.

If you're driving our swarm from an external agent, you only need the first three. The persona/strategy docs are for going deeper.

---

## Slash commands (Claude Code only)

`.claude/commands/swarm*.md` defines 9 slash commands. Other agents can invoke the underlying scripts directly — the slash commands are just convenience wrappers for Claude Code:

| Slash command | Underlying script |
|---|---|
| `/swarm` or `/swarm help` | print help card |
| `/swarm run <prompt-file>` | `python tools/swarm/swarm_run.py --prompt-file <p>` |
| `/swarm followup <yaml>` | `python tools/swarm/swarm_followup.py --config <y>` |
| `/swarm inspect [run_dir]` | `python tools/swarm/swarm_inspect.py --latest` |
| `/swarm stats` | `python tools/swarm/swarm_stats.py` |
| `/swarm engines` | `python tools/swarm/swarm_run.py --list-engines && python tools/swarm/config_loader.py` |
| `/swarm sessions` | `python tools/swarm/session_manager.py list` |
| `/swarm resume <eng> <sid> <prompt>` | `python tools/swarm/worker_runner.py --engine <e> --from-session <sid> --prompt-file <p>` |
| `/swarm-help` | combined help + stats summary |

**New (2026-05-04):** `/swarm-invent <problem.md>` — bootstrap personas + test blueprint for a new problem (see `INVENT_PERSONAS_PROTOCOL.md`).

---

## How to drive the swarm from your own code

**Python (recommended):**
```python
import subprocess, json
subprocess.run([
    "python", "tools/swarm/swarm_run.py",
    "--prompt-file", "my_prompt.md",
    "--engines", "deepseek,xai,nous,cerebras,kimi",
    "--max-parallel", "5",
], check=True)
# Outputs land in swarm_runs/run_<UTC>/<engine>.json
# Plus _summary.json with cost + per-engine bytes
```

**PowerShell (PR review pipeline):**
```powershell
pwsh tools/swarm/swarm_dispatch.ps1 -Prs 745,746 -Engines claude,deepseek,xai
pwsh tools/swarm/comment_poster.ps1 -RunDir swarm_runs/<TS>  # interactive y/N
```

**One-engine direct (skip schema validation):**
```bash
set -a; source .env; set +a
python tools/swarm/api_consult.py --provider deepseek --prompt-file p.md
```

---

## Live engines as of 2026-05-04

**Env-keyed (in `.env`):**
- ✅ `deepseek` (deepseek-chat)
- ✅ `cerebras` (default)
- ✅ `xai` (grok-3-latest)
- ✅ `inception` (mercury-2)
- ✅ `nous` (Hermes-4-70B; flaky — empty completions occasionally)
- ✅ `ollama_cloud` (gpt-oss:120b-cloud)
- ✅ `openrouter` (gpt-4o-mini default; `--model openai/gpt-4o-mini` etc.)
- ✅ `anthropic` (for openclaude routing only)

**CLI / OAuth:**
- ✅ `claude` (Claude Sonnet 4.6 — Claude Code itself)
- ✅ `opencode` (qwen-3-235b)
- ✅ `kilo` / `kilocode` (Grok-Code-Fast)
- ✅ `copilot` (npm/copilot — GPT-5.4)
- ✅ `kimi` (Moonshot Kimi v1.41.0)
- ✅ `agent` (Cursor agent — Composer)
- ⚠️ `codex` (`codex` CLI v0.128.0 — quota until 2026-05-05)
- ❌ `openclaude` (MCP schema crash; needs config fix)
- ~~`freebuff`~~ (PTY engine; **removed 2026-05-04** — TUI-only, low usage)

`python tools/swarm/config_loader.py` shows current OK/MISS for env-keyed.

---

## Naming convention for run artifacts

Every run lands in `swarm_runs/run_<UTC-stamp>/`:
- `<engine>.json` — schema-validated wrapper
- `<engine>.json.raw.txt` — raw model output before validation
- `_summary.json` — per-engine bytes / latency / transport_status

Persistent session sidecar (resumable conversations): `swarm_runs/_sessions.db` (sqlite).

Append-only call log: `swarm_runs/_calls.jsonl`.

---

## Pointing OTHER agents (not Claude) at this

Tell them: **"Read `tools/swarm/AGENTS_HOWTO.md` and `tools/swarm/README.md`. The swarm dispatcher is `python tools/swarm/swarm_run.py`. Engine list: see `--list-engines`. Auth status: see `python tools/swarm/config_loader.py`."**

For Copilot Cloud / GitHub Actions / Cursor agent etc., that's enough.

---

## Known landmines (from session 2026-05-04 postmortem)

1. **Static-only review misses runtime bugs.** The swarm validated PRs #746-#748 as "looks good" but missed the synthetic-click swallow Kimi found by running live jsdom tests. **For runtime/UI bugs, demand live verification (Playwright trace, jsdom test) — not just diff review.** See `reports/swarm_process_postmortem_2026_05_04.md`.

2. **Anchoring bias when prompts come from previous round.** If you embed an earlier diagnosis in a new prompt, all engines converge on it. Run a parallel red-team prompt with no patch context to disagree. See `multi_specialist_debugging_strategy.md` §"What NOT to do".

3. **Cross-critique catches fabrications.** Round-2 of a 3-round protocol consistently flags 5-10 false claims (line numbers, function names that don't exist) per PR. Don't skip round 2.

4. **CLI engines on Windows.** `kimi` and `kilo` can choke on long prompts due to Windows arg-length limits — fall back to `ollama_cloud` or pipe via stdin.

5. **`nous` is flaky.** Empty completions ~10-15% of calls (HTTP 200, content="" — observability fix in `api_consult.py:258`). Set `--retries 2` for nous-only runs.

---

🤖 Maintained by the swarm. If you (the next agent) think any of this is wrong, append a section below — don't delete.
