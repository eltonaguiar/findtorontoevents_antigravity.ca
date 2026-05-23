# Icon Links Section – Reference

Templates and examples for adding or modifying icon link items (promo banners) on the main events page (**index.html**). Use with the **icon-links-section** skill.

## 1. Where to Edit

- **File:** `index.html` (project root)
- **Static Template:** `#static-promo-container` (lines ~416-622) - ALWAYS edit here
- **CSS:** `#force-banners` style block (lines ~131-230)
- **Clone Script:** End of file (lines ~1173-1245)
- **Verification:** `node tools/check-promos.js`

**CRITICAL:** Edit the static template (`#static-promo-container`), NOT content inside `<main>`. React hydration will destroy anything inside main.

## 2. Current Layout

The 6 promos are in a **2-column, 3-row grid**:

```
┌─────────────────────┬─────────────────────┐
│  System Issues?     │  Movie/TV Trailers  │
│  🛠️ Learn More →   │  🎬 V1/V2/V3 ℹ️     │
├─────────────────────┼─────────────────────┤
│  Fav Creators       │  Stock Ideas        │
│  💎 Open App → ℹ️   │  📈 Open App → ℹ️   │
├─────────────────────┼─────────────────────┤
│  Mental Health      │  $100K+ Jobs        │
│  🧠 Open App → ℹ️   │  💼 Find Jobs → ℹ️  │
└─────────────────────┴─────────────────────┘
```

## 3. Adding a New Promo Section - COMPLETE CHECKLIST

**You MUST update ALL of these locations or the promo will be INVISIBLE:**

### Step 1: Add HTML Template

Insert inside `#static-promo-container`'s `<div class="grid grid-cols-2 gap-4">`:

```html
<!-- [NAME] Promo -->
<div class="[PROMO-CLASS]-promo w-full">
  <div class="promo-banner bg-white/5 rounded-2xl p-5 h-full">
    <div class="flex items-center gap-4 transition-all duration-500 group">
      <!-- Icon Circle -->
      <div class="w-16 h-16 rounded-full bg-gradient-to-br from-[GRADIENT-FROM] to-[GRADIENT-TO] flex items-center justify-center shadow-lg">
        <span class="text-3xl">[ICON]</span>
      </div>
      
      <!-- Title & Subtitle -->
      <div class="transition-all duration-500">
        <div class="flex flex-col whitespace-nowrap">
          <span class="text-lg font-bold text-white">[TITLE]</span>
          <span class="text-sm text-[var(--text-2)]">[SUBTITLE]</span>
        </div>
      </div>
      
      <!-- Action Button -->
      <div class="relative">
        <a class="ml-2 px-5 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-base font-bold text-white transition-all whitespace-nowrap" href="[URL]" target="_blank">[BUTTON-TEXT]</a>
      </div>
      
      <!-- Info Tooltip -->
      <div class="relative group/info">
        <button class="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 text-xs flex items-center justify-center cursor-pointer border-0" style="font-size:14px;">ℹ️</button>
        <div class="absolute [left-0 OR right-0] mt-2 w-80 p-4 bg-[#1a1a2e] border border-white/10 rounded-xl shadow-2xl opacity-0 invisible group-hover/info:opacity-100 group-hover/info:visible transition-all duration-300 z-[9999] text-left" style="top: 100%;">
          <p class="text-xs font-bold text-[TOOLTIP-COLOR]-400 mb-2">[TOOLTIP-EMOJI] [TOOLTIP-TITLE]</p>
          <div class="space-y-2 text-xs text-[var(--text-2)]">
            [TOOLTIP-CONTENT]
          </div>
          <p class="text-[10px] text-[var(--text-3)] mt-2 italic">[FOOTER-NOTE]</p>
        </div>
      </div>
    </div>
  </div>
</div>
```

### Step 2: Update CSS Hide Rule

Search for `/* HIDE React's promo sections */` and add your class:

```css
main .windows-fixer-promo,
main .favcreators-promo,
main .movieshows-promo,
main .stocks-promo,
main .mentalhealth-promo,
main .gotjob-promo,
main .[NEW]-promo {          /* <-- ADD THIS LINE */
  display: none !important;
}
```

### Step 3: Update CSS Visibility Rule

Search for `/* FORCE ALL` and add your class:

```css
#injected-promos .windows-fixer-promo,
#injected-promos .favcreators-promo,
#injected-promos .movieshows-promo,
#injected-promos .stocks-promo,
#injected-promos .mentalhealth-promo,
#injected-promos .gotjob-promo,
#injected-promos .[NEW]-promo {    /* <-- ADD THIS LINE */
  display: block !important;
  visibility: visible !important;
  height: auto !important;
  overflow: visible !important;
  position: relative !important;
}
```

### Step 4: Update CSS Tooltip Rules

Search for `/* FIX: Create proper stacking context */` and add your class to ALL these rules:

```css
/* Stacking context */
.favcreators-promo .group > .relative,
...
.[NEW]-promo .group > .relative {    /* <-- ADD */
  z-index: 10 !important;
  position: relative !important;
}

/* Overflow */
.favcreators-promo .override-overflow,
...
.[NEW]-promo .override-overflow {    /* <-- ADD */
  z-index: 1 !important;
  ...
}

/* Tooltip hidden */
.favcreators-promo .tooltip-panel,
...
.[NEW]-promo .tooltip-panel {        /* <-- ADD */
  visibility: hidden !important;
  opacity: 0 !important;
}

/* Tooltip hover */
.favcreators-promo:hover .tooltip-panel,
...
.[NEW]-promo:hover .tooltip-panel {  /* <-- ADD */
  visibility: visible !important;
  opacity: 1 !important;
}
```

### Step 5: Update JS Section Check

Search for `// Check if our injected container exists and has all` and add:

```javascript
const hasAll = existing.querySelector('.windows-fixer-promo') &&
               existing.querySelector('.movieshows-promo') &&
               existing.querySelector('.favcreators-promo') &&
               existing.querySelector('.stocks-promo') &&
               existing.querySelector('.mentalhealth-promo') &&
               existing.querySelector('.gotjob-promo') &&
               existing.querySelector('.[NEW]-promo');    // <-- ADD
```

### Step 6: Update JS Hide Selector

Search for `// Hide React's promo sections` and add:

```javascript
document.querySelectorAll('main .windows-fixer-promo, main .movieshows-promo, main .favcreators-promo, main .stocks-promo, main .mentalhealth-promo, main .gotjob-promo, main .[NEW]-promo').forEach(el => {
```

### Step 7: Verify

```bash
node tools/check-promos.js
```

Should show `Visible sections: N/N` where N is the new total.

## 4. Example: Mental Health Promo (Current)

```html
<!-- Mental Health Resources -->
<div class="mentalhealth-promo w-full">
  <div class="promo-banner bg-white/5 rounded-2xl p-5 h-full">
    <div class="flex items-center gap-4 transition-all duration-500 group">
      <div class="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg">
        <span class="text-3xl">🧠</span>
      </div>
      <div class="transition-all duration-500">
        <div class="flex flex-col whitespace-nowrap">
          <span class="text-lg font-bold text-white">Mental Health</span>
          <span class="text-sm text-[var(--text-2)]">Wellness games, crisis support & tools</span>
        </div>
      </div>
      <div class="relative">
        <a class="ml-2 px-5 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-base font-bold text-white transition-all whitespace-nowrap" href="/MENTALHEALTHRESOURCES/" target="_blank">Open App →</a>
      </div>
      <div class="relative group/info">
        <button class="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 text-xs flex items-center justify-center cursor-pointer border-0" style="font-size:14px;">ℹ️</button>
        <div class="absolute left-0 mt-2 w-80 p-4 bg-[#1a1a2e] border border-white/10 rounded-xl shadow-2xl opacity-0 invisible group-hover/info:opacity-100 group-hover/info:visible transition-all duration-300 z-[9999] text-left" style="top: 100%;">
          <p class="text-xs font-bold text-emerald-400 mb-2">💚 Your mental wellness toolkit</p>
          <div class="space-y-2 text-xs text-[var(--text-2)]">
            <p>Free resources for <span class="text-white">stress, anxiety & crisis support</span>.</p>
            <ul class="list-disc list-inside space-y-1 pl-1">
              <li><span class="text-white">🎮 Wellness games</span> — Breathing, grounding, meditation</li>
              <li><span class="text-white">🆘 Crisis lines</span> — 24/7 support by country</li>
              <li><span class="text-white">🌍 Global resources</span> — LGBTQ+, youth, veterans & more</li>
            </ul>
          </div>
          <p class="text-[10px] text-[var(--text-3)] mt-2 italic">If in crisis, call 1-833-456-4566 or text HOME to 741741.</p>
        </div>
      </div>
    </div>
  </div>
</div>
```

## 5. Example: Got Job Promo (Current)

```html
<!-- Got Job / BestieJob -->
<div class="gotjob-promo w-full">
  <div class="promo-banner bg-white/5 rounded-2xl p-5 h-full">
    <div class="flex items-center gap-4 transition-all duration-500 group">
      <div class="w-16 h-16 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg">
        <span class="text-3xl">💼</span>
      </div>
      <div class="transition-all duration-500">
        <div class="flex flex-col whitespace-nowrap">
          <span class="text-lg font-bold text-white">$100K+ Jobs</span>
          <span class="text-sm text-[var(--text-2)]">Toronto tech & creative manager roles</span>
        </div>
      </div>
      <div class="relative">
        <a class="ml-2 px-5 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-base font-bold text-white transition-all whitespace-nowrap" href="/gotjob/" target="_blank">Find Jobs →</a>
      </div>
      <div class="relative group/info">
        <button class="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 text-xs flex items-center justify-center cursor-pointer border-0" style="font-size:14px;">ℹ️</button>
        <div class="absolute right-0 mt-2 w-80 p-4 bg-[#1a1a2e] border border-white/10 rounded-xl shadow-2xl opacity-0 invisible group-hover/info:opacity-100 group-hover/info:visible transition-all duration-300 z-[9999] text-left" style="top: 100%;">
          <p class="text-xs font-bold text-cyan-400 mb-2">🎯 Skip the $60K listings</p>
          <div class="space-y-2 text-xs text-[var(--text-2)]">
            <p>Find <span class="text-white">$100K+ manager roles</span> in Toronto tech & creative.</p>
            <ul class="list-disc list-inside space-y-1 pl-1">
              <li><span class="text-white">💰 Salary filter</span> — Set your minimum ($100K+)</li>
              <li><span class="text-white">🔍 11+ sources</span> — Adzuna, Greenhouse, LinkedIn & more</li>
              <li><span class="text-white">🏠 Remote options</span> — Filter for remote-friendly roles</li>
            </ul>
          </div>
          <p class="text-[10px] text-[var(--text-3)] mt-2 italic">Aggregates 12,000+ listings daily.</p>
        </div>
      </div>
    </div>
  </div>
</div>
```

## 6. Example: Movie/TV Show Trailers (Multiple Buttons)

This section has V1/V2/V3 buttons instead of a single link:

```html
<!-- Movie/TV Show Trailers -->
<div class="movieshows-promo w-full">
  <div class="promo-banner bg-white/5 rounded-2xl p-5 h-full">
    <div class="flex items-center gap-4 transition-all duration-500">
      <div class="w-16 h-16 rounded-full bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg">
        <span class="text-3xl">🎬</span>
      </div>
      <div class="transition-all duration-500">
        <div class="flex flex-col whitespace-nowrap">
          <span class="text-lg font-bold text-white">Movie/TV Show Trailers</span>
          <span class="text-sm text-[var(--text-2)]">Swipe through trailers — your next binge awaits</span>
        </div>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <!-- Multiple version buttons -->
        <a class="px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-sm font-bold text-white transition-all whitespace-nowrap" href="/MOVIESHOWS/" target="_blank">V1 →</a>
        <a class="px-3 py-1.5 rounded-full bg-amber-500/20 hover:bg-amber-500/30 text-sm font-bold text-amber-300 transition-all whitespace-nowrap" href="/movieshows2/" target="_blank">V2 →</a>
        <a class="px-3 py-1.5 rounded-full bg-orange-500/20 hover:bg-orange-500/30 text-sm font-bold text-orange-300 transition-all whitespace-nowrap" href="/movieshows3/" target="_blank">V3 →</a>
        
        <!-- Info Tooltip -->
        <div class="relative group/info">
          <button class="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 text-xs flex items-center justify-center cursor-pointer border-0" style="font-size:14px;">ℹ️</button>
          <div class="absolute left-0 mt-2 w-80 p-4 bg-[#1a1a2e] border border-white/10 rounded-xl shadow-2xl opacity-0 invisible group-hover/info:opacity-100 group-hover/info:visible transition-all duration-300 z-[9999] text-left" style="top: 100%;">
            <p class="text-xs font-bold text-amber-400 mb-2">📺 TikTok-style trailer browsing</p>
            <div class="space-y-2 text-xs text-[var(--text-2)]">
              <div class="p-2 bg-white/5 rounded-lg"><span class="font-bold text-white">V1</span> — Toronto theater info, IMDb + RT ratings, emoji reactions</div>
              <div class="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20"><span class="font-bold text-amber-300">V2</span> — TMDB integration, genre filters, playlist export/import</div>
              <div class="p-2 bg-orange-500/10 rounded-lg border border-orange-500/20"><span class="font-bold text-orange-300">V3</span> — Browse & search, user accounts, likes, auto-scroll, queue</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

## 7. Gradient Colors

| Style | From | To | Use For |
|-------|------|-----|---------|
| Purple | `from-[#667eea]` | `to-[#764ba2]` | Windows Fixer |
| Pink/Rose | `from-pink-500` | `to-rose-600` | Fav Creators |
| Amber/Orange | `from-amber-500` | `to-orange-600` | Movie/TV |
| Blue/Indigo | `from-blue-500` | `to-indigo-600` | Stocks |
| Emerald/Teal | `from-emerald-500` | `to-teal-600` | Mental Health |
| Cyan/Blue | `from-cyan-500` | `to-blue-600` | Got Job |
| Red | `from-red-500` | `to-rose-600` | Custom |

## 8. Tooltip Color Classes

Match the tooltip title color to the gradient:

| Gradient | Tooltip Color Class |
|----------|---------------------|
| Purple | `text-purple-400` |
| Pink/Rose | `text-pink-400` |
| Amber/Orange | `text-amber-400` |
| Blue/Indigo | `text-indigo-400` |
| Emerald/Teal | `text-emerald-400` |
| Cyan/Blue | `text-cyan-400` |

## 9. Tooltip Position

- **Left column** (odd positions: Windows Fixer, Fav Creators, Mental Health): Use `left-0`
- **Right column** (even positions: Movie/TV, Stocks, Got Job): Use `right-0`

This prevents tooltips from going off-screen.

## 10. Quick Modification Reference

| What to Change | Where | Example |
|----------------|-------|---------|
| Icon emoji | `<span class="text-3xl">[ICON]</span>` | `🛠️` → `🔧` |
| Title | `<span class="text-lg font-bold text-white">` | `System Issues?` → `PC Problems?` |
| Subtitle | `<span class="text-sm text-[var(--text-2)]">` | Edit text |
| Button URL | `href="[URL]"` | `/WINDOWSFIXER/` → `/new-path/` |
| Button text | Inside `<a>` or `<button>` tag | `Learn More →` → `Try Now →` |
| Gradient | `bg-gradient-to-br from-[...] to-[...]` | See §7 |
| Tooltip title | `<p class="text-xs font-bold text-[COLOR]-400">` | Edit text and emoji |
| Tooltip content | Inside the tooltip's inner `<div>` | Add/edit lists, text |

## 11. Testing After Changes

```bash
# Quick verification - checks all sections visible
node tools/check-promos.js

# Full JS error test
npx playwright test tests/no_js_errors.spec.ts
```

The check-promos.js script:
- Shows container status
- Lists each promo section found/visible
- Creates screenshot at `test-results/promos-check.png`
- Exits with error code if not all sections visible
