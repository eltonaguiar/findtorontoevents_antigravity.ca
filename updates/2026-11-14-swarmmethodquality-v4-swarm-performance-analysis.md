# SWARM_METHODQUALITY-V4 — Swarm Performance Analysis Summary

> **Date:** 2026-11-14  
> **Worktree:** swarmmethodquality-v4  
> **Author:** Kilo (analysis session)  
> **Source Repo:** https://github.com/eltonaguiar/SWARM_CONSOLIDATED  
> **Parent Repo:** findtorontoevents_antigravity.ca (where AI_MENU and swarm tooling live)

---

## Executive Summary

Analyzed the SWARM_CONSOLIDATED repository's three swarm architectures and updated the README.md with comprehensive findings. The key deliverable is PR #1 with a merged README that preserves all original content plus adds the live benchmark results with proper caveats.

---

## Key Findings

### 1. Is Ruflo Swarm better than Hermes Swarm?

**Answer: No separate "Hermes Swarm" exists.** Ruflo Swarm *is* the Hermes-driven swarm — `.ruflo/orchestrator.py` dispatches work through Hermes Agent (Nous Research v0.12.0) with OpenRouter backend. There's no distinct "Hermes Swarm" architecture.

**Real comparison:** Ruflo (Hermes-driven) vs tools/swarm (direct API)

| System | Best For | Free Tier | Memory | Consensus |
|--------|----------|-----------|--------|-----------|
| **Ruflo** | Structured audit/strategy/bugs, continuous loops | ✅ OpenRouter free | ❌ Ephemeral | ❌ Single model/agent |
| **tools/swarm** | PR reviews, multi-model consensus, second opinions | ❌ Needs paid keys | ✅ SQLite (`--persist-sessions`) | ✅ N models parallel |

**Rule of thumb:** Need second opinion → `tools/swarm`; audit/hunt bugs → `.ruflo/`; persistent memory → `tools/swarm --persist-sessions`; daily live-data check → `.ruflo/ --continuous`.

### 2. tools/swarm_v2 vs Ruflo Swarm

**tools/swarm_v2 (core/v2/) is SUPERIOR for production engineering:**

| Dimension | tools/swarm_v2 | Ruflo Swarm |
|-----------|----------------|-------------|
| **Parallelism** | ✅ True asyncio + ThreadPoolExecutor | ⚠️ Sequential via Hermes CLI |
| **Memory** | ✅ ChromaDB + BM25/vector hybrid search | ❌ File-based only |
| **Skill Export** | ✅ Claude/OpenAI formats | ❌ Not implemented |
| **Safety** | ✅ AST static analysis, sandboxed tests | ⚠️ Sanitization only |
| **Cost Ceiling** | ✅ Hard `cost_cap_usd` abort | ❌ Advisory only |
| **Health Gates** | ✅ `is_live()` checks `content` + `reasoning_content` | ❌ Not implemented |
| **Testing** | 300+ tests | 0 automated tests |
| **Production Ready** | ✅ Yes (PR review, CI, coding) | ⚠️ Beta |

**When to use Ruflo:** Free-tier-only, zero-setup audit/strategy, Windows+WSL workflows.

---

## Live Reliability Benchmark (2026-05-05)

> **Source:** `findtorontoevents_antigravity.ca/updates/SWARM_STYLE_DIFF.MD` (parent repo)

### Test Results

| Task | tools/swarm (deepseek) | Ruflo Swarm |
|------|------------------------|-------------|
| **PR Review** (4 PRs) | ✅ SUCCESS, 10.91s, $0.0016 | ❌ FAILED (HTTP 404) |
| **Actions Failure Analysis** | ✅ SUCCESS, 13.24s, $0.0016 | ❌ FAILED (HTTP 404) |
| **Audit Dashboard Eval** | Ready (prompt created) | ❌ Both agents failed (HTTP 404) |

### Critical Caveats (Config-Dependent)

⚠️ **This is CONFIG vs CONFIG, not architecture vs architecture:**

1. tools/swarm used **PAID DeepSeek key** (`deepseek-v4-flash`) — reliable, fast, structured JSON
2. Ruflo ran **FREE-TIER ONLY** — no paid keys wired into Hermes config
3. OpenRouter free-tier models were **down/rate-limited** at test time (persistent 404/429)
4. Hermes `chat -q --source tool --yolo` path may have OpenRouter config issues in WSL

**With paid keys in Hermes config or `--direct` mode calling `api_consult.py` directly, re-benchmark before concluding.** The failure reflects missing configuration, not an architectural cap.

---

## Critical Architectural Finding: LiteLLM Bottleneck

**Testing 16 models on broken mermaid diagram: 14/16 solved, all performed equally (~$0.001–$0.0023/task).**

**Bottleneck is NOT model capability — it's LiteLLM proxy concurrency.**

`tools/start_litellm_proxy.sh:435` launches with `--num_workers 1` — a single worker serializes every request. Swarm fan-out queues behind one worker; timeouts pile up; proxy looks "crashed."

**Industry-standard fix:** Route each agent to its **own independent inference endpoint**:
- Agent 1 → vLLM :8000 (qwen3-8b)
- Agent 2 → Ollama :11434 (qwen2.5-coder:7b)  
- Agent 3 → Ollama :11434 (qwen3:30b-a3b)
- (Optional) Agent 4 → Windows Hermes :8642

All run simultaneously, no shared queue, no single point of failure.

---

## Free-Key Admission Test (Critical)

A `/models` 200 response is **NOT** evidence a key can serve requests. Every key must pass:

1. **Tool-calling call** → returns `tool_calls`
2. **34k-token context call** → succeeds
3. **Chat-level auth/balance** → succeeds

### Verified Working (2026-11-13 probes)

| Provider | Status | Notes |
|----------|--------|-------|
| Cerebras (gpt-oss-120b) | ✅ Works | Tool call + 34k prompt OK |
| DeepInfra (DeepSeek-V3.2) | ✅ Works | Tool call + 35k prompt OK |
| AIML API (gpt-4o-mini) | ✅ Works | $20 paid cap |
| xAI (Grok-4.5) | ✅ Works | Tool call + 33.5k prompt OK |

### Dead/Unusable

| Provider | Issue |
|----------|-------|
| NVIDIA (Kimi/GLM/DeepSeek) | 404/timeouts, only Nemotron 3.5 works |
| SambaNova | 401 incorrect key |
| Groq | 413 on 15k-token prompt (TPM 8,000 limit) |
| Gemini ×3 | 401 invalid credentials |
| Together/Fireworks | 401/412 suspended |
| Mistral | Fragile — `content` is list of blocks, breaks `.strip()` |

**Verified Fallback Chain (Hermes):**
```
primary: deepseek-v4-flash
1. xai/grok-4.5
2. deepinfra/DeepSeek-V3.2
3. aimlapi/gpt-4o-mini
4. cerebras/gpt-oss-120b
5. kimi-coding/kimi-k3.1-pro (429s often)
```

Groq was position 1 in earlier draft — failed live with `413 TPM: Limit 8000, Requested 15391`. A fallback that can't hold the prompt is worse than no fallback.

---

## P0 Bugs Needing Fix (from Hermes Peer Review 2026-11-13)

| File | Issue |
|------|-------|
| `swarm_e2e_fix.py` | `LIVE_ALIASES` undefined → NameError |
| `swarm_unified.py` | `run_combine_team(query, model)` passes model alias as `n` parameter → TypeError |
| `swarm_model_eval.py` | `call_model()` ignores resolved `base_url`, always uses `:4000` |
| `swarm_fix_worktree.py` | Same issues as `swarm_e2e_fix.py` |
| `swarm_parallel_runner.py` | Exists but **never called** by main workflow — all "parallel" swarms are sequential |

---

## Actions Taken

1. **Created PR #1:** https://github.com/eltonaguiar/SWARM_CONSOLIDATED/pull/1
   - Merged README preserving ALL original main branch content (578 lines, 19 sections)
   - Added "Live Reliability Benchmark (2026-05-05)" section with config-dependent caveats
   - Fixed source link to parent repo: `findtorontoevents_antigravity.ca/updates/SWARM_STYLE_DIFF.MD`
   - Updated TL;DR with benchmark verdict and caveats
   - Updated Maintenance log with merge note

2. **Key README improvements:**
   - Table of Contents with 19 sections
   - All original sections preserved: Performance Snapshot, Six Architectures, Two Systems, Ruflo vs Hermes, tools/swarm_v2 vs Ruflo, AI_MENU Guide, Performance Findings, LiteLLM Bottleneck, How Pro Swarms Research, Critical Fixes, Known Bugs, Quick Start, Recommendations, Related Docs, TL;DR, AI_MENU Mapping, Maintenance
   - New benchmark section with proper caveats

---

## Recommendations (Priority Order)

1. **Fix LiteLLM serialization** — Raise `--num_workers` in `tools/start_litellm_proxy.sh:435` or bypass proxy for fan-out leg
2. **Wire paid keys into Hermes** — Add OpenRouter API keys to `~/.hermes/config.toml` for Ruflo paid tier
3. **Add `--direct` mode to Ruflo** — Bypass WSL/Hermes, call `api_consult.py` directly with YAML agent configs
4. **Wire `swarm_parallel_runner.py`** — Connect the existing parallel executor to main workflows
5. **Fix P0 bugs** — `swarm_e2e_fix.py`, `swarm_unified.py`, `swarm_model_eval.py`, `swarm_fix_worktree.py`
6. **Adopt 3-part admission test** as gate in `probe_providers.py` (tool-calls + 34k context + chat auth)
7. **Add planner + critic stage** to CombineTeam (gpt-researcher/STORM pattern)
8. **Separate panel vs report keys** — Free 8k TPM keys for panel voters only; paid keys for report writers

---

## Files Modified

| File | Change |
|------|--------|
| `SWARM_CONSOLIDATED/README.md` | PR #1: Merged comprehensive update with live benchmark |
| `findtorontoevents_antigravity.ca/updates/2026-11-14-swarmmethodquality-v4-swarm-performance-analysis.md` | This summary document |

---

## Next Steps

1. **Review and merge PR #1** after validation
2. **Fix P0 bugs** in `swarm_unified.py`, `swarm_model_eval.py`, `swarm_e2e_fix.py`, `swarm_fix_worktree.py`
3. **Wire paid keys into Hermes** for Ruflo paid tier benchmark re-run
4. **Raise LiteLLM workers** or implement direct upstream parallel calls
5. **Connect `swarm_parallel_runner.py`** to main workflow paths

---

*Generated by Kilo analysis session in worktree `swarmmethodquality-v4` on 2026-11-14*