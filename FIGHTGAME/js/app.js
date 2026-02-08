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

// === PRESENCE MANAGER (cross-game online tracking) ===
var PresenceManager = {
    PRESENCE_URL: '/FIGHTGAME/api/presence.php',
    HEARTBEAT_MS: 8000,
    POLL_MS: 5000,
    STORAGE_KEY: 'shadowArena_presence',

    playerId: null,
    playerName: null,
    currentGame: 'Shadow Arena',
    currentGameUrl: '/FIGHTGAME/',
    currentStatus: 'online',
    roomCode: '',
    joinable: false,
    spectatable: false,
    _hbTimer: null,
    _pollTimer: null,
    _players: [],
    onPlayersUpdated: null,

    _apiEnabled: false,

    init: function() {
        this._loadIdentity();
        // Only enable API calls on real server (skip localhost/dev to avoid 404 noise)
        var host = window.location.hostname;
        this._apiEnabled = (host !== 'localhost' && host !== '127.0.0.1' && host.indexOf('192.168') !== 0);
        if (this._apiEnabled) {
            this._startHeartbeat();
            this._startPolling();
            var self = this;
            window.addEventListener('beforeunload', function() {
                self._sendLeave();
            });
        }
    },

    _loadIdentity: function() {
        // Saved identity
        try {
            var saved = localStorage.getItem(this.STORAGE_KEY);
            if (saved) {
                var d = JSON.parse(saved);
                this.playerId = d.id ? d.id : null;
                this.playerName = d.name ? d.name : null;
            }
        } catch (e) {}
        // Cross-game auth (VR / FavCreators)
        if (!this.playerName) {
            try {
                var vu = sessionStorage.getItem('vr_auth_user');
                if (vu) { var ud = JSON.parse(vu); this.playerName = ud.name ? ud.name : (ud.username ? ud.username : null); }
            } catch (e) {}
        }
        if (!this.playerName) {
            try {
                var fc = sessionStorage.getItem('fc_user');
                if (fc) { var fd = JSON.parse(fc); this.playerName = fd.name ? fd.name : (fd.username ? fd.username : null); }
            } catch (e) {}
        }
        if (!this.playerId) {
            this.playerId = 'sa_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
        }
        if (!this.playerName) {
            this.playerName = 'Fighter_' + Math.floor(1000 + Math.random() * 9000);
        }
        this._saveIdentity();
    },

    _saveIdentity: function() {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify({ id: this.playerId, name: this.playerName }));
        } catch (e) {}
    },

    setStatus: function(status, roomCode, joinable, spectatable) {
        this.currentStatus = status || 'online';
        this.roomCode = roomCode || '';
        this.joinable = !!joinable;
        this.spectatable = !!spectatable;
        this._sendHeartbeat();
    },

    setName: function(name) {
        if (name && name.length > 0) {
            this.playerName = name.substr(0, 20);
            this._saveIdentity();
            this._sendHeartbeat();
        }
    },

    getPlayers: function() { return this._players; },

    _startHeartbeat: function() {
        var self = this;
        this._sendHeartbeat();
        this._hbTimer = setInterval(function() { self._sendHeartbeat(); }, this.HEARTBEAT_MS);
    },

    _startPolling: function() {
        var self = this;
        this._fetchPlayers();
        this._pollTimer = setInterval(function() { self._fetchPlayers(); }, this.POLL_MS);
    },

    _sendHeartbeat: function() {
        if (!this._apiEnabled) return;
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', this.PRESENCE_URL, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.send(JSON.stringify({
                action: 'heartbeat',
                player_id: this.playerId,
                player_name: this.playerName,
                game: this.currentGame,
                game_url: this.currentGameUrl,
                status: this.currentStatus,
                room_code: this.roomCode,
                joinable: this.joinable,
                spectatable: this.spectatable
            }));
        } catch (e) {}
    },

    _sendLeave: function() {
        if (!this._apiEnabled) return;
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('POST', this.PRESENCE_URL, false);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.send(JSON.stringify({ action: 'leave', player_id: this.playerId }));
        } catch (e) {}
    },

    _fetchPlayers: function() {
        if (!this._apiEnabled) return;
        var self = this;
        try {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', this.PRESENCE_URL, true);
            xhr.onreadystatechange = function() {
                if (xhr.readyState === 4 && xhr.status === 200) {
                    try {
                        var data = JSON.parse(xhr.responseText);
                        if (data && data.players) {
                            self._players = data.players;
                            if (self.onPlayersUpdated) self.onPlayersUpdated(self._players);
                        }
                    } catch (e) {}
                }
            };
            xhr.send();
        } catch (e) {}
    },

    destroy: function() {
        if (this._hbTimer) clearInterval(this._hbTimer);
        if (this._pollTimer) clearInterval(this._pollTimer);
        this._sendLeave();
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
        this._initTouchControls();
        this._renderCharacterGrid();
        this._renderWeaponGrid();
        this._renderStageGrid();
        this._updateProfile();
        this.showScreen('title-screen');

        // Gamepad detection
        this._pollGamepads();

        OnlineManager.init();

        // Presence tracking (cross-game online players)
        this._initPresence();

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
                    var self = this;
                    speechSynthesis.onvoiceschanged = function() {
                        speechSynthesis.getVoices();
                        self._announcerVoice = null; // re-select best voice
                    };
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

        // Touch controls: show only during gameplay
        if (screenId === 'game-screen') {
            this._showTouchControls(true);
        } else {
            this._showTouchControls(false);
            this._clearTouchState();
        }

        // Players Online panel: show on title/mode, hide during game
        this._updatePresencePanel(screenId);

        // Update presence status based on screen
        this._updatePresenceStatus(screenId);
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

    // === MOBILE TOUCH CONTROLS ===
    _isTouchDevice: false,

    _initTouchControls: function() {
        var self = this;
        // Detect touch capability
        this._isTouchDevice = ('ontouchstart' in window) ||
            (navigator.maxTouchPoints > 0) ||
            (navigator.msMaxTouchPoints > 0);

        var container = document.getElementById('touch-controls');
        if (!container) return;

        if (this._isTouchDevice) {
            container.classList.remove('hidden');
        }

        var buttons = container.querySelectorAll('.touch-btn');
        for (var i = 0; i < buttons.length; i++) {
            (function(btn) {
                var action = btn.getAttribute('data-action');
                if (!action) return;

                // Touch start — activate
                btn.addEventListener('touchstart', function(e) {
                    e.preventDefault();
                    btn.classList.add('pressed');
                    if (self.engine && self.engine.input) {
                        self.engine.input.touchState[action] = true;
                    }
                    // Ensure audio context is unlocked
                    if (window.GameAudio) GameAudio.ensureResumed();
                }, { passive: false });

                // Touch end — deactivate
                btn.addEventListener('touchend', function(e) {
                    e.preventDefault();
                    btn.classList.remove('pressed');
                    if (self.engine && self.engine.input) {
                        self.engine.input.touchState[action] = false;
                    }
                }, { passive: false });

                // Touch cancel (e.g. finger slides off)
                btn.addEventListener('touchcancel', function(e) {
                    btn.classList.remove('pressed');
                    if (self.engine && self.engine.input) {
                        self.engine.input.touchState[action] = false;
                    }
                }, { passive: false });

                // Also handle touchmove leaving the button
                btn.addEventListener('touchmove', function(e) {
                    var touch = e.touches[0];
                    if (!touch) return;
                    var rect = btn.getBoundingClientRect();
                    var inside = touch.clientX >= rect.left && touch.clientX <= rect.right &&
                                 touch.clientY >= rect.top && touch.clientY <= rect.bottom;
                    if (!inside) {
                        btn.classList.remove('pressed');
                        if (self.engine && self.engine.input) {
                            self.engine.input.touchState[action] = false;
                        }
                    }
                }, { passive: false });

                // Prevent context menu on long-press
                btn.addEventListener('contextmenu', function(e) { e.preventDefault(); });
            })(buttons[i]);
        }

        // Prevent scroll/zoom on the touch controls area
        container.addEventListener('touchmove', function(e) { e.preventDefault(); }, { passive: false });
    },

    _showTouchControls: function(show) {
        var el = document.getElementById('touch-controls');
        if (!el) return;
        if (show && this._isTouchDevice) {
            el.classList.remove('hidden');
        } else {
            el.classList.add('hidden');
        }
    },

    // Clear all touch state (e.g. on screen transition)
    _clearTouchState: function() {
        if (this.engine && this.engine.input) {
            var ts = this.engine.input.touchState;
            for (var k in ts) ts[k] = false;
        }
        // Remove pressed class from all buttons
        var btns = document.querySelectorAll('.touch-btn.pressed');
        for (var i = 0; i < btns.length; i++) btns[i].classList.remove('pressed');
    },

    // === ANNOUNCER (Vocal Synth + Enhanced Speech) ===

    _announcerVoice: null,

    /**
     * Pick the best available SpeechSynthesis voice.
     * Prefers natural / neural voices which sound dramatically more human.
     */
    _getAnnouncerVoice: function() {
        if (this._announcerVoice) return this._announcerVoice;
        if (!window.speechSynthesis) return null;
        var voices = speechSynthesis.getVoices();
        if (!voices || voices.length === 0) return null;

        // Priority: natural-sounding voices first (Google neural, MS Online, Apple)
        var priority = [
            'google uk english male',     // Chrome — very natural
            'google us english',          // Chrome — natural
            'microsoft guy online',       // Edge — neural voice
            'microsoft mark online',      // Edge — neural
            'microsoft david online',     // Edge — neural
            'microsoft zira online',      // Edge — neural (female, but natural)
            'alex',                       // macOS — high quality
            'daniel',                     // macOS — British, decent
            'tom',                        // macOS
            'aaron',                      // newer macOS
            'david',                      // Windows built-in
            'mark',                       // Windows built-in
            'james'                       // general
        ];

        for (var p = 0; p < priority.length; p++) {
            for (var i = 0; i < voices.length; i++) {
                if (voices[i].name.toLowerCase().indexOf(priority[p]) >= 0) {
                    this._announcerVoice = voices[i];
                    return voices[i];
                }
            }
        }
        // Fallback: first English voice
        for (var j = 0; j < voices.length; j++) {
            if (voices[j].lang && voices[j].lang.indexOf('en') === 0) {
                this._announcerVoice = voices[j];
                return voices[j];
            }
        }
        return null;
    },

    /**
     * Announce a character name as an energetic shout: "VEX!"
     * Layers: vocal formant synth + stinger SFX + improved speech synthesis.
     */
    _announceCharacter: function(name) {
        if (window.GameAudio && GameAudio.isMuted()) return;

        // 1) Play the formant-synth vocal shout (stylized arcade layer)
        if (window.GameAudio && GameAudio.announcer) {
            GameAudio.announcer.shout(name, { pitch: 95, volume: 0.45 });
        }

        // 2) Play dramatic stinger SFX
        if (window.GameAudio) GameAudio.sfx.announcerName();

        // 3) Speak the name with improved settings
        if (window.speechSynthesis) {
            speechSynthesis.cancel();
            var utt = new SpeechSynthesisUtterance(name.toUpperCase() + '!');
            utt.rate   = 1.05;   // slightly fast for energy
            utt.pitch  = 0.9;    // authoritative but not robot-deep
            utt.volume = 1.0;
            var voice = this._getAnnouncerVoice();
            if (voice) utt.voice = voice;
            speechSynthesis.speak(utt);
        }
    },

    /**
     * Announce a gameplay phrase (FIGHT!, K.O.!, X WINS!, etc.)
     * @param {string} text     Display text
     * @param {string} vocalKey Key in VocalAnnouncer PHRASES (e.g. 'Fight', 'KO')
     * @param {string} sfxKey   Key on SFX (e.g. 'announcerFight', 'announcerKO')
     * @param {number} rate     Speech rate override
     * @param {number} pitch    Speech pitch override
     */
    _announceText: function(text, vocalKey, sfxKey, rate, pitch) {
        if (window.GameAudio && GameAudio.isMuted()) return;

        // 1) Vocal formant shout
        if (vocalKey && window.GameAudio && GameAudio.announcer) {
            GameAudio.announcer.shout(vocalKey, { pitch: 95, volume: 0.5 });
        }

        // 2) Stinger SFX
        if (sfxKey && window.GameAudio && GameAudio.sfx[sfxKey]) {
            GameAudio.sfx[sfxKey]();
        }

        // 3) Speech synthesis
        if (window.speechSynthesis) {
            speechSynthesis.cancel();
            var utt = new SpeechSynthesisUtterance(text);
            utt.rate   = rate  || 1.0;
            utt.pitch  = pitch || 0.9;
            utt.volume = 1.0;
            var voice = this._getAnnouncerVoice();
            if (voice) utt.voice = voice;
            speechSynthesis.speak(utt);
        }
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
            // Shout the winner's name + "WINS!"
            if (window.GameAudio && GameAudio.announcer) {
                GameAudio.announcer.shout(winChar.name, { pitch: 100, volume: 0.5 });
            }
            self._announceText(
                winChar.name.toUpperCase() + ' WINS!',
                'Wins', 'announcerWins', 0.95, 0.9
            );
            setTimeout(function() { self._showResults(); }, 2500);
        };

        this.engine.onCountdownFight = function() {
            self._announceText('FIGHT!', 'Fight', 'announcerFight', 1.1, 0.85);
        };

        this.engine.onRoundEnd = function(winner) {
            var winChar = winner === 1 ? CHARACTERS[self.selectedChar1] : CHARACTERS[self.selectedChar2];
            setTimeout(function() {
                self._announceText('K.O.!', 'KO', 'announcerKO', 0.8, 0.75);
            }, 200);
        };

        // Announce matchup: shout both names then "ROUND ONE!"
        var c1 = CHARACTERS[this.selectedChar1];
        var c2 = CHARACTERS[this.selectedChar2];
        var roundWords = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE'];
        var roundNum = roundWords[0] || '1';

        // Vocal shouts for both character names
        if (window.GameAudio && GameAudio.announcer) {
            GameAudio.announcer.shout(c1.name, { pitch: 95, volume: 0.4 });
            setTimeout(function() {
                if (window.GameAudio && GameAudio.announcer) {
                    GameAudio.announcer.shout(c2.name, { pitch: 95, volume: 0.4 });
                }
            }, 600);
        }
        this._announceText(
            c1.name.toUpperCase() + '! VERSUS! ' + c2.name.toUpperCase() + '! ROUND ' + roundNum + '!',
            'Versus', 'announcerVersus', 0.95, 0.9
        );

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

    // === PRESENCE / PLAYERS ONLINE ===
    _initPresence: function() {
        var self = this;
        PresenceManager.init();

        // Populate name input with current name
        var nameInput = document.getElementById('fighter-name-input');
        if (nameInput) {
            nameInput.value = PresenceManager.playerName;
            nameInput.addEventListener('change', function() {
                var v = nameInput.value.trim();
                if (v.length > 0) {
                    PresenceManager.setName(v);
                }
            });
            nameInput.addEventListener('blur', function() {
                var v = nameInput.value.trim();
                if (v.length > 0) {
                    PresenceManager.setName(v);
                }
            });
        }

        // Listen for player list updates
        PresenceManager.onPlayersUpdated = function(players) {
            self._renderPlayersOnline(players);
        };

        // Toggle floating panel collapse
        var toggle = document.getElementById('players-online-toggle');
        if (toggle) {
            toggle.addEventListener('click', function() {
                var list = document.getElementById('players-online-list');
                var chev = document.getElementById('players-online-chevron');
                if (list) list.classList.toggle('collapsed');
                if (chev) chev.classList.toggle('collapsed');
            });
        }
    },

    _updatePresenceStatus: function(screenId) {
        var statusMap = {
            'title-screen': 'online',
            'mode-screen': 'choosing_mode',
            'char-select-screen': 'character_select',
            'weapon-select-screen': 'weapon_select',
            'stage-select-screen': 'stage_select',
            'game-screen': 'fighting',
            'results-screen': 'results',
            'scores-screen': 'online',
            'profile-screen': 'online',
            'controls-screen': 'online',
            'online-lobby-screen': 'in_lobby'
        };
        var status = statusMap[screenId] || 'online';
        var roomCode = OnlineManager.roomCode || '';
        var joinable = (screenId === 'online-lobby-screen' && roomCode.length > 0 && !OnlineManager.connected);
        var spectatable = (screenId === 'game-screen' && this.gameMode === 'vs_ai');
        PresenceManager.setStatus(status, roomCode, joinable, spectatable);
    },

    _updatePresencePanel: function(screenId) {
        var panel = document.getElementById('players-online-panel');
        if (!panel) return;
        // Show floating panel on title, mode, scores, profile, controls screens
        // Hide on lobby (has its own inline panel), game, char/weapon/stage select
        var showOn = {
            'title-screen': true,
            'mode-screen': true,
            'scores-screen': true,
            'profile-screen': true,
            'controls-screen': true,
            'results-screen': true
        };
        if (showOn[screenId]) {
            panel.classList.remove('hidden');
        } else {
            panel.classList.add('hidden');
        }
    },

    _renderPlayersOnline: function(players) {
        var self = this;
        var myId = PresenceManager.playerId;

        // Sort: current user first, then by game, then alphabetical
        players.sort(function(a, b) {
            if (a.id === myId) return -1;
            if (b.id === myId) return 1;
            if (a.game !== b.game) return a.game < b.game ? -1 : 1;
            return a.name < b.name ? -1 : 1;
        });

        // Build HTML
        var html = '';
        if (players.length === 0) {
            html = '<div class="players-online-empty">No players online</div>';
        } else {
            for (var i = 0; i < players.length; i++) {
                html += self._buildPlayerEntry(players[i], myId);
            }
        }

        // Update floating panel
        var floatList = document.getElementById('players-online-list');
        var floatCount = document.getElementById('players-online-count');
        if (floatList) floatList.innerHTML = html;
        if (floatCount) floatCount.textContent = players.length;

        // Update lobby inline panel
        var lobbyList = document.getElementById('lobby-players-list');
        var lobbyCount = document.getElementById('lobby-players-count');
        if (lobbyList) lobbyList.innerHTML = html;
        if (lobbyCount) lobbyCount.textContent = players.length;

        // Attach click handlers for join/spectate buttons
        self._bindPlayerActions();
    },

    _buildPlayerEntry: function(player, myId) {
        var isMe = (player.id === myId);

        // Dot color based on status
        var dotClass = 'player-dot';
        if (player.status === 'fighting') dotClass += ' fighting';
        else if (player.status === 'in_lobby' || player.status === 'choosing_mode') dotClass += ' lobby';

        // Status display text
        var statusText = this._presenceStatusLabel(player.status);
        var statusClass = 'player-status';
        if (player.status === 'fighting') statusClass += ' status-fighting';
        else if (player.status === 'in_lobby') statusClass += ' status-lobby';
        else if (player.status === 'character_select' || player.status === 'weapon_select' || player.status === 'stage_select') statusClass += ' status-select';
        else statusClass += ' status-online';

        // Action buttons
        var actions = '';
        if (!isMe) {
            if (player.joinable && player.room_code) {
                actions += '<button class="player-action-btn join-btn" data-room="' + player.room_code + '" data-game-url="' + (player.game_url || '') + '" title="Join Room">' +
                    '&#x2694;' + '</button>';
            }
            if (player.spectatable) {
                actions += '<button class="player-action-btn spectate-btn" data-player-id="' + player.id + '" title="Spectate">' +
                    '&#x1F441;' + '</button>';
            }
        }

        return '<div class="player-entry' + (isMe ? ' is-you' : '') + '">' +
            '<div class="' + dotClass + '"></div>' +
            '<div class="player-info">' +
                '<div class="player-name">' + this._escHtml(player.name) + (isMe ? '<span class="you-tag">(YOU)</span>' : '') + '</div>' +
                '<div class="player-game">' + this._escHtml(player.game) + '</div>' +
                '<div class="' + statusClass + '">' + statusText + '</div>' +
            '</div>' +
            (actions ? '<div class="player-actions">' + actions + '</div>' : '') +
        '</div>';
    },

    _presenceStatusLabel: function(status) {
        var labels = {
            'online': 'Online',
            'choosing_mode': 'Choosing Mode',
            'character_select': 'Picking Fighter',
            'weapon_select': 'Picking Weapon',
            'stage_select': 'Picking Stage',
            'fighting': 'In Battle',
            'results': 'Match Results',
            'in_lobby': 'In Lobby',
            'playing': 'Playing',
            'idle': 'Idle'
        };
        return labels[status] || status;
    },

    _escHtml: function(str) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    },

    _bindPlayerActions: function() {
        var self = this;

        // Join buttons
        var joinBtns = document.querySelectorAll('.player-action-btn.join-btn');
        for (var i = 0; i < joinBtns.length; i++) {
            (function(btn) {
                btn.onclick = function() {
                    var roomCode = btn.getAttribute('data-room');
                    var gameUrl = btn.getAttribute('data-game-url');
                    if (gameUrl && gameUrl !== '/FIGHTGAME/' && gameUrl !== '') {
                        // Different game — navigate there
                        window.location.href = gameUrl;
                        return;
                    }
                    // Same game (Shadow Arena) — go to lobby and auto-join
                    self.showScreen('online-lobby-screen');
                    var codeInput = document.getElementById('room-code-input');
                    if (codeInput) codeInput.value = roomCode;
                    setTimeout(function() { self._joinOnlineRoom(); }, 300);
                };
            })(joinBtns[i]);
        }

        // Spectate buttons
        var specBtns = document.querySelectorAll('.player-action-btn.spectate-btn');
        for (var j = 0; j < specBtns.length; j++) {
            (function(btn) {
                btn.onclick = function() {
                    var statusEl = document.getElementById('online-status');
                    if (statusEl) statusEl.textContent = 'Spectating coming soon!';
                    self.showScreen('online-lobby-screen');
                };
            })(specBtns[j]);
        }
    },

    // === ONLINE ===
    _createOnlineRoom: function() {
        var statusEl = document.getElementById('online-status');
        if (statusEl) statusEl.textContent = 'Creating room...';

        OnlineManager.createRoom(function(code) {
            if (statusEl) statusEl.innerHTML = 'Room Code: <strong style="color:#ffd700;font-size:28px;letter-spacing:4px;">' + code + '</strong><br>Share this code with your opponent. Waiting for them to join...';
            // Mark as joinable in presence so others see the room
            PresenceManager.setStatus('in_lobby', code, true, false);
        });

        OnlineManager.onConnected = function() {
            if (statusEl) statusEl.textContent = 'Opponent connected! Starting match...';
            // No longer joinable
            PresenceManager.setStatus('fighting', '', false, false);
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
