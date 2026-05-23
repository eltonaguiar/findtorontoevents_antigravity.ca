"""Hypothesis pre-registration ledger for audit-page strategies.

Why this exists
---------------
Pre-registration kills HARKing (Hypothesizing After Results are Known).
A strategy author commits — at strategy birth, before any forward
data — to a target metric, threshold, sample size, and hold-out window.
The audit page can then display only forward results that match the
pre-registered claim. A skeptic can verify: does this strategy hit the
threshold its author committed to, on data they could not have seen
when they registered?

Cross-AI institutional reviewer (2026-05-02) ranked this in the top 2
alternatives for credibility uplift on `/audit`: "a timestamped,
hash-locked pre-reg ledger is the only artifact on the page that a
skeptic literally cannot fake."

Storage
-------
- Ledger files: `audit_trail/preregistration/<strategy_id>.yaml`
- Each registration also appends a SHA-256 entry to
  `audit_trail/notary/notary_log.jsonl` so git history anchors the
  timestamp.

Subcommands
-----------
- register --strategy ... --metric ... --threshold ...   create entry
- verify <strategy_id>                                   evaluate one
- verify-all                                              evaluate all
- list                                                   roster + status

Wiring status: OPT-IN SIDECAR. No production caller. A follow-up PR
will surface PASS/FAIL on `audit_dashboard/template.html`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from scipy.stats import beta as _beta

REPO_ROOT = Path(__file__).resolve().parents[1]
PREREG_DIR = REPO_ROOT / "audit_trail" / "preregistration"
PICKS_PATH = REPO_ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
TC_PATH = REPO_ROOT / "tools" / "data" / "transaction_costs.json"
STATUS_OUT = REPO_ROOT / "tools" / "data" / "preregistration_status.json"
NOTARY_LOG = REPO_ROOT / "audit_trail" / "notary" / "notary_log.jsonl"
SCHEMA_VERSION = 1

SUPPORTED_METRICS = (
    "wr_pct",
    "wilson_lb_wr_pct",
    "after_cost_pnl_per_trade",
    "posterior_p_above_50",
    "posterior_mean_wr",
)

REQUIRED_FIELDS = (
    "strategy_id",
    "declared_at_utc",
    "asset_class",
    "target_metric",
    "threshold",
    "sample_size_min",
    "holdout_window_start",
    "holdout_window_end",
    "git_sha_at_registration",
    "schema_version",
)


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def _git_head_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
        )
        return out.decode("ascii").strip()
    except Exception:
        return ""


def compute_yaml_hash(entry: dict) -> str:
    payload = {k: v for k, v in entry.items() if k != "yaml_hash"}
    return _sha256(_canonical_json(payload))


def _parse_iso(s: str) -> datetime:
    s2 = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s2)


def validate_entry(entry: dict) -> list[str]:
    errors: list[str] = []
    for f in REQUIRED_FIELDS:
        if f not in entry:
            errors.append(f"missing required field: {f}")
    if entry.get("target_metric") not in SUPPORTED_METRICS:
        errors.append(f"target_metric must be one of {SUPPORTED_METRICS}")
    if entry.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")
    try:
        thr = float(entry.get("threshold", "x"))
        ssm = int(entry.get("sample_size_min", "x"))
        if thr < 0:
            errors.append("threshold must be non-negative")
        if ssm < 1:
            errors.append("sample_size_min must be >= 1")
    except (TypeError, ValueError):
        errors.append("threshold and sample_size_min must be numeric")
    for ts_field in ("declared_at_utc", "holdout_window_start", "holdout_window_end"):
        v = entry.get(ts_field)
        if not isinstance(v, str):
            errors.append(f"{ts_field} must be ISO-8601 string")
            continue
        try:
            _parse_iso(v)
        except ValueError:
            errors.append(f"{ts_field}: cannot parse '{v}' as ISO-8601")
    if entry.get("holdout_window_start") and entry.get("holdout_window_end"):
        try:
            s = _parse_iso(entry["holdout_window_start"])
            e = _parse_iso(entry["holdout_window_end"])
            if e <= s:
                errors.append("holdout_window_end must be after holdout_window_start")
        except ValueError:
            pass
    return errors


def _wilson_lb(wins: int, n: int) -> float:
    if n == 0:
        return 0.0
    p = wins / n
    z = 1.96
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p + z2 / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return (centre - half) / denom * 100.0


def _round_trip_tc_pct(asset_class: str) -> float:
    if not TC_PATH.exists():
        return 0.0
    try:
        with TC_PATH.open("r", encoding="utf-8") as f:
            tc = json.load(f)
    except Exception:
        return 0.0
    cost = tc.get(asset_class.upper())
    if isinstance(cost, dict):
        if "round_trip_pct" in cost:
            return float(cost["round_trip_pct"])
        if "round_trip_bps" in cost:
            return float(cost["round_trip_bps"]) / 10000.0
    if isinstance(cost, (int, float)):
        return float(cost)
    return 0.0


def compute_metric(picks: list[dict], metric: str, asset_class: str) -> dict[str, float | int]:
    n = len(picks)
    wins = sum(1 for p in picks if (p.get("pnl_pct") or 0) > 0)
    pnl_list = [float(p["pnl_pct"]) for p in picks if p.get("pnl_pct") is not None]

    if metric == "wr_pct":
        value = (wins / n * 100.0) if n else 0.0
    elif metric == "wilson_lb_wr_pct":
        value = _wilson_lb(wins, n)
    elif metric == "after_cost_pnl_per_trade":
        if n == 0:
            value = 0.0
        else:
            mean_pnl = sum(pnl_list) / len(pnl_list) if pnl_list else 0.0
            tc = _round_trip_tc_pct(asset_class) * 100.0
            value = mean_pnl - tc
    elif metric == "posterior_p_above_50":
        a = 0.5 + wins
        b = 0.5 + (n - wins)
        value = float(1.0 - _beta.cdf(0.50, a, b))
    elif metric == "posterior_mean_wr":
        a = 0.5 + wins
        b = 0.5 + (n - wins)
        value = float(a / (a + b))
    else:
        raise ValueError(f"unsupported metric: {metric}")

    return {"value": float(value), "n": n, "wins": wins}


def _load_recent_closed() -> list[dict]:
    with PICKS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("picks", {}).get("recent_closed", [])


def filter_picks_for_entry(entry: dict, all_picks: list[dict]) -> list[dict]:
    sid = entry["strategy_id"]
    klass = (entry.get("asset_class") or "").upper()
    win_start = _parse_iso(entry["holdout_window_start"])
    win_end = _parse_iso(entry["holdout_window_end"])

    out: list[dict] = []
    for p in all_picks:
        if (p.get("strategy") or "") != sid:
            continue
        if klass and (p.get("asset_class") or "").upper() != klass:
            continue
        ts = p.get("closed_at") or p.get("opened_at")
        if not ts:
            continue
        try:
            t = _parse_iso(ts)
        except ValueError:
            continue
        if win_start <= t <= win_end:
            out.append(p)
    return out


def cmd_register(args) -> int:
    entry = {
        "strategy_id": args.strategy,
        "declared_at_utc": datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "asset_class": args.asset_class.upper(),
        "target_metric": args.metric,
        "threshold": float(args.threshold),
        "sample_size_min": int(args.sample_size),
        "holdout_window_start": args.window_start,
        "holdout_window_end": args.window_end,
        "git_sha_at_registration": _git_head_sha(),
        "schema_version": SCHEMA_VERSION,
    }
    errors = validate_entry(entry)
    if errors:
        print("VALIDATION ERRORS:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 2
    entry["yaml_hash"] = compute_yaml_hash(entry)

    PREREG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PREREG_DIR / f"{args.strategy}.yaml"
    if out_path.exists() and not args.force:
        print(f"ERROR: {out_path} already exists; use --force to overwrite",
              file=sys.stderr)
        return 3
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(entry, f, sort_keys=True, default_flow_style=False)

    NOTARY_LOG.parent.mkdir(parents=True, exist_ok=True)
    notary_entry = {
        "ts_utc": entry["declared_at_utc"],
        "schema_version": 1,
        "git_sha": entry["git_sha_at_registration"],
        "kind": "preregistration",
        "strategy_id": entry["strategy_id"],
        "yaml_hash": entry["yaml_hash"],
    }
    with NOTARY_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(notary_entry, sort_keys=True) + "\n")

    if not args.quiet:
        print(f"Registered: {out_path}")
        print(f"  yaml_hash: {entry['yaml_hash']}")
        print(f"  notary appended to {NOTARY_LOG}")
    return 0


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: yaml root is not a mapping")
    return data


def verify_one(entry: dict, all_picks: list[dict]) -> dict:
    errors = validate_entry(entry)
    if errors:
        return {"strategy_id": entry.get("strategy_id"),
                "status": "INVALID",
                "errors": errors}
    expected = compute_yaml_hash(entry)
    actual = entry.get("yaml_hash")
    hash_ok = expected == actual

    matched = filter_picks_for_entry(entry, all_picks)
    n = len(matched)
    if n < int(entry["sample_size_min"]):
        status = "PENDING"
        metric_value = None
    else:
        m = compute_metric(matched, entry["target_metric"], entry["asset_class"])
        metric_value = m["value"]
        threshold = float(entry["threshold"])
        status = "PASS" if metric_value >= threshold else "FAIL"

    return {
        "strategy_id": entry["strategy_id"],
        "status": status,
        "n_in_window": n,
        "sample_size_min": int(entry["sample_size_min"]),
        "target_metric": entry["target_metric"],
        "threshold": float(entry["threshold"]),
        "metric_value": metric_value,
        "yaml_hash_ok": hash_ok,
        "expected_yaml_hash": expected,
        "stored_yaml_hash": actual,
        "asset_class": entry["asset_class"],
        "holdout_window": [entry["holdout_window_start"], entry["holdout_window_end"]],
    }


def cmd_verify(args) -> int:
    path = PREREG_DIR / f"{args.strategy}.yaml"
    if not path.exists():
        print(f"ERROR: no registration at {path}", file=sys.stderr)
        return 4
    entry = _load_yaml(path)
    all_picks = _load_recent_closed()
    result = verify_one(entry, all_picks)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result["status"] in ("PASS", "PENDING") else 1


def cmd_verify_all(args) -> int:
    if not PREREG_DIR.exists():
        print("(no preregistrations yet)")
        return 0
    all_picks = _load_recent_closed()
    results: list[dict] = []
    for yaml_path in sorted(PREREG_DIR.glob("*.yaml")):
        try:
            entry = _load_yaml(yaml_path)
        except Exception as exc:
            results.append({"strategy_id": yaml_path.stem,
                            "status": "MALFORMED",
                            "errors": [str(exc)]})
            continue
        results.append(verify_one(entry, all_picks))
    summary = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "n": len(results),
        "by_status": {},
        "results": results,
    }
    for r in results:
        summary["by_status"][r["status"]] = summary["by_status"].get(r["status"], 0) + 1
    STATUS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with STATUS_OUT.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    if not args.quiet:
        for r in results:
            mv = "" if r.get("metric_value") is None else f" {r['metric_value']:.4f}"
            print(f"  {r['status']:<8} {r['strategy_id']:<35} "
                  f"n={r.get('n_in_window', '-')} {r.get('target_metric', '')}{mv}")
        print(f"\nWrote {STATUS_OUT}")
    return 0


def cmd_list(args) -> int:
    if not PREREG_DIR.exists():
        print("(none)")
        return 0
    for yaml_path in sorted(PREREG_DIR.glob("*.yaml")):
        try:
            e = _load_yaml(yaml_path)
            print(f"  {yaml_path.stem:<35} metric={e.get('target_metric')} "
                  f"threshold={e.get('threshold')} window=[{e.get('holdout_window_start')}, "
                  f"{e.get('holdout_window_end')}]")
        except Exception as exc:
            print(f"  {yaml_path.stem:<35} MALFORMED: {exc}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_reg = sub.add_parser("register")
    p_reg.add_argument("--strategy", required=True)
    p_reg.add_argument("--asset-class", required=True)
    p_reg.add_argument("--metric", required=True, choices=SUPPORTED_METRICS)
    p_reg.add_argument("--threshold", required=True, type=float)
    p_reg.add_argument("--sample-size", required=True, type=int)
    p_reg.add_argument("--window-start", required=True)
    p_reg.add_argument("--window-end", required=True)
    p_reg.add_argument("--force", action="store_true")
    p_reg.add_argument("--quiet", action="store_true")
    p_reg.set_defaults(func=cmd_register)

    p_v = sub.add_parser("verify")
    p_v.add_argument("strategy")
    p_v.set_defaults(func=cmd_verify)

    p_va = sub.add_parser("verify-all")
    p_va.add_argument("--quiet", action="store_true")
    p_va.set_defaults(func=cmd_verify_all)

    p_l = sub.add_parser("list")
    p_l.set_defaults(func=cmd_list)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
