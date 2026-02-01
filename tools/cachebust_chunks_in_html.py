import os
import re
from datetime import datetime, timezone

ROOT = r"e:\\findtorontoevents.ca"

# Adds ?v=<timestamp> to chunk urls in exported HTML so browsers fetch fresh bundles.
# Targets common exported paths:
#   /next/_next/static/chunks/<hash>.js
#   /next/_next/static/chunks/<hash>.css
#   /next/static/chunks/<hash>.js
#   /next/static/chunks/<hash>.css

CHUNK_RE = re.compile(
    r'(?P<attr>(?:src|href)=\")(?P<url>/(?:next/_next|next)/static/chunks/[^\"?]+\.(?:js|css))(?P<end>\")',
    re.IGNORECASE,
)

TURBOPACK_QS_RE = re.compile(
    r'(?P<attr>(?:src|href)=\")(?P<url>/(?:next/_next|next)/static/chunks/turbopack-[^\"?]+\.js)\?v=[^\"]+(?P<end>\")',
    re.IGNORECASE,
)


def patch_html(s: str, v: str) -> str:
    def _strip_turbopack_qs(m: re.Match) -> str:
        return f"{m.group('attr')}{m.group('url')}{m.group('end')}"

    s = TURBOPACK_QS_RE.sub(_strip_turbopack_qs, s)

    def _repl(m: re.Match) -> str:
        url = m.group('url')
        if "/turbopack-" in url.lower():
            return m.group(0)
        return f"{m.group('attr')}{url}?v={v}{m.group('end')}"

    return CHUNK_RE.sub(_repl, s)


def main() -> None:
    v = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    changed = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in {"node_modules", ".git", "backups"}]
        for fn in filenames:
            if not fn.lower().endswith((".html", ".htm")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                s = open(p, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                continue

            if "/static/chunks/" not in s:
                continue

            s2 = patch_html(s, v)
            if s2 != s:
                open(p, "w", encoding="utf-8", newline="").write(s2)
                changed.append(os.path.relpath(p, ROOT))

    print(f"CACHEBUST_VERSION {v}")
    print(f"PATCHED_HTML {len(changed)}")
    for x in changed[:80]:
        print(x)
    if len(changed) > 80:
        print("...")


if __name__ == "__main__":
    main()
