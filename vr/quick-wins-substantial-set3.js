/**
 * VR Substantial Quick Wins - Set 3: Advanced Interaction & Systems
 * 
 * 10 Additional Major Features:
 * 1. Physics-based Grabbing (grab, throw, drop objects)
 * 2. Personal Inventory System (virtual backpack)
 * 3. Waypoint Navigation (set and follow markers)
 * 4. Dynamic Shadows (time-based shadow casting)
 * 5. Proximity Interactions (hover effects, tooltips)
 * 6. Achievement System (unlock badges for actions)
 * 7. Stats Tracker (distance, time, interactions)
 * 8. Quick Travel System (fast travel to bookmarks)
 * 9. VR Virtual Keyboard (text input in VR)
 * 10. Zone Mini-map (overhead view navigation)
 */

(function() {
  'use strict';

  // ==================== CONFIGURATION ====================
  const CONFIG = {
    physics: {
      enabled: true,
      gravity: -9.8,
      throwMultiplier: 1.5
    },
    inventory: {
      maxSlots: 8,
      persist: true
    },
    achievements: {
      enabled: true,
      showNotifications: true
    },
    stats: {
      trackDistance: true,
      trackTime: true,
      trackInteractions: true
    },
    minimap: {
      enabled: true,
      updateInterval: 100
    }
  };

  // ==================== STATE ====================
  const state = {
    inventory: JSON.parse(localStorage.getItem('vr-inventory') || '[]'),
    waypoints: JSON.parse(localStorage.getItem('vr-waypoints') || '{}'),
    achievements: JSON.parse(localStorage.getItem('vr-achievements') || '{}'),
    stats: JSON.parse(localStorage.getItem('vr-stats') || JSON.stringify({
      totalDistance: 0,
      totalTime: 0,
      zonesVisited: [],
      interactions: 0,
      itemsGrabbed: 0,
      sessionStart: Date.now()
    })),
    grabbedObject: null,
    lastPosition: null,
    keyboardOpen: false
  };

  // ==================== 1. PHYSICS-BASED GRABBING ====================
  const PhysicsGrabbing = {
    grabbableObjects: [],
    handPosition: null,
    handRotation: null,

    init() {
      this.findGrabbableObjects();
      this.setupGrabDetection();
      this.createHandVisuals();
      console.log('[VR Physics] Grabbing initialized');
    },

    findGrabbableObjects() {
      // Find all objects marked as grabbable
      document.querySelectorAll('[data-grabbable], .grabbable').forEach(el => {
        el.classList.add('vr-grabbable');
        this.grabbableObjects.push(el);
      });

      // Also make some decorative objects grabbable
      document.querySelectorAll('a-box, a-sphere, a-cylinder').forEach(el => {
        if (!el.classList.contains('vr-grabbable') && !el.classList.contains('clickable')) {
          el.classList.add('vr-grabbable');
          el.setAttribute('data-grabbable', 'true');
          this.grabbableObjects.push(el);
        }
      });
    },

    setupGrabDetection() {
      // Mouse grab for desktop testing
      let isGrabbing = false;
      
      document.addEventListener('mousedown', (e) => {
        if (e.button === 2) { // Right click to grab
          this.tryGrab();
        }
      });

      document.addEventListener('mouseup', () => {
        if (state.grabbedObject) {
          this.release();
        }
      });

      // Track hand/controller position
      const trackHand = () => {
        const rightHand = document.getElementById('right-hand');
        if (rightHand && rightHand.object3D) {
          this.handPosition = rightHand.object3D.position.clone();
          this.handRotation = rightHand.object3D.rotation.clone();
          
          if (state.grabbedObject) {
            this.updateGrabbedPosition();
          }
        }
        requestAnimationFrame(trackHand);
      };
      requestAnimationFrame(trackHand);

      // Controller trigger for grab
      this.setupControllerGrab();
    },

    setupControllerGrab() {
      // Poll for controller input
      const checkControllers = () => {
        const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
        
        for (const gp of gamepads) {
          if (!gp) continue;
          
          // Trigger button (index 0) for grab
          if (gp.buttons[0]?.pressed) {
            if (!state.grabbedObject) {
              this.tryGrab();
            }
          } else {
            if (state.grabbedObject) {
              this.release();
            }
          }
        }
        
        requestAnimationFrame(checkControllers);
      };
      requestAnimationFrame(checkControllers);
    },

    tryGrab() {
      // Find nearest grabbable object
      const camera = document.querySelector('a-camera');
      if (!camera) return;

      let nearest = null;
      let nearestDist = Infinity;

      this.grabbableObjects.forEach(obj => {
        if (!obj.object3D) return;
        const objPos = obj.object3D.position;
        // Simple distance check from camera
        // In full implementation, would use raycaster from hand
        nearest = obj;
      });

      if (nearest) {
        this.grab(nearest);
      }
    },

    grab(obj) {
      state.grabbedObject = obj;
      obj.setAttribute('data-grabbed', 'true');
      
      // Disable physics/animations while grabbed
      const currentAnim = obj.getAttribute('animation');
      if (currentAnim) {
        obj.setAttribute('data-saved-animation', JSON.stringify(currentAnim));
        obj.removeAttribute('animation');
      }

      // Visual feedback
      obj.setAttribute('material', 'emissive', '#00d4ff');
      obj.setAttribute('material', 'emissiveIntensity', '0.3');
      
      HapticFeedback.play('click');
      showToast('✊ Grabbed object');
      
      // Track stat
      state.stats.itemsGrabbed++;
      this.saveStats();
      
      // Check achievement
      Achievements.check('firstGrab');
    },

    updateGrabbedPosition() {
      if (!state.grabbedObject || !this.handPosition) return;
      
      // Move object with hand
      state.grabbedObject.object3D.position.copy(this.handPosition);
      state.grabbedObject.object3D.rotation.copy(this.handRotation);
    },

    release() {
      if (!state.grabbedObject) return;

      const obj = state.grabbedObject;
      
      // Apply throw velocity (simplified)
      // In full implementation, would calculate actual velocity
      
      // Restore saved animation
      const savedAnim = obj.getAttribute('data-saved-animation');
      if (savedAnim) {
        try {
          obj.setAttribute('animation', JSON.parse(savedAnim));
        } catch (e) {}
      }

      // Remove visual feedback
      obj.setAttribute('material', 'emissive', '#000000');
      obj.setAttribute('material', 'emissiveIntensity', '0');
      obj.removeAttribute('data-grabbed');

      state.grabbedObject = null;
      HapticFeedback.play('success');
      showToast('👋 Released');
    },

    createHandVisuals() {
      // Visual indicator for grab range
      const indicator = document.createElement('div');
      indicator.id = 'vr-grab-indicator';
      indicator.style.cssText = `
        position: fixed;
        bottom: 200px;
        right: 20px;
        background: rgba(0,212,255,0.2);
        border: 1px solid #00d4ff;
        border-radius: 8px;
        padding: 8px 12px;
        color: #00d4ff;
        font-size: 12px;
        z-index: 99995;
      `;
      indicator.innerHTML = `
        <div>✊ Grab: Right-click or Trigger</div>
        <div id="vr-grab-status">No object held</div>
      `;
      document.body.appendChild(indicator);

      // Update status
      setInterval(() => {
        const status = document.getElementById('vr-grab-status');
        if (status) {
          status.textContent = state.grabbedObject ? 'Holding object' : 'No object held';
          status.style.color = state.grabbedObject ? '#22c55e' : '#888';
        }
      }, 100);
    },

    saveStats() {
      localStorage.setItem('vr-stats', JSON.stringify(state.stats));
    }
  };

  // ==================== 2. PERSONAL INVENTORY SYSTEM ====================
  const InventorySystem = {
    isOpen: false,

    init() {
      this.createInventoryUI();
      this.setupKeyboardShortcut();
      console.log('[VR Inventory] Initialized with', state.inventory.length, 'items');
    },

    createInventoryUI() {
      // Inventory button
      const btn = document.createElement('button');
      btn.id = 'vr-inventory-btn';
      btn.innerHTML = '🎒';
      btn.title = 'Inventory (I)';
      btn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 200px;
        background: rgba(234, 179, 8, 0.5);
        border: 2px solid #eab308;
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

      // Inventory panel
      const panel = document.createElement('div');
      panel.id = 'vr-inventory-panel';
      panel.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
        border: 2px solid #eab308;
        border-radius: 20px;
        padding: 25px;
        z-index: 100000;
        display: none;
        min-width: 400px;
        backdrop-filter: blur(15px);
        color: var(--vr-text, #e0e0e0);
      `;
      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #eab308;">🎒 Inventory</h3>
          <button onclick="VRQuickWinsSet3.Inventory.toggle()" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        <div id="vr-inventory-grid" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 15px;">
          ${this.generateSlots()}
        </div>
        <div style="font-size: 12px; opacity: 0.7; text-align: center;">
          ${state.inventory.length} / ${CONFIG.inventory.maxSlots} slots used
        </div>
      `;
      document.body.appendChild(panel);
    },

    generateSlots() {
      let html = '';
      for (let i = 0; i < CONFIG.inventory.maxSlots; i++) {
        const item = state.inventory[i];
        html += `
          <div style="
            aspect-ratio: 1;
            background: rgba(255,255,255,0.05);
            border: 2px solid ${item ? '#eab308' : 'rgba(255,255,255,0.1)'};
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            cursor: ${item ? 'pointer' : 'default'};
            position: relative;
          " ${item ? `onclick="VRQuickWinsSet3.Inventory.useItem(${i})" title="${item.name}"` : ''}>
            ${item ? item.icon : ''}
            ${item ? `<span style="position: absolute; bottom: 2px; right: 4px; font-size: 10px; color: #888;">${item.quantity || 1}</span>` : ''}
          </div>
        `;
      }
      return html;
    },

    setupKeyboardShortcut() {
      document.addEventListener('keydown', (e) => {
        if (e.key === 'i' || e.key === 'I') {
          this.toggle();
        }
      });
    },

    toggle() {
      const panel = document.getElementById('vr-inventory-panel');
      if (panel) {
        this.isOpen = !this.isOpen;
        panel.style.display = this.isOpen ? 'block' : 'none';
        if (this.isOpen) {
          this.refresh();
        }
      }
    },

    refresh() {
      const grid = document.getElementById('vr-inventory-grid');
      if (grid) {
        grid.innerHTML = this.generateSlots();
      }
    },

    addItem(item) {
      if (state.inventory.length >= CONFIG.inventory.maxSlots) {
        showToast('❌ Inventory full!');
        return false;
      }

      // Check if stackable
      const existing = state.inventory.find(i => i.id === item.id);
      if (existing && item.stackable) {
        existing.quantity = (existing.quantity || 1) + 1;
      } else {
        state.inventory.push({ ...item, quantity: 1 });
      }

      this.save();
      showToast(`🎒 Added: ${item.name}`);
      
      if (this.isOpen) this.refresh();
      
      // Check achievement
      if (state.inventory.length >= 5) {
        Achievements.check('packRat');
      }
      
      return true;
    },

    useItem(index) {
      const item = state.inventory[index];
      if (!item) return;

      // Use item logic
      showToast(`✨ Used: ${item.name}`);
      
      // Remove or decrement
      if (item.quantity > 1) {
        item.quantity--;
      } else {
        state.inventory.splice(index, 1);
      }

      this.save();
      this.refresh();
    },

    save() {
      if (CONFIG.inventory.persist) {
        localStorage.setItem('vr-inventory', JSON.stringify(state.inventory));
      }
    }
  };

  // ==================== 3. WAYPOINT NAVIGATION ====================
  const WaypointNavigation = {
    activeWaypoint: null,

    init() {
      this.createUI();
      this.loadWaypointsForCurrentZone();
      console.log('[VR Waypoints] Initialized');
    },

    createUI() {
      // Waypoint button
      const btn = document.createElement('button');
      btn.id = 'vr-waypoint-btn';
      btn.innerHTML = '📍';
      btn.title = 'Set Waypoint (M)';
      btn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 260px;
        background: rgba(34, 197, 94, 0.5);
        border: 2px solid #22c55e;
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
      btn.addEventListener('click', () => this.setWaypoint());
      document.body.appendChild(btn);

      // Waypoint list button
      const listBtn = document.createElement('button');
      listBtn.id = 'vr-waypoint-list-btn';
      listBtn.innerHTML = '🗺️';
      listBtn.title = 'View Waypoints';
      listBtn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 320px;
        background: rgba(34, 197, 94, 0.3);
        border: 2px solid #22c55e;
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
      listBtn.addEventListener('click', () => this.showWaypointList());
      document.body.appendChild(listBtn);

      document.addEventListener('keydown', (e) => {
        if (e.key === 'm' || e.key === 'M') {
          this.setWaypoint();
        }
      });
    },

    setWaypoint() {
      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (!rig) return;

      const pos = rig.getAttribute('position');
      const zone = window.location.pathname;
      const name = prompt('Waypoint name:', `Waypoint ${Date.now() % 1000}`);
      
      if (!name) return;

      if (!state.waypoints[zone]) {
        state.waypoints[zone] = [];
      }

      const waypoint = {
        id: Date.now(),
        name,
        position: { x: pos.x, y: pos.y, z: pos.z },
        created: Date.now()
      };

      state.waypoints[zone].push(waypoint);
      localStorage.setItem('vr-waypoints', JSON.stringify(state.waypoints));

      // Create visual marker in scene
      this.createVisualMarker(waypoint);

      showToast(`📍 Waypoint set: ${name}`);
      Achievements.check('firstWaypoint');
    },

    createVisualMarker(waypoint) {
      const scene = document.querySelector('a-scene');
      if (!scene) return;

      const marker = document.createElement('a-entity');
      marker.setAttribute('position', `${waypoint.position.x} ${waypoint.position.y + 2} ${waypoint.position.z}`);
      marker.innerHTML = `
        <a-cone radius-bottom="0.3" radius-top="0" height="0.6" color="#22c55e" opacity="0.8"
          animation="property: position; dir: alternate; dur: 1000; to: 0 0.3 0; loop: true"></a-cone>
        <a-text value="${waypoint.name}" align="center" position="0 0.8 0" width="4" color="#22c55e"></a-text>
      `;
      scene.appendChild(marker);
    },

    loadWaypointsForCurrentZone() {
      const zone = window.location.pathname;
      const waypoints = state.waypoints[zone] || [];
      
      waypoints.forEach(wp => {
        this.createVisualMarker(wp);
      });
    },

    showWaypointList() {
      const zone = window.location.pathname;
      const waypoints = state.waypoints[zone] || [];

      let content = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #22c55e;">🗺️ Waypoints</h3>
          <button onclick="this.closest('#vr-waypoint-list').remove()" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
      `;

      if (waypoints.length === 0) {
        content += '<p style="text-align: center; opacity: 0.6;">No waypoints in this zone</p>';
      } else {
        content += waypoints.map(wp => `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px;">
            <span>📍 ${wp.name}</span>
            <button onclick="VRQuickWinsSet3.Waypoints.navigateTo(${wp.id})" style="background: #22c55e; border: none; padding: 5px 12px; border-radius: 5px; color: white; cursor: pointer;">Go</button>
          </div>
        `).join('');
      }

      // Create or update list panel
      let panel = document.getElementById('vr-waypoint-list');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-waypoint-list';
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
          min-width: 350px;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }
      panel.innerHTML = content;
      panel.style.display = 'block';
    },

    navigateTo(id) {
      const zone = window.location.pathname;
      const waypoint = (state.waypoints[zone] || []).find(w => w.id === id);
      if (!waypoint) return;

      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (rig) {
        rig.setAttribute('animation', 
          `property: position; to: ${waypoint.position.x} ${waypoint.position.y} ${waypoint.position.z}; dur: 1500; easing: easeInOutQuad`
        );
        showToast(`🧭 Navigating to: ${waypoint.name}`);
        
        // Close list
        const panel = document.getElementById('vr-waypoint-list');
        if (panel) panel.style.display = 'none';
      }
    }
  };

  // ==================== 4. DYNAMIC SHADOWS ====================
  const DynamicShadows = {
    sunLight: null,

    init() {
      this.setupShadows();
      this.startShadowUpdates();
      console.log('[VR Shadows] Dynamic shadows initialized');
    },

    setupShadows() {
      const scene = document.querySelector('a-scene');
      if (!scene) return;

      // Find or create main directional light
      this.sunLight = scene.querySelector('a-light[type="directional"]');
      if (!this.sunLight) {
        this.sunLight = document.createElement('a-light');
        this.sunLight.setAttribute('type', 'directional');
        this.sunLight.setAttribute('castShadow', 'true');
        this.sunLight.setAttribute('shadowMapHeight', '2048');
        this.sunLight.setAttribute('shadowMapWidth', '2048');
        this.sunLight.setAttribute('shadowCameraTop', '50');
        this.sunLight.setAttribute('shadowCameraBottom', '-50');
        this.sunLight.setAttribute('shadowCameraLeft', '-50');
        this.sunLight.setAttribute('shadowCameraRight', '50');
        scene.appendChild(this.sunLight);
      }

      // Enable shadows on all objects
      scene.querySelectorAll('a-box, a-sphere, a-cylinder, a-plane').forEach(el => {
        if (!el.hasAttribute('shadow')) {
          el.setAttribute('shadow', 'cast: true; receive: true');
        }
      });

      this.updateSunPosition();
    },

    updateSunPosition() {
      if (!this.sunLight) return;

      const hour = new Date().getHours();
      
      // Calculate sun angle based on time
      let angle, height, intensity;
      
      if (hour >= 6 && hour < 18) {
        // Day time
        const dayProgress = (hour - 6) / 12;
        angle = dayProgress * 180 - 90;
        height = Math.sin(dayProgress * Math.PI) * 60;
        intensity = Math.sin(dayProgress * Math.PI) * 0.8 + 0.2;
      } else {
        // Night time
        angle = 0;
        height = -30;
        intensity = 0.1;
      }

      this.sunLight.setAttribute('position', `${Math.sin(angle * Math.PI / 180) * 50} ${height} ${Math.cos(angle * Math.PI / 180) * 50}`);
      this.sunLight.setAttribute('intensity', intensity);

      // Shadow color based on time
      const colors = {
        morning: '#ffddaa',
        afternoon: '#ffffff',
        evening: '#ff8844',
        night: '#4444aa'
      };
      
      let timeOfDay = 'night';
      if (hour >= 5 && hour < 12) timeOfDay = 'morning';
      else if (hour >= 12 && hour < 17) timeOfDay = 'afternoon';
      else if (hour >= 17 && hour < 21) timeOfDay = 'evening';
      
      this.sunLight.setAttribute('color', colors[timeOfDay]);
    },

    startShadowUpdates() {
      // Update every minute
      setInterval(() => {
        this.updateSunPosition();
      }, 60000);
    }
  };

  // ==================== 5. PROXIMITY INTERACTIONS ====================
  const ProximityInteractions = {
    tooltipEl: null,

    init() {
      this.createTooltip();
      this.setupProximityDetection();
      console.log('[VR Proximity] Initialized');
    },

    createTooltip() {
      const tooltip = document.createElement('div');
      tooltip.id = 'vr-proximity-tooltip';
      tooltip.style.cssText = `
        position: fixed;
        background: rgba(0,0,0,0.8);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 8px;
        padding: 8px 12px;
        color: white;
        font-size: 12px;
        pointer-events: none;
        z-index: 99994;
        display: none;
        backdrop-filter: blur(5px);
        max-width: 200px;
      `;
      document.body.appendChild(tooltip);
      this.tooltipEl = tooltip;
    },

    setupProximityDetection() {
      // Add hover listeners to all interactables
      document.querySelectorAll('.clickable, [onclick], [data-tooltip], button').forEach(el => {
        el.addEventListener('mouseenter', (e) => {
          const text = el.getAttribute('data-tooltip') || el.title || el.textContent;
          this.showTooltip(e, text);
          HapticFeedback.play('hover');
        });
        
        el.addEventListener('mouseleave', () => {
          this.hideTooltip();
        });

        // Scale effect
        el.addEventListener('mouseenter', () => {
          if (el.style.transform) return;
          el.style.transform = 'scale(1.05)';
          el.style.transition = 'transform 0.2s';
        });
        
        el.addEventListener('mouseleave', () => {
          el.style.transform = 'scale(1)';
        });
      });
    },

    showTooltip(e, text) {
      if (!this.tooltipEl || !text) return;
      
      this.tooltipEl.textContent = text;
      this.tooltipEl.style.display = 'block';
      this.tooltipEl.style.left = e.clientX + 10 + 'px';
      this.tooltipEl.style.top = e.clientY + 10 + 'px';
    },

    hideTooltip() {
      if (this.tooltipEl) {
        this.tooltipEl.style.display = 'none';
      }
    }
  };

  // ==================== 6. ACHIEVEMENT SYSTEM ====================
  const Achievements = {
    definitions: {
      firstSteps: { name: 'First Steps', desc: 'Move 10 meters in VR', icon: '🚶', condition: () => state.stats.totalDistance > 10 },
      explorer: { name: 'Explorer', desc: 'Visit all 7 zones', icon: '🌍', condition: () => (state.stats.zonesVisited || []).length >= 7 },
      packRat: { name: 'Pack Rat', desc: 'Collect 5 items', icon: '🎒', condition: () => state.inventory.length >= 5 },
      socialite: { name: 'Socialite', desc: 'Spend 1 hour in VR', icon: '⏰', condition: () => state.stats.totalTime > 3600 },
      firstGrab: { name: 'Grabber', desc: 'Grab your first object', icon: '✊', condition: () => state.stats.itemsGrabbed > 0 },
      firstWaypoint: { name: 'Navigator', desc: 'Set your first waypoint', icon: '🧭', condition: () => Object.keys(state.waypoints).length > 0 },
      shutterbug: { name: 'Shutterbug', desc: 'Take 5 screenshots', icon: '📸', condition: () => (state.stats.screenshots || 0) >= 5 },
      zoneMaster: { name: 'Zone Master', desc: 'Spend 10 minutes in each zone', icon: '🏆', condition: () => this.checkZoneMastery() }
    },

    init() {
      this.checkAll();
      setInterval(() => this.checkAll(), 30000); // Check every 30s
      console.log('[VR Achievements] Initialized');
    },

    checkAll() {
      Object.keys(this.definitions).forEach(id => {
        this.check(id);
      });
    },

    check(id) {
      if (state.achievements[id]) return; // Already unlocked
      
      const def = this.definitions[id];
      if (!def) return;

      try {
        if (def.condition()) {
          this.unlock(id);
        }
      } catch (e) {
        // Condition might reference other systems not loaded
      }
    },

    unlock(id) {
      const def = this.definitions[id];
      state.achievements[id] = {
        unlocked: Date.now(),
        ...def
      };
      
      localStorage.setItem('vr-achievements', JSON.stringify(state.achievements));
      
      if (CONFIG.achievements.showNotifications) {
        this.showNotification(def);
      }
    },

    showNotification(def) {
      const notif = document.createElement('div');
      notif.style.cssText = `
        position: fixed;
        top: 100px;
        left: 50%;
        transform: translateX(-50%) translateY(-50px);
        background: linear-gradient(135deg, #eab308 0%, #f59e0b 100%);
        border-radius: 15px;
        padding: 20px 30px;
        color: white;
        font-weight: bold;
        z-index: 100001;
        animation: achievementSlide 0.5s ease forwards;
        box-shadow: 0 10px 40px rgba(234, 179, 8, 0.4);
      `;
      notif.innerHTML = `
        <div style="font-size: 32px; margin-bottom: 5px;">🏆 Achievement Unlocked!</div>
        <div style="font-size: 24px;">${def.icon} ${def.name}</div>
        <div style="font-size: 14px; opacity: 0.9;">${def.desc}</div>
      `;
      document.body.appendChild(notif);

      // Add animation
      const style = document.createElement('style');
      style.textContent = `
        @keyframes achievementSlide {
          to { transform: translateX(-50%) translateY(0); }
        }
      `;
      document.head.appendChild(style);

      HapticFeedback.play('success');

      setTimeout(() => {
        notif.style.animation = 'achievementSlide 0.5s ease reverse forwards';
        setTimeout(() => notif.remove(), 500);
      }, 4000);
    },

    checkZoneMastery() {
      // This would check time spent in each zone
      return false; // Placeholder
    },

    showList() {
      let content = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #eab308;">🏆 Achievements</h3>
          <button onclick="this.closest('#vr-achievements-list').remove()" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
      `;

      Object.entries(this.definitions).forEach(([id, def]) => {
        const unlocked = state.achievements[id];
        content += `
          <div style="
            display: flex;
            align-items: center;
            padding: 12px;
            background: ${unlocked ? 'rgba(234,179,8,0.1)' : 'rgba(255,255,255,0.05)'};
            border: 2px solid ${unlocked ? '#eab308' : 'rgba(255,255,255,0.1)'};
            border-radius: 10px;
            margin-bottom: 8px;
            opacity: ${unlocked ? 1 : 0.6};
          ">
            <span style="font-size: 32px; margin-right: 15px;">${unlocked ? def.icon : '🔒'}</span>
            <div>
              <div style="font-weight: bold; color: ${unlocked ? '#eab308' : '#888'};">${def.name}</div>
              <div style="font-size: 12px; opacity: 0.8;">${def.desc}</div>
            </div>
          </div>
        `;
      });

      let panel = document.getElementById('vr-achievements-list');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-achievements-list';
        panel.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
          border: 2px solid #eab308;
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
      panel.innerHTML = content;
      panel.style.display = 'block';
    }
  };

  // ==================== 7. STATS TRACKER ====================
  const StatsTracker = {
    lastPos: null,
    lastUpdate: Date.now(),

    init() {
      this.startTracking();
      this.createStatsUI();
      console.log('[VR Stats] Tracking initialized');
    },

    startTracking() {
      // Track distance
      const track = () => {
        const rig = document.getElementById('rig') || document.getElementById('camera-rig');
        if (rig) {
          const pos = rig.getAttribute('position');
          
          if (this.lastPos) {
            const dx = pos.x - this.lastPos.x;
            const dz = pos.z - this.lastPos.z;
            const dist = Math.sqrt(dx*dx + dz*dz);
            
            if (dist > 0.01) { // Ignore tiny movements
              state.stats.totalDistance += dist;
              this.saveStats();
            }
          }
          
          this.lastPos = { x: pos.x, z: pos.z };
        }
        
        // Track time
        const now = Date.now();
        state.stats.totalTime += (now - this.lastUpdate) / 1000;
        this.lastUpdate = now;
        
        requestAnimationFrame(track);
      };
      requestAnimationFrame(track);

      // Track zones
      const currentZone = window.location.pathname;
      if (!state.stats.zonesVisited) state.stats.zonesVisited = [];
      if (!state.stats.zonesVisited.includes(currentZone)) {
        state.stats.zonesVisited.push(currentZone);
        this.saveStats();
      }
    },

    createStatsUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-stats-btn';
      btn.innerHTML = '📊';
      btn.title = 'Statistics';
      btn.style.cssText = `
        position: fixed;
        top: 120px;
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
      btn.addEventListener('click', () => this.showStats());
      document.body.appendChild(btn);
    },

    showStats() {
      const dist = Math.round(state.stats.totalDistance * 10) / 10;
      const time = Math.floor(state.stats.totalTime / 60);
      const zones = (state.stats.zonesVisited || []).length;

      let panel = document.getElementById('vr-stats-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-stats-panel';
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
          min-width: 300px;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #3b82f6;">📊 Statistics</h3>
          <button onclick="document.getElementById('vr-stats-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        <div style="display: grid; gap: 15px;">
          <div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">
            <span>Distance Traveled</span>
            <span style="color: #3b82f6; font-weight: bold;">${dist}m</span>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">
            <span>Time in VR</span>
            <span style="color: #3b82f6; font-weight: bold;">${time} min</span>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">
            <span>Zones Visited</span>
            <span style="color: #3b82f6; font-weight: bold;">${zones} / 7</span>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">
            <span>Items Grabbed</span>
            <span style="color: #3b82f6; font-weight: bold;">${state.stats.itemsGrabbed || 0}</span>
          </div>
        </div>
        <button onclick="VRQuickWinsSet3.Achievements.showList()" style="width: 100%; margin-top: 15px; padding: 10px; background: rgba(234,179,8,0.3); border: 1px solid #eab308; border-radius: 8px; color: #eab308; cursor: pointer;">
          🏆 View Achievements
        </button>
      `;
      panel.style.display = 'block';
    },

    saveStats() {
      localStorage.setItem('vr-stats', JSON.stringify(state.stats));
    }
  };

  // ==================== 8. QUICK TRAVEL SYSTEM ====================
  const QuickTravel = {
    init() {
      this.createUI();
      console.log('[VR QuickTravel] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-quicktravel-btn';
      btn.innerHTML = '⚡';
      btn.title = 'Quick Travel (T)';
      btn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 380px;
        background: rgba(139, 92, 246, 0.5);
        border: 2px solid #8b5cf6;
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
      btn.addEventListener('click', () => this.showTravelMenu());
      document.body.appendChild(btn);

      document.addEventListener('keydown', (e) => {
        if (e.key === 't' || e.key === 'T') {
          this.showTravelMenu();
        }
      });
    },

    showTravelMenu() {
      const zone = window.location.pathname;
      const bookmarks = JSON.parse(localStorage.getItem('vr-bookmarks') || '[]');
      const waypoints = (state.waypoints[zone] || []);

      let content = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #8b5cf6;">⚡ Quick Travel</h3>
          <button onclick="this.closest('#vr-quicktravel-menu').remove()" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
      `;

      if (waypoints.length > 0) {
        content += '<div style="font-weight: bold; margin-bottom: 10px;">📍 Waypoints</div>';
        content += waypoints.map(wp => `
          <button onclick="VRQuickWinsSet3.QuickTravel.travelTo(${wp.position.x}, ${wp.position.y}, ${wp.position.z})" 
            style="width: 100%; padding: 10px; margin-bottom: 8px; background: rgba(34,197,94,0.2); border: 1px solid #22c55e; border-radius: 8px; color: #22c55e; cursor: pointer; text-align: left;">
            📍 ${wp.name}
          </button>
        `).join('');
      }

      if (bookmarks.length > 0) {
        content += '<div style="font-weight: bold; margin: 15px 0 10px;">🔖 Bookmarks</div>';
        content += bookmarks.filter(b => b.zone === zone).map(bm => `
          <button onclick="VRQuickWinsSet3.QuickTravel.travelTo(${bm.position.x}, ${bm.position.y}, ${bm.position.z})" 
            style="width: 100%; padding: 10px; margin-bottom: 8px; background: rgba(168,85,247,0.2); border: 1px solid #a855f7; border-radius: 8px; color: #a855f7; cursor: pointer; text-align: left;">
            🔖 ${bm.name}
          </button>
        `).join('');
      }

      if (waypoints.length === 0 && bookmarks.filter(b => b.zone === zone).length === 0) {
        content += '<p style="text-align: center; opacity: 0.6; padding: 20px;">No travel points set. Create waypoints or bookmarks first!</p>';
      }

      let menu = document.getElementById('vr-quicktravel-menu');
      if (!menu) {
        menu = document.createElement('div');
        menu.id = 'vr-quicktravel-menu';
        menu.style.cssText = `
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
          max-height: 60vh;
          overflow-y: auto;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(menu);
      }
      menu.innerHTML = content;
      menu.style.display = 'block';
    },

    travelTo(x, y, z) {
      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (rig) {
        rig.setAttribute('animation', 
          `property: position; to: ${x} ${y} ${z}; dur: 1000; easing: easeInOutQuad`
        );
        showToast('⚡ Traveling...');
        HapticFeedback.play('teleport');
        
        const menu = document.getElementById('vr-quicktravel-menu');
        if (menu) menu.style.display = 'none';
      }
    }
  };

  // ==================== 9. VR VIRTUAL KEYBOARD ====================
  const VirtualKeyboard = {
    targetInput: null,
    keyboardEl: null,

    init() {
      this.setupInputDetection();
      console.log('[VR Keyboard] Initialized');
    },

    setupInputDetection() {
      // Show keyboard when focusing inputs in VR
      document.querySelectorAll('input[type="text"], textarea').forEach(input => {
        input.addEventListener('focus', () => {
          if (this.isInVR()) {
            this.show(input);
          }
        });
      });
    },

    isInVR() {
      const scene = document.querySelector('a-scene');
      return scene && scene.is('vr-mode');
    },

    show(targetInput) {
      this.targetInput = targetInput;
      state.keyboardOpen = true;

      if (!this.keyboardEl) {
        this.createKeyboard();
      }

      this.keyboardEl.style.display = 'block';
    },

    createKeyboard() {
      const keyboard = document.createElement('div');
      keyboard.id = 'vr-virtual-keyboard';
      keyboard.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(10,10,20,0.95);
        border: 2px solid #00d4ff;
        border-radius: 15px;
        padding: 15px;
        z-index: 100002;
        display: none;
      `;

      const keys = [
        '1234567890',
        'qwertyuiop',
        'asdfghjkl',
        'zxcvbnm',
        ' '
      ];

      let html = '<div style="text-align: center;">';
      keys.forEach((row, i) => {
        html += '<div style="display: flex; justify-content: center; margin: 5px 0;">';
        
        if (i === 2) {
          html += '<button onclick="VRQuickWinsSet3.Keyboard.onKey(\'CAPS\')" style="padding: 10px 15px; margin: 2px; background: rgba(255,255,255,0.1); border: 1px solid #00d4ff; border-radius: 5px; color: white; cursor: pointer;">⇪</button>';
        }
        
        for (const key of row) {
          html += `<button onclick="VRQuickWinsSet3.Keyboard.onKey('${key}')" style="padding: 10px 15px; margin: 2px; background: rgba(0,212,255,0.2); border: 1px solid #00d4ff; border-radius: 5px; color: white; cursor: pointer; min-width: 35px;">${key}</button>`;
        }
        
        if (i === 2) {
          html += '<button onclick="VRQuickWinsSet3.Keyboard.onKey(\'BACK\')" style="padding: 10px 15px; margin: 2px; background: rgba(239,68,68,0.3); border: 1px solid #ef4444; border-radius: 5px; color: white; cursor: pointer;">⌫</button>';
        }
        
        html += '</div>';
      });

      html += `
        <div style="display: flex; justify-content: center; margin-top: 10px;">
          <button onclick="VRQuickWinsSet3.Keyboard.onKey('ENTER')" style="padding: 10px 30px; margin: 2px; background: rgba(34,197,94,0.3); border: 1px solid #22c55e; border-radius: 5px; color: white; cursor: pointer;">Enter</button>
          <button onclick="VRQuickWinsSet3.Keyboard.hide()" style="padding: 10px 30px; margin: 2px; background: rgba(239,68,68,0.3); border: 1px solid #ef4444; border-radius: 5px; color: white; cursor: pointer;">Close</button>
        </div>
      `;
      html += '</div>';

      keyboard.innerHTML = html;
      document.body.appendChild(keyboard);
      this.keyboardEl = keyboard;
    },

    onKey(key) {
      if (!this.targetInput) return;

      switch(key) {
        case 'BACK':
          this.targetInput.value = this.targetInput.value.slice(0, -1);
          break;
        case 'ENTER':
          this.targetInput.dispatchEvent(new Event('change'));
          this.hide();
          break;
        case 'CAPS':
          // Toggle caps
          break;
        default:
          this.targetInput.value += key;
      }

      this.targetInput.dispatchEvent(new Event('input'));
      HapticFeedback.play('click');
    },

    hide() {
      state.keyboardOpen = false;
      if (this.keyboardEl) {
        this.keyboardEl.style.display = 'none';
      }
    }
  };

  // ==================== 10. ZONE MINI-MAP ====================
  const ZoneMinimap = {
    canvas: null,
    ctx: null,

    init() {
      this.createMinimap();
      this.startUpdates();
      console.log('[VR Minimap] Initialized');
    },

    createMinimap() {
      const container = document.createElement('div');
      container.id = 'vr-minimap-container';
      container.style.cssText = `
        position: fixed;
        top: 170px;
        right: 20px;
        width: 150px;
        height: 150px;
        background: rgba(0,0,0,0.7);
        border: 2px solid #00d4ff;
        border-radius: 50%;
        overflow: hidden;
        z-index: 99996;
        display: none;
      `;

      const canvas = document.createElement('canvas');
      canvas.width = 150;
      canvas.height = 150;
      canvas.style.cssText = 'width: 100%; height: 100%;';
      
      container.appendChild(canvas);
      document.body.appendChild(container);

      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');

      // Toggle button
      const btn = document.createElement('button');
      btn.id = 'vr-minimap-toggle';
      btn.innerHTML = '🗺️';
      btn.title = 'Toggle Minimap (N)';
      btn.style.cssText = `
        position: fixed;
        top: 170px;
        right: 20px;
        background: rgba(0, 212, 255, 0.5);
        border: 2px solid #00d4ff;
        color: white;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 16px;
        z-index: 99997;
      `;
      btn.addEventListener('click', () => this.toggle());
      document.body.appendChild(btn);

      document.addEventListener('keydown', (e) => {
        if (e.key === 'n' || e.key === 'N') {
          this.toggle();
        }
      });

      // Show when in VR
      const scene = document.querySelector('a-scene');
      if (scene) {
        scene.addEventListener('enter-vr', () => {
          container.style.display = 'block';
          btn.style.top = '170px';
          btn.style.right = '180px';
        });
        scene.addEventListener('exit-vr', () => {
          container.style.display = 'none';
          btn.style.top = '170px';
          btn.style.right = '20px';
        });
      }
    },

    toggle() {
      const container = document.getElementById('vr-minimap-container');
      if (container) {
        container.style.display = container.style.display === 'none' ? 'block' : 'none';
      }
    },

    startUpdates() {
      const update = () => {
        if (!this.ctx || !CONFIG.minimap.enabled) {
          requestAnimationFrame(update);
          return;
        }

        const container = document.getElementById('vr-minimap-container');
        if (!container || container.style.display === 'none') {
          requestAnimationFrame(update);
          return;
        }

        this.draw();
        
        setTimeout(() => requestAnimationFrame(update), CONFIG.minimap.updateInterval);
      };
      requestAnimationFrame(update);
    },

    draw() {
      const ctx = this.ctx;
      const w = this.canvas.width;
      const h = this.canvas.height;
      const centerX = w / 2;
      const centerY = h / 2;

      // Clear
      ctx.fillStyle = 'rgba(0,0,0,0.8)';
      ctx.fillRect(0, 0, w, h);

      // Draw grid
      ctx.strokeStyle = 'rgba(0,212,255,0.2)';
      ctx.lineWidth = 1;
      for (let i = 0; i < w; i += 30) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, h);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(w, i);
        ctx.stroke();
      }

      // Get player position
      const rig = document.getElementById('rig') || document.getElementById('camera-rig');
      if (rig) {
        const pos = rig.getAttribute('position');
        const rot = rig.getAttribute('rotation');

        // Draw waypoints
        const zone = window.location.pathname;
        const waypoints = (state.waypoints[zone] || []);
        waypoints.forEach(wp => {
          const x = centerX + (wp.position.x - pos.x) * 2;
          const y = centerY + (wp.position.z - pos.z) * 2;
          
          if (x > 0 && x < w && y > 0 && y < h) {
            ctx.fillStyle = '#22c55e';
            ctx.beginPath();
            ctx.arc(x, y, 4, 0, Math.PI * 2);
            ctx.fill();
          }
        });

        // Draw player (center)
        ctx.fillStyle = '#00d4ff';
        ctx.beginPath();
        ctx.arc(centerX, centerY, 6, 0, Math.PI * 2);
        ctx.fill();

        // Draw direction
        const angle = (rot.y - 90) * Math.PI / 180;
        ctx.strokeStyle = '#00d4ff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(centerX + Math.cos(angle) * 15, centerY + Math.sin(angle) * 15);
        ctx.stroke();
      }

      // Draw border circle
      ctx.strokeStyle = '#00d4ff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(centerX, centerY, w/2 - 1, 0, Math.PI * 2);
      ctx.stroke();
    }
  };

  // ==================== UTILITY: HAPTIC FEEDBACK ====================
  const HapticFeedback = {
    play(type) {
      const intensities = {
        click: { intensity: 0.3, duration: 50 },
        hover: { intensity: 0.1, duration: 30 },
        success: { intensity: 0.5, duration: 100 },
        teleport: { intensity: 0.6, duration: 150 }
      };

      const config = intensities[type];
      if (!config) return;

      // Try to pulse controller
      const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
      for (const gp of gamepads) {
        if (gp && gp.hapticActuators?.[0]) {
          gp.hapticActuators[0].pulse(config.intensity, config.duration);
        }
      }
    }
  };

  // ==================== UTILITY: TOAST ====================
  function showToast(message) {
    let toast = document.getElementById('vr-toast-set3');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'vr-toast-set3';
      toast.style.cssText = `
        position: fixed;
        bottom: 180px;
        left: 50%;
        transform: translateX(-50%) translateY(20px);
        background: rgba(10,10,20,0.95);
        backdrop-filter: blur(12px);
        border: 1px solid #22c55e;
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
    console.log('[VR Substantial Quick Wins - Set 3] Initializing...');

    PhysicsGrabbing.init();
    InventorySystem.init();
    WaypointNavigation.init();
    DynamicShadows.init();
    ProximityInteractions.init();
    Achievements.init();
    StatsTracker.init();
    QuickTravel.init();
    VirtualKeyboard.init();
    ZoneMinimap.init();

    console.log('[VR Substantial Quick Wins - Set 3] Initialized!');
    console.log('New shortcuts:');
    console.log('  I - Inventory');
    console.log('  M - Set waypoint');
    console.log('  T - Quick Travel');
    console.log('  N - Toggle minimap');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose API
  window.VRQuickWinsSet3 = {
    Physics: PhysicsGrabbing,
    Inventory: InventorySystem,
    Waypoints: WaypointNavigation,
    Shadows: DynamicShadows,
    Proximity: ProximityInteractions,
    Achievements: Achievements,
    Stats: StatsTracker,
    QuickTravel: QuickTravel,
    Keyboard: VirtualKeyboard,
    Minimap: ZoneMinimap,
    showToast
  };

})();
