# Swarm Consolidated README Collision Audit

**Date:** 2026-11-14  
**Worktree:** swarmmethodquality  
**Author:** Kilo (OpenCode agent)  
**Repo:** SWARM_CONSOLIDATED (eltonaguiar/SWARM_CONSOLIDATED)  
**Trigger:** Three-agent collision on README.md (07:54–07:58 UTC), reconciled via merge commit `bdc457b`  

---

## Incident Summary

Three agent sessions concurrently edited `README.md` on `eltonaguiar/SWARM_CONSOLIDATED` within a 4-minute window:

| Agent Timestamp | SHA | Summary |
|-----------------|-----|---------|
| `097d10f` 07:54:50Z | Initial | 318-line README with 11 numbered sections (What this repo contains → Appendix AI_MENU mapping) |
| `15e087c` 07:54:51Z | Reformat | 256-line README with new heading style (`SWARM_CONSOLIDATED — Multi-Agent AI Swarm Orchestration`) |
| `aaaf234` 07:58:04Z | My update | 214-line update adding performance snapshot, Ruflo vs Hermes comparison, and tools/swarm_v2 vs Ruflo engine comparison |
| `bdc457b` 08:03:29Z | Merge | **578-line merged README** reconciling all 3 versions, adding TOC and TL;DR |

---

## Collision Analysis — No Data Loss

**Verification:** All unique sections from all 3 agent writes are present in the merged `bdc457b` README. Zero duplicate section headers exist after merge. The merge preserved all content from all three authors.

### Merged README Metrics (current main HEAD)

| Metric | Value |
|--------|-------|
| Lines | 578 |
| Words | 5,233 |
| Bytes | 38,945 |
| Sections | 21 |
| Duplicate headers | 0 |
| TOC present | ✅ |
| TL;DR present | ✅ |

### Sections Preserved Across All Authors

| Section | Author |
|---------|--------|
| Performance Snapshot (2026-11-13) | `097d10f` |
| Swarm Architecture Comparison (6 engines) | `15e087c` |
| Ruflo Swarm vs Hermes Swarm | All 3 |
| tools/swarm_v2 vs Ruflo Swarm | All 3 |
| AI_MENU / Swarm Picker — Tool Selection Guide | All 3 |
| Performance Findings per AI_MENU Items | `097d10f` |
| Verified fallback chain (Hermes, this machine) | `097d10f` |
| Model assessment for swarm research | `097d10f` |
| Free-tier economics | `097d10f` |
| Critical Architectural Finding: LiteLLM Bottleneck | All 3 |
| How Professional Swarms Do Research | `097d10f` |
| Critical Fixes Applied (2026-11-13) | All 3 |
| Known Bugs & Limitations | All 3 |
| Quick Start | All 3 |
| Recommendations (ordered by payoff) | All 3 |
| Related Documents | All 3 |
| TL;DR summary per section | Merge commit `bdc457b` |
| Appendix — AI_MENU → Swarm Mapping | All 3 |
| Table of Contents | Merge commit `bdc457b` |

---

## Key Findings

### 1. Ruflo Swarm vs Hermes Swarm
- **Ruflo IS Hermes-driven** — there is no separate "Hermes Swarm." Ruflo runs through Hermes Agent (`.ruflo/orchestrator.py`).
- Ruflo wins for free-tier specialized audit (5 roles, 3-attempt model failover, WSL bridge).
- Hermes gateway (Windows, paid keys) wins only for low-latency single tasks requiring true parallelism.

### 2. tools/swarm_v2 vs Ruflo Swarm
- **swarm_v2 is superior for production engineering** — true asyncio + ThreadPoolExecutor parallelism, ChromaDB persistent memory, skill export, AST safety guards, hard cost ceilings (`cost_cap_usd = $0.05`), 300+ tests.
- Ruflo wins only for zero-setup free-tier audit/strategy work.

### 3. AI_MENU / Swarm Picker Recommendations
| Goal | Use |
|------|-----|
| Default implementation | `swarmv2` (CodingSwarm) |
| Deep research | `swarm-research` + retrieval |
| Free-tier only | `ruflo --tier free` |
| PR review | `swarmv2 pr-review` |
| CI health | `swarmv2 actions` |

### 4. Performance Findings (live probes 2026-11-13)
- **`/models` 200 ≠ usable** — must probe tool-calls + 34k-token context + chat auth
- **Best research roster:** `ZZZ_BAD_LEGACY_MIXED_F_MODE_FAST` (3/4 terms) + `ULTRA_PAID_MODE` with retrieval
- **~50% of `dbpasses.txt` keys dead** at `/chat/completions` despite `/models` returning 200
- Groq 413s on 15k-token prompts (TPM limit 8,000)
- NVIDIA/SambaNova/Gemini/Together/Fireworks/dead at chat level

### 5. LiteLLM Concurrency Bottleneck
- `--num_workers 1` serializes all swarm fan-out calls through one event loop
- Industry standard: give each agent its own endpoint (vLLM :8000, Ollama :11434) or raise workers

### 6. P0 Bugs Requiring Fix (Hermes Peer Review 2026-11-13)
| File | Severity | Issue |
|------|----------|-------|
| `swarm_e2e_fix.py` | P0 | `LIVE_ALIASES` undefined → NameError; import path mismatch |
| `swarm_unified.py` | P0 | `run_combine_team(query, model)` passes model alias as `n` parameter → TypeError |
| `swarm_model_eval.py` | P0 | `call_model()` ignores resolved `base_url` → always uses `:4000` |
| `swarm_fix_worktree.py` | P0 | Same issues as `swarm_e2e_fix.py` |

### 7. Merge Preserved All Content
No sections lost during collision. The merge commit `bdc457b` intentionally reconciled all 3 agent-authored versions, adding only TOC and TL;DR as structural improvements.

---

## Commit History

```
097d10f 07:54:50Z  Initial README (318 lines, 11 sections)
15e087c 07:54:51Z  Reformat README (256 lines, new heading style)
aaaf234 07:58:04Z  My update: performance snapshot + Ruflo/Hermes + swarm_v2 comparison (214 lines)
bdc457b 08:03:29Z  Merge commit: reconciles all 3 versions → 578 lines, adds TOC + TL;DR
```

---

## TL;DR per Major Question

| Question | Answer |
|----------|--------|
| **Is Ruflo Swarm better than Hermes Swarm?** | Ruflo Swarm *is* the Hermes-driven swarm — no separate "Hermes Swarm." Ruflo wins for free-tier specialized audit; use Hermes gateway (paid) only when you need true parallelism for low-latency single tasks. |
| **Is tools/swarm_v2 better than Ruflo?** | swarm_v2 for production engineering (parallelism, memory, safety, tests). Ruflo for free-tier audit/strategy with zero setup. |
| **What's the #1 performance problem?** | LiteLLM `--num_workers 1` serializes all swarm fan-out calls. Fix: give each agent its own endpoint or raise workers. |
| **Which keys actually work in a swarm?** | Cerebras, DeepInfra, AIML API, xAI (Grok) pass tool-calls + 34k-context + chat auth. Groq 413s on 15k tokens. NVIDIA/SambaNova/Gemini/Together/Fireworks dead at chat level despite `/models` 200. |
| **Best research setup?** | Planner → CombineTeam (diverse providers) → Critic → Publisher, with harness-fetched retrieval. Expect ~3/4 on expert benchmarks even with retrieval. |

---

## Appendices

### Appendix A: Agent Write Signatures

| SHA | Lines | Unique Sections | Key Contribution |
|-----|-------|-----------------|------------------|
| `097d10f` | 318 | 11 | Initial structure + Performance Findings + Professional Swarms + all TL;DRs |
| `15e087c` | 256 | 10 | Reformatted heading style + Six Swarm Architectures + Two Swarm Systems |
| `aaaf234` | 214 | 6 | My update: Performance Snapshot + Ruflo vs Hermes + tools/swarm_v2 vs Ruflo + Benchmark |
| `bdc457b` | 578 | 21 | Merge: reconciles all + adds TOC + TL;DR |

### Appendix B: Merge Reconciliation Heuristic

1. **Collect** all unique section headers from all agent versions
2. **Group** sections by semantic equivalence (same topic, different heading style)
3. **Preserve** content from all authors under the canonical heading style
4. **Add** TOC and TL;DR as structural improvements only (no content sacrifice)
5. **Verify** zero duplicate headers in final merged output

### Appendix C: Collision Prevention (Future)

- Use feature branches + PR review for README changes
- Schedule edit windows (no concurrent edits)
- Add `git pull --rebase` before editing shared docs
- For critical docs, use `git merge` with conflict resolution instead of ad-hoc writes

---

**End of report.**