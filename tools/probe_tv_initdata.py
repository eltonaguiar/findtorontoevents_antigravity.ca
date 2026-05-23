"""Probe window.initData payload from a cached TV profile HTML."""
import re
import json
import sys
from pathlib import Path


def extract_initdata_blocks(html: str) -> list:
    """Return list of (start_offset, parsed_obj) for each window.initData = {...};"""
    out = []
    for m in re.finditer(r"window\.initData\s*=\s*\{", html):
        start = m.end() - 1
        depth = 0
        in_str = False
        esc = False
        end = None
        for i in range(start, len(html)):
            c = html[i]
            if esc:
                esc = False
                continue
            if c == "\\" and in_str:
                esc = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            continue
        raw = html[start:end]
        try:
            obj = json.loads(raw)
            out.append((start, obj, len(raw)))
        except Exception as e:
            out.append((start, {"_parse_error": str(e), "_head": raw[:200]}, len(raw)))
    return out


def main():
    p = Path(sys.argv[1] if len(sys.argv) > 1
             else "reports/data/leap_profiles_html/MarketMaverick007/profile.html")
    html = p.read_text(encoding="utf-8", errors="ignore")
    print(f"File: {p}  size: {len(html):,}")
    blocks = extract_initdata_blocks(html)
    print(f"initData blocks found: {len(blocks)}")
    for i, (start, obj, raw_len) in enumerate(blocks):
        print(f"\n--- block {i} @ {start}  raw={raw_len:,} chars ---")
        if isinstance(obj, dict):
            keys = sorted(obj.keys())
            print(f"top-level keys ({len(keys)}): {keys[:30]}")
            for k in keys[:30]:
                v = obj[k]
                if isinstance(v, dict):
                    inner = sorted(v.keys())
                    print(f"  {k}.keys ({len(inner)}): {inner[:15]}")
                elif isinstance(v, list):
                    print(f"  {k}: list[{len(v)}]")
                    if v and isinstance(v[0], dict):
                        print(f"     [0].keys: {sorted(v[0].keys())[:12]}")
                else:
                    sv = str(v)
                    if len(sv) > 80:
                        sv = sv[:80] + "..."
                    print(f"  {k}: {sv}")
        else:
            print(f"  obj: {obj}")


if __name__ == "__main__":
    main()
