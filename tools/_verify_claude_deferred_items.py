"""One-off: verify Claude deferred #1-4 (scanner calibration, luxalgo, quarantine, orphans)."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    # --- #1 calibration JSON ---
    candidates = [
        ROOT / ".tmp-validation-mcp" / "scanner_calibration_config.json",
        ROOT / "alpha_engine" / "data" / "scanner_calibration_config.json",
    ]
    print("=== #1 Scanner calibration JSON ===")
    for p in candidates:
        print(f"  {p.name}: {'EXISTS' if p.exists() else 'missing'} ({p})")

    # --- #2 luxalgo file ---
    lux = ROOT / "baby_strategies" / "vt_csv_edge_luxalgo_alts.py"
    print("\n=== #2 Luxalgo alts module ===")
    print(f"  {lux.name}: {'EXISTS' if lux.exists() else 'MISSING (not in repo)'}")

    # --- #3 quarantine stats (no write) ---
    closed = ROOT / "alpha_engine" / "data" / "closed_picks.json"
    print("\n=== #3 closed_picks.json ghost/dup heuristic (inline) ===")
    if not closed.exists():
        print("  closed_picks.json: missing")
    else:
        data = json.loads(closed.read_text(encoding="utf-8"))
        picks = data if isinstance(data, list) else data.get(
            "picks", data.get("closed_picks", [])
        )

        def _sf(v, d=0.0):
            try:
                return float(v) if v is not None else d
            except (TypeError, ValueError):
                return d

        ghosts = 0
        for p in picks:
            e, x = _sf(p.get("entry_price")), _sf(p.get("exit_price"))
            if e > 0 and x > 0 and abs(x - e) < 0.0001:
                ghosts += 1
                continue
            pnl = _sf(p.get("pnl_pct"))
            if abs(pnl) < 0.0001 and not p.get("exit_reason"):
                st = str(p.get("status", "")).upper()
                if st in ("CLOSED", "EXPIRED", "FLAT"):
                    ghosts += 1

        seen: dict[str, dict] = {}
        dups = 0
        for p in picks:
            sym = str(p.get("symbol", "")).upper()
            strat = str(p.get("strategy", ""))[:50]
            et = str(p.get("entry_time", p.get("opened_at", "")))[:16]
            direction = str(p.get("direction", "")).upper()
            key = f"{sym}|{strat}|{direction}|{et}"
            if key in seen:
                dups += 1
            else:
                seen[key] = p

        n = len(picks)
        print(f"  total rows: {n}")
        print(f"  ghost heuristic: {ghosts} ({100.0 * ghosts / n:.1f}%)")
        print(f"  duplicate keys (minute-grain): {dups} ({100.0 * dups / n:.1f}%)")
        print(
            f"  note: quarantine_closed_picks.py uses two-phase dedup; "
            f"dups counted only among non-ghosts"
        )

    # --- #4 vt orphans vs TIER1 ---
    scanner_py = ROOT / "incubator" / "backtest_team" / "forward_signal_scanner.py"
    text = scanner_py.read_text(encoding="utf-8")
    tier1_vt = set(re.findall(r'"((?:VT)[A-Za-z0-9_]+Strategy)"\s*:', text))

    baby = ROOT / "baby_strategies"
    vt_files = sorted(baby.glob("vt_*.py"))
    class_by_stem: dict[str, str] = {}
    for fpath in vt_files:
        try:
            tree = ast.parse(fpath.read_text(encoding="utf-8"))
        except SyntaxError:
            class_by_stem[fpath.stem] = "<syntax_error>"
            continue
        cls_name = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name.endswith("Strategy"):
                cls_name = node.name
                break
        class_by_stem[fpath.stem] = cls_name or "<no_strategy_class>"

    orphans = [
        (stem, cls)
        for stem, cls in sorted(class_by_stem.items())
        if cls and not cls.startswith("<") and cls not in tier1_vt
    ]
    print("\n=== #4 baby_strategies vt_* vs TIER1 VT*Strategy ===")
    print(f"  vt_*.py files: {len(vt_files)}")
    print(f"  VT*Strategy keys in forward_signal_scanner: {len(tier1_vt)}")
    print(f"  not in TIER1 (by primary *Strategy class name): {len(orphans)}")
    for stem, cls in orphans:
        print(f"    {stem}.py -> {cls}")


if __name__ == "__main__":
    main()
