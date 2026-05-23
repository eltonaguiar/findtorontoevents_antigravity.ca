# B25 — TradingAgents identical-metrics bug: Multi-AI Feedback #1
## AI: Claude Sonnet 4.6 | Date: 2026-05-01

---

## A. Confirmed assumptions

1. **Root cause identified.** Both NVDA and SOFI picks showed `conf=0.86`,
   `TP=12%`, `SL=5%` because the LLM defaulted to round "typical" values
   without real per-ticker market data. There is currently NO multi-provider
   adjudication in `call_tradingagents()` — it calls `_post_chat()` once
   with a single provider per ticker. The "adjudication" in the B25 doc
   refers to a future state; the current bug is purely a prompt regression.

2. **File paths correct.** `alpha_engine/tradingagents_emitter.py` contains
   both `SYSTEM_PROMPT` and `emit_picks()`. `alpha_engine/adversarial_debate.py`
   provides `_post_chat`, `DebateError`, `_extract_content` — none of these
   need changes for B25.

3. **B24 prerequisite satisfied.** B24 (placeholder text guard) merged at
   21:20:45 UTC 2026-05-01. The `_is_placeholder()` guard is live.

4. **Wire-Up Rule satisfied.** Changes are entirely within existing
   production code paths — no new module, no opt-in needed.

---

## B. Surfaced contradictions / blockers

1. **B25 description assumes multi-provider adjudication.** The doc says
   "If providers differ but adjudication averages to a fixed point, fix
   adjudication." But `call_tradingagents()` currently uses ONE provider.
   The root cause is simpler: the SYSTEM_PROMPT doesn't explicitly
   discourage round defaults for numeric fields.

2. **Cannot test with real LLM in CI.** The `--debug-raw` / ENV_DEBUG_RAW
   flag is the right diagnostic; the batch dedup WARNING provides the
   production signal without requiring a live LLM call in tests.

---

## C. Recommended deltas

1. **Prompt fix**: Add to SYSTEM_PROMPT Rules: "confidence, target_pct, and
   stop_pct MUST reflect THIS ticker's specific risk profile. Do NOT use
   round defaults (e.g. 0.80, 10.0, 5.0). Identical metrics across
   different tickers indicate insufficient per-ticker analysis."

2. **Batch dedup warning**: In `emit_picks()`, after all picks assembled,
   Counter the `(round(conf,2), round(tp,1), round(sl,1))` tuples. Log
   WARNING if any tuple appears 2+ times.

3. **Debug raw env**: Add `ENV_DEBUG_RAW = "TRADINGAGENTS_DEBUG_RAW"` +
   `logger.debug(raw_response)` in `call_tradingagents()`.

4. **Tests**: Add 4 B25 tests to `tests/test_tradingagents_emitter.py`:
   - distinct_metrics: 3 tickers with distinct responses → 3 distinct tuples
   - identical_metrics_warning: all same response → WARNING in logs
   - prompt_hardening_line_present: assert anti-default text in SYSTEM_PROMPT
   - debug_raw_env_var_defined: assert ENV_DEBUG_RAW constant

---

## D. Net verdict: ready-to-ship

3 targeted changes to `tradingagents_emitter.py` + 4 tests.
Risk: LOW (prompt hardening + warning log, no gate change).
