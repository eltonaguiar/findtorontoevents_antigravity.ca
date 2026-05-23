# Swarm Systems Guide

> Last updated 2026-05-15. Covers all three multi-agent swarm systems in this repo:
> `/swarm` (general multi-engine), `/swarm-ruflo` (Hermes orchestrator), and the new
> `/swarmv2-*` (enhanced coding/review/research swarm). Read this before running a swarm.

---

## 1. The three systems at a glance

| System | Slash commands | Code root | Purpose | Writes code? |
|---|---|---|---|---|
| **`/swarm`** | `/swarm run`, `/swarm followup`, `/swarm pr-review`, `/swarm second-opinion`, `/swarm invent`, `/swarmwithprework`, … | `tools/swarm/` | General multi-engine fan-out — consult N different LLM vendors on one prompt, consensus, red-team | Analysis by default; only the `code_implementer` persona can write |
| **`/swarm-ruflo`** | `/swarm-ruflo audit\|github\|strategy\|bugs\|wizard` | `.ruflo/` | Hermes/ruflo orchestrator — audit / research / hygiene swarms, free OpenRouter or paid keys | No — analysis/JSON findings only |
| **`/swarmv2-*`** | `/swarmv2-coding`, `/swarmv2-pr-review`, `/swarmv2-actions`, `/swarmv2-research`, `/swarmv2-ensemble`, `/swarmv2-hierarchical` | `tools/swarm_v2/` | Enhanced typed swarms — coding pipeline (generate→test→review→revise→verify), PR review, CI audit, research, ensemble/hierarchical decision | **Yes** — the coding swarm produces real source + tests via real LLMs |

**Which to use:**
- Want a fast second/third opinion on a decision or design → `/swarm second-opinion` or `/swarm run`.
- Want a batch of todos *coded, tested and reviewed* → `/swarmv2-coding`.
- Want the audit dashboard / strategies / GitHub hygiene scanned → `/swarm-ruflo audit` / `bugs` / `github`.
- Want a PR reviewed by multiple specialists → `/swarm pr-review` (per-PR) or `/swarmv2-pr-review`.
- Want deep research with cross-verification → `/swarmv2-research` or `/swarm followup`.

---

## 2. System 1 — `/swarm` (general multi-engine)

**Code:** `tools/swarm/` — `swarm_run.py` (fan-out), `worker_runner.py` (single-engine worker),
`swarm_followup.py` (multi-turn chain), `swarm_critique.py` (prompt red-team), `api_consult.py`
(HTTP API caller), `safety.py` (read-only allowlist), `swarm_inspect.py` (run auditor).

### 2.1 Slash commands

| Command | Usage | Notes |
|---|---|---|
| `/swarm run` | `/swarm run <prompt-file> [engine,engine,…]` | Fan one prompt to N engines in parallel. Default `deepseek,xai,kilo`. Auto-inspects after. |
| `/swarm followup` | `/swarm followup <yaml-config>` | Multi-turn chain (priming→analysis→critique→final), one engine. |
| `/swarm second-opinion` | `/swarm second-opinion <question>` | Quick 3-engine consensus check. One-shot. |
| `/swarm pr-review` | `/swarm pr-review [PR#\|all\|open] [--consensus]` | 3 specialist agents **per PR** + consensus. |
| `/swarm invent` | `/swarm invent <problem-file> [design-engine]` | Bootstrap custom personas for a new problem domain. |
| `/swarm actions-audit` | `/swarm actions-audit [--deep] [--fix]` | Multi-agent GitHub Actions audit. |
| `/swarmwithprework` | `/swarmwithprework <task>` | 4-phase: pre-work → brainstorm → synthesis → QA. |
| `/swarm engines` / `stats` / `inspect` / `sessions` | — | Diagnostics. |

### 2.2 Engines + keys

API engines: `deepseek`, `xai`, `cerebras`, `inception`, `openrouter`, `groq`, `huggingface`,
`gemini_api`, `github_models`, `pollinations` (keyless), `nous`, `ollama_cloud`, `ollama_local`.
CLI engines (OAuth, installed CLIs): `claude`, `gemini`, `opencode`, `kilo`, `copilot`, `agent` (Cursor), `kimi`, `openclaude`.

Engine presets (`--preset`): `consensus-3` (deepseek,xai,kilo), `fast-cheap` (cerebras,deepseek),
`deep-strict` (claude,kilo,deepseek), `non-opus-4` (xai,deepseek,groq,cerebras — genuine vendor diversity).

### 2.3 Fan-out YAML template (`tools/swarm/examples/*.yaml`)

```yaml
name: my_run_${TS}
prompt_file: swarm_runs/briefing_my_task.md
out_dir: swarm_runs/run_${TS}
max_parallel: 4
strictness: strict          # strict | lenient | off
preset: consensus-3         # OR an explicit engines: list
red_team: true              # adds a claude-opus red-team pass
cost_cap_usd: 5.0
engines:                    # only if not using preset
  - name: deepseek
    model: deepseek-chat
    persona: regime-specialist
    sampling: {temperature: 0.1, max_tokens: 8000}
```

### 2.4 Multi-turn followup chain — prompts per round

`swarm_followup.py` runs one engine through sequential turns (each turn resumes the prior session):
1. **priming** — feed a briefing file as warm-up context.
2. **analysis** — "narrow to the problem, cite specific numbers from the briefing."
3. **critique** — "which single claim is weakest, what unstated assumption, which 2 sentences would you retract."
4. **final** — "emit valid JSON only, per this schema." (`capture_to: final.json`)

### 2.5 Personas

`tools/swarm/agent_personas/` — ~60 `.md` files (YAML frontmatter: `name`, `description`, `tools`, `model`).
Inject with `--persona <name>`. The only **writer** persona is `code_implementer.md` (has the `Write` tool).
Asset-class specialists exist: `crypto_specialist`, `equity_specialist`, `forex_specialist`,
`commodity_specialist`, `etf_specialist`, `bond_specialist`.

### 2.6 Safety

`safety.py` puts every worker on a **read-only allowlist** — `Edit`/`Write` and all mutating
git/gh/fs commands are blocked, env is isolated to that engine's keys, and a post-run
`git status` drift check runs. Writing requires explicitly choosing the `code_implementer` persona.

---

## 3. System 2 — `/swarm-ruflo` (Hermes orchestrator)

**Code:** `.ruflo/orchestrator.py`, `.ruflo/wizard.py`, `.ruflo/agents/*.yaml`.

`/swarm-ruflo [audit|github|strategy|bugs|wizard|keys|continuous] [--tier free|paid|hybrid]`

| Subcommand | Agents | Action |
|---|---|---|
| `audit` | `audit-researcher` + `audit-quant` | Audit dashboard — forward-WR, stale strategies, leakage |
| `bugs` | `bug-hunter` | Hardcoded paths, SQL injection, races, key leaks |
| `github` | `github-hygiene` | Stale PRs, failing Actions, commits without tests |
| `strategy` | `strategist` | Propose 3 new trading strategies |
| `wizard` | — | Interactive tier/model selector |

**Tiers:** `free` (OpenRouter free models via Hermes inside WSL, zero cost), `paid` (direct API
via `api_consult.py`), `hybrid` (paid first, free fallback). Free tier runs only in WSL:
`wsl bash -c "cd /mnt/c/findtorontoevents_antigravity.ca && python3 .ruflo/orchestrator.py --swarm audit --tier free"`.

**Agent template:** copy `.ruflo/agents/TEMPLATE_agent.yaml`, fill `type`, `role`, `model`, `goal`
(the prompt), `capabilities`, `metadata.dataSources`, `checks`. Output → `swarm_runs/ruflo-insights/*.json`.
Ruflo agents **never write code** — they return JSON findings only.

---

## 4. System 3 — `/swarmv2-*` (enhanced typed swarm) — NEW 2026-05-15

**Code:** `tools/swarm_v2/swarms/` — Python package. Install: `cd tools/swarm_v2 && pip install -e ".[dev]"`.
CLI: `python -m swarms.cli.main <command>`.

### 4.0 What changed today — and what did NOT

A common confusion: *"didn't the swarm always call AI models?"* For **swarm_v2, no.**

- **`tools/swarm` (System 1) — UNCHANGED.** It always called real models (real API/CLI engines via
  `api_consult.py`). Nothing about it changed today.
- **`.ruflo/` (System 2) — UNCHANGED.** Still the same Hermes audit/research orchestrator. Untouched.
- **`tools/swarm_v2/` (System 3) — NEW directory, then LLM-wired.** It did not exist before today.

**The template-stub vs real-LLM difference (swarm_v2 only):**

A "template stub" is **not** an AI call. As delivered (the Kimi scaffold), swarm_v2's engine literally
returned a hardcoded string — e.g. `_run_generators` returned `{"source_code": "# Generated by <id>\ndef
foo(): pass"}` — and the workers filled deterministic string templates. **Zero LLM calls, zero network.**
The "6 swarm engines" were orchestration skeletons producing canned output. So running `/swarmv2-coding`
on the old code would *not* solve your task — it returned placeholder code regardless of the prompt.

Today's work added `swarms/core/llm_client.py` and wired every worker (generator, test-writer, reviewer,
researcher, impact-analyzer) to call a **real LLM** (deepseek/groq/cerebras/openrouter). The deterministic
template is now only the **offline fallback** — used when no API key is present, so tests stay hermetic
and the CLI never hard-crashes. With a key, the swarm genuinely generates/reviews/researches.

| | swarm_v2 before today (Kimi scaffold) | swarm_v2 after today |
|---|---|---|
| Code generation | hardcoded `def foo(): pass` | real LLM writes source + tests |
| Review / research | deterministic string templates | real LLM review / findings |
| LLM calls | none | deepseek/groq/cerebras/openrouter |
| Template | the *only* path | *fallback* only (offline / no key) |

### 4.1 The 6 swarm types + parameters

| Swarm | CLI | Key parameters | Pipeline |
|---|---|---|---|
| **Coding** | `swarm coding <task-file> [--agents 3] [--strict] [--models a,b]` | `--agents` parallel generators, `--strict` 90% coverage | decompose → parallel generate → write tests → review → revise (≤3) → verify |
| **PR Review** | `swarm pr-review <repo> [--pr N] [--all-open]` | `--pr`, `--all-open` | fetch → impact analysis + code review + risk → aggregate approve/reject |
| **GitHub Actions** | `swarm actions <repo> [--since 30d] [--notify]` | `--since`, `--notify` | fetch runs → detect failed/flaky/cancelled/stale → blast radius |
| **Research** | `swarm research "<topic>" [--depth 3-5] [--route A\|B\|C\|D]` | `--depth` researcher count | decompose → parallel research → cross-verify → synthesize |
| **Ensemble** | `swarm ensemble "<task>" [--agents 5] [--confidence-threshold 0.8]` | `--agents`, `--confidence-threshold` | register N agents → predict → weighted vote → expand if low confidence |
| **Hierarchical** | `swarm hierarchical "<task>" [--strategists 2] [--tacticians 3]` | `--strategists`, `--tacticians` | strategic signals → tactical (conditioned) → execution → risk veto |

Slash-command equivalents: `/swarmv2-coding`, `/swarmv2-pr-review`, `/swarmv2-actions`,
`/swarmv2-research`, `/swarmv2-ensemble`, `/swarmv2-hierarchical`.

### 4.2 Real LLM providers (wired 2026-05-15)

`swarms/core/llm_client.py` auto-detects a provider from env API keys. Validated working in this
environment: **deepseek, groq, cerebras, openrouter**. (xai key currently invalid; inception 403.)
Run `python -m swarms.core.llm_client --validate` to re-probe. Every worker degrades to a
deterministic template when no key is present — the swarm never hard-crashes offline.

### 4.3 Agent types / templates

The coding swarm uses three worker roles, each an LLM agent with a fixed system prompt
(no YAML to fill — they are code, in `tools/swarm_v2/swarms/workers/`):
- **code_generator** — writes source + tests. Prompt: "terse senior engineer, production code, no TODO placeholders."
- **test_writer** — enriches/writes the pytest file, re-runs the suite.
- **code_reviewer** — returns `severity | message | suggestion` findings; sets `approved` bool.

The task you provide is a plain task file (markdown) — that is the only "template" to fill.

### 4.4 Memory + skill export

Swarm outputs are stored in a ChromaDB vector store with hybrid BM25 + vector search:
- `swarm memory search "<query>" [--tags …]` — find prior swarm results (avoid reinventing).
- `swarm memory export-skill "<query>" <name>` then `swarm skill export <name> --format claude-md`
  — turn a swarm result into a reusable Claude skill.

---

## 5. Quick-start

### 5.1 Get a fast multi-vendor opinion (System 1)
```
/swarm second-opinion "Should we size up the COMMODITY class given PF 2.49 / n=322?"
```
Three engines answer in parallel; a consensus is synthesized. ~30 s, costs cents.

### 5.2 Code a batch of todos (System 3)
```
cd tools/swarm_v2
# write your todos into task.md, one task or a short spec
python -m swarms.cli.main coding task.md --agents 3 --strict
```
3 generator agents each attempt it via a real LLM → tests written → reviewed → revised up to
3× → only test-passing artifacts survive. Output is a JSON artifact set; apply the winning diff
yourself or hand it to a `cavecrew-builder` subagent.

### 5.3 Audit the trading system (System 2)
```
/swarm-ruflo audit --tier hybrid
```

---

## 6. Sample end-to-end flow — "code 5 todos with the coding swarm"

1. **Write the task file** — `tools/swarm_v2/task.md`:
   ```
   Implement a retry decorator `with_retry(max_attempts, backoff)` for API calls.
   Must: exponential backoff, jitter, only retry on listed exception types.
   Include pytest unit tests covering success-first-try, retry-then-succeed, exhaustion.
   ```
2. **Run the swarm** — `python -m swarms.cli.main coding task.md --agents 3 --strict`.
3. **Pipeline runs:** decompose → 3 generators write code+tests in parallel (each may use a
   different provider for diversity) → test_writer enriches tests + re-runs pytest →
   2 reviewers score each artifact (`approved`, `score`, findings) → if a reviewer flags issues,
   the generator revises (up to 3 rounds) → `_enforce_tests` drops any artifact whose tests fail.
4. **Collect output** — surviving `CodeArtifact`s (source + tests + review comments + test results).
5. **Apply** — review the winning artifact, apply the diff (main thread or a `cavecrew-builder`
   subagent). The swarm does **not** auto-commit.
6. **Memory** — the run is stored; `swarm memory search "retry decorator"` finds it next time.

---

## 7. Bulk-reviewing many files (e.g. 50 files)

**There is no purpose-built 50-file batch reviewer.** What exists and the workaround:
- `/swarm pr-review` is **per-PR**, not per-file — it reads each PR's diff.
- `/swarmv2-pr-review` reviews a PR (impact + review + risk), still PR-scoped.
- `/swarm actions-audit` is scoped to workflow YAML only.

**Recommended workaround:** build one **briefing file** containing the 50 files (or their relevant
excerpts) and fan it out:
```
/swarm run swarm_runs/briefing_50_files.md deepseek,xai,cerebras
```
Use `--cost-cap-usd` to bound spend. For genuine per-file parallelism, script a loop over
`worker_runner.py` (one call per file) — no built-in batcher does this yet. This is a noted gap;
a `swarm bulk-review <glob>` mode is a reasonable future addition.

---

## 8. Use case per swarm type

One concrete, project-specific scenario for every swarm type.

### swarm_v2 (`/swarmv2-*`)

| Swarm | Concrete use case in this repo | Command |
|---|---|---|
| **Coding** | Implement a queued backlog of `TESTING_PROTOCOL.MD` todos — e.g. wire the `kill_gate` min-n floor (M-055) into the commodity/fx kill switches. 3 agents draft + test in parallel; reviewers gate; you apply the winner. | `swarm coding m055_task.md --agents 3 --strict` |
| **PR Review** | Triage the open-PR backlog before merge — impact score + risk level + breaking-change list per PR, so safe PRs merge fast and risky ones get flagged. | `swarm pr-review eltonaguiar/findtorontoevents_antigravity.ca --all-open` |
| **GitHub Actions** | Find chronically cancelled / flaky jobs in `audit-dashboard.yml` + `sports-smoke-and-e2e.yml` that have no subsequent successful run — the recurring CI-drift problem. | `swarm actions eltonaguiar/findtorontoevents_antigravity.ca --since 30d` |
| **Research** | Scope a hard feature before building it — e.g. the López de Prado PBO/CPCV harness (M-052): decompose, research in parallel, cross-verify, surface disputed claims. | `swarm research "Lopez de Prado PBO/CPCV overfitting harness" --depth 4` |
| **Ensemble** | Aggregate a directional call — e.g. BTC 4h LONG vs SHORT from N model votes, weighted by confidence; surfaces dissent instead of one model's guess. | `swarm ensemble "BTC 4h direction next 6h" --agents 5` |
| **Hierarchical** | Mirror the trading desk: macro regime (VIX / BTC-dominance / fear-greed) → per-asset-class tactician signal → risk-controller veto on sizing. Produces a structured signal, not a trade. | `swarm hierarchical "size COMMODITY exposure" --strategists 2 --tacticians 3` |

### `/swarm` (System 1)

| Mode | Concrete use case |
|---|---|
| `/swarm run` | Fan an asset-class audit briefing to `deepseek,xai,cerebras` — cross-vendor consensus on whether COMMODITY clears the Tier-2 bar. |
| `/swarm followup` | Single-strategy deep dive — prime with the FOREX briefing, then analysis → self-critique → final JSON verdict, one engine, 4 turns. |
| `/swarm second-opinion` | Quick 3-engine gut-check on a decision: "kill or mutate the FOREX class given PF 0.27 / n=1249?" |
| `/swarm pr-review` | Multi-specialist (architecture / cost-risk / data-flow) review of one PR before merge. |
| `/swarm invent` | A new problem domain with no persona — bootstrap a custom persona split + test blueprint. |
| `/swarmwithprework` | A large fuzzy task — 4-phase pre-work → brainstorm → synthesis → QA. |

### `/swarm-ruflo` (System 2)

| Subcommand | Concrete use case |
|---|---|
| `audit` | Scan the `/audit` dashboard data for strategies with `forward_wr < 0.55`, stale strategies, elite-score starvation, anti-predictive leakage. |
| `bugs` | Hunt the codebase for hardcoded paths, SQL injection, race conditions, unclosed DB connections, leaked API keys. |
| `github` | GitHub hygiene — stale PRs (>7d), failing Actions, commits without tests, workflow-file mismatches. |
| `strategy` | Ideation — propose 3 new trading strategies (name, asset class, edge, implementation sketch, risk controls). |

## 9. Recommended usage in this project

- **Stock/crypto prediction work** — `/swarm run` with asset-class specialist personas
  (`crypto_specialist`, `equity_specialist`, …) or `/swarm-ruflo audit`. `/swarmv2-ensemble` does
  weighted signal voting; `/swarmv2-hierarchical` mirrors macro→tactician→risk-veto. These produce
  signals/analysis — they do **not** place trades.
- **Coding a backlog of todos faster** — `/swarmv2-coding`. Multiple agents attempt each task,
  tests are mandatory, reviewers gate quality. Divergent attempts surface edge-cases a single
  pass misses, and the revise loop is enforced, not optional.
- **PR triage** — `/swarm pr-review` or `/swarmv2-pr-review`. **CI health** — `/swarmv2-actions`
  or `/swarm-ruflo github`.

---

## 10. File reference

- System 1: `tools/swarm/` — `README.md`, `SPEC.md`, `METHODOLOGY.md` for deep detail.
- System 2: `.ruflo/` — `agents/TEMPLATE_agent.yaml` to author a new agent.
- System 3: `tools/swarm_v2/README.md`; tests `tools/swarm_v2/swarms/tests/` (376 passing).
- Slash commands: `.claude/commands/swarm*.md`.
- Run artifacts: `swarm_runs/` (per-run dirs, `_calls.jsonl`, `ruflo-insights/`).
