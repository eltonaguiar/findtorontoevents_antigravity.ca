#!/usr/bin/env python3
"""
send_daily_report.py — CLI to generate and dispatch the Alpha Engine daily report.

Usage:
    python scripts/send_daily_report.py --format markdown --webhook URL
    python scripts/send_daily_report.py --format html --output report.html
    python scripts/send_daily_report.py --format text

Stdlib only: argparse, json, csv, datetime, urllib.request, os, sys.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ---------------------------------------------------------------------------
# Path bootstrap — allow running from repo root or scripts/
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
for p in (REPO_ROOT, os.path.join(REPO_ROOT, "impl")):
    if p not in sys.path:
        sys.path.insert(0, p)

from alpha_engine.daily_report import generate_daily_report
from alpha_engine.daily_report_formatter import format_report


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_CLOSED = os.path.join(REPO_ROOT, "data", "closed_picks.json")
DEFAULT_ACTIVE = os.path.join(REPO_ROOT, "data", "active_picks.json")
DEFAULT_PAYLOAD = os.path.join(REPO_ROOT, "data", "dashboard_payload.json")
REPORT_DIR = os.path.join(REPO_ROOT, "reports")


def _send_to_slack(text: str, webhook_url: str) -> bool:
    """POST markdown text to a Slack incoming webhook. Returns True on success."""
    payload = json.dumps({"text": text}).encode("utf-8")
    req = Request(webhook_url, data=payload,
                  headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=20) as resp:
            return resp.status in (200, 204)
    except (URLError, HTTPError, OSError) as e:
        print(f"[send_daily_report] Slack send failed: {e}", file=sys.stderr)
        return False


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Generate and send Alpha Engine daily report")
    parser.add_argument("--closed", default=DEFAULT_CLOSED,
                        help="Path to closed picks file")
    parser.add_argument("--active", default=DEFAULT_ACTIVE,
                        help="Path to active picks file")
    parser.add_argument("--payload", default=DEFAULT_PAYLOAD,
                        help="Path to dashboard payload JSON")
    parser.add_argument("--format", "-f", default="markdown",
                        choices=["markdown", "html", "text"],
                        help="Output format (default: markdown)")
    parser.add_argument("--webhook", default=None,
                        help="Slack webhook URL (sends report as message)")
    parser.add_argument("--output", "-o", default=None,
                        help="Write formatted report to file")
    parser.add_argument("--json-output", default=None,
                        help="Also write raw JSON report to this path")
    parser.add_argument("--no-stdout", action="store_true",
                        help="Suppress stdout (useful in CI)")
    args = parser.parse_args()

    # 1. Generate
    report = generate_daily_report(args.closed, args.active, args.payload)
    date_str = report.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    # 2. Optional JSON dump
    if args.json_output:
        _ensure_dir(os.path.dirname(args.json_output) or ".")
        with open(args.json_output, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"[send_daily_report] JSON → {args.json_output}", file=sys.stderr)

    # 3. Format
    formatted = format_report(report, args.format)

    # 4. Write file
    if args.output:
        _ensure_dir(os.path.dirname(args.output) or ".")
        with open(args.output, "w") as f:
            f.write(formatted)
        print(f"[send_daily_report] {args.format} → {args.output}", file=sys.stderr)

    # 5. Also auto-archive to reports/ if no explicit --output
    if not args.output:
        ext = {"markdown": "md", "html": "html", "text": "txt"}[args.format]
        archive_path = os.path.join(REPORT_DIR, f"daily_{date_str}.{ext}")
        _ensure_dir(REPORT_DIR)
        with open(archive_path, "w") as f:
            f.write(formatted)
        print(f"[send_daily_report] archived → {archive_path}", file=sys.stderr)

    # 6. Send to Slack
    if args.webhook:
        ok = _send_to_slack(formatted, args.webhook)
        status = "sent" if ok else "FAILED"
        print(f"[send_daily_report] Slack: {status}", file=sys.stderr)

    # 7. Stdout
    if not args.no_stdout:
        print(formatted)

    # Return exit code
    sys.exit(0)


if __name__ == "__main__":
    main()
