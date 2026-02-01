import os
import re

ROOT = r"e:\\findtorontoevents.ca"

# Rename label
RENAME_FROM = " Windows Fixer"
RENAME_TO = " Windows Boot Fixer"

# Remove the /findamovie/ menu entry from compiled JS/HTML.
# This targets the common Next/React compiled pattern:
# (0,t.jsxs)("a",{href:"/findamovie/", ... })
# possibly preceded by a comma.
FINDAMOVIE_BLOCK = re.compile(
    r",?\(0,[a-zA-Z0-9_$]+\.jsxs\)\(\"a\",\{href:\"/findamovie/\".*?\}\)",
    re.S,
)

# HTML anchor fallback
FINDAMOVIE_HTML = re.compile(r"<a[^>]*findamovie[^>]*>.*?</a>", re.I | re.S)


def patch_text(s: str) -> str:
    s2 = s.replace(RENAME_FROM, RENAME_TO)
    s2 = s2.replace(">Windows Fixer<", ">Windows Boot Fixer<")
    s2 = FINDAMOVIE_BLOCK.sub("", s2)
    s2 = FINDAMOVIE_HTML.sub("", s2)
    return s2


def main() -> None:
    changed = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in {"node_modules", ".git", "backups"}]
        for fn in filenames:
            low = fn.lower()
            if not (low.endswith(".js") or low.endswith(".html") or low.endswith(".htm")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                s = open(p, "r", encoding="utf-8", errors="ignore").read()
            except Exception:
                continue

            if "windows fixer" not in s.lower() and "findamovie" not in s.lower():
                continue

            s2 = patch_text(s)
            if s2 != s:
                open(p, "w", encoding="utf-8", newline="").write(s2)
                changed.append(os.path.relpath(p, ROOT))

    print(f"PATCHED_FILES {len(changed)}")
    for x in changed[:80]:
        print(x)
    if len(changed) > 80:
        print("...")


if __name__ == "__main__":
    main()
