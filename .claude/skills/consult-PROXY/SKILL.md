---
name: consult-PROXY
description: Fan a prompt to N AIs through the local LiteLLM rotating proxy (http://localhost:4000) via tools/freellm.py. Three modes — team (CombineTeam, ask N AIs the same question), debate (DebateTeam, multi-round structured debate), file (FileTeam, divide files across AIs). Outputs .MD files. Use when the user says "/consult-PROXY", "proxy swarm", "ask the proxy team", "debate via proxy", or wants a multi-AI second opinion routed through the local proxy instead of per-provider CLIs.
---

# consult-PROXY

Multi-AI consultation that routes **through the local LiteLLM proxy on :4000** (the same proxy `/startvllmp` manages), instead of hitting each provider's API directly. The proxy auto-rotates across 15+ keyed upstreams on 429/401, so a fan-out keeps working even when individual providers rate-limit. Wraps `tools/freellm.py`.

## Why this over /consult-multi

- **One endpoint, auto-rotation.** Every call goes to a model *group* (`free-mode`, `paid-mode`, `hybrid-model`, …). If the upstream serving that group fails, the proxy transparently falls through to the next key. `/consult-multi` pins a single provider per call and 403s/429s are terminal.
- **Distinct named upstreams when you need clean filenames.** Direct routes (`claude-haiku-direct`, `deepseek-chat-direct`, `openrouter-ring-1t`, `nvidia-deepseek-v4-pro`, `cloudflare-llama`, `novita-deepseek-v4-pro-direct`) map a request to a known model, so per-model output files are deterministic.
- Built on `freellm.py`'s three team modes (CombineTeam / DebateTeam / FileTeam).

## Pre-flight (ALWAYS)

1. Proxy up? `curl -s -m3 http://localhost:4000/health/liveliness` → expect `"I'm alive!"`. If down, tell the user to run `/startvllmp` (do not auto-start unless asked).
2. List model groups if you need to pick routes: `curl -s -m5 http://localhost:4000/v1/models | python3 -c "import sys,json;print('\n'.join(m['id'] for m in json.load(sys.stdin)['data']))"`.

## Grounding rule (MANDATORY for /audit + pick-performance prompts)

Proxy models have **NO browser/tool access**. They will fabricate plausible-but-wrong WR/PF/Sharpe numbers if asked to "look at findtorontoevents.ca/audit" (see CLAUDE.md "DO NOT trust unsourced model claims"). Always: pull the data locally (the JSON under `audit_dashboard/data/`), embed it verbatim in the prompt, and instruct the model it was given the data and must NOT claim to fetch anything. Never let a proxy model claim to have fetched a URL.

## Modes

### team — CombineTeam (default)
Ask N AIs the same question; each reply lands in its own `.MD`.
```
python3 tools/freellm.py CombineTeam -q "<question>" -n 5 --reply-mode files \
  --results <out_dir> --max-tokens 2000 --timeout 180
```
Override which models answer with `--aliases free-mode,paid-mode,claude-haiku-direct,deepseek-chat-direct,openrouter-ring-1t` (comma-separated model-group / direct-route names). Default aliases: free-mode-fast, free-mode, free-mode-large, paid-mode, paid-mode-large.

### debate — DebateTeam
Multi-round structured debate; produces a `DebateTeam_<ts>/` folder with per-round `.MD` files + a summary.
```
python3 tools/freellm.py DebateTeam -q "<topic>" --rounds 3 -n 4 --reply-mode files --results <out_dir>
```
Resume an interrupted debate: `--resume <DebateTeam_folder>`.

### file — FileTeam
Divide a list of files across AIs in parallel, applying one instruction to each.
```
python3 tools/freellm.py FileTeam --files a.md b.md c.md --prompt "<instruction>" \
  --chunk 3 --model auto --results <out_dir>
```
`--model` ∈ {auto, free, paid, large}.

## Custom fan-out (when you need PROVIDER_MODEL filenames)

`freellm.py` aliases map to whatever the proxy serves and the served model can rotate. When the user wants one deterministic file per named model (e.g. `TOURNYFIND_<PROVIDER>_<MODEL>.MD`), drive the proxy directly with a small script that hits specific **direct routes** and reads `choices[0].message.content` (falling back to `reasoning_content` for reasoning models like ring-1t, which otherwise return empty `content`). POST to `http://localhost:4000/v1/chat/completions` with `{"model": "<direct-route>", "messages": [...], "max_tokens": N}`. Known-good direct routes: `claude-haiku-direct`, `deepseek-chat-direct`, `openrouter-ring-1t`. Flaky: `nvidia-deepseek-v4-pro` (429s), `novita-deepseek-v4-pro-direct` (403 key), `cloudflare-llama` (small context — returns empty on payloads >~5KB; don't use for large data dumps).

## Gotchas (learned 2026-05-28)

- **Reasoning models** (`openrouter-ring-1t`, nvidia deepseek) put text in `reasoning_content`, not `content`; with `max_tokens` too low they emit only chain-of-thought and get truncated mid-thought. Give them ≥3000 tokens.
- **cloudflare-llama** has a tiny context window — it returns HTTP 200 with empty `content` when the prompt is large. Verify non-empty output; swap to another route for big payloads.
- **Cloudflare Workers AI hosts no Anthropic/xAI models** via the native `/ai/run` path. `anthropic/claude-*` and `xai/grok-*` are real only on the **AI Gateway** `/ai/v1/*` endpoints and need a funded gateway or BYOK (402 otherwise). Don't add them as free proxy routes.
- Set `--timeout` generously (180–420s) for reasoning models; the default 90s times them out.
```
```
