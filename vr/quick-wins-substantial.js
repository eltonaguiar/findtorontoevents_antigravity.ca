/**
 * VR Substantial Quick Wins - Cross-Zone Enhancements
 * 
 * 10 Major Features:
 * 1. Performance Monitor (FPS, memory, frame time)
 * 2. Auto-Save Position (localStorage persistence)
 * 3. Theme Switcher (dark/light/high contrast)
 * 4. Voice Commands (speech recognition navigation)
 * 5. Screenshot Tool (capture VR view)
 * 6. Session Timer (track VR time)
 * 7. Emergency Exit (motion sickness relief)
 * 8. Accessibility Menu (font size, contrast, motion)
 * 9. Zone Bookmarks (save favorite positions)
 * 10. Quick Settings Panel (volume, brightness, etc.)
 */

(function() {
  'use strict';

  // ==================== CONFIGURATION ====================
  const CONFIG = {
    autoSaveInterval: 30000, // Save position every 30s
    maxBookmarks: 10,
    speechLang: 'en-US',
    themes: ['dark', 'light', 'high-contrast'],
    defaultTheme: 'dark'
  };

  // ==================== STATE ====================
  const state = {
    currentTheme: localStorage.getItem('vr-theme') || CONFIG.defaultTheme,
    sessionStartTime: Date.now(),
    bookmarks: JSON.parse(localStorage.getItem('vr-bookmarks') || '[]'),
    autoSaveEnabled: localStorage.getItem('vr-autosave') !== 'false',
    speechEnabled: false,
    recognition: null,
    performanceVisible: false,
    accessibilitySettings: JSON.parse(localStorage.getItem('vr-accessibility') || '{}'),
    lastSavedPosition: null
  };

  // ==================== 1. PERFORMANCE MONITOR ====================
  const PerformanceMonitor = {
    frameCount: 0,
    lastTime: performance.now(),
    fps: 0,
    frameTime: 0,
    container: null,

    init() {
      this.container = this.createUI();
      this.loop();
      
      // Toggle with Ctrl+F
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'f') {
          e.preventDefault();
          this.toggle();
        }
      });
    },

    createUI() {
      const div = document.createElement('div');
      div.id = 'vr-performance-monitor';
      div.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(0,0,0,0.85);
        border: 1px solid #00d4ff;
        border-radius: 12px;
        padding: 15px;
        color: #00d4ff;
        font-family: 'Courier New', monospace;
        font-size: 13px;
        z-index: 100001;
        display: none;
        backdrop-filter: blur(10px);
        min-width: 150px;
      `;
      div.innerHTML = `
        <div style="font-weight: bold; margin-bottom: 8px; border-bottom: 1px solid rgba(0,212,255,0.3); padding-bottom: 5px;">
          📊 Performance
        </div>
        <div>FPS: <span id="vr-fps">--</span></div>
        <div>MS: <span id="vr-ms">--</span></div>
        <div>Mem: <span id="vr-mem">--</span></div>
        <div style="margin-top: 8px; font-size: 10px; opacity: 0.7;">
          Press Ctrl+F to hide
        </div>
      `;
      document.body.appendChild(div);
      return div;
    },

    loop() {
      this.frameCount++;
      const now = performance.now();
      const delta = now - this.lastTime;

      if (delta >= 1000) {
        this.fps = Math.round((this.frameCount * 1000) / delta);
        this.frameTime = Math.round(delta / this.frameCount);
        this.updateDisplay();
        this.frameCount = 0;
        this.lastTime = now;
      }

      requestAnimationFrame(() => this.loop());
    },

    updateDisplay() {
      const fpsEl = document.getElementById('vr-fps');
      const msEl = document.getElementById('vr-ms');
      const memEl = document.getElementById('vr-mem');

      if (fpsEl) fpsEl.textContent = this.fps;
      if (msEl) msEl.textContent = this.frameTime;
      
      // Memory info (if available)
      if (memEl && performance.memory) {
        const used = Math.round(performance.memory.usedJSHeapSize / 1048576);
        memEl.textContent = used + 'MB';
      } else if (memEl) {
        memEl.textContent = 'N/A';
      }
    },

    toggle() {
      state.performanceVisible = !state.performanceVisible;
      if (this.container) {
        this.container.style.display = state.performanceVisible ? 'block' : 'none';
      }
    }
  };

  // ==================== 2. AUTO-SAVE POSITION ====================
  const AutoSavePosition = {
    intervalId: null,

    init() {
      if (!state.autoSaveEnabled) return;

      // Restore saved position on load
      this.restorePosition();

      // Start auto-save interval
      this.intervalId = setInterval(() => this.savePosition(), CONFIG.autoSaveInterval);

      // Also save on page unload
      window.addEventListener('beforeunload', () => this.savePosition());
    },

    savePosition() {
      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (!rig) return;

      const position = rig.getAttribute('position');
      const rotation = rig.getAttribute('rotation');
      const zone = window.location.pathname;

      const saveData = {
        zone,
        position: { x: position.x, y: position.y, z: position.z },
        rotation: { x: rotation.x, y: rotation.y, z: rotation.z },
        timestamp: Date.now()
      };

      localStorage.setItem('vr-saved-position', JSON.stringify(saveData));
      state.lastSavedPosition = saveData;
      
      console.log('[VR Auto-Save] Position saved:', saveData.position);
    },

    restorePosition() {
      const saved = localStorage.getItem('vr-saved-position');
      if (!saved) return;

      try {
        const data = JSON.parse(saved);
        const currentZone = window.location.pathname;

        // Only restore if same zone and within last 24 hours
        if (data.zone === currentZone && (Date.now() - data.timestamp) < 86400000) {
          setTimeout(() => {
            const rig = document.getElementById('rig') || document.getElementById('camera-rig');
            if (rig && data.position) {
              rig.setAttribute('position', data.position);
              if (data.rotation) {
                rig.setAttribute('rotation', data.rotation);
              }
              console.log('[VR Auto-Save] Position restored:', data.position);
              showToast('📍 Position restored');
            }
          }, 1000);
        }
      } catch (e) {
        console.error('[VR Auto-Save] Failed to restore:', e);
      }
    },

    clear() {
      localStorage.removeItem('vr-saved-position');
      showToast('📍 Saved position cleared');
    }
  };

  // ==================== 3. THEME SWITCHER ====================
  const ThemeSwitcher = {
    init() {
      this.applyTheme(state.currentTheme);
    },

    applyTheme(theme) {
      state.currentTheme = theme;
      localStorage.setItem('vr-theme', theme);

      // Remove existing theme classes
      document.body.classList.remove('vr-theme-dark', 'vr-theme-light', 'vr-theme-high-contrast');
      document.body.classList.add(`vr-theme-${theme}`);

      // Apply CSS variables based on theme
      const root = document.documentElement;
      
      switch(theme) {
        case 'light':
          root.style.setProperty('--vr-bg', '#f0f0f0');
          root.style.setProperty('--vr-text', '#1a1a1a');
          root.style.setProperty('--vr-accent', '#0066cc');
          root.style.setProperty('--vr-overlay-bg', 'rgba(255,255,255,0.95)');
          break;
        case 'high-contrast':
          root.style.setProperty('--vr-bg', '#000000');
          root.style.setProperty('--vr-text', '#ffffff');
          root.style.setProperty('--vr-accent', '#ffff00');
          root.style.setProperty('--vr-overlay-bg', 'rgba(0,0,0,0.95)');
          break;
        default: // dark
          root.style.setProperty('--vr-bg', '#0a0a0a');
          root.style.setProperty('--vr-text', '#e0e0e0');
          root.style.setProperty('--vr-accent', '#00d4ff');
          root.style.setProperty('--vr-overlay-bg', 'rgba(10,10,20,0.95)');
      }

      console.log('[VR Theme] Applied:', theme);
    },

    cycle() {
      const themes = CONFIG.themes;
      const currentIndex = themes.indexOf(state.currentTheme);
      const nextTheme = themes[(currentIndex + 1) % themes.length];
      this.applyTheme(nextTheme);
      showToast(`🎨 Theme: ${nextTheme}`);
    }
  };

  // ==================== 4. VOICE COMMANDS ====================
  const VoiceCommands = {
    init() {
      if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.log('[VR Voice] Speech recognition not supported');
        return;
      }

      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      state.recognition = new SpeechRecognition();
      state.recognition.continuous = true;
      state.recognition.interimResults = false;
      state.recognition.lang = CONFIG.speechLang;

      state.recognition.onresult = (e) => {
        const transcript = e.results[e.results.length - 1][0].transcript.toLowerCase().trim();
        console.log('[VR Voice] Heard:', transcript);
        this.processCommand(transcript);
      };

      state.recognition.onerror = (e) => {
        console.error('[VR Voice] Error:', e.error);
      };

      // Toggle with Ctrl+V
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'v') {
          e.preventDefault();
          this.toggle();
        }
      });
    },

    processCommand(cmd) {
      // Navigation commands
      if (cmd.includes('hub') || cmd.includes('home')) {
        window.location.href = '/vr/';
      } else if (cmd.includes('weather')) {
        window.location.href = '/vr/weather-zone.html';
      } else if (cmd.includes('event')) {
        window.location.href = '/vr/events/';
      } else if (cmd.includes('movie') || cmd.includes('theater')) {
        window.location.href = '/vr/movies.html';
      } else if (cmd.includes('creator') || cmd.includes('streamer')) {
        window.location.href = '/vr/creators.html';
      } else if (cmd.includes('stock')) {
        window.location.href = '/vr/stocks-zone.html';
      } else if (cmd.includes('wellness') || cmd.includes('health')) {
        window.location.href = '/vr/wellness/';
      }
      // Action commands
      else if (cmd.includes('menu')) {
        toggleMenu && toggleMenu();
      } else if (cmd.includes('reset')) {
        window.resetPosition && window.resetPosition();
      } else if (cmd.includes('screenshot')) {
        ScreenshotTool.capture();
      } else if (cmd.includes('theme')) {
        ThemeSwitcher.cycle();
      }
    },

    toggle() {
      state.speechEnabled = !state.speechEnabled;
      
      if (state.speechEnabled) {
        state.recognition.start();
        showToast('🎤 Voice commands ON');
      } else {
        state.recognition.stop();
        showToast('🎤 Voice commands OFF');
      }
    }
  };

  // ==================== 5. SCREENSHOT TOOL ====================
  const ScreenshotTool = {
    init() {
      // Ctrl+P for screenshot
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'p') {
          e.preventDefault();
          this.capture();
        }
      });
    },

    capture() {
      const scene = document.querySelector('a-scene');
      if (!scene || !scene.renderer) {
        showToast('❌ Screenshot failed');
        return;
      }

      try {
        // Render frame
        scene.renderer.render(scene.object3D, scene.camera);
        
        // Get canvas data
        const canvas = scene.renderer.domElement;
        const dataURL = canvas.toDataURL('image/png');
        
        // Download
        const link = document.createElement('a');
        link.download = `vr-screenshot-${Date.now()}.png`;
        link.href = dataURL;
        link.click();
        
        showToast('📸 Screenshot saved!');
      } catch (e) {
        console.error('[VR Screenshot] Error:', e);
        showToast('❌ Screenshot failed');
      }
    }
  };

  // ==================== 6. SESSION TIMER ====================
  const SessionTimer = {
    element: null,
    
    init() {
      this.element = this.createUI();
      this.update();
    },

    createUI() {
      const div = document.createElement('div');
      div.id = 'vr-session-timer';
      div.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(0,0,0,0.7);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 8px;
        padding: 8px 12px;
        color: #e0e0e0;
        font-family: 'Courier New', monospace;
        font-size: 12px;
        z-index: 99999;
        backdrop-filter: blur(5px);
      `;
      document.body.appendChild(div);
      return div;
    },

    update() {
      const elapsed = Math.floor((Date.now() - state.sessionStartTime) / 1000);
      const hours = Math.floor(elapsed / 3600);
      const minutes = Math.floor((elapsed % 3600) / 60);
      const seconds = elapsed % 60;
      
      const timeStr = `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
      
      if (this.element) {
        this.element.textContent = `⏱️ ${timeStr}`;
      }

      // Show reminder every 30 minutes
      if (elapsed > 0 && elapsed % 1800 === 0) {
        showToast('⏰ Take a break! 30 min in VR');
      }

      setTimeout(() => this.update(), 1000);
    }
  };

  // ==================== 7. EMERGENCY EXIT ====================
  const EmergencyExit = {
    init() {
      // Triple-press ESC to exit
      let escCount = 0;
      let escTimer = null;

      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          escCount++;
          
          if (escCount === 1) {
            escTimer = setTimeout(() => { escCount = 0; }, 1000);
          } else if (escCount >= 3) {
            clearTimeout(escTimer);
            this.exit();
          }
        }
      });

      // Create exit button for VR mode
      this.createExitButton();
    },

    createExitButton() {
      const btn = document.createElement('button');
      btn.id = 'vr-emergency-exit';
      btn.innerHTML = '🚪 Exit VR';
      btn.style.cssText = `
        position: fixed;
        top: 20px;
        left: 20px;
        background: rgba(239, 68, 68, 0.8);
        border: 2px solid #ef4444;
        color: white;
        padding: 10px 16px;
        border-radius: 20px;
        cursor: pointer;
        font-weight: bold;
        z-index: 99999;
        display: none;
      `;
      btn.addEventListener('click', () => this.exit());
      document.body.appendChild(btn);

      // Show button when in VR
      const scene = document.querySelector('a-scene');
      if (scene) {
        scene.addEventListener('enter-vr', () => {
          btn.style.display = 'block';
        });
        scene.addEventListener('exit-vr', () => {
          btn.style.display = 'none';
        });
      }
    },

    exit() {
      // Exit VR mode if active
      const scene = document.querySelector('a-scene');
      if (scene && scene.is('vr-mode')) {
        scene.exitVR();
      }
      
      // Navigate to main site
      window.location.href = '/';
      showToast('🚪 Exiting VR...');
    }
  };

  // ==================== 8. ACCESSIBILITY MENU ====================
  const AccessibilityMenu = {
    init() {
      this.applySettings();
      this.createMenu();
    },

    applySettings() {
      const settings = state.accessibilitySettings;
      
      if (settings.fontSize) {
        document.documentElement.style.fontSize = settings.fontSize + '%';
      }
      if (settings.reduceMotion) {
        document.body.classList.add('vr-reduce-motion');
      }
      if (settings.highContrast) {
        ThemeSwitcher.applyTheme('high-contrast');
      }
    },

    createMenu() {
      // Create menu button
      const btn = document.createElement('button');
      btn.id = 'vr-accessibility-btn';
      btn.innerHTML = '♿';
      btn.title = 'Accessibility Options';
      btn.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(78, 205, 196, 0.8);
        border: 2px solid #4ecdc4;
        color: white;
        width: 44px;
        height: 44px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 20px;
        z-index: 99998;
        display: flex;
        align-items: center;
        justify-content: center;
      `;
      btn.addEventListener('click', () => this.toggleMenu());
      document.body.appendChild(btn);

      // Create menu overlay
      const menu = document.createElement('div');
      menu.id = 'vr-accessibility-menu';
      menu.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
        border: 2px solid var(--vr-accent, #00d4ff);
        border-radius: 20px;
        padding: 25px;
        z-index: 100000;
        display: none;
        min-width: 300px;
        backdrop-filter: blur(15px);
        color: var(--vr-text, #e0e0e0);
      `;
      menu.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: var(--vr-accent, #00d4ff);">♿ Accessibility</h3>
          <button onclick="this.parentElement.parentElement.style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px;">Text Size</label>
          <input type="range" id="vr-font-size" min="80" max="200" value="100" style="width: 100%;">
          <span id="vr-font-size-val">100%</span>
        </div>
        
        <div style="margin-bottom: 15px;">
          <label style="display: flex; align-items: center; cursor: pointer;">
            <input type="checkbox" id="vr-reduce-motion" style="margin-right: 10px;">
            Reduce Motion
          </label>
        </div>
        
        <div style="margin-bottom: 15px;">
          <label style="display: flex; align-items: center; cursor: pointer;">
            <input type="checkbox" id="vr-sound-effects" checked style="margin-right: 10px;">
            Sound Effects
          </label>
        </div>
        
        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px;">Theme</label>
          <select id="vr-theme-select" style="width: 100%; padding: 5px; border-radius: 5px;">
            <option value="dark">Dark</option>
            <option value="light">Light</option>
            <option value="high-contrast">High Contrast</option>
          </select>
        </div>
        
        <button id="vr-save-accessibility" style="width: 100%; padding: 10px; background: var(--vr-accent, #00d4ff); border: none; border-radius: 8px; color: white; font-weight: bold; cursor: pointer;">
          Save Settings
        </button>
      `;
      document.body.appendChild(menu);

      // Event listeners
      setTimeout(() => {
        const fontSizeInput = document.getElementById('vr-font-size');
        const fontSizeVal = document.getElementById('vr-font-size-val');
        const reduceMotionInput = document.getElementById('vr-reduce-motion');
        const soundEffectsInput = document.getElementById('vr-sound-effects');
        const themeSelect = document.getElementById('vr-theme-select');
        const saveBtn = document.getElementById('vr-save-accessibility');

        if (fontSizeInput) {
          fontSizeInput.addEventListener('input', (e) => {
            fontSizeVal.textContent = e.target.value + '%';
            document.documentElement.style.fontSize = e.target.value + '%';
          });
        }

        if (saveBtn) {
          saveBtn.addEventListener('click', () => {
            state.accessibilitySettings = {
              fontSize: fontSizeInput?.value || 100,
              reduceMotion: reduceMotionInput?.checked || false,
              soundEffects: soundEffectsInput?.checked !== false,
              theme: themeSelect?.value || 'dark'
            };
            localStorage.setItem('vr-accessibility', JSON.stringify(state.accessibilitySettings));
            ThemeSwitcher.applyTheme(state.accessibilitySettings.theme);
            showToast('♿ Settings saved');
            menu.style.display = 'none';
          });
        }
      }, 100);
    },

    toggleMenu() {
      const menu = document.getElementById('vr-accessibility-menu');
      if (menu) {
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
      }
    }
  };

  // ==================== 9. ZONE BOOKMARKS ====================
  const ZoneBookmarks = {
    init() {
      this.createUI();
    },

    createUI() {
      // Bookmark button
      const btn = document.createElement('button');
      btn.id = 'vr-bookmark-btn';
      btn.innerHTML = '🔖';
      btn.title = 'Save Bookmark';
      btn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 80px;
        background: rgba(168, 85, 247, 0.8);
        border: 2px solid #a855f7;
        color: white;
        width: 44px;
        height: 44px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 20px;
        z-index: 99998;
        display: flex;
        align-items: center;
        justify-content: center;
      `;
      btn.addEventListener('click', () => this.addBookmark());
      document.body.appendChild(btn);

      // Bookmarks panel
      const panel = document.createElement('div');
      panel.id = 'vr-bookmarks-panel';
      panel.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
        border: 2px solid var(--vr-accent, #00d4ff);
        border-radius: 20px;
        padding: 25px;
        z-index: 100000;
        display: none;
        min-width: 350px;
        max-height: 60vh;
        overflow-y: auto;
        backdrop-filter: blur(15px);
        color: var(--vr-text, #e0e0e0);
      `;
      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: var(--vr-accent, #00d4ff);">🔖 Bookmarks</h3>
          <button onclick="document.getElementById('vr-bookmarks-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        <div id="vr-bookmarks-list"></div>
        <button onclick="VRQuickWins.Bookmarks.showAddDialog()" style="width: 100%; padding: 10px; margin-top: 15px; background: rgba(0,212,255,0.3); border: 1px solid var(--vr-accent, #00d4ff); border-radius: 8px; color: var(--vr-accent, #00d4ff); cursor: pointer;">
          + Add Current Position
        </button>
      `;
      document.body.appendChild(panel);

      // View bookmarks button
      const viewBtn = document.createElement('button');
      viewBtn.id = 'vr-view-bookmarks-btn';
      viewBtn.innerHTML = '📑';
      viewBtn.title = 'View Bookmarks';
      viewBtn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 140px;
        background: rgba(0, 212, 255, 0.5);
        border: 2px solid #00d4ff;
        color: white;
        width: 44px;
        height: 44px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
        display: flex;
        align-items: center;
        justify-content: center;
      `;
      viewBtn.addEventListener('click', () => this.showPanel());
      document.body.appendChild(viewBtn);
    },

    addBookmark() {
      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (!rig) return;

      const position = rig.getAttribute('position');
      const zone = window.location.pathname;
      const name = prompt('Bookmark name:', `Position ${state.bookmarks.length + 1}`);
      
      if (!name) return;

      const bookmark = {
        id: Date.now(),
        name,
        zone,
        position: { x: position.x, y: position.y, z: position.z },
        created: Date.now()
      };

      state.bookmarks.push(bookmark);
      localStorage.setItem('vr-bookmarks', JSON.stringify(state.bookmarks));
      showToast(`🔖 Bookmark saved: ${name}`);
    },

    showPanel() {
      const panel = document.getElementById('vr-bookmarks-panel');
      const list = document.getElementById('vr-bookmarks-list');
      
      if (!panel || !list) return;

      // Filter bookmarks for current zone
      const currentZone = window.location.pathname;
      const zoneBookmarks = state.bookmarks.filter(b => b.zone === currentZone);

      if (zoneBookmarks.length === 0) {
        list.innerHTML = '<p style="text-align: center; opacity: 0.6; padding: 20px;">No bookmarks for this zone</p>';
      } else {
        list.innerHTML = zoneBookmarks.map(b => `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px;">
            <span>${b.name}</span>
            <div>
              <button onclick="VRQuickWins.Bookmarks.goTo(${b.id})" style="background: var(--vr-accent, #00d4ff); border: none; padding: 5px 12px; border-radius: 5px; color: white; cursor: pointer; margin-right: 5px;">Go</button>
              <button onclick="VRQuickWins.Bookmarks.delete(${b.id})" style="background: #ef4444; border: none; padding: 5px 12px; border-radius: 5px; color: white; cursor: pointer;">×</button>
            </div>
          </div>
        `).join('');
      }

      panel.style.display = 'block';
    },

    goTo(id) {
      const bookmark = state.bookmarks.find(b => b.id === id);
      if (!bookmark) return;

      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (rig && bookmark.position) {
        rig.setAttribute('animation', 
          `property: position; to: ${bookmark.position.x} ${bookmark.position.y} ${bookmark.position.z}; dur: 1000; easing: easeInOutQuad`
        );
        showToast(`🔖 Teleporting to: ${bookmark.name}`);
        document.getElementById('vr-bookmarks-panel').style.display = 'none';
      }
    },

    delete(id) {
      state.bookmarks = state.bookmarks.filter(b => b.id !== id);
      localStorage.setItem('vr-bookmarks', JSON.stringify(state.bookmarks));
      this.showPanel();
      showToast('🔖 Bookmark deleted');
    },

    showAddDialog() {
      this.addBookmark();
    }
  };

  // ==================== 10. QUICK SETTINGS PANEL ====================
  const QuickSettings = {
    init() {
      this.createUI();
      
      // Ctrl+, to open
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === ',') {
          e.preventDefault();
          this.toggle();
        }
      });
    },

    createUI() {
      const panel = document.createElement('div');
      panel.id = 'vr-quick-settings';
      panel.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
        border: 2px solid var(--vr-accent, #00d4ff);
        border-radius: 20px;
        padding: 25px;
        z-index: 100000;
        display: none;
        min-width: 300px;
        backdrop-filter: blur(15px);
        color: var(--vr-text, #e0e0e0);
      `;
      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: var(--vr-accent, #00d4ff);">⚙️ Quick Settings</h3>
          <button onclick="document.getElementById('vr-quick-settings').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px;">Master Volume</label>
          <input type="range" id="vr-master-volume" min="0" max="100" value="50" style="width: 100%;">
        </div>
        
        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 5px;">Brightness</label>
          <input type="range" id="vr-brightness" min="50" max="150" value="100" style="width: 100%;">
        </div>
        
        <div style="margin-bottom: 15px;">
          <label style="display: flex; align-items: center; cursor: pointer;">
            <input type="checkbox" id="vr-autosave-toggle" checked style="margin-right: 10px;">
            Auto-Save Position
          </label>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
          <button onclick="VRQuickWins.AutoSave.restorePosition(); document.getElementById('vr-quick-settings').style.display='none';" style="padding: 10px; background: rgba(0,212,255,0.3); border: 1px solid var(--vr-accent, #00d4ff); border-radius: 8px; color: var(--vr-accent, #00d4ff); cursor: pointer;">
            📍 Restore Pos
          </button>
          <button onclick="VRQuickWins.Bookmarks.showPanel(); document.getElementById('vr-quick-settings').style.display='none';" style="padding: 10px; background: rgba(168,85,247,0.3); border: 1px solid #a855f7; border-radius: 8px; color: #a855f7; cursor: pointer;">
            🔖 Bookmarks
          </button>
        </div>
      `;
      document.body.appendChild(panel);

      // Settings button
      const btn = document.createElement('button');
      btn.id = 'vr-quick-settings-btn';
      btn.innerHTML = '⚙️';
      btn.title = 'Quick Settings (Ctrl+,)';
      btn.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 20px;
        background: rgba(100, 100, 100, 0.5);
        border: 2px solid #888;
        color: white;
        width: 44px;
        height: 44px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 20px;
        z-index: 99998;
        display: flex;
        align-items: center;
        justify-content: center;
      `;
      btn.addEventListener('click', () => this.toggle());
      document.body.appendChild(btn);

      // Event listeners for sliders
      setTimeout(() => {
        const volumeInput = document.getElementById('vr-master-volume');
        const brightnessInput = document.getElementById('vr-brightness');
        const autosaveToggle = document.getElementById('vr-autosave-toggle');

        if (volumeInput) {
          volumeInput.addEventListener('input', (e) => {
            const volume = e.target.value / 100;
            // Apply to all audio/video elements
            document.querySelectorAll('audio, video').forEach(el => {
              el.volume = volume;
            });
          });
        }

        if (brightnessInput) {
          brightnessInput.addEventListener('input', (e) => {
            const brightness = e.target.value / 100;
            document.body.style.filter = `brightness(${brightness})`;
          });
        }

        if (autosaveToggle) {
          autosaveToggle.checked = state.autoSaveEnabled;
          autosaveToggle.addEventListener('change', (e) => {
            state.autoSaveEnabled = e.target.checked;
            localStorage.setItem('vr-autosave', state.autoSaveEnabled);
            showToast(state.autoSaveEnabled ? '💾 Auto-save ON' : '💾 Auto-save OFF');
          });
        }
      }, 100);
    },

    toggle() {
      const panel = document.getElementById('vr-quick-settings');
      if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
      }
    }
  };

  // ==================== UTILITY: TOAST NOTIFICATIONS ====================
  function showToast(message) {
    let toast = document.getElementById('vr-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'vr-toast';
      toast.style.cssText = `
        position: fixed;
        bottom: 100px;
        left: 50%;
        transform: translateX(-50%) translateY(20px);
        background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
        backdrop-filter: blur(12px);
        border: 1px solid var(--vr-accent, #00d4ff);
        border-radius: 10px;
        color: var(--vr-text, #e0e0e0);
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
    console.log('[VR Substantial Quick Wins] Initializing...');

    // Initialize all features
    PerformanceMonitor.init();
    AutoSavePosition.init();
    ThemeSwitcher.init();
    VoiceCommands.init();
    ScreenshotTool.init();
    SessionTimer.init();
    EmergencyExit.init();
    AccessibilityMenu.init();
    ZoneBookmarks.init();
    QuickSettings.init();

    console.log('[VR Substantial Quick Wins] Initialized!');
    console.log('Keyboard shortcuts:');
    console.log('  Ctrl+F - Performance monitor');
    console.log('  Ctrl+P - Screenshot');
    console.log('  Ctrl+V - Voice commands');
    console.log('  Ctrl+, - Quick settings');
    console.log('  ESC x3 - Emergency exit');
  }

  // Start when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose public API
  window.VRQuickWins = {
    Performance: PerformanceMonitor,
    AutoSave: AutoSavePosition,
    Theme: ThemeSwitcher,
    Voice: VoiceCommands,
    Screenshot: ScreenshotTool,
    Session: SessionTimer,
    Emergency: EmergencyExit,
    Accessibility: AccessibilityMenu,
    Bookmarks: ZoneBookmarks,
    Settings: QuickSettings,
    showToast
  };

})();
