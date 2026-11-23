#!/usr/bin/env python3
"""audit_total_return.py — which return computations use PRICE-ONLY (raw Close)?

CORRECTION 2026-11-23 (important): yfinance 1.3.0's `Ticker.history()` defaults to
`auto_adjust=None` which RESOLVES TO TRUE — so `history()["Close"]` is ALREADY adjusted
(verified: VTV first Close 27.32 adjusted vs 49.25 raw). An earlier version of this tool
wrongly flagged yfinance-default users as price-only. The GENUINELY price-only cases are:
  - explicit `auto_adjust=False`
  - raw Close from Stooq/custom CSV (unadjusted)
  - raw chart-API `quote[0]["close"]` (not `adjclose`)
This scans for THOSE in equity/etf/bond context; crypto/FX are exempt (no dividends).
"""
import subprocess, re, json
from pathlib import Path

EQUITY = re.compile(r"equity|stock|etf|dividend|fund|bond|reit|SPY|QQQ|VTV|VTI|TLT|IEF|GLD", re.I)
CRYPTO = re.compile(r"USDT|BTC|ETH|SOL|DOGE|binance|ccxt|crypto|coin", re.I)
RETURN = re.compile(r"pct_change|returns?\b|shift\(|cumprod", re.I)


def scan(root="."):
    raw = subprocess.run(["grep", "-rl", "--include=*.py", "-e", "auto_adjust=False",
                          "-e", 'row["Close"]', "-e", "quote\"][0][\"close\"]", "."],
                         cwd=root, capture_output=True, text=True).stdout.split()
    raw = [f for f in raw if "node_modules" not in f and "/.kilo/" not in f]
    rows = []
    for f in raw:
        try:
            t = (Path(root) / f).read_text(errors="ignore")
        except Exception:
            continue
        explicit_raw = "auto_adjust=False" in t
        raw_csv_close = bool(re.search(r'row\["Close"\]|row\[\'Close\'\]', t))
        raw_api_close = bool(re.search(r'quote"\]\[0\]\["close"\]', t))
        if not (explicit_raw or raw_csv_close or raw_api_close):
            continue
        crypto = bool(CRYPTO.search(t)); equity = bool(EQUITY.search(t)); ret = bool(RETURN.search(t))
        if crypto and not equity:
            status = "EXEMPT(crypto)"
        elif equity and ret:
            status = "EXPOSED"
        else:
            status = "REVIEW"
        rows.append({"file": f, "status": status, "explicit_auto_adjust_false": explicit_raw,
                     "raw_csv_close": raw_csv_close, "raw_api_close": raw_api_close})
    return rows


def main():
    rows = scan(".")
    from collections import Counter
    c = Counter(r["status"] for r in rows)
    out = {"rule": "EXPOSED = explicit auto_adjust=False OR raw CSV/chart-API Close, in equity return math",
           "total_price_only_candidates": len(rows), "by_status": dict(c),
           "exposed_files": sorted(r["file"] for r in rows if r["status"] == "EXPOSED"),
           "correction": "yfinance default history()['Close'] is ADJUSTED (auto_adjust None->True); NOT flagged here"}
    Path("reports/total_return_audit.json").write_text(json.dumps(out, indent=2) + "\n")
    print("price-only candidates:", len(rows), dict(c))
    for f in out["exposed_files"]:
        print("  EXPOSED", f)


if __name__ == "__main__":
    main()
