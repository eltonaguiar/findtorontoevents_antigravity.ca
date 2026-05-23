# B24 — Fix TradingAgents Rationale/Thesis Placeholder Bug (2026-05-01)

## Problem

Live `alpha_engine/data/tradingagents_picks.json` (empirically verified 2026-04-30
21:15 UTC) contained two picks with:

```json
"thesis": "Thesis text",
"rationale": "Rationale text"
```

The LLM was copying the template placeholder strings from the prompt verbatim
instead of generating real per-ticker analysis. Picks with placeholder text are
worthless for decision-making and pollute the dashboard's active-pick table.

## Root cause

The prompt used angle-bracket syntax for field descriptions:

```
"thesis": "<<= 2 sentences capturing the consensus view>"
```

Some LLM responses echoed these descriptions literally. The emitter had no guard
against placeholder text — it forwarded any non-empty string to the dashboard.

## Fix

### 1. Prompt hardening (`alpha_engine/tradingagents_emitter.py`)

Changed the field descriptions to be imperative and add an explicit "DO NOT copy"
instruction:

```
"thesis": "<WRITE 2 real sentences specific to THIS ticker's fundamentals/technicals — DO NOT copy example text>",
"rationale": "<WRITE 4 real sentences synthesizing bull vs bear case for THIS ticker — DO NOT copy example text>",
```

Added a final rule: `thesis and rationale MUST be ticker-specific real analysis, never template text.`

### 2. Placeholder reject guard in `_assemble_pick`

Added `_PLACEHOLDER_PATTERNS` frozenset and `_is_placeholder()` helper. If either
`thesis` or `rationale` matches any known placeholder string (case-insensitive,
after strip), `_assemble_pick` logs a warning and returns `None` — the pick is
counted in `skipped`, not `emitted`.

Known patterns: `"thesis text"`, `"rationale text"`, `"thesis here"`,
`"rationale here"`, `"your thesis here"`, `"your rationale here"`,
`"insert thesis"`, `"insert rationale"`, `"consensus view"`, `"<thesis>"`,
`"<rationale>"`, `"n/a"`, `""`.

### 3. Tests extended (`tests/test_tradingagents_emitter.py`)

19 new tests (B24 section):
- `test_assemble_rejects_placeholder_thesis` — 10 parametrized placeholder strings
- `test_assemble_rejects_placeholder_rationale` — 6 parametrized placeholder strings
- `test_assemble_accepts_real_thesis_and_rationale` — legitimate text passes
- `test_emit_picks_skips_placeholder_picks` — end-to-end: pick with placeholder text counts as skipped

All 36 tests (17 pre-existing + 19 new) pass.

## Files changed

| File | Change |
|---|---|
| `alpha_engine/tradingagents_emitter.py` | Add `_PLACEHOLDER_PATTERNS`, `_is_placeholder()`, placeholder check in `_assemble_pick`, hardened prompt |
| `tests/test_tradingagents_emitter.py` | 19 new tests |

## Wire-Up Rule

Wired: `_assemble_pick` is called inside `emit_picks` which is the production
pick-generation path. No opt-in needed.

## Related

- B25 (identical-metrics bug) is the companion fix; tracks whether the LLM is
  actually differentiating tickers in its metric outputs (conf/TP/SL all identical).
