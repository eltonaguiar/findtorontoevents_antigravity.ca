#!/usr/bin/env python3
"""Patch all build/blog HTML files to include 10 main sections navigation bar.

Injects a scrollable sections nav bar after the existing top-nav in all
TORONTOEVENTS_ANTIGRAVITY/build/blog/ HTML files.

Usage: python tools/patch_blog_sections_nav.py
       python tools/patch_blog_sections_nav.py --replace   (re-patch already patched files)
"""

import os
import re
import sys
import glob

BLOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'TORONTOEVENTS_ANTIGRAVITY', 'build', 'blog')

# The sections nav bar HTML + inline CSS (icons aligned with main index.html)
# Includes sticky positioning + script to dynamically offset below fixed top-nav
SECTIONS_NAV = '''<div id="sections-nav" style="position:sticky;top:0;z-index:999;display:flex;gap:4px;padding:8px 12px;background:rgba(10,10,20,0.95);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,0.08);overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:thin;">
<style>#sections-nav a{display:inline-flex;align-items:center;gap:4px;padding:6px 12px;border-radius:20px;font-size:.75rem;font-weight:600;color:rgba(255,255,255,0.7);text-decoration:none;white-space:nowrap;transition:all .2s;border:1px solid rgba(255,255,255,0.06);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}#sections-nav a:hover{background:rgba(255,255,255,0.1);color:#fff;border-color:rgba(255,255,255,0.15);}@media(max-width:768px){#sections-nav{padding:6px 8px;gap:3px;}#sections-nav a{padding:5px 10px;font-size:.7rem;}}</style>
<a href="/">\U0001F3E0 Home</a>
<a href="/WINDOWSFIXER/">\U0001F6E0\uFE0F System Issues</a>
<a href="/MOVIESHOWS/">\U0001F3AC Movies &amp; TV</a>
<a href="/fc/#/guest">\u2B50 Fav Creators</a>
<a href="/findstocks/">\U0001F4C8 Stock Ideas</a>
<a href="/MENTALHEALTHRESOURCES/">\U0001F9E0 Mental Health</a>
<a href="/vr/">\U0001F97D VR Experience</a>
<a href="/vr/game-arena/">\U0001F3AE Game Prototypes</a>
<a href="/fc/#/accountability">\U0001F3AF Accountability</a>
<a href="/updates/">\U0001F195 Latest Updates</a>
<a href="/">\U0001F31F Other Stuff</a>
<a href="/blog/">\U0001F4DD Blog</a>
</div>
<script>document.addEventListener("DOMContentLoaded",function(){var n=document.querySelector("nav.top-nav,nav");var s=document.getElementById("sections-nav");if(n&&s){var cs=getComputedStyle(n);if(cs.position==="fixed"){var h=n.offsetHeight;s.style.marginTop=h+"px";s.style.top=h+"px";}}});</script>'''

MARKER = 'id="sections-nav"'


def patch_file(filepath, replace_mode=False):
    """Inject sections nav after </nav> in an HTML file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    already_patched = MARKER in content

    if already_patched and not replace_mode:
        return 'skip'

    if already_patched and replace_mode:
        # Remove old sections-nav block + optional positioning script
        content = re.sub(
            r'\n?<div id="sections-nav"[^>]*>.*?</div>\s*(?:<script>document\.addEventListener\("DOMContentLoaded".*?</script>)?\n?',
            '\n',
            content,
            count=1,
            flags=re.DOTALL
        )

    # Find the closing </nav> tag
    nav_close = '</nav>'
    idx = content.find(nav_close)
    if idx == -1:
        return 'no_nav'

    # Insert sections nav right after </nav>
    insert_pos = idx + len(nav_close)
    new_content = content[:insert_pos] + '\n' + SECTIONS_NAV + '\n' + content[insert_pos:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return 'replaced' if already_patched else 'patched'


def main():
    replace_mode = '--replace' in sys.argv

    if not os.path.isdir(BLOG_DIR):
        print(f'ERROR: Blog directory not found: {BLOG_DIR}')
        return

    html_files = glob.glob(os.path.join(BLOG_DIR, '*.html'))
    print(f'Found {len(html_files)} HTML files in {BLOG_DIR}')
    if replace_mode:
        print('MODE: Replace existing sections-nav\n')

    counts = {'patched': 0, 'replaced': 0, 'skip': 0, 'no_nav': 0}

    for filepath in sorted(html_files):
        fname = os.path.basename(filepath)
        result = patch_file(filepath, replace_mode)
        counts[result] += 1
        if result in ('patched', 'replaced'):
            print(f'  [{result.upper():8s}] {fname}')
        elif result == 'no_nav':
            print(f'  [NO NAV  ] {fname}')

    print(f'\nDone: {counts["patched"]} new, {counts["replaced"]} replaced, '
          f'{counts["skip"]} skipped, {counts["no_nav"]} no nav')


if __name__ == '__main__':
    main()
