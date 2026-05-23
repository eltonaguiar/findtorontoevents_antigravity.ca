---
name: icon-links-section
description: Modify, add, or remove icon link items (promo banners) on the main events page (index.html). Edit the static template container for the 2-column grid of promos with tooltips.
---

# Icon Links Section (Main Events Page)

Use this skill when changing the **icon links section** on the main events page (findtorontoevents.ca): the 2-column grid of promo items below the header showing an icon, title/subtitle, action buttons, and info tooltips.

## CRITICAL: React Hydration Issue

**Problem:** React hydration destroys promo sections due to server/client mismatch (Minified React error #418). The server HTML has N sections but React's client code may render fewer.

**Solution:** Clone injection approach:
1. A **static template** (`#static-promo-container`) is placed OUTSIDE React's hydration scope (before the React wrapper div)
2. JavaScript **clones** this template and injects it as `#injected-promos` after the header
3. A **MutationObserver** watches for React destroying the content and re-injects if needed
4. CSS **hides** the template and React's broken sections, **shows** the injected container

**Rule:** Always edit the **static template container** (`#static-promo-container`), NOT React's hydrated content inside `<main>`.

## Quick Actions

| Goal | Where | Action |
|------|-------|--------|
| **Modify** icon/title/subtitle/URL/tooltip | `#static-promo-container` in index.html (lines ~416-622) | Edit the promo section's HTML directly in the static template |
| **Add** new promo section | Inside `#static-promo-container`'s grid + **5 CSS/JS locations** | Follow the **Adding a New Promo Section** checklist below |
| **Remove** promo section | Inside `#static-promo-container` + CSS/JS | Delete the `<div class="[name]-promo w-full">` block and remove from CSS/JS |
| **Change tooltip content** | The `group/info` div inside each promo | Edit the tooltip's `<div class="absolute...">` content |

## 1. Architecture Overview

### File Locations

| Location | Role |
|----------|------|
| **index.html** `#static-promo-container` (lines ~416-622) | Static HTML template for all promos. Placed OUTSIDE React's wrapper div. Hidden by default (`display:none`). |
| **index.html** CSS `#force-banners` style block (lines ~131-230) | CSS that hides template, hides React's broken sections, shows injected container, and enables tooltip hover |
| **index.html** Clone injection script (lines ~1173-1245) | JavaScript that clones template, injects after header, watches for React destroying it |
| **add-promos.js** | Legacy script - now just checks if `#static-promo-container` exists and skips |
| **tools/check-promos.js** | Playwright verification script - checks all sections are visible |

### DOM Structure

```
<body>
  ...fixed buttons...
  
  <!-- STATIC TEMPLATE - Outside React's scope -->
  <div id="static-promo-container" style="display:none;">
    <div class="grid grid-cols-2 gap-4">
      <div class="windows-fixer-promo">...</div>
      <div class="movieshows-promo">...</div>
      <div class="favcreators-promo">...</div>
      <div class="stocks-promo">...</div>
      <div class="mentalhealth-promo">...</div>
      <div class="gotjob-promo">...</div>
    </div>
  </div>
  
  <!-- React's wrapper - hydration happens here -->
  <div class="font-size-md density-normal...">
    <main class="min-h-screen">
      <header>...</header>
      
      <!-- INJECTED CLONE - JavaScript inserts here -->
      <div id="injected-promos">
        ...cloned from static template...
      </div>
      
      ...events grid...
    </main>
  </div>
</body>
```

## 2. Current Promo Sections

| # | Class | Icon | Title | Subtitle | Action | Tooltip |
|---|-------|------|-------|----------|--------|---------|
| 1 | `windows-fixer-promo` | 🛠️ | System Issues? | Try Windows Boot Fixer | Learn More → | Miracle Boot description |
| 2 | `movieshows-promo` | 🎬 | Movie/TV Show Trailers | Swipe through trailers... | V1/V2/V3 buttons | Version differences |
| 3 | `favcreators-promo` | 💎 | Fav Creators | Never miss when your favorites go live | Open App → | Platform info |
| 4 | `stocks-promo` | 📈 | Stock Ideas | AI-validated picks, updated daily | Open App → | Algorithm info |
| 5 | `mentalhealth-promo` | 🧠 | Mental Health | Wellness games, crisis support & tools | Open App → | Crisis lines, interactive games |
| 6 | `gotjob-promo` | 💼 | $100K+ Jobs | Toronto tech & creative manager roles | Find Jobs → | Salary filters, job sources |

**Layout:** 2-column grid (`grid grid-cols-2 gap-4`), currently 3 rows with 6 promos
**Order:** Left-to-right, top-to-bottom

## 3. How to Modify a Promo Section

1. **Find the static template** - Search for `id="static-promo-container"` in index.html
2. **Locate the promo** - Find the `<div class="[name]-promo w-full">` block
3. **Make changes:**
   - **Icon:** Change emoji in `<span class="text-3xl">[EMOJI]</span>`
   - **Title:** Change `<span class="text-lg font-bold text-white">[TITLE]</span>`
   - **Subtitle:** Change `<span class="text-sm text-[var(--text-2)]">[SUBTITLE]</span>`
   - **URL:** Change `href="[URL]"` on the `<a>` tag
   - **Button text:** Change text inside `<a>` or `<button>` tag
   - **Tooltip:** Edit content inside the `group/info` div's absolute-positioned tooltip
   - **Gradient:** Change `bg-gradient-to-br from-[...] to-[...]` on icon circle

4. **Test:** Run `node tools/check-promos.js` to verify all sections appear

## 4. CRITICAL: Adding a New Promo Section

**When adding a new promo, you MUST update 5 locations or the promo will be INVISIBLE:**

### Checklist for Adding a New Promo

- [ ] **1. HTML Template** - Add the promo HTML inside `#static-promo-container`'s grid (use template from reference.md)

- [ ] **2. CSS Hide Rule** - Add class to `main .[name]-promo` hide rule:
  ```css
  main .windows-fixer-promo,
  main .favcreators-promo,
  ...
  main .[NEW]-promo { display: none !important; }
  ```

- [ ] **3. CSS Visibility Rule** - Add class to `#injected-promos .[name]-promo` visibility rule:
  ```css
  #injected-promos .windows-fixer-promo,
  ...
  #injected-promos .[NEW]-promo {
    display: block !important;
    visibility: visible !important;
    ...
  }
  ```

- [ ] **4. CSS Tooltip Rules** - Add class to tooltip stacking/hover rules:
  ```css
  .[NEW]-promo .group > .relative { z-index: 10 !important; ... }
  .[NEW]-promo .tooltip-panel { visibility: hidden !important; ... }
  .[NEW]-promo:hover .tooltip-panel { visibility: visible !important; ... }
  ```

- [ ] **5. JS Section Check** - Update the `hasAll` check in the injection script:
  ```javascript
  const hasAll = existing.querySelector('.windows-fixer-promo') &&
                 ...
                 existing.querySelector('.[NEW]-promo');
  ```

- [ ] **6. JS Hide Selector** - Update the querySelectorAll for hiding React's sections:
  ```javascript
  document.querySelectorAll('main .windows-fixer-promo, ... main .[NEW]-promo').forEach(...)
  ```

### Quick Search Terms

Find these in index.html to update:
- `/* HIDE React's promo sections */` - CSS hide rule
- `/* FORCE ALL` - CSS visibility rule  
- `/* FIX: Create proper stacking` - CSS tooltip rules
- `// Check if our injected container exists` - JS hasAll check
- `// Hide React's promo sections` - JS hide selector

## 5. Tooltip Structure

Each promo has an info tooltip using the `group/info` pattern:

```html
<div class="relative group/info">
  <!-- Info button -->
  <button class="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 text-xs flex items-center justify-center cursor-pointer border-0" style="font-size:14px;">ℹ️</button>
  
  <!-- Tooltip content - shows on hover -->
  <div class="absolute left-0 mt-2 w-80 p-4 bg-[#1a1a2e] border border-white/10 rounded-xl shadow-2xl opacity-0 invisible group-hover/info:opacity-100 group-hover/info:visible transition-all duration-300 z-[9999] text-left" style="top: 100%;">
    <p class="text-xs font-bold text-[COLOR]-400 mb-2">[EMOJI] [TOOLTIP TITLE]</p>
    <div class="space-y-2 text-xs text-[var(--text-2)]">
      [TOOLTIP CONTENT - lists, paragraphs, etc.]
    </div>
  </div>
</div>
```

**Position:** Use `left-0` for left-column tooltips, `right-0` for right-column tooltips (prevents off-screen)

## 6. CSS Selectors Summary

The `#force-banners` style block controls visibility. **ALL promo classes must appear in these rules:**

```css
/* 1. Hide template */
#static-promo-container { display: none !important; }

/* 2. Hide React's broken sections */
main .windows-fixer-promo,
main .favcreators-promo,
main .movieshows-promo,
main .stocks-promo,
main .mentalhealth-promo,
main .gotjob-promo { display: none !important; }

/* 3. Show injected container */
#injected-promos { display: block !important; }

/* 4. Force visibility for ALL promos in injected container */
#injected-promos .windows-fixer-promo,
#injected-promos .favcreators-promo,
#injected-promos .movieshows-promo,
#injected-promos .stocks-promo,
#injected-promos .mentalhealth-promo,
#injected-promos .gotjob-promo {
  display: block !important;
  visibility: visible !important;
  ...
}

/* 5. Tooltip hover */
.group\/info:hover > div[class*="absolute"] {
  opacity: 1 !important;
  visibility: visible !important;
}
```

## 7. Clone Injection Script

The script captures the template and injects it after the header:

```javascript
(function() {
  const templateContainer = document.getElementById('static-promo-container');
  const PROMO_HTML = templateContainer ? templateContainer.outerHTML
    .replace('id="static-promo-container"', 'id="injected-promos"')
    .replace('display:none', 'display:block') : '';
  
  function injectPromos() {
    let existing = document.getElementById('injected-promos');
    if (existing) {
      // Check ALL promo classes are present
      const hasAll = existing.querySelector('.windows-fixer-promo') &&
                     existing.querySelector('.movieshows-promo') &&
                     existing.querySelector('.favcreators-promo') &&
                     existing.querySelector('.stocks-promo') &&
                     existing.querySelector('.mentalhealth-promo') &&
                     existing.querySelector('.gotjob-promo');
      if (hasAll) { existing.style.display = 'block'; return; }
      existing.remove();
    }
    
    const header = document.querySelector('main header');
    if (header && PROMO_HTML) {
      header.insertAdjacentHTML('afterend', PROMO_HTML);
    }
    
    // Hide React's broken sections (list ALL promo classes)
    document.querySelectorAll('main .windows-fixer-promo, main .movieshows-promo, main .favcreators-promo, main .stocks-promo, main .mentalhealth-promo, main .gotjob-promo').forEach(el => {
      if (!el.closest('#injected-promos') && !el.closest('#static-promo-container')) {
        el.style.cssText = 'display:none !important;';
      }
    });
  }
  
  // Run on delays to catch React hydration
  [100, 300, 500, 800, 1000, 1500, 2000, 3000, 5000, 7000, 10000].forEach(delay => {
    setTimeout(injectPromos, delay);
  });
  
  // MutationObserver re-injects if React destroys it
  new MutationObserver(() => {
    if (!document.getElementById('injected-promos')) injectPromos();
  }).observe(document.body, { childList: true, subtree: true });
})();
```

## 8. Post-Edit Verification

1. **Run promo check script:**
   ```bash
   node tools/check-promos.js
   ```
   - Should show: `Visible sections: 6/6` (or however many promos exist)
   - Creates screenshot at `test-results/promos-check.png`

2. **Run no JS errors test:**
   ```bash
   npx playwright test tests/no_js_errors.spec.ts
   ```

3. **Visual check:** Open http://localhost:5173/
   - All promos visible in 2-column grid
   - Tooltips appear on hover
   - Check console for `[STATIC PROMOS] Template has N promo sections`

## 9. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| **New promo not visible** | CSS visibility rule missing the new class | Add class to `#injected-promos .[name]-promo` CSS rule (see §4) |
| Only some promos visible | React hydration won, injection failed | Check clone script is present, increase timeout delays |
| Promos appear then disappear | MutationObserver not re-injecting | Verify observer is watching `document.body` |
| Tooltips don't show | CSS missing or wrong selector | Check `#force-banners` has tooltip hover rules |
| Wrong content | Edited React's section instead of template | Always edit `#static-promo-container` |
| Console: "hasAll: true" but missing promos | CSS rule doesn't include new class | **Most common issue** - update the `#injected-promos .[name]-promo` visibility rule |

## 10. Related Skills & Files

- **reference.md** – Templates for adding new promo sections with examples
- **tools/check-promos.js** – Playwright verification script
- **tests/no_js_errors.spec.ts** – JS error check test
- **fix-toronto-events** skill – Full diagnosis when events don't load
