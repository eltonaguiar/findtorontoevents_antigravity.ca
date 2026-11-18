#!/usr/bin/env python3
"""Audit live BESTIEJOB feed against source-rights.yaml.

Reads jobs.json from the published feed, maps each job.source to a
rights value from source-rights.yaml, and reports percentages.
Exits 0 if unknown < 5%, exits 1 otherwise.

Uses only Python stdlib — no PyYAML dependency.
"""

import json
import re
import sys
import urllib.request

CONFIG_PATH = "updates/config/source-rights.yaml"
FEED_URL = "https://eltonaguiar.github.io/BESTIEJOB/jobs.json"


def parse_simple_yaml(path: str) -> dict:
    """Minimal YAML parser for the known source-rights.yaml structure."""
    sources = {}
    current_source = None
    with open(path) as f:
        for line in f:
            # Match  "  sourcename:"
            m = re.match(r"^  ([\w_]+):$", line)
            if m:
                current_source = m.group(1)
                if current_source not in sources:
                    sources[current_source] = {}
                continue
            # Match keys like "    rights: value" or "    redistribute: true"
            m = re.match(r"^    ([\w_]+):\s*(.+)$", line)
            if m and current_source is not None:
                key, val = m.group(1), m.group(2).strip()
                sources[current_source][key] = val
    return sources


def load_feed(url: str) -> list:
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read().decode())
    if isinstance(data, dict):
        return data.get("jobs", data.get("results", []))
    return data


def main() -> int:
    config = parse_simple_yaml(CONFIG_PATH)
    rights_map = {
        src: info.get("rights", "unknown")
        for src, info in config.items()
    }

    jobs = load_feed(FEED_URL)
    if not jobs:
        print("ERROR: No jobs found in feed", file=sys.stderr)
        return 1

    counts: dict[str, int] = {}
    for job in jobs:
        source = job.get("source") or "unknown_source"
        rights = rights_map.get(source, "unknown")
        counts[rights] = counts.get(rights, 0) + 1

    total = len(jobs)
    order = [
        "redistribution_approved",
        "permitted_api_private",
        "manual_discovery",
        "unknown",
    ]
    parts = []
    unknown_pct = 0.0
    for r in order:
        cnt = counts.get(r, 0)
        pct = (cnt / total) * 100
        parts.append(f"{pct:.1f}% {r}")
        if r == "unknown":
            unknown_pct = pct

    print(", ".join(parts))
    for r, cnt in sorted(counts.items()):
        if r not in order:
            pct = (cnt / total) * 100
            print(f"  {r}: {cnt} ({pct:.1f}%)")

    if unknown_pct < 5.0:
        print(f"PASS: unknown rights {unknown_pct:.1f}% < 5% threshold")
        return 0
    else:
        print(
            f"FAIL: unknown rights {unknown_pct:.1f}% >= 5% threshold",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())