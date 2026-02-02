#!/usr/bin/env python3
"""
Stage the Toronto Events site for tdotevent.ca into a local folder.

Copies from this project into STAGING_DIR (default E:\\tdotevent.ca) and rewrites
paths/domains: findtorontoevents.ca → tdotevent.ca so the staged site is ready
to deploy to https://tdotevent.ca.

Usage (from project root):
  python tools/stage_for_tdotevent.py

Environment:
  STAGING_DIR  Local folder to write to (default: E:\\tdotevent.ca)
"""
import os
import re
import shutil
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = _SCRIPT_DIR.parent

DEFAULT_STAGING = "E:\\tdotevent.ca"

# Domain/site name rewrites for tdotevent.ca (order matters: more specific first)
# We do NOT rewrite the raw GitHub events fallback URL so events still load if you don't have a tdotevent.ca repo.
REWRITES = [
    (r"https?://(?:www\.)?findtorontoevents\.ca", "https://www.tdotevent.ca"),
    (r"www\.findtorontoevents\.ca", "www.tdotevent.ca"),
    # Skip raw.githubusercontent.com/.../findtorontoevents - keep as fallback for events
    (r"(?<!raw\.githubusercontent\.com/eltonaguiar/)findtorontoevents\.ca", "tdotevent.ca"),
]
# Pre-compile for multiple use
REWRITE_PATTERNS = [(re.compile(p), r) for p, r in REWRITES]


def _env(key: str, fallback: str = "") -> str:
    return os.environ.get(key, fallback).strip()


def rewrite_content(text: str) -> str:
    for pattern, repl in REWRITE_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def copy_tree(src: Path, dst: Path, rewrite_extensions: tuple = ()) -> int:
    """Copy directory tree. If file extension is in rewrite_extensions, rewrite content."""
    count = 0
    dst.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(src):
        root_path = Path(root)
        rel = root_path.relative_to(src)
        dest_dir = dst / rel
        dest_dir.mkdir(parents=True, exist_ok=True)
        for name in files:
            src_file = root_path / name
            dest_file = dest_dir / name
            if any(name.lower().endswith(ext) for ext in rewrite_extensions):
                content = src_file.read_text(encoding="utf-8", errors="replace")
                dest_file.write_text(rewrite_content(content), encoding="utf-8")
            else:
                shutil.copy2(src_file, dest_file)
            count += 1
    return count


def main() -> None:
    staging = Path(_env("STAGING_DIR") or DEFAULT_STAGING)
    staging.mkdir(parents=True, exist_ok=True)

    print(f"Staging for tdotevent.ca -> {staging}")
    print("Rewrites: findtorontoevents.ca -> tdotevent.ca")
    print()

    # 1. index.html (rewrite)
    idx_src = WORKSPACE / "index.html"
    if idx_src.is_file():
        content = idx_src.read_text(encoding="utf-8", errors="replace")
        (staging / "index.html").write_text(rewrite_content(content), encoding="utf-8")
        print("  index.html (rewritten)")
    else:
        print("  Skip index.html (not found)")

    # 2. .htaccess (copy as-is)
    ht = WORKSPACE / ".htaccess"
    if ht.is_file():
        shutil.copy2(ht, staging / ".htaccess")
        print("  .htaccess")

    # 3. events.json
    ev = WORKSPACE / "events.json"
    if ev.is_file():
        shutil.copy2(ev, staging / "events.json")
        print("  events.json")

    # 4. next/events.json
    next_ev = WORKSPACE / "next" / "events.json"
    (staging / "next").mkdir(parents=True, exist_ok=True)
    if next_ev.is_file():
        shutil.copy2(next_ev, staging / "next" / "events.json")
        print("  next/events.json")

    # 5. next/_next/ (full tree, no rewrites in JS/CSS to avoid breaking chunks)
    next_next = WORKSPACE / "next" / "_next"
    if next_next.is_dir():
        n = 0
        for root, dirs, files in os.walk(next_next):
            root_path = Path(root)
            rel = root_path.relative_to(next_next)
            dest_dir = staging / "next" / "_next" / rel
            dest_dir.mkdir(parents=True, exist_ok=True)
            for name in files:
                shutil.copy2(root_path / name, dest_dir / name)
                n += 1
        print(f"  next/_next/ -> {n} files")
    else:
        print("  Skip next/_next (not found)")

    # 6. FavCreators -> fc/
    fc_src = WORKSPACE / "favcreators" / "docs"
    fc_dst = staging / "fc"
    if fc_src.is_dir():
        if fc_dst.exists():
            shutil.rmtree(fc_dst)
        shutil.copytree(fc_src, fc_dst)
        print(f"  fc/ (FavCreators, {len(list(fc_dst.rglob('*')))} items)")
    else:
        print("  Skip fc/ (favcreators/docs not found)")

    print()
    print("Staging complete. Deploy with: python tools/deploy_tdotevent_to_ftp.py")


if __name__ == "__main__":
    main()
