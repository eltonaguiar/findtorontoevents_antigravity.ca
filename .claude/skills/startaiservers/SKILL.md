---
name: startaiservers
description: Bring up (or health-check / restart) the LOCAL AI stack on the GX10 — vLLM :8000, Ollama :11434, LiteLLM proxy :4000, Open WebUI :3000 — idempotently with the correct GX10 memory settings. Use when the user says "/startaiservers", "start our vLLM", "start local AI", "bring up the local stack", "local models are down", "vLLM not responding", "is local AI up", or before any /consult-local call that hangs. Aliases — startaiservers, start-ai, localai-up, bring-up-local-ai.
---

# /startaiservers — one-command local AI bring-up

Starts whichever of the local AI services are **not already healthy**. Safe to re-run
(idempotent) — it probes each port first and skips what's up. Encodes the GX10 memory
gotchas so you never starve Ollama or pick the wrong parser again.

## Run it

```bash
bash tools/start_ai_servers.sh            # start everything that's down, then print status
bash tools/start_ai_servers.sh status     # health table only (no changes)
bash tools/start_ai_servers.sh restart    # stop vLLM + proxy, start again
bash tools/start_ai_servers.sh stop       # stop vLLM + LiteLLM (Ollama left running)
bash tools/start_ai_servers.sh --gpu-util 0.45            # more KV cache for vLLM
bash tools/start_ai_servers.sh --no-proxy --no-tools      # GPU model only, no tool flags
bash tools/start_ai_servers.sh --model Qwen/Qwen3.5-35B-A3B
```

Output:

```
=== Local AI stack: start ===
  Ollama    :11434  already up
  vLLM      :8000   starting Qwen/Qwen2.5-14B-Instruct
            gpu-util=0.3 max-len=16384 tools=1 log=/tmp/vllm_serve.log
  vLLM      :8000   OK
  LiteLLM   :4000   starting rotating proxy
  LiteLLM   :4000   OK

LOCAL AI STACK — 2026-10-10 14:57:03
  vLLM       :8000   UP    Qwen/Qwen2.5-14B-Instruct
  Ollama     :11434  UP    23 models
  LiteLLM    :4000   UP
  OpenWebUI  :3000   UP
```

## Port map

| Port | Service | Notes |
|---|---|---|
| 8000 | vLLM (GPU, OpenAI-compatible) | `Qwen/Qwen2.5-14B-Instruct`, rapid second-opinion engine |
| 11434 | Ollama daemon | local models + `*-cloud` models; `/api/tags` to list |
| 4000 | LiteLLM rotating proxy | cloud key pool; probe `/health/readiness` (**not** `/health` — that one hangs) |
| 3000 | Open WebUI (docker `open-webui`) | opt-in via `--webui` |

## GX10 / GB10 hard-won rules (why the flags matter)

1. **`--gpu-memory-utilization 0.3`, never the 0.85 default.** 0.85 reserves ~103 GB of the
   121 GB unified memory → Ollama can't load anything >7B. 0.3 = ~36 GB, frees ~67 GB.
   (Verified: nvidia-smi 105,309 MiB → 37,243 MiB.)
2. **One vLLM instance at a time.** A second instance dies with
   `ValueError: free memory < desired GPU memory utilization`.
3. **Never restart vLLM with a 57 GB checkpoint** (e.g. Qwen3-Coder-30B-A3B) — OOM kills SSH.
4. **Tool-calling needs explicit flags**: without
   `--enable-auto-tool-choice --tool-call-parser hermes`, Qwen2/2.5 tool calls FAIL.
   The script adds these by default and auto-retries without them if a parser is unsupported.
5. **Scope the util to the model.** A 14B at util 0.3 fits fine; if you load a 35B-A3B instead
   (~22 GB weights) you may need `--gpu-util 0.45`.
6. **Don't `sleep`-poll.** Readiness waits use `curl --retry-connrefused` (bounded, no idle burn).
7. **Probe LiteLLM via `/health/readiness`, not `/health`.** `/health` performs live upstream
   checks and can hang for seconds (returns `http=000`) even while the proxy is serving fine —
   a false "DOWN". `/health/readiness` answers instantly with `{"status":"healthy"}`.

## Verify inference (smoke test)

```bash
# vLLM
curl -s http://localhost:8000/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"Qwen/Qwen2.5-14B-Instruct","messages":[{"role":"user","content":"Reply with exactly: VLLM OK"}],"max_tokens":16,"temperature":0}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['choices'][0]['message']['content'])"

# Ollama (native API)
curl -s http://localhost:11434/api/generate -d '{"model":"qwen2.5:7b-instruct-fp16","prompt":"hi","stream":false}'

# LiteLLM proxy health
curl -s http://localhost:4000/health/readiness
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| vLLM starts then dies | `tail /tmp/vllm_serve.log` — usually a bad `--tool-call-parser` or OOM; retry with `--no-tools --gpu-util 0.3` |
| `free memory < desired` | Another vLLM is live → `bash tools/start_ai_servers.sh stop` first |
| Ollama can't load >7B | vLLM is hogging memory → restart with `--gpu-util 0.3` |
| Local model returns empty content | Thinking models (r1, qwen3.x thinking) spend budget on reasoning — give `max_tokens`/`num_predict` ≥ 200 |
| Proxy up but model gives 4xx | Keys come from `~/dbpasses.txt`; check `/tmp/litellm_proxy.log` |
| Status says LiteLLM DOWN but calls work | You probed `/health` (slow/hangs) — use `/health/readiness` |
| SFTP/SSH drops during load | You were loading a >57 GB checkpoint — don't |

## Related

- `.claude/skills/consult-local/SKILL.md` — how to *use* the fleet for second opinions.
- `.claude/skills/litellm-proxy/SKILL.md` — proxy internals, provider chain, rotation.
- `/memories/repo/vllm-setup.md` + `/memories/repo/litellm-proxy-introspection.md` — raw verified facts.
- `tools/vllmp_mode_status.py` — per-group health + cooldown + 60m request counts.
