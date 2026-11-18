# Vision Model Test Results

**Test image:** `C:\Users\zerou\Desktop\image alt.png` (518x337px, 32bpp RGBA)
**Test date:** 2026-11-18

## Image Content (ground truth)

A simple text-based graphic with dark background and single line of centered white text:

> "Out of the six models listed, Qwen2-VL-7B-Instruct and Qwen3.5-9B are the only ones with vision capabilities."

## Server Topology

| Host | Port | Service | First Model |
|---|---|---|---|
| `localhost` / `127.0.0.1` | 1234 | LM Studio / llama-server | `mistralai/ministral-3-3b` |
| `localhost` / `127.0.0.1` | 4000 | Cloud proxy | `ULTRA_FREE_CLOUD_LARGE` |
| `192.168.2.52` | 11434 | Ollama | `qwen2.5vl:7b` |
| `192.168.2.52` | 8003 | vLLM | `Qwen3-VL-2B-Instruct` |
| `192.168.2.32` | — | — | No LLM servers responding |

## Working Vision Models

| Server | Model | Endpoint | Method | Result |
|---|---|---|---|---|
| localhost:1234 | `mistralai/ministral-3-3b` | `/v1/chat/completions` | Multimodal content format (text + image_url parts) | Correct |
| 192.168.2.52:11434 (Ollama) | `qwen2.5vl:7b` | `/api/generate` | `prompt` + `images` (base64) | Correct |
| 192.168.2.52:11434 (Ollama) | `qwen3.5:4b` | `/api/generate` | `prompt` + `images` (base64) | Correct |
| 192.168.2.52:11434 (Ollama) | `qwen3.5:35b-a3b` | `/api/generate` | `prompt` + `images` (base64) | Correct |
| 192.168.2.52:8003 (vLLM) | `Qwen3-VL-2B-Instruct` | `/v1/chat/completions` | OpenAI multimodal format | Correct |

## Failed / Broken Vision Models

| Server | Model | Issue |
|---|---|---|
| 192.168.2.52:11434 (Ollama) | `moondream:latest` | Works but severe hallucination (described non-existent checkered tablecloth) |
| 192.168.2.52:11434 (Ollama) | `llama3.2-vision:11b` | Server error: `unknown model architecture: 'mllama'` |
| 192.168.2.52:11434 (Ollama) | `gemma3:12b` | Hung / timed out (likely OOM) |
| localhost:4000 | `ULTRA_FREE_CLOUD_LARGE` | Cloud proxy — rejects image input |

## Key Notes

- **Ollama `/api/chat` ignores the `images` field** — must use `/api/generate` with `prompt` + `images` for vision models on Ollama
- **Ministral-3-3b on localhost:1234** requires the multimodal content array format (`{type: "text"}` + `{type: "image_url"}` parts), not the simple `images` field
- **Ministral-3-3b on localhost:1234** initially hallucinated when using the simple `images` field format — only works with proper multimodal content parts
- **vLLM on 192.168.2.52:8003** uses standard OpenAI-compatible `/v1/chat/completions` with image_url data URIs
- **192.168.2.32** has no LLM servers on any scanned port (1234, 4000, 11434, 8003)
- Port 8003 was initially not responding; confirmed active after remote reconfiguration to bind to `192.168.2.52:8003`
- LM Studio models on disk (`E:\Users\zerou\.lmstudio\models`) are not loaded into a running server