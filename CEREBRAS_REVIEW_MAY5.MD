# CEREBRAS REVIEW — MULTI-AGENT SWARM SYSTEMS (2026-05-05)

## Executive Summary

Reviewed both core swarm frameworks: the standalone `delegate_task`-based **multi-agent-swarm** skill and the **Ruflo-inspired orchestrator.py** system. Both are fully functional and complementary. The multi-agent-swarm skill remains the tool of choice for deep, 60-agent research sessions. The Ruflo orchestrator has been hardened and repaired and now serves as an effective lightweight, continuous, multi-tiered monitoring system with failover capability.

### Key Findings

1. **`multi-agent-swarm` Skill is Robust**: The existing pattern for large-scale swarm operations is stable and well-documented. The user's preference for single-model swarms (`tencent/hy3-preview:free`) remains valid due to its high success rate.
2. **Ruflo Orchestrator is Fixed**: The `.ruflo/orchestrator.py` has been successfully repaired and now supports multiple execution modes (direct, tmux, paid, hybrid, auto).
3. **YAML Agent Merge Logic Corrected**: A critical bug where YAML agent configs were silently overwritten by inline definitions was fixed, restoring full specification control via files.
4. **Model Passthrough Implemented**: The orchestrator now correctly passes the `--model` argument from the YAML config to the Hermes CLI, enabling true multi-model execution within swarms.
5. **Failover Mechanism Added**: A robust failover system with exponential backoff and error pattern recognition is implemented, allowing continuity during provider outages.
6. **Tiered Execution Support**: The orchestrator can target free (Hermes), paid (direct API), local (Ollama), hybrid, or auto tiers, making it highly adaptable to cost and availability constraints.
7. **`agents/` Directory Populated**: Five YAML agent definitions are present, each with correct model assignments and enhanced goals that prevent hallucination via `unable_to_verify`.

---

## Component Review: multi-agent-swarm Skill

### Current State

The `multi-agent-swarm` skill is the primary method for executing large-scale, one-off swarm analyses (e.g., 60+ agents across 10 rounds). It uses Hermes' `delegate_task` to spawn concurrent subagents, collecting diverse insights before synthesis.

### Key Features

- **High-Concurrency**: Supports up to 60+ agent runs in a single session.
- **Structured Output**: Enforces pure JSON output to facilitate programmatic parsing.
- **Workspace Pathing**: Explicitly sets workspace path in agent context to prevent incorrect working directories.
- **Security**: Includes automatic key sanitization in output, critical for compliance.
- **Cost-Effective**: The validated pattern of using a single, free-tier model (`tencent/hy3-preview:free`) has proven to be highly reliable and zero-cost.

### Deficiencies & Workarounds

- **Large File Handling**: Cannot delegate analysis of files >1GB. Workaround: Use `grep`, `sed`, or Python extraction in master agent, then delegate analysis of summaries.
- **Browser Task Failures**: Site crawling tasks often time out. Workaround: Perform direct parallel `curl` fetches followed by batch Python parsing.
- **Tooling**: Relies on internal Hermes tools (`delegate_task`, `execute_code`) rather than external scripts.

### Recommendation

Continue using `multi-agent-swarm` for deep-dive research, planning, and strategy generation. Its 3-cycle pattern (generate → peer review → apply) is ideal for complex tasks requiring consensus and cross-validation.

---

## Component Review: Ruflo Swarm Orchestrator (`orchestrator.py`)

### Current State

A Python script at `.ruflo/orchestrator.py` that runs automated swarms on demand or continuously. It was initially faulty, failing due to `HERMES_BIN` path issues, incorrect model argument passing, and YAML loading bugs. These have been resolved.

### Architecture

- **Execution Modes**: 
  - `--mode direct`: Uses `hermes chat -q` (quiet, non-interactive mode).
  - `--mode tmux`: Falls back to tmux sessions if direct mode is unavailable.
- **Model Tiers**:
  - `--tier free`: Uses Hermes with its configured models.
  - `--tier paid`: Bypasses Hermes and calls provider APIs directly via `api_consult.py`.
  - `--tier hybrid`: Tries paid first, then free.
  - `--tier local`: Uses local Ollama.
  - `--tier auto`: Uses local first, then free.
- **Agents**: Five types defined, also loadable from `.ruflo/agents/*.yaml`:
  - `audit_researcher` (audit)
  - `audit_quant` (audit)
  - `github_hygiene` (github)
  - `bug_hunter` (bugs)
  - `strategist` (strategy)
- **Swarms**: Logical groupings (audit, github, bugs, strategy, all, continuous) map to agent sets.

### Key Fixes Implemented

1. **`--model` Passthrough**: The orchestrator now correctly passes the model from the agent's YAML config via `--model` CLI argument to Hermes. This was the root cause of all agents defaulting to a single model.
2. **`HERMES_BIN` Resolution**: Full path resolution chain with fallback to `~/.local/bin/hermes` is in place.
3. **YAML Merge Logic**: Changed from `if k not in AGENTS` to an explicit field-merge (YAML overwrites inline, inline provides defaults), preventing key agent definitions from being silently dropped.
4. **Failover System**: `get_failover_model()` uses a chain of backup models and `should_failover()` checks stderr for common error patterns, enabling continuity.
5. **Context Hardening**: Agent goals explicitly command `Output JSON ONLY` and `Sanitize any API keys`, aligning with security policy.

### Agent YAML Review

Five YAML files in `.ruflo/agents/` are present and correct:

| Agent | Role | Model | Key Fix |
|-------|------|-------|--------|
| `audit_researcher.yaml` | researcher | `google/gemini-2.0-flash-exp:free` | Goal enforces `unable_to_verify` if data missing |
| `audit-quant.yaml` | coder | `deepseek/deepseek-chat:free` | Goal enforces `unable_to_verify` |
| `github-hygiene.yaml` | reviewer | `meta-llama/llama-3.3-70b-instruct:free` | Goal requires `gh CLI` and returns `unable_to_verify` if authentication fails |
| `bug-hunter.yaml` | security-architect | `meta-llama/llama-3.3-70b-instruct:free` | Goal requires actual file inspection, rejects hallucination |
| `strategist.yaml` | architect | `meta-llama/llama-3.3-70b-instruct:free` | Goal requires `unable_to_verify` for missing data |

### Usage

```bash
# Windows → WSL Bridge
wsl bash -c "cd /mnt/c/findtorontoevents_antigravity.ca && python3 .ruflo/orchestrator.py --swarm audit --no-verify"

# Run One-time Audit Swarm
python3 .ruflo/orchestrator.py --swarm audit

# Run All Swarms Once
python3 .ruflo/orchestrator.py --swarm all

# Continuous Monitoring (Default: 30-min cycles)
python3 .ruflo/orchestrator.py --continuous

# Continuous with 60-min cycles
python3 .ruflo/orchestrator.py --continuous --cycle-minutes 60

# List registered agents
python3 .ruflo/orchestrator.py --list-agents

# Check available paid API keys
python3 .ruflo/orchestrator.py --check-keys
```