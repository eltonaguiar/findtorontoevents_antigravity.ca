#!/usr/bin/env python3
"""Run by data-pipeline-test.yml: probe EnhancedDataFetcher and write data_source_health.json."""
import json
import os
import sys
from datetime import datetime


def summarize(symbol: str, df):
    if df is None:
        return {"success": False, "rows": 0, "latest": None, "error": "no data"}
    if len(df) == 0:
        return {"success": False, "rows": 0, "latest": None, "error": "empty frame"}
    return {"success": True, "rows": len(df), "latest": str(df.index[-1])}


def main():
    from data_fetcher_enhanced import EnhancedDataFetcher

    key = (os.environ.get("ALPHA_VANTAGE_KEY") or "").strip()
    fetcher = EnhancedDataFetcher(
        alpha_vantage_key=key if key else None,
        max_retries=5,
        base_delay=3.0,
    )

    results = {"tested_at": datetime.now().isoformat(), "sources": {}}

    for symbol in ("BTC/USDT", "ETH/USDT"):
        try:
            df = fetcher.fetch_crypto(symbol)
            results["sources"][symbol] = summarize(symbol, df)
        except Exception as e:
            results["sources"][symbol] = {"success": False, "error": str(e)}

    try:
        df = fetcher.fetch_forex("EUR/USD")
        results["sources"]["EUR/USD"] = summarize("EUR/USD", df)
    except Exception as e:
        results["sources"]["EUR/USD"] = {"success": False, "error": str(e)}

    out = "data_source_health.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=== DATA SOURCE HEALTH ===")
    for symbol, result in results["sources"].items():
        mark = "OK" if result.get("success") else "FAIL"
        rows = result.get("rows", 0)
        print(f"{mark} {symbol}: {rows} rows")
    print("===========================")

    ok_any = any(r.get("success") for r in results["sources"].values())
    sys.exit(0 if ok_any else 1)


if __name__ == "__main__":
    main()
