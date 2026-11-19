#!/usr/bin/env python3
"""Check job source rights against the source-rights config.

Exits 0 if <5% of jobs have unknown rights, 1 otherwise.
"""
import json
import sys
from pathlib import Path
from urllib.request import urlopen

try:
    import yaml
except ImportError:
    yaml = None

FEED_URL = "https://eltonaguiar.github.io/BESTIEJOB/jobs.json"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "source-rights.yaml"
WARNING_THRESHOLD = 0.05


def load_config(path):
    if not path.exists():
        default = {
            "sources": {
                "unknown_source": {"rights": "unknown", "redistribute": False}
            }
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        if yaml:
            path.write_text(yaml.dump(default, default_flow_style=False))
        else:
            path.write_text(json.dumps(default, indent=2))
        return default

    raw = path.read_text()
    if yaml and path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(raw)
    return json.loads(raw)


def main():
    config = load_config(CONFIG_PATH)
    sources_cfg = config.get("sources", {})

    print(f"Fetching: {FEED_URL}", file=sys.stderr)
    data = json.loads(urlopen(FEED_URL, timeout=30).read())
    jobs = data.get("jobs", [])

    total = len(jobs)
    warning_count = 0

    for job in jobs:
        source = (job.get("source") or "").strip().lower()
        title = job.get("title", "?")
        company = job.get("company", "?")
        entry = sources_cfg.get(source, {})

        if not source or not entry or entry.get("rights", "unknown") == "unknown":
            print(
                f"WARNING: source='{source}' rights=unknown "
                f"job='{title}' company='{company}'"
            )
            warning_count += 1

    ratio = warning_count / total if total else 0
    print(
        f"\n{ratio:.1%} — {warning_count} of {total} jobs have unknown rights",
        file=sys.stderr,
    )

    sys.exit(0 if ratio < WARNING_THRESHOLD else 1)


if __name__ == "__main__":
    main()