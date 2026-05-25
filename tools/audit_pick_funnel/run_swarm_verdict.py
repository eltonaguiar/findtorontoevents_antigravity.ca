"""
run_swarm_verdict.py — Asks the multi-engine swarm whether the edges found by
top_edges.py are real or noise and would have made money in the last 90 days.

Pipeline:
  1. Read audit_dashboard/data/top_edges_per_class.json
  2. Build a structured prompt embedding the JSON + the gate blueprint refs
  3. Invoke tools/swarm/swarm_run.py against deepseek,xai,cerebras,gemini
  4. Collect each engine's verdict into reports/2026-05-25_pick_funnel_swarm_verdict.md

Soft-fails per engine — engines that are unauthenticated are skipped, the rest
still produce a verdict.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOP_EDGES = ROOT / "audit_dashboard" / "data" / "top_edges_per_class.json"
FUNNEL_90D = ROOT / "audit_dashboard" / "data" / "pick_funnel_90d.json"
REPORT_OUT = ROOT / "reports" / "2026-05-25_pick_funnel_swarm_verdict.md"
SWARM_RUNS = ROOT / "swarm_runs"
ENGINES = "deepseek,xai,cerebras,gemini"


def build_prompt() -> Path:
    top = json.loads(TOP_EDGES.read_text())
    funnel = json.loads(FUNNEL_90D.read_text())

    # Trim top edges payload to keep prompt lean
    trimmed = {}
    for ac, b in top["by_class"].items():
        trimmed[ac] = {
            "n_closed": b["n_closed"],
            "top_edges_proven": b["top_edges_proven"][:3],
            "best_pf_overall": b["best_pf_overall"][:3],
        }

    funnel_summary = {ac: {k: v for k, v in b.items()}
                      for ac, b in funnel["funnel_by_class"].items()}

    prompt = f"""# Audit Pick-Funnel Verdict — 90-day edge analysis

You are reviewing the live /audit dashboard pick funnel for findtorontoevents.ca.
Our gates live in `audit_trail/quality_gates.py` (Smart per-class floor map),
`alpha_engine/production_scanner.py` (Smart_Picks scoring), and
`audit_dashboard/hc_filter.js` (HIGH CONVICTION client-side gate at score>=80,
conf>=0.75, trust>=60).

90-day funnel (per asset class — scanned / passed_smart / passed_HC / opened /
closed / win / loss / WR_decisive_only_pct):
```json
{json.dumps(funnel_summary, indent=2)}
```

Top edge cells per asset class — combinations of (trust band, confidence band,
R:R band, strategy family, direction, source) where the cell has n>=20 closed
trades over 90d. "PROVEN" definition: Bayesian-shrunk WR>=55%, PF>=1.5.
```json
{json.dumps(trimmed, indent=2)}
```

## Per asset class, answer:

(a) **Is the identified edge statistically real or sample-noise?** Comment on
   each PROVEN cell's n, WR_shrunk, PF. Flag any that look like leakage,
   look-ahead bias, or single-symbol concentration (especially the FOREX
   `consensus` and CRYPTO `ml` cells — those PF numbers look suspiciously high).

(b) **If we had put real money behind these edges over the last 90 days at
   appropriate sizing (1% risk per trade, $100k notional account), what
   would the expected P&L be?** Provide a concrete dollar estimate and list
   your sizing/slippage assumptions.

(c) **What ONE gate change would lift the edge most?** Be specific: name the
   constant in `audit_trail/quality_gates.py` (e.g. SMART_PICKS_MIN_SCORE_CRYPTO)
   or the variable in `hc_filter.js` and the value you would set it to.

## Format:
For each asset class output exactly:
```
### {{CLASS}}
- Real/noise verdict: ...
- 90d expected P&L (1% risk, $100k): $...
- Gate change: ... = ...
- Confidence (1-5): ...
```

Then add a SYSTEM-WIDE conclusion at the bottom: which class would you scale up
TODAY with real money, and which class should we DEMOTE per the
`docs/MUTATION_THREE_AXIS_PROTOCOL.md` (mutate before kill).

Be brutally honest. The user explicitly says "do not invent edges to look
productive — if a class has no edge, say so."
"""
    prompt_path = SWARM_RUNS / "pick_funnel_prompt.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt)
    return prompt_path


def run_swarm(prompt_path: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = SWARM_RUNS / f"pick_funnel_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, str(ROOT / "tools" / "swarm" / "swarm_run.py"),
        "--prompt-file", str(prompt_path),
        "--engines", ENGINES,
        "--out-dir", str(out_dir),
        "--max-parallel", "4",
    ]
    print(f"[swarm] running: {' '.join(cmd)}", flush=True)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        (out_dir / "_stdout.log").write_text(proc.stdout or "")
        (out_dir / "_stderr.log").write_text(proc.stderr or "")
        print(f"[swarm] exit={proc.returncode}")
    except subprocess.TimeoutExpired:
        print("[swarm] WARN: timed out after 10min")
    return out_dir


def summarize(out_dir: Path) -> None:
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        f"# Pick Funnel Swarm Verdict — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Source: `tools/audit_pick_funnel/run_swarm_verdict.py` (deepseek + xai + "
        "cerebras + gemini consult on top_edges_per_class.json).",
        "",
        f"Swarm run dir: `{out_dir.relative_to(ROOT)}`",
        "",
        "## Per-engine raw responses",
        "",
    ]
    found = 0
    for resp_file in sorted(out_dir.glob("*.json")):
        if resp_file.name.startswith("_") or resp_file.name.endswith(".raw.txt"):
            continue
        try:
            d = json.loads(resp_file.read_text(errors="ignore"))
        except Exception:
            continue
        found += 1
        engine = d.get("engine", resp_file.stem)
        verdict = d.get("verdict", "?")
        conf = d.get("confidence", "?")
        body = d.get("commentary_text") or d.get("summary") or ""
        parts.append(f"### {engine}  (verdict={verdict}, confidence={conf})")
        parts.append("")
        parts.append(body[:20000])
        parts.append("")
    if found == 0:
        parts.append("_No engine responses captured. Check `_stdout.log` / `_stderr.log` "
                     "in the run dir — likely all engines unauthenticated in this env._")
        parts.append("")
        stderr_path = out_dir / "_stderr.log"
        if stderr_path.exists():
            parts.append("```")
            parts.append(stderr_path.read_text()[:4000])
            parts.append("```")
    REPORT_OUT.write_text("\n".join(parts))
    print(f"[swarm] wrote {REPORT_OUT}")


def main() -> int:
    if not TOP_EDGES.exists():
        print(f"ERROR: {TOP_EDGES} missing — run top_edges.py first")
        return 1
    p = build_prompt()
    out_dir = run_swarm(p)
    summarize(out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
