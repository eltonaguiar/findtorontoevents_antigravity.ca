"""
AST-aware code search using ast-grep-py (pip install ast-grep-py).
Usage:
    python tools/ast_search.py "<pattern>" [file_or_dir] [--lang python|js|ts]

Examples:
    python tools/ast_search.py "def \$NAME(\$\$\$):" audit_trail/
    python tools/ast_search.py "pick.get(\$KEY, \$DEFAULT)" alpha_engine/
    python tools/ast_search.py "\$X < 55" audit_trail/quality_gates.py
"""
import sys, os, glob, argparse
from ast_grep_py import SgRoot

LANG_EXT = {"python": [".py"], "js": [".js", ".mjs"], "ts": [".ts", ".tsx"]}


def search_file(path, pattern, lang):
    try:
        src = open(path, encoding="utf-8").read()
    except Exception:
        return []
    root = SgRoot(src, lang).root()
    return [(path, m.range().start.line + 1, m.text()) for m in root.find_all(pattern=pattern)]


def collect_files(target, lang):
    exts = LANG_EXT.get(lang, [".py"])
    if os.path.isfile(target):
        return [target]
    files = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(target, "**", f"*{ext}"), recursive=True))
    return files


def main():
    ap = argparse.ArgumentParser(description="AST-aware code search via ast-grep-py")
    ap.add_argument("pattern", help="ast-grep pattern, e.g. 'def $NAME($$$):'")
    ap.add_argument("target", nargs="?", default=".", help="file or directory to search")
    ap.add_argument("--lang", default="python", choices=list(LANG_EXT), help="language")
    args = ap.parse_args()

    files = collect_files(args.target, args.lang)
    total = 0
    for f in sorted(files):
        for path, line, text in search_file(f, args.pattern, args.lang):
            print(f"{path}:{line}: {text[:120]}")
            total += 1
    print(f"\n{total} match(es) across {len(files)} file(s)")


if __name__ == "__main__":
    main()
