# Swarm design notes

Internal engineering notes for the swarm CLI/PTY adapters.

## Cursor `agent` CLI integration — KFM (2026-05-03)

Cursor agent (`cursor-agent` v2026.05.01-eea359f+) is wired into the swarm
as `agent`. CLI class — headless `-p / --print` + `--output-format json`.

- [`worker_runner.py`](worker_runner.py) — `agent` in `CLI_ENGINES`; new
  `_resolve_cursor_agent()` (custom resolver because the binary lives at
  `%LOCALAPPDATA%/cursor-agent/cursor-agent.cmd`, NOT `%APPDATA%/npm` —
  the standard `_resolve_cli` only probes the npm path); `call_agent()`
  passes prompt as positional arg with `-p --output-format json --force`
  (`--force` / alias `--yolo` is mandatory in headless mode so any tool
  call inside the agent doesn't deadlock on an approval prompt). JSON
  envelope `{type:result, result:..., session_id:..., usage:{...}}`
  `.result` extracted upstream + via [`output_parsers.parse_agent_envelope`](output_parsers.py).
- [`swarm_run.py`](swarm_run.py) — `agent` in `ALL_ENGINES`;
  `COST_PER_1K_TOKENS["agent"] = $0` (Cursor subscription-bundled).
- [`safety.py`](safety.py) `ENGINE_REQUIRED_KEYS["agent"] =
  ("CURSOR_API_KEY", "CURSOR_AGENT_CLI")` — OAuth-primary; both vars are
  optional (CURSOR_API_KEY for CI; CURSOR_AGENT_CLI is a binary-path
  override).

Auth: OAuth-primary (`cursor-agent login` -> Cursor account). Optional
alternate auth via `CURSOR_API_KEY` env. Verified against
zerounderscore@gmail.com on 2026-05-03.

**Stdin pipe is broken.** `cursor-agent -p` blocks waiting on a tty
even when stdin is piped from a non-tty process. Verified empirically
against v2026.05.01-eea359f: `"prompt" | cursor-agent -p` hangs
indefinitely. The adapter passes the prompt as a single positional arg
instead. Python `subprocess.run(shell=False)` uses CreateProcessW which
preserves embedded newlines + UTF-8 in args up to the ~32 KB Windows
command-line limit — safe for the swarm's 6-8 KB asset-class briefs.

**Large-prompt fallback.** PR-review prompts can hit 40-50 KB once the
diff + checks output + persona preamble is interpolated. On 2026-05-03
a 46 KB prompt for PR #676 review tripped
`[WinError 206] The filename or extension is too long` from
CreateProcessW (~32 KB limit). The adapter detects prompts >24 KB and
writes the prompt to a temp `.md` file under the system TEMP dir, then
passes a short marker arg telling cursor-agent to use its Read tool to
load that file. Best-effort cleanup of the temp file in a `try/finally`.
This mirrors the pattern used by `pty_driver.py --mode fileref` for
freebuff long prompts.

**Known-failure-mode (KFM): default `composer-2-fast` model is
IDE-task-tuned and refuses prose Q&A.** On 2026-05-03 the smoke ladder
revealed:

- PONG smoke (`composer-2-fast`): 4 B "PONG" in 7s — works.
- 6.9 KB asset-class brief (`composer-2-fast`): 5.2 KB substantive,
  repo-aware response — works.
- Persona-injected 4.6 KB prompt (`composer-2-fast`): model claims
  "Your message stops right after the heading" and refuses to answer.
  Verified via direct subprocess that the full 4593-char prompt arrives
  intact (cursor-agent's own `inputTokens=20675` confirms receipt) —
  this is a model-quality regression, not a transport bug. Switching to
  `--model gpt-5.2` or any `gpt-5.3-codex-*` variant makes the model
  acknowledge the persona contract, but it still tends to "do code work"
  (read repo files, ask clarifying questions) instead of answering
  prose Q&A directly.

Mitigations:

1. Use cursor-agent for **code-task swarm members only** (PR review,
   lint-style checks, code-grounded Q&A). Bypass it for prose-style
   asset-class briefs and persona consultations — those should route to
   `claude` / `gemini` / API engines (deepseek/cerebras/xai).
2. When using for code Q&A, prefer `--model gpt-5.2` or `gpt-5.3-codex`
   over the default `composer-2-fast`.
3. Auto-mode threshold: cursor-agent's prose-Q&A failure is a
   model-tuning issue, not a transport one — don't add a smoke-time
   filter; document the limitation in the engine matrix and let users
   pick `--model` per task.

Brief result was the canonical "HEALTHY" indicator: 5150 B raw, 2670 B
envelope, no transport errors, no auth failures. Inspect output for the
five smoke runs (PONG / brief / persona / persona_smart / persona2):
`HEALTHY,PARSE_FAILED` for brief + persona2 (PARSE_FAILED is expected —
the prompts asked for prose, not the swarm JSON contract).

## OpenAI Codex CLI integration — KFM (2026-05-03)

Codex (`@openai/codex` v0.128.0+) is wired into the swarm as `codex`:

- [`worker_runner.py`](worker_runner.py) — `codex` in `CLI_ENGINES`; new
  `call_codex()` uses `codex exec --skip-git-repo-check --sandbox read-only
  --json -c approval_policy="never"` and parses JSONL events
  (`thread.started` -> session id; `item.completed` with
  `item.type=agent_message` -> response text; `turn.completed.usage` ->
  token counts).
- [`swarm_run.py`](swarm_run.py) — `codex` in `ALL_ENGINES`;
  `COST_PER_1K_TOKENS["codex"] = $0` (ChatGPT OAuth-bundled).
- [`safety.py`](safety.py) `ENGINE_REQUIRED_KEYS["codex"] = ("OPENAI_API_KEY", "CODEX_HOME")`.
- [`config_loader.py`](config_loader.py) `ENGINE_KEY_ENVS["codex"] = ("OPENAI_API_KEY",)`.
- [`README.md`](README.md), [`SPEC.md`](SPEC.md), [`CHANGELOG.md`](CHANGELOG.md)
  — engine matrix rows added.

Auth: OAuth-primary (`codex login` -> ChatGPT). Optional alternate auth
via `OPENAI_API_KEY` env var (codex auto-detects). The swarm does not
require either, but the worker subprocess pass-through env list includes
both `OPENAI_API_KEY` and `CODEX_HOME` so OAuth-stored credentials under
`%USERPROFILE%/.codex` keep working under env isolation.

**Known-failure-mode (KFM): ChatGPT usage cap.** When authenticated via
ChatGPT OAuth (default), codex bills against the user's ChatGPT plan.
On 2026-05-03 the persona-test smoke run hit a usage cap mid-response:

```
{"type":"error","message":"You've hit your usage limit. To get more
access now, send a request to your admin or try again at May 5th,
2026 2:50 PM."}
```

The codex `exec` subprocess returns rc=1 in this state and emits the
error as a JSONL `error` event followed by `turn.failed`. Mitigations:
1. Set `OPENAI_API_KEY` to fall back to API billing (per-token, no cap
   beyond org-level rate limits).
2. Wait for the rolling-window reset (codex surfaces the reset
   timestamp in the error message).
3. Mark `codex` optional in the YAML preset and let other engines carry
   the run.

The PONG smoke + brief smoke both succeeded earlier in the same session
(consuming ~930K input tokens for the brief due to codex's auto-context
expansion via `read_url` / file reads). The cap hit on the 3rd back-to-back
call. Plan codex usage accordingly: it's high-context per call.

**KFM #2: codex auto-runs tools.** Even with `--sandbox read-only`,
codex defaults to running shell probes (`rg --files`, `Get-ChildItem`,
etc.) before answering. This inflates input-token usage 5-10x vs other
CLIs and adds 20-90s of latency before the agent message arrives. For
short questions where the prompt is self-contained, this is wasted
budget. No silver-bullet fix — the prompt has to explicitly say "do not
read any files or run any commands" to suppress it (verified PONG
smoke). Document this in user-facing prompts when minimal latency is
needed.



## OpenRouter integration — KFM gate (2026-05-03)

OpenRouter (OpenAI-compat HTTP gateway exposing 200+ models from many
vendors) is wired into the swarm engine list as `openrouter`:

- [`api_consult.py`](api_consult.py) `PROVIDERS["openrouter"]` +
  `SAMPLING_DEFAULTS["openrouter"]`; `_post()` accepts `extra_headers`,
  `call_openai_compat()` attaches `HTTP-Referer` + `X-Title` for
  `provider == "openrouter"` (rate-limit attribution + leaderboard
  credit).
- [`safety.py`](safety.py) `ENGINE_REQUIRED_KEYS["openrouter"] = ("OPENROUTER", "OPENROUTER_MODEL")`.
- [`config_loader.py`](config_loader.py) `ENGINE_KEY_ENVS["openrouter"] = ("OPENROUTER",)`.
- [`worker_runner.py`](worker_runner.py) — `openrouter` in `API_ENGINES`.
- [`swarm_run.py`](swarm_run.py) — `openrouter` in `ALL_ENGINES`;
  `COST_PER_1K_TOKENS["openrouter"]` = gpt-4o-mini default rate.

Default model: `openai/gpt-4o-mini` (~$0.15/M in, $0.60/M out). Override
via `OPENROUTER_MODEL` env or `--model openai/gpt-4o-mini` /
`anthropic/claude-haiku-4.5` / `x-ai/grok-2` /
`meta-llama/llama-3.3-70b-instruct:free` / etc.

**Known-failure-mode (KFM): OPENROUTER env unset.** As of integration
shipment, the user has NOT yet exported the `OPENROUTER` Bearer token
into the shell env. `python tools/swarm/config_loader.py` reports
`openrouter MISS  checked ('OPENROUTER',)` and any
`api_consult.py --provider openrouter` invocation will `RuntimeError:
openrouter: no key in env (checked ('OPENROUTER',))`.

Resolution path (user action):
```
# PowerShell (current session only)
$env:OPENROUTER = "<bearer token from openrouter.ai/keys>"

# PowerShell (persisted)
[Environment]::SetEnvironmentVariable("OPENROUTER", "<token>", "User")
```

After the env var is set, the smoke ladder in the integration brief
(PONG → brief → inspect → persona → multi-model → swarm-fanout) can be
run end-to-end. All swarm code paths are wired and `--list-engines` /
`config_loader` / `py_compile` already pass green.

## OpenClaude integration — trust audit + KFM (2026-05-03)

`openclaude` (`@gitlawb/openclaude` v0.7.0; source: github.com/Gitlawb/openclaude)
is a **third-party Claude Code fork** with a `--provider` flag that routes to
OpenAI / Gemini / DeepSeek / Anthropic / GitHub Models / Bedrock / Vertex /
Foundry / Ollama in a single binary. Wired into the swarm as a CLI engine on
2026-05-03 after a trust audit unblocked it from the earlier "untrusted" hold.

**Trust audit (2026-05-03, npm-installed `@gitlawb/openclaude@0.7.0`):**

- `package.json` ships **no `postinstall`/`preinstall`/`install` lifecycle
  hooks**. Only `prepack` (publisher-side build) runs at publish, never on
  install.
- The published tarball contains only `bin/openclaude`, `dist/cli.mjs`, and
  `README.md` (per `files:` whitelist). **No `scripts/` directory shipped on
  disk** — none of the `dev:codex`, `verify:privacy`, etc. helpers are
  distributed; they live in the GitHub source tree only.
- `bin/openclaude` is a 33-line ESM shim: `existsSync(distPath) ? import(...)
  : print build instructions`. No network, no exfil paths.
- `dist/cli.mjs` is a single 21 MB bundled file. Surface-level scan: the deps
  declared in `package.json` are all standard (Anthropic SDKs:
  `@anthropic-ai/sdk` 0.81.0, `@anthropic-ai/bedrock-sdk`,
  `@anthropic-ai/foundry-sdk`, `@anthropic-ai/sandbox-runtime`,
  `@anthropic-ai/vertex-sdk`; plus Commander, React, undici, ws, axios,
  google-auth-library, sharp, MCP SDK, OpenTelemetry, etc.). No suspicious
  packages.
- Verdict: **clean for v0.7.0**. Re-audit `package.json` before each version
  bump.

**Wiring layer:**

- [`worker_runner.py`](worker_runner.py) — `CLI_ENGINES` adds `openclaude`;
  new `call_openclaude()` invokes
  `openclaude -p <prompt> --provider <p> --output-format json
  [--resume|--session-id]`. Swarm `--model` arg is mapped onto openclaude's
  `--provider` (because openclaude's own `--model` arg means the model
  *within* a provider, e.g. `gpt-4o`, `deepseek-chat`). `OPENCLAUDE_PROVIDER`
  env sets the default; falls back to `openai`. JSON envelope `.result` /
  `.session_id` are auto-extracted (same shape as native claude).
- [`safety.py`](safety.py) — `ENGINE_REQUIRED_KEYS["openclaude"]` passes
  through the union of provider keys (OPENAI_API_KEY, ANTHROPIC_API_KEY,
  DEEPSEEK_API_KEY/_API, GEMINI_API_KEY, GOOGLE_API_KEY, GH_TOKEN,
  GITHUB_TOKEN, OPENCLAUDE_PROVIDER) so any provider the user routes to
  authenticates without leaking unrelated secrets.
- [`swarm_run.py`](swarm_run.py) — `openclaude` in `ALL_ENGINES`;
  `COST_PER_1K_TOKENS["openclaude"]` carries gpt-4o-mini list price
  ($0.15/M in, $0.60/M out) as a conservative default. **Cost estimate is
  APPROXIMATE when the user routes to a pricier provider** (Anthropic Opus
  via openclaude is ~100× the gpt-4o-mini rate). Same caveat shape as
  `openrouter` — see SPEC.md cost-estimation note.

**Smoke ladder (2026-05-03 17:47-17:49Z):**

- PONG: rc=0, 4 B raw output, transport_status=ok.
- 6.9 KB asset-class brief: rc=0, 241 B response (gpt-4o-mini answered the
  brief in one paragraph), 36 s end-to-end.
- Persona injection (`--persona crypto_specialist`): rc=0, persona text
  reached the CLI (verified by prompt builder), but gpt-4o-mini gave a
  weak 2-word reply ("What need?"). This is a **model-quality issue, not a
  transport bug**; route via `--model deepseek` for serious persona work.
- Swarm fanout 2-engine (openclaude + deepseek): 2/2 ok, deepseek 4.2 s,
  openclaude 36.4 s (Claude Code startup overhead + gpt-4o-mini cold
  start). Cost estimate $0.0035 — under the $0.05 cap.

**Known-failure-mode (KFM): no provider key in env.** If the user has not
exported `OPENAI_API_KEY` (or whichever key matches `OPENCLAUDE_PROVIDER`),
openclaude will error at runtime with provider-auth-failed. Resolution: set
the appropriate `*_API_KEY` env var, or pass `--model deepseek` /
`--model gemini` etc. and ensure the matching key is set.

**Why we didn't just alias to native `claude`:** the value-add is the
`--provider` flag — a single binary giving us OpenAI / Gemini / DeepSeek /
GitHub Models / Bedrock / Vertex / Foundry / Ollama routing without
spinning up another `api_consult.py` provider entry. For Anthropic-routed
runs, native `claude` is preferred (same auth path, no third-party hop).

## Freebuff long-prompt strategy (HISTORICAL — engine removed 2026-05-04)

> The freebuff PTY engine was removed on 2026-05-04 (TUI-only, low usage).
> `pty_driver.py` and `_freebuff_test_ladder.py` were deleted with it. The
> notes below are preserved as design-history for any future PTY engine.

### Finding: TUI input buffer clamps at ~512-1024 chars

freebuff's TUI alt-screen ("Enter a coding task" input box) accepts a
single logical line. Empirically:

- 24-char `Reply PONG` smoke test: 100% reliable (`swarm_runs/probe_excluded/freebuff_v2.raw.txt`, 151 KB capture).
- 6,826-char asset-class brief: fails — driver returns banner-only output (`swarm_runs/probe_excluded/freebuff_brief.json.raw.txt`, 167 B). Symptoms split between (a) TUI silently truncating once buffer overflows and (b) the renderer raising `operation was aborted` mid-send.
- The boundary is somewhere between 512 and 1024 chars depending on render-thread timing; we treat **800 bytes** as the conservative auto-switch threshold.

### Three modes (`--mode` flag on `pty_driver.py`)

| Mode      | When | Trade-offs |
|-----------|------|------------|
| `single`  | prompts <=800 B (default; PONG path). | Lowest overhead; preserves the proven path. Fails silently or aborts on long prompts. |
| `fileref` | prompts >800 B and the model has tool-use. **Auto-selected by `worker_runner.call_pty_engine`.** Writes the prompt to `swarm_runs/_freebuff_in_<UTC>.md` and sends a <=200-char instruction telling freebuff to Read it. | Most reliable for big payloads. Risk: free-tier MiniMax M2.7 may refuse the Read tool ("I can't access local files") — driver detects refusal phrases and emits a `fileref_warning` in meta. Temp file is best-effort deleted (Windows PermissionError swallowed). |
| `chunked` | empirical fallback when fileref refuses. Splits at paragraph boundaries into <=450-char chunks, prefixes each with `PART {n}/{N}: `, paces 1.5 s between chunks, ends with a `FINAL.` trigger. | No tool-use needed. Risk: many round-trips; abort detection on each chunk; model may respond before FINAL. |

### Auto-selection (in `worker_runner.call_pty_engine`)

```
mode = "fileref" if prompt_bytes > 800 else "single"
```

Callers do not need to set `--mode` — `worker_runner` picks. `chunked` is reserved for manual invocation when fileref empirically refuses on a given target model.

### Known limitations / TODO

- `fileref` depends on the freebuff free-tier model invoking its built-in Read tool. If MiniMax declines, the driver returns the refusal text and logs a warning; caller must detect short response and retry with `chunked`. We do **not** auto-fall-through today (would burn quota; explicit retry is safer).
- `chunked` ack-detection is a fixed 3 s sleep, not a marker scan. The TUI does not echo a stable per-chunk ack; the model is requested to reply with a single dot but compliance varies. Pacing is conservative (1.5 s between chunks) instead.
- Pyte-rendered response extractor (`extract_model_response`) is unchanged — handles all three modes.
- `single` mode is byte-identical to pre-mode-flag behavior; PONG smoke test must keep passing as a regression gate.
- Test ladder lives at `tools/swarm/_freebuff_test_ladder.py`; outputs to `swarm_runs/_freebuff_ladder/`.

### File reference for posterity

- Working capture (PONG, single mode): `swarm_runs/probe_excluded/freebuff_v2.raw.txt` (151 KB).
- Failed capture (long brief, single mode pre-fix): `swarm_runs/probe_excluded/freebuff_brief.json.raw.txt` (167 B banner-only).
- Reproducer prompts: `tools/swarm/_freebuff_test_ladder.py --run {1..4}`.

## Known failure modes

### KFM-1: claude CLI rc=1 "command line is too long" on Windows (FIXED 2026-05-03)

- **Symptom**: `call_claude` returns 0 bytes in <1 s with rc=1; stderr contains `"The command line is too long."`.
- **Cause**: `claude.cmd` (npm shim) routes through `cmd.exe` whose line-length cap is ~8191 chars. With `-p <prompt>` plus `--allowedTools` / `--disallowedTools` flag lists, prompts > ~6 KB blow the cap.
- **Fix**: `worker_runner.py::call_claude` switches to stdin pipe when `prompt_bytes > 6000`. ≤ 30 LOC change.
- **Reference**: `swarm_runs/_kilo_debug/SELF_REVIEW_DEBUG.md` (full repro + verification).
- **Hit by**: red-team auto-invoke against `swarm_runs/self_review_20260503T163857Z/_redteam_prompt.md` (12,127 B) at 16:42 UTC; produced 0-byte output and `fabrication_risk:HIGH` fallback envelope.

### KFM-2: kilo CLI rc=0 + 0 bytes (transient backend hiccup)

- **Symptom**: `call_opencode_or_kilo` returns rc=0 with empty stdout after 100-300 s. Same prompt succeeds on retry.
- **Cause**: Unknown — kilo backend appears to drop the response stream silently. Not a quota / auth / content-refusal issue (verified by retry-success).
- **Mitigation**: `worker_runner` already flags `low_signal=true` when output < 50 B. Operator must re-dispatch.
- **TODO** (low priority, ≤ 5 LOC): add a single rc=0+empty retry to `call_opencode_or_kilo` mirroring the `call_api_consultant` retry loop. Not implemented because kilo PONG legitimately returns 5 bytes — distinguishing transient-fail from terse-success requires more nuance than a simple length gate.
- **Reference**: `_calls.jsonl:67` (2026-05-03T16:42:53Z); reproducer in `swarm_runs/_kilo_debug/SELF_REVIEW_DEBUG.md`.
