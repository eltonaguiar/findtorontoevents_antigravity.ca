#!/usr/bin/env python3
"""
3-axis autopsy on closed picks CSV — before killing a system, see if it is misapplied.

Export closed picks from the audit dashboard (Export Closed CSV) or point --csv at any
compatible file. Expected columns (case-insensitive, flexible names):
  Strategy, Direction, PnL% (or PnL %%), Timeframe, System, Symbol

Usage (repo root):
  python tools/mutation_analysis.py --json
  python tools/mutation_analysis.py --json path/to/closed_picks.json
  python tools/mutation_analysis.py --csv closed_picks.csv
  python tools/mutation_analysis.py --json -o reports/mutation_report.txt --matrix-csv reports/system_symbol_matrix.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


def _norm_key(row: dict[str, str], *candidates: str) -> str:
    lower = {k.strip().lower(): (v or "").strip() for k, v in row.items()}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return ""


def read_csv_clean(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _normalize_direction(raw: str) -> str:
    u = (raw or "").strip().upper()
    if u in ("BUY", "LONG"):
        return "LONG"
    if u in ("SELL", "SHORT"):
        return "SHORT"
    return (raw or "").strip()


def _json_pick_to_row(p: dict) -> dict[str, str]:
    """Map repo closed-pick JSON object to CSV-like row keys for analysis."""
    direction = _normalize_direction(
        str(p.get("signal_type") or p.get("direction") or "")
    )
    pnl = p.get("pnl_pct")
    if pnl is None:
        pnl_s = "0"
    else:
        pnl_s = str(float(pnl))
    mode = p.get("mode") or p.get("timeframe") or p.get("trade_timeframe") or ""
    system = p.get("source_system") or p.get("source") or ""
    sym = p.get("symbol") or p.get("ticker") or ""
    strat = p.get("strategy") or ""
    return {
        "strategy": str(strat),
        "direction": direction,
        "pnl%": pnl_s,
        "timeframe": str(mode),
        "system": str(system),
        "symbol": str(sym),
    }


def read_closed_picks_json(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        for key in ("picks", "closed_picks", "items", "trades_list"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            data = []
    if not isinstance(data, list):
        return []
    rows: list[dict[str, str]] = []
    for p in data:
        if isinstance(p, dict):
            rows.append(_json_pick_to_row(p))
    return rows


def pnl_pct(row: dict[str, str]) -> float:
    raw = _norm_key(row, "pnl%", "pnl %", "pnl_pct", "pnl")
    raw = raw.replace("%", "").strip()
    try:
        return float(raw)
    except ValueError:
        return 0.0


def run_analysis(rows: list[dict[str, str]], min_trades: int, dir_spread_pp: float, tf_spread_pp: float, sym_spread_pp: int) -> None:
    # --- 1. Same strategy, different direction ---
    print("=" * 70)
    print("1. STRATEGIES THAT FLIP WR BY DIRECTION (same strategy)")
    print("=" * 70)
    strat_dir: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0.0]))

    for p in rows:
        strat = _norm_key(p, "strategy", "strat")
        direction = _norm_key(p, "direction", "dir")
        pnl = pnl_pct(p)
        if not strat:
            continue
        bucket = strat_dir[strat][direction]
        bucket[1] += 1
        bucket[2] += pnl
        if pnl > 0:
            bucket[0] += 1

    flips: list[tuple[str, dict]] = []
    for strat, dirs in strat_dir.items():
        if len(dirs) < 2:
            continue
        dir_stats: dict[str, dict] = {}
        for d, (w, t, tp) in dirs.items():
            if not d:
                continue
            if t >= min_trades:
                dir_stats[d] = {"wr": w / t * 100, "trades": t, "avg": tp / t}
        if len(dir_stats) >= 2:
            wrs = [v["wr"] for v in dir_stats.values()]
            if max(wrs) - min(wrs) > dir_spread_pp:
                flips.append((strat, dir_stats))

    flips.sort(
        key=lambda x: max(v["wr"] for v in x[1].values()) - min(v["wr"] for v in x[1].values()),
        reverse=True,
    )
    for strat, dirs in flips[:20]:
        print(f"\n  {strat[:72]}:")
        for d, stats in sorted(dirs.items(), key=lambda kv: -kv[1]["wr"]):
            print(
                f"    {d:8s}: {stats['wr']:5.1f}% WR | {stats['trades']:4d} trades | avg {stats['avg']:+.2f}%"
            )
        wrs = [v["wr"] for v in dirs.values()]
        print(f"    SPREAD: {max(wrs) - min(wrs):.0f}pp  -> consider LONG-only / SHORT-only mutation")

    # --- 2. Same strategy, different timeframe ---
    print("\n" + "=" * 70)
    print("2. STRATEGIES THAT FLIP WR BY TIMEFRAME")
    print("=" * 70)
    strat_tf: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0.0]))

    for p in rows:
        strat = _norm_key(p, "strategy", "strat")
        tf = _norm_key(p, "timeframe", "tf", "trade_timeframe")
        pnl = pnl_pct(p)
        if not strat or not tf:
            continue
        bucket = strat_tf[strat][tf]
        bucket[1] += 1
        bucket[2] += pnl
        if pnl > 0:
            bucket[0] += 1

    flips_tf: list[tuple[str, dict]] = []
    for strat, tfs in strat_tf.items():
        if len(tfs) < 2:
            continue
        tf_stats: dict[str, dict] = {}
        for tf, (w, t, tp) in tfs.items():
            if t >= min_trades:
                tf_stats[tf] = {"wr": w / t * 100, "trades": t, "avg": tp / t}
        if len(tf_stats) >= 2:
            wrs = [v["wr"] for v in tf_stats.values()]
            if max(wrs) - min(wrs) > tf_spread_pp:
                flips_tf.append((strat, tf_stats))

    flips_tf.sort(
        key=lambda x: max(v["wr"] for v in x[1].values()) - min(v["wr"] for v in x[1].values()),
        reverse=True,
    )
    for strat, tfs in flips_tf[:20]:
        print(f"\n  {strat[:72]}:")
        for tf, stats in sorted(tfs.items(), key=lambda kv: -kv[1]["wr"]):
            print(
                f"    {tf:14s}: {stats['wr']:5.1f}% WR | {stats['trades']:4d} trades | avg {stats['avg']:+.2f}%"
            )

    # --- 3. Same system, symbol variance ---
    print("\n" + "=" * 70)
    print("3. SYSTEMS WITH HIGH SYMBOL VARIANCE (winner vs loser symbols)")
    print("=" * 70)
    sys_sym: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0.0]))

    for p in rows:
        sys = _norm_key(p, "system", "source_system", "source")
        sym = _norm_key(p, "symbol", "ticker")
        pnl = pnl_pct(p)
        if not sys or not sym:
            continue
        bucket = sys_sym[sys][sym]
        bucket[1] += 1
        bucket[2] += pnl
        if pnl > 0:
            bucket[0] += 1

    for sys, syms in sorted(sys_sym.items(), key=lambda kv: kv[0]):
        if len(syms) < 5:
            continue
        sym_stats: dict[str, dict] = {}
        for sym, (w, t, tp) in syms.items():
            if t >= min_trades:
                sym_stats[sym] = {"wr": w / t * 100, "trades": t, "avg": tp / t}
        if len(sym_stats) < 3:
            continue
        wrs = [v["wr"] for v in sym_stats.values()]
        spread = max(wrs) - min(wrs)
        if spread > sym_spread_pp:
            print(f"\n  {sys} (WR spread: {spread:.0f}pp across symbols with >={min_trades} trades each):")
            top = sorted(sym_stats.items(), key=lambda x: x[1]["wr"], reverse=True)[:6]
            for sym, stats in top:
                print(
                    f"    {sym:14s}: {stats['wr']:5.1f}% WR | {stats['trades']:3d} trades | avg {stats['avg']:+.2f}%"
                )
            worst = sorted(sym_stats.items(), key=lambda x: x[1]["wr"])[:3]
            worst_s = ", ".join(f"{s} ({v['wr']:.0f}%)" for s, v in worst)
            print(f"    WORST: {worst_s}  -> consider symbol-allowlist mutation (SANDBOX)")

    # --- 4. Axis 4: Volatility/ATR-normalization candidates ---
    # Registered 2026-05-17 per DAILY_IDEAS_LLMARENA_May162026.MD (P4) + mutation protocol Step 1b.
    # This axis does not split on existing data columns — it's a re-parameterization hint:
    # if a system has WR < 45% overall but passes Axes 1-3 with no clear winner split,
    # the entry trigger may be mis-scaled for the asset class's native volatility.
    # Candidate check: find systems with WR < 50% and no high-spread direction/symbol split above.
    print("\n" + "=" * 70)
    print("4. AXIS 4 (VOL-NORMALIZATION) CANDIDATES — low-WR systems with no axis 1-3 rescue")
    print("   Rationale: trigger calibrated for high-vol class (e.g. CRYPTO) may miss for FOREX")
    print("   Action: re-express entry threshold in ATR units. See docs/MUTATION_THREE_AXIS_PROTOCOL.md §Step1b")
    print("=" * 70)
    sys_wrs: dict[str, list] = defaultdict(lambda: [0, 0])
    for p in rows:
        sys = _norm_key(p, "system", "source_system", "source")
        pnl = pnl_pct(p)
        if not sys:
            continue
        sys_wrs[sys][1] += 1
        if pnl > 0:
            sys_wrs[sys][0] += 1
    low_wr_candidates = sorted(
        [(s, w / t * 100, t) for s, (w, t) in sys_wrs.items() if t >= min_trades and w / t < 0.50],
        key=lambda x: x[1],
    )
    if low_wr_candidates:
        for sys, wr, t in low_wr_candidates[:10]:
            print(f"  {sys[:60]:60s}: {wr:5.1f}% WR ({t} trades) — Axis 4 candidate")
    else:
        print("  No systems below 50% WR with sufficient trades — no Axis 4 candidates.")

    print("\n" + "=" * 70)
    print("NEXT: See docs/MUTATION_THREE_AXIS_PROTOCOL.md (mutation quality, allowlist rules)")
    print("=" * 70)


def write_compatibility_matrix(rows: list[dict[str, str]], path: Path, min_trades: int) -> None:
    """Per (system, symbol) win rate and size — for allowlist / blocklist mutations."""
    sys_sym: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0.0]))
    for p in rows:
        sys = _norm_key(p, "system", "source_system", "source")
        sym = _norm_key(p, "symbol", "ticker")
        pnl = pnl_pct(p)
        if not sys or not sym:
            continue
        b = sys_sym[sys][sym]
        b[1] += 1
        b[2] += pnl
        if pnl > 0:
            b[0] += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["system", "symbol", "trades", "wins", "wr_pct", "avg_pnl_pct"])
        flat: list[tuple[str, str, int, int, float, float]] = []
        for sys, syms in sys_sym.items():
            for sym, (wins, t, tp) in syms.items():
                if t < min_trades:
                    continue
                flat.append((sys, sym, t, wins, (wins / t) * 100.0, tp / t))
        flat.sort(key=lambda x: (x[0], -x[4], x[1]))
        for sys, sym, t, wins, wr, avg in flat:
            w.writerow([sys, sym, t, wins, round(wr, 2), round(avg, 4)])


class _Tee:
    """Write to multiple text streams (stdout + optional report file)."""

    def __init__(self, *streams: object) -> None:
        self.streams = streams

    def write(self, s: str) -> int:
        for st in self.streams:
            st.write(s)
        return len(s)

    def flush(self) -> None:
        for st in self.streams:
            st.flush()


def main() -> int:
    ap = argparse.ArgumentParser(description="3-axis closed-pick autopsy for mutation candidates")
    ap.add_argument(
        "--csv",
        type=Path,
        default=None,
        help="Exported closed picks CSV (dashboard Export Closed)",
    )
    ap.add_argument(
        "--json",
        type=Path,
        nargs="?",
        const=Path("alpha_engine/data/closed_picks.json"),
        default=None,
        help="Repo closed_picks JSON (default path if flag given alone: alpha_engine/data/closed_picks.json)",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Also write full text report to this file (stdout unchanged)",
    )
    ap.add_argument(
        "--matrix-csv",
        type=Path,
        default=None,
        help="Write system×symbol compatibility matrix (WR, trades) for gated mutations",
    )
    ap.add_argument("--min-trades", type=int, default=5, help="Minimum trades per bucket")
    ap.add_argument("--dir-spread", type=float, default=20.0, help="Min WR spread (pp) for direction flip report")
    ap.add_argument("--tf-spread", type=float, default=15.0, help="Min WR spread (pp) for timeframe flip report")
    ap.add_argument("--sym-spread", type=float, default=30.0, help="Min WR spread (pp) for system symbol report")
    args = ap.parse_args()

    rows: list[dict[str, str]] | None = None
    if args.json is not None:
        if not args.json.is_file():
            print(f"Missing JSON: {args.json.resolve()}", file=sys.stderr)
            return 2
        rows = read_closed_picks_json(args.json)
        if not rows:
            print("JSON has no pick rows.", file=sys.stderr)
            return 2
    else:
        csv_path = args.csv if args.csv is not None else Path("closed_picks.csv")
        if not csv_path.is_file():
            print(f"Missing CSV: {csv_path.resolve()}", file=sys.stderr)
            print("Use --json or export closed picks (Export Closed) to closed_picks.csv.", file=sys.stderr)
            return 2
        rows = read_csv_clean(csv_path)
        if not rows:
            print("CSV has no rows.", file=sys.stderr)
            return 2

    if args.matrix_csv is not None:
        write_compatibility_matrix(rows, args.matrix_csv, args.min_trades)

    out_file = None
    saved_out = sys.stdout
    try:
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            out_file = args.output.open("w", encoding="utf-8")
            sys.stdout = _Tee(saved_out, out_file)
        run_analysis(rows, args.min_trades, args.dir_spread, args.tf_spread, args.sym_spread)
    finally:
        sys.stdout = saved_out
        if out_file is not None:
            out_file.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
