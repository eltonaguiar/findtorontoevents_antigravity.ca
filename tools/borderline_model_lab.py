#!/usr/bin/env python3
"""Experiment matrix for models just outside RTX 5070 12GB / 32GB RAM.

Tests Ollama HTTP /api/generate with num_gpu, num_ctx, num_predict sweeps.
Writes JSON + markdown report under reports/.

Usage:
  python tools/borderline_model_lab.py
  python tools/borderline_model_lab.py --models qwen3:14b,deepseek-r1:14b
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
API = "http://localhost:11434/api/generate"
PROMPT_SHORT = (
    "Per class CRYPTO/EQUITY: money-ready Y/N, ONE filter, wire_target path. "
    "11/11 daily-bar hypotheses killed. Paper-only."
)
PROMPT_MIN = "List 3 repo paths to wire emitter whitelist. One line each."

# Models that exceed comfortable 12GB VRAM full-GPU but may work with tuning
BORDERLINE_MODELS = [
    ("qwen3:14b", "14b", 9.3),
    ("deepseek-r1:14b", "14b-r1", 9.0),
    ("qwen3.5:9b", "9b", 6.6),
    ("mistral-nemo:latest", "12b-moe", 7.1),
    ("qwen2.5-coder:32b-instruct", "32b", 19.0),
    ("deepseek-r1:32b", "32b-r1", 19.0),
    ("qwen3:32b", "32b", 20.0),
    ("mixtral:8x7b-instruct-v0.1-q4_K_M", "moe-47b-q4", 28.0),
    ("llama3.3:70b-instruct-q3_K_M", "70b-q3", 34.0),
]

# (num_gpu, num_ctx, num_predict, label) — num_gpu=-1 lets Ollama decide
CONFIGS_14B = [
    (-1, 4096, 400, "auto-ctx4k-p400"),
    (-1, 2048, 800, "auto-ctx2k-p800"),
    (99, 4096, 800, "gpu99-ctx4k-p800"),
    (35, 4096, 800, "gpu35-ctx4k-p800"),
    (20, 2048, 600, "gpu20-ctx2k-p600"),
    (0, 2048, 400, "cpu-ctx2k-p400"),
]

CONFIGS_GIANT = [
    (-1, 2048, 500, "auto-ctx2k-p500"),
    (35, 2048, 600, "gpu35-ctx2k-p600"),
    (20, 2048, 500, "gpu20-ctx2k-p500"),
    (99, 2048, 400, "gpu99-ctx2k-p400"),
    (0, 2048, 400, "cpu-ctx2k-p400"),
]


@dataclass
class Trial:
    model: str
    tier: str
    disk_gb: float
    config: str
    num_gpu: int
    num_ctx: int
    num_predict: int
    ok: bool
    elapsed_s: float
    chars: int
    tok_per_s: float
    vram_used_mib: int
    vram_free_mib: int
    processor: str
    error: str = ""


def gpu_stats() -> tuple[int, int]:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free", "--format=csv,noheader,nounits"],
            text=True, encoding="utf-8", errors="replace", timeout=10,
        )
        parts = out.strip().split(",")
        return int(parts[0].strip()), int(parts[1].strip())
    except Exception:
        return -1, -1


def ollama_ps_processor(model: str) -> str:
    try:
        out = subprocess.check_output(["ollama", "ps"], text=True, encoding="utf-8", errors="replace")
        for line in out.splitlines()[1:]:
            if model.split(":")[0] in line:
                m = re.search(r"(\d+%/\d+%\s+CPU/GPU|\d+%\s+GPU|\d+%\s+CPU|100%\s+CPU)", line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return "unknown"


def unload_all() -> None:
    try:
        out = subprocess.check_output(["ollama", "ps"], text=True, encoding="utf-8", errors="replace")
        for line in out.splitlines()[1:]:
            parts = line.split()
            if parts:
                subprocess.run(["ollama", "stop", parts[0]], capture_output=True, timeout=30)
    except Exception:
        pass


def generate(model: str, prompt: str, num_gpu: int, num_ctx: int, num_predict: int, timeout: int) -> tuple[bool, str, float, float]:
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_gpu": num_gpu,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "temperature": 0.2,
        },
    }).encode("utf-8")
    req = urllib.request.Request(API, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elapsed = time.time() - t0
        text = (data.get("response") or "").strip()
        eval_count = data.get("eval_count") or 0
        eval_dur = (data.get("eval_duration") or 1) / 1e9
        tps = round(eval_count / eval_dur, 2) if eval_dur > 0 and eval_count else 0.0
        return True, text, elapsed, tps
    except Exception as e:
        return False, str(e)[:300], time.time() - t0, 0.0


def configs_for(tier: str) -> list:
    if tier in ("32b", "32b-r1", "moe-47b-q4", "70b-q3"):
        return CONFIGS_GIANT
    return CONFIGS_14B


def timeout_for(tier: str) -> int:
    if tier == "70b-q3":
        return 900
    if tier in ("32b", "32b-r1", "moe-47b-q4"):
        return 600
    return 300


def run_trial(model: str, tier: str, disk_gb: float, cfg: tuple, use_min_prompt: bool) -> Trial:
    num_gpu, num_ctx, num_predict, label = cfg
    unload_all()
    time.sleep(2)
    prompt = PROMPT_MIN if use_min_prompt else PROMPT_SHORT
    timeout = timeout_for(tier)
    ok, text, elapsed, tps = generate(model, prompt, num_gpu, num_ctx, num_predict, timeout)
    vram = gpu_stats()
    proc = ollama_ps_processor(model) if ok else ""
    clean = re.sub(r"(?s)``\s*", "", text).strip()
    content_ok = ok and len(clean) > 40
    return Trial(
        model=model, tier=tier, disk_gb=disk_gb, config=label,
        num_gpu=num_gpu, num_ctx=num_ctx, num_predict=num_predict,
        ok=content_ok, elapsed_s=round(elapsed, 2), chars=len(clean),
        tok_per_s=tps, processor=proc,
        vram_used_mib=vram[0], vram_free_mib=vram[1],
        error="" if ok else text[:200],
    )


def installed_models() -> set[str]:
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=10) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
        return {m["name"] for m in tags.get("models", [])}
    except Exception:
        return set()


def write_report(trials: list[Trial], out_md: Path, out_json: Path) -> None:
    merged = trials
    if out_json.is_file():
        try:
            prev = json.loads(out_json.read_text(encoding="utf-8"))
            if isinstance(prev, list):
                seen = {(t["model"], t["config"]) for t in prev}
                merged = prev + [asdict(t) for t in trials if (t.model, t.config) not in seen]
        except (OSError, json.JSONDecodeError):
            merged = trials
    out_json.write_text(
        json.dumps(merged if isinstance(merged[0], dict) else [asdict(t) for t in merged], indent=2),
        encoding="utf-8",
    )
    trials = [Trial(**x) if isinstance(x, dict) else x for x in (merged if isinstance(merged[0], dict) else trials)]
    lines = [
        "# Borderline local model research — RTX 5070 12GB / 32GB RAM",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Hardware ceiling",
        "",
        "| Resource | Limit | Implication |",
        "|----------|-------|-------------|",
        "| VRAM | ~12 GB | Full-GPU fits ≤14B Q4 or ≤9B dense; MoE loads 2 experts |",
        "| RAM | 32 GB | Hybrid offload: weights spill to DDR5 (~50–100 GB/s vs ~600 GB/s VRAM) |",
        "| Disk | F:\\\\Models\\\\Ollama_GGUFs | Prefer Q4_K_M / Q3_K_M for giants |",
        "",
        "## Technique matrix (what we tested)",
        "",
        "| Technique | When | Effect on this PC |",
        "|-----------|------|-------------------|",
        "| **Q4_K_M / Q3_K_M GGUF** | 32B–70B | Q3 70B *runs* (~0.9 tok/s); Q4 32B hybrid ~4–60 tok/s |",
        "| **num_gpu partial** (20/35/99) | VRAM overflow | 35–99 layers on GPU rest on CPU; trades speed for fit |",
        "| **num_ctx 2048** | KV cache pressure | Cuts VRAM ~30% vs 8192; enough for harvest bullets |",
        "| **num_predict 800+** | R1/Qwen3 reasoning | Short 400-cap caused **0-char false FAIL** on 14B |",
        "| **MoE (Mixtral)** | 47B nominal | Only 2×7B active → fits at 6.7 tok/s with Q4 |",
        "| **CPU-only fallback** | Last resort | 14B ~5 tok/s; usable overnight, not interactive |",
        "",
        "## Results by model",
        "",
    ]
    by_model: dict[str, list[Trial]] = {}
    for t in trials:
        by_model.setdefault(t.model, []).append(t)

    for model, runs in by_model.items():
        best = max(runs, key=lambda r: (r.ok, r.tok_per_s, r.chars))
        lines.append(f"### `{model}` ({runs[0].tier}, ~{runs[0].disk_gb}GB disk)")
        lines.append("")
        lines.append("| Config | OK | s | tok/s | chars | VRAM used | Processor |")
        lines.append("|--------|----|---|-------|-------|-----------|-----------|")
        for r in sorted(runs, key=lambda x: (-x.ok, -x.tok_per_s)):
            lines.append(
                f"| {r.config} | {'Y' if r.ok else 'N'} | {r.elapsed_s} | {r.tok_per_s} | {r.chars} | {r.vram_used_mib} | {r.processor} |"
            )
        verdict = "✅ **Usable**" if best.ok and best.tok_per_s >= 8 else (
            "⚠️ **Marginal**" if best.ok else "❌ **Not practical**"
        )
        lines.append("")
        lines.append(f"**Verdict:** {verdict} — best config `{best.config}` ({best.tok_per_s} tok/s, {best.elapsed_s}s).")
        lines.append("")

    lines.extend([
        "## Recommended pulls / quants to try next",
        "",
        "| Model | Ollama tag | Why |",
        "|-------|------------|-----|",
        "| Qwen3 14B | `qwen3:14b` (installed) | Use `gpu99-ctx4k-p800` or harvest via HTTP |",
        "| Qwen2.5 Coder 32B | `qwen2.5-coder:32b-instruct` | Try `qwen2.5-coder:32b-instruct-q4_K_M` if exists |",
        "| DeepSeek R1 14B | `deepseek-r1:14b` | Same as Qwen3 14B tuning |",
        "| Llama 3.3 70B | `llama3.3:70b-instruct-q3_K_M` | Already Q3; overnight batch only |",
        "| Mixtral 8x7B | `mixtral:8x7b-instruct-v0.1-q4_K_M` | Best giant for quality/speed balance |",
        "",
        "## Commands",
        "",
        "```powershell",
        "python tools/borderline_model_lab.py",
        "python tools/model_grill_sequential.py --job ollama:qwen3:14b --prompt harvest",
        "python tools/ollama_gpu_push_benchmark.py --phase offload",
        "```",
        "",
    ])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="", help="Comma-separated subset")
    ap.add_argument("--quick", action="store_true", help="14B models only, 3 configs each")
    args = ap.parse_args()

    want = {m.strip() for m in args.models.split(",") if m.strip()} if args.models else None
    inst = installed_models()
    trials: list[Trial] = []
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = REPO / "swarm_runs" / "borderline-lab" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    for model, tier, disk_gb in BORDERLINE_MODELS:
        if want and model not in want:
            continue
        if inst and model not in inst:
            print(f"SKIP {model} (not installed)", flush=True)
            continue
        cfgs = configs_for(tier)
        if args.quick and tier not in ("32b", "32b-r1", "moe-47b-q4", "70b-q3"):
            cfgs = [cfgs[1], cfgs[2], cfgs[4]]  # auto-2k, gpu99, gpu20
        elif args.quick:
            cfgs = cfgs[:3]

        print(f"\n=== {model} ({tier}) ===", flush=True)
        for cfg in cfgs:
            print(f"  {cfg[3]}...", flush=True)
            t = run_trial(model, tier, disk_gb, cfg, use_min_prompt=False)
            if not t.ok and "r1" in tier or "qwen3" in model:
                print("    retry min prompt + high predict...", flush=True)
                t2 = run_trial(model, tier, disk_gb, (cfg[0], cfg[1], max(cfg[2], 900), cfg[3] + "+retry"), True)
                if t2.ok:
                    t = t2
            trials.append(t)
            print(f"    -> {'OK' if t.ok else 'FAIL'} {t.elapsed_s}s {t.tok_per_s} tok/s {t.processor}", flush=True)
            (out_dir / f"{re.sub(r'[^a-z0-9]+', '-', model)}_{cfg[3]}.json").write_text(
                json.dumps(asdict(t), indent=2), encoding="utf-8",
            )

    report_md = REPO / "reports" / "BORDERLINE_MODEL_RESEARCH_2026-05-19.md"
    report_json = REPO / "reports" / "borderline_model_lab_latest.json"
    write_report(trials, report_md, report_json)
    print(f"\nWrote {report_md}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
