#!/usr/bin/env python3
"""Patch all blog HTML files so the robot icon opens the AI chat panel
instead of linking to the main site.

Changes:
1. Robot icon <a href="/"> → <a href="#" onclick="FTEAssistant.open()">
2. Adds <script src="/ai-assistant.js"></script> if missing
3. Hides the default #fte-ai-btn (ai-assistant.js creates its own button)

Targets:
- blog3-53 in TORONTOEVENTS_ANTIGRAVITY/build/blog/ (id="ai-bot-btn")
- blog100-149 in TORONTOEVENTS_ANTIGRAVITY/build/blog/ (id="blog-ai-btn")

Blog300-349 use blog_template_base.js (fixed separately in that JS file).

Usage: python tools/patch_blog_ai_chat.py
       python tools/patch_blog_ai_chat.py --replace
"""

import os
import re
import sys

BLOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'TORONTOEVENTS_ANTIGRAVITY', 'build', 'blog')

MARKER = 'ai-assistant.js'

# Two patterns for the robot icon link (blog3-53 vs blog100-149)
PATTERNS = [
    # blog3-53: <a href="/" id="ai-bot-btn"
    (r'<a href="/" id="ai-bot-btn"', '<a href="#" id="ai-bot-btn" onclick="if(window.FTEAssistant){window.FTEAssistant.open();}return false;"'),
    # blog100-149: <a href="/" id="blog-ai-btn"
    (r'<a href="/" id="blog-ai-btn"', '<a href="#" id="blog-ai-btn" onclick="if(window.FTEAssistant){window.FTEAssistant.open();}return false;"'),
]

AI_SCRIPT_TAG = '<script src="/ai-assistant.js"></script>'
HIDE_DEFAULT_BTN = '#fte-ai-btn{display:none!important;}'


def patch_file(filepath, replace_mode=False):
    """Update robot icon to open AI chat and load ai-assistant.js."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    already_patched = MARKER in content

    if already_patched and not replace_mode:
        return 'skip'

    if already_patched and replace_mode:
        # Remove old script tag and CSS to re-apply
        content = content.replace(AI_SCRIPT_TAG, '')
        content = content.replace(HIDE_DEFAULT_BTN, '')
        # Revert onclick back to href="/"
        content = content.replace(
            'href="#" id="ai-bot-btn" onclick="if(window.FTEAssistant){window.FTEAssistant.open();}return false;"',
            'href="/" id="ai-bot-btn"'
        )
        content = content.replace(
            'href="#" id="blog-ai-btn" onclick="if(window.FTEAssistant){window.FTEAssistant.open();}return false;"',
            'href="/" id="blog-ai-btn"'
        )

    # Check if file has any robot icon to patch
    has_icon = False
    for old_pat, new_pat in PATTERNS:
        if old_pat in content:
            has_icon = True
            content = content.replace(old_pat, new_pat)

    if not has_icon and not already_patched:
        return 'no_icon'

    # Add ai-assistant.js script tag before </body> if not present
    if AI_SCRIPT_TAG not in content:
        body_close = content.rfind('</body>')
        if body_close != -1:
            content = content[:body_close] + AI_SCRIPT_TAG + '\n' + content[body_close:]

    # Add CSS to hide default #fte-ai-btn if not present
    if HIDE_DEFAULT_BTN not in content:
        # Find a <style> block to append to, or add inline
        # Look for existing floating buttons style
        style_idx = content.rfind('</style>')
        if style_idx != -1:
            content = content[:style_idx] + '\n' + HIDE_DEFAULT_BTN + '\n' + content[style_idx:]
        else:
            # Add as new style block before </head> or </body>
            head_close = content.find('</head>')
            if head_close != -1:
                content = content[:head_close] + '<style>' + HIDE_DEFAULT_BTN + '</style>\n' + content[head_close:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return 'replaced' if already_patched else 'patched'


def main():
    replace_mode = '--replace' in sys.argv

    if not os.path.isdir(BLOG_DIR):
        print(f'ERROR: Blog directory not found: {BLOG_DIR}')
        return

    # Target ALL HTML files in the blog directory
    import glob
    html_files = glob.glob(os.path.join(BLOG_DIR, '*.html'))

    print(f'Found {len(html_files)} blog HTML files in {BLOG_DIR}')
    if replace_mode:
        print('MODE: Replace existing patches\n')

    counts = {'patched': 0, 'replaced': 0, 'skip': 0, 'no_icon': 0}

    for filepath in sorted(html_files):
        fname = os.path.basename(filepath)
        result = patch_file(filepath, replace_mode)
        counts[result] += 1
        if result in ('patched', 'replaced'):
            print(f'  [{result.upper():8s}] {fname}')
        elif result == 'no_icon':
            print(f'  [NO ICON ] {fname}')

    print(f'\nDone: {counts["patched"]} new, {counts["replaced"]} replaced, '
          f'{counts["skip"]} skipped, {counts["no_icon"]} no icon')


if __name__ == '__main__':
    main()
