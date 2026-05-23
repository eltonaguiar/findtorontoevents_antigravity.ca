# FIRING 7 - Fixed Reference Version of dashboard_generator.py (relevant sections only)
# This is a reference file showing exactly what the fixed code would look like after applying the Firing 6/7 patches.
# It is NOT meant to be run directly — it is for engineering review and PR preparation.

# --- In the CFTC/COT normalization branch (around original line 8254) ---

                if not p.get("strategy"):
                    p["strategy"] = "cftc_cot_commercial_signal"
                if not p.get("asset_class"):
                    p["asset_class"] = self._infer_asset_class(p.get("symbol", ""))   # <-- FIXED
                if not p.get("timeframe"):
                    p["timeframe"] = "1w"

# --- In the penny_picks_latest.json normalization branch (around original line 8282) ---

                if not p.get("strategy"):
                    p["strategy"] = "penny_stock_screener"
                if not p.get("asset_class"):
                    p["asset_class"] = self._infer_asset_class(p.get("symbol", ""))   # <-- FIXED
                if parent_ts and not any(...):
                    p["generated_at"] = parent_ts

# --- New helper method added to the class (recommended location: near other private helpers) ---

    def _infer_asset_class(self, symbol: str) -> str:
        """Fail-loud, symbol-based asset class inference.
        Prevents the previous pollution where native crypto pairs were defaulted to EQUITY or FOREX.
        """
        if not symbol:
            return "UNKNOWN"
        s = str(symbol).upper()
        # Crypto native pairs (BTC-USD, ETH-USDT, SOL-USD, etc.)
        if any(x in s for x in ("-USD", "USDT", "BTC", "ETH", "SOL", "DOGE", "AVAX", "LINK")) and \
           not any(x in s for x in ("AAPL", "TSLA", "NVDA", "GOOGL", "MSFT")):
            return "CRYPTO"
        # Forex pairs (EUR-USD, GBPUSD=X, etc.)
        if "=X" in s or any(x in s for x in ("EUR", "GBP", "USDJPY", "AUDUSD", "USDCHF")):
            return "FOREX"
        # Major ETFs
        if any(x in s for x in ("SPY", "QQQ", "XLK", "XLV", "XLF", "TLT", "BND", "VNQ")):
            return "ETF"
        return "UNKNOWN"   # Fail loud — forces proper classification upstream