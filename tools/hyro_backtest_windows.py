#!/usr/bin/env python3
"""
Rolling historical windows for Hyro extended strategies (out-of-sample stability).

Each window is a non-overlapping slice ending at (now - stride * k); use to see
whether a setup holds across regimes or was a single lucky period.

From repo root:
  python tools/hyro_backtest_windows.py --symbol ETHUSDT --strategy volume --windows 6 --win-months 3
  python tools/hyro_backtest_windows.py --symbol BTCUSDT --strategy heikin_ashi --min-rr 1.2 --max-atr-pct 6 --save
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from hyro_backtest_extended import EXTENDED_STRATEGIES, run_single

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_OUT = _ROOT / "audit_dashboard" / "data" / "hyro_backtest_windows.json"


def main() -> int:
    p = argparse.ArgumentParser(description="Hyro rolling-window stress backtest")
    p.add_argument("--symbol", required=True)
    p.add_argument("--strategy", required=True, choices=sorted(EXTENDED_STRATEGIES.keys()))
    p.add_argument("--windows", type=int, default=6, help="Number of backward windows")
    p.add_argument(
        "--stride-months",
        type=float,
        default=3.0,
        help="Months to step end-date backward between windows (default 3)",
    )
    p.add_argument("--win-months", type=int, default=3, help="Months of data per window")
    p.add_argument("--risk", type=float, default=0.75)
    p.add_argument("--long-only", action="store_true")
    p.add_argument("--min-rr", type=float, default=0.0)
    p.add_argument("--max-atr-pct", type=float, default=0.0)
    p.add_argument("--save", action="store_true")
    p.add_argument("--output", type=str, default=str(_DEFAULT_OUT))
    args = p.parse_args()

    now = datetime.now(timezone.utc)
    stride_days = int(args.stride_months * 30)
    rows: list[dict] = []

    for k in range(args.windows):
        end = now - timedelta(days=k * stride_days)
        r = run_single(
            args.symbol,
            args.strategy,
            months=args.win_months,
            risk_pct=args.risk,
            long_only=args.long_only,
            end_utc=end,
            min_rr=args.min_rr,
            max_atr_pct=args.max_atr_pct,
        )
        label = f"w{k} end={end.date().isoformat()}"
        if not r:
            rows.append({"window": k, "end_utc": end.isoformat(), "label": label, "ok": False})
            print(f"{label}: no trades / no signals")
            continue
        r = dict(r)
        r["window"] = k
        r["end_utc"] = end.isoformat()
        r["label"] = label
        r["ok"] = True
        rows.append(r)
        st = "PASS" if r["passed"] else ("FAIL" if r["failed"] else "INC")
        print(
            f"{label}: {st} tr={r['total_trades']} WR={r['win_rate']}% "
            f"PnL%={r['pnl_pct']} maxDD={r['max_dd']}"
        )

    ok = [x for x in rows if x.get("ok")]
    if ok:
        pnls = [x["pnl_pct"] for x in ok]
        dds = [x["max_dd"] for x in ok]
        passed_n = sum(1 for x in ok if x.get("passed"))
        print(
            f"\nSummary: {passed_n}/{len(ok)} windows passed challenge | "
            f"PnL% min/median/max = {min(pnls):.1f} / {sorted(pnls)[len(pnls)//2]:.1f} / {max(pnls):.1f} | "
            f"maxDD worst = {max(dds):.1f}"
        )

    if args.save:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "symbol": args.symbol,
            "strategy": args.strategy,
            "windows": args.windows,
            "stride_months": args.stride_months,
            "win_months": args.win_months,
            "risk_pct": args.risk,
            "min_rr": args.min_rr,
            "max_atr_pct": args.max_atr_pct,
            "results": rows,
        }
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"Saved -> {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
