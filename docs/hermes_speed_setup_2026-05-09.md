# Hermes Agent Rocket-Speed Setup — 2026-05-09

3-engine swarm consult (deepseek + xai + kilo @ `swarm_runs/second-opinion-20260510T003344Z/`) ranked 6 paths for max sustained tok/s on RTX 5070 12GB / Core Ultra 9 / 32GB / Win11 + Hermes Agent in WSL UbuntuRecovered.

## Consensus

**Path 2 (Ollama env vars) = best immediate quick-win. All 3 engines pick this in top-2.**

**Path 4 (vLLM) = best long-term upgrade (xai #1, deepseek/kilo #3).**

**Path 1 (smaller model) = backup if Path 2 insufficient (kilo + xai #2/#3).**

**Path 5 (Groq cloud) = cheap insurance fallback (deepseek explicit; xai/kilo silent).**

## Done now

### Phase 1 — Ollama env vars (Windows host)

```powershell
[Environment]::SetEnvironmentVariable("OLLAMA_FLASH_ATTENTION","1","User")
[Environment]::SetEnvironmentVariable("OLLAMA_KV_CACHE_TYPE","q4_0","User")
[Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL","1","User")
# restart Ollama
```

Effect: q4_0 KV cache shrinks 4× → fits 65k context in ~4GB instead of ~16GB; flash-attn cuts prefill latency.

### Phase 3 — Groq + phi3.5 fallback in `/root/.hermes/config.yaml`

```yaml
fallback_providers:
  - name: groq_cloud
    provider: openai
    base_url: https://api.groq.com/openai/v1
    api_key: PLACEHOLDER_GROQ_API_KEY     # ← FILL THIS
    default: llama-3.3-70b-versatile
    context_length: 32768
  - name: ollama_phi35
    provider: custom
    base_url: http://172.27.192.1:11434/v1
    api_key: ollama
    default: phi3.5:latest
    context_length: 16384
```

## User TODO

1. Get free Groq API key: https://console.groq.com/keys
2. Replace `PLACEHOLDER_GROQ_API_KEY` in `/root/.hermes/config.yaml`
3. Restart Hermes Agent (`hermes` from WSL)
4. Test — should see speed-up from Phase 1 immediately; cloud fallback kicks in if local times out

## If still too slow → Phase 2

Swap primary model to smaller fast variant:

```yaml
model:
  default: llama3.2:3b   # 200-300 tok/s, native tool_calls, 3B Q4 ~3GB VRAM
  # or phi3.5:latest     # 150-250 tok/s, 3.8B
  # or gemma2:2b         # 300-450 tok/s, but weak tool_calls
```

## Long-term (Phase 4) — vLLM in WSL

Per xai #1 pick: 2-4× speedup via PagedAttention + FP8 KV.

```bash
wsl
pip install vllm
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-3.1-8B-Instruct \
  --kv-cache-dtype fp8 \
  --port 8000
```

Then change Hermes config:
```yaml
model:
  base_url: http://127.0.0.1:8000/v1
```

Risk: WSL2 GPU passthrough config + driver compat tweaks. ~2-4 hour setup. Defer until Phase 1+3 prove insufficient.

## Speed math (why Phase 1 alone may be enough)

KV cache size at fp16 vs q4_0:

| ctx | model | fp16 KV | q4_0 KV | fits 12GB? |
|---|---|---|---|---|
| 32k | llama3.1-8B | ~6GB | ~1.5GB | ✅ |
| 65k | llama3.1-8B | ~12GB | ~3GB | ✅ |
| 32k | qwen2.5-14B | ~16GB | ~4GB | ✅ |
| 65k | qwen2.5-14B | ~32GB | ~8GB | ✅ (tight) |

After Phase 1, even 14B at 65k context fits in VRAM. If Hermes works with current llama3.1:latest after restart — done.

## Backup files

- `/root/.hermes/config.yaml.bak.groq.<ts>` (pre-Groq edit)
- `/root/.hermes/config.yaml.bak.aux.<ts>` (pre-aux fix)
- `/root/.hermes/config.yaml.bak.ctxlen.<ts>` (pre-context_length)
- `/root/.hermes/config.yaml.bak.<ts>` (original)

Roll back: `cp <backup> /root/.hermes/config.yaml`.

## Swarm artifacts

`swarm_runs/second-opinion-20260510T003344Z/{deepseek,xai,kilo}.json` + `_summary.json`.
