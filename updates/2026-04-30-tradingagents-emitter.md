# 2026-04-30 — TradingAgents-style stock-pick emitter

## What this PR does

Adds a producer that emits stock picks under `source_system='tradingagents'`,
inspired by [tauricresearch/tradingagents](https://github.com/tauricresearch/tradingagents)
(Apache-2.0). Picks surface under **active_picks** on `/audit` once the cron
runs. Strategy attribution: `tradingagents_consensus`.

## Why this approach (and not a wholesale TradingAgents import)

The upstream repo uses LangGraph + per-role LLMs (4 analysts × 2 researchers
× trader × risk-mgr × PM = ~8 LLM calls per ticker, often Sonnet/Opus tier).
For a 40-ticker watchlist that's 320 calls per emit run — roughly $1–$3 per
run on premium models.

This emitter captures the same multi-perspective decision committee pattern
in **a single consolidated prompt** that asks one LLM to internally play
every role and emit a single consensus JSON. ~40 calls per run on
DeepSeek/Cerebras/Grok pricing ≈ **$0.05–$0.20 per emit cycle**.

The Wire-Up Rule (CLAUDE.md) is honored: this PR DOES wire the picks file
into `dashboard_generator.JSON_PICK_SOURCES` so the producer reaches /audit
the moment it runs. The producer itself is opt-in
(`TRADINGAGENTS_EMITTER_ENABLED=1`) — when off, the JSON is never written
and the source appears with 0 picks (graceful no-op).

## Files

| File | Purpose |
|---|---|
| `alpha_engine/tradingagents_emitter.py` | New producer (~280 LOC) |
| `alpha_engine/data/tradingagents_watchlist.json` | Default 40-ticker mega-cap watchlist (editable) |
| `tests/test_tradingagents_emitter.py` | 18 tests, no live LLM calls |
| `audit_trail/dashboard_generator.py` | +1 line: register `tradingagents` source |
| `updates/2026-04-30-tradingagents-emitter.md` | This doc |

## Pick schema

The emitter writes a JSON file with `active_picks: [...]` (the shape
`_extract_picks` in dashboard_generator already accepts). Each pick:

```jsonc
{
  "id":            "tradingagents::NVDA::202604301830",
  "strategy":      "tradingagents_consensus",
  "source_system": "tradingagents",
  "symbol":        "NVDA",
  "asset_class":   "EQUITY",
  "category":      "equity",
  "signal_type":   "BUY",                 // or "SELL"
  "direction":     "LONG",                // or "SHORT"
  "entry_price":   null,                  // resolver fills from live yfinance
  "take_profit_pct": 11.0,
  "stop_loss_pct":   5.0,
  "score":           82,                  // confidence * 100
  "confidence":      0.82,
  "thesis":          "<<= 2 sentences>",
  "rationale":       "<<= 4 sentences>",
  "time_horizon_days": 21,
  "key_risks":       ["valuation", "..."],
  "timestamp":       "2026-04-30T18:30:00+00:00",
  "status":          "OPEN",
  "source_tier":     "EXPERIMENTAL",
  "tradingagents_version": "v1-consolidated-prompt"
}
```

## Decision committee prompt

The system prompt asks the LLM to internally play 9 roles in order
(Fundamentals → Technical → News → Sentiment → Bull researcher → Bear
researcher → Trader → Risk Manager → Portfolio Manager) and emit a single
JSON object. Hard rules baked into the prompt:

- BUY only on strong multi-role agreement; default HOLD on conflict.
- `target_pct >= stop_pct * 1.5` (positive risk-reward).
- `confidence >= 0.65` for trade-worthy conviction (configurable).

Picks below the floor or with HOLD action are dropped — they don't reach the
output JSON. The dashboard never sees them, so the active book stays clean.

## Provider selection

Reuses the registry from `alpha_engine.adversarial_debate` (PR #543). One
LLM call per ticker. Default: **DeepSeek** (`deepseek-chat`). Override via:

```bash
TRADINGAGENTS_PROVIDER=xai            # any provider name in adversarial_debate._PROVIDERS
TRADINGAGENTS_MODEL=grok-2-latest     # optional; uses provider default otherwise
```

Standard env vars from the TradingAgents README work directly:
`OPENAI_API_KEY`, `XAI_API_KEY`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`,
`ANTHROPIC_API_KEY` (via OpenRouter route). Legacy fallbacks honored.

## How to run TODAY

```bash
# Sanity check (no LLM calls)
python -m alpha_engine.tradingagents_emitter --dry-run

# Actual emit — writes alpha_engine/data/tradingagents_picks.json
TRADINGAGENTS_EMITTER_ENABLED=1 \
DEEPSEEK_API_KEY=$DEEPSEEK_API \
python -m alpha_engine.tradingagents_emitter

# Then re-run the dashboard generator and the picks appear under
# source_system='tradingagents' on /audit:
python audit_trail/dashboard_generator.py    # do NOT run locally if it overwrites
                                              # live HTML — see CLAUDE.md
```

The emitter is also safe to schedule from cron / GitHub Actions; the
existing audit-dashboard cron will pick up the JSON on its next run with no
changes needed there.

## Risk classification: LOW–MEDIUM

- Producer adds a new `source_system` label, NOT a new gate or scoring
  change. Picks flow through the existing `_normalize_pick` →
  `passes_active_gate` pipeline like every other source.
- All emitted picks land under `source_tier="EXPERIMENTAL"` so the leaderboard
  treats them as un-promoted until they accrue closed-trade history.
- Default-off; the JSON file is absent until an operator runs the emitter
  with the env flag set. `_safe_json` returns None for missing files — no
  loader-side breakage.
- Wire-up to `JSON_PICK_SOURCES` is unconditional (no env-flag guard) so the
  source registers even when 0 picks are present, keeping
  `_FRESHNESS_REQUIRED_HOURS` and per-source counters consistent.

## Out of scope (deliberately)

- LangGraph / TradingAgents framework import — heavy dep with redundant
  modules vs. existing `alpha_engine/`.
- Reflection loop (TradingAgents writes to `~/.tradingagents/memory/`) —
  redundant with `consecutive_loss_tracker.json`, per-strategy stats, and
  the audit dashboard's leaderboard.
- Multi-agent per-role calls (the "deep" mode). v1 is single-call. A v2
  could add `TRADINGAGENTS_MODE=deep` to fire 3–4 LLM calls per ticker
  (Fundamentals/Technical/News/Sentiment in parallel, then Bull/Bear, then
  PM) for higher cost / nuance.
- Closed-trade emission. Outcomes settle through the universal resolver
  (`alpha_engine/outcome_resolver.py`) on whatever take-profit / stop-loss
  the live resolver computes from `take_profit_pct` / `stop_loss_pct` plus
  the fetched entry price.

## Acceptance criteria for default-on flip (separate PR, after first 30 closes)

- WR ≥ 50% on n ≥ 30 closed `tradingagents_consensus` picks.
- Sharpe-improvement vs SPY benchmark positive on Wilson-95% lower bound.
- Cost-per-pick (LLM calls × provider price) below $0.01 amortized over
  closes.

If neither lands by day 30, retire the source via `BLOCKED_SOURCE_SYSTEMS`
with a documented null result per `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

## Test plan

- [x] `pytest tests/test_tradingagents_emitter.py tests/test_adversarial_debate.py` → **37/37 pass** locally
- [x] `python -m alpha_engine.tradingagents_emitter --dry-run` → loads watchlist, prints flag status
- [x] `python -m py_compile audit_trail/dashboard_generator.py` clean
- [ ] Reviewer enables flag with a small watchlist (e.g. NVDA only) + DeepSeek key, runs emit, inspects the output JSON, confirms picks render on /audit after dashboard regen
