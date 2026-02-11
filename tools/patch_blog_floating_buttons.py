#!/usr/bin/env python3
"""Patch blog3-53 HTML files to replace hamburger menu with gear + AI bot icons.

Replaces the bottom-right hamburger (&#9776;) with:
1. A gear icon (SVG, opens the existing mega menu)
2. An AI bot icon (links to the main site's AI chatbot)

Matches the main index.html's floating button style.

Usage: python tools/patch_blog_floating_buttons.py
       python tools/patch_blog_floating_buttons.py --replace   (re-patch already patched files)
"""

import os
import re
import sys
import glob

BLOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'TORONTOEVENTS_ANTIGRAVITY', 'build', 'blog')

# The gear SVG icon (matches main site's gear button)
GEAR_SVG = '<svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>'

# AI bot SVG icon
AI_BOT_SVG = '<svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7v1a2 2 0 01-2 2h-1v1a2 2 0 01-2 2H8a2 2 0 01-2-2v-1H5a2 2 0 01-2-2v-1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"></path><circle cx="9" cy="13" r="1.25" fill="currentColor" stroke="none"></circle><circle cx="15" cy="13" r="1.25" fill="currentColor" stroke="none"></circle><path d="M10 17h4" stroke-linecap="round" stroke-width="1.5"></path></svg>'

MARKER = 'id="floating-buttons"'

# CSS + HTML for the floating buttons container
FLOATING_BUTTONS = '''<!-- Floating Buttons: AI Bot + Gear (matching main site) -->
<div id="floating-buttons" style="position:fixed;bottom:20px;right:20px;z-index:998;display:flex;flex-direction:column;gap:12px;align-items:center;">
<a href="#" id="ai-bot-btn" title="AI Chat Assistant" onclick="if(window.FTEAssistant){window.FTEAssistant.open();}return false;" style="width:52px;height:52px;border-radius:50%;background:rgba(0,212,255,0.15);backdrop-filter:blur(10px);border:2px solid rgba(0,212,255,0.3);color:#00d4ff;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all 0.3s;text-decoration:none;box-shadow:0 4px 20px rgba(0,212,255,0.2);">''' + AI_BOT_SVG + '''</a>
<button id="gear-menu-toggle" title="Settings & Navigation" style="width:56px;height:56px;border-radius:50%;background:rgba(255,255,255,0.08);backdrop-filter:blur(10px);border:2px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.8);font-size:1.5rem;cursor:pointer;transition:all 0.3s;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 20px rgba(0,0,0,0.3);">''' + GEAR_SVG + '''</button>
</div>
<style>
#ai-bot-btn:hover{background:rgba(0,212,255,0.25);border-color:rgba(0,212,255,0.5);transform:scale(1.1);box-shadow:0 6px 30px rgba(0,212,255,0.4);}
#gear-menu-toggle:hover{background:rgba(255,255,255,0.15);border-color:rgba(255,255,255,0.3);transform:scale(1.1);box-shadow:0 6px 30px rgba(255,255,255,0.15);}
#gear-menu-toggle.open{transform:rotate(90deg);}
#fte-ai-btn{display:none!important;}
</style>
<script src="/ai-assistant.js"></script>'''


def patch_file(filepath, replace_mode=False):
    """Replace hamburger menu toggle with gear + AI bot floating buttons."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    already_patched = MARKER in content

    if already_patched and not replace_mode:
        return 'skip'

    if already_patched and replace_mode:
        # Remove old floating-buttons block
        content = re.sub(
            r'\n?<!-- Floating Buttons: AI Bot \+ Gear.*?</style>\n?',
            '\n',
            content,
            count=1,
            flags=re.DOTALL
        )

    # Check if file has the hamburger menu-toggle
    if '<button class="menu-toggle" id="menu-toggle"' not in content:
        if already_patched:
            pass  # Was patched before, re-insert
        else:
            return 'no_toggle'

    # Hide the old hamburger button (add display:none) instead of removing it
    # so the mega-menu JS still works
    content = content.replace(
        '<button class="menu-toggle" id="menu-toggle" title="Menu">&#9776;</button>',
        '<button class="menu-toggle" id="menu-toggle" title="Menu" style="display:none;">&#9776;</button>'
    )

    # Also handle already-hidden buttons (for --replace mode)
    content = content.replace(
        'style="display:none;display:none;"',
        'style="display:none;"'
    )

    # Find the mega-menu div and insert floating buttons right before it
    mega_menu_pattern = '<!-- Mega Menu -->'
    idx = content.find(mega_menu_pattern)
    if idx == -1:
        # Try alternative: find the menu-toggle button and insert after it
        toggle_pattern = '</button>\n\n    <!-- Mega Menu'
        idx = content.find(toggle_pattern)
        if idx == -1:
            # Last resort: insert before closing </body>
            idx = content.find('</body>')
            if idx == -1:
                return 'no_insert_point'

    insert_pos = idx
    new_content = content[:insert_pos] + '\n' + FLOATING_BUTTONS + '\n\n    ' + content[insert_pos:]

    # Add JS to wire up the gear button to the existing mega-menu toggle logic
    # Find the existing menu toggle script and add gear button wiring
    gear_script = '''
<script>
document.addEventListener("DOMContentLoaded", function() {
    var gearBtn = document.getElementById("gear-menu-toggle");
    var oldToggle = document.getElementById("menu-toggle");
    var megaMenu = document.getElementById("mega-menu");
    if (gearBtn && megaMenu) {
        gearBtn.addEventListener("click", function() {
            gearBtn.classList.toggle("open");
            megaMenu.classList.toggle("open");
            if (oldToggle) oldToggle.classList.toggle("open");
        });
        megaMenu.addEventListener("click", function(e) {
            if (e.target === megaMenu) {
                gearBtn.classList.remove("open");
                megaMenu.classList.remove("open");
                if (oldToggle) oldToggle.classList.remove("open");
            }
        });
    }
});
</script>'''

    # Insert gear script before </body>
    body_close = new_content.rfind('</body>')
    if body_close != -1:
        new_content = new_content[:body_close] + gear_script + '\n' + new_content[body_close:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return 'replaced' if already_patched else 'patched'


def main():
    replace_mode = '--replace' in sys.argv

    if not os.path.isdir(BLOG_DIR):
        print(f'ERROR: Blog directory not found: {BLOG_DIR}')
        return

    # Only target blog3-53 (the themed files with hamburger menus)
    html_files = []
    for i in range(3, 54):
        filepath = os.path.join(BLOG_DIR, f'blog{i}.html')
        if os.path.isfile(filepath):
            html_files.append(filepath)

    print(f'Found {len(html_files)} blog theme files (blog3-53) in {BLOG_DIR}')
    if replace_mode:
        print('MODE: Replace existing floating buttons\n')

    counts = {'patched': 0, 'replaced': 0, 'skip': 0, 'no_toggle': 0, 'no_insert_point': 0}

    for filepath in sorted(html_files):
        fname = os.path.basename(filepath)
        result = patch_file(filepath, replace_mode)
        counts[result] += 1
        if result in ('patched', 'replaced'):
            print(f'  [{result.upper():8s}] {fname}')
        elif result == 'no_toggle':
            print(f'  [NO TOGGLE] {fname}')
        elif result == 'no_insert_point':
            print(f'  [NO INSERT] {fname}')

    print(f'\nDone: {counts["patched"]} new, {counts["replaced"]} replaced, '
          f'{counts["skip"]} skipped, {counts["no_toggle"]} no toggle, '
          f'{counts["no_insert_point"]} no insert point')


if __name__ == '__main__':
    main()
