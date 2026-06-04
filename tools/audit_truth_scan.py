#!/usr/bin/env python3
"""Read-only audit: reverse splits, staleness, high-WR strategies, PnL tiers.

Usage:
  python3 tools/audit_truth_scan.py [--json PATH] [--live]

Default reads audit_dashboard/data/dashboard_data.json; --live fetches production.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from audit_trail.reverse_split_symbols import (
    REVERSE_SPLIT_SYMBOLS,
    get_reverse_split_info,
    is_reverse_split_affected,
)

EST = timezone(timedelta(hours=-4))


def fmt_est(iso: str | None) -> str:
    if not iso:
        return "?"
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.astimezone(EST).strftime("%Y-%m-%d %I:%M %p EST")
    except Exception:
        return str(iso)[:19]


def load_dashboard(path: Path | None, live: bool) -> dict:
    if live:
        req = urllib.request.Request(
            "https://findtorontoevents.ca/audit/data/dashboard_data.json",
            headers={"User-Agent": "Mozilla/5.0 audit_truth_scan"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.load(resp)
    p = path or REPO_ROOT / "audit_dashboard/data/dashboard_data.json"
    return json.loads(p.read_text(encoding="utf-8"))


def scan_high_wr_strategies(data: dict) -> list[dict]:
    found: list[dict] = []

    def walk(obj, path: str = "", depth: int = 0):
        if depth > 10:
            return
        if isinstance(obj, dict):
            wr = obj.get("win_rate") or obj.get("wr")
            n = (
                obj.get("resolved")
                or obj.get("n_resolved")
                or obj.get("n")
                or obj.get("count")
            )
            name = (
                obj.get("name")
                or obj.get("strategy")
                or obj.get("source")
                or obj.get("system")
            )
            if wr is not None and n is not None:
                try:
                    wrf = float(wr)
                    ni = int(n)
                    if wrf >= 50 and ni >= 3:
                        found.append(
                            {
                                "wr": wrf,
                                "n": ni,
                                "name": name,
                                "path": path[:80],
                                "dsr_verdict": obj.get("dsr_verdict"),
                                "total_pnl": obj.get("total_pnl") or obj.get("total_pnl_pct"),
                            }
                        )
                except (TypeError, ValueError):
                    pass
            skip = {"picks", "recent_closed", "active", "closed_picks", "ueps_picks"}
            for k, v in obj.items():
                if k not in skip:
                    walk(v, f"{path}.{k}" if path else k, depth + 1)
        elif isinstance(obj, list) and len(obj) < 300:
            for i, v in enumerate(obj[:80]):
                walk(v, f"{path}[{i}]", depth + 1)

    walk(data)
    # Dedupe by name+wr+n
    seen = set()
    out = []
    for row in sorted(found, key=lambda x: (-x["wr"], -x["n"])):
        key = (row["name"], row["wr"], row["n"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def classify_wr_legit(row: dict) -> str:
    wr, n = row["wr"], row["n"]
    dsr = (row.get("dsr_verdict") or "").upper()
    if wr >= 100 and n < 10:
        return "SKEW: tiny sample (n<10) — 100% WR not actionable"
    if wr >= 80 and n < 30:
        return "SKEW: small sample (n<30) — headline WR inflated"
    if "OVERFIT" in dsr:
        return "SKEW: DSR OVERFIT_LIKELY — raw WR not publishable"
    if wr >= 80 and n >= 30:
        return "REVIEW: n>=30 but verify DSR/concentration before sizing"
    return "OK: plausible at this n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, help="Local dashboard_data.json path")
    ap.add_argument("--live", action="store_true", help="Fetch live production JSON")
    args = ap.parse_args()

    data = load_dashboard(args.json, args.live)
    gen = data.get("generated_at")
    now = datetime.now(timezone.utc)
    try:
        gen_dt = datetime.fromisoformat(str(gen).replace("Z", "+00:00"))
        age_h = (now - gen_dt).total_seconds() / 3600
    except Exception:
        gen_dt = None
        age_h = None

    print("=" * 72)
    print("AUDIT TRUTH SCAN")
    print(f"  generated_at: {fmt_est(gen)}  (age {age_h:.1f}h)" if age_h else f"  generated_at: {gen}")
    if age_h and age_h > 24:
        print("  ⚠ STALE: payload >24h old")
    elif age_h and age_h <= 2:
        print("  ✓ Fresh (<2h)")

    print("\n--- Reverse-split registry ---")
    for sym, (ratio, dt) in REVERSE_SPLIT_SYMBOLS.items():
        print(f"  {sym}: {ratio} effective {dt}")

    rc = data.get("picks", {}).get("recent_closed") or data.get("recent_closed") or []
    active = data.get("picks", {}).get("active") or []
    print(f"\n--- Reverse-split hits (recent_closed={len(rc)}, active={len(active)}) ---")
    for label, picks in [("recent_closed", rc), ("active", active)]:
        for p in picks:
            sym = (p.get("symbol") or "").upper()
            if is_reverse_split_affected(sym):
                info = get_reverse_split_info(sym)
                print(
                    f"  [{label}] {sym} pnl={p.get('pnl_pct')} "
                    f"flag={p.get('reverse_split_affected')} adj={p.get('_reverse_split_adjusted')} "
                    f"split={info}"
                )

    print("\n--- PnL tiers (recent_closed) ---")
    for tier in (80, 70, 60, 50, 40, 30, 20, 10):
        hits = [
            p
            for p in rc
            if abs(float(p.get("pnl_pct") or p.get("pnl") or 0)) >= tier
        ]
        if hits:
            top = sorted(
                hits,
                key=lambda x: -abs(float(x.get("pnl_pct") or x.get("pnl") or 0)),
            )[0]
            print(
                f"  |pnl|>={tier}%: {len(hits)}  top={top.get('symbol')} "
                f"{top.get('pnl_pct')}%"
            )

    print("\n--- WR tiers (strategies/sources) ---")
    rows = scan_high_wr_strategies(data)
    for tier in (80, 70, 60, 50):
        tier_rows = [r for r in rows if r["wr"] >= tier]
        if not tier_rows:
            continue
        print(f"\n  WR>={tier}%:")
        for r in tier_rows[:12]:
            verdict = classify_wr_legit(r)
            print(
                f"    WR={r['wr']:5.1f}% n={r['n']:4} {str(r['name'])[:36]:36} "
                f"dsr={r.get('dsr_verdict') or '-'}  → {verdict}"
            )

    ah = data.get("asset_class_health", {})
    if ah:
        print("\n--- asset_class_health (verdict-grade) ---")
        for ac in sorted(ah.keys()):
            v = ah[ac]
            if isinstance(v, dict):
                print(
                    f"  {ac:12} WR={v.get('win_rate')} PF={v.get('profit_factor')} "
                    f"n={v.get('n')}"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())