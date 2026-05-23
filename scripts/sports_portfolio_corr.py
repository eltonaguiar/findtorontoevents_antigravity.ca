#!/usr/bin/env python3
"""
Pivot daily PnL from sports_forensics.php?action=daily_returns JSON into sport columns
and print a simple Pearson correlation matrix (offline analysis).

Usage:
  curl -s "https://example.com/live-monitor/api/sports_forensics.php?action=daily_returns" \\
    | python scripts/sports_portfolio_corr.py

Requires: Python 3.8+ with urllib if fetching URL yourself; stdin expects JSON with daily_rows.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        print("No JSON on stdin.", file=sys.stderr)
        sys.exit(1)
    data = json.loads(raw)
    rows = data.get("daily_rows") or []
    by_date: dict[str, dict[str, float]] = defaultdict(dict)
    sports: set[str] = set()
    for r in rows:
        d = str(r.get("date") or "")
        short = str(r.get("sport_short") or r.get("sport") or "UNK")
        sports.add(short)
        by_date[d][short] = by_date[d].get(short, 0.0) + float(r.get("pnl") or 0)
    sport_list = sorted(sports)
    dates = sorted(by_date.keys())
    if len(dates) < 5 or len(sport_list) < 2:
        print("Not enough dates or sports for correlation.", file=sys.stderr)
        sys.exit(0)

    def mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    def corr(a: list[float], b: list[float]) -> float:
        n = min(len(a), len(b))
        if n < 3:
            return float("nan")
        a, b = a[:n], b[:n]
        ma, mb = mean(a), mean(b)
        va = sum((x - ma) ** 2 for x in a)
        vb = sum((x - mb) ** 2 for x in b)
        if va < 1e-12 or vb < 1e-12:
            return float("nan")
        cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
        return cov / (va**0.5 * vb**0.5)

    series = {s: [by_date[d].get(s, 0.0) for d in dates] for s in sport_list}
    print("Correlation matrix (daily PnL):")
    header = "        " + "".join(f"{x:>8}" for x in sport_list)
    print(header)
    for s1 in sport_list:
        line = f"{s1:>8}"
        for s2 in sport_list:
            v = corr(series[s1], series[s2])
            line += f"{v:8.2f}" if v == v else f"{'nan':>8}"
        print(line)


if __name__ == "__main__":
    main()
