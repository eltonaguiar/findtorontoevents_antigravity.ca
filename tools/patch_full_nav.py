"""
Patch Quick Nav with full Other Stuff hierarchy.
Generates both static HTML (for index.html) and minified JSX (for React chunk).
Mirrors the complete Other Stuff popup menu structure.
"""
import os, sys, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO, "index.html")
CHUNK = "a2ac3a6616d60872.js"
CHUNK_PATHS = [
    os.path.join(REPO, "TORONTOEVENTS_ANTIGRAVITY", "_next", "static", "chunks", CHUNK),
    os.path.join(REPO, "TORONTOEVENTS_ANTIGRAVITY", "next", "_next", "static", "chunks", CHUNK),
    os.path.join(REPO, "next", "_next", "static", "chunks", CHUNK),
    os.path.join(REPO, "_next", "static", "chunks", CHUNK),
]

# ═══════════════════════════════════════════════════════════════════════
# MENU DATA — the single source of truth for the full navigation hierarchy
# ═══════════════════════════════════════════════════════════════════════

FEATURED = [
    {"href": "/weather/", "emoji": "\U0001f324\ufe0f", "label": "Toronto Weather", "hover": "cyan", "text": "cyan"},
    {"href": "/affiliates/", "emoji": "\U0001f517", "label": "Gear & Links", "hover": "amber", "text": "amber"},
    {"href": "/updates/", "emoji": "\U0001f195", "label": "Latest Updates", "hover": "emerald", "text": "emerald"},
    {"href": "/news/", "emoji": "\U0001f4f0", "label": "News Aggregator", "hover": "red", "text": "red"},
    {"href": "/deals/", "emoji": "\U0001f381", "label": "Deals & Freebies", "hover": "amber", "text": "yellow"},
]

APPS_AND_TOOLS = {
    "id": "apps-tools",
    "emoji": "\U0001f4f1",
    "title": "Apps & Tools",
    "children": [
        # Investment Hub (expandable submenu)
        {
            "type": "submenu",
            "id": "inv-hub",
            "emoji": "\U0001f4ca",
            "title": "Investment Hub",
            "overview": {"href": "/investments/", "label": "Investment Tools \u2014 Overview", "dot": "#6366f1"},
            "categories": [
                {
                    "id": "stocks",
                    "emoji": "\U0001f4c8",
                    "title": "Stocks",
                    "links": [
                        {"href": "/findstocks/", "label": "Stock Ideas \u2014 AI picks, updated daily", "dot": "#f59e0b"},
                        {"href": "/findstocks/portfolio2/dashboard.html", "label": "Portfolio Dashboard", "dot": "#6366f1"},
                        {"href": "/findstocks/portfolio2/picks.html", "label": "Quick Picks", "dot": "#6366f1"},
                        {"href": "/findstocks/portfolio2/horizon-picks.html", "label": "Horizon Picks", "dot": "#6366f1"},
                        {"href": "/findstocks/portfolio2/dividends.html", "label": "Dividends & Earnings", "dot": "#22c55e"},
                        {"href": "/findstocks/portfolio2/stats/index.html", "label": "Portfolio Stats", "dot": "#6366f1"},
                        {"href": "/findstocks/portfolio2/smart-learning.html", "label": "Smart Learning", "dot": "#a78bfa"},
                        {"href": "/findstocks/portfolio2/stock-intel.html", "label": "Stock Intel", "dot": "#a78bfa"},
                        {"href": "/findstocks/portfolio2/daytrader-sim.html", "label": "Day Trader Sim", "dot": "#f43f5e"},
                        {"href": "/findstocks/portfolio2/penny-stocks.html", "label": "Penny Stock Finder", "dot": "#84cc16"},
                        {"href": "/findstocks_global/", "label": "Global Stocks Hub", "dot": "#22c55e"},
                        {"href": "/updates/?category=stocks", "label": "Stock Updates & Changelog", "dot": "#64748b"},
                    ]
                },
                {
                    "id": "funds",
                    "emoji": "\U0001f4ca",
                    "title": "Mutual Funds",
                    "links": [
                        {"href": "/findmutualfunds/portfolio1/", "label": "Fund Portfolio", "dot": "#6366f1"},
                        {"href": "/findmutualfunds/portfolio1/stats.html", "label": "Fund Stats", "dot": "#6366f1"},
                        {"href": "/findmutualfunds/portfolio1/report.html", "label": "Fund Report", "dot": "#6366f1"},
                        {"href": "/findmutualfunds2/portfolio2/", "label": "Portfolio v2", "dot": "#22c55e"},
                        {"href": "/findmutualfunds2/portfolio2/stats/index.html", "label": "Portfolio v2 Stats", "dot": "#22c55e"},
                    ]
                },
                {
                    "id": "crypto",
                    "emoji": "\U0001fa99",
                    "title": "Crypto",
                    "links": [
                        {"href": "/findcryptopairs/", "label": "Crypto Pairs Scanner", "dot": "#f59e0b"},
                        {"href": "/findcryptopairs/portfolio/", "label": "Crypto Portfolio", "dot": "#f59e0b"},
                        {"href": "/findcryptopairs/portfolio/stats/index.html", "label": "Crypto Stats", "dot": "#f59e0b"},
                        {"href": "/findcryptopairs/meme.html", "label": "Meme Coin Scanner", "dot": "#d946ef"},
                    ]
                },
                {
                    "id": "forex",
                    "emoji": "\U0001f4b1",
                    "title": "Forex",
                    "links": [
                        {"href": "/findforex2/", "label": "Forex Scanner", "dot": "#06b6d4"},
                        {"href": "/findforex2/portfolio/", "label": "Forex Portfolio", "dot": "#06b6d4"},
                        {"href": "/findforex2/portfolio/stats/index.html", "label": "Forex Stats", "dot": "#06b6d4"},
                    ]
                },
                {
                    "id": "goldmines",
                    "emoji": "\u26cf\ufe0f",
                    "title": "Goldmines",
                    "links": [
                        {"href": "/investments/goldmines/antigravity/", "label": "Antigravity Goldmine", "dot": "#22c55e"},
                        {"href": "/goldmine_cursor/", "label": "Cursor Goldmine", "dot": "#f59e0b"},
                        {"href": "/live-monitor/goldmine-dashboard.html", "label": "Claude Goldmine", "dot": "#6366f1"},
                        {"href": "/live-monitor/multi-dimensional.html", "label": "Multi-Dimensional (6D)", "dot": "#818cf8"},
                        {"href": "/investments/goldmines/kimi/kimi-goldmine-client.html", "label": "Kimi Goldmine", "dot": "#ffd700"},
                    ]
                },
            ]
        },
        # Standalone items in Apps & Tools
        {"type": "link", "href": "/live-monitor/sports-betting.html", "emoji": "\u26bd", "label": "Sports Bet Finder", "hover": "green", "text": "green"},
        {"type": "link", "href": "/MENTALHEALTHRESOURCES/", "emoji": "\U0001f9e0", "label": "Mental Health", "hover": "green", "text": "green"},
        {"type": "link", "href": "/fc/#/guest", "emoji": "\U0001f48e", "label": "Fav Creators", "hover": "pink", "text": "pink"},
        {"type": "link", "href": "/WINDOWSFIXER/", "emoji": "\U0001f6e0\ufe0f", "label": "Windows Boot Fixer", "hover": "blue", "text": "blue"},
    ]
}

MOVIES_TV = {
    "id": "movies-tv",
    "emoji": "\U0001f3ac",
    "title": "Movies & TV",
    "links": [
        {"href": "/MOVIESHOWS/", "emoji": "\U0001f3ac", "label": "Now Showing", "hover": "amber", "text": "amber"},
        {"href": "/movieshows2/", "emoji": "\U0001f39e\ufe0f", "label": "The Film Vault", "hover": "orange", "text": "orange"},
        {"href": "/MOVIESHOWS3/", "emoji": "\U0001f3a5", "label": "Binge Mode", "hover": "rose", "text": "rose"},
    ]
}

IMMERSIVE = {
    "id": "immersive",
    "emoji": "\U0001f3ae",
    "title": "Immersive",
    "children": [
        {
            "type": "submenu",
            "id": "games-vr",
            "emoji": "\U0001f3ae",
            "title": "Games & VR",
            "categories": [
                {
                    "id": "vr-exp",
                    "emoji": "\U0001f97d",
                    "title": "VR Experience",
                    "links": [
                        {"href": "/vr/", "label": "VR Hub \u2014 Desktop & Quest 3", "dot": "#a855f7"},
                        {"href": "/vr/mobile-index.html", "label": "VR Mobile", "dot": "#d946ef"},
                        {"href": "/vr/weather-zone.html", "label": "VR Weather Observatory", "dot": "#00d4ff"},
                        {"href": "/vr/events/", "label": "VR Events Explorer", "dot": "#a855f7"},
                        {"href": "/vr/movies-tiktok.html", "label": "VR Movie Theater", "dot": "#f59e0b"},
                        {"href": "/vr/creators.html", "label": "VR Creators Lounge", "dot": "#ec4899"},
                        {"href": "/vr/stocks-zone.html", "label": "VR Stocks Floor", "dot": "#6366f1"},
                        {"href": "/vr/wellness/", "label": "VR Wellness Zone", "dot": "#22c55e"},
                    ]
                },
                {
                    "id": "game-arena",
                    "emoji": "\U0001f3ae",
                    "title": "Game Arena",
                    "links": [
                        {"href": "/vr/game-arena/", "label": "Game Arena Hub", "dot": "#a855f7"},
                        {"href": "/vr/game-arena/tic-tac-toe.html", "label": "Tic-Tac-Toe", "dot": "#6366f1"},
                        {"href": "/vr/game-arena/soccer-shootout.html", "label": "Soccer Shootout", "dot": "#22c55e"},
                        {"href": "/vr/ant-rush/", "label": "Ant Rush", "dot": "#f59e0b"},
                    ]
                },
                {
                    "id": "fps",
                    "emoji": "\U0001f3af",
                    "title": "FPS & Shooters",
                    "links": [
                        {"href": "/vr/game-arena/fps-arena.html", "label": "FPS Arena", "dot": "#ef4444"},
                        {"href": "/vr/game-arena/fps-v5/", "label": "Game Prototypes Hub", "dot": "#a855f7"},
                        {"href": "/vr/game-arena/fps-v5/prototype-tactical.html", "label": "FPS: Tactical", "dot": "#f43f5e"},
                        {"href": "/vr/game-arena/fps-v5/prototype-realistic.html", "label": "FPS: Realistic", "dot": "#f43f5e"},
                        {"href": "/vr/game-arena/fps-v5/prototype-krunker.html", "label": "FPS: Krunker-style", "dot": "#f43f5e"},
                    ]
                },
                {
                    "id": "fighting",
                    "emoji": "\u2694\ufe0f",
                    "title": "Fighting Games",
                    "links": [
                        {"href": "/FIGHTGAME/", "label": "Shadow Arena", "dot": "#e74c3c"},
                        {"href": "/vr/game-arena/fighting-arena.html", "label": "VR Fighting Arena", "dot": "#e74c3c"},
                    ]
                },
            ]
        },
    ]
}

DRAFTS = {
    "id": "drafts",
    "emoji": "\U0001f4dd",
    "title": "Drafts",
    "links": [
        {"href": "/fc/taste-profile/", "emoji": "\U0001f3b5", "label": "Taste Profile", "hover": "purple", "text": "purple"},
        {"href": "/fc/#/accountability", "emoji": "\U0001f3af", "label": "Accountability", "hover": "amber", "text": "amber"},
        {"href": "/gotjob/", "emoji": "\U0001f4bc", "label": "GotJob", "hover": "cyan", "text": "cyan"},
    ]
}


# ═══════════════════════════════════════════════════════════════════════
# HTML GENERATION (for static index.html nav)
# ═══════════════════════════════════════════════════════════════════════

def _h_link(href, emoji, label, hover, text, indent=12):
    sp = ' ' * indent
    return (
        f'{sp}<a class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 '
        f'hover:bg-{hover}-500/20 text-{text}-200 hover:text-white transition-all '
        f'border border-transparent hover:border-{hover}-500/30 overflow-hidden text-sm" '
        f'href="{href}"><span class="text-base">{emoji}</span> {label}</a>'
    )

def _h_sub_link(href, label, dot_color, indent=16):
    sp = ' ' * indent
    return (
        f'{sp}<a class="w-full text-left px-3 py-1.5 rounded-lg flex items-center gap-2 '
        f'hover:bg-white/10 text-gray-300 hover:text-white transition-all text-xs '
        f'border border-transparent hover:border-white/10" '
        f'href="{href}">'
        f'<span class="w-1.5 h-1.5 rounded-full flex-shrink-0" style="background:{dot_color}"></span>'
        f' {label}</a>'
    )

def _h_category(cat, indent=14):
    sp = ' ' * indent
    lines = []
    lines.append(f'{sp}<details class="group/{cat["id"]}">')
    lines.append(f'{sp}  <summary class="w-full text-left px-3 py-1.5 rounded-lg flex items-center gap-2 '
                 f'hover:bg-white/5 text-gray-400 hover:text-white transition-all cursor-pointer list-none text-xs font-semibold">'
                 f'{cat["emoji"]} {cat["title"]} '
                 f'<span class="ml-auto group-open/{cat["id"]}:rotate-180 transition-transform text-[10px] opacity-60">\u25bc</span></summary>')
    lines.append(f'{sp}  <div class="space-y-0.5 mt-0.5 ml-3">')
    for link in cat["links"]:
        lines.append(_h_sub_link(link["href"], link["label"], link["dot"], indent + 4))
    lines.append(f'{sp}  </div>')
    lines.append(f'{sp}</details>')
    return '\n'.join(lines)

def _h_submenu(item, indent=12):
    sp = ' ' * indent
    lines = []
    lines.append(f'{sp}<details class="group/{item["id"]}">')
    lines.append(f'{sp}  <summary class="w-full text-left px-4 py-2 rounded-xl flex items-center gap-3 '
                 f'hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all cursor-pointer list-none text-sm">'
                 f'{item["emoji"]} {item["title"]} '
                 f'<span class="ml-auto group-open/{item["id"]}:rotate-180 transition-transform text-xs opacity-60">\u25bc</span></summary>')
    lines.append(f'{sp}  <div class="space-y-0.5 mt-1 ml-3">')
    # Overview link if present
    if "overview" in item:
        ov = item["overview"]
        lines.append(_h_sub_link(ov["href"], ov["label"], ov["dot"], indent + 4))
    # Categories
    for cat in item.get("categories", []):
        lines.append(_h_category(cat, indent + 4))
    lines.append(f'{sp}  </div>')
    lines.append(f'{sp}</details>')
    return '\n'.join(lines)

def _h_section(section, indent=12):
    """Build a top-level expandable section (Apps & Tools, Movies & TV, etc.)."""
    sp = ' ' * indent
    lines = []
    lines.append(f'{sp}<details class="group/{section["id"]}">')
    lines.append(f'{sp}  <summary class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 '
                 f'hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all cursor-pointer list-none text-sm">'
                 f'{section["emoji"]} {section["title"]} '
                 f'<span class="ml-auto group-open/{section["id"]}:rotate-180 transition-transform text-xs opacity-60">\u25bc</span></summary>')
    lines.append(f'{sp}  <div class="space-y-0.5 mt-1 ml-4">')

    # For sections with children (mixed submenus and links)
    if "children" in section:
        for child in section["children"]:
            if child["type"] == "submenu":
                lines.append(_h_submenu(child, indent + 4))
            elif child["type"] == "link":
                lines.append(_h_link(child["href"], child["emoji"], child["label"],
                                     child["hover"], child["text"], indent + 4))
    # For simple link sections (Movies & TV, Drafts)
    if "links" in section:
        for link in section["links"]:
            lines.append(_h_link(link["href"], link["emoji"], link["label"],
                                 link["hover"], link["text"], indent + 4))

    lines.append(f'{sp}  </div>')
    lines.append(f'{sp}</details>')
    return '\n'.join(lines)

def generate_html():
    """Generate the full OTHER STUFF section HTML for index.html."""
    lines = []
    lines.append('          <!-- OTHER STUFF Section (Gold Glow) -->')
    lines.append('          <div class="space-y-1 pt-4 border-t border-white/5">')
    lines.append('            <div class="px-3 py-2.5 mx-1 mb-1 rounded-xl text-center gold-glow-nav">')
    lines.append('              <p class="text-[11px] font-black uppercase tracking-[0.2em] text-black/90">\u2728 OTHER STUFF \u2728</p>')
    lines.append('            </div>')

    # Featured links
    for f in FEATURED:
        lines.append(_h_link(f["href"], f["emoji"], f["label"], f["hover"], f["text"]))

    # Sections
    lines.append(_h_section(APPS_AND_TOOLS))
    lines.append(_h_section(MOVIES_TV))
    lines.append(_h_section(IMMERSIVE))
    lines.append(_h_section(DRAFTS))

    # Event System Settings
    lines.append('            <button class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 '
                 'hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all overflow-hidden">')
    lines.append('              <span class="text-lg">\u2699\ufe0f</span> Event System Settings</button>')
    lines.append('          </div>')

    return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════════
# JSX GENERATION (for React chunk)
# ═══════════════════════════════════════════════════════════════════════

def _j_link(href, emoji, label, hover, text):
    return (
        f'(0,t.jsxs)("a",{{href:"{href}",className:"w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 '
        f'hover:bg-{hover}-500/20 text-{text}-200 hover:text-white transition-all border border-transparent '
        f'hover:border-{hover}-500/30 overflow-hidden text-sm",onClick:()=>r(!1),'
        f'children:[(0,t.jsx)("span",{{className:"text-base",children:"{emoji}"}})," {label}"]}})'
    )

def _j_sub_link(href, label, dot_color):
    return (
        f'(0,t.jsxs)("a",{{href:"{href}",className:"w-full text-left px-3 py-1.5 rounded-lg flex items-center gap-2 '
        f'hover:bg-white/10 text-gray-300 hover:text-white transition-all text-xs '
        f'border border-transparent hover:border-white/10",onClick:()=>r(!1),'
        f'children:[(0,t.jsx)("span",{{className:"w-1.5 h-1.5 rounded-full flex-shrink-0",'
        f'style:{{background:"{dot_color}"}}}})," {label}"]}})'
    )

def _j_category(cat):
    links_jsx = ','.join([_j_sub_link(l["href"], l["label"], l["dot"]) for l in cat["links"]])
    return (
        f'(0,t.jsxs)("details",{{className:"group/{cat["id"]}",children:['
        f'(0,t.jsxs)("summary",{{className:"w-full text-left px-3 py-1.5 rounded-lg flex items-center gap-2 '
        f'hover:bg-white/5 text-gray-400 hover:text-white transition-all cursor-pointer list-none text-xs font-semibold",'
        f'children:[" {cat["emoji"]} {cat["title"]} ",'
        f'(0,t.jsx)("span",{{className:"ml-auto group-open/{cat["id"]}:rotate-180 transition-transform text-[10px] opacity-60",children:"\\u25bc"}})]}})'
        f',(0,t.jsxs)("div",{{className:"space-y-0.5 mt-0.5 ml-3",children:[{links_jsx}]}})]}})'
    )

def _j_submenu(item):
    inner_parts = []
    # Overview link
    if "overview" in item:
        ov = item["overview"]
        inner_parts.append(_j_sub_link(ov["href"], ov["label"], ov["dot"]))
    # Categories
    for cat in item.get("categories", []):
        inner_parts.append(_j_category(cat))
    inner_jsx = ','.join(inner_parts)

    return (
        f'(0,t.jsxs)("details",{{className:"group/{item["id"]}",children:['
        f'(0,t.jsxs)("summary",{{className:"w-full text-left px-4 py-2 rounded-xl flex items-center gap-3 '
        f'hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all cursor-pointer list-none text-sm",'
        f'children:[" {item["emoji"]} {item["title"]} ",'
        f'(0,t.jsx)("span",{{className:"ml-auto group-open/{item["id"]}:rotate-180 transition-transform text-xs opacity-60",children:"\\u25bc"}})]}})'
        f',(0,t.jsxs)("div",{{className:"space-y-0.5 mt-1 ml-3",children:[{inner_jsx}]}})]}})'
    )

def _j_section(section):
    inner_parts = []
    if "children" in section:
        for child in section["children"]:
            if child["type"] == "submenu":
                inner_parts.append(_j_submenu(child))
            elif child["type"] == "link":
                inner_parts.append(_j_link(child["href"], child["emoji"], child["label"],
                                           child["hover"], child["text"]))
    if "links" in section:
        for link in section["links"]:
            inner_parts.append(_j_link(link["href"], link["emoji"], link["label"],
                                       link["hover"], link["text"]))

    inner_jsx = ','.join(inner_parts)

    return (
        f'(0,t.jsxs)("details",{{className:"group/{section["id"]}",children:['
        f'(0,t.jsxs)("summary",{{className:"w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 '
        f'hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all cursor-pointer list-none text-sm",'
        f'children:[" {section["emoji"]} {section["title"]} ",'
        f'(0,t.jsx)("span",{{className:"ml-auto group-open/{section["id"]}:rotate-180 transition-transform text-xs opacity-60",children:"\\u25bc"}})]}})'
        f',(0,t.jsxs)("div",{{className:"space-y-0.5 mt-1 ml-4",children:[{inner_jsx}]}})]}})'
    )

def generate_jsx():
    """Generate the full OTHER STUFF section JSX for the React chunk."""
    parts = []

    # Gold glow header
    parts.append(
        '(0,t.jsx)("div",{className:"px-3 py-2.5 mx-1 mb-1 rounded-xl text-center gold-glow-nav",'
        'style:{background:"linear-gradient(90deg,#fbbf24,#f59e0b,#eab308,#f59e0b,#fbbf24)",'
        'backgroundSize:"300% auto",'
        'animation:"goldShimmer 3s ease-in-out infinite",'
        'boxShadow:"0 0 20px rgba(251,191,36,0.4),0 0 40px rgba(251,191,36,0.2)"},'
        'children:(0,t.jsx)("p",{className:"text-[11px] font-black uppercase tracking-[0.2em] text-black/90",'
        'children:"\\u2728 OTHER STUFF \\u2728"})})'
    )

    # Featured links
    for f in FEATURED:
        parts.append(_j_link(f["href"], f["emoji"], f["label"], f["hover"], f["text"]))

    # Sections
    parts.append(_j_section(APPS_AND_TOOLS))
    parts.append(_j_section(MOVIES_TV))
    parts.append(_j_section(IMMERSIVE))
    parts.append(_j_section(DRAFTS))

    all_children = ','.join(parts)

    # Wrap in the section div
    return (
        f'(0,t.jsxs)("div",{{className:"space-y-1 pt-4 border-t border-white/5",children:[{all_children}]}})'
    )


# ═══════════════════════════════════════════════════════════════════════
# PATCHING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def patch_index_html():
    """Replace the OTHER STUFF section in root index.html."""
    print("=== Patching root index.html ===")

    with open(INDEX, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the OTHER STUFF section — look for gold-glow-nav in the Quick Nav area
    quicknav_start = content.find('Quick Nav')
    if quicknav_start == -1:
        # Fallback: not patched yet, look for NETWORK
        print("  ERROR: Quick Nav not found")
        return False

    # Find the gold-glow-nav div (start of OTHER STUFF)
    glow_marker = 'gold-glow-nav'
    glow_idx = content.find(glow_marker, quicknav_start)

    if glow_idx == -1:
        print("  ERROR: gold-glow-nav not found in Quick Nav area")
        return False

    # Back up to find the containing div with border-t
    # Pattern: <!-- OTHER STUFF Section or <div class="space-y-1 pt-4 border-t
    section_start = content.rfind('<div class="space-y-1 pt-4 border-t border-white/5">', quicknav_start, glow_idx)
    # Also check for the comment marker
    comment_start = content.rfind('<!-- OTHER STUFF', quicknav_start, glow_idx)
    if comment_start != -1 and (section_start == -1 or comment_start < section_start):
        section_start = comment_start

    if section_start == -1:
        print("  ERROR: OTHER STUFF section start not found")
        return False

    # Find the Event System Settings button (end marker)
    settings_marker = 'Event System Settings</button>'
    settings_idx = content.find(settings_marker, glow_idx)
    if settings_idx == -1:
        print("  ERROR: Event System Settings end marker not found")
        return False

    # Find the closing </div> after the settings button
    settings_end = settings_idx + len(settings_marker)
    # The section div closes after the settings button
    close_div = content.find('</div>', settings_end)
    if close_div == -1:
        print("  ERROR: Closing div not found after Event System Settings")
        return False
    section_end = close_div + len('</div>')

    old_section = content[section_start:section_end]
    print(f"  Replacing {len(old_section)} chars (pos {section_start}-{section_end})")

    new_html = generate_html()
    new_content = content[:section_start] + new_html + content[section_end:]

    with open(INDEX, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"  OK: {len(content)} -> {len(new_content)} chars")
    return True


def patch_chunk(filepath):
    """Replace the OTHER STUFF section in a React chunk file."""
    if not os.path.exists(filepath):
        print(f"  SKIP (not found): {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the OTHER STUFF section in the chunk
    # Start marker: the div with gold-glow-nav class
    glow_marker = 'gold-glow-nav'
    glow_idx = content.find(glow_marker)
    if glow_idx == -1:
        # Not patched yet — try original NETWORK marker
        if 'children:"NETWORK"' in content:
            print(f"  ERROR: File has NETWORK but no gold-glow-nav. Run patch_quicknav.py first")
        else:
            print(f"  ERROR: Neither gold-glow-nav nor NETWORK found in {filepath}")
        return False

    # Back up to find the section div start
    # Pattern: (0,t.jsxs)("div",{className:"space-y-1 pt-4 border-t border-white/5"
    section_pattern = '(0,t.jsxs)("div",{className:"space-y-1 pt-4 border-t border-white/5"'
    section_start = content.rfind(section_pattern, 0, glow_idx)
    if section_start == -1:
        print(f"  ERROR: Section div start not found before gold-glow-nav")
        return False

    # Find the Event System Settings button (end marker)
    settings_marker = 'Event System Settings'
    settings_idx = content.find(settings_marker, glow_idx)
    if settings_idx == -1:
        print(f"  ERROR: Event System Settings end marker not found")
        return False

    # The section contains the gold header, all links, groups, AND the settings button
    # Find the closing pattern after Event System Settings: ]})
    # The settings button ends with: "Event System Settings"]})
    # Then the section div closes: ]})
    end_search = settings_idx + len(settings_marker)
    # After "Event System Settings" there's: "]})  then  ]})"
    # Pattern: Event System Settings"]})]}
    # Find "Event System Settings" text and then the closure
    first_close = content.find(']})', end_search)
    if first_close == -1:
        print(f"  ERROR: First close after settings not found")
        return False
    # That closes the button children, then ]}) closes the button, then ]}) closes the section div
    second_close = content.find(']})', first_close + 3)
    if second_close == -1:
        print(f"  ERROR: Second close after settings not found")
        return False

    section_end = second_close + 3  # past the ]}

    # Verify what comes next (should be a comma or the contact support section)
    after = content[section_end:section_end+10]
    print(f"  After section: {repr(after[:10])}")

    old_section = content[section_start:section_end]
    print(f"  Replacing {len(old_section)} chars (pos {section_start}-{section_end})")

    # Build the new section: the outer div wrapper + all content + settings button
    new_jsx = generate_jsx()

    # The settings button JSX
    settings_jsx = (
        ',(0,t.jsxs)("button",{onClick:()=>{o(!0),r(!1)},'
        'className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all overflow-hidden",'
        'children:[(0,t.jsx)("span",{className:"text-lg",children:"\\u2699\\ufe0f"})," Event System Settings"]})'
    )

    # Combine: the OTHER STUFF div already includes the section wrapper
    # But we need to add the settings button INSIDE the section div
    # The generate_jsx() returns: (0,t.jsxs)("div",{className:"space-y-1...",children:[...content...]})
    # We need to insert the settings button before the closing ]})
    # So: strip the trailing ]}) from new_jsx, add settings, re-close
    if new_jsx.endswith(']})'):
        new_section = new_jsx[:-3] + settings_jsx + ']})'
    else:
        print(f"  WARNING: Unexpected JSX ending")
        new_section = new_jsx

    new_content = content[:section_start] + new_section + content[section_end:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"  OK: {os.path.basename(filepath)} ({len(content)} -> {len(new_content)} chars)")
    return True


def main():
    print("=== Full Hierarchy Nav Patcher ===\n")

    # Patch root index.html
    index_ok = patch_index_html()
    print()

    # Patch React chunks
    chunk_ok = 0
    for path in CHUNK_PATHS:
        rel = os.path.relpath(path, REPO)
        print(f"Processing chunk: {rel}")
        if patch_chunk(path):
            chunk_ok += 1
        print()

    print(f"\nDone: index.html={'OK' if index_ok else 'FAIL'}, chunks={chunk_ok}/{len(CHUNK_PATHS)}")
    return 0 if (index_ok and chunk_ok > 0) else 1


if __name__ == "__main__":
    sys.exit(main())
