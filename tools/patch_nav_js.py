import re, os

def patch_js():
    file_path = 'next/_next/static/chunks/a2ac3a6616d60872.js'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # 1. Rename System Settings to Event System Settings
    content = content.replace('" System Settings"]})', '" Event System Settings"]})')

    # 2. Add tooltip to Windows Boot Fixer (only once; collapse any duplicates)
    title_attr = ',title:"Fixes boot issues such as EFI corrupt, winload.efi missing, or INACCESSIBLE_BOOT_DEVICE."'
    while title_attr + title_attr in content:
        content = content.replace(title_attr + title_attr, title_attr)
    if 'href:"/WINDOWSFIXER/",' in content and title_attr not in content:
        content = content.replace('href:"/WINDOWSFIXER/",', 'href:"/WINDOWSFIXER/"' + title_attr + ',')

    # 2b. Fix 2XKO as separate menu item (restore full link when it was merged/orphaned after Windows Fixer)
    # Broken: " Windows Fixer"]})," 2XKO Frame Data"]}),  -> 2XKO is orphan text; restore full anchor.
    full_2xko_link = '(0,t.jsxs)("a",{href:"/2xko",className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-purple-500/20 text-purple-200 hover:text-white transition-all border border-transparent hover:border-purple-500/30 overflow-hidden",onClick:()=>r(!1),children:[(0,t.jsx)("span",{className:"text-lg",children:"\uD83C\uDFAE"})," 2XKO Frame Data"]}),'
    broken_2xko = '" Windows Fixer"]})," 2XKO Frame Data"]}),'
    fix_2xko_after_windows = '" Windows Boot Fixer"]}),' + full_2xko_link
    if broken_2xko in content:
        content = content.replace(broken_2xko, fix_2xko_after_windows)
    # 2b2. Orphan " 2XKO Frame Data"]}), before Mental Health link — only when there is no full 2XKO link before it (sister chunk already has full link)
    orphan_before_mental = '" 2XKO Frame Data"]}),(0,t.jsxs)("a",{href:"/MENTALHEALTHRESOURCES/"'
    pos = content.find(orphan_before_mental)
    if pos != -1 and content.rfind('href:"/2xko",', 0, pos) == -1:
        content = content.replace(orphan_before_mental, full_2xko_link.rstrip(',') + ',(0,t.jsxs)("a",{href:"/MENTALHEALTHRESOURCES/"')

    # 3. FavCreators nav link: use /fc/#/guest (path /favcreators/ returns 500 on host)
    content = content.replace('href:"/favcreators/"', 'href:"/fc/#/guest"')
    content = content.replace('href:"/favcreators/#/guest"', 'href:"/fc/#/guest"')
    
    # 4. Add /fc/#/guest FAVCREATORS link after Movies & TV if missing (sister and antigravity both get it)
    movies_end = '" Movies & TV"]}),'
    fav_link = '(0,t.jsxs)("a",{href:"/fc/#/guest",className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-rose-500/20 text-rose-200 hover:text-white transition-all border border-transparent hover:border-rose-500/30 overflow-hidden",onClick:()=>r(!1),children:[(0,t.jsx)("span",{className:"text-lg",children:"\u2B50"})," FAVCREATORS"]}),'
    if movies_end in content and '" FAVCREATORS"]' not in content:
        content = content.replace(movies_end, movies_end + fav_link)

    # 5. Remove /findamovie/ link entirely — only when FAVCREATORS present (sister chunk: skip to avoid syntax error; keep comma when removing)
    if '" FAVCREATORS"]' in content:
        content = re.sub(r'\(0,t\.jsxs\)\("a",\{href:"/findamovie/".*?" Find a movie"\]\}\),', ',', content)
        content = content.replace('" Find a movie"', '')

    # 6. Hide old redundant links
    content = content.replace('href:"/FAVCREATOR"', 'href:"/FAVCREATOR",style:{display:"none"}')

    # 6.5. Remove orphaned " 2XKO Frame Data"]}), if present (left by previous patch; causes double comma)
    content = content.replace('" 2XKO Frame Data"]}),,(0,t.jsxs)("a",{href:"/2xko"', '(0,t.jsxs)("a",{href:"/2xko"')
    # 6.6. Fix double comma after Mental Health (breaks NETWORK menu; only 2 items show)
    content = content.replace('" Mental Health Resources"]}),,(0,t.jsxs)("a",{href:"/2xko"', '" Mental Health Resources"]}),(0,t.jsxs)("a",{href:"/2xko"')

    # 7. Reorder 2XKO to bottom (before Event System Settings) — DISABLED: causes bracket/syntax issues; 2XKO stays in NETWORK as link (fixed by 2b2).
    # match_2xko = re.search(r'\(0,t\.jsxs\)\("a",\{href:"/2xko",.*?" 2XKO Frame Data"\]\}\),', content)
    # if match_2xko:
    #     str_2xko = match_2xko.group(0)
    #     content = content.replace(str_2xko, '')
    #     content = content.replace('Event System Settings"]})', 'Event System Settings"]}),' + str_2xko)

    # 8. Add Collapsible (details) to NETWORK section — only when chunk already has details elsewhere (antigravity); skip on sister to avoid bracket imbalance
    if '" FAVCREATORS"]' in content and '(0,t.jsxs)("details",{open:!0,className:"group/nav-section"' in content and '(0,t.jsx)("p",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60",children:"NETWORK"})' in content:
        old_p = '(0,t.jsx)("p",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60",children:"NETWORK"})'
        new_details_start = '(0,t.jsxs)("details",{open:!0,className:"group/nav-section",children:[(0,t.jsxs)("summary",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60 cursor-pointer list-none flex items-center justify-between hover:opacity-100 transition-opacity",children:["NETWORK ",(0,t.jsx)("span",{className:"group-open/nav-section:rotate-180 transition-transform",children:"\u25BC"})]}),(0,t.jsxs)("div",{className:"space-y-1 mt-1",children:['
        content = content.replace(old_p + ',', new_details_start)
        content = content.replace('children:"\uD83D\uDC8E"})," FAVCREATORS"', 'children:"\u2B50"})," FAVCREATORS"')
        content = content.replace('" FAVCREATORS"]}),', '" FAVCREATORS"]})]})]}),')

    # 8a. Flat-structure chunk: move 2XKO and Mental Health after FAVCREATORS (Mental Health just above 2XKO).
    if '" FAVCREATORS"]' in content and '(0,t.jsxs)("details",{open:!0,className:"group/nav-section"' not in content:
        two_xko_link = '(0,t.jsxs)("a",{href:"/2xko",className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-purple-500/20 text-purple-200 hover:text-white transition-all border border-transparent hover:border-purple-500/30 overflow-hidden",onClick:()=>r(!1),children:[(0,t.jsx)("span",{className:"text-lg",children:"\uD83C\uDFAE"})," 2XKO Frame Data"]}),'
        # Remove 2XKO from between Windows Fixer and Mental Health (regex: any emoji encoding in chunk)
        remove_2xko_after_fixer = re.compile(
            r'(" Windows (?:Boot )?Fixer"\]\}\)),(\(0,t\.jsxs\)\("a",\{href:"/2xko",.*?" 2XKO Frame Data"\]\}\),)(\(0,t\.jsxs\)\("a",\{href:"/MENTALHEALTHRESOURCES/")',
            re.DOTALL,
        )
        content = remove_2xko_after_fixer.sub(r'\1,\3', content, count=1)
        # Capture and remove Mental Health from between Windows Fixer and Find Stocks so we can insert it above 2XKO
        # Chunk has " Windows Fixer"]}),  (0,t.jsxs)("a",{href:"/MENTALHEALTHRESOURCES/"... " Mental Health Resources"]}),  (no extra ),)
        mental_health_re = re.compile(
            r'(" Windows (?:Boot )?Fixer"\]\}\)),\s*((\(0,t\.jsxs\)\("a",\{href:"/MENTALHEALTHRESOURCES/".*?" Mental Health Resources"\]\}\),))',
            re.DOTALL,
        )
        mh_match = mental_health_re.search(content)
        mh_link = mh_match.group(2) if mh_match else None
        if mh_match:
            content = mental_health_re.sub(r'\1,', content, count=1)
        # Insert Mental Health right after FAVCREATORS (below FAVCREATORS, above 2XKO) when chunk has FAVCREATORS then 2XKO
        fav_then_2xko_re = re.compile(
            r'(" FAVCREATORS"\]\}\)),\s*\((0,t\.jsxs\)\("a",\{href:"/2xko",)',
        )
        if mh_link and fav_then_2xko_re.search(content):
            content = fav_then_2xko_re.sub(
                r'\1,' + mh_link + r',(\2',
                content,
                count=1,
            )
        fav_then_double_comma = '" FAVCREATORS"]}),,(0,t.jsxs)("button",{onClick:()=>{o(!0),r(!1)},'
        insert_after_fav = (mh_link + ',' if mh_link else '') + two_xko_link
        if fav_then_double_comma in content:
            content = content.replace(fav_then_double_comma, '" FAVCREATORS"]}),' + insert_after_fav + '(0,t.jsxs)("button",{onClick:()=>{o(!0),r(!1)},')
        # If we already have 2XKO after FAVCREATORS but duplicate still after Windows Fixer, remove duplicate
        content = remove_2xko_after_fixer.sub(r'\1,\3', content, count=1)

    # 8b. Move Data Management to bottom: remove from current position, insert collapsible block before 2XKO (second Contact Support / gaming controller).
    data_mgmt_inner = '(0,t.jsxs)("div",{className:"px-4 py-2 grid grid-cols-2 gap-2",children:[(0,t.jsxs)("button",{onClick:()=>x("json"),className:"p-3 bg-white/5 hover:bg-white/10 rounded-xl border border-white/5 flex flex-col items-center gap-1 transition-all group overflow-hidden",title:"Export as JSON",children:[(0,t.jsx)("span",{className:"text-xl group-hover:scale-110 transition-transform",children:"\uD83D\uDCE6"}),(0,t.jsx)("span",{className:"text-[9px] font-black uppercase tracking-wider",children:"JSON"})]}),(0,t.jsxs)("button",{onClick:()=>x("csv"),className:"p-3 bg-white/5 hover:bg-white/10 rounded-xl border border-white/5 flex flex-col items-center gap-1 transition-all group overflow-hidden",title:"Export as CSV",children:[(0,t.jsx)("span",{className:"text-xl group-hover:scale-110 transition-transform",children:"\uD83D\uDCCA"}),(0,t.jsx)("span",{className:"text-[9px] font-black uppercase tracking-wider",children:"CSV"})]}),(0,t.jsxs)("button",{onClick:()=>x("ics"),className:"p-3 bg-white/5 hover:bg-white/10 rounded-xl border border-white/5 flex flex-col items-center gap-1 transition-all group col-span-2 overflow-hidden",title:"Export Calendar File (.ics)",children:[(0,t.jsx)("span",{className:"text-xl group-hover:scale-110 transition-transform",children:"\uD83D\uDCC5"}),(0,t.jsx)("span",{className:"text-[9px] font-black uppercase tracking-wider",children:"Calendar (ICS)"})]})]}),(0,t.jsxs)("button",{onClick:()=>{c.current?.click()},className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all overflow-hidden",children:[(0,t.jsx)("span",{className:"text-lg",children:"\uD83D\uDCE5"})," Import Collection"]}),(0,t.jsx)("input",{type:"file",ref:c,onChange:e=>{let t=e.target.files?.[0];if(!t)return;let a=new FileReader;a.onload=e=>{try{let a=e.target?.result;if(t.name.endsWith(".json")){let e=JSON.parse(a);Array.isArray(e)&&(n(e),alert(`Successfully imported ${e.length} events!`))}else alert("Only JSON import is currently supported.")}catch(e){console.error("Import failed",e),alert("Failed to parse file.")}},a.readAsText(t)},className:"hidden",accept:".json"})'
    data_mgmt_block = ',(0,t.jsxs)("div",{className:"space-y-1 pt-4 border-t border-white/5",children:[(0,t.jsx)("p",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60",children:"Data Management"}),(0,t.jsxs)("div",{className:"px-4 py-2 grid grid-cols-2 gap-2",children:[(0,t.jsxs)("button",{onClick:()=>x("json"),className:"p-3 bg-white/5 hover:bg-white/10 rounded-xl border border-white/5 flex flex-col items-center gap-1 transition-all group overflow-hidden",title:"Export as JSON",children:[(0,t.jsx)("span",{className:"text-xl group-hover:scale-110 transition-transform",children:"\uD83D\uDCE6"}),(0,t.jsx)("span",{className:"text-[9px] font-black uppercase tracking-wider",children:"JSON"})]}),(0,t.jsxs)("button",{onClick:()=>x("csv"),className:"p-3 bg-white/5 hover:bg-white/10 rounded-xl border border-white/5 flex flex-col items-center gap-1 transition-all group overflow-hidden",title:"Export as CSV",children:[(0,t.jsx)("span",{className:"text-xl group-hover:scale-110 transition-transform",children:"\uD83D\uDCCA"}),(0,t.jsx)("span",{className:"text-[9px] font-black uppercase tracking-wider",children:"CSV"})]}),(0,t.jsxs)("button",{onClick:()=>x("ics"),className:"p-3 bg-white/5 hover:bg-white/10 rounded-xl border border-white/5 flex flex-col items-center gap-1 transition-all group col-span-2 overflow-hidden",title:"Export Calendar File (.ics)",children:[(0,t.jsx)("span",{className:"text-xl group-hover:scale-110 transition-transform",children:"\uD83D\uDCC5"}),(0,t.jsx)("span",{className:"text-[9px] font-black uppercase tracking-wider",children:"Calendar (ICS)"})]})]}),(0,t.jsxs)("button",{onClick:()=>{c.current?.click()},className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all overflow-hidden",children:[(0,t.jsx)("span",{className:"text-lg",children:"\uD83D\uDCE5"})," Import Collection"]}),(0,t.jsx)("input",{type:"file",ref:c,onChange:e=>{let t=e.target.files?.[0];if(!t)return;let a=new FileReader;a.onload=e=>{try{let a=e.target?.result;if(t.name.endsWith(".json")){let e=JSON.parse(a);Array.isArray(e)&&(n(e),alert(`Successfully imported ${e.length} events!`))}else alert("Only JSON import is currently supported.")}catch(e){console.error("Import failed",e),alert("Failed to parse file.")}},a.readAsText(t)},className:"hidden",accept:".json"})]}),'
    # Three ]}) close: grid div (inside data_mgmt_inner), mt-1 div, details, outer (Fix 1b: not ]})]})]})],)
    collapsible_data_mgmt = '(0,t.jsxs)("div",{className:"space-y-1 pt-4 border-t border-white/5",children:[(0,t.jsxs)("details",{className:"group/nav-section",children:[(0,t.jsxs)("summary",{className:"px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60 cursor-pointer list-none flex items-center justify-between hover:opacity-100 transition-opacity",children:["DATA MANAGEMENT ",(0,t.jsx)("span",{className:"group-open/nav-section:rotate-180 transition-transform",children:"\u25BC"})]}),(0,t.jsxs)("div",{className:"space-y-1 mt-1",children:[' + data_mgmt_inner + ']})]})]})'
    # 8b: only when chunk already has details (antigravity); skip on sister
    if '" FAVCREATORS"]' in content and '(0,t.jsxs)("details",{open:!0,className:"group/nav-section"' in content:
        if data_mgmt_block in content:
            content = content.replace(data_mgmt_block, ',')
        data_mgmt_block_literal = data_mgmt_block.replace('\uD83D\uDCE6', '\U0001F4E6').replace('\uD83D\uDCCA', '\U0001F4CA').replace('\uD83D\uDCC5', '\U0001F4C5').replace('\uD83D\uDCE5', '\U0001F4E5')
        if data_mgmt_block_literal in content:
            content = content.replace(data_mgmt_block_literal, ',')
        anchor_before_contact = '" 2XKO Frame Data"]}),(0,t.jsxs)("button",{onClick:()=>{p(),r(!1)},'
        insert_collapsible = '" 2XKO Frame Data"]}),' + collapsible_data_mgmt + '),(0,t.jsxs)("button",{onClick:()=>{p(),r(!1)},'
        if anchor_before_contact in content and collapsible_data_mgmt not in content:
            content = content.replace(anchor_before_contact, insert_collapsible)

    # 8c. Fix nav end: wrong ]})})]})} causes "Unexpected token '}'" in browser. Use 4 ]}) then }.
    bad_end = '"Build: 2026-01-29-parallel-fix"})]})]})]})})]})}e.s(["default",()=>r])'
    good_end = '"Build: 2026-01-29-parallel-fix"})]})]})]})}e.s(["default",()=>r])'
    if bad_end in content:
        content = content.replace(bad_end, good_end)
    # 8c2. Alternate nav end — only when chunk has details (antigravity); do not change sister chunk's valid nav end
    if '" FAVCREATORS"]' in content and '(0,t.jsxs)("details",{open:!0,className:"group/nav-section"' in content:
        for bad, good in [
            ('"Build: 2026-01-29-parallel-fix"})]})]})})]})}e.s(["default",()=>r])', '"Build: 2026-01-29-parallel-fix"})]})]})]})}e.s(["default",()=>r])'),
            ('"Build: 2026-01-29-parallel-fix"})]})]})]})})]})}e.s(["default",()=>r])', '"Build: 2026-01-29-parallel-fix"})]})]})]})}e.s(["default",()=>r])'),
        ]:
            if bad in content:
                content = content.replace(bad, good)
                break

    # 9. Mirror to other chunk locations (so menu FavCreators link is /fc/#/guest everywhere)
    targets = [
        'e:/findtorontoevents_antigravity.ca/_next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/_next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/next/_next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/TORONTOEVENTS_ANTIGRAVITY/TORONTOEVENTS_ANTIGRAVITY/_next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/DEPLOY/_next/static/chunks/a2ac3a6616d60872.js',
        'e:/findtorontoevents_antigravity.ca/DEPLOY/next/_next/static/chunks/a2ac3a6616d60872.js',
    ]
    if len(content) < 1000:
        print("ERROR: content too short after patch; aborting write to avoid corrupting chunk.")
        return
    raw = content.encode('utf-8', errors='replace')
    for target in targets:
        if os.path.exists(target):
            try:
                with open(target, 'wb') as f:
                    f.write(raw)
                print(f" Mirrored to {target}")
            except Exception as e:
                print(f" Failed mirroring to {target}: {e}")
    
    # Final write to source
    if os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(raw)

    # Require chunk to parse (no syntax error) before claiming success
    import subprocess
    check = subprocess.run(
        ["npx", "acorn", file_path] if os.name != "nt" else f'npx acorn "{file_path}"',
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True,
        timeout=15,
        shell=(os.name == "nt"),
    )
    if check.returncode != 0:
        err = (check.stderr or check.stdout or b"").decode("utf-8", "replace").encode("ascii", "replace").decode("ascii")
        print("ERROR: Chunk has syntax error (do not pass). Run: python tools/verify_events_loading.py")
        print(err)
        return
    print("Patch successful.")

if __name__ == "__main__":
    patch_js()
