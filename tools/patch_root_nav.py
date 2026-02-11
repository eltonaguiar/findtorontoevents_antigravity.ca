"""
Patch the root index.html Quick Nav:
1. Add My Collection button to Platform section
2. Replace NETWORK + PERSONAL + Data Management with OTHER STUFF section
3. Keep Contact Support as-is
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")

# The new OTHER STUFF section HTML (matches TORONTOEVENTS_ANTIGRAVITY/index.html)
OTHER_STUFF_HTML = """          <!-- OTHER STUFF Section (Gold Glow) -->
          <div class="space-y-1 pt-4 border-t border-white/5">
            <div class="px-3 py-2.5 mx-1 mb-1 rounded-xl text-center gold-glow-nav">
              <p class="text-[11px] font-black uppercase tracking-[0.2em] text-black/90">\u2728 OTHER STUFF \u2728</p>
            </div>
            <!-- Featured -->
            <a class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 hover:bg-cyan-500/20 text-cyan-200 hover:text-white transition-all border border-transparent hover:border-cyan-500/30 overflow-hidden text-sm" href="/weather/"><span class="text-base">\U0001f324\ufe0f</span> Toronto Weather</a>
            <a class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 hover:bg-amber-500/20 text-amber-200 hover:text-white transition-all border border-transparent hover:border-amber-500/30 overflow-hidden text-sm" href="/affiliates/"><span class="text-base">\U0001f517</span> Gear &amp; Links</a>
            <a class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 hover:bg-emerald-500/20 text-emerald-200 hover:text-white transition-all border border-transparent hover:border-emerald-500/30 overflow-hidden text-sm" href="/updates/"><span class="text-base">\U0001f195</span> Latest Updates</a>
            <a class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 hover:bg-red-500/20 text-red-200 hover:text-white transition-all border border-transparent hover:border-red-500/30 overflow-hidden text-sm" href="/news/"><span class="text-base">\U0001f4f0</span> News Aggregator</a>
            <a class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 hover:bg-amber-500/20 text-yellow-200 hover:text-white transition-all border border-transparent hover:border-amber-500/30 overflow-hidden text-sm" href="/deals/"><span class="text-base">\U0001f381</span> Deals &amp; Freebies</a>
            <!-- Apps & Tools -->
            <details class="group/apps-tools">
              <summary class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all cursor-pointer list-none text-sm">\U0001f4f1 Apps &amp; Tools <span class="ml-auto group-open/apps-tools:rotate-180 transition-transform text-xs opacity-60">\u25bc</span></summary>
              <div class="space-y-0.5 mt-1 ml-4">
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-green-500/20 text-green-200 hover:text-white transition-all text-xs border border-transparent hover:border-green-500/30" href="/investments/"><span class="text-sm">\U0001f4b9</span> Investment Hub</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-yellow-500/20 text-yellow-200 hover:text-white transition-all text-xs border border-transparent hover:border-yellow-500/30" href="/findstocks/"><span class="text-sm">\U0001f4c8</span> Stock Ideas</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-indigo-500/20 text-indigo-200 hover:text-white transition-all text-xs border border-transparent hover:border-indigo-500/30" href="/findstocks/portfolio2/dashboard.html"><span class="text-sm">\U0001f4ca</span> Portfolio Dashboard</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-green-500/20 text-green-200 hover:text-white transition-all text-xs border border-transparent hover:border-green-500/30" href="/findstocks/portfolio2/dividends.html"><span class="text-sm">\U0001f4b0</span> Dividends &amp; Earnings</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-yellow-500/20 text-orange-200 hover:text-white transition-all text-xs border border-transparent hover:border-yellow-500/30" href="/findcryptopairs/"><span class="text-sm">\u20bf</span> Crypto Scanner</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-cyan-500/20 text-cyan-200 hover:text-white transition-all text-xs border border-transparent hover:border-cyan-500/30" href="/findforex2/"><span class="text-sm">\U0001f4b1</span> Forex Scanner</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-indigo-500/20 text-indigo-200 hover:text-white transition-all text-xs border border-transparent hover:border-indigo-500/30" href="/live-monitor/goldmine-dashboard.html"><span class="text-sm">\u26cf\ufe0f</span> Goldmine Dashboard</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-green-500/20 text-green-200 hover:text-white transition-all text-xs border border-transparent hover:border-green-500/30" href="/live-monitor/sports-betting.html"><span class="text-sm">\U0001f3c0</span> Sports Bet Finder</a>
              </div>
            </details>
            <!-- Entertainment -->
            <details class="group/entertainment">
              <summary class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all cursor-pointer list-none text-sm">\U0001f3ad Entertainment <span class="ml-auto group-open/entertainment:rotate-180 transition-transform text-xs opacity-60">\u25bc</span></summary>
              <div class="space-y-0.5 mt-1 ml-4">
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-amber-500/20 text-amber-200 hover:text-white transition-all text-xs border border-transparent hover:border-amber-500/30" href="/MOVIESHOWS/"><span class="text-sm">\U0001f3ac</span> Now Showing</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-orange-500/20 text-orange-200 hover:text-white transition-all text-xs border border-transparent hover:border-orange-500/30" href="/movieshows2/"><span class="text-sm">\U0001f39e\ufe0f</span> The Film Vault</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-rose-500/20 text-rose-200 hover:text-white transition-all text-xs border border-transparent hover:border-rose-500/30" href="/MOVIESHOWS3/"><span class="text-sm">\U0001f3a5</span> Binge Mode</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-pink-500/20 text-pink-200 hover:text-white transition-all text-xs border border-transparent hover:border-pink-500/30" href="/fc/#/guest"><span class="text-sm">\u2b50</span> Fav Creators</a>
              </div>
            </details>
            <!-- More -->
            <details class="group/more-stuff">
              <summary class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-3 hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all cursor-pointer list-none text-sm">\U0001f52e More <span class="ml-auto group-open/more-stuff:rotate-180 transition-transform text-xs opacity-60">\u25bc</span></summary>
              <div class="space-y-0.5 mt-1 ml-4">
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-green-500/20 text-green-200 hover:text-white transition-all text-xs border border-transparent hover:border-green-500/30" href="/MENTALHEALTHRESOURCES/"><span class="text-sm">\U0001f31f</span> Mental Health</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-blue-500/20 text-blue-200 hover:text-white transition-all text-xs border border-transparent hover:border-blue-500/30" href="/WINDOWSFIXER/"><span class="text-sm">\U0001f6e0\ufe0f</span> Windows Boot Fixer</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-purple-500/20 text-purple-200 hover:text-white transition-all text-xs border border-transparent hover:border-purple-500/30" href="/vr/"><span class="text-sm">\U0001f97d</span> VR Experience</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-violet-500/20 text-violet-200 hover:text-white transition-all text-xs border border-transparent hover:border-violet-500/30" href="/vr/game-arena/"><span class="text-sm">\U0001f3ae</span> Game Arena</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-cyan-500/20 text-cyan-200 hover:text-white transition-all text-xs border border-transparent hover:border-cyan-500/30" href="/gotjob/"><span class="text-sm">\U0001f4bc</span> GotJob</a>
                <a class="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2 hover:bg-indigo-500/20 text-indigo-200 hover:text-white transition-all text-xs border border-transparent hover:border-indigo-500/30" href="/blog/"><span class="text-sm">\U0001f4dd</span> Blog</a>
              </div>
            </details>
            <!-- Event System Settings -->
            <button class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-white/5 text-[var(--text-2)] hover:text-white transition-all overflow-hidden">
              <span class="text-lg">\u2699\ufe0f</span> Event System Settings</button>
          </div>"""


def patch():
    if not os.path.exists(INDEX):
        print(f"ERROR: {INDEX} not found")
        return 1

    with open(INDEX, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if already patched (look for the gold-glow-nav header in the nav area)
    if 'gold-glow-nav' in content and 'NETWORK' not in content[content.find('Quick Nav'):content.find('Quick Nav')+5000]:
        print("Already patched (gold-glow-nav in nav, NETWORK removed)")
        return 0

    # === Step 1: Add My Collection to Platform section ===
    # Find "Global Feed</button>" then the closing </div> of Platform section
    gf_marker = 'Global Feed</button>'
    gf_idx = content.find(gf_marker)
    if gf_idx == -1:
        print("ERROR: Global Feed button not found")
        return 1

    # Find the </div> that closes the Platform section (first one after Global Feed)
    platform_close = content.find('</div>', gf_idx + len(gf_marker))
    if platform_close == -1:
        print("ERROR: Platform closing div not found")
        return 1

    # Insert My Collection button before the closing </div>
    my_collection_btn = (
        '\n            <button class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 '
        'transition-all hover:bg-white/5 text-[var(--text-2)] hover:text-white">'
        '<span class="text-lg">\u2665</span>'
        '<span class="flex-1 truncate">My Collection</span>'
        '<span class="bg-black/30 px-2 py-0.5 rounded text-[10px] font-mono">0</span></button>'
    )

    content = content[:platform_close] + my_collection_btn + '\n          ' + content[platform_close:]

    # === Step 2: Replace NETWORK + PERSONAL + Data Management ===
    # Find the NETWORK section div (starts after Platform div)
    # Look for the div containing the NETWORK details
    net_marker = 'NETWORK'
    # Find it in the nav context (after Global Feed area)
    net_idx = content.find(net_marker, gf_idx)
    if net_idx == -1:
        print("ERROR: NETWORK marker not found")
        return 1

    # Find the containing div that starts this section
    # It's a <div class="space-y-1 pt-4 border-t border-white/5">
    section_div = 'class="space-y-1 pt-4 border-t border-white/5"'
    net_div_start = content.rfind('<div', 0, net_idx)
    # Verify it's the right div by checking it has the section class
    while net_div_start > 0 and section_div not in content[net_div_start:net_div_start+200]:
        net_div_start = content.rfind('<div', 0, net_div_start)

    if net_div_start <= 0:
        print("ERROR: NETWORK section div not found")
        return 1

    print(f"  NETWORK section div starts at char {net_div_start}")

    # Find the end of Data Management section
    # Data Management has the unique marker: accept=".json"
    dm_marker = 'accept=".json"'
    dm_idx = content.find(dm_marker, net_div_start)
    if dm_idx == -1:
        print("ERROR: Data Management end marker not found")
        return 1

    # Find the closing </div> after the accept marker — this closes the Data Management section
    # We need to find the right closing div. The structure is:
    # <div ...Data Management...>
    #   ...
    #   <input accept=".json" .../>
    # </div>
    dm_close = content.find('</div>', dm_idx)
    if dm_close == -1:
        print("ERROR: Data Management closing div not found")
        return 1

    dm_end = dm_close + len('</div>')

    print(f"  Data Management section ends at char {dm_end}")
    print(f"  Replacing {dm_end - net_div_start} chars")

    # Verify what comes after (should be the Contact Support section or another section)
    after_snippet = content[dm_end:dm_end+100].strip()[:60]
    print(f"  After replacement zone: {repr(after_snippet)}")

    # Replace NETWORK + Event System Settings + PERSONAL + Data Management
    # with the new OTHER STUFF section
    content = content[:net_div_start] + OTHER_STUFF_HTML + '\n' + content[dm_end:]

    # Write back
    with open(INDEX, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n  OK: Root index.html patched successfully")
    return 0


if __name__ == "__main__":
    print("=== Patching root index.html nav ===\n")
    sys.exit(patch())
