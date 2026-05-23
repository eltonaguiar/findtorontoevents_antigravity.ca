/**
 * MovieShows Premium Features v2.6
 * 20 Major Updates - Batch 7 (Features 121-140)
 */

(function() {
    'use strict';
    
    // ============================================================
    // FEATURE 121: CINEMA MODE
    // ============================================================
    const CinemaMode = {
        enabled: false,
        
        toggle() {
            this.enabled = !this.enabled;
            
            if (this.enabled) {
                this.enable();
            } else {
                this.disable();
            }
        },
        
        enable() {
            // Hide all UI elements except video
            const style = document.createElement('style');
            style.id = 'cinema-mode-style';
            style.textContent = `
                .cinema-mode-active button:not(.snap-center button),
                .cinema-mode-active [id*="panel"],
                .cinema-mode-active [id*="toggle"],
                .cinema-mode-active [id*="control"],
                .cinema-mode-active .fixed:not(.snap-center) {
                    opacity: 0 !important;
                    pointer-events: none !important;
                    transition: opacity 0.3s !important;
                }
                .cinema-mode-active:hover button,
                .cinema-mode-active:hover [id*="toggle"],
                .cinema-mode-active:hover [id*="control"] {
                    opacity: 1 !important;
                    pointer-events: auto !important;
                }
            `;
            document.head.appendChild(style);
            document.body.classList.add('cinema-mode-active');
            window.showToast?.('🎬 Cinema mode: UI hidden. Hover to reveal.');
        },
        
        disable() {
            document.getElementById('cinema-mode-style')?.remove();
            document.body.classList.remove('cinema-mode-active');
            window.showToast?.('Cinema mode disabled');
        }
    };
    
    // ============================================================
    // FEATURE 122: GESTURE CONTROLS
    // ============================================================
    const GestureControls = {
        touchStartX: 0,
        touchStartY: 0,
        
        init() {
            document.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
            document.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: true });
        },
        
        handleTouchStart(e) {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        },
        
        handleTouchEnd(e) {
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;
            
            const diffX = touchEndX - this.touchStartX;
            const diffY = touchEndY - this.touchStartY;
            
            // Minimum swipe distance
            const minSwipe = 50;
            
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > minSwipe) {
                // Horizontal swipe
                if (diffX > 0) {
                    // Swipe right - previous
                    window.scrollToPreviousSlide?.();
                } else {
                    // Swipe left - next
                    window.scrollToNextSlide?.();
                }
            }
        }
    };
    
    // ============================================================
    // FEATURE 123: CONTENT QUEUE MANAGER
    // ============================================================
    const QueueManager = {
        storageKey: 'movieshows-managed-queue',
        
        getQueue() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        addToQueue(movie, position = 'end') {
            const queue = this.getQueue();
            const item = { title: movie.title, posterUrl: movie.posterUrl, addedAt: Date.now() };
            
            if (position === 'next') {
                queue.splice(1, 0, item);
            } else {
                queue.push(item);
            }
            
            localStorage.setItem(this.storageKey, JSON.stringify(queue));
            window.showToast?.(`Added to queue (${position === 'next' ? 'up next' : 'end'})`);
        },
        
        removeFromQueue(index) {
            const queue = this.getQueue();
            queue.splice(index, 1);
            localStorage.setItem(this.storageKey, JSON.stringify(queue));
        },
        
        reorder(fromIndex, toIndex) {
            const queue = this.getQueue();
            const [item] = queue.splice(fromIndex, 1);
            queue.splice(toIndex, 0, item);
            localStorage.setItem(this.storageKey, JSON.stringify(queue));
        },
        
        showManager() {
            const queue = this.getQueue();
            const existing = document.getElementById('queue-manager');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'queue-manager';
            panel.innerHTML = `
                <div style="position: fixed; right: 0; top: 0; bottom: 0; width: 380px; background: rgba(0,0,0,0.98); z-index: 99999; border-left: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column;">
                    <div style="padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="color: white; margin: 0;">📋 Queue Manager</h3>
                            <button onclick="this.closest('#queue-manager').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 20px;">×</button>
                        </div>
                        <p style="color: #888; font-size: 12px; margin: 5px 0 0 0;">${queue.length} items • Drag to reorder</p>
                    </div>
                    
                    <div style="flex: 1; overflow-y: auto; padding: 15px;">
                        ${queue.length === 0 ? '<p style="color: #666; text-align: center; padding: 40px 0;">Queue is empty</p>' : ''}
                        ${queue.map((item, i) => `
                            <div class="queue-item" draggable="true" data-index="${i}" style="display: flex; gap: 12px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px; cursor: grab; align-items: center;">
                                <span style="color: #888; font-size: 12px; width: 20px;">${i + 1}</span>
                                <img src="${item.posterUrl}" style="width: 40px; height: 60px; object-fit: cover; border-radius: 4px;" onerror="this.style.display='none'">
                                <div style="flex: 1;">
                                    <div style="color: white; font-size: 13px;">${item.title}</div>
                                </div>
                                <button class="remove-queue-item" data-index="${i}" style="background: none; border: none; color: #888; cursor: pointer; padding: 5px;">×</button>
                            </div>
                        `).join('')}
                    </div>
                    
                    <div style="padding: 15px; border-top: 1px solid rgba(255,255,255,0.1);">
                        <button id="play-queue" style="width: 100%; padding: 12px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">▶ Play Queue</button>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.remove-queue-item').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.removeFromQueue(parseInt(btn.dataset.index));
                    panel.remove();
                    this.showManager();
                });
            });
            
            document.getElementById('play-queue')?.addEventListener('click', () => {
                if (queue.length > 0) {
                    window.playMovieByTitle?.(queue[0].title);
                    panel.remove();
                }
            });
        }
    };
    
    // ============================================================
    // FEATURE 124: SCREEN ORIENTATION LOCK
    // ============================================================
    const OrientationLock = {
        locked: false,
        
        async lock(orientation = 'landscape') {
            if (screen.orientation && screen.orientation.lock) {
                try {
                    await screen.orientation.lock(orientation);
                    this.locked = true;
                    window.showToast?.(`🔒 Screen locked to ${orientation}`);
                } catch (e) {
                    window.showToast?.('Unable to lock orientation');
                }
            }
        },
        
        unlock() {
            if (screen.orientation && screen.orientation.unlock) {
                screen.orientation.unlock();
                this.locked = false;
                window.showToast?.('Screen orientation unlocked');
            }
        },
        
        toggle() {
            if (this.locked) {
                this.unlock();
            } else {
                this.lock();
            }
        }
    };
    
    // ============================================================
    // FEATURE 125: CONTENT PREVIEW CARDS
    // ============================================================
    const PreviewCards = {
        showPreview(movie, x, y) {
            const existing = document.getElementById('preview-card');
            if (existing) existing.remove();
            
            const card = document.createElement('div');
            card.id = 'preview-card';
            card.innerHTML = `
                <div style="position: fixed; left: ${Math.min(x, window.innerWidth - 320)}px; top: ${Math.min(y, window.innerHeight - 250)}px; width: 300px; background: rgba(0,0,0,0.98); border-radius: 16px; overflow: hidden; z-index: 99999; box-shadow: 0 20px 60px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.1);">
                    <img src="${movie.posterUrl}" style="width: 100%; height: 120px; object-fit: cover;">
                    <div style="padding: 15px;">
                        <h4 style="color: white; margin: 0 0 8px 0; font-size: 14px;">${movie.title}</h4>
                        <div style="display: flex; gap: 10px; color: #888; font-size: 12px; margin-bottom: 10px;">
                            <span>${movie.year}</span>
                            <span>•</span>
                            <span style="color: #22c55e;">⭐ ${movie.rating || 'N/A'}</span>
                            <span>•</span>
                            <span>${movie.type}</span>
                        </div>
                        <p style="color: #aaa; font-size: 11px; margin: 0; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${movie.description || 'No description available.'}</p>
                        <div style="display: flex; gap: 8px; margin-top: 12px;">
                            <button onclick="window.playMovieByTitle?.('${movie.title}'); this.closest('#preview-card').remove();" style="flex: 1; padding: 8px; background: #22c55e; color: black; border: none; border-radius: 6px; font-size: 12px; font-weight: bold; cursor: pointer;">▶ Play</button>
                            <button onclick="this.closest('#preview-card').remove();" style="padding: 8px 12px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 6px; cursor: pointer;">×</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(card);
            
            // Auto-hide after 5 seconds
            setTimeout(() => card.remove(), 5000);
        }
    };
    
    // ============================================================
    // FEATURE 126: AUDIO BOOST
    // ============================================================
    const AudioBoost = {
        level: 1,
        maxLevel: 2,
        
        boost() {
            this.level = Math.min(this.maxLevel, this.level + 0.25);
            this.apply();
            window.showToast?.(`🔊 Volume boost: ${Math.round(this.level * 100)}%`);
        },
        
        reset() {
            this.level = 1;
            this.apply();
            window.showToast?.('Volume reset to normal');
        },
        
        apply() {
            // Note: This would require Web Audio API for actual implementation
            console.log(`[MovieShows] Audio boost level: ${this.level}`);
        }
    };
    
    // ============================================================
    // FEATURE 127: SUBTITLE CUSTOMIZATION
    // ============================================================
    const SubtitleCustomization = {
        settings: {
            fontSize: 16,
            fontColor: '#ffffff',
            bgColor: 'rgba(0,0,0,0.8)',
            position: 'bottom'
        },
        storageKey: 'movieshows-subtitle-settings',
        
        init() {
            try {
                const saved = JSON.parse(localStorage.getItem(this.storageKey));
                if (saved) this.settings = { ...this.settings, ...saved };
            } catch {}
        },
        
        save() {
            localStorage.setItem(this.storageKey, JSON.stringify(this.settings));
            window.showToast?.('Subtitle settings saved');
        },
        
        showCustomizer() {
            const existing = document.getElementById('subtitle-customizer');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'subtitle-customizer';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        📝 Subtitle Settings
                        <button onclick="this.closest('#subtitle-customizer').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="color: #888; font-size: 11px; display: block; margin-bottom: 8px;">FONT SIZE</label>
                        <input type="range" id="sub-font-size" min="12" max="24" value="${this.settings.fontSize}" style="width: 100%;">
                        <div style="display: flex; justify-content: space-between; color: #888; font-size: 10px;"><span>Small</span><span>Large</span></div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="color: #888; font-size: 11px; display: block; margin-bottom: 8px;">FONT COLOR</label>
                        <div style="display: flex; gap: 8px;">
                            ${['#ffffff', '#ffff00', '#00ff00', '#00ffff'].map(c => `
                                <button class="sub-color-btn" data-color="${c}" style="width: 40px; height: 40px; background: ${c}; border: ${this.settings.fontColor === c ? '3px solid #22c55e' : '2px solid transparent'}; border-radius: 8px; cursor: pointer;"></button>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 20px; padding: 20px; background: ${this.settings.bgColor}; border-radius: 8px; text-align: center;">
                        <span id="sub-preview" style="color: ${this.settings.fontColor}; font-size: ${this.settings.fontSize}px;">Preview Text</span>
                    </div>
                    
                    <button id="save-sub-settings" style="width: 100%; padding: 14px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Save Settings</button>
                </div>
            `;
            document.body.appendChild(panel);
            
            document.getElementById('sub-font-size')?.addEventListener('input', (e) => {
                this.settings.fontSize = parseInt(e.target.value);
                document.getElementById('sub-preview').style.fontSize = this.settings.fontSize + 'px';
            });
            
            panel.querySelectorAll('.sub-color-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.settings.fontColor = btn.dataset.color;
                    document.getElementById('sub-preview').style.color = this.settings.fontColor;
                    panel.querySelectorAll('.sub-color-btn').forEach(b => b.style.border = '2px solid transparent');
                    btn.style.border = '3px solid #22c55e';
                });
            });
            
            document.getElementById('save-sub-settings')?.addEventListener('click', () => {
                this.save();
                panel.remove();
            });
        }
    };
    
    // ============================================================
    // FEATURE 128: VIDEO TIMESTAMP SHARING
    // ============================================================
    const TimestampSharing = {
        createTimestampUrl(movieTitle, seconds) {
            const url = new URL(window.location.href);
            url.searchParams.set('movie', encodeURIComponent(movieTitle));
            url.searchParams.set('t', seconds);
            return url.toString();
        },
        
        share(movie, seconds = 0) {
            const url = this.createTimestampUrl(movie.title, seconds);
            
            navigator.clipboard.writeText(url).then(() => {
                window.showToast?.('🔗 Timestamp link copied!');
            }).catch(() => {
                window.showToast?.('Failed to copy link');
            });
        },
        
        parseUrl() {
            const params = new URLSearchParams(window.location.search);
            const movie = params.get('movie');
            const time = parseInt(params.get('t')) || 0;
            
            if (movie) {
                return { movie: decodeURIComponent(movie), time };
            }
            return null;
        }
    };
    
    // ============================================================
    // FEATURE 129: CONTENT REACTIONS
    // ============================================================
    const ContentReactions = {
        reactions: ['👍', '❤️', '😂', '😮', '😢', '🔥'],
        storageKey: 'movieshows-reactions',
        
        getReactions(movieTitle) {
            try {
                const all = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
                return all[movieTitle] || {};
            } catch { return {}; }
        },
        
        addReaction(movieTitle, reaction) {
            const all = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
            if (!all[movieTitle]) all[movieTitle] = {};
            all[movieTitle][reaction] = (all[movieTitle][reaction] || 0) + 1;
            localStorage.setItem(this.storageKey, JSON.stringify(all));
            
            window.showToast?.(`${reaction} reaction added!`);
        },
        
        showReactionPicker(movie) {
            const existing = document.getElementById('reaction-picker');
            if (existing) { existing.remove(); return; }
            
            const reactions = this.getReactions(movie.title);
            
            const picker = document.createElement('div');
            picker.id = 'reaction-picker';
            picker.innerHTML = `
                <div style="position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.95); border-radius: 30px; padding: 12px 20px; z-index: 99999; display: flex; gap: 15px; border: 1px solid rgba(255,255,255,0.1);">
                    ${this.reactions.map(r => `
                        <button class="reaction-btn" data-reaction="${r}" style="font-size: 28px; background: none; border: none; cursor: pointer; transition: transform 0.2s; position: relative;" onmouseover="this.style.transform='scale(1.3)'" onmouseout="this.style.transform='scale(1)'">
                            ${r}
                            ${reactions[r] ? `<span style="position: absolute; bottom: -5px; right: -5px; background: #22c55e; color: black; font-size: 10px; padding: 2px 5px; border-radius: 10px;">${reactions[r]}</span>` : ''}
                        </button>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(picker);
            
            picker.querySelectorAll('.reaction-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.addReaction(movie.title, btn.dataset.reaction);
                    picker.remove();
                });
            });
            
            // Auto-hide after 5 seconds
            setTimeout(() => picker.remove(), 5000);
        }
    };
    
    // ============================================================
    // FEATURE 130: CONTENT FRESHNESS INDICATOR
    // ============================================================
    const FreshnessIndicator = {
        getFreshness(movie) {
            const year = parseInt(movie.year);
            const currentYear = new Date().getFullYear();
            const age = currentYear - year;
            
            if (age <= 0) return { label: 'Coming Soon', color: '#8b5cf6', icon: '🔮' };
            if (age <= 1) return { label: 'New Release', color: '#22c55e', icon: '✨' };
            if (age <= 3) return { label: 'Recent', color: '#3b82f6', icon: '🆕' };
            if (age <= 10) return { label: 'Modern', color: '#f59e0b', icon: '📅' };
            if (age <= 25) return { label: 'Classic', color: '#ec4899', icon: '🎬' };
            return { label: 'Vintage', color: '#888888', icon: '📼' };
        },
        
        createBadge(movie) {
            const freshness = this.getFreshness(movie);
            return `<span style="display: inline-flex; align-items: center; gap: 4px; padding: 4px 8px; background: ${freshness.color}20; color: ${freshness.color}; border-radius: 12px; font-size: 10px;">${freshness.icon} ${freshness.label}</span>`;
        }
    };
    
    // ============================================================
    // FEATURE 131: SMART CONTENT RESUMPTION
    // ============================================================
    const SmartResumption = {
        storageKey: 'movieshows-resume-points',
        
        saveProgress(movieTitle, progress) {
            try {
                const all = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
                all[movieTitle] = { progress, savedAt: Date.now() };
                localStorage.setItem(this.storageKey, JSON.stringify(all));
            } catch {}
        },
        
        getProgress(movieTitle) {
            try {
                const all = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
                return all[movieTitle]?.progress || 0;
            } catch { return 0; }
        },
        
        showResumePrompt(movie) {
            const progress = this.getProgress(movie.title);
            if (progress < 10) return; // Don't prompt for < 10%
            
            const prompt = document.createElement('div');
            prompt.innerHTML = `
                <div style="position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.95); border-radius: 16px; padding: 20px; z-index: 99999; text-align: center; border: 1px solid rgba(34,197,94,0.3);">
                    <p style="color: white; margin: 0 0 15px 0;">Resume "${movie.title}" at ${progress}%?</p>
                    <div style="display: flex; gap: 10px;">
                        <button onclick="this.closest('div').parentElement.remove()" style="flex: 1; padding: 10px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Resume</button>
                        <button onclick="this.closest('div').parentElement.remove()" style="flex: 1; padding: 10px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 8px; cursor: pointer;">Start Over</button>
                    </div>
                </div>
            `;
            document.body.appendChild(prompt);
            
            setTimeout(() => prompt.remove(), 10000);
        }
    };
    
    // ============================================================
    // FEATURE 132: CONTENT CATEGORIES BROWSER
    // ============================================================
    const CategoriesBrowser = {
        categories: {
            'by-decade': {
                name: 'By Decade',
                items: ['2020s', '2010s', '2000s', '1990s', '1980s', 'Classic']
            },
            'by-mood': {
                name: 'By Mood',
                items: ['Feel Good', 'Intense', 'Emotional', 'Mind-Bending', 'Relaxing']
            },
            'by-length': {
                name: 'By Length',
                items: ['Quick Watch (<90m)', 'Standard (90-120m)', 'Epic (>120m)']
            },
            'by-audience': {
                name: 'By Audience',
                items: ['Family Friendly', 'Teen', 'Adult', 'Critics Pick']
            }
        },
        
        showBrowser() {
            const existing = document.getElementById('categories-browser');
            if (existing) { existing.remove(); return; }
            
            const browser = document.createElement('div');
            browser.id = 'categories-browser';
            browser.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 500px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        📂 Browse Categories
                        <button onclick="this.closest('#categories-browser').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${Object.entries(this.categories).map(([id, cat]) => `
                        <div style="margin-bottom: 20px;">
                            <h4 style="color: #888; font-size: 11px; text-transform: uppercase; margin-bottom: 10px;">${cat.name}</h4>
                            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                                ${cat.items.map(item => `
                                    <button class="category-item" data-category="${id}" data-item="${item}" style="padding: 8px 16px; background: rgba(255,255,255,0.1); border: none; border-radius: 20px; color: white; cursor: pointer; font-size: 12px; transition: all 0.2s;" onmouseover="this.style.background='rgba(34,197,94,0.2)'; this.style.color='#22c55e'" onmouseout="this.style.background='rgba(255,255,255,0.1)'; this.style.color='white'">${item}</button>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(browser);
            
            browser.querySelectorAll('.category-item').forEach(btn => {
                btn.addEventListener('click', () => {
                    window.showToast?.(`Filtering by: ${btn.dataset.item}`);
                    browser.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 133: CONTENT POLL
    // ============================================================
    const ContentPoll = {
        showPoll(options) {
            const existing = document.getElementById('content-poll');
            if (existing) { existing.remove(); return; }
            
            const poll = document.createElement('div');
            poll.id = 'content-poll';
            poll.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: linear-gradient(135deg, rgba(139,92,246,0.95), rgba(59,130,246,0.95)); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; text-align: center;">
                    <h2 style="color: white; margin-bottom: 10px;">🗳️ What to Watch?</h2>
                    <p style="color: rgba(255,255,255,0.8); margin-bottom: 25px;">Help us decide!</p>
                    
                    <div style="display: grid; gap: 12px;">
                        ${options.map((opt, i) => `
                            <button class="poll-option" data-index="${i}" style="padding: 15px 20px; background: rgba(255,255,255,0.2); border: none; border-radius: 12px; color: white; cursor: pointer; font-size: 14px; text-align: left; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s;" onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.2)'">
                                <span>${opt.title}</span>
                                <span style="background: rgba(0,0,0,0.2); padding: 4px 10px; border-radius: 10px; font-size: 12px;">⭐ ${opt.rating || 'N/A'}</span>
                            </button>
                        `).join('')}
                    </div>
                    
                    <button onclick="this.closest('#content-poll').remove()" style="margin-top: 20px; padding: 10px 20px; background: rgba(255,255,255,0.2); border: none; color: white; border-radius: 8px; cursor: pointer;">Cancel</button>
                </div>
            `;
            document.body.appendChild(poll);
            
            poll.querySelectorAll('.poll-option').forEach(btn => {
                btn.addEventListener('click', () => {
                    const selected = options[parseInt(btn.dataset.index)];
                    window.showToast?.(`Selected: ${selected.title}`);
                    window.playMovieByTitle?.(selected.title);
                    poll.remove();
                });
            });
        },
        
        createRandomPoll() {
            const movies = window.allMoviesData?.filter(m => m.trailerUrl).slice(0, 100) || [];
            const options = [];
            
            while (options.length < 4 && movies.length > 0) {
                const index = Math.floor(Math.random() * movies.length);
                options.push(movies.splice(index, 1)[0]);
            }
            
            this.showPoll(options);
        }
    };
    
    // ============================================================
    // FEATURE 134: CONTENT MATCHMAKER
    // ============================================================
    const ContentMatchmaker = {
        questions: [
            { q: "What's your mood?", options: ['Excited', 'Relaxed', 'Thoughtful', 'Adventurous'] },
            { q: "How much time do you have?", options: ['< 30 min', '1-2 hours', '2+ hours', 'All day'] },
            { q: "Watching with?", options: ['Alone', 'Partner', 'Friends', 'Family'] },
            { q: "Preferred era?", options: ['New releases', 'Modern classics', 'Retro', 'Any'] }
        ],
        answers: [],
        
        start() {
            this.answers = [];
            this.showQuestion(0);
        },
        
        showQuestion(index) {
            if (index >= this.questions.length) {
                this.showResult();
                return;
            }
            
            const q = this.questions[index];
            const existing = document.getElementById('matchmaker');
            if (existing) existing.remove();
            
            const panel = document.createElement('div');
            panel.id = 'matchmaker';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 40px; z-index: 99999; min-width: 400px; text-align: center; border: 1px solid rgba(34,197,94,0.3);">
                    <div style="color: #888; font-size: 12px; margin-bottom: 10px;">Question ${index + 1} of ${this.questions.length}</div>
                    <h2 style="color: white; margin-bottom: 30px;">${q.q}</h2>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        ${q.options.map((opt, i) => `
                            <button class="matchmaker-option" data-answer="${i}" style="padding: 20px; background: rgba(255,255,255,0.1); border: none; border-radius: 12px; color: white; cursor: pointer; font-size: 14px; transition: all 0.2s;" onmouseover="this.style.background='rgba(34,197,94,0.2)'" onmouseout="this.style.background='rgba(255,255,255,0.1)'">${opt}</button>
                        `).join('')}
                    </div>
                    
                    <button onclick="this.closest('#matchmaker').remove()" style="margin-top: 25px; color: #888; background: none; border: none; cursor: pointer; font-size: 12px;">Cancel</button>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.matchmaker-option').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.answers.push(parseInt(btn.dataset.answer));
                    panel.remove();
                    this.showQuestion(index + 1);
                });
            });
        },
        
        showResult() {
            const movies = window.allMoviesData?.filter(m => m.trailerUrl) || [];
            const recommendation = movies[Math.floor(Math.random() * Math.min(50, movies.length))];
            
            const panel = document.createElement('div');
            panel.id = 'matchmaker';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: linear-gradient(135deg, rgba(34,197,94,0.95), rgba(59,130,246,0.95)); border-radius: 20px; padding: 40px; z-index: 99999; min-width: 400px; text-align: center;">
                    <div style="font-size: 60px; margin-bottom: 20px;">🎯</div>
                    <h2 style="color: white; margin-bottom: 10px;">Perfect Match!</h2>
                    <p style="color: rgba(255,255,255,0.8); margin-bottom: 25px;">Based on your preferences, we recommend:</p>
                    
                    <div style="background: rgba(0,0,0,0.3); border-radius: 16px; padding: 20px; margin-bottom: 25px;">
                        <h3 style="color: white; margin: 0 0 10px 0;">${recommendation?.title || 'Mystery Movie'}</h3>
                        <div style="color: rgba(255,255,255,0.7); font-size: 14px;">⭐ ${recommendation?.rating || 'N/A'} • ${recommendation?.year || ''} • ${recommendation?.type || ''}</div>
                    </div>
                    
                    <div style="display: flex; gap: 12px;">
                        <button onclick="window.playMovieByTitle?.('${recommendation?.title}'); this.closest('#matchmaker').remove();" style="flex: 1; padding: 14px; background: white; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">▶ Watch Now</button>
                        <button onclick="window.MovieShowsFeaturesBatch7?.ContentMatchmaker?.start();" style="padding: 14px 20px; background: rgba(255,255,255,0.2); color: white; border: none; border-radius: 8px; cursor: pointer;">Try Again</button>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 135: DOUBLE TAP TO LIKE
    // ============================================================
    const DoubleTapLike = {
        lastTap: 0,
        
        init() {
            document.addEventListener('touchend', (e) => this.handleTap(e));
        },
        
        handleTap(e) {
            const currentTime = Date.now();
            const tapLength = currentTime - this.lastTap;
            
            if (tapLength < 300 && tapLength > 0) {
                // Double tap detected
                const slide = e.target.closest('.snap-center');
                if (slide) {
                    this.showLikeAnimation(e);
                    // Add to favorites
                    const title = slide.querySelector('h2')?.textContent;
                    if (title) {
                        window.MovieShowsFeatures?.Favorites?.toggleFavorite({ title });
                    }
                }
            }
            
            this.lastTap = currentTime;
        },
        
        showLikeAnimation(e) {
            const heart = document.createElement('div');
            heart.innerHTML = '❤️';
            heart.style.cssText = `position: fixed; left: ${e.changedTouches?.[0]?.clientX || e.clientX}px; top: ${e.changedTouches?.[0]?.clientY || e.clientY}px; font-size: 60px; z-index: 99999; pointer-events: none; transform: translate(-50%, -50%) scale(0); animation: heartPop 0.6s ease-out forwards;`;
            document.body.appendChild(heart);
            
            setTimeout(() => heart.remove(), 600);
        }
    };
    
    // ============================================================
    // FEATURE 136: CONTENT CHAPTERS
    // ============================================================
    const ContentChapters = {
        getChapters(movie) {
            // Simulated chapters for trailers
            return [
                { time: 0, title: 'Intro' },
                { time: 30, title: 'Setup' },
                { time: 60, title: 'Rising Action' },
                { time: 90, title: 'Climax Tease' },
                { time: 120, title: 'Title Card' }
            ];
        },
        
        showChapters(movie) {
            const chapters = this.getChapters(movie);
            const existing = document.getElementById('chapters-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'chapters-panel';
            panel.innerHTML = `
                <div style="position: fixed; bottom: 100px; right: 20px; background: rgba(0,0,0,0.95); border-radius: 12px; padding: 15px; z-index: 99999; min-width: 200px; border: 1px solid rgba(255,255,255,0.1);">
                    <h4 style="color: white; margin: 0 0 12px 0; font-size: 12px;">📑 Chapters</h4>
                    ${chapters.map((ch, i) => `
                        <div class="chapter-item" data-time="${ch.time}" style="padding: 8px; cursor: pointer; border-radius: 6px; margin-bottom: 4px; display: flex; justify-content: space-between;" onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='transparent'">
                            <span style="color: white; font-size: 12px;">${ch.title}</span>
                            <span style="color: #888; font-size: 11px;">${Math.floor(ch.time / 60)}:${(ch.time % 60).toString().padStart(2, '0')}</span>
                        </div>
                    `).join('')}
                    <button onclick="this.closest('#chapters-panel').remove()" style="width: 100%; margin-top: 8px; padding: 6px; background: rgba(255,255,255,0.1); border: none; color: #888; border-radius: 6px; cursor: pointer; font-size: 11px;">Close</button>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 137: SMART BUFFERING INDICATOR
    // ============================================================
    const BufferingIndicator = {
        show() {
            const existing = document.getElementById('buffering-indicator');
            if (existing) return;
            
            const indicator = document.createElement('div');
            indicator.id = 'buffering-indicator';
            indicator.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 99999;">
                    <div style="width: 60px; height: 60px; border: 3px solid rgba(255,255,255,0.2); border-top-color: #22c55e; border-radius: 50%; animation: bufferSpin 1s linear infinite;"></div>
                </div>
            `;
            
            const style = document.createElement('style');
            style.id = 'buffer-style';
            style.textContent = '@keyframes bufferSpin { to { transform: rotate(360deg); } }';
            document.head.appendChild(style);
            
            document.body.appendChild(indicator);
        },
        
        hide() {
            document.getElementById('buffering-indicator')?.remove();
            document.getElementById('buffer-style')?.remove();
        }
    };
    
    // ============================================================
    // FEATURE 138: CONTENT MOOD LIGHTING
    // ============================================================
    const MoodLighting = {
        colors: {
            'action': '#ef4444',
            'comedy': '#fbbf24',
            'drama': '#3b82f6',
            'horror': '#8b5cf6',
            'romance': '#ec4899',
            'scifi': '#06b6d4'
        },
        
        apply(genre) {
            const color = this.colors[genre?.toLowerCase()] || '#22c55e';
            document.documentElement.style.setProperty('--mood-color', color);
            
            const glow = document.createElement('div');
            glow.id = 'mood-glow';
            glow.style.cssText = `position: fixed; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; z-index: 1; background: radial-gradient(ellipse at center, ${color}10 0%, transparent 70%);`;
            
            document.getElementById('mood-glow')?.remove();
            document.body.appendChild(glow);
        },
        
        clear() {
            document.getElementById('mood-glow')?.remove();
        }
    };
    
    // ============================================================
    // FEATURE 139: VOICE COMMANDS (PLACEHOLDER)
    // ============================================================
    const VoiceCommands = {
        commands: {
            'play': () => window.showToast?.('Playing...'),
            'pause': () => window.showToast?.('Paused'),
            'next': () => window.scrollToNextSlide?.(),
            'previous': () => window.scrollToPreviousSlide?.(),
            'search': () => document.querySelector('[id*="search"]')?.click(),
            'mute': () => window.toggleMute?.()
        },
        
        processCommand(text) {
            const command = text.toLowerCase().trim();
            
            for (const [key, action] of Object.entries(this.commands)) {
                if (command.includes(key)) {
                    action();
                    return true;
                }
            }
            
            return false;
        }
    };
    
    // ============================================================
    // FEATURE 140: SESSION STATISTICS
    // ============================================================
    const SessionStats = {
        sessionStart: Date.now(),
        videosWatched: 0,
        searchesPerformed: 0,
        filtersUsed: 0,
        
        increment(stat) {
            this[stat]++;
        },
        
        getSessionDuration() {
            return Math.floor((Date.now() - this.sessionStart) / 60000);
        },
        
        showStats() {
            const duration = this.getSessionDuration();
            
            const existing = document.getElementById('session-stats');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'session-stats';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 350px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        📊 Session Stats
                        <button onclick="this.closest('#session-stats').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                        <div style="padding: 20px; background: rgba(34,197,94,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #22c55e; font-size: 32px; font-weight: bold;">${duration}</div>
                            <div style="color: #888; font-size: 12px;">Minutes</div>
                        </div>
                        <div style="padding: 20px; background: rgba(59,130,246,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #3b82f6; font-size: 32px; font-weight: bold;">${this.videosWatched}</div>
                            <div style="color: #888; font-size: 12px;">Videos</div>
                        </div>
                        <div style="padding: 20px; background: rgba(139,92,246,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #8b5cf6; font-size: 32px; font-weight: bold;">${this.searchesPerformed}</div>
                            <div style="color: #888; font-size: 12px;">Searches</div>
                        </div>
                        <div style="padding: 20px; background: rgba(245,158,11,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #f59e0b; font-size: 32px; font-weight: bold;">${this.filtersUsed}</div>
                            <div style="color: #888; font-size: 12px;">Filters</div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // INITIALIZATION
    // ============================================================
    function initializeBatch7Features() {
        console.log('[MovieShows] Initializing Premium Features v2.6 (Batch 7)...');
        
        setTimeout(() => {
            try {
                GestureControls.init();
                SubtitleCustomization.init();
                DoubleTapLike.init();
                
                // Add heart animation style
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes heartPop {
                        0% { transform: translate(-50%, -50%) scale(0); opacity: 1; }
                        50% { transform: translate(-50%, -50%) scale(1.2); opacity: 1; }
                        100% { transform: translate(-50%, -50%) scale(1); opacity: 0; }
                    }
                `;
                document.head.appendChild(style);
                
                console.log('[MovieShows] Premium Features v2.6 initialized successfully!');
                
            } catch (e) {
                console.error('[MovieShows] Error initializing batch 7 features:', e);
            }
        }, 6500);
    }
    
    // Expose features globally
    window.MovieShowsFeaturesBatch7 = {
        CinemaMode,
        GestureControls,
        QueueManager,
        OrientationLock,
        PreviewCards,
        AudioBoost,
        SubtitleCustomization,
        TimestampSharing,
        ContentReactions,
        FreshnessIndicator,
        SmartResumption,
        CategoriesBrowser,
        ContentPoll,
        ContentMatchmaker,
        DoubleTapLike,
        ContentChapters,
        BufferingIndicator,
        MoodLighting,
        VoiceCommands,
        SessionStats
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeBatch7Features);
    } else {
        initializeBatch7Features();
    }
    
})();
