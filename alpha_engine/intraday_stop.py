"""intraday_stop.py - keep CRYPTO/ETF INTRADAY picks out of the money path.

Measured, not assumed. ``tools/alpha_slice_scan.py`` scored the 2026-11-19
closed book (2,475 picks, 73 slices, Benjamini-Hochberg across the whole batch)
and found exactly two pre-committable slices whose picks lose to simply holding
the same instrument over the same window:

    class_tf:CRYPTO/INTRADAY  -0.155%/pick  CI [-0.260, -0.053]  n=1581  q=0.015
    class_tf:ETF/INTRADAY     -0.265%/pick  CI [-0.488, -0.033]  n= 256  q=0.073

Evidence: ``reports/alpha_slice_scan_2026-11-19.json``.

The stop does not delete anything. Every pick keeps its row and gains

    money_path    True/False - may this row be sized?
    shadow        True       - measured out of the money path, still tracked
    shadow_reason 'intraday_stop:<CLASS>/<TIMEFRAME>' when shadowed

so the shadow book keeps accruing the evidence that would let the policy be
reversed (a class x timeframe slice that turns positive retires itself).

Usage
-----
  python3 alpha_engine/intraday_stop.py --rows /tmp/alpha_rows.jsonl \\
      --json-out reports/intraday_stop_effect_2026-11-19.json
  python3 alpha_engine/intraday_stop.py --picks audit_dashboard/data/dashboard_data.json \\
      --out /tmp/annotated.json

Exit codes: 0 written; 2 nothing usable to read.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

POLICY_ID = "intraday-stop-2026-11-19"
EVIDENCE = "reports/alpha_slice_scan_2026-11-19.json"

#: (asset_class, timeframe) pairs measured to lose to holding the same thing.
SHADOW_ONLY: set[tuple[str, str]] = {("CRYPTO", "INTRADAY"), ("ETF", "INTRADAY")}

POLICY: dict[str, Any] = {
    "policy_id": POLICY_ID,
    "evidence": EVIDENCE,
    "rule": ("rows whose (asset_class, trade_timeframe) is in SHADOW_ONLY stay in the "
             "payload as shadow rows and are excluded from the money path"),
    "slices": {
        "class_tf:CRYPTO/INTRADAY": {"alpha_pct": -0.155, "alpha_ci": [-0.260, -0.053],
                                     "n": 1581, "q": 0.015},
        "class_tf:ETF/INTRADAY": {"alpha_pct": -0.265, "alpha_ci": [-0.488, -0.033],
                                  "n": 256, "q": 0.073},
    },
    "reversal": ("re-run tools/alpha_slice_scan.py; a slice that turns positive and "
                 "survives BH is removed from SHADOW_ONLY"),
}

TF_KEYS = ("trade_timeframe", "timeframe", "tf")
BUCKETS = ("active", "smart_picks", "recent_closed")


def _norm(value: Any) -> str:
    return str(value or "").strip().upper()


def timeframe_of(pick: dict) -> str:
    """The pick's timeframe, whichever key the emitter used."""
    for key in TF_KEYS:
        val = _norm(pick.get(key))
        if val:
            return val
    return ""


def is_shadow_only(asset_class: Any, timeframe: Any) -> bool:
    return (_norm(asset_class), _norm(timeframe)) in SHADOW_ONLY


def annotate_pick(pick: dict) -> dict:
    """Return a copy carrying money_path / shadow / shadow_reason."""
    out = dict(pick)
    ac, tf = _norm(pick.get("asset_class")), timeframe_of(pick)
    if is_shadow_only(ac, tf):
        out["money_path"] = False
        out["shadow"] = True
        out["shadow_reason"] = f"intraday_stop:{ac}/{tf}"
    else:
        out.setdefault("money_path", True)
        out.setdefault("shadow", False)
    return out


def annotate_picks(picks: list[dict]) -> dict[str, Any]:
    """Annotate a list in place; return counts. Never drops a row."""
    shadow = 0
    for i, pick in enumerate(picks):
        if not isinstance(pick, dict):
            continue
        new = annotate_pick(pick)
        picks[i] = new
        if new.get("shadow"):
            shadow += 1
    total = len(picks)
    return {
        "total": total,
        "shadow": shadow,
        "money_path": total - shadow,
        "policy_id": POLICY_ID,
        "by_slice": {f"{ac}/{tf}": {"shadow": sum(
            1 for p in picks if isinstance(p, dict)
            and _norm(p.get("asset_class")) == ac and timeframe_of(p) == tf)}
            for ac, tf in sorted(SHADOW_ONLY)},
    }


MONEY_PATH_BUCKET = "smart_picks"
SHADOW_BUCKET = "shadow_picks"


def annotate_buckets(buckets: dict, partition_money_path: bool = True) -> dict[str, Any]:
    """Annotate payload['picks'] and move shadow rows out of the sizing list.

    ``active`` and ``recent_closed`` keep every row (research view, flagged).
    ``smart_picks`` is the sizing list, so rows measured out of the money path are
    moved - not deleted - into ``shadow_picks``.
    """
    out: dict[str, Any] = {"policy_id": POLICY_ID, "evidence": EVIDENCE,
                           "total": 0, "shadow": 0, "money_path": 0,
                           "moved_to_shadow_picks": 0, "buckets": {}}
    for name in BUCKETS:
        rows = buckets.get(name)
        if not isinstance(rows, list):
            continue
        summary = annotate_picks(rows)
        if partition_money_path and name == MONEY_PATH_BUCKET:
            keep = [p for p in rows if not (isinstance(p, dict) and p.get("money_path") is False)]
            moved = [p for p in rows if isinstance(p, dict) and p.get("money_path") is False]
            if moved:
                buckets[name] = keep
                buckets[SHADOW_BUCKET] = list(buckets.get(SHADOW_BUCKET) or []) + moved
                summary = {**summary, "money_path": len(keep), "shadow": len(moved)}
                out["moved_to_shadow_picks"] += len(moved)
                out["buckets"][SHADOW_BUCKET] = {
                    "total": len(moved), "shadow": len(moved), "money_path": 0}
        out["buckets"][name] = summary
        for key in ("total", "shadow", "money_path"):
            out[key] += summary[key]
    return out


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def alpha_effect(rows: Iterable[dict]) -> dict[str, Any]:
    """Mean selection alpha with the stop on vs off, overall and per class.

    ``rows`` are per-pick records from
    ``audit3_selection_alpha.py --rows-out`` (keys: class, timeframe, alpha).
    """
    kept: list[dict] = []
    shadow: list[dict] = []
    for r in rows:
        ac = _norm(r.get("asset_class") or r.get("class"))
        alpha = r.get("alpha", r.get("alpha_pct"))
        if alpha is None:
            continue
        rec = {"class": ac, "timeframe": _norm(r.get("timeframe") or r.get("trade_timeframe")),
               "alpha": float(alpha)}
        (shadow if is_shadow_only(rec["class"], rec["timeframe"]) else kept).append(rec)

    def block(items: list[dict]) -> dict[str, Any]:
        return {"n": len(items), "mean_alpha_pct": _mean([i["alpha"] for i in items])}

    per_class: dict[str, Any] = {}
    for cls in sorted({r["class"] for r in kept + shadow}):
        k = [r["alpha"] for r in kept if r["class"] == cls]
        s = [r["alpha"] for r in shadow if r["class"] == cls]
        per_class[cls] = {
            "kept": {"n": len(k), "mean_alpha_pct": _mean(k)},
            "shadow": {"n": len(s), "mean_alpha_pct": _mean(s)},
            "mean_alpha_pct_with_stop": _mean(k) if k else None,
            "mean_alpha_pct_without_stop": _mean(k + s) if (k or s) else None,
        }
    all_rows = kept + shadow
    before, after = _mean([r["alpha"] for r in all_rows]), _mean([r["alpha"] for r in kept])
    return {
        "policy_id": POLICY_ID,
        "evidence": EVIDENCE,
        "rows_scored": len(all_rows),
        "money_path": block(kept),
        "shadow": block(shadow),
        "book_mean_alpha_pct_without_stop": before,
        "book_mean_alpha_pct_with_stop": after,
        "improvement_pct_per_pick": (round(after - before, 4)
                                     if before is not None and after is not None else None),
        "per_class": per_class,
        "note": ("alpha is pick net return minus the direction-adjusted hold over the "
                 "same window, in percent per pick; positive means the pick beat doing "
                 "nothing. Mean alpha is not a portfolio return."),
    }


def _load_rows(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CRYPTO/ETF INTRADAY money-path stop")
    ap.add_argument("--rows", help="per-pick JSONL from audit3_selection_alpha --rows-out")
    ap.add_argument("--picks", help="payload JSON (dict with picks, or a list of picks)")
    ap.add_argument("--out", help="write the annotated picks payload here")
    ap.add_argument("--json-out", help="write the alpha-effect / policy report here")
    args = ap.parse_args(argv)
    rc = 0
    if args.rows:
        effect = alpha_effect(_load_rows(args.rows))
        print(json.dumps({k: effect[k] for k in (
            "rows_scored", "book_mean_alpha_pct_without_stop",
            "book_mean_alpha_pct_with_stop", "improvement_pct_per_pick")}, indent=1))
        for cls, blk in effect["per_class"].items():
            print(f"  {cls:<10} kept n={blk['kept']['n']:<5} "
                  f"{blk['kept']['mean_alpha_pct']}  shadow n={blk['shadow']['n']:<5} "
                  f"{blk['shadow']['mean_alpha_pct']}")
        if args.json_out:
            Path(args.json_out).write_text(json.dumps({**POLICY, **effect}, indent=1) + "\n")
            print(f"wrote {args.json_out}")
        rc = 0 if effect["rows_scored"] else 2
    if args.picks:
        data = json.loads(Path(args.picks).read_text())
        if isinstance(data, dict) and isinstance(data.get("picks"), dict):
            summary = annotate_buckets(data["picks"])
        elif isinstance(data, dict) and isinstance(data.get("picks"), list):
            summary = annotate_picks(data["picks"])
        elif isinstance(data, list):
            data = {"picks": data}
            summary = annotate_picks(data["picks"])
        else:
            print("no picks found in payload", file=sys.stderr)
            return 2
        print(f"annotated total={summary['total']} shadow={summary['shadow']} "
              f"money_path={summary['money_path']}")
        if args.out:
            Path(args.out).write_text(json.dumps(data, default=str) + "\n")
            print(f"wrote {args.out}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
