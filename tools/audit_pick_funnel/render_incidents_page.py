"""
Render two artifacts from the live INCIDENT_* / ENHANCEMENT_* tables:

1. audit_dashboard/incidents.html — full dashboard page (filterable, dark theme)
2. JSON sidecar audit_dashboard/data/incidents_enhancements_feed.json
3. Inject the latest 10 OPEN P0/P1 incidents + 5 high-impact enhancements
   into updates/index.html under a fresh "INCIDENTS + ENHANCEMENTS" section,
   colored distinctly from the existing update-entry cards (gold/red border).

Idempotent. Updates/index.html block is delimited by HTML comment markers
so reruns replace just that section.
"""
from __future__ import annotations
import json, os, re
from datetime import datetime, timezone
from pathlib import Path
import pymysql

REPO = Path(__file__).resolve().parents[2]
OUT_HTML = REPO / "audit_dashboard" / "incidents.html"
OUT_JSON = REPO / "audit_dashboard" / "data" / "incidents_enhancements_feed.json"
UPDATES_PAGE = REPO / "updates" / "index.html"

CLASSES = ["OVERALL", "STOCKS", "ETFS", "CRYPTO", "FOREX", "COMMODITIES", "BONDS", "FUTURES", "PENNY"]

INJECTION_START = "<!-- AUTO-INJECTED:INCIDENTS-ENHANCEMENTS:START -->"
INJECTION_END = "<!-- AUTO-INJECTED:INCIDENTS-ENHANCEMENTS:END -->"


def fetch_all():
    conn = pymysql.connect(
        host=os.environ.get("DB_HOST_STOCKS", "mysql.50webs.com"),
        user="ejaguiar1_stocks",
        password=os.environ["DB_PASS_STOCKS"],
        database=os.environ["DB_NAME_STOCKS"],
        port=3306, connect_timeout=20,
        cursorclass=pymysql.cursors.DictCursor,
    )
    incidents = {}
    enhancements = {}
    with conn.cursor() as cur:
        for cls in CLASSES:
            cur.execute(f"SELECT * FROM INCIDENT_{cls} ORDER BY FIELD(severity,'P0','P1','P2','P3','INFO'), created_at DESC")
            incidents[cls] = list(cur.fetchall())
            cur.execute(f"SELECT * FROM ENHANCEMENT_{cls} ORDER BY FIELD(expected_impact,'HIGH','MEDIUM','LOW','UNKNOWN'), FIELD(effort,'S','M','L','XL'), created_at DESC")
            enhancements[cls] = list(cur.fetchall())
    conn.close()
    return incidents, enhancements


def esc(s):
    if s is None: return ""
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&#39;")


def sev_badge(s):
    colors = {"P0":"#ef4444", "P1":"#f59e0b", "P2":"#3b82f6", "P3":"#6b7280", "INFO":"#22c55e"}
    c = colors.get(s, "#6b7280")
    return f'<span style="background:{c};color:#0a0a0f;padding:1px 7px;border-radius:8px;font-size:10px;font-weight:700">{esc(s)}</span>'


def status_badge(s):
    colors = {"OPEN":"#ef4444","TRIAGED":"#f59e0b","IN_PROGRESS":"#3b82f6","RESOLVED":"#22c55e","WONTFIX":"#6b7280","DUPLICATE":"#6b7280",
              "BACKLOG":"#6b7280","VALIDATED":"#fbbf24","ACCEPTED":"#3b82f6","IMPLEMENTED":"#22c55e","REJECTED":"#6b7280","SUPERSEDED":"#6b7280"}
    c = colors.get(s, "#6b7280")
    return f'<span style="background:rgba({int(c[1:3],16)},{int(c[3:5],16)},{int(c[5:7],16)},0.18);color:{c};border:1px solid {c};padding:1px 7px;border-radius:8px;font-size:10px;font-weight:600">{esc(s)}</span>'


def render_links(row):
    bits = []
    if row.get("link_md_path"):
        p = row["link_md_path"]
        bits.append(f'<a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/blob/main/{p}">📄 doc</a>')
    if row.get("link_url"):
        bits.append(f'<a href="{esc(row["link_url"])}">🔗 page</a>')
    if row.get("link_github_ref"):
        ref = row["link_github_ref"]
        # commit shas (7+ hex chars) get linked to /commit/, PR/issue refs to /pull or /issues
        for r in ref.split(","):
            r = r.strip()
            if re.match(r"^[0-9a-f]{7,40}$", r):
                bits.append(f'<a href="https://github.com/eltonaguiar/findtorontoevents_antigravity.ca/commit/{r}">⎌ {r[:7]}</a>')
            else:
                bits.append(f'<code>{esc(r)}</code>')
    return " · ".join(bits) if bits else '<span style="color:#4b5563">—</span>'


def render_table_section(title, rows_by_class, is_incident=True):
    out = [f'<h2 id="{title.lower().replace(" ","-")}">{title}</h2>']
    total = sum(len(v) for v in rows_by_class.values())
    out.append(f'<div class="small">Total: <strong>{total}</strong> across {sum(1 for v in rows_by_class.values() if v)} asset classes</div>')
    for cls in CLASSES:
        rows = rows_by_class.get(cls, [])
        if not rows: continue
        out.append(f'<details {"open" if cls in ("OVERALL","STOCKS","CRYPTO") else ""}><summary><strong>{cls}</strong> <span class="small">({len(rows)})</span></summary>')
        out.append('<table class="lb"><thead><tr>')
        if is_incident:
            out.append('<th>Sev</th><th>Status</th><th>Title</th><th>Component</th><th>Recommended fix</th><th>Reporter</th><th>Links</th>')
        else:
            out.append('<th>Impact</th><th>Effort</th><th>Status</th><th>Cat</th><th>Title</th><th>Success metric</th><th>Proposed by</th><th>Links</th>')
        out.append('</tr></thead><tbody>')
        for r in rows:
            if is_incident:
                out.append(f'<tr><td>{sev_badge(r["severity"])}</td><td>{status_badge(r["status"])}</td>'
                           f'<td><strong>{esc(r["title"])}</strong><div class="small" style="color:#9ca3af;margin-top:3px">{esc((r.get("description") or "")[:300])}{"…" if r.get("description") and len(r["description"])>300 else ""}</div></td>'
                           f'<td class="small">{esc(r.get("affected_component") or "")}</td>'
                           f'<td class="small">{esc((r.get("recommended_fix") or "")[:200])}</td>'
                           f'<td class="small">{esc(r.get("reported_by") or "")}</td>'
                           f'<td class="small">{render_links(r)}</td></tr>')
            else:
                out.append(f'<tr><td>{sev_badge(r["expected_impact"])}</td><td><span class="small">{esc(r["effort"])}</span></td>'
                           f'<td>{status_badge(r["status"])}</td>'
                           f'<td class="small">{esc(r["category"])}</td>'
                           f'<td><strong>{esc(r["title"])}</strong><div class="small" style="color:#9ca3af;margin-top:3px">{esc((r.get("description") or "")[:300])}{"…" if r.get("description") and len(r["description"])>300 else ""}</div></td>'
                           f'<td class="small">{esc(r.get("success_metric") or "")}</td>'
                           f'<td class="small">{esc(r.get("proposed_by") or "")}</td>'
                           f'<td class="small">{render_links(r)}</td></tr>')
        out.append('</tbody></table></details>')
    return "\n".join(out)


def render_html(incidents, enhancements, generated_at):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Incidents + Enhancements · findtorontoevents.ca/audit</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 1500px; margin: 24px auto; padding: 0 16px; background: #0a0a0f; color: #e6e6f0; line-height: 1.5; }}
  h1 {{ margin-bottom: 4px; font-size: 22px; }}
  h2 {{ font-size: 15px; padding-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.1); color: #a0a0b0; margin: 28px 0 10px; }}
  a {{ color: #60a5fa; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  code {{ background: rgba(255,255,255,0.06); padding: 1px 5px; border-radius: 3px; font-size: 11px; }}
  .small {{ font-size: 11px; color: #a0a0b0; }}
  .nav {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
  .nav a {{ background: rgba(255,255,255,0.05); padding: 6px 14px; border-radius: 6px; font-size: 13px; border: 1px solid rgba(255,255,255,0.08); }}
  table.lb {{ width: 100%; border-collapse: collapse; font-size: 12px; margin: 8px 0; }}
  table.lb th {{ background: rgba(255,255,255,0.04); font-weight: 700; padding: 6px 8px; text-align: left; border-bottom: 2px solid rgba(255,255,255,0.1); font-size: 10px; color: #a0a0b0; text-transform: uppercase; letter-spacing: 0.5px; }}
  table.lb td {{ padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.05); vertical-align: top; }}
  table.lb tr:hover td {{ background: rgba(96,165,250,0.06); }}
  details {{ margin: 12px 0; background: rgba(255,255,255,0.02); border-radius: 8px; padding: 8px 12px; border: 1px solid rgba(255,255,255,0.06); }}
  details summary {{ cursor: pointer; font-size: 13px; padding: 4px 0; }}
  details[open] summary {{ border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 6px; padding-bottom: 6px; }}
  .hero {{ text-align: center; padding: 22px 16px 16px; background: linear-gradient(135deg,rgba(239,68,68,0.10),rgba(245,158,11,0.10)); border: 1px solid rgba(245,158,11,0.3); border-radius: 12px; margin-bottom: 18px; }}
  .hero h1 {{ font-size: 24px; }}
</style></head><body>

<nav class="nav">
  <a href="/audit/">← Main Audit</a>
  <a href="/audit/ai-tournament.html">AI Tournament</a>
  <a href="/audit/pick_funnel.html">Pick Funnel</a>
  <a href="/updates/">Updates</a>
</nav>

<div class="hero">
  <h1>🐛 Incidents + 🚀 Enhancements per Asset Class</h1>
  <p class="small">Live from <code>INCIDENT_*</code> and <code>ENHANCEMENT_*</code> tables in <code>ejaguiar1_stocks</code>. Auto-regenerated nightly. Last refresh: <strong>{esc(generated_at)}</strong></p>
</div>

{render_table_section("Incidents (bugs / data-quality issues / outages)", incidents, is_incident=True)}
{render_table_section("Enhancements (scoring / gate / data-feed / UI proposals)", enhancements, is_incident=False)}

<footer style="margin-top:40px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.07);color:#4b5563;font-size:11px">
  Generated by <code>tools/audit_pick_funnel/render_incidents_page.py</code> via GH Actions workflow <code>incidents-enhancements-nightly.yml</code>. Source: <code>vw_all_incidents</code> + <code>vw_all_enhancements</code> in <code>ejaguiar1_stocks</code>.
</footer>
</body></html>"""


def render_updates_injection(incidents, enhancements, generated_at):
    """Pick top P0/P1 OPEN incidents + HIGH-impact enhancements; render distinct-color cards."""
    flat_inc = [r for cls in CLASSES for r in incidents.get(cls, [])]
    flat_enh = [r for cls in CLASSES for r in enhancements.get(cls, [])]
    top_inc = [r for r in flat_inc if r["severity"] in ("P0","P1") and r["status"] in ("OPEN","TRIAGED","IN_PROGRESS")][:10]
    top_enh = [r for r in flat_enh if r["expected_impact"] == "HIGH" and r["status"] in ("BACKLOG","VALIDATED","ACCEPTED")][:5]

    parts = [INJECTION_START, '''
<!-- Auto-generated section — do not hand-edit between START/END markers.
     Source: ejaguiar1_stocks INCIDENT_* / ENHANCEMENT_* tables.
     Distinct visual identity via the .incident-card / .enhancement-card classes
     and the orange/green left border vs the default update-entry cards. -->
<style>
  .ie-section { margin: 28px 0; padding: 18px; background: linear-gradient(135deg, rgba(245,158,11,0.06), rgba(34,197,94,0.06)); border: 1px solid rgba(245,158,11,0.25); border-radius: 12px; }
  .ie-section > h2 { margin: 0 0 8px; font-size: 18px; color: #f59e0b; }
  .ie-section > p.intro { color: #94a3b8; font-size: 13px; margin-bottom: 14px; }
  .incident-card { background: rgba(239,68,68,0.04); border-left: 4px solid #ef4444; border-radius: 0 8px 8px 0; padding: 10px 14px; margin: 8px 0; font-size: 13px; }
  .incident-card.sev-P1 { border-left-color: #f59e0b; background: rgba(245,158,11,0.04); }
  .enhancement-card { background: rgba(34,197,94,0.05); border-left: 4px solid #22c55e; border-radius: 0 8px 8px 0; padding: 10px 14px; margin: 8px 0; font-size: 13px; }
  .ie-card-meta { font-size: 11px; color: #9ca3af; margin-top: 3px; }
  .ie-card a { color: #93c5fd; text-decoration: none; font-weight: 600; }
  .ie-card a:hover { text-decoration: underline; color: #60a5fa; }
  .ie-class { display: inline-block; background: rgba(96,165,250,0.18); color: #93c5fd; padding: 1px 6px; border-radius: 6px; font-size: 10px; font-weight: 700; margin-right: 5px; }
</style>
<div class="ie-section">
  <h2>🐛 Open Incidents + 🚀 Top Enhancements (auto-synced from /audit DB)</h2>
  <p class="intro">Live from the <code>INCIDENT_*</code> + <code>ENHANCEMENT_*</code> per-asset-class tables in <code>ejaguiar1_stocks</code>. <strong>Refreshed: ''' + esc(generated_at) + '''.</strong> Full list: <a href="/audit/incidents.html">/audit/incidents.html</a>.</p>
''']

    if top_inc:
        parts.append('<h3 style="color:#ef4444;font-size:14px;margin:14px 0 6px">Open P0/P1 Incidents</h3>')
        for r in top_inc:
            sev_cls = f"sev-{r['severity']}"
            parts.append(f'''  <div class="incident-card ie-card {sev_cls}">
    <span class="ie-class">{esc(r["asset_class"])}</span> <strong>{esc(r["title"])}</strong>
    <div class="ie-card-meta">{esc(r["severity"])} · {esc(r["status"])} · component: <code>{esc(r.get("affected_component") or "—")}</code> · reporter: {esc(r.get("reported_by") or "")} · <a href="/audit/incidents.html#incidents">view in full table →</a></div>
  </div>''')

    if top_enh:
        parts.append('<h3 style="color:#22c55e;font-size:14px;margin:14px 0 6px">Top HIGH-impact Enhancements</h3>')
        for r in top_enh:
            parts.append(f'''  <div class="enhancement-card ie-card">
    <span class="ie-class">{esc(r["asset_class"])}</span> <strong>{esc(r["title"])}</strong>
    <div class="ie-card-meta">Impact {esc(r["expected_impact"])} · effort {esc(r["effort"])} · status {esc(r["status"])} · category {esc(r["category"])} · <a href="/audit/incidents.html#enhancements">view in full table →</a></div>
  </div>''')
    parts.append('</div>')
    parts.append(INJECTION_END)
    return "\n".join(parts)


def inject_into_updates(html_block):
    if not UPDATES_PAGE.exists():
        print(f"[render] skip updates injection — {UPDATES_PAGE} missing")
        return False
    src = UPDATES_PAGE.read_text(encoding="utf-8")
    if INJECTION_START in src and INJECTION_END in src:
        new = re.sub(
            re.escape(INJECTION_START) + ".*?" + re.escape(INJECTION_END),
            html_block.replace("\\", "\\\\"),  # escape backslashes for re.sub replacement
            src, flags=re.DOTALL)
    else:
        # Find <main> opening tag and inject right after; fallback to before </body>
        m = re.search(r"<main[^>]*>", src, re.IGNORECASE)
        if m:
            insertion_point = m.end()
            new = src[:insertion_point] + "\n" + html_block + "\n" + src[insertion_point:]
        else:
            new = src.replace("</body>", html_block + "\n</body>", 1)
    UPDATES_PAGE.write_text(new, encoding="utf-8")
    return True


def main():
    incidents, enhancements = fetch_all()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = render_html(incidents, enhancements, generated_at)
    OUT_HTML.write_text(html, encoding="utf-8")
    feed = {
        "generated_at": generated_at,
        "incidents": {k: [{kk:(str(vv) if hasattr(vv,'isoformat') else vv) for kk,vv in r.items()} for r in v] for k,v in incidents.items()},
        "enhancements": {k: [{kk:(str(vv) if hasattr(vv,'isoformat') else vv) for kk,vv in r.items()} for r in v] for k,v in enhancements.items()},
        "totals": {"incidents": sum(len(v) for v in incidents.values()), "enhancements": sum(len(v) for v in enhancements.values())},
    }
    OUT_JSON.write_text(json.dumps(feed, indent=2, default=str), encoding="utf-8")
    block = render_updates_injection(incidents, enhancements, generated_at)
    injected = inject_into_updates(block)
    print(f"[render] wrote {OUT_HTML.relative_to(REPO)} ({len(html):,} bytes)")
    print(f"[render] wrote {OUT_JSON.relative_to(REPO)} ({OUT_JSON.stat().st_size:,} bytes)")
    print(f"[render] updates/index.html injection: {'OK' if injected else 'SKIPPED'}")
    print(f"[render] totals: {feed['totals']['incidents']} incidents · {feed['totals']['enhancements']} enhancements")


if __name__ == "__main__":
    main()
