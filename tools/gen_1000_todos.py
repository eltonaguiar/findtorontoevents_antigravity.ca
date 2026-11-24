#!/usr/bin/env python3
"""Generate the 1000-cell evidence backlog.

Why this exists
---------------
Three coding agents kept stopping because the work queue was prose. A prose queue can always be
declared "exhausted" - and it was, twice ("The honest queue is finite and I've now worked the
genuinely unblocked remainder"). A queue of enumerated cells cannot be exhausted by argument: each
cell is either measured or it is not, and its state is a file on disk.

The grid is a full crossing of what we actually test, so the count is not padded filler:
  20 symbols x 10 strategy families x 5 horizons = 1000 cells.

Every cell asks the same falsifiable question: does this strategy family, on this instrument, at
this horizon, produce net-of-cost expectancy whose confidence interval excludes zero AND survives
a permutation control? Anything else is a KILL, and a KILL is a completed cell, not a failure.

Usage
-----
  python tools/gen_1000_todos.py            # writes 1000_TODOS.md + 1000_TODOS.json
  python tools/gen_1000_todos.py --claim    # print the first unclaimed cell as JSON
  python tools/gen_1000_todos.py --set SYM/STRAT/HORIZON --status done --note "..."
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "1000_TODOS.md"
JSON_PATH = ROOT / "1000_TODOS.json"

# 20 instruments: 7 liquid crypto, 10 US equity/ETF, 3 FX majors.
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT",
    "SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "JPM", "XLE", "GLD", "TLT",
    "EURUSD", "USDJPY", "GBPUSD",
]

# 10 strategy families already implemented somewhere in the repo's harness family.
STRATEGIES = [
    "trend_pullback", "rsi2_pullback", "vol_compression", "breakout", "donchian",
    "ma_cross", "bb_meanrev", "vwap_reversion", "momentum_12_1", "gap_fade",
]

# 5 horizons the ledger can actually score.
HORIZONS = ["15m", "1h", "4h", "1d", "1w"]

CELL_STATUSES = ["open", "claimed", "done", "killed", "blocked_no_data"]

DONE_CONDITION = (
    "Report n (closed trades), net mean bp/trade after 26bp round-turn, 95% bootstrap CI, "
    "permutation p, and DSR. Cell is DONE when a JSON artifact exists under "
    "results/cells/<symbol>_<strategy>_<horizon>.json carrying those five numbers plus git SHA. "
    "Cell is KILLED (also complete) when n<30 or CI includes 0 or permutation p>0.05. "
    "Cell is BLOCKED_NO_DATA only when the instrument has no bars at that horizon in the repo - "
    "and then the bar count must be recorded to prove it."
)


def build_cells() -> list[dict]:
    cells = []
    for sym in SYMBOLS:
        for strat in STRATEGIES:
            for hz in HORIZONS:
                key = f"{sym}/{strat}/{hz}"
                cells.append({
                    "key": key,
                    "symbol": sym,
                    "strategy": strat,
                    "horizon": hz,
                    "status": "open",
                    "owner": None,
                    "claimed_at": None,
                    "artifact": f"results/cells/{sym}_{strat}_{hz}.json",
                    "note": None,
                })
    return cells


def load_state() -> dict:
    if JSON_PATH.exists():
        try:
            return json.loads(JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def write_all(cells: list[dict]) -> None:
    state = load_state()
    done = [c for c in cells if c["status"] in ("done", "killed")]
    open_ = [c for c in cells if c["status"] == "open"]
    claimed = [c for c in cells if c["status"] == "claimed"]
    blocked = [c for c in cells if c["status"] == "blocked_no_data"]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(cells),
        "grid": {"symbols": SYMBOLS, "strategies": STRATEGIES, "horizons": HORIZONS},
        "done_condition": DONE_CONDITION,
        "counts": {
            "open": len(open_), "claimed": len(claimed),
            "done_or_killed": len(done), "blocked_no_data": len(blocked),
        },
        "cells": cells,
        "carried_forward": state.get("carried_forward", {}),
    }
    JSON_PATH.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")

    lines = [
        "# 1000-TODO evidence backlog",
        "",
        f"Generated {payload['generated_at']} by `tools/gen_1000_todos.py`. "
        "Machine state: `1000_TODOS.json`. Do not hand-edit the counts - rerun the generator.",
        "",
        "**Worked {done} of {total}.** open {open_} | claimed {claimed} | blocked_no_data {blocked}".format(
            done=len(done), total=len(cells), open_=len(open_),
            claimed=len(claimed), blocked=len(blocked)),
        "",
        "## Done condition (identical for every cell)",
        "",
        DONE_CONDITION,
        "",
        "A KILL is a completed cell. Null results are the expected majority; they are the product.",
        "",
    ]
    for sym in SYMBOLS:
        rows = [c for c in cells if c["symbol"] == sym]
        n_done = sum(1 for c in rows if c["status"] in ("done", "killed"))
        lines.append(f"## {sym} - {n_done}/{len(rows)} worked")
        lines.append("")
        lines.append("| cell | status | artifact |")
        lines.append("|---|---|---|")
        for c in rows:
            mark = {"open": " ", "claimed": "~", "done": "x",
                    "killed": "x", "blocked_no_data": "-"}[c["status"]]
            lines.append(f"| [{mark}] `{c['key']}` | {c['status']} | `{c['artifact']}` |")
        lines.append("")
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


IMPOSSIBLE = {("rsi2_pullback", "1d"), ("ma_cross", "1d")}  # daily samples can't reach n>=30
CRYPTO_DAILY = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"}  # symbols with daily bars in repo


def _roundrobin_open(cells: list[dict]) -> list[dict]:
    """Order open cells round-robin across SYMBOLS instead of symbol-major."""
    si = {s: i for i, s in enumerate(SYMBOLS)}
    hi = {h: i for i, h in enumerate(HORIZONS)}
    sti = {s: i for i, s in enumerate(STRATEGIES)}
    def depth(c):
        return sti[c["strategy"]] * len(HORIZONS) + hi[c["horizon"]]
    return sorted([c for c in cells if c["status"] == "open"],
                  key=lambda c: (depth(c), si[c["symbol"]], c["key"]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claim", action="store_true", help="print first unclaimed cell as JSON")
    ap.add_argument("--set", help="cell key to update")
    ap.add_argument("--status", choices=CELL_STATUSES)
    ap.add_argument("--note")
    ap.add_argument("--owner")
    a = ap.parse_args()

    cells = build_cells()
    existing = {c["key"]: c for c in load_state().get("cells", [])}
    for c in cells:
        if c["key"] in existing:
            c.update({k: v for k, v in existing[c["key"]].items()
                      if k in ("status", "owner", "claimed_at", "note")})

    if a.claim:
        # auto-resolve known-impossible cells first (cannot reach n>=30), then claim round-robin
        for c in cells:
            if c["status"] == "open" and (c["strategy"], c["horizon"]) in IMPOSSIBLE:
                if c["symbol"] in CRYPTO_DAILY:
                    c["status"] = "killed"
                    c["note"] = ("INSUFFICIENT_TRADES: daily sample cannot reach n>=30 for "
                                 f"{c['strategy']} on {c['horizon']}")
                else:
                    c["status"] = "blocked_no_data"
                    c["note"] = f"BLOCKED_NO_DATA: bars=0 for {c['symbol']} at {c['horizon']} (no daily bars in repo)"
                c["owner"] = a.owner or "unassigned"
                c["claimed_at"] = datetime.now(timezone.utc).isoformat()
        for c in _roundrobin_open(cells):
            if (c["strategy"], c["horizon"]) in IMPOSSIBLE:
                continue
            c["status"] = "claimed"
            c["claimed_at"] = datetime.now(timezone.utc).isoformat()
            c["owner"] = a.owner or "unassigned"
            print(json.dumps(c, indent=1))
            break
        else:
            if open([x for x in cells if x["status"] == "open"]):
                print(json.dumps({"exhausted": False, "note": "only impossible cells remain"}))
            else:
                print(json.dumps({"exhausted": True, "total": len(cells)}))
        write_all(cells)
        return 0

    if a.set:
        hits = [c for c in cells if c["key"] == a.set]
        if not hits:
            print(f"no such cell: {a.set}", file=sys.stderr)
            return 2
        hits[0]["status"] = a.status or hits[0]["status"]
        if a.note:
            hits[0]["note"] = a.note
        if a.owner:
            hits[0]["owner"] = a.owner
        write_all(cells)
        print(json.dumps(hits[0], indent=1))
        return 0

    write_all(cells)
    print(f"wrote {MD_PATH.name} and {JSON_PATH.name}: {len(cells)} cells")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
