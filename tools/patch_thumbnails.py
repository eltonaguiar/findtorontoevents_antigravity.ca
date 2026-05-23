#!/usr/bin/env python3
"""
Patch thumbnail system and ghost card fix on all sites:
  findtorontoevents.ca, torontoevent.net, tdotevent.ca

Removes:
  - GHOST CARD FIX CSS hack
  - 56x56 thumbnail CSS
  - card-thumb-placeholder emoji system
  - startThumbnailEnforcer interval
  - flex-direction:row manipulation
  - Old corrupted fixGhostCards JS (v1-v3)

Adds:
  - Full-width banner thumbnail CSS (width:100%, height:160px/180px)
  - Clean applyThumbnails that inserts at card top
  - Ghost event fix: applyFilters() now hides parent grid containers
  - CSS :has() rule for cards without titles
"""

import re
import sys
import os


# ── The replacement CSS (from tdotevent.ca) ─────────────────────────────
NEW_THUMB_CSS = """\
/* Thumbnail mode: show real event images as full-width banners on cards */
  .card-thumbnail {
    display: none;
    width: 100%;
    height: 160px;
    object-fit: cover;
    border-radius: 12px 12px 0 0;
    flex-shrink: 0;
  }
  @media (min-width: 640px) {
    .card-thumbnail { height: 180px; }
  }
  .thumbnails-on .card-thumbnail {
    display: block;
  }
  /* Ensure card has proper layout for banner thumbnail */
  .thumbnails-on [class*="glass-panel"]:not(.animate-pulse) {
    overflow: hidden;
  }
  /* Ghost card fix: prevent title squeeze when thumbnail takes space */
  .thumbnails-on [class*="glass-panel"]:not(.animate-pulse) h3 {
    flex-shrink: 0;
    min-height: 2.75em;
  }
  /* Ghost card fix: hide card containers without titles (React hydration failure) */
  [class*="glass-panel"]:not(.animate-pulse):not(:has(h3)):not(:has(h2)) {
    display: none !important;
  }"""

# ── The replacement JS function (from tdotevent.ca) ─────────────────────
NEW_APPLY_FN = """\
function applyThumbnails() {
    if (thumbnailsEnabled) {
      document.body.classList.add('thumbnails-on');
    } else {
      document.body.classList.remove('thumbnails-on');
      return;
    }
    var cards = document.querySelectorAll('[class*="glass-panel"]:not(.animate-pulse), [class*="event-card"], [class*="EventCard"]');
    cards.forEach(function(card) {
      if (card.querySelector('.card-thumbnail')) return;
      var titleEl = card.querySelector('h2, h3, [class*="title"], [class*="Title"]');
      if (!titleEl) return;
      var title = (titleEl.textContent || '').trim();
      if (!title) return;
      var imageUrl = null;
      if (window.__RAW_EVENTS__) {
        var ev = window.__RAW_EVENTS__.find(function(e) {
          return (e.title || '').toLowerCase().includes(title.toLowerCase().substring(0, 15));
        });
        if (ev) {
          imageUrl = ev.image || ev.imageUrl || ev.thumbnail || null;
        }
      }
      if (!imageUrl) return;
      var thumb = document.createElement('img');
      thumb.className = 'card-thumbnail';
      thumb.src = imageUrl;
      thumb.alt = title;
      thumb.loading = 'lazy';
      thumb.onerror = function() {
        if (this.parentNode) this.parentNode.removeChild(this);
      };
      card.insertBefore(thumb, card.firstChild);
    });
  }"""


def find_function_end(html, start_pos):
    """Find the closing brace of a function starting at start_pos."""
    brace_count = 0
    started = False
    for i in range(start_pos, len(html)):
        if html[i] == '{':
            brace_count += 1
            started = True
        elif html[i] == '}':
            brace_count -= 1
            if started and brace_count == 0:
                return i + 1
    return start_pos


def patch_file(filepath, label):
    """Patch a site's index.html to use tdotevent.ca's thumbnail system."""

    if not os.path.exists(filepath):
        print(f'  [{label}] File not found, skipping')
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    original_size = len(html)
    print(f'\n{"="*60}')
    print(f'  Patching {label} ({original_size} bytes)')
    print(f'{"="*60}')

    changes = 0

    # ─── PATCH A: Remove GHOST CARD FIX CSS block ─────────────────
    if 'GHOST CARD FIX' in html:
        # Find the comment and remove everything until we hit a line
        # that doesn't look like it's part of the CSS block
        start = html.find('/* GHOST CARD FIX')
        if start >= 0:
            # Find the end: look for the last closing brace in this block
            # The block ends with a rule for mt-auto followed by }
            end = start
            pos = start
            while True:
                next_close = html.find('}', pos + 1)
                if next_close < 0:
                    break
                # Check if there's another CSS rule starting after this brace
                after = html[next_close + 1:next_close + 100].lstrip()
                if after.startswith('.glass-panel') or after.startswith('/*'):
                    pos = next_close
                    end = next_close + 1
                    continue
                else:
                    end = next_close + 1
                    break

            if end > start:
                # Also remove any trailing whitespace/newlines
                while end < len(html) and html[end] in '\r\n ':
                    end += 1
                html = html[:start] + html[end:]
                print(f'  [OK] Removed GHOST CARD FIX CSS block ({end - start} chars)')
                changes += 1
            else:
                print(f'  [WARN] Found GHOST CARD FIX comment but could not determine block end')
    else:
        print(f'  [INFO] No GHOST CARD FIX CSS found')

    # ─── PATCH B: Replace thumbnail CSS ───────────────────────────
    # Find the old .card-thumbnail CSS block (with 56px dimensions)
    thumb_css_comment = html.find('/* Thumbnail mode:')
    if thumb_css_comment < 0:
        thumb_css_comment = html.find('.card-thumbnail {')
        if thumb_css_comment >= 0:
            # Back up to find any comment before it
            prev_comment = html.rfind('/*', max(0, thumb_css_comment - 200), thumb_css_comment)
            if prev_comment >= 0:
                thumb_css_comment = prev_comment

    if thumb_css_comment >= 0:
        # Find the end of the thumbnail CSS section
        # It ends after .thumbnails-on .card-thumb-placeholder { ... }
        # or .thumbnails-on .card-thumbnail { ... } if no placeholder
        end_pos = thumb_css_comment

        # Walk through the CSS blocks
        pos = thumb_css_comment
        for _ in range(10):  # max 10 CSS blocks
            next_brace = html.find('{', pos)
            if next_brace < 0 or next_brace > thumb_css_comment + 2000:
                break
            close_brace = html.find('}', next_brace)
            if close_brace < 0:
                break
            end_pos = close_brace + 1
            pos = close_brace + 1

            # Check what comes next
            remaining = html[pos:pos + 100].strip()
            if (remaining.startswith('.card-thumb') or
                remaining.startswith('.thumbnails-on .card-thumb') or
                remaining.startswith('@media') or
                remaining.startswith('/* Generated') or
                remaining.startswith('/* Ensure')):
                continue
            else:
                break

        if end_pos > thumb_css_comment:
            old_css = html[thumb_css_comment:end_pos]
            html = html[:thumb_css_comment] + NEW_THUMB_CSS + html[end_pos:]
            print(f'  [OK] Replaced thumbnail CSS ({len(old_css)} chars -> {len(NEW_THUMB_CSS)} chars)')
            changes += 1
        else:
            print(f'  [WARN] Could not determine thumbnail CSS block boundaries')
    else:
        if 'width: 100%' in html and '.card-thumbnail' in html:
            print(f'  [INFO] Thumbnail CSS already appears to be full-width')
        else:
            print(f'  [WARN] Could not locate thumbnail CSS section')

    # ─── PATCH C: Replace applyThumbnails function ────────────────
    fn_start = html.find('function applyThumbnails()')
    if fn_start < 0:
        fn_start = html.find('function applyThumbnails ()')

    if fn_start >= 0:
        fn_end = find_function_end(html, fn_start)
        old_fn = html[fn_start:fn_end]

        if 'thumbnailsEnabled' in old_fn or 'thumbnails-on' in old_fn:
            html = html[:fn_start] + NEW_APPLY_FN + html[fn_end:]
            print(f'  [OK] Replaced applyThumbnails function ({len(old_fn)} -> {len(NEW_APPLY_FN)} chars)')
            changes += 1
        else:
            print(f'  [WARN] Found applyThumbnails but content does not match expected')
    else:
        print(f'  [WARN] Could not find applyThumbnails function')

    # ─── PATCH D: Remove startThumbnailEnforcer ───────────────────
    enforcer_start = html.find('function startThumbnailEnforcer')
    if enforcer_start >= 0:
        enforcer_end = find_function_end(html, enforcer_start)

        # Also remove the _thumbInterval variable before it
        pre_start = html.rfind('var _thumbInterval', max(0, enforcer_start - 200), enforcer_start)
        if pre_start >= 0:
            enforcer_start = pre_start

        html = html[:enforcer_start] + html[enforcer_end:]
        print(f'  [OK] Removed startThumbnailEnforcer function')
        changes += 1
    else:
        print(f'  [INFO] No startThumbnailEnforcer found')

    # ─── PATCH E: Clean up references ─────────────────────────────
    old_len = len(html)
    html = html.replace('startThumbnailEnforcer();', '')
    html = html.replace('startThumbnailEnforcer()', '')
    if len(html) != old_len:
        print(f'  [OK] Removed startThumbnailEnforcer() calls')

    # ─── PATCH F: Remove leftover .card-thumb-placeholder CSS ─────
    leftover = re.findall(r'\.card-thumb-placeholder\s*\{[^}]*\}', html)
    for lf in leftover:
        html = html.replace(lf, '')
        print(f'  [OK] Removed leftover .card-thumb-placeholder CSS rule')

    # Also remove .thumbnails-on .card-thumb-placeholder rules
    leftover2 = re.findall(r'\.thumbnails-on\s+\.card-thumb-placeholder\s*\{[^}]*\}', html)
    for lf in leftover2:
        html = html.replace(lf, '')
        print(f'  [OK] Removed leftover .thumbnails-on .card-thumb-placeholder CSS rule')

    # ─── PATCH F2: Remove old ghost card CSS from v1/v2 ──
    old_article_rules = re.findall(r'article\[aria-label[^\}]*\}', html)
    for rule in old_article_rules:
        html = html.replace(rule, '')
        print(f'  [OK] Removed old article[aria-label] CSS rule')

    # Remove old v2 ghost rule that included :not(:has(button)) — too strict
    old_v2 = re.findall(r'\[class\*="glass-panel"\][^{]*:not\(:has\(button\)\)[^}]*\}', html)
    for rule in old_v2:
        html = html.replace(rule, '')
        print(f'  [OK] Removed old v2 ghost card CSS rule (had :not(:has(button)))')

    # ─── PATCH G: Remove old ghost card fix JS (corrupted or outdated) ──────
    # The old fixGhostCards JS may be corrupted (broken querySelectorAll) or
    # embedded inside a shared script block (MovieLinks). We surgically remove
    # just the ghost fix portion, preserving any other code in the same block.
    # The applyFilters() fix (PATCH H below) is the proper solution.
    removed_ghost_js = False
    for attempt in range(5):  # max 5 removal passes
        ghost_pos = html.find('// Ghost card fix')
        if ghost_pos < 0:
            ghost_pos = html.find('function fixGhostCards')
        if ghost_pos < 0:
            break
        # Remove from here to just before the next </script> tag
        script_close = html.find('</script>', ghost_pos)
        if script_close < 0:
            break
        removed_text = html[ghost_pos:script_close]
        html = html[:ghost_pos] + '\n' + html[script_close:]
        print(f'  [OK] Removed ghost fix JS (pass {attempt+1}, {len(removed_text)} chars)')
        removed_ghost_js = True
    # Clean up empty script blocks left after removal
    html = re.sub(r'<script>\s*\n?\s*</script>', '', html)
    if removed_ghost_js:
        changes += 1
    elif 'fixGhostCards' in html:
        print(f'  [WARN] fixGhostCards still present but could not remove')
    else:
        print(f'  [INFO] No old fixGhostCards JS found')

    # ─── PATCH H: Fix ghost events by hiding parent grid containers ──────
    # Root cause: applyFilters() hides inner card via .event-card-hidden
    # but the parent grid item wrapper (div.group.h-[400px]) stays visible,
    # creating blank "ghost" gaps in the grid.
    # Fix: use card.closest('.group') to find and hide the grid wrapper.
    # DOM structure: grid > div.group.h-[400px] > div.h-[320px] > div.glass-panel
    ghost_parent_show = """card.classList.remove('event-card-hidden');
            // Also show the parent grid wrapper to prevent ghost gaps
            var gridItem = card.closest('.group');
            if (gridItem) { gridItem.style.display = ''; }
            shownCount++;"""
    ghost_parent_hide = """card.classList.add('event-card-hidden');
            // Also hide the parent grid wrapper to collapse ghost gaps
            var gridItem = card.closest('.group');
            if (gridItem) { gridItem.style.display = 'none'; }
            hiddenCount++;"""

    # First, remove the old broken parentGridItem version if present
    if 'parentGridItem' in html:
        # The old fix used parentGridItem with wrong DOM level check — replace it
        old_show_pat = re.compile(
            r"card\.classList\.remove\('event-card-hidden'\);\s*\n?"
            r"[^\n]*(?:Restore|Also show)[^\n]*\n?"
            r"(?:\s*var parentGridItem[^\n]*\n?)+"
            r"(?:\s*if \(parentGridItem[^}]*\{[^}]*\}\s*\n?)*"
            r"\s*shownCount\+\+;")
        old_hide_pat = re.compile(
            r"card\.classList\.add\('event-card-hidden'\);\s*\n?"
            r"[^\n]*(?:collapse|Also hide|Also collapse)[^\n]*\n?"
            r"(?:\s*var parentGridItem[^\n]*\n?)+"
            r"(?:\s*if \(parentGridItem[^}]*\{[^}]*\}\s*\n?)*"
            r"\s*hiddenCount\+\+;")
        if old_show_pat.search(html) and old_hide_pat.search(html):
            html = old_show_pat.sub(ghost_parent_show, html, count=1)
            html = old_hide_pat.sub(ghost_parent_hide, html, count=1)
            print(f'  [OK] Replaced old parentGridItem ghost fix with .closest() version')
            changes += 1
        else:
            print(f'  [WARN] parentGridItem found but regex did not match — trying simple replace')
            # Fallback: simple string replacement
            html = html.replace("parentGridItem.style.display = '';",
                               "var gridItem = card.closest('.group'); if (gridItem) { gridItem.style.display = ''; }")
            html = html.replace("parentGridItem.style.display = 'none';",
                               "var gridItem = card.closest('.group'); if (gridItem) { gridItem.style.display = 'none'; }")
            print(f'  [OK] Applied simple parentGridItem → closest(.group) replacement')
            changes += 1
    elif "card.closest('.group')" in html:
        print(f'  [INFO] Ghost parent-hiding fix (.closest) already applied')
    else:
        # Fresh install: find the simple show/hide pattern and inject fix
        show_pat = re.compile(
            r"card\.classList\.remove\('event-card-hidden'\);\s*\n?\s*shownCount\+\+;")
        hide_pat = re.compile(
            r"card\.classList\.add\('event-card-hidden'\);\s*\n?\s*hiddenCount\+\+;")

        if show_pat.search(html) and hide_pat.search(html):
            html = show_pat.sub(ghost_parent_show, html, count=1)
            html = hide_pat.sub(ghost_parent_hide, html, count=1)
            print(f'  [OK] Patched applyFilters() to hide parent grid containers (ghost fix)')
            changes += 1
        else:
            print(f'  [WARN] Could not find applyFilters show/hide pattern to patch')

    # ─── PATCH I: Fix gear icon hidden by overly broad animate-pulse rule ──
    # The CSS rule `.events-loaded .animate-pulse { display: none !important; }`
    # is meant to hide skeleton ghost cards after events load, but it also hides
    # the settings gear FAB which uses animate-pulse for a subtle pulsing effect.
    # Fix: scope the rule to only affect elements inside #events-grid.
    old_pulse_rule = '.events-loaded .animate-pulse'
    new_pulse_rule = '.events-loaded #events-grid .animate-pulse'
    if old_pulse_rule in html and new_pulse_rule not in html:
        html = html.replace(old_pulse_rule, new_pulse_rule)
        print(f'  [OK] Scoped .events-loaded .animate-pulse to #events-grid only (gear icon fix)')
        changes += 1
    elif new_pulse_rule in html:
        print(f'  [INFO] animate-pulse rule already scoped to #events-grid')
    else:
        print(f'  [INFO] No .events-loaded .animate-pulse rule found')

    # ─── Verification ─────────────────────────────────────────────
    has_flex_dir = 'target.style.flexDirection' in html
    has_ghost_fix = 'GHOST CARD FIX' in html
    has_56px = '56px' in html and '.card-thumbnail' in html
    has_placeholder = 'card-thumb-placeholder' in html
    has_fullwidth = 'width: 100%' in html and '.card-thumbnail' in html
    has_enforcer = 'startThumbnailEnforcer' in html
    has_card_insert = 'card.insertBefore(thumb, card.firstChild)' in html
    has_ghost_hydration = 'fixGhostCards' in html
    has_ghost_parent_fix = "card.closest('.group')" in html
    has_old_parent_fix = 'parentGridItem' in html
    has_ghost_css = ':not(:has(h3))' in html
    has_scoped_pulse = '.events-loaded #events-grid .animate-pulse' in html
    has_broad_pulse = '.events-loaded .animate-pulse' in html and not has_scoped_pulse

    print(f'\n  Verification:')
    print(f'    flexDirection in JS:          {has_flex_dir} (want: False)')
    print(f'    GHOST CARD FIX CSS:           {has_ghost_fix} (want: False)')
    print(f'    56px thumbnail size:          {has_56px} (want: False)')
    print(f'    card-thumb-placeholder:       {has_placeholder} (want: False)')
    print(f'    Full-width thumbnails:        {has_fullwidth} (want: True)')
    print(f'    startThumbnailEnforcer:       {has_enforcer} (want: False)')
    print(f'    card.insertBefore at top:     {has_card_insert} (want: True)')
    print(f'    Old fixGhostCards JS:          {has_ghost_hydration} (want: False)')
    print(f'    Ghost .closest(.group) fix:   {has_ghost_parent_fix} (want: True)')
    print(f'    Old parentGridItem (broken):  {has_old_parent_fix} (want: False)')
    print(f'    Ghost card CSS :has() hide:   {has_ghost_css} (want: True)')
    print(f'    Gear icon pulse scoped:       {has_scoped_pulse} (want: True)')
    print(f'    Broad pulse rule (bad):       {has_broad_pulse} (want: False)')
    print(f'    Total changes: {changes}')
    print(f'    File size: {original_size} -> {len(html)} bytes')

    # Check for problems
    problems = []
    if has_flex_dir:
        problems.append('flexDirection still present')
    if has_ghost_fix:
        problems.append('GHOST CARD FIX still present')
    if has_placeholder:
        problems.append('card-thumb-placeholder still present')
    if not has_fullwidth:
        problems.append('full-width thumbnails not found')
    if not has_card_insert:
        problems.append('card.insertBefore not found')
    if has_ghost_hydration:
        problems.append('old fixGhostCards JS still present (should be removed)')
    if not has_ghost_parent_fix:
        problems.append('ghost .closest(.group) fix not applied')
    if has_old_parent_fix:
        problems.append('old broken parentGridItem fix still present')
    if has_broad_pulse:
        problems.append('broad .events-loaded .animate-pulse rule still present (hides gear icon)')

    if problems:
        print(f'\n  [WARN] Remaining issues: {", ".join(problems)}')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    return changes > 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Patch thumbnail system')
    parser.add_argument('--fte', default='/tmp/fte_index.html',
                        help='Path to findtorontoevents.ca index.html')
    parser.add_argument('--tnet', default='/tmp/tnet_index.html',
                        help='Path to torontoevent.net index.html')
    parser.add_argument('--tdot', default='/tmp/tdot_index.html',
                        help='Path to tdotevent.ca index.html')
    args = parser.parse_args()

    fte_ok = patch_file(args.fte, 'findtorontoevents.ca')
    tnet_ok = patch_file(args.tnet, 'torontoevent.net')
    tdot_ok = patch_file(args.tdot, 'tdotevent.ca')

    if not fte_ok and not tnet_ok and not tdot_ok:
        print('\n[ERROR] No patches applied to any site!')
        sys.exit(1)

    print('\n[DONE] Patching complete')
