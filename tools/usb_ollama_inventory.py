#!/usr/bin/env python3
"""Inventory Ollama blobs/manifests on USB vs local; find duplicates and USB-only models."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

USB_ROOT = Path(r"H:\ollama\models")
LOCAL_ROOT = Path.home() / ".ollama" / "models"
F_GGUF = Path(r"F:\Models\Ollama_GGUFs")


def blob_index(root: Path) -> dict[str, int]:
    blobs = root / "blobs"
    if not blobs.is_dir():
        return {}
    out: dict[str, int] = {}
    for p in blobs.iterdir():
        if p.is_file() and p.name.startswith("sha256-"):
            try:
                out[p.name] = p.stat().st_size
            except OSError:
                pass
    return out


def manifest_models(root: Path) -> list[dict]:
    lib = root / "manifests" / "registry.ollama.ai" / "library"
    if not lib.is_dir():
        return []
    models: list[dict] = []
    for model_dir in lib.iterdir():
        if not model_dir.is_dir():
            continue
        for tag_dir in model_dir.iterdir():
            if not tag_dir.is_dir():
                continue
            manifest = tag_dir / "manifest.json"
            if not manifest.is_file():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            layers = data.get("layers") or []
            blob_ids = [L.get("digest", "").replace(":", "-") for L in layers if L.get("digest")]
            models.append({
                "name": f"{model_dir.name}:{tag_dir.name}",
                "blobs": blob_ids,
                "total_bytes": sum(
                    blob_index(root).get(f"sha256-{b.split('sha256-')[-1]}", 0)
                    if "sha256" in b else 0
                    for b in blob_ids
                ),
            })
    return models


def gguf_index(directory: Path) -> dict[str, int]:
    if not directory.is_dir():
        return {}
    out: dict[str, int] = {}
    for p in directory.glob("*.gguf"):
        try:
            out[p.name.lower()] = p.stat().st_size
        except OSError:
            pass
    return out


def list_ollama() -> set[str]:
    try:
        out = subprocess.check_output(["ollama", "list"], text=True, encoding="utf-8", errors="replace")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return set()
    return {line.split()[0] for line in out.splitlines()[1:] if line.split()}


def main() -> int:
    usb_blobs = blob_index(USB_ROOT)
    local_blobs = blob_index(LOCAL_ROOT)
    shared = set(usb_blobs) & set(local_blobs)
    usb_only_blobs = set(usb_blobs) - set(local_blobs)

    def gb(n: int) -> float:
        return round(n / (1024**3), 2)

    print(f"USB blobs: {len(usb_blobs)} ({gb(sum(usb_blobs.values()))} GB)")
    print(f"Local blobs: {len(local_blobs)} ({gb(sum(local_blobs.values()))} GB)")
    print(f"Shared SHA (duplicate weight): {len(shared)} ({gb(sum(usb_blobs[k] for k in shared))} GB on USB)")

  # Large USB-only blobs
    print("\n## USB-only blobs (by size)")
    only = [(k, usb_blobs[k]) for k in usb_only_blobs]
    only.sort(key=lambda x: -x[1])
    for name, size in only[:25]:
        if size > 100_000_000:
            print(f"  {name}  {gb(size)} GB")

    usb_models = manifest_models(USB_ROOT)
    local_models = manifest_models(LOCAL_ROOT)
    print(f"\nUSB manifest models: {len(usb_models)}")
    print(f"Local manifest models: {len(local_models)}")
    for m in usb_models:
        print(f"  USB: {m['name']}")

    # F: gguf names vs ollama list
    f_gguf = gguf_index(F_GGUF)
    installed = list_ollama()
    print(f"\nF: GGUF files: {len(f_gguf)}")
    print(f"ollama list: {len(installed)}")

    report = {
        "usb_blob_count": len(usb_blobs),
        "local_blob_count": len(local_blobs),
        "shared_blob_count": len(shared),
        "usb_only_large": [
            {"sha": k, "gb": gb(v)} for k, v in only[:30] if v > 500_000_000
        ],
        "usb_models": [m["name"] for m in usb_models],
    }
    out_path = Path(__file__).resolve().parents[1] / "reports" / "usb_ollama_inventory.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
