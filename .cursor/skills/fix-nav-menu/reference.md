# Fix Nav Menu – Reference

Paths and line numbers are for **index.html** at the workspace root (`e:\findtorontoevents_antigravity.ca`).

## Nav block in index.html

| Section | Approx. lines | Notes |
|--------|----------------|--------|
| Fixed UI layer + hamburger | 104–111 | Button that opens the panel. |
| Panel overlay + "Quick Nav" header | 112–120 | Backdrop and title row. |
| Platform (Global Feed, Contact Support) | 121–129 | Buttons, not links. |
| NETWORK (details) + links | 131–156 | Windows Boot Fixer, Find Stocks, Movies & TV, Favorite Creators, FAVCREATORS, "are your favorite creators live?", Mental Health Resources, 2XKO Frame Data. |
| Event System Settings, Contact Support | 157–166 | Buttons. |
| Data Management | 170–184 | JSON/CSV/Calendar/Import. |
| PERSONAL (My Collection) | 185–191 | |
| Support (Manual Uplink) | 192–201 | |
| Footer (Antigravity Systems version) | 204–207 | |

## Color classes for nav links

Use these for the `class="... hover:bg-X-500/20 text-X-200 ... hover:border-X-500/30"` pattern when adding or modifying a link. Replace `X` in the template with the color name.

| Color   | Hover/text classes (use in `<a class="...">`) |
|--------|------------------------------------------------|
| blue   | `hover:bg-blue-500/20 text-blue-200 hover:text-white ... hover:border-blue-500/30` |
| green  | `hover:bg-green-500/20 text-green-200 ... hover:border-green-500/30` |
| yellow | `hover:bg-yellow-500/20 text-yellow-200 ... hover:border-yellow-500/30` |
| amber  | `hover:bg-amber-500/20 text-amber-200 ... hover:border-amber-500/30` |
| orange | `hover:bg-orange-500/20 text-orange-200 ... hover:border-orange-500/30` |
| rose   | `hover:bg-rose-500/20 text-rose-200 ... hover:border-rose-500/30` |
| red    | `hover:bg-red-500/20 text-red-200 ... hover:border-red-500/30` |
| purple | `hover:bg-purple-500/20 text-purple-200 ... hover:border-purple-500/30` |

Base pattern (same for all):  
`class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-[COLOR]-500/20 text-[COLOR]-200 hover:text-white transition-all border border-transparent hover:border-[COLOR]-500/30 overflow-hidden"`

## Copy-paste templates (add items)

**NETWORK link** (insert inside `<div class="space-y-1 mt-1">`, before `</div></details>`):

```html
                <a class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-blue-500/20 text-blue-200 hover:text-white transition-all border border-transparent hover:border-blue-500/30 overflow-hidden"
                  href="/PATH/"><span class="text-lg">🔗</span> Label</a>
```

**Standalone link** (after NETWORK `</details>`, same style as 2XKO):

```html
            <a class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-purple-500/20 text-purple-200 hover:text-white transition-all border border-transparent hover:border-purple-500/30 overflow-hidden"
              href="/PATH/"><span class="text-lg">🎮</span> Label</a>
```

**New section** (insert before `</nav>`, after last section):

```html
          <div class="space-y-1 pt-4 border-t border-white/5">
            <p class="px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60">SECTION TITLE</p>
            <a class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-blue-500/20 text-blue-200 hover:text-white transition-all border border-transparent hover:border-blue-500/30 overflow-hidden"
              href="/PATH/"><span class="text-lg">🔗</span> Label</a>
          </div>
```

Replace `/PATH/`, `Label`, `SECTION TITLE`, and the emoji/color as needed. Use `&amp;` for `&` in labels (e.g. `Movies &amp; TV`).

## Asset URLs (do not edit when fixing nav)

- **Lines 44–58, 99:** `<link>` and `<script>` tags with `/next/_next/static/...`. Do not change `href`/`src` or add/remove `?v=...`.
- **Lines 664+:** Inline scripts referencing `/next/_next/static/chunks/...`. Do not modify when doing menu-only edits.

## Tools

- **patch_nav_js.py** – Patches `next/_next/static/chunks/a2ac3a6616d60872.js` (and mirrors) for nav link URLs/labels and **reordering** (e.g. FavCreators, Event System Settings, Windows Boot Fixer title; moving 2XKO and Mental Health after FAVCREATORS). Uses regex for removal so matching is emoji-agnostic. Run from project root; then deploy the chunk and optionally sync index.html.
- **serve_local.py** – Use for local verification after any index.html or chunk change. Do not use `python -m http.server`.

## Cross-reference

- Full rules and event-loading fixes: **fix-toronto-events** skill and **FIX_SUMMARY.md**.
- FavCreators deployment: **DEPLOYMENT_FIX_FAVCREATORS.md**.
