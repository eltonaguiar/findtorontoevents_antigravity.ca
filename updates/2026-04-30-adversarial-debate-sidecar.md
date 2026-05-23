# 2026-04-30 — Adversarial bull/bear debate sidecar (PR-LIFT-1)

## Problem statement

UEPS top-30 picks (long-term equity stack) currently ship with a single-pass
score. There is no "what's the bear case?" gate before a pick reaches the
active book. Inspired by the bull/bear researcher debate stage in
[tauricresearch/tradingagents](https://github.com/tauricresearch/tradingagents)
(Apache-2.0), this PR adds an opt-in adversarial pre-flight that runs two
opposing LLMs on each pick and records the margin.

## What this is NOT

- Not a wholesale TradingAgents import. We don't take LangGraph, the analyst
  team, the risk manager, or the reflection loop — those duplicate
  alpha_engine/ modules already in production (`thesis_resolver`,
  `score_booster`, `consecutive_loss_tracker`, `pump_guard`,
  `passes_active_gate`).
- Not a production wire-in. Sidecar / opt-in / default-off per the CLAUDE.md
  Wire-Up Rule.

## Files

- `alpha_engine/adversarial_debate.py` (new, ~270 LOC) — stdlib-only sidecar
- `tests/test_adversarial_debate.py` (new, 19 tests, no live LLM calls)

## Design

### Provider-agnostic OpenAI-compatible HTTP

Uses `urllib.request` (stdlib, no SDK dependency). All supported providers
expose a `/chat/completions` endpoint with the OpenAI request shape, so a
single `_post_chat()` works for every one. Provider registry covers:

| Provider | Standard env | Legacy env in this repo |
|---|---|---|
| DeepSeek | `DEEPSEEK_API_KEY` | `DEEPSEEK_API` |
| xAI Grok | `XAI_API_KEY` | `X_AI_KEY`, `GROK_SUPER`, `X_AI_SECONDOP` |
| OpenAI | `OPENAI_API_KEY` | — |
| OpenRouter | `OPENROUTER_API_KEY` | — |
| Anthropic (via OpenRouter) | `OPENROUTER_API_KEY` | `ANTHROPIC_API_KEY` |
| Cerebras | `CEREBRAS_API_KEY` | `CEREBRAS_API` |
| Moonshot/Kimi | `MOONSHOT_API_KEY` | `KIMI_API_KEY` |
| Ollama Cloud | `OLLAMA_CLOUD_KEY` | — |

Standard names lifted directly from the TradingAgents README so the module
slots into any environment that already follows that convention.

### Bull-vs-bear by 2 different model families

To avoid same-model groupthink, the defaults pair providers from different
families:

- Bull thesis: **DeepSeek** (`deepseek-chat`)
- Bear thesis: **xAI Grok** (`grok-2-latest`)

Both overridable via `UEPS_ADVERSARIAL_BULL_PROVIDER` /
`UEPS_ADVERSARIAL_BEAR_PROVIDER`. Both prompts are short (≈40 tokens system,
~100 tokens user) and ask for strict JSON output with a `confidence` ∈ [0, 1].

### Tolerant JSON parser

LLMs habitually wrap JSON in markdown fences or prose. `_parse_thesis_json`
extracts the outermost `{...}` blob and gracefully falls through on garbage,
returning the raw text + 0.0 confidence rather than raising.

### Score + keep decision

```
adversarial_score = bull_confidence - bear_confidence  ∈ [-1, +1]
adversarial_keep  = (both sides answered) AND (score >= KEEP_MARGIN)
```

`KEEP_MARGIN` defaults to `0.15` (overridable via
`UEPS_ADVERSARIAL_KEEP_MARGIN`). If either provider errors, `adversarial_keep`
is False — we don't keep a pick on the strength of an unanswered debate.

### Sidecar contract: never crash the host

`apply_to_picks()` wraps every pick in `try/except Exception` and logs via
`logger.exception`. A transport meltdown or rate-limit cascade leaves the
host pipeline untouched.

## Default-OFF rationale

Per the CLAUDE.md Wire-Up Rule: "New integration modules must include at
least one caller in the production pick-generation or scoring path — or be
explicitly labeled opt-in with a wiring plan."

This PR ships **opt-in only**. No call site in production. Activation
requires:
1. `UEPS_ADVERSARIAL_ENABLED=1` in the cron environment.
2. API keys for both default providers (DeepSeek + xAI) under standard names
   or legacy fallbacks.

## Wiring plan (follow-up PR)

**Target caller:** `alpha_engine/long_term_pick_contract.py` —
`emit_long_term_picks()` immediately before final `picks.json` write.

**Shape:**
```python
from alpha_engine.adversarial_debate import apply_to_picks
picks = apply_to_picks(picks)  # no-op when env flag is off
# Optional: filter to picks where adversarial_keep is True
```

**Shadow-run protocol** (14 days):
- Stamp `bull_thesis`, `bear_thesis`, `adversarial_score`, `adversarial_keep`
  on every UEPS pick.
- Do NOT use `adversarial_keep` to drop picks during the shadow window —
  log only.
- After 30 closes (n>=30), compare:
  - WR delta vs baseline UEPS WR
  - Sharpe delta on Wilson-95% lower bound
  - Cost: ~60 LLM calls/day at Cerebras/DeepSeek pricing (≈$0.05/day)

**Acceptance for default-on flip (separate PR):**
- Sharpe-improvement positive on Wilson-95% lower bound, OR
- WR improvement ≥ 5pp on n>=30 closed at the same risk profile.

If neither lands by day 30, retire the sidecar with a documented null result.

## Reproducer

```bash
# Tests (no network)
python -m pytest tests/test_adversarial_debate.py -v

# Smoke (requires keys)
DEEPSEEK_API_KEY=$DEEPSEEK_API \
XAI_API_KEY=$X_AI_KEY \
UEPS_ADVERSARIAL_ENABLED=1 \
python -c "
from alpha_engine.adversarial_debate import score_pick
print(score_pick({
    'symbol': 'NVDA', 'asset_class': 'EQUITY', 'direction': 'LONG',
    'entry_price': 1100, 'take_profit': 1300, 'stop_loss': 1000,
    'thesis': 'AI capex cycle continues',
}))
"
```

## Risk classification: LOW

- Pure additive sidecar; no production caller.
- Default-off; no behavior change unless an operator sets the flag.
- All HTTP calls are to providers under operator-controlled keys.
- Sidecar swallows every exception; host pipeline cannot be broken by a
  provider outage.

## Out of scope

- Reflection loop (TradingAgents writes to `~/.tradingagents/memory/`) —
  redundant with `consecutive_loss_tracker.json` + per-strategy stats already
  surfaced on /audit.
- Risk-manager LLM gate — redundant with `passes_active_gate` and
  `pump_guard`.
- Anthropic native API path — current Anthropic route uses OpenRouter for
  OpenAI-compat. Direct `/v1/messages` shape can be added in a v2 if the
  provider becomes a default pick.
- Wire to `long_term_pick_contract.py` — separate PR after shadow-run
  validation.
