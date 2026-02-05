// Google AdSense Integration
(function() {
  'use strict';
  
  // AdSense Publisher ID
  const ADSENSE_CLIENT = 'ca-pub-7893721225790912';
  
  // Load AdSense script
  function loadAdSense() {
    if (window.adsbygoogle) return; // Already loaded
    
    try {
      var script = document.createElement('script');
      script.async = true;
      script.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + ADSENSE_CLIENT;
      script.crossOrigin = 'anonymous';
      script.onerror = function() {
        console.warn('AdSense script failed to load');
      };
      document.head.appendChild(script);
    } catch (e) {
      console.warn('AdSense initialization failed:', e);
    }
  }
  
  // Initialize ads
  function initAds() {
    if (window.adsbygoogle) {
      // Push all ad slots
      var adElements = document.querySelectorAll('ins.adsbygoogle');
      adElements.forEach(function(el) {
        if (!el.getAttribute('data-adsbygoogle-status')) {
          (window.adsbygoogle = window.adsbygoogle || []).push({});
        }
      });
    }
  }
  
  // Load when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      loadAdSense();
      setTimeout(initAds, 1000);
    });
  } else {
    loadAdSense();
    setTimeout(initAds, 1000);
  }
  
  // Retry after window load
  window.addEventListener('load', function() {
    setTimeout(initAds, 2000);
  });
})();
