# B25 — TradingAgents identical-metrics fix
**Date:** 2026-05-01 | **Branch:** fix/tradingagents-identical-metrics-b25-2026-04-30

## Problem

Both NVDA and SOFI picks from the TradingAgents emitter showed identical
`confidence=0.86`, `take_profit_pct=12%`, `stop_loss_pct=5%`. The LLM
returned round default values without differentiating between tickers.

**Root cause:** The SYSTEM_PROMPT did not explicitly discourage round defaults
for numeric fields. Without real-time market data, the LLM defaults to
"typical" values. There is currently no multi-provider adjudication — each
ticker gets one LLM call, so the identical output was the same model
defaulting on both calls.

## Changes

| File | Change |
|------|--------|
| `alpha_engine/tradingagents_emitter.py` | (1) Prompt hardening rule added; (2) batch dedup WARNING; (3) `ENV_DEBUG_RAW` + debug logging |
| `tests/test_tradingagents_emitter.py` | 4 new B25 regression tests |
| `reports/feedback/B25-*.md` | 2× multi-AI feedback (§5 protocol) |

## Details

### 1. Prompt hardening (SYSTEM_PROMPT)

Added rule:
> "confidence, target_pct, and stop_pct MUST reflect THIS ticker's specific
> risk profile. Do NOT use round defaults (e.g. 0.80, 10.0, 5.0). If your
> analysis produces the same numbers as a prior ticker, reconsider —
> identical metrics across different tickers indicate insufficient
> per-ticker analysis."

### 2. Batch dedup warning (emit_picks)

After all picks are assembled, if 2+ picks share the same
`(round(conf,2), round(tp,1), round(sl,1))` tuple, a WARNING is logged:

```
[tradingagents] identical (conf, tp, sl) metrics across 3 picks: {(0.86, 12.0, 5.0): 3}
— LLM may not be differentiating tickers. Set TRADINGAGENTS_DEBUG_RAW=1 to log raw responses.
```

The picks are NOT rejected — the warning is informational so the operator
can diagnose the issue without losing valid picks.

### 3. Debug raw logging

`TRADINGAGENTS_DEBUG_RAW=1` enables `logger.debug` of raw LLM responses
per ticker in `call_tradingagents()`. Useful for diagnosing prompt issues
in production.

## Tests (4 new, all pass)

1. `test_distinct_metrics_across_tickers` — 3 tickers with distinct mock
   responses produce 3 distinct (conf, TP, SL) tuples
2. `test_identical_metrics_logs_warning` — all-same response triggers
   WARNING (verified via caplog)
3. `test_prompt_hardening_line_present` — SYSTEM_PROMPT contains
   anti-default instruction
4. `test_debug_raw_env_var_defined` — `ENV_DEBUG_RAW` constant defined

## Queue item

B25 from `reports/REMAINING_ACTION_ITEMS_2026_04_30.md` (Order 30).
Prereq: B24 ✅ (merged 2026-05-01 21:20 UTC).
Unlocks: B26 (TradingAgents end-to-end smoke test).
