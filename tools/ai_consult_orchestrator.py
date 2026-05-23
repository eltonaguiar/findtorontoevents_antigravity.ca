#!/usr/bin/env python3
"""Multi-phase AI consultation orchestrator for money-ready / asset-class edge.

Phases:
  1 — prompts only (writes manifest)
  2 — API engines (paid first, then free) via tools/swarm/swarm_run.py + api_consult + grok wsl
  3 — local GGUF/Ollama/LM Studio via local_gguf_ollama_consult.py

Usage:
  python tools/ai_consult_orchestrator.py --phase 2 --tier paid
  python tools/ai_consult_orchestrator.py --phase 2 --tier free
  python tools/ai_consult_orchestrator.py --phase 3
  python tools/ai_consult_orchestrator.py --phase all

Outputs: swarm_runs/money-ready-consult/<ts>/
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROMPT_MASTER = REPO / "swarm_runs/_prompts/MONEY_READY_MASTER_v1.md"
PROMPT_HARVEST = REPO / "swarm_runs/_prompts/MONEY_READY_HARVEST_v1.md"
SWARM = REPO / "tools/swarm/swarm_run.py"
API = REPO / "tools/swarm/api_consult.py"
LOCAL_OLLAMA = REPO / "tools/local_gguf_ollama_consult.py"
OLLAMA_IMPORT = REPO / "tools/ollama_import_gguf.py"

PAID_ENGINES = ["xai", "inception", "deepseek", "kimi"]
FREE_ENGINES = ["groq", "openrouter", "ollama_local", "llm7", "gemini_api", "github_models", "pollinations"]
CLI_ENGINES = ["opencode", "kilo"]  # uses OPENCODE_API_KEY / KILOCODE_API_KEY via CLI

# OpenRouter free/fast models to try (engine openrouter + model override via env)
OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "google/gemma-2-9b-it:free",
]


def ts_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = REPO / "swarm_runs/money-ready-consult" / stamp
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_cmd(cmd: list[str], timeout: int, cwd: Path | None = None) -> dict:
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(cwd or REPO), encoding="utf-8", errors="replace",
        )
        elapsed = round(time.time() - t0, 2)
        return {
            "cmd": " ".join(cmd[:6]),
            "rc": proc.returncode,
            "elapsed_s": elapsed,
            "stdout_tail": (proc.stdout or "")[-2000:],
            "stderr_tail": (proc.stderr or "")[-1000:],
            "ok": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"cmd": " ".join(cmd[:6]), "rc": -1, "elapsed_s": timeout, "ok": False, "error": "TIMEOUT"}


def grok_wsl(prompt_path: Path, out_dir: Path) -> dict:
    prompt = prompt_path.read_text(encoding="utf-8")[:12000]
    cmd = [
        "wsl", "bash", "-lc",
        f"grok -p {json.dumps(prompt)} --cwd /tmp --no-alt-screen --output-format json",
    ]
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace")
        elapsed = round(time.time() - t0, 2)
        out_file = out_dir / "grok-wsl.json"
        out_file.write_text(proc.stdout or proc.stderr or "", encoding="utf-8")
        return {"engine": "grok-wsl", "ok": proc.returncode == 0, "elapsed_s": elapsed, "out": str(out_file)}
    except subprocess.TimeoutExpired:
        return {"engine": "grok-wsl", "ok": False, "elapsed_s": 600, "error": "TIMEOUT"}


def phase2(out_dir: Path, tier: str, prompt: Path) -> list[dict]:
    results = []
    engines = PAID_ENGINES + CLI_ENGINES if tier == "paid" else FREE_ENGINES
    eng_dir = out_dir / f"phase2-{tier}"
    eng_dir.mkdir(exist_ok=True)

    if tier == "paid":
        results.append(grok_wsl(prompt, eng_dir))

    if tier in ("paid", "free"):
        eng_list = ",".join(engines)
        r = run_cmd([
            sys.executable, str(SWARM),
            "--prompt-file", str(prompt),
            "--engines", eng_list,
            "--out-dir", str(eng_dir / "swarm"),
            "--max-parallel", "3",
        ], timeout=3600)
        r["tier"] = tier
        r["engines"] = eng_list
        results.append(r)

    # Individual api_consult for openrouter variants
    if tier == "free" and os.environ.get("OPENROUTER") or os.environ.get("OPENROUTER_API_KEY"):
        for model in OPENROUTER_MODELS[:2]:
            slug = model.replace("/", "-").replace(":", "-")[:60]
            r = run_cmd([
                sys.executable, str(API),
                "--provider", "openrouter",
                "--model", model,
                "--prompt-file", str(PROMPT_HARVEST),
            ], timeout=300)
            if r.get("stdout_tail"):
                (eng_dir / f"openrouter-{slug}.txt").write_text(r["stdout_tail"], encoding="utf-8")
            r["engine"] = f"openrouter:{model}"
            results.append(r)

    return results


def phase3(out_dir: Path, prompt: Path) -> list[dict]:
    eng_dir = out_dir / "phase3-local"
    eng_dir.mkdir(exist_ok=True)
    run_cmd([sys.executable, str(OLLAMA_IMPORT), "--import-all"], timeout=7200)
    r = run_cmd([
        sys.executable, str(LOCAL_OLLAMA),
        "--out-dir", str(eng_dir),
        "--import-missing",
        "--all-installed",
    ], timeout=7200)
    r["phase"] = 3
    r["prompt"] = str(prompt)
    return [r]


def write_manifest(out_dir: Path, results: list) -> None:
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "prompt_master": str(PROMPT_MASTER),
        "prompt_harvest": str(PROMPT_HARVEST),
        "out_dir": str(out_dir),
        "results": results,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["1", "2", "3", "all"], default="2")
    ap.add_argument("--tier", choices=["paid", "free", "both"], default="paid")
    ap.add_argument("--prompt", choices=["master", "harvest"], default="master")
    args = ap.parse_args()

    prompt = PROMPT_MASTER if args.prompt == "master" else PROMPT_HARVEST
    out_dir = ts_dir()
    print(f"Output: {out_dir}")
    all_results: list[dict] = []

    if args.phase in ("1", "all"):
        (out_dir / "prompts").mkdir(exist_ok=True)
        for p in (PROMPT_MASTER, PROMPT_HARVEST):
            dest = out_dir / "prompts" / p.name
            dest.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        all_results.append({"phase": 1, "ok": True, "note": "prompts copied"})

    if args.phase in ("2", "all"):
        tiers = ["paid", "free"] if args.tier == "both" else [args.tier]
        for t in tiers:
            print(f"=== Phase 2 tier={t} ===")
            all_results.extend(phase2(out_dir, t, prompt))

    if args.phase in ("3", "all"):
        print("=== Phase 3 local ===")
        all_results.extend(phase3(out_dir, PROMPT_HARVEST))

    write_manifest(out_dir, all_results)
    ok = sum(1 for r in all_results if r.get("ok"))
    print(f"Done {ok}/{len(all_results)} steps ok. Manifest: {out_dir / 'manifest.json'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
