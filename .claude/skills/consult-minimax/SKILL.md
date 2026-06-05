---
name: consult-minimax
description: Consult MiniMax M3 via Ollama Cloud (`minimax-m3:cloud`) for peer review and second-opinion analysis. Use when the user says `/consult-minimax`, "ask minimax", "minimax second opinion", or wants MiniMax's beautiful structured analysis on a finding, plan, or strategy claim.
---

# /consult-minimax — MiniMax M3 (Ollama Cloud) consult

MiniMax M3 is hosted on Ollama Cloud as `minimax-m3:cloud`. It produces clear, structured, often beautiful analyses — the user has flagged it as a particularly strong peer-review counterparty.

## Prerequisites

- `ollama` installed (`/usr/local/bin/ollama` on this machine).
- Ollama Cloud auth (the `:cloud` suffix routes to managed inference; if `ollama run minimax-m3:cloud` returns an auth error, `ollama signin` first).

## Usage

```
/consult-minimax <question or prompt>
/consult-minimax --file <path-to-prompt.md>
```

## Invocation (Bash)

### Quick inline question

```bash
ollama run minimax-m3:cloud "<your full prompt here>" 2>&1 | tee /tmp/consult-minimax-$(date -u +%Y%m%dT%H%M%SZ).txt
```

### From a file (recommended for any prompt > 200 words)

```bash
ollama run minimax-m3:cloud "$(cat /path/to/prompt.md)" 2>&1 | tee /tmp/consult-minimax-$(date -u +%Y%m%dT%H%M%SZ).txt
```

### Structured peer-review pattern (for double-checking a finding)

```bash
cat <<'EOF' | ollama run minimax-m3:cloud 2>&1
You are MiniMax M3 acting as an independent quant peer reviewer for a multi-AI audit system.

# Finding under review
<paste finding here — include the live-DB numbers, OOS-split, concentration, fat-tail check>

# Your job
1. Identify any axis the reviewer didn't check (e.g. survivorship bias, regime dependency, slippage realism, look-ahead in resolver, broker-side fill assumption).
2. For each axis, state CORROBORATE / REFUTE / NEEDS_MORE_EVIDENCE and one-sentence rationale.
3. End with a single VERDICT: PROMOTE / HOLD / REFUTE.

Be terse and structural. No marketing language. Mirror the reviewer's evidence style.
EOF
```

## When MiniMax is a better fit than other consult-* skills

- Peer-reviewing a quant/strategy claim where you want a structural breakdown (multi-axis verdict table).
- Cross-checking another AI's "VALIDATED ✅" — see memory `project-multi-agent-storm-2026-06-05` for why this matters (Cloud-Minimix VRP failure pattern).
- Strategy survivorship / regime-dependency analysis.

## When to prefer another consult-*

- Live web search needed → `/consult-grok` (xAI has web access).
- Fast/cheap throwaway second opinion → `/consult-gemini` or `/consult-cloudflare` (CF models).
- Code review with diff context → `/consult-codex` or `/consult-cursor-agent`.

## Notes

- The `:cloud` suffix on the model name routes through Ollama Cloud's managed inference, not local hardware (good — local MiniMax M3 weights would be >100GB).
- Output is plain text; if you want structured JSON back, prefix the prompt with `Respond in this exact JSON schema: {...}` and MiniMax will usually comply.
- Cost: bills against the user's Ollama Cloud account. For routine session-level peer-review (1-2 consults per investigation) this is negligible; do not fan out 100 prompts.
- For multi-AI fan-out including MiniMax, use `/consult-PROXY` or `/consult-multi` if it has a MiniMax provider, otherwise drive ollama in a `parallel`/`xargs` loop.
