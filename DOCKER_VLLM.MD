# Docker vLLM Runbook

This file documents the Docker-only vLLM setup validated in this workspace.

## Goal

Run an OpenAI-compatible local API for `Qwen/Qwen2.5-1.5B-Instruct` on port `8000` using Docker with GPU.

## One-Time Cleanup (optional, done in this session)

If switching from local `uv pip install vllm` to Docker-only mode, reclaim space:

```bash
uv cache clean
rm -rf .venv
pip cache purge
```

## Recommended Launch Command

Use detached mode (`-d`) and include the two stability flags used in this session:

```bash
docker run -d --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -p 8000:8000 \
  --ipc=host \
  --name vllm-qwen \
  vllm/vllm-openai:latest \
  Qwen/Qwen2.5-1.5B-Instruct \
  --gpu-memory-utilization 0.90 \
  --enforce-eager
```

Why these flags:

- `--gpu-memory-utilization 0.90`: avoids startup failure when free VRAM is slightly below vLLM default target.
- `--enforce-eager`: reduces startup complexity and avoids long compile/cudagraph warmup behavior.

## Verify Service

Wait for startup completion in logs:

```bash
docker logs -f vllm-qwen
```

Look for:

`Application startup complete.`

Then validate endpoints:

```bash
curl -sS -o /tmp/vllm_models.json -w 'models_http=%{http_code}\n' http://127.0.0.1:8000/v1/models
curl -sS -o /tmp/vllm_health.txt -w 'health_http=%{http_code}\n' http://127.0.0.1:8000/health
```

Expected: `models_http=200` and `health_http=200`.

## Minimal Test Request

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen2.5-1.5B-Instruct",
    "messages": [{"role": "user", "content": "Say hello in 5 words"}],
    "max_tokens": 32
  }'
```

## Container Operations

```bash
docker ps --filter name=vllm-qwen
docker stop vllm-qwen
docker start vllm-qwen
docker rm -f vllm-qwen
```

## Common Issues

1. **Engine fails at startup with GPU memory utilization error**

Example:

`Free memory on device cuda:0 ... is less than desired GPU memory utilization ...`

Fix: lower `--gpu-memory-utilization` from `0.92` to `0.90` (or lower).

2. **`curl` returns connection reset while container is up**

Usually means startup is still in progress. Keep watching logs until `Application startup complete.`

3. **Model downloads are slow or rate-limited**

Set `HF_TOKEN` if needed and keep the volume mount:

`-v ~/.cache/huggingface:/root/.cache/huggingface`

## Security Note

If any tokens were pasted into chat or local files, rotate/revoke them immediately.