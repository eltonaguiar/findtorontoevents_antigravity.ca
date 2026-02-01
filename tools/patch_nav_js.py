import re, os

def patch_js():
    file_path = 'next/_next/static/chunks/a2ac3a6616d60872.js'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8', errors='surrogateescape') as f:
        content = f.read()

    # 1. Rename System Settings to Event System Settings
    content = content.replace('" System Settings"]})', '" Event System Settings"]})')

    # 2. Add tooltip to Windows Boot Fixer
    # Use hex escaping to bypass WAF for the JS itself just in case
    title_attr = ',title:"Fixes boot issues such as EFI corrupt, winload.efi missing, or INACCESSIBLE_BOOT_DEVICE."'
    content = content.replace('href:"/WINDOWSFIXER/",', 'href:"/WINDOWSFIXER/"' + title_attr + ',')

    # 3. Fix any existing /favcreators/ links to use /favcreators/#/guest
    content = content.replace('href:"/favcreators/"', 'href:"/favcreators/#/guest"')
    
    # 4. Add /favcreators/#/guest FAVCREATORS link if it doesn't exist
    # I'll look for the end of the MOVIESHOWS link and insert there
    movies_end = '" Movies & TV"]}),'
    fav_link = '(0,t.jsxs)("a",{href:"/favcreators/#/guest",className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-rose-500/20 text-rose-200 hover:text-white transition-all border border-transparent hover:border-rose-500/30 overflow-hidden",onClick:()=>r(!1),children:[(0,t.jsx)("span",{className:"text-lg",children:"\uD83D\uDC8E"})," FAVCREATORS"]}),'
    # Only add if the pattern exists and FAVCREATORS link doesn't already exist after Movies & TV
    if movies_end in content and '" FAVCREATORS"]' not in content:
        content = content.replace(movies_end, movies_end + fav_link)

    # 5. Remove /findamovie/ if it exists (it seems to be a stray string)
    content = content.replace('" Find a movie"', '')

    # 6. Hide old redundant links
    content = content.replace('href:"/FAVCREATOR"', 'href:"/FAVCREATOR",style:{display:"none"}')

    # 7. Reorder 2XKO to bottom (before System Settings)
    # This is trickier. I'll extract it and move it.
    # 2XKO pattern: (0,t.jsxs)("a",{href:"/2xko",...})
    match_2xko = re.search(r'\(0,t\.jsxs\)\("a",\{href:"/2xko",.*?\}\),', content)
    if match_2xko:
        str_2xko = match_2xko.group(0)
        content = content.replace(str_2xko, '')
        # Insert before System Settings
        content = content.replace('Event System Settings"]})', 'Event System Settings"]}),' + str_2xko.rstrip(','))

    # 8. Add Collapsible (details) to NETWORK section
    # Anchor: (0,t.jsxs)("div",{className:"space-y-1 pt-4 border-t border-white/5",children:[(0,t.jsx)("p",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60",children:"NETWORK"})
    # I'll replace the <p> with a <details><summary>
    old_p = '(0,t.jsx)("p",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60",children:"NETWORK"})'
    # Use (0,t.jsxs)("details",...) instead of <p>
    new_details_start = '(0,t.jsxs)("details",{className:"group/nav-section",children:[(0,t.jsxs)("summary",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60 cursor-pointer list-none flex items-center justify-between hover:opacity-100 transition-opacity",children:["NETWORK ",(0,t.jsx)("span",{className:"group-open/nav-section:rotate-180 transition-transform",children:"\u25BC"})]}),(0,t.jsxs)("div",{className:"space-y-1 mt-1",children:['
    
    content = content.replace(old_p + ',', new_details_start)
    
    # We need to close the div and details. 
    # I'll close it right after the FAVCREATORS link I added.
    # The links are children of the details-div.
    # I'll find the last link in the list (now FAVCREATORS) and add close tags.
    content = content.replace('" FAVCREATORS"]}),', '" FAVCREATORS"]})]})]})],')

    # 9. Mirror to other chunk locations
    targets = [
        'e:/findtorontoevents_antigravity.ca/_next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/_next/static/chunks/a2ac3a6616d60872.js'
    ]
    for target in targets:
        if os.path.exists(target):
            try:
                with open(target, 'w', encoding='utf-8', errors='surrogateescape') as f:
                    f.write(content)
                print(f" Mirrored to {target}")
            except Exception as e:
                print(f" Failed mirroring to {target}: {e}")
    
    # Final write to source
    if os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8', errors='surrogateescape') as f:
            f.write(content)
    
    print("Patch successful.")

if __name__ == "__main__":
    patch_js()
