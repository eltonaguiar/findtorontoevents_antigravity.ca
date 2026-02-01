import os

def patch():
    files = [
        r'e:\findtorontoevents_antigravity.ca\next\_next\static\chunks\a2ac3a6616d60872.js'
    ]
    
    old_href = 'href:"/favcreators/"'
    new_href = 'href:"/favcreators/#/guest"'
    
    # New Link JS
    new_link_js = r',(0,t.jsxs)("a",{href:"/favcreators/#/guest",className:"w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-red-500/20 text-red-200 hover:text-white transition-all border border-transparent hover:border-red-500/30 overflow-hidden",onClick:()=>r(!1),children:[(0,t.jsx)("span",{className:"text-lg",children:"🔴"})," are your favorite creators live?"]})'
    
    for fpath in files:
        if not os.path.exists(fpath):
            print(f"Skipping {fpath}")
            continue
            
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Update HREF
        if old_href in content:
            content = content.replace(old_href, new_href)
            print(f"Updated HREF in {fpath}")
        elif new_href in content:
             print(f"HREF already updated in {fpath}")
        else:
            print(f"HREF OLD pattern not found in {fpath}")
            
        # 2. Add New Link
        anchor = '" FAVCREATORS"]})'
        if anchor in content:
            if "are your favorite creators live?" not in content:
                content = content.replace(anchor, anchor + new_link_js)
                print(f"Added New Link in {fpath}")
            else:
                 print("New link already present.")
        else:
            print(f"Anchor not found in {fpath}")
            
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)

if __name__ == "__main__":
    patch()
