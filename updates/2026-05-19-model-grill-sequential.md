# 2026-05-19 — Model grill (cloud parallel + local sequential)

## What shipped

- `tools/model_grill_sequential.py` — cloud parallel **per API key**; local **one-at-a-time** with hard timeouts
- `tools/api_model_roster.py` + `config/api_model_roster.json` + skill `.cursor/skills/api-model-roster/`
- `swarm_runs/_prompts/` — HARVEST, MASTER, DOUBLE_CHECK R1–R3
- Reports: `INTELLIGENCE_RANKING_2026-05-19.md`, `DOUBLE_CHECK_SYNTHESIS_2026-05-19.md`

## Findings

- **Smartest cloud (harvest):** DeepSeek + Pollinations (intel 4)
- **Fastest cloud:** Inception Mercury-2 (~2.4s) — verify outputs; rejects false live-ready claims
- **Ring 2.6-1t:** ~19s, intel 3 — good free-tier speed, not best depth
- **Local Ollama:** CLI grill timed out this session; use HTTP API + fixed 14b timeout regex

## Verified

```powershell
python tools/model_grill_sequential.py --wave paid --prompt harvest
python tools/model_grill_sequential.py --wave ring --prompt harvest
python -m py_compile tools/model_grill_sequential.py tools/api_model_roster.py
```
