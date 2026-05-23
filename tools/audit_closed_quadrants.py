#!/usr/bin/env python3
"""
Closed-pick quadrant + simple filter-edge analysis for /audit methodology docs.

Reads ``audit_dashboard/data/dashboard_data.json`` → ``picks.recent_closed``.
Run: ``.venv/Scripts/python.exe tools/audit_closed_quadrants.py``

Output: human-readable tables on stdout (also suitable to paste into README updates).
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"


def norm_ac(x: str) -> str:
    x = (x or "UNKNOWN").upper().strip()
    if x in {"STOCK", "STOCKS", "EQUITIES"}:
        return "EQUITY"
    if x in {"FUTURES"}:
        return "FUTURES"
    return x


def _f(x, d=0.0):
    try:
        if x is None:
            return d
        return float(x)
    except Exception:
        return d


def wr_pf(picks: list) -> tuple[float, float, int]:
    n = len(picks)
    if not n:
        return 0.0, 0.0, 0
    wins = sum(1 for p in picks if _f(p.get("pnl_pct")) > 0)
    gains = sum(_f(p.get("pnl_pct")) for p in picks if _f(p.get("pnl_pct")) > 0)
    losses = -sum(_f(p.get("pnl_pct")) for p in picks if _f(p.get("pnl_pct")) < 0)
    pf = (gains / losses) if losses > 0 else (float("inf") if gains > 0 else 0.0)
    return wins / n * 100, pf, n


def score(p):
    return _f(p.get("elite_score") or p.get("score"))


def rsi(p):
    ind = p.get("indicators")
    if isinstance(ind, dict):
        r = ind.get("rsi") or ind.get("rsi_14")
        if r is not None:
            return _f(r)
    return _f(p.get("rsi") or p.get("rsi_14"))


def vol_ratio(p):
    ind = p.get("indicators")
    if isinstance(ind, dict):
        v = ind.get("volume_ratio")
        if v is not None:
            return _f(v)
    return _f(p.get("volume_ratio"))


def rr(p):
    return _f(p.get("rr_ratio") or p.get("risk_reward"))


def direction(p):
    return (p.get("direction") or p.get("signal_type") or "").upper()


def main() -> None:
    if not DATA.is_file():
        print(f"Missing {DATA}", file=sys.stderr)
        sys.exit(1)
    with DATA.open("r", encoding="utf-8") as f:
        d = json.load(f)
    closed = d.get("picks", {}).get("recent_closed") or d.get("recent_closed") or []
    print(f"# recent_closed rows: {len(closed)}", file=sys.stderr)
    print(f"# generated_at: {d.get('generated_at', '?')}\n")

    by_ac: dict[str, list] = defaultdict(list)
    for p in closed:
        by_ac[norm_ac(p.get("asset_class", ""))].append(p)

    print("=== PER CLASS COUNTS ===")
    for ac, ps in sorted(by_ac.items(), key=lambda kv: -len(kv[1])):
        print(f"{ac:12s} n={len(ps)}")

    print("\n=== QUADRANTS (score>=60 & pnl<=0 vs score<40 & pnl>=2%) ===")
    print(f"{'class':10s} {'hi_lo_n':>7s} {'lo_hi_n':>7s} {'hi_lo_avgPnL':>13s} {'lo_hi_avgPnL':>13s}")
    for ac, ps in sorted(by_ac.items()):
        hi_lo = [p for p in ps if score(p) >= 60 and _f(p.get("pnl_pct")) <= 0]
        lo_hi = [p for p in ps if score(p) < 40 and _f(p.get("pnl_pct")) >= 2.0]
        a = sum(_f(p.get("pnl_pct")) for p in hi_lo) / max(len(hi_lo), 1)
        b = sum(_f(p.get("pnl_pct")) for p in lo_hi) / max(len(lo_hi), 1)
        print(f"{ac:10s} {len(hi_lo):>7d} {len(lo_hi):>7d} {a:>13.2f} {b:>13.2f}")
        if hi_lo:
            print(f"    hi_lo top: {Counter(p.get('strategy', '?') for p in hi_lo).most_common(3)}")
        if lo_hi:
            print(f"    lo_hi top: {Counter(p.get('strategy', '?') for p in lo_hi).most_common(3)}")

    # CRYPTO recency slices
    crypto = sorted(
        [p for p in by_ac.get("CRYPTO", []) if p.get("closed_at") or p.get("resolved_at")],
        key=lambda p: str(p.get("closed_at") or p.get("resolved_at") or ""),
        reverse=True,
    )
    if crypto:
        print("\n=== CRYPTO recent_closed (newest first) - WR / mean pnl / PF ===")
        for label, n in [("last_10", 10), ("last_20", 20), ("last_50", 50), ("last_100", 100)]:
            sl = crypto[:n]
            wr, pf, nn = wr_pf(sl)
            mean = sum(_f(p.get("pnl_pct")) for p in sl) / max(nn, 1)
            print(f"  {label:10s} n={nn:3d}  WR={wr:5.1f}%  meanPnL={mean:+.3f}%  PF={pf:.2f}")
        wr, pf, nn = wr_pf(crypto)
        mean = sum(_f(p.get("pnl_pct")) for p in crypto) / max(nn, 1)
        print(f"  {'all_crypto':10s} n={nn:3d}  WR={wr:5.1f}%  meanPnL={mean:+.3f}%  PF={pf:.2f}")

    print("\n=== FILTER EDGE (n>=20 per class only) ===")
    print(f"{'class':10s} {'filter':20s} {'bWR':>7s} {'fWR':>7s} {'bPF':>8s} {'fPF':>8s} {'n_b':>6s} {'n_f':>6s}")
    for ac, ps in sorted(by_ac.items()):
        if len(ps) < 20:
            continue
        b_wr, b_pf, n = wr_pf(ps)

        rsi_ok = []
        for p in ps:
            r = rsi(p)
            if r <= 0:
                continue
            d = direction(p)
            if d in ("BUY", "LONG") and r < 30:
                rsi_ok.append(p)
            elif d in ("SELL", "SHORT") and r > 70:
                rsi_ok.append(p)
        if rsi_ok:
            f_wr, f_pf, n2 = wr_pf(rsi_ok)
            print(
                f"{ac:10s} {'RSI_dir':20s} {b_wr:6.1f}% {f_wr:6.1f}% "
                f"{b_pf:8.2f} {f_pf:8.2f} {n:6d} {n2:6d}"
            )

        vol_ok = [p for p in ps if vol_ratio(p) > 1.5]
        if vol_ok:
            f_wr, f_pf, n2 = wr_pf(vol_ok)
            print(
                f"{ac:10s} {'vol_ratio>1.5':20s} {b_wr:6.1f}% {f_wr:6.1f}% "
                f"{b_pf:8.2f} {f_pf:8.2f} {n:6d} {n2:6d}"
            )

        rr_ok = [p for p in ps if rr(p) >= 1.5]
        if rr_ok:
            f_wr, f_pf, n2 = wr_pf(rr_ok)
            print(
                f"{ac:10s} {'rr>=1.5':20s} {b_wr:6.1f}% {f_wr:6.1f}% "
                f"{b_pf:8.2f} {f_pf:8.2f} {n:6d} {n2:6d}"
            )


if __name__ == "__main__":
    main()
