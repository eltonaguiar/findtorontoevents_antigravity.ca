/* ============================================================
   SHADOW ARENA — Application Layer
   Menus, UI, Scores, Ranks, Online Multiplayer
   ============================================================ */

// === SCORE MANAGER ===
var ScoreManager = {
    STORAGE_KEY: 'shadowArena_data',

    load: function() {
        try {
            var data = localStorage.getItem(this.STORAGE_KEY);
            if (data) return JSON.parse(data);
        } catch (e) {}
        return { xp: 0, wins: 0, losses: 0, highScores: [], settings: { musicVolume: 0.5, sfxVolume: 0.7 } };
    },

    save: function(data) {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
        } catch (e) {}
    },

    addMatch: function(won, xpEarned, matchData) {
        var data = this.load();
        data.xp += xpEarned;
        if (won) data.wins++; else data.losses++;
        data.highScores.push({
            date: new Date().toISOString(),
            xp: xpEarned,
            won: won,
            character: matchData.character,
            opponent: matchData.opponent,
            difficulty: matchData.difficulty,
            score: matchData.score
        });
        // Keep top 50 scores
        data.highScores.sort(function(a, b) { return b.score - a.score; });
        if (data.highScores.length > 50) data.highScores = data.highScores.slice(0, 50);
        this.save(data);
        return data;
    },

    getProfile: function() {
        var data = this.load();
        var rank = getRank(data.xp);
        return {
            xp: data.xp,
            wins: data.wins,
            losses: data.losses,
            rank: rank,
            highScores: data.highScores || [],
            winRate: data.wins + data.losses > 0 ? Math.round((data.wins / (data.wins + data.losses)) * 100) : 0
        };
    }
};

// === ONLINE MANAGER (WebRTC) ===
var OnlineManager = {
    connection: null,
    dataChannel: null,
    roomCode: null,
    isHost: false,
    connected: false,
    onMessage: null,
    onConnected: null,
    onDisconnected: null,
    signalingURL: '',

    init: function(signalingURL) {
        this.signalingURL = signalingURL || '/FIGHTGAME/api/signal.php';
    },

    createRoom: function(callback) {
        var self = this;
        this.isHost = true;
        this.roomCode = this._generateCode();

        var config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };
        this.connection = new RTCPeerConnection(config);

        this.dataChannel = this.connection.createDataChannel('gameData');
        this._setupDataChannel(this.dataChannel);

        this.connection.onicecandidate = function(e) {
            if (e.candidate === null) {
                // All ICE candidates gathered, send offer
                self._sendSignal('offer', {
                    room: self.roomCode,
                    sdp: self.connection.localDescription.sdp
                });
            }
        };

        this.connection.createOffer().then(function(offer) {
            return self.connection.setLocalDescription(offer);
        }).then(function() {
            if (callback) callback(self.roomCode);
        });
    },

    joinRoom: function(roomCode, callback) {
        var self = this;
        this.isHost = false;
        this.roomCode = roomCode;

        var config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };
        this.connection = new RTCPeerConnection(config);

        this.connection.ondatachannel = function(e) {
            self.dataChannel = e.channel;
            self._setupDataChannel(self.dataChannel);
        };

        this.connection.onicecandidate = function(e) {
            if (e.candidate === null) {
                self._sendSignal('answer', {
                    room: self.roomCode,
                    sdp: self.connection.localDescription.sdp
                });
            }
        };

        // Get offer from signaling server
        this._getSignal(roomCode, function(offer) {
            if (!offer) {
                if (callback) callback(false, 'Room not found');
                return;
            }
            self.connection.setRemoteDescription(new RTCSessionDescription({ type: 'offer', sdp: offer.sdp }))
                .then(function() { return self.connection.createAnswer(); })
                .then(function(answer) { return self.connection.setLocalDescription(answer); })
                .then(function() { if (callback) callback(true); });
        });
    },

    send: function(data) {
        if (this.dataChannel && this.dataChannel.readyState === 'open') {
            this.dataChannel.send(JSON.stringify(data));
        }
    },

    disconnect: function() {
        if (this.dataChannel) this.dataChannel.close();
        if (this.connection) this.connection.close();
        this.connected = false;
        this.connection = null;
        this.dataChannel = null;
        this.roomCode = null;
    },

    _setupDataChannel: function(channel) {
        var self = this;
        channel.onopen = function() {
            self.connected = true;
            if (self.onConnected) self.onConnected();
        };
        channel.onclose = function() {
            self.connected = false;
            if (self.onDisconnected) self.onDisconnected();
        };
        channel.onmessage = function(e) {
            try {
                var data = JSON.parse(e.data);
                if (self.onMessage) self.onMessage(data);
            } catch (err) {}
        };
    },

    _generateCode: function() {
        var chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        var code = '';
        for (var i = 0; i < 6; i++) {
            code += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return code;
    },

    _sendSignal: function(type, data) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', this.signalingURL, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(JSON.stringify({ action: type, data: data }));
    },

    _getSignal: function(room, callback) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', this.signalingURL + '?room=' + encodeURIComponent(room), true);
        xhr.onload = function() {
            try {
                var resp = JSON.parse(xhr.responseText);
                callback(resp.data || null);
            } catch (e) {
                callback(null);
            }
        };
        xhr.onerror = function() { callback(null); };
        xhr.send();
    }
};


// === MAIN APPLICATION ===
var App = {
    engine: null,
    currentScreen: 'title',
    selectedChar1: 0,
    selectedChar2: 1,
    selectedWeapon1: 0,
    selectedWeapon2: 0,
    selectedDifficulty: 'medium',
    selectedStage: 0,
    gameMode: 'vs_ai',
    selectingPlayer: 1,
    cursorPos: 0,

    // DOM elements
    screens: {},
    canvas: null,

    init: function() {
        this.canvas = document.getElementById('gameCanvas');
        this._resizeCanvas();
        window.addEventListener('resize', this._resizeCanvas.bind(this));

        this.engine = new GameEngine(this.canvas);

        // Cache screen elements
        var screenIds = ['title-screen', 'mode-screen', 'char-select-screen', 'weapon-select-screen',
                         'stage-select-screen', 'game-screen', 'results-screen', 'scores-screen',
                         'profile-screen', 'controls-screen', 'online-lobby-screen'];
        for (var i = 0; i < screenIds.length; i++) {
            var el = document.getElementById(screenIds[i]);
            if (el) this.screens[screenIds[i]] = el;
        }

        this._setupEventListeners();
        this._renderCharacterGrid();
        this._renderWeaponGrid();
        this._renderStageGrid();
        this._updateProfile();
        this.showScreen('title-screen');

        // Gamepad detection
        this._pollGamepads();

        OnlineManager.init();

        // Audio init (lazy — unlocked on first user gesture)
        if (window.GameAudio) {
            GameAudio.init();
            // Load saved volume prefs
            var savedData = ScoreManager.load();
            if (savedData.settings) {
                GameAudio.setSfxVolume(savedData.settings.sfxVolume !== undefined ? savedData.settings.sfxVolume : 0.45);
                GameAudio.setMusicVolume(savedData.settings.musicVolume !== undefined ? savedData.settings.musicVolume : 0.18);
            }
            // Pre-load speech synthesis voices
            if (window.speechSynthesis) {
                speechSynthesis.getVoices();
                if (speechSynthesis.onvoiceschanged !== undefined) {
                    speechSynthesis.onvoiceschanged = function() { speechSynthesis.getVoices(); };
                }
            }
            // Resume context on first interaction
            var resumeOnce = function() {
                GameAudio.ensureResumed();
                GameAudio.startMusic('menu');
                document.removeEventListener('click', resumeOnce);
                document.removeEventListener('keydown', resumeOnce);
            };
            document.addEventListener('click', resumeOnce);
            document.addEventListener('keydown', resumeOnce);
        }
    },

    _resizeCanvas: function() {
        if (!this.canvas) return;
        var container = this.canvas.parentElement;
        if (!container) return;
        var aspect = CONFIG.CANVAS_WIDTH / CONFIG.CANVAS_HEIGHT;
        var cw = container.clientWidth;
        var ch = container.clientHeight || (cw / aspect);
        if (cw / ch > aspect) {
            this.canvas.style.width = (ch * aspect) + 'px';
            this.canvas.style.height = ch + 'px';
        } else {
            this.canvas.style.width = cw + 'px';
            this.canvas.style.height = (cw / aspect) + 'px';
        }
        this.canvas.width = CONFIG.CANVAS_WIDTH;
        this.canvas.height = CONFIG.CANVAS_HEIGHT;
    },

    showScreen: function(screenId) {
        for (var key in this.screens) {
            this.screens[key].classList.remove('active');
        }
        if (this.screens[screenId]) {
            this.screens[screenId].classList.add('active');
        }

        // Music transitions
        if (window.GameAudio) {
            if (screenId === 'title-screen' || screenId === 'mode-screen') {
                GameAudio.startMusic('menu');
            } else if (screenId === 'results-screen') {
                GameAudio.stopMusic();
            }
        }

        // Portrait animation management
        if (screenId === 'char-select-screen') {
            if (window.startPortraitAnimation) startPortraitAnimation();
            var current = this.selectingPlayer === 1 ? this.selectedChar1 : this.selectedChar2;
            this._startPreviewAnimation(current);
        } else {
            if (window.stopPortraitAnimation) stopPortraitAnimation();
            this._stopPreviewAnimation();
        }

        this.currentScreen = screenId;

        // Show/hide canvas
        var gameContainer = document.getElementById('game-container');
        if (gameContainer) {
            gameContainer.style.display = screenId === 'game-screen' ? 'block' : 'none';
        }
    },

    _setupEventListeners: function() {
        var self = this;

        // Title screen buttons
        this._bindBtn('btn-play', function() { self.showScreen('mode-screen'); });
        this._bindBtn('btn-scores', function() { self._renderScoresScreen(); self.showScreen('scores-screen'); });
        this._bindBtn('btn-profile', function() { self._updateProfile(); self.showScreen('profile-screen'); });
        this._bindBtn('btn-controls', function() { self.showScreen('controls-screen'); });

        // Mode selection
        this._bindBtn('btn-mode-arcade', function() { self.gameMode = 'vs_ai'; self.selectingPlayer = 1; self._renderCharacterGrid(); self.showScreen('char-select-screen'); });
        this._bindBtn('btn-mode-versus', function() { self.gameMode = 'vs_local'; self.selectingPlayer = 1; self._renderCharacterGrid(); self.showScreen('char-select-screen'); });
        this._bindBtn('btn-mode-online', function() { self.showScreen('online-lobby-screen'); });
        this._bindBtn('btn-mode-back', function() { self.showScreen('title-screen'); });

        // Character select
        this._bindBtn('btn-char-confirm', function() {
            if (self.gameMode === 'vs_local' && self.selectingPlayer === 1) {
                self.selectingPlayer = 2;
                self._renderCharacterGrid();
                var label = document.getElementById('char-select-label');
                if (label) label.textContent = 'PLAYER 2 — SELECT YOUR FIGHTER';
            } else {
                self.showScreen('weapon-select-screen');
                self.selectingPlayer = 1;
                self._renderWeaponGrid();
                var wlabel = document.getElementById('weapon-select-label');
                if (wlabel) wlabel.textContent = 'PLAYER 1 — CHOOSE YOUR WEAPON';
            }
        });
        this._bindBtn('btn-char-back', function() {
            if (self.gameMode === 'vs_local' && self.selectingPlayer === 2) {
                self.selectingPlayer = 1;
                self._renderCharacterGrid();
                var label = document.getElementById('char-select-label');
                if (label) label.textContent = 'PLAYER 1 — SELECT YOUR FIGHTER';
            } else {
                self.showScreen('mode-screen');
            }
        });

        // Weapon select
        this._bindBtn('btn-weapon-confirm', function() {
            if (self.gameMode === 'vs_local' && self.selectingPlayer === 1) {
                self.selectingPlayer = 2;
                self._renderWeaponGrid();
                var label = document.getElementById('weapon-select-label');
                if (label) label.textContent = 'PLAYER 2 — CHOOSE YOUR WEAPON';
            } else {
                self.selectingPlayer = 1;
                self.showScreen('stage-select-screen');
            }
        });
        this._bindBtn('btn-weapon-back', function() {
            if (self.gameMode === 'vs_local' && self.selectingPlayer === 2) {
                self.selectingPlayer = 1;
                self._renderWeaponGrid();
                var wlabel = document.getElementById('weapon-select-label');
                if (wlabel) wlabel.textContent = 'PLAYER 1 — CHOOSE YOUR WEAPON';
            } else {
                self.selectingPlayer = self.gameMode === 'vs_local' ? 2 : 1;
                self.showScreen('char-select-screen');
            }
        });

        // Stage select
        this._bindBtn('btn-stage-confirm', function() { self._startGame(); });
        this._bindBtn('btn-stage-back', function() {
            self.selectingPlayer = self.gameMode === 'vs_local' ? 2 : 1;
            self.showScreen('weapon-select-screen');
        });

        // Difficulty buttons
        var diffBtns = document.querySelectorAll('.diff-btn');
        for (var d = 0; d < diffBtns.length; d++) {
            (function(btn) {
                btn.addEventListener('click', function() {
                    self.selectedDifficulty = btn.getAttribute('data-diff');
                    var allDiff = document.querySelectorAll('.diff-btn');
                    for (var dd = 0; dd < allDiff.length; dd++) allDiff[dd].classList.remove('selected');
                    btn.classList.add('selected');
                });
            })(diffBtns[d]);
        }

        // Results screen
        this._bindBtn('btn-rematch', function() { self._startGame(); });
        this._bindBtn('btn-results-menu', function() { self.engine.stop(); self.showScreen('title-screen'); });

        // Scores / Profile back
        this._bindBtn('btn-scores-back', function() { self.showScreen('title-screen'); });
        this._bindBtn('btn-profile-back', function() { self.showScreen('title-screen'); });
        this._bindBtn('btn-controls-back', function() { self.showScreen('title-screen'); });

        // Online lobby
        this._bindBtn('btn-create-room', function() { self._createOnlineRoom(); });
        this._bindBtn('btn-join-room', function() { self._joinOnlineRoom(); });
        this._bindBtn('btn-online-back', function() { OnlineManager.disconnect(); self.showScreen('mode-screen'); });

        // Controls overlay toggle (? button + close button)
        this._bindBtn('btn-controls-toggle', function() { self._toggleControlsOverlay(); });
        this._bindBtn('btn-overlay-close', function() { self._toggleControlsOverlay(false); });

        // Sound toggle button
        var soundBtn = document.getElementById('btn-sound-toggle');
        if (soundBtn) {
            soundBtn.addEventListener('click', function() {
                self._toggleSound();
            });
        }

        // Click outside overlay content to close
        var overlay = document.getElementById('controls-overlay');
        if (overlay) {
            overlay.addEventListener('click', function(e) {
                if (e.target === overlay) {
                    self._toggleControlsOverlay(false);
                }
            });
        }

        // Global keyboard for navigation
        document.addEventListener('keydown', function(e) {
            // F1 = toggle controls overlay (anywhere, but especially during game)
            if (e.code === 'F1') {
                e.preventDefault();
                self._toggleControlsOverlay();
                return;
            }
            // M = mute/unmute
            if (e.code === 'KeyM' && !e.ctrlKey && !e.altKey) {
                self._toggleSound();
                return;
            }
            if (e.code === 'Enter' || e.code === 'NumpadEnter') {
                if (self.currentScreen === 'game-screen' && self.engine.gameState === 'match_end') {
                    self._showResults();
                }
            }
            if (e.code === 'Escape') {
                // If controls overlay is open, close it first
                var ov = document.getElementById('controls-overlay');
                if (ov && !ov.classList.contains('hidden')) {
                    self._toggleControlsOverlay(false);
                    return;
                }
                if (self.currentScreen === 'game-screen') {
                    self.engine.stop();
                    self.showScreen('title-screen');
                }
            }
        });

        // Gamepad START for match end, BACK for controls overlay
        window.addEventListener('gamepadconnected', function() {
            self._updateGamepadStatus();
        });
        window.addEventListener('gamepaddisconnected', function() {
            self._updateGamepadStatus();
        });
    },

    // === ANNOUNCER (Web Speech API) ===
    _announceCharacter: function(name) {
        if (!window.speechSynthesis) return;
        if (window.GameAudio && GameAudio.isMuted()) return;

        // Cancel any in-progress speech
        speechSynthesis.cancel();

        var utt = new SpeechSynthesisUtterance(name);
        utt.rate = 0.85;    // slightly slow for dramatic effect
        utt.pitch = 0.7;    // deeper, more imposing
        utt.volume = 0.9;

        // Try to pick a deep/dramatic voice
        var voices = speechSynthesis.getVoices();
        var preferred = null;
        // Prefer male voices or voices with "Male" / "David" / "Daniel" in name
        for (var i = 0; i < voices.length; i++) {
            var vn = voices[i].name.toLowerCase();
            if (vn.indexOf('david') >= 0 || vn.indexOf('daniel') >= 0 || vn.indexOf('james') >= 0 || vn.indexOf('mark') >= 0) {
                preferred = voices[i];
                break;
            }
        }
        // Fallback: first English voice
        if (!preferred) {
            for (var j = 0; j < voices.length; j++) {
                if (voices[j].lang.indexOf('en') === 0) {
                    preferred = voices[j];
                    break;
                }
            }
        }
        if (preferred) utt.voice = preferred;

        speechSynthesis.speak(utt);
    },

    _announceText: function(text, rate, pitch) {
        if (!window.speechSynthesis) return;
        if (window.GameAudio && GameAudio.isMuted()) return;
        speechSynthesis.cancel();
        var utt = new SpeechSynthesisUtterance(text);
        utt.rate = rate || 0.9;
        utt.pitch = pitch || 0.8;
        utt.volume = 0.9;
        var voices = speechSynthesis.getVoices();
        for (var i = 0; i < voices.length; i++) {
            var vn = voices[i].name.toLowerCase();
            if (vn.indexOf('david') >= 0 || vn.indexOf('daniel') >= 0 || vn.indexOf('james') >= 0) {
                utt.voice = voices[i];
                break;
            }
        }
        speechSynthesis.speak(utt);
    },

    _toggleSound: function() {
        if (!window.GameAudio) return;
        var muted = GameAudio.toggleMute();
        var soundBtn = document.getElementById('btn-sound-toggle');
        var icon = document.getElementById('sound-icon');
        if (soundBtn) {
            if (muted) {
                soundBtn.classList.add('muted');
                if (icon) icon.innerHTML = '&#x1F507;'; // muted speaker
            } else {
                soundBtn.classList.remove('muted');
                if (icon) icon.innerHTML = '&#x1F50A;'; // speaker
            }
        }
    },

    _controlsOverlayVisible: false,

    _toggleControlsOverlay: function(forceState) {
        var overlay = document.getElementById('controls-overlay');
        if (!overlay) return;

        var show;
        if (forceState !== undefined) {
            show = forceState;
        } else {
            show = overlay.classList.contains('hidden');
        }

        if (show) {
            overlay.classList.remove('hidden');
            this._controlsOverlayVisible = true;
            // Pause the game while overlay is open
            if (this.engine && this.engine.running && this.engine.gameState === 'fighting') {
                this.engine._pausedByOverlay = true;
                this.engine.gameState = 'paused';
            }
        } else {
            overlay.classList.add('hidden');
            this._controlsOverlayVisible = false;
            // Resume if we paused it
            if (this.engine && this.engine._pausedByOverlay) {
                this.engine._pausedByOverlay = false;
                this.engine.gameState = 'fighting';
            }
        }
    },

    _bindBtn: function(id, handler) {
        var el = document.getElementById(id);
        if (el) el.addEventListener('click', function(e) {
            if (window.GameAudio) GameAudio.sfx.uiClick();
            handler(e);
        });
    },

    // === CHARACTER SELECT ===
    _renderCharacterGrid: function() {
        var grid = document.getElementById('char-grid');
        if (!grid) return;
        var self = this;
        grid.innerHTML = '';

        for (var i = 0; i < CHARACTERS.length; i++) {
            (function(index) {
                var c = CHARACTERS[index];
                var card = document.createElement('div');
                card.className = 'char-card';
                var selected = (self.selectingPlayer === 1 && self.selectedChar1 === index) ||
                               (self.selectingPlayer === 2 && self.selectedChar2 === index);
                if (selected) card.classList.add('selected');

                // Portrait canvas instead of letter icon
                var portraitDiv = document.createElement('div');
                portraitDiv.className = 'char-portrait';
                portraitDiv.style.background = 'transparent';
                var portraitCanvas = document.createElement('canvas');
                portraitCanvas.className = 'char-portrait-canvas';
                portraitCanvas.setAttribute('data-char-index', index);
                portraitCanvas.width = 120;
                portraitCanvas.height = 140;
                portraitDiv.appendChild(portraitCanvas);

                card.appendChild(portraitDiv);

                var nameDiv = document.createElement('div');
                nameDiv.className = 'char-name';
                nameDiv.textContent = c.name;
                card.appendChild(nameDiv);

                var titleDiv = document.createElement('div');
                titleDiv.className = 'char-title';
                titleDiv.textContent = c.title;
                card.appendChild(titleDiv);

                var statsDiv = document.createElement('div');
                statsDiv.className = 'char-stats';
                statsDiv.innerHTML =
                    self._statBar('SPD', c.stats.speed, c.colors.accent) +
                    self._statBar('PWR', c.stats.power, c.colors.accent) +
                    self._statBar('DEF', c.stats.defense, c.colors.accent) +
                    self._statBar('RNG', c.stats.range, c.colors.accent) +
                    self._statBar('SPL', c.stats.special, c.colors.accent);
                card.appendChild(statsDiv);

                // Initial render
                if (window.renderCharacterPortrait) {
                    renderCharacterPortrait(portraitCanvas, index, false);
                }

                card.addEventListener('click', function() {
                    if (self.selectingPlayer === 1) self.selectedChar1 = index;
                    else self.selectedChar2 = index;
                    self._renderCharacterGrid();
                    self._updateCharPreview(index);
                    self._startPreviewAnimation(index);
                    // Announcer says character name
                    self._announceCharacter(CHARACTERS[index].name);
                    if (window.GameAudio) GameAudio.sfx.uiConfirm();
                });

                grid.appendChild(card);
            })(i);
        }

        // Start portrait animation
        if (window.startPortraitAnimation) startPortraitAnimation();

        // Update preview
        var current = this.selectingPlayer === 1 ? this.selectedChar1 : this.selectedChar2;
        this._updateCharPreview(current);

        // Update label
        var label = document.getElementById('char-select-label');
        if (label) {
            if (this.gameMode === 'vs_ai') {
                label.textContent = 'SELECT YOUR FIGHTER';
            } else {
                label.textContent = 'PLAYER ' + this.selectingPlayer + ' — SELECT YOUR FIGHTER';
            }
        }
    },

    _updateCharPreview: function(index) {
        var c = CHARACTERS[index];
        var el = document.getElementById('char-preview-info');
        if (!el) return;
        el.innerHTML = '<h2 style="color:' + c.colors.accent + ';">' + c.name + ' — ' + c.title + '</h2>' +
            '<p>' + c.description + '</p>' +
            '<p class="char-lore">' + c.lore + '</p>' +
            '<div class="special-info"><strong style="color:' + c.colors.glow + ';">Special: ' + c.specialName + '</strong><br>' + c.specialDesc + '</div>';

        // Render large preview portrait
        var previewCanvas = document.getElementById('char-preview-canvas');
        if (previewCanvas && window.renderCharacterPortrait) {
            previewCanvas.style.borderColor = c.colors.glow;
            previewCanvas.style.boxShadow = '0 0 20px ' + c.colors.glow + '60';
            renderCharacterPortrait(previewCanvas, index, true);
        }
    },

    _previewAnimFrame: null,
    _startPreviewAnimation: function(index) {
        var self = this;
        if (this._previewAnimFrame) cancelAnimationFrame(this._previewAnimFrame);
        var canvas = document.getElementById('char-preview-canvas');
        if (!canvas || !window.renderCharacterPortrait) return;
        function animLoop() {
            renderCharacterPortrait(canvas, index, true);
            self._previewAnimFrame = requestAnimationFrame(animLoop);
        }
        animLoop();
    },
    _stopPreviewAnimation: function() {
        if (this._previewAnimFrame) {
            cancelAnimationFrame(this._previewAnimFrame);
            this._previewAnimFrame = null;
        }
    },

    _statBar: function(label, value, color) {
        var pct = (value / 10) * 100;
        return '<div class="stat-row"><span class="stat-label">' + label + '</span>' +
            '<div class="stat-bar-bg"><div class="stat-bar-fill" style="width:' + pct + '%;background:' + color + ';"></div></div>' +
            '<span class="stat-val">' + value + '</span></div>';
    },

    // === WEAPON SELECT ===
    _renderWeaponGrid: function() {
        var grid = document.getElementById('weapon-grid');
        if (!grid) return;
        var self = this;
        grid.innerHTML = '';

        for (var i = 0; i < WEAPONS.length; i++) {
            (function(index) {
                var w = WEAPONS[index];
                var card = document.createElement('div');
                card.className = 'weapon-card';
                var selected = (self.selectingPlayer === 1 && self.selectedWeapon1 === index) ||
                               (self.selectingPlayer === 2 && self.selectedWeapon2 === index);
                if (selected) card.classList.add('selected');

                card.innerHTML = '<div class="weapon-icon" style="color:' + w.color + ';">' + self._weaponIcon(w.drawType) + '</div>' +
                    '<div class="weapon-name">' + w.name + '</div>' +
                    '<div class="weapon-desc">' + w.description + '</div>' +
                    '<div class="weapon-stats">' +
                    self._statBar('SPD', w.stats.speed, w.color) +
                    self._statBar('DMG', w.stats.damage, w.color) +
                    self._statBar('RNG', w.stats.range, w.color) +
                    '</div>';

                card.addEventListener('click', function() {
                    if (self.selectingPlayer === 1) self.selectedWeapon1 = index;
                    else self.selectedWeapon2 = index;
                    self._renderWeaponGrid();
                });

                grid.appendChild(card);
            })(i);
        }
    },

    _weaponIcon: function(type) {
        switch (type) {
            case 'blade': return '⚔️';
            case 'hammer': return '🔨';
            case 'daggers': return '🗡️';
            case 'chain': return '⛓️';
            case 'axe': return '🪓';
            case 'staff': return '🏑';
            default: return '⚔️';
        }
    },

    // === STAGE SELECT ===
    _renderStageGrid: function() {
        var grid = document.getElementById('stage-grid');
        if (!grid) return;
        var self = this;
        grid.innerHTML = '';

        for (var i = 0; i < STAGES.length; i++) {
            (function(index) {
                var s = STAGES[index];
                var card = document.createElement('div');
                card.className = 'stage-card' + (self.selectedStage === index ? ' selected' : '');
                card.innerHTML = '<div class="stage-preview" style="background:linear-gradient(135deg,' + s.skyColors[0] + ',' + s.skyColors[1] + ');border-bottom:4px solid ' + s.groundColor + ';">' +
                    '<div class="stage-accent" style="color:' + s.accentColor + ';">★</div>' +
                    '</div>' +
                    '<div class="stage-name">' + s.name + '</div>';

                card.addEventListener('click', function() {
                    self.selectedStage = index;
                    self._renderStageGrid();
                });

                grid.appendChild(card);
            })(i);
        }
    },

    // === START GAME ===
    _startGame: function() {
        var self = this;

        // AI picks random character/weapon if vs AI
        if (this.gameMode === 'vs_ai') {
            this.selectedChar2 = Math.floor(Math.random() * CHARACTERS.length);
            // Avoid same character
            if (this.selectedChar2 === this.selectedChar1) {
                this.selectedChar2 = (this.selectedChar2 + 1) % CHARACTERS.length;
            }
            this.selectedWeapon2 = Math.floor(Math.random() * WEAPONS.length);
        }

        this.showScreen('game-screen');
        var gameContainer = document.getElementById('game-container');
        if (gameContainer) gameContainer.style.display = 'block';
        this._resizeCanvas();

        // Detect gamepads
        this._assignGamepads();

        this.engine.setupMatch(
            this.selectedChar1, this.selectedWeapon1,
            this.selectedChar2, this.selectedWeapon2,
            this.gameMode, this.selectedDifficulty, this.selectedStage
        );

        this.engine.onMatchEnd = function(winner, stats) {
            var winChar = winner === 1 ? CHARACTERS[self.selectedChar1] : CHARACTERS[self.selectedChar2];
            self._announceText(winChar.name + ' wins!', 0.8, 0.6);
            setTimeout(function() { self._showResults(); }, 2500);
        };

        this.engine.onCountdownFight = function() {
            self._announceText('Fight!', 1.1, 0.5);
        };

        this.engine.onRoundEnd = function(winner) {
            var winChar = winner === 1 ? CHARACTERS[self.selectedChar1] : CHARACTERS[self.selectedChar2];
            setTimeout(function() { self._announceText('K O!', 0.7, 0.4); }, 200);
        };

        // Announce "Round X"
        var c1 = CHARACTERS[this.selectedChar1];
        var c2 = CHARACTERS[this.selectedChar2];
        this._announceText(c1.name + ' versus ' + c2.name + '! Round 1!', 0.9, 0.6);

        this.engine.start();
    },

    _showResults: function() {
        this.engine.stop();

        var winner = this.engine.p1Wins >= CONFIG.ROUNDS_TO_WIN ? 1 : 2;
        var won = winner === 1;
        var stats = this.engine.matchStats;

        var timeBonus = Math.max(0, this.engine.roundTimer);
        var healthRemaining = won ? this.engine.fighter1.health : this.engine.fighter2.health;
        var combos = won ? stats.p1Combos : stats.p2Combos;
        var maxCombo = won ? stats.p1MaxCombo : stats.p2MaxCombo;

        var xp = calculateXP(won, this.selectedDifficulty, healthRemaining, combos, stats.perfectRounds > 0, timeBonus);

        var score = Math.floor(
            (won ? 1000 : 200) +
            (stats.p1Damage * 5) +
            (combos * 50) +
            (maxCombo * 100) +
            (stats.perfectRounds * 500) +
            (timeBonus * 10)
        );

        var matchData = {
            character: CHARACTERS[this.selectedChar1].name,
            opponent: CHARACTERS[this.selectedChar2].name,
            difficulty: this.selectedDifficulty,
            score: score
        };

        var updatedData = ScoreManager.addMatch(won, xp, matchData);
        var rank = getRank(updatedData.xp);

        // Populate results
        var resultsEl = document.getElementById('results-content');
        if (resultsEl) {
            var winChar = won ? CHARACTERS[this.selectedChar1] : CHARACTERS[this.selectedChar2];
            resultsEl.innerHTML =
                '<div class="result-banner ' + (won ? 'victory' : 'defeat') + '">' +
                    '<h1>' + (won ? 'VICTORY!' : 'DEFEAT') + '</h1>' +
                    '<p>' + winChar.name + ' wins the match!</p>' +
                '</div>' +
                '<div class="result-stats">' +
                    '<div class="result-row"><span>Score</span><span class="result-val">' + score.toLocaleString() + '</span></div>' +
                    '<div class="result-row"><span>XP Earned</span><span class="result-val xp-val">+' + xp + ' XP</span></div>' +
                    '<div class="result-row"><span>Total XP</span><span class="result-val">' + updatedData.xp.toLocaleString() + '</span></div>' +
                    '<div class="result-row"><span>Rank</span><span class="result-val" style="color:' + rank.current.color + ';">' + rank.current.icon + ' ' + rank.current.name + '</span></div>' +
                    '<div class="result-row"><span>Damage Dealt</span><span class="result-val">' + Math.floor(stats.p1Damage) + '</span></div>' +
                    '<div class="result-row"><span>Max Combo</span><span class="result-val">' + stats.p1MaxCombo + ' hits</span></div>' +
                    '<div class="result-row"><span>Perfect Rounds</span><span class="result-val">' + stats.perfectRounds + '</span></div>' +
                    (rank.next ? '<div class="rank-progress"><span>Next: ' + rank.next.icon + ' ' + rank.next.name + '</span>' +
                        '<div class="rank-bar"><div class="rank-bar-fill" style="width:' + Math.min(100, ((updatedData.xp - rank.current.minXP) / (rank.next.minXP - rank.current.minXP)) * 100) + '%;background:' + rank.current.color + ';"></div></div></div>' : '') +
                '</div>';
        }

        this.showScreen('results-screen');
    },

    // === SCORES SCREEN ===
    _renderScoresScreen: function() {
        var el = document.getElementById('scores-content');
        if (!el) return;
        var profile = ScoreManager.getProfile();
        var scores = profile.highScores;

        var html = '<table class="scores-table"><thead><tr><th>#</th><th>Character</th><th>Opponent</th><th>Score</th><th>Result</th></tr></thead><tbody>';
        if (scores.length === 0) {
            html += '<tr><td colspan="5" style="text-align:center;padding:30px;color:#666;">No matches played yet. Start fighting!</td></tr>';
        }
        for (var i = 0; i < Math.min(scores.length, 20); i++) {
            var s = scores[i];
            html += '<tr><td>' + (i + 1) + '</td><td>' + (s.character || '?') + '</td><td>' + (s.opponent || '?') + '</td>' +
                '<td>' + (s.score || 0).toLocaleString() + '</td>' +
                '<td class="' + (s.won ? 'win-text' : 'loss-text') + '">' + (s.won ? 'WIN' : 'LOSS') + '</td></tr>';
        }
        html += '</tbody></table>';
        el.innerHTML = html;
    },

    // === PROFILE SCREEN ===
    _updateProfile: function() {
        var profile = ScoreManager.getProfile();
        var el = document.getElementById('profile-content');
        if (!el) return;

        var rank = profile.rank;
        el.innerHTML =
            '<div class="profile-rank">' +
                '<div class="rank-icon" style="color:' + rank.current.color + ';border-color:' + rank.current.color + ';">' + rank.current.icon + '</div>' +
                '<h2 style="color:' + rank.current.color + ';">' + rank.current.name + '</h2>' +
            '</div>' +
            '<div class="profile-stats-grid">' +
                '<div class="pstat"><div class="pstat-val">' + profile.xp.toLocaleString() + '</div><div class="pstat-label">Total XP</div></div>' +
                '<div class="pstat"><div class="pstat-val">' + profile.wins + '</div><div class="pstat-label">Wins</div></div>' +
                '<div class="pstat"><div class="pstat-val">' + profile.losses + '</div><div class="pstat-label">Losses</div></div>' +
                '<div class="pstat"><div class="pstat-val">' + profile.winRate + '%</div><div class="pstat-label">Win Rate</div></div>' +
            '</div>' +
            (rank.next ? '<div class="rank-progress-lg"><p>Next Rank: <span style="color:' + rank.next.color + ';">' + rank.next.icon + ' ' + rank.next.name + '</span> (' + rank.next.minXP.toLocaleString() + ' XP)</p>' +
                '<div class="rank-bar lg"><div class="rank-bar-fill" style="width:' + Math.min(100, ((profile.xp - rank.current.minXP) / (rank.next.minXP - rank.current.minXP)) * 100) + '%;background:linear-gradient(90deg,' + rank.current.color + ',' + rank.next.color + ');"></div></div></div>' : '<p style="color:#ffd700;margin-top:20px;">Maximum rank achieved!</p>');
    },

    // === ONLINE ===
    _createOnlineRoom: function() {
        var statusEl = document.getElementById('online-status');
        if (statusEl) statusEl.textContent = 'Creating room...';

        OnlineManager.createRoom(function(code) {
            if (statusEl) statusEl.innerHTML = 'Room Code: <strong style="color:#ffd700;font-size:28px;letter-spacing:4px;">' + code + '</strong><br>Share this code with your opponent. Waiting for them to join...';
        });

        OnlineManager.onConnected = function() {
            if (statusEl) statusEl.textContent = 'Opponent connected! Starting match...';
            // TODO: exchange character/weapon selections then start
        };
    },

    _joinOnlineRoom: function() {
        var codeInput = document.getElementById('room-code-input');
        var code = codeInput ? codeInput.value.trim().toUpperCase() : '';
        if (code.length !== 6) {
            var statusEl = document.getElementById('online-status');
            if (statusEl) statusEl.textContent = 'Please enter a valid 6-character room code.';
            return;
        }

        var statusEl = document.getElementById('online-status');
        if (statusEl) statusEl.textContent = 'Joining room ' + code + '...';

        OnlineManager.joinRoom(code, function(success, err) {
            if (!success) {
                if (statusEl) statusEl.textContent = 'Failed to join: ' + (err || 'Room not found');
            }
        });

        OnlineManager.onConnected = function() {
            if (statusEl) statusEl.textContent = 'Connected! Starting match...';
        };
    },

    // === GAMEPAD ===
    _assignGamepads: function() {
        var pads = navigator.getGamepads ? navigator.getGamepads() : [];
        this.engine.p1GamepadIndex = null;
        this.engine.p2GamepadIndex = null;
        var padCount = 0;
        for (var i = 0; i < pads.length; i++) {
            if (pads[i]) {
                if (padCount === 0) {
                    this.engine.p1GamepadIndex = i;
                } else if (padCount === 1 && this.gameMode === 'vs_local') {
                    this.engine.p2GamepadIndex = i;
                }
                padCount++;
            }
        }
    },

    _pollGamepads: function() {
        var self = this;
        setInterval(function() {
            self._updateGamepadStatus();
            // Gamepad nav for menus
            var pads = navigator.getGamepads ? navigator.getGamepads() : [];
            for (var i = 0; i < pads.length; i++) {
                var pad = pads[i];
                if (!pad) continue;
                // START button to continue from match end
                if (pad.buttons[GAMEPAD_MAP.START] && pad.buttons[GAMEPAD_MAP.START].pressed) {
                    if (self.currentScreen === 'game-screen' && self.engine.gameState === 'match_end') {
                        self._showResults();
                    }
                }
            }
        }, 100);
    },

    _updateGamepadStatus: function() {
        var el = document.getElementById('gamepad-status');
        if (!el) return;
        var pads = navigator.getGamepads ? navigator.getGamepads() : [];
        var count = 0;
        for (var i = 0; i < pads.length; i++) {
            if (pads[i]) count++;
        }
        if (count > 0) {
            el.textContent = count + ' controller' + (count > 1 ? 's' : '') + ' connected';
            el.style.color = '#2ecc71';
        } else {
            el.textContent = 'No controllers detected — use keyboard';
            el.style.color = '#888';
        }
    }
};

// === INIT ===
document.addEventListener('DOMContentLoaded', function() {
    App.init();
});
