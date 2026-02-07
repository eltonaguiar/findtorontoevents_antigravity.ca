/**
 * VR Substantial Quick Wins - Set 7: Innovation & AI Features
 * 
 * 10 Additional Major Features:
 * 1. AI Virtual Assistant (voice-activated help)
 * 2. Voice-to-Text Notes (dictation system)
 * 3. Gesture Drawing (3D drawing in VR)
 * 4. Music Visualizer (audio reactive visuals)
 * 5. Pet Companion (virtual pet)
 * 6. VR Camera (video recording)
 * 7. World Clock (multiple time zones)
 * 8. Time Travel Mode (historical era views)
 * 9. Seated Mode (accessibility)
 * 10. Custom Avatars (avatar customization)
 */

(function() {
  'use strict';

  // ==================== CONFIGURATION ====================
  const CONFIG = {
    ai: {
      enabled: true,
      wakeWord: 'hey assistant',
      responseDelay: 500
    },
    visualizer: {
      fftSize: 256,
      barCount: 32
    },
    pet: {
      hungerRate: 0.1,
      happinessRate: 0.05
    },
    recording: {
      format: 'webm',
      quality: 'high'
    }
  };

  // ==================== STATE ====================
  const state = {
    aiListening: false,
    aiContext: [],
    drawings: [],
    isDrawing: false,
    audioContext: null,
    analyser: null,
    pet: JSON.parse(localStorage.getItem('vr-pet') || JSON.stringify({
      name: 'Buddy',
      hunger: 50,
      happiness: 50,
      level: 1,
      xp: 0
    })),
    isRecording: false,
    mediaRecorder: null,
    recordedChunks: [],
    seatedMode: false,
    avatar: JSON.parse(localStorage.getItem('vr-avatar') || JSON.stringify({
      color: '#00d4ff',
      hat: 'none',
      accessory: 'none'
    })),
    timeTravel: {
      active: false,
      era: 'present'
    }
  };

  // ==================== 1. AI VIRTUAL ASSISTANT ====================
  const AIAssistant = {
    responses: {
      'hello': 'Hello! How can I help you today?',
      'help': 'I can help you navigate, answer questions, or control VR features. Try saying "go to weather" or "what time is it?"',
      'time': () => `The current time is ${new Date().toLocaleTimeString()}.`,
      'weather': 'I can see the weather zone. Would you like me to take you there?',
      'navigate': 'Where would you like to go? Say "go to hub", "go to movies", etc.',
      'status': () => `You're in ${window.location.pathname}. Your session has been active for ${Math.floor((Date.now() - state.sessionStart) / 60000)} minutes.`,
      'thanks': "You're welcome! Let me know if you need anything else.",
      'bye': 'Goodbye! Have a great time in VR!'
    },

    init() {
      this.createUI();
      this.setupVoiceRecognition();
      console.log('[VR AI Assistant] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-ai-btn';
      btn.innerHTML = '🤖';
      btn.title = 'AI Assistant (Hold Space)';
      btn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 620px;
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
      btn.addEventListener('click', () => this.toggle());
      document.body.appendChild(btn);

      // AI Panel
      const panel = document.createElement('div');
      panel.id = 'vr-ai-panel';
      panel.style.cssText = `
        position: fixed;
        bottom: 80px;
        right: 580px;
        width: 300px;
        background: rgba(10,10,20,0.95);
        border: 2px solid #8b5cf6;
        border-radius: 15px;
        padding: 15px;
        z-index: 99997;
        display: none;
        backdrop-filter: blur(10px);
      `;
      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
          <span style="color: #8b5cf6; font-weight: bold;">🤖 AI Assistant</span>
          <span id="vr-ai-status" style="font-size: 11px; color: #888;">Idle</span>
        </div>
        <div id="vr-ai-chat" style="height: 150px; overflow-y: auto; margin-bottom: 10px; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px; font-size: 12px;">
          <div style="color: #888;">Say "Hey Assistant" or click the mic to talk...</div>
        </div>
        <div style="display: flex; gap: 8px;">
          <input type="text" id="vr-ai-input" placeholder="Type a message..." style="flex: 1; padding: 8px; border-radius: 5px; background: rgba(255,255,255,0.1); border: 1px solid #8b5cf6; color: white; font-size: 12px;">
          <button onclick="VRQuickWinsSet7.AI.sendMessage()" style="padding: 8px 12px; background: #8b5cf6; border: none; border-radius: 5px; color: white; cursor: pointer;">➤</button>
        </div>
      `;
      document.body.appendChild(panel);

      // Space key to talk
      document.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && e.target === document.body) {
          e.preventDefault();
          this.startListening();
        }
      });
      document.addEventListener('keyup', (e) => {
        if (e.code === 'Space') {
          this.stopListening();
        }
      });
    },

    setupVoiceRecognition() {
      if (!('webkitSpeechRecognition' in window)) return;
      
      this.recognition = new webkitSpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      
      this.recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript.toLowerCase();
        this.processInput(transcript);
      };
    },

    toggle() {
      const panel = document.getElementById('vr-ai-panel');
      if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
      }
    },

    startListening() {
      state.aiListening = true;
      const status = document.getElementById('vr-ai-status');
      if (status) {
        status.textContent = 'Listening...';
        status.style.color = '#22c55e';
      }
      
      if (this.recognition) {
        this.recognition.start();
      }
    },

    stopListening() {
      state.aiListening = false;
      const status = document.getElementById('vr-ai-status');
      if (status) {
        status.textContent = 'Processing...';
        status.style.color = '#f59e0b';
      }
      
      if (this.recognition) {
        this.recognition.stop();
      }
    },

    processInput(input) {
      this.addMessage('You', input);
      
      // Check for navigation commands
      if (input.includes('go to') || input.includes('take me to')) {
        const zones = {
          'hub': '/vr/',
          'weather': '/vr/weather-zone.html',
          'movies': '/vr/movies.html',
          'events': '/vr/events/',
          'creators': '/vr/creators.html',
          'stocks': '/vr/stocks-zone.html',
          'wellness': '/vr/wellness/'
        };
        
        for (const [name, url] of Object.entries(zones)) {
          if (input.includes(name)) {
            this.respond(`Taking you to ${name}...`);
            setTimeout(() => window.location.href = url, 1000);
            return;
          }
        }
      }
      
      // Check for predefined responses
      for (const [key, response] of Object.entries(this.responses)) {
        if (input.includes(key)) {
          const resp = typeof response === 'function' ? response() : response;
          this.respond(resp);
          return;
        }
      }
      
      this.respond("I'm not sure about that. Try asking for help!");
    },

    sendMessage() {
      const input = document.getElementById('vr-ai-input');
      if (input && input.value.trim()) {
        this.processInput(input.value.trim().toLowerCase());
        input.value = '';
      }
    },

    respond(message) {
      setTimeout(() => {
        this.addMessage('AI', message);
        const status = document.getElementById('vr-ai-status');
        if (status) {
          status.textContent = 'Idle';
          status.style.color = '#888';
        }
        
        // Speak response
        if ('speechSynthesis' in window) {
          const utterance = new SpeechSynthesisUtterance(message);
          utterance.rate = 1.1;
          speechSynthesis.speak(utterance);
        }
      }, CONFIG.ai.responseDelay);
    },

    addMessage(sender, text) {
      const chat = document.getElementById('vr-ai-chat');
      if (chat) {
        const msg = document.createElement('div');
        msg.style.cssText = `margin-bottom: 8px; ${sender === 'AI' ? 'color: #8b5cf6;' : 'color: #e0e0e0;'}`;
        msg.innerHTML = `<strong>${sender}:</strong> ${text}`;
        chat.appendChild(msg);
        chat.scrollTop = chat.scrollHeight;
      }
    }
  };

  // ==================== 2. VOICE-TO-TEXT NOTES ====================
  const VoiceToText = {
    init() {
      this.createUI();
      console.log('[VR Voice-to-Text] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-voice-notes-btn';
      btn.innerHTML = '🎤';
      btn.title = 'Voice Notes';
      btn.style.cssText = `
        position: fixed;
        top: 1120px;
        right: 20px;
        background: rgba(234, 179, 8, 0.5);
        border: 2px solid #eab308;
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
      let panel = document.getElementById('vr-voice-notes-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-voice-notes-panel';
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
          min-width: 400px;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #eab308;">🎤 Voice Notes</h3>
          <button onclick="document.getElementById('vr-voice-notes-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="display: flex; gap: 10px; margin-bottom: 15px;">
          <button id="vr-dictate-btn" onclick="VRQuickWinsSet7.VoiceNotes.toggleDictation()" style="flex: 1; padding: 12px; background: rgba(234,179,8,0.3); border: 1px solid #eab308; border-radius: 8px; color: white; cursor: pointer;">
            🎤 Start Dictation
          </button>
        </div>
        
        <textarea id="vr-dictated-text" style="width: 100%; height: 150px; padding: 12px; border-radius: 8px; background: rgba(255,255,255,0.1); border: 1px solid #eab308; color: white; resize: none;" placeholder="Your dictated text will appear here..."></textarea>
        
        <div style="display: flex; gap: 10px; margin-top: 15px;">
          <button onclick="VRQuickWinsSet7.VoiceNotes.copyText()" style="flex: 1; padding: 10px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; cursor: pointer;">📋 Copy</button>
          <button onclick="VRQuickWinsSet7.VoiceNotes.saveNote()" style="flex: 1; padding: 10px; background: #eab308; border: none; border-radius: 8px; color: black; cursor: pointer;">💾 Save</button>
        </div>
      `;
      panel.style.display = 'block';
    },

    toggleDictation() {
      if (!('webkitSpeechRecognition' in window)) {
        showToast('❌ Speech recognition not supported');
        return;
      }

      const btn = document.getElementById('vr-dictate-btn');
      
      if (this.recognition && this.isListening) {
        this.recognition.stop();
        this.isListening = false;
        btn.innerHTML = '🎤 Start Dictation';
        btn.style.background = 'rgba(234,179,8,0.3)';
      } else {
        this.recognition = new webkitSpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        
        const textarea = document.getElementById('vr-dictated-text');
        
        this.recognition.onresult = (e) => {
          let final = '';
          for (let i = e.resultIndex; i < e.results.length; i++) {
            if (e.results[i].isFinal) {
              final += e.results[i][0].transcript;
            }
          }
          if (final && textarea) {
            textarea.value += final + ' ';
          }
        };
        
        this.recognition.start();
        this.isListening = true;
        btn.innerHTML = '⏹️ Stop Dictation';
        btn.style.background = 'rgba(239,68,68,0.5)';
      }
    },

    copyText() {
      const textarea = document.getElementById('vr-dictated-text');
      if (textarea && textarea.value) {
        navigator.clipboard.writeText(textarea.value);
        showToast('📋 Copied to clipboard!');
      }
    },

    saveNote() {
      const textarea = document.getElementById('vr-dictated-text');
      if (textarea && textarea.value) {
        const notes = JSON.parse(localStorage.getItem('vr-voice-notes') || '[]');
        notes.push({
          text: textarea.value,
          timestamp: Date.now(),
          zone: window.location.pathname
        });
        localStorage.setItem('vr-voice-notes', JSON.stringify(notes));
        textarea.value = '';
        showToast('💾 Note saved!');
      }
    }
  };

  // ==================== 3. GESTURE DRAWING ====================
  const GestureDrawing = {
    init() {
      this.createUI();
      console.log('[VR Gesture Drawing] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-drawing-btn';
      btn.innerHTML = '🎨';
      btn.title = 'Gesture Drawing';
      btn.style.cssText = `
        position: fixed;
        top: 1170px;
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
      btn.addEventListener('click', () => this.toggle());
      document.body.appendChild(btn);
    },

    toggle() {
      state.isDrawing = !state.isDrawing;
      
      const btn = document.getElementById('vr-drawing-btn');
      if (btn) {
        btn.style.background = state.isDrawing ? 'rgba(236, 72, 153, 0.8)' : 'rgba(236, 72, 153, 0.5)';
        btn.style.boxShadow = state.isDrawing ? '0 0 20px #ec4899' : 'none';
      }

      if (state.isDrawing) {
        this.enableDrawing();
        showToast('🎨 Drawing mode ON - Click and drag to draw');
      } else {
        this.disableDrawing();
        showToast('🎨 Drawing mode OFF');
      }
    },

    enableDrawing() {
      const scene = document.querySelector('a-scene');
      if (!scene) return;

      // Create drawing surface
      this.drawingEl = document.createElement('a-entity');
      this.drawingEl.id = 'vr-drawing-surface';
      scene.appendChild(this.drawingEl);

      // Track mouse/controller for drawing
      this.drawHandler = (e) => {
        if (!state.isDrawing) return;
        
        // Simplified - in full implementation would raycast and draw
        if (e.buttons === 1) { // Left click
          this.addDrawPoint(e.clientX, e.clientY);
        }
      };

      document.addEventListener('mousemove', this.drawHandler);
      document.addEventListener('mousedown', this.drawHandler);
    },

    disableDrawing() {
      document.removeEventListener('mousemove', this.drawHandler);
      document.removeEventListener('mousedown', this.drawHandler);
    },

    addDrawPoint(x, y) {
      // Placeholder - would create 3D drawing in scene
      const dot = document.createElement('a-sphere');
      dot.setAttribute('radius', '0.02');
      dot.setAttribute('color', '#ec4899');
      dot.setAttribute('position', `${(x / window.innerWidth) * 10 - 5} 2 ${(y / window.innerHeight) * 10 - 5}`);
      this.drawingEl.appendChild(dot);
    },

    clear() {
      if (this.drawingEl) {
        this.drawingEl.innerHTML = '';
      }
    }
  };

  // ==================== 4. MUSIC VISUALIZER ====================
  const MusicVisualizer = {
    init() {
      this.createUI();
      console.log('[VR Music Visualizer] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-visualizer-btn';
      btn.innerHTML = '🎵';
      btn.title = 'Music Visualizer';
      btn.style.cssText = `
        position: fixed;
        top: 1220px;
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
      btn.addEventListener('click', () => this.toggle());
      document.body.appendChild(btn);
    },

    async toggle() {
      if (this.isActive) {
        this.stop();
      } else {
        await this.start();
      }
    },

    async start() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = this.audioContext.createMediaStreamSource(stream);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = CONFIG.visualizer.fftSize;
        source.connect(this.analyser);

        this.isActive = true;
        this.createVisuals();
        this.animate();

        const btn = document.getElementById('vr-visualizer-btn');
        if (btn) {
          btn.style.background = 'rgba(59, 130, 246, 0.8)';
          btn.style.boxShadow = '0 0 20px #3b82f6';
        }

        showToast('🎵 Visualizer started!');
      } catch (e) {
        showToast('❌ Microphone access required');
      }
    },

    stop() {
      this.isActive = false;
      if (this.visualizerEl) {
        this.visualizerEl.remove();
      }
      if (this.audioContext) {
        this.audioContext.close();
      }

      const btn = document.getElementById('vr-visualizer-btn');
      if (btn) {
        btn.style.background = 'rgba(59, 130, 246, 0.5)';
        btn.style.boxShadow = 'none';
      }
    },

    createVisuals() {
      const scene = document.querySelector('a-scene');
      if (!scene) return;

      this.visualizerEl = document.createElement('a-entity');
      this.visualizerEl.id = 'vr-music-visualizer';
      this.visualizerEl.setAttribute('position', '0 0 -5');

      // Create bars
      for (let i = 0; i < CONFIG.visualizer.barCount; i++) {
        const bar = document.createElement('a-box');
        bar.setAttribute('width', '0.1');
        bar.setAttribute('depth', '0.1');
        bar.setAttribute('height', '0.1');
        bar.setAttribute('position', `${(i - CONFIG.visualizer.barCount / 2) * 0.2} 0 0`);
        bar.setAttribute('color', `hsl(${i * 10}, 70%, 50%)`);
        this.visualizerEl.appendChild(bar);
      }

      scene.appendChild(this.visualizerEl);
    },

    animate() {
      if (!this.isActive) return;

      const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      this.analyser.getByteFrequencyData(dataArray);

      const bars = this.visualizerEl?.querySelectorAll('a-box');
      if (bars) {
        bars.forEach((bar, i) => {
          const value = dataArray[i * 2] / 255;
          const height = 0.1 + value * 3;
          bar.setAttribute('height', height);
          bar.setAttribute('position', `${(i - CONFIG.visualizer.barCount / 2) * 0.2} ${height / 2} 0`);
        });
      }

      requestAnimationFrame(() => this.animate());
    }
  };

  // ==================== 5. PET COMPANION ====================
  const PetCompanion = {
    init() {
      this.createUI();
      this.startPetLoop();
      console.log('[VR Pet] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-pet-btn';
      btn.innerHTML = '🐕';
      btn.title = 'Pet Companion';
      btn.style.cssText = `
        position: fixed;
        top: 1270px;
        right: 20px;
        background: rgba(251, 146, 60, 0.5);
        border: 2px solid #fb923c;
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

      // Pet indicator
      const indicator = document.createElement('div');
      indicator.id = 'vr-pet-indicator';
      indicator.style.cssText = `
        position: fixed;
        top: 1315px;
        right: 20px;
        background: rgba(0,0,0,0.8);
        border-radius: 8px;
        padding: 5px 10px;
        color: #fb923c;
        font-size: 11px;
        z-index: 99997;
        text-align: center;
      `;
      indicator.innerHTML = `❤️ ${state.pet.hunger}% 😊 ${state.pet.happiness}%`;
      document.body.appendChild(indicator);
    },

    showPanel() {
      let panel = document.getElementById('vr-pet-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-pet-panel';
        panel.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
          border: 2px solid #fb923c;
          border-radius: 20px;
          padding: 25px;
          z-index: 100000;
          min-width: 300px;
          text-align: center;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #fb923c;">🐕 ${state.pet.name}</h3>
          <button onclick="document.getElementById('vr-pet-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="font-size: 64px; margin-bottom: 15px;">🐕</div>
        
        <div style="display: grid; gap: 10px; margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">
            <span>❤️ Hunger</span>
            <div style="width: 100px; height: 20px; background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden;">
              <div style="width: ${state.pet.hunger}%; height: 100%; background: linear-gradient(90deg, #ef4444, #22c55e);"></div>
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">
            <span>😊 Happiness</span>
            <div style="width: 100px; height: 20px; background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden;">
              <div style="width: ${state.pet.happiness}%; height: 100%; background: linear-gradient(90deg, #ef4444, #22c55e);"></div>
            </div>
          </div>
        </div>

        <div style="display: flex; gap: 10px;">
          <button onclick="VRQuickWinsSet7.Pet.feed()" style="flex: 1; padding: 12px; background: rgba(34,197,94,0.3); border: 1px solid #22c55e; border-radius: 8px; color: white; cursor: pointer;">🍖 Feed</button>
          <button onclick="VRQuickWinsSet7.Pet.play()" style="flex: 1; padding: 12px; background: rgba(59,130,246,0.3); border: 1px solid #3b82f6; border-radius: 8px; color: white; cursor: pointer;">🎾 Play</button>
        </div>

        <div style="margin-top: 15px; font-size: 12px; opacity: 0.7;">Level ${state.pet.level} • ${state.pet.xp} XP</div>
      `;
      panel.style.display = 'block';
    },

    feed() {
      state.pet.hunger = Math.min(100, state.pet.hunger + 20);
      state.pet.xp += 5;
      this.checkLevelUp();
      this.save();
      this.updateUI();
      showToast('🍖 Yummy! Pet is fed!');
    },

    play() {
      state.pet.happiness = Math.min(100, state.pet.happiness + 20);
      state.pet.hunger = Math.max(0, state.pet.hunger - 10);
      state.pet.xp += 10;
      this.checkLevelUp();
      this.save();
      this.updateUI();
      showToast('🎾 Pet is happy!');
    },

    checkLevelUp() {
      const xpNeeded = state.pet.level * 100;
      if (state.pet.xp >= xpNeeded) {
        state.pet.level++;
        state.pet.xp -= xpNeeded;
        showToast(`🎉 Pet leveled up to ${state.pet.level}!`);
      }
    },

    startPetLoop() {
      setInterval(() => {
        state.pet.hunger = Math.max(0, state.pet.hunger - CONFIG.pet.hungerRate);
        state.pet.happiness = Math.max(0, state.pet.happiness - CONFIG.pet.happinessRate);
        this.save();
        this.updateUI();
      }, 60000);
    },

    updateUI() {
      const indicator = document.getElementById('vr-pet-indicator');
      if (indicator) {
        indicator.innerHTML = `❤️ ${Math.floor(state.pet.hunger)}% 😊 ${Math.floor(state.pet.happiness)}%`;
      }
    },

    save() {
      localStorage.setItem('vr-pet', JSON.stringify(state.pet));
    }
  };

  // ==================== 6. VR CAMERA (VIDEO RECORDING) ====================
  const VRCamera = {
    init() {
      this.createUI();
      console.log('[VR Camera] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-camera-btn';
      btn.innerHTML = '📹';
      btn.title = 'VR Camera (Record)';
      btn.style.cssText = `
        position: fixed;
        top: 1320px;
        right: 20px;
        background: rgba(239, 68, 68, 0.5);
        border: 2px solid #ef4444;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
      `;
      btn.addEventListener('click', () => this.toggleRecording());
      document.body.appendChild(btn);

      // Recording indicator
      const indicator = document.createElement('div');
      indicator.id = 'vr-recording-indicator';
      indicator.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(239, 68, 68, 0.9);
        border-radius: 20px;
        padding: 8px 16px;
        color: white;
        font-size: 14px;
        z-index: 100002;
        display: none;
        align-items: center;
        gap: 8px;
      `;
      indicator.innerHTML = `
        <span style="width: 10px; height: 10px; background: white; border-radius: 50%; animation: pulse 1s infinite;"></span>
        <span id="vr-recording-time">00:00</span>
      `;
      document.body.appendChild(indicator);
    },

    async toggleRecording() {
      if (state.isRecording) {
        this.stopRecording();
      } else {
        await this.startRecording();
      }
    },

    async startRecording() {
      try {
        const canvas = document.querySelector('canvas');
        if (!canvas) {
          showToast('❌ No canvas found');
          return;
        }

        const stream = canvas.captureStream(30);
        state.mediaRecorder = new MediaRecorder(stream, {
          mimeType: 'video/webm;codecs=vp9'
        });

        state.recordedChunks = [];
        state.mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            state.recordedChunks.push(e.data);
          }
        };

        state.mediaRecorder.onstop = () => {
          this.saveRecording();
        };

        state.mediaRecorder.start();
        state.isRecording = true;
        this.recordingStartTime = Date.now();

        // Update UI
        const btn = document.getElementById('vr-camera-btn');
        const indicator = document.getElementById('vr-recording-indicator');
        if (btn) {
          btn.style.background = 'rgba(239, 68, 68, 0.9)';
          btn.style.boxShadow = '0 0 20px #ef4444';
        }
        if (indicator) {
          indicator.style.display = 'flex';
        }

        this.updateRecordingTime();
        showToast('🔴 Recording started!');
      } catch (e) {
        showToast('❌ Recording failed');
        console.error(e);
      }
    },

    stopRecording() {
      if (!state.mediaRecorder) return;

      state.mediaRecorder.stop();
      state.isRecording = false;

      // Update UI
      const btn = document.getElementById('vr-camera-btn');
      const indicator = document.getElementById('vr-recording-indicator');
      if (btn) {
        btn.style.background = 'rgba(239, 68, 68, 0.5)';
        btn.style.boxShadow = 'none';
      }
      if (indicator) {
        indicator.style.display = 'none';
      }

      clearTimeout(this.recordingTimer);
      showToast('✅ Recording saved!');
    },

    updateRecordingTime() {
      if (!state.isRecording) return;

      const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
      const mins = Math.floor(elapsed / 60).toString().padStart(2, '0');
      const secs = (elapsed % 60).toString().padStart(2, '0');

      const timeEl = document.getElementById('vr-recording-time');
      if (timeEl) {
        timeEl.textContent = `${mins}:${secs}`;
      }

      this.recordingTimer = setTimeout(() => this.updateRecordingTime(), 1000);
    },

    saveRecording() {
      const blob = new Blob(state.recordedChunks, { type: 'video/webm' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `vr-recording-${Date.now()}.webm`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  // ==================== 7. WORLD CLOCK ====================
  const WorldClock = {
    cities: [
      { name: 'Toronto', zone: 'America/Toronto', flag: '🇨🇦' },
      { name: 'London', zone: 'Europe/London', flag: '🇬🇧' },
      { name: 'Tokyo', zone: 'Asia/Tokyo', flag: '🇯🇵' },
      { name: 'Sydney', zone: 'Australia/Sydney', flag: '🇦🇺' },
      { name: 'New York', zone: 'America/New_York', flag: '🇺🇸' },
      { name: 'Paris', zone: 'Europe/Paris', flag: '🇫🇷' }
    ],

    init() {
      this.createUI();
      this.startClock();
      console.log('[VR World Clock] Initialized');
    },

    createUI() {
      const container = document.createElement('div');
      container.id = 'vr-world-clock';
      container.style.cssText = `
        position: fixed;
        top: 1370px;
        right: 20px;
        background: rgba(0,0,0,0.8);
        border: 2px solid #00d4ff;
        border-radius: 12px;
        padding: 10px 15px;
        z-index: 99998;
        min-width: 150px;
        backdrop-filter: blur(5px);
      `;
      document.body.appendChild(container);

      // Toggle button
      const btn = document.createElement('button');
      btn.id = 'vr-world-clock-btn';
      btn.innerHTML = '🌍';
      btn.title = 'World Clock';
      btn.style.cssText = `
        position: fixed;
        top: 1370px;
        right: 180px;
        background: rgba(0, 212, 255, 0.5);
        border: 2px solid #00d4ff;
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 18px;
        z-index: 99998;
      `;
      btn.addEventListener('click', () => this.toggleExpanded());
      document.body.appendChild(btn);
    },

    startClock() {
      this.updateClock();
      setInterval(() => this.updateClock(), 1000);
    },

    updateClock() {
      const container = document.getElementById('vr-world-clock');
      if (!container) return;

      const mainCity = this.cities[0];
      const time = new Date().toLocaleTimeString('en-US', {
        timeZone: mainCity.zone,
        hour: '2-digit',
        minute: '2-digit'
      });

      container.innerHTML = `
        <div style="color: #00d4ff; font-size: 12px;">${mainCity.flag} ${mainCity.name}</div>
        <div style="color: white; font-size: 24px; font-family: monospace; font-weight: bold;">${time}</div>
      `;
    },

    toggleExpanded() {
      let panel = document.getElementById('vr-world-clock-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-world-clock-panel';
        panel.style.cssText = `
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: var(--vr-overlay-bg, rgba(10,10,20,0.95));
          border: 2px solid #00d4ff;
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
          <h3 style="margin: 0; color: #00d4ff;">🌍 World Clock</h3>
          <button onclick="document.getElementById('vr-world-clock-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="display: grid; gap: 10px;">
          ${this.cities.map(city => {
            const time = new Date().toLocaleTimeString('en-US', {
              timeZone: city.zone,
              hour: '2-digit',
              minute: '2-digit'
            });
            const date = new Date().toLocaleDateString('en-US', {
              timeZone: city.zone,
              weekday: 'short'
            });
            return `
              <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 10px;">
                <div>
                  <div style="font-size: 20px;">${city.flag} ${city.name}</div>
                  <div style="font-size: 11px; opacity: 0.6;">${date}</div>
                </div>
                <div style="font-size: 24px; font-family: monospace; color: #00d4ff;">${time}</div>
              </div>
            `;
          }).join('')}
        </div>
      `;
      panel.style.display = 'block';
    }
  };

  // ==================== 8. TIME TRAVEL MODE ====================
  const TimeTravel = {
    eras: [
      { id: 'present', name: 'Present Day', year: '2025', filter: 'none' },
      { id: 'retro', name: '80s Retro', year: '1985', filter: 'sepia(0.5) hue-rotate(180deg)' },
      { id: 'medieval', name: 'Medieval', year: '1350', filter: 'grayscale(0.5) sepia(0.8)' },
      { id: 'future', name: 'Cyber Future', year: '2077', filter: 'hue-rotate(90deg) saturate(2)' },
      { id: 'noir', name: 'Film Noir', year: '1945', filter: 'grayscale(1) contrast(1.5)' }
    ],

    init() {
      this.createUI();
      console.log('[VR Time Travel] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-time-travel-btn';
      btn.innerHTML = '⏰';
      btn.title = 'Time Travel';
      btn.style.cssText = `
        position: fixed;
        top: 1420px;
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
      btn.addEventListener('click', () => this.showPanel());
      document.body.appendChild(btn);
    },

    showPanel() {
      let panel = document.getElementById('vr-time-travel-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-time-travel-panel';
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
          min-width: 350px;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #8b5cf6;">⏰ Time Travel</h3>
          <button onclick="document.getElementById('vr-time-travel-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="display: grid; gap: 10px;">
          ${this.eras.map(era => `
            <button onclick="VRQuickWinsSet7.TimeTravel.setEra('${era.id}')" 
              style="padding: 15px; background: ${state.timeTravel.era === era.id ? 'rgba(139,92,246,0.3)' : 'rgba(255,255,255,0.05)'}; border: 2px solid ${state.timeTravel.era === era.id ? '#8b5cf6' : 'rgba(255,255,255,0.1)'}; border-radius: 12px; color: white; cursor: pointer; text-align: left;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-weight: bold; font-size: 16px;">${era.name}</div>
                  <div style="font-size: 12px; opacity: 0.6;">${era.year}</div>
                </div>
                ${state.timeTravel.era === era.id ? '<span style="color: #8b5cf6;">✓</span>' : ''}
              </div>
            </button>
          `).join('')}
        </div>
      `;
      panel.style.display = 'block';
    },

    setEra(eraId) {
      const era = this.eras.find(e => e.id === eraId);
      if (!era) return;

      state.timeTravel.era = eraId;
      state.timeTravel.active = eraId !== 'present';

      // Apply filter to scene
      const scene = document.querySelector('a-scene');
      if (scene) {
        if (era.filter !== 'none') {
          scene.style.filter = era.filter;
        } else {
          scene.style.filter = '';
        }
      }

      document.getElementById('vr-time-travel-panel').style.display = 'none';
      showToast(`⏰ Traveling to ${era.name}...`);
    }
  };

  // ==================== 9. SEATED MODE ====================
  const SeatedMode = {
    init() {
      this.createUI();
      console.log('[VR Seated Mode] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-seated-btn';
      btn.innerHTML = '🪑';
      btn.title = 'Seated Mode';
      btn.style.cssText = `
        position: fixed;
        top: 1470px;
        right: 20px;
        background: ${state.seatedMode ? 'rgba(34, 197, 94, 0.8)' : 'rgba(100, 100, 100, 0.3)'};
        border: 2px solid ${state.seatedMode ? '#22c55e' : '#888'};
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
    },

    toggle() {
      state.seatedMode = !state.seatedMode;
      
      const btn = document.getElementById('vr-seated-btn');
      if (btn) {
        btn.style.background = state.seatedMode ? 'rgba(34, 197, 94, 0.8)' : 'rgba(100, 100, 100, 0.3)';
        btn.style.borderColor = state.seatedMode ? '#22c55e' : '#888';
      }

      if (state.seatedMode) {
        this.enableSeatedMode();
        showToast('🪑 Seated mode enabled');
      } else {
        this.disableSeatedMode();
        showToast('🪑 Seated mode disabled');
      }
    },

    enableSeatedMode() {
      // Adjust camera height for seated position
      const camera = document.querySelector('a-camera');
      if (camera) {
        camera.setAttribute('position', '0 1.2 0');
      }

      // Reduce movement speed
      if (window.VRControllerSupport) {
        const config = window.VRControllerSupport.getConfig?.();
        if (config) {
          config.movement.speed = 1.5;
        }
      }

      // Show seated indicator
      const indicator = document.createElement('div');
      indicator.id = 'vr-seated-indicator';
      indicator.style.cssText = `
        position: fixed;
        bottom: 60px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(34, 197, 94, 0.3);
        border: 1px solid #22c55e;
        border-radius: 20px;
        padding: 8px 16px;
        color: #22c55e;
        font-size: 12px;
        z-index: 99999;
      `;
      indicator.textContent = '🪑 Seated Mode';
      document.body.appendChild(indicator);
    },

    disableSeatedMode() {
      // Restore camera height
      const camera = document.querySelector('a-camera');
      if (camera) {
        camera.setAttribute('position', '0 1.6 0');
      }

      // Restore movement speed
      if (window.VRControllerSupport) {
        const config = window.VRControllerSupport.getConfig?.();
        if (config) {
          config.movement.speed = 3.0;
        }
      }

      const indicator = document.getElementById('vr-seated-indicator');
      if (indicator) indicator.remove();
    }
  };

  // ==================== 10. CUSTOM AVATARS ====================
  const CustomAvatars = {
    colors: ['#00d4ff', '#ec4899', '#22c55e', '#eab308', '#ef4444', '#8b5cf6', '#f97316'],
    hats: ['none', '👒', '🎩', '🧢', '👑', '🎓'],
    accessories: ['none', '🕶️', '👓', '🎀', '⭐'],

    init() {
      this.createUI();
      console.log('[VR Custom Avatars] Initialized');
    },

    createUI() {
      const btn = document.createElement('button');
      btn.id = 'vr-avatar-btn';
      btn.innerHTML = '👤';
      btn.title = 'Customize Avatar';
      btn.style.cssText = `
        position: fixed;
        top: 1520px;
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
      btn.addEventListener('click', () => this.showPanel());
      document.body.appendChild(btn);
    },

    showPanel() {
      let panel = document.getElementById('vr-avatar-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.id = 'vr-avatar-panel';
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
          text-align: center;
          backdrop-filter: blur(15px);
          color: var(--vr-text, #e0e0e0);
        `;
        document.body.appendChild(panel);
      }

      panel.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0; color: #ec4899;">👤 Customize Avatar</h3>
          <button onclick="document.getElementById('vr-avatar-panel').style.display='none'" style="background: rgba(239,68,68,0.8); border: none; color: white; width: 30px; height: 30px; border-radius: 50%; cursor: pointer;">×</button>
        </div>
        
        <div style="font-size: 80px; margin-bottom: 20px;">
          <span style="color: ${state.avatar.color};">👤</span>
          ${state.avatar.hat !== 'none' ? `<span style="position: relative; top: -40px; left: -30px;">${state.avatar.hat}</span>` : ''}
          ${state.avatar.accessory !== 'none' ? `<span style="position: relative; top: -10px; left: -50px;">${state.avatar.accessory}</span>` : ''}
        </div>

        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 8px; text-align: left;">Color:</label>
          <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: center;">
            ${this.colors.map(color => `
              <button onclick="VRQuickWinsSet7.Avatar.setColor('${color}')" 
                style="width: 32px; height: 32px; border-radius: 50%; background: ${color}; border: 3px solid ${state.avatar.color === color ? 'white' : 'transparent'}; cursor: pointer;">
              </button>
            `).join('')}
          </div>
        </div>

        <div style="margin-bottom: 15px;">
          <label style="display: block; margin-bottom: 8px; text-align: left;">Hat:</label>
          <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: center;">
            ${this.hats.map(hat => `
              <button onclick="VRQuickWinsSet7.Avatar.setHat('${hat}')" 
                style="padding: 8px 12px; background: ${state.avatar.hat === hat ? 'rgba(236,72,153,0.3)' : 'rgba(255,255,255,0.05)'}; border: 2px solid ${state.avatar.hat === hat ? '#ec4899' : 'rgba(255,255,255,0.1)'}; border-radius: 8px; cursor: pointer; font-size: 20px;">
                ${hat === 'none' ? '❌' : hat}
              </button>
            `).join('')}
          </div>
        </div>

        <div style="margin-bottom: 20px;">
          <label style="display: block; margin-bottom: 8px; text-align: left;">Accessory:</label>
          <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: center;">
            ${this.accessories.map(acc => `
              <button onclick="VRQuickWinsSet7.Avatar.setAccessory('${acc}')" 
                style="padding: 8px 12px; background: ${state.avatar.accessory === acc ? 'rgba(236,72,153,0.3)' : 'rgba(255,255,255,0.05)'}; border: 2px solid ${state.avatar.accessory === acc ? '#ec4899' : 'rgba(255,255,255,0.1)'}; border-radius: 8px; cursor: pointer; font-size: 20px;">
                ${acc === 'none' ? '❌' : acc}
              </button>
            `).join('')}
          </div>
        </div>

        <button onclick="VRQuickWinsSet7.Avatar.save()" style="width: 100%; padding: 12px; background: #ec4899; border: none; border-radius: 8px; color: white; cursor: pointer; font-weight: bold;">💾 Save Avatar</button>
      `;
      panel.style.display = 'block';
    },

    setColor(color) {
      state.avatar.color = color;
      this.showPanel();
    },

    setHat(hat) {
      state.avatar.hat = hat;
      this.showPanel();
    },

    setAccessory(acc) {
      state.avatar.accessory = acc;
      this.showPanel();
    },

    save() {
      localStorage.setItem('vr-avatar', JSON.stringify(state.avatar));
      document.getElementById('vr-avatar-panel').style.display = 'none';
      showToast('👤 Avatar saved!');
    }
  };

  // ==================== UTILITY: TOAST ====================
  function showToast(message) {
    let toast = document.getElementById('vr-toast-set7');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'vr-toast-set7';
      toast.style.cssText = `
        position: fixed;
        bottom: 350px;
        left: 50%;
        transform: translateX(-50%) translateY(20px);
        background: rgba(10,10,20,0.95);
        backdrop-filter: blur(12px);
        border: 1px solid #8b5cf6;
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
    console.log('[VR Substantial Quick Wins - Set 7] Initializing...');
    
    state.sessionStart = Date.now();

    AIAssistant.init();
    VoiceToText.init();
    GestureDrawing.init();
    MusicVisualizer.init();
    PetCompanion.init();
    VRCamera.init();
    WorldClock.init();
    TimeTravel.init();
    SeatedMode.init();
    CustomAvatars.init();

    console.log('[VR Substantial Quick Wins - Set 7] Initialized!');
    console.log('New shortcuts:');
    console.log('  Hold Space - Talk to AI');
    console.log('  Features accessible via UI buttons');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose API
  window.VRQuickWinsSet7 = {
    AI: AIAssistant,
    VoiceNotes: VoiceToText,
    Drawing: GestureDrawing,
    Visualizer: MusicVisualizer,
    Pet: PetCompanion,
    Camera: VRCamera,
    WorldClock,
    TimeTravel,
    SeatedMode,
    Avatar: CustomAvatars,
    showToast
  };

})();
