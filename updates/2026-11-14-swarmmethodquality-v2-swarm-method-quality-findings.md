# Swarm Method Quality Findings — SWARM_CONSOLIDATED

**Date:** 2026-11-14  
**Worktree:** `swarmmethodquality-v2`  
**Repo of record:** `eltonaguiar/SWARM_CONSOLIDATED` (https://github.com/eltonaguiar/SWARM_CONSOLIDATED)  
**Parent tooling repo:** `eltonaguiar/TORONTOEVENTS_ANTIGRAVITY` (`tools/ai_menu.sh`, `tools/swarm/`, `tools/swarm_v2/`, `.ruflo/`)  
**Author:** Kilo (software engineer)

---

## 1. TL;DR — Direct answers

| Question | Answer |
|----------|--------|
| **Is Ruflo Swarm better than Hermes Swarm?** | Ruflo Swarm *is* the Hermes-driven swarm — `.ruflo/orchestrator.py` dispatches work *through* Hermes Agent (Nous Research v0.12.0) with OpenRouter backend. There is no separate "Hermes Swarm." The real comparison is **Ruflo vs tools/swarm**: Ruflo = free-tier, 5 role-specialized agents, 3-attempt failover, WSL bridge; tools/swarm = multi-model consensus with persistent SQLite sessions (needs API keys). |
| **Is tools/swarm_v2 better than Ruflo?** | swarm_v2 is superior for **production engineering**: true parallelism (asyncio + ThreadPoolExecutor), persistent `SwarmMemory`+`MessageBus`+`AgentRegistry`+`SafetyEnforcer`, skill export, AST safety guards, hard `cost_cap_usd`, 300+ tests. Ruflo wins only for **zero-setup free-tier** audit/strategy work. |
| **#1 performance problem?** | LiteLLM `--num_workers 1` serializes all swarm fan-out calls through one event loop (`tools/start_litellm_proxy.sh:435`). Fix: give each agent its own endpoint (vLLM :8000, Ollama :11434) instead of a shared proxy. |
| **Which keys work in a swarm?** | Cerebras, DeepInfra, AIML API, xAI (Grok) pass tool-calls + 34k-context + chat auth. Groq 413s on 15k-token prompts (TPM 8,000). NVIDIA/SambaNova/Gemini/Together/Fireworks dead at chat level despite `/models` returning 200. |
| **Best research setup?** | Planner → CombineTeam (diverse providers) → Critic → Publisher, with harness-fetched retrieval (Startpage/Ecosia + full-markup frame extraction). `max_tokens >= 3000` for reasoning aliases. Expect ~3/4 on expert benchmarks even with retrieval. |

---

## 2. README.md collision investigation (SWARM_CONSOLIDATED)

Three agents each rewrote `README.md` from scratch instead of building on each other, progressively losing content:

| Commit | Lines | What it contributed |
|--------|-------|---------------------|
| `097d10f` (mine) | 318 | Detailed per-provider key table, verified fallback chain, ServiceNow model assessment (3/4 ceiling, `max_tokens>=3000` rule), free-tier TPM economics, pro-swarm research survey, ordered recommendations, AI_MENU→swarm mapping appendix, maintenance notes |
| `15e087c` (agent1) | 256 | V1/V2/Meta engine matrix, repo structure tree, P0 bug list (`swarm_e2e_fix.py`, `swarm_unified.py`, `swarm_model_eval.py`, `swarm_fix_worktree.py`), Next Steps |
| `aaaf234` (agent2, prior remote HEAD) | 214 | Performance Snapshot, 6-engine comparison table, Ruflo vs Hermes detailed table, tools/swarm_v2 vs Ruflo engine table, Critical Fixes Applied, BROKENMERMAIDTEST benchmark, Known Limitations, License |

**Root cause:** Sequential agent rewrites overwrote each other rather than merging. Each version was shorter than the last (318 → 256 → 214), confirming material was lost.

**Resolution:** I merged all three versions into a single 578-line README (21 sections + table of contents + TL;DR table), recovered all unique content, and committed as `bdc457b` to SWARM_CONSOLIDATED remote `main`. Verified via `git merge-base --is-ancestor bdc457b origin/main` → YES.

**Deployed:** `https://github.com/eltonaguiar/SWARM_CONSOLIDATED` now has the merged README live on `main`.

---

## 3. Performance findings per AI_MENU items

The AI_MENU (`tools/ai_menu.sh` in the parent repo) routes swarms through these agent CLIs:

**Agent CLIs:** claude, command-code, cursor, opencode, kilo, codex, grok, gemini, qwen, copilot, continue, hermes, openclaude, blackbox, freebuff, kimi, agent, freellm, browseruse, ollama

**Repo-local swarm commands:** litellm (rotating proxy on :4000), swarm (`tools/swarm/swarm_run.py` multi-engine fan-out), consult (`tools/swarm/api_consult.py` single-provider API consult)

### Live key/probe results (2026-11-13)

A `/models` 200 response is **not** evidence a key can serve a request. Every key entering a swarm must pass a 3-part admission test: (1) tool-calling call returns `tool_calls`, (2) ~34k-token context-capacity call succeeds, (3) chat-level auth/balance succeeds.

| Provider / key | `/models` | `/chat/completions` | Swarm verdict |
|---|---|---|---|
| NVIDIA + ALT | 200, 83 models | every call times out; per-model 404 | **unusable** |
| SambaNova | 200, 5 models | 401 incorrect key | **unusable** |
| Groq | 200, 11 models | 200 small; **413 on 15k-token prompt** (TPM 8,000) | unusable as main-agent fallback |
| Cerebras | 200 | 200 incl. 34k-token + tool call | **works** |
| DeepInfra | 200 | 200, 35k prompt, tool call | **works** |
| AIML API | 200 | 200, 34k prompt, tool call | **works** ($20 paid cap) |
| xAI (Grok) | 200, 13 models | 200, 33.5k prompt, tool call | **works** |
| Kimi | 200, 6 models | 429 engine overloaded (persistent) | flaky |
| Novita / Z.AI GLM / SiliconFlow | 200 | 402/429 insufficient balance | **no credits** |
| Gemini ×3 | — | 401 invalid credentials | **dead** |
| Together ×2 / Hyperbolic | — | 401 | **dead** |
| Fireworks ×2 | — | 412 account suspended | **dead** |
| Mistral ×3 | 200 | 200 but `content` is a list of blocks | fragile (breaks `.strip()` clients) |

### Verified fallback chain (Hermes, this machine)

```
primary  deepseek-v4-flash
  1. xai / grok-4.5                    (tool call OK, 33.5k prompt OK)
  2. deepinfra / DeepSeek-V3.2         (tool call OK, 35k prompt OK)
  3. aimlapi / gpt-4o-mini             (tool call OK, 34k prompt OK)
  4. cerebras / gpt-oss-120b           (tool call OK, 34k prompt OK)
  5. kimi-coding / kimi-k3.1-pro       (key valid, 429s often — last resort)
```

Groq was position 1 in an earlier draft and failed live with `413 ... TPM: Limit 8000, Requested 15391` — a fallback that cannot hold the prompt is worse than no fallback, because it burns the single fallback activation per turn.

### Model assessment for swarm research (`SWARM_MODEL_ASSESSMENT_SERVICENOW_RESEARCH_2026-11-13.md`)

Tested 38 proxy groups on a neutral ServiceNow Discovery research question (must name: Identification Rules, Reconciliation Rules, Data Precedence, CMDB 360/multisource):

- **0 models named all 4 terms** memory-only; best score 3/4.
- **25 of 38 returned empty `content` with `finish=length`** — reasoning consumed the whole 900-token budget. This is a **budget artifact, not ignorance**: re-asking with `max_tokens=3500` recovered 8 of 18 cloud candidates and 2 of 7 local.
- **Hard rule:** `max_tokens >= 3000` for any reasoning alias, or a `200` with `content: ""` is indistinguishable from a refusal.
- **Retrieval matters more than the model:** `ULTRA_PAID_MODE` went 1/4 (memory) → 3/4 (with harness-fetched pages); `ULTRA_FREE_LOCAL_FAST` stayed 0/4 even with web.
- **Best research roster:** `ZZZ_BAD_LEGACY_MIXED_F_MODE_FAST` and `ULTRA_PAID_MODE` with retrieval (3/4); `ULTRA_FREE_GEMINI` memory-only (3/4, fastest useful answer at 2.9s).

### Free-tier economics (real currency is TPM/RPD, not context window)

| Provider | Model | Context | Documented limit | Implication |
|----------|-------|---------|------------------|-------------|
| Groq | gpt-oss-120b | 131K | 30 RPM, 1,000 RPD, 8,000 TPM, 200k TPD | 131K context is a lie in practice |
| Kilo Code | kilo-auto/free, `:free` | 256K–1M | 200 req/hr | Great for wide fan-out, useless for long prompts |
| Google Gemini | 2.5/3.x Flash | 1M | free tier, no card | Best free context; treat as non-confidential |
| Cloudflare Workers AI | various | 128K | 10k neurons/day shared | Fine for aux tasks |

Plan fan-out width against TPM, not context size.

---

## 4. Architecture comparison (merged into README)

### Ruflo vs tools/swarm (the two systems that actually run)

| | Ruflo Swarm (`.ruflo/`) | tools/swarm (`tools/swarm/`) |
|---|---|---|
| Drives via | Hermes Agent (`hermes chat -q`) | Direct API calls + CLI adapters |
| Agent model | 5 specialized agents | 16+ engine adapters |
| Free tier | ✅ Yes | ❌ Needs API keys |
| Memory/persistence | ❌ Ephemeral | ✅ SQLite sessions (`--persist-sessions`) |
| Multi-model consensus | ❌ Single model per agent | ✅ N models → ranked synthesis |
| Best for | Audit/strategy/bugs, continuous loops | PR reviews, second opinions, ad-hoc |

### Ruflo vs tools/swarm_v2

| Dimension | Ruflo swarm | swarm_v2 |
|-----------|-------------|----------|
| Parallelism | ⚠️ Sequential via Hermes CLI | ✅ True asyncio + ThreadPoolExecutor |
| Memory | Ephemeral per run | Persistent `SwarmMemory` + `MessageBus` |
| Safety/guards | ⚠️ Sanitization only | ✅ AST static analysis, sandboxed tests |
| Cost ceiling | ❌ Advisory only | ✅ `cost_cap_usd` hard abort |
| Tests | 0 | 300+ |
| Best for | Free-tier audit/strategy | Production engineering workflows |

---

## 5. Critical fixes applied (2026-11-13)

1. **LiteLLM concurrency serialization** — `tools/start_litellm_proxy.sh:435`: `--num_workers 1` → raise workers or bypass proxy for fan-out leg.
2. **Health gate for thinking models** — `core/combine_team.py`, `core/debate_team.py`: `is_live()` checks `reasoning_content` when `content` empty.
3. **Free-key admission test** — `probe_providers.py`: every key must pass tool-calls + 34k-context + chat-auth.
4. **Proxy-first pattern** — No swarm reads `dbpasses.txt` directly; launcher owns keys, proxy holds them. One env var: `LITELLM_BASE_URL=http://localhost:4000/v1`.

---

## 6. Known bugs & limitations (P0)

| Severity | File | Issue |
|----------|------|-------|
| P0 | `swarm_e2e_fix.py` | `LIVE_ALIASES` undefined → NameError |
| P0 | `swarm_unified.py` | `run_combine_team(query, model)` passes model alias string as `n` → TypeError |
| P0 | `swarm_model_eval.py` | `call_model()` ignores resolved `base_url`, always uses `:4000` |
| P0 | `swarm_fix_worktree.py` | Same issues as `swarm_e2e_fix.py` |
| MEDIUM | `swarm_parallel_runner.py` | Exists but never called — all "parallel" swarms are sequential |
| MEDIUM | `core/combine_team.py` | Cost cap continues processing instead of hard abort |
| MEDIUM | Ruflo | 0 automated tests |

---

## 7. Recommendations (ordered by payoff)

1. Kill the serialization: raise `--num_workers` in `tools/start_litellm_proxy.sh:435`, or route fan-out leg direct to upstreams.
2. Adopt the 3-part admission test in `probe_providers.py`, emit machine-readable pool file.
3. Separate "panel" keys from "report" keys (free 8k TPM keys vote but can't synthesize long context).
4. Add planner + critic stages around `CombineTeam` (gpt-researcher / STORM shape).
5. Structured output required: votes as JSON `{claim, confidence, evidence_ref}`.
6. Budget guard per run: track tokens, abort at `cost_cap_usd`.
7. Route log per call: provider, model, latency, tokens, cost, fallback depth.
8. Ground against local data always — free proxy models have no browser and hallucinate fetches.

---

## 8. Quick start

```bash
# SWARM_CONSOLIDATED
git clone https://github.com/eltonaguiar/SWARM_CONSOLIDATED.git
cd SWARM_CONSOLIDATED
pip install -r requirements.txt
bash tools/start_litellm_proxy.sh
python3 swarm_task.py "is approach X better than Y?" --mode combine
python3 cli/swarm_picker.py

# Parent repo (TORONTOEVENTS_ANTIGRAVITY)
python3 .ruflo/orchestrator.py --swarm audit --tier free          # Ruflo (Hermes-driven, free)
python3 tools/swarm/swarm_run.py --preset consensus-3            # tools/swarm second opinion
tools/ai_menu.sh swarm                                            # AI_MENU launcher
```

---

## 9. Related documents

- `SWARM_ARCHITECTURE_COMPARISON.md` — architecture patterns + recommended 3-agent parallel swarm
- `SWARM_CONCURRENCY_RESEARCH_2026-11-13.md` — LiteLLM hardening, token bucket, circuit breakers
- `SWARM_FREE_KEYS_FINDINGS_2026-11-13.md` — crash root cause + free-key research patterns
- `SWARM_MODEL_ASSESSMENT_SERVICENOW_RESEARCH_2026-11-13.md` — model eval with/without retrieval
- `SWARM_RESEARCH_PATTERNS_2026-11-13.md` — how pro swarms (gpt-researcher, STORM, open_deep_research) work
- `FEEDBACK_FROM_OPENCODE/hermes/hermes-peer-review.md` — P0/P1 defects in orchestration code
- `RUFLO_SWARM_GUIDE.MD`, `HERMES_SWARM_NOTES.MD` — Ruflo/Hermes operation

---

## 10. Git & deployment notes

- README.md merged commit on SWARM_CONSOLIDATED remote `main`: `bdc457b` (verified ancestor of `origin/main`).
- This findings file: committed to the `swarmmethodquality-v2` worktree branch of `eltonaguiar/findtorontoevents_antigravity.ca`.
- **Branch divergence note:** `origin/main` and `swarmmethodquality-v2` diverged (neither contains the other). I did **not** force-push this branch to remote `main`, per safety rules (`git push --force` forbidden). The findings file is on branch `swarmmethodquality-v2`; merge it into `main` when ready.
- No secrets exposed; `~/dbpasses.txt` is gitignored; keys referenced by name only.
