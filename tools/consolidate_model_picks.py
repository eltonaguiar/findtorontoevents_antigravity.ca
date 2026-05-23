"""Consolidate all model_picks_research_*.md reports into one master MD.

Walks reports/model_picks_research_*.md, parses by section, aggregates
per (asset_class, model). Output: reports/MODEL_PICKS_CONSOLIDATED.md
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "reports"


def parse_md(md: str) -> dict[str, dict[str, dict]]:
    """Return {asset_class: {model_name: {role, picks, factors, data, swing, short}}}."""
    out: dict = {}
    current_class = None
    current_model = None
    current_section = None
    for line in md.splitlines():
        m_class = re.match(r"^## ([A-Z]+)\s*$", line)
        if m_class and m_class.group(1) not in ("Live", "Per", "Consensus"):
            current_class = m_class.group(1)
            if current_class not in out:
                out[current_class] = {}
            current_model = None
            current_section = None
            continue
        m_model = re.match(r"^### ([^\s]+)\s*[—-]\s*(.+?)\s*\(elapsed", line)
        if m_model and current_class:
            current_model = m_model.group(1)
            role = m_model.group(2).strip()
            out[current_class].setdefault(current_model, {
                "role": role, "picks": [], "factors": [],
                "data": [], "swing": "", "short": "",
            })
            current_section = None
            continue
        if current_class and current_model:
            if line.startswith("**Top picks:**"):
                current_section = "picks"
            elif line.startswith("**Factors Used:**"):
                current_section = "factors"
            elif line.startswith("**Data Points To Fetch:**"):
                current_section = "data"
            elif line.startswith("**Swing Trade Setup:**"):
                out[current_class][current_model]["swing"] = line.split("**Swing Trade Setup:**", 1)[1].strip()
                current_section = None
            elif line.startswith("**Short Term Setup:**"):
                out[current_class][current_model]["short"] = line.split("**Short Term Setup:**", 1)[1].strip()
                current_section = None
            elif line.startswith("- ") and current_section:
                if current_section == "picks":
                    out[current_class][current_model]["picks"].append(line[2:].strip())
                elif current_section in ("factors", "data"):
                    out[current_class][current_model][current_section].append(line[2:].strip())
    return out


def merge(per_file: list[dict]) -> dict:
    """Merge multiple parses; later overrides earlier for same (class, model)."""
    out: dict = {}
    for p in per_file:
        for ac, models in p.items():
            out.setdefault(ac, {})
            for m, data in models.items():
                if data["picks"] or data["factors"]:  # only keep useful entries
                    out[ac][m] = data
    return out


def write_master(merged: dict, out_path: Path) -> None:
    lines = [
        "# Multi-Model Picks per Asset Class — Consolidated",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "Combines all `reports/model_picks_research_*.md` runs (REST cloud + Ollama Cloud + local).",
        "Each model: top picks + factors used + data points + swing/short setups.",
        "",
        "## Asset classes covered",
        "",
    ]
    for ac in sorted(merged.keys()):
        n = len(merged[ac])
        lines.append(f"- **{ac}** — {n} model verdicts")
    lines.append("")

    for ac in ("CRYPTO", "EQUITY", "FOREX", "COMMODITY", "ETF", "BOND"):
        if ac not in merged:
            continue
        lines += [f"## {ac}", ""]
        for model in sorted(merged[ac].keys()):
            d = merged[ac][model]
            lines.append(f"### {model} — _{d['role']}_")
            if d["picks"]:
                lines.append("**Top picks:**")
                for p in d["picks"]:
                    lines.append(f"- {p}")
            if d["factors"]:
                lines.append("**Factors:** " + "; ".join(d["factors"][:5]))
            if d["data"]:
                lines.append("**Data points:** " + "; ".join(d["data"][:5]))
            if d["swing"]:
                lines.append(f"**Swing:** {d['swing']}")
            if d["short"]:
                lines.append(f"**Short-term:** {d['short']}")
            lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_path.relative_to(REPO)}")


def main() -> None:
    files = sorted(REPORTS.glob("model_picks_research_*.md"))
    if not files:
        print("no reports found")
        return
    print(f"merging {len(files)} reports")
    parses = []
    for f in files:
        parses.append(parse_md(f.read_text(encoding="utf-8")))
    merged = merge(parses)
    out_path = REPORTS / "MODEL_PICKS_CONSOLIDATED.md"
    write_master(merged, out_path)


if __name__ == "__main__":
    main()
