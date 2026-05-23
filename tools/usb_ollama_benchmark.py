#!/usr/bin/env python3
"""Benchmark Ollama models stored on USB (H:\\ollama\\models) vs local duplicates.

Creates ephemeral tags `usb-<model>` from H: blob paths, runs CODEBASE_NARROW prompt,
writes to swarm_runs/usb-model-grill/<stamp>/.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
USB_MODELS = Path(r"H:\ollama\models")
LOCAL_MODELS = Path.home() / ".ollama" / "models"
LIB = "registry.ollama.ai/library"
PROMPT_PATH = REPO / "docs" / "swarm_prompts" / "CODEBASE_NARROW_v1.md"
OLLAMA_GENERATE = "http://localhost:11434/api/generate"
SYSTEM = (
    "Senior quant. 11/11 causal hypotheses killed. pf_registry canonical. "
    "Answer in markdown with per-class table + wire_targets + acceptance tests.\n\n"
)

# USB-only or high-value; skip 120b/480b cloud-only
CURATED = [
    "gemma3:12b",
    "mistral-nemo:12b",
    "mistral-small:24b",
    "phi4:14b",
    "qwen2.5:14b",
    "qwen2.5-coder:32b",
    "deepseek-r1:8b",
    "qwen3.5:27b",
    "mistral:7b",
    "gemma3:1b",
]
# Duplicates — re-benchmark from USB blob path
DUPLICATE_REBENCH = [
    "qwen3:14b",
    "deepseek-r1:14b",
    "gemma3:4b",
]


def digest_to_blob_path(root: Path, digest: str) -> Path | None:
    key = digest.replace(":", "-")
    if not key.startswith("sha256-"):
        key = f"sha256-{key.replace('sha256-', '')}"
    p = root / "blobs" / key
    return p if p.is_file() and p.stat().st_size > 0 else None


def read_manifest(root: Path, model: str, tag: str) -> dict | None:
    mf = root / "manifests" / LIB / model / tag
    if not mf.is_file():
        return None
    try:
        return json.loads(mf.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def model_blob_digest(manifest: dict) -> str | None:
    for layer in manifest.get("layers") or []:
        if layer.get("mediaType") == "application/vnd.ollama.image.model":
            return layer.get("digest")
    return None


def list_usb_tags() -> list[str]:
    lib = USB_MODELS / "manifests" / LIB
    if not lib.is_dir():
        return []
    tags: list[str] = []
    for model_dir in sorted(lib.iterdir()):
        if not model_dir.is_dir():
            continue
        for tag_file in model_dir.iterdir():
            if tag_file.is_file():
                tags.append(f"{model_dir.name}:{tag_file.name}")
    return tags


def classify_tags(usb_tags: list[str]) -> tuple[list[str], list[str]]:
    local_tags: set[str] = set()
    lib = LOCAL_MODELS / "manifests" / LIB
    if lib.is_dir():
        for model_dir in lib.iterdir():
            if not model_dir.is_dir():
                continue
            for tag_file in model_dir.iterdir():
                if tag_file.is_file():
                    local_tags.add(f"{model_dir.name}:{tag_file.name}")
    usb_only = [t for t in usb_tags if t not in local_tags]
    dup = [t for t in usb_tags if t in local_tags]
    return usb_only, dup


def same_weight_blob(tag: str) -> bool:
    model, _, t = tag.partition(":")
    u = read_manifest(USB_MODELS, model, t)
    l = read_manifest(LOCAL_MODELS, model, t)
    if not u or not l:
        return False
    return model_blob_digest(u) == model_blob_digest(l)


def ollama_create_usb_tag(tag: str, blob_path: Path, template: str = "qwen3:14b") -> tuple[bool, str]:
    safe = re.sub(r"[^a-z0-9._-]+", "-", tag.lower())[:50]
    usb_tag = f"usb-{safe}"
    from_posix = blob_path.resolve().as_posix()
    mf_dir = REPO / "swarm_runs" / "ollama-modelfiles"
    mf_dir.mkdir(parents=True, exist_ok=True)
    mf = mf_dir / f"Modelfile-usb-{safe}"
    try:
        tmpl = subprocess.check_output(
            ["ollama", "show", template, "--modelfile"],
            text=True, encoding="utf-8", errors="replace", timeout=60,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        tmpl = "PARAMETER num_predict 900\nPARAMETER num_ctx 4096\n"
    lines = [f"# USB FROM {tag}\n", f"FROM {from_posix}\n"]
    for line in tmpl.splitlines():
        if line.strip().startswith("FROM ") or line.strip().startswith("# FROM"):
            continue
        lines.append(line + "\n")
    mf.write_text("".join(lines), encoding="utf-8")
    gb = blob_path.stat().st_size / (1024**3)
    timeout = 1200 if gb > 15 else 600 if gb > 8 else 300
    try:
        proc = subprocess.run(
            ["ollama", "create", usb_tag, "-f", str(mf)],
            capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace",
        )
        ok = proc.returncode == 0
        return ok, usb_tag if ok else (proc.stderr or proc.stdout or "")[-500:]
    except subprocess.TimeoutExpired:
        return False, "create timeout"


def ollama_stop_all() -> None:
    try:
        out = subprocess.check_output(["ollama", "ps"], text=True, encoding="utf-8", errors="replace")
        for line in out.splitlines()[1:]:
            name = line.split()[0] if line.strip() else ""
            if name and name != "NAME":
                subprocess.run(["ollama", "stop", name], capture_output=True, timeout=60)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass


def timeout_for_tag(tag: str) -> int:
    low = tag.lower()
    if re.search(r"(27b|24b|32b|70b)", low):
        return 420
    if re.search(r"(12b|14b|13b)", low):
        return 240
    if re.search(r"(7b|8b|9b)", low):
        return 150
    return 180


def run_generate(usb_tag: str, prompt: str, timeout: int) -> tuple[bool, str, float]:
    low = usb_tag.lower()
    num_predict = 900 if re.search(r"(14b|32b|12b|24b|27b|r1)", low) else 500
    num_ctx = 2048 if re.search(r"(27b|24b|32b)", low) else 4096
    body = json.dumps({
        "model": usb_tag,
        "prompt": SYSTEM + prompt,
        "stream": False,
        "options": {"num_predict": num_predict, "temperature": 0.2, "num_ctx": num_ctx},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA_GENERATE, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        text = (data.get("response") or "").strip()
        return len(text) > 150, text, round(time.time() - t0, 2)
    except Exception as e:
        return False, str(e)[:300], round(time.time() - t0, 2)


def score(text: str) -> int:
    low = text.lower()
    s = 1
    if len(text) > 800:
        s += 1
    if "11/11" in text or "killed" in low:
        s += 1
    if re.search(r"`(?:alpha_engine|audit_|tools)/", text):
        s += 1
    if "paper" in low and "ready" in low:
        s += 1
    return min(5, s)


def main() -> int:
    if not USB_MODELS.is_dir():
        print("H:\\ollama\\models not found", file=sys.stderr)
        return 2
    if not PROMPT_PATH.is_file():
        print(f"Missing prompt {PROMPT_PATH}", file=sys.stderr)
        return 2

    usb_tags = list_usb_tags()
    usb_only, dup_tags = classify_tags(usb_tags)
    print(f"USB tags: {len(usb_tags)} | usb-only: {len(usb_only)} | name-dup: {len(dup_tags)}")

    to_run: list[tuple[str, str]] = []  # (tag, reason)
    for t in CURATED:
        if t in usb_tags:
            to_run.append((t, "curated_usb"))
    for t in DUPLICATE_REBENCH:
        if t in usb_tags and same_weight_blob(t):
            to_run.append((t, "duplicate_rebench_usb_blob"))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = REPO / "swarm_runs" / "usb-model-grill" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    results: list[dict] = []

    for tag, reason in to_run:
        model, _, tname = tag.partition(":")
        manifest = read_manifest(USB_MODELS, model, tname)
        if not manifest:
            results.append({"tag": tag, "ok": False, "error": "no manifest"})
            continue
        digest = model_blob_digest(manifest)
        if not digest:
            results.append({"tag": tag, "ok": False, "error": "no model layer"})
            continue
        blob = digest_to_blob_path(USB_MODELS, digest)
        if not blob:
            results.append({"tag": tag, "ok": False, "error": f"missing blob {digest}"})
            continue
        print(f"\n[{tag}] {reason} blob={blob.name} ({blob.stat().st_size/1e9:.1f}GB)")
        ollama_stop_all()
        time.sleep(2)
        ok_create, usb_tag_or_err = ollama_create_usb_tag(tag, blob)
        if not ok_create:
            print(f"  create FAIL: {usb_tag_or_err}")
            results.append({"tag": tag, "ok": False, "error": "create", "detail": str(usb_tag_or_err)})
            continue
        usb_tag = usb_tag_or_err
        cap = timeout_for_tag(tag)
        ok, text, elapsed = run_generate(usb_tag, prompt, cap)
        slug = re.sub(r"[^a-z0-9]+", "-", tag.lower())
        out_path = out_dir / f"{slug}__narrow__{reason}.md"
        out_path.write_text(
            f"# USB {tag} -> {usb_tag}\n\nreason={reason}\nblob={blob}\nelapsed={elapsed}s ok={ok}\n\n{text}\n",
            encoding="utf-8",
        )
        intel = score(text) if ok else 0
        print(f"  -> {'OK' if ok else 'FAIL'} {elapsed}s intel={intel}")
        results.append({
            "tag": tag, "usb_tag": usb_tag, "reason": reason, "ok": ok,
            "elapsed_s": elapsed, "intel": intel, "path": str(out_path),
            "blob_gb": round(blob.stat().st_size / (1024**3), 2),
            "duplicate_same_blob": reason == "duplicate_rebench_usb_blob",
        })
        ollama_stop_all()
        time.sleep(1)

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"results": results, "usb_only": usb_only[:40]}, indent=2), encoding="utf-8")
    ok_n = sum(1 for r in results if r.get("ok"))
    print(f"\nDone {ok_n}/{len(results)} -> {out_dir}")
    return 0 if ok_n else 1


if __name__ == "__main__":
    sys.exit(main())
