"""Move the dashed '--- Contact Support ---' button to just above the Support section in the chunk."""
import os, sys, subprocess

CHUNK = 'next/_next/static/chunks/a2ac3a6616d60872.js'

def patch():
    with open(CHUNK, 'r', encoding='utf-8', errors='replace') as f:
        c = f.read()
    original = c

    # The dashed Contact Support button has unique class: border-dashed
    marker = 'border-dashed'
    pos = c.find(marker)
    if pos == -1:
        print("Dashed Contact Support button not found"); return False

    # Find start of this button element - search backward
    # Pattern: (0,t.jsxs)("button",{onClick:()=>{p(),r(!1)},className:"w-full text-center
    search = '(0,t.jsxs)("button",{onClick:()=>{p(),r(!1)},className:"w-full text-center'
    btn_start = c.rfind(search, 0, pos)
    if btn_start == -1:
        print("ERROR: Could not find dashed button start"); return False

    # Find the end: children:"---"})]})
    end_marker = 'children:"---"})]})'
    btn_end_pos = c.find(end_marker, pos)
    if btn_end_pos == -1:
        print("ERROR: Could not find dashed button end"); return False
    btn_end = btn_end_pos + len(end_marker)

    # Extract the button
    btn_text = c[btn_start:btn_end]
    print(f"  Found dashed Contact Support: {len(btn_text)} chars at {btn_start}-{btn_end}")

    # Remove from current position (handle surrounding commas)
    before = c[btn_start - 1] if btn_start > 0 else ''
    after = c[btn_end] if btn_end < len(c) else ''

    if before == ',' and after == ',':
        c = c[:btn_start - 1] + c[btn_end:]
    elif before == ',':
        c = c[:btn_start - 1] + c[btn_end:]
    elif after == ',':
        c = c[:btn_start] + c[btn_end + 1:]
    else:
        c = c[:btn_start] + c[btn_end:]

    print("  Removed from original position")

    # Find the Support section to insert before
    support_section = '(0,t.jsx)("p",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60",children:"Support"})'
    support_pos = c.find(support_section)
    if support_pos == -1:
        print("ERROR: Could not find Support section"); return False

    # The Support section is inside a div: (0,t.jsxs)("div",{className:"space-y-1...",children:[
    # We want to insert the Contact Support button inside that children array, before the Support <p>
    # So insert: btn_text,  right before the Support <p>
    c = c[:support_pos] + btn_text + ',' + c[support_pos:]
    print("  Inserted dashed Contact Support just above Support section")

    if c == original:
        print("No changes made"); return True

    if len(c) < 1000:
        print("ERROR: Content too short"); return False

    raw = c.encode('utf-8', errors='replace')
    with open(CHUNK, 'wb') as f:
        f.write(raw)
    print(f"  Written {len(raw)} bytes")

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

    check = subprocess.run(
        f'npx acorn "{CHUNK}"',
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True, timeout=15, shell=True
    )
    if check.returncode != 0:
        err = (check.stderr or check.stdout or b"").decode("utf-8", "replace")[:500]
        print(f"ERROR: Chunk syntax error!\n{err}"); return False
    print("  Acorn syntax check: PASSED")
    print("Patch successful.")
    return True

if __name__ == '__main__':
    sys.exit(0 if patch() else 1)
