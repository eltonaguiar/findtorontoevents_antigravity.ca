/**
 * Mobile Detection & Redirect for VR Hub
 * Automatically redirects mobile users to mobile-friendly version
 */

(function() {
  'use strict';

  const MobileDetect = {
    // Check if device is mobile
    isMobile() {
      const userAgent = navigator.userAgent || navigator.vendor || window.opera;
      
      // Check for mobile devices
      const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile|CriOS/i;
      
      // Check for touch support
      const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      
      // Check screen size
      const isSmallScreen = window.innerWidth < 1024;
      
      return mobileRegex.test(userAgent) || (hasTouch && isSmallScreen);
    },

    // Check if device supports VR
    supportsVR() {
      return 'xr' in navigator || 'getVRDisplays' in navigator;
    },

    // Check if in standalone mode (PWA)
    isStandalone() {
      return window.matchMedia('(display-mode: standalone)').matches || 
             window.navigator.standalone === true;
    },

    // Get device info
    getDeviceInfo() {
      const ua = navigator.userAgent;
      return {
        isIOS: /iPad|iPhone|iPod/.test(ua),
        isAndroid: /Android/.test(ua),
        isSafari: /Safari/.test(ua) && !/Chrome/.test(ua),
        isChrome: /Chrome/.test(ua),
        orientation: window.innerWidth > window.innerHeight ? 'landscape' : 'portrait'
      };
    },

    // Redirect to mobile version
    redirect() {
      const currentPath = window.location.pathname;
      
      // Don't redirect if already on mobile version
      if (currentPath.includes('mobile')) return;
      
      // Don't redirect if user prefers desktop
      if (localStorage.getItem('vr-desktop-mode') === 'true') return;
      
      // Build mobile URL
      let mobileUrl = '/vr/mobile-index.html';
      
      // Preserve zone if applicable
      if (currentPath.includes('weather')) mobileUrl = '/vr/mobile-weather.html';
      else if (currentPath.includes('movies')) mobileUrl = '/vr/mobile-movies.html';
      else if (currentPath.includes('events')) mobileUrl = '/vr/mobile-events.html';
      else if (currentPath.includes('creators')) mobileUrl = '/vr/mobile-creators.html';
      else if (currentPath.includes('stocks')) mobileUrl = '/vr/mobile-stocks.html';
      
      // Redirect
      window.location.href = mobileUrl;
    },

    // Show mobile prompt
    showPrompt() {
      const prompt = document.createElement('div');
      prompt.id = 'mobile-prompt';
      prompt.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0,212,255,0.9);
        color: #0a0a1f;
        padding: 15px 25px;
        border-radius: 25px;
        font-size: 14px;
        font-weight: 600;
        z-index: 100000;
        box-shadow: 0 4px 20px rgba(0,212,255,0.4);
        display: flex;
        align-items: center;
        gap: 15px;
        max-width: 90vw;
      `;
      
      prompt.innerHTML = `
        <span>📱 Mobile version available!</span>
        <button onclick="MobileDetect.redirect()" style="
          background: #0a0a1f;
          color: #00d4ff;
          border: none;
          padding: 8px 16px;
          border-radius: 15px;
          cursor: pointer;
          font-weight: bold;
        ">Switch</button>
        <button onclick="MobileDetect.dismissPrompt()" style="
          background: transparent;
          border: none;
          color: #0a0a1f;
          font-size: 18px;
          cursor: pointer;
        ">×</button>
      `;
      
      document.body.appendChild(prompt);
    },

    // Dismiss prompt
    dismissPrompt() {
      const prompt = document.getElementById('mobile-prompt');
      if (prompt) prompt.remove();
      localStorage.setItem('vr-mobile-prompt-dismissed', Date.now().toString());
    },

    // Initialize
    init() {
      // If vr-mobile.js is loaded, the VR pages are already mobile-enhanced — just show prompt
      if (this.isMobile()) {
        const lastPrompt = localStorage.getItem('vr-mobile-prompt-dismissed');
        const promptDelay = 24 * 60 * 60 * 1000; // 24 hours

        if (!lastPrompt || (Date.now() - parseInt(lastPrompt)) > promptDelay) {
          // Show choice prompt instead of hard redirect
          this.showPrompt();
        }
      } else {
        if (window.innerWidth < 768) {
          this.showPrompt();
        }
      }

      window.addEventListener('resize', () => {
        if (window.innerWidth < 768 && !document.getElementById('mobile-prompt')) {
          this.showPrompt();
        }
      });
    }
  };

  // Expose to global scope
  window.MobileDetect = MobileDetect;

  // Auto-init if not already on mobile version
  if (!window.location.pathname.includes('mobile')) {
    document.addEventListener('DOMContentLoaded', () => {
      MobileDetect.init();
    });
  }
})();
