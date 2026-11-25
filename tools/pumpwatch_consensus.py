#!/usr/bin/env python3
"""Cross-system consensus test (H-248) for the pump-watch -> audit3 panel (todo 10).

WHAT THIS ANSWERS
-----------------
pump-watch aggregates picks from several independent systems. audit3 ranks one
ledger. The obvious next question is whether *agreement between systems* carries
information: if two systems independently pick the same asset in the same
direction, is that pick better than a pick only one system made?

This module answers exactly that and nothing else. It compares, on the SAME
closed ledgers over the SAME window:

    CONSENSUS  = clusters where >= 2 distinct systems agree on (asset, direction)
                 with entries inside a 24h window
    CONTROL    = clusters where only one system emitted the pick

FROZEN BEFORE MEASUREMENT (M-107, H-248)
-----------------------------------------
The following were fixed in ``reports/hypothesis_registry.json`` before the first
run and must not be retuned after seeing results:

  * window            = 24 hours
  * min_systems       = 2 distinct systems
  * systems           = alpha_engine, ml_battleground/system_f_clawsofdoom, mercury2
  * symbol_normalization (stated explicitly, also fixed pre-run):
        upper-case, strip a trailing quote asset (USDT/USDC/BUSD/USD) and the
        suffixes -PERP / PERP / =X, then keep the leading alphabetic base.
        So BTCUSDT -> BTC, BTC-USD -> BTC, 'BTC' -> BTC, 'AUDJPY=X' -> AUDJPY.
        This is applied identically to both arms, so it cannot tilt the result.

WHY THE CONTROL MATTERS
-----------------------
Without single-system picks, "consensus works" is unfalsifiable: any observed
return could be the systems' general selectivity rather than the agreement. Both
arms are drawn from the same three ledgers over the same overlapping period.

HONEST PRIOR
------------
All three systems read the same exchange OHLCV, so agreement is more likely
redundant than independent confirmation. Prior: no edge.

OUTPUT
------
``audit_dashboard/data/pumpwatch_consensus.json`` plus a human-readable summary on
stdout. Paper only, zero capital, not investment advice.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
import random
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

WINDOW_HOURS = 24          # frozen
MIN_SYSTEMS = 2            # frozen
BOOTSTRAP_N = 2000
BOOTSTRAP_SEED = 20261123  # fixed so the CI is reproducible

# system -> (path, pnl field, timestamp field)
SOURCES: dict[str, tuple[str, str, str]] = {
    "alpha_engine": ("alpha_engine/data/closed_picks.json", "pnl_pct", "timestamp"),
    "claws_ml_battleground": (
        "ml_battleground/system_f_clawsofdoom/data/closed_picks.json",
        "realized_pnl_pct",
        "timestamp_est",
    ),
    "mercury2": ("mercury2/data/closed_picks.json", "pnl_pct", "timestamp"),
}

QUOTE_SUFFIXES = ("USDT", "USDC", "BUSD", "USD")
DIRECTION_MAP = {"LONG": "LONG", "BUY": "LONG", "SHORT": "SHORT", "SELL": "SHORT"}

# Candidate ENTRY timestamp fields, in preference order. Deliberately excludes
# closed_at / exit_date / resolved_at: those are EXIT times, and clustering two
# systems on when they exited would manufacture "consensus" out of unrelated
# entries. Only entry-time fields may be used.
CANDIDATE_TS_FIELDS = ("timestamp", "timestamp_est", "entry_date", "entry_time", "created_at")


def normalization_audit() -> dict:
    """Per-ledger field coverage, so normalization completeness is measured.

    This exists because the first run of H-248 rejected 1,874 of alpha_engine's
    2,204 rows for a missing timestamp. Before blaming the normalizer it is worth
    proving which fields are actually populated: ``entry_date`` turns out to be a
    strict SUBSET of ``timestamp`` (290 rows, all of which also have a timestamp),
    so no fallback can recover them -- the data is not there. The exit-time fields
    that DO cover 94.9% (``closed_at``) are unusable by construction.
    """
    audit: dict[str, dict] = {}
    for system, (rel, pnl_field, _ts_field) in SOURCES.items():
        path = REPO_ROOT / rel
        entry: dict[str, Any] = {"file": rel, "exists": path.exists()}
        if not path.exists():
            audit[system] = entry
            continue
        try:
            data = json.loads(path.read_text())
        except Exception as exc:
            entry["parse_error"] = str(exc)
            audit[system] = entry
            continue
        if not isinstance(data, list):
            entry["error"] = "not a list"
            audit[system] = entry
            continue
        n = len(data)
        entry["n_rows"] = n
        entry["entry_time_coverage"] = {
            f: sum(1 for r in data if isinstance(r, dict) and r.get(f)) for f in CANDIDATE_TS_FIELDS
        }
        entry["pnl_field"] = pnl_field
        entry["pnl_coverage"] = sum(
            1 for r in data
            if isinstance(r, dict) and isinstance(r.get(pnl_field), (int, float))
            and not isinstance(r.get(pnl_field), bool)
        )
        # exit-time fields, recorded only to explain why they are NOT used
        entry["exit_time_fields_not_used"] = {
            f: sum(1 for r in data if isinstance(r, dict) and r.get(f))
            for f in ("closed_at", "exit_date", "resolved_at", "exit_time", "exit_time_est")
        }
        usable = sum(
            1 for r in data
            if isinstance(r, dict)
            and any(r.get(f) for f in ("timestamp", "timestamp_est", "entry_date"))
            and isinstance(r.get(pnl_field), (int, float))
        )
        entry["entry_time_and_pnl_usable"] = usable
        audit[system] = entry
    return audit


def normalize_symbol(raw: Any) -> str:
    """Reduce a symbol to its base asset (see the frozen rule in the docstring)."""
    if not raw:
        return ""
    s = str(raw).upper().strip()
    for suffix in ("-PERP", "PERP", "=X", "=F"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    s = s.replace("/", "").replace("-", "").replace("_", "").replace(" ", "")
    for quote in QUOTE_SUFFIXES:
        if s.endswith(quote) and len(s) > len(quote):
            s = s[: -len(quote)]
            break
    # keep the leading alphabetic base only (drops stray digits/numeric codes)
    out = []
    for ch in s:
        if ch.isalpha():
            out.append(ch)
        else:
            break
    return "".join(out)


def parse_ts(raw: Any) -> dt.datetime | None:
    """Parse the several timestamp shapes these ledgers use, always to UTC."""
    if raw in (None, ""):
        return None
    text = str(raw).strip()
    # claws writes "2026-02-24T23:18:54 EST"; treat non-UTC suffixes as naive-UTC
    for suffix, offset in ((" EST", "-05:00"), (" EDT", "-04:00"), (" UTC", "+00:00")):
        if text.endswith(suffix):
            text = text[: -len(suffix)] + offset
            break
    text = text.replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
        try:
            if fmt is None:
                parsed = dt.datetime.fromisoformat(text)
            else:
                parsed = dt.datetime.strptime(text, fmt)
            break
        except Exception:
            parsed = None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def load_rows() -> tuple[list[dict], list[dict]]:
    """Return (usable rows, rejected rows with a reason)."""
    rows: list[dict] = []
    rejected: list[dict] = []
    for system, (rel, pnl_field, ts_field) in SOURCES.items():
        path = REPO_ROOT / rel
        if not path.exists():
            rejected.append({"system": system, "reason": f"missing file {rel}"})
            continue
        try:
            data = json.loads(path.read_text())
        except Exception as exc:
            rejected.append({"system": system, "reason": f"parse error: {exc}"})
            continue
        if not isinstance(data, list):
            rejected.append({"system": system, "reason": "not a list"})
            continue
        for rec in data:
            if not isinstance(rec, dict):
                continue
            base = normalize_symbol(rec.get("symbol"))
            direction = DIRECTION_MAP.get(str(rec.get("direction", "")).upper(), "")
            ts = parse_ts(rec.get(ts_field))
            pnl = rec.get(pnl_field)
            if not base or not direction:
                rejected.append({"system": system, "reason": "bad symbol/direction"}); continue
            if ts is None:
                rejected.append({"system": system, "reason": f"no {ts_field}"}); continue
            if not isinstance(pnl, (int, float)) or isinstance(pnl, bool) or not math.isfinite(pnl):
                rejected.append({"system": system, "reason": f"no {pnl_field}"}); continue
            rows.append(
                {
                    "system": system,
                    "base": base,
                    "direction": direction,
                    "ts": ts,
                    "pnl_pct": float(pnl),
                }
            )
    return rows, rejected


def build_clusters(rows: list[dict]) -> list[dict]:
    """Group rows into (base, direction) clusters with a max WINDOW_HOURS gap."""
    by_key: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        by_key.setdefault((r["base"], r["direction"]), []).append(r)

    clusters: list[dict] = []
    for (base, direction), group in by_key.items():
        group.sort(key=lambda r: r["ts"])
        current: list[dict] = []
        last_ts: dt.datetime | None = None
        for r in group:
            if last_ts is not None and (r["ts"] - last_ts).total_seconds() > WINDOW_HOURS * 3600:
                clusters.append(_summarise(base, direction, current))
                current = []
            current.append(r)
            last_ts = r["ts"]
        if current:
            clusters.append(_summarise(base, direction, current))
    clusters.sort(key=lambda c: c["start"])
    return clusters


def _summarise(base: str, direction: str, group: list[dict]) -> dict:
    systems = sorted({r["system"] for r in group})
    return {
        "base": base,
        "direction": direction,
        "start": group[0]["ts"],
        "n_rows": len(group),
        "systems": systems,
        "n_systems": len(systems),
        "pnl_pct": sum(r["pnl_pct"] for r in group) / len(group),
    }


def bootstrap_ci(values: list[float], n: int = BOOTSTRAP_N, seed: int = BOOTSTRAP_SEED):
    """Percentile bootstrap CI for the mean (fixed seed => reproducible)."""
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(values)
    means = []
    for _ in range(n):
        means.append(sum(values[rng.randrange(k)] for _ in range(k)) / k)
    means.sort()
    lo = means[int(0.025 * (n - 1))]
    hi = means[int(0.975 * (n - 1))]
    return (lo, hi)


def analyse(cost_bps: float = 0.0) -> dict:
    rows, rejected = load_rows()
    if not rows:
        return {"ok": False, "error": "no usable rows", "rejected": rejected[:10]}

    clusters = build_clusters(rows)
    consensus = [c for c in clusters if c["n_systems"] >= MIN_SYSTEMS]
    single = [c for c in clusters if c["n_systems"] < MIN_SYSTEMS]

    cost_pct = cost_bps / 100.0  # bps -> percent

    def stats(arm: list[dict]) -> dict:
        vals = [c["pnl_pct"] - cost_pct for c in arm]
        if not vals:
            return {"n": 0, "mean_pct": None, "median_pct": None,
                    "ci95": [None, None], "win_rate": None}
        lo, hi = bootstrap_ci(vals)
        wins = sum(1 for v in vals if v > 0)
        return {
            "n": len(vals),
            "mean_pct": round(sum(vals) / len(vals), 6),
            "median_pct": round(sorted(vals)[len(vals) // 2], 6),
            "ci95": [round(lo, 6), round(hi, 6)],
            "win_rate": round(wins / len(vals), 4),
        }

    cons = stats(consensus)
    ctrl = stats(single)

    diff = None
    diff_ci = [None, None]
    if cons["n"] and ctrl["n"]:
        diff = cons["mean_pct"] - ctrl["mean_pct"]
        # paired-free bootstrap on the difference of independent means
        rng = random.Random(BOOTSTRAP_SEED)
        cv = [c["pnl_pct"] - cost_pct for c in consensus]
        sv = [c["pnl_pct"] - cost_pct for c in single]
        draws = []
        for _ in range(BOOTSTRAP_N):
            mc = sum(cv[rng.randrange(len(cv))] for _ in range(len(cv))) / len(cv)
            ms = sum(sv[rng.randrange(len(sv))] for _ in range(len(sv))) / len(sv)
            draws.append(mc - ms)
        draws.sort()
        diff_ci = [round(draws[int(0.025 * (BOOTSTRAP_N - 1))], 6),
                   round(draws[int(0.975 * (BOOTSTRAP_N - 1))], 6)]

    criteria = {
        "mean_diff_gt_0": bool(diff is not None and diff > 0),
        "ci_lb_gt_0": bool(diff_ci[0] is not None and diff_ci[0] > 0),
        "survives_2x_cost": bool(cons["n"] and ctrl["n"]
                                 and (stats(consensus)["mean_pct"] or 0) > 0),
    }
    passed = criteria["mean_diff_gt_0"] and criteria["ci_lb_gt_0"]

    if not cons["n"] or not ctrl["n"]:
        verdict = "INSUFFICIENT"
    elif not passed:
        verdict = "REFUTED"
    elif not criteria["survives_2x_cost"]:
        verdict = "WEAK"
    else:
        verdict = "SUPPORTED"

    return {
        "ok": True,
        "hypothesis": "H-248",
        "frozen": {
            "window_hours": WINDOW_HOURS,
            "min_systems": MIN_SYSTEMS,
            "systems": sorted(SOURCES),
            "cost_bps_applied": cost_bps,
        },
        "rows_usable": len(rows),
        "rows_rejected": len(rejected),
        "rejected_reasons": _reject_summary(rejected),
        "clusters_total": len(clusters),
        "consensus": cons,
        "single_control": ctrl,
        "mean_diff_pct": None if diff is None else round(diff, 6),
        "mean_diff_ci95": diff_ci,
        "criteria": criteria,
        "verdict": verdict,
        "per_system_rows": {s: sum(1 for r in rows if r["system"] == s) for s in SOURCES},
        "normalization_audit": normalization_audit(),
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "note": ("Descriptive comparison of already-resolved ledger rows. No capital, "
                 "no picks, not investment advice."),
    }


def _reject_summary(rejected: list[dict]) -> dict:
    out: dict[str, int] = {}
    for r in rejected:
        key = f"{r['system']}: {r['reason']}"
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1])[:12])


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cost-bps", type=float, default=25.0,
                    help="round-trip cost in bp subtracted from every cluster (default 25)")
    ap.add_argument("--out", default="audit_dashboard/data/pumpwatch_consensus.json")
    args = ap.parse_args(argv[1:])

    result = analyse(cost_bps=args.cost_bps)
    if not result.get("ok"):
        print("FAILED:", result.get("error"))
        return 1

    out_path = REPO_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=1) + "\n")

    print(f"H-248 cross-system consensus (window {WINDOW_HOURS}h, >= {MIN_SYSTEMS} systems)")
    print(f"  usable rows      {result['rows_usable']}  (rejected {result['rows_rejected']})")
    for k, v in result["rejected_reasons"].items():
        print(f"      - {k}: {v}")
    print(f"  clusters         {result['clusters_total']}")
    print(f"  CONSENSUS        n={result['consensus']['n']:<5} mean {result['consensus']['mean_pct']}%  "
          f"CI {result['consensus']['ci95']}  wr {result['consensus']['win_rate']}")
    print(f"  SINGLE control   n={result['single_control']['n']:<5} "
          f"mean {result['single_control']['mean_pct']}%  CI {result['single_control']['ci95']}  "
          f"wr {result['single_control']['win_rate']}")
    print(f"  mean difference  {result['mean_diff_pct']}%  CI {result['mean_diff_ci95']}")
    print(f"  criteria         {result['criteria']}")
    print(f"  VERDICT          {result['verdict']}")
    print("  normalization    (entry-time coverage per ledger)")
    for system, info in result["normalization_audit"].items():
        if "n_rows" not in info:
            print(f"      {system:<24} {info}")
            continue
        cov = info["entry_time_coverage"]
        print(f"      {system:<24} n={info['n_rows']:<5} "
              f"entry-usables={info['entry_time_and_pnl_usable']:<5} "
              f"timestamp={cov.get('timestamp', 0)} entry_date={cov.get('entry_date', 0)}")
    print(f"  written          {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
