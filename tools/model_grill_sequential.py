#!/usr/bin/env python3
"""Run money-ready prompts — cloud vs local scheduling.

**Cloud:** parallel across *different* API providers (one key each); sequential
within the same provider (avoids rate-limit / key contention).
**Local Ollama:** strictly one model at a time; hard per-size timeouts; unload between runs.

Usage:
  python tools/model_grill_sequential.py --wave paid --prompt harvest
  python tools/model_grill_sequential.py --wave ring --cloud-parallel
  python tools/model_grill_sequential.py --wave local_smoke --no-cloud-parallel
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCK = REPO / "swarm_runs" / ".model_grill.lock"
def _prompt_path(name: str) -> Path:
    staged = REPO / "swarm_runs" / "_prompts" / name
    if staged.is_file():
        return staged
    tracked = REPO / "docs" / "swarm_prompts" / name
    return tracked if tracked.is_file() else staged


PROMPTS = {
    "harvest": _prompt_path("MONEY_READY_HARVEST_v1.md"),
    "master": _prompt_path("MONEY_READY_MASTER_v1.md"),
    "narrow": _prompt_path("CODEBASE_NARROW_v1.md"),
    "r1": _prompt_path("DOUBLE_CHECK_R1.md"),
    "r2": _prompt_path("METHODOLOGY_R2.md"),
    "r3": _prompt_path("WORST_STRATEGY_R3.md"),
    "rescue_factory": _prompt_path("RESCUE_QUESTION_FACTORY_v1.md"),
    "rescue_execute": _prompt_path("RESCUE_EDGE_EXECUTE_v1.md"),
}
API = REPO / "tools/swarm/api_consult.py"
OLLAMA_GENERATE = "http://localhost:11434/api/generate"
BENCHMARK = REPO / "BENCHMARK_LOCALAI_DESKTOP.md"
_BENCH_LOCK = threading.Lock()
SYSTEM = (
    "Senior quant. 11/11 causal hypotheses killed. pf_registry canonical. "
    "Answer in markdown with per-class table + wire_targets + acceptance tests.\n\n"
)

# wave -> list of "provider:model" or "ollama:tag"
WAVES: dict[str, list[str]] = {
    "paid": [
        "xai:grok-3-latest",
        "inception:mercury-2",
        "deepseek:deepseek-chat",
    ],
    "ring": [
        "openrouter:openrouter/free",
        "openrouter:inclusionai/ring-2.6-1t",
        "openrouter:inclusionai/ling-2.6-1t",
        "openrouter:inclusionai/ling-2.6-flash",
    ],
    "free": [
        "groq:llama-3.3-70b-versatile",
        "cerebras:llama-3.3-70b",
        "openrouter:meta-llama/llama-3.3-70b-instruct:free",
        "ofox:z-ai/glm-4.7-flash:free",
        "pollinations:openai",
    ],
    "cloud_deep": [
        "xai:grok-3-latest",
        "deepseek:deepseek-chat",
        "openrouter:inclusionai/ring-2.6-1t",
        "openrouter:deepseek/deepseek-v4-flash",
        "openrouter:qwen/qwen3.6-max-preview",
    ],
    "local_smoke": [
        "ollama:gemma3:4b",
        "ollama:qwen2.5-coder:14b-instruct-q4_K_M",
        "ollama:qwen3:14b",
    ],
    "local_variety": [
        "ollama:mistral-nemo:latest",
        "ollama:qwen3:14b",
        "ollama:deepseek-r1:14b",
        "ollama:qwen2.5-coder:14b-instruct-q4_K_M",
        "ollama:mixtral:8x7b-instruct-v0.1-q4_K_M",
    ],
    "local_giants": [
        "ollama:qwen2.5-coder:32b-instruct",
        "ollama:deepseek-r1:32b",
        "ollama:qwen3:32b",
    ],
    "rescue_cloud": [
        "xai:grok-3-latest",
        "deepseek:deepseek-chat",
        "openrouter:inclusionai/ring-2.6-1t",
        "openrouter:qwen/qwen3.6-max-preview",
        "inception:mercury-2",
    ],
    "rescue_local": [
        "ollama:qwen3:14b",
        "ollama:qwen2.5-coder:14b-instruct-q4_K_M",
        "ollama:mistral-nemo:latest",
        "ollama:deepseek-r1:14b",
    ],
}


def ts_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = REPO / "swarm_runs" / "model-grill" / stamp
    d.mkdir(parents=True, exist_ok=True)
    return d


def acquire_lock() -> bool:
    if LOCK.exists():
        try:
            age = time.time() - LOCK.stat().st_mtime
            if age < 7200:
                print(f"LOCKED: another grill running ({LOCK}, age {age:.0f}s)", file=sys.stderr)
                return False
        except OSError:
            pass
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8")
    return True


def release_lock() -> None:
    try:
        LOCK.unlink(missing_ok=True)
    except OSError:
        pass


def ollama_stop_all() -> None:
    try:
        subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=15)
        out = subprocess.check_output(["ollama", "ps"], text=True, encoding="utf-8", errors="replace")
        for line in out.splitlines()[1:]:
            name = line.split()[0] if line.strip() else ""
            if name and name != "NAME":
                subprocess.run(["ollama", "stop", name], capture_output=True, timeout=60)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass


def ollama_timeout(tag: str) -> int:
    """Per-run ceiling for local models (seconds). No indefinite waits."""
    low = tag.lower()
    # Largest-first — avoid matching '4b' inside '14b-instruct-q4_K_M'
    if re.search(r"(70b|32b)", low):
        return 420
    if re.search(r"(14b|13b|12b)", low):
        return 240
    if re.search(r"(7b|8b|9b)", low):
        return 150
    if re.search(r"(1b|1\.7b|1\.8b|2b|3b|4b|smollm)", low):
        return 75
    return 180


def job_provider(job: str) -> str:
    if job.startswith("ollama:"):
        return "ollama"
    return job.split(":", 1)[0]


def split_cloud_local(jobs: list[str]) -> tuple[list[str], list[str]]:
    cloud, local = [], []
    for j in jobs:
        (local if j.startswith("ollama:") else cloud).append(j)
    return cloud, local


def group_by_provider(jobs: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for j in jobs:
        groups.setdefault(job_provider(j), []).append(j)
    return groups


def score_response(text: str) -> dict:
    """Heuristic intelligence rubric 1-5."""
    low = text.lower()
    score = 1
    if len(text) > 800:
        score += 1
    if "11/11" in text or "killed" in low:
        score += 1
    if re.search(r"`(?:alpha_engine|ml_consensus|audit_|tools)/[^`]+`", text):
        score += 1
    if "paper-only" in low or "paper only" in low or "not money-ready" in low:
        score += 1
    if re.search(r"money[- ]ready.*\by\b", low) and "equity" in low:
        score = max(1, score - 2)
    return {"intelligence_1_5": min(5, score), "chars": len(text)}


def append_benchmark(row: dict) -> None:
    if not BENCHMARK.exists():
        return
    line = (
        f"| {row.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))} "
        f"| {row.get('model', '?')} "
        f"| {row.get('backend', 'api')} "
        f"| {row.get('tier', 'cloud')} "
        f"| {row.get('prompt', 'harvest')} "
        f"| {row.get('elapsed_s', '-')} "
        f"| {'Y' if row.get('ok') else 'N'} "
        f"| {row.get('chars', 0)} "
        f"| intel={row.get('intelligence', '-')} | {row.get('notes', '')} |"
    )
    text = BENCHMARK.read_text(encoding="utf-8")
    marker = "## Cloud + local intelligence log"
    if marker not in text:
        text += (
            "\n\n## Cloud + local intelligence log\n\n"
            "| Date | Model | Backend | Tier | Prompt | Elapsed | OK | Chars | Notes |\n"
            "|------|-------|---------|------|--------|---------|----|-------|-------|\n"
        )
    if line not in text:
        if marker in text:
            idx = text.index(marker)
            nl = text.index("\n", idx)
            text = text[: nl + 1] + line + "\n" + text[nl + 1 :]
        else:
            text += line + "\n"
        with _BENCH_LOCK:
            BENCHMARK.write_text(text, encoding="utf-8")


def run_api(provider: str, model: str, prompt: str, out_path: Path, timeout: int) -> dict:
    tmp = out_path.parent / f"_prompt_{re.sub(r'[^a-z0-9]+', '_', out_path.stem)}.txt"
    tmp.write_text(SYSTEM + prompt, encoding="utf-8")
    t0 = time.time()
    cmd = [
        sys.executable, str(API),
        "--provider", provider,
        "--model", model,
        "--max-tokens", "2200",
        "--prompt-file", str(tmp),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace", cwd=str(REPO))
        elapsed = round(time.time() - t0, 2)
        text = proc.stdout if proc.returncode == 0 else (proc.stderr or proc.stdout or "")
        ok = proc.returncode == 0 and len(text.strip()) > 200
        out_path.write_text(
            f"# {provider}:{model}\n\nelapsed={elapsed}s ok={ok}\n\n{text}\n",
            encoding="utf-8",
        )
        sc = score_response(text) if ok else {"intelligence_1_5": 0, "chars": len(text)}
        return {"ok": ok, "elapsed_s": elapsed, "provider": provider, "model": model,
                "backend": "api", **sc}
    except subprocess.TimeoutExpired:
        out_path.write_text(f"# {provider}:{model}\n\nTIMEOUT {timeout}s\n", encoding="utf-8")
        return {"ok": False, "elapsed_s": timeout, "error": "TIMEOUT", "provider": provider, "model": model}


def ollama_http_generate(tag: str, prompt: str, timeout: int) -> tuple[bool, str, str]:
    """HTTP /api/generate — avoids CLI hang on long harvest prompts."""
    low = tag.lower()
    num_predict = 900 if any(x in low for x in ("14b", "32b", "70b", "r1")) else 500
    if re.search(r"(70b|32b|8x7b|mixtral)", low):
        num_ctx = 2048
    elif re.search(r"(14b|12b|13b|nemo)", low):
        num_ctx = 4096
    else:
        num_ctx = 8192
    body = json.dumps({
        "model": tag,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict, "temperature": 0.2, "num_ctx": num_ctx},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA_GENERATE, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        text = (data.get("response") or "").strip()
        return True, text, ""
    except urllib.error.HTTPError as e:
        return False, "", f"HTTP {e.code}"
    except Exception as e:
        return False, "", str(e)[:200]


def run_ollama(tag: str, prompt: str, out_path: Path) -> dict:
    ollama_stop_all()
    time.sleep(2)
    timeout = ollama_timeout(tag)
    full = SYSTEM + prompt
    t0 = time.time()
    ok, text, err = ollama_http_generate(tag, full, timeout)
    elapsed = round(time.time() - t0, 2)
    if not ok:
        out_path.write_text(
            f"# ollama:{tag}\n\nelapsed={elapsed}s ok=False err={err}\n",
            encoding="utf-8",
        )
        ollama_stop_all()
        return {"ok": False, "elapsed_s": elapsed, "error": err or "http_fail", "model": tag, "backend": "ollama"}
    ok = len(text) > 150
    out_path.write_text(f"# ollama:{tag}\n\nelapsed={elapsed}s ok={ok}\n\n{text}\n", encoding="utf-8")
    sc = score_response(text) if ok else {"intelligence_1_5": 0, "chars": len(text)}
    ollama_stop_all()
    return {"ok": ok, "elapsed_s": elapsed, "model": tag, "backend": "ollama", **sc}


def run_job(job: str, prompt_name: str, out_dir: Path, api_timeout: int, row_notes: str = "grill") -> dict:
    prompt_path = PROMPTS.get(prompt_name, PROMPTS["harvest"])
    prompt = prompt_path.read_text(encoding="utf-8")
    slug = re.sub(r"[^a-z0-9]+", "-", job.lower())[:80]
    out_path = out_dir / f"{slug}__{prompt_name}.md"

    if job.startswith("ollama:"):
        tag = job.split(":", 1)[1]
        r = run_ollama(tag, prompt, out_path)
    else:
        prov, model = job.split(":", 1)
        r = run_api(prov, model, prompt, out_path, api_timeout)

    r["prompt"] = prompt_name
    r["path"] = str(out_path)
    r["job"] = job
    append_benchmark({
        "model": r.get("model", job),
        "backend": r.get("backend", "api"),
        "tier": "local" if r.get("backend") == "ollama" else "cloud",
        "prompt": prompt_name,
        "elapsed_s": r.get("elapsed_s"),
        "ok": r.get("ok"),
        "chars": r.get("chars", 0),
        "intelligence": r.get("intelligence_1_5", "-"),
        "notes": row_notes,
    })
    return r


def run_provider_group(
    provider: str,
    prov_jobs: list[str],
    prompts: list[str],
    out_dir: Path,
    api_timeout: int,
) -> list[dict]:
    """Sequential calls for one API key / provider bucket."""
    results: list[dict] = []
    for job in prov_jobs:
        for pname in prompts:
            print(f"  [{provider}] {job} prompt={pname}...", flush=True)
            r = run_job(job, pname, out_dir, api_timeout, row_notes=f"cloud/{provider}")
            results.append(r)
            print(
                f"    -> {'OK' if r.get('ok') else 'FAIL'} {r.get('elapsed_s')}s "
                f"intel={r.get('intelligence_1_5', '-')}",
                flush=True,
            )
    return results


def run_cloud_parallel(
    cloud_jobs: list[str],
    prompts: list[str],
    out_dir: Path,
    api_timeout: int,
    max_workers: int,
) -> list[dict]:
    groups = group_by_provider(cloud_jobs)
    workers = min(max_workers, max(1, len(groups)))
    print(
        f"Cloud: {len(cloud_jobs)} jobs across {len(groups)} provider keys "
        f"(parallel={workers}, sequential within each key)",
        flush=True,
    )
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {
            ex.submit(run_provider_group, prov, jobs, prompts, out_dir, api_timeout): prov
            for prov, jobs in groups.items()
        }
        for fut in as_completed(futs):
            prov = futs[fut]
            try:
                results.extend(fut.result())
            except Exception as e:
                print(f"  [{prov}] group FAIL: {e}", flush=True)
    return results


def run_local_sequential(
    local_jobs: list[str],
    prompts: list[str],
    out_dir: Path,
    api_timeout: int,
) -> list[dict]:
    results: list[dict] = []
    total = len(local_jobs) * len(prompts)
    n = 0
    print(f"Local: {len(local_jobs)} models — one at a time, hard timeouts", flush=True)
    for job in local_jobs:
        tag = job.split(":", 1)[1]
        cap = ollama_timeout(tag)
        for pname in prompts:
            n += 1
            print(f"[{n}/{total}] {job} prompt={pname} (timeout={cap}s)...", flush=True)
            r = run_job(job, pname, out_dir, api_timeout, row_notes=f"local seq cap={cap}s")
            results.append(r)
            print(
                f"  -> {'OK' if r.get('ok') else 'FAIL'} {r.get('elapsed_s')}s "
                f"intel={r.get('intelligence_1_5', '-')}",
                flush=True,
            )
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wave", choices=list(WAVES.keys()) + ["roster"], help="preset job list")
    ap.add_argument("--job", help="single job provider:model or ollama:tag")
    ap.add_argument("--prompt", default="harvest", choices=list(PROMPTS.keys()))
    ap.add_argument("--prompt-all", action="store_true", help="run harvest+r1+r2+r3 per job")
    ap.add_argument("--api-timeout", type=int, default=150, help="seconds per cloud API call")
    ap.add_argument(
        "--cloud-parallel",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="parallelize cloud jobs across different providers (default on)",
    )
    ap.add_argument(
        "--max-cloud-workers",
        type=int,
        default=8,
        help="max parallel provider buckets for cloud",
    )
    ap.add_argument("--probe-roster", action="store_true", help="run api_model_roster --probe all first")
    args = ap.parse_args()

    if not acquire_lock():
        return 2

    out_dir = ts_dir()
    manifest: dict = {"out_dir": str(out_dir), "runs": [], "started": datetime.now(timezone.utc).isoformat()}

    try:
        if args.probe_roster or args.wave == "roster":
            subprocess.run([sys.executable, str(REPO / "tools/api_model_roster.py"), "--probe", "all"],
                           cwd=str(REPO), timeout=3600)

        jobs: list[str] = []
        if args.job:
            jobs = [args.job]
        elif args.wave and args.wave != "roster":
            jobs = WAVES[args.wave]

        prompts = list(PROMPTS.keys()) if args.prompt_all else [args.prompt]
        cloud_jobs, local_jobs = split_cloud_local(jobs)
        all_runs: list[dict] = []

        if cloud_jobs:
            if args.cloud_parallel:
                all_runs.extend(
                    run_cloud_parallel(
                        cloud_jobs, prompts, out_dir, args.api_timeout, args.max_cloud_workers
                    )
                )
            else:
                for job in cloud_jobs:
                    prov = job_provider(job)
                    all_runs.extend(
                        run_provider_group(prov, [job], prompts, out_dir, args.api_timeout)
                    )

        if local_jobs:
            all_runs.extend(run_local_sequential(local_jobs, prompts, out_dir, args.api_timeout))

        manifest["runs"] = all_runs

        manifest["finished"] = datetime.now(timezone.utc).isoformat()
        manifest["ok"] = sum(1 for x in manifest["runs"] if x.get("ok"))
        manifest["total"] = len(manifest["runs"])
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nDone {manifest['ok']}/{manifest['total']} -> {out_dir}")
        return 0 if manifest["ok"] else 1
    finally:
        release_lock()
        ollama_stop_all()


if __name__ == "__main__":
    sys.exit(main())
