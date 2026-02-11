#!/usr/bin/env python3
"""Patch blog300-349 HTML files to show real event images in cards.

These files use blog_template_base.js and override renderEventCard() with text-only
cards. This patch adds an image div (edge-to-edge) at the top of each card when
event.image is available, with fallback to the existing text-only layout.

Usage: python tools/patch_blog300_event_images.py
       python tools/patch_blog300_event_images.py --replace   (re-patch already patched files)
"""

import os
import re
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MARKER = 'event-card-img'

# CSS for event card images (negative margin counters card padding for edge-to-edge)
IMG_CSS = """.event-card-img{height:160px;margin:-1.75rem -1.75rem 1rem;overflow:hidden;border-radius:20px 20px 0 0;position:relative;}
      .event-card-img img{width:100%;height:100%;object-fit:cover;}"""

# The image HTML to insert into renderEventCard
IMG_LINE = """          ${'${'}event.image ? '<div class="event-card-img"><img src="' + event.image + '" alt="" loading="lazy" onerror="this.parentElement.remove()"></div>' : ''}"""

# Old pattern: opening card div followed by h3
OLD_CARD_START = '<div class="event-card" data-category="${event.category || \'general\'}">\n          <h3>'

# New pattern: opening card div, then image, then h3
NEW_CARD_START = '<div class="event-card" data-category="${event.category || \'general\'}">\n          ${event.image ? \'<div class="event-card-img"><img src="\' + event.image + \'" alt="" loading="lazy" onerror="this.parentElement.remove()"></div>\' : \'\'}\n          <h3>'


def patch_file(filepath, replace_mode=False):
    """Add event image support to a blog300-349 file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    already_patched = MARKER in content

    if already_patched and not replace_mode:
        return 'skip'

    if already_patched and replace_mode:
        # Remove old image line from renderEventCard
        content = re.sub(
            r"\n\s*\$\{event\.image \? '<div class=\"event-card-img\">.*?'' : ''\}\n",
            '\n',
            content,
            count=1
        )
        # Remove old CSS
        content = re.sub(
            r'\n\s*\.event-card-img\{[^}]+\}\s*\n\s*\.event-card-img img\{[^}]+\}\s*',
            '',
            content,
            count=1
        )

    # Check for the renderEventCard pattern
    if 'renderEventCard' not in content:
        return 'no_render'

    # Insert image line between card opening div and h3
    old = """<div class="event-card" data-category="${event.category || 'general'}">\n          <h3>"""
    new = """<div class="event-card" data-category="${event.category || 'general'}">\n          ${event.image ? '<div class="event-card-img"><img src="' + event.image + '" alt="" loading="lazy" onerror="this.parentElement.remove()"></div>' : ''}\n          <h3>"""

    if old not in content:
        if already_patched:
            pass
        else:
            return 'no_pattern'

    content = content.replace(old, new, 1)

    # Add CSS for .event-card-img if not present
    if '.event-card-img{' not in content and '.event-card-img {' not in content:
        # Find the .event-card CSS rule and append img CSS after it
        # Look for the theme-specific .event-card:hover rule ending
        hover_match = re.search(r'\.event-card:hover\s*\{[^}]+\}', content)
        if hover_match:
            insert_pos = hover_match.end()
            content = content[:insert_pos] + '\n      ' + IMG_CSS + '\n' + content[insert_pos:]
        else:
            # Fallback: find .event-card rule
            card_match = re.search(r'\.event-card\s*\{[^}]+\}', content)
            if card_match:
                insert_pos = card_match.end()
                content = content[:insert_pos] + '\n      ' + IMG_CSS + '\n' + content[insert_pos:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return 'replaced' if already_patched else 'patched'


def main():
    replace_mode = '--replace' in sys.argv

    html_files = []
    for i in range(300, 350):
        filepath = os.path.join(ROOT_DIR, f'blog{i}.html')
        if os.path.isfile(filepath):
            html_files.append(filepath)

    print(f'Found {len(html_files)} blog template files (blog300-349) in {ROOT_DIR}')
    if replace_mode:
        print('MODE: Replace existing image patches\n')

    counts = {'patched': 0, 'replaced': 0, 'skip': 0, 'no_render': 0, 'no_pattern': 0}

    for filepath in sorted(html_files):
        fname = os.path.basename(filepath)
        result = patch_file(filepath, replace_mode)
        counts[result] += 1
        if result in ('patched', 'replaced'):
            print(f'  [{result.upper():8s}] {fname}')
        elif result == 'no_render':
            print(f'  [NO RENDER] {fname}')
        elif result == 'no_pattern':
            print(f'  [NO PATTERN] {fname}')

    print(f'\nDone: {counts["patched"]} new, {counts["replaced"]} replaced, '
          f'{counts["skip"]} skipped, {counts["no_render"]} no render, '
          f'{counts["no_pattern"]} no pattern')


if __name__ == '__main__':
    main()
