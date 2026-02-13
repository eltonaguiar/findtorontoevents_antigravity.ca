#!/usr/bin/env python3
"""Convert MOTHERLOAD MD files to sanitized HTML pages."""
import re, os, html as html_mod

ROOT = r"E:\findtorontoevents_antigravity.ca"
OUT_DIR = os.path.join(ROOT, "findstocks", "ai-research")
os.makedirs(OUT_DIR, exist_ok=True)

FILES = [
    {"src": os.path.join(ROOT, "ANTIGRAVITYMOTHERLOAD.MD"), "out": "antigravity-motherload.html",
     "title": "Antigravity Motherload: Complete Trading Algorithm Analysis", "model": "Gemini 2.0 Flash Thinking Experimental", "date": "February 11, 2026"},
    {"src": os.path.join(ROOT, "CHATGPT_CODEX_MOTHERLOAD.MD"), "out": "chatgpt-codex-motherload.html",
     "title": "ChatGPT Codex Motherload: Strategy Roadmap", "model": "ChatGPT / OpenAI Codex", "date": "February 2026"},
    {"src": os.path.join(ROOT, "DEEPSEEK_MOTHERLOAD.md"), "out": "deepseek-motherload.html",
     "title": "DeepSeek Motherload: Algorithm Analysis &amp; Enhancement Roadmap", "model": "DeepSeek V3.1 (671B)", "date": "February 11, 2026"},
    {"src": os.path.join(ROOT, "GROK_XAI_MOTHERLOAD.MD"), "out": "grok-xai-motherload.html",
     "title": "Grok xAI Motherload: Zero-Budget Quant Arsenal", "model": "Grok-4 (xAI)", "date": "February 12, 2026"},
    {"src": os.path.join(ROOT, "GITHUB_MOTHERLOAD.MD"), "out": "github-motherload.html",
     "title": "GitHub Motherload: Underdog vs. Big Players Strategy", "model": "GitHub Copilot", "date": "February 2026"},
    {"src": os.path.join(ROOT, "OPUS46_MOTHERLOAD.MD"), "out": "opus46-motherload.html",
     "title": "Opus 4.6 Motherload: Zero-Budget Quant Empire", "model": "Opus 4.6 (Anthropic)", "date": "February 12, 2026"},
    {"src": os.path.join(ROOT, "KIMIMOTHERLOAD.MD"), "out": "kimi-motherload.html",
     "title": "Kimi Motherload: Comprehensive Algorithm Review", "model": "Kimi AI", "date": "February 11, 2026"},
    {"src": os.path.join(ROOT, "KIMI", "KIMI_AGENTSWARM_MOTHERLOAD.md"), "out": "kimi-agentswarm-motherload.html",
     "title": "Kimi Agent Swarm Motherload: The Underdog's Guide", "model": "Kimi AI (Agent Swarm)", "date": "February 2026"},
    {"src": os.path.join(ROOT, "WINDSURF_MOTHERLOAD.MD"), "out": "windsurf-motherload.html",
     "title": "Windsurf Motherload: Battle Plan vs. Wall Street", "model": "Windsurf Cascade AI", "date": "February 11, 2026"},
]

# ── Sanitization ───────────────────────────────────────────────
TABLE_MAP = {
    "lm_signals": "[signals_table]", "lm_trades": "[trades_table]",
    "lm_market_regime": "[regime_table]", "lm_kelly_fractions": "[sizing_table]",
    "lm_algo_health": "[health_table]", "lm_intelligence": "[intelligence_table]",
    "lm_sports_daily_picks": "[sports_picks_table]", "lm_sports_bets": "[sports_bets_table]",
    "cp_signals": "[crypto_signals_table]", "fx_signals": "[forex_signals_table]",
    "gm_unified_picks": "[unified_picks_table]", "algo_performance": "[performance_table]",
    "daily_prices": "[prices_table]", "stock_picks": "[picks_table]",
    "market_data": "[market_table]",
}

def sanitize(text):
    # Passwords
    text = re.sub(r"POSTGRES_PASSWORD:\s*\S+", "POSTGRES_PASSWORD: [REDACTED]", text)
    # API keys
    text = re.sub(r"(API_KEY|api_key)\s*=\s*'[^']*'", r"\1 = '[REDACTED]'", text)
    text = re.sub(r"key=API_KEY", "key=[API_KEY]", text)
    # IP addresses
    text = text.replace("10_123_0_33", "[server]")
    text = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[server_ip]", text)
    # Database names
    text = text.replace("ejaguiar1_sportsbet", "[sports_database]")
    text = re.sub(r"ejaguiar\w*", "[database]", text)
    # Table names (longest first to avoid partial matches)
    for tbl in sorted(TABLE_MAP, key=len, reverse=True):
        text = text.replace(tbl, TABLE_MAP[tbl])
    # Generic lm_* tables
    text = re.sub(r"\blm_\w+\b", "[internal_table]", text)
    # SQL
    text = re.sub(r"SELECT\s+\*\s+FROM\s+\S+", "SELECT * FROM [table]", text, flags=re.I)
    text = re.sub(r"SELECT\s+\w[\w,\s]*\s+FROM\s+\S+", "SELECT [cols] FROM [table]", text, flags=re.I)
    text = re.sub(r"INSERT\s+INTO\s+\S+", "INSERT INTO [table]", text, flags=re.I)
    text = re.sub(r"CREATE\s+TABLE\s+\S+", "CREATE TABLE [table]", text, flags=re.I)
    # DB query calls
    text = re.sub(r"db\.fetchall\([^)]*\)", "db.fetch([query])", text)
    text = re.sub(r"db\.fetchone\([^)]*\)", "db.fetch([query])", text)
    text = re.sub(r"db\.col\([^)]*\)", "db.fetch([query])", text)
    text = re.sub(r"pd\.read_sql\([^)]*\)", "pd.read_sql([query])", text)
    text = re.sub(r"\$db->query\([^)]*\)", "$db->query([query])", text)
    return text

# ── Markdown → HTML ────────────────────────────────────────────
def inline(text):
    """Convert inline markdown."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r'<code class="inline">\1</code>', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text

def md_to_html(md):
    lines = md.split("\n")
    out = []
    in_code = False
    in_table = False
    first_table_row = False
    in_list = False
    list_tag = ""

    for raw_line in lines:
        line = raw_line.rstrip("\r")

        # Code fences
        m = re.match(r"^```(\w*)", line)
        if m:
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                lang = m.group(1)
                out.append(f"<pre class='code-block'><code class='language-{lang}'>")
                in_code = True
            continue
        if in_code:
            out.append(html_mod.escape(line))
            continue

        # Tables
        if line.startswith("|"):
            if not in_table:
                out.append("<div class='table-wrapper'><table>")
                in_table = True
                first_table_row = True
            # separator
            if re.match(r"^\|[\s\-:|]+\|?\s*$", line):
                continue
            cells = [c.strip() for c in line.split("|")[1:] if c.strip() != "" or c != ""]
            # trim trailing empty from split
            cells = [c.strip() for c in line.split("|")]
            cells = cells[1:]  # remove first empty
            if cells and cells[-1] == "":
                cells = cells[:-1]
            tag = "th" if first_table_row else "td"
            row = "<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>"
            out.append(row)
            first_table_row = False
            continue
        elif in_table:
            out.append("</table></div>")
            in_table = False

        # Close list on blank
        if not line.strip() and in_list:
            out.append(f"</{list_tag}>")
            in_list = False

        # Headers
        hm = re.match(r"^(#{1,6})\s+(.+)", line)
        if hm:
            level = len(hm.group(1))
            if level == 1:
                continue  # skip H1, using title from metadata
            out.append(f"<h{level}>{inline(hm.group(2))}</h{level}>")
            continue

        # Horizontal rule
        if re.match(r"^---+\s*$", line):
            out.append("<hr>")
            continue

        # Unordered list
        lm = re.match(r"^(\s*)[-*]\s+(.+)", line)
        if lm:
            if not in_list or list_tag != "ul":
                if in_list:
                    out.append(f"</{list_tag}>")
                out.append("<ul>")
                in_list = True
                list_tag = "ul"
            out.append(f"<li>{inline(lm.group(2))}</li>")
            continue

        # Ordered list
        lm = re.match(r"^(\s*)\d+\.\s+(.+)", line)
        if lm:
            if not in_list or list_tag != "ol":
                if in_list:
                    out.append(f"</{list_tag}>")
                out.append("<ol>")
                in_list = True
                list_tag = "ol"
            out.append(f"<li>{inline(lm.group(2))}</li>")
            continue

        # Blank
        if not line.strip():
            continue

        # Paragraph
        out.append(f"<p>{inline(line)}</p>")

    if in_code:
        out.append("</code></pre>")
    if in_table:
        out.append("</table></div>")
    if in_list:
        out.append(f"</{list_tag}>")

    return "\n".join(out)

# ── HTML template ──────────────────────────────────────────────
CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0e1a; color: #c8c8e0; min-height: 100vh; line-height: 1.7; }
a { color: #6366f1; text-decoration: none; }
a:hover { text-decoration: underline; color: #818cf8; }
.top-bar { background: #08081a; border-bottom: 1px solid #1e1e3a; padding: 0.75rem 2rem; display: flex; align-items: center; gap: 1rem; }
.top-bar a { color: #8888aa; font-size: 0.85rem; }
.top-bar a:hover { color: #e0e0f0; }
.hero { background: linear-gradient(135deg, #12122a 0%, #1a1040 50%, #0a0e1a 100%); border-bottom: 1px solid #1e1e3a; padding: 3rem 2rem 2.5rem; text-align: center; }
.hero h1 { font-size: 1.8rem; font-weight: 800; background: linear-gradient(135deg, #6366f1, #a78bfa, #22d3ee); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 0.6rem; line-height: 1.3; }
.hero .meta { display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; }
.hero .meta span { color: #8888aa; font-size: 0.85rem; }
.hero .meta .model-badge { background: rgba(99,102,241,0.15); color: #a78bfa; padding: 2px 10px; border-radius: 6px; font-weight: 600; }
.container { max-width: 920px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }
h2 { font-size: 1.4rem; font-weight: 700; color: #e0e0f0; margin: 2.5rem 0 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #1e1e3a; }
h3 { font-size: 1.15rem; font-weight: 600; color: #d0d0e8; margin: 2rem 0 0.75rem; }
h4 { font-size: 1rem; font-weight: 600; color: #b0b0d0; margin: 1.5rem 0 0.5rem; }
h5, h6 { font-size: 0.9rem; font-weight: 600; color: #9999bb; margin: 1rem 0 0.5rem; }
p { margin: 0.75rem 0; font-size: 0.92rem; color: #aaaacc; }
ul, ol { margin: 0.5rem 0 1rem 1.8rem; font-size: 0.92rem; }
li { margin-bottom: 0.4rem; color: #aaaacc; }
li strong { color: #e0e0f0; }
.table-wrapper { overflow-x: auto; margin: 1rem 0; border-radius: 8px; border: 1px solid #1e1e3a; }
table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
th { background: #161630; color: #b0b0d0; font-weight: 700; text-align: left; padding: 10px 12px; border-bottom: 2px solid #2a2a4a; white-space: nowrap; }
td { padding: 8px 12px; border-bottom: 1px solid #1a1a34; color: #aaaacc; }
tr:hover td { background: rgba(99,102,241,0.04); }
pre.code-block { background: #0d0d20; border: 1px solid #1e1e3a; border-radius: 8px; padding: 1rem 1.2rem; margin: 1rem 0; overflow-x: auto; font-size: 0.82rem; line-height: 1.6; }
pre.code-block code { color: #a78bfa; font-family: 'Fira Code','Cascadia Code',Consolas,monospace; }
code.inline { background: rgba(99,102,241,0.12); color: #a78bfa; padding: 1px 6px; border-radius: 4px; font-size: 0.85em; font-family: 'Fira Code','Cascadia Code',Consolas,monospace; }
hr { border: none; border-top: 1px solid #1e1e3a; margin: 2rem 0; }
strong { color: #e0e0f0; }
.footer { text-align: center; color: #555577; font-size: 0.8rem; margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid #1e1e3a; }
@media (max-width:700px) { .hero { padding: 2rem 1rem; } .hero h1 { font-size: 1.3rem; } .container { padding: 1rem; } table { font-size: 0.75rem; } th, td { padding: 6px 8px; } }
"""

def page_html(title, model, date, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} | AI Deep Research | FTE Invest</title>
<style>{CSS}</style>
</head>
<body>
<div class="top-bar">
<a href="/findstocks/updates.html">&larr; Back to Updates</a>
<a href="/findstocks/ai-research/">All AI Research</a>
</div>
<div class="hero">
<h1>{title}</h1>
<div class="meta">
<span class="model-badge">{model}</span>
<span>{date}</span>
<span>AI System Evaluation</span>
</div>
</div>
<div class="container">
{body}
<div class="footer">
<p>This document was generated by an AI system as part of the Antigravity AI evaluation process. Security-sensitive information has been redacted.</p>
<p style="margin-top:0.5rem">All trading data is from paper trading simulations. Not financial advice. Past performance does not guarantee future results.</p>
<p style="margin-top:0.5rem">&copy; 2026 Antigravity &middot; <a href="/findstocks/updates.html">Updates</a></p>
</div>
</div>
<script src="/findstocks/portfolio2/stock-nav.js"></script>
</body>
</html>"""

# ── Process all files ──────────────────────────────────────────
for i, f in enumerate(FILES, 1):
    print(f"[{i}/9] Processing: {os.path.basename(f['src'])}")
    if not os.path.exists(f["src"]):
        print(f"  WARNING: Not found, skipping")
        continue
    with open(f["src"], "r", encoding="utf-8", errors="replace") as fh:
        content = fh.read()
    sanitized = sanitize(content)
    body = md_to_html(sanitized)
    full = page_html(f["title"], f["model"], f["date"], body)
    out_path = os.path.join(OUT_DIR, f["out"])
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(full)
    print(f"  -> Saved: {out_path}")

# ── Create index ───────────────────────────────────────────────
INDEX_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0e1a; color: #e0e0f0; min-height: 100vh; line-height: 1.6; }
a { color: #6366f1; text-decoration: none; }
a:hover { text-decoration: underline; color: #818cf8; }
.top-bar { background: #08081a; border-bottom: 1px solid #1e1e3a; padding: 0.75rem 2rem; }
.top-bar a { color: #8888aa; font-size: 0.85rem; }
.hero { background: linear-gradient(135deg, #12122a 0%, #1a1040 50%, #0a0e1a 100%); border-bottom: 1px solid #1e1e3a; padding: 3rem 2rem 2.5rem; text-align: center; }
.hero h1 { font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, #6366f1, #a78bfa, #22d3ee); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 0.5rem; }
.hero .subtitle { color: #8888aa; font-size: 1rem; }
.container { max-width: 800px; margin: 0 auto; padding: 2rem 1.5rem 3rem; }
.card { background: #12122a; border: 1px solid #1e1e3a; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1rem; transition: border-color 0.2s, box-shadow 0.2s; display: block; }
.card:hover { border-color: rgba(99,102,241,0.5); box-shadow: 0 0 16px rgba(99,102,241,0.1); text-decoration: none; }
.card .title { font-size: 1.05rem; font-weight: 700; color: #e0e0f0; margin-bottom: 0.3rem; }
.card .meta { font-size: 0.8rem; color: #8888aa; }
.card .model-badge { display: inline-block; background: rgba(99,102,241,0.15); color: #a78bfa; padding: 1px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-right: 8px; }
.footer-note { text-align: center; color: #555577; font-size: 0.8rem; margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #1e1e3a; }
@media (max-width:600px) { .hero { padding: 1.5rem 1rem; } .hero h1 { font-size: 1.5rem; } .container { padding: 1rem; } }
"""

CARDS = [
    ("antigravity-motherload.html", "Complete Trading Algorithm Analysis", "Gemini 2.0 Flash", "Industry standards comparison &amp; strategic roadmap &mdash; Feb 11, 2026"),
    ("windsurf-motherload.html", "The Battle Plan vs. Wall Street's Supercomputers", "Windsurf Cascade", "50+ upgrades, live data audit, gap analysis &mdash; Feb 11, 2026"),
    ("kimi-agentswarm-motherload.html", "The Underdog's Guide to Competing with Billion-Dollar Firms", "Kimi Agent Swarm", "Agent swarm architecture, technical deep-dive &mdash; Feb 2026"),
    ("kimi-motherload.html", "Comprehensive Algorithm Review vs. Industry Standards", "Kimi AI", "23-algorithm inventory, performance analysis &mdash; Feb 11, 2026"),
    ("deepseek-motherload.html", "Algorithm Analysis &amp; Enhancement Roadmap", "DeepSeek V3.1 671B", "Core problem analysis, phased implementation &mdash; Feb 11, 2026"),
    ("opus46-motherload.html", "Zero-Budget Quant Empire vs. Wall Street Giants", "Opus 4.6", "Deep audit, 50 upgrades, free stack &mdash; Feb 12, 2026"),
    ("grok-xai-motherload.html", "Zero-Budget Quant Arsenal &amp; Roadmap", "Grok-4 (xAI)", "Ready-to-execute code drafts, 100 upgrades &mdash; Feb 12, 2026"),
    ("github-motherload.html", "Underdog vs. Big Players Strategy", "GitHub Copilot", "Strategic plan, advanced quant techniques &mdash; Feb 2026"),
    ("chatgpt-codex-motherload.html", "Codex Strategy Roadmap", "ChatGPT Codex", "Phased roadmap, free data stack &mdash; Feb 2026"),
]

cards_html = "\n".join(
    f'''<a class="card" href="{href}">
<div class="title">{title}</div>
<div class="meta"><span class="model-badge">{model}</span> {desc}</div>
</a>''' for href, title, model, desc in CARDS
)

index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Deep Research | FTE Invest</title>
<style>{INDEX_CSS}</style>
</head>
<body>
<div class="top-bar"><a href="/findstocks/updates.html">&larr; Back to Updates</a></div>
<div class="hero">
<h1>AI System Evaluation &amp; Deep Research</h1>
<p class="subtitle">Comprehensive algorithm analysis by 9 different AI systems</p>
</div>
<div class="container">
{cards_html}
<div class="footer-note">
Security-sensitive information has been redacted from all documents.<br>
All trading data is from paper trading simulations. Not financial advice.
</div>
</div>
<script src="/findstocks/portfolio2/stock-nav.js"></script>
</body>
</html>"""

idx_path = os.path.join(OUT_DIR, "index.html")
with open(idx_path, "w", encoding="utf-8") as fh:
    fh.write(index_html)
print(f"\n[DONE] Index page: {idx_path}")
print(f"Total: 10 files (9 research + 1 index)")
