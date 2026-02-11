"""Inject sections-nav into blog200-249 files that don't have it."""
import os
import glob

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAV_HTML = '''<div id="sections-nav" style="position:sticky;top:0;z-index:10000;display:flex;gap:4px;padding:8px 12px;background:rgba(10,10,20,0.95);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,0.08);overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:thin;">
<style>#sections-nav a{display:inline-flex;align-items:center;gap:4px;padding:6px 12px;border-radius:20px;font-size:.75rem;font-weight:600;color:rgba(255,255,255,0.7);text-decoration:none;white-space:nowrap;transition:all .2s;border:1px solid rgba(255,255,255,0.06);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}#sections-nav a:hover{background:rgba(255,255,255,0.1);color:#fff;border-color:rgba(255,255,255,0.15);}@media(max-width:768px){#sections-nav{padding:6px 8px;gap:3px;}#sections-nav a{padding:5px 10px;font-size:.7rem;}}</style>
<a href="/">&#127968; Home</a>
<a href="/WINDOWSFIXER/">&#128295; System Issues</a>
<a href="/MOVIESHOWS/">&#127909; Movies &amp; TV</a>
<a href="/fc/#/guest">&#11088; Fav Creators</a>
<a href="/findstocks/">&#128200; Stock Ideas</a>
<a href="/MENTALHEALTHRESOURCES/">&#129504; Mental Health</a>
<a href="/vr/">&#129405; VR Experience</a>
<a href="/vr/game-arena/">&#127918; Game Arena</a>
<a href="/fc/#/accountability">&#127919; Accountability</a>
<a href="/updates/">&#128203; Updates</a>
<a href="/">&#127775; Other Stuff</a>
<a href="/blog/">&#128240; Blog</a>
</div>
'''

patched = 0
skipped = 0
for i in range(200, 250):
    filepath = os.path.join(REPO, "blog%d.html" % i)
    if not os.path.exists(filepath):
        continue

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "sections-nav" in content:
        skipped += 1
        continue

    # Insert after <body> tag
    body_idx = content.find("<body")
    if body_idx == -1:
        print("WARN: no <body> in %s" % filepath)
        continue

    # Find the closing > of the body tag
    body_close = content.find(">", body_idx)
    if body_close == -1:
        continue

    insert_pos = body_close + 1
    content = content[:insert_pos] + "\n" + NAV_HTML + content[insert_pos:]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    patched += 1

print("Patched: %d, Skipped: %d" % (patched, skipped))
