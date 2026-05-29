#!/usr/bin/env python3
"""Build a consolidated summary HTML page from the multi-agent
*DOC*MAY292026*.MD documents, and inject/refresh a brief linking entry into
updates/index.html.

Idempotent: re-run as new DOC files land (monitor cadence). It rewrites the
summary page from scratch and replaces the index.html entry between marker
comments, so it never duplicates.

  python tools/build_doc_summary_page.py            # build page + update index entry
  python tools/build_doc_summary_page.py --page-only

Output:
  updates/2026-05-29-multi-agent-doc-summary.html
  updates/index.html  (entry between DOC_SUMMARY_ENTRY markers, above the
                       INCIDENTS-ENHANCEMENTS auto-block)
"""
from __future__ import annotations
import glob
import html
import os
import re
import sys
from datetime import datetime, timezone

try:
    import markdown as _md
except ImportError:
    _md = None

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(REPO, "updates", "2026-05-29-multi-agent-doc-summary.html")
INDEX = os.path.join(REPO, "updates", "index.html")
PAGE_URL = "https://findtorontoevents.ca/updates/2026-05-29-multi-agent-doc-summary.html"
ENTRY_START = "<!-- DOC_SUMMARY_ENTRY:START -->"
ENTRY_END = "<!-- DOC_SUMMARY_ENTRY:END -->"
INSERT_ANCHOR = "<!-- INSERT NEW ENTRY BELOW THIS LINE -->"

AGENT_LABELS = {
    "CLAUDE": "Claude", "QWEN": "Qwen", "KILOCODE": "Kilo Code",
    "FREEBUFF": "Freebuff", "GROK": "Grok", "CURSOR": "Cursor", "GEMINI": "Gemini",
}


def _docs() -> list[dict]:
    paths = []
    for p in glob.glob(os.path.join(REPO, "*.md")) + glob.glob(os.path.join(REPO, "*.MD")):
        b = os.path.basename(p)
        if "DOC" in b.upper() and "MAY292026" in b.upper():
            paths.append(p)
    paths = sorted(set(paths), key=lambda p: _docnum(os.path.basename(p)))
    out = []
    for p in paths:
        b = os.path.basename(p)
        txt = open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"^#\s+(.+)$", txt, re.M)
        title = m.group(1).strip() if m else b
        out.append({
            "file": b, "path": p, "agent": _agent(b), "docnum": _docnum(b),
            "title": title, "text": txt,
            "brief": _brief(txt), "anchor": re.sub(r"[^a-z0-9]+", "-", b.lower()),
            "mtime": datetime.fromtimestamp(os.path.getmtime(p), timezone.utc),
        })
    return out


def _agent(fname: str) -> str:
    tok = fname.split("_", 1)[0].upper()
    return AGENT_LABELS.get(tok, tok.title())


def _docnum(fname: str) -> int:
    m = re.search(r"DOC(\d+)", fname.upper())
    return int(m.group(1)) if m else 999


def _brief(txt: str) -> str:
    """First substantive sentence/line for the index summary."""
    for ln in txt.splitlines():
        s = ln.strip().lstrip("#* -").strip()
        if len(s) > 30 and not s.startswith("**") and not s.startswith("|"):
            return s[:240]
    return "Session updates document."


def _md_to_html(text: str) -> str:
    if _md is not None:
        return _md.markdown(text, extensions=["fenced_code", "tables", "sane_lists"])
    return "<pre>" + html.escape(text) + "</pre>"


def build_page(docs: list[dict]) -> str:
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    toc = "\n".join(
        f'<li><a href="#{d["anchor"]}">{html.escape(d["agent"])} · DOC{d["docnum"]}</a> '
        f'<span class="small">— {html.escape(d["title"][:80])}</span></li>'
        for d in docs
    )
    sections = []
    for d in docs:
        sections.append(
            f'<section id="{d["anchor"]}" class="doc">\n'
            f'  <h2>{html.escape(d["agent"])} <span class="badge">DOC{d["docnum"]}</span> '
            f'<span class="small">{html.escape(d["file"])} · {d["mtime"].strftime("%Y-%m-%d %H:%M UTC")}</span></h2>\n'
            f'  <div class="md">{_md_to_html(d["text"])}</div>\n'
            f'</section>'
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Multi-Agent Session Updates — 2026-05-29</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
 *{{box-sizing:border-box}} body{{font-family:-apple-system,system-ui,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;background:#0a0a0f;color:#e6e6f0;line-height:1.55}}
 h1{{font-size:24px}} h2{{font-size:18px;border-bottom:1px solid rgba(255,255,255,0.12);padding-bottom:6px;margin-top:34px;color:#cbd5e1}}
 h3{{font-size:14px;color:#a0a0b0}} a{{color:#60a5fa;text-decoration:none}} a:hover{{text-decoration:underline}}
 code{{background:rgba(255,255,255,0.07);padding:1px 5px;border-radius:3px;font-size:12px}}
 pre{{background:rgba(255,255,255,0.04);padding:12px;border-radius:8px;overflow:auto;font-size:12px}}
 table{{border-collapse:collapse;font-size:12px;margin:8px 0}} th,td{{border:1px solid rgba(255,255,255,0.1);padding:5px 9px;text-align:left}}
 .small{{font-size:11px;color:#94a3b8;font-weight:400}} .badge{{background:#3b82f6;color:#04111f;padding:1px 7px;border-radius:8px;font-size:11px;font-weight:700}}
 .doc{{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:6px 18px 14px;margin:14px 0}}
 .hero{{text-align:center;padding:26px 16px;background:linear-gradient(135deg,rgba(96,165,250,0.08),rgba(34,197,94,0.08));border:1px solid rgba(96,165,250,0.15);border-radius:12px}}
 .toc{{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);border-radius:8px;padding:10px 16px;margin:16px 0}} .toc li{{margin:3px 0}}
</style></head><body>
<div class="hero"><h1>Multi-Agent Session Updates — 2026-05-29</h1>
<p class="small">Consolidated summaries from the parallel agent fleet (Claude ×N, Qwen, Kilo Code, Freebuff, Grok). Generated {gen} · {len(docs)} document(s).</p>
<p><a href="https://findtorontoevents.ca/updates/">← back to updates</a></p></div>
<div class="toc"><strong>Documents</strong><ul>
{toc}
</ul></div>
{chr(10).join(sections)}
<hr style="border-color:rgba(255,255,255,0.1);margin-top:30px">
<p class="small">Auto-generated by tools/build_doc_summary_page.py from *DOC*MAY292026*.MD. Re-runs as new agent documents land.</p>
</body></html>
"""


def build_index_entry(docs: list[dict]) -> str:
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    by_agent = {}
    for d in docs:
        by_agent.setdefault(d["agent"], []).append(d["docnum"])
    roster = ", ".join(f"{a} ({len(n)})" if len(n) > 1 else a for a, n in sorted(by_agent.items()))
    items = "\n".join(
        f'    <li><strong>{html.escape(d["agent"])} · DOC{d["docnum"]}</strong> — '
        f'<a href="{PAGE_URL}#{d["anchor"]}">{html.escape(d["title"][:90])}</a></li>'
        for d in docs
    )
    return f"""{ENTRY_START}
<div class="update-entry" style="--dot-color: #60a5fa;" data-tags="multi-agent,session,documentation,audit,ci" data-category="meta" data-types="documentation">
  <h3>{gen} — Multi-Agent Session Documentation Round (2026-05-29)</h3>
  <p>{len(docs)} session-summary document(s) from the parallel agent fleet — {html.escape(roster)} — consolidated into one page. Covers AI-tournament data-quality fixes, the GitHub Actions fleet-health remediation (Node 24 bump, masking linter, guardian masked-failure detection, job-health self-commit-loop fix), CI test repair, multi-PR swarm review, and incident/enhancement documentation.</p>
  <ul>
{items}
  </ul>
  <p style="margin:8px 0 0;color:#60a5fa;font-weight:600;">→ <a href="{PAGE_URL}" style="color:#60a5fa;">Full consolidated summary (per-agent sections)</a></p>
</div>
{ENTRY_END}"""


def update_index(entry: str) -> str:
    s = open(INDEX, encoding="utf-8").read()
    if ENTRY_START in s and ENTRY_END in s:
        s = re.sub(re.escape(ENTRY_START) + r".*?" + re.escape(ENTRY_END), entry, s, count=1, flags=re.S)
    elif INSERT_ANCHOR in s:
        s = s.replace(INSERT_ANCHOR, INSERT_ANCHOR + "\n" + entry, 1)
    else:
        raise RuntimeError("No insertion anchor or existing markers in updates/index.html")
    open(INDEX, "w", encoding="utf-8").write(s)
    return s


def main() -> int:
    docs = _docs()
    if not docs:
        print("[doc-summary] no *DOC*MAY292026*.MD files found")
        return 0
    open(PAGE, "w", encoding="utf-8").write(build_page(docs))
    print(f"[doc-summary] wrote {os.path.relpath(PAGE, REPO)} ({len(docs)} docs: " +
          ", ".join(f'{d["agent"]}DOC{d["docnum"]}' for d in docs) + ")")
    if "--page-only" not in sys.argv:
        update_index(build_index_entry(docs))
        print(f"[doc-summary] refreshed entry in {os.path.relpath(INDEX, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
