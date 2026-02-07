/**
 * Mobile Detection & Redirect for VR Hub
 * Automatically redirects mobile users to mobile-friendly version
 */

(function() {
  'use strict';

  const MobileDetect = {
    // Check if device is mobile - CONSERVATIVE detection
    isMobile() {
      const userAgent = navigator.userAgent || navigator.vendor || window.opera;
      
      // Primary check: mobile user agents ONLY
      const mobileRegex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i;
      
      // Must match user agent AND have touch support
      const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
      
      // Desktop browsers sometimes report touch support, so we need BOTH conditions
      return mobileRegex.test(userAgent) && hasTouch;
    },

    // Check if device supports VR
    supportsVR() {
      return 'xr' in navigator || 'getVRDisplays' in navigator;
    },

    // Get device info
    getDeviceInfo() {
      const ua = navigator.userAgent;
      return {
        isIOS: /iPad|iPhone|iPod/.test(ua),
        isAndroid: /Android/.test(ua),
        isSafari: /Safari/.test(ua) && !/Chrome/.test(ua),
        isChrome: /Chrome/.test(ua),
        orientation: window.innerWidth > window.innerHeight ? 'landscape' : 'portrait',
        userAgent: ua
      };
    },

    // Redirect to mobile version
    redirect() {
      const currentPath = window.location.pathname;
      
      // Don't redirect if already on mobile version
      if (currentPath.includes('mobile')) return;
      
      // Don't redirect if user prefers desktop
      if (localStorage.getItem('vr-desktop-mode') === 'true') return;
      
      // Extra safety: Double-check we're actually mobile
      if (!this.isMobile()) {
        console.log('[MobileDetect] Not mobile, skipping redirect');
        return;
      }
      
      // Build mobile URL
      let mobileUrl = '/vr/mobile-index.html';
      
      // Preserve zone if applicable
      if (currentPath.includes('weather')) mobileUrl = '/vr/mobile-weather.html';
      else if (currentPath.includes('movies')) mobileUrl = '/vr/mobile-movies.html';
      else if (currentPath.includes('events')) mobileUrl = '/vr/mobile-events.html';
      else if (currentPath.includes('creators')) mobileUrl = '/vr/mobile-creators.html';
      else if (currentPath.includes('stocks')) mobileUrl = '/vr/mobile-stocks.html';
      
      console.log('[MobileDetect] Redirecting to:', mobileUrl);
      
      // Redirect
      window.location.href = mobileUrl;
    },

    // Show mobile prompt (non-intrusive)
    showPrompt() {
      // Only show on actual mobile devices that weren't auto-redirected
      if (!this.isMobile()) return;
      
      // Check if already dismissed recently
      const lastPrompt = localStorage.getItem('vr-mobile-prompt-dismissed');
      const promptDelay = 24 * 60 * 60 * 1000; // 24 hours
      if (lastPrompt && (Date.now() - parseInt(lastPrompt)) < promptDelay) return;
      
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

    // Initialize - NO AUTO REDIRECT, only manual
    init() {
      // Log detection results
      const info = this.getDeviceInfo();
      console.log('[MobileDetect] User Agent:', info.userAgent);
      console.log('[MobileDetect] Is Mobile:', this.isMobile());
      
      // NEVER auto-redirect - only show prompt if user wants to switch
      if (this.isMobile() && !window.location.pathname.includes('mobile')) {
        // Wait for page to load, then show gentle prompt
        setTimeout(() => {
          this.showPrompt();
        }, 3000);
      }
    }
  };

  // Expose to global scope
  window.MobileDetect = MobileDetect;

  // Initialize after page loads
  if (!window.location.pathname.includes('mobile')) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => MobileDetect.init());
    } else {
      MobileDetect.init();
    }
  }
})();
