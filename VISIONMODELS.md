# Vision Model Test Results

**Test image:** `C:\Users\zerou\Desktop\image alt.png` (518x337px, 32bpp RGBA)
**Test date:** 2026-11-18

## Image Content (ground truth)

A simple text-based graphic with dark background and single line of centered white text:

> "Out of the six models listed, Qwen2-VL-7B-Instruct and Qwen3.5-9B are the only ones with vision capabilities."

## Server Topology

| Host | Port | Service | First Model | Accessible From |
|---|---|---|---|---|
| `127.0.0.1` (this machine) | 1234 | LM Studio / llama-server | `mistralai/ministral-3-3b` | Local only |
| `127.0.0.1` (this machine) | 4000 | Cloud proxy | `ULTRA_FREE_CLOUD_LARGE` | Local only |
| `192.168.2.52` (this machine) | 11434 | Ollama | `qwen2.5vl:7b` | LAN (192.168.2.x) |
| `192.168.2.52` (this machine) | 8003 | vLLM | `Qwen3-VL-2B-Instruct` | LAN (192.168.2.x) |
| `192.168.2.32` | — | — | No LLM servers responding | — |

## Working Vision Models

| Server | Model | Endpoint | Method | Result | LAN Access |
|---|---|---|---|---|---|
| `127.0.0.1:1234` | `mistralai/ministral-3-3b` | `/v1/chat/completions` | Multimodal content format (text + image_url parts) | Correct | Local only |
| `192.168.2.52:11434` (Ollama) | `qwen2.5vl:7b` | `/api/generate` | `prompt` + `images` (base64) | Correct | LAN |
| `192.168.2.52:11434` (Ollama) | `qwen3.5:4b` | `/api/generate` | `prompt` + `images` (base64) | Correct | LAN |
| `192.168.2.52:11434` (Ollama) | `qwen3.5:35b-a3b` | `/api/generate` | `prompt` + `images` (base64) | Correct | LAN |
| `192.168.2.52:8003` (vLLM) | `Qwen3-VL-2B-Instruct` | `/v1/chat/completions` | OpenAI multimodal format | Correct | LAN |

## Failed / Broken Vision Models

| Server | Model | Issue |
|---|---|---|
| `192.168.2.52:11434` (Ollama) | `moondream:latest` | Works but severe hallucination (described non-existent checkered tablecloth) |
| `192.168.2.52:11434` (Ollama) | `llama3.2-vision:11b` | Server error: `unknown model architecture: 'mllama'` |
| `192.168.2.52:11434` (Ollama) | `gemma3:12b` | Hung / timed out (likely OOM) |
| `127.0.0.1:4000` | `ULTRA_FREE_CLOUD_LARGE` | Cloud proxy — rejects image input |

## Key Notes

- **Ollama `/api/chat` ignores the `images` field** — must use `/api/generate` with `prompt` + `images` for vision models on Ollama
- **Ministral-3-3b on `127.0.0.1:1234`** requires the multimodal content array format (`{type: "text"}` + `{type: "image_url"}` parts), not the simple `images` field
- **Ministral-3-3b on `127.0.0.1:1234`** initially hallucinated when using the simple `images` field format — only works with proper multimodal content parts
- **vLLM on `192.168.2.52:8003`** uses standard OpenAI-compatible `/v1/chat/completions` with image_url data URIs
- **`127.0.0.1` services (ports 1234, 4000)** are bound to loopback — not accessible from other PCs on the LAN
- **`192.168.2.52` services (ports 11434, 8003)** are bound to the LAN interface — accessible from other PCs in `192.168.2.x`
- **`192.168.2.32`** has no LLM servers on any scanned port (1234, 4000, 11434, 8003, 8002)
- Port 8003 was initially not responding; confirmed active after remote reconfiguration to bind to `192.168.2.52:8003`
- LM Studio models on disk (`E:\Users\zerou\.lmstudio\models`) are not loaded into a running server