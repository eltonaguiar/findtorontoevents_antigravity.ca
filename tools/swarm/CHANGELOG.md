# tools/swarm — Changelog

Per-day commit log of swarm-related changes. Format: [Keep a
Changelog](https://keepachangelog.com/en/1.1.0/) + commit SHA prefixes.

## 2026-05-04

### Removed

- **Freebuff engine deleted** (TUI-only PTY engine, low usage):
  - `tools/swarm/pty_driver.py` — `git rm`'d (was the ConPTY/pyte driver;
    no other engine used it).
  - `tools/swarm/_freebuff_test_ladder.py` — `git rm`'d.
  - `worker_runner.py`: dropped `PTY_ENGINES` set, `call_pty_engine()`
    function, dispatch branch, and docstring mentions.
  - `swarm_run.py`: dropped from `ALL_ENGINES` and `COST_PER_1K_TOKENS`.
  - `swarm_followup.py`: dropped from `ALL_ENGINES`.
  - `swarm_inspect.py`: dropped `FREEBUFF_BANNER_RE` and the `TUI_ONLY` flag
    (only ever fired for freebuff).
  - `safety.py`: dropped env tuple entry.
  - `swarm.config.example.json`: dropped `excluded_engines.freebuff`.
  - `requirements.txt`: dropped `pywinpty>=2.0` and `pyte>=0.8` (the PTY
    driver was their only consumer).
  - Docs scrubbed: README.md, AGENTS_HOWTO.md, POST_RUN_OPTIONS.md, SPEC.md,
    SWARM_DESIGN_NOTES.md, PORTING.md, METHODOLOGY.md, INTEGRATION_GUIDE.md,
    MANIFEST.txt. Historical entries below are preserved verbatim.

## 2026-05-03

Initial swarm shipment. Nine commits; chronological order below.

### Fixed (Kimi-flagged S-effort wins, items 3-6)

Per [`swarm_runs/KIMI_AUDIT_RESPONSE.md`](../../swarm_runs/KIMI_AUDIT_RESPONSE.md)
action queue items 3-6.

- **Item 3 — `swarm_inspect.py` recurses into per-engine subdir layout.**
  `inspect_run()` now follows the existing flat-layout walk with a
  one-level recursion into immediate subdirs that contain `pr_*.json`
  files (e.g. `pr_review_<TS>/<engine>/pr_724.json`). Engine name is
  derived from the parent directory unless the filename carries an
  explicit dot-suffix (in which case the filename wins). Verified
  against `swarm_runs/new_engine_audit_20260503T175428Z/<engine>/`
  which now reports `engines=15 healthy=3 suspect=10` instead of zero.
  Closes Kimi-missed-#2 (HIGH severity).
- **Item 4 — ZOMBIE threshold uses schema-validity on top of byte count.**
  New helper `swarm_log._envelope_has_substance(raw)` does an inline
  JSON poke (no `schema_validate` import to avoid circular dep) and
  checks for any of `concerns / strengths / commentary_text / answer /
  summary / q1_per_class` populated above the substance threshold.
  `CallTimer.set_output()` now stashes up to 8 KB of the raw response
  on `_raw`; `__exit__` runs the substance check when the response
  cleared the >=50-byte gate but failed substance, marks `low_signal`
  True, and appends `empty_envelope` to `error` (without clobbering a
  pre-existing transport error). Closes Kimi-missed-#3 (MEDIUM).
- **Item 5 — `_pr_capture._ascii_safe` preserves emoji.** The original
  strip-all-non-BMP logic existed to dodge a cp1252 encoding crash
  downstream; that root cause is now fixed at the env layer
  (`worker_runner.call_api_consultant` injects `PYTHONIOENCODING=utf-8`
  + `PYTHONUTF8=1`). The sanitiser now drops only C0 control chars
  (minus `\t \n \r`) and lone surrogates. Emoji urgency markers
  (🟢/🔴/🚀/etc.) reach the engine intact, restoring PR-severity
  signal in inline-diff prompts. Closes Kimi-missed-#5 (MEDIUM).
- **Item 6 — `_calls.jsonl` rows now carry `"v": "1"` as the first
  field.** New `SCHEMA_VERSION` constant in `swarm_log.py`. Future
  field add/rename/remove bumps to v2/v3/etc.; missing `v` = pre-imp-B
  legacy row. Reader contract + bump rules documented in
  [`SPEC.md`](SPEC.md) §"Logging schema versioning". `swarm_stats.py`
  is already missing-key-safe so legacy + v=1 rows interleave cleanly.
  Closes architectural-undo-#3.

### Added (post-shipment)

- Added: OpenAI `codex` CLI integration (`@openai/codex` v0.128.0+) as 9th
  headless CLI engine.
  - Update: [`worker_runner.py`](worker_runner.py) — `codex` in `CLI_ENGINES`;
    new `call_codex()` uses `codex exec --skip-git-repo-check --sandbox
    read-only --json -c approval_policy="never"` and parses JSONL events
    (`thread.started.thread_id` -> session id; `item.completed` items where
    `item.type=="agent_message"` -> response text; `turn.completed.usage`
    -> token counts); dispatch branch in `main()`.
  - Update: [`swarm_run.py`](swarm_run.py) — `codex` added to `ALL_ENGINES`
    and `COST_PER_1K_TOKENS` (ChatGPT OAuth-bundled, $0).
  - Update: [`safety.py`](safety.py) — `ENGINE_REQUIRED_KEYS["codex"] =
    ("OPENAI_API_KEY", "CODEX_HOME")` (OAuth-primary; key vars are optional
    CI overrides).
  - Update: [`config_loader.py`](config_loader.py) — `ENGINE_KEY_ENVS["codex"] =
    ("OPENAI_API_KEY",)`.
  - Update: [`README.md`](README.md), [`SPEC.md`](SPEC.md),
    [`SWARM_DESIGN_NOTES.md`](SWARM_DESIGN_NOTES.md) — engine matrix rows
    + KFMs (ChatGPT usage cap; auto-runs tools by default, inflating
    input-token usage 5-10x).
  - New: [`fixtures/codex_brief_response.json`](fixtures/codex_brief_response.json)
    — 11 KB structured-JSON brief response captured from the smoke ladder
    as a regression-fixture for future codex output-shape changes.

- Post-run options footer + [`POST_RUN_OPTIONS.md`](POST_RUN_OPTIONS.md)
  master doc. Every dispatcher (`swarm_run.py`, `swarm_dispatch.ps1`,
  `swarm_followup.py`) now prints a terse `NEXT STEPS` reminder to stdout
  covering inspect, red-team, resume, multi-turn, persona, strictness,
  preset switch. Long-form details (12 sections: inspect / contract /
  iterations / persona / presets / cost / hooks / multi-cycle / PR /
  GH-actions / patterns / when-not-to-rerun) live in `POST_RUN_OPTIONS.md`.
  Slash commands `/swarm run` and `/swarm followup` also surface the
  reminder.
- **17:50** — `openclaude` (`@gitlawb/openclaude` v0.7.0, third-party Claude
  Code fork with multi-provider routing) integrated as a headless CLI
  engine. Key value: a single `--provider openai|gemini|deepseek|...` flag
  routes to OpenAI / Gemini / DeepSeek / Anthropic / GitHub Models /
  Bedrock / Vertex / Foundry / Ollama, giving the swarm provider diversity
  beyond the OAuth-bundled CLI fleet without standing up another API
  consultant.
  - Update: [`worker_runner.py`](worker_runner.py) — `CLI_ENGINES` adds
    `openclaude`; new `call_openclaude()` mirrors `call_claude` shape
    (`-p <prompt> --output-format json`) with the swarm `--model` arg
    re-mapped onto openclaude's `--provider` flag. Default provider is
    `openai` (OPENAI_API_KEY); `OPENCLAUDE_PROVIDER` env overrides the
    default; per-run `--model deepseek|gemini|...` overrides both.
    Dispatch branch in `main()`.
  - Update: [`swarm_run.py`](swarm_run.py) — `openclaude` added to
    `ALL_ENGINES` and `COST_PER_1K_TOKENS` (gpt-4o-mini list price as
    conservative default; cost estimate becomes APPROXIMATE if user routes
    to a pricier provider — see openrouter caveat for the same shape).
  - Update: [`safety.py`](safety.py) — `ENGINE_REQUIRED_KEYS["openclaude"]`
    passes through the union of provider keys it may consult
    (OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY/_API,
    GEMINI_API_KEY, GOOGLE_API_KEY, GH_TOKEN, GITHUB_TOKEN,
    OPENCLAUDE_PROVIDER).
  - Trust caveat: third-party package, not Anthropic-published. v0.7.0
    audited 2026-05-03: no postinstall/preinstall hooks in `package.json`,
    no `scripts/` shipped on disk (only `bin/openclaude`, `dist/cli.mjs`,
    `LICENSE`, `README.md`), all deps are standard Anthropic SDKs +
    well-known OSS libs. Re-audit before each upgrade. Do not install on
    production-secret hosts without re-verification.
  - Smoke ladder (2026-05-03 17:47-17:49Z): PONG ok (rc=0, 4B raw),
    brief.md 6.9KB ok (rc=0, 241B response, 36s), persona injection
    technically wired (persona text reaches CLI; gpt-4o-mini gave a weak
    answer — model-quality issue, not transport), 2-engine fanout 2/2 ok
    (openclaude 36.4s + deepseek 4.2s).

- **18:00** — Kimi CLI (Moonshot AI) integration as 7th headless CLI engine.
  - Update: [`worker_runner.py`](worker_runner.py) — `CLI_ENGINES` adds
    `kimi`; new `_resolve_kimi_cli()` (custom resolver: `KIMI_CLI` env >
    VS Code extension bundle at
    `%APPDATA%/Code/User/globalStorage/moonshot-ai.kimi-code/bin/kimi/kimi.exe`
    > `~/.vscode/extensions/moonshot-ai.kimi-code-*/bin/kimi/` > PATH); new
    `call_kimi()` (`--quiet -p <prompt>`; `--quiet` =
    `--print --output-format text --final-message-only`; `--print` implies
    `--yolo`); dispatch branch in `main()`. Output is clean prose (no
    envelope, no parser needed). Session resume: `--session <id>` /
    `--continue`.
  - Update: [`swarm_run.py`](swarm_run.py) — `kimi` added to `ALL_ENGINES`
    and `COST_PER_1K_TOKENS` (Moonshot OAuth-bundled, $0).
  - Update: [`safety.py`](safety.py) — `ENGINE_REQUIRED_KEYS["kimi"] =
    ("KIMI_API_KEY", "MOONSHOT_API_KEY", "KIMI_CLI")` (OAuth-primary; key
    vars are optional CI overrides; `KIMI_CLI` is a binary-path override).
  - Update: [`config_loader.py`](config_loader.py) —
    `ENGINE_KEY_ENVS["kimi"] = ("KIMI_API_KEY", "MOONSHOT_API_KEY")` for
    `/swarm engines` key inventory output.
  - Update: [`README.md`](README.md), [`SPEC.md`](SPEC.md) — engine
    matrix rows added; engine count bumped 9 → 11 (kimi + openrouter).
  - Smoke: PONG ~3.5s, 6.8 KB asset-class brief in 30s producing 10.7 KB
    JSON, persona injection (crypto-specialist) clearly shapes output,
    fan-out `kimi,deepseek` 2/2 OK in 10.3s. Auth via `kimi login` (token
    under `~/.kimi/`); `KIMI_API_KEY` already populated in env.

- **17:55** — OpenRouter API engine (OpenAI-compat gateway, 200+ models).
  - Update: [`api_consult.py`](api_consult.py) — `PROVIDERS["openrouter"]`
    + `SAMPLING_DEFAULTS["openrouter"]`; `_post()` learned an
    `extra_headers` kwarg; `call_openai_compat()` attaches OpenRouter's
    `HTTP-Referer` + `X-Title` etiquette headers (rate-limit attribution
    + leaderboard credit) for `provider == "openrouter"` only — other
    OpenAI-compat providers see the same minimal header set as before.
  - Update: [`safety.py`](safety.py) —
    `ENGINE_REQUIRED_KEYS["openrouter"] = ("OPENROUTER", "OPENROUTER_MODEL")`.
  - Update: [`config_loader.py`](config_loader.py) —
    `ENGINE_KEY_ENVS["openrouter"] = ("OPENROUTER",)`.
  - Update: [`worker_runner.py`](worker_runner.py) — `openrouter` added
    to `API_ENGINES` so dispatch routes through `call_api_consultant`.
  - Update: [`swarm_run.py`](swarm_run.py) — `openrouter` added to
    `ALL_ENGINES` and `COST_PER_1K_TOKENS` (default-model rate;
    APPROXIMATE for non-default model overrides — see SPEC caveat).
  - Update: [`README.md`](README.md), [`SPEC.md`](SPEC.md) — engine
    matrix rows added; cost-cap caveat documented.
  - Default model: `openai/gpt-4o-mini` ($0.15/M in, $0.60/M out).
    Override via `OPENROUTER_MODEL` env or `--model openai/gpt-4o-mini`
    / `anthropic/claude-haiku-4.5` / `x-ai/grok-2` / etc.

- **17:30** — Cursor `agent` CLI integration as 6th headless CLI engine.
  - Update: [`worker_runner.py`](worker_runner.py) — `CLI_ENGINES` adds
    `agent`; new `_resolve_cursor_agent()` (custom resolver because the
    binary lives at `%LOCALAPPDATA%/cursor-agent/cursor-agent.cmd`, not
    `%APPDATA%/npm`); new `call_agent()` (`-p --output-format json
    --force`; positional prompt — stdin blocks on tty); dispatch branch
    in `main()`.
  - Update: [`swarm_run.py`](swarm_run.py) — `agent` added to
    `ALL_ENGINES` and `COST_PER_1K_TOKENS` (subscription-bundled, $0).
  - Update: [`safety.py`](safety.py) — `ENGINE_REQUIRED_KEYS["agent"] =
    ("CURSOR_API_KEY", "CURSOR_AGENT_CLI")` (OAuth-primary; key vars are
    optional CI overrides).
  - Update: [`output_parsers.py`](output_parsers.py) — new
    `parse_agent_envelope()` extracts `.result` from cursor-agent's JSON
    envelope; wired into `parse_engine_output` dispatch as
    belt-and-suspenders to `worker_runner.call_agent`'s upstream
    extract.
  - Update: [`README.md`](README.md), [`SPEC.md`](SPEC.md) — engine
    matrix rows added.

### Added

- **09:57 [`fb9ee89`](../../.git)** — Kimi-style local agent swarm + asset-class consultation.
  - New: [`worker_runner.py`](worker_runner.py),
    [`swarm_dispatch.ps1`](swarm_dispatch.ps1),
    [`comment_poster.ps1`](comment_poster.ps1),
    [`swarm_log.py`](swarm_log.py), [`swarm_stats.py`](swarm_stats.py),
    [`schema_validate.py`](schema_validate.py),
    [`schema_review.json`](schema_review.json),
    [`api_consult.py`](api_consult.py),
    [`README.md`](README.md), [`SPEC.md`](SPEC.md),
    [`PORTING.md`](PORTING.md), [`MANIFEST.txt`](MANIFEST.txt),
    [`requirements.txt`](requirements.txt),
    [`swarm.config.example.json`](swarm.config.example.json).
  - Prompts: [`prompts/pr_review.md`](prompts/pr_review.md),
    [`prompts/merge_reviews.md`](prompts/merge_reviews.md),
    [`prompts/redteam.md`](prompts/redteam.md).
  - Personas: [`agent_personas/INDEX.md`](agent_personas/INDEX.md) +
    six asset-class specialists (bond / commodity / crypto / equity /
    etf / forex).
  - Subagents: [`.claude/agents/pr-reviewer.md`](../../.claude/agents/pr-reviewer.md),
    [`fabrication-red-team.md`](../../.claude/agents/fabrication-red-team.md),
    [`merge-captain.md`](../../.claude/agents/merge-captain.md),
    [`dashboard-contract-reviewer.md`](../../.claude/agents/dashboard-contract-reviewer.md),
    [`quant-performance-auditor.md`](../../.claude/agents/quant-performance-auditor.md).
  - Fixtures: [`fixtures/good.json`](fixtures/good.json),
    [`fixtures/bad.json`](fixtures/bad.json).

- **10:28 [`b874437`](../../.git)** — `pty_driver` for TUI engines + 9-engine signs-of-life + Kimi merge plan.
  - New: [`pty_driver.py`](pty_driver.py) (ConPTY/pyte driver for
    freebuff TUI; ANSI / DCS / OSC strip; pyte-rendered display +
    history).
  - New: [`swarm_runs/KIMI_VS_OURS_MERGE_PLAN.md`](../../swarm_runs/KIMI_VS_OURS_MERGE_PLAN.md).

- **10:44 [`7f31763`](../../.git)** — freebuff via ConPTY + pyte renderer; `config_loader` env-var subst.
  - New: [`config_loader.py`](config_loader.py)
    (`load_dotenv`, `interpolate`, `load_config`,
    `resolve_engine_key`).
  - Update: [`pty_driver.py`](pty_driver.py) — pyte renderer + abort
    detection; +338/-106 lines.
  - Update: [`worker_runner.py`](worker_runner.py) — `--context-md`
    flag + freebuff PTY dispatch.

- **10:50 [`8490352`](../../.git)** — centralised safety + copilot output parser (Kimi merge #2).
  - New: [`safety.py`](safety.py)
    (`isolated_env`, `READ_ONLY_ALLOWED`, `READ_ONLY_DISALLOWED`,
    `post_run_git_check`, `claude_readonly_args`).
  - New: [`output_parsers.py`](output_parsers.py)
    (`parse_copilot`, `parse_claude_envelope`, `parse_engine_output`).
  - Update: [`worker_runner.py`](worker_runner.py) — wire
    `parse_engine_output` post-call; isolated env on API consults.

- **10:54 [`29e6299`](../../.git)** — `swarm_run.py` fan-out + Gemini JSON-strict wrapper.
  - New: [`swarm_run.py`](swarm_run.py) — one-shot parallel fan-out;
    flag mode (CLI engines) + JSONL summary.
  - Update: [`worker_runner.py`](worker_runner.py) — `--json-strict`
    flag; gemini wraps prompt with strict-JSON preamble when set.

- **11:12 [`a7a8338`](../../.git)** — YAML config + sqlite session sidecar + freebuff long-prompt modes.
  - New: [`session_manager.py`](session_manager.py) — sqlite sidecar
    at `swarm_runs/_sessions.db` (sessions + messages tables, WAL,
    `new_session`, `record_message`, `update_session`,
    `replay_messages`, `render_md_context`, expire / list / show
    CLI).
  - New: [`examples/asset_class_audit.yaml`](examples/asset_class_audit.yaml),
    [`examples/multi_model_qa.yaml`](examples/multi_model_qa.yaml).
  - New: [`SWARM_DESIGN_NOTES.md`](SWARM_DESIGN_NOTES.md) (freebuff
    long-prompt strategy: single / fileref / chunked).
  - New: [`_freebuff_test_ladder.py`](_freebuff_test_ladder.py)
    (empirical buffer probes, runs 1-4).
  - Update: [`pty_driver.py`](pty_driver.py) — three modes
    (`single` / `fileref` / `chunked`); auto-select on size.
  - Update: [`swarm_run.py`](swarm_run.py) — YAML config support
    (`--config`, `${VAR}` / `${TS}`); `--persist-sessions`
    pre-allocates one session per engine.
  - Update: [`worker_runner.py`](worker_runner.py) +
    [`requirements.txt`](requirements.txt) (pyyaml).
  - Update: [`SPEC.md`](SPEC.md) — Session Manager section.

- **11:18 [`674078a`](../../.git)** — `worker_runner --from-session` resume + answer-fallback capture.
  - Update: [`worker_runner.py`](worker_runner.py) — `--from-session`
    auto-routes (claude native / API JSONL replay / MD-context
    fallback); `--persist-session` records turn.
  - Update: [`swarm_run.py`](swarm_run.py) — answer fallback on
    session-record (commentary_text / summary / answer / content /
    text → fall back to `.raw.txt`).

- **11:39 [`411f801`](../../.git)** — slash commands + inspector + multi-turn chain + PR resume.
  - New: nine slash commands under
    [`.claude/commands/swarm*.md`](../../.claude/commands/) — `swarm`,
    `swarm-help`, `swarm-run`, `swarm-followup`, `swarm-inspect`,
    `swarm-stats`, `swarm-sessions`, `swarm-engines`, `swarm-resume`.
  - New: [`swarm_inspect.py`](swarm_inspect.py) — per-run audit
    (HEALTHY / TINY / ZERO / SHORT / CREDITS? / AUTH? / TUI_ONLY /
    PARSE_FAILED / TRUNCATED?).
  - New: [`swarm_followup.py`](swarm_followup.py) — multi-turn chain
    runner.
  - New: [`examples/forex_deep_dive.yaml`](examples/forex_deep_dive.yaml)
    (4-turn priming → analysis → critique → final chain).
  - Update: [`swarm_dispatch.ps1`](swarm_dispatch.ps1) —
    `-FromSessionsByPr`, `-PersistSessions`, `-AutoResume` (scans
    `_sessions.db` via `session_manager.py list --json`).
  - Update: [`swarm_run.py`](swarm_run.py) —
    `--from-session-by-engine` (resume subset, fresh rest).
  - Update: [`SPEC.md`](SPEC.md) — multi-turn followup + resume
    routing sections.

### Documentation

- **11:41 [`c04dfa7`](../../.git)** — asset-class CONSENSUS_v2 (5-engine
  refresh, 22 KB). Live consensus output at
  `swarm_runs/20260503T132558Z/`.

### Engine status (end-of-day)

- LIVE (9): `deepseek`, `xai`, `gemini`, `kilo`, `copilot`, `opencode`,
  `cerebras`, `inception`, `ollama_cloud`.
- PTY (verified PONG, fileref auto-selected on > 800 B prompts):
  `freebuff`.
- EXCLUDED: `codebuff` (TUI-only + out of credits).

### Known issues

- `freebuff` `fileref` mode depends on the free-tier MiniMax model
  invoking its built-in `Read` tool. If declined, the driver returns
  a refusal text; manual `--mode chunked` retry is the documented
  fallback (no auto-retry — would burn quota).
- The PowerShell orchestrator + comment poster have no POSIX bash port
  yet; Python drivers ([`swarm_run.py`](swarm_run.py),
  [`swarm_followup.py`](swarm_followup.py)) are cross-platform.
- [`pty_driver.py`](pty_driver.py) is Windows-only (pywinpty). macOS /
  Linux need a pty-fork backend (not yet written).
