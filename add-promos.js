// Add missing promo banners after React hydration
// NOTE: This script is DISABLED when static-promo-container exists
(function() {
  'use strict';
  
  function addPromos() {
    // SKIP if static promo container exists (managed by index.html)
    if (document.querySelector('#static-promo-container')) {
      console.log('[ADD-PROMOS] Skipping - static promo container exists');
      return;
    }
    
    console.log('[ADD-PROMOS] Static container not found, skipping');
  }

  // Run multiple times
  function init() {
    addPromos();
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
  });
})();
