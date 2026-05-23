# FIRING 8 - Patched Reference (Full Relevant Sections)
# This file shows exactly how the normalization logic in dashboard_generator.py
# will look after the tagging hygiene fix is applied.

# --- In the CFTC/COT branch (after the strategy default) ---

                if not p.get("strategy"):
                    p["strategy"] = "cftc_cot_commercial_signal"
                if not p.get("asset_class"):
                    p["asset_class"] = self._infer_asset_class(p.get("symbol", ""))  # FIXED
                if not p.get("timeframe"):
                    p["timeframe"] = "1w"

# --- In the penny_picks_latest.json branch (after the strategy default) ---

                if not p.get("strategy"):
                    p["strategy"] = "penny_stock_screener"
                if not p.get("asset_class"):
                    p["asset_class"] = self._infer_asset_class(p.get("symbol", ""))  # FIXED

# --- New helper method (add once, preferably near other private helpers) ---

    def _infer_asset_class(self, symbol: str) -> str:
        """Fail-loud, symbol-based asset class inference to stop the 90.8% pollution."""
        if not symbol:
            return "UNKNOWN"
        s = str(symbol).upper()
        if any(x in s for x in ("-USD", "USDT", "BTC", "ETH", "SOL", "DOGE", "AVAX", "LINK")) and \
           not any(x in s for x in ("AAPL", "TSLA", "NVDA", "GOOGL", "MSFT")):
            return "CRYPTO"
        if "=X" in s or any(x in s for x in ("EUR", "GBP", "USDJPY", "AUDUSD", "USDCHF")):
            return "FOREX"
        if any(x in s for x in ("SPY", "QQQ", "XLK", "XLV", "XLF", "TLT", "BND", "VNQ")):
            return "ETF"
        return "UNKNOWN"