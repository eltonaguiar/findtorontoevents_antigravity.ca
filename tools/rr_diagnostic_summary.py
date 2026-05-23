"""R:R diagnostic-only daily summary — Option D from
reports/rr_band_per_asset_2026_05_04.md.

This is a READ-ONLY observability tool. It does NOT gate any picks. It
aggregates R:R band performance from closed_picks.json across multiple
slices (cross-class, per-asset, per-symbol-within-asset) so a hard gate
can be designed against actual per-pair PF, not a fabricated 5.81 number.

Per swarm review consensus (3/5 ship_now, 2/5 ship_with_caveats on D5):
the existing feat/rr-hard-gate-shadow-2026-05-04 branch (149fbacd)
targets the WORST cross-class band (1.5-2.0 PF 0.36 in live data) and
must NOT merge until per-(asset, symbol, band) data shows where the real
edge sits. This script is the data source for that decision.

Usage:
    python tools/rr_diagnostic_summary.py [--days N] [--out PATH]

    --days N  : restrict to picks closed in the last N days (default: all)
    --out PATH: write JSON summary to PATH (default: stdout only)

Output schema:
    {
      "as_of": "2026-05-04T...",
      "n_total": 7472,
      "n_with_rr": 7472,
      "cross_class": [{"band": "0-1.0", "n": ..., "wr": ..., "pf": ...}, ...],
      "by_asset_class": {"COMMODITY": [...], "FOREX": [...], ...},
      "buried_elites": [{"strategy": "...", "n": ..., "pf": ..., "sum_$": ...}],
      "buried_disasters": [...]
    }
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEDGER = REPO / "alpha_engine" / "data" / "closed_picks.json"

BANDS = [
    (0.0, 1.0, "0-1.0"),
    (1.0, 1.5, "1.0-1.5"),
    (1.5, 2.0, "1.5-2.0"),
    (2.0, 3.0, "2.0-3.0"),
    (3.0, 5.0, "3.0-5.0"),
    (5.0, 9999, "5.0+"),
]


def _band_for(rr: float) -> str | None:
    for lo, hi, name in BANDS:
        if lo <= rr < hi:
            return name
    return None


def _band_stats(picks_in_band: list[dict]) -> dict:
    pnls = [p["_pnl_pct"] for p in picks_in_band]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else (
        float("inf") if wins else 0.0
    )
    return {
        "n": len(pnls),
        "wins": len(wins),
        "losses": len(losses),
        "wr": round(100.0 * len(wins) / len(pnls), 2) if pnls else 0.0,
        "pf": round(pf, 4) if pf != float("inf") else "inf",
        "avg_pnl_pct": round(statistics.mean(pnls), 4) if pnls else 0.0,
        "sum_pnl_pct": round(sum(pnls), 4),
    }


def _hydrate_pick(p: dict, since_dt: datetime | None) -> dict | None:
    """Return augmented pick with _rr / _pnl_pct or None if unusable."""
    e = p.get("entry_price") or 0
    tp = p.get("take_profit") or 0
    sl = p.get("stop_loss") or 0
    pnl = p.get("pnl_pct")
    if not (e and tp and sl) or pnl is None:
        return None
    try:
        e, tp, sl, pnl = float(e), float(tp), float(sl), float(pnl)
    except (TypeError, ValueError):
        return None
    risk = abs(e - sl)
    reward = abs(tp - e)
    if risk <= 0:
        return None
    if since_dt:
        ts = p.get("closed_at") or p.get("exit_date") or p.get("entry_date")
        if not ts:
            return None
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt < since_dt:
                return None
        except (TypeError, ValueError):
            return None
    p2 = dict(p)
    p2["_rr"] = reward / risk
    p2["_pnl_pct"] = pnl
    return p2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=0,
                    help="Restrict to picks closed in last N days (default: all)")
    ap.add_argument("--out", type=str,
                    help="Write JSON summary to PATH (default: stdout only)")
    args = ap.parse_args()

    if not LEDGER.exists():
        print(f"FATAL: {LEDGER} does not exist.", file=sys.stderr)
        return 2

    raw = json.loads(LEDGER.read_text(encoding="utf-8"))
    picks = raw.get("picks", raw) if isinstance(raw, dict) else raw

    since_dt = None
    if args.days > 0:
        since_dt = datetime.now(timezone.utc) - timedelta(days=args.days)

    hydrated = [h for p in picks if (h := _hydrate_pick(p, since_dt))]

    # Cross-class buckets
    by_band: dict[str, list] = defaultdict(list)
    for p in hydrated:
        b = _band_for(p["_rr"])
        if b:
            by_band[b].append(p)
    cross_class = []
    for _, _, name in BANDS:
        if by_band[name]:
            row = _band_stats(by_band[name])
            row["band"] = name
            cross_class.append(row)

    # Per-asset-class buckets
    by_asset: dict[str, dict] = defaultdict(lambda: defaultdict(list))
    for p in hydrated:
        ac = (p.get("asset_class") or "UNTAGGED").upper()
        b = _band_for(p["_rr"])
        if b:
            by_asset[ac][b].append(p)
    by_asset_out = {}
    for ac, bands in by_asset.items():
        rows = []
        for _, _, name in BANDS:
            if bands[name]:
                row = _band_stats(bands[name])
                row["band"] = name
                rows.append(row)
        if rows:
            by_asset_out[ac] = rows

    # Buried elite/disaster strategies (n>=20, sort by sum dollar)
    by_strat = defaultdict(list)
    for p in hydrated:
        by_strat[(p.get("strategy", "?"), (p.get("asset_class") or "UNTAGGED").upper())].append(p)
    strat_rows = []
    for (s, ac), ps in by_strat.items():
        if len(ps) < 20:
            continue
        pnl_d = sum(float(p.get("pnl_dollar", 0) or 0) for p in ps)
        if abs(pnl_d) < 100:  # filter near-zero noise
            continue
        wins = [p for p in ps if p["_pnl_pct"] > 0]
        wr = 100.0 * len(wins) / len(ps)
        wins_pct = sum(p["_pnl_pct"] for p in wins)
        losses_pct = abs(sum(p["_pnl_pct"] for p in ps if p["_pnl_pct"] < 0))
        pf = wins_pct / losses_pct if losses_pct > 0 else (float("inf") if wins_pct > 0 else 0.0)
        strat_rows.append({
            "strategy": s, "asset_class": ac, "n": len(ps),
            "wr": round(wr, 2),
            "pf": round(pf, 4) if pf != float("inf") else "inf",
            "sum_dollar": round(pnl_d, 2),
        })
    strat_rows.sort(key=lambda r: r["sum_dollar"], reverse=True)
    elites = [r for r in strat_rows if (r["pf"] == "inf" or r["pf"] >= 1.5) and r["sum_dollar"] > 500][:10]
    disasters = sorted(
        [r for r in strat_rows if r["pf"] != "inf" and r["pf"] < 0.5 and r["sum_dollar"] < -500],
        key=lambda r: r["sum_dollar"],
    )[:10]

    summary = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "ledger": str(LEDGER),
        "n_total": len(picks),
        "n_with_rr": len(hydrated),
        "days_window": args.days or "all",
        "cross_class": cross_class,
        "by_asset_class": by_asset_out,
        "buried_elites": elites,
        "buried_disasters": disasters,
    }

    print(json.dumps(summary, indent=2, default=str))

    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        print(f"\nWrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
