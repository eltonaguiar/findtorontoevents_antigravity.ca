/**
 * VR Substantial Quick Wins - Set 11: Advanced Systems (10 features)
 * Continuing to 110 TOTAL VR FEATURES!
 * 
 * 10 Additional Major Features:
 * 1. VR Notifications Center (unified notification hub)
 * 2. Accessibility Voice Navigation (voice control)
 * 3. Dynamic LOD System (performance optimizer)
 * 4. VR Keyboard Shortcuts Overlay (help system)
 * 5. Auto-Walk Mode (hands-free movement)
 * 6. Shadow Play Mode (creative lighting)
 * 7. Haptic Feedback Designer (custom vibrations)
 * 8. Spatial Bookmarks (3D saved positions)
 * 9. VR Task Manager (system monitor)
 * 10. Immersive Reading Mode (focus reader)
 */

(function() {
  'use strict';

  const CONFIG = {
    lod: { enabled: true, distance: [10, 30, 100] },
    autoWalk: { speed: 2.0, turnAngle: 15 },
    hapticDesigner: { maxPatterns: 10 }
  };

  const state = {
    notifications: [],
    voiceNavEnabled: false,
    autoWalkActive: false,
    shadowPlayActive: false,
    spatialBookmarks: JSON.parse(localStorage.getItem('vr-spatial-bookmarks') || '[]'),
    readingMode: false,
    customHaptics: JSON.parse(localStorage.getItem('vr-custom-haptics') || '[]')
  };

  // ==================== 1. VR NOTIFICATIONS CENTER ====================
  const NotificationsCenter = {
    init() {
      this.createUI();
      console.log('[VR Notifications Center] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-notifications-center-btn';
      btn.innerHTML = '🔔';
      btn.title = 'Notifications Center';
      btn.style.cssText = `
        position: fixed; bottom: 20px; right: 860px;
        background: rgba(234, 179, 8, 0.5); border: 2px solid #eab308;
        color: white; width: 44px; height: 44px; border-radius: 50%;
        cursor: pointer; font-size: 20px; z-index: 99998;
        display: flex; align-items: center; justify-content: center;
      `;
      btn.addEventListener('click', () => this.showCenter());
      document.body.appendChild(btn);

      // Badge
      const badge = document.createElement('span');
      badge.id = 'vr-notifications-badge';
      badge.style.cssText = `
        position: absolute; top: -5px; right: -5px;
        background: #ef4444; color: white; font-size: 10px;
        padding: 2px 6px; border-radius: 10px; display: none;
      `;
      badge.textContent = '0';
      btn.appendChild(badge);
    },

    showCenter() {
      let panel = document.getElementById('vr-notifications-center');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-notifications-center';
        panel.style.cssText = `
          position: fixed; top: 50%; left: 50%;
          transform: translate(-50%, -50%);
          background: rgba(10,10,20,0.95); border: 2px solid #eab308;
          border-radius: 20px; padding: 25px; z-index: 100000;
          min-width: 400px; max-height: 70vh; overflow-y: auto;
          color: white;
        `;
        document.body.appendChild(panel);
      }

      const notifications = state.notifications;
      
      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #eab308;">🔔 Notifications Center</h3>
          <button onclick="document.getElementById('vr-notifications-center').style.display='none'" 
            style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; 
            border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="display: flex; gap: 10px; margin-bottom: 15px;">
          <button onclick="VRQuickWinsSet11.Notifications.clearAll()" 
            style="flex: 1; padding: 8px; background: rgba(239,68,68,0.3); border: 1px solid #ef4444; 
            border-radius: 8px; color: white; cursor: pointer;">Clear All</button>
          <button onclick="VRQuickWinsSet11.Notifications.markAllRead()" 
            style="flex: 1; padding: 8px; background: rgba(34,197,94,0.3); border: 1px solid #22c55e; 
            border-radius: 8px; color: white; cursor: pointer;">Mark Read</button>
        </div>

        <div style="display: grid; gap: 8px;">
          ${notifications.length === 0 ? 
            '<p style="text-align: center; opacity: 0.5; padding: 30px;">No notifications</p>' :
            notifications.map((n, i) => `
              <div style="padding: 12px; background: ${n.read ? 'rgba(255,255,255,0.05)' : 'rgba(234,179,8,0.1)'}; 
                border-left: 4px solid ${n.type === 'error' ? '#ef4444' : n.type === 'success' ? '#22c55e' : '#eab308'}; 
                border-radius: 8px; cursor: pointer;" onclick="VRQuickWinsSet11.Notifications.markRead(${i})">
                <div style="font-weight: bold; font-size: 14px;">${n.title}</div>
                <div style="font-size: 12px; opacity: 0.8;">${n.message}</div>
                <div style="font-size: 10px; opacity: 0.5; margin-top: 5px;">${new Date(n.time).toLocaleTimeString()}</div>
              </div>
            `).join('')
          }
        </div>
      `;
      panel.style.display = 'block';
      this.updateBadge();
    },

    add(title, message, type = 'info') {
      state.notifications.unshift({
        title, message, type,
        time: Date.now(),
        read: false
      });
      
      if (state.notifications.length > 50) {
        state.notifications = state.notifications.slice(0, 50);
      }
      
      this.updateBadge();
    },

    markRead(index) {
      if (state.notifications[index]) {
        state.notifications[index].read = true;
        this.showCenter();
      }
    },

    markAllRead() {
      state.notifications.forEach(n => n.read = true);
      this.showCenter();
    },

    clearAll() {
      state.notifications = [];
      this.showCenter();
    },

    updateBadge() {
      const badge = document.getElementById('vr-notifications-badge');
      const unread = state.notifications.filter(n => !n.read).length;
      if (badge) {
        badge.textContent = unread;
        badge.style.display = unread > 0 ? 'block' : 'none';
      }
    }
  };

  // ==================== 2. ACCESSIBILITY VOICE NAVIGATION ====================
  const VoiceNavigation = {
    commands: {
      'menu': () => this.openMenu(),
      'home': () => window.location.href = '/vr/',
      'back': () => history.back(),
      'forward': () => history.forward(),
      'reset': () => window.resetPosition && window.resetPosition(),
      'help': () => this.showHelp(),
      'fullscreen': () => this.toggleFullscreen(),
      'screenshot': () => this.takeScreenshot()
    },

    init() {
      this.createUI();
      console.log('[VR Voice Navigation] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-voice-nav-btn';
      btn.innerHTML = '🎤';
      btn.title = 'Voice Navigation (Hold V)';
      btn.style.cssText = `
        position: fixed; top: 2920px; right: 20px;
        background: rgba(34, 197, 94, 0.5); border: 2px solid #22c55e;
        color: white; width: 40px; height: 40px; border-radius: 50%;
        cursor: pointer; font-size: 18px; z-index: 99998;
      `;
      btn.addEventListener('click', () => this.toggle());
      document.body.appendChild(btn);

      // Hold V key for voice
      document.addEventListener('keydown', (e) => {
        if (e.key === 'v' && !state.voiceNavEnabled) {
          this.startListening();
        }
      });
      document.addEventListener('keyup', (e) => {
        if (e.key === 'v') {
          this.stopListening();
        }
      });
    },

    toggle() {
      state.voiceNavEnabled = !state.voiceNavEnabled;
      const btn = document.getElementById('vr-voice-nav-btn');
      
      if (state.voiceNavEnabled) {
        btn.style.background = 'rgba(34, 197, 94, 0.9)';
        btn.style.boxShadow = '0 0 20px #22c55e';
        showToast('🎤 Voice Navigation ON - Hold V and speak');
      } else {
        btn.style.background = 'rgba(34, 197, 94, 0.5)';
        btn.style.boxShadow = 'none';
        showToast('🎤 Voice Navigation OFF');
      }
    },

    startListening() {
      if (!('webkitSpeechRecognition' in window)) return;
      
      this.recognition = new webkitSpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      
      this.recognition.onresult = (e) => {
        const cmd = e.results[0][0].transcript.toLowerCase().trim();
        this.processCommand(cmd);
      };
      
      this.recognition.start();
      showToast('🎤 Listening...');
    },

    stopListening() {
      if (this.recognition) {
        this.recognition.stop();
      }
    },

    processCommand(cmd) {
      for (const [key, action] of Object.entries(this.commands)) {
        if (cmd.includes(key)) {
          action();
          showToast(`🎤 Command: "${key}"`);
          return;
        }
      }
      showToast(`🎤 Unknown: "${cmd}"`);
    },

    openMenu() { showToast('Menu opened'); },
    showHelp() { showToast('Say: menu, home, back, reset, help, fullscreen, screenshot'); },
    toggleFullscreen() {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
      } else {
        document.exitFullscreen();
      }
    },
    takeScreenshot() {
      if (window.VRQuickWins && window.VRQuickWins.Screenshot) {
        window.VRQuickWins.Screenshot.capture();
      }
    }
  };

  // ==================== 3. DYNAMIC LOD SYSTEM ====================
  const DynamicLOD = {
    init() {
      this.createUI();
      this.startOptimizer();
      console.log('[VR Dynamic LOD] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-lod-btn';
      btn.innerHTML = '⚡';
      btn.title = 'Performance Optimizer';
      btn.style.cssText = `
        position: fixed; top: 2970px; right: 20px;
        background: rgba(59, 130, 246, 0.5); border: 2px solid #3b82f6;
        color: white; width: 40px; height: 40px; border-radius: 50%;
        cursor: pointer; font-size: 18px; z-index: 99998;
      `;
      btn.addEventListener('click', () => this.showStats());
      document.body.appendChild(btn);

      // FPS counter
      const fps = document.createElement('div');
      fps.id = 'vr-lod-fps';
      fps.style.cssText = `
        position: fixed; top: 3015px; right: 20px;
        background: rgba(0,0,0,0.8); border-radius: 8px;
        padding: 5px 10px; color: #3b82f6; font-size: 11px;
        z-index: 99997; font-family: monospace;
      `;
      fps.textContent = '60 FPS';
      document.body.appendChild(fps);
    },

    startOptimizer() {
      let frameCount = 0;
      let lastTime = performance.now();
      let currentFPS = 60;

      const measure = () => {
        frameCount++;
        const now = performance.now();
        
        if (now - lastTime >= 1000) {
          currentFPS = frameCount;
          frameCount = 0;
          lastTime = now;
          
          const fpsEl = document.getElementById('vr-lod-fps');
          if (fpsEl) {
            fpsEl.textContent = `${currentFPS} FPS`;
            fpsEl.style.color = currentFPS < 30 ? '#ef4444' : currentFPS < 50 ? '#eab308' : '#3b82f6';
          }
          
          this.adjustLOD(currentFPS);
        }
        
        requestAnimationFrame(measure);
      };
      requestAnimationFrame(measure);
    },

    adjustLOD(fps) {
      const scene = document.querySelector('a-scene');
      if (!scene) return;

      // Reduce quality if FPS is low
      if (fps < 30) {
        scene.querySelectorAll('a-sphere, a-box').forEach(el => {
          if (!el.hasAttribute('data-lod')) {
            el.setAttribute('data-lod', 'low');
            el.setAttribute('segments-width', '8');
            el.setAttribute('segments-height', '8');
          }
        });
      }
    },

    showStats() {
      showToast('⚡ Performance: Auto-optimizing');
    }
  };

  // ==================== 4. VR KEYBOARD SHORTCUTS OVERLAY ====================
  const ShortcutsOverlay = {
    shortcuts: [
      { key: 'WASD / Thumbstick', action: 'Move around' },
      { key: 'Mouse / Head', action: 'Look around' },
      { key: 'Space (hold)', action: 'Voice command' },
      { key: 'V (hold)', action: 'Voice navigation' },
      { key: 'ESC', action: 'Close menus / Exit' },
      { key: 'R', action: 'Reset position' },
      { key: 'H', action: 'Return to hub' },
      { key: 'M', action: 'Toggle menu' },
      { key: 'F', action: 'Friends list' },
      { key: 'G', action: 'Quick select wheel' },
      { key: 'T', action: 'Quick travel' },
      { key: 'I', action: 'Inventory' },
      { key: 'Q/E', action: 'Snap turn' },
      { key: 'Ctrl+F', action: 'FPS monitor' },
      { key: 'Ctrl+P', action: 'Screenshot' }
    ],

    init() {
      this.createUI();
      console.log('[VR Shortcuts Overlay] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-shortcuts-overlay-btn';
      btn.innerHTML = '⌨️';
      btn.title = 'Keyboard Shortcuts';
      btn.style.cssText = `
        position: fixed; top: 3020px; right: 20px;
        background: rgba(100, 100, 100, 0.5); border: 2px solid #888;
        color: white; width: 40px; height: 40px; border-radius: 50%;
        cursor: pointer; font-size: 18px; z-index: 99998;
      `;
      btn.addEventListener('click', () => this.showOverlay());
      document.body.appendChild(btn);

      // F1 key to show
      document.addEventListener('keydown', (e) => {
        if (e.key === 'F1') {
          e.preventDefault();
          this.showOverlay();
        }
      });
    },

    showOverlay() {
      let overlay = document.getElementById('vr-shortcuts-overlay');
      if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'vr-shortcuts-overlay';
        overlay.style.cssText = `
          position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
          background: rgba(0,0,0,0.9); backdrop-filter: blur(10px);
          z-index: 100001; display: flex; align-items: center; justify-content: center;
        `;
        document.body.appendChild(overlay);
      }

      overlay.innerHTML = `
        <div style="background: linear-gradient(135deg, #1a1a3e 0%, #0f0f1f 100%); 
          border: 2px solid #00d4ff; border-radius: 20px; padding: 40px; max-width: 600px; max-height: 80vh; overflow-y: auto;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
            <h2 style="color: #00d4ff; margin: 0;">⌨️ Keyboard Shortcuts</h2>
            <button onclick="document.getElementById('vr-shortcuts-overlay').style.display='none'" 
              style="background: rgba(239,68,68,0.8); border: none; color: white; width: 36px; height: 36px; 
              border-radius: 50%; cursor: pointer; font-size: 20px;">×</button>
          </div>
          
          <div style="display: grid; gap: 12px;">
            ${this.shortcuts.map(s => `
              <div style="display: flex; justify-content: space-between; align-items: center; 
                padding: 12px 15px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                <kbd style="background: rgba(0,212,255,0.2); padding: 6px 12px; border-radius: 6px; 
                  color: #00d4ff; font-family: monospace; font-size: 13px; border: 1px solid rgba(0,212,255,0.3);">${s.key}</kbd>
                <span style="color: #ccc; font-size: 14px;">${s.action}</span>
              </div>
            `).join('')}
          </div>
          
          <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); 
            color: #888; font-size: 12px; text-align: center;">
            Press F1 anytime to show this help
          </div>
        </div>
      `;
      overlay.style.display = 'flex';
    }
  };

  // ==================== 5. AUTO-WALK MODE ====================
  const AutoWalk = {
    init() {
      this.createUI();
      console.log('[VR Auto-Walk] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-autowalk-btn';
      btn.innerHTML = '🚶';
      btn.title = 'Auto-Walk (W to toggle)';
      btn.style.cssText = `
        position: fixed; top: 3070px; right: 20px;
        background: rgba(168, 85, 247, 0.5); border: 2px solid #a855f7;
        color: white; width: 40px; height: 40px; border-radius: 50%;
        cursor: pointer; font-size: 18px; z-index: 99998;
      `;
      btn.addEventListener('click', () => this.toggle());
      document.body.appendChild(btn);

      // W key toggle
      document.addEventListener('keydown', (e) => {
        if (e.key === 'w' && e.target === document.body) {
          this.toggle();
        }
      });
    },

    toggle() {
      state.autoWalkActive = !state.autoWalkActive;
      
      const btn = document.getElementById('vr-autowalk-btn');
      
      if (state.autoWalkActive) {
        btn.style.background = 'rgba(168, 85, 247, 0.9)';
        btn.style.boxShadow = '0 0 20px #a855f7';
        this.startWalking();
        showToast('🚶 Auto-walk ON - Press W to stop');
      } else {
        btn.style.background = 'rgba(168, 85, 247, 0.5)';
        btn.style.boxShadow = 'none';
        this.stopWalking();
        showToast('🚶 Auto-walk OFF');
      }
    },

    startWalking() {
      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (!rig) return;

      this.walkInterval = setInterval(() => {
        const pos = rig.getAttribute('position');
        const rot = rig.getAttribute('rotation');
        
        // Move forward in facing direction
        const rad = rot.y * Math.PI / 180;
        pos.x -= Math.sin(rad) * 0.05;
        pos.z -= Math.cos(rad) * 0.05;
        
        rig.setAttribute('position', pos);
      }, 50);
    },

    stopWalking() {
      clearInterval(this.walkInterval);
    }
  };

  // ==================== 6. SHADOW PLAY MODE ====================
  const ShadowPlay = {
    init() {
      this.createUI();
      console.log('[VR Shadow Play] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-shadowplay-btn';
      btn.innerHTML = '🎭';
      btn.title = 'Shadow Play Mode';
      btn.style.cssText = `
        position: fixed; top: 3120px; right: 20px;
        background: rgba(100, 100, 100, 0.5); border: 2px solid #666;
        color: white; width: 40px; height: 40px; border-radius: 50%;
        cursor: pointer; font-size: 18px; z-index: 99998;
      `;
      btn.addEventListener('click', () => this.toggle());
      document.body.appendChild(btn);
    },

    toggle() {
      state.shadowPlayActive = !state.shadowPlayActive;
      
      const scene = document.querySelector('a-scene');
      if (!scene) return;

      if (state.shadowPlayActive) {
        // Create shadow puppet theater effect
        scene.style.filter = 'contrast(1.5) brightness(0.8)';
        
        // Add dramatic lighting
        const light = document.createElement('a-light');
        light.id = 'vr-shadowplay-light';
        light.setAttribute('type', 'spot');
        light.setAttribute('position', '0 5 0');
        light.setAttribute('color', '#ffaa00');
        light.setAttribute('intensity', '2');
        light.setAttribute('angle', '30');
        scene.appendChild(light);
        
        showToast('🎭 Shadow Play Mode ON');
      } else {
        scene.style.filter = '';
        const light = document.getElementById('vr-shadowplay-light');
        if (light) light.remove();
        showToast('🎭 Shadow Play Mode OFF');
      }
    }
  };

  // ==================== 7. HAPTIC FEEDBACK DESIGNER ====================
  const HapticDesigner = {
    init() {
      this.createUI();
      console.log('[VR Haptic Designer] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-haptic-designer-btn';
      btn.innerHTML = '🔨';
      btn.title = 'Haptic Designer';
      btn.style.cssText = `
        position: fixed; top: 3170px; right: 20px;
        background: rgba(234, 179, 8, 0.5); border: 2px solid #eab308;
        color: white; width: 40px; height: 40px; border-radius: 50%;
        cursor: pointer; font-size: 18px; z-index: 99998;
      `;
      btn.addEventListener('click', () => this.showDesigner());
      document.body.appendChild(btn);
    },

    showDesigner() {
      let panel = document.getElementById('vr-haptic-designer');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-haptic-designer';
        panel.style.cssText = `
          position: fixed; top: 50%; left: 50%;
          transform: translate(-50%, -50%);
          background: rgba(10,10,20,0.95); border: 2px solid #eab308;
          border-radius: 20px; padding: 25px; z-index: 100000;
          min-width: 350px; color: white;
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <h3 style="color: #eab308; margin-bottom: 15px;">🔨 Haptic Designer</h3>
        <p style="font-size: 12px; color: #888; margin-bottom: 15px;">Create custom vibration patterns</p>
        
        <div style="display: grid; gap: 10px; margin-bottom: 15px;">
          <div style="display: flex; gap: 10px;">
            <button onclick="VRQuickWinsSet11.HapticDesigner.addPulse(100)" style="flex: 1; padding: 10px; background: rgba(234,179,8,0.3); border: 1px solid #eab308; border-radius: 8px; color: white; cursor: pointer;">Short</button>
            <button onclick="VRQuickWinsSet11.HapticDesigner.addPulse(300)" style="flex: 1; padding: 10px; background: rgba(234,179,8,0.3); border: 1px solid #eab308; border-radius: 8px; color: white; cursor: pointer;">Long</button>
            <button onclick="VRQuickWinsSet11.HapticDesigner.addPause()" style="flex: 1; padding: 10px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; cursor: pointer;">Pause</button>
          </div>
        </div>
        
        <div id="vr-haptic-pattern" style="background: rgba(0,0,0,0.5); border-radius: 10px; padding: 15px; min-height: 60px; margin-bottom: 15px; display: flex; gap: 5px; flex-wrap: wrap;">
          <span style="color: #666; font-size: 12px;">Pattern: (empty)</span>
        </div>
        
        <div style="display: flex; gap: 10px;">
          <button onclick="VRQuickWinsSet11.HapticDesigner.test()" style="flex: 1; padding: 12px; background: #eab308; border: none; border-radius: 8px; color: black; cursor: pointer;">Test</button>
          <button onclick="VRQuickWinsSet11.HapticDesigner.clear()" style="flex: 1; padding: 12px; background: rgba(239,68,68,0.3); border: 1px solid #ef4444; border-radius: 8px; color: white; cursor: pointer;">Clear</button>
        </div>
      `;
      panel.style.display = 'block';
      
      this.currentPattern = [];
    },

    addPulse(duration) {
      this.currentPattern.push({ type: 'pulse', duration });
      this.updateDisplay();
    },

    addPause() {
      this.currentPattern.push({ type: 'pause', duration: 200 });
      this.updateDisplay();
    },

    updateDisplay() {
      const display = document.getElementById('vr-haptic-pattern');
      if (!display) return;
      
      display.innerHTML = this.currentPattern.map(p => 
        `<div style="width: ${p.duration / 10}px; height: 30px; background: ${p.type === 'pulse' ? '#eab308' : 'transparent'}; border: ${p.type === 'pause' ? '1px dashed #666' : 'none'}; border-radius: 4px;"></div>`
      ).join('');
    },

    test() {
      const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
      let time = 0;
      
      this.currentPattern.forEach(p => {
        setTimeout(() => {
          if (p.type === 'pulse') {
            for (const gp of gamepads) {
              if (gp && gp.hapticActuators?.[0]) {
                gp.hapticActuators[0].pulse(0.8, p.duration);
              }
            }
          }
        }, time);
        time += p.duration + 50;
      });
      
      showToast('🔨 Testing pattern...');
    },

    clear() {
      this.currentPattern = [];
      this.updateDisplay();
    }
  };

  // ==================== 8. SPATIAL BOOKMARKS ====================
  const SpatialBookmarks = {
    init() {
      this.createUI();
      console.log('[VR Spatial Bookmarks] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-spatial-bookmarks-btn';
      btn.innerHTML = '📌';
      btn.title = 'Spatial Bookmarks';
      btn.style.cssText = `
        position: fixed; top: 3220px; right: 20px;
        background: rgba(14, 165, 233, 0.5); border: 2px solid #0ea5e9;
        color: white; width: 40px; height: 40px; border-radius: 50%;
        cursor: pointer; font-size: 18px; z-index: 99998;
      `;
      btn.addEventListener('click', () => this.showPanel());
      document.body.appendChild(btn);
    },

    showPanel() {
      let panel = document.getElementById('vr-spatial-bookmarks');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-spatial-bookmarks';
        panel.style.cssText = `
          position: fixed; top: 50%; left: 50%;
          transform: translate(-50%, -50%);
          background: rgba(10,10,20,0.95); border: 2px solid #0ea5e9;
          border-radius: 20px; padding: 25px; z-index: 100000;
          min-width: 350px; color: white;
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <h3 style="color: #0ea5e9; margin-bottom: 15px;">📌 Spatial Bookmarks</h3>
        <p style="font-size: 12px; color: #888; margin-bottom: 15px;">Save your exact position in 3D space</p>
        
        <button onclick="VRQuickWinsSet11.SpatialBookmarks.save()" 
          style="width: 100%; padding: 12px; background: #0ea5e9; border: none; border-radius: 8px; color: white; cursor: pointer; margin-bottom: 15px;">
          📌 Save Current Position
        </button>
        
        <div style="display: grid; gap: 8px;">
          ${state.spatialBookmarks.length === 0 ? 
            '<p style="text-align: center; opacity: 0.5; padding: 20px;">No spatial bookmarks yet</p>' :
            state.spatialBookmarks.map((bm, i) => `
              <div style="padding: 12px; background: rgba(14,165,233,0.1); border-radius: 8px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-weight: bold;">${bm.name}</div>
                  <div style="font-size: 11px; opacity: 0.7;">X:${bm.x.toFixed(1)} Y:${bm.y.toFixed(1)} Z:${bm.z.toFixed(1)}</div>
                </div>
                <button onclick="VRQuickWinsSet11.SpatialBookmarks.goto(${i})" 
                  style="padding: 8px 16px; background: #0ea5e9; border: none; border-radius: 6px; color: white; cursor: pointer;">Go</button>
              </div>
            `).join('')
          }
        </div>
      `;
      panel.style.display = 'block';
    },

    save() {
      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (!rig) return;

      const pos = rig.getAttribute('position');
      const name = prompt('Bookmark name:', `Position ${state.spatialBookmarks.length + 1}`);
      if (!name) return;

      state.spatialBookmarks.push({
        name,
        x: pos.x, y: pos.y, z: pos.z,
        zone: window.location.pathname,
        created: Date.now()
      });

      localStorage.setItem('vr-spatial-bookmarks', JSON.stringify(state.spatialBookmarks));
      this.showPanel();
      showToast('📌 Spatial bookmark saved!');
    },

    goto(index) {
      const bm = state.spatialBookmarks[index];
      if (!bm) return;

      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (rig) {
        rig.setAttribute('animation', 
          `property: position; to: ${bm.x} ${bm.y} ${bm.z}; dur: 1500; easing: easeInOutQuad`
        );
        showToast(`📌 Teleporting to ${bm.name}`);
      }
    }
  };

  // ==================== 9. VR TASK MANAGER ====================
  const VRTaskManager = {
    init() {
      this.createUI();
      this.startMonitoring();
      console.log('[VR Task Manager] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-taskmanager-btn';
      btn.innerHTML = '⚙️';
      btn.title = 'Task Manager';
      btn.style.cssText = `
        position: fixed; top: 3270px; right: 20px;
        background: rgba(100, 100, 100, 0.5); border: 2px solid #888;
        color: white; width: 40px; height: 40px; border-radius: 50%;
        cursor: pointer; font-size: 18px; z-index: 99998;
      `;
      btn.addEventListener('click', () => this.showManager());
      document.body.appendChild(btn);
    },

    startMonitoring() {
      setInterval(() => {
        this.memoryUsage = performance.memory ? performance.memory.usedJSHeapSize / 1048576 : 0;
      }, 5000);
    },

    showManager() {
      let panel = document.getElementById('vr-task-manager');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-task-manager';
        panel.style.cssText = `
          position: fixed; top: 50%; left: 50%;
          transform: translate(-50%, -50%);
          background: rgba(10,10,20,0.95); border: 2px solid #888;
          border-radius: 20px; padding: 25px; z-index: 100000;
          min-width: 400px; color: white; font-family: monospace;
        `;
        document.body.appendChild(panel);
      }

      const features = Object.keys(window).filter(k => k.startsWith('VRQuickWins')).length;
      
      panel.innerHTML = `
        <h3 style="color: #888; margin-bottom: 20px; font-family: sans-serif;">⚙️ VR Task Manager</h3>
        
        <div style="display: grid; gap: 15px;">
          <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
              <span>Memory Usage:</span>
              <span style="color: ${this.memoryUsage > 100 ? '#ef4444' : '#22c55e'};">${this.memoryUsage.toFixed(1)} MB</span>
            </div>
            <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px;">
              <div style="width: ${Math.min(this.memoryUsage / 2, 100)}%; height: 100%; background: ${this.memoryUsage > 100 ? '#ef4444' : '#22c55e'}; border-radius: 3px;"></div>
            </div>
          </div>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 10px; text-align: center;">
              <div style="font-size: 24px; color: #0ea5e9;">${features}</div>
              <div style="font-size: 11px; opacity: 0.7;">Feature Sets Active</div>
            </div>
            <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 10px; text-align: center;">
              <div style="font-size: 24px; color: #0ea5e9;">${document.querySelectorAll('a-entity').length}</div>
              <div style="font-size: 11px; opacity: 0.7;">3D Entities</div>
            </div>
          </div>
          
          <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 10px;">
            <div style="font-size: 12px; opacity: 0.7; margin-bottom: 8px;">Active Modules:</div>
            <div style="display: flex; flex-wrap: wrap; gap: 5px;">
              ${Object.keys(window).filter(k => k.startsWith('VRQuickWins')).map(k => 
                `<span style="padding: 4px 8px; background: rgba(14,165,233,0.3); border-radius: 4px; font-size: 10px;">${k.replace('VRQuickWins', 'Set')}</span>`
              ).join('')}
            </div>
          </div>
        </div>
        
        <button onclick="document.getElementById('vr-task-manager').style.display='none'" 
          style="width: 100%; margin-top: 20px; padding: 12px; background: #888; border: none; border-radius: 8px; color: white; cursor: pointer; font-family: sans-serif;">Close</button>
      `;
      panel.style.display = 'block';
    }
  };

  // ==================== 10. IMMERSIVE READING MODE ====================
  const ImmersiveReading = {
    init() {
      this.createUI();
      console.log('[VR Immersive Reading] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-reading-btn';
      btn.innerHTML = '📖';
      btn.title = 'Reading Mode';
      btn.style.cssText = `
        position: fixed; top: 3320px; right: 20px;
        background: rgba(251, 146, 60, 0.5); border: 2px solid #fb923c;
        color: white; width: 40px; height: 40px; border-radius: 50%;
        cursor: pointer; font-size: 18px; z-index: 99998;
      `;
      btn.addEventListener('click', () => this.toggle());
      document.body.appendChild(btn);
    },

    toggle() {
      state.readingMode = !state.readingMode;
      
      const btn = document.getElementById('vr-reading-btn');
      
      if (state.readingMode) {
        btn.style.background = 'rgba(251, 146, 60, 0.9)';
        btn.style.boxShadow = '0 0 20px #fb923c';
        
        // Dim non-essential UI
        document.querySelectorAll('button:not(#vr-reading-btn)').forEach(el => {
          if (!el.id.includes('vr-')) {
            el.dataset.originalOpacity = el.style.opacity || '1';
            el.style.opacity = '0.3';
          }
        });
        
        // Create reading focus
        const focus = document.createElement('div');
        focus.id = 'vr-reading-focus';
        focus.style.cssText = `
          position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
          width: 600px; max-height: 70vh; background: rgba(20,20,30,0.95);
          border: 2px solid #fb923c; border-radius: 20px; padding: 40px;
          z-index: 99999; overflow-y: auto; color: #e0e0e0; line-height: 1.8;
          font-size: 18px; box-shadow: 0 0 100px rgba(251,146,60,0.3);
        `;
        focus.innerHTML = `
          <h2 style="color: #fb923c; margin-bottom: 20px;">📖 Immersive Reading</h2>
          <p>This is a distraction-free reading environment designed for deep focus in VR. All non-essential UI elements are dimmed to help you concentrate.</p>
          <p style="margin-top: 20px;">You can load documents here for comfortable reading with reduced eye strain.</p>
          <button onclick="document.getElementById('vr-reading-focus').remove(); VRQuickWinsSet11.Reading.toggle();" 
            style="margin-top: 30px; padding: 12px 30px; background: #fb923c; border: none; border-radius: 8px; color: white; cursor: pointer;">Close Reading Mode</button>
        `;
        document.body.appendChild(focus);
        
        showToast('📖 Reading Mode ON - Distractions minimized');
      } else {
        btn.style.background = 'rgba(251, 146, 60, 0.5)';
        btn.style.boxShadow = 'none';
        
        // Restore UI
        document.querySelectorAll('button:not(#vr-reading-btn)').forEach(el => {
          if (!el.id.includes('vr-')) {
            el.style.opacity = el.dataset.originalOpacity || '1';
          }
        });
        
        const focus = document.getElementById('vr-reading-focus');
        if (focus) focus.remove();
        
        showToast('📖 Reading Mode OFF');
      }
    }
  };

  // ==================== UTILITY: TOAST ====================
  function showToast(message) {
    let toast = document.getElementById('vr-toast-set11');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'vr-toast-set11';
      toast.style.cssText = `
        position: fixed; bottom: 550px; left: 50%;
        transform: translateX(-50%) translateY(20px);
        background: rgba(10,10,20,0.95); backdrop-filter: blur(12px);
        border: 1px solid #22c55e; border-radius: 10px;
        color: #e0e0e0; font-size: 14px; padding: 12px 24px;
        opacity: 0; pointer-events: none; transition: all 0.3s ease;
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
    console.log('[VR Substantial Quick Wins - Set 11] Initializing...');
    console.log('🚀 TARGET: 110 TOTAL VR FEATURES!');

    NotificationsCenter.init();
    VoiceNavigation.init();
    DynamicLOD.init();
    ShortcutsOverlay.init();
    AutoWalk.init();
    ShadowPlay.init();
    HapticDesigner.init();
    SpatialBookmarks.init();
    VRTaskManager.init();
    ImmersiveReading.init();

    console.log('[VR Set 11] COMPLETE - 110 TOTAL FEATURES!');
    
    // Add sample notification
    setTimeout(() => {
      NotificationsCenter.add('Welcome!', 'Set 11 is now active with 10 new features', 'success');
    }, 3000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose API
  window.VRQuickWinsSet11 = {
    Notifications: NotificationsCenter,
    VoiceNav: VoiceNavigation,
    LOD: DynamicLOD,
    Shortcuts: ShortcutsOverlay,
    AutoWalk,
    ShadowPlay,
    Haptic: HapticDesigner,
    SpatialBookmarks,
    TaskManager: VRTaskManager,
    Reading: ImmersiveReading,
    showToast
  };

})();
