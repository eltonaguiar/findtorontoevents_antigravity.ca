---
name: ParallelSwarm
description: Distributed parallel implementation + review + test swarm across the whole free/paid AI key pool and cross-PC peers. Probes peers/providers for signs of life, assigns each action item (one file) to a live working model, has it implement + place the file, validates it, then runs a code-swarm review → testing plan → swarm-executed tests. Use when the user says "/ParallelSwarm", "parallel swarm", "distribute these implementations", "code swarm across AIs", "build these N files in parallel fast", or wants many action items implemented + reviewed + tested concurrently. Aliases - parallel-swarm, pswarm, distributed-swarm, code-swarm-distributed.
---

# /ParallelSwarm — Distributed parallel build → review → test swarm

Turn **N action items into N files in parallel**, each implemented by a *different* live
AI provider (or a cross-PC peer), then validated, swarm-reviewed, and swarm-tested.
Exploits the fact that this box has dozens of free + paid keys in `~/dbpasses.txt`
and env, plus live peer agents on the LAN — so independent work runs concurrently and fast.

> **Golden rule:** AI-written code is *untrusted until validated*. Every file an external
> model produces is syntax-checked, contract-checked, and test-gated before it counts as done.
> Never let a provider's output overwrite an existing file you haven't read first.

## Pipeline

```
Phase 0  SIGNS OF LIFE      probe cross-PC peers + provider keys → list of LIVE workers
   │
Phase 1  PARALLEL IMPLEMENT  1 action item → 1 file → 1 distinct live worker (concurrent)
   │                          worker returns full file; orchestrator writes it to the target path
Phase 2  VALIDATE            syntax / import / contract / no-secret / lands-at-right-path
   │                          (failed item → reassign to a different live worker, max 2 retries)
Phase 3  CODE-SWARM REVIEW   2–3 engines review each new file → verdict + a structured TESTING PLAN
   │
Phase 4  SWARM TEST          distribute test-writing across providers → run pytest/node → aggregate
   │
   └────▶ report: per-item worker, verdict, test result, artifacts
```

Phases 1 and 4 fan out; Phases 0/2/3 are barriers (you need the full live-worker list before
assigning, all files present before reviewing, all reviews before declaring done).

## Phase 0 — Signs of life (who can I dispatch to RIGHT NOW)

Two worker pools. Probe both; you only need a handful of live ones.

**A) Cross-PC peers** (other machines/agents that can implement + place a file themselves):
```bash
curl -s -m 4 http://192.168.2.32:8788/health | python3 -c "import sys,json;d=json.load(sys.stdin);print('peers:',[ (k,v.get('last_seen_ts_utc')) for k,v in d.get('peer_registry',{}).items()])"
```
A peer is "alive" if `last_seen_ts_utc` is within ~10 min. To delegate to one, send a
`task.request` (see Phase 1B) and wait for its reply on your inbox.

**B) Local provider keys** (call the model API directly). The engine→key map is
`tools/swarm/ENGINE_KEY_ENVS.py`; keys resolve from env first, then `~/dbpasses.txt`
(gitignored — never echo a key). List engines and cheap-ping the ones with keys:
```bash
python3 tools/swarm/swarm_run.py --list-engines        # 22 engines
# Cheap liveness ping per provider (api_consult exits non-zero / errors if the key is dead):
for p in cerebras groq gemini_api nvidia_deepseek deepseek xai ofox nous github_models together fireworks; do
  printf "%-16s " "$p"; echo "reply OK" | timeout 25 python3 tools/swarm/api_consult.py --provider $p --max-tokens 5 - >/dev/null 2>&1 && echo LIVE || echo dead
done
```
Fastest free providers (good default workers): **cerebras, groq, gemini_api, nvidia_deepseek, fireworks, together**. Paid/high-quality: **deepseek, xai, nvidia_deepseek (DeepSeek v4 Pro), nous**.
If every CLI path is jammed (WSL-only grok, missing modules, 429 storms), fall back to the
**LiteLLM proxy** at `http://localhost:4000` (`free-mode-fast`/`paid-mode-fast`) — see `/PeerReviewSwarmOptions` #11. Confirm it: `curl -s http://localhost:4000/health/readiness`.

**Output of Phase 0:** an ordered `LIVE_WORKERS` list (peers + providers). You need ≥ (number of parallel action items) distinct live workers; reuse the fastest ones if short.

## Phase 1 — Parallel implementation (1 item → 1 file → 1 worker)

For each action item, write a **precise, self-contained implement-prompt** to `/tmp/ps_task_<id>.md`:
- The exact **target path** the file must live at.
- The **contract**: language, public functions/classes + signatures, inputs/outputs, error behavior, deps it may import (and which it may NOT), style (match surrounding code).
- Any **interfaces it must conform to** (paste the caller signature / schema).
- The hard instruction: **"Return ONLY the complete file contents in a single fenced code block, nothing else."**

### 1A — Provider-generated file (default, fastest)
Assign each item to a *distinct* live provider and run them concurrently (background):
```bash
# one per action item, distinct --provider, all backgrounded:
python3 tools/swarm/api_consult.py --provider cerebras       --prompt-file /tmp/ps_task_1.md --max-tokens 4000 > /tmp/ps_out_1.txt 2>&1 &
python3 tools/swarm/api_consult.py --provider nvidia_deepseek --prompt-file /tmp/ps_task_2.md --max-tokens 4000 > /tmp/ps_out_2.txt 2>&1 &
python3 tools/swarm/api_consult.py --provider groq           --prompt-file /tmp/ps_task_3.md --max-tokens 4000 > /tmp/ps_out_3.txt 2>&1 &
wait
```
Then for each output: extract the first fenced code block and write it to the target path
(read the target first if it exists — never blind-overwrite):
```python
import re, pathlib
raw = pathlib.Path("/tmp/ps_out_1.txt").read_text(errors="replace")
m = re.search(r"```[a-zA-Z0-9_+-]*\n(.*?)```", raw, re.S)
code = m.group(1) if m else raw            # fall back to raw if the model didn't fence
pathlib.Path("<target/path>").write_text(code)
```
(For >3 items, prefer `tools/swarm/swarm_run.py --engines <e1,e2,e3,...> --prompt-file ...`
when every item shares one prompt; use per-item `api_consult` calls when prompts differ — the
common case. You may also drive distinct items as parallel **Agent**/subagent calls, one per
item, each instructed to call one provider and write one file.)

### 1B — Cross-PC peer delegation (when you want another machine to build + place it)
```bash
python3 tools/adapters/cursor_claude_adapter.py --runtime claude --http-base http://192.168.2.32:8788 \
  send --topic task.request --to <peer_id> \
  --payload '{"action":"implement_file","target_path":"<path>","contract":"<...>","return":"write the file at target_path and reply task.result with sha+path","require_ack":true}'
# then poll for its reply:
python3 tools/adapters/freebuff_adapter.py --peer-id claude-opus-4-8-desktop --http-base http://192.168.2.32:8788 poll --limit 20
```
Use 1B only for peers showing recent life in Phase 0; otherwise the task sits unclaimed.

## Phase 2 — Validate (gate before anything downstream)

For each produced file, run the cheapest sufficient checks and **reassign on failure** (different
worker, max 2 retries) before escalating:
- **Syntax:** `python3 -m py_compile <f>` · `node --check <f>` · `bash -n <f>` · TS via `tsc --noEmit`.
- **Landed at the right path** and is non-empty / not truncated (model didn't cut off mid-file).
- **Contract:** the required functions/classes exist (`grep`), signatures match, imports resolve
  (`python3 -c "import ast,sys; ast.parse(open('<f>').read())"` then a dry import in a subprocess).
- **No secrets / no placeholders:** grep for key patterns + `TODO`/`pass  # stub`/`NotImplemented`.
- **No unrequested deps:** grep imports against the allowed set from the contract.

Only files that pass Phase 2 advance. Log which worker produced each pass/fail (some providers
truncate long files — prefer larger-context providers for big files).

## Phase 3 — Code-swarm review + testing plan

For each validated file, fan a review across 2–3 engines and demand a **structured testing plan**:
```bash
cat > /tmp/ps_review.md <<'EOF'
Review this implementation for correctness, contract-conformance, edge cases, and security.
Then output a JSON testing plan: {"verdict":"approve|changes|reject","concerns":[...],
"test_plan":[{"name":...,"kind":"unit|integration|property","setup":...,"assert":...,"edge":bool}]}.
--- FILE: <path> ---
<paste file>
--- CONTRACT ---
<paste contract>
EOF
python3 tools/swarm/swarm_run.py --prompt-file /tmp/ps_review.md --preset consensus-3 --json-strict \
  --out-dir swarm_runs/pswarm-review-$(date -u +%Y%m%dT%H%M%SZ)
```
Merge the engines' plans: keep test cases ≥2 engines proposed, plus any single-engine edge case
that looks real. High-stakes files (money/secrets/prod gates) → `/swarmv2-pr-review` instead.
**Run the provenance gate too** — `python3 tools/check_claim_provenance.py <file>` — so a worker
can't justify logic with an invented citation.

## Phase 4 — Swarm executes the testing plan

Distribute test-writing across providers (one provider per file, or per test-group), each asked to
emit a runnable `tests/test_<name>.py` (or `*.test.js`) implementing the Phase-3 plan, then run them:
```bash
python3 tools/swarm/api_consult.py --provider <p> --prompt-file /tmp/ps_testgen_<id>.md --max-tokens 4000 > /tmp/ps_test_<id>.txt 2>&1 &
wait
# extract → write test files → run:
python3 -m pytest tests/test_<name>.py -q    # or: node --test / npm test
```
Aggregate: a file is **DONE** only when Phase-2 validation + Phase-4 tests both pass. Failing tests
→ feed the failure back to a fresh provider for a fix (one repair loop), then re-test.

> `tools/swarm_v2/` already encodes this generate→test→review→revise→verify loop in
> `meta_swarm_orchestrator.py` (task-file driven via `_task_*.md`). For a single complex item you can
> hand it off there (`/swarmv2-coding`); ParallelSwarm is the multi-item, multi-provider fan-out layer on top.

## Parallelism & key-pool discipline (the "fast!" part)

- **One distinct provider per concurrent item** — never hammer a single provider's quota with N
  parallel calls; that's how you 429-storm. Spread across cerebras/groq/gemini_api/nvidia/fireworks/together.
- **Cap concurrency** at ~the number of *distinct fast providers* you confirmed live (Phase 0), typically 6–8.
- **Rotate on 429/timeout**: a worker that errors is dropped to the back of `LIVE_WORKERS`; reassign its item to the next live one.
- **Background everything** independent (`... &` + `wait`, or `run_in_background` Agents/Bash). Phases 1 and 4 should never run serially.
- **Free first, paid for hard items**: send the gnarly/large-context files to deepseek/xai/nvidia_deepseek; send boilerplate to cerebras/groq.

## Worker-selection cheat sheet

| Need | Prefer |
|------|--------|
| Fast boilerplate / many small files | cerebras, groq, gemini_api, fireworks, together |
| Hard logic / large file / careful code | nvidia_deepseek (DeepSeek v4 Pro), deepseek, xai, nous |
| Another machine builds + places it | cross-PC peer via gateway `task.request` (Phase 1B) |
| All CLIs jammed (env/429) | LiteLLM proxy `free-mode-fast` / `paid-mode-fast` |
| Review / consensus | `swarm_run.py --preset consensus-3`; high-stakes → `/swarmv2-pr-review` |

## Safety & failure handling

- **Read-before-write**: if the target path exists, read it; only overwrite if the task is "replace".
  New files only by default.
- **Sandbox risky output**: never run AI-generated code with side effects (network/db/fs writes)
  until reviewed; run tests in a tmp dir / dry-run mode first.
- **Idempotent**: re-running the skill re-probes liveness and only re-does items that aren't DONE.
- **Honest reporting**: report exactly which worker built each file, validation result, and test
  pass/fail. If a worker truncated or hallucinated, say so and show the reassignment.
- **Never commit a secret**; never paste `~/dbpasses.txt` contents into a prompt or log.
- **Shared working tree**: other agents edit this repo concurrently — commit new files via an
  isolated `git worktree` off `origin/main` (see prior session pattern) to avoid clobbering.

## Output artifacts

- `swarm_runs/pswarm-*/` — review JSONs + `_summary.json` (cost/tokens/transport).
- `/tmp/ps_task_*.md`, `/tmp/ps_out_*.txt` — per-item prompts + raw worker output (debug).
- A final table: `item | target_path | worker | validate | review_verdict | tests | status`.

## Worked example (3 items, parallel)

> "Implement 3 helpers: `alpha_engine/util/zscore.py`, `alpha_engine/util/winsorize.py`,
> `alpha_engine/util/ewma.py`, each a pure function with a docstring + type hints."

1. **Phase 0**: gateway shows 1 live peer; provider ping → cerebras/groq/nvidia_deepseek LIVE.
2. **Phase 1**: zscore→cerebras, winsorize→groq, ewma→nvidia_deepseek (3 backgrounded `api_consult`
   calls); extract each fenced block → write to the 3 target paths.
3. **Phase 2**: `py_compile` all 3; confirm each exposes the named function + type hints; no extra deps. groq's winsorize truncated → reassign to fireworks → passes.
4. **Phase 3**: `swarm_run --preset consensus-3` reviews all 3 → approve + a 4-case test plan each.
5. **Phase 4**: nvidia_deepseek writes `tests/test_util_math.py` from the merged plan → `pytest -q` → 12 passed.
6. **Report**: 3/3 DONE, with the worker + test result per file.

## Quick commands

```bash
# liveness (providers)
for p in cerebras groq gemini_api nvidia_deepseek deepseek xai ofox fireworks together; do printf "%-16s " $p; echo ok | timeout 25 python3 tools/swarm/api_consult.py --provider $p --max-tokens 5 - >/dev/null 2>&1 && echo LIVE || echo dead; done
# liveness (peers)
curl -s -m4 http://192.168.2.32:8788/health | python3 -m json.tool | grep -A2 peer_registry
# implement one file with a chosen provider
python3 tools/swarm/api_consult.py --provider nvidia_deepseek --prompt-file /tmp/ps_task.md --max-tokens 4000
# review consensus
python3 tools/swarm/swarm_run.py --prompt-file /tmp/ps_review.md --preset consensus-3 --json-strict --out-dir swarm_runs/pswarm-review-$(date -u +%Y%m%dT%H%M%SZ)
# provenance gate on a produced file
python3 tools/check_claim_provenance.py <produced_file>
```

## Related
`/PeerReviewSwarmOptions` (pick the review engine) · `/swarmv2-coding` (single-item generate→test→verify) ·
`/swarm-pr-review` · `/consult-multi` · `/litellm-proxy` · `/dropchat-multipc` (peer coordination).
