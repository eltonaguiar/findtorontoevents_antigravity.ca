---
name: fix-nav-menu
description: Add, remove, or modify Quick Nav menu items on findtorontoevents.ca safely. Use when changing nav links, labels, sections, or structure while respecting project rules so events loading is not broken. Follows FIX_SUMMARY.md and INDEX_BROKEN_FIX.md; do not change asset URLs or add fallback scripts.
---

# Fix Nav Menu (Without Breaking Events)

Use this skill when changing the **Quick Nav** menu on the main page (findtorontoevents.ca). The menu is critical for UX but lives in the same file as all chunk URLs; edits must be **surgical** so the React app and events still load.

**Quick actions**

| Goal | Where | Action |
|------|--------|--------|
| **Modify** link/label/icon | index.html nav block (~123–202) | Edit only that `<a href="...">` and text; optional `title=""` and color classes (see reference.md). |
| **Remove** item | index.html nav block | Delete the full `<a>...</a>` or `<button>...</button>`; if React also renders it, consider patch_nav_js.py. |
| **Add** NETWORK link | Inside NETWORK `<div class="space-y-1 mt-1">`, before `</div></details>` | Paste NETWORK link template (§3 Add A); set href, icon, label, color. |
| **Add** standalone link | After NETWORK `</details>` or after 2XKO line | Paste standalone template (§3 Add B). |
| **Add** new section | Before `</nav>`, after last section | Paste new-section template (§3 Add C). |

Templates and color classes: **reference.md**.

## 1. Where the Nav Lives

| Location | Role |
|----------|------|
| **index.html** (approx. lines 104–209) | Static HTML for the slide-out "Quick Nav" panel: hamburger button, Platform (Global Feed, Contact Support), NETWORK (links), 2XKO, Event System Settings, Data Management, PERSONAL, Support. |
| **Chunk a2ac3a6616d60872.js** | React hydrates this same DOM. The chunk contains nav link URLs and labels (e.g. FavCreators, Windows Boot Fixer). Changing only index.html can cause a **hydration mismatch** if the chunk still renders different links. |

**Rule of thumb:** For **link URL or label changes** that React renders, use **patch_nav_js.py** and then **sync index.html** to match (or edit index.html only if the chunk is not the source of truth for that item). For **structure/layout** (e.g. reorder sections, add a new `<a>` in the same pattern), edit **index.html** only, then verify events still load. For **reordering items** that React also renders (e.g. moving Mental Health above 2XKO), do both: edit **index.html** and run **patch_nav_js.py** (see §8) so the chunk order matches and hydration does not mismatch.

## 2. Rules (Do Not Break Events Loading)

These come from **FIX_SUMMARY.md** and **INDEX_BROKEN_FIX.md**. Breaking them can cause SyntaxError, no events, no filter bar.

1. **Do not change any asset URL.**
   - Every `href` or `src` pointing to `_next` must stay exactly as-is.
   - Live base path: **`/next/_next/`** (e.g. `/next/_next/static/chunks/a2ac3a6616d60872.js`).
   - First query param on assets: **`?v=...`**, never **`&v=...`**.
   - Do not "fix" or normalize these URLs when updating the menu.

2. **Do not add a fallback/backup script** that fetches `events.json` and writes HTML into the events grid (or any container React hydrates). It breaks hydration.

3. **Do not reformat or minify the whole file.** Prefer editing only the **nav block** (the specific `<nav>...</nav>` and the panel div that contains it).

4. **Menu/nav link changes:** Only edit the **specific** `<a href="...">` and link text inside the existing nav. **Do not** run a global find-replace on `/_next/` or on `?`/`&` in the file.

5. **After any edit:** Confirm in the built HTML that:
   - All chunk URLs still start with **`/next/_next/`**.
   - Every asset URL uses **`?v=...`** for the first query param, not `&v=...`.

## 3. Add / Remove / Modify Menu Items

Work only inside the **nav block** in **index.html** (approx. lines 123–202). Do not touch any line that contains `_next` or asset URLs.

### Modify an item

- **Link (href or label):** Find the `<a href="...">` and change only `href="..."` and/or the text inside (e.g. after `<span class="text-lg">ICON</span>`). Use `&amp;` for `&` in link text (e.g. `Movies &amp; TV`).
- **Optional title:** Add or edit `title="..."` in the same `<a>`.
- **Icon:** Change the emoji inside `<span class="text-lg">🛠️</span>` (or the same pattern).
- **Color:** Swap the hover/text classes; see **reference.md** for the color table (e.g. `hover:bg-blue-500/20 text-blue-200` → `hover:bg-green-500/20 text-green-200`).

### Remove an item

1. Delete the **entire** `<a>...</a>` or `<button>...</button>` for that item (the full line or multi-line block). Do not leave broken tags.
2. If the item is inside **NETWORK**, remove it from inside the `<div class="space-y-1 mt-1">` (between `<summary>...</summary>` and `</div></details>`).
3. If React also renders this item (e.g. FavCreators links), the chunk may still output it; for a full remove you may need to patch **a2ac3a6616d60872.js** via **patch_nav_js.py** or a similar patch. For index-only removal, the static menu will no longer show the item; test hydration (see §6).

### Add an item

**A. Add a link inside NETWORK**

Insert a new line **before** `</div></details>` (i.e. before the closing `</div>` of the NETWORK `<div class="space-y-1 mt-1">`). Use this template; replace `[URL]`, `[ICON]`, `[LABEL]`, and optionally `[COLOR]` (see reference.md for color classes):

```html
                <a class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-[COLOR]-500/20 text-[COLOR]-200 hover:text-white transition-all border border-transparent hover:border-[COLOR]-500/30 overflow-hidden"
                  href="[URL]"><span class="text-lg">[ICON]</span> [LABEL]</a>
```

Example (new link with blue style):

```html
                <a class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-blue-500/20 text-blue-200 hover:text-white transition-all border border-transparent hover:border-blue-500/30 overflow-hidden"
                  href="/my-page/"><span class="text-lg">🔗</span> My Page</a>
```

**B. Add a standalone link (same style as 2XKO)**

Insert **after** the `</details>` of NETWORK and **before** the 2XKO `<a>` (or after it). Copy the 2XKO line and change `href`, icon, and label:

```html
            <a class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-purple-500/20 text-purple-200 hover:text-white transition-all border border-transparent hover:border-purple-500/30 overflow-hidden"
              href="[URL]"><span class="text-lg">[ICON]</span> [LABEL]</a>
```

**C. Add a new section (header + items)**

Insert **before** `</nav>`, after the last section (e.g. after the Support block). Use the same pattern as "Data Management" or "PERSONAL":

```html
          <div class="space-y-1 pt-4 border-t border-white/5">
            <p class="px-4 py-2 text-[10px] font-black uppercase text-[var(--pk-300)] tracking-widest opacity-60">[SECTION TITLE]</p>
            <a class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-blue-500/20 text-blue-200 hover:text-white transition-all border border-transparent hover:border-blue-500/30 overflow-hidden"
              href="[URL]"><span class="text-lg">[ICON]</span> [LABEL]</a>
          </div>
```

After any add/remove/modify, run **Post-Edit Verification** (§6).

## 4. Safe Edit Procedure (Summary)

### index.html-only changes (most menu edits)

1. Open **index.html**, go to the nav block (search for `Quick Nav` or `fixed-ui-layer`).
2. **Modify:** Edit only that `<a>` or `<button>` (href, label, icon, title, color classes).
3. **Remove:** Delete the full `<a>...</a>` or `<button>...</button>` for that item.
4. **Add:** Paste one of the templates above in the correct place (NETWORK, standalone, or new section).
5. Save; run verification (§6).

### When the chunk must stay in sync (FavCreators, etc.)

1. Use **tools/patch_nav_js.py** for URL/label changes that React renders. See **DEPLOYMENT_FIX_FAVCREATORS.md**.
2. Edit **index.html** the same way (modify/remove/add) so static HTML matches.
3. Deploy the patched chunk to the server; run verification (§6).

### What not to do

- Do **not** replace `/_next/` or `/next/_next/` anywhere in the file.
- Do **not** change `?v=` to `&v=` or remove the `next` segment from asset paths.
- Do **not** add a script that injects event HTML into the page.
- Do **not** reformat or minify the entire file.

## 5. Nav Structure Reference (index.html)

Rough structure of the Quick Nav in index.html:

- **Fixed UI layer** (top-left): Hamburger button → opens panel.
- **Panel:** "Quick Nav" title, close button.
- **Platform:** Global Feed, Contact Support (buttons).
- **NETWORK** (details/summary): Windows Boot Fixer, Find Stocks, Movies & TV, Favorite Creators, FAVCREATORS, "are your favorite creators live?", Mental Health Resources, 2XKO Frame Data (all `<a>` tags).
- **Event System Settings** (button).
- **Data Management:** JSON/CSV/Calendar export, Import.
- **PERSONAL:** My Collection.
- **Support:** Manual Uplink contact.

When adding/removing/reordering items, keep the same HTML patterns (same class names and structure) so React hydration still matches.

## 7. Reordering items (index.html + chunk patch)

When you **reorder** nav items (e.g. move Mental Health above 2XKO), both the static HTML and the React chunk must match or hydration will mismatch.

1. **index.html:** Move the item by cutting the full `<a>...</a>` from its current position and pasting it in the new position (e.g. just above 2XKO).
2. **Chunk (flat structure):** Use **tools/patch_nav_js.py**. The script has a flat-structure block (e.g. "8a") that:
   - Removes an item from its original position with a **regex** (so matching works regardless of emoji encoding in the chunk).
   - Inserts it in the new position (e.g. after FAVCREATORS, before 2XKO).
3. **Best practices for patch_nav_js.py:**
   - Use **regex** for removal so the pattern is emoji-agnostic (e.g. `" Windows (?:Boot )?Fixer"\]\}\)),` plus the link pattern).
   - Capture the link string when removing so you can re-insert it in the new place (e.g. Mental Health link captured then inserted above 2XKO).
   - Do **not** move large structural blocks (e.g. Data Management) in the same patch if that has caused runtime errors (e.g. `(0 , t.jsxs)(...) is not a function`); reorder only link-level items when possible.
4. After editing: run the patch, then **Post-Edit Verification** (§6); optionally `python tools/verify_events_loading.py` and Playwright nav tests.

## 6. Post-Edit Verification

1. **View Source** (or open the saved index.html): Search for `_next`. Every occurrence should still be **`/next/_next/`** with no accidental change to `/_next/` or removal of `next/`. Every asset URL should use **`?v=...`** (not `&v=...`).
2. **Local test:** Run `python tools/serve_local.py` from the project root, open the main page, and confirm:
   - Event cards and filter bar (search, GLOBAL FEED, date/price) appear.
   - No console errors (e.g. SyntaxError in a2ac3a6616d60872.js).
3. **Optional:** Run the FavCreators link test: `npx playwright test tests/inspect_favcreators_link.spec.ts` if you changed FavCreators URLs.

## 8. Project References

- **FIX_SUMMARY.md** – What breaks events loading, rules for editing index.html.
- **INDEX_BROKEN_FIX.md** – Diagnosis and fix steps (chunk paths, ModSecurity, events.json).
- **fix-toronto-events** skill – Full diagnosis when events do not load or chunks fail.
- **DEPLOYMENT_FIX_FAVCREATORS.md** – FavCreators link fix and patch_nav_js.py.
- **MENU_UPDATE_SUMMARY.md** – Past menu reorganization notes.
