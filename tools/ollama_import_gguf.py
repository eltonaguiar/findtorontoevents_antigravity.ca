#!/usr/bin/env python3
"""Import local GGUF files into Ollama using Modelfiles (no LM Studio).

F:\\Models\\Ollama_GGUFs\\*.gguf are usually symlinks into
``%USERPROFILE%\\.ollama\\models\\blobs\\sha256-*``. Ollama 0.24 on Windows
needs the **resolved blob path** (or a real GGUF file), not the symlink, in
the Modelfile ``FROM`` line. Copy chat templates from a similar installed model.

Usage:
  python tools/ollama_import_gguf.py --scan
  python tools/ollama_import_gguf.py --import-all
  python tools/ollama_import_gguf.py --path F:/Models/Ollama_GGUFs/library-gemma3-4b.gguf
  python tools/ollama_import_gguf.py --paths-file extra_ggufs.txt
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_GGUF_DIR = Path(r"F:\Models\Ollama_GGUFs")
MODELFILES_DIR = Path(__file__).resolve().parents[1] / "swarm_runs" / "ollama-modelfiles"
SKIP_SUBSTR = ("nomic-embed", "embed-text")

# filename hints -> template source for `ollama show --modelfile`
TEMPLATE_FOR_NAME: list[tuple[str, str]] = [
    (r"deepseek-r1", "deepseek-r1:14b"),
    (r"deepseek", "deepseek-r1:14b"),
    (r"qwen2\.5-coder|qwen2\.5", "qwen2.5-coder:14b-instruct-q4_K_M"),
    (r"qwen3|qwen", "qwen3:14b"),
    (r"mixtral|mistral|devstral", "mistral-nemo:latest"),
    (r"llama4|llama3|llama", "llama3.1:latest"),
    (r"phi", "phi3.5:latest"),
    (r"glm", "qwen3:14b"),
    (r"gemma", "llama3.1:latest"),
]
DEFAULT_TEMPLATE = "llama3.1:latest"


def slug_tag(stem: str) -> str:
    """Ollama tag: lowercase, dots ok, one colon for version."""
    base = re.sub(r"[^a-z0-9._-]+", "-", stem.lower()).strip("-")
    base = base[:56] or "imported"
    return f"{base}:latest"


def list_installed() -> set[str]:
    try:
        out = subprocess.check_output(["ollama", "list"], text=True, encoding="utf-8", errors="replace")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    names: set[str] = set()
    for line in out.splitlines()[1:]:
        parts = line.split()
        if parts:
            names.add(parts[0])
    return names


def resolve_from_path(gguf: Path) -> tuple[Path | None, str]:
    """Return (absolute path for FROM line, note)."""
    if not gguf.exists():
        return None, "path does not exist"
    try:
        resolved = gguf.resolve(strict=False)
    except OSError:
        resolved = gguf
    if resolved.is_file() and resolved.stat().st_size > 0:
        return resolved, "resolved file"
    if gguf.is_symlink():
        target = Path(os_readlink(gguf))
        if target.is_file() and target.stat().st_size > 0:
            return target, "symlink target"
        return None, f"symlink target missing: {target}"
    return None, "empty or missing blob"


def os_readlink(p: Path) -> Path:
    import os
    return Path(os.readlink(p))


def pick_template(name: str, installed: set[str]) -> str:
    low = name.lower()
    for pattern, template in TEMPLATE_FOR_NAME:
        if re.search(pattern, low):
            if template in installed:
                return template
    if DEFAULT_TEMPLATE in installed:
        return DEFAULT_TEMPLATE
    for t in installed:
        if "-cloud" not in t:
            return t
    return DEFAULT_TEMPLATE


def fetch_template_modelfile(template: str) -> str:
    try:
        out = subprocess.check_output(
            ["ollama", "show", template, "--modelfile"],
            text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        return out
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return f"# fallback minimal\nFROM placeholder\nPARAMETER num_predict 2048\n"


def build_modelfile(from_path: Path, template: str) -> str:
    raw = fetch_template_modelfile(template)
    # Absolute path with forward slashes (Grok / Ollama Windows guidance)
    from_line = f"FROM {from_path.resolve().as_posix()}"
    lines = raw.splitlines()
    out: list[str] = []
    replaced = False
    for line in lines:
        if line.strip().startswith("FROM "):
            if not replaced:
                out.append(from_line)
                replaced = True
            continue
        if line.strip().startswith("# FROM "):
            continue
        out.append(line)
    if not replaced:
        out.insert(0, from_line)
    header = (
        f"# Auto-generated for {from_path.name}\n"
        f"# Template chat format from: {template}\n"
    )
    return header + "\n".join(out) + "\n"


def create_model(tag: str, modelfile: Path, timeout: int = 600) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["ollama", "create", tag, "-f", str(modelfile)],
            capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace",
        )
        msg = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0:
            return True, msg[-500:]
        return False, msg[-1500:]
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT during ollama create"


def import_one(gguf: Path, installed: set[str], dry_run: bool = False) -> dict:
    stem = gguf.stem
    tag = slug_tag(stem)
    if tag in installed:
        return {"gguf": str(gguf), "tag": tag, "status": "already_installed", "ok": True}

    from_path, note = resolve_from_path(gguf)
    if from_path is None:
        return {"gguf": str(gguf), "tag": tag, "status": "skip", "ok": False, "error": note}

    template = pick_template(stem, installed)
    MODELFILES_DIR.mkdir(parents=True, exist_ok=True)
    mf_path = MODELFILES_DIR / f"Modelfile-{re.sub(r'[^a-z0-9._-]+', '-', stem.lower())}"
    body = build_modelfile(from_path, template)
    if dry_run:
        return {
            "gguf": str(gguf), "tag": tag, "status": "dry_run",
            "from": str(from_path), "template": template, "modelfile": str(mf_path), "ok": True,
        }

    mf_path.write_text(body, encoding="utf-8")
    gb = from_path.stat().st_size / (1024**3)
    timeout = 900 if gb > 12 else 600 if gb > 6 else 300
    ok, msg = create_model(tag, mf_path, timeout=timeout)
    return {
        "gguf": str(gguf), "tag": tag, "from": str(from_path), "template": template,
        "modelfile": str(mf_path), "status": "created" if ok else "create_failed",
        "ok": ok, "message": msg,
    }


def collect_paths(paths: list[Path], gguf_dir: Path | None) -> list[Path]:
    found: list[Path] = []
    for p in paths:
        if p.is_file() and p.suffix.lower() == ".gguf":
            found.append(p)
        elif p.is_dir():
            found.extend(sorted(p.glob("*.gguf")))
    if gguf_dir and gguf_dir.is_dir():
        for g in sorted(gguf_dir.glob("*.gguf")):
            if g not in found:
                found.append(g)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan", action="store_true", help="List GGUFs and whether blob/path exists")
    ap.add_argument("--import-all", action="store_true", help="Import all resolvable GGUFs under --gguf-dir")
    ap.add_argument("--path", type=Path, action="append", default=[], help="Single GGUF path")
    ap.add_argument("--paths-file", type=Path, help="Text file, one path per line")
    ap.add_argument("--gguf-dir", type=Path, default=DEFAULT_GGUF_DIR)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    extra: list[Path] = list(args.path)
    if args.paths_file and args.paths_file.is_file():
        for line in args.paths_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                extra.append(Path(line))

    ggufs = collect_paths(extra, args.gguf_dir if args.import_all or args.scan else None)
    ggufs = [g for g in ggufs if not any(s in g.name.lower() for s in SKIP_SUBSTR)]

    if args.scan:
        print(f"{'NAME':<45} {'OK':<5} {'FROM'}")
        for g in ggufs:
            fp, note = resolve_from_path(g)
            ok = "Y" if fp else "N"
            print(f"{g.name:<45} {ok:<5} {fp or note}")
        return 0

    if not (args.import_all or extra):
        ap.print_help()
        return 2

    installed = list_installed()
    results = []
    for g in ggufs:
        print(f"Import {g.name} ...")
        r = import_one(g, installed, dry_run=args.dry_run)
        results.append(r)
        print(f"  -> {r.get('status')} {r.get('tag', '')} {'OK' if r.get('ok') else r.get('error', r.get('message', ''))[:80]}")
        if r.get("ok") and r.get("status") == "created":
            installed = list_installed()

    ok_n = sum(1 for r in results if r.get("ok"))
    print(f"\n{ok_n}/{len(results)} ok")
    return 0 if ok_n else 1


if __name__ == "__main__":
    sys.exit(main())
