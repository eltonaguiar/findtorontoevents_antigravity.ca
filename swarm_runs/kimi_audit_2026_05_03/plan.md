# Plan: Local AI Agent Swarm Orchestrator

## Objective
Build a local/hybrid agent swarm orchestrator that allows Claude Code (or a custom orchestrator) to leverage multiple CLI/TUI AI tools (KiloCode, OpenCode, Gemini CLI, Copilot, etc.) and local API keys for one-shot or interactive multi-agent workflows.

## Stage 1 — Research & Validation (Parallel)
Load: `deep-research-swarm` principles
- **Agent 1**: Research KiloCode CLI installation, model support, TUI capabilities, headless mode
- **Agent 2**: Research OpenCode CLI, `opencode run` non-interactive mode, provider config
- **Agent 3**: Research Gemini CLI, headless/JSON output, auth methods
- **Agent 4**: Research other tools: Freebuff, OpenClaude, Copilot CLI, Claude Code subagents
- **Agent 5**: Research local model endpoints (Ollama, LM Studio, vLLM) integration patterns

Output: `info.md` with validated tool capabilities, install commands, config patterns, and headless vs TUI status.

## Stage 2 — Architecture & SPEC Design
Load: `vibecoding-general-swarm`
- Design orchestrator architecture based on research findings
- Write `SPEC.md` covering:
  - Module structure (orchestrator, worker dispatch, config, adapters)
  - CLI adapter interface (common contract for each tool)
  - Configuration schema (API keys, model aliases, endpoints)
  - Execution modes (one-shot vs interactive/follow-up)
  - Swarm patterns (parallel dispatch, result aggregation, red-team verification)
  - Safety model (read-only workers, evidence contracts, env isolation)

## Stage 3 — Implementation (Parallel by Module)
- **Agent 1**: Core orchestrator + config loader + CLI framework (Python/Node)
- **Agent 2**: Tool adapters (KiloCode, OpenCode, Gemini CLI, local API adapters)
- **Agent 3**: Swarm engine (parallel worker dispatch, result aggregation, red-team verifier)
- **Agent 4**: Interactive/follow-up mode + session persistence + TUI integration helpers
- **Agent 5**: Example workflows, PR-review swarm template, safety tooling

## Stage 4 — Integration & Validation
- Merge all modules
- Integration tests
- End-to-end validation with at least 2 tool adapters
- Documentation and usage examples

## Stage 5 — Final Deliverable Packaging
- Package as installable CLI tool
- Write README with architecture, install, config, and usage
- Include example swarm configs for common patterns

## Output
- `/mnt/agents/output/agent-swarm-orchestrator/` — complete working project
- `README.md` — comprehensive documentation
- Example configs and workflow templates
