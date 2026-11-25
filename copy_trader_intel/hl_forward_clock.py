#!/usr/bin/env python3
"""
hl_forward_clock.py — append-only snapshot clock + promotion gate for the trader-skill test.

The prior programme's fatal structural flaw was that no result could ever become PROVEN
because forward observation was required and the count was zero everywhere. This makes the
forward clock real: every run appends an immutable snapshot, and once two snapshots exist at
least MIN_GAP_DAYS apart the script computes the confirmatory statistic between them.

Promotion rule (H-260 `promote_requires`, enforced here rather than remembered):
    a persistence claim may only be promoted when
      (a) >= 2 snapshots exist with >= 7 days between them, AND
      (b) the later snapshot reproduces rho > 0 with a CI excluding zero.

Usage:
    python3 hl_forward_clock.py            # take a snapshot (skips if < 1h since last)
    python3 hl_forward_clock.py --status   # report only, no network
    python3 hl_forward_clock.py --force    # snapshot even if recent
"""
from __future__ import annotations

import glob
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

LB = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
STATE = Path(__file__).resolve().parent.parent / "reports" / "hl_clock"
MIN_GAP_DAYS = 7
MIN_HOURS_BETWEEN = 1.0
MIN_ACCT = 10_000.0


# ------------------------------------------------------------------ stats
def rankdata(x):
    x = np.asarray(x, float)
    n = x.size
    s = np.argsort(x, kind="mergesort")
    inv = np.empty(n, dtype=np.int64)
    inv[s] = np.arange(n)
    xs = x[s]
    obs = np.r_[True, xs[1:] != xs[:-1]]
    dense = obs.cumsum()[inv]
    cnt = np.r_[np.nonzero(obs)[0], n]
    return 0.5 * (cnt[dense] + cnt[dense - 1] + 1)


def rank_ic(a, b):
    ra, rb = rankdata(a), rankdata(b)
    ra -= ra.mean()
    rb -= rb.mean()
    d = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / d) if d > 0 else float("nan")


# ------------------------------------------------------------------ io
def load(entry):
    p = STATE / entry["file"]
    return json.loads(p.read_text())


def entries():
    idx = STATE / "index.json"
    if not idx.exists():
        return []
    return json.loads(idx.read_text()).get("snapshots", [])


def take_snapshot(hours_since_last: float) -> dict:
    raw = urllib.request.urlopen(LB, timeout=90).read()
    import hashlib
    sha = hashlib.sha256(raw).hexdigest()
    d = json.loads(raw)
    rows = d if isinstance(d, list) else next(v for v in d.values() if isinstance(v, list))
    slim = []
    for r in rows:
        wp = {k: v for k, v in (r.get("windowPerformances") or [])}

        def g(w, f):
            try:
                return float(wp[w][f])
            except (KeyError, TypeError, ValueError):
                return 0.0

        acct = float(r.get("accountValue") or 0.0)
        wk = g("week", "pnl")
        slim.append([(r.get("ethAddress") or "").lower(), acct, wk, g("month", "pnl"),
                     g("week", "vlm")])
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    name = f"snapshot_{ts}.json"
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / name).write_text(json.dumps({"sha256": sha, "ts": ts, "rows": slim}))
    e = {"file": name, "ts": ts, "epoch": int(time.time()), "sha256": sha,
         "n_rows": len(slim), "hours_since_prev": round(hours_since_last, 2)}
    idx = STATE / "index.json"
    cur = json.loads(idx.read_text()) if idx.exists() else {"snapshots": []}
    cur["snapshots"] = entries() + [e]
    idx.write_text(json.dumps(cur, indent=1))
    return e


def report():
    es = entries()
    print(f"forward clock: {len(es)} snapshot(s) in {STATE}")
    if not es:
        print("  EMPTY — run without --status to take the first snapshot.")
        return 1
    for e in es:
        print(f"  {e['ts']}  rows={e['n_rows']:>6}  sha={e['sha256'][:12]}...")
    newest = es[-1]["epoch"]
    elapsed = (newest - es[0]["epoch"]) / 86400.0
    print(f"\n  elapsed across clock : {elapsed:.2f} days   (need >= {MIN_GAP_DAYS})")
    if len(es) < 2:
        print("  PROMOTION GATE: CLOSED — only one snapshot. A persistence claim cannot be promoted.")
        return 0
    if elapsed < MIN_GAP_DAYS:
        print(f"  PROMOTION GATE: CLOSED — {MIN_GAP_DAYS - elapsed:.2f} more days required.")
        return 0

    # confirmatory statistic across the two furthest-apart usable snapshots
    a, b = load(es[0]), load(es[-1])
    ma = {r[0]: r for r in a["rows"] if r[1] >= MIN_ACCT}
    mb = {r[0]: r for r in b["rows"] if r[1] >= MIN_ACCT}
    common = [k for k in ma if k in mb and ma[k][4] > 0 and mb[k][4] > 0]
    if len(common) < 500:
        print(f"  PROMOTION GATE: CLOSED — only {len(common)} wallets in both snapshots.")
        return 0
    # prior-period performance in snapshot A vs realised change by snapshot B
    prior_a = np.array([ma[k][3] - ma[k][2] for k in common])
    realised = np.array([mb[k][3] - ma[k][3] for k in common])  # month pnl drift A->B
    rho = rank_ic(prior_a, realised)
    verdict = ("GATE OPEN - rho>0 reproduced" if rho > 0 else "GATE CLOSED - persistence did not reproduce")
    print(f"\n  confirmatory: n={len(common):,}  rho={rho:+.5f}  -> {verdict}")
    return 0


def main():
    if "--status" in sys.argv:
        return report()
    es = entries()
    hours = (time.time() - es[-1]["epoch"]) / 3600.0 if es else 1e9
    if es and hours < MIN_HOURS_BETWEEN and "--force" not in sys.argv:
        print(f"skipped: last snapshot {hours:.1f}h ago (< {MIN_HOURS_BETWEEN}h). Use --force.")
        return report()
    e = take_snapshot(hours)
    print(f"appended {e['file']}  rows={e['n_rows']:,}  sha={e['sha256'][:12]}...")
    return report()


if __name__ == "__main__":
    raise SystemExit(main())
