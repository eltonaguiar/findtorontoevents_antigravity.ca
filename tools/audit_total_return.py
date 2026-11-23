#!/usr/bin/env python3
"""audit_total_return.py — which price-return computations use raw Close (dividend-omitting)?

A raw Close feed erases dividends. That is harmless for crypto/FX (no dividends) but
understates EQUITY/ETF/BOND returns by ~2-4%/yr (VTV +2.78, DVY +3.78 measured). This scans
the repo for files that index ["Close"] WITHOUT auto_adjust/Adj Close, and classifies each as
'exempt' (crypto/fx-only) or 'exposed' (equity/etf/bond/fund context) so the real blast radius
is visible. Heuristic classifier — for triage, not a verdict.
"""
import subprocess, re, json
from pathlib import Path

CRYPTO = re.compile(r"USDT|BTC|ETH(?:USD)?|SOL|DOGE|binance|ccxt|crypto|coin", re.I)
EQUITY = re.compile(r"SPY|QQQ|VOO|VTI|VTV|DVY|VBR|GLD|TLT|IEF|SHY|stock|equity|\betf\b|dividend|fund|\bbond\b|reit|yfinance|yf\.Ticker", re.I)
RETURN = re.compile(r"pct_change|returns?\b|shift\(|cumprod|\bret\b|/ *close|np\.log", re.I)


def files_using_close(root="."):
    out = subprocess.run(["grep", "-rl", "--include=*.py", "-e", '["Close"]', "-e", "['Close']", "."],
                         cwd=root, capture_output=True, text=True).stdout.split()
    return [f for f in out if "node_modules" not in f and "/.kilo/" not in f]


def classify(root="."):
    rows = []
    for f in files_using_close(root):
        p = Path(root) / f
        try:
            t = p.read_text(errors="ignore")
        except Exception:
            continue
        if '["Close"]' not in t and "['Close']" not in t:
            continue
        adjusted = ("auto_adjust=True" in t) or ("Adj Close" in t) or ("adjclose" in t)
        if adjusted:
            continue  # OK
        crypto = bool(CRYPTO.search(t)); equity = bool(EQUITY.search(t)); ret = bool(RETURN.search(t))
        if ret and equity and not (crypto and not equity):
            status = "EXPOSED"     # equity/etf/bond return math on raw Close
        elif crypto:
            status = "EXEMPT(crypto)"
        else:
            status = "REVIEW"
        rows.append({"file": f, "status": status, "crypto": crypto, "equity": equity, "return_math": ret})
    return rows


def main():
    rows = classify(".")
    from collections import Counter
    c = Counter(r["status"] for r in rows)
    out = {"total_raw_close_no_adjust": len(rows), "by_status": dict(c),
           "exposed_files": sorted(r["file"] for r in rows if r["status"] == "EXPOSED"),
           "review_files": sorted(r["file"] for r in rows if r["status"] == "REVIEW")[:60],
           "measured_drag_pct": {"SPY": 1.94, "VTV": 2.78, "DVY": 3.78, "VBR": 2.23},
           "note": "EXPOSED = raw-Close return math in equity/etf/bond context; each understates by ~2-4%/yr."}
    Path("reports/total_return_audit.json").write_text(json.dumps(out, indent=2) + "\n")
    print("raw-Close-without-adjust files:", len(rows))
    for k, v in c.most_common():
        print(f"  {k}: {v}")
    print("\nfirst 12 EXPOSED:")
    for f in out["exposed_files"][:12]:
        print("  ", f)


if __name__ == "__main__":
    main()
