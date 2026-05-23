# ait_manus_composite — Design Note

**Date:** 2026-04-14
**Status:** Approved (fast-path after research findings)
**Source:** [.tmp-ai4trade/FINDINGS.md](../../../.tmp-ai4trade/FINDINGS.md) — reverse-engineered from `raftapart`/Manus AI strategy posts on ai4trade.ai

## What this is

A homegrown baby strategy that re-implements the Manus AI 4-factor composite scoring architecture observed on ai4trade.ai, using **our own data sources** instead of theirs. Every input is already wired in this repo. No ai4trade API call is ever made by this strategy.

## Architecture

```
score = w_ta · TA(symbol) + w_news · News(symbol) + w_macro · Macro() + w_community · Community(symbol)

signal = BUY        if score >=  4
        = LIGHT_SELL if score <= -2
        = NEUTRAL    otherwise
```

All four weights default to 1.0 (matching the observed Manus state). A future task can replace them with learned weights from our forward-validation pipeline. This module does not do the learning — it provides the composite and the threshold.

## Inputs

| Factor | Source module | Contribution to score |
|--------|----------------|------------------------|
| `TA` | RSI(14) computed from `df["Close"]` | `+3` if RSI<30; `+1` if <40; `0` if 40–60; `-1` if 60–70; `-3` if >70 |
| `News` | `alpha_engine.cryptopanic_feargreed.fetch_cryptopanic_news(currencies=symbol)` → `_classify_sentiment(votes)` | `+2` if positive; `0` neutral; `-2` negative |
| `Macro` | `regime_terminal/data/regime_state.json` → `market_overview.bull_count` vs `bear_count` | `+2` if bull_count > bear_count + 3; `-2` if bear_count > bull_count + 3; `0` otherwise |
| `Community` | `alpha_engine.lunarcrush_signal.get_lunarcrush_score(symbol)` → sentiment score 0–100 | `+2` if ≥70; `+1` if ≥55; `0` if 45–55; `-1` if ≤45; `-2` if ≤30 |

All factor functions are fault-tolerant: any missing input returns `0` for that factor rather than raising. The strategy degrades gracefully.

## Output

Standard baby-strategy `Signal` dataclass, same shape as `vwap_rsi_institutional`:

```python
Signal(
    symbol="BTCUSDT",
    direction="BUY",
    confidence=70,              # clamped 50..95 based on score magnitude
    entry_price=<current close>,
    take_profit=<current * 1.03>,
    stop_loss=<current * 0.985>,
    reason="manus score=6.0 TA=+3 news=+2 macro=+1 community=0",
)
```

TP/SL are fixed ratios (1.03 / 0.985). Not because Manus uses them — Manus never discloses exits — but because we need *some* exit to enter the forward-test pipeline. These can be tuned later; they're deliberately conservative.

## What this does NOT do

- **No scanner wiring.** This module lives in `baby_strategies/` but is NOT added to any `STRATEGIES` dict or imported by `scanner.py`. A human activates it by registering it in `antigravity_strategies.py` after reviewing this spec + the first dry-run output.
- **No backtest.** Per today's lessons: every in-sample backtest this repo has produced today has been contaminated (peek-ahead, no MHC, fake walk-forward, survivorship bias). I will not add another one. Forward-validation through the existing pipeline is the honest path.
- **No ai4trade API calls.** This is a reverse-engineer, not a copy-trader.
- **No weight learning.** Weights stay at 1.0 until a separate task decides how to learn them. The current Manus AI on ai4trade also has uniform 1.0 weights with zero evaluations, so we start even with them.

## Files

| File | Lines (est.) | Role |
|------|--------------|------|
| `baby_strategies/ait_manus_composite.py` | ~310 | Strategy class + factor helpers + `from_meta` loader |
| `baby_strategies/ait_manus_composite.meta.json` | ~40 | Attribution + runtime config block |
| `tests/test_ait_manus_composite.py` | ~280 | 32 unit tests covering factors, scoring, clamping, mtime cache, `from_meta` |

## meta.json schema

```jsonc
{
  "name": "ait_manus_composite",
  "category": "composite",
  "source": { /* attribution: platform, agent_id, method, research_note */ },
  "architecture": { /* factor descriptions + formula (audit only, not runtime) */ },
  "status": "draft — not wired into scanner; requires forward-validation before promotion",
  "created": "2026-04-14",
  "design_doc": "docs/superpowers/specs/2026-04-14-ait-manus-composite-design.md",
  "wired_in_scanner": false,
  "forward_test_started": null,
  "runtime": {
    "weights": {"ta": 1.0, "news": 1.0, "macro": 1.0, "community": 1.0},
    "buy_threshold": 4.0,
    "sell_threshold": -2.0
  }
}
```

`ManusCompositeStrategy.from_meta(path)` reads the `runtime` block. Missing fields fall back to module defaults. The attribution and architecture blocks are audit-only and ignored at runtime. A future weight-learning task updates `runtime.weights` in place and optionally appends a `runtime.learned_at` timestamp.

## Success criteria

- `py_compile` clean on the module.
- All unit tests green: factor isolation tests + composite scoring test + graceful-degrade tests (missing news, missing regime file, missing LunarCrush).
- Running `python -c "from baby_strategies.ait_manus_composite import ManusCompositeStrategy; print(ManusCompositeStrategy().scan_symbol(df, 'BTCUSDT'))"` against a live OHLCV frame returns a `Signal` or `None` without raising.
- Zero modifications to `scanner.py`, `config.py`, `antigravity_strategies.py` in the commit.

## Risk

- **News/LunarCrush modules hit free APIs.** Rate limits and occasional timeouts are expected. The fault-tolerant factor functions absorb this by returning 0 on failure.
- **Regime state file can be stale.** Read once per scan, timestamp-check; if older than 24h, the Macro factor is set to 0.
- **Inputs are equally weighted.** With `Total evaluations: 0`, there is no prior evidence this composite is profitable — even the original on ai4trade hasn't evaluated. This strategy enters our forward-validation pipeline as a hypothesis, not a proven alpha.

--INCEPTION FEEDBACK
**Overall Assessment**: The design captures the core composite scoring concept from Manus AI and adapts it to internal data sources, which is a solid foundation for a baby strategy. The clear separation of factor functions and fault‑tolerant defaults (returning 0 on missing data) ensures graceful degradation.

**Strengths**:
- **Modular factor design** – each input source (TA, News, Macro, Community) is encapsulated, making future weight‑learning integration straightforward.
- **Explicit thresholds** – the BUY/LIGHT_SELL/NEUTRAL logic is simple and easy to audit.
- **Testing plan** – unit tests for each factor and composite scoring are outlined, covering graceful‑degrade scenarios.

**Areas for Improvement**:
1. **Weight configurability** – expose `w_ta`, `w_news`, `w_macro`, `w_community` as configurable parameters (e.g., via a JSON meta file) so they can be tuned without code changes.
2. **Dynamic thresholds** – consider making the BUY/LIGHT_SELL thresholds configurable or derived from historical score distributions to avoid hard‑coded values.
3. **Signal enrichment** – the `reason` field currently hard‑codes a string; generate it programmatically from the factor contributions for better transparency.
4. **Performance monitoring** – add simple logging (e.g., `logging.info`) for each factor's contribution and any fallback to 0, to aid debugging in forward‑validation.
5. **Documentation consistency** – the file mentions a `meta.json` but does not describe its schema; a brief example would help future maintainers.

**Risk Mitigation Suggestions**:
- Implement a retry/back‑off mechanism for the News and Community APIs to reduce temporary data gaps.
- Cache the Macro regime state for the duration of a scan to avoid repeated file reads.
- Add a sanity check that the composite score is within expected bounds before mapping to a signal.

**Next Steps**:
- Update `baby_strategies/ait_manus_composite.meta.json` with weight fields.
- Refactor the scoring function to accept weight arguments (defaulting to 1.0).
- Extend unit tests to cover configurable thresholds and weight variations.

--END OF INCEPTION FEEDBACK

## Response to Inception (Mercury) feedback — 2026-04-14

| # | Mercury suggestion | Action | Notes |
|---|---|---|---|
| 1 | Weights configurable via meta.json | **Implemented** | Added `runtime.weights` block to meta.json and `ManusCompositeStrategy.from_meta(path)` classmethod. 3 new tests cover the loader, default fallback, and missing-file error. |
| 2 | Dynamic thresholds from historical distributions | **Declined** | Thresholds were already constructor-configurable. Deriving from historical score distributions requires a backtest layer — exactly the pattern we've been quarantining today after the peek-ahead / survivorship / no-MHC incidents. A learning task owns this later, not v1. |
| 3 | Signal enrichment — programmatic `reason` | **Already done (no-op)** | The existing `reason` field is programmatically generated from factor contributions: `f"manus score={score:.1f} TA={ta:+d} news={news:+d} macro={macro:+d} community={community:+d}"`. Mercury missed it on review. |
| 4 | Performance monitoring / logging | **Implemented** | Added `logger = logging.getLogger(__name__)` and debug-level logs in every factor function covering input validation, upstream failures, and score decisions. |
| 5 | Meta.json schema documentation | **Implemented** | Added the "meta.json schema" section above with a commented example and a note on what `from_meta` reads vs ignores. |
| Risk | Retry/back-off for News and Community APIs | **Declined** | Belongs in `cryptopanic_feargreed` and `lunarcrush_signal` themselves, not duplicated in every consumer. Adding it here would be DRY-violating. Filed as out-of-scope for this strategy. |
| Risk | Cache macro regime for scan duration | **Implemented** | Module-level `_regime_cache` keyed by `(path, mtime)`. Invalidates automatically when the HMM job rewrites the file. Test covers mtime-based cache-busting. |
| Risk | Sanity-check composite score bounds | **Implemented** | Defensive clamp at ±20 in `compute_score`, with a WARNING log when a raw score exceeds the bound. Catches runaway weight configurations. Test covers the clamp. |

**Test count:** 26 → 32 (all green).
