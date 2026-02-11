#!/usr/bin/env python3
"""Patch blog3-53 HTML files to show real event images instead of emoji placeholders.

Events in events.json often have an `image` field with a real URL. Currently the blog
card rendering only shows a category emoji on a CSS gradient background. This patch
updates the renderEvents() JS to display the real image (with lazy loading) and fall
back to the emoji + gradient when no image is available.

Usage: python tools/patch_blog_event_images.py
       python tools/patch_blog_event_images.py --replace   (re-patch already patched files)
"""

import os
import re
import sys

BLOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'TORONTOEVENTS_ANTIGRAVITY', 'build', 'blog')

MARKER = 'evt.image ?'

# CSS for the real image inside event-card-img
IMG_CSS = '.event-card-img img{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;}'

# The old emoji-only rendering line (what we're replacing)
OLD_PATTERN = r'<div class="event-card-img">\$\{emoji\}</div>'

# The new rendering: real image (if available) with emoji fallback
# - img is absolutely positioned over the gradient background
# - onerror removes img, revealing the emoji underneath
# - lazy loading for performance
NEW_RENDER = '<div class="event-card-img">${evt.image ? \'<img src="\' + evt.image + \'" alt="" loading="lazy" onerror="this.remove()">\' : \'\'}${emoji}</div>'


def patch_file(filepath, replace_mode=False):
    """Update event card rendering to show real images."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    already_patched = MARKER in content

    if already_patched and not replace_mode:
        return 'skip'

    if already_patched and replace_mode:
        # Revert the image rendering back to emoji-only so we can re-apply
        content = re.sub(
            r'<div class="event-card-img">\$\{evt\.image \?.*?\}\$\{emoji\}</div>',
            '<div class="event-card-img">${emoji}</div>',
            content
        )
        # Remove old img CSS
        content = content.replace(IMG_CSS, '')

    # Check if file has the emoji-only pattern
    if not re.search(OLD_PATTERN, content):
        if already_patched:
            pass  # Was patched before, continue with re-insert
        else:
            return 'no_pattern'

    # Replace the emoji-only rendering with image + emoji fallback
    content = re.sub(OLD_PATTERN, NEW_RENDER, content)

    # Add CSS for the img element (inside the existing <style> block)
    # Find the .event-card-img CSS rule and append img CSS after it
    if IMG_CSS not in content:
        # Insert after the .event-card-img::after rule's closing brace
        after_pattern = r'(\.event-card-img::after\s*\{[^}]+\})'
        match = re.search(after_pattern, content)
        if match:
            insert_pos = match.end()
            content = content[:insert_pos] + '\n        ' + IMG_CSS + '\n' + content[insert_pos:]
        else:
            # Fallback: insert after .event-card-img rule
            img_pattern = r'(\.event-card-img\s*\{[^}]+\})'
            match = re.search(img_pattern, content)
            if match:
                insert_pos = match.end()
                content = content[:insert_pos] + '\n        ' + IMG_CSS + '\n' + content[insert_pos:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return 'replaced' if already_patched else 'patched'


def main():
    replace_mode = '--replace' in sys.argv

    if not os.path.isdir(BLOG_DIR):
        print(f'ERROR: Blog directory not found: {BLOG_DIR}')
        return

    # Target blog3-53 (the themed files with event card rendering)
    html_files = []
    for i in range(3, 54):
        filepath = os.path.join(BLOG_DIR, f'blog{i}.html')
        if os.path.isfile(filepath):
            html_files.append(filepath)

    print(f'Found {len(html_files)} blog theme files (blog3-53) in {BLOG_DIR}')
    if replace_mode:
        print('MODE: Replace existing image patches\n')

    counts = {'patched': 0, 'replaced': 0, 'skip': 0, 'no_pattern': 0}

    for filepath in sorted(html_files):
        fname = os.path.basename(filepath)
        result = patch_file(filepath, replace_mode)
        counts[result] += 1
        if result in ('patched', 'replaced'):
            print(f'  [{result.upper():8s}] {fname}')
        elif result == 'no_pattern':
            print(f'  [NO EMOJI] {fname}')

    print(f'\nDone: {counts["patched"]} new, {counts["replaced"]} replaced, '
          f'{counts["skip"]} skipped, {counts["no_pattern"]} no pattern')


if __name__ == '__main__':
    main()
