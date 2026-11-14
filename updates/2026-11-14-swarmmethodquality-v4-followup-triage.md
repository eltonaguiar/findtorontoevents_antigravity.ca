# SWARM_METHODQUALITY-V4 — Follow-up Triage (P0 bugs + Ruflo direct mode)

> **Date:** 2026-11-14T08:17Z  
> **Worktree:** swarmmethodquality-v4  
> **Scope:** Read-only re-verification of the 2026-11-13 Hermes peer-review P0 claims against `eltonaguiar/SWARM_CONSOLIDATED@main`, plus feasibility of fixing Ruflo's OpenRouter 404.  
> **Method:** GitHub API + raw file inspection; nothing modified during triage.

---

## TL;DR

- **3 of 5** peer-review P0 claims are **already FIXED** on main.
- **2 remain:** `swarm_model_eval.py` hardcodes `base_url`; `swarm_parallel_runner.py` is a dead duplicate of the acceptance driver.
- **Ruflo 404 is not fixable in this repo** — `.ruflo/orchestrator.py` lives in the parent repo. In-repo `run_ruflo()` is only a proxy shim with no `--direct` mode and discards `base_url`/key.

---

## Claim status table

| # | Claim (2026-11-13 peer review) | Status | Evidence on GitHub `main` |
|---|---|---|---|
| 1 | `swarm_e2e_fix.py`: undefined `LIVE_ALIASES` + `call_with_fallback` import mismatch | **FIXED** | No `LIVE_ALIASES` in file; `call_with_fallback` defined locally at `swarm_e2e_fix.py:95`, uses `resolve_best_model()` → `base_url` at `:97-107`. Imports consistent (`core.transport`, `probe_providers`). |
| 2 | `swarm_unified.py`: `run_combine_team(query, model)` passes alias string as `n` | **FIXED** | `swarm_unified.py:139` uses `n=min(3,len(aliases)), aliases=aliases[:3]`; `:186` uses `n=3, aliases=aliases[:3]`. All call sites pass explicit int `n`. |
| 3 | `swarm_model_eval.py`: `call_model()` ignores resolved `base_url`, always `:4000` | **STILL-PRESENT** | `swarm_model_eval.py:172-180` hardcodes `base_url="http://localhost:4000/v1/chat/completions"`; `:280-284` resolves `best = resolve_best_model()` but passes only `best["alias"]`, never `best["base_url"]`. Fallback is dead code. |
| 4 | `swarm_fix_worktree.py`: same `LIVE_ALIASES` / `call_with_fallback` defects | **FIXED** | `LIVE_ALIASES` defined at `:33-40`; `call_with_fallback` defined `:98`, used `:126-127`; import correct `:19`. Residual (not the claimed bug): `PROXY_URL` still hardcoded at `:107`, loop is sequential. |
| 5 | `swarm_parallel_runner.py` exists but never imported/called by a main workflow | **STILL-PRESENT** | File exists (tree blob `559f0b4f…`, 7982 B) but its content is a duplicate of the acceptance driver (docstring: "Swarm Acceptance Driver — BROKENMERMAIDTEST (Phase 2)"). Zero `.py` references repo-wide; only mentioned in the peer-review doc. Not a real parallel runner. |

---

## Ruflo / OpenRouter 404 — feasibility

| Check | Result |
|---|---|
| `.ruflo/orchestrator.py` in this repo? | **ABSENT** (404; no `.ruflo` tree). Lives in parent repo `TORONTOEVENTS_ANTIGRAVITY`. |
| `--direct` mode in `swarm_unified.py run_ruflo()`? | **No.** Uses `fetch_live_aliases()` + `run_combine_team(..., n=1, aliases=[alias])`; no `base_url`, no key, no direct flag. |
| `--tier {free,paid,decision}` effect? | **Cosmetic** — only stamped onto result metadata (`:372`), does not change routing/creds. |
| Paid path exists? | **Disconnected.** `probe_providers.py:204-216` reads `OPENROUTER_API_KEY` and probes OpenRouter directly, but `run_with_fallback` (`:355-362`) keeps only `p["alias"]` and discards `p["base_url"]`/`key_env`. |
| Feasible in-repo? | **Partially.** `run_combine_team` already accepts `base_url` + `api_key` (`core/combine_team.py:62-63`), so threading `p["base_url"]`/key through `run_with_fallback` → runner + a `--direct` flag is ~10–20 LOC **if the 404 is proxy-side**. If the 404 originates inside `.ruflo/orchestrator.py`, it cannot be fixed here. |

---

## Prioritized fix list (STILL-PRESENT only)

1. **P0 — `swarm_model_eval.py:172-180` / `:280-284`:** make `call_model()` accept `base_url` and pass `best["base_url"]` from `resolve_best_model()`. Restores Ollama/Pollinations/OpenRouter fallback (currently dead).
2. **P1 — `swarm_parallel_runner.py` on `main`:** replace the acceptance-driver duplicate with the real parallel implementation (a 216-line `concurrent.futures` version exists in the local worktree but is NOT on main) or delete it; then wire it into `swarm_e2e_fix.py` to replace the sequential single-model path (`:95-117`, used `:141`). Otherwise "parallel swarm" stays sequential and the file stays dead code.
3. **P2 — Ruflo direct/paid path (only if 404 is proxy-side):** stop discarding `base_url`/`key_env` in `run_with_fallback` (`swarm_unified.py:355-362`) and add `--direct` that passes `p["base_url"]` + `OPENROUTER_API_KEY` into `run_combine_team`. Blocked on `.ruflo/orchestrator.py` (parent repo).

---

## Documentation outcome (this session)

- `SWARM_CONSOLIDATED/README.md` reconciled and committed to **main** as `9ec9feaf` (blob `31fa7122`, 628 lines / 42,047 bytes / 22 sections). Bases on the 3-agent merged content (`bdc457b`) and grafts the *Live Reliability Benchmark (2026-05-05)* section + TOC entry + TL;DR row + config-dependent caveats.
- PR #1 **closed as superseded** (it was `mergeable_state: dirty`; merging would have clobbered `bdc457b`).
- Findings summary committed to parent main: `updates/2026-11-14-swarmmethodquality-v4-swarm-performance-analysis.md` (`95520e55b35`).

---

## Recommended next actions

1. Approve and apply P0 fix #1 (two-line change in `swarm_model_eval.py`).
2. Decide whether to promote the local 216-line parallel runner to `main` and wire it (P1).
3. Re-run the Ruflo benchmark **after** wiring paid keys into Hermes and/or adding `--direct`, so the README's "config-dependent" caveat is replaced with a fair architecture-vs-architecture result.

---

*Generated by Kilo in worktree `swarmmethodquality-v4` on 2026-11-14.*
