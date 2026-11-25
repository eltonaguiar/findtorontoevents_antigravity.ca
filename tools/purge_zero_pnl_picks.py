#!/usr/bin/env python3
"""P0.0a — Purge/quarantine zero-PnL rows from closed_picks.json.

Grok external review (2026-11-20): ~69% of resolved trades have zero PnL.
These rows are either genuinely zero (timeout/expiry) or un-resolved/placeholder.
They must be quarantined before any statistical analysis — otherwise every
backtest is garbage.

Safe to re-run: idempotent (only touches rows where pnl_pct == 0).
Dry-run by default. Pass --apply to actually mutate the file.

Usage:
    python3 tools/purge_zero_pnl_picks.py
    python3 tools/purge_zero_pnl_picks.py --apply
    python3 tools/purge_zero_pnl_picks.py --source alpha_engine/data/closed_picks_enriched.json
"""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _is_zero_pnl(p: dict) -> bool:
    """True if pnl_pct is exactly 0 or null/missing."""
    pp = p.get("pnl_pct")
    if pp is None:
        return True
    try:
        return float(pp) == 0.0
    except (TypeError, ValueError):
        return True


def _quarantine_reason(p: dict) -> str:
    """Human-readable reason for quarantining."""
    pp = p.get("pnl_pct")
    if pp is None:
        return "null_pnl"
    try:
        if float(pp) == 0.0:
            ep = p.get("entry_price")
            xp = p.get("exit_price")
            if ep is not None and xp is not None and abs(float(ep) - float(xp)) > 1e-9:
                return "suspicious_zero_pnl_with_price_move"
            return "genuine_zero_pnl"
    except (TypeError, ValueError):
        return "unparseable_pnl"
    return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="alpha_engine/data/closed_picks.json")
    ap.add_argument("--quarantine", default="alpha_engine/data/closed_picks_quarantined.json")
    ap.add_argument("--apply", action="store_true", help="Mutate the file. Default is dry-run.")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.exists():
        raise SystemExit(f"Source not found: {src}")

    data = json.loads(src.read_text())
    picks = data if isinstance(data, list) else data.get("picks", data)

    keep = []
    quarantine = []
    for p in picks:
        if _is_zero_pnl(p):
            quarantine.append({
                "pick": p,
                "reason": _quarantine_reason(p),
                "quarantined_at": datetime.now(timezone.utc).isoformat(),
            })
        else:
            keep.append(p)

    # Summary
    from collections import Counter
    reasons = Counter(q["reason"] for q in quarantine)
    print(f"Total picks: {len(picks)}")
    print(f"Keep (non-zero pnl): {len(keep)}")
    print(f"Quarantine (zero/null pnl): {len(quarantine)}")
    for r, n in reasons.items():
        print(f"  {r}: {n}")

    # Write report
    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    report_path = out_dir / "purge_zero_pnl_report.json"
    report_path.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(src),
        "applied": args.apply,
        "total_picks": len(picks),
        "kept": len(keep),
        "quarantined": len(quarantine),
        "reasons": dict(reasons),
        "quarantine_rate_pct": round(100.0 * len(quarantine) / len(picks), 2) if picks else 0,
    }, indent=2))
    print(f"Report written: {report_path}")

    if args.apply:
        bak = src.with_suffix(".json.bak.purge")
        shutil.copy2(src, bak)
        quarantine_path = Path(args.quarantine)
        quarantine_path.write_text(json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": str(src),
            "quarantined_count": len(quarantine),
            "rows": quarantine,
        }, indent=2))
        # Write kept picks back
        if isinstance(data, list):
            src.write_text(json.dumps(keep, indent=2))
        else:
            data["picks"] = keep
            src.write_text(json.dumps(data, indent=2))
        print(f"Applied. Backup at {bak}")
        print(f"Quarantine file: {quarantine_path}")
    else:
        print("Dry-run only. Re-run with --apply to mutate.")


if __name__ == "__main__":
    main()
