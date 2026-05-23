# Enhanced Swarm Architecture

Multi-type agent swarm system with persistent memory, skill export, and 6 specialized swarm engines.

## Swarm Types

| Swarm | Purpose | Agents Used |
|---|---|---|
| **Coding** | Multi-agent code generation with mandatory testing | 3 code generators + 2 reviewers + 2 test writers |
| **PR Review** | Open PR impact analysis and risk assessment | Impact analyzer + code reviewer + risk controller |
| **GitHub Actions** | Failed/flaky/cancelled/stale job detection | 2 impact analyzers |
| **Research** | Deep research with epistemic triangulation | 3-5 researchers |
| **Ensemble** | Weighted voting for predictions/decisions | 3-7 tacticians |
| **Hierarchical** | Strategic -> Tactical -> Execution layers | 2 strategists + 3 tacticians + 1 risk controller |

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run a coding swarm
swarm coding task.md --agents 3 --strict

# Review a PR
swarm pr-review myorg/myrepo --pr 123

# Monitor GitHub Actions
swarm actions myorg/myrepo --since 30d

# Research a topic
swarm research "quantum computing applications in finance" --depth 5

# Search swarm memory
swarm memory search "python testing patterns" --tags coding

# Export a skill
swarm memory export-skill "testing patterns" pytest-skill
swarm skill export pytest-skill --format claude-md
```

## Architecture

```
swarms/
  core/          # Models, safety, messaging, registry, memory, orchestrator base
  memory/        # Vector store, skill store, hybrid search (BM25 + vector)
  workers/       # Code generator, reviewer, test writer, impact analyzer, researcher
  engines/       # 6 swarm orchestrators
  cli/           # Click-based CLI
  tests/         # 13 test files, 300+ tests
  slash_commands/# Claude slash commands
  skills/        # Exported skill output directory
```

## CLI Commands

```
swarm coding <task-file> [--agents N] [--models MODELS] [--strict]
swarm pr-review <repo> [--pr N] [--all-open]
swarm actions <repo> [--since Nd] [--notify]
swarm research <topic> [--depth N] [--route A|B|C|D]
swarm ensemble <task> [--agents N] [--confidence-threshold F]
swarm hierarchical <task> [--strategists N] [--tacticians N]
swarm memory search <query> [--tags ...]
swarm memory export-skill <query> <skill-name>
swarm skill list
swarm skill export <name> [--format claude-md|claude-json|openai]
```

## Swarm Memory & Skills

All swarm outputs are stored in a ChromaDB vector store with hybrid search (BM25 + vector similarity). Results can be exported as Claude-compatible skills:

- **Claude Skill** (markdown): YAML frontmatter + system prompt + examples
- **Claude Project** (json): System prompt + example conversations
- **OpenAI** (json): Compatible with GPTs

## Safety

- Read-only by default (configurable)
- Tool allowlisting
- AST-based static analysis blocks dangerous patterns
- Sandboxed test execution

## Testing

```bash
pytest swarms/tests/ -v --cov=swarms --cov-report=term-missing
```

## Repo

<https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/>
