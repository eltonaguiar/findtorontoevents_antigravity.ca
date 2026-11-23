#!/usr/bin/env python3
"""cross_system_consensus.py — audit3 cross-system view (translation of pump-watch.html).

pump-watch.html already aggregates active/closed picks from several independent systems.
This reads the same local files, normalises (symbol, direction) across systems, and reports:
  - how many systems agree on each (symbol, direction)
  - a CONSENSUS set (>=2 systems)
Caveat stated in output: agreement is NOT a recommendation; correlated systems on the same
universe agree trivially (operator Finding 5). Consensus is an input to audit3, not a pick.
"""
import argparse, json
from collections import defaultdict
from pathlib import Path

SYSTEMS = {
    "alpha_engine": "alpha_engine/data/active_picks.json",
    "kimi": "KIMI_RISEOFTHECLAW/data/active_picks.json",
    "crypto_ml_edge": "crypto_ml_edge/data/active_picks.json",
    "ml_battleground": "ml_battleground/ensemble_data/active_picks.json",
    "rapid_fire": "rapid_fire_data/active_picks.json",
    "crypto_signal_engine": "crypto_signal_engine/data/active_picks.json",
    "genome": "genome/active_picks.json",
}


def extract_rows(d):
    if isinstance(d, list):
        return d
    if not isinstance(d, dict):
        return []
    for k in ("picks", "active_picks", "activePicks", "items", "data", "rows"):
        v = d.get(k)
        if isinstance(v, list):
            return v
        if isinstance(v, dict):
            return list(v.values())
    return []


def norm_sym(s):
    if not s:
        return None
    s = str(s).upper().replace("-USD", "USDT").replace("/", "").replace("=X", "")
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reports/cross_system_consensus.json")
    a = ap.parse_args()
    votes = defaultdict(lambda: defaultdict(int))   # (sym,dir) -> {system: count}
    per_system = {}
    for sysname, path in SYSTEMS.items():
        p = Path(path)
        if not p.exists():
            per_system[sysname] = {"present": False}
            continue
        try:
            rows = extract_rows(json.loads(p.read_text()))
        except Exception as e:
            per_system[sysname] = {"present": True, "error": str(e)}
            continue
        cnt = 0
        for r in rows:
            if not isinstance(r, dict):
                continue
            sym = norm_sym(r.get("symbol") or r.get("Symbol") or r.get("ticker"))
            raw_dir = (r.get("direction") or r.get("side") or r.get("signal") or "").upper()
            # map signal vocabulary -> direction
            d = {"BUY": "LONG", "LONG": "LONG", "SELL": "SHORT", "SHORT": "SHORT"}.get(raw_dir, "")
            if not sym or d not in ("LONG", "SHORT"):
                continue
            votes[(sym, d)][sysname] += 1
            cnt += 1
        per_system[sysname] = {"present": True, "n_picks": cnt}
    consensus = []
    singles = []
    for (sym, d), by_sys in votes.items():
        systems = sorted(by_sys)
        row = {"symbol": sym, "direction": d, "n_systems": len(systems),
               "systems": systems, "votes": dict(by_sys)}
        (consensus if len(systems) >= 2 else singles).append(row)
    consensus.sort(key=lambda x: (-x["n_systems"], x["symbol"]))
    singles.sort(key=lambda x: x["symbol"])
    out = {"generated_at": __import__("datetime").datetime.now(__import__("datetime").UTC).isoformat(),
           "whAT": "cross-system consensus over live active picks (pump-watch translation)",
           "per_system": per_system,
           "n_consensus": len(consensus), "n_single_system": len(singles),
           "consensus": consensus, "single_system": singles,
           "caveat": "Agreement is NOT a recommendation and NOT evidence of edge. Correlated systems "
                     "on one universe agree trivially (Finding 5: corr>0.9 = one bet). This is an "
                     "audit3 INPUT showing coverage/overlap, not a pick or a score."}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2) + "\n")
    print("per-system:", {k: v.get("n_picks", v.get("present")) for k, v in per_system.items()})
    print(f"consensus (>=2 systems): {len(consensus)}")
    for c in consensus[:10]:
        print(f"  {c['symbol']} {c['direction']} <- {c['systems']}")
    print(f"single-system symbols: {len(singles)}")


if __name__ == "__main__":
    main()
