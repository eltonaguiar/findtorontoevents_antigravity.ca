"""Remove the pulsing Contact Support button from the top of the nav in the chunk."""
import os, sys, subprocess

CHUNK = 'next/_next/static/chunks/a2ac3a6616d60872.js'

def patch():
    with open(CHUNK, 'r', encoding='utf-8', errors='replace') as f:
        c = f.read()
    original = c

    # The pulsing Contact Support button is right before the first "]})]})" that leads to NETWORK
    # Pattern: ,(0,t.jsxs)("button",{onClick:()=>{p(),r(!1)},className:"...animate-pulse...",children:[..."Contact Support"]})
    # It appears right after My Collection, before the ]}) that closes the Platform section
    target = 'shadow-lg animate-pulse",children:'
    pos = c.find(target)
    if pos == -1:
        print("Pulsing Contact Support button not found (already removed?)"); return True

    # Search backward for the start of this button element
    search_back = '(0,t.jsxs)("button",{onClick:()=>{p(),r(!1)}'
    btn_start = c.rfind(search_back, 0, pos)
    if btn_start == -1:
        print("ERROR: Could not find button start"); return False

    # Find the end: " Contact Support"]})
    end_marker = '" Contact Support"]})'
    btn_end = c.find(end_marker, pos)
    if btn_end == -1:
        print("ERROR: Could not find button end"); return False
    btn_end += len(end_marker)

    # Check if there's a comma before the button
    if c[btn_start - 1] == ',':
        btn_start -= 1  # include the leading comma

    button_text = c[btn_start:btn_end]
    print(f"  Found pulsing Contact Support button: {len(button_text)} chars at {btn_start}-{btn_end}")
    print(f"  Preview: ...{button_text[:80]}...")

    # Remove
    c = c[:btn_start] + c[btn_end:]

    if c == original:
        print("No changes made"); return True

    if len(c) < 1000:
        print("ERROR: Content too short"); return False

    raw = c.encode('utf-8', errors='replace')
    with open(CHUNK, 'wb') as f:
        f.write(raw)
    print(f"  Written {len(raw)} bytes")

    # Mirror
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

    # Verify
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
