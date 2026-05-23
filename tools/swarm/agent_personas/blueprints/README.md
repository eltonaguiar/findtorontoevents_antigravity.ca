# Blueprints

Generated test blueprints for invented persona sets. Created by `tools/swarm/invent_personas.py` (see `../INVENT_PERSONAS_PROTOCOL.md`).

Each blueprint describes:

- The personas in the set (filenames + roles).
- The phases the orchestrator should run (plan → parallel specialists → cross-critique → coordinator synthesis).
- Cycle count + minimum engines per cycle.
- Verification required (Playwright trace / unit tests / manual / none).
- Ship-today threshold.
- Recommended `swarm_run.py` invocation.

Sidecar `<domain>_design.json` files preserve the raw JSON the design engine returned, for reproducibility and debugging.

These files are auto-generated. Hand-written blueprints belong in `../` next to the personas they reference.
