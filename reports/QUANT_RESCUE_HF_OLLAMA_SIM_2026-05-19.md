# Quant Rescue HF/Ollama Simulation - 2026-05-19

## Scope
Ran local Ollama model simulations against:
- [swarm_runs/_prompts/quant_rescue_deepdive_2026-05-19.md](swarm_runs/_prompts/quant_rescue_deepdive_2026-05-19.md)

Goal: produce additional model-jury ideas for salvageability, highest-leverage change, symbol-universe impact, best 3-month bet, and week-1 execution steps.

## Models Attempted
- `llama3.1:8b` -> success
- `llama3.2:3b` -> success
- `gpt-oss:120b-cloud` -> success
- `qwen2.5-coder:14b` -> failed (CUDA OOM)
- `gemma:latest` -> failed (CUDA OOM)
- HF pull attempt `hf.co/bartowski/Phi-3.5-mini-instruct-GGUF:Q4_K_M` -> failed (disk full during download)

Raw outputs saved in:
- [swarm_runs/_outputs/hf_sim_2026-05-19/llama3.1_8b.txt](swarm_runs/_outputs/hf_sim_2026-05-19/llama3.1_8b.txt)
- [swarm_runs/_outputs/hf_sim_2026-05-19/llama3.2_3b.txt](swarm_runs/_outputs/hf_sim_2026-05-19/llama3.2_3b.txt)
- [swarm_runs/_outputs/hf_sim_2026-05-19/gpt-oss_120b-cloud.txt](swarm_runs/_outputs/hf_sim_2026-05-19/gpt-oss_120b-cloud.txt)

## What the models said

### Q1: Salvageable vs paper-only
- 2/3 outputs lean to "not salvageable in current form" for live money.
- 1/3 says salvageable, but only with major architecture and data-resolution changes.

### Q2: One highest-leverage change
No full consensus, but the options converged to two themes:
1. Methodology pivot to meta-labeling.
2. Scope+data pivot to crypto-only with higher-frequency, depth-aware data.

### Q3: Symbol-universe widening
- All usable outputs agree this is not the main lever.
- Widening now likely increases noise before it adds edge.

### Q4: Best 3-month bet
- Most frequent answer: meta-labeling (about 15-30% success odds in these runs).
- Stronger mechanistic answer: high-frequency crypto with depth/order-flow features, then conditional meta-labeling if and only if primary lift is stable.

### Q5: Week-1 actions
Common recommendations:
- Data integrity audit first.
- Workflow simplification (reduce noisy emissions).
- Add intraday/depth data path before any serious new hypothesis.

## Practical simulation caveats
- OOM failures reduced model diversity.
- The successful local models are useful for brainstorming but not strong enough alone for capital decisions.
- The cloud-backed run gave the most concrete execution steps but still needs harness verification.

## Best combined idea (actionable)
1. Keep live trading paper-only now.
2. Run a 2-4 week falsification sprint, not a 3-month build commitment.
3. Focus one bet only: crypto intraday/depth-aware primary signal with strict walk-forward sign-stability checks.
4. Enable meta-labeling only if the primary signal first shows stable directional lift net of 30 bps.
5. Keep symbol-universe widening as a secondary power test, not a primary edge hypothesis.

## Immediate next command-level work
1. Free disk space enough to pull at least one HF GGUF model.
2. Re-run with CPU fallback for failed local models to improve jury breadth.
3. Standardize output format to JSON (Q1-Q5 + probability + failure modes) and auto-score model agreement.
4. Feed resulting candidate into the existing admissibility harness before any deployment decision.
