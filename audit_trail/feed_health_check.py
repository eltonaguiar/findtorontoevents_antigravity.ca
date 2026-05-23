#!/usr/bin/env python3
"""
Feed health: validate dashboard_payload.json vs JSON_PICK_SOURCES, optional Prometheus + Slack.

Schema (vs Mercury draft):
  - systems[].name  (not system_id)
  - Freshness: payload-level generated_at only (see dashboard_payload_health.py)

One-shot (CI / cron):
  python audit_trail/feed_health_check.py --once

Daemon with Prometheus (scrapes /metrics on PORT):
  pip install prometheus_client
  python audit_trail/feed_health_check.py --metrics-port 8000 --interval 300

Env: SLACK_WEBHOOK, MAX_AGE_SECONDS (default 14400), EXIT_ON_FAILURE=1 in daemon mode to exit on bad check.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PAYLOAD_PATH = Path(__file__).resolve().parent / "data" / "dashboard_payload.json"

_METRICS_REGISTERED = False
G_PAYLOAD_STALE = None
G_PAYLOAD_AGE = None
G_UP = None


def _register_prometheus_metrics():
    global _METRICS_REGISTERED, G_PAYLOAD_STALE, G_PAYLOAD_AGE, G_UP
    if _METRICS_REGISTERED:
        return
    from prometheus_client import Gauge

    G_PAYLOAD_STALE = Gauge(
        "crypto_feed_payload_stale",
        "1 if dashboard_payload.json is older than max age",
    )
    G_PAYLOAD_AGE = Gauge(
        "crypto_feed_payload_age_seconds",
        "Seconds since payload generated_at (or file mtime fallback)",
    )
    G_UP = Gauge(
        "crypto_feed_up_to_date",
        "1 if source row exists, numerics valid, and payload is fresh",
        ["system"],
    )
    _METRICS_REGISTERED = True


def _send_slack(msg: str) -> None:
    url = os.environ.get("SLACK_WEBHOOK", "").strip()
    if not url:
        print(msg)
        return
    body = json.dumps({"text": msg}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.URLError as exc:
        print(f"Slack post failed: {exc}", file=sys.stderr)
        print(msg)


def _update_prometheus(health: object, source_names: list[str]) -> None:
    _register_prometheus_metrics()
    G_PAYLOAD_STALE.set(1.0 if health.payload_stale else 0.0)
    G_PAYLOAD_AGE.set(max(0.0, float(health.age_seconds)))

    bad_names = set(health.bad_numeric_systems) | set(health.missing_systems)
    fresh = not health.payload_stale

    for name in source_names:
        ok = fresh and name not in bad_names
        G_UP.labels(system=name).set(1.0 if ok else 0.0)


def run_check(max_age: int):
    sys.path.insert(0, str(REPO))
    from audit_trail.collect_sources import get_registered_pick_source_names
    from audit_trail.dashboard_payload_health import check_dashboard_payload

    sources = get_registered_pick_source_names()
    health = check_dashboard_payload(REPO, PAYLOAD_PATH, max_age_seconds=max_age)
    return health, sources


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit dashboard payload feed health")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Single check then exit (for GitHub Actions / cron)",
    )
    parser.add_argument(
        "--metrics-port",
        type=int,
        default=0,
        metavar="PORT",
        help="If >0, start Prometheus client HTTP server on this port",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Sleep seconds between checks in daemon mode (default 300)",
    )
    args = parser.parse_args()

    max_age = int(os.environ.get("MAX_AGE_SECONDS", str(4 * 3600)))

    if args.metrics_port > 0:
        try:
            from prometheus_client import start_http_server
        except ImportError:
            print("Install: pip install prometheus_client", file=sys.stderr)
            return 2
        _register_prometheus_metrics()
        start_http_server(args.metrics_port)
        print(
            f"Prometheus metrics on http://0.0.0.0:{args.metrics_port}/metrics",
            file=sys.stderr,
        )

    def check_and_report() -> int:
        health, sources = run_check(max_age)
        if args.metrics_port > 0:
            _update_prometheus(health, sources)
        if not health.ok:
            lines = [":warning: *Crypto audit feed health*", *health.summary_lines()]
            for p in health.problems:
                lines.append(f"• `{p['system']}` — {p['reason']}")
            _send_slack("\n".join(lines))
            return 1
        print(
            f"OK age_s={health.age_seconds} sources={len(sources)} "
            f"payload_stale={health.payload_stale}"
        )
        return 0

    if args.once:
        return check_and_report()

    if args.metrics_port <= 0:
        print(
            "Use --once for one shot, or --metrics-port N for daemon mode.",
            file=sys.stderr,
        )
        return 2

    exit_on_fail = os.environ.get("EXIT_ON_FAILURE", "").lower() in ("1", "true", "yes")
    while True:
        rc = check_and_report()
        if rc != 0 and exit_on_fail:
            return rc
        time.sleep(max(30, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
