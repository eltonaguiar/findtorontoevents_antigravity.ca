#!/usr/bin/env python3
"""Push RTX 5070 12GB + i9-14900K: benchmark tiny→giant Ollama models with GPU/CPU offload.

Uses Ollama HTTP API (localhost:11434) so we can set per-run:
  num_gpu, num_ctx, num_predict

Writes:
  swarm_runs/gpu-push-benchmark/<ts>/results.json
  swarm_runs/gpu-push-benchmark/<ts>/REPORT.md
  Appends rows to BENCHMARK_LOCALAI_DESKTOP.md

Usage:
  python tools/ollama_gpu_push_benchmark.py --phase known
  python tools/ollama_gpu_push_benchmark.py --phase push --pull-giants
  python tools/ollama_gpu_push_benchmark.py --phase all
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BENCHMARK = REPO / "BENCHMARK_LOCALAI_DESKTOP.md"
PROMPT_SHORT = (
    "Per class CRYPTO/EQUITY/COMMODITY/FOREX: money-ready Y/N, ONE change, "
    "P(Tier-2 12mo)%. List 2 harvest ideas with wire_target repo path."
)
API = "http://localhost:11434/api/generate"
PULL = "http://localhost:11434/api/pull"

# (model, tier, approx_gb, notes)
KNOWN_MODELS: list[tuple[str, str, float, str]] = [
    ("llama3.2:1b", "tiny", 1.3, "Q8"),
    ("smollm2:1.7b", "tiny", 1.8, "Q8"),
    ("qwen2.5:3b", "tiny", 1.9, "Q4"),
    ("phi4-mini:latest", "small", 2.5, "Q4"),
    ("gemma3:4b", "small", 3.3, "Q4"),
    ("qwen3:4b", "small", 2.5, "Q4"),
    ("llama3.2:3b", "small", 2.0, "Q4"),
    ("phi3.5:latest", "small", 2.2, "Q4"),
    ("qwen2.5-coder:7b", "medium", 4.7, "Q4"),
    ("llama3.1:latest", "medium", 4.9, "Q4"),
    ("mistral-nemo:latest", "medium", 7.1, "Q4"),
    ("qwen3.5:9b", "medium", 6.6, "Q4"),
    ("qwen2.5-coder:14b-instruct-q4_K_M", "large", 9.0, "Q4_K_M"),
    ("deepseek-r1:14b", "large", 9.0, "Q4"),
    ("qwen3:14b", "large", 9.3, "Q4"),
]

# Giants to try pull (name, approx_gb) — skip if C: free < gb+8
GIANT_PULLS: list[tuple[str, float]] = [
    ("deepseek-r1:32b", 20.0),
    ("qwen2.5-coder:32b-instruct", 20.0),
    ("mixtral:8x7b-instruct-v0.1-q4_K_M", 26.0),
    ("llama3.3:70b-instruct-q3_K_M", 35.0),
    ("qwen3:32b", 20.0),
]

# Offload experiments on large models: (num_gpu, num_ctx, label)
OFFLOAD_MATRIX: list[tuple[int, int, str]] = [
    (-1, 8192, "auto-gpu"),
    (99, 4096, "max-gpu-99"),
    (35, 4096, "gpu-35"),
    (20, 4096, "gpu-20"),
    (0, 4096, "cpu-only"),
]


@dataclass
class RunResult:
    model: str
    tier: str
    config: str
    ok: bool
    elapsed_s: float
    chars: int
    tok_per_s: float
    processor: str
    vram_used_mib: int
    vram_free_mib: int
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "model": self.model, "tier": self.tier, "config": self.config,
            "ok": self.ok, "elapsed_s": self.elapsed_s, "chars": self.chars,
            "tok_per_s": self.tok_per_s, "processor": self.processor,
            "vram_used_mib": self.vram_used_mib, "vram_free_mib": self.vram_free_mib,
            "error": self.error,
        }


def free_gb(drive: str = "C:") -> float:
    try:
        return shutil.disk_usage(drive).free / (1024**3)
    except OSError:
        return 0.0


def gpu_stats() -> tuple[int, int]:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free", "--format=csv,noheader,nounits"],
            text=True, encoding="utf-8", errors="replace", timeout=10,
        )
        parts = out.strip().split(",")
        return int(parts[0].strip()), int(parts[1].strip())
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError):
        return -1, -1


def ollama_ps_processor(model: str) -> str:
    try:
        out = subprocess.check_output(["ollama", "ps"], text=True, encoding="utf-8", errors="replace")
        for line in out.splitlines()[1:]:
            if model.split(":")[0] in line:
                m = re.search(r"(\d+%/\d+%\s+CPU/GPU|100%\s+GPU|100%\s+CPU)", line)
                if m:
                    return m.group(1)
                if "GPU" in line:
                    return "GPU"
                if "CPU" in line:
                    return "CPU"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return "unknown"


def unload_all() -> None:
    try:
        out = subprocess.check_output(["ollama", "ps"], text=True, encoding="utf-8", errors="replace")
        for line in out.splitlines()[1:]:
            parts = line.split()
            if parts:
                subprocess.run(["ollama", "stop", parts[0]], capture_output=True, timeout=30)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass


def api_generate(model: str, prompt: str, num_gpu: int, num_ctx: int, num_predict: int | None = None) -> tuple[bool, str, float, float]:
    if num_predict is None:
        low = model.lower()
        num_predict = 1200 if any(x in low for x in ("deepseek-r1", "qwen3", "r1")) else 400
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
        with urllib.request.urlopen(req, timeout=900) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        elapsed = time.time() - t0
        text = data.get("response", "")
        eval_count = data.get("eval_count") or 0
        eval_dur = (data.get("eval_duration") or 1) / 1e9
        tps = round(eval_count / eval_dur, 2) if eval_dur > 0 and eval_count else 0.0
        return True, text, elapsed, tps
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:500]
        return False, err, time.time() - t0, 0.0
    except Exception as e:
        return False, str(e)[:500], time.time() - t0, 0.0


def pull_model(name: str, timeout: int = 3600) -> tuple[bool, str]:
    body = json.dumps({"name": name, "stream": False}).encode("utf-8")
    req = urllib.request.Request(PULL, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return True, str(data)[:200]
    except Exception as e:
        return False, str(e)[:300]


def run_one(model: str, tier: str, config: str, num_gpu: int, num_ctx: int) -> RunResult:
    unload_all()
    time.sleep(1)
    vram_before = gpu_stats()
    ok, text, elapsed, tps = api_generate(model, PROMPT_SHORT, num_gpu, num_ctx)
    time.sleep(0.5)
    vram_after = gpu_stats()
    proc = ollama_ps_processor(model) if ok else ""
    clean = re.sub(r"(?s).*?(?:|)\s*", "", text).strip()
    content_ok = ok and len(clean) > 60
    return RunResult(
        model=model, tier=tier, config=config, ok=content_ok,
        elapsed_s=round(elapsed, 2), chars=len(clean or text), tok_per_s=tps,
        processor=proc,
        vram_used_mib=vram_after[0] if vram_after[0] >= 0 else vram_before[0],
        vram_free_mib=vram_after[1] if vram_after[1] >= 0 else vram_before[1],
        error="" if ok else text[:300],
    )


def append_benchmark(r: RunResult) -> None:
    if not BENCHMARK.exists():
        return
    mode = r.processor.replace("|", "/")
    line = (
        f"| {datetime.now(timezone.utc).strftime('%Y-%m-%d')} "
        f"| {r.model} | ollama | {mode} | {r.config} | {r.elapsed_s} "
        f"| {'Y' if r.ok else 'N'} | {r.chars} | {r.tier} {r.tok_per_s} tok/s |"
    )
    text = BENCHMARK.read_text(encoding="utf-8")
    if line not in text:
        text = text.replace("\n*Add rows after each", f"\n{line}\n\n*Add rows after each", 1)
        BENCHMARK.write_text(text, encoding="utf-8")


def phase_known(out_dir: Path) -> list[RunResult]:
    results: list[RunResult] = []
    installed = set()
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=10) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
        installed = {m["name"] for m in tags.get("models", [])}
    except Exception:
        pass

    for model, tier, _gb, _q in KNOWN_MODELS:
        if installed and model not in installed:
            print(f"  skip {model} (not installed)", flush=True)
            continue
        print(f"  [{tier}] {model} auto-gpu...", flush=True)
        r = run_one(model, tier, "auto-gpu", -1, 4096)
        results.append(r)
        print(f"    -> {'OK' if r.ok else 'FAIL'} {r.elapsed_s}s {r.tok_per_s} tok/s {r.processor}", flush=True)
        append_benchmark(r)
        (out_dir / "runs").mkdir(parents=True, exist_ok=True)
        (out_dir / "runs" / f"{re.sub(r'[^a-z0-9]+', '-', model)}.json").write_text(
            json.dumps(r.to_dict(), indent=2), encoding="utf-8",
        )
    return results


def phase_offload(out_dir: Path) -> list[RunResult]:
    """Try num_gpu variants on the largest installed 14b model."""
    results: list[RunResult] = []
    target = "qwen3:14b"
    for num_gpu, num_ctx, label in OFFLOAD_MATRIX:
        print(f"  offload {target} {label} (num_gpu={num_gpu}, ctx={num_ctx})...", flush=True)
        r = run_one(target, "large", label, num_gpu, num_ctx)
        results.append(r)
        print(f"    -> {'OK' if r.ok else 'FAIL'} {r.elapsed_s}s {r.processor} VRAM {r.vram_used_mib}MiB", flush=True)
        append_benchmark(r)
    return results


def phase_giants(out_dir: Path, do_pull: bool) -> list[RunResult]:
    results: list[RunResult] = []
    for name, need_gb in GIANT_PULLS:
        if free_gb() < need_gb + 10:
            print(f"  skip pull {name} (need ~{need_gb}GB, C: free {free_gb():.0f}GB)", flush=True)
            continue
        if do_pull:
            print(f"  pulling {name} (~{need_gb} GB)...", flush=True)
            ok_pull, msg = pull_model(name)
            if not ok_pull:
                print(f"    pull FAIL: {msg[:120]}", flush=True)
                results.append(RunResult(name, "giant", "pull-fail", False, 0, 0, 0, "", -1, -1, msg))
                continue
            print(f"    pull OK", flush=True)
        for num_gpu, num_ctx, label in [(-1, 4096, "auto"), (99, 2048, "gpu99-ctx2k"), (0, 2048, "cpu")]:
            print(f"  giant run {name} {label}...", flush=True)
            r = run_one(name, "giant", label, num_gpu, num_ctx)
            results.append(r)
            print(f"    -> {'OK' if r.ok else 'FAIL'} {r.elapsed_s}s {r.processor}", flush=True)
            append_benchmark(r)
            if r.ok:
                break  # one successful config enough
    return results


def write_report(out_dir: Path, all_results: list[RunResult]) -> None:
    ok = [r for r in all_results if r.ok]
    lines = [
        "# GPU push benchmark report",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Hardware: RTX 5070 12GB · i9-14900K · 32GB RAM",
        f"C: free {free_gb():.1f} GB",
        "",
        f"**Summary:** {len(ok)}/{len(all_results)} runs OK",
        "",
        "## Best tok/s (local harvest quality proxy)",
        "",
        "| Model | Tier | Config | tok/s | elapsed_s | processor |",
        "|-------|------|--------|-------|-----------|-----------|",
    ]
    for r in sorted(ok, key=lambda x: -x.tok_per_s)[:15]:
        lines.append(
            f"| {r.model} | {r.tier} | {r.config} | {r.tok_per_s} | {r.elapsed_s} | {r.processor} |"
        )
    lines.extend([
        "",
        "## Techniques for 12GB VRAM",
        "",
        "1. **Q4_K_M 7B–14B** — full GPU, best speed (20–80 tok/s typical).",
        "2. **num_gpu=-1** — Ollama auto-fits layers to VRAM; use for 14B+.",
        "3. **num_ctx=2048–4096** — lowering context frees VRAM for more layers.",
        "4. **32B Q4** — hybrid 10–90% CPU/GPU expected; viable on 32GB RAM but slow.",
        "5. **70B+** — use `ollama` **cloud** tags (`gpt-oss:120b-cloud`) or API; not local VRAM.",
        "6. **Broken F: symlinks** — import via `tools/ollama_import_gguf.py` blob path only.",
        "",
        "## Failed / OOM",
        "",
    ])
    for r in all_results:
        if not r.ok:
            lines.append(f"- `{r.model}` [{r.config}]: {r.error[:120]}")
    (out_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    (out_dir / "results.json").write_text(
        json.dumps([r.to_dict() for r in all_results], indent=2), encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["known", "offload", "giants", "all"], default="known")
    ap.add_argument("--pull-giants", action="store_true")
    args = ap.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = REPO / "swarm_runs/gpu-push-benchmark" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    all_results: list[RunResult] = []
    if args.phase in ("known", "all"):
        print("=== Phase: known models ===", flush=True)
        all_results.extend(phase_known(out_dir))
    if args.phase in ("offload", "all"):
        print("=== Phase: offload matrix (qwen3:14b) ===", flush=True)
        all_results.extend(phase_offload(out_dir))
    if args.phase in ("giants", "all"):
        print("=== Phase: giant models ===", flush=True)
        all_results.extend(phase_giants(out_dir, args.pull_giants))

    write_report(out_dir, all_results)
    ok_n = sum(1 for r in all_results if r.ok)
    print(f"\nDone {ok_n}/{len(all_results)} -> {out_dir / 'REPORT.md'}", flush=True)
    return 0 if ok_n else 1


if __name__ == "__main__":
    sys.exit(main())
