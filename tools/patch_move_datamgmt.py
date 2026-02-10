"""
Move Data Management section to right before Support in the nav chunk.
Also add Recommended Gear & Links (affiliates) to NETWORK section.
"""
import os, sys, subprocess

CHUNK = 'next/_next/static/chunks/a2ac3a6616d60872.js'

def patch():
    if not os.path.exists(CHUNK):
        print(f"ERROR: {CHUNK} not found"); return False

    with open(CHUNK, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    original = content

    # ── 1. Move Data Management to right before Support ──────────────
    dm_marker = 'children:"Data Management"'
    support_marker = 'children:"Support"'

    dm_pos = content.find(dm_marker)
    support_pos = content.find(support_marker)

    if dm_pos == -1:
        print("ERROR: 'Data Management' not found in chunk"); return False
    if support_pos == -1:
        print("ERROR: 'Support' not found in chunk"); return False

    if dm_pos > support_pos:
        print("Data Management is already after Support section — skipping move")
    else:
        # Find the start of the Data Management container div
        # Pattern: (0,t.jsxs)("div",{className:"space-y-1 pt-4 border-t border-white/5",children:[
        # Search backward from dm_pos for the opening of this div
        search_back = '(0,t.jsxs)("div",{className:"space-y-1 pt-4 border-t border-white/5",children:['
        dm_div_start = content.rfind(search_back, 0, dm_pos)
        if dm_div_start == -1:
            print("ERROR: Could not find Data Management div start"); return False

        # Find the end of Data Management block
        # The block ends with: accept:".json"})]}),  then NETWORK or next section starts
        dm_end_marker = 'accept:".json"})'
        dm_end_pos = content.find(dm_end_marker, dm_pos)
        if dm_end_pos == -1:
            print("ERROR: Could not find Data Management end marker"); return False
        # After accept:".json"}) comes ]}) to close the div's children array and the div itself
        # Then a comma before the next section
        close_after = dm_end_pos + len(dm_end_marker)
        # Expect: ]}),
        expected_close = ']})'
        if content[close_after:close_after+len(expected_close)] == expected_close:
            dm_block_end = close_after + len(expected_close)
        else:
            print(f"ERROR: Unexpected content after Data Management end: {content[close_after:close_after+20]}")
            return False

        # Extract the Data Management block
        dm_block = content[dm_div_start:dm_block_end]
        print(f"  Found Data Management block: {len(dm_block)} chars (pos {dm_div_start}-{dm_block_end})")

        # Remove Data Management from current position
        # Check what's before and after in context:
        # Before: ...Contact Support"]})]}),  <dm_block>  ,(0,t.jsxs)("div",...NETWORK...
        # We need to handle the comma separator
        # The char before dm_div_start should be a comma
        char_before = content[dm_div_start-1] if dm_div_start > 0 else ''
        char_after = content[dm_block_end] if dm_block_end < len(content) else ''

        if char_before == ',' and char_after == ',':
            # Remove block and one comma: ,<block>,  -> ,
            content = content[:dm_div_start-1] + content[dm_block_end:]
        elif char_before == ',':
            # Remove block and leading comma: ,<block>  -> (nothing)
            content = content[:dm_div_start-1] + content[dm_block_end:]
        elif char_after == ',':
            # Remove block and trailing comma: <block>,  -> (nothing)
            content = content[:dm_div_start] + content[dm_block_end+1:]
        else:
            content = content[:dm_div_start] + content[dm_block_end:]

        print("  Removed Data Management from original position")

        # Find the Support section start (recalculate positions after removal)
        support_div_search = '(0,t.jsxs)("div",{className:"space-y-1 pt-4 border-t border-white/5",children:[(0,t.jsx)("p",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60",children:"Support"})'
        support_div_pos = content.find(support_div_search)
        if support_div_pos == -1:
            print("ERROR: Could not find Support section after removal"); return False

        # Insert Data Management before Support
        # Need a comma separator between the previous section and Data Management
        # Check if there's already a comma before the Support div
        if content[support_div_pos-1] == ',':
            # Insert: <dm_block>,  before Support
            content = content[:support_div_pos] + dm_block + ',' + content[support_div_pos:]
        else:
            content = content[:support_div_pos] + ',' + dm_block + ',' + content[support_div_pos:]

        print("  Inserted Data Management before Support section")

    # ── 2. Add Recommended Gear & Links (affiliates) to NETWORK ──────
    if 'href:"/affiliates/"' not in content:
        # Insert after Accountability Dashboard, before Event System Settings button
        acct_end = '" Accountability Dashboard"]})'
        acct_pos = content.find(acct_end)
        if acct_pos != -1:
            insert_pos = acct_pos + len(acct_end)
            affiliates_link = ',(0,t.jsxs)("a",{href:"/affiliates/",className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-amber-500/20 text-amber-200 hover:text-white transition-all border border-transparent hover:border-amber-500/30 overflow-hidden",onClick:()=>r(!1),children:[(0,t.jsx)("span",{className:"text-lg",children:"\\uD83D\\uDD17"})," Recommended Gear & Links"]})'
            # Fix: use actual unicode, not escaped
            affiliates_link = affiliates_link.replace('\\uD83D\\uDD17', '\U0001F517')
            content = content[:insert_pos] + affiliates_link + content[insert_pos:]
            print("  Added Recommended Gear & Links after Accountability Dashboard")
        else:
            print("  WARNING: Could not find Accountability Dashboard anchor for affiliates link")
    else:
        print("  Affiliates link already present — skipping")

    # ── 3. Write and verify ──────────────────────────────────────────
    if content == original:
        print("No changes made."); return True

    if len(content) < 1000:
        print("ERROR: Content too short after patch; aborting"); return False

    raw = content.encode('utf-8', errors='replace')
    with open(CHUNK, 'wb') as f:
        f.write(raw)
    print(f"  Written {len(raw)} bytes to {CHUNK}")

    # Mirror to other locations
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

    # Verify with acorn
    try:
        check = subprocess.run(
            f'npx acorn "{CHUNK}"',
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True, timeout=15, shell=True
        )
        if check.returncode != 0:
            err = (check.stderr or check.stdout or b"").decode("utf-8", "replace")[:500]
            print(f"ERROR: Chunk has syntax error after patch!")
            print(err)
            return False
        else:
            print("  Acorn syntax check: PASSED")
    except Exception as e:
        print(f"  WARNING: Could not run acorn check: {e}")

    print("Patch successful.")
    return True

if __name__ == '__main__':
    success = patch()
    sys.exit(0 if success else 1)
