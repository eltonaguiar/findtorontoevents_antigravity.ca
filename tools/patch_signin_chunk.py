#!/usr/bin/env python3
"""Patch a2ac3a6616d60872.js to add Sign in link in React tree (fix hydration)."""
import os
import re

FILE = "next/_next/static/chunks/a2ac3a6616d60872.js"
WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(WORKSPACE, FILE)

# 1. Top-right: change single child (Config button) to array [Sign-in link, Config button]
OLD_TOP_RIGHT = (
    '"fixed top-6 right-6 z-[200] flex gap-3 pointer-events-none",children:(0,t.jsx)("button",{onClick:i,className:"pointer-events-auto px-4 py-3 bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl hover:bg-[var(--pk-500)] text-white transition-all group overflow-hidden flex items-center gap-2",title:"System Configuration (Top Right)",children:(0,t.jsxs)("div",'
)
# Lock emoji as escaped codepoint (chunk is ASCII-safe)
SIGNIN_LINK = (
    '(0,t.jsxs)("a",{href:"/api/google_auth.php?return_to=/",className:"pointer-events-auto px-4 py-3 bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl hover:bg-[var(--pk-500)] text-white transition-all group overflow-hidden flex items-center gap-2 no-underline",title:"Sign in with Google",children:[(0,t.jsx)("span",{className:"text-xl",children:"\uD83D\uDD12"}),(0,t.jsx)("span",{className:"text-[10px] font-black uppercase tracking-tighter opacity-80 group-hover:opacity-100 transition-all",children:"Sign in"})]}),'
)
NEW_TOP_RIGHT = (
    '"fixed top-6 right-6 z-[200] flex gap-3 pointer-events-none items-center",children:['
    + SIGNIN_LINK
    + '(0,t.jsx)("button",{onClick:i,className:"pointer-events-auto px-4 py-3 bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl hover:bg-[var(--pk-500)] text-white transition-all group overflow-hidden flex items-center gap-2",title:"System Configuration (Top Right)",children:(0,t.jsxs)("div",'
)

# 2. Close the top-right div's children array: after Config button add ] to close array then })
#    Original: ... "Config"})]})})  = span }) + inner ]}) + button }) + outer })
#    New:      ... "Config"})]})])}) = span }) + inner ]}) + button }) + ] + outer })
OLD_CONFIG_CLOSE = 'children:"Config"})]})})'
NEW_CONFIG_CLOSE = 'children:"Config"})]})])})'

# 3. PERSONAL section: add Sign in with Google link before My Collection button
#    Find: PERSONAL section header then button "My Collection"
#    In chunk: "PERSONAL" then later a button with "My Collection"
OLD_PERSONAL_HEADER = '(0,t.jsx)("p",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60",children:"PERSONAL"}),'
SIGNIN_NAV_LINK = '(0,t.jsxs)("a",{href:"/api/google_auth.php?return_to=/",className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 transition-all hover:bg-blue-500/20 text-blue-200 hover:text-white border border-transparent hover:border-blue-500/30 overflow-hidden no-underline",children:[(0,t.jsx)("span",{className:"text-lg",children:"\uD83D\uDD12"}),(0,t.jsx)("span",{className:"flex-1",children:"Sign in with Google"})]}),'
NEW_PERSONAL_HEADER = (
    '(0,t.jsx)("p",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60",children:"PERSONAL"}),'
    + SIGNIN_NAV_LINK
)


def patch():
    if not os.path.exists(PATH):
        print(f"File not found: {PATH}")
        return False
    with open(PATH, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if OLD_TOP_RIGHT not in content:
        print("WARNING: top-right pattern not found (may already be patched)")
    else:
        content = content.replace(OLD_TOP_RIGHT, NEW_TOP_RIGHT)
        print("Patched top-right Sign in link")

    if OLD_CONFIG_CLOSE not in content:
        print("WARNING: Config close pattern not found")
    else:
        content = content.replace(OLD_CONFIG_CLOSE, NEW_CONFIG_CLOSE)
        print("Patched Config button array close")

    if OLD_PERSONAL_HEADER in content and SIGNIN_NAV_LINK not in content:
        content = content.replace(OLD_PERSONAL_HEADER, NEW_PERSONAL_HEADER)
        print("Patched PERSONAL section Sign in link")
    elif "PERSONAL" not in content:
        print("NOTE: PERSONAL section not in chunk (optional)")
    else:
        print("NOTE: PERSONAL already has Sign in or pattern differs")

    if len(content) < 1000:
        print("ERROR: content too short; abort")
        return False
    with open(PATH, "wb") as f:
        f.write(content.encode("utf-8", errors="replace"))

    # Syntax check
    import subprocess
    check = subprocess.run(
        ["npx", "acorn", PATH] if os.name != "nt" else ['npx', 'acorn', PATH],
        cwd=WORKSPACE,
        capture_output=True,
        timeout=15,
        shell=(os.name == "nt"),
    )
    if check.returncode != 0:
        err = (check.stderr or check.stdout or b"").decode("utf-8", "replace")
        print("ERROR: Chunk syntax error:", err[:500])
        return False
    print("Patch successful.")
    return True


if __name__ == "__main__":
    patch()
