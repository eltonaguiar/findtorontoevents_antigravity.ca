#!/usr/bin/env python3
"""
Patch all blog200–blog249 pages:
1. Replace simplified Investment Hub menu with full nested expandable version
2. Add submenu CSS + JS for expand/collapse
3. Add "Save Theme Preference" coming-soon feature badge
"""

import os, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── New Investment Hub section (replaces the flat items inside apps-tools) ──
OLD_APPS_BODY = '''<div class="os-section-body" data-sectionbody="apps-tools">
<a href="/investments/" class="otherstuff-item" target="_blank">
<div class="os-icon" style="background:rgba(34,197,94,0.15);">&#128200;</div>
<div class="os-text"><div class="os-title">Investment Hub</div>
<div class="os-desc">All portfolios, analytics &amp; tools</div></div>
<span class="os-arrow">&#8250;</span></a>
<a href="/findstocks/" class="otherstuff-item" target="_blank">
<div class="os-icon" style="background:rgba(245,158,11,0.15);">&#128200;</div>
<div class="os-text"><div class="os-title">Stock Ideas</div>
<div class="os-desc">AI picks updated daily</div></div>
<span class="os-arrow">&#8250;</span></a>
<a href="/live-monitor/sports-betting.html" class="otherstuff-item" target="_blank">
<div class="os-icon" style="background:rgba(34,197,94,0.15);">&#9917;</div>
<div class="os-text"><div class="os-title" style="color:#4ade80;">Sports Bet Finder</div>
<div class="os-desc">NHL, NBA, NFL &amp; more — value bets &amp; odds comparison</div></div>
<span class="os-arrow">&#8250;</span></a>
<a href="/MENTALHEALTHRESOURCES/" class="otherstuff-item" target="_blank">
<div class="os-icon" style="background:rgba(16,185,129,0.15);">&#129504;</div>
<div class="os-text"><div class="os-title">Mental Health</div>
<div class="os-desc">Wellness games, crisis support &amp; tools</div></div>
<span class="os-arrow">&#8250;</span></a>
<a href="/fc/#/guest" class="otherstuff-item" target="_blank">
<div class="os-icon" style="background:rgba(236,72,153,0.15);">&#128142;</div>
<div class="os-text"><div class="os-title">Fav Creators</div>
<div class="os-desc">Track streamers across Twitch, YouTube, Kick &amp; TikTok</div></div>
<span class="os-arrow">&#8250;</span></a>
<a href="/WINDOWSFIXER/" class="otherstuff-item" target="_blank">
<div class="os-icon" style="background:rgba(102,126,234,0.15);">&#128736;&#65039;</div>
<div class="os-text"><div class="os-title">Windows Boot Fixer</div>
<div class="os-desc">Fix BSOD, bootloader &amp; recovery issues</div></div>
<span class="os-arrow">&#8250;</span></a>
</div>'''

NEW_APPS_BODY = '''<div class="os-section-body" data-sectionbody="apps-tools">
<div class="os-submenu-toggle" data-submenu="investment-hub">
<div class="os-icon" style="background:rgba(34,197,94,0.15);">&#128200;</div>
<div class="os-text"><div class="os-title">Investment Hub</div>
<div class="os-desc">All portfolios, analytics &amp; tools in one place</div></div>
<span class="os-chevron">&#8250;</span></div>
<div class="os-submenu-panel" data-panel="investment-hub">
<a href="/investments/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#6366f1;"></span><span class="os-sub-text">Investment Tools &mdash; Overview</span><span class="os-sub-arrow">&#8250;</span></a>
<div class="os-category-toggle" data-category="stocks"><span class="os-cat-icon">&#128200;</span><span class="os-cat-title">Stocks</span><span class="os-cat-chevron">&#8250;</span></div>
<div class="os-category-panel" data-catpanel="stocks">
<a href="/findstocks/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#f59e0b;"></span><span class="os-sub-text">Stock Ideas &mdash; AI picks, updated daily</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findstocks/portfolio2/dashboard.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#6366f1;"></span><span class="os-sub-text">Portfolio Dashboard</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findstocks/portfolio2/picks.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#6366f1;"></span><span class="os-sub-text">Quick Picks</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findstocks/portfolio2/horizon-picks.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#6366f1;"></span><span class="os-sub-text">Horizon Picks</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findstocks/portfolio2/dividends.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#22c55e;"></span><span class="os-sub-text">Dividends &amp; Earnings</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findstocks/portfolio2/stats/index.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#6366f1;"></span><span class="os-sub-text">Portfolio Stats</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findstocks/portfolio2/smart-learning.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#a78bfa;"></span><span class="os-sub-text">Smart Learning</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findstocks/portfolio2/stock-intel.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#a78bfa;"></span><span class="os-sub-text">Stock Intel</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findstocks/portfolio2/daytrader-sim.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#f43f5e;"></span><span class="os-sub-text">Day Trader Sim</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findstocks/portfolio2/penny-stocks.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#84cc16;"></span><span class="os-sub-text">Penny Stock Finder</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findstocks_global/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#22c55e;"></span><span class="os-sub-text">Global Stocks Hub</span><span class="os-sub-arrow">&#8250;</span></a>
</div>
<div class="os-category-toggle" data-category="mutualfunds"><span class="os-cat-icon">&#128202;</span><span class="os-cat-title">Mutual Funds</span><span class="os-cat-chevron">&#8250;</span></div>
<div class="os-category-panel" data-catpanel="mutualfunds">
<a href="/findmutualfunds/portfolio1/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#6366f1;"></span><span class="os-sub-text">Fund Portfolio</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findmutualfunds/portfolio1/stats.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#6366f1;"></span><span class="os-sub-text">Fund Stats</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findmutualfunds2/portfolio2/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#22c55e;"></span><span class="os-sub-text">Portfolio v2</span><span class="os-sub-arrow">&#8250;</span></a>
</div>
<div class="os-category-toggle" data-category="crypto"><span class="os-cat-icon">&#129689;</span><span class="os-cat-title">Crypto</span><span class="os-cat-chevron">&#8250;</span></div>
<div class="os-category-panel" data-catpanel="crypto">
<a href="/findcryptopairs/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#f59e0b;"></span><span class="os-sub-text">Crypto Pairs Scanner</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findcryptopairs/portfolio/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#f59e0b;"></span><span class="os-sub-text">Crypto Portfolio</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findcryptopairs/meme.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#d946ef;"></span><span class="os-sub-text">Meme Coin Scanner</span><span class="os-sub-arrow">&#8250;</span></a>
</div>
<div class="os-category-toggle" data-category="forex"><span class="os-cat-icon">&#128177;</span><span class="os-cat-title">Forex</span><span class="os-cat-chevron">&#8250;</span></div>
<div class="os-category-panel" data-catpanel="forex">
<a href="/findforex2/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#06b6d4;"></span><span class="os-sub-text">Forex Scanner</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/findforex2/portfolio/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#06b6d4;"></span><span class="os-sub-text">Forex Portfolio</span><span class="os-sub-arrow">&#8250;</span></a>
</div>
<div class="os-category-toggle" data-category="goldmines"><span class="os-cat-icon">&#9935;&#65039;</span><span class="os-cat-title">Goldmines</span><span class="os-cat-chevron">&#8250;</span></div>
<div class="os-category-panel" data-catpanel="goldmines">
<a href="/investments/goldmines/antigravity/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#22c55e;"></span><span class="os-sub-text">Antigravity Goldmine</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/goldmine_cursor/" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#f59e0b;"></span><span class="os-sub-text">Cursor Goldmine</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/live-monitor/goldmine-dashboard.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#6366f1;"></span><span class="os-sub-text">Claude Goldmine</span><span class="os-sub-arrow">&#8250;</span></a>
<a href="/live-monitor/multi-dimensional.html" class="os-sub-link" target="_blank"><span class="os-sub-dot" style="background:#818cf8;"></span><span class="os-sub-text">Multi-Dimensional (6D)</span><span class="os-sub-arrow">&#8250;</span></a>
</div>
</div>
<a href="/live-monitor/sports-betting.html" class="otherstuff-item" target="_blank">
<div class="os-icon" style="background:rgba(34,197,94,0.15);">&#9917;</div>
<div class="os-text"><div class="os-title" style="color:#4ade80;">Sports Bet Finder</div>
<div class="os-desc">NHL, NBA, NFL &amp; more &mdash; value bets, odds comparison &amp; paper trading</div></div>
<span class="os-arrow">&#8250;</span></a>
<a href="/MENTALHEALTHRESOURCES/" class="otherstuff-item" target="_blank">
<div class="os-icon" style="background:rgba(16,185,129,0.15);">&#129504;</div>
<div class="os-text"><div class="os-title">Mental Health</div>
<div class="os-desc">Wellness games, crisis support &amp; tools</div></div>
<span class="os-arrow">&#8250;</span></a>
<a href="/fc/#/guest" class="otherstuff-item" target="_blank">
<div class="os-icon" style="background:rgba(236,72,153,0.15);">&#128142;</div>
<div class="os-text"><div class="os-title">Fav Creators</div>
<div class="os-desc">Track streamers across Twitch, YouTube, Kick &amp; TikTok</div></div>
<span class="os-arrow">&#8250;</span></a>
<a href="/WINDOWSFIXER/" class="otherstuff-item" target="_blank">
<div class="os-icon" style="background:rgba(102,126,234,0.15);">&#128736;&#65039;</div>
<div class="os-text"><div class="os-title">Windows Boot Fixer</div>
<div class="os-desc">Fix BSOD, bootloader &amp; recovery issues</div></div>
<span class="os-arrow">&#8250;</span></a>
</div>'''

# ── Additional CSS for submenu items ──
SUBMENU_CSS = '''
/* ── Submenu (Investment Hub nesting) ── */
.os-submenu-toggle{display:flex;align-items:center;gap:12px;padding:12px;border-radius:10px;cursor:pointer;transition:background 0.2s;}
.os-submenu-toggle:hover{background:rgba(255,255,255,0.06);}
.os-submenu-toggle .os-chevron{color:rgba(255,255,255,0.4);font-size:1.2rem;transition:transform 0.3s;margin-left:auto;}
.os-submenu-toggle.open .os-chevron{transform:rotate(90deg);}
.os-submenu-panel{display:none;padding:4px 0 4px 12px;border-left:2px solid rgba(255,255,255,0.08);margin-left:20px;}
.os-submenu-panel.open{display:block;}
.os-category-toggle{display:flex;align-items:center;gap:8px;padding:8px 12px;cursor:pointer;border-radius:8px;font-size:0.82rem;font-weight:600;color:rgba(255,255,255,0.7);transition:background 0.2s;}
.os-category-toggle:hover{background:rgba(255,255,255,0.05);}
.os-cat-icon{font-size:1rem;}
.os-cat-title{flex:1;}
.os-cat-chevron{transition:transform 0.3s;color:rgba(255,255,255,0.3);font-size:0.9rem;}
.os-category-toggle.open .os-cat-chevron{transform:rotate(90deg);}
.os-category-panel{display:none;padding:2px 0 6px 8px;}
.os-category-panel.open{display:block;}
.os-sub-link{display:flex;align-items:center;gap:8px;padding:7px 12px;border-radius:8px;text-decoration:none;color:rgba(255,255,255,0.7);font-size:0.8rem;transition:background 0.2s,color 0.2s;}
.os-sub-link:hover{background:rgba(255,255,255,0.06);color:#fff;}
.os-sub-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;}
.os-sub-text{flex:1;}
.os-sub-arrow{color:rgba(255,255,255,0.25);font-size:0.85rem;}
/* ── Theme Preference Badge ── */
.coming-soon-badge{display:inline-block;padding:2px 8px;border-radius:8px;font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;background:rgba(251,191,36,0.2);color:#fbbf24;border:1px solid rgba(251,191,36,0.3);margin-left:6px;vertical-align:middle;}
'''

# ── Additional JS for submenu toggles ──
SUBMENU_JS = '''
/* ── Submenu & Category Toggles ── */
var subToggle=e.target.closest&&e.target.closest('.os-submenu-toggle');
if(subToggle){e.preventDefault();e.stopPropagation();
  var key=subToggle.getAttribute('data-submenu');
  var panel=document.querySelector('.os-submenu-panel[data-panel="'+key+'"]');
  if(panel){var isOpen=panel.classList.contains('open');subToggle.classList.toggle('open',!isOpen);panel.classList.toggle('open',!isOpen);}return;}
var catToggle=e.target.closest&&e.target.closest('.os-category-toggle');
if(catToggle){e.preventDefault();e.stopPropagation();
  var cat=catToggle.getAttribute('data-category');
  var catPanel=document.querySelector('.os-category-panel[data-catpanel="'+cat+'"]');
  if(catPanel){var catOpen=catPanel.classList.contains('open');catToggle.classList.toggle('open',!catOpen);catPanel.classList.toggle('open',!catOpen);}return;}
'''

# ── "Save theme" coming-soon feature in the theme label ──
THEME_SAVE_BADGE = ' <span class="coming-soon-badge">Save Preference &mdash; Coming Soon</span>'

def patch_file(filepath):
    html = filepath.read_text(encoding='utf-8')
    changed = False

    # 1. Replace simplified Apps & Tools body with full nested version
    if OLD_APPS_BODY in html:
        html = html.replace(OLD_APPS_BODY, NEW_APPS_BODY)
        changed = True

    # 2. Inject submenu CSS before </style>
    if '.os-submenu-toggle' not in html and '</style>' in html:
        html = html.replace('</style>', SUBMENU_CSS + '\n</style>', 1)
        changed = True

    # 3. Inject submenu JS into the click handler (after the section-header handler)
    if '.os-submenu-toggle' not in html and "var sec=t.closest&&t.closest('.os-section-header');" in html:
        # The existing handler variable is 't', but our SUBMENU_JS uses e.target - fix reference
        submenu_js_fixed = SUBMENU_JS.replace('e.target.closest', 't.closest')
        # Insert after the section-header handler's closing return
        marker = "sec.classList.toggle('collapsed',!hidden);}return;}"
        if marker in html:
            html = html.replace(marker, marker + '\n' + submenu_js_fixed)
            changed = True

    # 4. Add "Save Theme Preference - Coming Soon" badge to theme-label
    if 'coming-soon-badge' not in html:
        # Find the theme-label span and append the badge
        pattern = r'(<span class="theme-label">Theme #\d+ &mdash; [^<]+)(</span>)'
        replacement = r'\1' + THEME_SAVE_BADGE + r'\2'
        new_html = re.sub(pattern, replacement, html)
        if new_html != html:
            html = new_html
            changed = True

    if changed:
        filepath.write_text(html, encoding='utf-8')
    return changed


def main():
    blog_files = sorted(ROOT.glob("blog2[0-4][0-9].html"))
    print(f"Found {len(blog_files)} blog files to patch")

    patched = 0
    for f in blog_files:
        if patch_file(f):
            patched += 1
            print(f"  Patched {f.name}")
        else:
            print(f"  Skipped {f.name} (already patched or no match)")

    print(f"\n{'='*50}")
    print(f"  Patched {patched}/{len(blog_files)} files")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
