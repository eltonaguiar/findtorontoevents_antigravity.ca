#!/usr/bin/env python3
"""Read swarm_runs/_calls.jsonl and print per-engine call stats.

Surfaces zombie/erroring engines: low_signal_rate >= 50% or ok_rate < 50%.

Usage:
    python tools/swarm/swarm_stats.py
    python tools/swarm/swarm_stats.py --since 2026-05-03
    python tools/swarm/swarm_stats.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOG_PATH = REPO / "swarm_runs" / "_calls.jsonl"


def _load(since: str | None) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    out: list[dict] = []
    with LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since and rec.get("ts_utc", "") < since:
                continue
            out.append(rec)
    return out


def aggregate(records: list[dict]) -> dict:
    by_engine: dict[str, dict] = defaultdict(lambda: {
        "calls": 0, "ok": 0, "low_signal": 0, "errors": 0,
        "total_latency_s": 0.0, "total_in_bytes": 0, "total_out_bytes": 0,
        "errors_seen": [], "models": set(),
        # imp-B audit-trail completeness aggregates. `*_seen` counts records
        # that carry a non-empty/non-zero value, used to decide whether to
        # render the new columns at all (back-compat with legacy logs).
        "total_tokens_in": 0, "total_tokens_out": 0,
        "tokens_seen": 0,
        "model_fps": set(), "fp_seen": 0,
        "transport_statuses": defaultdict(int),
        "retries_total": 0, "retry_seen": 0,
    })
    for r in records:
        e = r.get("engine") or "?"
        b = by_engine[e]
        b["calls"] += 1
        if r.get("ok"):
            b["ok"] += 1
        if r.get("low_signal"):
            b["low_signal"] += 1
        if r.get("returncode", 0) != 0:
            b["errors"] += 1
            err = r.get("error") or ""
            if err and len(b["errors_seen"]) < 3:
                b["errors_seen"].append(err[:200])
        b["total_latency_s"] += r.get("latency_s", 0.0)
        b["total_in_bytes"] += r.get("prompt_bytes", 0)
        b["total_out_bytes"] += r.get("output_bytes", 0)
        m = r.get("model")
        if m:
            b["models"].add(m)
        # imp-B fields — guard with `in` so legacy logs (no key) are skipped.
        if "tokens_in" in r or "tokens_out" in r:
            ti = int(r.get("tokens_in") or 0)
            to = int(r.get("tokens_out") or 0)
            if ti or to:
                b["total_tokens_in"] += ti
                b["total_tokens_out"] += to
                b["tokens_seen"] += 1
        if "model_fingerprint" in r:
            fp = r.get("model_fingerprint") or ""
            if fp:
                b["model_fps"].add(fp)
                b["fp_seen"] += 1
        if "transport_status" in r:
            ts = r.get("transport_status") or ""
            if ts:
                b["transport_statuses"][ts] += 1
        if "retry_count" in r:
            rc_n = int(r.get("retry_count") or 0)
            if rc_n:
                b["retries_total"] += rc_n
                b["retry_seen"] += 1

    summary = []
    for eng, b in sorted(by_engine.items()):
        n = b["calls"] or 1
        ok_rate = b["ok"] / n
        low_rate = b["low_signal"] / n
        flags = []
        if b["calls"] == 0:
            flags.append("UNUSED")
        if ok_rate < 0.5 and b["calls"] >= 2:
            flags.append("LOW_OK_RATE")
        if low_rate >= 0.5 and b["calls"] >= 2:
            flags.append("ZOMBIE_OUTPUT")
        if b["errors"] >= 1 and b["errors"] / n >= 0.5:
            flags.append("ERRORING")
        summary.append({
            "engine": eng, "calls": b["calls"], "ok": b["ok"],
            "ok_rate_pct": round(100 * ok_rate, 1),
            "low_signal": b["low_signal"], "errors": b["errors"],
            "avg_latency_s": round(b["total_latency_s"] / n, 2),
            "avg_in_bytes": int(b["total_in_bytes"] / n),
            "avg_out_bytes": int(b["total_out_bytes"] / n),
            "models": sorted(b["models"]), "flags": flags,
            "errors_seen": b["errors_seen"],
            # imp-B completeness aggregates.
            "tokens_seen": b["tokens_seen"],
            "avg_tokens_in": int(b["total_tokens_in"] / b["tokens_seen"]) if b["tokens_seen"] else 0,
            "avg_tokens_out": int(b["total_tokens_out"] / b["tokens_seen"]) if b["tokens_seen"] else 0,
            "fp_seen": b["fp_seen"],
            "model_fingerprints": sorted(b["model_fps"]),
            "transport_statuses": dict(b["transport_statuses"]),
            "retries_total": b["retries_total"],
            "retry_seen": b["retry_seen"],
        })
    return {"engines": summary, "total_calls": sum(s["calls"] for s in summary)}


def render_table(summary: dict) -> str:
    rows = summary["engines"]
    if not rows:
        return "(no calls logged yet)"
    # imp-B columns are added IFF at least one record carries the relevant
    # field — preserves the existing layout for legacy-only logs.
    show_tokens = any(r.get("tokens_seen", 0) for r in rows)
    show_fp = any(r.get("fp_seen", 0) for r in rows)
    headers = ["engine", "calls", "ok", "ok%", "low", "err", "avg_s", "in_b", "out_b"]
    if show_tokens:
        headers += ["tok_in", "tok_out"]
    if show_fp:
        headers += ["model_fp"]
    headers += ["flags"]
    table = [headers]
    for r in rows:
        row = [
            r["engine"], r["calls"], r["ok"], r["ok_rate_pct"],
            r["low_signal"], r["errors"], r["avg_latency_s"],
            r["avg_in_bytes"], r["avg_out_bytes"],
        ]
        if show_tokens:
            row += [r.get("avg_tokens_in", 0), r.get("avg_tokens_out", 0)]
        if show_fp:
            fps = r.get("model_fingerprints", [])
            row += [(",".join(fps)[:24] if fps else "-")]
        row += [",".join(r["flags"]) or "-"]
        table.append(row)
    widths = [max(len(str(row[i])) for row in table) for i in range(len(headers))]
    lines = [" | ".join(str(c).ljust(widths[i]) for i, c in enumerate(table[0]))]
    lines.append("-+-".join("-" * w for w in widths))
    for row in table[1:]:
        lines.append(" | ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)))
    for r in rows:
        for err in r["errors_seen"]:
            lines.append(f"  [{r['engine']}] err: {err}")
        # Surface non-ok transport statuses as a one-liner per engine.
        tss = r.get("transport_statuses") or {}
        non_ok = {k: v for k, v in tss.items() if k not in ("ok", "")}
        if non_ok:
            lines.append(f"  [{r['engine']}] transport: "
                         + ", ".join(f"{k}={v}" for k, v in sorted(non_ok.items())))
    lines.append(f"\nTotal calls: {summary['total_calls']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    records = _load(args.since)
    summary = aggregate(records)
    if args.json:
        print(json.dumps(summary, indent=2, default=list))
    else:
        print(render_table(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
