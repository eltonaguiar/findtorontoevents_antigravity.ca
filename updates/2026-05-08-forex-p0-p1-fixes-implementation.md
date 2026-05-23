# FOREX P0/P1 Fixes — Implementation Report
## May 8, 2026 | Buffy (Codebuff)

> **Source:** `docs/PERFORMANCE_DEEP_DIVE_MAY82026.md`  
> **Auditor:** Buffy + Theo the Theorizer (Gemini)  
> **Reviewer:** Nit Pick Nick (DeepSeek)

---

## Root Cause Summary

Non-crypto asset classes (FOREX PF 0.28, FUTURES, ETF, PENNY_STOCK) are trapped in a **data-integrity death spiral**: 100% of "closed" picks are marked as `phantom_expired` rather than properly resolved as TP_HIT/SL_HIT/TIME_EXIT. This corrupts all downstream metrics, triggering kill switches that disable good strategies and creating a feedback loop where no new picks survive to build clean forward history.

## Changes Applied

### File 1: `alpha_engine/forex_strategies.py` — TP/SL Hardcaps (P0-CRITICAL)

**Problem:** The `_forex_tp_sl()` function capped TP at 0.8% and SL at 0.5% of price, too tight for forex where spreads alone can be 0.1-0.2%. Good trades were hitting SL before spreads could be overcome.

**Fix:** Raised caps from 0.8%/0.5% → 1.5%/1.0% of price. Also raised individual strategy `tp_mult`/`sl_mult` for key strategies:

| Strategy | Old TP | Old SL | New TP | New SL |
|----------|--------|--------|--------|--------|
| `_forex_tp_sl` (default) | 2.0x ATR / 0.8% cap | 1.5x ATR / 0.5% cap | 2.0x ATR / 1.5% cap | 1.5x ATR / 1.0% cap |
| `forex_rsi2_mean_reversion` | 1.5x / 1.0x | 1.5x / 1.0x | 2.0x / 1.5x | 2.0x / 1.5x |
| `forex_bb_squeeze_breakout` | 2.0x / 1.5x | 2.0x / 1.5x | 2.5x / 2.0x | 2.5x / 2.0x |

**Reviewer note:** RSI2 stop at 2.0x ATR is wider than academic baseline (Connors & Alvarez use 1.0-1.5x). Intentionally aggressive to overcome the phantom-expired feedback loop. Monitor and tighten if forward results show excess drawdown.

### File 2: `alpha_engine/fx_kill_switch.py` — Remove False Positives (P1)

**Problem:** `forex_rsi2_mean_reversion` and `myfxbook_retail_contrarian` were in `_KNOWN_TOXIC_FOREX_STRATEGIES` based on metrics computed from 100% phantom-expired data.

**Fix:** Commented out both entries from the frozenset with TEMP UNBLOCKED annotations.

```python
_KNOWN_TOXIC_FOREX_STRATEGIES = frozenset({
    # "forex_rsi2_mean_reversion",   # TEMP UNBLOCKED 2026-05-08 — phantom-expired data
    # "myfxbook_retail_contrarian",  # TEMP UNBLOCKED 2026-05-08 — phantom-expired data
    "community_london_breakout_v2_forex",
})
```

### File 3: `audit_trail/quality_gates.py` — Unblock Falsely-Killed Strategies (P1)

**Changes applied:**

1. **`forex_rsi2_mean_reversion`** — Commented out of `PERMANENTLY_KILLED_STRATEGIES` (line 874). Academic baseline: 68% WR (Connors & Alvarez 2008). Current 43.3% WR / PF 0.37 computed on phantom-expired data.

2. **`myfxbook_retail_contrarian`** — Commented out of `BLOCKED_ASSET_STRATEGY_PAIRS` (line 1493). Retail sentiment contrarian has documented edge on forex.

3. **`ig_contrarian_sentiment, LONG`** — Commented out of `BLOCKED_DIRECTION_TRIPLES` (line 1566). Sharpe 5.87; was blocked on phantom data.

4. **`myfxbook_retail_contrarian, LONG`** — Commented out of `BLOCKED_DIRECTION_TRIPLES` (line 1567).

5. **`forex_carry_momentum`** — Commented out of `BLOCKED_ASSET_STRATEGY_PAIRS` (line 1526). 0% WR on non-JPY n=8 was based on phantom-expired data.

6. **JPY_CROSS_BUY_KILL** — Added default-disabled comments (lines 948-951). The -45.43% 30d loss was computed on phantom-expired data.

### Re-evaluation Deadlines

All TEMP UNBLOCKED entries carry: **"Re-evaluate by 2026-05-22 or when phantom_expired < 10%."**

## Verification

- ✅ All 3 files pass `py_compile` syntax check
- ✅ Code reviewer (DeepSeek) confirmed logic is sound
- ✅ `_KILLED_STRATEGIES_LOWER` is recomputed after `PERMANENTLY_KILLED_STRATEGIES` modification
- ✅ Frozenset syntax in `fx_kill_switch.py` is valid Python

## Pending (Phase 2)

These fixes unblock strategies that were killed on bad data. To close the loop:

1. **Fix the resolver** — The `lm_signals_resolver` shows 96.21% of expired picks have `no_resolve`. Non-crypto picks need the same TP/SL resolver that crypto uses.
2. **Monitor forward WR** — After 14 days of live trading with these unblocks, re-evaluate each strategy against clean forward data.
3. **Consider RSI2 stop tightening** — If forward results show the 2.0x ATR stop is too wide, dial back to 1.5x.

## Related

- `docs/PERFORMANCE_DEEP_DIVE_MAY82026.md` — Full analysis
- `updates/2026-05-06-forex-mutation-decisions.md` — Mutation decisions that led to some of these kills
- `updates/2026-05-06-day2-audit-kills.md` — Day-2 audit that killed several forex strategies
