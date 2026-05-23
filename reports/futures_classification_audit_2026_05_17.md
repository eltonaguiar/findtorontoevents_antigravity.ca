# FUTURES Classification Audit — 2026-05-17

**Generated:** 2026-05-17  
**Source data:** `alpha_engine/data/closed_picks.json`  
**Trigger:** FUTURES shows WR=3%/n=203/PF=0.06 in dashboard — anomaly investigation.

---

## Summary

All 203 FUTURES picks originate from a single source: `multi_asset_copytrader`. This is a **strategy failure**, not a classification error. The symbols (commodity futures =F) are correctly classified as FUTURES per the `=F` suffix rule in `alpha_engine/asset_class.py` line 142. The WR=3% reflects `multi_asset_copytrader`'s catastrophic performance on these instruments.

---

## Source Breakdown

| source_system | n | wins | WR% |
|---|---|---|---|
| multi_asset_copytrader | 203 | 6 | 3.0% |

Single-source concentration: 100% of FUTURES picks come from `multi_asset_copytrader`.

---

## Direction Breakdown

| Direction | n | WR% |
|---|---|---|
| BUY (LONG) | 147 | 2.0% |
| SELL (SHORT) | 56 | 5.4% |

Both directions are catastrophic losers. Avg PnL ≈ −0.03% per pick.

---

## Top Symbols (FUTURES)

| Symbol | n | WR% | Notes |
|---|---|---|---|
| CT=F | 59 | 3.4% | Cotton |
| SI=F | 45 | 2.2% | Silver |
| HG=F | 33 | 0.0% | Copper |
| KC=F | 22 | 4.5% | Coffee |
| PL=F | 19 | 0.0% | Platinum |
| ZW=F | 15 | 13.3% | Wheat |
| GC=F | 10 | 0.0% | Gold |

---

## Classification Logic Analysis

**`alpha_engine/asset_class.py` line 142–143:**
```python
if sym.endswith("=F"):
    return "futures"
```

All =F symbols are unconditionally classified as FUTURES by symbol-suffix rule. This is the **correct behavior** — the =F suffix indicates a CME/CBOT futures contract.

**`_CAT_MAP` line 66:**
```python
"commodity": "futures", "futures": "futures",
```
Picks with `asset_class="commodity"` in the raw field also normalize to FUTURES. This is consistent.

---

## Cross-Class Symbol Comparison

The same symbols appear under COMMODITY class (from COT-based strategies), showing very different performance:

| Symbol | COMMODITY WR% | COMMODITY n | FUTURES WR% | FUTURES n |
|---|---|---|---|---|
| CT=F | 85.7% | 231 | 3.4% | 59 |
| ZW=F | 26.3% | 19 | 13.3% | 15 |
| KC=F | 25.0% | 4 | 4.5% | 22 |
| SI=F | 0.0% | 1 | 2.2% | 45 |

CT=F is WR=85.7% under COT strategies vs WR=3.4% under `multi_asset_copytrader`. The edge on commodity futures exists — it just requires COT-aware strategy signals, not copytrader signals.

---

## Root Cause Verdict

**Strategy failure, not classification error.**

`multi_asset_copytrader` is emitting picks on commodity futures symbols with no predictive edge (WR=3% across 203 picks, both directions, all symbols). The `=F` classification is correct. The strategy itself is the problem.

**Supporting context:**
- `multi_asset_copytrader` FOREX LONG was already blocked 2026-05-17 (M-063: WR=10.9%/n=603)
- FOREX symbol-level blocks exist for AUDJPY=X (WR=3.9%), CADJPY=X (WR=10.8%) in `BLOCKED_SOURCE_SYMBOL_PAIRS`
- FUTURES picks show zero edge across all symbols and both directions (BUY=2.0%, SELL=5.4%)

---

## Recommendation

**Block `multi_asset_copytrader` for FUTURES class (both directions).**

Add to `BLOCKED_DIRECTION_TRIPLES` in `audit_trail/quality_gates.py`:

```python
# 2026-05-17 FUTURES classification audit: multi_asset_copytrader on =F symbols
# BUY n=147 WR=2.0%, SELL n=56 WR=5.4% — no edge in either direction.
# Same symbols show WR=85.7% under COT strategies (COMMODITY class).
# Root cause: copytrader signal has no commodity futures edge.
("FUTURES", "multi_asset_copytrader", "LONG"),
("FUTURES", "multi_asset_copytrader", "SHORT"),
```

**Do NOT reclassify =F symbols to COMMODITY** — the FUTURES classification is correct. The edge difference is strategy-driven, not class-driven.

**Do NOT add `multi_asset_copytrader` to `BLOCKED_SOURCE_SYSTEMS`** without `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` — the FOREX SHORT side (WR=52.7%/n=93) retains edge and the non-JPY pairs have real edge. Direction+class kills are the correct surgical intervention.

---

## Files Referenced

- `alpha_engine/data/closed_picks.json` — source data
- `alpha_engine/asset_class.py` — classification logic (lines 66, 142–143)
- `audit_trail/quality_gates.py` — `BLOCKED_DIRECTION_TRIPLES`, `BLOCKED_SOURCE_SYMBOL_PAIRS`
- `reports/` — existing mutation docs for `multi_asset_copytrader` M-063
