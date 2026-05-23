"""Generate an up-to-date inventory of all GitHub Actions workflows.

For each .github/workflows/*.yml: records triggers, jobs, the script files each
job runs, and any JSON output paths the workflow reads/writes/commits. Writes
docs/GITHUB_ACTIONS_INVENTORY_2026-05-15.md.
"""
import datetime
import re
from pathlib import Path

WF_DIR = Path(".github/workflows")
OUT = Path("docs/GITHUB_ACTIONS_INVENTORY_2026-05-15.md")

wf_files = sorted(
    [p for p in WF_DIR.iterdir() if p.suffix in (".yml", ".yaml")],
    key=lambda p: p.name.lower(),
)

SCRIPT_RE = re.compile(r"([\w./-]+\.(?:py|sh|js|ps1))")
JSON_RE = re.compile(r"([\w./-]+\.json)")


def parse(p: Path) -> dict:
    txt = p.read_text(encoding="utf-8", errors="replace")
    name_m = re.search(r"^name:\s*(.+)$", txt, flags=re.MULTILINE)
    name = name_m.group(1).strip().strip("'\"") if name_m else p.stem
    # triggers: keys under top-level `on:`
    triggers: list[str] = []
    on_m = re.search(r"^on:\s*(.*)$", txt, flags=re.MULTILINE)
    if on_m:
        inline = on_m.group(1).strip()
        if inline and not inline.startswith("#"):
            triggers = [t.strip() for t in inline.strip("[]").split(",") if t.strip()]
        else:
            block = txt[on_m.end():]
            for ln in block.splitlines():
                if re.match(r"^\S", ln):
                    break
                km = re.match(r"^  (\w[\w_-]*):", ln)
                if km:
                    triggers.append(km.group(1))
    cron = re.findall(r"cron:\s*['\"]([^'\"]+)['\"]", txt)
    jobs: list[str] = []
    js = re.search(r"^jobs:\s*$", txt, flags=re.MULTILINE)
    if js:
        for ln in txt[js.end():].splitlines():
            jm = re.match(r"^  (\w[\w_-]*):\s*$", ln)
            if jm:
                jobs.append(jm.group(1))
    scripts = sorted({s for s in SCRIPT_RE.findall(txt)
                      if not s.startswith((".github/", "actions/"))
                      and "/" in s or s.endswith((".py", ".sh", ".ps1"))})
    jsons = sorted(set(JSON_RE.findall(txt)))
    return {
        "file": p.name, "name": name, "triggers": triggers, "cron": cron,
        "jobs": jobs, "scripts": scripts, "jsons": jsons,
    }


parsed = [parse(p) for p in wf_files]
today = datetime.date(2026, 5, 15).isoformat()

L: list[str] = [
    "# GitHub Actions — Workflow Inventory",
    "",
    f"_Last updated {today}_",
    "",
    f"All **{len(parsed)}** workflows under `.github/workflows/`. For each: "
    "triggers, cron schedules, jobs, the script files it runs, and JSON "
    "artifacts it reads/writes. Regenerate with `tools/_gen_gh_actions_doc.py`.",
    "",
    "## Index",
    "",
]
for w in parsed:
    trg = ",".join(w["triggers"]) or "—"
    L.append(f"- [`{w['file']}`](#{w['file'].replace('.', '').lower()}) — {w['name']} · {trg}")
L.append("")
L.append("## Workflows")
L.append("")
for w in parsed:
    L.append(f"### `{w['file']}`")
    L.append("")
    L.append(f"- **Name:** {w['name']}")
    L.append(f"- **Triggers:** {', '.join(w['triggers']) or '—'}")
    if w["cron"]:
        L.append(f"- **Cron:** {', '.join('`'+c+'`' for c in w['cron'])}")
    L.append(f"- **Jobs:** {', '.join('`'+j+'`' for j in w['jobs']) or '—'}")
    if w["scripts"]:
        shown = w["scripts"][:25]
        more = f" … (+{len(w['scripts'])-25})" if len(w["scripts"]) > 25 else ""
        L.append(f"- **Scripts:** {', '.join('`'+s+'`' for s in shown)}{more}")
    if w["jsons"]:
        shown = w["jsons"][:20]
        more = f" … (+{len(w['jsons'])-20})" if len(w["jsons"]) > 20 else ""
        L.append(f"- **JSON I/O:** {', '.join('`'+j+'`' for j in shown)}{more}")
    L.append("")

OUT.write_text("\n".join(L), encoding="utf-8")
print(f"WROTE {OUT}  ({len(parsed)} workflows, {OUT.stat().st_size:,} bytes)")
