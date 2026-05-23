# /consult-ofox — OFOX AI Consultation

Consult **OFOX AI** (`z-ai/glm-4.7-flash:free`) on any quantitative, strategy, or code question. OFOX is an OpenAI-compatible gateway providing free access to ZhipuAI GLM-4.7-Flash.

## Prerequisites

- `OFOX_AI_KEY` set in Windows environment (already added by user 2026-05-16).
- Free model: `z-ai/glm-4.7-flash:free` (default; override via `OFOX_MODEL` env var).
- API endpoint: `https://api.ofox.ai/v1/chat/completions`

## Usage

```
/consult-ofox <question or prompt text>
/consult-ofox --file tools/swarm/prompts/my_prompt.md
```

## How to invoke

### Quick one-liner

```bash
python tools/swarm/api_consult.py --provider ofox --prompt-file <path>
```

Or pipe stdin:

```bash
echo "What is the best Kelly fraction for PF=1.56, WR=52%?" | python tools/swarm/api_consult.py --provider ofox -
```

### Via swarm engine (for multi-engine consensus)

```bash
python tools/swarm/swarm_run.py --prompt-file <path> --engines ofox,deepseek
```

The `ofox` engine runs via `api_consult.py` just like `deepseek`, `groq`, etc.

## When to use

- **Fast free consultation**: GLM-4.7-Flash is a capable, fast model ideal for secondary opinions on gate logic, quick code review, or synthesis tasks
- **Multi-engine swarms when other keys are unavailable**: `--engines ofox,deepseek` gives two independent opinions at zero cost
- **Prompt-heavy tasks** where token cost matters (free tier)

## Model capabilities (GLM-4.7-Flash)

- 128K context window
- Strong on structured reasoning, JSON output, Chinese/English bilingual
- Suitable for: code review, quant research, data analysis prompts
- Not ideal for: real-time web search, image analysis

## Key env var

| Var | Value |
|-----|-------|
| `OFOX_AI_KEY` | Set in Windows env via `setx OFOX_AI_KEY "..."` |
| `OFOX_MODEL` | Optional override (default: `z-ai/glm-4.7-flash:free`) |
| `OFOX_TEMPERATURE` | Optional (default: 0.2) |
| `OFOX_MAX_TOKENS` | Optional (default: 4000) |

## Troubleshooting

| Error | Fix |
|-------|-----|
| `401 Unauthorized` | Check `OFOX_AI_KEY` is set and correct |
| `404` on `/v1/chat/completions` | Base URL may differ — check OFOX docs for exact endpoint |
| Empty response | Try `OFOX_MODEL=z-ai/glm-4.7-flash:free` explicitly |
| SSL error | Update `certifi`: `pip install --upgrade certifi` |

## Notes

- Added 2026-05-16 alongside OFOX_AI_KEY Windows env var registration
- If the base URL `https://api.ofox.ai/v1/chat/completions` returns 404, update `tools/swarm/api_consult.py::PROVIDERS["ofox"]["url"]` with the correct endpoint from OFOX documentation
- GLM-4.7 is from ZhipuAI; the `z-ai/` prefix is OFOX's internal routing key for this model
