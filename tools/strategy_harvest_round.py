#!/usr/bin/env python3
"""Strategy harvest: TOP10 MD -> cloud meta-debate -> local execute.

  python tools/strategy_harvest_round.py --phase build
  python tools/strategy_harvest_round.py --phase cloud
  python tools/strategy_harvest_round.py --phase local
  python tools/strategy_harvest_round.py --phase all
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILD = REPO / "tools" / "build_top10_strategies_per_class.py"
GRILL = REPO / "tools" / "model_grill_sequential.py"
DEBATE_TEMPLATE = REPO / "docs" / "swarm_prompts" / "META_DEBATE_PER_CLASS_v1.md"
EXECUTE_TEMPLATE = REPO / "docs" / "swarm_prompts" / "STRATEGY_HARVEST_EXECUTE_v1.md"
PROMPTS_DIR = REPO / "swarm_runs" / "_prompts"
FINAL = REPO / "reports" / "STRATEGY_HARVEST_SYNTHESIS_2026-05-19.md"


def latest_top10() -> Path:
    files = sorted(REPO.glob("reports/TOP10_STRATEGIES_PER_ASSET_CLASS_*.md"), reverse=True)
    if not files:
        raise FileNotFoundError("Run --phase build first")
    return files[0]


def stage_prompt(name: str, template: Path, replacements: dict[str, str]) -> Path:
    text = template.read_text(encoding="utf-8")
    for k, v in replacements.items():
        text = text.replace(k, v)
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    out = PROMPTS_DIR / name
    out.write_text(text, encoding="utf-8")
    return out


def run_build() -> Path:
    subprocess.run([sys.executable, str(BUILD)], cwd=str(REPO), check=True)
    return latest_top10()


def run_grill(wave: str, prompt_key: str, api_timeout: int = 180) -> Path:
    r = subprocess.run(
        [
            sys.executable,
            str(GRILL),
            "--wave",
            wave,
            "--prompt",
            prompt_key,
            "--api-timeout",
            str(api_timeout),
        ],
        cwd=str(REPO),
    )
    if r.returncode != 0:
        sys.exit(r.returncode)
    base = REPO / "swarm_runs" / "model-grill"
    return sorted(base.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)[0]


def extract_debate_summary(cloud_dir: Path) -> str:
    parts = []
    for p in sorted(cloud_dir.glob("*__meta_debate.md")):
        body = p.read_text(encoding="utf-8")
        if len(body) > 400:
            parts.append(f"## {p.name}\n\n{body[-3500:]}")
    return "\n\n".join(parts) if parts else "(no cloud debate outputs)"


def synthesize(top10: Path, cloud_dir: Path | None, local_dir: Path | None) -> None:
    lines = [
        f"# Strategy harvest synthesis (2026-05-19)",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"## Source: {top10.name}",
        "",
        top10.read_text(encoding="utf-8")[:5000],
        "",
    ]
    if cloud_dir:
        lines.append(f"## Cloud debate (`{cloud_dir.name}`)\n")
        for p in sorted(cloud_dir.glob("*__meta_debate.md")):
            lines.append(f"### {p.name}\n")
            lines.append(p.read_text(encoding="utf-8")[:7000])
    if local_dir:
        lines.append(f"\n## Local execute (`{local_dir.name}`)\n")
        for p in sorted(local_dir.glob("*__strategy_harvest.md")):
            lines.append(f"### {p.name}\n")
            lines.append(p.read_text(encoding="utf-8")[:8000])
    lines.extend(
        [
            "",
            "## How to proceed next (operator)",
            "",
            "1. `python tools/build_top10_strategies_per_class.py` after each dashboard deploy",
            "2. Flip `EMITTER_WHITELIST_ENFORCE=1` only for classes where Judge verdict=RESCUE on rank1-3",
            "3. Pre-register tick/intraday hypotheses (CRYPTO) — not daily-bar killed families",
            "4. Re-run: `python tools/strategy_harvest_round.py --phase all`",
            "",
        ]
    )
    FINAL.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {FINAL}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["build", "cloud", "local", "all"], default="all")
    args = ap.parse_args()

    top10 = latest_top10() if args.phase != "build" else None
    cloud_dir = local_dir = None

    if args.phase in ("build", "all"):
        top10 = run_build()

    md = top10.read_text(encoding="utf-8")
    stage_prompt(
        "META_DEBATE_PER_CLASS_v1.md",
        DEBATE_TEMPLATE,
        {"{{TOP10_STRATEGIES_MD}}": md},
    )

    if args.phase in ("cloud", "all"):
        print("Cloud meta-debate...", flush=True)
        cloud_dir = run_grill("harvest_cloud", "meta_debate", api_timeout=200)

    debate_summary = extract_debate_summary(cloud_dir) if cloud_dir else "(run cloud phase first)"
    stage_prompt(
        "STRATEGY_HARVEST_EXECUTE_v1.md",
        EXECUTE_TEMPLATE,
        {
            "{{TOP10_STRATEGIES_MD}}": md,
            "{{DEBATE_SYNTHESIS}}": debate_summary,
        },
    )

    if args.phase in ("local", "all"):
        print("Local strategy harvest...", flush=True)
        local_dir = run_grill("harvest_local", "strategy_harvest")

    if args.phase == "all":
        synthesize(top10, cloud_dir, local_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
