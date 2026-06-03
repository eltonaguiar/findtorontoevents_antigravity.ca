# Operator loops supervisor (2026-06-03)

## Problem

`pick_momentum_loop.sh` and `eagle2_operator_loop.sh` run correctly but Cursor/agent
background shells enforce **~10h max_runtime**, which kills long-running loops even
though the scripts themselves are infinite.

## Fix

`tools/operator_loops_supervisor.sh` — parent process that restarts each loop when
its child exits. Intended for **desktop tmux**, not a short agent harness.

## Usage

```bash
tmux new -s audit-ops
cd /home/eaguiar2015/findtorontoevents_antigravity.ca
tools/operator_loops_supervisor.sh
```

Heavy EAGLE (swarm each tick):

```bash
EAGLE_LOOP_FULL=1 EAGLE_INTERVAL_SEC=1200 tools/operator_loops_supervisor.sh
```

Logs: `reports/operator_loops_supervisor.log`, existing loop logs unchanged.

## Verified

```bash
bash -n tools/operator_loops_supervisor.sh
```