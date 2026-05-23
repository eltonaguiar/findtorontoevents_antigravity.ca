# 2026-05-19 - Published localrun_eltonslaptop audit page

## What was needed
The requested audit page did not exist yet at the target URL path:
- /audit/localrun_eltonslaptop.html

The final publish step required:
1. Building a consolidated HTML report from local benchmark artifacts.
2. Uploading that HTML file to the FTP audit path.
3. Verifying the remote page was accessible and contained expected content.

## What was changed
Created new report page:
- audit_dashboard/localrun_eltonslaptop.html

The page includes:
- Round 1 baseline GPU/CPU benchmark table.
- Round 3/4 large-model reliability section.
- Explicit anomaly + recovery note for qwen2.5-coder:32b (Round 3 GPU 500, Round 4 recovery).
- MTP support status marked as inconclusive (as observed in session artifacts).
- Source artifact list used for compilation.

## Deployment
Uploaded the new file via FTPS to:
- findtorontoevents.ca/audit/localrun_eltonslaptop.html
- findtorontoevents.ca/audit_dashboard/localrun_eltonslaptop.html

## Verification
Verified live page response and key content via web fetch:
- Title present: "Local Ollama Run Audit: Elton's Laptop"
- Baseline table rows present (qwen2.5-coder:14b, llama3.1:8b, gemma:latest, etc.)
- Large-model reliability section present with Round 3 to Round 4 recovery callout.
- MTP support section present and marked inconclusive.

## Additional benchmark rounds completed

### Round 5 - Grok small/fast recommendations (completed)
Output file:
- swarm_runs/_outputs/hf_sim_2026-05-19/round5_grok_small_fast/round5_benchmark.csv

Key results (GPU warm tok/s):
- qwen3:4b -> 75.82 to 93.48 tok/s
- qwen3.5:9b -> 45.39 to 50.01 tok/s
- phi4-mini:latest -> 79.28 to 108.75 tok/s
- gemma3:4b -> 79.06 to 95.76 tok/s
- deepseek-r1:8b -> 56.28 to 56.37 tok/s

CPU baselines were captured for all Round 5 models and showed expected drops.

### Round 6 - High-ceiling sanity round (completed)
Output file:
- swarm_runs/_outputs/hf_sim_2026-05-19/round6_grok_high_ceiling/round5_benchmark.csv

Key outcomes:
- qwen3:14b -> failed (404 model/tag route)
- phi4:14b -> success (GPU 30.18 tok/s, CPU 6.36 tok/s)
- mistral-nemo:12b -> success (GPU 47.61 tok/s, CPU 6.81 tok/s)
- gpt-oss:120b-cloud -> failed in local metric parser path (cloud payload missing eval_duration field expected by benchmark script)
- qwen2.5:32b -> success (GPU 4.75 tok/s, CPU 2.57 tok/s)

## Re-evaluation exercise mapping (from latest audit guidance)
- Treat EQUITY as primary recovery lane while confidence inversion remains unresolved in mixed-asset scoring.
- Add strict automated gates (CPCV, DSR, PBO, MinTRL, WFE) before strategy promotion.
- Rebuild confidence score monotonicity and validate against forward WR slices.
- Use paper-pilot-first deployment and small sizing only after gate pass.
- Escalate failing strategy cohorts to frontier model critique (Claude/GLM class) for external validation.

## Under-the-radar model feasibility note
- Ring-1T / Ring-2.6-1T class models are promising but remain cloud-first for this hardware profile.
- Local laptop testing is still better focused on the validated small/fast set and selected 12b-32b tags.

## Metric glossary (plain English)
These labels come from the benchmark CSV files and the report table.

- GPU Tok/s: Tokens per second while the model runs with default GPU acceleration enabled.
- CPU Tok/s: Tokens per second while forcing CPU-only mode (no GPU acceleration).
- GPU WallSec: Total wall-clock time (real elapsed seconds) for the full GPU run request, from send to finish.
- CPU WallSec: Total wall-clock time (real elapsed seconds) for the full CPU-only run request.
- LoadSec: Time spent loading model/runtime state before token generation (cold starts are usually higher).
- Stage=pull: Download/import step for a model (no inference output yet).
- Stage=run: Inference/generation execution step.
- Round: Repeated trial number for the same model and mode. Round 1 is first timed run, Round 2 is repeat run.
- Status=ok: Command completed successfully.
- Status=failed: Command returned an error (example seen: HTTP 500 or network name-resolution failure).

## How to read one benchmark row quickly
- If GPU Tok/s is much higher than CPU Tok/s, GPU acceleration is materially helping throughput.
- If Round 2 WallSec is much lower than Round 1, that usually means warm-cache/warm-load effects.
- If WallSec is high but Tok/s is stable, much of the delay may be in LoadSec or startup overhead.
- Pull durations near 1 second on later rounds generally indicate cached artifacts, not a true cold download.

## Notes
No existing production index/template files were overwritten for this publish. Only the new standalone page was added and uploaded.
