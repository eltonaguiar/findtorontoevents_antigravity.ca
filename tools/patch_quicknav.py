"""
Patch the Quick Nav menu in the React chunk file.
Replaces NETWORK + Data Management sections with new "OTHER STUFF" section.
Keeps: Platform (Global Feed, My Collection), Event System Settings, Contact Support.
Removes: Data Management, Import Collection.
"""
import os, shutil, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNK_NAME = "a2ac3a6616d60872.js"

# All known locations of the chunk
CHUNK_PATHS = [
    os.path.join(REPO, "TORONTOEVENTS_ANTIGRAVITY", "_next", "static", "chunks", CHUNK_NAME),
    os.path.join(REPO, "TORONTOEVENTS_ANTIGRAVITY", "next", "_next", "static", "chunks", CHUNK_NAME),
    os.path.join(REPO, "TORONTOEVENTS_ANTIGRAVITY", "next", "static", "chunks", CHUNK_NAME),
    os.path.join(REPO, "TORONTOEVENTS_ANTIGRAVITY", "TORONTOEVENTS_ANTIGRAVITY", "_next", "static", "chunks", CHUNK_NAME),
    # Root-level copies (used by serve_local.py)
    os.path.join(REPO, "next", "_next", "static", "chunks", CHUNK_NAME),
    os.path.join(REPO, "_next", "static", "chunks", CHUNK_NAME),
]

def build_new_section():
    """Build the replacement JSX for the OTHER STUFF section."""

    # Helper: single link item
    def link(href, emoji, label, hover_color, text_color):
        return (
            f'(0,t.jsxs)("a",{{href:"{href}",className:"w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 '
            f'hover:bg-{hover_color}-500/20 text-{text_color}-200 hover:text-white transition-all border border-transparent '
            f'hover:border-{hover_color}-500/30 overflow-hidden text-sm",onClick:()=>r(!1),'
            f'children:[(0,t.jsx)("span",{{className:"text-base",children:"{emoji}"}})," {label}"]}})'
        )

    # Helper: expandable details group
    def details_group(group_id, title, items_jsx):
        return (
            f'(0,t.jsxs)("details",{{className:"group/{group_id}",children:['
            f'(0,t.jsxs)("summary",{{className:"w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 '
            f'hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all cursor-pointer list-none text-sm",'
            f'children:[" {title} ",(0,t.jsx)("span",{{className:"ml-auto group-open/{group_id}:rotate-180 transition-transform text-xs opacity-60",children:"▼"}})]}})'
            f',(0,t.jsxs)("div",{{className:"space-y-0.5 mt-1 ml-4",children:[{items_jsx}]}})]}})'
        )

    # Helper: sub-link inside a details group
    def sub_link(href, emoji, label, hover_color, text_color):
        return (
            f'(0,t.jsxs)("a",{{href:"{href}",className:"w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 '
            f'hover:bg-{hover_color}-500/20 text-{text_color}-200 hover:text-white transition-all text-xs border border-transparent '
            f'hover:border-{hover_color}-500/30",onClick:()=>r(!1),'
            f'children:[(0,t.jsx)("span",{{className:"text-sm",children:"{emoji}"}})," {label}"]}})'
        )

    # Build featured items
    featured = ','.join([
        link("/weather/", "🌤️", "Toronto Weather", "cyan", "cyan"),
        link("/affiliates/", "🔗", "Gear & Links", "amber", "amber"),
        link("/updates/", "🆕", "Latest Updates", "emerald", "emerald"),
        link("/news/", "📰", "News Aggregator", "red", "red"),
        link("/deals/", "🎁", "Deals & Freebies", "amber", "yellow"),
    ])

    # Build Apps & Tools group
    apps_items = ','.join([
        sub_link("/investments/", "💹", "Investment Hub", "green", "green"),
        sub_link("/findstocks/", "📈", "Stock Ideas", "yellow", "yellow"),
        sub_link("/findstocks/portfolio2/dashboard.html", "📊", "Portfolio Dashboard", "indigo", "indigo"),
        sub_link("/findstocks/portfolio2/dividends.html", "💰", "Dividends & Earnings", "green", "green"),
        sub_link("/findcryptopairs/", "₿", "Crypto Scanner", "yellow", "orange"),
        sub_link("/findforex2/", "💱", "Forex Scanner", "cyan", "cyan"),
        sub_link("/live-monitor/goldmine-dashboard.html", "⛏️", "Goldmine Dashboard", "indigo", "indigo"),
        sub_link("/live-monitor/sports-betting.html", "🏀", "Sports Bet Finder", "green", "green"),
    ])
    apps_group = details_group("apps-tools", "📱 Apps & Tools", apps_items)

    # Build Entertainment group
    ent_items = ','.join([
        sub_link("/MOVIESHOWS/", "🎬", "Now Showing", "amber", "amber"),
        sub_link("/movieshows2/", "🎞️", "The Film Vault", "orange", "orange"),
        sub_link("/MOVIESHOWS3/", "🎥", "Binge Mode", "rose", "rose"),
        sub_link("/fc/#/guest", "⭐", "Fav Creators", "pink", "pink"),
    ])
    ent_group = details_group("entertainment", "🎭 Entertainment", ent_items)

    # Build More group
    more_items = ','.join([
        sub_link("/MENTALHEALTHRESOURCES/", "🌟", "Mental Health", "green", "green"),
        sub_link("/WINDOWSFIXER/", "🛠️", "Windows Boot Fixer", "blue", "blue"),
        sub_link("/vr/", "🥽", "VR Experience", "purple", "purple"),
        sub_link("/vr/game-arena/", "🎮", "Game Arena", "violet", "violet"),
        sub_link("/gotjob/", "💼", "GotJob", "cyan", "cyan"),
        sub_link("/blog/", "📝", "Blog", "indigo", "indigo"),
    ])
    more_group = details_group("more-stuff", "🔮 More", more_items)

    # Event System Settings button (preserved from original)
    settings_btn = (
        '(0,t.jsxs)("button",{onClick:()=>{o(!0),r(!1)},'
        'className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all overflow-hidden",'
        'children:[(0,t.jsx)("span",{className:"text-lg",children:"⚙️"})," Event System Settings"]})'
    )

    # Gold glowing header for OTHER STUFF
    gold_header = (
        '(0,t.jsx)("div",{className:"px-3 py-2.5 mx-1 mb-1 rounded-xl text-center gold-glow-nav",'
        'style:{background:"linear-gradient(90deg,#fbbf24,#f59e0b,#eab308,#f59e0b,#fbbf24)",'
        'backgroundSize:"300% auto",'
        'animation:"goldShimmer 3s ease-in-out infinite",'
        'boxShadow:"0 0 20px rgba(251,191,36,0.4),0 0 40px rgba(251,191,36,0.2)"},'
        'children:(0,t.jsx)("p",{className:"text-[11px] font-black uppercase tracking-[0.2em] text-black/90",'
        'children:"✨ OTHER STUFF ✨"})})'
    )

    # Assemble the full section
    section = (
        '(0,t.jsxs)("div",{className:"space-y-1 pt-4 border-t border-white/5",children:['
        + gold_header + ','
        + featured + ','
        + apps_group + ','
        + ent_group + ','
        + more_group + ','
        + settings_btn
        + ']})'
    )

    return section


def patch_chunk(filepath):
    """Patch a single chunk file."""
    if not os.path.exists(filepath):
        print(f"  SKIP (not found): {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find NETWORK section start
    net_marker = 'children:"NETWORK"'
    net_idx = content.find(net_marker)
    if net_idx == -1:
        # Check if already patched
        if 'OTHER STUFF' in content:
            print(f"  SKIP (already patched): {filepath}")
            return True
        print(f"  ERROR: NETWORK marker not found in {filepath}")
        return False

    # Find the div containing NETWORK
    net_div_start = content.rfind('(0,t.jsxs)("div"', 0, net_idx)
    if net_div_start == -1:
        print(f"  ERROR: Could not find NETWORK div start")
        return False

    # Find Data Management section end (after accept:".json"})]}),)
    dm_marker = 'accept:".json"'
    dm_idx = content.find(dm_marker, net_div_start)
    if dm_idx == -1:
        print(f"  ERROR: Data Management end marker not found")
        return False

    # Find the closing pattern })]}) after the accept marker
    close_pattern = '})]})'
    close_idx = content.find(close_pattern, dm_idx)
    if close_idx == -1:
        print(f"  ERROR: Closing pattern not found")
        return False

    # End position is after })]})
    end_pos = close_idx + len(close_pattern)

    # Verify what comes after (should be ,( for the Contact Support section)
    after = content[end_pos:end_pos+5]
    if not after.startswith(',('):
        print(f"  WARNING: Unexpected content after section: {repr(after)}")

    old_section = content[net_div_start:end_pos]
    print(f"  Replacing {len(old_section)} chars (positions {net_div_start}-{end_pos})")

    # Build new section
    new_section = build_new_section()

    # Replace
    new_content = content[:net_div_start] + new_section + content[end_pos:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"  OK: {filepath} ({len(content)} -> {len(new_content)} chars)")
    return True


def main():
    print("=== Patching Quick Nav in React chunks ===\n")

    success = 0
    for path in CHUNK_PATHS:
        print(f"Processing: {os.path.relpath(path, REPO)}")
        if patch_chunk(path):
            success += 1
        print()

    print(f"\nDone: {success}/{len(CHUNK_PATHS)} files patched")
    return 0 if success > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
