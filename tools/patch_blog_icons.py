#!/usr/bin/env python3
"""Add 3 floating icons (AI Bot, Sign In with glow, Gear) to ALL blog pages.

Also fixes blog200-249 overlap where .home-link and .menu-trigger sit on
top of the sections-nav bar.

Groups handled:
  1. blog200-249 (root)       — fix overlap + add 3 floating icons
  2. blog3-53   (build/blog)  — replace 2-icon float with 3-icon version
  3. build/blog articles      — add 3 floating icons
  4. blog300-349 (root)       — handled via blog_template_base.js (separate)

Usage:
  python tools/patch_blog_icons.py
  python tools/patch_blog_icons.py --replace     (re-patch already patched files)
"""

import os
import re
import sys
import glob

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_BLOG = os.path.join(REPO, 'TORONTOEVENTS_ANTIGRAVITY', 'build', 'blog')

MARKER = 'id="blog-float-icons"'

# ── SVG icons ──

GEAR_SVG = '<svg width="22" height="22" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>'

AI_BOT_SVG = '<svg width="22" height="22" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7v1a2 2 0 01-2 2h-1v1a2 2 0 01-2 2H8a2 2 0 01-2-2v-1H5a2 2 0 01-2-2v-1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"></path><circle cx="9" cy="13" r="1.25" fill="currentColor" stroke="none"></circle><circle cx="15" cy="13" r="1.25" fill="currentColor" stroke="none"></circle><path d="M10 17h4" stroke-linecap="round" stroke-width="1.5"></path></svg>'

# ── Universal gear onclick (tries openOtherStuffMenu → mega-menu → navigate) ──
GEAR_ONCLICK = "if(typeof openOtherStuffMenu==='function'){openOtherStuffMenu();}else{var m=document.getElementById('mega-menu');if(m){m.classList.toggle('open');}else{window.location.href='/';}}"

# ── Floating icons HTML + CSS ──

FLOAT_ICONS = '''<!-- Blog Floating Icons: AI Bot, Sign In, Gear -->
<div id="blog-float-icons" style="position:fixed;bottom:20px;right:20px;z-index:998;display:flex;flex-direction:column;gap:10px;align-items:flex-end;">
<a href="/" id="blog-ai-btn" title="AI Chat Assistant" style="width:48px;height:48px;border-radius:50%%;background:rgba(0,212,255,0.12);backdrop-filter:blur(12px);border:1.5px solid rgba(0,212,255,0.25);color:#00d4ff;display:flex;align-items:center;justify-content:center;text-decoration:none;transition:all 0.3s;box-shadow:0 4px 15px rgba(0,212,255,0.15);">%(ai_svg)s</a>
<a href="/fc/#/guest" id="blog-signin-btn" title="Sign In" style="display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:22px;background:rgba(15,10,40,0.9);backdrop-filter:blur(12px);border:1.5px solid rgba(59,130,246,0.3);color:#93c5fd;font-size:0.75rem;font-weight:700;letter-spacing:1.2px;text-decoration:none;transition:all 0.3s;font-family:-apple-system,BlinkMacSystemFont,sans-serif;white-space:nowrap;">&#128274; SIGN IN</a>
<button id="blog-gear-btn" title="Settings &amp; Navigation" onclick="%(gear_onclick)s" style="width:48px;height:48px;border-radius:50%%;background:rgba(255,255,255,0.06);backdrop-filter:blur(12px);border:1.5px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.7);cursor:pointer;transition:all 0.3s;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 15px rgba(0,0,0,0.25);">%(gear_svg)s</button>
</div>
<style>
@keyframes blogSignInGlow{0%%,100%%{box-shadow:0 0 8px rgba(59,130,246,0.4),0 0 16px rgba(59,130,246,0.2);}50%%{box-shadow:0 0 16px rgba(59,130,246,0.6),0 0 32px rgba(59,130,246,0.3);}}
#blog-float-icons #blog-signin-btn{animation:blogSignInGlow 2.5s ease-in-out infinite;}
#blog-float-icons #blog-ai-btn:hover{background:rgba(0,212,255,0.25);border-color:rgba(0,212,255,0.5);transform:scale(1.1);box-shadow:0 6px 25px rgba(0,212,255,0.35);}
#blog-float-icons #blog-signin-btn:hover{background:rgba(59,130,246,0.15);border-color:rgba(59,130,246,0.5);color:#fff;transform:scale(1.05);}
#blog-float-icons #blog-gear-btn:hover{background:rgba(255,255,255,0.12);border-color:rgba(255,255,255,0.25);transform:scale(1.1);box-shadow:0 6px 25px rgba(255,255,255,0.12);}
</style>''' % {
    'ai_svg': AI_BOT_SVG,
    'gear_svg': GEAR_SVG,
    'gear_onclick': GEAR_ONCLICK,
}


def strip_old_floating_buttons(content):
    """Remove old 2-icon floating buttons (from patch_blog_floating_buttons.py)."""
    # Remove the floating-buttons div + style block
    content = re.sub(
        r'\n?<!-- Floating Buttons: AI Bot \+ Gear.*?</style>\n?',
        '\n',
        content,
        count=1,
        flags=re.DOTALL
    )
    # Remove the old gear wiring script
    content = re.sub(
        r'\n?<script>\s*document\.addEventListener\("DOMContentLoaded",\s*function\(\)\s*\{\s*var gearBtn = document\.getElementById\("gear-menu-toggle"\).*?</script>\n?',
        '\n',
        content,
        count=1,
        flags=re.DOTALL
    )
    return content


def strip_new_floating_icons(content):
    """Remove our own blog-float-icons block (for --replace mode)."""
    content = re.sub(
        r'\n?<!-- Blog Floating Icons:.*?</style>\n?',
        '\n',
        content,
        count=1,
        flags=re.DOTALL
    )
    return content


def fix_blog200_overlap(content):
    """Push .home-link and .menu-trigger below the sticky sections-nav (40px tall)."""
    # Push .menu-trigger from top:16px to top:52px
    content = re.sub(
        r'(\.menu-trigger\{[^}]*?)top:\s*16px',
        r'\g<1>top:52px',
        content,
        count=1
    )
    # Push .home-link from top:16px to top:52px
    content = re.sub(
        r'(\.home-link\{[^}]*?)top:\s*16px',
        r'\g<1>top:52px',
        content,
        count=1
    )
    return content


def insert_before_body_close(content, html_block):
    """Insert HTML block right before </body>."""
    idx = content.rfind('</body>')
    if idx == -1:
        return content
    return content[:idx] + html_block + '\n' + content[idx:]


# ── Group 1: blog200-249 (root) ──

def patch_blog200(filepath, replace_mode=False):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    has_new = MARKER in content
    if has_new and not replace_mode:
        return 'skip'
    if has_new and replace_mode:
        content = strip_new_floating_icons(content)

    # Fix overlap
    content = fix_blog200_overlap(content)

    # Insert floating icons before </body>
    content = insert_before_body_close(content, '\n' + FLOAT_ICONS)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return 'replaced' if has_new else 'patched'


# ── Group 2: blog3-53 (build/blog) ──

def patch_blog3_53(filepath, replace_mode=False):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    has_new = MARKER in content
    has_old = 'id="floating-buttons"' in content

    if has_new and not replace_mode:
        return 'skip'

    if has_new and replace_mode:
        content = strip_new_floating_icons(content)

    # Remove old 2-icon floating buttons if present
    if has_old:
        content = strip_old_floating_buttons(content)

    # Insert new 3-icon floating icons before </body>
    content = insert_before_body_close(content, '\n' + FLOAT_ICONS)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return 'replaced' if (has_new or has_old) else 'patched'


# ── Group 3: build/blog articles ──

def patch_article(filepath, replace_mode=False):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    has_new = MARKER in content
    if has_new and not replace_mode:
        return 'skip'
    if has_new and replace_mode:
        content = strip_new_floating_icons(content)

    # Insert floating icons before </body>
    content = insert_before_body_close(content, '\n' + FLOAT_ICONS)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return 'replaced' if has_new else 'patched'


def main():
    replace_mode = '--replace' in sys.argv
    total = {'patched': 0, 'replaced': 0, 'skip': 0, 'error': 0}

    # ── Group 1: blog200-249 ──
    print('=== Group 1: blog200-249 (root) ===')
    g1_counts = {'patched': 0, 'replaced': 0, 'skip': 0}
    for i in range(200, 250):
        fp = os.path.join(REPO, 'blog%d.html' % i)
        if not os.path.isfile(fp):
            continue
        result = patch_blog200(fp, replace_mode)
        g1_counts[result] += 1
        total[result] += 1
        if result in ('patched', 'replaced'):
            print('  [%8s] blog%d.html' % (result.upper(), i))
    print('  Done: %d patched, %d replaced, %d skipped\n' % (
        g1_counts['patched'], g1_counts['replaced'], g1_counts['skip']))

    # ── Group 2: blog3-53 (build/blog) ──
    print('=== Group 2: blog3-53 (build/blog) ===')
    g2_counts = {'patched': 0, 'replaced': 0, 'skip': 0}
    for i in range(3, 54):
        fp = os.path.join(BUILD_BLOG, 'blog%d.html' % i)
        if not os.path.isfile(fp):
            continue
        result = patch_blog3_53(fp, replace_mode)
        g2_counts[result] += 1
        total[result] += 1
        if result in ('patched', 'replaced'):
            print('  [%8s] blog%d.html' % (result.upper(), i))
    print('  Done: %d patched, %d replaced, %d skipped\n' % (
        g2_counts['patched'], g2_counts['replaced'], g2_counts['skip']))

    # ── Group 3: build/blog articles (everything except blog3-53 and index.html) ──
    print('=== Group 3: build/blog articles ===')
    g3_counts = {'patched': 0, 'replaced': 0, 'skip': 0}
    blog_numbered = set('blog%d.html' % i for i in range(3, 54))
    blog_numbered.add('index.html')
    if os.path.isdir(BUILD_BLOG):
        for fp in sorted(glob.glob(os.path.join(BUILD_BLOG, '*.html'))):
            fname = os.path.basename(fp)
            if fname in blog_numbered:
                continue
            result = patch_article(fp, replace_mode)
            g3_counts[result] += 1
            total[result] += 1
            if result in ('patched', 'replaced'):
                print('  [%8s] %s' % (result.upper(), fname))
    print('  Done: %d patched, %d replaced, %d skipped\n' % (
        g3_counts['patched'], g3_counts['replaced'], g3_counts['skip']))

    # ── Group 4: blog index page ──
    print('=== Group 4: blog index (build/blog/index.html) ===')
    idx_fp = os.path.join(BUILD_BLOG, 'index.html')
    if os.path.isfile(idx_fp):
        result = patch_article(idx_fp, replace_mode)
        total[result] += 1
        print('  [%8s] index.html' % result.upper())
    print()

    # ── Summary ──
    print('=' * 50)
    print('TOTAL: %d patched, %d replaced, %d skipped' % (
        total['patched'], total['replaced'], total['skip']))
    print()
    print('NOTE: blog300-349 are handled via blog_template_base.js (run separately)')


if __name__ == '__main__':
    main()
