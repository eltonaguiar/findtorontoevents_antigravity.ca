#!/usr/bin/env python3
"""Extract theme metadata from blog100-149, blog200-249, blog3-53 → theme-registry.js.

Reads each blog HTML file, extracts colors/fonts/backgrounds, and writes a
JavaScript file with all theme definitions for the theme switcher.

Usage: python tools/extract_themes.py
"""

import os
import re
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_BLOG = os.path.join(REPO, 'TORONTOEVENTS_ANTIGRAVITY', 'build', 'blog')
OUT_FILE = os.path.join(REPO, 'theme-registry.js')

# ── Categories for UI filtering ──
CATEGORIES = {
    # blog100-149 categories (from generate_blog_themes.py)
    100: "Cyberpunk", 101: "Cyberpunk", 102: "Cyberpunk", 103: "Space",
    104: "Cyberpunk", 105: "Cyberpunk", 106: "Cyberpunk", 107: "Space",
    108: "Cyberpunk", 109: "Retro",
    110: "Nature", 111: "Nature", 112: "Nature", 113: "Nature",
    114: "Nature", 115: "Elegant", 116: "Nature", 117: "Nature",
    118: "Nature", 119: "Minimal",
    120: "Retro", 121: "Elegant", 122: "Retro", 123: "Retro",
    124: "Retro", 125: "Light", 126: "Light", 127: "Light",
    128: "Retro", 129: "Light", 130: "Light", 131: "Elegant",
    132: "Light", 133: "Cyberpunk", 134: "Cyberpunk", 135: "Light",
    136: "Light", 137: "Light", 138: "Cyberpunk", 139: "Minimal",
    140: "Elegant", 141: "Elegant", 142: "Light", 143: "Elegant",
    144: "Elegant", 145: "Elegant", 146: "Elegant", 147: "Cyberpunk",
    148: "Cyberpunk", 149: "Minimal",
}


def hex_to_rgb(h):
    """Convert #rrggbb to 'r,g,b' string."""
    h = h.lstrip('#')
    if len(h) < 6:
        return '10,10,20'
    try:
        return '%d,%d,%d' % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return '10,10,20'


def is_dark_theme(bg):
    """Check if a background color is dark."""
    if bg.startswith('linear') or bg.startswith('radial'):
        # Extract first color from gradient
        m = re.search(r'#([0-9a-fA-F]{6})', bg)
        if m:
            bg = '#' + m.group(1)
        else:
            return True
    bg = bg.lstrip('#')
    if len(bg) < 6:
        return True
    try:
        r, g, b = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
        return (r * 299 + g * 587 + b * 114) / 1000 < 128
    except ValueError:
        return True


# ── blog100-149: Extract from generate_blog_themes.py T[] dict ──

def extract_blog100_149():
    """Import theme data directly from generate_blog_themes.py T[] list."""
    import importlib.util
    gen_path = os.path.join(REPO, 'tools', 'generate_blog_themes.py')
    spec = importlib.util.spec_from_file_location('gen', gen_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    themes = []
    for t in mod.T:
        tid = t['id']
        cat = CATEGORIES.get(tid, 'Cyberpunk' if is_dark_theme(t['bg']) else 'Light')
        themes.append({
            'id': 'blog%d' % tid,
            'name': t['n'],
            'tagline': t.get('t', ''),
            'group': '100-149',
            'category': cat,
            'bg': t['bg'],
            'accent': t['ac'],
            'text': t['tx'],
            'cardBg': t['cb'],
            'cardBorder': t['cd'],
            'headingFont': t['hf'],
            'bodyFont': t['bf'],
            'heroBg': t.get('hb', t['bg']),
            'previewUrl': '/blog/blog%d.html' % tid,
        })
    return themes


# ── blog200-249: Parse from HTML files ──

def extract_from_html(filepath, blog_id, group):
    """Parse theme data from an HTML file by extracting CSS values."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract theme name from <title> or theme comment
    name = ''
    # Try theme comment first: <!-- Theme #3: Cyberpunk Neon - Neon-lit digital city -->
    m = re.search(r'<!-- Theme #\d+:\s*([^-]+?)\s*-\s*([^>]+?)-->', content)
    if m:
        name = m.group(1).strip()
    if not name:
        m = re.search(r'<title>[^|]*\|\s*([^<]+)</title>', content)
        if m:
            name = m.group(1).strip()
    if not name:
        m = re.search(r'<title>Toronto Events - ([^|<]+?)(?:\s*Theme|\s*\|)', content)
        if m:
            name = m.group(1).strip()
    if not name:
        name = 'Theme %d' % blog_id

    # Extract tagline from theme comment or meta description
    tagline = ''
    m = re.search(r'<!-- Theme #\d+:\s*[^-]+-\s*([^>]+?)-->', content)
    if m:
        tagline = m.group(1).strip()
    if not tagline:
        m = re.search(r'<meta name="description" content="[^"]*?(?:theme\.\s*|themed experience\.\s*)([^"]*)"', content, re.I)
        if m:
            tagline = m.group(1).strip().rstrip('.')

    # Extract CSS custom properties
    css_vars = {}
    for vm in re.finditer(r'--([a-z0-9_-]+)\s*:\s*([^;]+);', content):
        css_vars[vm.group(1)] = vm.group(2).strip()

    # Extract body background and color
    bg = css_vars.get('bg-dark', '')
    text = css_vars.get('text-1', '')
    accent = css_vars.get('primary', '')

    # Fallback: parse body{} directly
    if not bg:
        m = re.search(r'body\s*\{[^}]*?background:\s*([^;]+);', content)
        if m:
            bg = m.group(1).strip()
    if not text:
        m = re.search(r'body\s*\{[^}]*?color:\s*([^;]+);', content)
        if m:
            text = m.group(1).strip()
    if not accent:
        # Look for the most prominent non-white/non-text color
        m = re.search(r'\.cat-pill\.active\s*\{[^}]*?background:\s*([^;]+);', content)
        if not m:
            m = re.search(r'\.cat-btn\.active\s*\{[^}]*?background:\s*([^;]+);', content)
        if m:
            accent = m.group(1).strip()

    # Resolve var() references
    if bg.startswith('var('):
        vname = bg.strip('var(-)').rstrip(')')
        bg = css_vars.get(vname, '#0a0a1a')
    if text.startswith('var('):
        vname = text.strip('var(-)').rstrip(')')
        text = css_vars.get(vname, '#e0e0e0')

    # Defaults
    bg = bg or '#0a0a1a'
    text = text or '#e0e0e0'
    accent = accent or '#00d4ff'

    # Card background
    card_bg = css_vars.get('card-bg', 'rgba(255,255,255,0.05)')
    card_border = css_vars.get('card-border', 'rgba(255,255,255,0.08)')

    # Fonts
    heading_font = "'Orbitron',sans-serif"
    body_font = "'Inter',sans-serif"
    m = re.search(r'font-family:\s*[\'"]?(Orbitron|VT323|Playfair Display|Space Grotesk|Bangers|Caveat)', content)
    if m:
        heading_font = "'%s',%s" % (m.group(1), 'monospace' if m.group(1) == 'VT323' else 'sans-serif')

    # Hero background
    hero_bg = css_vars.get('bg-dark', bg)
    m = re.search(r'\.hero(?:-section)?\s*\{[^}]*?background:\s*([^;]+);', content)
    if m:
        hero_bg = m.group(1).strip()
        if hero_bg.startswith('var('):
            hero_bg = bg

    # Category
    cat = 'Light' if not is_dark_theme(bg) else 'Cyberpunk'
    name_lower = name.lower()
    if any(k in name_lower for k in ['retro', 'vhs', 'arcade', 'vinyl', 'pixel', 'vaporwave', '80s', '70s']):
        cat = 'Retro'
    elif any(k in name_lower for k in ['nature', 'ocean', 'forest', 'aurora', 'cherry', 'tropical', 'zen', 'garden', 'coral', 'arctic']):
        cat = 'Nature'
    elif any(k in name_lower for k in ['elegant', 'marble', 'gold', 'velvet', 'royal', 'gala', 'jazz', 'noir', 'wine', 'deco']):
        cat = 'Elegant'
    elif any(k in name_lower for k in ['minimal', 'minimalist', 'clean', 'simple']):
        cat = 'Minimal'
    elif any(k in name_lower for k in ['cyber', 'neon', 'matrix', 'tron', 'glitch', 'synth', 'neural', 'quantum', 'holograph', 'tokyo']):
        cat = 'Cyberpunk'
    elif any(k in name_lower for k in ['space', 'star', 'galaxy', 'cosmic', 'nebula', 'particle']):
        cat = 'Space'
    elif any(k in name_lower for k in ['glass', 'blur', 'frost']):
        cat = 'Cyberpunk'
    elif any(k in name_lower for k in ['newspaper', 'typewriter', 'polaroid', 'sketch', 'watercolor', 'comic', 'origami', 'bauhaus', 'pop art', 'brutalist', 'fashion']):
        cat = 'Light'

    return {
        'id': 'blog%d' % blog_id,
        'name': name,
        'tagline': tagline,
        'group': group,
        'category': cat,
        'bg': bg,
        'accent': accent,
        'text': text,
        'cardBg': card_bg,
        'cardBorder': card_border,
        'headingFont': heading_font,
        'bodyFont': body_font,
        'heroBg': hero_bg,
        'previewUrl': '/blog/blog%d.html' % blog_id,
    }


def extract_blog200_249():
    """Extract themes from blog200-249 root HTML files."""
    themes = []
    for i in range(200, 250):
        fp = os.path.join(REPO, 'blog%d.html' % i)
        if not os.path.isfile(fp):
            continue
        t = extract_from_html(fp, i, '200-249')
        themes.append(t)
    return themes


def extract_blog3_53():
    """Extract themes from blog3-53 in build/blog."""
    themes = []
    for i in range(3, 54):
        fp = os.path.join(BUILD_BLOG, 'blog%d.html' % i)
        if not os.path.isfile(fp):
            continue
        t = extract_from_html(fp, i, '3-53')
        themes.append(t)
    return themes


def main():
    all_themes = []

    print('=== Extracting blog100-149 (from generate_blog_themes.py) ===')
    t1 = extract_blog100_149()
    print('  Found %d themes' % len(t1))
    all_themes.extend(t1)

    print('=== Extracting blog200-249 (root HTML) ===')
    t2 = extract_blog200_249()
    print('  Found %d themes' % len(t2))
    all_themes.extend(t2)

    print('=== Extracting blog3-53 (build/blog HTML) ===')
    t3 = extract_blog3_53()
    print('  Found %d themes' % len(t3))
    all_themes.extend(t3)

    # Write theme-registry.js
    js_themes = json.dumps(all_themes, indent=2, ensure_ascii=False)
    js_content = '// Auto-generated by tools/extract_themes.py\n'
    js_content += '// Total themes: %d\n' % len(all_themes)
    js_content += 'window.THEME_REGISTRY = %s;\n' % js_themes

    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print('\n=== Done! ===')
    print('Total: %d themes written to %s' % (len(all_themes), OUT_FILE))

    # Print summary by category
    cats = {}
    for t in all_themes:
        cats.setdefault(t['category'], []).append(t['name'])
    print('\nCategories:')
    for cat in sorted(cats.keys()):
        print('  %s: %d themes' % (cat, len(cats[cat])))


if __name__ == '__main__':
    main()
