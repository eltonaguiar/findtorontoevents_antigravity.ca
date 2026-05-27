---
name: PeerReviewSwarmOptions
description: Catalog of every available peer-review / multi-AI consultation mechanism in this repo. Use when picking the right tool for swarm-reviewing PRs, validating findings, or fan-out brainstorming. Pros/cons + cost/latency/auth for each.
aliases: [peer-review-swarms, swarm-options, which-swarm, swarmpicker]
---

# /PeerReviewSwarmOptions — Pick the right swarm for the job

## When to use this skill

Trigger when you need to pick BETWEEN swarm tools — not when you've already decided on one. If you already know "I want a 3-engine consensus", just call `/swarm-second-opinion`. If you don't know what to use, read this first.

## The 10 swarm/peer-review options ranked

### 1. `/swarm-second-opinion` (RECOMMENDED DEFAULT)
**What**: 3-engine consensus via `tools/swarm/swarm_run.py --preset consensus-3` (deepseek + xai + kilo).
**Pros**: Fast (~30-45s), well-tested, JSON-locked output, ~$0.001 cost. Catches most blindspots.
**Cons**: Only 3 engines; can miss niche failure modes.
**Best for**: PR reviews, decision tiebreakers, single-question second opinions.

### 2. `/consult-swarm` (Kilo Code's catalog-and-router)
**What**: Meta-skill that picks between swarm_v2, ruflo, consult-multi, combine-team.
**Pros**: Decision wrapper — handles "I don't know which tool".
**Cons**: Adds a layer; if you already know which tool, faster to call directly.
**Best for**: Open-ended "I want multi-AI input but I'm not sure what shape".

### 3. `tools/swarm/swarm_run.py` (raw multi-engine fan-out)
**What**: Direct CLI to fan a prompt across 2-N engines (deepseek, xai, kilo, gemini, ofox, nvidia_deepseek, etc).
**Pros**: Maximum control — pick exact engines, set `--cost-cap-usd`, `--json-strict`, `--persona`.
**Cons**: You write the prompt + parse the output. No built-in consensus extraction.
**Best for**: Production scripts, repeated fan-outs, when you know exactly what you want.
**Invocation**:
```bash
python3 tools/swarm/swarm_run.py --prompt-file /tmp/q.md --engines deepseek,xai --out-dir swarm_runs/topic-$(date -u +%Y%m%dT%H%M%SZ)
```

### 4. `/swarm-pr-review` (PR-specific 3-engine review)
**What**: Multi-model PR review with role-specialization (impact, code, risk).
**Pros**: Tailored for PR review (vs generic Q&A). Returns merge/needs-changes/major-rework verdict.
**Cons**: Slower than `/swarm-second-opinion` (~60-90s). Costs ~$0.005 per PR.
**Best for**: Open-PR sweeps — exactly what's needed for the "review all open PRs" task.
**Invocation**:
```bash
python tools/swarm/swarm_dispatch.ps1 -pr <number>  # PowerShell, the original; Windows-first
# OR for cross-platform:
python tools/swarm/swarm_run.py --pr <number> --preset consensus-3 --json-strict
```

### 5. `/swarmv2-pr-review` (enhanced PR review with risk model)
**What**: 6-engine self-improving swarm with quality scoring + A/B + skill export.
**Pros**: Most thorough — impact analysis + code review + risk assessment. Self-improving.
**Cons**: Slow (~2-5 min/PR), expensive (~$0.02). Overkill for trivial PRs.
**Best for**: High-stakes PRs (production secrets, financial logic, safety-critical).

### 6. `/swarm-ruflo` (ruflo orchestrator)
**What**: Hermes-based ruflo swarm with subcommands (audit/github/strategy/bugs/wizard/keys/continuous).
**Pros**: Domain-specialized agents (github-actions auditor, bug hunter, strategy reviewer).
**Cons**: Requires the Hermes agent to be running locally; key management complexity.
**Best for**: When you want a specific agent type (e.g., "github-actions auditor on PR #N").

### 7. `/consult-multi` (11-provider router)
**What**: Unified CLI fronting 11 LLM providers (NVIDIA, Groq, Cerebras, Together, Fireworks, GitHub Models, HuggingFace, Gemini, Cloudflare, DeepInfra, Nous).
**Pros**: Free-tier rotation across many providers; reads keys from `~/dbpasses.txt`. Single-provider OR fan-out (`--fanout diverse5/fast4/reasoning4/all9`).
**Cons**: Provider quality varies; some free-tier providers rate-limit aggressively.
**Best for**: Multi-provider triangulation when you want providers, not specific models.

### 8. `/consult-cloudflare-models` (Cloudflare Workers AI fan-out)
**What**: 37+ models on Cloudflare (Llama, GPT-OSS, Nemotron, Qwen, GLM, Mistral, Phi, Gemma).
**Pros**: Free-tier friendly; very wide model coverage.
**Cons**: Cloudflare model versions lag a bit behind upstream releases.
**Best for**: Wide-net brainstorming or "show me what 5 random models think".

### 9. `/consult-nvidia-models` (NVIDIA NIM fan-out)
**What**: 10+ models on NVIDIA Integrate API (DeepSeek v4 Pro, MiniMax, Kimi-K2.6, Nemotron, Qwen, Llama-4, Mistral).
**Pros**: High-quality models (DeepSeek v4 Pro is excellent); free tier.
**Cons**: Single provider — if NVIDIA NIM goes down or quota hits, everything fails.
**Best for**: When DeepSeek v4 Pro specifically is what you want.

### 10. FreeLLM CombineTeam / DebateTeam (external)
**What**: User's `FREELLM` repo runs CombineTeam (consensus aggregator) or DebateTeam (adversarial debate between AIs).
**Pros**: DebateTeam catches things consensus misses — adversarial framing surfaces hidden assumptions.
**Cons**: Lives in a separate repo (`E:\FREELLM\` per user); higher setup cost; output format different.
**Best for**: Truly high-stakes decisions where you want adversarial pressure-testing, not consensus.

## Single-provider variants (lighter weight)

When 1 AI is enough but you want a different perspective from Claude:

| Skill | Provider | When to use |
|---|---|---|
| `/consult-grok` | xAI Grok CLI | Real-time / current-event awareness |
| `/consult-gemini` | Google Gemini CLI | Long-context (>200K tokens) |
| `/consult-codex` | OpenAI Codex CLI | Code-heavy questions |
| `/consult-cursor-agent` | Cursor Agent CLI | Codebase-aware (it has its own context) |
| `/consult-opencode` | opencode CLI | Open-source CLI equivalent |
| `/consult-kilo` | kilo CLI (opencode fork) | Quick second opinion |
| `/consult-ofox` | Z.AI GLM-4.7-Flash (free) | Cheap structured-JSON |
| `/consult-ring261T` | inclusionai/ring-2.6-1t on OpenRouter | 1T-parameter extended-thinking; deep reasoning |
| `/consult-nvidia-deepseek` | DeepSeek v4 Pro on NVIDIA NIM | Default high-quality JSON-locked answer |
| `/consult-cloudflare` | Any of 37+ CF models | Specific model selection |

## Decision tree

```
Need peer review on a PR?
├── 1 PR, low-stakes      → /swarm-second-opinion (3 engines)
├── Many PRs, batch sweep → /swarm-pr-review per PR
├── High-stakes (real money, secrets, prod-critical) → /swarmv2-pr-review
└── Need adversarial framing → FreeLLM DebateTeam

Need brainstorming / fan-out?
├── 3-engine consensus        → /swarm-second-opinion
├── 5-9 provider diversity    → /consult-multi --fanout
├── 37+ model breadth         → /consult-cloudflare-models
└── Codebase-aware            → /consult-cursor-agent or /consult-kilo

Need a second opinion on a single answer?
├── JSON-locked output, cheap → /consult-ofox or /consult-nvidia-deepseek
├── Long context              → /consult-gemini
├── Real-time awareness       → /consult-grok
├── Deep reasoning            → /consult-ring261T
└── Cross-provider robustness → /consult-multi --provider <name>
```

## Cost summary (per call, approximate)

| Tier | Examples | Cost |
|---|---|---|
| Free | ofox, gemini, kilo, cloudflare, nvidia (free tier), groq, cerebras, together | $0 |
| Near-free | deepseek, xai | $0.001–0.005 |
| Paid | swarmv2 (multiple engines × tokens) | $0.005–0.05 |
| Expensive | ring261T (extended thinking) | $0.01–0.10 |

## Output format conventions

All swarm tools that follow our convention produce `swarm_runs/<topic>-<UTC-timestamp>/`:
```
swarm_runs/topic-ts/
  ├── <engine>.json          # parsed JSON response (preferred)
  ├── <engine>.json.raw.txt  # unparsed text (debugging)
  ├── _summary.json          # cost + tokens + transport metadata
```

Always inspect both `<engine>.json` (structured) AND `.raw.txt` (for engines that failed schema validation).

## Lessons learned

1. **TICK 15 retraction lesson** (2026-05-26 session): always run a swarm round on high-stakes findings BEFORE writing the pressure-test report. I called CT=F a Tier-1 candidate at n=230 raw and got falsified by the dedup view 4 ticks later. Two-engine swarm would have caught it.

2. **JSON-locked prompts beat open-ended**: When prompts request structured JSON output with named fields + a confidence enum, engines commit to concrete answers instead of hedging.

3. **2 engines is usually enough**: deepseek + xai catches ~90% of what 3-5 engines catch. Add more only when stakes are high (financial logic, secrets, safety-critical).

4. **Background mode for long-running**: `run_in_background=true` on `tools/swarm/swarm_run.py` lets you kick off and continue other work.

## Quick reference one-liners

```bash
# Two-engine fan-out (most common):
python3 tools/swarm/swarm_run.py --prompt-file /tmp/q.md \
  --engines deepseek,xai --out-dir swarm_runs/qq-$(date -u +%Y%m%dT%H%M%SZ)

# Three-engine consensus preset:
python3 tools/swarm/swarm_run.py --prompt-file /tmp/q.md \
  --preset consensus-3 --out-dir swarm_runs/big-$(date -u +%Y%m%dT%H%M%SZ)

# PR review specifically:
python3 tools/swarm/swarm_run.py --pr 8 --preset consensus-3 \
  --json-strict --out-dir swarm_runs/pr8-review-$(date -u +%Y%m%dT%H%M%SZ)

# Cheap free second opinion (no API budget):
echo "Your question" | python3 tools/swarm/api_consult.py --provider ofox -

# NVIDIA DeepSeek v4 Pro (free, high-quality, JSON-locked):
echo "Your question" | python3 tools/swarm/api_consult.py --provider nvidia_deepseek -
```

## Related skills

- `/swarm-second-opinion` — 3-engine consensus wrapper
- `/swarm-pr-review` — PR-specific review
- `/swarmv2-pr-review` — enhanced 6-engine PR review
- `/consult-swarm` — Kilo's meta-router (consolidates many of the above)
- `/swarm-actions-audit` — multi-agent GH Actions audit
- `/swarm-followup` — multi-turn chain (priming → analysis → critique → final)
- `/swarm-transcript-scan` — audit a session transcript for missed action items
- `/consult-multi` — 11-provider router
