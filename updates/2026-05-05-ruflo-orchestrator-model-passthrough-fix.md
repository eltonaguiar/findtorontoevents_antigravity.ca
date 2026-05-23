# Ruflo Orchestrator — `--model` Pass-Through Bug + Fix

**Agent:** claude-opus-4-7 (Claude Code)
**Timestamp:** 2026-05-05T07:00Z
**File patched:** `.ruflo/orchestrator.py`
**Functions:** `run_hermes_direct()` + `run_hermes_tmux()`

## Symptom

After PR #813 merged the local Hermes patcher, ruflo orchestrator runs started failing with:

```json
{
  "swarm": "github",
  "agent": "github_hygiene",
  "output": "API call failed after 3 retries: HTTP 404: No endpoints found for ."
}
```

The trailing `.` (period followed by nothing) is the giveaway. The model name field in the OpenRouter URL was empty/dot.

## Evidence (3 failed runs)

| File | Time | Agent | Error |
|---|---|---|---|
| `swarm_runs/ruflo-insights/bugs_bug_hunter_2026-05-05T05-51-31.594258+00-00.json` | 05:51Z | bug_hunter | HTTP 404 ... for . |
| `swarm_runs/ruflo-insights/github_github_hygiene_2026-05-05T06-06-07.493328+00-00.json` | 06:06Z | github_hygiene | HTTP 404 ... for . |
| `swarm_runs/ruflo-insights/github_github_hygiene_2026-05-05T06-48-10.255600+00-00.json` | 06:48Z | github_hygiene | HTTP 404 ... for . |

Note: the working `swarm_full_deployment_2026-05-05T05-46-49Z` run (which produced "78 strategies WR<0.55, 196 stale, 153 non-crypto starved") used a different code path that *did* pass the model — confirming the bug is in the `run_hermes_direct/tmux` paths only.

## Methodology

1. Inspected `swarm_runs/ruflo-insights/*.json` failure samples → all show empty model in URL
2. Read `.ruflo/orchestrator.py:260-280` (`run_hermes_direct`) and `:340-365` (`run_hermes_tmux`)
3. Found prompt builder at line 261-271 includes the literal text `f"Use model: {current_model}"` — this is decorative natural-language prompt content, not a CLI arg
4. The actual `cmd` list at line 273-280 was missing `--model` flag — Hermes CLI fell back to user's configured default
5. Confirmed via earlier sessions the user's Hermes default has been swapped multiple times (kimi-k2.5 → tencent/hy3-preview:free) — both unstable on free tier, hence sporadic 404s
6. Cross-referenced `.ruflo/agents/*.yaml` — every YAML correctly sets a `model:` field, so the orchestrator design intent IS multi-model; the implementation just wasn't wiring it through

## Root cause

`run_hermes_direct()` in `.ruflo/orchestrator.py` builds a prompt that *says* `"Use model: X"` (natural language hint to the LLM, ignored at HTTP-routing layer) but the spawned `hermes chat -q` subprocess gets no `--model` flag. So Hermes uses whatever default is in the user's config. When that default is broken/empty, you get the 404. When it works, you silently get *single-model behavior under multi-model labels* — exactly Bug 4 from the local-patcher MD, but in the orchestrator wrapper instead of Hermes core.

The `run_hermes_tmux()` fallback path had the identical bug (line 359).

## Fix

Add `--model {agent['model']}` to both code paths:

```python
# run_hermes_direct (cmd list):
cmd = [HERMES_BIN, "chat", "-q", prompt, "-Q",
       "--source", "tool", "--yolo", "--ignore-user-config",
       "--model", current_model]   # <-- new

# run_hermes_tmux (cmd string):
cmd = (f"{HERMES_BIN} chat -q '{safe_prompt}' -Q --source tool --yolo "
       f"--ignore-user-config --model '{agent['model']}'")  # <-- new
```

Both sites now honor the YAML's `model` field. With the failover-rotation logic already in `run_hermes_direct` (which reads `current_model` from the failover chain), this also means failover targets are real distinct models, not the same default repeated.

## Verification plan

Post-merge:
1. Run `python3 .ruflo/orchestrator.py --swarm github` from WSL
2. Check the resulting JSON in `swarm_runs/ruflo-insights/`
3. Pass criteria:
   - No `HTTP 404 ... for .` in output
   - The agent actually used the YAML-specified model (look for `mistral` patterns in github_hygiene output, `deepseek` patterns in audit_quant output, etc.)
4. Run `--swarm bugs` (was failing before)
5. Run all 4 swarms via `--continuous --cycle-minutes 1` (one full cycle)
6. Confirm at least 3/4 produce non-error output

## Related

- Bug 4 in `updates/2026-05-05-hermes-agent-bug-analysis-claude-opus-4-7.md` (Hermes core single-model swarm)
- Local patcher: `tools/patch_local_hermes.py` (covers the Hermes-core version of Bug 4)
- Orchestrator architecture: `.ruflo/orchestrator.py`
- Codebuff↔WSL bridge: `BUFFTOHERMES.MD`
