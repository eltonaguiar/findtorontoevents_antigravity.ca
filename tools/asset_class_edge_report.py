#!/usr/bin/env python3
"""Asset-class edge report — the standing answer to "what do I need to do to
make findtorontoevents.ca/audit profitable per asset class?"

Reads the resolved closed-pick ledger and reports, per asset class:

  1. Overall performance — n, win-rate, profit-factor, total pnl%.
  2. Best statistical edge — top strategy by profit-factor (n >= MIN_EDGE_N).
  3. Most reliable / consistent edge — top strategy by win-rate (n >= MIN_N).
  4. Accidentally-banned check — strategies on the blocklist whose own
     closed history looks GOOD (WR >= 55% or PF >= 1.5) — a possible
     mis-fire of the kill protocol worth a human look.
  5. High-edge / low-sample strategies — PF >= 1.5 + WR >= 55% but n < LOW_N.
     "Stopped emitting / broke, or only fires in a specific regime" — these
     are the hidden gems to investigate.

Pure stdlib. Runs on alpha_engine/data/closed_picks.json — no DB needed.

    python tools/asset_class_edge_report.py [--picks PATH] [--out report.md]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "alpha_engine"))

MIN_EDGE_N = 20      # min closed picks to qualify as a "best edge" candidate
MIN_N = 30           # min closed picks for the "most consistent" ranking
LOW_N = 20           # below this n, a high-edge strategy is "few picks"
PICKS_PATH = ROOT / "alpha_engine" / "data" / "closed_picks.json"


def _is_win(p: dict) -> bool:
    v = p.get("pnl_pct")
    return v is not None and float(v) > 0


def agg(picks: list[dict]) -> dict:
    """Aggregate n / win-rate / profit-factor / total-pnl over a pick list."""
    n = len(picks)
    if n == 0:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "pnl": 0.0}
    wins = sum(1 for p in picks if _is_win(p))
    gross_win = sum(float(p["pnl_pct"]) for p in picks
                    if p.get("pnl_pct") is not None and float(p["pnl_pct"]) > 0)
    gross_loss = abs(sum(float(p["pnl_pct"]) for p in picks
                         if p.get("pnl_pct") is not None and float(p["pnl_pct"]) < 0))
    pf = (gross_win / gross_loss) if gross_loss > 1e-9 else (999.0 if gross_win > 0 else 0.0)
    return {
        "n": n,
        "wr": wins / n,
        "pf": pf,
        "pnl": sum(float(p.get("pnl_pct") or 0) for p in picks),
    }


def load_picks(path: Path) -> list[dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    picks = d if isinstance(d, list) else d.get("picks", d.get("closed", []))
    return [p for p in picks if isinstance(p, dict)]


def _blocklist_checker():
    """Return is_blocked(name, asset_class) -> (bool, reason) — defensive."""
    try:
        from strategy_blocklist import is_blocked_strategy, block_reason  # type: ignore
        return lambda n, ac: (is_blocked_strategy(n, ac), block_reason(n, ac))
    except Exception:  # noqa: BLE001
        return lambda n, ac: (False, "")


def build_report(picks: list[dict]) -> str:
    is_blocked = _blocklist_checker()
    by_class: dict[str, list] = defaultdict(list)
    by_class_strat: dict[tuple, list] = defaultdict(list)
    for p in picks:
        ac = str(p.get("asset_class") or "UNKNOWN").upper()
        st = str(p.get("strategy") or p.get("source_system") or "?")
        by_class[ac].append(p)
        by_class_strat[(ac, st)].append(p)

    out = ["# Asset-Class Edge Report",
           "",
           f"Source: `closed_picks.json` — {len(picks)} resolved picks.",
           f"Thresholds: best-edge n>={MIN_EDGE_N}, consistent n>={MIN_N}, low-sample n<{LOW_N}.",
           ""]

    # 1. Overall per-class
    out += ["## 1. Overall performance per asset class", "",
            "| Asset class | n | WR | PF | total pnl% |",
            "|---|---|---|---|---|"]
    for ac in sorted(by_class, key=lambda k: -agg(by_class[k])["pf"]):
        a = agg(by_class[ac])
        out.append(f"| {ac} | {a['n']} | {a['wr']*100:.1f}% | {a['pf']:.2f} | {a['pnl']*100:.1f}% |")

    # per-class detail
    for ac in sorted(by_class):
        strfor = {st: agg(ps) for (c, st), ps in by_class_strat.items() if c == ac}
        out += ["", f"## {ac} — strategy breakdown", ""]

        # 2. best edge
        edge = [(s, a) for s, a in strfor.items() if a["n"] >= MIN_EDGE_N]
        edge.sort(key=lambda x: -x[1]["pf"])
        if edge:
            s, a = edge[0]
            out.append(f"- **Best edge:** `{s}` — PF {a['pf']:.2f}, WR {a['wr']*100:.1f}%, n={a['n']}")
        # 3. most consistent
        cons = [(s, a) for s, a in strfor.items() if a["n"] >= MIN_N]
        cons.sort(key=lambda x: -x[1]["wr"])
        if cons:
            s, a = cons[0]
            out.append(f"- **Most consistent:** `{s}` — WR {a['wr']*100:.1f}%, PF {a['pf']:.2f}, n={a['n']}")
        # 5. high-edge / low-n
        # n>=5 floor: a single-pick 100%-WR row is noise, not an edge.
        gems = [(s, a) for s, a in strfor.items()
                if a["pf"] >= 1.5 and a["wr"] >= 0.55 and 5 <= a["n"] < LOW_N]
        gems.sort(key=lambda x: -x[1]["pf"])
        if gems:
            out.append(f"- **High-edge / low-sample (investigate — broke or regime-specific):**")
            for s, a in gems[:5]:
                out.append(f"  - `{s}` — PF {a['pf']:.2f}, WR {a['wr']*100:.1f}%, n={a['n']}")
        # 4. accidentally-banned
        for s, a in strfor.items():
            blocked, reason = is_blocked(s, ac)
            if blocked and (a["wr"] >= 0.55 or a["pf"] >= 1.5) and a["n"] >= 10:
                out.append(f"- ⚠️ **Possible mis-ban:** `{s}` is BLOCKED ({reason}) "
                            f"but its closed history is WR {a['wr']*100:.1f}% / PF {a['pf']:.2f} "
                            f"/ n={a['n']} — human review.")

    return "\n".join(out)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--picks", type=Path, default=PICKS_PATH)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    if not args.picks.exists():
        print(f"ERROR: {args.picks} not found", file=sys.stderr)
        return 1
    report = build_report(load_picks(args.picks))
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"# wrote {args.out}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
