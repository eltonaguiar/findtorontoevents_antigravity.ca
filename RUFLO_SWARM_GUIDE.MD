# 🦊 RUFLO SWARM GUIDE — Agent Swarm Orchestrator via Hermes

> **Version:** 1.0.0
> **Date:** 2026-05-05
> **Authors:** Buffy (Codebuff) + Hermes Agent v0.12.0
> **Location:** `.ruflo/` directory

---

## WHAT IS RUFLO SWARM?

A 5-agent swarm orchestrator inspired by [ruvnet/ruflo](https://github.com/ruvnet/ruflo) but implemented as a Python CLI that dispatches work through **Hermes Agent** (Nous Research, v0.12.0) with OpenRouter as the model backend.

5 specialized agents run in parallel on different analysis tasks:
- **audit_researcher** — reads performance data, finds insights
- **audit_quant** — quantitative analysis, WR/PF/MDD by asset class
- **github_hygiene** — PR reviews, failed Actions, stale commits
- **bug_hunter** — code bugs, security issues, anti-patterns
- **strategist** — new trading strategy proposals

All output saved to `swarm_runs/ruflo-insights/` with a compiled JSON summary.

---

## QUICK START

### 1. Run the wizard (interactive guide)
```bash
# From WSL:
python3 .ruflo/wizard.py

# Or via slash command (in Claude/Cursor/etc.):
/swarm-ruflo wizard
```

### 2. Check your setup
```bash
# From WSL:
python3 .ruflo/orchestrator.py --list-agents --no-verify

# Via slash command:
/swarm-ruflo help
```

### 3. Run your first swarm
```bash
# From Codebuff (Windows):
wsl bash -c "cd /mnt/c/findtorontoevents_antigravity.ca && python3 .ruflo/orchestrator.py --swarm audit --no-verify"

# From WSL directly:
python3 .ruflo/orchestrator.py --swarm audit

# Via slash command:
/swarm-ruflo audit
```

### 4. Read results
```bash
cat swarm_runs/ruflo-insights/COMPILED_latest.json | python3 -m json.tool
```

---

## COMMANDS REFERENCE

### `/swarm-ruflo` (slash command)

| Command | Description | Agents | Est. Time |
|---------|-------------|--------|-----------|
| `/swarm-ruflo audit` | Performance audit by asset class | 2 (researcher + quant) | 2-5 min |
| `/swarm-ruflo github` | Repo hygiene: PRs, Actions, commits | 1 (github_hygiene) | 1-3 min |
| `/swarm-ruflo strategy` | New strategy proposals | 1 (strategist) | 2-4 min |
| `/swarm-ruflo bugs` | Bug & security hunt | 1 (bug_hunter) | 1-4 min |
| `/swarm-ruflo wizard` | Interactive tier selector | None (local) | <1 min |
| `/swarm-ruflo keys` | Check paid API key status | None (local) | <1 min |
| `/swarm-ruflo continuous` | Run all swarms in a loop | All 5 | N × 5-15 min |
| `/swarm-ruflo help` | Show help card | None (local) | <1 min |

All swarm commands accept `--tier free|paid|hybrid`:
- `/swarm-ruflo audit` — defaults to free tier
- `/swarm-ruflo audit --tier paid` — uses paid API keys
- `/swarm-ruflo audit --tier hybrid` — paid first, free fallback

### `orchestrator.py` (CLI)

```bash
# Run a specific swarm
python3 .ruflo/orchestrator.py --swarm audit       # audit swarm
python3 .ruflo/orchestrator.py --swarm github      # github hygiene
python3 .ruflo/orchestrator.py --swarm strategy    # strategy proposals
python3 .ruflo/orchestrator.py --swarm bugs        # bug hunt
python3 .ruflo/orchestrator.py --swarm all         # all swarms
python3 .ruflo/orchestrator.py --continuous        # continuous loop

# Tier selection
python3 .ruflo/orchestrator.py --swarm audit --tier free     # OpenRouter free models
python3 .ruflo/orchestrator.py --swarm audit --tier paid     # Direct API calls
python3 .ruflo/orchestrator.py --swarm audit --tier hybrid   # Paid first, free fallback

# Options
--timeout N          # Timeout per agent in seconds (default: 300)
--no-verify          # Skip Hermes binary check (for Codebuff basher)
--list-agents        # Show registered agents
--check-keys         # Show paid API key status
--help               # Full help
```

---

## TIER COMPARISON

| Dimension | FREE | PAID | HYBRID (★ Recommended) |
|-----------|------|------|------------------------|
| **Models** | OpenRouter free-tier via Hermes | Direct API via api_consult.py | Paid first, free fallback |
| **Cost** | $0.00 | Varies by provider | Pay only when paid succeeds |
| **Speed** | 🐢 Slow (shared capacity) | ⚡ Fast (dedicated) | ⚡ Fast normally |
| **Quality** | ⭐⭐ Base models | ⭐⭐⭐⭐ Frontier models | ⭐⭐⭐⭐ Best effort |
| **Reliability** | Rate-limited, may 404 | High (dedicated capacity) | High (always completes) |
| **Setup** | Zero config | Needs API keys | Needs API keys |
| **Failover** | 3-attempt model rotation | None (single call) | Paid fails → free |
| **Best for** | Background monitoring, non-urgent | Latency-sensitive, high-quality | Production use |

### FREE tier models (OpenRouter)
| Agent | Role | Model |
|-------|------|-------|
| audit_researcher | researcher | google/gemini-pro-1.5-preview:free |
| audit_quant | coder | deepseek/deepseek-chat:free |
| github_hygiene | reviewer | mistralai/mistral-7b-instruct:free |
| bug_hunter | security-architect | tencent/hy3-preview:free |
| strategist | architect | tencent/hy3-preview:free |

### PAID tier providers (when keys are set)
| Provider | Model | Env Var | Best for |
|----------|-------|---------|----------|
| cerebras | gpt-oss-120b | CEREBRAS_API_KEY | Research, fast inference |
| deepseek | deepseek-chat | DEEPSEEK_API | Coding, quantitative analysis |
| xai | grok-3-latest | X_AI_KEY | Architecture, strategy |
| inception | mercury-2 | INCEPTION_AI_KEY | Review, lightweight tasks |
| openrouter | gpt-4o-mini | OPENROUTER | Fallback, 200+ models |
| ollama_cloud | gpt-oss:120b-cloud | OLLAMA_CLOUD_KEY | Local CLI, cloud models |

---

## FAILOVER SYSTEM

The orchestrator has built-in runtime model failover for the free tier:

1. **Attempt 1:** Primary model (from agent YAML)
2. **Attempt 2:** Next model in FAILOVER_MODELS chain (filtered)
3. **Attempt 3:** Last model in chain (tencent/hy3-preview:free)

**Failover chain:** gemini-pro → deepseek-chat → mistral-7b → hy3-preview

**Triggers:** 429, rate limit, exhausted, timeout, connection errors, provider errors, empty stderr with non-zero exit.

**Exponential backoff:** 2^attempt seconds (2s, 4s between retries).

**Non-recoverable errors** (code bugs, file not found) exit immediately without retry.

---

## OUTPUT STRUCTURE

```
swarm_runs/ruflo-insights/
├── audit_researcher_output.txt
├── audit_quant_output.txt
├── github_hygiene_output.txt
├── bug_hunter_output.txt
├── strategist_output.txt
├── COMPILED_latest.json          ← Read this for summary
└── logs/
    └── swarm_YYYYMMDD_HHMMSS.log
```

### COMPILED_latest.json format
```json
[
  {
    "file": "audit_researcher_output.txt",
    "agent": "audit_researcher",
    "role": "researcher",
    "model": "google/gemini-pro-1.5-preview:free",
    "tier": "free",
    "elapsed_s": 45.2,
    "output": "{ ... agent JSON output ... }"
  },
  ...
]
```

---

## WINDOWS ↔ WSL BRIDGE

**The project lives at:** `C:\findtorontoevents_antigravity.ca` (Windows)
**WSL path:** `/mnt/c/findtorontoevents_antigravity.ca`

### From Codebuff (Windows terminal):
```bash
wsl bash -c "cd /mnt/c/findtorontoevents_antigravity.ca && python3 .ruflo/orchestrator.py --swarm audit --no-verify"
```

Note: `--no-verify` is needed because Codebuff's basher agent has a WSL path translation issue. Hermes itself works fine — the issue is in how basher translates Windows paths to WSL.

### From WSL directly:
```bash
cd /mnt/c/findtorontoevents_antigravity.ca
python3 .ruflo/orchestrator.py --swarm audit
```

---

## COMPARISON: ruflo swarm vs tools/swarm

| Dimension | ruflo swarm | tools/swarm |
|-----------|-------------|-------------|
| **Architecture** | Hermes Agent → OpenRouter | Python → api_consult.py |
| **Agent count** | 5 specialized | 2+ engines per run |
| **Model transport** | Hermes internal routing | Direct env-var API keys |
| **Free tier** | ✅ Yes (OpenRouter free) | ❌ No (needs API keys) |
| **Paid tier** | ✅ Direct API via api_consult | ✅ Direct API via api_consult |
| **Failover** | ✅ 3-attempt model rotation | ❌ Single engine call |
| **Wizard/UX** | ✅ Interactive wizard + slash commands | ❌ CLI only |
| **WSL bridged** | ✅ Yes (from Windows via wsl bash -c) | ❌ No (runs on Windows natively) |
| **Reliability** | ⚠️ Free tier hit-or-miss | ✅ High (paid APIs) |
| **Cost per run** | $0 (free) / varies (paid) | $0.001-0.01 (paid) |
| **Best for** | Strategy, bugs, audit, continuous monitoring | PR review, CI analysis, latency-sensitive |

**Recommendation:** Use both. ruflo for strategy/audit work (agent specialization), tools/swarm for PR reviews and CI analysis (proven reliability). Cross-validate important findings with both systems.

See `updates/SWARM_STYLE_DIFF.MD` for a detailed live benchmark comparison.

---

## KEY FILES

| File | Purpose |
|------|---------|
| `.ruflo/orchestrator.py` | Main engine — swarm dispatch, failover, output collection |
| `.ruflo/wizard.py` | Interactive tier & model selection guide |
| `.ruflo/agents/*.yaml` | 5 agent definitions (audit, github, bugs, strategy) |
| `.claude/commands/swarm-ruflo.md` | `/swarm-ruflo` slash command dispatcher |
| `.claude/commands/swarm-ruflo-help.md` | `/swarm-ruflo-help` command |
| `tools/swarm/api_consult.py` | Paid API caller (shared with tools/swarm) |
| `BUFFTOHERMES.MD` | Codebuff's review of Hermes' ruflo implementation |
| `HERMESTOFREEBUFF.MD` | Hermes' peer review of Codebuff's fixes |
| `updates/SWARM_STYLE_DIFF.MD` | Side-by-side benchmark comparison |
| `swarm_runs/ruflo-insights/` | Output directory for swarm runs |

---

## TROUBLESHOOTING

### "hermes: command not found"
Hermes binary not in PATH. Set `HERMES_BIN` env var or ensure `~/.local/bin` is in PATH.

### "HTTP 404: No endpoints found"
OpenRouter free tier overloaded. Wait and retry, or switch to paid tier.

### "C:/Program Files/..." path error from Codebuff basher
Known basher agent WSL path translation issue. Use `--no-verify` flag.

### "No paid API keys found"
Set environment variables:
```bash
export CEREBRAS_API_KEY="..."
export DEEPSEEK_API="..."
export X_AI_KEY="..."
export INCEPTION_AI_KEY="..."
export OPENROUTER="..."
export OLLAMA_CLOUD_KEY="..."
```

### Agent times out
Increase timeout: `--timeout 600` (10 minutes). Free models are slow.

---

## SAFETY

- **Paid API keys are NEVER output** — checked from env vars only, redacted in all output
- **All agent output is sanitized** — keys, tokens, passwords redacted
- **Free tier uses only OpenRouter free models** — no credit cost
- **Env var fallback chain** — multiple possible env var names per provider for compatibility
- **No destructive operations** — swarms are read-only analysis, no file mutations
