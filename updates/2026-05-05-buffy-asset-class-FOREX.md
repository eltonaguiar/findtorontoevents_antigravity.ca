# FOREX Asset Class Audit — Buffy
**Agent:** Buffy (Codebuff) | **Date:** 2026-05-05  
**Class Status:** STRESSED (WR 45.6% | PF <0.3 | n=1,169 total | **-986.27% cum PnL**)

---

## ⚠️ DATA INTEGRITY WARNING

**FOREX shows -986% total PnL but recent performance is POSITIVE:**

| Window | WR | PnL | n |
|--------|-----|-----|---|
| Total (7,645 closed) | 45.6% | **-986.27%** | 1,169 |
| Recent (3,500 closed) | **47.9%** | **+14.07%** | 883 |

**286 old FOREX trades are responsible for ~-1,000% PnL.** Recent FOREX is slightly profitable. The dashboard's `asset_class_health` aggregates ALL history, misleading operators into thinking FOREX is currently bleeding.

## Corrupted Outcome Rows

`quality_gates.py:CORRUPTED_OUTCOME_ROWS` identifies 3 fake FOREX entries:
- `USDCAD=X` — +40.45% PnL (impossible for unleveraged spot FX)
- `EURUSD=X` — +66.76% PnL (impossible)
- `AUDUSD=X` — +95.58% PnL (impossible)

All have `confidence=9.9999` (should be [0,1]) and `id=MISSING`. These inflate FOREX aggregate. **Must be deduplicated at resolver level.**

## Worst FOREX Symbols

| Symbol | WR | n | Cum PnL |
|--------|-----|---|---------|
| EURJPY=X | 32.2% | 87 | **-16.75%** |
| USDJPY=X | 51.1% | 88 | -2.94% |
| CADJPY=X | 50.0% | 64 | -0.69% |

JPY-cross pairs are the main bleeders. `quality_gates.py` already has `JPY_CROSS_PAIRS` frozenset with BUY-direction kill — verify it's enforced.

## Specific Fixes

1. **Deduplicate 3 corrupted outcome rows** — root cause: `universal_pick_resolver.py` make_pick_id() doesn't include entry_price in composite key
2. **Show split FOREX metrics** — total vs recent on dashboard to prevent panic from old data
3. **Investigate the 286 old FOREX trades** — what timeframe? What strategies? Can they be quarantined?
4. **Verify JPY_CROSS_BUY_KILL is enforced** — default-on per quality_gates.py, check `JPY_CROSS_BUY_KILL_DISABLED` env var
5. **Add FOREX score booster enrichment** — currently crypto-only (MTF + ensemble gates have crypto-only guards). Parity would help surface real FOREX edge.

## Recent FOREX Performance (The Good News)

Recent FOREX (883 trades) is net positive at +14.07% with 47.9% WR. Top strategies:
- `multi_asset_copytrader`: 45.0% WR, n=576 — workhorse
- `signal_validation`: 53.3% WR, n=15 — efficient but small sample
- `forex_copy_trader`: 57.9% WR, n=38 — profitable

**Conclusion:** FOREX is not currently dying — it's recovering from a catastrophic historical period. Focus on preventing old-trade contamination in aggregates.
