#!/usr/bin/env python3
"""Inspect a swarm run directory: per-engine response size, status flags,
preview of first/last chars. Fast-eyeballs whether engines returned real
content vs stub/dummy/credit-exhausted/banner-only output.

Heuristic flags applied to each engine response:
  ZERO       : raw byte size == 0 (process produced no output at all)
  TINY       : raw < 200 B (almost certainly garbage / banner-only)
  SHORT      : raw < 1 KB (suspicious for substantive prompts)
  HEALTHY    : raw >= 1 KB and parses as JSON if briefing was JSON-strict
  CREDITS?   : raw contains "credits" / "quota" / "rate limit" / "billing"
  AUTH?      : raw contains "401" / "403" / "unauthorized" / "forbidden"
  TRUNCATED? : raw ends mid-word with no terminating brace/bracket

Usage:
    python tools/swarm/swarm_inspect.py <run_dir>
    python tools/swarm/swarm_inspect.py --latest
    python tools/swarm/swarm_inspect.py --latest --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SWARM_DIR = REPO / "swarm_runs"

# Tight: only flag credit/quota when response looks like an ERROR message,
# not when "credit" appears inside substantive JSON (e.g., "credit spread"
# on a BOND strategy).
CRED_RE = re.compile(
    r"\b(out of credits?|insufficient credits?|no credits?|credit (?:limit|exhausted)|"
    r"quota (?:exceeded|exhausted|reached)|"
    r"rate[\s-]?limit(?:ed| reached| exceeded)|"
    r"billing (?:issue|error|required)|"
    r"insufficient (?:balance|funds))\b",
    re.I,
)
AUTH_RE = re.compile(
    r"\b(40[13]\b|unauthori[sz]ed|forbidden|invalid (?:api[\s_-]?key|token|credentials)|"
    r"authentication (?:failed|required))\b",
    re.I,
)
def _flags(raw: str, json_obj: dict | None) -> list[str]:
    flags: list[str] = []
    n = len(raw)
    if n == 0:
        flags.append("ZERO")
    elif n < 200:
        flags.append("TINY")
    elif n < 1024:
        flags.append("SHORT")
    else:
        flags.append("HEALTHY")
    if CRED_RE.search(raw):
        flags.append("CREDITS?")
    if AUTH_RE.search(raw):
        flags.append("AUTH?")
    # Truncation heuristic: ends mid-token without proper closure.
    tail = raw.rstrip()[-3:] if raw.strip() else ""
    if tail and tail[-1] not in ('}', ']', '"', '.', ')', '`', '\n'):
        flags.append("TRUNCATED?")
    if json_obj and isinstance(json_obj, dict):
        # Worker-runner stub envelope from un-parseable output.
        if (json_obj.get("verdict") == "COMMENT_ONLY"
                and json_obj.get("fabrication_risk", {}).get("level") == "HIGH"):
            flags.append("PARSE_FAILED")
    return flags


def _preview(raw: str, n: int = 80) -> str:
    if not raw:
        return ""
    s = raw.strip().replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s)
    return (s[:n] + "...") if len(s) > n else s


def inspect_run(run_dir: Path) -> dict:
    """Walk a swarm_runs/<TS>/ dir and return per-engine inspection report.

    Two run shapes are supported:

    - **Fan-out** (default, written by `swarm_run.py`): files like
      `engine.json` or `pr_<N>.<engine>.json`. Engine name is derived from
      the last dot-segment of the filename stem.
    - **Chain** (written by `swarm_followup.py`): files like
      `turn_<N>_<name>.json`, all from a single engine recorded in
      `_chain_summary.json::engine`. Each row is labelled
      ``<engine>:turn_<N>`` so a multi-turn deep-dive doesn't masquerade
      as N different "engines" called `turn_1_priming`, `turn_2_analysis`,
      etc. Detection rule: presence of `_chain_summary.json` in run_dir.
    """
    if not run_dir.exists():
        raise FileNotFoundError(f"{run_dir} does not exist")

    # Detect chain vs fan-out.
    chain_summary_path = run_dir / "_chain_summary.json"
    is_chain = chain_summary_path.exists()
    chain_engine = ""
    if is_chain:
        try:
            chain_meta = json.loads(
                chain_summary_path.read_text(encoding="utf-8", errors="replace"))
            chain_engine = chain_meta.get("engine") or ""
        except Exception:
            chain_meta = {}
            chain_engine = ""

    # Chain prompt sidecars (written by swarm_followup._resolve_turn_prompt)
    # are `_turn_<N>_<name>_prompt.md` — already covered by the `_*` skip,
    # but be explicit about excluding non-JSON anyway.
    engines: list[dict] = []

    # Build a list of (json_path, engine_override_from_subdir) tuples that
    # spans both run-shape variants:
    #
    #   1. Flat fan-out:  run_dir/<file>.json
    #      Engine name derived from the last dot-segment of the stem.
    #      (existing behavior — preserved verbatim.)
    #
    #   2. Per-engine subdir (item 3, 2026-05-03): run_dir/<engine>/<file>.json
    #      Used by swarm_dispatch.ps1 PR-review pipeline. Engine name comes
    #      from the immediate parent directory name; if the filename also
    #      carries an explicit dot-suffix (e.g. `pr_724.deepseek.json`),
    #      that wins so a stray copy under the wrong subdir doesn't relabel
    #      itself.
    #
    # The chain detection (`_chain_summary.json`) only fires for shape #1.
    candidates: list[tuple[Path, str]] = []
    for f in sorted(run_dir.iterdir()):
        if f.is_file() and f.suffix == ".json" \
                and not f.name.startswith("_") \
                and f.name not in ("final_merge_plan.json", "redteam.json"):
            candidates.append((f, ""))
    if not is_chain:
        # Recurse one level into immediate subdirs that look like
        # per-engine output bins (i.e. contain at least one pr_*.json).
        for sub in sorted(p for p in run_dir.iterdir() if p.is_dir()):
            if sub.name.startswith("_"):
                continue
            try:
                pr_jsons = [
                    p for p in sub.iterdir()
                    if p.is_file() and p.suffix == ".json"
                    and p.name.startswith("pr_")
                    and not p.name.startswith("_")
                ]
            except OSError:
                continue
            if not pr_jsons:
                continue
            engine_from_subdir = sub.name
            for f in sorted(pr_jsons):
                candidates.append((f, engine_from_subdir))

    for f, subdir_engine in candidates:
        raw_path = f.with_suffix(f.suffix + ".raw.txt")
        try:
            envelope = json.loads(f.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            envelope = None
        try:
            raw = raw_path.read_text(encoding="utf-8", errors="replace") if raw_path.exists() else ""
        except Exception:
            raw = ""

        if is_chain:
            # Chain filenames are `turn_<N>_<name>.json`. Label as
            # `<engine>:turn_<N>` so the table reflects the real engine.
            stem = f.stem  # e.g. "turn_1_priming"
            turn_label = stem
            m = re.match(r"^(turn_\d+)(?:_.+)?$", stem)
            if m:
                turn_label = m.group(1)
            engine_name = (f"{chain_engine}:{turn_label}"
                           if chain_engine else turn_label)
        else:
            # Fan-out: prefer filename-derived engine (what the worker
            # invoked) over the envelope's engine field (which the model can
            # spoof — e.g. cerebras responses sometimes claim engine="gpt-4o").
            stem_parts = f.stem.split(".")
            # Per-engine subdir layout (item 3): if the filename has only
            # one dot-segment (e.g. `pr_608.json` -> stem `pr_608`), the
            # filename can't tell us the engine — fall back to the parent
            # directory name. If the filename DOES carry an explicit dot-
            # suffix (e.g. `pr_608.deepseek.json` -> stem `pr_608.deepseek`),
            # we trust the filename even inside a subdir.
            if subdir_engine and len(stem_parts) == 1:
                engine_name = subdir_engine
            else:
                engine_name = stem_parts[-1]
            if envelope and isinstance(envelope, dict) and not engine_name:
                engine_name = envelope.get("engine") or ""

        rec = {
            "file": f.name,
            "engine": engine_name,
            "envelope_bytes": f.stat().st_size,
            "raw_bytes": len(raw.encode("utf-8", errors="replace")),
            "raw_path": str(raw_path) if raw_path.exists() else None,
            "flags": _flags(raw, envelope),
            "preview_head": _preview(raw, 100),
            "preview_tail": _preview(raw[-200:], 80) if len(raw) > 200 else "",
        }
        # imp-B: surface audit-trail fields if the envelope carries them.
        # Legacy envelopes lack `_swarm_meta` or its imp-B keys; default to ""/0
        # so old runs don't crash (back-compat).
        meta = (envelope or {}).get("_swarm_meta") or {} if isinstance(envelope, dict) else {}
        ti = int(meta.get("tokens_in") or 0)
        to = int(meta.get("tokens_out") or 0)
        if ti or to:
            rec["tokens_used"] = {"in": ti, "out": to, "total": ti + to}
        fp = meta.get("model_fingerprint") or ""
        if fp:
            rec["model_fingerprint"] = fp
        ts = meta.get("transport_status") or ""
        if ts and ts != "ok":
            rec["transport_status"] = ts
        rc_n = int(meta.get("retry_count") or 0)
        if rc_n:
            rec["retry_count"] = rc_n
        engines.append(rec)

    summary = {}
    if is_chain:
        # Surface the chain summary as the inspection summary so callers
        # (and --json consumers) can see ok_count / total / session ids.
        try:
            summary = chain_meta  # already parsed above
        except Exception:
            summary = {}
    else:
        summary_path = run_dir / "_summary.json"
        if summary_path.exists():
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
            except Exception:
                summary = {}

    # Status verdict per engine.
    healthy = sum(1 for e in engines if "HEALTHY" in e["flags"])
    suspect = sum(1 for e in engines
                  if any(f in e["flags"] for f in ("ZERO", "TINY", "PARSE_FAILED",
                                                  "CREDITS?", "AUTH?", "TUI_ONLY")))
    return {
        "run_dir": str(run_dir),
        "run_kind": "chain" if is_chain else "fanout",
        "chain_engine": chain_engine,
        "engines": engines,
        "engine_count": len(engines),
        "healthy": healthy,
        "suspect": suspect,
        "summary": summary,
    }


def render_table(report: dict) -> str:
    kind = report.get("run_kind", "fanout")
    chain_engine = report.get("chain_engine") or ""
    header = f"=== swarm_inspect: {report['run_dir']} ==="
    lines = [header]
    if kind == "chain":
        lines.append(f"run_kind=chain  engine={chain_engine or '(unknown)'}  "
                     f"turns={report['engine_count']}  "
                     f"healthy={report['healthy']}  suspect={report['suspect']}")
    else:
        lines.append(f"run_kind=fanout  engines={report['engine_count']}  "
                     f"healthy={report['healthy']}  suspect={report['suspect']}")
    lines.append("")
    # imp-B: only show tokens / model_fp columns when at least one engine
    # carries the field — keeps legacy run dirs identical.
    show_tokens = any("tokens_used" in e for e in report["engines"])
    show_fp = any("model_fingerprint" in e for e in report["engines"])
    headers = ["engine", "raw_B", "env_B"]
    if show_tokens:
        headers += ["tok_used"]
    if show_fp:
        headers += ["model_fp"]
    headers += ["flags", "preview"]
    rows = [headers]
    for e in report["engines"]:
        row = [
            e["engine"],
            f"{e['raw_bytes']:>7}",
            f"{e['envelope_bytes']:>5}",
        ]
        if show_tokens:
            tu = e.get("tokens_used") or {}
            row += [f"{tu.get('total', 0)}" if tu else "-"]
        if show_fp:
            row += [(e.get("model_fingerprint") or "-")[:24]]
        row += [
            ",".join(e["flags"]) or "-",
            e["preview_head"][:60] + ("..." if len(e["preview_head"]) > 60 else ""),
        ]
        rows.append(row)
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(headers))]
    for r_i, row in enumerate(rows):
        line = " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(row))
        lines.append(line)
        if r_i == 0:
            lines.append("-+-".join("-" * w for w in widths))
    if report["suspect"]:
        lines.append("")
        lines.append("⚠ Suspect engines (re-run individually with --debug):")
        for e in report["engines"]:
            sus = [f for f in e["flags"] if f in ("ZERO", "TINY", "PARSE_FAILED",
                                                  "CREDITS?", "AUTH?", "TUI_ONLY", "TRUNCATED?")]
            if sus:
                lines.append(f"  - {e['engine']:<14} flags={','.join(sus)} raw={e['raw_path']}")
    return "\n".join(lines)


def find_latest_run() -> Path | None:
    if not SWARM_DIR.exists():
        return None
    candidates = []
    for p in SWARM_DIR.iterdir():
        if p.is_dir() and p.name.startswith(("run_", "followup_", "20")):
            candidates.append(p)
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", nargs="?")
    ap.add_argument("--latest", action="store_true",
                    help="auto-pick the most-recent swarm_runs/ subdir")
    ap.add_argument("--json", action="store_true",
                    help="emit JSON report instead of text table")
    args = ap.parse_args()

    if args.latest or not args.run_dir:
        rd = find_latest_run()
        if rd is None:
            print("no run dirs found in swarm_runs/", file=sys.stderr)
            return 1
    else:
        rd = Path(args.run_dir)

    try:
        report = inspect_run(rd)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_table(report))
    return 0 if report["suspect"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
