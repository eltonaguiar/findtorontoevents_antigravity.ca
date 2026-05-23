---
description: Run a multi-turn chain (priming → analysis → critique → final) declared in YAML.
argument-hint: <yaml-config>
---

Run:
```
python tools/swarm/swarm_followup.py --config $ARGUMENTS
```

After completion, run:
```
python tools/swarm/swarm_inspect.py --latest
```

Show both outputs. The user wants to see (a) how each turn went (chain summary) and (b) the response size + suspect flags per turn.

If `$ARGUMENTS` is empty, fail with usage:
```
/swarm followup tools/swarm/examples/forex_deep_dive.yaml
```
List `tools/swarm/examples/*.yaml` so they can pick.

After the chain summary + inspector output, surface the same NEXT STEPS reminder that `swarm_followup.py` prints (so it stays visible inline):

```
NEXT STEPS (see tools/swarm/POST_RUN_OPTIONS.md for details):
  1. Inspect chain        python tools/swarm/swarm_inspect.py <run_dir>
  2. Add another turn     python tools/swarm/worker_runner.py --engine <eng> --from-session <chain_session_id> --prompt-file <next.md> --persist-session
  3. Branch into red-team python tools/swarm/swarm_run.py --config <yaml> --red-team
  4. Cross-engine compare python tools/swarm/swarm_run.py --prompt-file <q.md> --preset consensus-3
  5. Switch persona       set persona: in YAML, or --persona <name> on a fan-out
  6. Resume specific dissent  swarm_run.py --from-session-by-engine eng=<sid>,...
```
