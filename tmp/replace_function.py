#!/usr/bin/env python3
import re

# Read the HTML file
with open('fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Read the new function
with open('playMovieFromBrowse_new.js', 'r', encoding='utf-8') as f:
    new_function = f.read()

# Find and replace the playMovieFromBrowse function
# The function starts with "function playMovieFromBrowse(index) {" and ends before "function addToQueueFromBrowse"
pattern = r'function playMovieFromBrowse\(index\) \{[\s\S]*?\}\s*(?=function addToQueueFromBrowse)'

match = re.search(pattern, content)
if match:
    print(f"Found function at position {match.start()}-{match.end()}")
    print(f"Old function length: {len(match.group())}")
    print(f"New function length: {len(new_function)}")
    
    # Replace
    new_content = content[:match.start()] + new_function + content[match.end():]
    
    with open('fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("[OK] Function replaced successfully")
else:
    print("[ERROR] Could not find function to replace")
