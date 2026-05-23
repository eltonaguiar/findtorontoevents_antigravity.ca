---
description: Ruflo agent swarm orchestrator via Hermes. Subcommands: help|audit|github|strategy|bugs|wizard|keys|continuous
argument-hint: [help|audit|github|strategy|bugs|wizard|keys|continuous] [--tier free|paid|hybrid]
---

User invoked `/swarm-ruflo $ARGUMENTS`.

Parse `$ARGUMENTS` and dispatch:

- **`help`** or **empty** → print usage card below.
- **`audit [--tier free|paid|hybrid]`** → Run audit swarm (2 agents: researcher + quant). Shows insights path.
- **`github [--tier free|paid|hybrid]`** → Run GitHub hygiene swarm. Shows PRs, failed Actions, recommendations.
- **`strategy [--tier free|paid|hybrid]`** → Run strategy ideation swarm. Shows 3 new strategy proposals.
- **`bugs [--tier free|paid|hybrid]`** → Run bug hunter swarm. Shows bugs found with severity.
- **`wizard`** → Run `python3 .ruflo/wizard.py` — interactive tier/model selection guide.
- **`keys`** → Run `python3 .ruflo/orchestrator.py --check-keys` — show which paid API keys are available.
- **`continuous [--tier free|paid|hybrid] [--cycle-minutes N]`** → Run all swarms in a loop.

**Tier selection:**
- `free` (default): OpenRouter free models via Hermes — zero cost, slower, lower quality
- `paid`: Direct API calls via api_consult.py (DeepSeek, Cerebras, xAI, Inception) — faster, higher quality, costs credits
- `hybrid`: Try paid first, fall back to free on failure

**Windows bridge:** All swarms run via WSL:
```
wsl bash -c "cd /mnt/c/findtorontoevents_antigravity.ca && python3 .ruflo/orchestrator.py --swarm <name> --tier <tier>"
```

After every swarm run, show:
1. Which agents produced output (with byte sizes)
2. Path to saved insights: `swarm_runs/ruflo-insights/`
3. Path to compiled summary: `swarm_runs/ruflo-insights/COMPILED_latest.json`

If `$ARGUMENTS` is empty or `help`, output:

```
/swarm-ruflo — ruflo-style agent swarm via Hermes + paid APIs

USAGE
  /swarm-ruflo audit [--tier free|paid|hybrid]     performance audit (2 agents)
  /swarm-ruflo github [--tier free|paid|hybrid]     repo hygiene check
  /swarm-ruflo strategy [--tier free|paid|hybrid]   new strategy proposals
  /swarm-ruflo bugs [--tier free|paid|hybrid]       bug & security hunt
  /swarm-ruflo wizard                                interactive tier selector
  /swarm-ruflo keys                                  check paid API key status
  /swarm-ruflo continuous [--tier ...]              run all swarms in a loop
  /swarm-ruflo help                                  this help

AGENTS (5)
  audit_researcher   role=researcher       model=gemini-pro-1.5-preview:free
  audit_quant        role=coder            model=deepseek-chat:free
  github_hygiene     role=reviewer         model=mistral-7b-instruct:free
  bug_hunter         role=security-architect model=hy3-preview:free
  strategist         role=architect        model=hy3-preview:free

TIERS
  free     OpenRouter free models via hermes chat -q     zero cost, slower
  paid     Direct API calls via api_consult.py            costs credits, faster
  hybrid   Paid first, fallback to free                  best of both

PAID PROVIDERS (when keys are set)
  cerebras    gpt-oss-120b       → CEREBRAS_API_KEY
  deepseek    deepseek-chat      → DEEPSEEK_API
  xai         grok-3-latest      → X_AI_KEY
  inception   mercury-2          → INCEPTION_AI_KEY
  openrouter  gpt-4o-mini        → OPENROUTER
  ollama_cloud gpt-oss:120b-cloud → OLLAMA_CLOUD_KEY

KEY FILES
  .ruflo/orchestrator.py           main engine
  .ruflo/wizard.py                 interactive tier selector
  .ruflo/agents/*.yaml             5 agent definitions
  tools/swarm/api_consult.py       paid API caller
  swarm_runs/ruflo-insights/       output directory

GUIDE
  RUFLO_SWARM_GUIDE.md             comprehensive usage guide
  BUFFTOHERMES.MD                  Codebuff review + protocol doc

SAFETY
  Paid API keys are NEVER output — checked from env vars only.
  All agent output is sanitized (keys redacted).
  Free tier uses only OpenRouter free models (no credit cost).
```

Always show output byte sizes for each agent after a swarm run.
If paid tier fails, suggest `/swarm-ruflo keys` to diagnose.
If hermes is not found, suggest running from WSL directly.
