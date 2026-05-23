# tools/swarm — Porting guide

Lift-and-shift to another repo. The swarm core is generic; only two
subagents and three prompt files reference this project's paths.

A parallel Kimi swarm
([`swarm_runs/KIMI_VS_OURS_MERGE_PLAN.md`](../../swarm_runs/KIMI_VS_OURS_MERGE_PLAN.md))
is being built independently — when adopting into a third repo, you can
mix and match files between the two.

## File manifest

Authoritative list: [`MANIFEST.txt`](MANIFEST.txt). Summary by category:

```
# Core engine adapter + JSON-Schema gate
tools/swarm/api_consult.py            REQUIRED  direct-API path (deepseek/cerebras/xai/inception/ollama_cloud)
tools/swarm/schema_review.json        REQUIRED  JSON-Schema for worker output
tools/swarm/schema_validate.py        REQUIRED  schema gate
tools/swarm/worker_runner.py          REQUIRED  engine adapter

# TUI / PTY driver — REMOVED 2026-05-04 alongside the freebuff engine.
#   (was: _freebuff_test_ladder.py + pty_driver.py)

# Cleaners + safety
tools/swarm/output_parsers.py         REQUIRED  copilot tool-call stripper, claude envelope extractor
tools/swarm/safety.py                 REQUIRED  isolated_env() + read-only allow/deny lists
tools/swarm/config_loader.py          REQUIRED  .env autoload + ${VAR} substitution

# Sessions
tools/swarm/session_manager.py        REQUIRED  sqlite session sidecar
tools/swarm/swarm_janitor.py          OPTIONAL  expire stale sessions

# Drivers
tools/swarm/swarm_followup.py         REQUIRED  multi-turn chain
tools/swarm/swarm_run.py              REQUIRED  one-shot fan-out

# PR pipeline (PowerShell — see Known portability gaps)
tools/swarm/comment_poster.ps1        REQUIRED  only writer; y/N-gated
tools/swarm/swarm_dispatch.ps1        REQUIRED  PR-review fan-out

# Logging + audit
tools/swarm/swarm_inspect.py          REQUIRED  per-run audit (HEALTHY/TINY/ZERO/...)
tools/swarm/swarm_log.py              REQUIRED  thread-safe call logger
tools/swarm/swarm_stats.py            REQUIRED  historical engine stats

# Prompts
tools/swarm/prompts/merge_reviews.md  REQUIRED  merge-captain prompt
tools/swarm/prompts/pr_review.md      EDIT      PR-review prompt (project ref in line 3 + 14-18)
tools/swarm/prompts/redteam.md        REQUIRED  red-team prompt

# Fixtures + examples + personas
tools/swarm/fixtures/{good,bad}.json  OPTIONAL  schema fixtures
tools/swarm/examples/*.yaml           OPTIONAL  YAML config examples
tools/swarm/agent_personas/*.md       OPTIONAL  asset-class reviewer personas (project-specific content)

# Top-level docs
tools/swarm/{README,SPEC,PORTING,CHANGELOG,SWARM_DESIGN_NOTES,MANIFEST}.md
tools/swarm/requirements.txt
tools/swarm/swarm.config.example.json

# Claude Code subagents (Task tool / /agents)
.claude/agents/pr-reviewer.md                    REQUIRED  generic
.claude/agents/fabrication-red-team.md           REQUIRED  generic
.claude/agents/merge-captain.md                  REQUIRED  generic
.claude/agents/dashboard-contract-reviewer.md    PROJECT-SPECIFIC  drop or rewrite
.claude/agents/quant-performance-auditor.md      PROJECT-SPECIFIC  drop or rewrite

# Slash commands (9 files, all generic)
.claude/commands/swarm.md  swarm-help.md  swarm-run.md  swarm-followup.md
.claude/commands/swarm-inspect.md  swarm-stats.md  swarm-sessions.md
.claude/commands/swarm-engines.md  swarm-resume.md
```

## Required env vars

API engines:

| Var | Engine | Where to get it | Notes |
|---|---|---|---|
| `DEEPSEEK_API` (or `DEEPSEEK_API_KEY`) | deepseek | https://platform.deepseek.com → API keys | OpenAI-compatible |
| `CEREBRAS_API` (or `CEREBRAS_API_KEY` / `CERBRAS_FREE_ITHINK`) | cerebras | https://cloud.cerebras.ai → API keys | Needs `cerebras-cloud-sdk` pip pkg |
| `X_AI_KEY` (or `XAI_API_KEY` / `X_AI` / `GROK_SUPER`) | xai | https://console.x.ai → API keys | Grok 3 latest |
| `INCEPTION_AI_KEY` (or `INCEPTION_API_KEY`) | inception | https://platform.inceptionlabs.ai → API keys | Use model `mercury-2`; `mercury` is deprecated |
| `OLLAMA_CLOUD_KEY` | ollama_cloud | `ollama signin` → SSH key in `~/.ollama/id_ed25519` | **SSH ed25519 push key for `ollama push`, NOT a chat token.** Adapter shells out to local `ollama run gpt-oss:120b-cloud <prompt>`. |

Optional model overrides: `DEEPSEEK_MODEL`, `CEREBRAS_MODEL`, `XAI_MODEL`,
`INCEPTION_MODEL`, `OLLAMA_CLOUD_MODEL`.

`.env` at repo root is auto-loaded by [`config_loader.load_dotenv()`](config_loader.py)
when [`swarm_run.py`](swarm_run.py) / [`swarm_followup.py`](swarm_followup.py)
load a YAML config. Format: `KEY=value` per line, `#` comments, blank
lines ok.

CLI engines authenticate via their own login flow (no env vars):

- `claude` — `claude /login`
- `gemini` — `gemini auth login`
- `opencode` / `kilo` — OAuth in CLI
- `copilot` — `gh auth login` then `gh extension install github/gh-copilot`
- `ollama` — `ollama signin` for cloud-tagged models
- ~~`freebuff`~~ — removed 2026-05-04 (PTY/TUI engine, low usage)

Verify resolution:

```
python tools/swarm/config_loader.py
```

prints each engine + which env var it resolved + a masked key length.

## Required CLI tools

On `PATH` (Windows: prefer `%APPDATA%/npm/<name>.cmd` shims; the worker
auto-resolves there first via [`worker_runner._resolve_cli`](worker_runner.py)):

| Tool | Purpose | Min version |
|---|---|---|
| `claude` | Anthropic Claude CLI | recent enough for `--output-format=json` + `--session-id` / `--resume` |
| `gemini` | Google Gemini CLI | any |
| `opencode` | OAuth OpenAI-compatible CLI | any |
| `kilo` | Kilo CLI | any |
| `copilot` | GitHub Copilot CLI extension | recent — relies on `●`/`✗` markup parsed by [`output_parsers.py`](output_parsers.py) |
| `ollama` | Local LLM runtime + cloud auth | any with `signin` subcommand |
| `gh` | GitHub CLI | any (used by `swarm_dispatch.ps1` + `comment_poster.ps1`) |
| `python` | | >= 3.10 |
| `pwsh` | PowerShell 7+ | >= 7 — orchestrator uses `Start-Job` + chain operators |
| `git` | | any (used by prompts that grep history) |

## Path edits needed

Hardcoded project references that should be reviewed when porting:

1. [`tools/swarm/prompts/pr_review.md`](prompts/pr_review.md) line 3:
   ```
   Repository: eltonaguiar/findtorontoevents_antigravity.ca
   ```
   Replace with the new `<owner>/<repo>` slug.

2. [`tools/swarm/prompts/pr_review.md`](prompts/pr_review.md) lines
   ~14–18: project-specific evidence anchors (`audit_dashboard/template.html`,
   `audit_dashboard/hc_filter.js`, `audit_dashboard/data/dashboard_data.json`,
   `audit_trail/dashboard_generator.py`, `audit_trail/quality_gates.py`).
   Replace with your project's high-risk file list, or delete the
   section if your repo does not have a payload-contract / dashboard
   concern.

3. [`.claude/agents/dashboard-contract-reviewer.md`](../../.claude/agents/dashboard-contract-reviewer.md):
   entire body is project-specific (audit_dashboard / audit_trail /
   battleground / quality_gates references). Either delete or rewrite
   for your contract surface.

4. [`.claude/agents/quant-performance-auditor.md`](../../.claude/agents/quant-performance-auditor.md):
   entire body is project-specific (PF/WR/MDD charter,
   `audit_dashboard/data/dashboard_data.json`,
   `reports/hedge_fund_performance_review_*.md`). Either delete or
   replace with your domain auditor.

5. [`tools/swarm/swarm.config.example.json`](swarm.config.example.json)
   line 3: `"repo_slug": "eltonaguiar/findtorontoevents_antigravity.ca"`.

6. [`tools/swarm/agent_personas/*.md`](agent_personas/) — six
   asset-class personas reference `audit_dashboard/data/dashboard_data.json`
   keys (`asset_class_health`, `walk_forward_by_class`, `picks.active`)
   and `reports/HEDGE_FUND_AUDIT_REPORT_*.md`. Project-specific; drop
   or rewrite as a block.

7. ~~`tools/swarm/pty_driver.py`~~ — removed 2026-05-04 with the freebuff
   engine. (Was: a single line skipped the freebuff "Directory" banner
   if it contained `findtorontoevents`.)

Generic / portable as-is:

- [`worker_runner.py`](worker_runner.py),
  [`swarm_run.py`](swarm_run.py), [`swarm_followup.py`](swarm_followup.py),
  [`swarm_dispatch.ps1`](swarm_dispatch.ps1),
  [`comment_poster.ps1`](comment_poster.ps1),
  [`api_consult.py`](api_consult.py)
  (with the one-line edit above), [`safety.py`](safety.py),
  [`session_manager.py`](session_manager.py),
  [`swarm_janitor.py`](swarm_janitor.py),
  [`output_parsers.py`](output_parsers.py),
  [`config_loader.py`](config_loader.py),
  [`schema_validate.py`](schema_validate.py),
  [`schema_review.json`](schema_review.json),
  [`swarm_log.py`](swarm_log.py),
  [`swarm_inspect.py`](swarm_inspect.py),
  [`swarm_stats.py`](swarm_stats.py).
- [`prompts/merge_reviews.md`](prompts/merge_reviews.md),
  [`prompts/redteam.md`](prompts/redteam.md).
- [`.claude/agents/pr-reviewer.md`](../../.claude/agents/pr-reviewer.md),
  [`.claude/agents/fabrication-red-team.md`](../../.claude/agents/fabrication-red-team.md),
  [`.claude/agents/merge-captain.md`](../../.claude/agents/merge-captain.md).
- All nine [`.claude/commands/swarm*.md`](../../.claude/commands/) slash
  commands.

## 5-step adoption guide

1. **Lift the manifest into the target repo:**

   ```
   # bash / zsh
   rsync -av --include='tools/swarm/***' \
             --include='.claude/agents/{pr-reviewer,fabrication-red-team,merge-captain}.md' \
             --include='.claude/commands/swarm*.md' \
             --exclude='*' \
             <source-repo>/ <target-repo>/

   # Windows PowerShell
   robocopy <source-repo>\tools\swarm <target-repo>\tools\swarm /E /XD __pycache__
   robocopy <source-repo>\.claude\agents <target-repo>\.claude\agents pr-reviewer.md fabrication-red-team.md merge-captain.md
   robocopy <source-repo>\.claude\commands <target-repo>\.claude\commands swarm*.md
   ```

2. **Install Python deps + CLI tools.** See `Required env vars` and
   `Required CLI tools` above. Login per-engine. Drop a `.env` at the
   target repo root with the API keys; `config_loader.py` will pick it
   up.

   ```
   pip install -r tools/swarm/requirements.txt
   ```

3. **Edit the prompt + config:**

   ```
   tools/swarm/prompts/pr_review.md       (line 3 + lines 14-18)
   tools/swarm/swarm.config.example.json  (repo_slug)
   ```

4. **Decide on the project-specific subagents
   (`dashboard-contract-reviewer`, `quant-performance-auditor`) and
   asset-class personas (`agent_personas/*.md`):** keep, rewrite, or
   delete. They are not loaded by default — only invoked when explicitly
   referenced.

5. **Smoke test:**

   ```
   # 1. Verify env keys are wired.
   python tools/swarm/config_loader.py

   # 2. Verify safety isolation works.
   python tools/swarm/safety.py

   # 3. Run a dummy 2-engine fan-out.
   echo "Reply with the literal token PORT_TEST_OK" > /tmp/probe.md
   python tools/swarm/swarm_run.py --prompt-file /tmp/probe.md --engines deepseek,xai
   python tools/swarm/swarm_inspect.py --latest

   # 4. Optional: PR pipeline.
   pwsh tools/swarm/swarm_dispatch.ps1 -Prs 1 -Engines claude,deepseek -SkipMerge -SkipRedteam
   python tools/swarm/swarm_stats.py
   ```

   Expect every engine HEALTHY (≥ 1 KB) and a non-empty
   `<engine>.json` per worker.

## Cross-repo lift script (one-liner)

```
# Bash / Linux / macOS / WSL
rsync -av --delete \
  --include='tools/' --include='tools/swarm/' --include='tools/swarm/**' \
  --include='.claude/' --include='.claude/agents/' \
  --include='.claude/agents/pr-reviewer.md' \
  --include='.claude/agents/fabrication-red-team.md' \
  --include='.claude/agents/merge-captain.md' \
  --include='.claude/commands/' --include='.claude/commands/swarm*.md' \
  --exclude='*' \
  <source-repo>/ <target-repo>/

# Windows PowerShell (no /XF on dirs; copy then prune __pycache__)
robocopy "<source-repo>\tools\swarm" "<target-repo>\tools\swarm" /E /XD __pycache__
robocopy "<source-repo>\.claude\agents" "<target-repo>\.claude\agents" `
  pr-reviewer.md fabrication-red-team.md merge-captain.md
robocopy "<source-repo>\.claude\commands" "<target-repo>\.claude\commands" swarm*.md
```

After lifting, run the 5-step smoke test above before the first real
fan-out.

## Config template

[`swarm.config.example.json`](swarm.config.example.json) holds the
project-tunable knobs (engine list, default model per engine,
max-parallel, prompt paths). The dispatcher does not read it directly
today — copy relevant values into your `swarm_dispatch.ps1` defaults or
a wrapper script. Treat the JSON as the source of truth for human
reviewers; the runtime is currently driven by CLI args + YAML.

## Known portability gaps

- **PowerShell-only orchestrator + poster.** A bash port of
  `swarm_dispatch.ps1` and `comment_poster.ps1` is straightforward
  (`xargs -P` + `gh pr comment`) but not yet written. The Python
  drivers ([`swarm_run.py`](swarm_run.py),
  [`swarm_followup.py`](swarm_followup.py)) are cross-platform.
- **PTY driver removed 2026-05-04.** Was Windows-only (`pywinpty`/ConPTY)
  and only used by freebuff. Both deleted; no engine currently needs PTY.
- **Windows-specific CLI resolution** in
  [`worker_runner._resolve_cli`](worker_runner.py)
  (`%APPDATA%/npm/<name>.cmd`). On macOS/Linux the fallback to bare
  `<name>` on PATH works fine; the npm-shim probe is harmless.
- **`swarm_runs/` location is hardcoded** relative to repo root via
  `Path(__file__).resolve().parents[2]`. If you nest `tools/swarm/`
  deeper, adjust `REPO = ...parents[N]` in `worker_runner.py`,
  `swarm_log.py`, `swarm_stats.py`, `schema_validate.py`,
  `session_manager.py`, `swarm_run.py`,
  `swarm_followup.py`, `swarm_inspect.py`, `safety.py`,
  `config_loader.py`, `swarm_janitor.py`, `api_consult.py`.
- **Project-specific subagents** described above.
