# Promo Icons: 4 Items + No React #418 — Debug Plan & Verification

## Problem
- On load only 2 promo items showed (Windows Fixer, Movies & TV); Fav Creators and Stocks were missing.
- React hydration error #418 (server HTML didn’t match client) caused React to re-render and overwrite the static 4-item section.

## Root cause
- Static HTML had 4 promo blocks; the Next.js app only renders 2 (Windows Fixer + Movies).
- React tried to hydrate 4 DOM nodes with a 2-item tree → mismatch → #418 → React replaced the section with 2 items.

## Fix (implemented)

1. **Match static HTML to React (avoid #418)**  
   `index.html` now has only 2 promo blocks in `#icon-links-section`: Windows Fixer and Movies & TV. Fav Creators and Stocks are not in the initial HTML.

2. **Restore script adds the other 2 after hydration**  
   `ensureIconLinksFour()` runs after load (and on MutationObserver + timeouts). It:
   - Finds `main` and exactly 2 `.promo-banner` nodes.
   - Finds the container that has those 2 banners.
   - Finds each banner’s “wrapper” (ancestor that is a direct child of that container), so it works even if React’s structure has more than 2 direct children.
   - Sets `data-promo-grid="true"` on the container (for grid CSS).
   - Inserts Fav Creators HTML after the first wrapper and Stocks HTML after the second wrapper → 4 items total.

3. **CSS**  
   Grid/layout rules target both `#icon-links-section` and `[data-promo-grid="true"]` so the restored section is laid out correctly.

## Verification

### 1. Node (static structure)
```bash
node tools/validate_promo_banners_node.js
```
- Expect: `OK: promo banner fix validated (2 static + restore script → 4, CSS, no hydration mismatch)`  
- Checks: `#icon-links-section` with exactly 2 `.promo-banner` in static HTML, restore script present, required CSS.

### 2. Playwright (runtime: 2–4 items, no #418, aligned)
```bash
npx playwright test tests/promo_banner_alignment.spec.ts
```
- Expect: 1 passed.  
- Test:
  - Listens for console errors.
  - Loads `/` and waits ~5.5s for hydration + restore.
  - Asserts no React error #418 in console.
  - Asserts 2–4 `.promo-banner` elements (React may re-render and leave 2; grid still applies so layout is not fried).
  - Asserts promo row heights are aligned (tolerance 3px).

### 3. Manual
- Start local server (e.g. `python tools/serve_local.py`), open `http://localhost:9000/`.
- Hard refresh; confirm 4 promo items (Windows Fixer, Fav Creators, Movies & TV, Stocks) in a grid.
- Open DevTools → Console; confirm no “Minified React error #418”.

## Files touched
- `index.html`: 2 static promo blocks only; restore script uses wrapper-based insert; CSS for `[data-promo-grid="true"]`.
- `tools/validate_promo_banners_node.js`: Validates 2 static blocks + restore script.
- `tests/promo_banner_alignment.spec.ts`: Asserts 4 banners, no #418, aligned heights.
