"""Patch React chunks: add open attributes and glow classes to Quick Nav details elements."""
import os
import glob

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

chunks = glob.glob(os.path.join(REPO, "**", "a2ac3a6616d60872.js"), recursive=True)
chunks = [c for c in chunks if "node_modules" not in c]

REPLACEMENTS = [
    ('className:"group/apps-tools"', 'className:"group/apps-tools",open:!0'),
    ('className:"group/inv-hub"', 'className:"group/inv-hub nav-glow-invhub",open:!0'),
    ('className:"group/movies-tv"', 'className:"group/movies-tv",open:!0'),
    ('className:"group/immersive"', 'className:"group/immersive",open:!0'),
    ('className:"group/games-vr"', 'className:"group/games-vr",open:!0'),
    ('className:"group/drafts"', 'className:"group/drafts",open:!0'),
]

# Also patch Fav Creators link to add glow class
FAV_OLD = 'hover:border-pink-500/30 overflow-hidden text-sm"'
FAV_NEW = 'hover:border-pink-500/30 overflow-hidden text-sm nav-glow-favcreators"'

patched = 0
for chunk_path in chunks:
    with open(chunk_path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    for old, new in REPLACEMENTS:
        if old in content and new not in content:
            content = content.replace(old, new)

    # Fav Creators glow - only first occurrence near the actual Fav Creators link
    if FAV_OLD in content and FAV_NEW not in content:
        # Find the Fav Creators link specifically
        fc_idx = content.find("Fav Creators")
        if fc_idx > 0:
            # Find the nearest FAV_OLD before Fav Creators text
            search_start = max(0, fc_idx - 500)
            segment = content[search_start:fc_idx]
            last_match = segment.rfind(FAV_OLD)
            if last_match >= 0:
                abs_pos = search_start + last_match
                content = content[:abs_pos] + FAV_NEW + content[abs_pos + len(FAV_OLD):]

    if content != original:
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.write(content)
        patched += 1
        print("Patched:", chunk_path)
    else:
        print("Skip:", chunk_path)

print("Done: %d/%d patched" % (patched, len(chunks)))
