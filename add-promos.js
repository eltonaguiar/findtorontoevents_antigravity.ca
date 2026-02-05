// Add missing promo banners after React hydration
(function() {
  'use strict';
  
  const PROMOS = {
    favcreators: {
      class: 'favcreators-promo',
      html: `<div class="max-w-7xl mx-auto px-4" style="margin-bottom: 1rem; display: block !important; visibility: visible !important;">
        <div class="jsx-1b9a23bd3fa6c640 favcreators-promo" style="display: block !important; visibility: visible !important;">
          <div class="jsx-1b9a23bd3fa6c640 promo-banner" style="display: block !important; visibility: visible !important; position: relative; z-index: auto;">
            <div class="jsx-1b9a23bd3fa6c640 flex items-center gap-3 transition-all duration-500 opacity-60 grayscale hover:opacity-100 hover:grayscale-0 group" style="display: flex !important; visibility: visible !important; position: relative;">
              <div class="jsx-1b9a23bd3fa6c640 w-10 h-10 rounded-full bg-gradient-to-br from-pink-500 to-rose-600 flex items-center justify-center shadow-lg animate-pulse-slow">
                <span class="jsx-1b9a23bd3fa6c640 text-xl">💎</span>
              </div>
              <div class="jsx-1b9a23bd3fa6c640 transition-all duration-500 override-overflow max-w-0 opacity-0 overflow-hidden group-hover:max-w-xs group-hover:opacity-100" style="max-width: 0;">
                <div class="jsx-1b9a23bd3fa6c640 flex flex-col whitespace-nowrap">
                  <span class="jsx-1b9a23bd3fa6c640 text-sm font-bold text-white">Fav Creators</span>
                  <span class="jsx-1b9a23bd3fa6c640 text-[10px] text-[var(--text-2)]">Track creators across TikTok, Twitch, Kick & YouTube</span>
                </div>
              </div>
              <div class="jsx-1b9a23bd3fa6c640" style="position: relative;">
                <a class="jsx-1b9a23bd3fa6c640 ml-2 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-xs font-bold text-white transition-all whitespace-nowrap" href="/fc/#/guest" target="_blank">Open App →</a>
                <div class="jsx-1b9a23bd3fa6c640 absolute" style="
                  position: absolute;
                  right: 0;
                  top: calc(100% + 8px);
                  width: 260px;
                  padding: 12px;
                  background: rgba(30, 30, 40, 0.98);
                  backdrop-filter: blur(10px);
                  border: 1px solid rgba(255,255,255,0.1);
                  border-radius: 8px;
                  box-shadow: 0 10px 40px rgba(0,0,0,0.5);
                  opacity: 0;
                  visibility: hidden;
                  transform: translateY(-10px);
                  transition: all 0.3s ease;
                  z-index: 10000;
                  pointer-events: none;
                ">
                  <p class="text-xs text-[var(--text-2)]" style="line-height: 1.4; margin: 0 0 8px 0;">Track your favorite creators across TikTok, Twitch, Kick and YouTube!</p>
                  <div class="flex gap-2">
                    <a href="/fc/#/guest" target="_blank" class="text-[10px] px-2 py-1 bg-pink-500/20 text-pink-300 rounded hover:bg-pink-500/30 transition">TikTok</a>
                    <a href="/fc/#/guest" target="_blank" class="text-[10px] px-2 py-1 bg-purple-500/20 text-purple-300 rounded hover:bg-purple-500/30 transition">Twitch</a>
                    <a href="/fc/#/guest" target="_blank" class="text-[10px] px-2 py-1 bg-green-500/20 text-green-300 rounded hover:bg-green-500/30 transition">Kick</a>
                  </div>
                </div>
              </div>
            </div>
            <style>
              .favcreators-promo .group:hover + div [style*="z-index: 10000"],
              .favcreators-promo .group:hover ~ div [style*="z-index: 10000"],
              .favcreators-promo .group:hover [style*="z-index: 10000"] {
                opacity: 1 !important;
                visibility: visible !important;
                transform: translateY(0) !important;
                pointer-events: auto !important;
              }
              .favcreators-promo [style*="z-index: 10000"]:hover {
                opacity: 1 !important;
                visibility: visible !important;
                transform: translateY(0) !important;
                pointer-events: auto !important;
              }
            </style>
          </div>
        </div>
      </div>`
    },
    stocks: {
      class: 'stocks-promo',
      html: `<div class="max-w-7xl mx-auto px-4" style="margin-bottom: 1rem; display: block !important; visibility: visible !important;">
        <div class="jsx-1b9a23bd3fa6c640 stocks-promo" style="display: block !important; visibility: visible !important;">
          <div class="jsx-1b9a23bd3fa6c640 promo-banner" style="display: block !important; visibility: visible !important;">
            <div class="jsx-1b9a23bd3fa6c640 flex items-center gap-3 transition-all duration-500 opacity-60 grayscale hover:opacity-100 hover:grayscale-0 group" style="display: flex !important; visibility: visible !important;">
              <div class="jsx-1b9a23bd3fa6c640 w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg animate-pulse-slow">
                <span class="jsx-1b9a23bd3fa6c640 text-xl">📈</span>
              </div>
              <div class="jsx-1b9a23bd3fa6c640 transition-all duration-500 override-overflow max-w-0 opacity-0 overflow-hidden group-hover:max-w-xs group-hover:opacity-100" style="max-width: 0;">
                <div class="jsx-1b9a23bd3fa6c640 flex flex-col whitespace-nowrap">
                  <span class="jsx-1b9a23bd3fa6c640 text-sm font-bold text-white">Stock Ideas</span>
                  <span class="jsx-1b9a23bd3fa6c640 text-[10px] text-[var(--text-2)]">Research, picks & market insights</span>
                </div>
              </div>
              <div class="jsx-1b9a23bd3fa6c640 relative">
                <a class="jsx-1b9a23bd3fa6c640 ml-2 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-xs font-bold text-white transition-all whitespace-nowrap" href="/findstocks/" target="_blank">Open App →</a>
                <div class="jsx-1b9a23bd3fa6c640 absolute top-full right-0 mt-2 w-52 p-4 bg-[var(--surface-1)] border border-white/10 rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 z-50" style="max-width: 300px; line-height: 1.5;">
                  <p class="text-xs text-[var(--text-2)]">Looking for stock ideas? Browse research, daily picks, and portfolio tracking tools.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>`
    }
  };

  function addPromos() {
    const main = document.querySelector('main');
    if (!main) return;
    
    // Find insertion point (after movieshows-promo or before events grid)
    const moviesPromo = main.querySelector('.movieshows-promo');
    const eventsGrid = main.querySelector('#events-grid');
    
    let insertAfter = moviesPromo;
    if (!insertAfter && eventsGrid) {
      // Find the container before events grid
      insertAfter = eventsGrid.closest('.max-w-7xl');
    }
    
    if (!insertAfter) return;
    
    // Add FavCreators if missing
    if (!main.querySelector('.favcreators-promo')) {
      const wrapper = document.createElement('div');
      wrapper.innerHTML = PROMOS.favcreators.html;
      insertAfter.parentNode.insertBefore(wrapper.firstElementChild, insertAfter.nextSibling);
      console.log('[ADD-PROMOS] Added FavCreators');
    }
    
    // Add Stocks if missing  
    if (!main.querySelector('.stocks-promo')) {
      const wrapper = document.createElement('div');
      wrapper.innerHTML = PROMOS.stocks.html;
      const favPromo = main.querySelector('.favcreators-promo');
      if (favPromo) {
        favPromo.parentNode.insertBefore(wrapper.firstElementChild, favPromo.nextSibling);
      } else {
        insertAfter.parentNode.insertBefore(wrapper.firstElementChild, insertAfter.nextSibling);
      }
      console.log('[ADD-PROMOS] Added Stocks');
    }
  }

  // Run multiple times
  function init() {
    addPromos();
    setTimeout(addPromos, 500);
    setTimeout(addPromos, 1000);
    setTimeout(addPromos, 2000);
    setTimeout(addPromos, 3000);
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
  // Also run after window load
  window.addEventListener('load', () => {
    setTimeout(init, 100);
    setTimeout(init, 500);
    setTimeout(init, 1000);
  });
})();
