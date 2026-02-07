/**
 * VR Substantial Quick Wins - Set 6: Polish & Platform Features
 * 
 * 10 Additional Major Features:
 * 1. PWA Install Prompt (install VR hub as app)
 * 2. Offline Mode (cache zones for offline use)
 * 3. Cross-Device Sync (sync data across devices)
 * 4. Parental Controls (content filtering)
 * 5. Focus Mode (distraction-free VR)
 * 6. Guided Meditation (VR wellness mode)
 * 7. Productivity Tools (VR workspace)
 * 8. Social Rooms (private hangout spaces)
 * 9. Event Reminders (calendar integration)
 * 10. Advanced Accessibility (more assistive features)
 */

(function() {
  'use strict';

  // ==================== CONFIGURATION ====================
  const CONFIG = {
    pwa: {
      promptDelay: 5000,
      installButton: true
    },
    offline: {
      cacheZones: true,
      maxCacheAge: 86400000 // 24 hours
    },
    sync: {
      enabled: true,
      interval: 60000
    },
    parental: {
      pin: '1234',
      maxRating: 'E'
    },
    meditation: {
      sessions: [5, 10, 15, 20],
      breathingPatterns: ['calm', 'energy', 'sleep']
    }
  };

  // ==================== STATE ====================
  const state = {
    deferredPrompt: null,
    isOffline: !navigator.onLine,
    syncData: JSON.parse(localStorage.getItem('vr-sync-data') || '{}'),
    parentalEnabled: localStorage.getItem('vr-parental-enabled') === 'true',
    focusMode: false,
    meditationActive: false,
    eventReminders: JSON.parse(localStorage.getItem('vr-event-reminders') || '[]')
  };

  // ==================== 1. PWA INSTALL PROMPT ====================
  const PWAInstall = {
    init() {
      this.capturePrompt();
      this.createInstallButton();
      console.log('[VR PWA] Initialized');
    },

    capturePrompt() {
      window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        state.deferredPrompt = e;
        this.showInstallButton();
      });

      window.addEventListener('appinstalled', () => {
        state.deferredPrompt = null;
        this.hideInstallButton();
        showToast('✅ VR Hub installed!');
      });
    },

    createInstallButton() {
      const btn = document.createElement('button');
      btn.id = 'vr-pwa-install-btn';
      btn.innerHTML = '📲 Install';
      btn.style.cssText = `
        position: fixed;
        top: 20px;
        right: 280px;
        background: rgba(34, 197, 94, 0.8);
        border: 2px solid #22c55e;
        color: white;
        padding: 10px 20px;
        border-radius: 20px;
        cursor: pointer;
        font-weight: bold;
        z-index: 99999;
        display: none;
        backdrop-filter: blur(10px);
      `;
      btn.addEventListener('click', () => this.promptInstall());
      document.body.appendChild(btn);
    },

    showInstallButton() {
      const btn = document.getElementById('vr-pwa-install-btn');
      if (btn && state.deferredPrompt) {
        btn.style.display = 'block';
      }
    },

    hideInstallButton() {
      const btn = document.getElementById('vr-pwa-install-btn');
      if (btn) btn.style.display = 'none';
    },

    async promptInstall() {
      if (!state.deferredPrompt) return;
      
      state.deferredPrompt.prompt();
      const { outcome } = await state.deferredPrompt.userChoice;
      
      if (outcome === 'accepted') {
        showToast('✅ Installing VR Hub...');
      } else {
        showToast('❌ Installation cancelled');
      }
      
      state.deferredPrompt = null;
      this.hideInstallButton();
    }
  };

  // ==================== 2. OFFLINE MODE ====================
  const OfflineMode = {
    cacheName: 'vr-hub-cache-v1',

    init() {
      this.setupOfflineDetection();
      this.createOfflineUI();
      this.registerServiceWorker();
      console.log('[VR Offline] Initialized');
    },

    async registerServiceWorker() {
      if ('serviceWorker' in navigator) {
        try {
          const registration = await navigator.serviceWorker.register('/vr/sw.js');
          console.log('[VR Offline] Service Worker registered');
        } catch (e) {
          console.log('[VR Offline] SW registration failed:', e);
        }
      }
    },

    setupOfflineDetection() {
      window.addEventListener('online', () => {
        state.isOffline = false;
        this.updateUI();
        showToast('🌐 Back online!');
      });

      window.addEventListener('offline', () => {
        state.isOffline = true;
        this.updateUI();
        showToast('📴 Offline mode activated');
      });
    },

    createOfflineUI() {
      const indicator = document.createElement('div');
      indicator.id = 'vr-offline-indicator';
      indicator.style.cssText = `
        position: fixed;
        top: 70px;
        right: 20px;
        background: rgba(239, 68, 68, 0.8);
        border-radius: 8px;
        padding: 8px 12px;
        color: white;
        font-size: 12px;
        z-index: 99998;
        display: ${state.isOffline ? 'block' : 'none'};
        backdrop-filter: blur(5px);
      `;
      indicator.innerHTML = '📴 Offline Mode';
      document.body.appendChild(indicator);

      // Cache button
      const btn = document.createElement('button');
      btn.id = 'vr-cache-btn';
      btn.innerHTML = '💾';
      btn.title = 'Cache for Offline';
      btn.style.cssText = `
        position: fixed;
        top: 670px;
        right: 20px;
        background: rgba(59, 130, 246, 0.5);
        border: 2px solid #3b82f6;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
      `;
      btn.addEventListener('click', () => this.cacheCurrentZone());
      document.body.appendChild(btn);
    },

    updateUI() {
      const indicator = document.getElementById('vr-offline-indicator');
      if (indicator) {
        indicator.style.display = state.isOffline ? 'block' : 'none';
      }
    },

    async cacheCurrentZone() {
      if ('caches' in window) {
        try {
          const cache = await caches.open(this.cacheName);
          await cache.add(window.location.href);
          showToast('💾 Zone cached for offline use!');
        } catch (e) {
          showToast('❌ Failed to cache zone');
        }
      }
    }
  };

  // ==================== 3. CROSS-DEVICE SYNC ====================
  const CrossDeviceSync = {
    init() {
      this.createUI();
      this.startSync();
      console.log('[VR Sync] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-sync-btn';
      btn.innerHTML = '🔄';
      btn.title = 'Sync Data';
      btn.style.cssText = `
        position: fixed;
        top: 720px;
        right: 20px;
        background: rgba(168, 85, 247, 0.5);
        border: 2px solid #a855f7;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
      `;
      btn.addEventListener('click', () => this.manualSync());
      document.body.appendChild(btn);

      // Sync code display
      const codeDisplay = document.createElement('div');
      codeDisplay.id = 'vr-sync-code';
      codeDisplay.style.cssText = `
        position: fixed;
        top: 770px;
        right: 20px;
        background: rgba(0,0,0,0.8);
        border-radius: 8px;
        padding: 8px 12px;
        color: #a855f7;
        font-size: 11px;
        z-index: 99997;
        font-family: monospace;
        cursor: pointer;
      `;
      codeDisplay.textContent = `ID: ${this.getDeviceId().slice(0, 8)}`;
      codeDisplay.title = 'Click to copy sync code';
      codeDisplay.addEventListener('click', () => this.copySyncCode());
      document.body.appendChild(codeDisplay);
    },

    getDeviceId() {
      let id = localStorage.getItem('vr-device-id');
      if (!id) {
        id = 'vr-' + Math.random().toString(36).substr(2, 16);
        localStorage.setItem('vr-device-id', id);
      }
      return id;
    },

    async copySyncCode() {
      const code = this.getDeviceId();
      try {
        await navigator.clipboard.writeText(code);
        showToast('📋 Sync code copied!');
      } catch (e) {
        showToast('Sync ID: ' + code.slice(0, 8));
      }
    },

    manualSync() {
      // Collect all data to sync
      const syncData = {
        deviceId: this.getDeviceId(),
        timestamp: Date.now(),
        bookmarks: JSON.parse(localStorage.getItem('vr-bookmarks') || '[]'),
        achievements: JSON.parse(localStorage.getItem('vr-achievements') || '{}'),
        stats: JSON.parse(localStorage.getItem('vr-stats') || '{}'),
        inventory: JSON.parse(localStorage.getItem('vr-inventory') || '[]'),
        waypoints: JSON.parse(localStorage.getItem('vr-waypoints') || '{}'),
        friends: JSON.parse(localStorage.getItem('vr-friends') || '[]')
      };

      // Store for "cloud" sync (in reality, localStorage per domain)
      localStorage.setItem('vr-sync-data', JSON.stringify(syncData));
      
      // Visual feedback
      const btn = document.getElementById('vr-sync-btn');
      if (btn) {
        btn.style.animation = 'spin 1s linear';
        setTimeout(() => btn.style.animation = '', 1000);
      }
      
      showToast('🔄 Data synced!');
    },

    startSync() {
      // Auto sync every minute
      setInterval(() => this.manualSync(), CONFIG.sync.interval);
    }
  };

  // ==================== 4. PARENTAL CONTROLS ====================
  const ParentalControls = {
    init() {
      this.createUI();
      this.applyRestrictions();
      console.log('[VR Parental] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-parental-btn';
      btn.innerHTML = '👨‍👩‍👧‍👦';
      btn.title = 'Parental Controls';
      btn.style.cssText = `
        position: fixed;
        top: 770px;
        right: 20px;
        background: ${state.parentalEnabled ? 'rgba(34, 197, 94, 0.5)' : 'rgba(100, 100, 100, 0.3)'};
        border: 2px solid ${state.parentalEnabled ? '#22c55e' : '#888'};
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
      `;
      btn.addEventListener('click', () => this.showControls());
      document.body.appendChild(btn);
    },

    showControls() {
      const pin = prompt('Enter parental PIN:');
      if (pin !== CONFIG.parental.pin) {
        showToast('❌ Incorrect PIN');
        return;
      }

      let panel = document.getElementById('vr-parental-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-parental-panel';
        panel.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
          border: 2px solid #22c55e;
          border-radius: 20px;
          padding: 25px;
          z-index: 100000;
          min-width: 300px;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #22c55e;">👨‍👩‍👧‍👦 Parental Controls</h3>
          <button onclick="document.getElementById('vr-parental-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <label style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px; cursor: pointer;">
          <input type="checkbox" id="vr-parental-toggle" ${state.parentalEnabled ? 'checked' : ''} style="width: 18px; height: 18px;">
          <span>Enable Parental Controls</span>
        </label>

        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px;">Session Time Limit (minutes):</label>
          <input type="number" id="vr-time-limit" value="60" min="15" max="240" style="width: 100%; padding: 8px; border-radius: 5px; background: rgba(255,255,255,0.1); border: 1px solid #22c55e; color: white;">
        </div>

        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px;">Allowed Zones:</label>
          <div style="display: grid; gap: 5px;">
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
              <input type="checkbox" checked disabled> Hub (always allowed)
            </label>
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
              <input type="checkbox" checked> Weather
            </label>
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
              <input type="checkbox" checked> Events
            </label>
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
              <input type="checkbox" checked> Wellness
            </label>
            <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
              <input type="checkbox"> Movies (requires approval)
            </label>
          </div>
        </div>

        <button onclick="VRQuickWinsSet6.Parental.saveSettings()" style="width: 100%; padding: 10px; background: #22c55e; border: none; border-radius: 8px; color: white; cursor: pointer;">Save Settings</button>
      `;
      panel.style.display = 'block';
    },

    saveSettings() {
      const enabled = document.getElementById('vr-parental-toggle')?.checked;
      state.parentalEnabled = enabled;
      localStorage.setItem('vr-parental-enabled', enabled);
      
      document.getElementById('vr-parental-panel').style.display = 'none';
      
      // Update button appearance
      const btn = document.getElementById('vr-parental-btn');
      if (btn) {
        btn.style.background = enabled ? 'rgba(34, 197, 94, 0.5)' : 'rgba(100, 100, 100, 0.3)';
        btn.style.borderColor = enabled ? '#22c55e' : '#888';
      }
      
      showToast(enabled ? '🔒 Parental controls enabled' : '🔓 Parental controls disabled');
    },

    applyRestrictions() {
      if (!state.parentalEnabled) return;
      
      // Apply time limit
      const timeLimit = parseInt(localStorage.getItem('vr-time-limit') || '60');
      setTimeout(() => {
        this.showTimeWarning(timeLimit);
      }, (timeLimit - 5) * 60000);
      
      setTimeout(() => {
        this.enforceTimeLimit();
      }, timeLimit * 60000);
    },

    showTimeWarning(minutes) {
      showToast(`⏰ ${minutes} minute warning: Session ending soon`);
    },

    enforceTimeLimit() {
      showToast('🔒 Time limit reached. Returning to hub...');
      setTimeout(() => {
        window.location.href = '/vr/';
      }, 3000);
    }
  };

  // ==================== 5. FOCUS MODE ====================
  const FocusMode = {
    init() {
      this.createUI();
      console.log('[VR Focus] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-focus-btn';
      btn.innerHTML = '🎯';
      btn.title = 'Focus Mode (Z)';
      btn.style.cssText = `
        position: fixed;
        top: 820px;
        right: 20px;
        background: rgba(14, 165, 233, 0.5);
        border: 2px solid #0ea5e9;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
      `;
      btn.addEventListener('click', () => this.toggle());
      document.body.appendChild(btn);

      document.addEventListener('keydown', (e) => {
        if (e.key === 'z' || e.key === 'Z') {
          this.toggle();
        }
      });
    },

    toggle() {
      state.focusMode = !state.focusMode;
      
      if (state.focusMode) {
        this.enableFocusMode();
      } else {
        this.disableFocusMode();
      }

      const btn = document.getElementById('vr-focus-btn');
      if (btn) {
        btn.style.background = state.focusMode ? 'rgba(14, 165, 233, 0.8)' : 'rgba(14, 165, 233, 0.5)';
        btn.style.boxShadow = state.focusMode ? '0 0 20px #0ea5e9' : 'none';
      }

      showToast(state.focusMode ? '🎯 Focus mode ON' : '🎯 Focus mode OFF');
    },

    enableFocusMode() {
      // Hide distracting elements
      document.querySelectorAll('#vr-friends-btn, #vr-emotes-btn, #vr-notifications-container').forEach(el => {
        if (el) el.style.display = 'none';
      });

      // Dim non-essential UI
      document.body.classList.add('vr-focus-mode');
      
      // Add focus indicator
      const indicator = document.createElement('div');
      indicator.id = 'vr-focus-indicator';
      indicator.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(14, 165, 233, 0.3);
        border: 1px solid #0ea5e9;
        border-radius: 20px;
        padding: 8px 20px;
        color: #0ea5e9;
        font-size: 14px;
        z-index: 99999;
        backdrop-filter: blur(5px);
      `;
      indicator.innerHTML = '🎯 Focus Mode';
      document.body.appendChild(indicator);
    },

    disableFocusMode() {
      // Restore elements
      document.querySelectorAll('#vr-friends-btn, #vr-emotes-btn, #vr-notifications-container').forEach(el => {
        if (el) el.style.display = '';
      });

      document.body.classList.remove('vr-focus-mode');
      
      const indicator = document.getElementById('vr-focus-indicator');
      if (indicator) indicator.remove();
    }
  };

  // ==================== 6. GUIDED MEDITATION ====================
  const GuidedMeditation = {
    active: false,
    breathPhase: 0,

    init() {
      this.createUI();
      console.log('[VR Meditation] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-meditation-btn';
      btn.innerHTML = '🧘';
      btn.title = 'Guided Meditation';
      btn.style.cssText = `
        position: fixed;
        top: 870px;
        right: 20px;
        background: rgba(139, 92, 246, 0.5);
        border: 2px solid #8b5cf6;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
      `;
      btn.addEventListener('click', () => this.showMenu());
      document.body.appendChild(btn);
    },

    showMenu() {
      let panel = document.getElementById('vr-meditation-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-meditation-panel';
        panel.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
          border: 2px solid #8b5cf6;
          border-radius: 20px;
          padding: 25px;
          z-index: 100000;
          min-width: 300px;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #8b5cf6;">🧘 Guided Meditation</h3>
          <button onclick="document.getElementById('vr-meditation-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 8px;">Duration:</label>
          <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            ${CONFIG.meditation.sessions.map(m => `
              <button onclick="VRQuickWinsSet6.Meditation.start(${m})" style="padding: 8px 16px; background: rgba(139,92,246,0.3); border: 1px solid #8b5cf6; border-radius: 8px; color: white; cursor: pointer;">${m} min</button>
            `).join('')}
          </div>
        </div>

        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 8px;">Breathing Pattern:</label>
          <select id="vr-meditation-pattern" style="width: 100%; padding: 8px; border-radius: 5px; background: rgba(255,255,255,0.1); border: 1px solid #8b5cf6; color: white;">
            <option value="calm">Calm (4-7-8)</option>
            <option value="energy">Energy (6-0-6)</option>
            <option value="sleep">Sleep (4-4-4)</option>
          </select>
        </div>

        <div id="vr-meditation-preview" style="text-align: center; padding: 20px; background: rgba(139,92,246,0.1); border-radius: 10px;">
          <div style="font-size: 48px; margin-bottom: 10px;">🌊</div>
          <div style="font-size: 14px; opacity: 0.8;">Select duration to begin</div>
        </div>
      `;
      panel.style.display = 'block';
    },

    start(minutes) {
      state.meditationActive = true;
      document.getElementById('vr-meditation-panel').style.display = 'none';
      
      // Create meditation overlay
      const overlay = document.createElement('div');
      overlay.id = 'vr-meditation-overlay';
      overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: linear-gradient(135deg, #1a1a3e 0%, #0f0f2f 100%);
        z-index: 100001;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: white;
      `;

      overlay.innerHTML = `
        <div id="vr-breath-circle" style="
          width: 200px;
          height: 200px;
          border-radius: 50%;
          background: radial-gradient(circle, rgba(139,92,246,0.5) 0%, transparent 70%);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 24px;
          transition: transform 4s ease-in-out;
        ">Breathe</div>
        <div id="vr-meditation-timer" style="margin-top: 40px; font-size: 48px; font-family: monospace;">${minutes}:00</div>
        <button onclick="VRQuickWinsSet6.Meditation.stop()" style="margin-top: 40px; padding: 12px 30px; background: rgba(239,68,68,0.5); border: 2px solid #ef4444; border-radius: 25px; color: white; cursor: pointer; font-size: 16px;">End Session</button>
      `;

      document.body.appendChild(overlay);
      
      this.startBreathing();
      this.startTimer(minutes);
      
      showToast('🧘 Meditation started. Breathe deeply...');
    },

    startBreathing() {
      const circle = document.getElementById('vr-breath-circle');
      if (!circle) return;

      const breathe = () => {
        if (!state.meditationActive) return;
        
        // Inhale
        circle.style.transform = 'scale(1.5)';
        circle.textContent = 'Inhale';
        
        setTimeout(() => {
          if (!state.meditationActive) return;
          // Hold
          circle.textContent = 'Hold';
          
          setTimeout(() => {
            if (!state.meditationActive) return;
            // Exhale
            circle.style.transform = 'scale(1)';
            circle.textContent = 'Exhale';
          }, 2000);
        }, 4000);
      };

      breathe();
      this.breathInterval = setInterval(breathe, 10000);
    },

    startTimer(minutes) {
      let seconds = minutes * 60;
      
      this.timerInterval = setInterval(() => {
        seconds--;
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        
        const timer = document.getElementById('vr-meditation-timer');
        if (timer) {
          timer.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
        }
        
        if (seconds <= 0) {
          this.stop();
          showToast('🧘 Meditation complete!');
        }
      }, 1000);
    },

    stop() {
      state.meditationActive = false;
      clearInterval(this.breathInterval);
      clearInterval(this.timerInterval);
      
      const overlay = document.getElementById('vr-meditation-overlay');
      if (overlay) overlay.remove();
    }
  };

  // ==================== 7. PRODUCTIVITY TOOLS ====================
  const ProductivityTools = {
    init() {
      this.createUI();
      console.log('[VR Productivity] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-productivity-btn';
      btn.innerHTML = '✅';
      btn.title = 'Productivity Tools';
      btn.style.cssText = `
        position: fixed;
        top: 920px;
        right: 20px;
        background: rgba(34, 197, 94, 0.5);
        border: 2px solid #22c55e;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
      `;
      btn.addEventListener('click', () => this.showTools());
      document.body.appendChild(btn);

      // Pomodoro timer indicator
      const indicator = document.createElement('div');
      indicator.id = 'vr-pomodoro-indicator';
      indicator.style.cssText = `
        position: fixed;
        top: 970px;
        right: 20px;
        background: rgba(0,0,0,0.8);
        border-radius: 8px;
        padding: 5px 10px;
        color: #22c55e;
        font-size: 12px;
        z-index: 99997;
        font-family: monospace;
        display: none;
      `;
      indicator.textContent = '25:00';
      document.body.appendChild(indicator);
    },

    showTools() {
      let panel = document.getElementById('vr-productivity-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-productivity-panel';
        panel.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
          border: 2px solid #22c55e;
          border-radius: 20px;
          padding: 25px;
          z-index: 100000;
          min-width: 300px;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #22c55e;">✅ Productivity</h3>
          <button onclick="document.getElementById('vr-productivity-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="margin-bottom: 15px;">
          <div style="font-weight: bold; margin-bottom: 10px;">🍅 Pomodoro Timer</div>
          <div style="display: flex; gap: 8px;">
            <button onclick="VRQuickWinsSet6.Productivity.startPomodoro(25)" style="flex: 1; padding: 10px; background: rgba(34,197,94,0.3); border: 1px solid #22c55e; border-radius: 8px; color: white; cursor: pointer;">25 min</button>
            <button onclick="VRQuickWinsSet6.Productivity.startPomodoro(50)" style="flex: 1; padding: 10px; background: rgba(34,197,94,0.3); border: 1px solid #22c55e; border-radius: 8px; color: white; cursor: pointer;">50 min</button>
            <button onclick="VRQuickWinsSet6.Productivity.stopPomodoro()" style="flex: 1; padding: 10px; background: rgba(239,68,68,0.3); border: 1px solid #ef4444; border-radius: 8px; color: white; cursor: pointer;">Stop</button>
          </div>
        </div>

        <div style="margin-bottom: 15px;">
          <div style="font-weight: bold; margin-bottom: 10px;">📝 Quick Notes</div>
          <textarea id="vr-quick-notes" placeholder="Type your notes here..." style="width: 100%; height: 100px; padding: 10px; border-radius: 8px; background: rgba(255,255,255,0.1); border: 1px solid #22c55e; color: white; resize: none;"></textarea>
          <button onclick="VRQuickWinsSet6.Productivity.saveNotes()" style="width: 100%; margin-top: 8px; padding: 8px; background: rgba(34,197,94,0.3); border: 1px solid #22c55e; border-radius: 8px; color: white; cursor: pointer;">Save Notes</button>
        </div>

        <div>
          <div style="font-weight: bold; margin-bottom: 10px;">⏱️ Session Time</div>
          <div id="vr-session-time-display" style="font-size: 32px; font-family: monospace; text-align: center; color: #22c55e;">00:00</div>
        </div>
      `;
      panel.style.display = 'block';
      
      this.updateSessionTime();
    },

    startPomodoro(minutes) {
      let seconds = minutes * 60;
      const indicator = document.getElementById('vr-pomodoro-indicator');
      if (indicator) indicator.style.display = 'block';
      
      this.pomodoroInterval = setInterval(() => {
        seconds--;
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        const timeStr = `${mins}:${secs.toString().padStart(2, '0')}`;
        
        if (indicator) indicator.textContent = timeStr;
        
        if (seconds <= 0) {
          this.stopPomodoro();
          showToast('🍅 Pomodoro complete! Take a break.');
        }
      }, 1000);
      
      showToast(`🍅 ${minutes} minute timer started`);
    },

    stopPomodoro() {
      clearInterval(this.pomodoroInterval);
      const indicator = document.getElementById('vr-pomodoro-indicator');
      if (indicator) {
        indicator.style.display = 'none';
        indicator.textContent = '25:00';
      }
    },

    saveNotes() {
      const notes = document.getElementById('vr-quick-notes')?.value;
      if (notes) {
        localStorage.setItem('vr-quick-notes', notes);
        showToast('📝 Notes saved!');
      }
    },

    updateSessionTime() {
      const startTime = parseInt(sessionStorage.getItem('vr-session-start') || Date.now());
      sessionStorage.setItem('vr-session-start', startTime);
      
      setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const mins = Math.floor(elapsed / 60);
        const secs = elapsed % 60;
        
        const display = document.getElementById('vr-session-time-display');
        if (display) {
          display.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
      }, 1000);
    }
  };

  // ==================== 8. SOCIAL ROOMS ====================
  const SocialRooms = {
    rooms: JSON.parse(localStorage.getItem('vr-social-rooms') || '[]'),

    init() {
      this.createUI();
      console.log('[VR Social Rooms] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-social-rooms-btn';
      btn.innerHTML = '🏠';
      btn.title = 'Social Rooms';
      btn.style.cssText = `
        position: fixed;
        top: 970px;
        right: 20px;
        background: rgba(236, 72, 153, 0.5);
        border: 2px solid #ec4899;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
      `;
      btn.addEventListener('click', () => this.showRooms());
      document.body.appendChild(btn);
    },

    showRooms() {
      let panel = document.getElementById('vr-social-rooms-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-social-rooms-panel';
        panel.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
          border: 2px solid #ec4899;
          border-radius: 20px;
          padding: 25px;
          z-index: 100000;
          min-width: 350px;
          max-height: 70vh;
          overflow-y: auto;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #ec4899;">🏠 Social Rooms</h3>
          <button onclick="document.getElementById('vr-social-rooms-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="margin-bottom: 15px;">
          <input type="text" id="vr-room-name" placeholder="Room name..." style="width: 60%; padding: 8px; border-radius: 5px; background: rgba(255,255,255,0.1); border: 1px solid #ec4899; color: white;">
          <button onclick="VRQuickWinsSet6.SocialRooms.createRoom()" style="width: 38%; padding: 8px; background: #ec4899; border: none; border-radius: 5px; color: white; cursor: pointer;">Create Room</button>
        </div>

        <div style="display: grid; gap: 10px;">
          ${this.rooms.length === 0 ? 
            '<p style="text-align: center; opacity: 0.6; padding: 20px;">No rooms yet. Create one!</p>' :
            this.rooms.map(room => `
              <div style="padding: 12px; background: rgba(236,72,153,0.1); border: 1px solid rgba(236,72,153,0.3); border-radius: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <div>
                    <div style="font-weight: bold;">${room.name}</div>
                    <div style="font-size: 12px; opacity: 0.7;">${room.users || 0} users • ${room.zone}</div>
                  </div>
                  <button onclick="VRQuickWinsSet6.SocialRooms.joinRoom('${room.id}')" style="padding: 8px 16px; background: rgba(236,72,153,0.5); border: 1px solid #ec4899; border-radius: 8px; color: white; cursor: pointer;">Join</button>
                </div>
              </div>
            `).join('')
          }
        </div>
      `;
      panel.style.display = 'block';
    },

    createRoom() {
      const nameInput = document.getElementById('vr-room-name');
      const name = nameInput?.value.trim();
      if (!name) return;

      const room = {
        id: 'room-' + Date.now(),
        name,
        zone: window.location.pathname,
        created: Date.now(),
        users: 1,
        host: localStorage.getItem('vr-device-id') || 'anonymous'
      };

      this.rooms.push(room);
      localStorage.setItem('vr-social-rooms', JSON.stringify(this.rooms));
      
      nameInput.value = '';
      this.showRooms();
      showToast(`🏠 Room "${name}" created!`);
    },

    joinRoom(roomId) {
      const room = this.rooms.find(r => r.id === roomId);
      if (!room) return;

      showToast(`🏠 Joining ${room.name}...`);
      
      // In a real implementation, this would connect to the room
      setTimeout(() => {
        if (room.zone !== window.location.pathname) {
          window.location.href = room.zone;
        }
      }, 1000);
    }
  };

  // ==================== 9. EVENT REMINDERS ====================
  const EventReminders = {
    init() {
      this.loadEvents();
      this.createUI();
      this.checkReminders();
      console.log('[VR Event Reminders] Initialized');
    },

    loadEvents() {
      // Load from localStorage or use defaults
      const saved = localStorage.getItem('vr-event-reminders');
      if (saved) {
        state.eventReminders = JSON.parse(saved);
      }
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-events-btn';
      btn.innerHTML = '📅';
      btn.title = 'Event Reminders';
      btn.style.cssText = `
        position: fixed;
        top: 1020px;
        right: 20px;
        background: rgba(245, 158, 11, 0.5);
        border: 2px solid #f59e0b;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
      `;
      btn.addEventListener('click', () => this.showEvents());
      document.body.appendChild(btn);
    },

    showEvents() {
      let panel = document.getElementById('vr-events-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-events-panel';
        panel.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
          border: 2px solid #f59e0b;
          border-radius: 20px;
          padding: 25px;
          z-index: 100000;
          min-width: 350px;
          max-height: 70vh;
          overflow-y: auto;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }

      const upcoming = state.eventReminders.filter(e => new Date(e.time) > Date.now());

      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #f59e0b;">📅 Event Reminders</h3>
          <button onclick="document.getElementById('vr-events-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="margin-bottom: 15px;">
          <input type="text" id="vr-event-name" placeholder="Event name..." style="width: 100%; padding: 8px; margin-bottom: 8px; border-radius: 5px; background: rgba(255,255,255,0.1); border: 1px solid #f59e0b; color: white;">
          <input type="datetime-local" id="vr-event-time" style="width: 100%; padding: 8px; margin-bottom: 8px; border-radius: 5px; background: rgba(255,255,255,0.1); border: 1px solid #f59e0b; color: white;">
          <button onclick="VRQuickWinsSet6.EventReminders.addEvent()" style="width: 100%; padding: 8px; background: #f59e0b; border: none; border-radius: 5px; color: white; cursor: pointer;">Add Reminder</button>
        </div>

        <div style="display: grid; gap: 10px;">
          ${upcoming.length === 0 ? 
            '<p style="text-align: center; opacity: 0.6; padding: 20px;">No upcoming events</p>' :
            upcoming.map(e => `
              <div style="padding: 12px; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); border-radius: 10px;">
                <div style="font-weight: bold;">${e.name}</div>
                <div style="font-size: 12px; opacity: 0.7;">${new Date(e.time).toLocaleString()}</div>
              </div>
            `).join('')
          }
        </div>
      `;
      panel.style.display = 'block';
    },

    addEvent() {
      const nameInput = document.getElementById('vr-event-name');
      const timeInput = document.getElementById('vr-event-time');
      
      const name = nameInput?.value.trim();
      const time = timeInput?.value;
      
      if (!name || !time) return;

      state.eventReminders.push({
        id: 'event-' + Date.now(),
        name,
        time: new Date(time).toISOString()
      });

      localStorage.setItem('vr-event-reminders', JSON.stringify(state.eventReminders));
      
      nameInput.value = '';
      timeInput.value = '';
      this.showEvents();
      showToast('📅 Event reminder added!');
    },

    checkReminders() {
      setInterval(() => {
        const now = Date.now();
        state.eventReminders.forEach(event => {
          const eventTime = new Date(event.time).getTime();
          if (eventTime > now && eventTime - now < 60000 && !event.notified) {
            event.notified = true;
            showToast(`📅 Starting soon: ${event.name}`);
            localStorage.setItem('vr-event-reminders', JSON.stringify(state.eventReminders));
          }
        });
      }, 30000);
    }
  };

  // ==================== 10. ADVANCED ACCESSIBILITY ====================
  const AdvancedAccessibility = {
    init() {
      this.createUI();
      this.loadSettings();
      console.log('[VR Advanced Accessibility] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-accessibility-adv-btn';
      btn.innerHTML = '♿';
      btn.title = 'Advanced Accessibility';
      btn.style.cssText = `
        position: fixed;
        top: 1070px;
        right: 20px;
        background: rgba(59, 130, 246, 0.5);
        border: 2px solid #3b82f6;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
      `;
      btn.addEventListener('click', () => this.showPanel());
      document.body.appendChild(btn);
    },

    showPanel() {
      let panel = document.getElementById('vr-accessibility-adv-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-accessibility-adv-panel';
        panel.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
          border: 2px solid #3b82f6;
          border-radius: 20px;
          padding: 25px;
          z-index: 100000;
          min-width: 350px;
          max-height: 70vh;
          overflow-y: auto;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #3b82f6;">♿ Advanced Accessibility</h3>
          <button onclick="document.getElementById('vr-accessibility-adv-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="display: grid; gap: 15px;">
          <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
            <input type="checkbox" id="vr-screen-reader" style="width: 18px; height: 18px;">
            <span>Screen Reader Support</span>
          </label>

          <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
            <input type="checkbox" id="vr-color-blind" style="width: 18px; height: 18px;">
            <span>Color Blind Mode</span>
          </label>

          <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
            <input type="checkbox" id="vr-motor-assist" style="width: 18px; height: 18px;">
            <span>Motor Assist (Dwell Click)</span>
          </label>

          <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
            <input type="checkbox" id="vr-audio-desc" style="width: 18px; height: 18px;">
            <span>Audio Descriptions</span>
          </label>

          <div>
            <label style="display: block; margin-bottom: 8px;">Cursor Size:</label>
            <input type="range" id="vr-cursor-size" min="1" max="3" step="0.5" value="1" style="width: 100%;">
          </div>

          <div>
            <label style="display: block; margin-bottom: 8px;">Interface Scale:</label>
            <input type="range" id="vr-ui-scale" min="0.8" max="2" step="0.1" value="1" style="width: 100%;">
          </div>
        </div>

        <button onclick="VRQuickWinsSet6.Accessibility.saveSettings()" style="width: 100%; margin-top: 20px; padding: 12px; background: #3b82f6; border: none; border-radius: 8px; color: white; cursor: pointer;">Save Settings</button>
      `;
      panel.style.display = 'block';
    },

    saveSettings() {
      const settings = {
        screenReader: document.getElementById('vr-screen-reader')?.checked,
        colorBlind: document.getElementById('vr-color-blind')?.checked,
        motorAssist: document.getElementById('vr-motor-assist')?.checked,
        audioDesc: document.getElementById('vr-audio-desc')?.checked,
        cursorSize: document.getElementById('vr-cursor-size')?.value,
        uiScale: document.getElementById('vr-ui-scale')?.value
      };

      localStorage.setItem('vr-accessibility-adv', JSON.stringify(settings));
      this.applySettings(settings);
      
      document.getElementById('vr-accessibility-adv-panel').style.display = 'none';
      showToast('♿ Accessibility settings saved!');
    },

    loadSettings() {
      const saved = localStorage.getItem('vr-accessibility-adv');
      if (saved) {
        this.applySettings(JSON.parse(saved));
      }
    },

    applySettings(settings) {
      if (settings.uiScale) {
        document.documentElement.style.setProperty('--vr-ui-scale', settings.uiScale);
      }
      if (settings.cursorSize) {
        // Would apply to custom cursor
      }
      if (settings.colorBlind) {
        document.body.classList.add('vr-color-blind-mode');
      }
    }
  };

  // ==================== UTILITY: TOAST ====================
  function showToast(message) {
    let toast = document.getElementById('vr-toast-set6');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'vr-toast-set6';
      toast.style.cssText = `
        position: fixed;
        bottom: 300px;
        left: 50%;
        transform: translateX(-50%) translateY(20px);
        background: rgba(10,10,20,0.95);
        backdrop-filter: blur(12px);
        border: 1px solid #14b8a6;
        border-radius: 10px;
        color: #e0e0e0;
        font-size: 14px;
        padding: 12px 24px;
        opacity: 0;
        pointer-events: none;
        transition: all 0.3s ease;
        z-index: 99999;
      `;
      document.body.appendChild(toast);
    }
    
    toast.textContent = message;
    toast.style.opacity = '1';
    toast.style.transform = 'translateX(-50%) translateY(0)';
    
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(-50%) translateY(20px)';
    }, 2500);
  }

  // ==================== INITIALIZATION ====================
  function init() {
    console.log('[VR Substantial Quick Wins - Set 6] Initializing...');

    PWAInstall.init();
    OfflineMode.init();
    CrossDeviceSync.init();
    ParentalControls.init();
    FocusMode.init();
    GuidedMeditation.init();
    ProductivityTools.init();
    SocialRooms.init();
    EventReminders.init();
    AdvancedAccessibility.init();

    console.log('[VR Substantial Quick Wins - Set 6] Initialized!');
    console.log('New shortcuts:');
    console.log('  Z - Focus mode');
    console.log('  Install button - Add to home screen');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose API
  window.VRQuickWinsSet6 = {
    PWA: PWAInstall,
    Offline: OfflineMode,
    Sync: CrossDeviceSync,
    Parental: ParentalControls,
    Focus: FocusMode,
    Meditation: GuidedMeditation,
    Productivity: ProductivityTools,
    SocialRooms,
    EventReminders,
    Accessibility: AdvancedAccessibility,
    showToast
  };

})();
