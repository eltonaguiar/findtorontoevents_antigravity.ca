# /swarm-hierarchical

Hierarchical swarm: Strategic -> Tactical -> Execution layers.

## Usage
```
/swarm-hierarchical <task> [--strategists 2] [--tacticians 3]
```

## Pipeline
1. **Strategic Layer** — Macro signal analysis (trend, regime)
2. **Tactical Layer** — Asset-specific predictions (conditioned on strategic)
3. **Execution Layer** — Validation + position sizing
4. **Risk Veto** — Risk controller can block any layer

## Parameters
- `--strategists N` — Strategic agents (default: 2)
- `--tacticians N` — Tactical agents (default: 3)

## Output
- Hierarchical signals per layer
- Final execution plan
- Risk assessment
