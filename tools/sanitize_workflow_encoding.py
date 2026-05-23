"""
Rewrite .github/workflows/*.yml as valid UTF-8 and drop YAML-disallowed
control characters (Unicode Cc except tab/LF/CR).

Invalid UTF-8 sequences (common after broken emoji / copy-paste) are replaced
via errors='replace', then U+FFFD is removed.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path


def load_text(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def sanitize(s: str) -> str:
    s = s.replace("\ufffd", "")
    out: list[str] = []
    for c in s:
        if c in "\t\n\r":
            out.append(c)
            continue
        if unicodedata.category(c) == "Cc":
            continue
        out.append(c)
    return "".join(out)


def main() -> None:
    root = Path(__file__).resolve().parent.parent / ".github" / "workflows"
    n = 0
    for p in sorted(root.glob("*.yml")):
        raw = p.read_bytes()
        text = load_text(raw)
        clean = sanitize(text)
        new_bytes = clean.encode("utf-8")
        if new_bytes != raw:
            p.write_bytes(new_bytes)
            print("sanitized", p.name)
            n += 1
    print("total files rewritten:", n)


if __name__ == "__main__":
    main()
