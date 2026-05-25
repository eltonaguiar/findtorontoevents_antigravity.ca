"""
monitor_roo_diagnostics.py — watch /tmp/ for new roo-diagnostics-*.json files,
classify each error, and append actionable findings to a digest file.

Classification:
  RESTART_NOISE  — generic "Connection error" within 15s of a known proxy restart
                   (read from /tmp/litellm_proxy.log). These are my own fault,
                   not real upstream problems.
  REAL_ERROR     — anything else: upstream-specific errors, 4xx/5xx with detail,
                   context-window issues, mid-stream errors, etc.

For REAL_ERROR entries, the script writes:
  - the timestamp + error type
  - which model_group / upstream is implicated
  - a suggested fix (e.g. "remove X from rotation", "add fallback for Y")

Usage:
  python3 tools/monitor_roo_diagnostics.py            # one-shot scan, write digest
  python3 tools/monitor_roo_diagnostics.py --watch    # background poll loop (60s)
  python3 tools/monitor_roo_diagnostics.py --digest   # print digest only, no scan
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import re
import time
from pathlib import Path

DIGEST = Path("/tmp/roo_diagnostics_digest.md")
SEEN = Path("/tmp/roo_diagnostics_seen.txt")
RESTART_HISTORY = Path("/tmp/litellm_restart_history.jsonl")
PATTERN = "/tmp/roo-diagnostics-*.json"

# Window around proxy-restart events that's considered restart noise.
# Cover ~15s before the launcher records the new PID (kill window) and
# ~15s after (litellm boot ~6-10s + first-request warmup).
RESTART_WINDOW_BEFORE_SECONDS = 15
RESTART_WINDOW_AFTER_SECONDS = 25


def proxy_restart_times() -> list[_dt.datetime]:
    """Read explicit restart-history file written by start_litellm_proxy.sh."""
    if not RESTART_HISTORY.exists():
        return []
    times: list[_dt.datetime] = []
    try:
        for line in RESTART_HISTORY.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                ts = rec.get("utc", "")
                times.append(_dt.datetime.fromisoformat(ts.replace("Z", "+00:00")))
            except Exception:
                continue
    except Exception:
        pass
    return times


def seen_set() -> set[str]:
    if not SEEN.exists():
        return set()
    return {l.strip() for l in SEEN.read_text().splitlines() if l.strip()}


def mark_seen(path: str):
    with SEEN.open("a") as fh:
        fh.write(path + "\n")


def classify(diag: dict, restart_times: list[_dt.datetime]) -> tuple[str, str, str]:
    """Return (verdict, model_group, suggested_action)."""
    err = diag.get("error", {})
    ts_str = err.get("timestamp", "")
    details = err.get("details", "")
    model = err.get("model", "?")

    # Parse timestamp
    try:
        ts = _dt.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception:
        ts = _dt.datetime.now(_dt.timezone.utc)

    is_generic_connection = "Connection error" in details and len(details) < 60

    # If within restart window, label as restart noise.
    # Window: [restart_time - 15s, restart_time + 25s] covers the kill
    # window plus litellm boot/warmup.
    if is_generic_connection:
        for rt in restart_times:
            delta = (ts - rt).total_seconds()
            if -RESTART_WINDOW_BEFORE_SECONDS <= delta <= RESTART_WINDOW_AFTER_SECONDS:
                return "RESTART_NOISE", model, f"no-op — within {int(delta):+d}s of proxy restart @ {rt.isoformat()}"

    # Real errors — try to extract upstream / pattern
    lower = details.lower()
    if "413" in lower or "request body too large" in lower:
        return "REAL_ERROR", model, "add fallback group for context overflow; check free-mode-large depth"
    if "429" in lower and "midstream" in lower.replace(" ", ""):
        return "REAL_ERROR", model, "mid-stream 429 — upstream hit cap during generation; verify fallback chain depth"
    if "429" in lower and ("daily" in lower or "rate-limits" in lower):
        return "REAL_ERROR", model, "daily-quota upstream — verify smart_cooldown classified correctly"
    if "401" in lower or "invalid api key" in lower:
        return "REAL_ERROR", model, "auth error — re-run verify_all_keys.py for the implicated upstream"
    if "context_window" in lower or "context window" in lower:
        return "REAL_ERROR", model, "context overflow — context_window_fallbacks should have caught this; check rule config"
    if is_generic_connection:
        return "POSSIBLE_RESTART", model, "generic Connection error outside known restart window — check if proxy was up at the timestamp"
    return "REAL_ERROR", model, "unclassified — manual review needed"


def scan_new() -> list[dict]:
    seen = seen_set()
    restart_times = proxy_restart_times()
    findings: list[dict] = []
    for path in sorted(glob.glob(PATTERN)):
        if path in seen:
            continue
        try:
            # Roo files start with `// ...\n` comment lines before JSON.
            raw = Path(path).read_text()
            # strip leading // comment lines
            json_start = raw.find("{")
            if json_start < 0:
                mark_seen(path)
                continue
            diag = json.loads(raw[json_start:])
            verdict, model, action = classify(diag, restart_times)
            findings.append({
                "path": path,
                "timestamp": diag.get("error", {}).get("timestamp", "?"),
                "model": model,
                "verdict": verdict,
                "details": diag.get("error", {}).get("details", "")[:200],
                "action": action,
            })
            mark_seen(path)
        except Exception as e:
            findings.append({
                "path": path, "timestamp": "?", "model": "?",
                "verdict": "PARSE_FAIL", "details": str(e)[:100],
                "action": "manual inspection",
            })
            mark_seen(path)
    return findings


def append_digest(findings: list[dict]):
    if not findings:
        return
    with DIGEST.open("a") as fh:
        for f in findings:
            fh.write(f"\n## {f['timestamp']} — {f['verdict']}\n")
            fh.write(f"- model: `{f['model']}`\n")
            fh.write(f"- file: `{f['path']}`\n")
            fh.write(f"- details: {f['details'][:160]}\n")
            fh.write(f"- action: **{f['action']}**\n")


def print_digest():
    if not DIGEST.exists():
        print("no digest yet")
        return
    print(DIGEST.read_text())


def watch_loop(interval=30):
    print(f"watching {PATTERN} every {interval}s — writing to {DIGEST}")
    while True:
        f = scan_new()
        if f:
            append_digest(f)
            # surface only real errors to stdout for the operator
            real = [x for x in f if x["verdict"] not in ("RESTART_NOISE", "PARSE_FAIL")]
            if real:
                print(f"[{_dt.datetime.now().isoformat(timespec='seconds')}] {len(real)} REAL_ERROR — see {DIGEST}")
                for x in real:
                    print(f"  · {x['timestamp']} {x['verdict']} :: {x['action']}")
            else:
                print(f"[{_dt.datetime.now().isoformat(timespec='seconds')}] {len(f)} new file(s), all RESTART_NOISE")
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--digest", action="store_true")
    ap.add_argument("--interval", type=int, default=30)
    args = ap.parse_args()

    if args.digest:
        print_digest()
        return 0
    if args.watch:
        watch_loop(args.interval)
        return 0
    # One-shot
    findings = scan_new()
    if findings:
        append_digest(findings)
        real = [x for x in findings if x["verdict"] not in ("RESTART_NOISE", "PARSE_FAIL")]
        print(f"{len(findings)} new diagnostic(s) — {len(real)} REAL, {len(findings) - len(real)} restart-noise")
        for x in findings:
            print(f"  {x['timestamp']} [{x['verdict']:<16}] {x['action']}")
    else:
        print("no new diagnostic files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
