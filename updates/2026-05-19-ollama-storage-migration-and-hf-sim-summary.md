# 2026-05-19 Session Summary: Ollama Storage Migration, Drive Benchmarks, and HF Simulation

## User goal
- Free disk space on C
- Move model storage off C to external drives
- Validate whether external drive speed hurts local model runs
- Resume Hugging Face style local simulation workflow on the new drive
- Produce documented summary with prompts, models, outputs, and framework

## What was done and why

### 1) Immediate disk relief on C
Why:
- C had low free space and HF model pull failed earlier due to disk limits.

Actions:
- Removed large local Ollama models:
  - qwen2.5-coder:14b
  - gemma:latest
  - llama3.1:8b
- Removed partial failed Ollama blob download.

Result:
- C free space improved from about 14.34 GB to about 32.21 GB (then later higher after additional changes).

### 2) Verified and leveraged external drives
Why:
- User attached D and later E to offload model storage and reduce pressure on C.

Actions:
- Checked drive presence, free capacity, and write access.
- D was writable with large headroom.
- E was writable with large headroom.

### 3) Migrated Ollama model store to external drive
Why:
- Keep model downloads and blobs off C permanently.

Actions:
- Set persistent user environment variable OLLAMA_MODELS to external path.
- Migrated models to external path and validated with ollama list and live generate API call.
- Final state moved to E:
  - User OLLAMA_MODELS = E:\ollama\models
  - D model path no longer required

### 4) Benchmarked external-drive impact
Why:
- User asked whether USB external speed would inhibit runs.

Framework for benchmarks:
- Practical throughput benchmark by copying a real model blob (~1.93 GB)
- Real inference benchmark via Ollama REST API generate endpoint

Observed performance:
- D transfer benchmark (earlier):
  - D -> C: ~367.79 MB/s
  - C -> D: ~277.86 MB/s
- E transfer benchmark:
  - E -> C: ~784.85 MB/s
  - C -> E: ~604.03 MB/s
- E-backed inference benchmark with llama3.2:3b:
  - Run 1 (cold-ish): Wall ~2.539s, Load ~2.254s, ~237.58 tok/s
  - Run 2 (warm): Wall ~0.418s, Load ~0.116s, ~237.27 tok/s
  - Run 3 (warm): Wall ~0.370s, Load ~0.104s, ~237.68 tok/s

Conclusion:
- External E drive is not inhibiting normal local inference workflow.
- Cold load pays a small one-time load cost; warm runs are compute-dominant.

## HF/Ollama simulation work completed

### Framework used
- Runtime/orchestrator: Ollama local runtime
- Model-jury method: same constrained prompt shape across models
- Output capture: text outputs written under swarm_runs/_outputs/hf_sim_2026-05-19
- Inference method:
  - ollama run for prompt responses
  - REST generate endpoint for repeatable runtime metrics

### Prompt used (simulation guard + task)
The run used this guard instruction before the deep-dive prompt:
- You are one model in a quantitative model-jury simulation.
- Answer only with sections Q1..Q5 and FINAL.
- Be specific to architecture.
- Pick exactly one highest-leverage change in Q2.
- In Q4 pick exactly one 3-month bet (or none) and give explicit probability.
- Mention cron and retail taker execution constraints.
- Do not suggest forbidden killed families.
- Keep response length bounded.

Deep-dive task source file:
- swarm_runs/_prompts/quant_rescue_deepdive_2026-05-19.md

### Models tested in session
Tested/attempted:
- llama3.1:8b (local)
- llama3.2:3b (local)
- gemma:latest (attempted; earlier OOM before cleanup)
- qwen2.5-coder:14b (attempted; earlier OOM before cleanup)
- gpt-oss:120b-cloud (via Ollama listing path)
- hf.co/bartowski/Phi-3.5-mini-instruct-GGUF:Q4_K_M (pulled and run successfully on E)

Current active local models at end:
- hf.co/bartowski/Phi-3.5-mini-instruct-GGUF:Q4_K_M
- llama3.2:3b

## Output locations

Primary written summaries:
- reports/QUANT_RESCUE_HF_OLLAMA_SIM_2026-05-19.md
- updates/2026-05-19-ollama-storage-migration-and-hf-sim-summary.md

Raw simulation outputs:
- swarm_runs/_outputs/hf_sim_2026-05-19/llama3.1_8b.txt
- swarm_runs/_outputs/hf_sim_2026-05-19/llama3.2_3b.txt
- swarm_runs/_outputs/hf_sim_2026-05-19/gpt-oss_120b-cloud.txt
- swarm_runs/_outputs/hf_sim_2026-05-19/hf_phi3.5_mini_q4km_e_drive.txt

Decoded/cleaned helper outputs created during analysis:
- swarm_runs/_outputs/hf_sim_2026-05-19/llama3.1_8b_clean.txt
- swarm_runs/_outputs/hf_sim_2026-05-19/llama3.2_3b_clean.txt
- swarm_runs/_outputs/hf_sim_2026-05-19/gpt-oss_120b-cloud_clean.txt

## Final operational state
- Model storage path is externalized to E.
- D is no longer required for current model storage.
- E has strong free capacity and tested throughput.
- HF GGUF pull and run workflow is functioning on E.

## Suggested next run pattern
- Keep OLLAMA_MODELS on E for all pulls/runs.
- Use a fixed JSON schema output for model-jury comparisons.
- Run 3-5 repeated calls per model and score agreement + constraint compliance.
- Gate any strategy ideas through existing admissibility harness before deployment decisions.
