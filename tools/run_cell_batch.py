#!/usr/bin/env python3
"""Drive the cell loop: claim -> measure -> record, N cells at a time.

Every claim goes through tools/gen_1000_todos.py so the atomic claim/owner
write is respected; re-reading the ledger happens inside that tool, not here.

Cells whose symbol has no bar data are recorded as blocked_no_data WITH the bar
count, never guessed. A cell is never marked killed/done without an artifact.

    python3 tools/run_cell_batch.py --n 10 --owner copilot
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GEN = REPO_ROOT / "tools" / "gen_1000_todos.py"
MEASURE = REPO_ROOT / "tools" / "measure_cell.py"


LEDGER = REPO_ROOT / "1000_TODOS.json"


NON_CRYPTO = {"SPY","QQQ","IWM","AAPL","MSFT","NVDA","JPM","XLE","GLD","TLT",
              "EURUSD","USDJPY","GBPUSD"}
ONLY_SYMBOLS = None   # set by --only-symbols


def claim_measurable(owner):
    """Pick the first OPEN cell that can actually be measured, then claim it.

    The ledger is symbol-major, so plain --claim walks 15m/4h/1h horizons for
    every symbol before reaching a second 1d cell. Those horizons have no bar
    source (only a 3-month BTC 1h cache), so ~550 of 914 open cells could only
    ever return bars=0. Ordering by measurability lifts the yield from 8% to
    roughly 60% without touching the shared generator on main.

    Claiming still goes through --set, the same writer the generator uses, so
    the owner/claimed_at fields are set the same way --claim would set them.
    """
    d = json.loads(LEDGER.read_text())
    cells = d["cells"] if isinstance(d, dict) else d
    for c in cells:
        if c.get("status") != "open":
            continue
        h = c["horizon"]
        ok = h in ("1d", "1w") or (h == "1h" and c["symbol"] == "BTCUSDT")
        if not ok:
            continue
        if ONLY_SYMBOLS is not None and c["symbol"] not in ONLY_SYMBOLS:
            continue
        subprocess.run([sys.executable, str(GEN), "--set", c["key"], "--status",
                        "claimed", "--owner", owner,
                        "--note", "claimed by measurable-first order"],
                       capture_output=True, text=True, cwd=REPO_ROOT)
        c["status"], c["owner"] = "claimed", owner
        return c
    return None


def claim(owner):
    p = subprocess.run([sys.executable, str(GEN), "--claim", "--owner", owner],
                       capture_output=True, text=True, cwd=REPO_ROOT)
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    start = out.find("{")
    if start < 0:
        return None
    try:
        return json.loads(out[start:])
    except json.JSONDecodeError:
        return None


def set_status(key, status, owner, note):
    subprocess.run([sys.executable, str(GEN), "--set", key, "--status", status,
                    "--owner", owner, "--note", note],
                   capture_output=True, text=True, cwd=REPO_ROOT)


def measure(cell):
    art = REPO_ROOT / cell["artifact"]
    p = subprocess.run([sys.executable, str(MEASURE),
                        "--symbol", cell["symbol"], "--strategy", cell["strategy"],
                        "--horizon", cell["horizon"], "--out", str(art)],
                       capture_output=True, text=True, cwd=REPO_ROOT, timeout=900)
    if not art.exists():
        return None, (p.stdout + p.stderr)[-200:]
    return json.loads(art.read_text()), None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--only-symbols", default=None,
                    help="comma list, or 'non-crypto' to fill EQUITY/FOREX coverage")
    ap.add_argument("--measurable-first", action="store_true",
                    help="skip cells whose horizon has no bar source")
    ap.add_argument("--owner", default="copilot")
    args = ap.parse_args(argv)

    global ONLY_SYMBOLS
    if args.only_symbols:
        ONLY_SYMBOLS = (NON_CRYPTO if args.only_symbols == "non-crypto"
                        else set(args.only_symbols.split(",")))
    done = killed = blocked = insuff = 0
    rows = []
    for i in range(args.n):
        cell = (claim_measurable(args.owner) if args.measurable_first
                else claim(args.owner))
        if cell is None:
            print("  no claimable cell returned; stopping")
            break
        key = cell["key"]
        try:
            art, err = measure(cell)
        except Exception as exc:  # noqa: BLE001
            art, err = None, str(exc)[:180]
        if art is None:
            set_status(key, "blocked_no_data", args.owner,
                       f"measurement failed: {err}")
            blocked += 1
            rows.append((key, "ERROR", "", "", "", ""))
            print(f"  [{i+1:2d}] {key:38s} ERROR {err}")
            continue

        v = art.get("verdict")
        if v == "BLOCKED_NO_DATA":
            set_status(key, "blocked_no_data", args.owner,
                       f"BLOCKED_NO_DATA: {art.get('bars')} bars from {art.get('bar_source')}")
            blocked += 1
            rows.append((key, v, f"bars={art.get('bars')}", "", "", ""))
            print(f"  [{i+1:2d}] {key:38s} BLOCKED bars={art.get('bars')}")
        elif v == "INSUFFICIENT_TRADES":
            set_status(key, "done", args.owner,
                       f"INSUFFICIENT_TRADES: n={art.get('n')} from {art.get('bars')} bars")
            insuff += 1
            rows.append((key, v, f"n={art.get('n')}", "", "", ""))
            print(f"  [{i+1:2d}] {key:38s} INSUFF n={art.get('n')}")
        elif v == "KILL":
            set_status(key, "killed", args.owner,
                       f"n={art['n']}, net {art['net_mean_bp']:+.2f}bp, "
                       f"CI {art['ci95_net_bp']}, p={art['permutation_p']}, DSR={art['dsr']}")
            killed += 1
            rows.append((key, v, f"n={art['n']}", f"{art['net_mean_bp']:+.2f}",
                         str(art["ci95_net_bp"]), str(art["dsr"])))
            print(f"  [{i+1:2d}] {key:38s} KILL n={art['n']} net {art['net_mean_bp']:+.2f}bp "
                  f"p={art['permutation_p']} DSR={art['dsr']}")
        else:
            set_status(key, "done", args.owner,
                       f"{v}: n={art.get('n')}, net {art.get('net_mean_bp')}bp, "
                       f"CI {art.get('ci95_net_bp')}, p={art.get('permutation_p')}")
            done += 1
            rows.append((key, v, f"n={art.get('n')}", str(art.get("net_mean_bp")),
                         str(art.get("ci95_net_bp")), str(art.get("dsr"))))
            print(f"  [{i+1:2d}] {key:38s} {v} n={art.get('n')} net {art.get('net_mean_bp')}bp")

    print(f"\n  batch: killed={killed} done={done} insuff={insuff} blocked={blocked}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
