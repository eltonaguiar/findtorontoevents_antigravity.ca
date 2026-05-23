# Kimi swarm vs Ours — Merge Plan

Comparison between `tools/swarm/` (ours, Claude Code rebuild) and
`swarm_runs/kimi_swarm_compare/ai-swarm/` (Kimi extracted spec + impl).

Source-of-truth files referenced throughout:
- Ours: `tools/swarm/{SPEC.md, worker_runner.py, swarm_dispatch.ps1, schema_validate.py, schema_review.json, swarm_log.py, comment_poster.ps1, swarm.config.example.json}`
- Kimi: `swarm_runs/kimi_swarm_compare/ai-swarm/ai_swarm/{cli.py, config.py, orchestrator.py, swarm_engine.py, session_manager.py, safety.py, adapters/*}` + `tests/test_core.py` + `examples/*.yaml`

---

## Section 1 — Architecture diff

### Ours (PowerShell-orchestrated, file-bus, sync subprocess)
```
swarm_dispatch.ps1
   |-- Start-Job (PR x engine grid, MaxParallel throttle = polling sleep)
   |       \-- python worker_runner.py --engine X --pr N --out-file ...
   |               \-- subprocess.run (sync, blocking) -> CLI or api_consult.py
   |               \-- writes pr_<n>.<eng>.json + .raw.txt sidecar
   |               \-- swarm_log.CallTimer -> swarm_runs/_calls.jsonl
   |-- schema_validate.py per file (exit-code gate)
   |-- merge-captain (claude opus) -> final_merge_plan.json
   |-- redteam (claude opus)       -> redteam.json
   \-- comment_poster.ps1 (only writer; y/N gate; gh pr comment)
```
Bus = filesystem + JSONL log. Synchronous Python subprocess inside parallel PS jobs.

### Kimi (Python-async, in-process, model objects)
```
cli.py (click) -> Orchestrator
   |-- load_config (YAML + ${ENV} substitution + .env via python-dotenv)
   |-- SwarmEngine(SafetyEnforcer, SessionManager)
   |       |-- run_parallel  (asyncio.gather + Semaphore(max_workers))
   |       |-- run_sequential (cumulative context fed forward)
   |       |-- run_voting   (verdict tally, consensus threshold)
   |       |-- aggregate    (merge-captain pass)
   |       \-- red_team     (red-team pass)
   |-- adapters/*.py  (async subprocess via asyncio.create_subprocess_exec)
   |-- session_manager.py (sqlite at ~/.ai-swarm/sessions.db)
   \-- safety.py (env isolation, read-only enforcement, evidence validator)
```
Bus = in-memory pydantic objects (`SwarmResult.worker_results[]`). Optional JSON dump on demand.

### Output flow
- Ours: every artefact lives on disk under `swarm_runs/<TS>/`. Resumable / inspectable from any tool. Comment-poster reads finished JSON.
- Kimi: artefacts only on disk if you `--json-output`; sessions persist in sqlite; no comment-poster.

ASCII summary
```
            Orchestrator      Workers       IPC          Result store    Writer
Ours        PowerShell jobs   sync py       files+JSONL  swarm_runs/<TS> comment_poster.ps1
Kimi        asyncio (Python)  async py      pydantic     in-memory+sqlite  (none)
```

---

## Section 2 — Capability matrix

| Capability                          | Ours                                              | Kimi                                               | Best   |
|-------------------------------------|---------------------------------------------------|----------------------------------------------------|--------|
| Engines supported                   | 10 (claude/gemini/opencode/kilo/copilot + 5 API)  | 6 adapters (claude_code, gemini, opencode, kilocode, copilot, openai_api) | Ours |
| Headless mechanism                  | `subprocess.run` + `--print` flags; stdin fallback for opencode/kilo to dodge Win arg-quoting (`worker_runner.py:152-164`) | `asyncio.create_subprocess_exec`; positional prompt arg (no stdin fallback) | Ours |
| JSON contract enforcement           | `schema_validate.py` + `schema_review.json` (severity↔evidence rule, enums) | None — pydantic validates `WorkerResult` shape, but no per-engine JSON schema gate | **Ours** |
| Schema validation                   | jsonschema lib + handrolled fallback              | pydantic `model_validate` only                     | Ours   |
| Logging                             | `swarm_runs/_calls.jsonl` thread-safe append; `low_signal` flag; `swarm_stats.py` aggregator (LOW_OK_RATE/ZOMBIE/ERRORING) | duration_ms only on `WorkerResult`; no append-only call log | **Ours** |
| Session resume                      | `--session-id` / `--resume` flags forwarded to claude only | Generic `SessionManager` with sqlite + replay history for ALL adapters (incl. API) | **Kimi** |
| Red-team pass                       | Hardcoded after merge (`swarm_dispatch.ps1:159-176`) using opus | First-class `SwarmEngine.red_team()` + `SafetyConfig.red_team_enabled` toggle | Kimi |
| Merge-captain pass                  | Hardcoded; concatenates valid JSONs + `merge_reviews.md` (`swarm_dispatch.ps1:137-157`) | First-class `aggregate()` method; pluggable aggregator tool | Kimi |
| Comment-posting safety              | `comment_poster.ps1` is sole writer; per-PR y/N gate; tmp-file lifecycle in `finally` | None — Kimi has no comment-posting layer; would have to be built | **Ours** |
| Portability                         | Win-centric (`%APPDATA%/npm`, PowerShell jobs, `.cmd`/`.ps1` resolution) | Cross-platform (`shutil.which`, asyncio); pip-installable (`pyproject.toml`) | **Kimi** |
| Tests                               | Fixtures only (`fixtures/{good,bad}.json`)        | `tests/test_core.py`: 11 unit tests (config sub, safety, sessions, models) | **Kimi** |
| Examples / templates                | `swarm.config.example.json` (reference only, not auto-loaded) | `examples/{pr_review_swarm,multi_model_qa}.yaml` consumed by `cli swarm --config` | Kimi |
| Env-var substitution                | Ad-hoc; expects exported env vars (no `.env`)     | `${VAR}` recursion + `python-dotenv` + unresolved-var detector (`config.py:38-86`) | **Kimi** |
| Sequential / voting modes           | None — only parallel fan-out                      | `run_sequential`, `run_voting` with consensus threshold (`swarm_engine.py:110-165`) | Kimi |
| Asset-class specialist personas     | 6 personas + INDEX (`agent_personas/`)            | None                                              | **Ours** |
| `.claude/agents/` Task-tool subagents | 5 (pr-reviewer, fabrication-red-team, merge-captain, dashboard-contract-reviewer, quant-performance-auditor) | None — Kimi has no Claude subagent format | **Ours** |
| `{{PR_NUMBER}}` interpolation       | Yes (`worker_runner._read_prompt`)                | No — prompt passed as-is                           | Ours   |
| Project-specific PR review steps    | Yes — `pr_review.md` cites template.html, dashboard_data.json, dashboard_generator.py | Generic — no repo-specific paths                 | Ours (rightly) |

---

## Section 3 — Strengths Kimi has that we lack

1. **`safety.py:SafetyEnforcer`** (`ai_swarm/safety.py:1-99`)
   - Centralised read-only enforcement that *clones* a `ToolConfig` and adds disallowed-tools (`Edit`, `Bash(git push:*)`, `Bash(rm:*)`, `Bash(mv:*)`, `Bash(cp:*)`, `Write`).
   - `check_git_status` post-run sanity check (verifies no files mutated).
   - Why it matters: ours hardcodes claude allowlist inside `worker_runner.call_claude`; non-claude engines have no enforcement.
   - Mergeable: **yes**.

2. **`session_manager.py`** (`ai_swarm/session_manager.py:1-165`)
   - Sqlite-backed cross-engine session store with `record_message` / `record_result` / `export_session`.
   - We only thread `--session-id` to claude; can't resume gemini/opencode/api workers.
   - Mergeable: **yes** as a sidecar (write `swarm_runs/_sessions.db` next to `_calls.jsonl`).

3. **`config.py:_substitute_env_vars` + `_find_unresolved_vars`** (`ai_swarm/config.py:27-86`)
   - Recursive `${VAR}` expansion + `.env` autoload + hard-fail on unresolved keys.
   - Ours requires user to pre-export env vars; silently fails downstream.
   - Mergeable: **yes** — port the two helpers as `tools/swarm/config_loader.py`.

4. **YAML examples consumed by CLI** (`ai_swarm/examples/{pr_review_swarm,multi_model_qa}.yaml`)
   - Per-tool `read_only`, `allowed_tools`, `disallowed_tools`, `timeout` declarative.
   - Our `swarm.config.example.json` is reference-only.
   - Mergeable: **yes** if we add a YAML loader; otherwise translate to JSON and have `swarm_dispatch.ps1` consume it.

5. **Pydantic `ToolConfig`/`SwarmConfig`/`WorkerResult`** (`ai_swarm/models/`)
   - Typed config with validation; would replace ad-hoc dict access in our PS layer.
   - Mergeable: **partial** — would force a Python-side rewrite of `swarm_dispatch.ps1` orchestrator. Significant.

6. **Voting mode + consensus thresholding** (`swarm_engine.py:133-165`)
   - Tally `verdict` keys across workers, set `final_verdict` if ≥75% agree.
   - We compute consensus inside `merge_reviews.md` prompt; explicit numeric tally is more auditable.
   - Mergeable: **yes** as a Python post-processor on validated outputs.

7. **`tests/test_core.py`** with `:memory:` SessionManager DB and env-var substitution coverage.
   - We have fixtures but no asserts.
   - Mergeable: **yes** — port the test patterns even if implementation differs.

8. **Async parallelism + semaphore** (`swarm_engine.run_parallel`).
   - We use `Start-Job` with a busy-wait `Start-Sleep -Milliseconds 500` throttle (`swarm_dispatch.ps1:73`). Async is cleaner.
   - Mergeable: **yes** but only if we go Python-native orchestrator (large refactor).

9. **`copilot.supports_parallel = False` honest annotation** (`adapters/copilot.py:24`)
   - Documents a known session-leak quirk.
   - Mergeable: **yes** — copy the comment into our `swarm.config.example.json`.

10. **`pyproject.toml` packaging** — pip-installable, console-script entrypoint `ai-swarm`.
    - We're a flat folder with `requirements.txt`.
    - Mergeable: **yes** if we want users to install across repos.

---

## Section 4 — Strengths we have that Kimi lacks

1. **`schema_validate.py` + `schema_review.json` evidence-required rule**
   (`schema_validate.py:63-68`: blocking/major concerns must have non-empty evidence; strengths must have evidence).
   - Hard gate at the file boundary; rejects fabricated outputs before they reach merge-captain.
   - Kimi only validates pydantic shape, not the *evidence contract*. Critical anti-fabrication primitive.
   - Keep ours.

2. **`swarm_log.py` + `swarm_runs/_calls.jsonl` + `swarm_stats.py`**
   - Append-only thread-safe call log; `low_signal` flag (output<50 bytes or rc≠0); `LOW_OK_RATE`/`ZOMBIE_OUTPUT`/`ERRORING`/`UNUSED` flags by engine.
   - Kimi has nothing equivalent.
   - Keep ours; this is the engine-health surface.

3. **`comment_poster.ps1`** — only-writer principle, per-PR y/N, tmp-file in `finally`.
   - Kimi has zero write path. Ours is auditable + reviewable.
   - Keep ours.

4. **API engines via `api_consult.py`** — deepseek/cerebras/xai/inception/ollama_cloud.
   - Kimi covers OpenAI-compatible HTTP but no per-provider CLI shim. Inception/Cerebras have non-OpenAI quirks.
   - Keep ours; Kimi's `openai_api.py` is a subset.

5. **Windows-quoting workaround for opencode/kilo** (`worker_runner.py:152-164`).
   - Long prompts truncated at first newline when passed positionally on Win; we pipe via stdin. Kimi passes positional → will silently truncate.
   - Keep ours; port the *fix* into Kimi's adapters if anyone goes that direction.

6. **`{{PR_NUMBER}}` interpolation + context-md preamble** (`worker_runner._read_prompt`).
   - Multi-stage pipelines (worker → merge → redteam) reuse the same prompt template with different inputs.
   - Kimi has no template-token system.

7. **`.claude/agents/*.md` Task-tool subagents** + 6 asset-class personas.
   - Specific to claude-code's named-subagent feature; not portable but high-leverage for our workflow.
   - Keep.

8. **JSON-extraction fallback synthesizer** (`worker_runner.py:245-255`).
   - When raw output isn't JSON we still emit a schema-valid `COMMENT_ONLY/LOW/HIGH-fab-risk` envelope referencing the raw sidecar — downstream stages never crash on a bad worker.
   - Kimi returns `{"raw": ...}` and lets the caller deal with it.

9. **Project-specific PR-review prompt clauses** referencing `audit_dashboard/template.html`, `dashboard_data.json`, `quality_gates.py`.
   - Bakes the wiring rules into the prompt; less context-bleed.
   - Keep.

10. **`MANIFEST.txt` + `PORTING.md`** — explicit portability boundary doc.
    - Kimi has no such doc.

---

## Section 5 — Merge plan: adopt from Kimi (ranked)

| # | Item                                                    | Files to touch in `tools/swarm/`                                                  | Effort | Risk |
|---|---------------------------------------------------------|-----------------------------------------------------------------------------------|--------|------|
| 1 | Env-var substitution + `.env` autoload + unresolved-key fail | New `config_loader.py` (port `_substitute_env_vars`, `_find_unresolved_vars` from `ai_swarm/config.py:27-86`); call from `worker_runner.main` and `api_consult.py` | S | low |
| 2 | YAML config consumed by dispatcher                      | New `swarm.config.example.yaml`; update `swarm_dispatch.ps1` to optional `-ConfigFile` and read `engines`/`prs`/defaults from YAML via `ConvertFrom-Yaml` (or add small Python helper) | S-M | low |
| 3 | Centralised read-only enforcement for non-claude engines | New `tools/swarm/safety.py`: clone allowlist/disallowlist logic from `ai_swarm/safety.py:45-57`; have `worker_runner.call_gemini`/`call_opencode_or_kilo`/`call_copilot` consult it | S | low |
| 4 | Sqlite session store (sidecar)                          | New `tools/swarm/session_db.py` (port `ai_swarm/session_manager.py`, change default db to `swarm_runs/_sessions.db`); add `--record-session` flag to `worker_runner.py` | M | low — sidecar only, not on hot path |
| 5 | Voting/consensus tallier as Python post-processor       | New `tools/swarm/consensus.py`: read all `pr_<n>.<eng>.json` in run dir, tally `verdict`, emit `_consensus.json` with thresholds; called from `swarm_dispatch.ps1` after schema_validate, before merge-captain | S | low |
| 6 | Real `pytest` tests against fixtures                    | New `tools/swarm/tests/test_schema.py` mirroring `test_core.py` patterns (good/bad fixtures, env-var sub, allowlist enforcement) | S | low |
| 7 | Sequential mode (chain workers with cumulative context) | New `--mode sequential` in `swarm_dispatch.ps1`; concat prior raw outputs into `--context-md` for next worker (already supported by `worker_runner._read_prompt`) | S | low |
| 8 | `git status --porcelain` post-run safety check          | Bolt onto `worker_runner.main` after subprocess returns; warn if read-only worker mutated tree | S | low |
| 9 | Pip packaging (optional)                                | New `pyproject.toml` exporting `tools/swarm/*.py`; `console_scripts: swarm-worker = worker_runner:main` | S | low |
| 10 | `WorkerResult` pydantic shape (replace dict envelopes) | Refactor `worker_runner._extract_json_object` to return a typed `WorkerResult`; would bleed into schema_validate | M-L | medium — touches contract; defer |

Do NOT adopt the Kimi orchestrator wholesale. The PowerShell file-bus is the right primitive for our environment (auditability, restartability, peer-discoverable artefacts).

---

## Section 6 — Do NOT adopt

- **Kimi's pydantic-first config + Python-async orchestrator as the primary dispatcher.**
  Rationale: rewriting `swarm_dispatch.ps1` into Python loses (a) the `swarm_runs/<TS>/` tree-as-bus model that lets peers (claude-peers MCP) and humans inspect intermediate state, (b) PowerShell `Start-Job` debugging via `_job_*.log`, (c) integration with our `comment_poster.ps1` `gh` write-gate. Net cost > value.

- **`adapters/openai_api.py` as a replacement for `api_consult.py`.**
  Rationale: ours handles cerebras/inception/ollama-cloud quirks (e.g., `ollama_cloud` shells out to `ollama run` because the cloud key is an SSH push key, not a chat token — see `swarm.config.example.json` line 21). Kimi's generic `AsyncOpenAI` client would silently fail on those.

- **`adapters/claude_code.py:53` `--disallowedTools` packed comma-separated.**
  Claude code expects them as separate `--disallowedTools X --disallowedTools Y` args (which is what ours does at `worker_runner.py:124-127`). Kimi's `",".join(...)` is wrong on current claude CLI; do not copy this pattern.

- **`session_id = f"claude-{id(result)}"` fallback** (`adapters/claude_code.py:129`).
  Synthesises a non-resumable id; ours forwards the *real* `--session-id` from the JSON envelope (`worker_runner.py:131-134`). Keep ours.

- **In-memory `_sessions: dict` in `openai_api.py:33`.**
  Loses on process restart. If we adopt session storage, use the sqlite path (item #4 above), not the dict.

- **Generic `red_team_prompt` default text in `swarm_engine.py:207-211`.**
  Ours has a project-specific `redteam.md` requiring `confirmed/refuted/unverified` with `final_severity` — much stronger than Kimi's free-form prompt.

- **`adapters/gemini.py:81` accepting `returncode in (0, 53)` as success.**
  53 is "turn limit hit" — should be flagged, not silently OK. Our path treats any rc≠0 as warning; keep ours.

- **Kimi's `prompts/pr_review.md`.** It's generic; ours is wired to `findtorontoevents.ca` paths (template.html, dashboard_data.json, quality_gates.py). Project-specific by design.

---

## Section 7 — Adapter comparison: Kimi `claude_code.py` vs ours `worker_runner.call_claude`

Files: `swarm_runs/kimi_swarm_compare/ai-swarm/ai_swarm/adapters/claude_code.py:1-143` vs `tools/swarm/worker_runner.py:106-138`.

### Error handling
- **Kimi**: 3 explicit branches — `proc.returncode != 0` → `WorkerResult(status="error")`; `asyncio.TimeoutError` → `status="timeout"`; bare `Exception` → `status="error"`. Always returns a `WorkerResult` (never raises to caller).
- **Ours**: prints `[claude rc={rc}] {err[-500:]}` to stderr and returns `(text, sid)`. Caller (`worker_runner.main`) wraps in `try/except` for `subprocess.TimeoutExpired` (rc=4) and bare `Exception` (rc=5); `CallTimer` records.
- Diff: Kimi captures more state (duration_ms, error_message) inside the adapter; ours splits state across `CallTimer` + main loop. Kimi's model is cleaner per-call, ours yields better cross-call aggregates via `_calls.jsonl`. **Adopt:** keep ours, but add the `error_message[:500]` field to the synth-fallback envelope.

### Tool allowlist
- **Kimi** (`claude_code.py:36-54`):
  - Builds `--allowedTools <csv>` and `--disallowedTools <csv>` from `config.allowed_tools` / `config.disallowed_tools`.
  - If `config.read_only` adds `--disallowedTools "Edit,Bash(git push:*),Bash(gh pr merge:*),Bash(gh pr comment:*)"` as a single comma-joined string.
  - **Bug**: Claude CLI expects each allowlist entry as a separate flag value or space-separated list, not comma-joined; the comma form is parsed as a single literal tool name and silently disables enforcement. (Verify with `claude --help`.)
- **Ours** (`worker_runner.py:120-127`): hardcoded list of separate tokens after a single `--allowedTools` and a single `--disallowedTools`, each token its own arg. This matches what current claude code accepts.
- **Adopt:** keep ours. If we externalise the allowlist to YAML (Section 5 #2), preserve the per-token splitting.

### Session management
- **Kimi**: no real `--session-id` use; `start_session` calls `run_once` then synthesises `f"claude-{id(result)}"` as the id. Follow-ups call `run_once` with that synthetic id, which claude has never seen — so claude starts fresh each time. **Effectively broken.**
- **Ours**: `--session-id <uuid>` and `--resume <uuid>` flags forwarded directly to claude CLI; we extract `session_id` from claude's JSON envelope and write it into `_swarm_meta.session_id` (`worker_runner.py:131-138, 260`). Resumable for real.
- **Adopt:** keep ours. If we want Kimi's cross-engine session abstraction, layer the sqlite store on top *and* keep the real claude session id.

### Output parsing
- **Kimi** (`claude_code.py:60-64`): tries `json.loads(raw)` once; on fail returns `{"raw": raw}` as `structured_output`. No code-fence stripping, no bracket-scan fallback.
- **Ours** (`worker_runner.py:57-83`): strips ```json fences via regex; bracket-depth scanner picks the first balanced object if direct parse fails; if all fail, synthesises a schema-valid envelope with `verdict=COMMENT_ONLY` / `confidence=LOW` / `fabrication_risk=HIGH` so downstream merge-captain still gets typed input.
- **Adopt:** keep ours. Kimi's `{"raw": ...}` would fail `schema_validate.py` and exclude the worker from merge — we'd lose visibility into low-confidence contributions.

### Net call
Ours is more robust on the four hot axes (errors, allowlist, sessions, parsing). Kimi's win is only the structural one — typed `WorkerResult` and async — which is orthogonal and adoptable later (Section 5 #10) if we ever rewrite the orchestrator.

---

## Top-3 bottom line

**Adopt from Kimi (low-risk, high-value):**
1. Env-var substitution + `.env` autoload + unresolved-key hard-fail (Section 5 #1).
2. Centralised read-only enforcement for *non-claude* engines via a new `safety.py` (Section 5 #3).
3. YAML config consumed by `swarm_dispatch.ps1` + sqlite session sidecar (Section 5 #2 + #4).

**Keep ours:**
1. `schema_validate.py` + `schema_review.json` evidence-required rule.
2. `swarm_log.py` + `_calls.jsonl` + `swarm_stats.py` engine-health surface.
3. `comment_poster.ps1` only-writer + y/N gate.
