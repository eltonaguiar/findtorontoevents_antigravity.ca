#!/usr/bin/env python3
"""Ollama-only local consult: import GGUFs via Modelfile + run money-ready prompt.

No LM Studio. Uses:
  - ``tools/ollama_import_gguf.py`` logic (blob-resolved FROM + template copy)
  - ``ollama run`` for inference

Usage:
  python tools/local_gguf_ollama_consult.py
  python tools/local_gguf_ollama_consult.py --import-missing
  python tools/local_gguf_ollama_consult.py --all-installed
  python tools/local_gguf_ollama_consult.py --paths-file extra.txt
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROMPT_FILE = REPO / "swarm_runs/_prompts/MONEY_READY_HARVEST_v1.md"
PROMPT_FALLBACK = REPO / "swarm_runs/_prompts/quant_rescue_local_models_2026-05-19.md"
GGUF_DIR = Path(r"F:\Models\Ollama_GGUFs")
OUT_DIR = REPO / "swarm_runs/local-gguf-consult"
IMPORT_TOOL = REPO / "tools/ollama_import_gguf.py"

SKIP = ("nomic-embed", "embed-text")

SYSTEM = (
    "Senior quant. Brutal honesty. 11/11 causal hypotheses killed. "
    "pf_registry canonical. No dashboard PF as proof of edge."
)

# Prefer these tags when present (skip *-cloud for local GPU benchmark)
PREFER_LOCAL = (
    "qwen2.5-coder:14b-instruct-q4_K_M",
    "qwen3:14b",
    "deepseek-r1:14b",
    "mistral-nemo:latest",
    "llama3.1:latest",
    "phi3.5:latest",
    "qwen2.5-coder:7b",
    "llama3.2:3b",
    "qwen3:4b",
    "qwen3.5:9b",
)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:72]


def list_ollama_models(local_only: bool = True) -> list[str]:
    try:
        out = subprocess.check_output(["ollama", "list"], text=True, encoding="utf-8", errors="replace")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    names: list[str] = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if parts:
            tag = parts[0]
            if local_only and ("-cloud" in tag or tag.endswith(":cloud")):
                continue
            names.append(tag)
    return names


def run_import_missing(gguf_dir: Path) -> int:
    cmd = [sys.executable, str(IMPORT_TOOL), "--import-all", "--gguf-dir", str(gguf_dir)]
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, timeout=7200)
    return proc.returncode


def run_ollama(model: str, user_prompt: str, timeout: int) -> tuple[bool, str, float]:
    full = SYSTEM + "\n\n" + user_prompt
    t0 = time.time()
    try:
        proc = subprocess.run(
            ["ollama", "run", model, full],
            capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace",
        )
        elapsed = round(time.time() - t0, 2)
        text = (proc.stdout or "").strip()
        if proc.returncode != 0:
            err = (proc.stderr or text or f"rc={proc.returncode}")[:1500]
            return False, err, elapsed
        return True, text or "[empty]", elapsed
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", round(time.time() - t0, 2)
    except FileNotFoundError:
        return False, "ollama not found", 0.0


def timeout_for_tag(tag: str) -> int:
    low = tag.lower()
    if any(x in low for x in ("32b", "70b", "671b")):
        return 900
    if any(x in low for x in ("14b", "13b", "12b", "9b")):
        return 600
    if any(x in low for x in ("7b", "8b")):
        return 360
    return 240


def pick_models(
    all_installed: list[str],
    extra: list[str],
    all_flag: bool,
    library_only: bool,
) -> list[str]:
    if extra:
        return [m for m in extra if m in all_installed]
    if all_flag:
        tags = list(all_installed)
    else:
        tags = [m for m in PREFER_LOCAL if m in all_installed]
        # Also any library-* / qr-* tags from imports
        for m in all_installed:
            if m.startswith(("library-", "lib-", "qr-")) and m not in tags:
                tags.append(m)
    if library_only:
        tags = [t for t in tags if t.startswith(("library-", "lib-", "qr-"))]
    return tags


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--import-missing", action="store_true",
                    help="Run ollama_import_gguf.py --import-all first")
    ap.add_argument("--all-installed", action="store_true", help="Consult every local ollama tag")
    ap.add_argument("--library-only", action="store_true", help="Only library-/qr- imported tags")
    ap.add_argument("--models", nargs="*", default=[], help="Explicit ollama tags")
    ap.add_argument("--paths-file", type=Path, help="Import these GGUF paths then consult new tags")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--prompt-file", type=Path, default=None)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.import_missing or args.paths_file:
        if args.paths_file:
            subprocess.run(
                [sys.executable, str(IMPORT_TOOL), "--paths-file", str(args.paths_file)],
                timeout=7200, check=False,
            )
        elif args.import_missing:
            run_import_missing(GGUF_DIR)

    prompt_path = args.prompt_file or (PROMPT_FILE if PROMPT_FILE.is_file() else PROMPT_FALLBACK)
    prompt = prompt_path.read_text(encoding="utf-8")

    installed = list_ollama_models(local_only=True)
    print(f"Local Ollama models: {len(installed)}")

    models = pick_models(installed, args.models, args.all_installed, args.library_only)
    if not models:
        print("No models to run. Try: python tools/ollama_import_gguf.py --scan", file=sys.stderr)
        return 2

    results = []
    for i, tag in enumerate(models, 1):
        tmo = timeout_for_tag(tag)
        print(f"[{i}/{len(models)}] ollama run {tag} ({tmo}s, GPU auto)...")
        ok, text, elapsed = run_ollama(tag, prompt, tmo)
        s = slug(tag.replace(":", "-"))
        out = args.out_dir / f"{s}.md"
        hdr = (
            f"# {s}\n\n"
            f"- **ollama:** `{tag}`\n"
            f"- **elapsed_s:** {elapsed}\n"
            f"- **mode:** ollama (GPU/CPU auto)\n"
            f"- **prompt:** `{prompt_path.name}`\n"
            f"- **ok:** {ok}\n\n"
        )
        out.write_text(hdr + text + "\n", encoding="utf-8")
        results.append({
            "slug": s, "ollama": tag, "ok": ok, "chars": len(text),
            "elapsed_s": elapsed, "backend": "ollama",
        })
        print(f"  -> {'OK' if ok else 'FAIL'} {len(text)} chars in {elapsed}s")

    (args.out_dir / "_summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok_n = sum(1 for r in results if r["ok"])
    print(f"Done {ok_n}/{len(results)} -> {args.out_dir}")
    return 0 if ok_n else 1


if __name__ == "__main__":
    sys.exit(main())
