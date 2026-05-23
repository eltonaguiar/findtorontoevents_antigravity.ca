#!/usr/bin/env python3
"""Rescue edge round: cloud question-factory -> curate -> local execute.

Phase A: cloud models invent creative rescue questions (rescue_factory).
Phase B: merge cloud outputs + daily-ideas digest into curated list.
Phase C: local Ollama answers curated questions (rescue_execute).

Usage:
  python tools/rescue_edge_round.py --phase cloud
  python tools/rescue_edge_round.py --phase curate --cloud-dir swarm_runs/model-grill/<stamp>
  python tools/rescue_edge_round.py --phase local
  python tools/rescue_edge_round.py --phase all
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DIGEST = REPO / "reports" / "DAILY_IDEAS_DIGEST_FOR_RESCUE_2026-05-19.md"
CURATED = REPO / "reports" / "RESCUE_CURATED_QUESTIONS_2026-05-19.md"
EXECUTE_PROMPT = REPO / "docs" / "swarm_prompts" / "RESCUE_EDGE_EXECUTE_v1.md"
EXECUTE_STAGED = REPO / "swarm_runs" / "_prompts" / "RESCUE_EDGE_EXECUTE_STAGED.md"
FINAL_REPORT = REPO / "reports" / "RESCUE_EDGE_CREATIVE_2026-05-19.md"
GRILL = REPO / "tools" / "model_grill_sequential.py"

# Seed questions from digest (used if cloud curate finds few)
SEED_QUESTIONS = """
### CRYPTO
- RESCUE_CRYPTO_01: What single tick-level experiment proves H-035 in 30d without killed daily-bar families? Falsify if eff<0.30 on 3/5 windows.
- RESCUE_CRYPTO_02: Can we isolate elite systems (`aggregated_picks`, `mega_mutation`) with emitter whitelist + UTC hour — what SQL proves drag removal lifts WR≥50?
- RESCUE_CRYPTO_MOON: Does 5m order-flow imbalance predict 4h forward return conditional on funding z-score decile?

### EQUITY
- RESCUE_EQUITY_01: Which `at_raw_picks` column replaces inverted confidence for HC gating? Falsify if Spearman(confidence, pnl)>0 on n≥200.
- RESCUE_EQUITY_02: Does PEAD top-100 + trust_score≥0.7 beat PEAD alone on walk-forward? Falsify if PF<1.2.
- RESCUE_EQUITY_MOON: Sector rotation (XLK/XLE spread) as regime gate for equity picks only?

### COMMODITY
- RESCUE_COMMODITY_01: After dedup, does `multi_asset_cot` on non-CT=F symbols still show PF≥1.5 n≥50? Falsify if all symbols fail.
- RESCUE_COMMODITY_02: DBMF replication — does our COMMODITY PnL correlate >0.3 with DBMF monthly? Falsify if ρ<0.1.
- RESCUE_COMMODITY_MOON: Roll-yield sign × COT percentile interaction — pre-register on weekly bars only.

### ETF
- RESCUE_ETF_01: ETF premium/discount vs NAV — do we have data path or free API? Falsify if no historical series.
- RESCUE_ETF_02: Are ETF picks 90% equity beta — if yes, merge class or add beta-neutral filter?
- RESCUE_ETF_MOON: Rates-regime gate (TLT/IEF ratio) sizing ETF picks only?

### FOREX
- RESCUE_FOREX_01: Isolate `signal_validation` FOREX rows only — PF on that slice vs class? Falsify if n<30 or PF<1.0.
- RESCUE_FOREX_02: G10 carry factor from free FRED/ECB — pre-register weekly, not daily COT?
- RESCUE_FOREX_MOON: Session overlap (London+NY) volatility filter for any surviving FOREX emitter?

### BOND
- RESCUE_BOND_01: Freeze BOND emissions 90d — does portfolio PF/MDD improve? Falsify if BOND slice was positive expectancy.
- RESCUE_BOND_02: `etf-bond-scanner` only path — can we reach n=100 in 12mo at current emit rate?
- RESCUE_BOND_MOON: Curve steepener (2s10s) regime gate for bond picks — monthly bars only?

### META
- RESCUE_META_01: Does universal dedup + resolver v2.1 explain >50% of cross-class PF inflation vs raw?
"""


def run_cloud() -> Path:
    print("Phase A: cloud rescue_factory (rescue_cloud wave)...", flush=True)
    r = subprocess.run(
        [
            sys.executable,
            str(GRILL),
            "--wave",
            "rescue_cloud",
            "--prompt",
            "rescue_factory",
            "--api-timeout",
            "180",
        ],
        cwd=str(REPO),
    )
    if r.returncode != 0:
        sys.exit(r.returncode)
    # latest manifest dir
    base = REPO / "swarm_runs" / "model-grill"
    dirs = sorted(base.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[0] if dirs else base


def extract_questions(text: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(
        r"(?:Q-ID:\s*RESCUE_[A-Z0-9_]+|RESCUE_[A-Z]+_\d+|###\s*(?:CRYPTO|EQUITY|COMMODITY|ETF|FOREX|BOND|META))"
        r"[^\n]*\n(?:.*?\n){0,12}",
        text,
        re.I | re.MULTILINE,
    ):
        block = m.group(0).strip()
        if len(block) > 40:
            out.append(block)
    return out


def curate(cloud_dir: Path | None) -> None:
    print("Phase B: curate questions...", flush=True)
    blocks: list[str] = []
    if DIGEST.is_file():
        blocks.append("## Daily-ideas digest seeds\n\n" + DIGEST.read_text(encoding="utf-8")[:4000])

    if cloud_dir and cloud_dir.is_dir():
        for p in sorted(cloud_dir.glob("*__rescue_factory.md")):
            body = p.read_text(encoding="utf-8")
            qs = extract_questions(body)
            if qs:
                blocks.append(f"## From {p.name}\n\n" + "\n\n".join(qs[:12]))
            elif len(body) > 500:
                blocks.append(f"## Summary excerpt: {p.name}\n\n" + body[-3500:])

    curated_body = (
        "# Curated rescue questions (2026-05-19)\n\n"
        "Merged: daily-ideas digest + cloud factory outputs + seeds.\n\n"
        + "\n\n".join(blocks)
        + "\n\n## Fixed seeds (always include)\n"
        + SEED_QUESTIONS
    )
    CURATED.write_text(curated_body, encoding="utf-8")
    print(f"Wrote {CURATED}", flush=True)

    template = EXECUTE_PROMPT.read_text(encoding="utf-8")
    staged = template.replace("{{CURATED_QUESTIONS}}", curated_body)
    EXECUTE_STAGED.parent.mkdir(parents=True, exist_ok=True)
    EXECUTE_STAGED.write_text(staged, encoding="utf-8")


def run_local() -> Path:
    if not EXECUTE_STAGED.is_file():
        curate(None)
    print("Phase C: local rescue_execute (sequential)...", flush=True)
    # Temporarily point grill at staged prompt via swarm_runs/_prompts copy name
    staged_name = "RESCUE_EDGE_EXECUTE_STAGED.md"
    if not (REPO / "swarm_runs" / "_prompts" / staged_name).exists():
        EXECUTE_STAGED.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(EXECUTE_STAGED, REPO / "swarm_runs" / "_prompts" / staged_name)

    # Staged prompt overrides tracked (model_grill _prompt_path prefers swarm_runs/_prompts/)
    local_prompt = REPO / "swarm_runs" / "_prompts" / "RESCUE_EDGE_EXECUTE_v1.md"
    local_prompt.write_text(EXECUTE_STAGED.read_text(encoding="utf-8"), encoding="utf-8")

    r = subprocess.run(
        [
            sys.executable,
            str(GRILL),
            "--wave",
            "rescue_local",
            "--prompt",
            "rescue_execute",
            "--no-cloud-parallel",
        ],
        cwd=str(REPO),
    )
    if r.returncode != 0:
        sys.exit(r.returncode)
    base = REPO / "swarm_runs" / "model-grill"
    dirs = sorted(base.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[0] if dirs else base


def synthesize_report(cloud_dir: Path | None, local_dir: Path | None) -> None:
    parts = [
        "# Rescue edge creative synthesis (2026-05-19)\n",
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n",
        "\n## Curated questions\n",
        CURATED.read_text(encoding="utf-8")[:8000] if CURATED.is_file() else "(missing)\n",
    ]
    if cloud_dir:
        parts.append(f"\n## Cloud factory dir\n`{cloud_dir}`\n")
        for p in sorted(cloud_dir.glob("*__rescue_factory.md")):
            parts.append(f"\n### {p.name}\n")
            parts.append(p.read_text(encoding="utf-8")[:6000])
    if local_dir:
        parts.append(f"\n## Local execute dir\n`{local_dir}`\n")
        for p in sorted(local_dir.glob("*__rescue_execute.md")):
            parts.append(f"\n### {p.name}\n")
            parts.append(p.read_text(encoding="utf-8")[:8000])
    FINAL_REPORT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {FINAL_REPORT}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["cloud", "curate", "local", "all"], default="all")
    ap.add_argument("--cloud-dir", type=Path, help="model-grill stamp for curate")
    args = ap.parse_args()

    cloud_dir = args.cloud_dir
    local_dir = None

    if args.phase in ("cloud", "all"):
        cloud_dir = run_cloud()

    if args.phase in ("curate", "all"):
        curate(cloud_dir)

    if args.phase in ("local", "all"):
        if not CURATED.is_file():
            curate(cloud_dir)
        local_dir = run_local()

    if args.phase == "all":
        synthesize_report(cloud_dir, local_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
