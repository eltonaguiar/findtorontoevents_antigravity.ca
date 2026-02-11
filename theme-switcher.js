/**
 * Theme Switcher — Site-wide theme picker for findtorontoevents.ca
 *
 * Reads window.THEME_REGISTRY (from theme-registry.js) and provides:
 * - A full-screen theme picker overlay (opens from gear button)
 * - CSS variable overrides to re-skin the main page
 * - localStorage persistence in toronto-events-settings
 * - Auto-apply saved theme on page load
 *
 * Selector contract (matches tests/theme-switcher.spec.ts):
 *   #theme-picker-overlay, #theme-picker-panel, #theme-picker-close,
 *   #theme-picker-search, #theme-picker-reset,
 *   [data-category-tab], [data-theme-id], [data-action="apply"],
 *   .theme-card-active
 */
(function () {
  'use strict';

  // ── Registry check ──────────────────────────────────────────────────
  var REGISTRY = window.THEME_REGISTRY;
  if (!REGISTRY || !REGISTRY.length) {
    console.warn('[ThemeSwitcher] No THEME_REGISTRY found. Skipping.');
    return;
  }

  // ── Constants ───────────────────────────────────────────────────────
  var STORAGE_KEY = 'toronto-events-settings';
  var CATEGORIES = ['All', 'Living', 'Still', 'Cyberpunk', 'Light', 'Nature', 'Elegant', 'Retro', 'Space', 'Minimal'];
  var OVERLAY_Z = 100000; // above z-[9999] tooltips

  // ── Default CSS variable snapshot (captured before any theme applied) ──
  var DEFAULT_VARS = {};
  var DEFAULT_BG = '';
  var DEFAULT_COLOR = '';
  var varsToCapture = ['--pk-200', '--pk-300', '--pk-400', '--pk-500', '--pk-500-rgb', '--pk-900', '--surface-0', '--text-2', '--text-3'];

  function captureDefaults() {
    var root = document.documentElement;
    var cs = getComputedStyle(root);
    for (var i = 0; i < varsToCapture.length; i++) {
      DEFAULT_VARS[varsToCapture[i]] = cs.getPropertyValue(varsToCapture[i]).trim();
    }
    DEFAULT_BG = cs.getPropertyValue('background-color').trim() || getComputedStyle(document.body).backgroundColor;
    DEFAULT_COLOR = cs.getPropertyValue('color').trim() || getComputedStyle(document.body).color;
  }

  // ── Utilities ───────────────────────────────────────────────────────
  function hexToRgb(hex) {
    hex = hex.replace('#', '');
    if (hex.length === 3) hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
    var r = parseInt(hex.slice(0, 2), 16);
    var g = parseInt(hex.slice(2, 4), 16);
    var b = parseInt(hex.slice(4, 6), 16);
    return r + ', ' + g + ', ' + b;
  }

  function lighten(hex, pct) {
    hex = hex.replace('#', '');
    var r = parseInt(hex.slice(0, 2), 16);
    var g = parseInt(hex.slice(2, 4), 16);
    var b = parseInt(hex.slice(4, 6), 16);
    r = Math.min(255, Math.round(r + (255 - r) * pct));
    g = Math.min(255, Math.round(g + (255 - g) * pct));
    b = Math.min(255, Math.round(b + (255 - b) * pct));
    return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  }

  function darken(hex, pct) {
    hex = hex.replace('#', '');
    var r = parseInt(hex.slice(0, 2), 16);
    var g = parseInt(hex.slice(2, 4), 16);
    var b = parseInt(hex.slice(4, 6), 16);
    r = Math.max(0, Math.round(r * (1 - pct)));
    g = Math.max(0, Math.round(g * (1 - pct)));
    b = Math.max(0, Math.round(b * (1 - pct)));
    return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  }

  function isLightColor(hex) {
    hex = hex.replace('#', '');
    var r = parseInt(hex.slice(0, 2), 16);
    var g = parseInt(hex.slice(2, 4), 16);
    var b = parseInt(hex.slice(4, 6), 16);
    var luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5;
  }

  // ── Storage ─────────────────────────────────────────────────────────
  function getSettings() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    } catch (e) {
      return {};
    }
  }

  function saveThemeId(id) {
    var s = getSettings();
    s.selectedTheme = id;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  }

  function clearThemeId() {
    var s = getSettings();
    delete s.selectedTheme;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  }

  function getSavedThemeId() {
    return getSettings().selectedTheme || null;
  }

  // Auto-apply: ON by default — clicking a card instantly applies it
  function getAutoApply() {
    var s = getSettings();
    return s.autoApply !== false; // default true
  }

  function setAutoApply(val) {
    var s = getSettings();
    s.autoApply = val;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  }

  // Helper: does this theme have a custom animation?
  // Checks both canvas animations in THEME_ANIMATIONS and CSS-animated themes
  // flagged with "living: true" in the registry.
  function hasAnimation(themeId) {
    if (window.THEME_ANIMATIONS && window.THEME_ANIMATIONS[themeId]) return true;
    var theme = findTheme(themeId);
    return !!(theme && theme.living);
  }

  // ── Theme Application ──────────────────────────────────────────────
  function findTheme(id) {
    for (var i = 0; i < REGISTRY.length; i++) {
      if (REGISTRY[i].id === id) return REGISTRY[i];
    }
    return null;
  }

  // ── Navigation Bar ────────────────────────────────────────────────
  var NAV_LINKS = [
    { href: '/', icon: '&#127968;', label: 'Home' },
    { href: '/WINDOWSFIXER/', icon: '&#128295;', label: 'System Issues' },
    { href: '/MOVIESHOWS/', icon: '&#127909;', label: 'Movies & TV' },
    { href: '/fc/#/guest', icon: '&#11088;', label: 'Fav Creators' },
    { href: '/findstocks/', icon: '&#128200;', label: 'Stock Ideas' },
    { href: '/MENTALHEALTHRESOURCES/', icon: '&#129504;', label: 'Mental Health' },
    { href: '/vr/', icon: '&#129405;', label: 'VR Experience' },
    { href: '/vr/game-arena/', icon: '&#127918;', label: 'Game Arena' },
    { href: '/fc/#/accountability', icon: '&#127919;', label: 'Accountability' },
    { href: '/updates/', icon: '&#128203;', label: 'Updates' },
    { href: '/', icon: '&#127775;', label: 'Other Stuff' },
    { href: '/blog/', icon: '&#128240;', label: 'Blog' }
  ];
  var NAV_BAR_HEIGHT = 44; // approx height of the sticky nav

  function injectNavBar(theme) {
    removeNavBar(); // remove any existing
    var accent = theme.accent || '#ec4899';
    var bg = theme.bg || '#0a0a12';
    var accentAlpha = accent + '33';

    var nav = document.createElement('div');
    nav.id = 'theme-sections-nav';
    // Use position:fixed so we append to body END (not before #__next) — avoids React hydration breakage
    nav.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:10000;display:flex;gap:4px;padding:8px 12px;background:rgba(' + hexToRgb(bg) + ',0.95);backdrop-filter:blur(20px);border-bottom:1px solid ' + accentAlpha + ';overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:thin;';

    for (var i = 0; i < NAV_LINKS.length; i++) {
      var a = document.createElement('a');
      a.href = NAV_LINKS[i].href;
      a.innerHTML = NAV_LINKS[i].icon + ' ' + NAV_LINKS[i].label;
      a.style.cssText = 'display:inline-flex;align-items:center;gap:4px;padding:6px 12px;border-radius:20px;font-size:.75rem;font-weight:600;color:rgba(255,255,255,0.7);text-decoration:none;white-space:nowrap;transition:all .2s;border:1px solid rgba(255,255,255,0.06);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;';
      (function(link) {
        link.addEventListener('mouseenter', function() {
          link.style.background = 'rgba(255,255,255,0.1)';
          link.style.color = '#fff';
          link.style.borderColor = 'rgba(255,255,255,0.15)';
        });
        link.addEventListener('mouseleave', function() {
          link.style.background = 'transparent';
          link.style.color = 'rgba(255,255,255,0.7)';
          link.style.borderColor = 'rgba(255,255,255,0.06)';
        });
      })(a);
      nav.appendChild(a);
    }

    // Append to body END — does NOT disrupt React's #__next hydration tree
    document.body.appendChild(nav);

    // Push body content down so it's not hidden behind the fixed nav
    document.body.style.paddingTop = NAV_BAR_HEIGHT + 'px';

    // Adjust fixed elements that have top positioning
    adjustFixedElements(true);
  }

  function removeNavBar() {
    var existing = document.getElementById('theme-sections-nav');
    if (existing) existing.remove();
    document.body.style.paddingTop = '';
    adjustFixedElements(false);
  }

  function adjustFixedElements(pushed) {
    var topOffset = pushed ? 'calc(1.5rem + ' + NAV_BAR_HEIGHT + 'px)' : '';
    // Sign-in island
    var island = document.getElementById('signin-island');
    if (island) {
      island.style.top = pushed ? 'calc(1.5rem + ' + NAV_BAR_HEIGHT + 'px)' : '1.5rem';
    }
    // Top-right gear container (fixed top-6 right-6 z-[200])
    var topGearContainers = document.querySelectorAll('.fixed.top-6.right-6');
    for (var i = 0; i < topGearContainers.length; i++) {
      topGearContainers[i].style.top = topOffset;
    }
    // Hamburger menu button (fixed top-6 left-6 z-[200])
    var hamburger = document.querySelector('.fixed.top-6.left-6');
    if (hamburger) {
      hamburger.style.top = topOffset;
    }
  }

  // ── Comprehensive CSS Generation ──────────────────────────────────
  function buildThemeCSS(theme) {
    var accent = theme.accent || '#ec4899';
    var bg = theme.bg || '#0a0a12';
    var text = theme.text || '#e0e0e0';
    var cardBg = theme.cardBg || 'rgba(255,255,255,0.05)';
    var cardBorder = theme.cardBorder || 'rgba(255,255,255,0.1)';
    var heroBg = theme.heroBg || bg;
    var headingFont = theme.headingFont || "'Inter',sans-serif";
    var bodyFont = theme.bodyFont || "'Inter',sans-serif";
    var isLight = isLightColor(bg);

    var accentRgb = hexToRgb(accent);
    var accent20 = 'rgba(' + accentRgb + ',0.2)';
    var accent10 = 'rgba(' + accentRgb + ',0.1)';
    var accent30 = 'rgba(' + accentRgb + ',0.3)';
    var accent40 = 'rgba(' + accentRgb + ',0.4)';
    var accent60 = 'rgba(' + accentRgb + ',0.6)';
    var bgRgb = hexToRgb(bg);
    var subtext = isLight ? 'rgba(0,0,0,0.6)' : 'rgba(255,255,255,0.6)';
    var subtextFaint = isLight ? 'rgba(0,0,0,0.4)' : 'rgba(255,255,255,0.4)';
    var borderSoft = isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';
    var borderFaint = isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)';
    var hoverBg = isLight ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)';

    var css = '';

    // ── 0. Content stacking — keep #__next above canvas background ──
    css += '#__next { position: relative; z-index: 1; }\n';
    css += '.fixed-ui-layer { position: relative; z-index: 2; }\n';

    // ── 1. Body & Background ─────────────────────────────────────────
    css += 'body { background: ' + heroBg + ' !important; color: ' + text + ' !important; }\n';
    if (bodyFont !== "'Inter',sans-serif") {
      css += 'body, p, span, div, button, input, textarea, select, li, td, th { font-family: ' + bodyFont + ' !important; }\n';
    }
    if (headingFont !== "'Inter',sans-serif" && headingFont !== bodyFont) {
      css += 'h1, h2, h3, h4, h5, h6 { font-family: ' + headingFont + ' !important; }\n';
    }

    // ── 2. Main heading — "Toronto Events" title ─────────────────────
    css += '#__next h1, .text-4xl, .text-5xl, .text-6xl { color: ' + accent + ' !important; text-shadow: 0 0 30px ' + accent40 + ' !important; }\n';
    // Version badge
    css += '.text-xs.font-bold.opacity-60 { color: ' + subtext + ' !important; }\n';
    // Subtitle text
    css += '.text-sm.leading-relaxed, .text-base.leading-relaxed { color: ' + subtext + ' !important; }\n';

    // ── 3. Glass panels & generic card backgrounds ───────────────────
    css += '.glass-panel { background: ' + cardBg + ' !important; border-color: ' + cardBorder + ' !important; }\n';

    // ── 4. Tailwind background overrides ─────────────────────────────
    if (isLight) {
      css += '.bg-black\\/40, .bg-black\\/80 { background: rgba(255,255,255,0.7) !important; }\n';
      css += '.bg-black\\/60 { background: rgba(255,255,255,0.5) !important; }\n';
      css += '[class*="bg-white\\/5"], [class*="bg-white\\/10"] { background: rgba(0,0,0,0.05) !important; }\n';
    } else {
      css += '.bg-black\\/40 { background: ' + accent10 + ' !important; }\n';
      css += '[class*="bg-white\\/5"] { background: ' + cardBg + ' !important; }\n';
    }

    // ── 5. Border color overrides ────────────────────────────────────
    css += '[class*="border-white\\/10"], [class*="border-white\\/5"] { border-color: ' + borderSoft + ' !important; }\n';
    css += '.border-white\\/20 { border-color: ' + accent20 + ' !important; }\n';

    // ── 6. Text color overrides ──────────────────────────────────────
    if (isLight) {
      css += '.text-white { color: #1a1a2e !important; }\n';
      css += '[class*="text-white\\/"] { color: rgba(26,26,46,0.7) !important; }\n';
      css += '.text-gray-300, .text-gray-400, .text-gray-500 { color: rgba(0,0,0,0.6) !important; }\n';
    } else {
      css += '.text-white { color: ' + text + ' !important; }\n';
      css += '[class*="text-white\\/60"], [class*="text-white\\/70"] { color: ' + subtext + ' !important; }\n';
      css += '[class*="text-white\\/40"], [class*="text-white\\/50"] { color: ' + subtextFaint + ' !important; }\n';
    }

    // ── 7. Promo/App cards grid (System Issues, Movies & TV, etc.) ───
    css += '.promo-banner, [class*="bg-white\\/5"][class*="rounded-2xl"] { background: ' + cardBg + ' !important; border: 1px solid ' + cardBorder + ' !important; }\n';
    css += '.promo-banner:hover, [class*="bg-white\\/5"][class*="rounded-2xl"]:hover { border-color: ' + accent30 + ' !important; box-shadow: 0 8px 30px ' + accent20 + ' !important; }\n';

    // ── 8. Event cards ───────────────────────────────────────────────
    css += '[class*="rounded-xl"][class*="border"][class*="shadow"] { background: ' + cardBg + ' !important; border-color: ' + cardBorder + ' !important; }\n';
    css += '[class*="rounded-xl"][class*="border"][class*="shadow"]:hover { border-color: ' + accent30 + ' !important; box-shadow: 0 12px 40px ' + accent20 + ' !important; }\n';

    // ── 9. Search input ──────────────────────────────────────────────
    css += 'input[placeholder*="Search"], input[type="text"] { background: ' + (isLight ? 'rgba(0,0,0,0.04)' : 'rgba(255,255,255,0.06)') + ' !important; border-color: ' + borderSoft + ' !important; color: ' + text + ' !important; }\n';
    css += 'input:focus { border-color: ' + accent + ' !important; box-shadow: 0 0 12px ' + accent30 + ' !important; }\n';
    css += 'input::placeholder { color: ' + subtextFaint + ' !important; }\n';

    // ── 10. Category filter buttons ──────────────────────────────────
    css += 'button[class*="rounded-full"][class*="text-sm"], button[class*="rounded-full"][class*="text-xs"] { border-color: ' + accent30 + ' !important; color: ' + text + ' !important; }\n';
    css += 'button[class*="rounded-full"][class*="text-sm"]:hover, button[class*="rounded-full"][class*="text-xs"]:hover { background: ' + accent20 + ' !important; }\n';
    // Active filter state
    css += 'button[class*="rounded-full"][class*="bg-[var(--pk-500)]"] { background: ' + accent + ' !important; color: ' + (isLight ? '#fff' : bg) + ' !important; border-color: ' + accent + ' !important; }\n';

    // ── 11. Sign-in island ───────────────────────────────────────────
    css += '#signin-island button, #signin-island a { background: ' + accent10 + ' !important; border-color: ' + accent30 + ' !important; color: ' + text + ' !important; }\n';
    css += '#signin-island button:hover, #signin-island a:hover { background: ' + accent + ' !important; color: ' + (isLight ? '#fff' : bg) + ' !important; }\n';

    // ── 12. Gear buttons ─────────────────────────────────────────────
    // Top-right gear
    css += '.fixed.top-6.right-6 button { background: ' + accent10 + ' !important; border-color: ' + accent30 + ' !important; }\n';
    css += '.fixed.top-6.right-6 button:hover { background: ' + accent + ' !important; }\n';
    // Bottom-right gear
    css += '.fixed.bottom-6.right-6 button { color: ' + accent + ' !important; }\n';
    css += '.fixed.bottom-6.right-6 button:hover { box-shadow: 0 0 40px ' + accent60 + ' !important; }\n';

    // ── 13. Glow animations (recolor to accent) ──────────────────────
    css += '@keyframes signInGlow {\n';
    css += '  0%, 100% { box-shadow: 0 0 8px ' + accent40 + ', 0 0 16px ' + accent20 + '; }\n';
    css += '  50% { box-shadow: 0 0 16px ' + accent60 + ', 0 0 32px ' + accent30 + '; }\n';
    css += '}\n';
    css += '@keyframes navGlow {\n';
    css += '  0%, 100% { box-shadow: 0 0 8px ' + accent30 + ', 0 0 16px ' + accent20 + '; }\n';
    css += '  50% { box-shadow: 0 0 16px ' + accent40 + ', 0 0 32px ' + accent20 + '; }\n';
    css += '}\n';
    css += '.nav-glow-signin { border-color: ' + accent30 + ' !important; }\n';
    css += '.nav-glow-favcreators { border-color: ' + accent30 + ' !important; }\n';

    // ── 14. "Other Stuff" section + slide-out menu ───────────────────
    css += '.otherstuff-glow { box-shadow: 0 0 12px ' + accent30 + ', 0 0 24px ' + accent20 + ' !important; }\n';
    // Quick Nav slide-out panel (the 300px sidebar, not the hamburger button itself)
    css += '.fixed-ui-layer .fixed.top-0.left-0.h-full { background: rgba(' + bgRgb + ',0.97) !important; }\n';

    // ── 15. Links & accent-colored text ──────────────────────────────
    css += 'a[class*="text-pink"], a[class*="text-blue"], a[class*="text-indigo"] { color: ' + accent + ' !important; }\n';
    css += '[class*="text-\\[var\\(--pk-"] { color: ' + accent + ' !important; }\n';
    css += '[class*="bg-\\[var\\(--pk-"] { background-color: ' + accent + ' !important; }\n';

    // ── 16. Scrollbar ────────────────────────────────────────────────
    css += '::-webkit-scrollbar { width: 8px; }\n';
    css += '::-webkit-scrollbar-track { background: ' + bg + '; }\n';
    css += '::-webkit-scrollbar-thumb { background: ' + accent30 + '; border-radius: 4px; }\n';
    css += '::-webkit-scrollbar-thumb:hover { background: ' + accent40 + '; }\n';

    // ── 17. Shadows ──────────────────────────────────────────────────
    css += '.shadow-2xl { box-shadow: 0 25px 50px -12px ' + accent20 + ' !important; }\n';
    css += '.shadow-lg { box-shadow: 0 10px 30px ' + accent10 + ' !important; }\n';

    // ── 18. Gradient text (gold shimmer nav) ─────────────────────────
    css += '.gold-glow-nav { background: linear-gradient(90deg, ' + accent + ', ' + lighten(accent, 0.3) + ', ' + accent + ') !important; }\n';

    // ── 19. Nav bar theming ──────────────────────────────────────────
    css += '#theme-sections-nav { background: rgba(' + bgRgb + ',0.95) !important; border-bottom-color: ' + accent30 + ' !important; }\n';
    css += '#theme-sections-nav a { color: ' + subtext + ' !important; border-color: ' + borderFaint + ' !important; }\n';
    css += '#theme-sections-nav a:hover { background: ' + hoverBg + ' !important; color: ' + text + ' !important; border-color: ' + borderSoft + ' !important; }\n';
    // Hide scrollbar in nav
    css += '#theme-sections-nav::-webkit-scrollbar { height: 3px; }\n';
    css += '#theme-sections-nav::-webkit-scrollbar-thumb { background: ' + accent20 + '; border-radius: 2px; }\n';

    // ── 20. Hamburger menu button ─────────────────────────────────────
    css += 'button.fixed.top-6.left-6, .fixed.top-6.left-6 button, button.fixed.top-4.left-4 { background: ' + accent10 + ' !important; border-color: ' + accent30 + ' !important; color: ' + text + ' !important; }\n';

    // ── 21. "View Event" link buttons ────────────────────────────────
    css += 'a[class*="rounded"][class*="bg-"][class*="text-sm"] { background: ' + accent20 + ' !important; color: ' + accent + ' !important; }\n';
    css += 'a[class*="rounded"][class*="bg-"][class*="text-sm"]:hover { background: ' + accent40 + ' !important; }\n';

    // ── 22. Date/location text in event cards ────────────────────────
    css += '.text-xs[class*="text-"], .text-sm[class*="opacity"] { color: ' + subtext + ' !important; }\n';

    // ── 23. Category badges (EVENT, MUSIC, etc.) ─────────────────────
    css += '[class*="rounded"][class*="text-xs"][class*="font-bold"][class*="uppercase"] { background: ' + accent20 + ' !important; color: ' + accent + ' !important; }\n';

    return css;
  }

  function applyTheme(themeId) {
    var theme = findTheme(themeId);
    if (!theme) return;

    var root = document.documentElement;
    var accent = theme.accent || '#ec4899';

    // Core accent variables
    root.style.setProperty('--pk-500', accent);
    root.style.setProperty('--pk-500-rgb', hexToRgb(accent));
    root.style.setProperty('--pk-300', lighten(accent, 0.4));
    root.style.setProperty('--pk-400', lighten(accent, 0.2));
    root.style.setProperty('--pk-200', lighten(accent, 0.6));
    root.style.setProperty('--pk-900', darken(accent, 0.6));

    // Surface and text
    if (theme.bg) {
      root.style.setProperty('--surface-0', theme.bg);
    }

    // Build and inject comprehensive override stylesheet
    var styleId = 'theme-override';
    var existing = document.getElementById(styleId);
    if (existing) existing.remove();

    var style = document.createElement('style');
    style.id = styleId;
    style.textContent = buildThemeCSS(theme);
    document.head.appendChild(style);

    // Load Google Font if needed
    loadThemeFont(theme);

    // Inject top navigation bar
    injectNavBar(theme);

    // Inject animated canvas background (particle constellation)
    injectAnimatedBg(theme);

    // Save
    saveThemeId(themeId);

    // Update picker if open
    updateActiveIndicator(themeId);

    // Show toast
    showToast('Theme applied: ' + theme.name);
  }

  function resetTheme() {
    var root = document.documentElement;

    // Restore captured defaults
    for (var v in DEFAULT_VARS) {
      if (DEFAULT_VARS[v]) {
        root.style.setProperty(v, DEFAULT_VARS[v]);
      } else {
        root.style.removeProperty(v);
      }
    }

    // Remove override stylesheet
    var existing = document.getElementById('theme-override');
    if (existing) existing.remove();

    // Remove nav bar
    removeNavBar();

    // Remove animated background
    removeAnimatedBg();

    // Remove any loaded theme fonts
    var fontLink = document.getElementById('theme-font-link');
    if (fontLink) fontLink.remove();

    // Clear storage
    clearThemeId();

    // Update picker
    updateActiveIndicator(null);

    showToast('Theme reset to default');
  }

  // ── Font Loading ────────────────────────────────────────────────────
  var loadedFonts = {};

  function loadThemeFont(theme) {
    var fonts = [];
    if (theme.headingFont) {
      var m = theme.headingFont.match(/'([^']+)'/);
      if (m && m[1] !== 'Inter') fonts.push(m[1]);
    }
    if (theme.bodyFont) {
      var m2 = theme.bodyFont.match(/'([^']+)'/);
      if (m2 && m2[1] !== 'Inter' && fonts.indexOf(m2[1]) === -1) fonts.push(m2[1]);
    }
    if (fonts.length === 0) return;

    // Remove previous theme font link
    var old = document.getElementById('theme-font-link');
    if (old) old.remove();

    var families = fonts.map(function (f) { return f.replace(/ /g, '+') + ':wght@400;700'; }).join('&family=');
    var link = document.createElement('link');
    link.id = 'theme-font-link';
    link.rel = 'stylesheet';
    link.href = 'https://fonts.googleapis.com/css2?family=' + families + '&display=swap';
    document.head.appendChild(link);
  }

  // ── Animated Canvas Background ─────────────────────────────────────
  // Uses per-theme animations from window.THEME_ANIMATIONS (theme-animations.js)
  // Falls back to generic particle animation for themes without specific code.
  var _animGeneration = 0; // incremented on each apply/remove to stop orphaned loops

  function injectAnimatedBg(theme) {
    removeAnimatedBg(); // remove any existing canvas + stop loop

    var canvas = document.createElement('canvas');
    canvas.id = 'bg-canvas'; // same ID as blog pages use — animation code expects this
    canvas.setAttribute('aria-hidden', 'true');
    var canvasCSS = 'position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;';
    canvas.style.cssText = canvasCSS;
    document.body.appendChild(canvas);

    _animGeneration++;
    var myGen = _animGeneration;

    // Check for theme-specific animation code
    var animCode = window.THEME_ANIMATIONS && window.THEME_ANIMATIONS[theme.id];
    if (animCode) {
      // Auto-detect canvas opacity from animation rendering pattern:
      //  - clearRect animations redraw from scratch each frame (canvas stays transparent) → opacity 1
      //  - fillRect with rgba accumulates trails (canvas goes opaque over time) → opacity 0.3
      var usesClearRect = animCode.indexOf('clearRect(0,0,c.width,c.height)') !== -1;
      canvas.style.opacity = usesClearRect ? '1' : '0.3';

      // Inject a generation check so the loop auto-stops when theme changes.
      // We inject an early-return guard at the TOP of draw() rather than wrapping
      // the requestAnimationFrame call, so `draw` stays in its own closure scope.
      window._themeAnimGen = myGen;
      var guardedCode = animCode.replace(
        /function draw\(\)\{/g,
        'function draw(){if(window._themeAnimGen!==' + myGen + ')return;'
      );
      try {
        eval(guardedCode);
      } catch (e) {
        console.warn('[ThemeSwitcher] Animation eval error for ' + theme.id + ':', e);
        _runGenericParticles(canvas, theme, myGen);
      }
    } else {
      // Generic particle/constellation animation (uses clearRect → full opacity is fine)
      _runGenericParticles(canvas, theme, myGen);
    }
  }

  function _runGenericParticles(canvas, theme, gen) {
    var ctx = canvas.getContext('2d');
    var accent = theme.accent || '#d4af37';
    var accent2 = darken(accent, 0.15);

    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    var pts = [];
    for (var i = 0; i < 80; i++) {
      pts.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.7,
        vy: (Math.random() - 0.5) * 0.7,
        r: Math.random() * 3 + 1
      });
    }

    function draw() {
      if (window._themeAnimGen !== gen) return; // stop if generation changed
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (var i = 0; i < pts.length; i++) {
        var p = pts[i];
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = i % 2 === 0 ? accent : accent2;
        ctx.globalAlpha = 0.6;
        ctx.fill();
        for (var j = i + 1; j < pts.length; j++) {
          var q = pts[j];
          var dx = p.x - q.x;
          var dy = p.y - q.y;
          var d = Math.sqrt(dx * dx + dy * dy);
          if (d < 120) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.strokeStyle = accent;
            ctx.globalAlpha = 0.15 * (1 - d / 120);
            ctx.stroke();
          }
        }
      }
      ctx.globalAlpha = 1;
      requestAnimationFrame(function () { if (window._themeAnimGen === gen) draw(); });
    }

    window._themeAnimGen = gen;
    draw();
  }

  function removeAnimatedBg() {
    _animGeneration++; // invalidates any running animation loop
    window._themeAnimGen = _animGeneration;
    var canvas = document.getElementById('bg-canvas');
    if (canvas) canvas.remove();
  }

  // ── Toast ───────────────────────────────────────────────────────────
  function showToast(msg) {
    var existing = document.getElementById('theme-toast');
    if (existing) existing.remove();

    var toast = document.createElement('div');
    toast.id = 'theme-toast';
    toast.textContent = msg;
    toast.style.cssText = 'position:fixed;bottom:90px;left:50%;transform:translateX(-50%);z-index:' + (OVERLAY_Z + 10) + ';background:rgba(0,0,0,0.85);color:#fff;padding:10px 24px;border-radius:12px;font-size:14px;font-weight:600;pointer-events:none;opacity:0;transition:opacity 0.3s;backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,0.1);';
    document.body.appendChild(toast);

    requestAnimationFrame(function () {
      toast.style.opacity = '1';
    });

    setTimeout(function () {
      toast.style.opacity = '0';
      setTimeout(function () { toast.remove(); }, 300);
    }, 2000);
  }

  // ── Picker UI ──────────────────────────────────────────────────────
  var pickerOpen = false;
  var currentCategory = 'all';
  var searchQuery = '';

  function createPicker() {
    if (document.getElementById('theme-picker-overlay')) return;

    // Overlay — transparent click-catcher (no blur, no dark bg — user sees live theme preview)
    var overlay = document.createElement('div');
    overlay.id = 'theme-picker-overlay';
    overlay.style.cssText = 'position:fixed;inset:0;z-index:' + OVERLAY_Z + ';background:transparent;display:none;';
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closePicker();
    });

    // Panel — right-side slide-in drawer (no backdrop blur — live preview behind it)
    var panel = document.createElement('div');
    panel.id = 'theme-picker-panel';
    panel.style.cssText = 'position:fixed;top:0;right:0;bottom:0;z-index:' + (OVERLAY_Z + 1) + ';width:380px;max-width:90vw;background:rgba(13,13,26,0.97);border-left:1px solid rgba(255,255,255,0.1);display:none;flex-direction:column;overflow:hidden;transform:translateX(100%);transition:transform 0.3s ease;box-shadow:-10px 0 40px rgba(0,0,0,0.5);';

    // Header
    var header = document.createElement('div');
    header.style.cssText = 'padding:20px 24px 16px;border-bottom:1px solid rgba(255,255,255,0.06);flex-shrink:0;';

    var headerTop = document.createElement('div');
    headerTop.style.cssText = 'display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;';

    var title = document.createElement('h2');
    title.textContent = 'Choose Your Theme';
    title.style.cssText = 'color:#fff;font-size:20px;font-weight:700;margin:0;letter-spacing:0.5px;';

    var closeBtn = document.createElement('button');
    closeBtn.id = 'theme-picker-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.style.cssText = 'background:none;border:none;color:#888;font-size:28px;cursor:pointer;padding:0 4px;line-height:1;transition:color 0.2s;';
    closeBtn.addEventListener('mouseenter', function () { closeBtn.style.color = '#fff'; });
    closeBtn.addEventListener('mouseleave', function () { closeBtn.style.color = '#888'; });
    closeBtn.addEventListener('click', closePicker);

    headerTop.appendChild(title);
    headerTop.appendChild(closeBtn);
    header.appendChild(headerTop);

    // Search bar
    var searchRow = document.createElement('div');
    searchRow.style.cssText = 'display:flex;gap:10px;align-items:center;';

    var searchInput = document.createElement('input');
    searchInput.id = 'theme-picker-search';
    searchInput.type = 'text';
    searchInput.placeholder = 'Search themes...';
    searchInput.style.cssText = 'flex:1;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:8px 14px;color:#fff;font-size:14px;outline:none;transition:border-color 0.2s;';
    searchInput.addEventListener('focus', function () { searchInput.style.borderColor = 'rgba(255,255,255,0.3)'; });
    searchInput.addEventListener('blur', function () { searchInput.style.borderColor = 'rgba(255,255,255,0.1)'; });
    searchInput.addEventListener('input', function () {
      searchQuery = searchInput.value.toLowerCase();
      renderCards();
    });

    var resetBtn = document.createElement('button');
    resetBtn.id = 'theme-picker-reset';
    resetBtn.textContent = 'Reset';
    resetBtn.style.cssText = 'background:rgba(239,68,68,0.15);border:1px solid rgba(239,68,68,0.3);color:#ef4444;padding:8px 16px;border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap;transition:all 0.2s;';
    resetBtn.addEventListener('mouseenter', function () { resetBtn.style.background = 'rgba(239,68,68,0.3)'; });
    resetBtn.addEventListener('mouseleave', function () { resetBtn.style.background = 'rgba(239,68,68,0.15)'; });
    resetBtn.addEventListener('click', function () {
      resetTheme();
      renderCards();
    });

    searchRow.appendChild(searchInput);
    searchRow.appendChild(resetBtn);
    header.appendChild(searchRow);

    // Auto-apply toggle
    var autoRow = document.createElement('div');
    autoRow.style.cssText = 'display:flex;align-items:center;gap:8px;margin-top:10px;';

    var autoLabel = document.createElement('label');
    autoLabel.style.cssText = 'display:flex;align-items:center;gap:8px;cursor:pointer;font-size:12px;color:#aab;user-select:none;';

    var autoCheck = document.createElement('input');
    autoCheck.type = 'checkbox';
    autoCheck.id = 'theme-auto-apply';
    autoCheck.checked = getAutoApply();
    autoCheck.style.cssText = 'accent-color:#88aaff;width:16px;height:16px;cursor:pointer;';
    autoCheck.addEventListener('change', function () {
      setAutoApply(autoCheck.checked);
    });

    var autoText = document.createElement('span');
    autoText.textContent = 'Auto-apply on click';

    autoLabel.appendChild(autoCheck);
    autoLabel.appendChild(autoText);
    autoRow.appendChild(autoLabel);
    header.appendChild(autoRow);

    // Category tabs
    var tabsRow = document.createElement('div');
    tabsRow.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;margin-top:12px;';

    for (var ci = 0; ci < CATEGORIES.length; ci++) {
      (function (catName) {
        var tab = document.createElement('button');
        tab.setAttribute('data-category-tab', catName.toLowerCase());
        tab.textContent = catName;
        tab.style.cssText = 'padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;transition:all 0.2s;border:1px solid rgba(255,255,255,0.08);background:transparent;color:#888;';

        if (catName.toLowerCase() === currentCategory) {
          tab.style.background = 'rgba(136,170,255,0.15)';
          tab.style.borderColor = 'rgba(136,170,255,0.3)';
          tab.style.color = '#88aaff';
        }

        tab.addEventListener('click', function () {
          currentCategory = catName.toLowerCase();
          // Update tab styles
          var allTabs = tabsRow.querySelectorAll('[data-category-tab]');
          for (var t = 0; t < allTabs.length; t++) {
            allTabs[t].style.background = 'transparent';
            allTabs[t].style.borderColor = 'rgba(255,255,255,0.08)';
            allTabs[t].style.color = '#888';
          }
          tab.style.background = 'rgba(136,170,255,0.15)';
          tab.style.borderColor = 'rgba(136,170,255,0.3)';
          tab.style.color = '#88aaff';
          renderCards();
        });

        tabsRow.appendChild(tab);
      })(CATEGORIES[ci]);
    }

    header.appendChild(tabsRow);
    panel.appendChild(header);

    // Grid container
    var grid = document.createElement('div');
    grid.id = 'theme-picker-grid';
    grid.style.cssText = 'flex:1;overflow-y:auto;padding:16px 16px 20px;display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;align-content:start;';
    panel.appendChild(grid);

    // Count
    var countBar = document.createElement('div');
    countBar.id = 'theme-picker-count';
    countBar.style.cssText = 'padding:10px 24px;border-top:1px solid rgba(255,255,255,0.06);font-size:12px;color:#556;text-align:center;flex-shrink:0;';
    panel.appendChild(countBar);

    overlay.appendChild(panel);
    document.body.appendChild(overlay);

    // Render initial cards
    renderCards();
  }

  function renderCards() {
    var grid = document.getElementById('theme-picker-grid');
    var countBar = document.getElementById('theme-picker-count');
    if (!grid) return;

    grid.innerHTML = '';

    var savedId = getSavedThemeId();
    var filtered = REGISTRY.filter(function (t) {
      var matchesCategory;
      if (currentCategory === 'all') {
        matchesCategory = true;
      } else if (currentCategory === 'living') {
        matchesCategory = hasAnimation(t.id);
      } else if (currentCategory === 'still') {
        matchesCategory = !hasAnimation(t.id);
      } else {
        matchesCategory = (t.category || '').toLowerCase() === currentCategory;
      }
      var matchesSearch = !searchQuery || (t.name || '').toLowerCase().indexOf(searchQuery) !== -1 || (t.tagline || '').toLowerCase().indexOf(searchQuery) !== -1;
      return matchesCategory && matchesSearch;
    });

    if (countBar) {
      countBar.textContent = filtered.length + ' of ' + REGISTRY.length + ' themes';
    }

    if (filtered.length === 0) {
      var empty = document.createElement('div');
      empty.style.cssText = 'grid-column:1/-1;text-align:center;padding:40px 20px;color:#556;';
      empty.textContent = 'No themes match your search.';
      grid.appendChild(empty);
      return;
    }

    for (var i = 0; i < filtered.length; i++) {
      grid.appendChild(createCard(filtered[i], savedId));
    }
  }

  function createCard(theme, activeId) {
    var card = document.createElement('div');
    card.setAttribute('data-theme-id', theme.id);
    var isActive = theme.id === activeId;
    if (isActive) card.classList.add('theme-card-active');

    card.style.cssText = 'background:rgba(255,255,255,0.04);border:1px solid ' + (isActive ? 'rgba(136,170,255,0.5)' : 'rgba(255,255,255,0.08)') + ';border-radius:14px;padding:14px;cursor:pointer;transition:all 0.2s;position:relative;display:flex;flex-direction:column;gap:10px;';

    card.addEventListener('mouseenter', function () {
      if (!card.classList.contains('theme-card-active')) {
        card.style.borderColor = 'rgba(255,255,255,0.2)';
        card.style.background = 'rgba(255,255,255,0.07)';
      }
    });
    card.addEventListener('mouseleave', function () {
      if (!card.classList.contains('theme-card-active')) {
        card.style.borderColor = 'rgba(255,255,255,0.08)';
        card.style.background = 'rgba(255,255,255,0.04)';
      }
    });

    // Auto-apply: clicking anywhere on the card applies immediately
    (function (tid) {
      card.addEventListener('click', function () {
        if (getAutoApply() && tid !== getSavedThemeId()) {
          applyTheme(tid);
          renderCards();
        }
      });
    })(theme.id);

    // Color swatch
    var swatch = document.createElement('div');
    swatch.style.cssText = 'height:48px;border-radius:10px;position:relative;overflow:hidden;';
    swatch.style.background = theme.heroBg || theme.bg || '#1a1a2e';

    // Accent dot
    var dot = document.createElement('div');
    dot.style.cssText = 'position:absolute;bottom:6px;right:6px;width:18px;height:18px;border-radius:50%;border:2px solid rgba(255,255,255,0.3);';
    dot.style.background = theme.accent || '#ec4899';
    swatch.appendChild(dot);

    // Active check mark
    if (isActive) {
      var check = document.createElement('div');
      check.style.cssText = 'position:absolute;top:6px;right:6px;width:22px;height:22px;border-radius:50%;background:#22c55e;display:flex;align-items:center;justify-content:center;font-size:13px;color:#fff;';
      check.textContent = '\u2713';
      swatch.appendChild(check);
    }

    card.appendChild(swatch);

    // Living badge — pulsing dot for themes with animations
    if (hasAnimation(theme.id)) {
      var livingDot = document.createElement('div');
      livingDot.style.cssText = 'position:absolute;top:8px;left:8px;width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 6px #22c55e;animation:theme-pulse 2s ease-in-out infinite;';
      livingDot.title = 'Animated theme';
      swatch.appendChild(livingDot);
    }

    // Name + tagline
    var nameEl = document.createElement('div');
    nameEl.style.cssText = 'font-size:13px;font-weight:700;color:#fff;line-height:1.3;';
    nameEl.textContent = theme.name || theme.id;
    card.appendChild(nameEl);

    if (theme.tagline) {
      var tagline = document.createElement('div');
      tagline.style.cssText = 'font-size:11px;color:#667;line-height:1.3;margin-top:-4px;';
      tagline.textContent = theme.tagline;
      card.appendChild(tagline);
    }

    // Buttons row
    var btns = document.createElement('div');
    btns.style.cssText = 'display:flex;gap:6px;margin-top:auto;';

    var applyBtn = document.createElement('button');
    applyBtn.setAttribute('data-action', 'apply');
    applyBtn.textContent = isActive ? 'Applied' : 'Apply';
    applyBtn.style.cssText = 'flex:1;padding:6px 0;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer;transition:all 0.2s;border:none;' + (isActive ? 'background:#22c55e;color:#fff;' : 'background:rgba(136,170,255,0.15);color:#88aaff;');

    if (!isActive) {
      applyBtn.addEventListener('mouseenter', function () { applyBtn.style.background = 'rgba(136,170,255,0.3)'; });
      applyBtn.addEventListener('mouseleave', function () { applyBtn.style.background = 'rgba(136,170,255,0.15)'; });
    }

    applyBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      applyTheme(theme.id);
      renderCards();
    });

    var previewBtn = document.createElement('button');
    previewBtn.textContent = 'Preview';
    previewBtn.style.cssText = 'padding:6px 12px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;transition:all 0.2s;border:1px solid rgba(255,255,255,0.1);background:transparent;color:#888;';
    previewBtn.addEventListener('mouseenter', function () { previewBtn.style.borderColor = 'rgba(255,255,255,0.3)'; previewBtn.style.color = '#fff'; });
    previewBtn.addEventListener('mouseleave', function () { previewBtn.style.borderColor = 'rgba(255,255,255,0.1)'; previewBtn.style.color = '#888'; });
    previewBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      if (theme.previewUrl) {
        window.open(theme.previewUrl, '_blank');
      }
    });

    btns.appendChild(applyBtn);
    btns.appendChild(previewBtn);
    card.appendChild(btns);

    return card;
  }

  function updateActiveIndicator(activeId) {
    var cards = document.querySelectorAll('[data-theme-id]');
    for (var i = 0; i < cards.length; i++) {
      cards[i].classList.remove('theme-card-active');
      if (cards[i].getAttribute('data-theme-id') === activeId) {
        cards[i].classList.add('theme-card-active');
      }
    }
  }

  // ── Open / Close ───────────────────────────────────────────────────
  function openPicker() {
    createPicker();
    var overlay = document.getElementById('theme-picker-overlay');
    var panel = document.getElementById('theme-picker-panel');
    if (!overlay || !panel) return;

    overlay.style.display = 'block';
    panel.style.display = 'flex';
    // Don't lock body scroll — user should be able to scroll and see the page behind

    requestAnimationFrame(function () {
      panel.style.transform = 'translateX(0)';
    });

    pickerOpen = true;

    // Focus search
    var search = document.getElementById('theme-picker-search');
    if (search) setTimeout(function () { search.focus(); }, 300);
  }

  function closePicker() {
    var overlay = document.getElementById('theme-picker-overlay');
    var panel = document.getElementById('theme-picker-panel');
    if (!overlay || !panel) return;

    panel.style.transform = 'translateX(100%)';

    setTimeout(function () {
      overlay.style.display = 'none';
      panel.style.display = 'none';
      pickerOpen = false;
    }, 300);
  }

  // ── Gear Button Interception (event delegation — survives React hydration) ──
  function isGearButton(el) {
    // Walk up from click target to find the gear button or its container
    var node = el;
    for (var i = 0; i < 6 && node; i++) {
      if (node.tagName === 'BUTTON' && node.getAttribute('aria-label') === 'Open Settings') return true;
      // Check if inside the fixed bottom-right gear container
      if (node.classList && node.classList.contains('fixed') &&
          node.classList.contains('bottom-6') && node.classList.contains('right-6')) return true;
      node = node.parentElement;
    }
    return false;
  }

  // Use document-level capture listener — immune to React DOM replacement
  document.addEventListener('click', function (e) {
    if (isGearButton(e.target)) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      if (pickerOpen) {
        closePicker();
      } else {
        openPicker();
      }
    }
  }, true); // capture phase — fires before React's delegation

  // ── ESC key handler ─────────────────────────────────────────────────
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && pickerOpen) {
      e.preventDefault();
      e.stopPropagation();
      closePicker();
    }
  }, true);

  // ── Responsive grid ─────────────────────────────────────────────────
  function injectResponsiveStyles() {
    var style = document.createElement('style');
    style.id = 'theme-picker-styles';
    style.textContent = [
      '#theme-picker-grid::-webkit-scrollbar { width: 6px; }',
      '#theme-picker-grid::-webkit-scrollbar-track { background: transparent; }',
      '#theme-picker-grid::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }',
      '#theme-picker-grid::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }',
      '@keyframes theme-pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.3); } }',
      '@media (max-width: 600px) {',
      '  #theme-picker-panel { width: 100vw !important; max-width: 100vw !important; }',
      '  #theme-picker-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)) !important; gap: 10px !important; padding: 12px !important; }',
      '}',
    ].join('\n');
    document.head.appendChild(style);
  }

  // ── Init ────────────────────────────────────────────────────────────
  function init() {
    captureDefaults();
    injectResponsiveStyles();

    // Apply saved theme immediately
    var savedId = getSavedThemeId();
    if (savedId && findTheme(savedId)) {
      applyTheme(savedId);
      // React hydration may overwrite CSS vars after our initial apply.
      // Re-apply after a delay to ensure the theme survives hydration.
      setTimeout(function () {
        var stillSaved = getSavedThemeId();
        if (stillSaved && findTheme(stillSaved)) {
          var current = getComputedStyle(document.documentElement).getPropertyValue('--pk-500').trim();
          var expected = findTheme(stillSaved).accent || '#ec4899';
          if (current !== expected) {
            applyTheme(stillSaved);
          }
        }
      }, 2500);
    } else {
      // Always show nav bar even without a theme — use default site colors
      injectNavBar({ accent: '#ec4899', bg: '#0a0a12', text: '#ffffff' });
    }

    // Gear button interception is handled by document-level event delegation
    // (set up above) — no retries needed, survives React hydration
  }

  // Run init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
