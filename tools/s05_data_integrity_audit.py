"""
S0.5 Data Integrity Audit — Strategy Factory v1.1 §3

Foundational gate ALL strategies must pass before any backtest work. Validates
the DATA, not the strategy. See docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md §3.

Read-only. Does not modify input data.

Usage:
    python tools/s05_data_integrity_audit.py [--out PATH] [--verbose] [--fail-on-critical]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json"
DEFAULT_OUTPUT = REPO_ROOT / "audit_trail" / "data" / "s05_integrity_report.json"

CRITICAL_FIELDS = [
    "symbol",
    "direction",
    "strategy",
    "opened_at",
    "closed_at",
    "pnl_pct",
    "status",
]

# Per §3 thresholds
COMPLETENESS_THRESHOLD = 0.01  # < 1% missing per critical field/combo
OUTLIER_THRESHOLD = 0.03       # < 3% outliers
OUTLIER_SIGMA = 5.0            # +/- 5 sigma
PNL_RECOMPUTE_TOL_PCT = 0.01   # 0.01% realized-delta tolerance


def _parse_ts(val: Any):
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(float(val), tz=timezone.utc)
        except Exception:
            return None
    s = str(val).strip()
    if not s:
        return None
    # Try ISO first
    try:
        # Accept "2026-03-22T11:11:04.564861" (naive) and "...+00:00"
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def _is_utc_naive_or_utc(dt) -> bool:
    if dt is None:
        return False
    if dt.tzinfo is None:
        return True  # naive — assumed UTC per project convention
    return dt.utcoffset() is not None and dt.utcoffset().total_seconds() == 0


def load_rows(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = list(data.values())
    if not isinstance(data, list):
        raise SystemExit(f"Unexpected top-level type in {path}: {type(data).__name__}")
    return data


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_completeness(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"status": "FAIL", "details": {"reason": "no rows"}}
    per_field = {}
    for f in CRITICAL_FIELDS:
        missing = sum(1 for r in rows if r.get(f) in (None, "", []))
        per_field[f] = {"missing": missing, "rate": missing / n}

    # Per-combo missing: group (symbol, direction, strategy)
    combos: Dict[tuple, List[Dict[str, Any]]] = {}
    for r in rows:
        k = (r.get("symbol"), r.get("direction"), r.get("strategy"))
        combos.setdefault(k, []).append(r)
    combo_fails = []
    for k, rs in combos.items():
        m = len(rs)
        if m < 20:  # skip tiny combos to avoid noise
            continue
        for f in CRITICAL_FIELDS:
            miss = sum(1 for r in rs if r.get(f) in (None, "", []))
            rate = miss / m
            if rate > COMPLETENESS_THRESHOLD:
                combo_fails.append({"combo": list(k), "field": f, "rate": rate, "n": m})

    any_field_fail = any(v["rate"] > COMPLETENESS_THRESHOLD for v in per_field.values())
    status = "FAIL" if any_field_fail or combo_fails else "PASS"
    return {
        "status": status,
        "details": {
            "n_rows": n,
            "per_field": per_field,
            "n_combos": len(combos),
            "combo_violations": combo_fails[:25],
            "combo_violations_total": len(combo_fails),
            "threshold": COMPLETENESS_THRESHOLD,
        },
    }


def check_outliers(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    import numpy as np
    by_sym: Dict[str, List[float]] = {}
    for r in rows:
        v = r.get("pnl_pct")
        if v is None:
            continue
        try:
            by_sym.setdefault(r.get("symbol", "UNKNOWN"), []).append(float(v))
        except Exception:
            continue
    total = 0
    outliers = 0
    flagged_syms = []
    for sym, vals in by_sym.items():
        arr = np.asarray(vals, dtype=float)
        total += arr.size
        if arr.size < 5:
            continue
        mu = float(arr.mean())
        sd = float(arr.std(ddof=0))
        if sd == 0:
            continue
        mask = np.abs(arr - mu) > OUTLIER_SIGMA * sd
        k = int(mask.sum())
        if k:
            outliers += k
            flagged_syms.append({"symbol": sym, "n": int(arr.size), "outliers": k,
                                 "mu": mu, "sigma": sd})
    rate = (outliers / total) if total else 0.0
    status = "PASS" if rate < OUTLIER_THRESHOLD else ("WARN" if rate < 2 * OUTLIER_THRESHOLD else "FAIL")
    flagged_syms.sort(key=lambda x: -x["outliers"])
    return {
        "status": status,
        "details": {
            "total_pnl_pct_values": total,
            "outliers": outliers,
            "rate": rate,
            "threshold": OUTLIER_THRESHOLD,
            "sigma": OUTLIER_SIGMA,
            "top_symbols": flagged_syms[:15],
        },
    }


def check_timestamps(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    future_open = 0
    future_close = 0
    close_before_open = 0
    unparseable_open = 0
    unparseable_close = 0
    non_utc = 0
    ids_seen = Counter()
    for r in rows:
        pid = r.get("id") if r.get("id") is not None else r.get("pick_id")
        if pid is not None:
            ids_seen[pid] += 1
        o = _parse_ts(r.get("opened_at"))
        c = _parse_ts(r.get("closed_at"))
        if r.get("opened_at") and o is None:
            unparseable_open += 1
        if r.get("closed_at") and c is None:
            unparseable_close += 1
        for dt in (o, c):
            if dt is not None and not _is_utc_naive_or_utc(dt):
                non_utc += 1
        # Compare as naive UTC
        def _naive(dt):
            if dt is None:
                return None
            return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt
        no, nc = _naive(o), _naive(c)
        now_naive = now.replace(tzinfo=None)
        if no is not None and no > now_naive:
            future_open += 1
        if nc is not None and nc > now_naive:
            future_close += 1
        if no is not None and nc is not None and nc < no:
            close_before_open += 1
    dup_ids = {pid: cnt for pid, cnt in ids_seen.items() if cnt > 1}
    problems = (future_open + future_close + close_before_open +
                unparseable_open + unparseable_close + non_utc + len(dup_ids))
    status = "PASS" if problems == 0 else "FAIL"
    return {
        "status": status,
        "details": {
            "future_opened_at": future_open,
            "future_closed_at": future_close,
            "closed_before_opened": close_before_open,
            "unparseable_opened_at": unparseable_open,
            "unparseable_closed_at": unparseable_close,
            "non_utc_timestamps": non_utc,
            "duplicate_pick_ids": len(dup_ids),
            "sample_duplicates": list(dup_ids.items())[:10],
        },
    }


def _asset_class(symbol: str) -> str:
    if not symbol:
        return "UNKNOWN"
    s = str(symbol).upper()
    if s.endswith("USDT") or s.endswith("USD") or s.endswith("BUSD") or s.endswith("USDC"):
        return "CRYPTO"
    if s.endswith("=F"):
        return "FUTURES"
    if "-" in s or "/" in s:
        return "FX"
    return "EQUITY"


def check_stationarity(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    try:
        from statsmodels.tsa.stattools import adfuller  # type: ignore
    except Exception as e:
        return {"status": "WARN", "details": {
            "reason": "statsmodels not installed; ADF not run",
            "error": str(e),
            "action": "pip install statsmodels (env issue — not installed per spec)",
        }}
    import numpy as np
    import pandas as pd

    buckets: Dict[str, List[tuple]] = {}
    for r in rows:
        c = _parse_ts(r.get("closed_at"))
        v = r.get("pnl_pct")
        if c is None or v is None:
            continue
        try:
            v = float(v)
        except Exception:
            continue
        buckets.setdefault(_asset_class(r.get("symbol", "")), []).append((c, v))

    per_class = {}
    nonstationary = []
    for cls, pairs in buckets.items():
        if len(pairs) < 30:
            per_class[cls] = {"status": "SKIP", "reason": "n<30", "n": len(pairs)}
            continue
        df = pd.DataFrame(pairs, columns=["ts", "pnl"])
        df["day"] = pd.to_datetime(df["ts"]).dt.floor("D")
        daily = df.groupby("day")["pnl"].sum().sort_index()
        series = daily.values.astype(float)
        if series.size < 20 or float(np.nanstd(series)) == 0.0:
            per_class[cls] = {"status": "SKIP", "reason": "insufficient or constant series", "n": int(series.size)}
            continue
        try:
            stat, pval, *_ = adfuller(series, autolag="AIC")
        except Exception as e:
            per_class[cls] = {"status": "ERROR", "error": str(e)}
            continue
        is_stationary = pval < 0.05
        per_class[cls] = {
            "status": "STATIONARY" if is_stationary else "NON_STATIONARY",
            "adf_stat": float(stat),
            "pvalue": float(pval),
            "n_days": int(series.size),
            "n_rows": len(pairs),
        }
        if not is_stationary:
            nonstationary.append(cls)
    status = "PASS" if not nonstationary else "WARN"
    return {"status": status, "details": {"per_class": per_class, "non_stationary_classes": nonstationary}}


def check_survivorship(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    tagged = 0
    untagged_candidates = []
    matic_rows = 0
    matic_tagged = 0
    symbols = Counter()
    for r in rows:
        sym = r.get("symbol") or ""
        symbols[sym] += 1
        if sym == "MATICUSDT":
            matic_rows += 1
            if r.get("rebrand_artifact") or (str(r.get("status", "")).lower() == "delisted"):
                matic_tagged += 1
        if r.get("rebrand_artifact") or (str(r.get("status", "")).lower() == "delisted"):
            tagged += 1
    # Heuristic: symbols appearing only in early data may be delisted; we cannot prove without universe.
    status = "PASS" if matic_rows == 0 or matic_tagged == matic_rows else "WARN"
    return {
        "status": status,
        "details": {
            "rows_tagged_rebrand_or_delisted": tagged,
            "MATICUSDT_rows": matic_rows,
            "MATICUSDT_tagged": matic_tagged,
            "unique_symbols": len(symbols),
            "note": "Full survivorship check requires current-universe snapshot; this is a spot-check on MATICUSDT reference case.",
        },
    }


DIRECTION_CANONICAL = {
    "BUY": "LONG", "LONG": "LONG",
    "SELL": "SHORT", "SHORT": "SHORT",
}


def check_schema_consistency(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    dist = Counter()
    unknown = []
    for r in rows:
        d = r.get("direction")
        dist[str(d)] += 1
        if d is not None and str(d).upper() not in DIRECTION_CANONICAL:
            unknown.append(str(d))
    vocab = {k: v for k, v in dist.items()}
    multi = len({DIRECTION_CANONICAL.get(str(k).upper(), str(k)) for k in dist.keys() if k is not None})
    distinct_raw = len([k for k in dist.keys() if k is not None])
    status = "PASS" if distinct_raw <= 1 else "FAIL"
    return {
        "status": status,
        "details": {
            "direction_distribution": vocab,
            "distinct_raw_values": distinct_raw,
            "distinct_canonical": multi,
            "unknown_values": sorted(set(unknown))[:20],
            "note": "Vocabulary must be single (LONG/SHORT OR BUY/SELL, not mixed).",
        },
    }


def check_source_attribution(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    non_null = sum(1 for r in rows if r.get("source_system") not in (None, ""))
    by_src = Counter(r.get("source_system") or "__NULL__" for r in rows)
    rate = non_null / n if n else 0.0
    status = "PASS" if rate >= 0.99 else ("WARN" if rate >= 0.90 else "FAIL")
    return {
        "status": status,
        "details": {
            "non_null": non_null,
            "total": n,
            "rate": rate,
            "distribution": dict(by_src.most_common(20)),
        },
    }


def check_forward_looking(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    close_before_open = 0
    pnl_mismatch = 0
    mismatch_samples = []
    for r in rows:
        o = _parse_ts(r.get("opened_at"))
        c = _parse_ts(r.get("closed_at"))
        if o is not None and c is not None:
            o_cmp = o.replace(tzinfo=None) if o.tzinfo is not None else o
            c_cmp = c.replace(tzinfo=None) if c.tzinfo is not None else c
            if c_cmp < o_cmp:
                close_before_open += 1
        ep = r.get("entry_price")
        xp = r.get("exit_price")
        pnl = r.get("pnl_pct")
        direction = str(r.get("direction") or "").upper()
        if ep not in (None, 0) and xp is not None and pnl is not None:
            try:
                ep_f = float(ep); xp_f = float(xp); pnl_f = float(pnl)
                if ep_f == 0:
                    continue
                raw = (xp_f - ep_f) / ep_f * 100.0
                if direction in ("SELL", "SHORT"):
                    raw = -raw
                if abs(raw - pnl_f) > PNL_RECOMPUTE_TOL_PCT:
                    pnl_mismatch += 1
                    if len(mismatch_samples) < 10:
                        mismatch_samples.append({
                            "id": r.get("id"), "symbol": r.get("symbol"),
                            "direction": direction, "entry": ep_f, "exit": xp_f,
                            "stored_pnl_pct": pnl_f, "recomputed_pct": raw,
                        })
            except Exception:
                continue
    problems = close_before_open + pnl_mismatch
    status = "PASS" if problems == 0 else ("WARN" if pnl_mismatch / max(len(rows), 1) < 0.05 and close_before_open == 0 else "FAIL")
    return {
        "status": status,
        "details": {
            "closed_before_opened": close_before_open,
            "pnl_recompute_mismatches": pnl_mismatch,
            "tolerance_pct": PNL_RECOMPUTE_TOL_PCT,
            "samples": mismatch_samples,
        },
    }


CHECKS = [
    ("completeness", check_completeness),
    ("outliers", check_outliers),
    ("timestamps", check_timestamps),
    ("stationarity", check_stationarity),
    ("survivorship", check_survivorship),
    ("schema_consistency", check_schema_consistency),
    ("source_attribution", check_source_attribution),
    ("forward_looking_bias", check_forward_looking),
]


def run(input_path: Path, output_path: Path, verbose: bool = False) -> Dict[str, Any]:
    rows = load_rows(input_path)
    results: Dict[str, Any] = {}
    critical_fails: List[str] = []
    for name, fn in CHECKS:
        try:
            r = fn(rows)
        except Exception as e:
            r = {"status": "ERROR", "details": {"error": repr(e)}}
        results[name] = r
        if r.get("status") == "FAIL":
            critical_fails.append(name)

    recommended: List[str] = []
    if "schema_consistency" in critical_fails:
        recommended.append("Normalize `direction` to single vocabulary (LONG/SHORT) in ETL before backtest.")
    if "timestamps" in critical_fails:
        recommended.append("Resolve timestamp anomalies (duplicates/future/unparseable) before backtest.")
    if "completeness" in critical_fails:
        recommended.append("Backfill or drop rows missing critical fields per (symbol, direction, strategy) combo.")
    if "forward_looking_bias" in critical_fails:
        recommended.append("Audit pnl_pct computation — realized delta mismatches indicate ETL bug.")
    if results.get("stationarity", {}).get("status") == "WARN":
        recommended.append("Non-stationary asset classes: difference the series or split by regime before backtest.")
    if results.get("source_attribution", {}).get("status") in ("WARN", "FAIL"):
        recommended.append("Backfill `source_system` attribution — required for strategy concentration analysis.")

    report = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "input": str(input_path),
        "total_rows": len(rows),
        "checks": results,
        "critical_fails": critical_fails,
        "recommended_actions": recommended,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, default=str)

    # stdout summary
    print(f"S0.5 Data Integrity Audit  —  rows={len(rows)}  input={input_path}")
    for name, _ in CHECKS:
        st = results[name].get("status", "?")
        print(f"  [{st:>5}] {name}")
    if critical_fails:
        print(f"CRITICAL FAILS: {', '.join(critical_fails)}")
    if recommended:
        print("Recommended actions:")
        for a in recommended:
            print(f"  - {a}")
    print(f"Report written: {output_path}")
    if verbose:
        print(json.dumps(report, indent=2, default=str))
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="S0.5 Data Integrity Audit (Strategy Factory v1.1 §3)")
    ap.add_argument("--input", default=str(DEFAULT_INPUT))
    ap.add_argument("--out", default=str(DEFAULT_OUTPUT))
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--fail-on-critical", action="store_true")
    args = ap.parse_args(argv)

    report = run(Path(args.input), Path(args.out), verbose=args.verbose)
    if args.fail_on_critical and report["critical_fails"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
