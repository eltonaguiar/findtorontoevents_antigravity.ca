# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

---

## Local AI fleet (verified 2026-11-22)

### Hosts and engines

| Host | Engine | Port | Models | Notes |
|---|---|---|---|---|
| 192.168.2.32 (Windows) | LM Studio | 1234 | 11 | `gpt-oss-20b` loaded; also `mistralai/ministral-3-3b`, `deepseek-r1-distill-qwen-32b-*` |
| 192.168.2.32 (Windows) | Ollama | 11434 | 71 | `llama3.1:8b`, `usb-mistral-small-24b`, plus cloud tags |
| 192.168.2.52 (Linux, this box) | Ollama | 11434 | 26 | `gemma3:12b`, `gemma4:31b-cloud`, `minimax-m3:cloud`, `deepseek-r1:32b` |
| 192.168.2.52 (Linux) | vLLM | 8002 | 1 | `nvidia/diffusiongemma-26B-A4B-it-NVFP4` — **rejects the `temperature` field (HTTP 400)** |
| 192.168.2.52 (Linux) | vLLM | 8000 | 1 | container `vllm-qwen36`: `Qwen3.6-35B-A3B-NVFP4` (35B MoE / 3B active, NVFP4, 16k ctx), **thinking on by default** — see below |
| 192.168.2.52 (Linux) | vLLM | 8001 / 8003 | 0–1 | 8001 not running; 8003 = container `vllm-qwen3-vl` (Qwen3-VL-2B, 2k ctx) |

Kilo's global config (`~/.config/kilo/kilo.jsonc`) lists 34 providers. Read it for
provider/model names only — it and `~/dbpasses.txt` hold credentials. Never print
key values; key *names* are fine.

### What actually answers

- Cloud via **Ollama cloud tags** (no API key needed): `gemma4:31b-cloud` (best ideas,
  ~5 s), `gpt-oss:120b-cloud` (~6 s).
- Local: `llama3.1:8b`, `gemma3:12b`, `llama3.1:8b`.
- `glm-5.3-flash:cloud`, `minimax-m3:cloud`, LM Studio `gpt-oss-20b`: return
  **HTTP 200 with empty `content`** — reasoning models burn the whole budget before
  emitting. An empty reply is *not* assent; record it as no reply.

### Traps that cost real time

1. **Reasoning-model budget.** Below ~2,500 tokens these return `content: ""` with
   `finish_reason: length`. Budget 4,000; still expect occasional blanks.
2. **Cold 20–32 GB models** can exceed a 420 s timeout and then answer in 2 s once
   warm. `GET /api/ps` shows what is loaded.
3. **Model names differ per host** — `gemma3:12b` 404s on Windows, `qwen2.5:14b` too.
   Always address `engine:model@host:port`.
4. **`consult_multi.py --fanout`** presets are `diverse5`, `fast4`, `reasoning4`,
   `all` — not a number. As of 2026-11-22 all five *diverse5* providers failed
   (410 retired model, 404 ×2, 401), even though `~/dbpasses.txt` has keys for them:
   the keys are present but stale.
5. **Background jobs do not survive a tool-cleanup cycle.** A `nohup … &` inside a
   SYNC command is killed; long fan-outs must run as BACKGROUND or inside one waiting
   SYNC command.

### Port 8000 (the local reasoning model)

```
docker run -d --name vllm-qwen36 --restart unless-stopped --gpus all --ipc=host \
  -p 127.0.0.1:8000:8000 \
  -v /home/eaguiar2015/.cache/huggingface:/root/.cache/huggingface \
  -e HF_HOME=/root/.cache/huggingface vllm/vllm-openai:latest \
  --model nvidia/Qwen3.6-35B-A3B-NVFP4 \
  --served-model-name Qwen3.6-35B-A3B-NVFP4 \
  --max-model-len 16384 --max-num-seqs 4 \
  --gpu-memory-utilization 0.25 --enable-prefix-caching --reasoning-parser qwen3
```

- **Cold start is ~5 min** (weights load from NVMe). `--gpu-memory-utilization 0.25` is
  deliberate: diffusiongemma already reserves 0.35 and Qwen3-VL 0.08 of the GB10's
  unified memory, and swap was already full.
- **Thinking mode is on by default.** With `max_tokens` below ~1,500 it returns
  `content: ""` and puts everything in `reasoning_content` — `completion_tokens_details.
  reasoning_tokens` equals the whole budget. Either budget 1,500–2,000 tokens, or send
  `chat_template_kwargs: {"enable_thinking": false}` for a 38-token answer in 0.75 s.
- Measured on this host: **~80 tok/s** while thinking (1,541 reasoning tokens in 20 s),
  ~50 tok/s without (38 tokens in 0.75 s including HTTP overhead).
- Verify it is alive: `curl -s localhost:8000/v1/models`, then read `docker logs vllm-qwen36`.

### Tools

- `tools/fleet_consult.py` — discovers LM Studio `/v1/models` + Ollama `/api/tags`
  across hosts, routes per model, fans out in parallel, writes each reply as it lands.
  Modes: `--list`, `--model engine:model@host:port`, `--fanout N`,
  `--check-claims` (verifies `path:line` + verbatim quote → `VERIFIED` /
  `VERIFIED_ELSEWHERE` / `UNVERIFIED`), `--claim-protocol`, `--self-check`.
- `tools/registry_metric_audit.py` — mechanical registry audit (R1/R3/R5/I1),
  `--self-check`, validated against the pre-fix registry.
- `tools/consult_multi.py` — 14 provider presets; currently unreliable (see trap 4).
