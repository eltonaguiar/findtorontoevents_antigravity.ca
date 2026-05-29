---
title: "AI Tournament — Widen secret-fallback chains so all 23 models can produce picks"
date: 2026-05-28
status: PR open, awaiting operator action for OPENAI + ANTHROPIC secrets
parent_diagnosis: reports/2026-05-27_ai_tournament_model_gap_diagnosis.md
---

# Fix: Widen GH Actions Secret Chains for AI Tournament

## Problem (recap)

`config/model_persona_mapping.json` enables **23** models. The daily
`ai-tournament-pipeline.yml` only produces picks for **3** of them
(grok3, deepseek_v4, cerebras_llama4). The other 20 silently no-op
because their provider env-var was unset on the runner — the underlying
secret either had a different name or was missing entirely.

## What this PR changes

Single file: `.github/workflows/ai-tournament-pipeline.yml`, env block
of the `Generate picks fleet` step.

| Provider env var      | Before                               | After                                                            | Effect                                  |
|-----------------------|---------------------------------------|------------------------------------------------------------------|-----------------------------------------|
| INCEPTION_API_KEY     | `secrets.INCEPTION_API_KEY \|\| ''`        | `secrets.INCEPTION_API_KEY \|\| secrets.TOGETHER_API_KEY \|\| ''`     | mercury wakes up (routes via Together)  |
| GROQ_API_KEY          | `secrets.GROQ_API_KEY \|\| ''`             | `secrets.GROQ_API_KEY \|\| secrets.GROQ_KEY \|\| ''`                  | covers legacy secret name in the vault  |
| OPENAI_API_KEY        | (no fallback exists)                 | TODO(operator) annotation added                                  | needs `gh secret set OPENAI_API_KEY`    |
| ANTHROPIC_API_KEY     | (no fallback exists)                 | TODO(operator) annotation added                                  | needs `gh secret set ANTHROPIC_API_KEY` |

All other provider chains were already widened in commit `31b1411fe`
(GEMINI_FREE_KEY fallback) and the 2026-05-27 broadening that added
NVIDIA, TOGETHER, FIREWORKS, GH_MODELS, NOUS, AIMLAPI, HYPERBOLIC,
FEATHER, NOVITA, INCEPTION env wires.

## Per-model status after this PR merges

| Model                  | provider env var       | Secret present? | Submits? |
|------------------------|------------------------|------------------|----------|
| deepseek_v4            | DEEPSEEK_API_KEY       | yes              | yes      |
| cerebras_llama4        | CEREBRAS_API_KEY       | yes              | yes      |
| grok3                  | XAI_API_KEY            | yes              | yes      |
| gemini_25_pro          | GEMINI_FREE_KEY (fb)   | yes              | yes      |
| mistral_large          | MISTRAL_API_KEY        | yes              | yes      |
| nvidia_deepseek_v4_pro | NVIDIA_API_KEY         | yes              | yes      |
| nvidia_nemotron_3_70b  | NVIDIA_API_KEY         | yes              | yes      |
| nvidia_minimax_m2      | NVIDIA_API_KEY         | yes              | yes      |
| groq_llama_3_70b       | GROQ_API_KEY/GROQ_KEY  | yes              | yes      |
| groq_kimi_k2           | GROQ_API_KEY/GROQ_KEY  | yes              | yes      |
| together_qwen_3        | TOGETHER_API_KEY       | yes              | yes      |
| together_deepseek_v3   | TOGETHER_API_KEY       | yes              | yes      |
| fireworks_qwen         | FIREWORKS_API_KEY      | yes              | yes      |
| gh_models_gpt4o        | GH_MODELS_API_KEY      | yes              | yes      |
| nous_hermes_4          | NOUS_API_KEY           | yes              | yes      |
| hyperbolic_llama       | HYPERBOLIC_API_KEY     | yes              | yes      |
| feather_llama          | FEATHER_API_KEY        | yes              | yes      |
| aimlapi_gpt4o          | AIMLAPI_API_KEY        | yes              | yes      |
| mercury                | INCEPTION/TOGETHER fb  | yes (via fb)     | yes      |
| ring_261T              | OPENROUTER_API_KEY     | yes              | needs runtime debug (see parent diag §FIX 3) |
| gpt4o_mini             | OPENAI_API_KEY         | **NO**           | blocked  |
| cursor_agent           | ANTHROPIC_API_KEY      | **NO**           | blocked  |
| claude_opus            | ANTHROPIC_API_KEY      | **NO**           | blocked  |

Expected outcome after merge: **3 active → 19+ active** (provided each
provider's quotas/model IDs work — runtime debug may be required per
provider on first run).

## Operator action required (NOT done by this PR)

The keys live in `~/dbpasses.txt` on the workstation. To unblock the
last 3 models, run:

```bash
gh secret set OPENAI_API_KEY     # value from ~/dbpasses.txt OPENAI section
gh secret set ANTHROPIC_API_KEY  # value from ~/dbpasses.txt ANTHROPIC section
```

These are intentionally not done in CI/by this PR because:
1. The agent does not read `~/dbpasses.txt`.
2. Secret-setting requires a real key value, not a fallback wire.

## Why not merge automatically

User policy is "PR open, leave for review". After human merge plus the
two `gh secret set` commands, the next scheduled run at 12:00 UTC will
show the wider model fleet on `/audit/ai-tournament.html`.

## Verification

- `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ai-tournament-pipeline.yml'))"` → OK
- No literal secret values added to code.
- Diff is +12 / -4 lines in one file.
