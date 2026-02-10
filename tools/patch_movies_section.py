"""Replace single Movie Trailers link with collapsible Movies & TV & Trailers section (V1/V2/V3)."""
import os, sys, subprocess

CHUNK = 'next/_next/static/chunks/a2ac3a6616d60872.js'

def patch():
    with open(CHUNK, 'r', encoding='utf-8', errors='replace') as f:
        c = f.read()
    original = c

    # Find the single Movie Trailers link
    marker = '" Movie Trailers"]})'
    pos = c.find(marker)
    if pos == -1:
        print("Movie Trailers link not found (already patched?)"); return True

    # Find the full link start: (0,t.jsxs)("a",{href:"/MOVIESHOWS/"
    link_start_search = '(0,t.jsxs)("a",{href:"/MOVIESHOWS/"'
    link_start = c.rfind(link_start_search, 0, pos)
    if link_start == -1:
        print("ERROR: Could not find Movie Trailers link start"); return False

    link_end = pos + len(marker)
    old_link = c[link_start:link_end]
    print(f"  Found Movie Trailers link: {len(old_link)} chars")

    # Build the collapsible details section with V1, V2, V3
    v1_link = '(0,t.jsxs)("a",{href:"/MOVIESHOWS/",className:"w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-amber-500/20 text-amber-200 hover:text-white transition-all text-sm border border-transparent hover:border-amber-500/30",title:"TikTok-style trailer scroll with Toronto Cineplex & Imagine Cinemas showtimes, IMDb & Rotten Tomatoes ratings",onClick:()=>r(!1),children:[(0,t.jsx)("span",{className:"text-base",children:"\uD83C\uDFAC"})," V1 \u2014 Now Showing"]})'
    v2_link = '(0,t.jsxs)("a",{href:"/movieshows2/",className:"w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-orange-500/20 text-orange-200 hover:text-white transition-all text-sm border border-transparent hover:border-orange-500/30",title:"4,000+ curated titles with genre filters, playlist export & import, and deep TMDB integration",onClick:()=>r(!1),children:[(0,t.jsx)("span",{className:"text-base",children:"\uD83C\uDF9E\uFE0F"})," V2 \u2014 The Film Vault"]})'
    v3_link = '(0,t.jsxs)("a",{href:"/MOVIESHOWS3/",className:"w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-rose-500/20 text-rose-200 hover:text-white transition-all text-sm border border-transparent hover:border-rose-500/30",title:"Create an account, like & save trailers, build your watchlist queue \u2014 TikTok-style auto-scroll player",onClick:()=>r(!1),children:[(0,t.jsx)("span",{className:"text-base",children:"\uD83C\uDF7F"})," V3 \u2014 Binge Mode"]})'

    details_section = (
        '(0,t.jsxs)("details",{className:"group/movies-section",children:['
        '(0,t.jsxs)("summary",{className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-amber-500/20 text-amber-200 hover:text-white transition-all border border-transparent hover:border-amber-500/30 cursor-pointer list-none",children:['
        '(0,t.jsx)("span",{className:"text-lg",children:"\uD83C\uDFAC"}),'
        '" Movies & TV & Trailers ",'
        '(0,t.jsx)("span",{className:"ml-auto group-open/movies-section:rotate-180 transition-transform text-xs opacity-60",children:"\u25BC"})'
        ']}),'
        '(0,t.jsxs)("div",{className:"space-y-1 mt-1 ml-6",children:['
        + v1_link + ',' + v2_link + ',' + v3_link +
        ']})'
        ']})'
    )

    c = c[:link_start] + details_section + c[link_end:]
    print("  Replaced with collapsible Movies & TV & Trailers section (V1/V2/V3)")

    if len(c) < 1000:
        print("ERROR: Content too short"); return False

    raw = c.encode('utf-8', errors='replace')
    with open(CHUNK, 'wb') as f:
        f.write(raw)
    print(f"  Written {len(raw)} bytes")

    mirrors = [
        'e:/findtorontoevents_antigravity.ca/_next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/_next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/next/_next/static/chunks/a2ac3a6616d60872.js',
    ]
    for m in mirrors:
        if os.path.exists(m):
            try:
                with open(m, 'wb') as f:
                    f.write(raw)
                print(f"  Mirrored to {m}")
            except Exception as e:
                print(f"  Mirror failed: {m}: {e}")

    check = subprocess.run(
        f'npx acorn "{CHUNK}"',
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True, timeout=15, shell=True
    )
    if check.returncode != 0:
        err = (check.stderr or check.stdout or b"").decode("utf-8", "replace")[:500]
        print(f"ERROR: Chunk syntax error!\n{err}"); return False
    print("  Acorn syntax check: PASSED")
    print("Patch successful.")
    return True

if __name__ == '__main__':
    sys.exit(0 if patch() else 1)
