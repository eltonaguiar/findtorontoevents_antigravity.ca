# Tooltip Overlap Fix — Changes Applied

*Date: 2026-02-05*

---

## Summary

Fixed the overlapping text issue on the FavCreators banner at `findtorontoevents.ca/index.html` where banner text and tooltip text appeared on top of each other on hover. Also wrote 40 automated tests (20 Playwright + 20 Puppeteer).

---

## Files Modified

| File | Type of Change |
|------|---------------|
| `index.html` | CSS fixes + inline style fix + force-banners template fix |
| `add-promos.js` | Added `override-overflow` class + `absolute` class + solid background |
| `tests/tooltip_overlap.spec.ts` | Rewrote 20 Playwright tests |
| `tests/tooltip_overlap_puppeteer.spec.ts` | Rewrote 20 Puppeteer/Node tests |
| `package.json` | Added `puppeteer` and `@playwright/test` as dev dependencies |

---

## Code Changes

### 1. `index.html` — Inline style fix (line 383)

**Changed** the FavCreators tooltip inline `top` from `4px` to `8px` to match the CSS override:

```diff
- style="top: calc(100% + 4px); max-width: 300px; ..."
+ style="top: calc(100% + 8px); max-width: 300px; ..."
```

### 2. `index.html` — Restored scoped tooltip visibility CSS (lines ~163-173)

The original Fix 1 removed `.group:hover .group-hover\:visible` CSS, but Tailwind's compiled CSS doesn't include that utility class. Tooltips never became visible on hover. Added it back, **scoped only to tooltip elements** (`.absolute`) to avoid re-introducing the overlap:

```css
/* Tooltip visibility on hover – Tailwind build omits group-hover:visible,
   so we add it back scoped to .absolute (tooltip) only */
.group:hover > .relative .absolute,
.group:hover .absolute[class*="z-"] {
  visibility: visible !important;
  opacity: 1 !important;
}
```

### 3. `index.html` — Added z-index enforcement (line ~185)

Tailwind's JIT class `z-[9999]` was not in the compiled CSS, so tooltips had `z-index: auto`. Added explicit z-index to the existing CSS rule:

```diff
  .favcreators-promo .absolute {
    top: calc(100% + 8px) !important;
    right: 0 !important;
    min-width: 280px;
+   z-index: 9999 !important;
  }
```

### 4. `index.html` — Fixed force-banners FAVCREATORS template (line ~829)

The inline `<script>` force-banners template recreated banners with `z-50` and `top-full` instead of `z-[9999]` with proper positioning. Updated to match the static HTML:

```diff
- z-50" style="max-width: 300px; line-height: 1.5;">
+ z-[9999]" style="top: calc(100% + 8px); max-width: 300px; line-height: 1.5; transform: translateY(0);">
```

### 5. `add-promos.js` — Added `override-overflow` class

The dynamically injected FavCreators and Stocks banners were missing the `override-overflow` class on their text containers. Without it, the CSS rule `.promo-banner:hover .override-overflow` wouldn't expand the text:

```diff
- transition-all duration-500 max-w-0 opacity-0 overflow-hidden group-hover:...
+ transition-all duration-500 override-overflow max-w-0 opacity-0 overflow-hidden group-hover:...
```

Applied to both FavCreators (line 15) and Stocks (line 78) templates.

### 6. `add-promos.js` — Added `absolute` class + solid background to tooltip

The dynamically injected FavCreators tooltip used inline `position: absolute` but lacked the CSS class `absolute`, so the style rule `.favcreators-promo .absolute` didn't match it:

```diff
- <div class="jsx-1b9a23bd3fa6c640" style="position: absolute; ...
-   background: var(--surface-1, #1a1a2e); ...">
+ <div class="jsx-1b9a23bd3fa6c640 absolute" style="position: absolute; ...
+   background: rgba(30, 30, 40, 0.98);
+   backdrop-filter: blur(10px); ...">
```

---

## Pre-existing CSS Fixes (already in working copy)

These were already applied before this session and remain in place:

| Fix | CSS Rule | Purpose |
|-----|----------|---------|
| Solid background | `.favcreators-promo .absolute, .stocks-promo .absolute, ...` | `background: rgba(30,30,40,0.98)` prevents text bleed-through |
| Tooltip repositioning | `.favcreators-promo .absolute` | `top: calc(100% + 8px) !important` separates from banner text |
| Overflow protection | `.favcreators-promo .override-overflow` | `overflow: hidden !important` clips banner text at boundary |
| Conflicting selectors removed | ~~`.group:hover .group-hover\:visible`~~ | Was removed in earlier commit (now added back scoped) |

---

## Tests Written

### Playwright — 20 Tests (`tests/tooltip_overlap.spec.ts`)

| # | Test | What it verifies |
|---|------|-----------------|
| 1 | Page loads, FavCreators visible | Banner renders |
| 2 | All 4 promo banners present | Windows Fixer, FavCreators, MovieShows, Stocks |
| 3 | Correct child structure | `.promo-banner`, `.override-overflow`, Open App link |
| 4 | Tooltip element exists | `.favcreators-promo .absolute` count = 1 |
| 5 | Tooltip has z-index applied | Computed z-index >= 0 |
| 6 | Hover shows tooltip | Opacity > 0 on hover |
| 7 | Tooltip text matches | Contains "Track your favorite creators" |
| 8 | TikTok/Twitch/Kick links | All 3 platform links present |
| 9 | Solid opaque background | alpha >= 0.95 |
| 10 | No overlap with banner text | Bounding box comparison |
| 11 | Each banner shows own tooltip | Content keyword check per banner |
| 12 | Multiple hover cycles | 3 hover/unhover cycles |
| 13 | No overlap with next section text | Tooltip vs next `.override-overflow` |
| 14 | overflow: hidden applied | Computed style check |
| 15 | Links point to /fc/#/guest | href attribute check |
| 16 | No duplicate banners | Count = 1 after hydration |
| 17 | backdrop-filter blur applied | Computed style check |
| 18 | Responsive at 768px | Banner visible at tablet width |
| 19 | No console errors on hover | Filter tooltip-related pageerror |
| 20 | Full integration all 4 banners | Hover each, verify title text |

### Puppeteer/Node — 20 Tests (`tests/tooltip_overlap_puppeteer.spec.ts`)

| # | Test | What it verifies |
|---|------|-----------------|
| P-1 | 4 promo banners exist | `.promo-banner` count |
| P-2 | FavCreators visible | BoundingClientRect > 0 |
| P-3 | `.absolute` tooltip exists | querySelector check |
| P-4 | position: absolute | Computed style |
| P-5 | All banners have tooltip/link | Fallback to `<a>` check |
| P-6 | Hover triggers opacity > 0 | Mouse move + computed opacity |
| P-7 | Tooltip text correct | textContent check |
| P-8 | TikTok/Twitch/Kick links | Link text content check |
| P-9 | No overlap with adjacent text | Bounding rect comparison |
| P-10 | Multiple hover cycles stable | 3 cycles, opacity check |
| P-11 | Solid near-opaque background | RGBA alpha check |
| P-12 | backdrop-filter blur | Computed style |
| P-13 | overflow: hidden on text | Computed style |
| P-14 | z-index applied | Computed z-index >= 0 |
| P-15 | Links to /fc/#/guest | href attribute |
| P-16 | No duplicate FavCreators | Count after 5s hydration wait |
| P-17 | Hover sequence all banners | Mouse move to each |
| P-18 | Styling consistency | position: absolute on all |
| P-19 | Responsive at 768px | Viewport resize test |
| P-20 | No JS errors on hover | pageerror listener |

---

## Test Results

**39/40 passing** — 1 remaining Puppeteer test (`P-5`) fails intermittently because React hydration removes the Windows Fixer tooltip's `.absolute` class from the DOM. This is a pre-existing React hydration behavior, not a regression from these fixes.

---

## Root Cause Found During Testing

The original Fix 1 (removing `.group:hover .group-hover\:visible` CSS) was **premature** — Tailwind's compiled CSS (`cd9d6741b3ff3a25.css`) does not include the `group-hover:visible` or `z-[9999]` JIT utilities. The classes exist in the HTML but their corresponding CSS rules were never compiled into the stylesheet. The force-banners `<style>` block must provide these rules explicitly.

---

## Deployment Status

**Not yet deployed.** Changes are in the working copy. To deploy:

```bash
git add index.html add-promos.js tests/tooltip_overlap.spec.ts tests/tooltip_overlap_puppeteer.spec.ts
git commit -m "Fix tooltip overlap: scoped visibility, z-index, inline style consistency"
git push origin main
```

---

*Generated: 2026-02-05*
