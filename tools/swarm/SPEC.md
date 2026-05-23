# tools/swarm — Architecture & Data Contracts

Reference companion to [`README.md`](README.md). Read this before adding a
new engine, changing the JSON shape, or porting to another repo.

## Architecture

```
                       +-------------------------------+
                       |  swarm_dispatch.ps1           |
                       |  (orchestrator / fan-out)     |
                       |   for each (pr x engine):     |
                       |     Start-Job python worker   |
                       +---------------+---------------+
                                       |
              +----------+----------+--+--+----------+----------+
              |          |          |     |          |          |
              v          v          v     v          v          v
         +--------+  +--------+  +-----+  +-----+  +-----+  +-----+
         | claude |  | gemini |  | xai |  |dseek|  | ... |  | ... |    <-- worker_runner.py
         +---+----+  +---+----+  +--+--+  +--+--+  +--+--+  +--+--+
             |           |          |        |        |        |
             |       (CLI shells)   |     (api_consult.py for API engines)
             |           |          |        |        |        |
             v           v          v        v        v        v
         pr_<n>.<engine>.json      +     pr_<n>.<engine>.json.raw.txt
                  |
                  v
         +-------------------------+
         | schema_validate.py      |   per-output gate; non-zero exit => exclude
         | schema_review.json      |
         +-----------+-------------+
                     |
                     v   (valid outputs only)
         +-------------------------+
         | merge-captain pass      |   another worker call, claude opus
         | prompt: merge_reviews   |   input: concatenated valid JSONs
         +-----------+-------------+
                     v
              final_merge_plan.json
                     |
                     v
         +-------------------------+
         | fabrication red-team    |   another worker call, claude opus
         | prompt: redteam.md      |   input: final_merge_plan.json
         +-----------+-------------+
                     v
                redteam.json
                     |
                     v
         +-------------------------+
         | comment_poster.ps1      |   ONLY writer; y/N gate per PR
         | gh pr comment           |
         +-------------------------+

         every worker call -> swarm_log.CallTimer -> swarm_runs/_calls.jsonl
                                                         |
                                                         v
                                                  swarm_stats.py
                                                  (LOW_OK_RATE / ZOMBIE / ERRORING)
```

## Engine adapter contract — `worker_runner.py`

One worker invocation = one engine × one prompt × one output file.

CLI signature (stable):

```
python tools/swarm/worker_runner.py
  --engine     <claude|gemini|opencode|kilo|copilot|agent|kimi|openclaude|deepseek|cerebras|xai|inception|ollama_cloud|openrouter>
  --prompt-file <path/to/prompt.md>
  --out-file   <swarm_runs/.../pr_<n>.<engine>.json>
  [--pr        <int>]               # interpolated as {{PR_NUMBER}} in prompt
  [--model     <engine-specific>]
  [--session-id <uuid>]             # claude only — start a named session
  [--resume    <uuid>]              # claude only — resume a session
  [--context-md <path>]             # prepend prior context as a preamble
```

Behavior:

1. Read prompt; replace `{{PR_NUMBER}}` if `--pr` given; prepend context if
   any.
2. Dispatch to the engine's adapter function:
   - CLI engines: resolve `<name>.cmd`/`<name>.ps1` from `%APPDATA%/npm`,
     fall back to PATH; run via `subprocess.run(text=True, encoding=utf-8)`.
     - **opencode / kilo**: prompt MUST be piped on stdin (`stdin_data=prompt`),
       NOT passed as `-p` or positional arg. Windows arg-quoting truncates
       multi-line input past the first newline, so a 6.8 KB asset-class
       brief was silently clipped to 1.2 KB on 2026-05-03 before this fix.
       Adapter command: `<bin> run [--model <m>]` with prompt on stdin.
       **Model caveat:** opencode's default model (groq llama-4-scout) raises
       `Failed to call a function. Please adjust your prompt.` on long briefs
       (>~5 KB) — the CLI returns rc=0 but emits 0 bytes. Long-prompt swarm
       runs MUST pass a more capable model, e.g.
       `--model github-copilot/claude-haiku-4.5` or
       `github-copilot/claude-sonnet-4.6`. Verified 2026-05-03: 29 KB
       coherent response with claude-haiku-4.5 on the same 6.8 KB brief.
     - **claude / gemini / copilot**: short single-line prompts work via
       `-p`; long prompts could hit the same Windows quoting issue if ever
       exercised — mitigation today is that those CLIs accept stdin too.
   - API engines: shell out to `python tools/swarm/api_consult.py --provider
     <name> -` with prompt on stdin.
3. Wrap the call in `CallTimer` so latency / bytes / rc are logged to
   `swarm_runs/_calls.jsonl`.
4. Write raw response to `<out-file>.raw.txt` (always, even on error).
5. Try to extract a JSON object from the raw text (strip code fences,
   bracket-scan as fallback). If extraction fails, synthesize a
   `verdict: "COMMENT_ONLY"` / `confidence: "LOW"` envelope referencing the
   raw sidecar so downstream stages still get schema-valid input.
6. Inject `_swarm_meta = {raw_path, engine, ts, session_id}` and write
   `<out-file>`.
7. Print `<out-file>` on stdout; exit 0 on success.

Exit codes:
- `0` — JSON written (may be the synthesized fallback envelope).
- `2` — unknown engine.
- `4` — subprocess timeout.
- `5` — adapter raised.

## JSON schemas

Worker output JSON (canonical schema:
[`schema_review.json`](schema_review.json)):

```json
{
  "pr": 669,
  "engine": "claude-sonnet",
  "verdict": "MERGE | HOLD | REQUEST_CHANGES | COMMENT_ONLY",
  "confidence": "LOW | MEDIUM | HIGH",
  "summary": "one paragraph",
  "strengths": [
    {"claim": "...", "evidence": "path:line or command output"}
  ],
  "concerns": [
    {
      "severity": "blocking | major | minor | question",
      "claim": "...",
      "evidence": "path:line or command output (REQUIRED for blocking/major)",
      "requested_fix": "..."
    }
  ],
  "commentary_text": "Markdown comment suitable to post on the PR",
  "fabrication_risk": {"level": "LOW | MEDIUM | HIGH", "notes": "..."},
  "_swarm_meta": {
    "raw_path": "swarm_runs/<TS>/pr_669.claude.json.raw.txt",
    "engine": "claude",
    "ts": "20260503T132558Z",
    "session_id": "..."
  }
}
```

Hard rules enforced by [`schema_validate.py`](schema_validate.py):
- `concerns[*].severity == "blocking"` or `"major"` requires non-empty
  `evidence`.
- `strengths[*]` requires non-empty `evidence`.
- Enum fields rejected on typo.

Merge-captain output: see [`prompts/merge_reviews.md`](prompts/merge_reviews.md).
Red-team output: see [`prompts/redteam.md`](prompts/redteam.md).
Fixtures: [`fixtures/good.json`](fixtures/good.json) (schema-valid),
[`fixtures/bad.json`](fixtures/bad.json) (schema-invalid).

## Logging schema — `swarm_runs/_calls.jsonl`

One JSON object per line. Append-only; thread-safe via module-level lock in
[`swarm_log.py`](swarm_log.py).

```json
{
  "ts_utc": "2026-05-03T13:26:34Z",
  "engine": "deepseek",
  "model": "deepseek-chat",
  "pr": 669,
  "prompt_bytes": 6826,
  "output_bytes": 7292,
  "latency_s": 28.95,
  "returncode": 0,
  "ok": true,
  "low_signal": false,
  "error": "",
  "run_dir": "swarm_runs/20260503T132558Z",
  "out_file": "swarm_runs/20260503T132558Z/pr_669.deepseek.json",
  "retry_count": 0,
  "model_fingerprint": "deepseek-chat-v3-0324",
  "tokens_in": 1612,
  "tokens_out": 423,
  "transport_status": "200"
}
```

`ok = (returncode == 0 and output_bytes >= 50)`.
`low_signal = (output_bytes < 50 or returncode != 0)`.

### Audit-trail completeness fields (imp-B, post-2026-05-03)

Each row now also carries:

- **`retry_count`** — number of retries before this attempt landed (`0` on
  first try). Surfaces "silent retry success" (original 504 + retry 200 used
  to look like `ok=true`).
- **`model_fingerprint`** — the model id echoed by the API (e.g. `data.model`
  on OpenAI-compat responses; SDK `resp.model` on cerebras). Catches
  **self-spoofing** — a router silently downgrading to a smaller model than
  `--model` requested.
- **`tokens_in`** / **`tokens_out`** — `prompt_tokens` / `completion_tokens`
  from the API `usage` object. `0` when the engine doesn't expose it (CLI
  engines, ollama_cloud). Catches **prompt-truncation hallucinations** — the
  engine claims to have read 6 KB but `tokens_in=200` means the briefing hit
  a context cap.
- **`transport_status`** — HTTP status code as a string for API engines
  (`"200"`, `"504"`); `"ok"`, `"timeout"`, `"closed-by-peer"`, or `"rc=<n>"`
  for CLI engines. Distinguishes "engine refused" vs "engine answered but
  transport dropped output" vs "engine timed out" — the kilo silent-failure
  symptom from the 2026-05-03 self-review run is now classified, not
  invisible.

Backward compat: rows logged before imp-B omit these fields. Readers
(`swarm_stats.py`, `swarm_inspect.py`) treat missing keys as `""` / `0` and
suppress the new columns when no record carries them.

`swarm_stats.py` aggregates by engine and raises flags described in
[`README.md`](README.md#logging--stats).

## Prompt template contract

Files in [`prompts/`](prompts/):

- [`pr_review.md`](prompts/pr_review.md) — per-PR review. Uses
  `{{PR_NUMBER}}` token; the worker substitutes via `--pr`. Required clause:
  every claim in `strengths`/`concerns` must be diff-, source-, test-, or
  dashboard-data-backed, OR explicitly `severity: "question"`. The worker
  appends nothing — the prompt is used verbatim.
- [`merge_reviews.md`](prompts/merge_reviews.md) — merge-captain. Concerns
  dropped unless they have evidence OR ≥ 2 corroborating engines.
  Blocking/major without evidence → demoted to `question`.
- [`redteam.md`](prompts/redteam.md) — fabrication red-team. Each concern
  marked `confirmed | refuted | unverified` with `final_severity`.

When you add a new prompt:
1. Use `{{PR_NUMBER}}` only (do not invent more tokens unless you also
   extend `worker_runner._read_prompt`).
2. Demand JSON-only output, no prose / no fences.
3. Anti-hallucination clause: every blocking/major claim must cite
   evidence; speculative claims must use `severity: "question"`.

## Subagent spec — `.claude/agents/*.md`

Claude Code reads these as named subagents (`/agents`, `Task` tool).
Frontmatter is YAML; body is the system prompt.

```yaml
---
name: pr-reviewer
description: <one-line>
tools:
  - Bash         # gh / git / grep
  - Read
  - Grep
  - Glob
model: sonnet | opus
---
<system prompt body>
```

Existing personas:
- [`pr-reviewer.md`](../../.claude/agents/pr-reviewer.md) — read-only PR reviewer; produces `schema_review.json`-shaped output.
- [`fabrication-red-team.md`](../../.claude/agents/fabrication-red-team.md) — refutes claims; opus.
- [`merge-captain.md`](../../.claude/agents/merge-captain.md) — consolidates engines; opus, Read-only.
- [`dashboard-contract-reviewer.md`](../../.claude/agents/dashboard-contract-reviewer.md) — frontend / backend payload-key contract checker (project-specific).
- [`quant-performance-auditor.md`](../../.claude/agents/quant-performance-auditor.md) — enforces charter tier floors against `audit_dashboard/data/dashboard_data.json` (project-specific).

The last two reference project-specific paths and are intentionally
non-portable — see [`PORTING.md`](PORTING.md) for swap targets.

## Permission model

Read-only by default everywhere except [`comment_poster.ps1`](comment_poster.ps1).

`worker_runner.py` (claude path) hardcodes:

- Allowed: `Bash(gh pr view:*)`, `Bash(gh pr diff:*)`, `Bash(gh pr checks:*)`,
  `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(grep:*)`, `Bash(rg:*)`,
  `Read`, `Grep`, `Glob`.
- Disallowed: `Edit`, `Bash(git push:*)`, `Bash(gh pr merge:*)`,
  `Bash(gh pr comment:*)`, `Bash(gh pr review:*)`, `Bash(gh pr edit:*)`.

Other CLIs (gemini/opencode/kilo/copilot) inherit their own user defaults;
they do not get an allowlist baked in by the worker — keep their config
read-only.

`comment_poster.ps1` is the only process that runs `gh pr comment`. It
prints the synthesized body, prompts `y/N` per PR, writes the body to a
temp file, calls `gh pr comment <pr> --body-file <tmp>`, and removes the
temp file in `finally`. `-DryRun` skips the prompt and the post.

## Session Manager

[`session_manager.py`](session_manager.py) is an opt-in sqlite sidecar at
`swarm_runs/_sessions.db` that persists a (session_id × engine × prompt ×
message-log) record per worker invocation. It is **not** auto-enabled; pass
`--persist-sessions` to [`swarm_run.py`](swarm_run.py) to turn it on.

### Schema

```sql
CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY,
  engine TEXT NOT NULL,
  model TEXT,
  created_utc TEXT NOT NULL,           -- "YYYY-MM-DDTHH:MM:SSZ"
  last_used_utc TEXT NOT NULL,
  prompt_bytes INTEGER,
  prompt_sha256 TEXT,
  cli_session_id TEXT,                 -- engine-native id if any (claude, etc.)
  status TEXT,                         -- active | done | error | expired
  metadata_json TEXT
);
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL REFERENCES sessions(session_id),
  ts_utc TEXT NOT NULL,
  role TEXT NOT NULL,                  -- user | assistant | system | tool
  content TEXT NOT NULL,
  output_bytes INTEGER DEFAULT 0,
  latency_s REAL DEFAULT 0.0
);
CREATE INDEX idx_engine_status ON sessions(engine, status);
CREATE INDEX idx_session_msgs   ON messages(session_id, id);
```

WAL is enabled (`PRAGMA journal_mode=WAL`) so concurrent fan-out workers can
write without contention. Tables are created lazily on first call —
`init_db()` is idempotent.

### Three follow-up modes

The session is the source-of-truth for the next turn. Three resume paths,
in priority order:

1. **Native CLI session id** — when an engine returns a real session
   handle (today: `claude` via `--resume`, recorded under
   `_swarm_meta.session_id` by [`worker_runner.py`](worker_runner.py) and
   copied into `sessions.cli_session_id` post-run), pass it back via
   `worker_runner --resume <cli_session_id>`. Cheapest, highest fidelity.

2. **JSONL replay** (stateless API engines) — call
   `replay_messages(session_id)` to get
   `[{"role": "user|assistant", "content": "..."}, ...]` in chronological
   order. Suitable as the `messages=[...]` argument to OpenAI-shaped APIs
   (deepseek/cerebras/xai/inception). Use this for any engine without a
   native session id.

3. **MD-context fallback** — `render_md_context(session_id, max_chars=4000)`
   compresses prior messages into a Markdown preamble (newest-first
   budget-greedy with per-block soft cap). Pipe its output into a temp file
   and pass `worker_runner --context-md <path>` for engines that have
   neither session id nor `messages=` support (CLI engines without resume).

### Ops CLI

```
python tools/swarm/session_manager.py list [--engine X] [--since-hours 24] [--json]
python tools/swarm/session_manager.py show <session_id>
python tools/swarm/session_manager.py expire [--hours 72]
```

`list --json` emits a JSON array (utf-8 stdout) with `metadata_json` parsed
into a dict; consumed by `swarm_dispatch.ps1 -AutoResume` to map sessions
back to PRs without a per-row `show` round-trip.

`expire` flips `status='active' → 'expired'` for sessions whose
`last_used_utc` is older than `--hours` (default 72). Run as a cron/janitor
to keep the DB lean — schedule
[`swarm_janitor.py`](swarm_janitor.py) via cron / GHA if the DB grows past
~10 MB:

```
python tools/swarm/swarm_janitor.py --hours 72 --vacuum
# Expired 3 session(s) older than 72h. Reclaimed 12 KB.
```

### YAML config

[`swarm_run.py`](swarm_run.py) accepts a `--config <path>.yaml` alternative
to `--prompt-file`/`--engines`. Loaded via
[`config_loader.load_config()`](config_loader.py) so `${VAR}` /
`${VAR:-default}` substitution works; `${TS}` is also resolved to the
current UTC stamp. Examples in
[`examples/asset_class_audit.yaml`](examples/asset_class_audit.yaml) and
[`examples/multi_model_qa.yaml`](examples/multi_model_qa.yaml).

## Resuming a fan-out (`--from-session-by-engine`)

[`swarm_run.py`](swarm_run.py) supports resuming specific engines from a
prior session while keeping the rest fresh. Two ways to drive it:

1. **CLI flag** — comma-separated `ENGINE=SESSION_ID` pairs:

   ```
   python tools/swarm/swarm_run.py --prompt-file q2.md --engines deepseek,xai \
       --from-session-by-engine deepseek=a3ca27a7-8aad-4e4b-a1cb-a45cf623bd63
   # deepseek resumes; xai starts fresh.
   ```

2. **YAML field** per engine:

   ```yaml
   engines:
     - name: deepseek
       from_session: a3ca27a7-8aad-4e4b-a1cb-a45cf623bd63
     - name: xai
   ```

Behaviour:

- For each `(engine, session_id)` pair, the worker subprocess is invoked
  with `--from-session <session_id>`, which auto-routes via the three
  follow-up modes documented in *Session Manager* above (claude native
  resume / API JSONL replay / MD-context fallback).
- Resumed engines auto-set `--persist-session` so the chain can keep
  growing on the same `session_id`. Fresh engines (not in the map) only
  pre-allocate a new session if `--persist-sessions` is also passed.
- The CLI map wins over the YAML field on conflict.
- Stale map entries (engine not in the run) print a warning and are
  ignored.
- The resume map is recorded in `<out-dir>/_summary.json` under
  `from_session_by_engine`.

## Multi-turn followup ([`swarm_followup.py`](swarm_followup.py))

Where [`swarm_run.py`](swarm_run.py) is a parallel **fan-out** (one prompt
across N engines), [`swarm_followup.py`](swarm_followup.py) is a sequential
**chain** (one engine, N turns, each building on the prior turn's session).
Use it for priming -> analysis -> critique -> final flows where you want a
single engine to refine its own work.

### YAML shape

```yaml
name: forex-deep-dive
engine: deepseek                  # single engine for the whole chain
model: deepseek-chat              # optional
out_dir: swarm_runs/followup_${TS}
pr: 669                           # optional, applied to every turn
json_strict: false                # optional fleet default
turns:
  - name: priming
    prompt_file: prompts/forex_priming.md
  - name: analysis
    prompt: |
      Now analyze the FOREX class against the data you just summarised.
  - name: critique
    prompt: |
      Critique your own analysis. What's the weakest claim?
  - name: final
    prompt: |
      Final JSON answer per the original contract.
    capture_to: final.json     # optional — copies turn output to a stable name
```

A turn must specify exactly **one** of `prompt:` (inline) or
`prompt_file:` (path). Inline prompts get written to a sidecar
(`<out_dir>/_turn_<N>_<name>_prompt.md`) so the worker — which only reads
`--prompt-file` — can consume them.

### Session chaining

Turn 1 starts a fresh session (worker auto-persists because the chain
runner always passes `--persist-session`). After each turn, the runner
reads the worker's output `_swarm_meta.session_id_db` and passes that as
`--from-session` to the next turn. The shared session id surfaces in
`<out_dir>/_chain_summary.json` as `chain_session_id`.

If a turn fails to persist a session id (e.g. worker crashed), the chain
stops with a clear stderr message rather than silently re-priming on a
missing context.

### Outputs

Under `out_dir`:

- `turn_<N>_<name>.json` + `turn_<N>_<name>.json.raw.txt` — per turn.
- `_turn_<N>_<name>_prompt.md` — only for turns that used inline `prompt:`.
- `<capture_to>` — optional alias copies (e.g. `final.json`).
- `_chain_summary.json` — `{engine, model, out_dir, chain_session_id,
  turns: [...], ok_count, total}`.

### CLI

```
python tools/swarm/swarm_followup.py --config tools/swarm/examples/forex_deep_dive.yaml
```

See [`examples/forex_deep_dive.yaml`](examples/forex_deep_dive.yaml) for a
real 4-turn chain that re-uses the asset-class audit briefing.

## Engine adapter matrix

Single source of truth for which engines exist, how they're authed, how
the worker invokes them, and what to watch out for. Keep this in sync
with [`worker_runner.py`](worker_runner.py)'s dispatch table and
[`safety.py::ENGINE_REQUIRED_KEYS`](safety.py).

| Engine | Kind | Auth | Worker invocation | Caveats |
|---|---|---|---|---|
| `claude` | CLI | Anthropic OAuth | `claude -p <prompt> --output-format json --max-turns 12 --permission-mode default --allowedTools ... --disallowedTools ...` | Read-only allow/deny lists from [`safety.py`](safety.py); supports `--session-id`/`--resume` for native resume. |
| `gemini` | CLI | Google OAuth | `gemini -p <prompt> --approval-mode plan [-m <model>]` | `--json-strict` prepends a strict-JSON preamble (gemini ignores in-prompt contracts). |
| `opencode` | CLI | OAuth | `opencode run [--model <m>]` (prompt via stdin) | Windows arg quoting drops content past first newline; stdin is mandatory. |
| `kilo` | CLI | OAuth | `kilo run [--model <m>]` (prompt via stdin) | Same code path / same caveats as opencode. |
| `copilot` | CLI | `gh auth` + `gh extension install github/gh-copilot` | `copilot -p <prompt>` | Wraps replies with `●`/`✗` tool-call markup; [`output_parsers.parse_copilot`](output_parsers.py) strips before JSON extraction. |
| `agent` | CLI | Cursor OAuth (`cursor-agent login`); optional `CURSOR_API_KEY` | `cursor-agent -p --output-format json --force [--model <m>] [--resume <sid>] <prompt>` | Stdin pipe blocks waiting for tty (verified 2026-05-03); worker passes prompt as positional arg. Custom resolver checks `CURSOR_AGENT_CLI` env > `%LOCALAPPDATA%/cursor-agent/cursor-agent.cmd` > PATH. JSON envelope `.result` extracted via [`output_parsers.parse_agent_envelope`](output_parsers.py); `session_id` surfaced for resume. `--force` set so headless tool-use doesn't hang on approval prompts. |
| `kimi` | CLI | Moonshot OAuth (`kimi login`; token under `~/.kimi/`); optional `KIMI_API_KEY` / `MOONSHOT_API_KEY` for CI | `kimi --quiet -p <prompt> [--model <m>] [--session <sid>] [--continue]` | Kimi CLI v1.23.0 (Moonshot AI). Custom resolver in [`worker_runner._resolve_kimi_cli`](worker_runner.py) checks `KIMI_CLI` env > `%APPDATA%/Code/User/globalStorage/moonshot-ai.kimi-code/bin/kimi/kimi.exe` (VS Code extension bundle) > `~/.vscode/extensions/moonshot-ai.kimi-code-*/bin/kimi/` > PATH. `--quiet` is an alias for `--print --output-format text --final-message-only`; `--print` implies `--yolo`, no approval prompts. Output is clean prose (no envelope, no parser needed). Session resume: `--session <id>` for explicit sid, `--continue` for last session in working dir. PONG smoke ~3-5s; 6.8 KB brief ~30s producing 10 KB JSON. |
| `openclaude` | CLI | provider-dependent: `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY` / `GEMINI_API_KEY` / `GH_TOKEN` (whichever provider `--provider` selects) | `openclaude -p <prompt> --provider <p> --output-format json [--resume <sid>] [--session-id <sid>]` | Third-party Claude Code fork (`@gitlawb/openclaude` v0.7.0; source: github.com/Gitlawb/openclaude) with multi-provider routing (OpenAI / Gemini / DeepSeek / Anthropic / GitHub Models / Bedrock / Vertex / Foundry / Ollama). Swarm `--model` arg is mapped onto openclaude's `--provider`; `OPENCLAUDE_PROVIDER` env sets the default (falls back to `openai`). JSON envelope `.result` / `.session_id` auto-extracted (same shape as native claude). **Trust caveat**: third-party package, audit `package.json` before each upgrade — v0.7.0 verified clean (no postinstall/preinstall hooks, no `scripts/` shipped, all standard Anthropic SDK + OSS deps). Cost estimate is APPROXIMATE — table uses gpt-4o-mini list price; routing to a pricier provider will under-estimate. PONG smoke ~5s; 6.9 KB brief ~36s (gpt-4o-mini default). |
| `codex` | CLI | OpenAI ChatGPT OAuth (`codex login`); optional `OPENAI_API_KEY` for API-billed fallback; optional `CODEX_HOME` to redirect auth dir | `codex exec --skip-git-repo-check --sandbox read-only --json -c approval_policy="never" [-m <model>] [exec resume <sid>]` (prompt via stdin) | OpenAI Codex CLI v0.128.0+ (`@openai/codex`); shim at `%APPDATA%/npm/codex.cmd`. Worker parses JSONL events: `thread.started.thread_id` -> session id, `item.completed` items where `item.type=="agent_message"` -> response text (joined), `turn.completed.usage.{input,output}_tokens` -> meta. Sandbox hard-coded to `read-only`; approval policy hard-coded to `never` so headless runs never escalate to interactive prompts. Auto-runs filesystem probes by default (high input-token usage; 19K-930K observed for short-vs-brief prompts) — for minimal latency, prompt must explicitly forbid tool use. **KFM**: ChatGPT OAuth has a usage cap that surfaces as a JSONL `error` event + rc=1 — set `OPENAI_API_KEY` to fall back to API billing. See [`SWARM_DESIGN_NOTES.md`](SWARM_DESIGN_NOTES.md). PONG smoke ~30s; 6.9 KB brief ~5min producing 11 KB structured JSON. |
| ~~`freebuff`~~ | PTY | OAuth | n/a | **REMOVED 2026-05-04** — TUI-only PTY engine, low usage. `pty_driver.py` and `_freebuff_test_ladder.py` deleted with this engine. See [`CHANGELOG.md`](CHANGELOG.md) and [`SWARM_DESIGN_NOTES.md`](SWARM_DESIGN_NOTES.md) (historical). |
| `deepseek` | API | `DEEPSEEK_API` | `python api_consult.py --provider deepseek -` | OpenAI-compatible `/chat/completions`; default model `deepseek-chat`. |
| `cerebras` | API | `CEREBRAS_API` | `python api_consult.py --provider cerebras -` | Uses `cerebras-cloud-sdk` Python client; `max_completion_tokens` not `max_tokens`. |
| `xai` | API | `X_AI_KEY` (or `XAI_API_KEY` / `X_AI` / `GROK_SUPER`) | `python api_consult.py --provider xai -` | Default model `grok-3-latest`. |
| `inception` | API | `INCEPTION_AI_KEY` | `python api_consult.py --provider inception -` | Use `mercury-2`; `mercury` is deprecated and 404s. |
| `ollama_cloud` | API (local CLI shell-out) | `ollama signin` | `python api_consult.py --provider ollama_cloud -` → `ollama run gpt-oss:120b-cloud <prompt>` | `OLLAMA_CLOUD_KEY` env is an SSH push key, NOT a chat token. Adapter ignores HTTP and shells out to local CLI, then runs smart-quote / wrap-dup repair to make output JSON-parseable. |
| `openrouter` | API | `OPENROUTER` (Bearer) | `python api_consult.py --provider openrouter -` | OpenAI-compat HTTP gateway exposing 200+ models from many vendors (`<provider>/<model>` ids: `openai/gpt-4o-mini`, `anthropic/claude-haiku-4.5`, `x-ai/grok-2`, `meta-llama/llama-3.3-70b-instruct:free`, ...). Default model: `openai/gpt-4o-mini` (cheap+fast). Override via `OPENROUTER_MODEL` env or `--model`. Adapter sends `HTTP-Referer` + `X-Title` etiquette headers (rate-limit attribution + leaderboard credit). **Cost-cap caveat**: [`swarm_run.COST_PER_1K_TOKENS["openrouter"]`](swarm_run.py) carries the gpt-4o-mini rate ($0.15/M in, $0.60/M out). When user overrides to a more expensive model (e.g. Claude Opus, GPT-5) the pre-dispatch cost estimate becomes APPROXIMATE — actual spend can be ~100x the estimate. For precise cost gating with a non-default model, raise `--cost-cap-usd` accordingly or wrap the run with a per-model rate override. |
| `codebuff` | n/a | n/a | EXCLUDED | TUI-only and account out of credits. Removed from the engine list. |

## --from-session resume routing

`worker_runner.py --from-session <sid>` reads the session row from
`swarm_runs/_sessions.db` and chooses one of three resume modes based on
the engine:

```
                   --from-session <sid>
                            |
                            v
              +-----------------------------+
              | get_session(sid).engine == ?|
              +--------------+--------------+
                             |
        +--------------------+-----------------+
        |                    |                 |
     claude              API_ENGINES       CLI_ENGINES
   (cli_session_id      (deepseek/cere    (gemini/opencode/
    present?)            xai/inception/    kilo/copilot/
        |                ollama_cloud)     )
        |                    |                 |
        v                    v                 v
  --resume <cli_sid>    JSONL replay:      MD-context fallback:
  (native CLI            replay_messages   render_md_context()
   resume; cheapest)     -> preface.md     -> 4 KB Markdown preamble
                         -> --context-md   -> --context-md
```

- **claude → native** when `sessions.cli_session_id` is set; the worker
  appends `--resume <cli_sid>` to the claude CLI args.
- **API engines → JSONL replay**: full message history (chronological)
  written to a temp `.md` file under
  `swarm_runs/_session_<sid8>_ctx.md` and passed via `--context-md`.
- **CLI engines → MD-context fallback**:
  [`session_manager.render_md_context(sid, max_chars=4000)`](session_manager.py)
  produces a newest-first, budget-greedy preamble.

Cross-engine resume is allowed but logged to stderr; the worker uses the
fallback path and the chain may suffer if the original engine had unique
state.

## Slash command contract

Slash commands live under [`.claude/commands/swarm*.md`](../../.claude/commands/).
Frontmatter (YAML) declares `description` and optional `argument-hint`;
the body is the system prompt the slash interpreter uses to decide what
to run. Hard rules:

1. **Slash commands must NOT write engine outputs themselves.** They run
   the documented Python / PowerShell entry point and print stdout
   verbatim. No restating, no summarisation.
2. **Every command that writes a run dir must auto-run `swarm_inspect.py
   --latest`** before returning so the user sees response sizes + suspect
   flags. This is the no-surprise rule (see
   [`swarm.md`](../../.claude/commands/swarm.md) and
   [`swarm-run.md`](../../.claude/commands/swarm-run.md)).
3. **Unknown subcommand falls through to `run`** — i.e.
   `/swarm somefile.md` is interpreted as `/swarm run somefile.md`.
4. **No engine output should be invented.** When the command needs byte
   counts or flags, it MUST call `swarm_inspect.py` — never make them up
   from CLI stdout heuristics.
5. **Read-only.** Slash commands may not run `gh pr comment`,
   `git push`, or any other network write. The PR pipeline's only
   writer is [`comment_poster.ps1`](comment_poster.ps1), which runs
   under interactive `y/N`.

The nine commands map 1:1 to the entry points documented in
[`README.md`](README.md#slash-commands).

## Inspector flag taxonomy

[`swarm_inspect.py`](swarm_inspect.py) walks every `*.json` +
`*.json.raw.txt` pair in a run dir and tags each engine with one or more
flags. Detection rules:

| Flag | Detected by | Action |
|---|---|---|
| `HEALTHY` | `len(raw) >= 1024` | None — engine looks fine. |
| `SHORT` | `200 <= len(raw) < 1024` | Inspect raw before trusting. |
| `TINY` | `0 < len(raw) < 200` | Almost certainly garbage / banner. |
| `ZERO` | `len(raw) == 0` | Process produced no output; rerun with `--debug`. |
| `CREDITS?` | regex `out of credits / insufficient credits / quota exceeded / rate limit / billing required / insufficient balance` | Top up / switch provider. |
| `AUTH?` | regex `40[13] / unauthori[sz]ed / forbidden / invalid api[\s_-]?key / authentication failed` | Re-login / re-issue key. |
| `PARSE_FAILED` | envelope has `verdict=COMMENT_ONLY` AND `fabrication_risk.level=HIGH` | Worker's stub fallback fired; raw output was non-JSON. |
| `TRUNCATED?` | `raw.rstrip()[-1] not in '}])"`.\n)' ` | Response cut mid-token; check timeout / max-tokens. |

`render_table()` lists every engine with `flags = sus_flag_subset` under
"Suspect engines" so the user can re-run only the bad ones.

A run dir with at least one suspect flag exits the inspector with rc=3
— useful as a CI / GHA gate.

## Output parsers

[`output_parsers.py`](output_parsers.py) cleans engine-specific wrappers
before JSON extraction in [`worker_runner.py`](worker_runner.py).

### Copilot tool-call markup

GitHub Copilot CLI prefixes tool actions with `●` (success) or `✗`
(failure), followed by indented `│` (args) and `└` (result) body lines.
[`parse_copilot`](output_parsers.py) drops every tool-call block and
keeps only the model prose; multiple blank lines collapse to two.

```
●  Read file: foo.py         <- header → drop, arm body skip
  │ args: ...                <- body   → drop
  └ result: ok               <- body   → drop
                             <- blank  → still skipping
The actual answer starts here. <- non-body → resume capture
```

### Claude `--output-format=json` envelope

Claude CLI returns
`{ "result": "<text>", "session_id": "...", ... }` when invoked with
`--output-format=json`. [`parse_claude_envelope`](output_parsers.py)
unwraps `.result` (falling back to `.text` / `.content` / `.message`).
The worker reads `session_id` separately and stores it in
`_swarm_meta.session_id` for the resume path.

Other engines (gemini, opencode, kilo, all API engines) pass
through unchanged.

## Schema strictness levels

[`schema_validate.py`](schema_validate.py) supports three strictness levels
selected via `--strictness {strict,lenient,off}` (CLI) or
`strictness:` (top-level YAML field). Default is `strict`.

| Level | Required fields | Enums | `concerns[*].evidence` (severity ∈ blocking/major) |
|---|---|---|---|
| `strict` (default) | enforced | enforced | **≥10 chars** |
| `lenient`          | enforced | enforced | **≥1 char (non-empty)** |
| `off`              | enforced | NOT enforced | NOT enforced |

`minor` and `question` concerns may always have empty evidence at every
level — consistent with the anti-hallucination contract in
[`prompts/pr_review.md`](prompts/pr_review.md) (speculative claims must
use `severity: "question"`).

### The `if`/`then` minLength rule

[`schema_review.json`](schema_review.json) ships a draft-07 conditional
on `concerns[*]`:

```json
"if": {"properties": {"severity": {"enum": ["blocking", "major"]}}},
"then": {"properties": {"evidence": {"minLength": 10}}}
```

This is the strict-only floor — a worker emitting `"evidence": ""` (or any
short placeholder) on a blocking/major concern fails strict validation.
For non-strict modes the validator strips `if`/`then`/`else` blocks via
[`_strip_strict_only_constraints`](schema_validate.py) before handing the
schema to `jsonschema`. The hand-rolled fallback path mirrors the same
ladder by switching its evidence-floor between 10 (strict) and 1
(lenient).

`off` further strips `enum` constraints so schema-skeleton placeholders
pass — useful for early-prototype engines whose verdict/confidence
vocabularies haven't stabilised. It does NOT skip required-field
validation; a payload missing `confidence`/`concerns`/`commentary_text`/
`fabrication_risk` still fails at every level (see
[`fixtures/bad.json`](fixtures/bad.json)).

### Override sources

```yaml
# tools/swarm/examples/asset_class_audit.yaml
strictness: strict   # strict | lenient | off
```

```bash
# CLI override (wins over YAML)
python tools/swarm/schema_validate.py path/to/output.json --strictness lenient
```

When both are set, the CLI flag wins. The default-without-config
behaviour is `strict` — peers should opt **down** explicitly when an
engine legitimately can't produce evidence in its domain.

### Fixture matrix

| Fixture | strict | lenient | off |
|---|---|---|---|
| [`fixtures/good.json`](fixtures/good.json) (full payload, evidence >10 chars) | pass | pass | pass |
| [`fixtures/bad.json`](fixtures/bad.json) (missing required fields) | fail | fail | fail |
| [`fixtures/lenient.json`](fixtures/lenient.json) (blocking concern, evidence=" ") | fail | pass | pass |



## Per-engine sampling (`api_consult.py:SAMPLING_DEFAULTS`)

Each API provider ships with a default sampling block keyed by provider
name. Callers can override per-call via three precedence-ordered surfaces
(highest to lowest): explicit CLI/Python `sampling=` arg → env var →
`SAMPLING_DEFAULTS`.

```python
SAMPLING_DEFAULTS = {
    "deepseek":     {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "xai":          {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "inception":    {"temperature": 0.2, "max_tokens": 4000, "top_p": 1.0},
    "cerebras":     {"temperature": 0.2, "max_completion_tokens": 4000, "top_p": 1.0},
    "ollama_cloud": {"temperature": 0.2, "num_predict": 4000, "top_p": 1.0},
}
```

### Field-name quirks

- `cerebras` accepts `max_completion_tokens`, NOT `max_tokens`. The
  `--max-tokens` CLI flag is auto-mapped to the correct field name by
  [`api_consult._resolve_sampling`](api_consult.py).
- `ollama_cloud` accepts `num_predict` (the local CLI honours it via the
  `OLLAMA_NUM_PREDICT` env var, set on the child process only). Same
  alias-mapping applies for `--max-tokens`.
- All other providers use the OpenAI-compatible `max_tokens`.

### Override surfaces

1. **CLI flags** on `api_consult.py`:
   `--temperature <float>`, `--max-tokens <int>`, `--top-p <float>`.
2. **Worker pass-through** on `worker_runner.py`: same three flags;
   forwarded to the spawned `api_consult.py` process when set.
3. **YAML per-engine** under `engines[].sampling:`:

   ```yaml
   engines:
     - name: deepseek
       sampling:
         temperature: 0.1
         max_tokens: 8000
   ```

   Read at worker-launch time via
   [`_engine_overrides.load(yaml_path, engine_name)`](_engine_overrides.py)
   and merged onto the api_consult command line as CLI flags. CLI flag wins
   on conflict; YAML loses to explicit CLI but beats provider defaults.
4. **Env vars** (lowest precedence; useful for one-off shell sessions):
   `<PROVIDER>_TEMPERATURE`, `<PROVIDER>_MAX_TOKENS`, `<PROVIDER>_TOP_P`
   (e.g. `DEEPSEEK_TEMPERATURE=0.1`). Read inside
   [`api_consult._resolve_sampling`](api_consult.py); auto-mapped to
   provider-correct field names.

### YAML schema fields recognised by `_engine_overrides.py`

```yaml
engines:
  - name: deepseek
    model: deepseek-chat
    sampling:               # optional dict; passed to api_consult
      temperature: 0.1
      max_tokens: 8000      # auto-mapped per provider
      top_p: 0.95
    retries: 2              # optional int; overrides --retries default
```

Allowed sampling keys: `temperature`, `max_tokens`, `max_completion_tokens`,
`num_predict`, `top_p`, `presence_penalty`, `frequency_penalty`. Unknown
keys are silently dropped by `_engine_overrides.load(...)`.

**Note:** `swarm_run.py` (owned by Subagent N) does not yet wire the
per-engine `sampling:` / `retries:` fields through to the worker
subprocess. Until it does, callers can pass `--config-yaml <path>` to
`worker_runner.py` directly to consult the YAML for overrides. Once
`swarm_run.py` learns the new fields, it can either pass `--config-yaml`
through or build the equivalent CLI flags itself.

## Retry policy (`worker_runner.py --retries`)

API-engine calls are wrapped in a retry loop inside
[`worker_runner.call_api_consultant`](worker_runner.py). The loop is
narrow on purpose — it covers the noisy "rate-limit / transient
upstream / undersized response" failure modes that retries actually fix,
and explicitly skips failure modes where retrying makes things worse.

### Defaults

- **Budget:** 1 retry on top of the initial attempt (so 2 attempts max).
  Configurable via `--retries N` (0 disables retries).
- **Trigger:** retry if `rc != 0` OR `len(output) < 200` bytes.
- **Backoff:** linear 2 s × attempt index. First retry sleeps 2 s, second
  sleeps 4 s, etc.

### Skipped on

- `subprocess.TimeoutExpired` — fast-fail. The loop re-raises so the
  outer `main()` handler records `rc=4` via `CallTimer.set_rc(4)`.
- Schema-validation failures — those happen downstream of the worker,
  retrying the worker doesn't help.

### Logging

Every NON-final attempt is logged separately to `swarm_runs/_calls.jsonl`
via `swarm_log.log_call(...)` with:

```json
{"retry_count": <attempt_idx>, "retry_attempt": true, "retry_total": <budget+1>}
```

The FINAL attempt (success or last fail) is logged by the outer
`CallTimer` in `worker_runner.main()` as the canonical record for that
worker invocation. Aggregators (`swarm_stats.py`) treat `retry_attempt:
true` rows as auxiliary signals, not as additional invocations.

### Precedence

CLI flag → YAML `engines[].retries:` → 1 (default).

If `--retries` is **explicitly set** on the CLI, it always wins. If it
is omitted (`None` after argparse), the per-engine YAML value (if any)
is used. If neither is set, the default of 1 applies.

## Engine presets

[`swarm_run.py`](swarm_run.py) ships a small library of named engine bundles
selectable via `--preset NAME` or YAML `preset: NAME`. Resolves the same as a
bare `--engines a,b,c` would. Mutually exclusive with `--engines`; explicit
`engines:` in YAML wins over both.

| Preset | Members | When to use |
|---|---|---|
| `consensus-3`  | `deepseek,xai,kilo`                              | Cross-vendor consensus at moderate cost (default for PR review). |
| `fast-cheap`   | `cerebras,deepseek`                              | Quick gut-check; sub-cent per run. |
| `deep-strict`  | `claude,kilo,deepseek`                           | Highest-fidelity engines + opus red-team. |
| `all-paid-api` | `deepseek,xai,cerebras,inception,ollama_cloud`   | Maximum API breadth; skip CLI auth flows. |
| `all-cli`      | `claude,gemini,kilo,opencode,copilot`            | Maximum CLI breadth; skip pay-per-token engines. |

Discovery: `python tools/swarm/swarm_run.py --list-engines` prints both the
engine inventory and the preset table. To add a new preset, edit
`ENGINE_PRESETS` at the top of [`swarm_run.py`](swarm_run.py) and document it
here. Keep the list short — presets are curated, not generated.

## Cost cap

Every run computes a pre-dispatch USD estimate from `COST_PER_1K_TOKENS` in
[`swarm_run.py`](swarm_run.py) using `(prompt_chars / 4) / 1000 * in_rate +
4000/1000 * out_rate` per engine. The total prints to stdout always
(transparency); if it exceeds `--cost-cap-usd` the run aborts before any
worker dispatches with a per-engine breakdown.

Default cap: **$1.00**. Override per-run with `--cost-cap-usd 5.0` (CLI) or
`cost_cap_usd: 5.0` (YAML). Set high (e.g. `100`) to effectively disable.

Rate-table notes (USD per 1K tokens, 2026-05 list prices):

| Engine | Input | Output |
|---|---|---|
| `deepseek`     | $0.00014 | $0.00028 |
| `cerebras`     | $0.0001  | $0.0001  |
| `inception`    | $0.001   | $0.002   |
| `xai`          | $0.005   | $0.015   |
| `claude`       | $0.003   | $0.015   |
| `ollama_cloud` | $0      | $0      | (subscription) |
| `gemini` / `kilo` / `opencode` / `copilot` | $0 | $0 | (OAuth-bundled) |

When a provider raises prices, update `COST_PER_1K_TOKENS` in tandem — the
table does not auto-refresh.

## Pre/post hooks

`--pre-hook CMD` and `--post-hook CMD` (or YAML `pre_hook:` / `post_hook:`)
take a shell command run via `subprocess.run(shell=True)`. Use them for
guard-rails ("git status check before swarm runs") and post-processing
("auto-run swarm_inspect.py and pipe to Slack").

Env vars exposed to the child process:

| Hook | Vars |
|---|---|
| pre  | `SWARM_OUT_DIR` |
| post | `SWARM_OUT_DIR`, `SWARM_OK_COUNT`, `SWARM_TOTAL` |

Hooks are advisory: a non-zero exit code logs a warning to stderr but does
not fail the swarm. Hook timeout is 300s. Stdout/stderr from the hook is
relayed verbatim. Do not pass untrusted input via these flags — they are
shell-evaluated by design.

## Red-team auto-invoke

`--red-team` (or YAML `red_team: true`) appends a fabrication-red-team pass
after all workers + post-hook. It concatenates every engine envelope into
`<out_dir>/_redteam_input.json`, builds a prompt from
[`prompts/redteam.md`](prompts/redteam.md) plus the merged plan, and dispatches
`worker_runner --engine claude --model opus --json-strict` to produce
`<out_dir>/redteam.json`.

Opt-in by default because **opus is the most expensive engine** in the rate
table above (~$0.06–$0.10 per swarm even with a small prompt). Closes Subagent
J audit flag #1 ("verify red-team is auto-invoked") without forcing the cost
on every run.

### Caveats (post 2026-05-03 self-review debug)

1. **Long-prompt stdin path (FIXED 2x)** — concat'd redteam prompts (engine envelopes + redteam.md) routinely exceed 8 KB. Original fix piped via stdin when `prompt_bytes > 6000`. Post-2026-05-03 PR-review forensics (`swarm_runs/PR_REVIEW_ABORTED.md`) showed prompts in the 5-8 KB band still failed: 3/3 claude PR-review jobs returned only the system banner ("Ready. Awaiting PR review task.", 32-59 raw bytes) with the per-task prompt silently dropped. Root cause: argv path with allowedTools/disallowedTools flag list pushed the 5 KB prompt past cmd.exe's effective ceiling on the `.cmd` shim path. Final fix: `call_claude` now ALWAYS pipes via stdin (the 6000-byte threshold was removed). See KFM-1 in `SWARM_DESIGN_NOTES.md` and the [PR-review pipeline (post-fix)](#pr-review-pipeline-post-fix) section below.

2. **`--max-turns 12` is tight for redteam** — opus tries to verify each concern with `Bash(gh pr diff)` / `Bash(grep)` / `Read`. With ~5 concerns × 2-3 verification commands each, 12 turns gets exhausted (`error_max_turns`). The output IS valid JSON (claude's `-p --output-format json` envelope) so the worker_runner JSON extractor still saves it; but the *inner* fabrication-summary may be partial. Operator may want to bump `--max-turns 25` for redteam-heavy runs by editing `swarm_run.py:685-688`.

3. **`--json-strict` is a no-op for claude** — `call_claude` ignores the flag entirely (only `call_gemini` honors it via `_GEMINI_JSON_PREFIX`). The outer claude envelope is always JSON regardless, so this doesn't break the redteam fallback path; but the inner `result` field may contain prose / markdown rather than the strict JSON shape declared in `redteam.md`. To enforce, either inject the JSON-only preamble into the prompt before dispatch, OR post-process to parse `envelope.result` and rewrite `redteam.json` with the inner JSON. Not implemented (would exceed the 30-LOC budget for this fix).

4. **`permission_denials` accumulate** — readonly sandbox rejects `Bash(python -c ...)` and similar. Redteam prompt steers claude toward `gh`/`grep`/`git`/`Read` — those are on the allowlist. If a redteam run produces a low-signal envelope, check `_swarm_meta` / raw output for `permission_denials`; consider broadening `READ_ONLY_ALLOWED` for the redteam invocation only.

## Persona injection (`--persona`)

Closes the orphan flagged in `swarm_runs/SWARM_SELF_REVIEW.md` imp-A
(deepseek + xai both ranked this the highest-leverage swarm improvement).
Persona files live under [`agent_personas/`](agent_personas/) and were
authored long before any wire-up; this section documents how they reach
the engine.

### CLI flags

`worker_runner.py`:

```
--persona <NAME>
```

`swarm_run.py`:

```
--persona <NAME>          # fleet default for all engines
```

`<NAME>` resolves to a persona body via the following candidates (first hit
wins, cross-platform via `pathlib.Path`):

1. `tools/swarm/agent_personas/<NAME>.md`
2. `tools/swarm/agent_personas/<NAME>_specialist.md`
3. `tools/swarm/agent_personas/<NAME-with-hyphens-replaced-by-underscores>.md`
4. Same as #3 with the `_specialist` suffix appended.
5. `<NAME>` treated as an absolute or relative path.

Hyphen↔underscore normalization is necessary because personas advertise
hyphenated names in their YAML frontmatter (`name: crypto-specialist`)
but ship as underscored filenames (`crypto_specialist.md`).

A typo raises `FileNotFoundError` and exits non-zero — silent fallthrough
would defeat the purpose of declaring a persona contract.

### YAML config

```yaml
persona: ml-validation-specialist     # fleet-wide default
engines:
  - name: deepseek
    persona: regime-specialist        # per-engine override
  - name: xai                         # inherits ml-validation-specialist
```

### Resolution precedence

Per-engine YAML `persona:` > top-level YAML `persona:` > `--persona` CLI flag > none.

CLI is the lowest priority because the YAML config is the documented,
reviewable artifact for a swarm run; the CLI flag is a one-shot override
useful for quick experiments.

### Prompt shape

When a persona resolves, `worker_runner._read_prompt` prepends:

```
## You are operating under this persona contract
<persona body, frontmatter stripped>

## Task
<original prompt body>
```

Frontmatter strip is YAML 3-dash delimiter only. The persona body is
trimmed (`.strip()`); no further redaction.

### Verifying the wire-up

Same prompt + 2 different personas should produce visibly different
framing:

```
python tools/swarm/worker_runner.py \
    --engine deepseek \
    --prompt-file swarm_runs/_persona_smoke.md \
    --out-file swarm_runs/_smoke_crypto.json \
    --persona crypto-specialist

python tools/swarm/worker_runner.py \
    --engine deepseek \
    --prompt-file swarm_runs/_persona_smoke.md \
    --out-file swarm_runs/_smoke_forex.json \
    --persona forex-specialist
```

Cost per pair: ~$0.005. The persona-conditioned response should reference
the kill rules, blocked patterns, or edge sources from the persona body
that the no-persona baseline does not surface.

## PR-review pipeline (post-fix)

**Background.** On 2026-05-03 a forensic audit
(`swarm_runs/PR_REVIEW_ABORTED.md`) found two compounding bugs that
together produced a **100% fabrication rate** on a 9-PR / 3-engine
review pass:

1. **Bug #1 (API engines fabricate `gh` output).** The legacy
   [`prompts/pr_review.md`](prompts/pr_review.md) instructed every
   worker to run `gh pr view <N>` / `gh pr diff <N>` and grep the
   checked-out source. API engines
   (`deepseek` / `xai` / `cerebras` / `inception` / `ollama_cloud`) are
   pure text-to-text — they have **no shell access** — so they
   confabulated `gh` output from the PR title alone, marking
   `fabrication_risk: LOW`. 7/7 API jobs invented file paths and
   components that did not exist in the diff. Schema validation
   passed (envelopes were JSON-shaped); content was made up.
2. **Bug #2 (claude CLI delivered "system header only").**
   `call_claude` previously argv-passed prompts <=6000 bytes and
   piped via stdin only above the threshold. PR-review prompts land
   in the 5-8 KB band; combined with the
   `--allowedTools` / `--disallowedTools` flag list, the effective
   command line crossed cmd.exe's ~8191-char ceiling on the `.cmd`
   shim path. Symptom: claude launched, returned 32-59 raw bytes
   containing only its banner ("Ready. Awaiting PR review task."),
   then exited rc=0 with the per-task prompt silently dropped.
   3/3 claude PR-review jobs in the abort run hit this.

### Pipeline (after the fix)

```
swarm_dispatch.ps1
  for each PR in $Prs:
    1. python tools/swarm/_pr_capture.py <pr> --out-file pr_<n>_capture.json
       (server-side gh: pr view --json + pr diff, truncated to 60 KB)
    2. python tools/swarm/_pr_embed_helper.py
         --template prompts/pr_review_inline.md
         --capture pr_<n>_capture.json
         --out pr_<n>_prompt.md
       (substitutes {{PR_NUMBER}} + {{PR_CAPTURE}} via _pr_capture.embed_into_prompt)
    3. for each engine in $Engines:
         Start-Job python worker_runner.py
           --prompt-file pr_<n>_prompt.md   <-- per-PR sidecar with diff already inlined
           --engine <engine> --pr <n>
```

Every engine — CLI **or** API — receives the same fully-rendered
prompt with the diff already embedded as a fenced ``` ```diff ``` block.
No worker is asked to run a shell command. The new prompt template,
[`prompts/pr_review_inline.md`](prompts/pr_review_inline.md), explicitly
forbids inventing file paths and requires every claim to cite either
the embedded diff (`path:LINE`), the embedded body, the file list, or
the status-checks list — or be marked `severity: "question"`.

The legacy [`prompts/pr_review.md`](prompts/pr_review.md) is preserved
for backward-compat; pass `-NoInlineCapture` to `swarm_dispatch.ps1`
plus `-PromptFile <legacy>` to revert. **Only safe for shell-capable
CLI engines** (`claude` / `gemini` / `opencode` / `kilo` / `copilot`);
do NOT combine with API engines.

### Default behaviour change

`swarm_dispatch.ps1` defaults updated:
- `-PromptFile` default: `prompts/pr_review_inline.md` (was `pr_review.md`).
- `-NoInlineCapture` switch added; default **off** = capture + embed always.

`_summary.json` records the inline-capture state so post-mortems can
distinguish runs:

```json
{
  "inline_capture": true,
  "capture_files": {"724": "swarm_runs/.../pr_724_capture.json"},
  "per_pr_prompt_files": {"724": "swarm_runs/.../pr_724_prompt.md"},
  "prompt_template": "tools/swarm/prompts/pr_review_inline.md"
}
```

### Why API engines must never be told to run shell

`api_consult.py` only knows `messages=[{"role": "user", "content": "..."}]`
— it has no Bash/Read/Grep tool surface. When an API engine is given a
prompt that says "run `gh pr view X`", the model will dutifully *narrate*
running the command, then hallucinate plausible-looking output for it,
because that is the lowest-loss continuation of the prompt. The output
is **schema-valid** (the model knows the JSON shape), so
`schema_validate.py` passes it; only manual content audit catches the
fabrication. **Inline-embed every external artifact the worker needs.**

### Always-stdin claude path

[`worker_runner.call_claude`](worker_runner.py) now pipes the full
prompt via stdin **unconditionally** (`stdin_data=prompt`); the prior
`prompt_bytes > 6000` threshold was removed. There is no downside —
`claude -p` reads from stdin when no positional arg is supplied — and
the change closes the entire Windows command-line-length failure class
in one place. Verified: a 5.7 KB PR-review prompt now produces a
4-12 KB review envelope rather than 59 bytes of banner.

### Verification

```
# 1. Compile-check the new helper + worker.
python -m py_compile tools/swarm/_pr_capture.py tools/swarm/worker_runner.py

# 2. Smoke the capture against a real merged PR.
python tools/swarm/_pr_capture.py 739 --out-file /tmp/cap739.json
# -> diff field non-empty, files list non-empty.

# 3. PowerShell parse-check the dispatcher.
[System.Management.Automation.Language.Parser]::ParseFile(
    "tools/swarm/swarm_dispatch.ps1", [ref]$null, [ref]$null)

# 4. Live cross-engine swarm against a merged PR.
pwsh tools/swarm/swarm_dispatch.ps1 -Prs 739 -Engines deepseek,xai -PersistSessions
# -> per-PR JSONs cite REAL paths from the diff, not invented React components.
```

## Logging schema versioning

Every row written to `swarm_runs/_calls.jsonl` from 2026-05-03 onward
carries a `"v"` field as the **FIRST** key. Downstream parsers should
switch on this version to interpret the row.

### Version history

| `v`       | Released   | Fields | Notes |
|-----------|------------|--------|-------|
| _missing_ | < 2026-05-03 | 11 base | Pre-imp-B legacy rows. Treat imp-B audit fields as `""` / 0. |
| `"1"`     | 2026-05-03 | 16 = 11 base + 5 imp-B | Current. See [`swarm_log.py`](swarm_log.py) `SCHEMA_VERSION`. |

### Bump rules

- **Bump to v2/v3/etc.** when adding, removing, or renaming a column,
  or when changing the semantics of an existing field (e.g. moving
  `transport_status` from free-form string to a closed enum).
- **Don't bump** for purely additive `extra` dict keys passed via
  `log_call(extra=...)` — those are caller-scoped and not part of the
  base schema.
- When bumping, document the diff in this table and update
  `SCHEMA_VERSION` at the top of `swarm_log.py`.

### Reader contract

Robust readers MUST handle:

```python
import json
for line in open("swarm_runs/_calls.jsonl"):
    rec = json.loads(line)
    v = rec.get("v")  # missing => legacy
    if v is None:
        # Legacy row: imp-B audit fields may be absent.
        retry_count = rec.get("retry_count", 0)
        model_fp = rec.get("model_fingerprint", "")
        # ...
    elif v == "1":
        # Current schema; all fields guaranteed present.
        pass
    else:
        # Future schema; either upgrade the parser or skip.
        continue
```

`tools/swarm/swarm_stats.py` is already missing-key-safe (uses
`rec.get(...)` for every imp-B field), so legacy rows interleaved with
v=1 rows aggregate correctly.

### `low_signal` semantics (post-item-4)

Schema version `1` widens `low_signal` to also cover schema-valid empty
envelopes. The triggers are:

1. `returncode != 0`
2. `output_bytes < 50`
3. `output_bytes >= 50` AND output is a parseable JSON object that
   contains none of `concerns / strengths / commentary_text / answer /
   summary / q1_per_class` populated above the substance threshold
   (non-empty list, >20-char non-whitespace string, non-empty dict).

Trigger #3 appends `empty_envelope` to the row's `error` field
(without overwriting any existing transport-layer error). Use this to
distinguish the schema-stub failure mode from a transport timeout.
