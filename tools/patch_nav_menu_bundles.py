#!/usr/bin/env python3
"""
Patch JavaScript bundles to update the Quick Nav menu:
1. Add FAVCREATORS link to NETWORK section
2. Move "My Collection" from PLATFORM to new PERSONAL section at bottom
3. Reorganize menu order
"""

import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

def add_favcreators_link(content):
    """Add FAVCREATORS link before System Settings in NETWORK section"""
    
    # Pattern to match the Movies & TV link followed by System Settings
    # We'll insert FAVCREATORS between them
    
    # Look for the Movies & TV link pattern
    movies_pattern = r'(\(0,[a-zA-Z0-9_$]+\.jsx\)\("a",\{[^}]*href:"/MOVIESHOWS/"[^}]*children:\[[^\]]*"Movies & TV"[^\]]*\]\}\))'
    
    # FAVCREATORS link to insert (orange theme)
    favcreators_insert = r',\1,(0,t.jsx)("a",{href:"/favcreators",className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-orange-500/20 text-orange-200 hover:text-white transition-all border border-transparent hover:border-orange-500/30 overflow-hidden",children:[(0,t.jsx)("span",{className:"text-lg",children:"⭐"})," Favorite Creators"]})'
    
    # Try to add after Movies & TV
    modified = re.sub(movies_pattern, favcreators_insert, content, count=1)
    
    if modified != content:
        return modified
    
    # Alternative: Add before System Settings button
    system_pattern = r'(\(0,[a-zA-Z0-9_$]+\.jsx\)\("button",\{[^}]*children:\[[^\]]*System Settings[^\]]*\]\}\))'
    favcreators_before_settings = r'(0,t.jsx)("a",{href:"/favcreators",className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-orange-500/20 text-orange-200 hover:text-white transition-all border border-transparent hover:border-orange-500/30 overflow-hidden",children:[(0,t.jsx)("span",{className:"text-lg",children:"⭐"})," Favorite Creators"]}),\1'
    
    modified = re.sub(system_pattern, favcreators_before_settings, content, count=1)
    
    return modified

def move_my_collection_to_bottom(content):
    """Move My Collection button from PLATFORM to PERSONAL section at bottom"""
    
    # Find and extract My Collection button
    my_collection_pattern = r',?\(0,[a-zA-Z0-9_$]+\.jsx\)\("button",\{[^}]*className:"[^"]*",children:\[\(0,[a-zA-Z0-9_$]+\.jsx\)\("span",\{className:"text-lg",children:"♥"\}\),\(0,[a-zA-Z0-9_$]+\.jsx\)\("span",\{className:"flex-1 truncate",children:"My Collection"\}\),[^\]]*\]\}\)'
    
    # Try to find it
    match = re.search(my_collection_pattern, content)
    if match:
        my_collection_code = match.group(0).lstrip(',')
        # Remove it from current location
        content = content.replace(match.group(0), '')
        
        # Add PERSONAL section with My Collection before Support section
        support_pattern = r'(\(0,[a-zA-Z0-9_$]+\.jsx\)\("p",\{className:"[^"]*",children:"Support"\}\))'
        
        personal_section = f'(0,t.jsx)("div",{{className:"space-y-1 pt-4 border-t border-white/5",children:[(0,t.jsx)("p",{{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60",children:"PERSONAL"}}),{my_collection_code}]}}),(0,t.jsx)("div",{{className:"space-y-1 pt-4 border-white/5",children:[\\1'
        
        content = re.sub(support_pattern, personal_section, content, count=1)
    
    return content

def patch_content(content):
    """Apply all patches to content"""
    original = content
    
    # Add FAVCREATORS link
    content = add_favcreators_link(content)
    
    # Move My Collection to bottom  
    content = move_my_collection_to_bottom(content)
    
    return content

def main():
    changed = []
    
    print("Scanning for JavaScript bundles to patch...")
    
    # Focus on the _next and next directories where bundles are
    search_dirs = [
        ROOT / "_next",
        ROOT / "next",
        ROOT / "TORONTOEVENTS_ANTIGRAVITY" / "_next",
        ROOT / "TORONTOEVENTS_ANTIGRAVITY" / "next",
    ]
    
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
            
        for dirpath, dirnames, filenames in os.walk(search_dir):
            # Skip backup and node_modules directories
            dirnames[:] = [d for d in dirnames if d not in {"node_modules", ".git", "backups"}]
            
            for fn in filenames:
                # Only process JS and HTML files
                if not (fn.endswith('.js') or fn.endswith('.html') or fn.endswith('.htm')):
                    continue
                
                filepath = Path(dirpath) / fn
                
                try:
                    content = filepath.read_text(encoding='utf-8', errors='ignore')
                except Exception as e:
                    continue
                
                # Check if file contains menu-related content
                if not ('My Collection' in content or 'Global Feed' in content):
                    continue
                
                # Apply patches
                patched = patch_content(content)
                
                if patched != content:
                    filepath.write_text(patched, encoding='utf-8', newline='')
                    rel_path = filepath.relative_to(ROOT)
                    changed.append(str(rel_path))
                    print(f"  [PATCHED] {rel_path}")
    
    print(f"\n{'='*60}")
    print(f"PATCHED {len(changed)} FILES")
    print(f"{'='*60}")
    
    if changed:
        print("\nPatched files:")
        for x in changed[:50]:
            print(f"  - {x}")
        if len(changed) > 50:
            print(f"  ... and {len(changed) - 50} more")
    else:
        print("\nNo files needed patching (menu may already be updated or pattern not found)")
    
    return len(changed)

if __name__ == "__main__":
    count = main()
    exit(0 if count >= 0 else 1)
