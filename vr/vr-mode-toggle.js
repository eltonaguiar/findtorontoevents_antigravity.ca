/**
 * VR Simple/Advanced Mode Toggle
 * Reduces UI clutter by hiding advanced features in Simple mode
 */

(function() {
  'use strict';

  const VRModeToggle = {
    mode: 'advanced', // 'simple' or 'advanced'
    simpleButtons: [],
    advancedButtons: [],
    
    init() {
      // Load saved preference
      const savedMode = localStorage.getItem('vr-ui-mode');
      if (savedMode) this.mode = savedMode;
      
      this.createToggle();
      this.categorizeButtons();
      this.applyMode();
      
      console.log('[VR Mode] Initialized:', this.mode);
    },
    
    createToggle() {
      // Create mode toggle button
      const toggle = document.createElement('button');
      toggle.id = 'vr-mode-toggle';
      toggle.innerHTML = this.mode === 'simple' ? '🎯' : '🎛️';
      toggle.title = this.mode === 'simple' ? 'Switch to Advanced Mode' : 'Switch to Simple Mode';
      toggle.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        width: 50px;
        height: 50px;
        background: ${this.mode === 'simple' ? 'linear-gradient(135deg, #22c55e, #16a34a)' : 'linear-gradient(135deg, #6b7280, #4b5563)'};
        border: 2px solid rgba(255,255,255,0.3);
        border-radius: 25px;
        color: white;
        font-size: 20px;
        cursor: pointer;
        z-index: 99999;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
      `;
      
      toggle.onclick = () => this.toggleMode();
      document.body.appendChild(toggle);
      
      // Create mode indicator text
      const indicator = document.createElement('div');
      indicator.id = 'vr-mode-indicator';
      indicator.textContent = this.mode === 'simple' ? 'Simple Mode' : 'Advanced Mode';
      indicator.style.cssText = `
        position: fixed;
        bottom: 75px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0,0,0,0.8);
        color: ${this.mode === 'simple' ? '#22c55e' : '#6b7280'};
        padding: 5px 15px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: bold;
        z-index: 99998;
        pointer-events: none;
        transition: all 0.3s ease;
      `;
      document.body.appendChild(indicator);
      
      // First-time user: show mode selector
      if (!localStorage.getItem('vr-mode-seen')) {
        this.showModeSelector();
        localStorage.setItem('vr-mode-seen', 'true');
      }
    },
    
    showModeSelector() {
      const selector = document.createElement('div');
      selector.id = 'vr-mode-selector';
      selector.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(10,10,30,0.95);
        backdrop-filter: blur(10px);
        z-index: 100000;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 20px;
      `;
      
      selector.innerHTML = `
        <h2 style="color: #00d4ff; font-size: 28px; margin-bottom: 10px;">Choose Your Experience</h2>
        <p style="color: #888; margin-bottom: 40px; text-align: center;">Select a mode that suits your preference</p>
        
        <div style="display: flex; gap: 20px; flex-wrap: wrap; justify-content: center;">
          <button id="vr-mode-simple-btn" style="
            width: 200px;
            padding: 30px;
            background: linear-gradient(135deg, #22c55e, #16a34a);
            border: none;
            border-radius: 20px;
            color: white;
            cursor: pointer;
            transition: transform 0.2s;
          ">
            <div style="font-size: 48px; margin-bottom: 15px;">🎯</div>
            <div style="font-size: 20px; font-weight: bold; margin-bottom: 10px;">Simple Mode</div>
            <div style="font-size: 12px; opacity: 0.9;">Clean, minimal UI<br>Essential features only</div>
          </button>
          
          <button id="vr-mode-advanced-btn" style="
            width: 200px;
            padding: 30px;
            background: linear-gradient(135deg, #6b7280, #4b5563);
            border: none;
            border-radius: 20px;
            color: white;
            cursor: pointer;
            transition: transform 0.2s;
          ">
            <div style="font-size: 48px; margin-bottom: 15px;">🎛️</div>
            <div style="font-size: 20px; font-weight: bold; margin-bottom: 10px;">Advanced Mode</div>
            <div style="font-size: 12px; opacity: 0.9;">Full feature set<br>160+ VR features</div>
          </button>
        </div>
        
        <p style="color: #666; margin-top: 30px; font-size: 12px;">You can change this anytime using the mode button</p>
      `;
      
      document.body.appendChild(selector);
      
      selector.querySelector('#vr-mode-simple-btn').onclick = () => {
        this.setMode('simple');
        selector.remove();
      };
      
      selector.querySelector('#vr-mode-advanced-btn').onclick = () => {
        this.setMode('advanced');
        selector.remove();
      };
    },
    
    categorizeButtons() {
      // Get all buttons and categorize them
      const allButtons = Array.from(document.querySelectorAll('button, [role="button"]'));
      
      allButtons.forEach(btn => {
        const id = btn.id || '';
        const classes = btn.className || '';
        
        // Simple mode buttons (always visible)
        if (
          id.includes('hub') ||
          id.includes('back') ||
          id.includes('menu') ||
          id.includes('reset') ||
          classes.includes('primary') ||
          btn.textContent.includes('ENTER') ||
          id === 'vr-mode-toggle'
        ) {
          this.simpleButtons.push(btn);
          btn.dataset.vrMode = 'simple';
        }
        // Advanced mode buttons (hidden in simple mode)
        else if (
          id.includes('set') ||
          id.includes('quick') ||
          id.includes('clipboard') ||
          id.includes('gesture') ||
          id.includes('haptic') ||
          id.includes('profiler') ||
          id.includes('bookmark') ||
          id.includes('note') ||
          id.includes('pet') ||
          id.includes('weather-widget') ||
          id.includes('notifications') ||
          id.includes('shortcuts') ||
          id.includes('ambient') ||
          id.includes('fireworks') ||
          id.includes('celebration') ||
          classes.includes('advanced') ||
          btn.style.position === 'fixed' && !btn.dataset.vrMode
        ) {
          this.advancedButtons.push(btn);
          btn.dataset.vrMode = 'advanced';
        }
      });
      
      console.log('[VR Mode] Simple buttons:', this.simpleButtons.length);
      console.log('[VR Mode] Advanced buttons:', this.advancedButtons.length);
    },
    
    toggleMode() {
      this.mode = this.mode === 'simple' ? 'advanced' : 'simple';
      this.setMode(this.mode);
    },
    
    setMode(mode) {
      this.mode = mode;
      localStorage.setItem('vr-ui-mode', mode);
      this.applyMode();
      this.updateToggleAppearance();
      
      // Show toast
      this.showToast(mode === 'simple' ? '🎯 Simple Mode: Clean UI' : '🎛️ Advanced Mode: All Features');
      
      console.log('[VR Mode] Switched to:', mode);
    },
    
    applyMode() {
      if (this.mode === 'simple') {
        // Hide advanced buttons
        this.advancedButtons.forEach(btn => {
          btn.style.display = 'none';
        });
        
        // Show simple buttons
        this.simpleButtons.forEach(btn => {
          btn.style.display = '';
        });
      } else {
        // Show all buttons
        this.advancedButtons.forEach(btn => {
          btn.style.display = '';
        });
        this.simpleButtons.forEach(btn => {
          btn.style.display = '';
        });
      }
    },
    
    updateToggleAppearance() {
      const toggle = document.getElementById('vr-mode-toggle');
      const indicator = document.getElementById('vr-mode-indicator');
      
      if (toggle) {
        toggle.innerHTML = this.mode === 'simple' ? '🎯' : '🎛️';
        toggle.title = this.mode === 'simple' ? 'Switch to Advanced Mode' : 'Switch to Simple Mode';
        toggle.style.background = this.mode === 'simple' 
          ? 'linear-gradient(135deg, #22c55e, #16a34a)' 
          : 'linear-gradient(135deg, #6b7280, #4b5563)';
      }
      
      if (indicator) {
        indicator.textContent = this.mode === 'simple' ? 'Simple Mode' : 'Advanced Mode';
        indicator.style.color = this.mode === 'simple' ? '#22c55e' : '#6b7280';
      }
    },
    
    showToast(message) {
      const toast = document.createElement('div');
      toast.style.cssText = `
        position: fixed;
        top: 100px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(10,10,20,0.95);
        color: white;
        padding: 15px 30px;
        border-radius: 25px;
        font-size: 14px;
        z-index: 100001;
        animation: fadeInOut 2s ease;
      `;
      toast.textContent = message;
      
      const style = document.createElement('style');
      style.textContent = `
        @keyframes fadeInOut {
          0% { opacity: 0; transform: translateX(-50%) translateY(-20px); }
          20% { opacity: 1; transform: translateX(-50%) translateY(0); }
          80% { opacity: 1; transform: translateX(-50%) translateY(0); }
          100% { opacity: 0; transform: translateX(-50%) translateY(-20px); }
        }
      `;
      document.head.appendChild(style);
      document.body.appendChild(toast);
      
      setTimeout(() => toast.remove(), 2000);
    }
  };
  
  // Expose globally
  window.VRModeToggle = VRModeToggle;
  
  // Initialize after page loads
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => VRModeToggle.init());
  } else {
    // Delay to let other buttons load first
    setTimeout(() => VRModeToggle.init(), 2000);
  }
})();
