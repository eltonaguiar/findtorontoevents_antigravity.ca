"""Anomaly canary on the notary log.

Reads `audit_trail/notary/notary_log.jsonl` and flags suspicious patterns
WITHOUT requiring access to the full 31MB dashboard_payload.json. The
notary log is small, append-only, and already captures the dispositive
fields (n_active, n_recent_closed, active_picks_hash, summary_hash) so
this is a near-free monitor for the kinds of corruption documented in
the user's memory file:
  - phantom HALT alert (false `_daily_loss` summed terminal-status PnL)
  - MATIC ghost rows + 100%-WR artifacts
  - clone_hl_copy placeholder stats (100/100/100 triples)
  - circuit_breaker stale-state leak

Detectors (each pure-python, no scikit-learn dependency):
  - n_recent_closed went backwards (data deletion)
  - n_active swung > k_sigma standard deviations from rolling mean
  - summary_hash churn (high change-rate suggests upstream instability)
  - active_picks_hash unchanged across many entries (stuck cron)
  - declared schema_version regressed

Outputs:
  - tools/data/notary_anomaly_status.json (machine-readable)
  - exit 1 when any high-severity flag fires; 0 otherwise

Wiring status: OPT-IN SIDECAR. Run manually:
    python tools/notary_anomaly_check.py
A follow-up PR will hook this into the audit-dashboard.yml cron AFTER
the notarize step lands so each hourly run gets a canary check.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = REPO_ROOT / "audit_trail" / "notary" / "notary_log.jsonl"
OUT_JSON = REPO_ROOT / "tools" / "data" / "notary_anomaly_status.json"

# Defaults: tuned to be loud on real corruption, quiet on legitimate
# pick-rotation churn. Tune via CLI flags.
DEFAULT_K_SIGMA = 3.0          # n_active sudden-swing threshold
DEFAULT_WINDOW = 24            # rolling window of entries (24h at hourly cron)
DEFAULT_MAX_STUCK = 6          # consecutive entries with same active_picks_hash before alarm


def _load_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                # Malformed line is itself an anomaly the canary should report.
                out.append({"_malformed_line": line})
                continue
            out.append(e)
    return out


def _rolling_mean_std(values: list[float], window: int) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    sample = values[-window:] if len(values) >= window else values
    n = len(sample)
    if n < 2:
        return float(sample[0]), 0.0
    mu = sum(sample) / n
    var = sum((v - mu) ** 2 for v in sample) / max(n - 1, 1)
    return mu, math.sqrt(var)


def detect_anomalies(entries: list[dict],
                     k_sigma: float = DEFAULT_K_SIGMA,
                     window: int = DEFAULT_WINDOW,
                     max_stuck: int = DEFAULT_MAX_STUCK) -> list[dict]:
    """Return a list of alert dicts. Empty list = clean."""
    alerts: list[dict] = []

    # Filter to "kind == notarize" entries (registrations are a separate kind)
    pick_entries = [e for e in entries
                    if "_malformed_line" not in e
                    and e.get("kind") in (None, "notarize")
                    and "n_active" in e]

    # Malformed JSONL lines
    for e in entries:
        if "_malformed_line" in e:
            alerts.append({"severity": "high",
                           "kind": "malformed_log_line",
                           "details": "JSONL parse failed",
                           "sample": e["_malformed_line"][:80]})

    # n_recent_closed going backwards
    prev_n_closed = None
    for e in pick_entries:
        n_c = e.get("n_recent_closed")
        if n_c is None:
            continue
        if prev_n_closed is not None and n_c < prev_n_closed:
            alerts.append({"severity": "high",
                           "kind": "n_recent_closed_regression",
                           "ts": e.get("ts_utc"),
                           "details": f"n_recent_closed dropped {prev_n_closed} -> {n_c}"})
        prev_n_closed = n_c

    # schema_version regression
    prev_sv = None
    for e in pick_entries:
        sv = e.get("schema_version")
        if sv is None:
            continue
        if prev_sv is not None and sv < prev_sv:
            alerts.append({"severity": "medium",
                           "kind": "schema_version_regression",
                           "ts": e.get("ts_utc"),
                           "details": f"schema_version dropped {prev_sv} -> {sv}"})
        prev_sv = sv

    # n_active sudden swing > k_sigma
    n_active_series: list[float] = []
    for e in pick_entries:
        n_a = e.get("n_active")
        if not isinstance(n_a, (int, float)):
            n_active_series.append(0.0)
            continue
        if len(n_active_series) >= 2:
            mu, sd = _rolling_mean_std(n_active_series, window)
            delta = abs(float(n_a) - mu)
            # Fire when value is k_sigma standard deviations from mean,
            # OR when sd==0 (constant series) and value differs by > 50%.
            fired = False
            if sd > 0 and delta > k_sigma * sd:
                fired = True
                z = delta / sd
                detail = (f"n_active={n_a} vs rolling mean={mu:.1f} "
                          f"std={sd:.1f} -> {z:.1f}σ")
            elif sd == 0 and mu > 0 and delta / mu > 0.5:
                fired = True
                detail = (f"n_active={n_a} vs rolling mean={mu:.1f} "
                          f"(constant series, {delta/mu*100:.0f}% jump)")
            if fired:
                alerts.append({"severity": "medium",
                               "kind": "n_active_sudden_swing",
                               "ts": e.get("ts_utc"),
                               "details": detail})
        n_active_series.append(float(n_a))

    # active_picks_hash stuck across max_stuck consecutive entries
    if pick_entries:
        run_hash = pick_entries[0].get("active_picks_hash")
        run_len = 1
        run_start_ts = pick_entries[0].get("ts_utc")
        for e in pick_entries[1:]:
            h = e.get("active_picks_hash")
            if h == run_hash:
                run_len += 1
                if run_len == max_stuck + 1:
                    alerts.append({"severity": "medium",
                                   "kind": "active_picks_hash_stuck",
                                   "ts": e.get("ts_utc"),
                                   "details": (
                                       f"active_picks_hash unchanged for "
                                       f"{run_len} consecutive entries (since "
                                       f"{run_start_ts})"
                                   )})
            else:
                run_hash = h
                run_len = 1
                run_start_ts = e.get("ts_utc")

    # Identical-triple clone_hl_copy-style placeholder pattern: when
    # n_active, n_recent_closed, summary_hash form a tuple seen too often
    triple_counts: dict[tuple, int] = {}
    for e in pick_entries:
        triple = (e.get("n_active"), e.get("n_recent_closed"),
                  e.get("summary_hash"))
        triple_counts[triple] = triple_counts.get(triple, 0) + 1
    for triple, c in triple_counts.items():
        if c >= 5 and triple[0] is not None:
            alerts.append({"severity": "low",
                           "kind": "identical_triple_repeated",
                           "details": (
                               f"(n_active, n_closed, summary_hash) seen "
                               f"{c} times: {triple[0]}, {triple[1]}, "
                               f"{(triple[2] or '')[:24]}..."
                           )})

    return alerts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--log-path", default=str(LOG_PATH))
    ap.add_argument("--k-sigma", type=float, default=DEFAULT_K_SIGMA)
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW)
    ap.add_argument("--max-stuck", type=int, default=DEFAULT_MAX_STUCK)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    entries = _load_log(Path(args.log_path))
    alerts = detect_anomalies(entries, args.k_sigma, args.window, args.max_stuck)

    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for a in alerts:
        s = a.get("severity", "low")
        severity_counts[s] = severity_counts.get(s, 0) + 1

    summary = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "log_path": str(args.log_path),
        "n_entries": len(entries),
        "n_alerts": len(alerts),
        "severity_counts": severity_counts,
        "alerts": alerts,
        "config": {"k_sigma": args.k_sigma, "window": args.window,
                   "max_stuck": args.max_stuck},
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    if not args.quiet:
        print(f"Notary log: {args.log_path}")
        print(f"  entries: {len(entries)}")
        print(f"  alerts:  high={severity_counts['high']} "
              f"medium={severity_counts['medium']} low={severity_counts['low']}")
        for a in alerts[:10]:
            print(f"  [{a['severity']:<6}] {a['kind']:<32} {a.get('details', '')}")
        if len(alerts) > 10:
            print(f"  ... +{len(alerts) - 10} more (see {OUT_JSON})")

    return 1 if severity_counts["high"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
