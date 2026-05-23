---
description: Fan a prompt to multiple engines. Auto-shows per-engine response sizes after.
argument-hint: <prompt-file> [engine,engine,...]
---

Parse `$ARGUMENTS`:
- First word: prompt file path. If missing, fail with usage.
- Remainder (optional): comma-separated engine list. Default: `deepseek,xai,kilo`.

Run:
```
python tools/swarm/swarm_run.py --prompt-file <prompt> --engines <engines> --max-parallel 4
```

After the run completes, immediately run:
```
python tools/swarm/swarm_inspect.py --latest
```

The inspector output is the user's signal:
- **HEALTHY** = ≥1KB response, parses fine.
- **SHORT** = <1KB, suspicious for substantive prompts.
- **TINY** = <200B, almost certainly garbage.
- **ZERO** = process produced no output.
- **CREDITS?** = response looks like an "out of credits" / quota / billing error.
- **AUTH?** = 401/403/unauthorized indicators.
- **PARSE_FAILED** = worker fell back to stub envelope.
- **TRUNCATED?** = response ends mid-token.

Show the table verbatim. Don't restate or summarize the engines — let the user read response sizes and suspect flags directly.

If any engine returns ZERO or TINY, suggest one re-run command:
```
python tools/swarm/worker_runner.py --engine <eng> --prompt-file <prompt> --out-file swarm_runs/_retry/<eng>.json
```

After the inspector table, surface the same NEXT STEPS reminder that `swarm_run.py` prints to stdout (so the user sees it inline even when the dispatcher's footer scrolled off):

```
NEXT STEPS (see tools/swarm/POST_RUN_OPTIONS.md for details):
  1. Inspect output       python tools/swarm/swarm_inspect.py <run_dir>
  2. Re-run with red-team python tools/swarm/swarm_run.py --config <yaml> --red-team
  3. Resume a dissenter   python tools/swarm/worker_runner.py --engine <eng> --from-session <sid> ...
  4. Multi-turn deep-dive python tools/swarm/swarm_followup.py --config tools/swarm/examples/<x>.yaml
  5. Switch persona       --persona <name>  (see agent_personas/INDEX.md)
  6. Stricter validation  --strictness strict
  7. Try different preset python tools/swarm/swarm_run.py --preset deep-strict ...
```
