"""Report strategy tooltip description coverage vs active picks (local JSON)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def norm_text(v):
    return (v if v is not None else "").strip()


def norm_key(v: str) -> str:
    t = norm_text(v).lower()
    t = re.sub(r"[^a-z0-9]+", "_", t)
    return re.sub(r"^_+|_+$", "", t)


def humanize_key(v: str) -> str:
    n = norm_key(v)
    if not n:
        return ""
    parts = [p for p in n.split("_") if p]
    out = []
    for p in parts:
        if len(p) <= 3:
            out.append(p.upper())
        else:
            out.append(p[0].upper() + p[1:])
    return " ".join(out)


def parse_strategy_descriptions_from_template(html: str) -> dict[str, str]:
    m = re.search(r"const _STRATEGY_DESCRIPTIONS = \{([\s\S]*?)\n\};", html)
    if not m:
        raise SystemExit("Could not find _STRATEGY_DESCRIPTIONS in template.html")
    block = m.group(1)
    desc_map: dict[str, str] = {}
    for km in re.finditer(
        r"'([^']+)'\s*:\s*'((?:\\'|[^'])*)'", block
    ):
        k, d = km.group(1), km.group(2).replace("\\'", "'")
        desc_map[k] = d
    return desc_map


def lookup_strategy_desc(name: str, desc_map: dict[str, str]) -> str:
    raw = norm_text(name)
    normalized = norm_key(raw)
    if not normalized:
        return ""
    if raw in desc_map and desc_map[raw]:
        return desc_map[raw]
    if normalized in desc_map and desc_map[normalized]:
        return desc_map[normalized]
    for key, desc in desc_map.items():
        if norm_key(key) == normalized and desc:
            return desc
    for key, desc in desc_map.items():
        kn = norm_key(key)
        if not kn or not desc:
            continue
        if normalized in kn or kn in normalized:
            return desc
    return ""


def classify(name: str, desc_map: dict[str, str]) -> str:
    desc = lookup_strategy_desc(name, desc_map)
    hum = humanize_key(name)
    if desc and desc != hum:
        return "map"
    low = (name or "").lower()
    if "super signal" in low:
        return "super_narrative"
    if " via " in low:
        return "via_narrative"
    if desc:
        return "humanize_only"
    return "missing"


def main() -> None:
    html = (ROOT / "audit_dashboard" / "template.html").read_text(encoding="utf-8")
    desc_map = parse_strategy_descriptions_from_template(html)
    data_path = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
    d = json.loads(data_path.read_text(encoding="utf-8"))
    active = d.get("picks", {}).get("active", [])
    strats = sorted({norm_text(x.get("strategy")) for x in active if x.get("strategy")})

    by_cat: dict[str, list[str]] = {
        "map": [],
        "super_narrative": [],
        "via_narrative": [],
        "humanize_only": [],
        "missing": [],
    }
    for s in strats:
        by_cat[classify(s, desc_map)].append(s)

    print("Active picks:", len(active), "| Unique strategies:", len(strats))
    for cat in ("map", "super_narrative", "via_narrative", "humanize_only", "missing"):
        rows = by_cat[cat]
        print(f"\n== {cat} ({len(rows)}) ==")
        for r in rows:
            print(" ", r)


if __name__ == "__main__":
    main()
