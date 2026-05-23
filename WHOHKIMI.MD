# Kimi Swarm & Ruflo Changes — 2026-05-05

## Files Changed
| File | PR | What Changed |
|------|-----|-------------|
| `.ruflo/orchestrator.py` | #817, #819, #820 | `--model` passthrough, `threading.Lock()`, auto `REPO_ROOT`, `--tier`, `--check-keys`, `--swarm all`, new free model assignments |
| `tools/swarm/api_consult.py` | #818, #820 | Cerebras SDK→HTTP fallback, Groq/HuggingFace/Ollama local providers |
| `tools/swarm/worker_runner.py` | #818, #820 | Empty-envelope retry for CLI engines, added `groq`/`huggingface`/`ollama_local` to `API_ENGINES` |
| `tools/swarm/swarm_run.py` | #818, #820 | Pre-flight API key skip, added new engines to `ALL_ENGINES` and presets |
| `tools/swarm/safety.py` | #820 | `ENGINE_REQUIRED_KEYS` for Groq, HuggingFace, Ollama local |
| `tools/swarm/config_loader.py` | #820 | `ENGINE_KEY_ENVS` for Groq, HuggingFace |
| `.claude/commands/swarm-ruflo.md` | #819, #820 | Updated docs to match new flags and providers |
| `.claude/commands/swarm-ruflo-help.md` | #819 | Updated help text |

## Why
- OpenRouter free-tier 404/rate-limit failures on old models
- Paid engines burning slots with missing API keys
- Cerebras SDK crashing when pip package absent
- CLI engines returning 0-byte envelopes
- Docs lied: `--tier`, `--check-keys`, `--swarm all` didn't exist in code
- Ruflo race condition: parallel agents overwriting shared `results` list

## Expected Benefits
- **Free tier**: Uses stable models (`llama-3.3-70b`, `gemini-2.0-flash-exp`, `deepseek-v3.1`) + Groq/HuggingFace/Ollama fallbacks
- **Resilience**: Skips keyless engines pre-flight, retries empty CLI output, SDK→HTTP fallback
- **Honesty**: CLI flags now match documentation
- **Thread safety**: `threading.Lock()` prevents lost audit outputs

## Remaining Work (Not Started)
- Test Groq/HuggingFace live calls end-to-end
- Add Ollama auto-start / `ollama pull` check in `orchestrator.py`
- Wire `LOCAL_MODELS` in Ruflo to actually call `ollama_local` when `--tier local`
- Retry/backoff tuning after production telemetry
