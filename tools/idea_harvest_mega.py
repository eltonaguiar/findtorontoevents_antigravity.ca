#!/usr/bin/env python3
"""Mega idea harvest: run MONEY_READY_HARVEST across many API + local Ollama models.

Writes per-model outputs + aggregated harvest ideas under:
  swarm_runs/idea-harvest/<timestamp>/

Usage:
  python tools/idea_harvest_mega.py --tier all
  python tools/idea_harvest_mega.py --tier api --max-parallel 4
  python tools/idea_harvest_mega.py --tier local
  python tools/idea_harvest_mega.py --pull-small   # ollama pull while disk > min_gb
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROMPT = REPO / "swarm_runs/_prompts/MONEY_READY_HARVEST_v1.md"
API = REPO / "tools/swarm/api_consult.py"
IMPORT = REPO / "tools/ollama_import_gguf.py"
BENCHMARK = REPO / "BENCHMARK_LOCALAI_DESKTOP.md"

SYSTEM_PREFIX = (
    "Senior quant. 11/11 causal hypotheses killed. pf_registry canonical. "
    "Answer in markdown with per-class table + 3 harvest ideas (id, wire_target, acceptance_test).\n\n"
)


@dataclass(frozen=True)
class ModelJob:
    tier: str  # paid | free | local | hf
    provider: str
    model: str
    slug: str

    @property
    def key(self) -> str:
        return f"{self.provider}::{self.model}"


# --- API model matrix (extend freely) ---
PAID_API: list[ModelJob] = [
    ModelJob("paid", "xai", "grok-3-latest", "xai-grok3"),
    ModelJob("paid", "inception", "mercury-2", "inception-mercury2"),
    ModelJob("paid", "deepseek", "deepseek-chat", "deepseek-chat"),
]

FREE_OPENROUTER: list[ModelJob] = [
    ModelJob("free", "openrouter", "openrouter/free", "or-free-router"),
    ModelJob("free", "openrouter", "inclusionai/ring-2.6-1t:free", "or-ring-2.6"),
    ModelJob("free", "openrouter", "meta-llama/llama-3.3-70b-instruct:free", "or-llama33-70b-free"),
    ModelJob("free", "openrouter", "qwen/qwen-2.5-72b-instruct:free", "or-qwen25-72b-free"),
    ModelJob("free", "openrouter", "google/gemma-2-9b-it:free", "or-gemma2-9b-free"),
    ModelJob("free", "openrouter", "mistralai/mistral-small-3.1-24b-instruct:free", "or-mistral-small-free"),
    ModelJob("free", "openrouter", "nvidia/nemotron-3-nano-30b-a3b:free", "or-nemotron-nano-free"),
    ModelJob("free", "openrouter", "deepseek/deepseek-r1:free", "or-deepseek-r1-free"),
]

FREE_OTHER: list[ModelJob] = [
    ModelJob("free", "groq", "llama-3.3-70b-versatile", "groq-llama33-70b"),
    ModelJob("free", "groq", "mixtral-8x7b-32768", "groq-mixtral"),
    ModelJob("free", "groq", "gemma2-9b-it", "groq-gemma2-9b"),
    # HF router: skip if account returns HTTP 402 (credits depleted)
    ModelJob("free", "pollinations", "openai", "pollinations-default"),
]

# Small models to pull if disk allows (name, approx GB)
OLLAMA_PULL_CANDIDATES: list[tuple[str, float]] = [
    ("gemma3:4b", 3.5),
    ("llama3.2:1b", 1.5),
    ("qwen2.5:3b", 2.5),
    ("smollm2:1.7b", 1.2),
    ("phi4-mini", 2.5),
]


def ts_dir() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = REPO / "swarm_runs/idea-harvest" / stamp
    d.mkdir(parents=True, exist_ok=True)
    return d


def free_gb(drive: str) -> float:
    try:
        total, used, free = shutil.disk_usage(drive)
        return free / (1024**3)
    except OSError:
        return 0.0


def list_ollama_local() -> list[str]:
    try:
        out = subprocess.check_output(["ollama", "list"], text=True, encoding="utf-8", errors="replace")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    tags: list[str] = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if not parts:
            continue
        tag = parts[0]
        if "embed" in tag.lower():
            continue
        if tag.endswith(":cloud") or "-cloud" in tag:
            continue
        tags.append(tag)
    return tags


def run_swarm_models_endpoint(label: str, model: str, prompt: str, out_dir: Path) -> dict:
    """Call extra endpoints from tools/swarm_models.py (llm7, mistral, etc.)."""
    slug_path = out_dir / "api" / f"sm-{label}-{re.sub(r'[^a-z0-9]+', '-', model.lower())[:40]}.md"
    slug_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        sys.path.insert(0, str(REPO))
        from tools import swarm_models as sm  # noqa: WPS433
        ep = next((e for e in sm.ENDPOINTS if e.label == label), None)
        if not ep:
            return {"slug": f"sm-{label}", "ok": False, "error": "unknown endpoint"}
        key = sm.resolve_key(ep.env_vars)
        if not key:
            return {"slug": f"sm-{label}", "ok": False, "error": "no key"}
        import urllib.request
        body = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PREFIX.strip()},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 2500,
            "temperature": 0.2,
        }).encode("utf-8")
        url = ep.base_url.rstrip("/") + "/chat/completions"
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {key}")
        for hk, hv in ep.extra_headers:
            req.add_header(hk, hv)
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
        elapsed = round(time.time() - t0, 2)
        slug_path.write_text(
            f"# sm-{label}\n\n- **model:** `{model}`\n- **elapsed_s:** {elapsed}\n- **ok:** true\n\n{text}\n",
            encoding="utf-8",
        )
        return {"slug": f"sm-{label}", "provider": label, "model": model, "tier": "free",
                "backend": "swarm_models", "ok": True, "elapsed_s": elapsed,
                "chars": len(text), "path": str(slug_path)}
    except Exception as e:
        slug_path.write_text(f"# sm-{label}\n\nFAIL: {e}\n", encoding="utf-8")
        return {"slug": f"sm-{label}", "ok": False, "error": str(e)[:500]}


def run_api(job: ModelJob, prompt: str, out_dir: Path, timeout: int) -> dict:
    slug_path = out_dir / "api" / f"{job.slug}.md"
    slug_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    cmd = [
        sys.executable, str(API),
        "--provider", job.provider,
        "--model", job.model,
        "--max-tokens", "2500",
        "--prompt-file", str(out_dir / "_prompt.txt"),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace", cwd=str(REPO))
        elapsed = round(time.time() - t0, 2)
        text = proc.stdout if proc.returncode == 0 else (proc.stderr or proc.stdout or "")
        ok = proc.returncode == 0 and len(text.strip()) > 150
        body = (
            f"# {job.slug}\n\n"
            f"- **provider:** `{job.provider}`\n"
            f"- **model:** `{job.model}`\n"
            f"- **tier:** {job.tier}\n"
            f"- **elapsed_s:** {elapsed}\n"
            f"- **ok:** {ok}\n\n"
            f"{text}\n"
        )
        slug_path.write_text(body, encoding="utf-8")
        return {
            "slug": job.slug, "provider": job.provider, "model": job.model,
            "tier": job.tier, "backend": "api", "ok": ok, "elapsed_s": elapsed,
            "chars": len(text), "path": str(slug_path),
        }
    except subprocess.TimeoutExpired:
        slug_path.write_text(f"# {job.slug}\n\nTIMEOUT\n", encoding="utf-8")
        return {"slug": job.slug, "provider": job.provider, "model": job.model,
                "tier": job.tier, "backend": "api", "ok": False, "error": "TIMEOUT"}


def run_ollama(tag: str, prompt: str, out_dir: Path, timeout: int) -> dict:
    slug = re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")[:72]
    path = out_dir / "local" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    full = SYSTEM_PREFIX + prompt
    t0 = time.time()
    try:
        proc = subprocess.run(
            ["ollama", "run", tag, full],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        elapsed = round(time.time() - t0, 2)
        text = (proc.stdout or "").strip()
        ok = proc.returncode == 0 and len(text) > 100
        if not ok:
            text = (proc.stderr or text or f"rc={proc.returncode}")[:2000]
        path.write_text(
            f"# {slug}\n\n- **ollama:** `{tag}`\n- **elapsed_s:** {elapsed}\n- **ok:** {ok}\n\n{text}\n",
            encoding="utf-8",
        )
        return {"slug": slug, "model": tag, "tier": "local", "backend": "ollama",
                "ok": ok, "elapsed_s": elapsed, "chars": len(text), "path": str(path)}
    except subprocess.TimeoutExpired:
        path.write_text(f"# {slug}\n\nTIMEOUT\n", encoding="utf-8")
        return {"slug": slug, "model": tag, "tier": "local", "backend": "ollama",
                "ok": False, "error": "TIMEOUT"}


def ollama_timeout(tag: str) -> int:
    low = tag.lower()
    if any(x in low for x in ("32b", "70b")):
        return 900
    if any(x in low for x in ("14b", "13b", "12b", "9b")):
        return 600
    return 300


def extract_ideas(text: str, source: str) -> list[dict]:
    ideas: list[dict] = []
    # wire_target paths
    for m in re.finditer(r"`((?:alpha_engine|audit_|tools|copy_trader|ml_)[^`]+)`", text):
        ideas.append({"source": source, "type": "wire_target", "text": m.group(1)})
    # numbered harvest lines
    for m in re.finditer(
        r"(?im)^(?:\d+[\.\)]\s*)?(?:[-*]\s*)?(?:\*\*)?(?:id|idea|harvest)[:\s]*([^\n]+)",
        text,
    ):
        ideas.append({"source": source, "type": "harvest_line", "text": m.group(1).strip()[:300]})
    # acceptance tests
    for m in re.finditer(r"(?i)acceptance[_\s]?test[:\s]+([^\n]+)", text):
        ideas.append({"source": source, "type": "acceptance", "text": m.group(1).strip()[:200]})
    return ideas


def aggregate_harvest(out_dir: Path, runs: list[dict]) -> None:
    all_ideas: list[dict] = []
    for r in runs:
        if not r.get("ok"):
            continue
        p = r.get("path")
        if not p or not Path(p).is_file():
            continue
        text = Path(p).read_text(encoding="utf-8", errors="replace")
        src = r.get("slug") or r.get("model") or "unknown"
        all_ideas.extend(extract_ideas(text, src))

    # Dedupe wire_targets
    seen: set[str] = set()
    unique: list[dict] = []
    for idea in all_ideas:
        key = (idea.get("type"), idea.get("text", "").lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(idea)

    by_type: dict[str, list] = {}
    for idea in unique:
        by_type.setdefault(idea["type"], []).append(idea)

    (out_dir / "harvest_ideas.json").write_text(
        json.dumps({"count": len(unique), "ideas": unique, "by_type": by_type}, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Idea harvest aggregate",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Runs: {sum(1 for r in runs if r.get('ok'))}/{len(runs)} ok",
        "",
        "## Top wire targets (frequency)",
        "",
    ]
    wt = [i["text"] for i in unique if i["type"] == "wire_target"]
    freq: dict[str, int] = {}
    for w in wt:
        freq[w] = freq.get(w, 0) + 1
    for path, n in sorted(freq.items(), key=lambda x: -x[1])[:40]:
        lines.append(f"- ({n}x) `{path}`")
    lines.append("\n## Sample harvest lines\n")
    for idea in unique:
        if idea["type"] == "harvest_line":
            lines.append(f"- **{idea['source']}**: {idea['text'][:200]}")
    (out_dir / "HARVEST_AGGREGATE.md").write_text("\n".join(lines), encoding="utf-8")


def append_benchmark_row(r: dict) -> None:
    if not BENCHMARK.exists():
        return
    line = (
        f"| {datetime.now(timezone.utc).strftime('%Y-%m-%d')} "
        f"| {r.get('model', r.get('slug', '?'))} "
        f"| {r.get('backend', 'api')} "
        f"| auto | harvest | {r.get('elapsed_s', '-')} "
        f"| {'Y' if r.get('ok') else 'N'} | {r.get('chars', 0)} | mega harvest |"
    )
    text = BENCHMARK.read_text(encoding="utf-8")
    if "| Date (UTC) |" in text and line not in text:
        text = text.replace(
            "\n*Add rows after each",
            f"\n{line}\n\n*Add rows after each",
            1,
        )
        BENCHMARK.write_text(text, encoding="utf-8")


def run_grok_wsl(prompt: str, out_dir: Path) -> dict:
    """SuperGrok via WSL if available."""
    path = out_dir / "api" / "grok-wsl-supergrok.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        proc = subprocess.run(
            [
                "wsl", "bash", "-lc",
                f"grok -p {json.dumps(SYSTEM_PREFIX + prompt[:10000])} "
                "--cwd /tmp --no-alt-screen --output-format json",
            ],
            capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace",
        )
        elapsed = round(time.time() - t0, 2)
        ok = proc.returncode == 0 and len(proc.stdout or "") > 200
        path.write_text(
            f"# grok-wsl-supergrok\n\n- **elapsed_s:** {elapsed}\n- **ok:** {ok}\n\n{proc.stdout or proc.stderr}\n",
            encoding="utf-8",
        )
        return {"slug": "grok-wsl-supergrok", "provider": "grok-wsl", "model": "supergrok",
                "tier": "paid", "backend": "wsl", "ok": ok, "elapsed_s": elapsed,
                "chars": len(proc.stdout or ""), "path": str(path)}
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        path.write_text(f"# grok-wsl\n\nFAIL: {e}\n", encoding="utf-8")
        return {"slug": "grok-wsl-supergrok", "ok": False, "error": str(e)}


def pull_small_models(min_free_gb: float = 15.0) -> list[str]:
    """Pull small Ollama models while C: has space."""
    free_c = free_gb("C:")
    if free_c < min_free_gb:
        print(f"Skip pulls: C: only {free_c:.1f} GB free (need {min_free_gb})")
        return []
    installed = set(list_ollama_local())
    pulled: list[str] = []
    for name, need_gb in OLLAMA_PULL_CANDIDATES:
        if free_gb("C:") < need_gb + 5:
            break
        if name in installed:
            continue
        print(f"ollama pull {name} (~{need_gb} GB)...", flush=True)
        try:
            proc = subprocess.run(
                ["ollama", "pull", name], capture_output=True, text=True,
                timeout=1800, encoding="utf-8", errors="replace",
            )
            if proc.returncode == 0:
                pulled.append(name)
                installed.add(name)
        except subprocess.TimeoutExpired:
            print(f"  TIMEOUT {name}")
    return pulled


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", choices=["paid", "free", "local", "api", "all"], default="all")
    ap.add_argument("--max-parallel", type=int, default=1,
                    help="API parallelism (default 1 — avoids GPU/API contention; use 1 always for fair benchmarks)")
    ap.add_argument("--pull-small", action="store_true", help="ollama pull small models if C: has space")
    ap.add_argument("--no-pull", action="store_true", help="skip ollama pull even if --pull-small")
    ap.add_argument("--skip-import", action="store_true")
    args = ap.parse_args()

    out_dir = ts_dir()
    prompt = PROMPT.read_text(encoding="utf-8")
    (out_dir / "_prompt.txt").write_text(SYSTEM_PREFIX + prompt, encoding="utf-8")

    if not args.skip_import:
        subprocess.run([sys.executable, str(IMPORT), "--import-all"], timeout=7200, cwd=str(REPO))

    if args.pull_small and not args.no_pull:
        pull_small_models()

    jobs: list[ModelJob] = []
    if args.tier in ("paid", "api", "all"):
        jobs.extend(PAID_API)
    if args.tier in ("free", "api", "all"):
        jobs.extend(FREE_OPENROUTER)
        jobs.extend(FREE_OTHER)

    runs: list[dict] = []
    manifest = {"out_dir": str(out_dir), "started": datetime.now(timezone.utc).isoformat(), "runs": []}

    if args.tier in ("paid", "api", "all"):
        print("Grok WSL (SuperGrok)...")
        gr = run_grok_wsl(prompt, out_dir)
        runs.append(gr)
        manifest["runs"].append(gr)
        print(f"  grok-wsl: {'OK' if gr.get('ok') else 'FAIL'}")

    # API batch
    if jobs:
        print(f"API jobs: {len(jobs)} (parallel={args.max_parallel})", flush=True)
        with ThreadPoolExecutor(max_workers=args.max_parallel) as ex:
            futs = {ex.submit(run_api, j, prompt, out_dir, 180): j for j in jobs}
            for fut in as_completed(futs):
                j = futs[fut]
                r = fut.result()
                runs.append(r)
                manifest["runs"].append(r)
                print(f"  {j.slug}: {'OK' if r.get('ok') else 'FAIL'} {r.get('elapsed_s', 0)}s", flush=True)
                if r.get("ok"):
                    append_benchmark_row(r)

    # swarm_models extras (llm7, mistral)
    if args.tier in ("free", "api", "all"):
        extras = [
            ("llm7", "qwen2.5-coder-32b"),
            ("mistral", "mistral-small-latest"),
            ("mistral-codestral", "codestral-latest"),
        ]
        print(f"swarm_models extras: {len(extras)}", flush=True)
        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = {ex.submit(run_swarm_models_endpoint, lbl, mdl, prompt, out_dir): lbl
                    for lbl, mdl in extras}
            for fut in as_completed(futs):
                r = fut.result()
                runs.append(r)
                manifest["runs"].append(r)
                print(f"  {r.get('slug')}: {'OK' if r.get('ok') else 'FAIL'}", flush=True)

    # Local Ollama (sequential — GPU)
    if args.tier in ("local", "all"):
        tags = list_ollama_local()
        print(f"Local Ollama: {len(tags)} models (sequential)", flush=True)
        for i, tag in enumerate(tags, 1):
            print(f"  [{i}/{len(tags)}] {tag}...", flush=True)
            r = run_ollama(tag, prompt, out_dir, ollama_timeout(tag))
            runs.append(r)
            manifest["runs"].append(r)
            print(f"    -> {'OK' if r.get('ok') else 'FAIL'} {r.get('elapsed_s', 0)}s", flush=True)
            if r.get("ok"):
                append_benchmark_row(r)

    aggregate_harvest(out_dir, runs)
    manifest["finished"] = datetime.now(timezone.utc).isoformat()
    manifest["ok"] = sum(1 for r in runs if r.get("ok"))
    manifest["total"] = len(runs)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nDone {manifest['ok']}/{manifest['total']} -> {out_dir}")
    print(f"Aggregate: {out_dir / 'HARVEST_AGGREGATE.md'}")
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
