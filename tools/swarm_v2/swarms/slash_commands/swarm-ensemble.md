# /swarm-ensemble

Ensemble voting swarm for predictions and decisions.

## Usage
```
/swarm-ensemble <task> [--agents 5] [--confidence-threshold 0.8]
```

## Pipeline
1. **Register** N prediction agents with varied configs
2. **Predict** — All agents make prediction with confidence (parallel)
3. **Aggregate** — Weighted vote based on confidence:
   - Classification: weighted majority
   - Regression: weighted average + confidence interval
   - Probabilistic: weighted distribution blend
4. **Expand** — If confidence interval too wide, add agents

## Parameters
- `--agents N` — Number of voting agents (default: 5)
- `--confidence-threshold F` — Minimum acceptable confidence (default: 0.8)

## Output
- Aggregated prediction
- Confidence interval
- Individual votes with reasoning
- Dissenting opinions
