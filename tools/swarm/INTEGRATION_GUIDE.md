# Swarm Integration Guide

How to add a new CLI / TUI / API engine to the swarm. Step-by-step playbook
for an IDE coding agent (or human). Every step has a copy-paste-ready snippet
plus a pointer to an existing reference adapter.

Companion: [README.md](README.md) · [SPEC.md](SPEC.md) ·
[METHODOLOGY.md](METHODOLOGY.md) · [PORTING.md](PORTING.md).

---

## 1. Decide the integration class

Three classes. Probe `<engine> --help`:

```
  has -p / --prompt or `run <msg>`  ->  CLI
  only --continue / TUI on stdin    ->  PTY
  HTTP-only (curl-able)             ->  API
```

| Class | What it is | Adapter file |
|------|-----------|--------------|
| **API** | HTTP, stateless | [`api_consult.py`](api_consult.py) — see `PROVIDERS` dict |
| **CLI** | Headless flag (`-p`, `run`, etc.) | [`worker_runner.py`](worker_runner.py) — see `call_<name>()` |
| ~~**PTY**~~ | ~~TUI-only, alt-screen, ConPTY~~ | **REMOVED 2026-05-04** with the freebuff engine. (Was: `pty_driver.py` routed via `worker_runner.call_pty_engine`.) |

Reference adapters: API → `api_consult.py::call_openai_compat`, `call_cerebras`,
`call_ollama_cloud`. CLI → `worker_runner.py::call_claude`, `call_gemini`,
`call_opencode_or_kilo`, `call_copilot`. PTY support was removed 2026-05-04.

---

## 2. Per-class checklist

### 2A. API engine

Edit five files. Example uses placeholder `myapi`.

**`api_consult.py`** — extend `PROVIDERS` and `--provider` choices:

```python
PROVIDERS = {
    # ...
    "myapi": {
        "url": "https://api.example.com/v1/chat/completions",
        "model": "myapi-default-model",
        "key_envs": ("MYAPI_KEY", "MYAPI_API_KEY"),
        "max_tokens_field": "max_tokens",   # or "max_completion_tokens"
        "max_tokens": 4000,
    },
}
```

If OpenAI-compatible, `call_openai_compat` handles it. If it has a custom SDK,
add `call_myapi()` next to `call_cerebras` / `call_ollama_cloud` and wire it in
`main()`. Add `"myapi"` to the `--provider` argparse choices.

**`safety.py`** — add to `ENGINE_REQUIRED_KEYS` (env isolation allowlist):

```python
"myapi": ("MYAPI_KEY", "MYAPI_API_KEY", "MYAPI_MODEL"),
```

Without this, the worker subprocess sees no key and fails with "no key in env".

**`config_loader.py`** — add to `ENGINE_KEY_ENVS`:

```python
"myapi": ("MYAPI_KEY", "MYAPI_API_KEY"),
```

**`worker_runner.py`** — add to `API_ENGINES` set. No new dispatch branch
needed; `call_api_consultant()` auto-handles anything in `API_ENGINES`.

**`swarm_run.py`** — add `"myapi"` to `ALL_ENGINES` tuple.

Test: see §7.

### 2B. CLI engine

Edit two files. Example uses `mycli`.

**`worker_runner.py`** — add to `CLI_ENGINES`, write `call_mycli()`, add a
dispatch branch in `main()`:

```python
CLI_ENGINES = {"claude", "gemini", "opencode", "kilo", "copilot", "mycli"}

def call_mycli(prompt: str, args: argparse.Namespace) -> tuple[str, str]:
    base = _resolve_cli("mycli")
    cmd = base + ["-p", prompt]                     # or ["run"] + stdin path
    if args.model:
        cmd += ["--model", args.model]
    rc, out, err = _run(cmd, timeout=900)            # use stdin_data=prompt if
    if rc != 0:                                      # Windows arg-quoting eats
        sys.stderr.write(f"[mycli rc={rc}] {err[-500:]}\n")  # newlines
    return out, ""                                   # 2nd val = session_id

# In main():
elif eng == "mycli":
    raw, sid = call_mycli(prompt, args)
```

**`swarm_run.py`** — add to `ALL_ENGINES`.

Reference: `call_opencode_or_kilo()` uses `stdin_data=prompt` to dodge Windows
arg-length / quoting bugs (see §8).

### 2C. PTY engine — REMOVED 2026-05-04

The PTY/TUI engine class was retired with `freebuff` on 2026-05-04
(`pty_driver.py`, `_freebuff_test_ladder.py`, `PTY_ENGINES`,
`call_pty_engine`, and the `pywinpty`/`pyte` deps were all removed).

If a future TUI engine needs adding back, the historical pattern was:
extend `--cli` choices in `pty_driver.py::main()`, tune `READY_MARKERS` /
`DONE_MARKERS` / `ABORT_MARKERS` / `_FOOTER_TOKENS`, then add the engine
name to `worker_runner.PTY_ENGINES`. See `git log --diff-filter=D --
tools/swarm/pty_driver.py` for the deleted reference implementation.

---

## 3. Output cleaner

If the engine wraps responses with tool-call markers, banners, or JSON
envelopes, add a parser to [`output_parsers.py`](output_parsers.py):

```python
def parse_mycli(raw: str) -> str:
    # regex-based filter that strips wrapper, keeps prose
    return cleaned

def parse_engine_output(engine: str, raw: str) -> str:
    if engine == "mycli":
        return parse_mycli(raw)
    # ... existing branches ...
```

Reference: `parse_copilot()` strips `●` / `✗` action lines and `│` / `└` body
lines. `parse_claude_envelope()` extracts `.result` from Claude's
`--output-format=json` envelope. The dispatch runs at
`worker_runner.main()` line `raw = parse_engine_output(eng, raw)`.

---

## 4. Schema integration

Canonical JSON contract: [`schema_review.json`](schema_review.json). Required:
`pr`, `verdict`, `confidence`, `summary`, `concerns`, `commentary_text`,
`fabrication_risk`. Engine-agnostic prompts in [`prompts/`](prompts/):
[`pr_review.md`](prompts/pr_review.md), [`merge_reviews.md`](prompts/merge_reviews.md),
[`redteam.md`](prompts/redteam.md). New engines inherit the contract for free
unless they need JSON-only framing (see `worker_runner._GEMINI_JSON_PREFIX`,
toggled via `--json-strict`).

---

## 5. Slash command registration

Optional. Add an entry to
[`.claude/commands/swarm-engines.md`](../../.claude/commands/swarm-engines.md).

---

## 6. Logging & inspect — no code changes

Three observability tools auto-pick up the new engine on first call:

- [`swarm_log.py::CallTimer`](swarm_log.py) — appends a JSONL line per call
  to `swarm_runs/_calls.jsonl`.
- [`swarm_inspect.py`](swarm_inspect.py) — derives engine from filename stem,
  not envelope (defeats self-spoofing).
- [`swarm_stats.py`](swarm_stats.py) — aggregates by engine, flags
  `LOW_OK_RATE` / `ZOMBIE_OUTPUT` / `ERRORING`.

---

## 7. Smoke test ladder

4-step verification. Replace `<name>` with your engine.

**1. PONG smoke** (30 s):

```
echo "Reply with the single word PONG and nothing else." > ping.md
python tools/swarm/worker_runner.py --engine <name> \
    --prompt-file ping.md --out-file swarm_runs/_smoke/<name>.json
```

Expect `<name>.json.raw.txt` to contain `PONG`.

**2. Asset-class brief** (90 s):

```
python tools/swarm/worker_runner.py --engine <name> \
    --prompt-file swarm_runs/briefing_asset_class_audit.md \
    --out-file swarm_runs/_smoke/<name>_brief.json
```

Expect substantive JSON >2 KB.

**3. Inspect** (5 s):

```
python tools/swarm/swarm_inspect.py swarm_runs/_smoke
```

Expect `HEALTHY`, no `ZERO`/`TINY`/`CREDITS?`/`AUTH?`/`PARSE_FAILED` flags.

**4. Fan-out via swarm_run**:

```
python tools/swarm/swarm_run.py --engines <name> \
    --prompt-file swarm_runs/briefing_asset_class_audit.md
```

Expect `_summary.json` with `ok_count >= 1`.

---

## 8. Common gotchas

| Symptom | Cause | Fix |
|--------|-------|-----|
| Multi-line prompt truncated past first newline | Windows `CreateProcess` arg-quoting | Use `stdin_data=prompt` in `_run()` (see `call_opencode_or_kilo`) |
| `UnicodeDecodeError` / mojibake in response | Default cp1252 stdout on Windows | `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` in adapter |
| Stdin piping eats prompt, only banner returned | TUI uses alt-screen (`\x1B[?1049h`) | PTY class was removed 2026-05-04; reintroduce a PTY driver if you need a TUI engine. |
| `json.JSONDecodeError` on smart quotes | Cloud model emits U+2018/2019/201C/201D/2011 | Already normalised — see `worker_runner._SMART_PUNCT` and `_extract_json_object` |
| Engine returns `engine: "gpt-4o"` regardless of caller | Model self-spoofs envelope fields | `swarm_inspect.py` derives engine from filename, not envelope (already correct) |
| `--version` hangs forever | TUI binary | `_smoke_check` treats timeout as launch-OK; raise the timeout in `_resolve_cli` if needed |
| Cost runaway from retry loops | None — there is no retry | Default behavior; do NOT add retries without a hard call-budget |

---

## 9. Reference adapters (cheat sheet)

| You're adding... | Read this first |
|------------------|-----------------|
| OpenAI-compatible API | `api_consult.py::call_openai_compat` + `PROVIDERS["deepseek"]` |
| API with vendor SDK | `api_consult.py::call_cerebras` |
| API behind a CLI binary | `api_consult.py::call_ollama_cloud` |
| Headless CLI agent (npm shim) | `worker_runner.py::call_opencode_or_kilo` + `_resolve_cli` |
| CLI with JSON envelope | `worker_runner.py::call_claude` + `output_parsers.parse_claude_envelope` |
| CLI that emits tool-call markup | `output_parsers.py::parse_copilot` |
| TUI / alt-screen | (removed 2026-05-04 with freebuff — see git history) |
| Engine that ignores in-prompt JSON | `worker_runner._GEMINI_JSON_PREFIX` (`--json-strict`) |
| Long-prompt TUI workaround | (removed 2026-05-04 with freebuff) |

Copy the most-similar `call_*()` and edit the binary path + flags.
