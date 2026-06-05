# 2026-06-05 - Local-only LiteLLM aliases (no cloud spillover)

## What was needed
The proxy needed model names on http://localhost:4000/v1 that are strictly local-only:
- local Ollama pool with local failover only
- local vLLM pool with local failover only
- mixed local pool that never touches cloud/paid providers

## What changed
Updated litellm_config.yaml:
- Added local-only fallback policy in router_settings.fallbacks:
  - local-only -> [local-vllm, local-vllm-alt, local-ollama]
  - local-vllm -> [local-vllm-alt, local-ollama]
  - local-vllm-alt -> [local-vllm, local-ollama]
  - local-ollama -> [local-only]
- Added local-only context fallback policy in router_settings.context_window_fallbacks.
- Added local model groups in model_list:
  - local-vllm (127.0.0.1:8000)
  - local-vllm-alt (127.0.0.1:8001)
  - local-ollama (127.0.0.1:11434)
  - local-only (mixed local chain)

Updated tools/vllmp_mode_status.py:
- Extended MODE GUIDE output to include local-only, local-vllm, local-vllm-alt, and local-ollama usage.

## Verification
Runtime checks performed:
1. Confirmed local aliases are exposed on proxy model listing:
   - local-vllm
   - local-vllm-alt
   - local-ollama
   - local-only
2. Sent chat requests through new aliases:
   - local-ollama -> success
   - local-vllm -> success via local fallback path when vLLM port is unavailable
   - local-only -> success
3. Confirmed local endpoint failure evidence in proxy log for 127.0.0.1:8001 and successful completion after fallback (no configured route from these aliases to cloud groups).

## Notes
- On this machine during verification, Ollama was live on :11434 and vLLM ports :8000/:8001 were not listening.
- If your vLLM model IDs differ, adjust the local-vllm model strings to match each vLLM server's /v1/models output.
