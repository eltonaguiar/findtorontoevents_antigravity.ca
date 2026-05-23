# Audit Plan: Claude-Code-driven Agent Swarm

## Stage 1 — Repository Exploration (Parallel)
- **Agent 1**: Browse repo structure, read tools/swarm/README.md, SPEC.md, METHODOLOGY.md, REVIEW_GUIDE.md
- **Agent 2**: Browse .claude/agents/ and .claude/commands/ definitions
- **Agent 3**: Browse swarm_runs/ outputs — CONSENSUS.md, PR_REVIEW_ABORTED.md, etc.
- **Agent 4**: Read core swarm code — swarm_run.py, worker_runner.py, config_loader.py
- **Agent 5**: Read PR capture pipeline, api_consult.py, inspector, session manager

## Stage 2 — Pain Point Verification (Parallel)
For each of 13 pain points:
- Locate the claimed fix in code
- Verify fix logic
- Assess adequacy
- Output verdict per requested schema

## Stage 3 — Synthesis
- Top 5 missed issues
- Top 3 architectural choices to undo
- One Kimi feature recommendation
- One false-confidence claim
- Compare _pr_capture.py vs our ai-swarm approach

## Stage 4 — Final JSON Output
- Compile all findings into requested JSON format
