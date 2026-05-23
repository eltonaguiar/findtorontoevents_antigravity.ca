# Hermes Swarm Reference — for Agent Context

> **For:** Hermes Agent v0.12.0 (and any future Codebuff session)
> **Updated:** 2026-05-05
> **Last reviewed by:** Buffy (Codebuff)

---

## OVERVIEW — Two Swarm Systems

This repo has **two independent swarm systems** that complement each other:

| | `.ruflo/` (Orchestrator) | `tools/swarm/` |
|--|---|---|
| **Drives via** | Hermes Agent (`hermes chat -q`) | Direct API calls + CLI adapters |
| **Agent model** | 5 specialized agents (audit, github, bugs, strategy, brainstorm) | 16+ engine adapters (claude, deepseek, xai, etc.) |
| **Best for** | Structured analysis tasks, continuous loops, strategy ideation | PR reviews, multi-model consensus, ad-hoc prompts |
| **Free tier** | ✅ Yes (via Hermes + OpenRouter free models) | ❌ Needs API keys (deepseek ~$0.001/run) |
| **Memory/persistence** | ❌ Ephemeral (each run fresh) | ✅ SQLite sessions (`swarm_runs/_sessions.db`) |
| **Multi-model consensus** | ❌ Single model per agent | ✅ N models in parallel → ranked synthesis |
| **Setup** | Needs Hermes binary + WSL | Needs Python + API keys |
| **Output** | `swarm_runs/ruflo-insights/COMPILED_latest.json` | `swarm_runs/run_<TS>/` + `_summary.json` |

**When to use which:**
- Need a **second opinion** on findings? → `tools/swarm/` (multi-engine consensus)
- Want to **audit performance / hunt bugs**? → `.ruflo/` (specialized agents)
- Want **persistent memory** across repeated identical tasks? → `tools/swarm/` with `--persist-sessions`
- Running the **same daily check** (e.g. PR status)? → `.ruflo/ --continuous` for periodic loops, `tools/swarm/` for one-shot
- Need **consensus before a Claude push**? → `tools/swarm/` with brainstorm_review (6 models → synthesis)

---

## 🦊 RUFLO SWARM — `.ruflo/orchestrator.py`

**Purpose:** 5-agent specialized orchestrator via Hermes Agent. Best for structured, recurring analysis tasks.

### How it works

1. **5 built-in agents** with defined roles and goals:
   - `audit_researcher` — reads MySQL picks, audit dashboard data, universal_resolved_picks.json. Finds strategies with forward_wr < 0.55, stale strategies, elite score starvation
   - `audit_quant` — quantitative: WR by asset class, regime gate status, transaction cost modeling, forward resolution tracker health
   - `github_hygiene` — uses `gh` CLI to check: old PRs (>7 days), failing Actions, commits without tests, workflow file mismatches
   - `bug_hunter` — searches for hardcoded paths, SQL injection, race conditions, unclosed DB connections, ghost elite scores
   - `strategist` — reads strong strategy docs + battleground signals → proposes 3 new strategies with edge, implementation sketch, risk controls

2. **Model tier selection** (default: `hybrid`):
   - `free` — uses Hermes + OpenRouter free models (pollinations, hy3-preview, nemotron-nano/super, minimax-m2.5, gemini-2.5-flash)
   - `paid` — direct API via `api_consult.py` (cerebras, deepseek, xai, inception, groq, huggingface)
   - `hybrid` — paid first, free fallback if paid fails
   - `local` — Ollama only (no API keys needed)
   - `auto` — local first, then free

3. **Runtime failover:** 3-attempt model rotation with exponential backoff on rate limit/timeout/429 errors

### Key commands

```bash
# One-shot swarms (default tier: hybrid — paid first, free fallback)
python3 .ruflo/orchestrator.py --swarm audit       # 2 agents: audit_researcher + audit_quant (parallel)
python3 .ruflo/orchestrator.py --swarm github      # 1 agent: github_hygiene
python3 .ruflo/orchestrator.py --swarm strategy    # 1 agent: strategist
python3 .ruflo/orchestrator.py --swarm bugs        # 1 agent: bug_hunter
python3 .ruflo/orchestrator.py --swarm all         # all 4 swarms, one-shot

# Override tier: --tier free  → OpenRouter free models (no cost)
#                --tier paid  → direct API (fastest, paid per call)
#                --tier hybrid → paid first, free fallback (default)

# Brainstorm → Review (6 models parallel → synthesis)
python3 .ruflo/orchestrator.py --swarm brainstorm_review --task <task description>

# Continuous loop
python3 .ruflo/orchestrator.py --continuous --cycle-minutes 30

# Utilities
python3 .ruflo/orchestrator.py --list-agents
python3 .ruflo/orchestrator.py --check-keys         # Show which paid keys are configured
```

**Windows bridge** (from Codebuff/PowerShell):
```bash
wsl bash -c \"cd /mnt/c/findtorontoevents_antigravity.ca && python3 .ruflo/orchestrator.py --swarm audit --no-verify\"
```

### Memory behavior (IMPORTANT)
- **NOT persistent** — each agent run is ephemeral. If you ask the same task twice, both runs start from scratch
- Output goes to `swarm_runs/ruflo-insights/YYYY-MM-DD/<swarm>_<agent>_<ts>.json`
- `COMPILED_latest.json` accumulates the last 50 insight files
- **If you want persistent memory across repeated identical tasks → use `tools/swarm` with `--persist-sessions`**

### YAML agent files (loaded from `.ruflo/agents/*.yaml`)
These override the inline agent definitions. If a `.yaml` file has a `type:` matching an inline key (audit_researcher, audit_quant, github_hygiene, bug_hunter, strategist), the YAML's goal text takes priority. This is the fix from 2026-05-05 — previously YAML agents were silently dropped, causing the 71% hallucination rate in bug_hunter.

---

## ⚡ TOOLS/SWARM — `tools/swarm/swarm_run.py`

**Purpose:** One-shot multi-engine fan-out. One prompt → N engines in parallel → JSON output per engine. Best for second opinions, consensus building, PR reviews.

### How it works

1. **16 engine adapters** — each is a subprocess that calls a CLI tool or direct API
2. **One-shot run** — prompt fans out to all engines in parallel, results collected
3. **Optional sessions** — `--persist-sessions` creates SQLite records; `--from-session` resumes prior sessions
4. **Cost cap** — `--cost-cap-usd 0.50` aborts if estimated cost exceeds threshold
5. **Pre-flight API key check** — engines with missing API keys are skipped automatically (saves 2-10s per failed attempt)

### Engine presets

```bash
python3 tools/swarm/swarm_run.py --preset consensus-3   # deepseek + xai + kilo (for second opinion)
python3 tools/swarm/swarm_run.py --preset fast-cheap    # cerebras + deepseek
python3 tools/swarm/swarm_run.py --preset deep-strict   # claude + kilo + deepseek (highest quality)
python3 tools/swarm/swarm_run.py --preset all-paid-api  # all paid engines (needs API keys)
python3 tools/swarm/swarm_run.py --preset all-cli       # all OAuth CLI engines
```

### Quick runs

```bash
# Fan-out a prompt file to specific engines
python3 tools/swarm/swarm_run.py --prompt-file tools/swarm/prompts/pr_review.md --engines deepseek,xai,kilo

# With YAML config (reproducible)
python3 tools/swarm/swarm_run.py --config tools/swarm/examples/asset_class_audit.yaml

# Second opinion (2 engines, cheap)
python3 tools/swarm/swarm_run.py --prompt-file my_prompt.md --engines deepseek,xai --cost-cap-usd 0.10

# All PRs check (via batch YAML)
python3 tools/swarm/swarm_run.py --config tools/swarm/examples/multi_model_qa.yaml --preset consensus-3
```

### Memory behavior (IMPORTANT)
- **Ephemeral by default** — each run is independent, no memory
- **With `--persist-sessions`** — messages stored in `swarm_runs/_sessions.db`. Resumable via `--from-session <engine>=<sid>`
- **Persistent memory is real** — `session_manager.py list` shows active sessions. Repeated identical tasks benefit from context in prior sessions
- `--persist-sessions` auto-on when using `--from-session` (resumed engines get persistent sessions)

### Inspect results

```bash
python3 tools/swarm/swarm_inspect.py --latest              # per-engine health check
python3 tools/swarm/swarm_inspect.py swarm_runs/run_20260505T120000Z/

python3 tools/swarm/swarm_stats.py                        # historical ok/latency by engine
python3 tools/swarm/session_manager.py list               # active sessions
```

### Auto-generated post-run footer (printed after every run)

```
NEXT STEPS:
  1. Inspect output     python tools/swarm/swarm_inspect.py <out_dir>
  2. Re-run red-team    python tools/swarm/swarm_run.py --config <cfg> --red-team
  3. Resume a dissenter python tools/swarm/worker_runner.py --engine <eng> --from-session <sid> ...
  4. Multi-turn         python tools/swarm/swarm_followup.py --config <yaml>
  5. Switch persona     --persona <name>  (see agent_personas/INDEX.md)
```

---

## USER WORKFLOW — How These Are Used in Practice

### Workflow 1: Second Opinion Before Claude Push
```
User wants: second opinion on a PR, then let CLAUDE review consensus and push

Best approach: tools/swarm --preset consensus-3
  → Fan out prompt to deepseek + xai + kilo
  → Collect responses
  → If 2+ models agree → high confidence → invoke CLAUDE to push
  → If models disagree → human review needed

Memory: use --persist-sessions so repeated second-opinion requests are faster
```

### Workflow 2: GitHub Actions Health Check
```
User wants: check for failing jobs or jobs that haven't run in a while

Best approach: .ruflo/orchestrator.py --swarm github
  → github_hygiene agent uses `gh` CLI to list failed runs, stale jobs
  → Returns JSON: {prs: [...], failed_actions: [...], recommendations: [...]}
  → Fast (1-3 min), single agent

Alternative: tools/swarm with a custom prompt about Actions status
  → More engines = more thorough but slower
```

### Workflow 3: All Open PRs Review
```
User wants: review ALL open PRs at once for the consensus workflow

Best approach: tools/swarm with YAML config targeting PR list
  → Prompt: list all open PRs via `gh pr list --state open`
  → Fan out to 3-5 engines for parallel analysis
  → Merge consensus → CLAUDE pushes if 2+ agree

The PR pipeline in tools/swarm/ has:
  - swarm_dispatch.ps1 for fan-out
  - comment_poster.ps1 for posting (y/N gated)
  - schema validation before any write
```

### Workflow 4: Performance Audit (Daily/Periodic)
```
User wants: daily audit of strategy performance, stale strategies, anomalies

Best approach: .ruflo/orchestrator.py --continuous --cycle-minutes 1440
  → Runs audit_researcher + audit_quant every 24h
  → Compiles insights to COMPILED_latest.json
  → No human input needed

Alternative: --swarm audit --tier hybrid (one-shot)
```

---

## SLASH COMMAND RECOMMENDATIONS FOR HERMES

The user requested slash commands that wrap both swarm systems. Here are the recommended commands:

## SLASH COMMAND RECOMMENDATIONS FOR HERMES

> The following are **recommended `/swarm-*` slash commands for Hermes to implement**, wrapping both swarm systems. They are not yet built — this section serves as the design spec for implementation.

### `/swarm-second [prompt-file]` — Second Opinion
```
Usage: /swarm-second path/to/prompt.md
       /swarm-second <inline task description>

Behavior:
  1. Run tools/swarm with --preset consensus-3 (deepseek + xai + kilo)
  2. Wait for all 3 engines
  3. If 2+ agree → HIGH CONFIDENCE → offer to invoke CLAUDE for push
  4. If disagreement → show consensus + dissenter, recommend human review

Memory: --persist-sessions ON (repeated requests benefit from session context)
```

### `/swarm-prs [--all|--stale|--failed]` — PR Review Swarm
```
Usage: /swarm-prs              # all open PRs
       /swarm-prs --stale      # PRs older than 7 days
       /swarm-prs --failed     # PRs with failing CI

Behavior:
  1. List open PRs via gh CLI
  2. Fan out to 3 engines: claude + deepseek + xai
  3. Each engine analyzes all PRs
  4. Collect responses → consensus on action (merge / comment / close)
  5. If consensus → offer CLAUDE push

Memory: ON (session persists for repeated PR checks)
```

### `/swarm-actions [--failed|--stale]` — GitHub Actions Monitor
```
Usage: /swarm-actions              # all recent Actions runs
       /swarm-actions --failed     # failed jobs only
       /swarm-actions --stale      # jobs not run in 48h+

Behavior:
  Option A (quick): .ruflo/orchestrator.py --swarm github (1 agent, fast)
  Option B (thorough): tools/swarm with --preset consensus-3

  Returns: list of failed/stale jobs with file paths, line numbers, and
  recommended fixes. Prioritizes by recency and failure rate.
```

### `/swarm-audit` — Performance Audit
```
Usage: /swarm-audit [--tier free|paid|hybrid]

Behavior:
  1. Run .ruflo/orchestrator.py --swarm audit (2 agents in parallel)
  2. audit_researcher + audit_quant read live data from files + MySQL
  3. Output: swarm_runs/ruflo-insights/COMPILED_latest.json with findings

Memory: OFF (each run reads fresh data from files; sessions not used)
```

### `/swarm-brainstorm <task>` — Multi-Model Consensus
```
Usage: /swarm-brainstorm Analyze the FOREX strategy performance and suggest improvements

Behavior (runs via .ruflo/orchestrator.py --swarm brainstorm_review):
  Phase 1: 6 models in parallel (pollinations + hy3 + nemotron-nano + nemotron-super + minimax + gemini)
  Phase 2: cerebras/deepseek synthesis of all 6 into ranked final answer
  Output: ranked synthesis with citations to which model supported each claim

Memory: Phase 1 ephemeral, Phase 2 uses api_consult sessions
```

---

## MEMORY COMPARISON — Which System Remembers?

| Task Type | Recommended System | Memory |
|-----------|-------------------|--------|
| Second opinion (repeated) | tools/swarm `--persist-sessions` | ✅ Persistent (SQLite) |
| PR status check (daily) | .ruflo `--continuous` | ❌ Ephemeral (from file data) |
| GitHub Actions monitor | .ruflo `--swarm github` | ❌ Ephemeral (from gh CLI) |
| All PRs consensus check | tools/swarm brainstorm_review | ✅ Phase 1 persistent |
| Bug hunt (one-shot) | .ruflo `--swarm bugs` | ❌ Ephemeral |
| Strategy ideation | .ruflo `--swarm strategy` | ❌ Ephemeral |

**Rule of thumb:** If you want the same task to run faster or smarter on the 2nd+ invocation → `tools/swarm --persist-sessions`. If you're reading live data (files, gh CLI, MySQL) → `.ruflo` (data is always fresh).

---

## KEY FILES

### .ruflo/ (Orchestrator)
| File | Purpose |
|------|---------|
| `.ruflo/orchestrator.py` | Main dispatcher — 5 agents, 5 tiers, failover, insight storage |
| `.ruflo/wizard.py` | Interactive tier & model selector (main entry point for setup) |
| `.ruflo/agents/*.yaml` | Agent definitions (loaded at runtime) |
| (no `.ruflo/README.md` — use wizard.py for setup) |
| `swarm_runs/ruflo-insights/` | Output directory |

### tools/swarm/
| File | Purpose |
|------|---------|
| `tools/swarm/swarm_run.py` | One-shot fan-out dispatcher |
| `tools/swarm/worker_runner.py` | Per-engine adapter (calls CLIs + APIs) |
| `tools/swarm/api_consult.py` | Direct API caller (shared with .ruflo) |
| `tools/swarm/swarm_followup.py` | Multi-turn chain |
| `tools/swarm/swarm_dispatch.ps1` | PR review pipeline |
| `tools/swarm/swarm_inspect.py` | Per-run health audit |
| `tools/swarm/swarm_stats.py` | Historical engine stats |
| `tools/swarm/session_manager.py` | SQLite session ops |
| `tools/swarm/config_loader.py` | YAML config loader + key env vars |
| `tools/swarm/prompts/*.md` | Prompt templates |
| `swarm_runs/` | All run output (gitignored) |

---

## API KEY STATUS

Check with: `python3 .ruflo/orchestrator.py --check-keys`

| Provider | Model | Env vars |
|----------|-------|---------|
| cerebras | gpt-oss-120b | CEREBRAS_API_KEY, CEREBRAS_API, etc. |
| deepseek | deepseek-chat | DEEPSEEK_API, DEEPSEEK_API_KEY |
| xai | grok-3-latest | X_AI_KEY, XAI_API_KEY, etc. |
| inception | mercury-2 | INCEPTION_AI_KEY, INCEPTION_API_KEY |
| groq | llama-3.3-70b | GROQ_KEY, GROQ_API_KEY |
| huggingface | llama-3.3-70b | HUGGINGFACE_API, HF_TOKEN |
| openrouter | gpt-4o-mini (default) | OPENROUTER_API_KEY, OPENROUTER |
| pollinations | openai (default, zero-key) | — (no key needed) |

### Pre-flight skip (2026-05-05 fix)
`tools/swarm/swarm_run.py` now skips API engines whose required keys are missing — saves 2-10s per failed attempt. Checked at runtime via `config_loader.ENGINE_KEY_ENVS`.

---

## 2026-05-05 CRITICAL FIXES (live on main)

1. **Cost overrun fix** — `swarm_run.py` `_lookup_openrouter_cost()` now reads `OPENROUTER_MODEL` env var and applies correct rate (was always using gpt-4o-mini rate regardless of model, causing 100x overruns)

2. **Empty envelope retry** — `worker_runner.py` retries once on rc=0 empty output (transient CLI init races)

3. **API key pre-flight** — `swarm_run.py` skips engines with missing keys before burning retry time

4. **Thread safety** — `.ruflo/orchestrator.py` now uses `threading.Lock()` for shared results dict (was bare dict, causing race conditions in parallel mode)

5. **YAML agent override fix** — `.ruflo/orchestrator.py` now properly merges YAML agent definitions (was silently dropping them, causing 71% hallucination rate in bug_hunter)

6. **Hermes --model flag** — `.ruflo/orchestrator.py` now passes `--model` to `hermes chat` CLI so YAML-configured model is honored (was using Hermes' default instead, causing 404 errors)

---

## GOTCHAS / KNOWN ISSUES

- **OpenRouter :free models are broken** (HTTP 404/429). Use pollinations (zero-key) or set OPENROUTER_API_KEY with :free models
- **pollinations also 403** on some WSL setups — fallback chain: pollinations → hy3-preview → nemotron-nano → gemini-2.5-flash
- **Hermes is 36 commits behind** — run `hermes update` to upgrade
- **`grok-3-fast` not found** — use `grok-3` or `grok-3-mini` instead
- **Codebuff basher WSL path issue** — use `--no-verify` when invoking orchestrator from Codebuff
- **.claude/agents/ is partially gitignored** — only `.claude/worktrees/` is gitignored, so agent YAMLs in `.claude/agents/` ARE tracked (quant-performance-auditor files were removed 2026-05-05)

---

## CONTEXT WINDOW CONSIDERATIONS

The orchestrator has context safety for free-tier models:

| Model | Context | Safe prompt |
|-------|---------|-------------|
| pollinations/default | 8K tokens | ≤ 24K chars (keep workspace context minimal) |
| nemotron-nano | 8K tokens | ≤ 24K chars |
| nemotron-super | 32K tokens (unverified) | ≤ 90K chars |
| minimax-m2.5 | 8K tokens | ≤ 24K chars |
| hy3-preview | 32K tokens | ≤ 90K chars |
| gemini-2.5-flash | 128K tokens | ≤ 400K chars |
| deepseek-chat | 64K tokens | ≤ 200K chars |
| grok-3-latest | 128K tokens | ≤ 400K chars |

Prompts exceeding safe limits are auto-truncated with task directive preserved in last 500 chars.