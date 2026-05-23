#!/usr/bin/env python3
"""DEPRECATED — use Ollama-only tools instead.

Prefer:
  python tools/ollama_import_gguf.py --import-all
  python tools/local_gguf_ollama_consult.py

This script required LM Studio (lms.exe + GUI server). Kept for reference only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT = REPO / "swarm_runs/_prompts/quant_rescue_local_models_2026-05-19.md"
LMS = Path(r"E:\Program Files\LM Studio\resources\app\.webpack\lms.exe")
API = "http://127.0.0.1:1234/v1/chat/completions"

# F: Ollama library + E: LM Studio (user list); embed models excluded
DEFAULT_GGUF_PATHS: list[str] = [
    r"F:\Models\Ollama_GGUFs\library-gemma3-4b.gguf",
    r"F:\Models\Ollama_GGUFs\library-qwen2.5-coder-7b.gguf",
    r"F:\Models\Ollama_GGUFs\library-qwen2.5-coder-14b.gguf",
    r"F:\Models\Ollama_GGUFs\library-qwen2.5-coder-14b-instruct-q4_K_M.gguf",
    r"F:\Models\Ollama_GGUFs\library-qwen2.5-latest.gguf",
    r"F:\Models\Ollama_GGUFs\library-devstral-small-2-latest.gguf",
    r"F:\Models\Ollama_GGUFs\library-glm-4.7-flash-latest.gguf",
    r"F:\Models\Ollama_GGUFs\library-llama3-latest.gguf",
    r"F:\Models\Ollama_GGUFs\library-llama3.1-latest.gguf",
    r"F:\Models\Ollama_GGUFs\library-llama4-scout.gguf",
    r"F:\Models\Ollama_GGUFs\library-mistral-latest.gguf",
    r"F:\Models\Ollama_GGUFs\library-mistral-nemo-latest.gguf",
    r"F:\Models\Ollama_GGUFs\library-mixtral-latest.gguf",
    r"F:\Models\Ollama_GGUFs\library-mixtral-8x7b.gguf",
    r"F:\Models\Ollama_GGUFs\library-deepseek-r1-14b.gguf",
    r"F:\Models\Ollama_GGUFs\library-deepseek-r1-32b.gguf",
    r"F:\Models\Ollama_GGUFs\library-qwen2.5-coder-32b.gguf",
    r"E:\Users\zerou\.lmstudio\models\mradermacher\DeepSeek-R1-Distill-Qwen-14B-Uncensored-GGUF\DeepSeek-R1-Distill-Qwen-14B-Uncensored.Q3_K_S.gguf",
    r"E:\Users\zerou\.lmstudio\models\mradermacher\DeepSeek-R1-Distill-Qwen-32B-Uncensored-GGUF\DeepSeek-R1-Distill-Qwen-32B-Uncensored.Q3_K_S.gguf",
    r"E:\Users\zerou\.lmstudio\models\bartowski\DeepSeek-R1-Distill-Qwen-32B-abliterated-GGUF\DeepSeek-R1-Distill-Qwen-32B-abliterated-Q3_K_S.gguf",
    r"E:\Users\zerou\.lmstudio\models\bartowski\gemma-2-2b-it-abliterated-GGUF\gemma-2-2b-it-abliterated-Q5_K_S.gguf",
    r"E:\Users\zerou\.lmstudio\models\DavidAU\OpenAi-GPT-oss-20b-abliterated-uncensored-NEO-Imatrix-gguf\OpenAI-20B-NEO-CODEPlus-Uncensored-Q5_1.gguf",
    r"E:\Users\zerou\.lmstudio\models\lmstudio-community\gpt-oss-20b-GGUF\gpt-oss-20b-MXFP4.gguf",
    r"E:\Users\zerou\.lmstudio\models\mradermacher\UNCENSORED-Fusetrix-Dolphin-3.2-1B-GRPO_Creative_RP-GGUF\UNCENSORED-Fusetrix-Dolphin-3.2-1B-GRPO_Creative_RP.Q8_0.gguf",
    r"E:\Users\zerou\.lmstudio\models\Orenguteng\Llama-3.1-8B-Lexi-Uncensored-V2-GGUF\Llama-3.1-8B-Lexi-Uncensored_V2_Q4.gguf",
]

SKIP_PATTERNS = ("nomic-embed", "embed-text")

# If already in `ollama list`, use ollama run (faster than LM Studio load)
OLLAMA_ALIAS: dict[str, str] = {
    "library-deepseek-r1-14b.gguf": "deepseek-r1:14b",
    "library-mistral-nemo-latest.gguf": "mistral-nemo:latest",
    "library-qwen2.5-coder-7b.gguf": "qwen2.5-coder:7b",
    "library-qwen2.5-coder-14b-instruct-q4_K_M.gguf": "qwen2.5-coder:14b-instruct-q4_K_M",
    "library-llama3.1-latest.gguf": "llama3.1:latest",
}


def slug_from_path(p: Path) -> str:
    name = p.stem.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return name[:80] or "model"


def size_gb(path: Path) -> float:
    try:
        return path.stat().st_size / (1024**3)
    except OSError:
        return 99.0


def timeout_for(path: Path) -> int:
    gb = size_gb(path)
    if gb < 4:
        return 180
    if gb < 12:
        return 420
    return 720


def lms_run(args: list[str], timeout: int = 600) -> tuple[int, str]:
    if not LMS.is_file():
        return 127, "lms.exe not found"
    cmd = [str(LMS)] + args
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace"
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"


def wait_for_server(max_wait: int = 90) -> bool:
    for _ in range(max_wait):
        try:
            req = urllib.request.Request("http://127.0.0.1:1234/v1/models", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(1)
    return False


def chat_lms(identifier: str, system: str, user: str, timeout_s: int) -> tuple[bool, str]:
    body = json.dumps({
        "model": identifier,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        API, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = json.load(resp)
        text = data["choices"][0]["message"]["content"]
        return True, text or "[empty]"
    except Exception as exc:  # noqa: BLE001
        return False, f"[API ERROR] {exc}"


def chat_ollama(model: str, system: str, user: str, timeout_s: int) -> tuple[bool, str]:
    full = f"{system}\n\n{user}"
    try:
        proc = subprocess.run(
            ["ollama", "run", model, full],
            capture_output=True, text=True, timeout=timeout_s, encoding="utf-8", errors="replace",
        )
        if proc.returncode != 0:
            return False, (proc.stderr or proc.stdout or f"rc={proc.returncode}")[:2000]
        return True, (proc.stdout or "").strip() or "[empty]"
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except FileNotFoundError:
        return False, "ollama not on PATH"


def consult_one(
    path: Path,
    prompt: str,
    out_dir: Path,
    use_ollama: bool,
) -> dict:
    slug = slug_from_path(path)
    out_file = out_dir / f"{slug}.md"
    system = (
        "Senior quant. Brutal honesty. 11/11 causal hypotheses killed by edge_stability_harness. "
        "pf_registry.json is canonical; do not claim live edge from dashboard tiles."
    )
    tmo = timeout_for(path)
    rec: dict = {
        "path": str(path),
        "slug": slug,
        "size_gb": round(size_gb(path), 2),
        "timeout_s": tmo,
        "backend": "",
        "ok": False,
        "chars": 0,
        "error": "",
    }

    if not path.is_file():
        rec["error"] = "file not found"
        out_file.write_text(f"# {slug}\n\nMISSING: {path}\n", encoding="utf-8")
        return rec

    fname = path.name
    if any(s in fname.lower() for s in SKIP_PATTERNS):
        rec["error"] = "skip embed model"
        rec["backend"] = "skip"
        return rec

    ollama_name = OLLAMA_ALIAS.get(fname) if use_ollama else None
    if ollama_name:
        rec["backend"] = f"ollama:{ollama_name}"
        print(f"  [ollama] {ollama_name} ({rec['size_gb']} GB, timeout {tmo}s)...")
        ok, text = chat_ollama(ollama_name, system, prompt, tmo)
    else:
        ident = f"qr-{slug}"[:60]
        rec["backend"] = f"lms:{ident}"
        print(f"  [lms load] {path.name} ({rec['size_gb']} GB)...")
        rc, msg = lms_run(
            ["load", str(path), "-y", "--exact", "--identifier", ident, "--context-length", "8192"],
            timeout=max(600, tmo),
        )
        if rc != 0:
            rec["error"] = f"load failed: {msg[:500]}"
            out_file.write_text(f"# {slug}\n\nLOAD FAILED:\n\n{msg}\n", encoding="utf-8")
            return rec
        print(f"  [lms chat] {ident}...")
        ok, text = chat_lms(ident, system, prompt, tmo)
        lms_run(["unload", ident], timeout=120)

    rec["ok"] = ok
    rec["chars"] = len(text)
    if not ok:
        rec["error"] = text[:300]
    header = f"# {slug}\n\n- **path:** `{path}`\n- **backend:** {rec['backend']}\n- **size_gb:** {rec['size_gb']}\n\n"
    out_file.write_text(header + text + "\n", encoding="utf-8")
    print(f"    -> {'OK' if ok else 'FAIL'} {rec['chars']} chars -> {out_file.name}")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPT)
    ap.add_argument("--out-dir", type=Path, default=REPO / "swarm_runs/local-gguf-consult")
    ap.add_argument("--paths-file", type=Path, help="One GGUF path per line")
    ap.add_argument("--max-models", type=int, default=0, help="0 = all")
    ap.add_argument("--no-ollama-alias", action="store_true")
    ap.add_argument("--start-server", action="store_true", help="Run lms server start first")
    args = ap.parse_args()

    paths: list[Path] = []
    if args.paths_file and args.paths_file.is_file():
        for line in args.paths_file.read_text(encoding="utf-8").splitlines():
            line = line.strip().strip('"')
            if line and line.lower().endswith(".gguf"):
                paths.append(Path(line))
    else:
        paths = [Path(p) for p in DEFAULT_GGUF_PATHS]

    # Dedupe by resolved path
    seen: set[str] = set()
    unique: list[Path] = []
    for p in paths:
        key = str(p).lower()
        if key not in seen and p.name.lower().endswith(".gguf"):
            seen.add(key)
            unique.append(p)
    unique.sort(key=lambda p: size_gb(p))

    if args.max_models > 0:
        unique = unique[: args.max_models]

    prompt = args.prompt_file.read_text(encoding="utf-8")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.start_server:
        print("Starting LM Studio server...")
        subprocess.Popen(
            [str(LMS), "server", "start", "--port", "1234"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(3)

    if not wait_for_server(120):
        print("ERROR: LM Studio API not reachable at 127.0.0.1:1234", file=sys.stderr)
        print("Start LM Studio app or run: lms server start", file=sys.stderr)
        return 2

    print(f"Consulting {len(unique)} models -> {args.out_dir}")
    results = []
    for i, p in enumerate(unique, 1):
        print(f"[{i}/{len(unique)}] {p.name}")
        results.append(consult_one(p, prompt, args.out_dir, use_ollama=not args.no_ollama_alias))

    summary_path = args.out_dir / "_summary.json"
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok_n = sum(1 for r in results if r.get("ok"))
    print(f"\nDone: {ok_n}/{len(results)} ok. Summary: {summary_path}")
    return 0 if ok_n else 1


if __name__ == "__main__":
    sys.exit(main())
