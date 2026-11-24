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
    ap.add_argument("--owner", default="copilot")
    args = ap.parse_args(argv)

    done = killed = blocked = insuff = 0
    rows = []
    for i in range(args.n):
        cell = claim(args.owner)
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
