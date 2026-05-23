#!/usr/bin/env python3
"""
Firing 10 — Quick Pre-Hygiene Pollution Analyzer
================================================
Run this (or an equivalent) before and after the tagging hygiene patch + backfill
to quantify the 90.8% CRYPTO-in-EQUITY problem.

Example:
    python FIRING10_CURRENT_POLLUTION_ANALYZER_2026-05-21.py --input audit_dashboard/data/dashboard_data.json
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

CRYPTO_PATTERN = re.compile(r'(-USD|USDT|USDC|BTC|ETH|SOL|DOGE|AVAX|LINK)')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text())
    picks = data.get("picks", []) or data.get("data", []) or []

    total = len(picks)
    equity_tagged = [p for p in picks if (p.get("asset_class") or "").upper() == "EQUITY"]
    crypto_looks_like_equity = [p for p in equity_tagged if CRYPTO_PATTERN.search(str(p.get("symbol", "")).upper())]

    print(f"Total picks in file: {total}")
    print(f"Tagged EQUITY: {len(equity_tagged)}")
    print(f"CRYPTO symbols tagged as EQUITY: {len(crypto_looks_like_equity)}")
    if equity_tagged:
        print(f"Pollution rate among EQUITY-tagged: {len(crypto_looks_like_equity)/len(equity_tagged)*100:.1f}%")
    print("Example polluted symbols:", [p.get("symbol") for p in crypto_looks_like_equity[:5]])

if __name__ == "__main__":
    main()