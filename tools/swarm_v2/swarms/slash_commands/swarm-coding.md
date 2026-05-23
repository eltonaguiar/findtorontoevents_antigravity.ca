# /swarm-coding

Multi-agent coding swarm. Generates code with mandatory testing via parallel agents.

## Usage
```
/swarm-coding <task-description or task-file> [--agents 3] [--strict]
```

## Pipeline
1. **Decompose** — Split task into file-level sub-tasks
2. **Generate** — Fan out to N code_generator agents (parallel)
3. **Test** — Each agent writes code + mandatory tests
4. **Review** — Code reviewers check quality, security, style
5. **Revise** — Feedback loop (max 3 iterations)
6. **Verify** — Run tests; failures trigger auto-revision
7. **Output** — All passing artifacts collected

## Parameters
- `--agents N` — Number of parallel generators (default: 3)
- `--strict` — Enforce 90%+ test coverage (default: 80%)
- `--models` — Comma-separated model list (default: gpt-4o,claude-sonnet)

## Example
```
/swarm-coding "Implement a Redis-backed rate limiter with sliding window algorithm. Python. Include unit tests."
```

## Output
- Code artifacts with source + tests
- Test results (pass/fail + coverage)
- Review comments
- Stored in swarm memory for future search
