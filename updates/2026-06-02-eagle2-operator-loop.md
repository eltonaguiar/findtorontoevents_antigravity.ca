# EAGLE2 operator loop replaces AGENT_LOOP_TICK placeholder (2026-06-02)

## Problem

A background job ran `while true; sleep 1200; echo AGENT_LOOP_TICK_eagle2 …` for ~10h
until max_runtime killed it. It never executed `run_eagle_suite`, swarm synthesis, or
`pick_quality_pulse`.

## Fix

**`tools/eagle2_operator_loop.sh`** — real operator ticks:

| Env | Default | Effect |
|-----|---------|--------|
| `INTERVAL_SEC` | 3600 | Sleep between ticks |
| `EAGLE_LOOP_FULL` | 0 | `1` → include `verify_best_picks_swarm` + `eagle_swarm_synthesis` |
| `EAGLE_LOOP_GIT_PULL` | 0 | `1` → `git pull --ff-only origin main` before each tick |
| `EAGLE_LOOP_TEST_LITELLM` | 0 | `1` → probe `:4000` for ollama/hybrid models |
| `MAX_RUNS` | 0 | `1` = smoke test one tick |

Log: `reports/eagle2_operator_loop.log`

Companion: **`tools/pick_momentum_loop.sh`** (20m `pick_quality_pulse` only).

## Verified

```bash
MAX_RUNS=1 tools/eagle2_operator_loop.sh   # exit 0, log shows run_eagle_suite
bash -n tools/eagle2_operator_loop.sh
```

## Usage

```bash
# light hourly refresh (no LLM swarm)
tools/eagle2_operator_loop.sh

# full EAGLE2 cadence (tmux; heavy)
INTERVAL_SEC=1200 EAGLE_LOOP_FULL=1 EAGLE_LOOP_GIT_PULL=1 tools/eagle2_operator_loop.sh
```