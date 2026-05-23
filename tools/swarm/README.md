# tools/swarm — Local AI agent swarm

Kimi-style multi-engine reviewer / research swarm, driven by Claude Code.
One prompt fans out across CLI agents and direct-API consultants in
parallel; results are size-audited, schema-validated, optionally merged
and red-teamed, and (for the PR pipeline) y/N-gated before any GitHub
write.

This is the Claude-Code-driven counterpart to the parallel Kimi
[`ai-swarm`](https://github.com/MoonshotAI/Kimi-K2) implementation. Either
can drive the same engines, prompts, and JSON contract — and either can
be cherry-picked into a third repo. Running merge plan:
[`swarm_runs/KIMI_VS_OURS_MERGE_PLAN.md`](../../swarm_runs/KIMI_VS_OURS_MERGE_PLAN.md).

Read-only by default. Only [`comment_poster.ps1`](comment_poster.ps1) has
GitHub write access, and it gates each PR behind interactive `y/N`. Worker
subprocesses run with an env-isolated allowlist (see
[`safety.py`](safety.py)) so a leaked or compromised engine can't read
unrelated secrets.

---

## What this is

Three orthogonal use modes, all sharing the same worker adapter
([`worker_runner.py`](worker_runner.py)):

1. **One-shot fan-out** — single prompt, N engines, parallel.
   ([`swarm_run.py`](swarm_run.py))
2. **Multi-turn chain** — single engine, N turns, each building on the
   prior turn's session. ([`swarm_followup.py`](swarm_followup.py))
3. **PR review pipeline** — (PR x engine) fan-out → schema validate →
   merge-captain → fabrication-red-team → y/N posting.
   ([`swarm_dispatch.ps1`](swarm_dispatch.ps1) +
   [`comment_poster.ps1`](comment_poster.ps1))

Every worker call is timed and append-logged to
[`swarm_runs/_calls.jsonl`](../../swarm_runs/_calls.jsonl). Sessions can
optionally be persisted to a sqlite sidecar
([`swarm_runs/_sessions.db`](../../swarm_runs/_sessions.db)) for resume.

Build context:
[`swarm_runs/SESSION_SUMMARY.md`](../../swarm_runs/SESSION_SUMMARY.md).
Today's commit log: [`CHANGELOG.md`](CHANGELOG.md).

---

## Quickstart

> **After any run**, see [`POST_RUN_OPTIONS.md`](POST_RUN_OPTIONS.md) for
> the full menu of follow-ups (red-team, resume a dissenter, multi-turn
> deep-dive, persona switch, preset switch, cost cap, hooks). Every
> dispatcher also prints a terse `NEXT STEPS` reminder to stdout.

### One-shot fan-out (slash command)

```
/swarm run path/to/prompt.md
/swarm run path/to/prompt.md deepseek,xai,kilo
```

Equivalent direct call:

```
python tools/swarm/swarm_run.py --prompt-file prompt.md \
    --engines deepseek,xai,kilo --max-parallel 4
```

After the run completes, the slash command auto-runs
[`swarm_inspect.py --latest`](swarm_inspect.py) so per-engine response
sizes + suspect flags are visible without opening files.

### YAML config (named, reproducible)

```
python tools/swarm/swarm_run.py --config tools/swarm/examples/asset_class_audit.yaml
python tools/swarm/swarm_run.py --config tools/swarm/examples/multi_model_qa.yaml
```

YAML supports `${VAR}` / `${VAR:-default}` substitution (via
[`config_loader.load_config`](config_loader.py)) and a special `${TS}`
token that resolves to the run's UTC stamp. `.env` at repo root is
auto-loaded if present. Examples live in [`examples/`](examples/).

### Multi-turn chain (priming → analysis → critique → final)

```
python tools/swarm/swarm_followup.py \
    --config tools/swarm/examples/forex_deep_dive.yaml
```

The 4-turn chain re-uses the prior turn's session via
`worker_runner --from-session`, which auto-routes to claude `--resume`
(native), API JSONL replay, or MD-context fallback depending on the
engine. See `Sessions & resume` below.

### PR review pipeline

```
pwsh tools/swarm/swarm_dispatch.ps1 -Prs 669,676 -Engines claude,gemini,deepseek
pwsh tools/swarm/comment_poster.ps1 -RunDir swarm_runs/<TS> -DryRun
pwsh tools/swarm/comment_poster.ps1 -RunDir swarm_runs/<TS>     # interactive y/N
```

Auto-resume an earlier review pass for the same PRs:

```
pwsh tools/swarm/swarm_dispatch.ps1 -Prs 669,676 -Engines claude,deepseek -AutoResume
```

`-AutoResume` scans `swarm_runs/_sessions.db` for the most-recent active
(engine, PR) session in the last 72 h and reuses each one.

### Inspect any run

```
/swarm inspect                                  # latest
python tools/swarm/swarm_inspect.py --latest
python tools/swarm/swarm_inspect.py swarm_runs/<TS>
```

Prints a per-engine table: raw bytes, envelope bytes, suspect flags
(HEALTHY / TINY / ZERO / SHORT / CREDITS? / AUTH? / TUI_ONLY /
PARSE_FAILED / TRUNCATED?), and a 100-char preview. Exits non-zero if
any suspect engines exist — handy as a regression gate in CI.

### Historical engine health

```
python tools/swarm/swarm_stats.py
python tools/swarm/swarm_stats.py --since 2026-05-03 --json
```

---

## Engine matrix

Verified live against a 6.8 KB briefing on 2026-05-03 (see
[`swarm_runs/SESSION_SUMMARY.md`](../../swarm_runs/SESSION_SUMMARY.md)).
**13 alive engines** (kimi + openclaude + codex added 2026-05-03). The PTY/TUI engine `freebuff` was removed 2026-05-04 (low usage).

| Engine | Auth | Headless | Status | Caveats |
|---|---|---|---|---|
| `claude` | Anthropic OAuth (`claude /login`) | yes | LIVE | Read-only allow/deny lists baked in via [`safety.py`](safety.py); supports `--session-id`/`--resume` for native resume. |
| `gemini` | Google OAuth (`gemini auth login`) | yes | LIVE | Ignores in-prompt JSON contracts — pass `--json-strict` to wrap with the strict-JSON preamble. |
| `opencode` | OAuth (CLI login) | partial | LIVE | Windows arg quoting truncates long prompts; worker pipes via stdin instead. |
| `kilo` | OAuth (CLI login) | partial | LIVE | Same code path as opencode; same caveats. |
| `copilot` | GitHub OAuth (`gh auth login` + `gh extension install github/gh-copilot`) | yes | LIVE | Wraps responses with tool-call markup; [`output_parsers.parse_copilot`](output_parsers.py) strips it. |
| `agent` | Cursor OAuth (`cursor-agent login`) — optional `CURSOR_API_KEY` for CI | yes | LIVE | Cursor agent CLI; ships at `%LOCALAPPDATA%/cursor-agent/cursor-agent.cmd` (custom resolver in [`worker_runner._resolve_cursor_agent`](worker_runner.py)). Stdin pipe is broken — worker passes prompt as positional arg. JSON envelope `{type:result, result:..., session_id:...}`; `.result` is auto-extracted. `--force` (alias `--yolo`) is set so headless runs don't hang on tool-approval prompts. |
| `kimi` | Moonshot OAuth (`kimi login`; token under `~/.kimi/`) — optional `KIMI_API_KEY` / `MOONSHOT_API_KEY` for CI | yes | LIVE | Kimi CLI v1.23.0 (Moonshot AI). Ships bundled with the VS Code extension `moonshot-ai.kimi-code` at `%APPDATA%/Code/User/globalStorage/moonshot-ai.kimi-code/bin/kimi/kimi.exe` (custom resolver in [`worker_runner._resolve_kimi_cli`](worker_runner.py); checks `KIMI_CLI` override > VS Code path > `~/.vscode/extensions/moonshot-ai.kimi-code-*/` > PATH). Invoked with `--quiet -p <prompt>`; `--quiet` = `--print --output-format text --final-message-only`. `--print` implies `--yolo`, no approval prompts. Output is clean prose (no envelope), no parser needed. |
| `openclaude` | provider-dependent: `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY` / `GEMINI_API_KEY` / `GH_TOKEN` (whichever provider `--provider` selects) | yes | LIVE | Third-party Claude Code fork (`@gitlawb/openclaude` v0.7.0; source: [github.com/Gitlawb/openclaude](https://github.com/Gitlawb/openclaude)) with a `--provider` flag that routes to OpenAI / Gemini / DeepSeek / Anthropic / GitHub Models / Bedrock / Vertex / Foundry / Ollama. The swarm `--model` arg is mapped onto openclaude's `--provider`; `OPENCLAUDE_PROVIDER` env sets the default (falls back to `openai`). Uses `-p <prompt> --output-format json` envelope; `.result` and `.session_id` are auto-extracted. **Trust caveat**: third-party package; v0.7.0 audited 2026-05-03 (no postinstall/preinstall hooks, no `scripts/` shipped on disk, all standard Anthropic SDK + OSS deps). Re-audit before each upgrade. Cost estimate is APPROXIMATE — table uses gpt-4o-mini list price; routing to a pricier provider will under-estimate. |
| `codex` | OpenAI ChatGPT OAuth (`codex login`) — optional `OPENAI_API_KEY` for API-billed fallback | yes | LIVE | OpenAI Codex CLI (`@openai/codex` v0.128.0+); shim at `%APPDATA%/npm/codex.cmd`. Worker uses `codex exec --skip-git-repo-check --sandbox read-only --json -c approval_policy="never"` and parses JSONL events: `agent_message` items -> response text, `turn.completed.usage` -> token counts, `thread.started.thread_id` -> session id. Auto-runs filesystem probes by default (high input-token usage; observed 19K-930K in for short-vs-brief prompts); for minimal latency, prompt must explicitly forbid tool use. **KFM**: ChatGPT OAuth has a usage cap that surfaces as a JSONL `error` event + rc=1 — set `OPENAI_API_KEY` to fall back to API billing, or wait for the cap-reset timestamp in the error message. See [`SWARM_DESIGN_NOTES.md`](SWARM_DESIGN_NOTES.md) for both KFMs. |
| `deepseek` | `DEEPSEEK_API` env | yes | LIVE | OpenAI-compatible. |
| `cerebras` | `CEREBRAS_API` env | yes | LIVE | Needs `cerebras-cloud-sdk` pip pkg; uses `max_completion_tokens`. |
| `xai` | `X_AI_KEY` env (or `XAI_API_KEY`/`X_AI`/`GROK_SUPER`) | yes | LIVE | Grok 3 latest. |
| `inception` | `INCEPTION_AI_KEY` env | yes | LIVE | Use `mercury-2`; `mercury` is deprecated. |
| `ollama_cloud` | local `ollama signin` for cloud-tagged models | yes | LIVE | `OLLAMA_CLOUD_KEY` env is an SSH push key — NOT a chat token; adapter shells out to `ollama run gpt-oss:120b-cloud <prompt>`. |
| `openrouter` | `OPENROUTER` env (Bearer token) | yes | LIVE | OpenAI-compat HTTP gateway exposing 200+ models from many vendors. Default model: `openai/gpt-4o-mini` (cheap+fast). Override via `OPENROUTER_MODEL` env or `--model openai/gpt-4o-mini` / `anthropic/claude-haiku-4.5` / `x-ai/grok-2` / `meta-llama/llama-3.3-70b-instruct:free` etc. Sends `HTTP-Referer` + `X-Title` etiquette headers (rate-limit attribution + leaderboard). Cost-cap is APPROXIMATE for non-default models — see SPEC.md. |
| `nous` | `NOUS_API_KEY` env (or `NOUS_PORTAL_KEY` alias; Bearer token) | yes | LIVE | Nous Research Portal (Hermes API); OpenAI-compat. Verified live 2026-05-03 (2.2s latency, 649B response). Base URL `https://inference-api.nousresearch.com/v1/chat/completions`; default model `Hermes-4-70B` ($0.05/M in / $0.20/M out, 128K ctx); override via `NOUS_MODEL` env or `--model Hermes-4-405B` for deeper reasoning ($0.09/$0.37). Get key at https://portal.nousresearch.com/. |
| ~~`freebuff`~~ | OAuth (CLI login) | TUI-only | REMOVED | Removed 2026-05-04 — PTY engine, TUI-only, low usage. `pty_driver.py` and `_freebuff_test_ladder.py` deleted with this engine. |
| `codebuff` | n/a | n/a | EXCLUDED | Account out of credits, TUI-only. |

---

## Slash commands

All nine live under [`.claude/commands/swarm*.md`](../../.claude/commands/).

| Command | Action |
|---|---|
| `/swarm` or `/swarm help` | Print the usage card from [`.claude/commands/swarm.md`](../../.claude/commands/swarm.md). |
| `/swarm run <prompt-file> [engines]` | One-shot fan-out via [`swarm_run.py`](swarm_run.py), then auto-`inspect`. |
| `/swarm followup <yaml>` | Multi-turn chain via [`swarm_followup.py`](swarm_followup.py). |
| `/swarm inspect [run_dir]` | Per-engine response audit; defaults to `--latest`. |
| `/swarm stats` | Historical per-engine ok-rate / latency. |
| `/swarm sessions [list\|show <id>\|expire]` | sqlite session sidecar ops. |
| `/swarm engines` | Print supported engine names + which API keys are wired. |
| `/swarm resume <eng> <sid> <prompt-file>` | Resume one engine from a saved session id. |
| `/swarm-help` | Shortcut for the help card + `swarm_stats.py` summary. |
| `/swarm-invent <problem-file> [engine]` | Bootstrap custom personas + a test blueprint for a new problem domain. |

The slash-command contract lives in [`SPEC.md`](SPEC.md#slash-command-contract).

---

## Inventing personas for new problem domains

When the existing persona library doesn't cover the problem (touches 2+ orthogonal subsystems and no existing persona obviously fits), use [`invent_personas.py`](invent_personas.py) to ask a fast/cheap design engine (default: cerebras; falls back to inception, then claude) to design an orthogonal multi-specialist split + a test blueprint.

```
python tools/swarm/invent_personas.py --problem-file my_problem.md
```

The script writes one `.md` per persona to `agent_personas/`, a blueprint to `agent_personas/blueprints/<domain>_blueprint.md`, appends entries to `INDEX.md`, and prints the recommended `swarm_run.py` invocation. Defensive against clobbering: if a persona filename already exists it writes to `<name>.invented.md` and warns. Decision tree, meta-prompt schema, and worked examples: [`agent_personas/INVENT_PERSONAS_PROTOCOL.md`](agent_personas/INVENT_PERSONAS_PROTOCOL.md). Slash-command wrapper: `/swarm-invent`.

---

## File layout

Authoritative listing: [`MANIFEST.txt`](MANIFEST.txt). Quick orientation:

```
tools/swarm/
  worker_runner.py     api_consult.py
  swarm_run.py         swarm_followup.py  swarm_dispatch.ps1  comment_poster.ps1
  swarm_inspect.py     swarm_stats.py     swarm_log.py        swarm_janitor.py
  config_loader.py     output_parsers.py  safety.py           session_manager.py
  schema_validate.py   schema_review.json swarm.config.example.json
  README.md  SPEC.md  PORTING.md  CHANGELOG.md  SWARM_DESIGN_NOTES.md
  MANIFEST.txt  requirements.txt
  prompts/{pr_review,merge_reviews,redteam}.md
  fixtures/{good,bad}.json
  examples/{asset_class_audit,multi_model_qa,forex_deep_dive}.yaml
  agent_personas/{INDEX,bond,commodity,crypto,equity,etf,forex}_specialist.md

.claude/agents/    pr-reviewer.md  fabrication-red-team.md  merge-captain.md
                   dashboard-contract-reviewer.md *  quant-performance-auditor.md *
.claude/commands/  swarm.md + swarm-{help,run,followup,inspect,stats,sessions,engines,resume}.md

swarm_runs/        _calls.jsonl  _sessions.db  run_<TS>/  followup_<TS>/  <TS>/   (gitignored)

* = project-specific subagents; see PORTING.md for swap targets.
```

---

## Logging & stats

Every worker call appends one JSON line to
[`swarm_runs/_calls.jsonl`](../../swarm_runs/_calls.jsonl). Fields:
`ts_utc, engine, model, pr, prompt_bytes, output_bytes, latency_s,
returncode, ok, low_signal, error, run_dir, out_file`.

`low_signal` flips true if `output_bytes < 50` or `returncode != 0`.
`swarm_stats.py` aggregates by engine and raises:

- `LOW_OK_RATE` — ok rate < 50% over ≥ 2 calls.
- `ZOMBIE_OUTPUT` — low_signal rate ≥ 50% over ≥ 2 calls.
- `ERRORING` — error rate ≥ 50%.
- `UNUSED` — engine never logged a call.

[`swarm_inspect.py`](swarm_inspect.py) is the per-run companion. It reads
each `*.json` + `*.json.raw.txt` pair and tags each engine with one of:

| Flag | Meaning |
|---|---|
| `HEALTHY` | raw ≥ 1 KB and parses |
| `SHORT` | raw 200 B – 1 KB |
| `TINY` | raw < 200 B |
| `ZERO` | raw size 0 |
| `CREDITS?` | regex match for "out of credits" / "quota exceeded" / "rate limit" / "billing" |
| `AUTH?` | match for "401" / "403" / "unauthorized" / "invalid api key" |
| `PARSE_FAILED` | worker fell back to `verdict: COMMENT_ONLY` stub |
| `TRUNCATED?` | response ends mid-token without proper closure |

This is the no-surprise rule — every slash command that writes a run dir
auto-runs `swarm_inspect.py --latest` so dummy / empty / credit-exhausted
output is visible without opening JSONs. The taxonomy is documented in
[`SPEC.md`](SPEC.md#inspector-flag-taxonomy).

Together they caught the Inception wrong-model bug and the Ollama_Cloud
SSH-key-vs-chat-token bug during the build session. (Also caught freebuff's
silent long-prompt truncation; that engine was removed 2026-05-04.)

---

## Sessions & resume

Opt-in sqlite sidecar at
[`swarm_runs/_sessions.db`](../../swarm_runs/_sessions.db) persists
`(session_id × engine × prompt × message-log)` per worker invocation.
Pass `--persist-sessions` to [`swarm_run.py`](swarm_run.py) (or
`-PersistSessions` to [`swarm_dispatch.ps1`](swarm_dispatch.ps1)) to turn
it on. [`swarm_followup.py`](swarm_followup.py) always persists.

Three resume modes, in priority order:

1. **Native CLI session id** — claude `--resume <sid>` when available
   (cheapest, highest fidelity).
2. **JSONL replay** — for stateless API engines
   (deepseek/cerebras/xai/inception). The runner injects prior messages
   as a context preface.
3. **MD-context fallback** — newest-first, budget-greedy markdown
   preamble for CLI engines without native resume.

Auto-routing happens in
[`worker_runner.py:--from-session`](worker_runner.py); callers do not
need to know which mode applies.

Driver flags:

- `worker_runner.py --from-session <sid>` — resume from a sqlite session.
- `worker_runner.py --persist-session` — record this turn in the sqlite DB.
- `swarm_run.py --persist-sessions` — pre-allocate one fresh session per engine.
- `swarm_run.py --from-session-by-engine eng=sid,eng=sid` — resume a subset of
  engines while the rest start fresh. (Or set `from_session:` per-engine in YAML.)
- `swarm_dispatch.ps1 -FromSessionsByPr @{ <pr> = @{ <eng> = '<sid>' } }`
  — explicit map for PR pipeline.
- `swarm_dispatch.ps1 -AutoResume` — scan the DB for the most-recent
  (engine, PR) sessions in the last 72 h and reuse them.

Ops CLI: `python tools/swarm/session_manager.py {list,show,expire}`.
Janitor: `python tools/swarm/swarm_janitor.py [--hours 72] [--vacuum]`.

Detailed docs: [`SPEC.md` → Session Manager](SPEC.md#session-manager).

---

## Pointers

- [`SPEC.md`](SPEC.md) — architecture diagram, adapter contract, JSON
  schema, prompt-template contract, slash-command contract, inspector
  flag taxonomy, output parsers, session manager, multi-turn followup,
  resume routing.
- [`PORTING.md`](PORTING.md) — lift-and-shift adoption guide for another
  repo (file manifest, env vars, CLI tools, hardcoded path edits, 5-step
  guide, cross-repo rsync/robocopy one-liner).
- [`CHANGELOG.md`](CHANGELOG.md) — per-day commit log for swarm-related
  changes.
- [`SWARM_DESIGN_NOTES.md`](SWARM_DESIGN_NOTES.md) — internal notes
  (historical freebuff long-prompt strategy: single / fileref / chunked
  modes, empirical buffer-size findings — engine removed 2026-05-04).
- [`swarm.config.example.json`](swarm.config.example.json) — config
  template (engines / models / paths).
- [`examples/`](examples/) — three working YAML configs (audit fan-out,
  ad-hoc QA, FOREX deep-dive chain).
- [`agent_personas/INDEX.md`](agent_personas/INDEX.md) — six asset-class
  reviewer personas.
- [`swarm_runs/KIMI_VS_OURS_MERGE_PLAN.md`](../../swarm_runs/KIMI_VS_OURS_MERGE_PLAN.md)
  — running merge plan with the parallel Kimi swarm.
