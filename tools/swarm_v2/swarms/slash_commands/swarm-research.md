# /swarm-research

Multi-agent deep research with epistemic triangulation.

## Usage
```
/swarm-research <topic> [--depth 3-5] [--route A|B|C|D]
```

## Pipeline
1. **Decompose** — Split topic into sub-questions/dimensions
2. **Parallel Research** — 3-5 researcher agents investigate (parallel)
3. **Cross-Verify** — Researchers check each other's findings
4. **Resolve** — Contradictions trigger additional verification
5. **Synthesize** — Aggregate into structured result with confidence

## Parameters
- `--depth N` — Number of researchers (3-5)
- `--route` — Research route: A=wide, B=focused, C=file-only, D=file-augmented

## Output
- Research findings with confidence scores
- Consensus claims (high confidence)
- Disputed claims (conflicting evidence)
- Knowledge gaps
- Source list
- Stored in swarm memory
