# Firing 10 — Minimal Hygiene Merge Diff for dashboard_generator.py (P0)

**Date:** 2026-05-21 (Firing 10 of continual 6-gate research loop)  
**Purpose:** Provide the smallest, exact, safe diff that engineering can apply to eliminate the two hardcoded defaults causing the 90.8% CRYPTO-in-EQUITY pollution.

**Based on:**
- FIRING8_DASHBOARD_GENERATOR_PATCHED_REFERENCE_2026-05-21.py (the _infer_asset_class helper)
- FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py (same logic)
- Exact current code at dashboard_generator.py:8254-8255 and 8281-8282

## The Two Changes (Minimal)

### Change 1 — CFTC / COT branch (around line 8254)

```diff
                 if not p.get("strategy"):
                     p["strategy"] = "cftc_cot_commercial_signal"
-                if not p.get("asset_class"):
-                    p["asset_class"] = "FOREX"
+                if not p.get("asset_class"):
+                    p["asset_class"] = self._infer_asset_class(p.get("symbol", ""))
                 if not p.get("timeframe"):
                     p["timeframe"] = "1w"
```

### Change 2 — Penny picks branch (around line 8281)

```diff
                 if not p.get("strategy"):
                     p["strategy"] = "penny_stock_screener"
-                if not p.get("asset_class"):
-                    p["asset_class"] = "EQUITY"
+                if not p.get("asset_class"):
+                    p["asset_class"] = self._infer_asset_class(p.get("symbol", ""))
                 if parent_ts and not any(
```

## Add the Helper Method (once, near other private helpers)

Insert the following method (copy from FIRING8 patched reference, expanded for robustness):

```python
    def _infer_asset_class(self, symbol: str) -> str:
        """Fail-loud, symbol-based asset class inference.
        Replaces the two dangerous hardcoded defaults at 8255 and 8282.
        """
        if not symbol:
            return "UNKNOWN"
        s = str(symbol).upper().strip()

        # CRYPTO (native pairs) — highest priority to stop 90.8% pollution
        crypto_markers = ("-USD", "USDT", "USDC", "BTC", "ETH", "SOL", "DOGE", "AVAX", "LINK", "ADA", "XRP", "HBAR", "NEAR")
        equity_exempt = ("AAPL", "TSLA", "NVDA", "GOOGL", "MSFT", "AMZN", "META", "NFLX")
        if any(x in s for x in crypto_markers) and not any(x in s for x in equity_exempt):
            return "CRYPTO"

        # FOREX
        if s.endswith("=X") or any(x in s for x in ("EUR", "GBP", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD")):
            return "FOREX"

        # COMMODITY / FUTURES
        commodity_markers = ("GC=F", "SI=F", "HG=F", "NG=F", "CL=F", "CT=F", "OJ=F", "KC=F", "ZB=F", "ZN=F", "ES=F", "NQ=F")
        if any(m in s for m in commodity_markers) or s in ("GC", "CL", "NG", "SI", "HG"):
            return "COMMODITY"

        # ETF (sector SPDRs, broad, bonds)
        etf_markers = ("SPY", "QQQ", "XLK", "XLV", "XLF", "XLE", "XLY", "XLB", "XLP", "XLU", "XLRE", "XLC", "TLT", "BND", "VNQ", "IWM", "DIA", "EFA", "EEM")
        if any(m in s for m in etf_markers):
            return "ETF"

        # EQUITY (conservative fallback for obvious tickers)
        if len(s) <= 5 and s.isalpha() and not any(c in s for c in ("=", "-", "/")):
            return "EQUITY"

        return "UNKNOWN"
```

## Additional Recommended (but not strictly minimal) Sites

After this core change in dashboard_generator.py, the same pattern should be applied or verified in:
- `KIMI_RISEOFTHECLAW/signal_tracker.py` (emitter)
- `audit_trail/quality_gates.py:5598` (remove or condition the erroneous EQUITY score bonus)
- `universal_pick_resolver.py` (add validation guard)

The FIRING7_TAGGING_HYGIENE_PR_SCOPE_2026-05-21.md and FIRING9 backfill script already list these.

## Verification After Merge

```bash
python reports/continual_research/6gate_validation/pending_fresh_backtest/FIRING9_TAGGING_BACKFILL_SCRIPT_2026-05-21.py --input ... --dry-run
python tools/validate_resolved_picks.py --by-asset-class --min-trades 10
# Expect: sharp drop in "EQUITY" crypto pollution, rise in clean CRYPTO and ETF counts, zero -USD symbols in EQUITY bucket.
```

This diff is the smallest possible change that eliminates the root cause while preserving all existing behavior for correctly tagged items.

**Ready for engineering handoff.** Combine with the already-created FIRING9 backfill script for the full P0 fix.