"""Replace old ensureIconLinksFour/showFourViaFallback script with sister's forceBanners script."""
import os

INDEX = os.path.join(os.path.dirname(__file__), "..", "index.html")
with open(INDEX, "r", encoding="utf-8") as f:
    content = f.read()

# Old block: from this script tag (with FAVCREATORS_HTML) until its closing </script> before self.__next_f
START_MARKER = "  <script>\n    (function () {\n      var FAVCREATORS_HTML = "
END_MARKER = "    })();\n  </script>\n  <script>self.__next_f"

aggressive_js = '''  <script>
(function() {
  console.log('[FORCE BANNERS] Aggressive banner protection loaded');

  const FAVCREATORS = '<div class="max-w-7xl mx-auto px-4" style="margin-bottom: 1rem;"><div class="jsx-1b9a23bd3fa6c640 favcreators-promo"><div class="jsx-1b9a23bd3fa6c640 promo-banner"><div class="jsx-1b9a23bd3fa6c640 flex items-center gap-3 transition-all duration-500 opacity-60 grayscale"><div class="jsx-1b9a23bd3fa6c640 w-10 h-10 rounded-full bg-gradient-to-br from-pink-500 to-rose-600 flex items-center justify-center shadow-lg animate-pulse-slow"><span class="jsx-1b9a23bd3fa6c640 text-xl">⭐</span></div><div class="jsx-1b9a23bd3fa6c640 transition-all duration-500 override-overflow max-w-0 opacity-0 overflow-hidden"><div class="jsx-1b9a23bd3fa6c640 flex flex-col whitespace-nowrap"><span class="jsx-1b9a23bd3fa6c640 text-sm font-bold text-white">Fav Creators</span><span class="jsx-1b9a23bd3fa6c640 text-[10px] text-[var(--text-2)]">Live Status & More</span></div></div><a class="jsx-1b9a23bd3fa6c640 ml-2 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-xs font-bold text-white transition-all whitespace-nowrap" href="/fc/#/guest" rel="noopener noreferrer" target="_blank">Open App →</a></div></div></div></div>';

  const STOCKS = '<div class="max-w-7xl mx-auto px-4" style="margin-bottom: 1rem;"><div class="jsx-1b9a23bd3fa6c640 stocks-promo"><div class="jsx-1b9a23bd3fa6c640 promo-banner"><div class="jsx-1b9a23bd3fa6c640 flex items-center gap-3 transition-all duration-500 opacity-60 grayscale"><div class="jsx-1b9a23bd3fa6c640 w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg animate-pulse-slow"><span class="jsx-1b9a23bd3fa6c640 text-xl">📈</span></div><div class="jsx-1b9a23bd3fa6c640 transition-all duration-500 override-overflow max-w-0 opacity-0 overflow-hidden"><div class="jsx-1b9a23bd3fa6c640 flex flex-col whitespace-nowrap"><span class="jsx-1b9a23bd3fa6c640 text-sm font-bold text-white">Stocks</span><span class="jsx-1b9a23bd3fa6c640 text-[10px] text-[var(--text-2)]">Research & Portfolio</span></div></div><a class="jsx-1b9a23bd3fa6c640 ml-2 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-xs font-bold text-white transition-all whitespace-nowrap" href="/findstocks" rel="noopener noreferrer" target="_blank">Open App →</a></div></div></div></div>';

  let restoredCount = 0;

  function forceBanners() {
    const windows = document.querySelector('.windows-fixer-promo');
    const movies = document.querySelector('.movieshows-promo');

    if (!windows || !movies) return;

    const count = document.querySelectorAll('.promo-banner').length;
    if (count >= 4) {
      if (restoredCount === 0) {
        console.log('[FORCE BANNERS] All 4 banners present!');
        restoredCount = 4;
      }
      return;
    }

    const windowsContainer = windows.closest('.max-w-7xl');
    const moviesContainer = movies.closest('.max-w-7xl');

    if (windowsContainer && !document.querySelector('.favcreators-promo')) {
      windowsContainer.insertAdjacentHTML('afterend', FAVCREATORS);
      console.log('[FORCE BANNERS] Restored FavCreators');
      restoredCount++;
    }

    if (moviesContainer && !document.querySelector('.stocks-promo')) {
      moviesContainer.insertAdjacentHTML('afterend', STOCKS);
      console.log('[FORCE BANNERS] Restored Stocks');
      restoredCount++;
    }

    document.querySelectorAll('.favcreators-promo, .stocks-promo').forEach(el => {
      el.style.display = 'block';
      el.style.visibility = 'visible';
      el.style.opacity = '1';
    });
  }

  forceBanners();
  setTimeout(forceBanners, 100);
  setTimeout(forceBanners, 500);
  setTimeout(forceBanners, 1000);
  setTimeout(forceBanners, 2000);
  setTimeout(forceBanners, 3000);

  const observer = new MutationObserver(function() {
    const count = document.querySelectorAll('.promo-banner').length;
    if (count < 4) {
      console.log('[FORCE BANNERS] React removed banners! Restoring...');
      forceBanners();
    }
  });

  setTimeout(function() {
    const main = document.querySelector('main');
    if (main) {
      observer.observe(main, { childList: true, subtree: true });
      console.log('[FORCE BANNERS] Watching for React interference');
    }
  }, 1000);
})();
</script>
'''

start = content.find(START_MARKER)
if start < 0:
    raise SystemExit("Start marker not found (old banner script)")
end = content.find(END_MARKER, start)
if end < 0:
    raise SystemExit("End marker not found (old banner script)")
# Replace from start through "    })();\n  </script>\n", keep "  <script>self.__next_f..."
end_of_block = end + len("    })();\n  </script>\n")
new_content = content[:start] + aggressive_js + content[end_of_block:]
with open(INDEX, "w", encoding="utf-8") as f:
    f.write(new_content)
print("Replaced old banner script with sister forceBanners script.")
