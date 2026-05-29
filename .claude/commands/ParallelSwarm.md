# /ParallelSwarm — distributed parallel build → review → test swarm

Slash-command entry point for the **ParallelSwarm** capability. Turn **N action
items into N files in parallel**, each implemented by a *different* live worker
(free/paid API key pool + cross-PC peers), then code-review → test the results.

## What to do

Invoke the **`ParallelSwarm`** skill and follow its steps exactly
(`.claude/skills/ParallelSwarm/SKILL.md`). In short:

1. **Probe for live workers** (do NOT assume any are up):
   - Cross-PC peers: `curl -s -m4 http://192.168.2.32:8788/health | python3 -c "import sys,json;d=json.load(sys.stdin);print('peers:',list(d.get('peer_registry',{})))"`
   - API engines: `python3 tools/swarm/swarm_run.py --list-engines`; liveness-probe each with `tools/swarm/api_consult.py --provider <p> --max-tokens 5`.
2. **Phase 1 — parallel implement:** one action item → one self-contained prompt (`/tmp/ps_task_<id>.md`) → one distinct live worker, concurrently (`api_consult.py --provider <p> --prompt-file ... &`, or `swarm_run.py --engines e1,e2,e3 ...` for >3). Place each returned file.
3. **Phase 2 — validate:** syntax/compile/lint each placed file (py_compile, node check, etc.).
4. **Phase 3 — code-swarm review:** fan the diffs to reviewers; collect findings.
5. **Phase 4 — test plan + swarm-executed tests:** generate + run tests; report pass/fail.

## When to use
"/ParallelSwarm", "parallel swarm", "pswarm", "distribute these implementations",
"code swarm across AIs", "build these N files in parallel fast".

## Guardrails
- Probe liveness first — never assign to a dead provider/peer.
- One action item = one file = one worker (no overlapping writes).
- Validate + review + test before declaring any file done (no breadth-only "tests pass, no caller" — honor the repo Wire-Up Rule).
- Keys resolve via `tools/swarm/ENGINE_KEY_ENVS.py` (env first, then `~/dbpasses.txt`, gitignored).

Full reference + the dry-run log: `.claude/skills/ParallelSwarm/SKILL.md`, `.claude/skills/ParallelSwarm/DRYRUN.md`.
