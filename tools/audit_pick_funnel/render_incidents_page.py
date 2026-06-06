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
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo
from pathlib import Path
import pymysql
import re

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
    findings = {}
    with conn.cursor() as cur:
        for cls in CLASSES:
            cur.execute(f"SELECT * FROM INCIDENT_{cls} ORDER BY FIELD(severity,'P0','P1','P2','P3','INFO'), created_at DESC")
            incidents[cls] = list(cur.fetchall())
            cur.execute(f"SELECT * FROM ENHANCEMENT_{cls} ORDER BY FIELD(expected_impact,'HIGH','MEDIUM','LOW','UNKNOWN'), FIELD(effort,'S','M','L','XL'), created_at DESC")
            enhancements[cls] = list(cur.fetchall())
            # FINDING_<CLASS> tables are newer (migration 20260529_finding_tables).
            # Tolerate their absence on environments where the migration hasn't
            # been applied yet, so the renderer doesn't hard-fail on legacy DBs.
            try:
                cur.execute(f"SELECT * FROM FINDING_{cls} ORDER BY FIELD(severity,'P0','P1','P2','P3','NOTEWORTHY','INFO'), created_at_utc DESC")
                findings[cls] = list(cur.fetchall())
            except pymysql.err.ProgrammingError:
                findings[cls] = []
    conn.close()
    return incidents, enhancements, findings


def esc(s):
    if s is None: return ""
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&#39;")


def sev_badge(s):
    # P0=red, P1=amber, P2=yellow, P3=grey, INFO=blue, NOTEWORTHY=teal (matches
    # the FINDINGS spec; incidents still pass INFO/P0..P3 via the existing path).
    colors = {"P0":"#ef4444", "P1":"#f59e0b", "P2":"#eab308", "P3":"#6b7280", "INFO":"#3b82f6", "NOTEWORTHY":"#14b8a6"}
    c = colors.get(s, "#6b7280")
    return f'<span style="background:{c};color:#0a0a0f;padding:1px 7px;border-radius:8px;font-size:10px;font-weight:700">{esc(s)}</span>'


def target_badge(row):
    """Render target_release with EST timeline badge. Green=on-track, yellow=due-soon, red=overdue.
    NOTE: date.today() uses system time, not EST. Near midnight UTC the days-left count
    may be off by 1, which is acceptable for a dashboard badge."""
    tr = row.get("target_release")
    if not tr:
        return '<span style="color:#4b5563;font-size:10px">—</span>'
    # Parse date from "YYYY-MM-DD HH:MM EST" format
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(tr))
    if not m:
        return f'<span style="font-size:10px;color:#9ca3af">{esc(str(tr))}</span>'
    try:
        target_date = date.fromisoformat(m.group(1))
        today = date.today()
        days_left = (target_date - today).days
        if days_left < 0:
            color, bg, label = "#ef4444", "rgba(239,68,68,0.15)", f"OVERDUE {abs(days_left)}d"
        elif days_left <= 3:
            color, bg, label = "#f59e0b", "rgba(245,158,11,0.15)", f"due in {days_left}d"
        elif days_left <= 7:
            color, bg, label = "#fbbf24", "rgba(251,191,36,0.10)", f"in {days_left}d"
        else:
            color, bg, label = "#22c55e", "rgba(34,197,94,0.10)", f"in {days_left}d"
        return f'<span style="background:{bg};color:{color};border:1px solid {color};padding:2px 7px;border-radius:8px;font-size:10px;font-weight:600;white-space:nowrap">{esc(str(tr))}</span><div style="font-size:10px;color:{color};margin-top:2px">{label}</div>'
    except (ValueError, TypeError):
        return f'<span style="font-size:10px;color:#9ca3af">{esc(str(tr))}</span>'


def created_est(row):
    """Render created_at as EST/EDT. Prefer date_est/time_est columns when available;
    fall back to converting created_at (UTC-naive) to America/New_York."""
    de = row.get("date_est")
    te = row.get("time_est")
    if de and te:
        # time_est already contains %Z (e.g. "21:06 EST"), so don't append another
        return f'<span class="small" style="white-space:nowrap">{esc(str(de))} {esc(str(te))}</span>'
    ts = row.get("created_at")
    if not ts:
        return '<span style="color:#4b5563;font-size:10px">—</span>'
    try:
        if isinstance(ts, str):
            # MySQL DATETIME strings use space separator, not T
            dt = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        else:
            dt = ts
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        est = dt.astimezone(ZoneInfo("America/New_York"))
        return f'<span class="small" style="white-space:nowrap" title="{esc(str(ts))} UTC">{est.strftime("%Y-%m-%d %H:%M %Z")}</span>'
    except (ValueError, TypeError):
        return f'<span class="small">{esc(str(ts))}</span>'


def status_badge(s):
    colors = {"OPEN":"#ef4444","TRIAGED":"#f59e0b","IN_PROGRESS":"#3b82f6","RESOLVED":"#22c55e","WONTFIX":"#6b7280","DUPLICATE":"#6b7280",
              "BACKLOG":"#6b7280","VALIDATED":"#fbbf24","ACCEPTED":"#3b82f6","IMPLEMENTED":"#22c55e","REJECTED":"#6b7280","SUPERSEDED":"#6b7280",
              "INVESTIGATING":"#f59e0b","CONFIRMED":"#a855f7"}
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
            out.append('<th>Sev</th><th>Status</th><th>Target</th><th>Created</th><th>Title</th><th>Component</th><th>Recommended fix</th><th>Reporter</th><th>Links</th>')
        else:
            out.append('<th>Impact</th><th>Effort</th><th>Status</th><th>Target</th><th>Created</th><th>Cat</th><th>Title</th><th>Success metric</th><th>Plan</th><th>Proposed by</th><th>Links</th>')
        out.append('</tr></thead><tbody>')
        for r in rows:
            if is_incident:
                out.append(f'<tr><td>{sev_badge(r["severity"])}</td><td>{status_badge(r["status"])}</td>'
                           f'<td style="white-space:nowrap">{target_badge(r)}</td>'
                           f'<td>{created_est(r)}</td>'
                           f'<td><strong>{esc(r["title"])}</strong><div class="small" style="color:#9ca3af;margin-top:3px">{esc((r.get("description") or "")[:300])}{"…" if r.get("description") and len(r["description"])>300 else ""}</div></td>'
                           f'<td class="small">{esc(r.get("affected_component") or "")}</td>'
                           f'<td class="small">{esc((r.get("recommended_fix") or "")[:200])}</td>'
                           f'<td class="small">{esc(r.get("reported_by") or "")}</td>'
                           f'<td class="small">{render_links(r)}</td></tr>')
            else:
                ep = r.get("enhancement_plan") or ""
                ep_display = f'<div class="small" style="color:#9ca3af;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{esc(ep)}">{esc(ep[:120])}</div>' if ep else '<span style="color:#4b5563;font-size:10px">—</span>'
                out.append(f'<tr><td>{sev_badge(r["expected_impact"])}</td><td><span class="small">{esc(r["effort"])}</span></td>'
                           f'<td>{status_badge(r["status"])}</td>'
                           f'<td style="white-space:nowrap">{target_badge(r)}</td>'
                           f'<td>{created_est(r)}</td>'
                           f'<td class="small">{esc(r["category"])}</td>'
                           f'<td><strong>{esc(r["title"])}</strong><div class="small" style="color:#9ca3af;margin-top:3px">{esc((r.get("description") or "")[:300])}{"…" if r.get("description") and len(r["description"])>300 else ""}</div></td>'
                           f'<td class="small">{esc(r.get("success_metric") or "")}</td>'
                           f'<td class="small">{ep_display}</td>'
                           f'<td class="small">{esc(r.get("proposed_by") or "")}</td>'
                           f'<td class="small">{render_links(r)}</td></tr>')
        out.append('</tbody></table></details>')
    return "\n".join(out)


def finding_created_est(row):
    """Render created_at_utc as EST. Finding tables use created_at_utc (not created_at)."""
    ts = row.get("created_at_utc") or row.get("created_at")
    if not ts:
        return '<span style="color:#4b5563;font-size:10px">—</span>'
    try:
        if isinstance(ts, str):
            dt = datetime.strptime(ts[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        else:
            dt = ts
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        est = dt.astimezone(ZoneInfo("America/New_York"))
        return f'<span class="small" style="white-space:nowrap" title="{esc(str(ts))} UTC">{est.strftime("%Y-%m-%d %H:%M %Z")}</span>'
    except (ValueError, TypeError):
        return f'<span class="small">{esc(str(ts))}</span>'


def render_finding_linked(cls, row):
    """Render the linked-incident / linked-enhancement cell (only the columns that aren't NULL)."""
    bits = []
    li = row.get("linked_incident_id")
    le = row.get("linked_enhancement_id")
    if li:
        bits.append(f'<code>INCIDENT_{esc(cls)} #{int(li)}</code>')
    if le:
        bits.append(f'<code>ENHANCEMENT_{esc(cls)} #{int(le)}</code>')
    return "<br>".join(bits) if bits else '<span style="color:#4b5563">—</span>'


def render_findings_section(findings_by_class, generated_at):
    """Render the FINDINGS block — IDE-agent-logged dated findings, optionally linked
    to an incident/enhancement. Anchor 'findings' for in-page jumps."""
    total = sum(len(v) for v in findings_by_class.values())
    n_classes = sum(1 for v in findings_by_class.values() if v)
    out = [f'<h2 id="findings"><a id="findings"></a>Findings — {total} total across {n_classes} classes (last refresh: {esc(generated_at)})</h2>']
    out.append('<div class="small">Dated findings logged by IDE agents (Claude / Grok / Cursor / etc.) via <code>tools/audit_pick_funnel/cli_track.py finding</code>. Times stored UTC, rendered EST. Linked column points to the related INCIDENT or ENHANCEMENT row when set.</div>')
    if total == 0:
        out.append('<div class="small" style="color:#6b7280;margin-top:8px">No findings logged yet.</div>')
        return "\n".join(out)
    for cls in CLASSES:
        rows = findings_by_class.get(cls, [])
        if not rows:
            continue
        out.append(f'<details {"open" if cls in ("OVERALL","STOCKS","CRYPTO") else ""}><summary><strong>{cls}</strong> <span class="small">({len(rows)})</span></summary>')
        out.append('<table class="lb"><thead><tr>')
        out.append('<th>Sev</th><th>Title</th><th>Status</th><th>Agent</th><th>Created (EST)</th><th>Linked</th>')
        out.append('</tr></thead><tbody>')
        for r in rows:
            desc = (r.get("description") or "")
            desc_html = f'<div class="small" style="color:#9ca3af;margin-top:3px">{esc(desc[:300])}{"…" if len(desc)>300 else ""}</div>' if desc else ""
            evidence = r.get("evidence")
            evidence_html = f'<div class="small" style="color:#6b7280;margin-top:3px;font-family:monospace;font-size:10px">evidence: {esc(str(evidence)[:200])}</div>' if evidence else ""
            out.append(
                f'<tr><td>{sev_badge(r["severity"])}</td>'
                f'<td><strong>{esc(r["title"])}</strong>{desc_html}{evidence_html}</td>'
                f'<td>{status_badge(r["status"])}</td>'
                f'<td class="small">{esc(r.get("agent") or "")}</td>'
                f'<td>{finding_created_est(r)}</td>'
                f'<td class="small">{render_finding_linked(cls, r)}</td></tr>'
            )
        out.append('</tbody></table></details>')
    return "\n".join(out)


def render_html(incidents, enhancements, findings, generated_at):
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
  <a href="/audit/picks-now.html">⚡ Picks Now</a>
  <a href="/audit/ai-tournament.html">AI Tournament</a>
  <a href="/audit/pick_funnel.html">Pick Funnel</a>
  <a href="/updates/">Updates</a>
  <a href="#findings">Findings ↓</a>
</nav>

<div class="hero">
  <h1>🐛 Incidents + 🚀 Enhancements per Asset Class</h1>
  <p class="small">Live from <code>INCIDENT_*</code> and <code>ENHANCEMENT_*</code> tables in <code>ejaguiar1_stocks</code>. Auto-regenerated nightly. Last refresh: <strong>{esc(generated_at)}</strong></p>
</div>

{render_table_section("Incidents (bugs / data-quality issues / outages)", incidents, is_incident=True)}
{render_table_section("Enhancements (scoring / gate / data-feed / UI proposals)", enhancements, is_incident=False)}
{render_findings_section(findings, generated_at)}

<footer style="margin-top:40px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.07);color:#4b5563;font-size:11px">
  Generated by <code>tools/audit_pick_funnel/render_incidents_page.py</code> via GH Actions workflow <code>incidents-enhancements-nightly.yml</code>. Source: <code>vw_all_incidents</code> + <code>vw_all_enhancements</code> in <code>ejaguiar1_stocks</code>.
</footer>
</body></html>"""


def _summarize_by_class(incidents, enhancements):
    """Return rows of (class, n_inc_open, n_p0, top_inc_title, n_enh_open, top_enh_title)."""
    rows = []
    for cls in CLASSES:
        inc = [r for r in incidents.get(cls, []) if r["status"] in ("OPEN", "TRIAGED", "IN_PROGRESS")]
        enh = [r for r in enhancements.get(cls, []) if r["status"] in ("BACKLOG", "VALIDATED", "ACCEPTED")]
        if not inc and not enh:
            continue
        n_p0 = sum(1 for r in inc if r["severity"] == "P0")
        inc_sorted = sorted(inc, key=lambda r: (r["severity"] != "P0", r["severity"] != "P1"))
        enh_sorted = sorted(enh, key=lambda r: (r["expected_impact"] != "HIGH", r["expected_impact"] != "MEDIUM"))
        rows.append({
            "class": cls,
            "n_inc": len(inc),
            "n_p0": n_p0,
            "top_inc": inc_sorted[0]["title"] if inc_sorted else None,
            "n_enh": len(enh),
            "top_enh": enh_sorted[0]["title"] if enh_sorted else None,
        })
    return rows


def render_updates_injection(incidents, enhancements, generated_at):
    """Render the top-of-feed block with: (1) what this is, (2) per-class summary
    table, (3) top P0/P1 incidents, (4) top HIGH-impact enhancements."""
    flat_inc = [r for cls in CLASSES for r in incidents.get(cls, [])]
    flat_enh = [r for cls in CLASSES for r in enhancements.get(cls, [])]
    open_inc = [r for r in flat_inc if r["status"] in ("OPEN", "TRIAGED", "IN_PROGRESS")]
    open_enh = [r for r in flat_enh if r["status"] in ("BACKLOG", "VALIDATED", "ACCEPTED")]
    n_p0 = sum(1 for r in open_inc if r["severity"] == "P0")
    n_p1 = sum(1 for r in open_inc if r["severity"] == "P1")
    summary_rows = _summarize_by_class(incidents, enhancements)
    top_inc = sorted(open_inc, key=lambda r: (r["severity"] != "P0", r["severity"] != "P1"))[:10]
    top_enh = sorted(open_enh, key=lambda r: r["expected_impact"] != "HIGH")[:5]

    parts = [INJECTION_START, '''
<!-- Auto-generated section — do not hand-edit between START/END markers.
     Source: ejaguiar1_stocks INCIDENT_* / ENHANCEMENT_* tables.
     Distinct visual identity via the .incident-card / .enhancement-card classes
     and the orange/green left border vs the default update-entry cards. -->
<style>
  .ie-section { margin: 28px 20px; padding: 20px 22px; background: linear-gradient(135deg, rgba(245,158,11,0.07), rgba(34,197,94,0.07)); border: 2px solid rgba(245,158,11,0.35); border-radius: 12px; max-width: 820px; margin-left: auto; margin-right: auto; }
  .ie-section > h2 { margin: 0 0 6px; font-size: 19px; color: #f59e0b; }
  .ie-section > .intro { color: #cbd5e1; font-size: 13px; margin: 0 0 14px; line-height: 1.55; }
  .ie-section > .intro a { color: #93c5fd; text-decoration: underline; font-weight: 600; }
  .ie-explainer { background: rgba(15,23,42,0.5); border: 1px solid rgba(148,163,184,0.2); border-radius: 8px; padding: 12px 14px; margin: 0 0 14px; font-size: 12.5px; color: #cbd5e1; line-height: 1.55; }
  .ie-explainer strong { color: #fbbf24; }
  .ie-explainer code { background: rgba(0,0,0,0.3); padding: 1px 5px; border-radius: 3px; font-size: 11px; color: #fcd34d; }
  table.ie-class-summary { width: 100%; border-collapse: collapse; font-size: 12px; margin: 10px 0 16px; }
  table.ie-class-summary th { background: rgba(0,0,0,0.25); padding: 6px 8px; text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; border-bottom: 1px solid rgba(148,163,184,0.2); }
  table.ie-class-summary td { padding: 7px 8px; border-bottom: 1px solid rgba(148,163,184,0.08); color: #cbd5e1; vertical-align: top; }
  table.ie-class-summary tr:hover td { background: rgba(96,165,250,0.05); }
  table.ie-class-summary .cls { font-weight: 700; color: #93c5fd; }
  table.ie-class-summary .p0 { color: #ef4444; font-weight: 700; }
  table.ie-class-summary .top-issue { color: #f8fafc; font-size: 11.5px; }
  .incident-card { background: rgba(239,68,68,0.06); border-left: 4px solid #ef4444; border-radius: 0 8px 8px 0; padding: 10px 14px; margin: 8px 0; font-size: 13px; }
  .incident-card.sev-P1 { border-left-color: #f59e0b; background: rgba(245,158,11,0.05); }
  .enhancement-card { background: rgba(34,197,94,0.06); border-left: 4px solid #22c55e; border-radius: 0 8px 8px 0; padding: 10px 14px; margin: 8px 0; font-size: 13px; }
  .ie-card-meta { font-size: 11px; color: #9ca3af; margin-top: 3px; }
  .ie-card a { color: #93c5fd; text-decoration: none; font-weight: 600; }
  .ie-card a:hover { text-decoration: underline; color: #60a5fa; }
  .ie-class { display: inline-block; background: rgba(96,165,250,0.18); color: #93c5fd; padding: 1px 6px; border-radius: 6px; font-size: 10px; font-weight: 700; margin-right: 5px; }
  .ie-section h3 { font-size: 14px; margin: 16px 0 6px; }
</style>
<div class="ie-section">
  <h2>🐛 Open Incidents + 🚀 Top Enhancements — Live from /audit</h2>
  <p class="intro"><strong>Refreshed:</strong> ''' + esc(generated_at) + ''' · <strong>''' + str(len(open_inc)) + ''' open incidents</strong> (''' + str(n_p0) + ''' P0 · ''' + str(n_p1) + ''' P1) · <strong>''' + str(len(open_enh)) + ''' enhancements</strong> in backlog · across 9 asset-class buckets.</p>

  <div class="ie-explainer">
    <strong>What this section is:</strong> a live readout of every known issue + improvement proposal in the trading pipeline, sliced per asset class.
    <strong>Where the data lives:</strong> 18 MySQL tables — <code>INCIDENT_&lt;CLASS&gt;</code> + <code>ENHANCEMENT_&lt;CLASS&gt;</code> for STOCKS / ETFS / CRYPTO / FOREX / COMMODITIES / BONDS / FUTURES / PENNY + <code>OVERALL</code> for cross-cutting issues — exported to <a href="/audit/data/incidents_enhancements_feed.json">JSON</a> and rendered to the dashboard at <a href="/audit/incidents.html">/audit/incidents.html</a> (full filterable view).
    <strong>How it updates:</strong> peer-AI audits (Claude / Ring / Qwen / Kilo / Grok / opencode) seed new findings via <code>tools/audit_pick_funnel/cli_track.py</code>; the renderer runs nightly via <code>incidents-enhancements-nightly.yml</code> and FTP-pushes <code>incidents.html</code> + this <code>updates/index.html</code> block.
    <strong>How to read severity:</strong> <span style="color:#ef4444">P0</span> = blocks the page from being trustable (data corruption, broken gate, false claim); <span style="color:#f59e0b">P1</span> = misleading or stale but page still works; P2/P3 = cleanup. Enhancement impact: HIGH = expected to materially lift WR/PF or close a known data gap.
  </div>

  <h3 style="color:#93c5fd">Per-asset-class summary</h3>
  <table class="ie-class-summary">
    <thead><tr><th>Class</th><th>Open #</th><th>P0</th><th>Top issue</th><th>Enh #</th><th>Top enhancement</th></tr></thead>
    <tbody>''']
    for r in summary_rows:
        parts.append(f'''      <tr>
        <td class="cls">{esc(r["class"])}</td>
        <td>{r["n_inc"]}</td>
        <td class="p0">{r["n_p0"] if r["n_p0"] else "—"}</td>
        <td class="top-issue">{esc((r["top_inc"] or "—")[:90])}{"…" if r["top_inc"] and len(r["top_inc"])>90 else ""}</td>
        <td>{r["n_enh"]}</td>
        <td class="top-issue">{esc((r["top_enh"] or "—")[:80])}{"…" if r["top_enh"] and len(r["top_enh"])>80 else ""}</td>
      </tr>''')
    parts.append('''    </tbody>
  </table>
''')

    if top_inc:
        parts.append('<h3 style="color:#ef4444">Top 10 open P0/P1 incidents</h3>')
        for r in top_inc:
            sev_cls = f"sev-{r['severity']}"
            tr_info = f' · target: {r["target_release"]}' if r.get("target_release") else ""
            parts.append(f'''  <div class="incident-card ie-card {sev_cls}">
    <span class="ie-class">{esc(r["asset_class"])}</span> <strong>{esc(r["title"])}</strong>
    <div class="ie-card-meta">{esc(r["severity"])} · {esc(r["status"])} · component: <code>{esc(r.get("affected_component") or "—")}</code> · reporter: {esc(r.get("reported_by") or "")}{tr_info} · <a href="/audit/incidents.html#incidents">view in full table →</a></div>
  </div>''')

    if top_enh:
        parts.append('<h3 style="color:#22c55e">Top 5 HIGH-impact enhancements</h3>')
        for r in top_enh:
            tr_info = f' · target: {r["target_release"]}' if r.get("target_release") else ""
            parts.append(f'''  <div class="enhancement-card ie-card">
    <span class="ie-class">{esc(r["asset_class"])}</span> <strong>{esc(r["title"])}</strong>
    <div class="ie-card-meta">Impact {esc(r["expected_impact"])} · effort {esc(r["effort"])} · status {esc(r["status"])} · category {esc(r["category"])}{tr_info} · <a href="/audit/incidents.html#enhancements">view in full table →</a></div>
  </div>''')

    parts.append('<p style="margin:14px 0 0;font-size:12px;color:#94a3b8">→ Full filterable table with every row + asset-class drill-downs: <a href="/audit/incidents.html" style="color:#fbbf24;font-weight:700">/audit/incidents.html</a></p>')
    parts.append('</div>')
    parts.append(INJECTION_END)
    return "\n".join(parts)


def inject_into_updates(html_block):
    """Inject (or replace) the auto-block at the TOP of the updates feed so it's
    the first thing readers see — not buried 54,000 lines down."""
    if not UPDATES_PAGE.exists():
        print(f"[render] skip updates injection — {UPDATES_PAGE} missing")
        return False
    src = UPDATES_PAGE.read_text(encoding="utf-8")
    # Defensive: strip ANY existing block first (even bottom-of-page ones from
    # the old fallback), so we never end up with two copies after a fix.
    src = re.sub(
        re.escape(INJECTION_START) + r".*?" + re.escape(INJECTION_END) + r"\s*",
        "", src, flags=re.DOTALL)
    # Insert just before the FIRST `<div class="update-entry"` so the block
    # sits above the most recent entry in the feed (where eyes land first).
    m = re.search(r'<div\s+class="update-entry"', src)
    if m:
        insertion_point = m.start()
        # Walk backwards to start-of-line so the injected block sits flush left
        line_start = src.rfind("\n", 0, insertion_point) + 1
        # Use lambda for the replacement to avoid backreference interpretation in re.sub-style logic
        new = src[:line_start] + html_block + "\n\n  " + src[line_start:]
    else:
        # Fallback: just after <main> (if present), otherwise just before </body>
        m2 = re.search(r"<main[^>]*>", src, re.IGNORECASE)
        if m2:
            new = src[:m2.end()] + "\n" + html_block + "\n" + src[m2.end():]
        else:
            new = src.replace("</body>", html_block + "\n</body>", 1)
    UPDATES_PAGE.write_text(new, encoding="utf-8")
    return True


def main():
    incidents, enhancements, findings = fetch_all()
    now_utc = datetime.now(timezone.utc)
    est_now = now_utc.astimezone(ZoneInfo("America/New_York"))
    generated_at = est_now.strftime("%Y-%m-%d %H:%M %Z")
    html = render_html(incidents, enhancements, findings, generated_at)
    OUT_HTML.write_text(html, encoding="utf-8")
    feed = {
        "generated_at": generated_at,
        "incidents": {k: [{kk:(str(vv) if hasattr(vv,'isoformat') else vv) for kk,vv in r.items()} for r in v] for k,v in incidents.items()},
        "enhancements": {k: [{kk:(str(vv) if hasattr(vv,'isoformat') else vv) for kk,vv in r.items()} for r in v] for k,v in enhancements.items()},
        "findings": {k: [{kk:(str(vv) if hasattr(vv,'isoformat') else vv) for kk,vv in r.items()} for r in v] for k,v in findings.items()},
        "totals": {
            "incidents": sum(len(v) for v in incidents.values()),
            "enhancements": sum(len(v) for v in enhancements.values()),
            "findings": sum(len(v) for v in findings.values()),
        },
    }
    OUT_JSON.write_text(json.dumps(feed, indent=2, default=str), encoding="utf-8")
    block = render_updates_injection(incidents, enhancements, generated_at)
    injected = inject_into_updates(block)
    print(f"[render] wrote {OUT_HTML.relative_to(REPO)} ({len(html):,} bytes)")
    print(f"[render] wrote {OUT_JSON.relative_to(REPO)} ({OUT_JSON.stat().st_size:,} bytes)")
    print(f"[render] updates/index.html injection: {'OK' if injected else 'SKIPPED'}")
    print(f"[render] totals: {feed['totals']['incidents']} incidents · {feed['totals']['enhancements']} enhancements · {feed['totals']['findings']} findings")


if __name__ == "__main__":
    main()
