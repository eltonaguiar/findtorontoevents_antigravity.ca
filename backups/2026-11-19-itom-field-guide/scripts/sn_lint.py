#!/usr/bin/env python3
"""sn_lint.py — keep the ITOM field guide honest.

    python3 scripts/sn_lint.py           # human readable
    python3 scripts/sn_lint.py --quiet   # exit code only

Checks:
  1. Every doc has an H1, an Agent stamp, and an Updated date.
  2. Every doc has an "Official sources" section with at least one URL, and every URL in
     that section is on the ServiceNow allowlist.
  3. No TODO/TBD/FIXME/XXX left in published prose.
  4. Every relative link resolves on disk (so the Pages site has no dead links).
  5. data/modules.json is valid, has unique ids, required keys, and existing labs.
  6. data/sources.json has a non-empty allowlist and valid URL entries.
  7. Every navigation target in _layouts/default.html resolves to a markdown/asset file.

Exit code 1 if anything fails.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DOCS = (
    sorted((ROOT / "docs").rglob("*.md"))
    + sorted((ROOT / "labs").glob("*.md"))
    + [ROOT / "README.md", ROOT / "index.md"]
)
REQUIRED_MODULE_KEYS = {
    "id", "name", "app", "why", "primary_table", "tables", "roles",
    "breadcrumbs", "fields", "must_know", "mistakes", "timebox_min",
    "quiz", "labs", "official_docs",
}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
URL_RE = re.compile(r"https?://[^\s)>\]]+")
FRONT_MATTER_RE = re.compile(r"^---\n.*?\n---\n", re.S)


class Result:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def load_allowlist() -> list[str]:
    data = load_json("data/sources.json")
    return data.get("allowlisted_domains", [])


def strip_front_matter(text: str) -> str:
    return FRONT_MATTER_RE.sub("", text, count=1)


def check_doc(path: Path, allow: list[str], res: Result) -> None:
    rel = path.relative_to(ROOT)
    text = strip_front_matter(path.read_text(encoding="utf-8"))

    if not text.lstrip().startswith("# "):
        res.err(f"{rel}: no H1 title")
    if "**Agent:**" not in text:
        res.err(f"{rel}: missing '**Agent:**' stamp")
    if not re.search(r"\*\*Updated:\*\*\s*\d{4}-\d{2}-\d{2}", text):
        res.err(f"{rel}: missing '**Updated:** YYYY-MM-DD'")

    for bad in ("TODO", "TBD", "FIXME", "XXX"):
        if re.search(rf"\b{bad}\b", text):
            res.err(f"{rel}: contains {bad}")

    m = re.search(r"^## Official sources\s*$((?:(?!^## ).)*)", text, re.S | re.M)
    if not m:
        res.err(f"{rel}: no '## Official sources' section")
    else:
        section = m.group(1)
        urls = URL_RE.findall(section)
        if not urls:
            res.err(f"{rel}: 'Official sources' has no URL")
        for u in urls:
            host = urlparse(u).netloc.lower()
            if not any(host == d or host.endswith("." + d) for d in allow):
                res.err(f"{rel}: non-official source in 'Official sources': {u}")

    for target in LINK_RE.findall(text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        clean = target.split("#")[0].split("?")[0]
        if not clean:
            continue
        candidate = (path.parent / clean).resolve()
        if not candidate.exists():
            res.err(f"{rel}: dead relative link -> {clean}")


def check_modules(res: Result) -> None:
    data = load_json("data/modules.json")
    modules = data.get("modules")
    if not isinstance(modules, list) or not modules:
        res.err("modules.json: missing or empty modules array")
        return
    seen = set()
    for mod in modules:
        missing = REQUIRED_MODULE_KEYS - set(mod)
        if missing:
            res.err(f"modules.json [{mod.get('id', '?')}]: missing keys {sorted(missing)}")
        mid = mod.get("id")
        if mid in seen:
            res.err(f"modules.json: duplicate id {mid}")
        seen.add(mid)
        for lab in mod.get("labs", []):
            if not (ROOT / lab).exists():
                res.err(f"modules.json [{mid}]: lab missing on disk -> {lab}")
        for url in mod.get("official_docs", []):
            if not url.startswith("https://www.servicenow.com/docs/"):
                res.err(f"modules.json [{mid}]: official_docs URL not on docs site -> {url}")
        tb = mod.get("timebox_min")
        if not isinstance(tb, dict) or not tb:
            res.err(f"modules.json [{mid}]: timebox_min must be a non-empty object")


def check_sources(res: Result) -> None:
    data = load_json("data/sources.json")
    allow = data.get("allowlisted_domains")
    if not allow:
        res.err("sources.json: allowlisted_domains empty")
        return
    if "www.servicenow.com" not in allow:
        res.err("sources.json: www.servicenow.com missing from allowlist")
    for name, urls in data.get("per_module", {}).items():
        if not isinstance(urls, list) or not urls:
            res.err(f"sources.json [{name}]: empty URL list")
            continue
        for url in urls:
            host = urlparse(url).netloc.lower()
            if not any(host == d or host.endswith("." + d) for d in allow):
                res.err(f"sources.json [{name}]: non-allowlisted URL -> {url}")


def check_nav(res: Result) -> None:
    layout = (ROOT / "_layouts" / "default.html").read_text(encoding="utf-8")
    hrefs = re.findall(r'href="\{\{\s*[\'"]([^\'"]+)[\'"]\s*\|\s*relative_url\s*\}\}"', layout)
    for href in hrefs:
        if href in ("/", ""):
            target = ROOT / "index.md"
        elif href.endswith("/"):
            base = ROOT / href.strip("/")
            if base.with_suffix(".md").exists():
                target = base.with_suffix(".md")
            else:
                target = base / "index.md"
        else:
            target = ROOT / href.lstrip("/")
        if not target.exists() and target.suffix == ".css":
            target = target.with_suffix(".scss")
        if not target.exists():
            res.err(f"layout nav: target missing -> {href} (looked for {target.relative_to(ROOT)})")


def main() -> None:
    res = Result()
    allow = load_allowlist()
    if not allow:
        res.err("sources.json: allowlisted_domains empty")

    for doc in DOCS:
        if doc.exists():
            check_doc(doc, allow, res)

    check_modules(res)
    check_sources(res)
    check_nav(res)

    quiet = "--quiet" in sys.argv
    if not quiet:
        for w in res.warnings:
            print(f"warn  {w}")
        for e in res.errors:
            print(f"ERROR {e}")
        print(
            f"\nchecked {len([d for d in DOCS if d.exists()])} docs · "
            f"{len(res.errors)} errors · {len(res.warnings)} warnings"
        )
    sys.exit(1 if res.errors else 0)


if __name__ == "__main__":
    main()
