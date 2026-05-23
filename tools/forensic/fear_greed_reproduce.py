#!/usr/bin/env python3
"""Forensic reproduction script for st_fear_greed_contrarian collapse.

READ-ONLY. Stdlib only. Stand-alone — run from repo root:

    python tools/forensic/fear_greed_reproduce.py

It scans 3 trade ledgers for any strategy variant matching 'fear_greed',
computes WR/PF/expectancy overall and in a trailing 48h window, walks
rolling 48h WR over the strategy lifetime, and dumps a plaintext summary
to stdout. No files are written, no gates touched.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

LEDGERS = [
    ("closed_picks",       REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"),
    ("universal_resolved", REPO_ROOT / "audit_trail"  / "data" / "universal_resolved_picks.json"),
    ("claudes_test_state", REPO_ROOT / "audit_dashboard" / "data" / "claudes_test_state.json"),
]

NAME_KEYS = ("strategy", "strategy_name", "source", "source_system", "system")
OUTCOME_KEYS = ("outcome", "result", "status", "exit_reason", "resolution")
PNL_KEYS = ("pnl_pct", "pnl", "return_pct", "return", "realized_pnl", "realized_return", "profit_pct")
TIME_KEYS = ("closed_at", "resolved_at", "exit_time", "close_time", "timestamp", "created_at", "entry_time")


def as_rows(obj):
    """Coerce whatever the JSON root is into a flat list of dict rows."""
    if isinstance(obj, list):
        return [r for r in obj if isinstance(r, dict)]
    if isinstance(obj, dict):
        out = []
        for v in obj.values():
            if isinstance(v, list):
                out.extend([r for r in v if isinstance(r, dict)])
            elif isinstance(v, dict):
                # nested: flatten one level
                for vv in v.values():
                    if isinstance(vv, list):
                        out.extend([r for r in vv if isinstance(r, dict)])
                    elif isinstance(vv, dict):
                        out.append(vv)
                out.append(v)
        return out
    return []


def load_json(path: Path):
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return as_rows(json.load(f))
    except Exception as e:
        print(f"[WARN] failed to load {path}: {e}", file=sys.stderr)
        return []


def row_strategy_name(row):
    for k in NAME_KEYS:
        v = row.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


def is_fear_greed(name: str) -> bool:
    n = (name or "").lower()
    return "fear_greed" in n or "feargreed" in n or "fng" in n


def row_time(row):
    for k in TIME_KEYS:
        v = row.get(k)
        if not v:
            continue
        if isinstance(v, (int, float)):
            try:
                return datetime.fromtimestamp(float(v), tz=timezone.utc)
            except Exception:
                continue
        if isinstance(v, str):
            s = v.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                continue
    return None


def row_outcome(row):
    """Return ('WIN'|'LOSS'|None, pnl_pct_or_None)."""
    pnl = None
    for k in PNL_KEYS:
        v = row.get(k)
        if isinstance(v, (int, float)):
            pnl = float(v)
            break
        if isinstance(v, str):
            try:
                pnl = float(v.replace("%", "").strip())
                break
            except Exception:
                pass
    label = None
    for k in OUTCOME_KEYS:
        v = row.get(k)
        if not isinstance(v, str):
            continue
        s = v.strip().upper()
        if s in ("WIN", "WON", "TP", "TAKE_PROFIT", "TAKE-PROFIT", "HIT_TP", "PROFIT"):
            label = "WIN"
            break
        if s in ("LOSS", "LOST", "SL", "STOP_LOSS", "STOP-LOSS", "HIT_SL", "LOSE"):
            label = "LOSS"
            break
    if label is None and pnl is not None:
        label = "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else None)
    return label, pnl


def stats(rows):
    wins = losses = 0
    gp = gl = 0.0
    for r in rows:
        lbl, pnl = row_outcome(r)
        if lbl == "WIN":
            wins += 1
            if pnl is not None and pnl > 0:
                gp += pnl
        elif lbl == "LOSS":
            losses += 1
            if pnl is not None and pnl < 0:
                gl += abs(pnl)
    n = wins + losses
    wr = (wins / n * 100) if n else 0.0
    pf = (gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0)
    # expectancy as avg pnl% across rows with any pnl
    pnls = [row_outcome(r)[1] for r in rows]
    pnls = [p for p in pnls if p is not None]
    exp = (sum(pnls) / len(pnls)) if pnls else 0.0
    return {
        "rows": len(rows),
        "resolved": n,
        "wins": wins,
        "losses": losses,
        "wr_pct": round(wr, 2),
        "pf": round(pf, 3) if pf != float("inf") else "inf",
        "expectancy_pct": round(exp, 4),
        "gross_profit": round(gp, 4),
        "gross_loss": round(gl, 4),
    }


def rolling_48h(rows):
    dated = []
    for r in rows:
        t = row_time(r)
        if t is None:
            continue
        lbl, pnl = row_outcome(r)
        if lbl is None:
            continue
        dated.append((t, lbl, pnl))
    dated.sort(key=lambda x: x[0])
    if not dated:
        return []
    out = []
    window = timedelta(hours=48)
    n = len(dated)
    i = 0
    for j in range(n):
        cutoff = dated[j][0] - window
        while i < j and dated[i][0] < cutoff:
            i += 1
        sub = dated[i:j + 1]
        wins = sum(1 for x in sub if x[1] == "WIN")
        losses = sum(1 for x in sub if x[1] == "LOSS")
        tot = wins + losses
        wr = (wins / tot * 100) if tot else 0.0
        gp = sum(x[2] for x in sub if x[1] == "WIN"  and x[2] is not None and x[2] > 0)
        gl = sum(abs(x[2]) for x in sub if x[1] == "LOSS" and x[2] is not None and x[2] < 0)
        pf = (gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0)
        out.append({
            "ts": dated[j][0].isoformat(),
            "n": tot,
            "wr_pct": round(wr, 2),
            "pf": round(pf, 3) if pf != float("inf") else None,
        })
    return out, dated[0][0], dated[-1][0]


def scan_strategy_names(all_rows):
    names = {}
    for r in all_rows:
        n = row_strategy_name(r)
        if not n:
            continue
        names[n] = names.get(n, 0) + 1
    return names


def main():
    print("=" * 72)
    print("st_fear_greed_contrarian forensic reproduction")
    print("repo root:", REPO_ROOT)
    print("=" * 72)

    combined_matches = []
    for label, path in LEDGERS:
        rows = load_json(path)
        names = scan_strategy_names(rows)
        fg_names = {n: c for n, c in names.items() if is_fear_greed(n)}
        matches = [r for r in rows if is_fear_greed(row_strategy_name(r))]
        print(f"\n--- ledger: {label}  ({path.name})")
        print(f"  total rows: {len(rows)}")
        print(f"  distinct strategies: {len(names)}")
        print(f"  fear_greed variants: {fg_names or '(none)'}")
        if not matches:
            continue
        overall = stats(matches)
        print(f"  OVERALL stats: {overall}")

        # last 48h window
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=48)
        last48 = [r for r in matches if (row_time(r) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
        print(f"  LAST-48h rows: {len(last48)}  stats: {stats(last48) if last48 else '(none)'}")

        roll, first_t, last_t = rolling_48h(matches)
        if roll:
            print(f"  lifetime span: {first_t.isoformat()} -> {last_t.isoformat()}")
            peak = max(roll, key=lambda x: (x["wr_pct"], x["n"]))
            print(f"  peak rolling-48h WR: {peak}")
            # first drop below 50%
            collapse = next((x for x in roll if x["n"] >= 10 and x["wr_pct"] < 50.0), None)
            print(f"  first <50% rolling-48h (n>=10): {collapse}")
            print(f"  final rolling-48h point: {roll[-1]}")

        for r in matches:
            combined_matches.append((label, r))

    print("\n" + "=" * 72)
    print(f"combined matches across all ledgers: {len(combined_matches)}")
    if combined_matches:
        print("stats across combined:", stats([r for _, r in combined_matches]))
    print("=" * 72)


if __name__ == "__main__":
    main()
