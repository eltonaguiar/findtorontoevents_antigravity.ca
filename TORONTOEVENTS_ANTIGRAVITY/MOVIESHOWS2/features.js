/**
 * MovieShows Premium Features v2.0
 * 20 Major Updates - Batch 1
 */

(function() {
    'use strict';
    
    // ============================================================
    // FEATURE 1: ADVANCED SEARCH WITH FILTERS
    // ============================================================
    const SearchFilters = {
        currentFilters: {
            genre: 'all',
            year: 'all',
            rating: 'all',
            platform: 'all',
            query: ''
        },
        
        genres: ['Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Drama', 'Family', 'Fantasy', 'Horror', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller', 'War', 'History', 'Biography', 'Music', 'Sport', 'Documentary'],
        years: ['2027', '2026', '2025', '2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017', '2016', '2015', '2010s', '2000s', '1990s', 'Classic'],
        ratings: ['9+', '8+', '7+', '6+', '5+', 'All'],
        platforms: ['Netflix', 'Disney+', 'Max', 'Prime Video', 'Apple TV+', 'Hulu', 'Paramount+', 'Peacock', 'In Theatres', 'All'],
        
        init() {
            this.enhanceSearchPanel();
        },
        
        enhanceSearchPanel() {
            const searchPanel = document.getElementById('search-panel');
            if (!searchPanel) return;
            
            const content = searchPanel.querySelector('.panel-content');
            if (!content) return;
            
            // Check if already enhanced
            if (content.querySelector('#advanced-filters')) return;
            
            const filtersHTML = `
                <div id="advanced-filters" style="margin-bottom: 20px; padding: 15px; background: rgba(255,255,255,0.03); border-radius: 12px;">
                    <h4 style="color: #22c55e; font-size: 12px; text-transform: uppercase; margin-bottom: 12px;">🔍 Advanced Filters</h4>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <div>
                            <label style="color: #888; font-size: 11px; display: block; margin-bottom: 4px;">Genre</label>
                            <select id="filter-genre" style="width: 100%; padding: 8px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: white; font-size: 12px;">
                                <option value="all">All Genres</option>
                                ${this.genres.map(g => `<option value="${g}">${g}</option>`).join('')}
                            </select>
                        </div>
                        
                        <div>
                            <label style="color: #888; font-size: 11px; display: block; margin-bottom: 4px;">Year</label>
                            <select id="filter-year" style="width: 100%; padding: 8px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: white; font-size: 12px;">
                                <option value="all">All Years</option>
                                ${this.years.map(y => `<option value="${y}">${y}</option>`).join('')}
                            </select>
                        </div>
                        
                        <div>
                            <label style="color: #888; font-size: 11px; display: block; margin-bottom: 4px;">Rating</label>
                            <select id="filter-rating" style="width: 100%; padding: 8px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: white; font-size: 12px;">
                                <option value="all">All Ratings</option>
                                ${this.ratings.map(r => `<option value="${r}">${r === 'All' ? 'All Ratings' : r + ' ⭐'}</option>`).join('')}
                            </select>
                        </div>
                        
                        <div>
                            <label style="color: #888; font-size: 11px; display: block; margin-bottom: 4px;">Platform</label>
                            <select id="filter-platform" style="width: 100%; padding: 8px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: white; font-size: 12px;">
                                <option value="all">All Platforms</option>
                                ${this.platforms.filter(p => p !== 'All').map(p => `<option value="${p}">${p}</option>`).join('')}
                            </select>
                        </div>
                    </div>
                    
                    <div style="margin-top: 12px; display: flex; gap: 8px;">
                        <button id="apply-filters" style="flex: 1; padding: 10px; background: #22c55e; color: black; border: none; border-radius: 6px; font-weight: bold; cursor: pointer;">Apply Filters</button>
                        <button id="clear-filters" style="padding: 10px 15px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 6px; cursor: pointer;">Clear</button>
                    </div>
                </div>
            `;
            
            const searchInput = content.querySelector('input');
            if (searchInput) {
                searchInput.parentElement.insertAdjacentHTML('afterend', filtersHTML);
            }
            
            // Add event listeners
            document.getElementById('apply-filters')?.addEventListener('click', () => this.applyFilters());
            document.getElementById('clear-filters')?.addEventListener('click', () => this.clearFilters());
        },
        
        applyFilters() {
            this.currentFilters.genre = document.getElementById('filter-genre')?.value || 'all';
            this.currentFilters.year = document.getElementById('filter-year')?.value || 'all';
            this.currentFilters.rating = document.getElementById('filter-rating')?.value || 'all';
            this.currentFilters.platform = document.getElementById('filter-platform')?.value || 'all';
            
            // Trigger search with filters
            if (window.performAdvancedSearch) {
                window.performAdvancedSearch(this.currentFilters);
            }
            
            window.showToast?.('Filters applied!');
        },
        
        clearFilters() {
            this.currentFilters = { genre: 'all', year: 'all', rating: 'all', platform: 'all', query: '' };
            document.getElementById('filter-genre').value = 'all';
            document.getElementById('filter-year').value = 'all';
            document.getElementById('filter-rating').value = 'all';
            document.getElementById('filter-platform').value = 'all';
            window.showToast?.('Filters cleared!');
        }
    };
    
    // ============================================================
    // FEATURE 2: WATCH HISTORY
    // ============================================================
    const WatchHistory = {
        storageKey: 'movieshows-watch-history',
        maxItems: 100,
        
        getHistory() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        addToHistory(movie) {
            if (!movie?.title) return;
            
            const history = this.getHistory();
            // Remove if exists
            const filtered = history.filter(h => h.title !== movie.title);
            // Add to front with timestamp
            filtered.unshift({
                title: movie.title,
                posterUrl: movie.posterUrl,
                type: movie.type,
                year: movie.year,
                watchedAt: Date.now(),
                progress: 0
            });
            // Limit size
            const trimmed = filtered.slice(0, this.maxItems);
            localStorage.setItem(this.storageKey, JSON.stringify(trimmed));
        },
        
        updateProgress(title, progress) {
            const history = this.getHistory();
            const item = history.find(h => h.title === title);
            if (item) {
                item.progress = progress;
                item.lastWatched = Date.now();
                localStorage.setItem(this.storageKey, JSON.stringify(history));
            }
        },
        
        getRecentlyWatched(limit = 10) {
            return this.getHistory().slice(0, limit);
        },
        
        getContinueWatching() {
            return this.getHistory().filter(h => h.progress > 0 && h.progress < 90).slice(0, 5);
        },
        
        clearHistory() {
            localStorage.removeItem(this.storageKey);
        }
    };
    
    // ============================================================
    // FEATURE 3: CONTINUE WATCHING SECTION
    // ============================================================
    const ContinueWatching = {
        init() {
            this.createSection();
        },
        
        createSection() {
            const continueItems = WatchHistory.getContinueWatching();
            if (continueItems.length === 0) return;
            
            // Add to nav or create floating section
            const existingSection = document.getElementById('continue-watching-section');
            if (existingSection) existingSection.remove();
            
            const section = document.createElement('div');
            section.id = 'continue-watching-section';
            section.innerHTML = `
                <div style="position: fixed; bottom: 80px; left: 20px; background: rgba(0,0,0,0.95); border-radius: 12px; padding: 15px; z-index: 9999; max-width: 300px; border: 1px solid rgba(34,197,94,0.3);">
                    <h4 style="color: #22c55e; font-size: 12px; text-transform: uppercase; margin-bottom: 10px;">▶️ Continue Watching</h4>
                    ${continueItems.map(item => `
                        <div class="continue-item" data-title="${item.title}" style="display: flex; gap: 10px; padding: 8px; cursor: pointer; border-radius: 6px; margin-bottom: 5px; background: rgba(255,255,255,0.05);">
                            <img src="${item.posterUrl || ''}" style="width: 40px; height: 60px; object-fit: cover; border-radius: 4px;" onerror="this.style.display='none'">
                            <div style="flex: 1;">
                                <div style="color: white; font-size: 12px; margin-bottom: 4px;">${item.title}</div>
                                <div style="background: rgba(255,255,255,0.2); height: 4px; border-radius: 2px;">
                                    <div style="background: #22c55e; height: 100%; width: ${item.progress}%; border-radius: 2px;"></div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                    <button id="dismiss-continue" style="width: 100%; padding: 8px; background: transparent; border: 1px solid rgba(255,255,255,0.2); color: #888; border-radius: 6px; cursor: pointer; margin-top: 8px; font-size: 11px;">Dismiss</button>
                </div>
            `;
            document.body.appendChild(section);
            
            // Event listeners
            section.querySelectorAll('.continue-item').forEach(item => {
                item.addEventListener('click', () => {
                    const title = item.dataset.title;
                    window.playMovieByTitle?.(title);
                    section.remove();
                });
            });
            
            document.getElementById('dismiss-continue')?.addEventListener('click', () => section.remove());
        }
    };
    
    // ============================================================
    // FEATURE 4: KEYBOARD SHORTCUTS
    // ============================================================
    const KeyboardShortcuts = {
        shortcuts: {
            'Space': 'Play/Pause',
            'ArrowUp': 'Previous video',
            'ArrowDown': 'Next video',
            'ArrowLeft': 'Rewind 10s',
            'ArrowRight': 'Forward 10s',
            'm': 'Toggle mute',
            'f': 'Toggle fullscreen',
            's': 'Open search',
            'q': 'Open queue',
            'r': 'Random video',
            '?': 'Show shortcuts',
            'Escape': 'Close panels'
        },
        
        init() {
            document.addEventListener('keydown', (e) => this.handleKeydown(e));
        },
        
        handleKeydown(e) {
            // Don't trigger if typing in input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            
            const key = e.key;
            
            switch(key) {
                case ' ':
                    e.preventDefault();
                    this.togglePlayPause();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    window.scrollToPreviousSlide?.();
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    window.scrollToNextSlide?.();
                    break;
                case 'm':
                case 'M':
                    window.toggleMute?.();
                    break;
                case 'f':
                case 'F':
                    this.toggleFullscreen();
                    break;
                case 's':
                case 'S':
                    document.querySelector('[id*="search"]')?.click();
                    break;
                case 'q':
                case 'Q':
                    document.querySelector('button[name*="Queue"], button:has-text("Queue")')?.click();
                    break;
                case 'r':
                case 'R':
                    RandomShuffle.playRandom();
                    break;
                case '?':
                    this.showShortcutsHelp();
                    break;
                case 'Escape':
                    this.closeAllPanels();
                    break;
            }
        },
        
        togglePlayPause() {
            const playBtn = document.querySelector('button:has-text("▶"), button:has-text("⏸")');
            playBtn?.click();
        },
        
        toggleFullscreen() {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                document.documentElement.requestFullscreen();
            }
        },
        
        closeAllPanels() {
            document.querySelectorAll('[style*="right: 0"]').forEach(panel => {
                if (panel.style) panel.style.right = '-400px';
            });
        },
        
        showShortcutsHelp() {
            const existing = document.getElementById('shortcuts-help');
            if (existing) { existing.remove(); return; }
            
            const help = document.createElement('div');
            help.id = 'shortcuts-help';
            help.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.95); border-radius: 16px; padding: 25px; z-index: 99999; min-width: 350px; border: 1px solid rgba(34,197,94,0.3);">
                    <h3 style="color: #22c55e; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
                        ⌨️ Keyboard Shortcuts
                        <button onclick="this.closest('#shortcuts-help').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 20px;">×</button>
                    </h3>
                    <div style="display: grid; gap: 8px;">
                        ${Object.entries(this.shortcuts).map(([key, action]) => `
                            <div style="display: flex; justify-content: space-between; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 6px;">
                                <span style="color: white;">${action}</span>
                                <kbd style="background: rgba(34,197,94,0.2); color: #22c55e; padding: 4px 10px; border-radius: 4px; font-family: monospace;">${key}</kbd>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(help);
        }
    };
    
    // ============================================================
    // FEATURE 5: AUTOPLAY SETTINGS
    // ============================================================
    const AutoplaySettings = {
        storageKey: 'movieshows-autoplay',
        
        isEnabled() {
            return localStorage.getItem(this.storageKey) !== 'false';
        },
        
        toggle() {
            const current = this.isEnabled();
            localStorage.setItem(this.storageKey, !current);
            window.showToast?.(current ? 'Autoplay disabled' : 'Autoplay enabled');
            return !current;
        },
        
        init() {
            // Add autoplay toggle to settings
            this.addToggleToSettings();
        },
        
        addToggleToSettings() {
            const settingsPanel = document.getElementById('player-size-control');
            if (!settingsPanel || settingsPanel.querySelector('#autoplay-toggle')) return;
            
            const toggle = document.createElement('div');
            toggle.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-top: 10px;">
                    <span style="color: white; font-size: 13px;">▶️ Autoplay Next</span>
                    <button id="autoplay-toggle" style="padding: 6px 12px; background: ${this.isEnabled() ? '#22c55e' : 'rgba(255,255,255,0.2)'}; color: ${this.isEnabled() ? 'black' : 'white'}; border: none; border-radius: 4px; cursor: pointer; font-size: 11px;">${this.isEnabled() ? 'ON' : 'OFF'}</button>
                </div>
            `;
            settingsPanel.appendChild(toggle);
            
            document.getElementById('autoplay-toggle')?.addEventListener('click', (e) => {
                const enabled = this.toggle();
                e.target.textContent = enabled ? 'ON' : 'OFF';
                e.target.style.background = enabled ? '#22c55e' : 'rgba(255,255,255,0.2)';
                e.target.style.color = enabled ? 'black' : 'white';
            });
        }
    };
    
    // ============================================================
    // FEATURE 6: SLEEP TIMER
    // ============================================================
    const SleepTimer = {
        timerId: null,
        endTime: null,
        
        set(minutes) {
            this.clear();
            this.endTime = Date.now() + (minutes * 60 * 1000);
            this.timerId = setTimeout(() => {
                window.forceStopAllVideos?.();
                window.showToast?.('Sleep timer: Videos paused');
                this.showSleepNotification();
            }, minutes * 60 * 1000);
            
            window.showToast?.(`Sleep timer set for ${minutes} minutes`);
            this.updateDisplay();
        },
        
        clear() {
            if (this.timerId) {
                clearTimeout(this.timerId);
                this.timerId = null;
                this.endTime = null;
            }
        },
        
        getRemaining() {
            if (!this.endTime) return null;
            const remaining = Math.max(0, this.endTime - Date.now());
            return Math.ceil(remaining / 60000);
        },
        
        updateDisplay() {
            // Update any UI showing timer status
            const display = document.getElementById('sleep-timer-display');
            if (display && this.endTime) {
                const interval = setInterval(() => {
                    const remaining = this.getRemaining();
                    if (remaining === null || remaining <= 0) {
                        clearInterval(interval);
                        display.textContent = '';
                        return;
                    }
                    display.textContent = `😴 ${remaining}m`;
                }, 60000);
            }
        },
        
        showSleepNotification() {
            const notif = document.createElement('div');
            notif.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.95); border-radius: 16px; padding: 30px; z-index: 99999; text-align: center; border: 1px solid rgba(34,197,94,0.3);">
                    <div style="font-size: 48px; margin-bottom: 15px;">😴</div>
                    <h3 style="color: white; margin-bottom: 10px;">Time to Rest</h3>
                    <p style="color: #888; margin-bottom: 20px;">Your sleep timer has ended.</p>
                    <button onclick="this.closest('div').parentElement.remove()" style="padding: 12px 30px; background: #22c55e; color: black; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">OK</button>
                </div>
            `;
            document.body.appendChild(notif);
        },
        
        createTimerUI() {
            const btn = document.createElement('button');
            btn.id = 'sleep-timer-btn';
            btn.innerHTML = '😴 Sleep';
            btn.style.cssText = 'position: fixed; bottom: 20px; left: 20px; padding: 10px 15px; background: rgba(0,0,0,0.8); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; cursor: pointer; z-index: 9999; font-size: 12px;';
            btn.onclick = () => this.showTimerOptions();
            document.body.appendChild(btn);
        },
        
        showTimerOptions() {
            const existing = document.getElementById('sleep-timer-options');
            if (existing) { existing.remove(); return; }
            
            const options = document.createElement('div');
            options.id = 'sleep-timer-options';
            options.innerHTML = `
                <div style="position: fixed; bottom: 70px; left: 20px; background: rgba(0,0,0,0.95); border-radius: 12px; padding: 15px; z-index: 99999; border: 1px solid rgba(255,255,255,0.2);">
                    <h4 style="color: #22c55e; margin-bottom: 10px; font-size: 12px;">😴 SLEEP TIMER</h4>
                    ${[15, 30, 45, 60, 90, 120].map(m => `
                        <button class="sleep-option" data-minutes="${m}" style="display: block; width: 100%; padding: 8px; margin-bottom: 5px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 6px; cursor: pointer;">${m} minutes</button>
                    `).join('')}
                    <button id="cancel-sleep" style="display: block; width: 100%; padding: 8px; background: rgba(239,68,68,0.2); color: #ef4444; border: none; border-radius: 6px; cursor: pointer;">Cancel Timer</button>
                </div>
            `;
            document.body.appendChild(options);
            
            options.querySelectorAll('.sleep-option').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.set(parseInt(btn.dataset.minutes));
                    options.remove();
                });
            });
            
            document.getElementById('cancel-sleep')?.addEventListener('click', () => {
                this.clear();
                window.showToast?.('Sleep timer cancelled');
                options.remove();
            });
        }
    };
    
    // ============================================================
    // FEATURE 7: PICTURE-IN-PICTURE
    // ============================================================
    const PictureInPicture = {
        miniPlayer: null,
        
        init() {
            this.createPiPButton();
        },
        
        createPiPButton() {
            const existing = document.getElementById('pip-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'pip-btn';
            btn.innerHTML = '🖼️ Mini';
            btn.title = 'Picture-in-Picture';
            btn.style.cssText = 'position: fixed; bottom: 20px; left: 100px; padding: 10px 15px; background: rgba(0,0,0,0.8); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; cursor: pointer; z-index: 9999; font-size: 12px;';
            btn.onclick = () => this.toggle();
            document.body.appendChild(btn);
        },
        
        toggle() {
            if (this.miniPlayer) {
                this.closeMiniPlayer();
            } else {
                this.openMiniPlayer();
            }
        },
        
        openMiniPlayer() {
            const currentIframe = document.querySelector('iframe[src*="youtube"]');
            if (!currentIframe) {
                window.showToast?.('No video playing');
                return;
            }
            
            this.miniPlayer = document.createElement('div');
            this.miniPlayer.id = 'mini-player';
            this.miniPlayer.innerHTML = `
                <div style="position: fixed; bottom: 80px; right: 20px; width: 320px; height: 180px; background: black; border-radius: 12px; overflow: hidden; z-index: 99999; box-shadow: 0 10px 40px rgba(0,0,0,0.5); border: 2px solid rgba(34,197,94,0.5);">
                    <div style="position: absolute; top: 0; left: 0; right: 0; padding: 8px; background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent); display: flex; justify-content: space-between; align-items: center; z-index: 1;">
                        <span style="color: white; font-size: 11px; font-weight: bold;">Mini Player</span>
                        <button id="close-pip" style="background: none; border: none; color: white; cursor: pointer; font-size: 16px;">×</button>
                    </div>
                    <iframe src="${currentIframe.src}" style="width: 100%; height: 100%; border: none;" allow="autoplay; encrypted-media"></iframe>
                </div>
            `;
            document.body.appendChild(this.miniPlayer);
            
            document.getElementById('close-pip')?.addEventListener('click', () => this.closeMiniPlayer());
            
            // Make draggable
            this.makeDraggable(this.miniPlayer.firstElementChild);
        },
        
        closeMiniPlayer() {
            this.miniPlayer?.remove();
            this.miniPlayer = null;
        },
        
        makeDraggable(element) {
            let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
            
            element.onmousedown = dragMouseDown;
            
            function dragMouseDown(e) {
                if (e.target.tagName === 'BUTTON' || e.target.tagName === 'IFRAME') return;
                e.preventDefault();
                pos3 = e.clientX;
                pos4 = e.clientY;
                document.onmouseup = closeDragElement;
                document.onmousemove = elementDrag;
            }
            
            function elementDrag(e) {
                e.preventDefault();
                pos1 = pos3 - e.clientX;
                pos2 = pos4 - e.clientY;
                pos3 = e.clientX;
                pos4 = e.clientY;
                element.style.top = (element.offsetTop - pos2) + "px";
                element.style.left = (element.offsetLeft - pos1) + "px";
                element.style.right = 'auto';
                element.style.bottom = 'auto';
            }
            
            function closeDragElement() {
                document.onmouseup = null;
                document.onmousemove = null;
            }
        }
    };
    
    // ============================================================
    // FEATURE 8: TRENDING SECTION
    // ============================================================
    const TrendingSection = {
        getTrending(limit = 10) {
            const movies = window.allMoviesData || [];
            // Sort by rating and recent year
            return movies
                .filter(m => m.trailerUrl && parseFloat(m.rating) >= 7)
                .sort((a, b) => {
                    const ratingDiff = parseFloat(b.rating || 0) - parseFloat(a.rating || 0);
                    const yearDiff = parseInt(b.year || 0) - parseInt(a.year || 0);
                    return yearDiff * 0.3 + ratingDiff * 0.7;
                })
                .slice(0, limit);
        },
        
        createTrendingCategory() {
            // Add "Trending" to category buttons
            const categoryContainer = document.querySelector('.flex.gap-2');
            if (!categoryContainer || categoryContainer.querySelector('#trending-btn')) return;
            
            const trendingBtn = document.createElement('button');
            trendingBtn.id = 'trending-btn';
            trendingBtn.innerHTML = '🔥 Trending';
            trendingBtn.style.cssText = 'padding: 8px 16px; background: linear-gradient(135deg, #f59e0b, #ef4444); color: white; border: none; border-radius: 20px; cursor: pointer; font-size: 12px; font-weight: bold;';
            trendingBtn.onclick = () => {
                window.currentFilter = 'trending';
                window.repopulateFeedWithFilter?.();
                window.showToast?.('Showing trending content');
            };
            categoryContainer.appendChild(trendingBtn);
        }
    };
    
    // ============================================================
    // FEATURE 9: NEW RELEASES SECTION
    // ============================================================
    const NewReleases = {
        getNewReleases(limit = 10) {
            const movies = window.allMoviesData || [];
            const currentYear = new Date().getFullYear();
            return movies
                .filter(m => m.trailerUrl && (parseInt(m.year) >= currentYear - 1))
                .sort((a, b) => parseInt(b.year || 0) - parseInt(a.year || 0))
                .slice(0, limit);
        },
        
        createNewReleasesCategory() {
            const categoryContainer = document.querySelector('.flex.gap-2');
            if (!categoryContainer || categoryContainer.querySelector('#new-releases-btn')) return;
            
            const newBtn = document.createElement('button');
            newBtn.id = 'new-releases-btn';
            newBtn.innerHTML = '✨ New';
            newBtn.style.cssText = 'padding: 8px 16px; background: linear-gradient(135deg, #8b5cf6, #ec4899); color: white; border: none; border-radius: 20px; cursor: pointer; font-size: 12px; font-weight: bold;';
            newBtn.onclick = () => {
                window.currentFilter = 'new';
                window.repopulateFeedWithFilter?.();
                window.showToast?.('Showing new releases');
            };
            categoryContainer.appendChild(newBtn);
        }
    };
    
    // ============================================================
    // FEATURE 10: RANDOM SHUFFLE
    // ============================================================
    const RandomShuffle = {
        playRandom() {
            const movies = window.allMoviesData || [];
            const valid = movies.filter(m => m.trailerUrl && m.trailerUrl.length > 10);
            if (valid.length === 0) return;
            
            const random = valid[Math.floor(Math.random() * valid.length)];
            window.addMovieToFeed?.(random, true, true);
            window.showToast?.(`🎲 Random pick: ${random.title}`);
        },
        
        createShuffleButton() {
            const existing = document.getElementById('shuffle-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'shuffle-btn';
            btn.innerHTML = '🎲 Shuffle';
            btn.style.cssText = 'position: fixed; bottom: 20px; left: 180px; padding: 10px 15px; background: rgba(0,0,0,0.8); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; cursor: pointer; z-index: 9999; font-size: 12px;';
            btn.onclick = () => this.playRandom();
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 11: DECADE BROWSING
    // ============================================================
    const DecadeBrowsing = {
        decades: ['2020s', '2010s', '2000s', '1990s', '1980s', 'Classic'],
        
        filterByDecade(decade) {
            const movies = window.allMoviesData || [];
            const yearRanges = {
                '2020s': [2020, 2029],
                '2010s': [2010, 2019],
                '2000s': [2000, 2009],
                '1990s': [1990, 1999],
                '1980s': [1980, 1989],
                'Classic': [1900, 1979]
            };
            
            const range = yearRanges[decade];
            if (!range) return movies;
            
            return movies.filter(m => {
                const year = parseInt(m.year);
                return year >= range[0] && year <= range[1];
            });
        },
        
        createDecadeFilters() {
            const filterPanel = document.getElementById('filter-panel');
            if (!filterPanel || filterPanel.querySelector('#decade-filters')) return;
            
            const content = filterPanel.querySelector('.panel-content');
            if (!content) return;
            
            const decadeSection = document.createElement('div');
            decadeSection.id = 'decade-filters';
            decadeSection.innerHTML = `
                <h4 style="color: #22c55e; font-size: 12px; text-transform: uppercase; margin: 20px 0 12px;">📅 Browse by Decade</h4>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    ${this.decades.map(d => `
                        <button class="decade-btn" data-decade="${d}" style="padding: 8px 16px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 20px; cursor: pointer; font-size: 12px;">${d}</button>
                    `).join('')}
                </div>
            `;
            content.appendChild(decadeSection);
            
            decadeSection.querySelectorAll('.decade-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    window.currentFilter = 'decade-' + btn.dataset.decade;
                    window.repopulateFeedWithFilter?.();
                    window.showToast?.(`Showing ${btn.dataset.decade} content`);
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 12: GENRE PAGES
    // ============================================================
    const GenrePages = {
        genres: ['Action', 'Comedy', 'Drama', 'Horror', 'Sci-Fi', 'Romance', 'Thriller', 'Animation', 'Fantasy', 'Adventure'],
        
        filterByGenre(genre) {
            const movies = window.allMoviesData || [];
            return movies.filter(m => m.genres?.some(g => g.toLowerCase().includes(genre.toLowerCase())));
        },
        
        createGenreFilters() {
            const filterPanel = document.getElementById('filter-panel');
            if (!filterPanel || filterPanel.querySelector('#genre-filters')) return;
            
            const content = filterPanel.querySelector('.panel-content');
            if (!content) return;
            
            const genreSection = document.createElement('div');
            genreSection.id = 'genre-filters';
            genreSection.innerHTML = `
                <h4 style="color: #22c55e; font-size: 12px; text-transform: uppercase; margin: 20px 0 12px;">🎭 Browse by Genre</h4>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    ${this.genres.map(g => `
                        <button class="genre-btn" data-genre="${g}" style="padding: 8px 16px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 20px; cursor: pointer; font-size: 12px;">${g}</button>
                    `).join('')}
                </div>
            `;
            content.appendChild(genreSection);
            
            genreSection.querySelectorAll('.genre-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    window.currentFilter = 'genre-' + btn.dataset.genre;
                    window.repopulateFeedWithFilter?.();
                    window.showToast?.(`Showing ${btn.dataset.genre} content`);
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 13: USER RATING SYSTEM
    // ============================================================
    const UserRatings = {
        storageKey: 'movieshows-user-ratings',
        
        getRatings() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '{}');
            } catch { return {}; }
        },
        
        setRating(title, rating) {
            const ratings = this.getRatings();
            ratings[title] = { rating, ratedAt: Date.now() };
            localStorage.setItem(this.storageKey, JSON.stringify(ratings));
            window.showToast?.(`Rated "${title}" ${rating} stars`);
        },
        
        getRating(title) {
            return this.getRatings()[title]?.rating || 0;
        },
        
        createRatingUI(title, container) {
            const existingRating = this.getRating(title);
            
            const ratingDiv = document.createElement('div');
            ratingDiv.className = 'user-rating';
            ratingDiv.style.cssText = 'display: flex; gap: 4px; margin-top: 8px;';
            
            for (let i = 1; i <= 5; i++) {
                const star = document.createElement('button');
                star.innerHTML = i <= existingRating ? '⭐' : '☆';
                star.style.cssText = 'background: none; border: none; cursor: pointer; font-size: 18px; padding: 0;';
                star.onclick = () => {
                    this.setRating(title, i);
                    // Update all stars
                    ratingDiv.querySelectorAll('button').forEach((s, idx) => {
                        s.innerHTML = idx < i ? '⭐' : '☆';
                    });
                };
                ratingDiv.appendChild(star);
            }
            
            container?.appendChild(ratingDiv);
            return ratingDiv;
        }
    };
    
    // ============================================================
    // FEATURE 14: PERSISTENT FAVORITES
    // ============================================================
    const Favorites = {
        storageKey: 'movieshows-favorites',
        
        getFavorites() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        isFavorite(title) {
            return this.getFavorites().some(f => f.title === title);
        },
        
        toggleFavorite(movie) {
            const favorites = this.getFavorites();
            const index = favorites.findIndex(f => f.title === movie.title);
            
            if (index >= 0) {
                favorites.splice(index, 1);
                window.showToast?.(`Removed "${movie.title}" from favorites`);
            } else {
                favorites.unshift({
                    title: movie.title,
                    posterUrl: movie.posterUrl,
                    type: movie.type,
                    year: movie.year,
                    addedAt: Date.now()
                });
                window.showToast?.(`Added "${movie.title}" to favorites`);
            }
            
            localStorage.setItem(this.storageKey, JSON.stringify(favorites));
            this.updateFavoriteButtons();
        },
        
        updateFavoriteButtons() {
            document.querySelectorAll('.favorite-btn').forEach(btn => {
                const title = btn.dataset.title;
                const isFav = this.isFavorite(title);
                btn.innerHTML = isFav ? '❤️' : '🤍';
                btn.title = isFav ? 'Remove from favorites' : 'Add to favorites';
            });
        }
    };
    
    // ============================================================
    // FEATURE 15: PWA SUPPORT
    // ============================================================
    const PWASupport = {
        init() {
            this.createManifest();
            this.registerServiceWorker();
            this.addInstallPrompt();
        },
        
        createManifest() {
            const manifest = {
                name: 'MovieShows',
                short_name: 'MovieShows',
                description: 'Discover Your Next Obsession',
                start_url: '/',
                display: 'standalone',
                background_color: '#000000',
                theme_color: '#22c55e',
                icons: [
                    { src: 'https://eltonaguiar.github.io/MOVIESHOWS2_CURSORNOSCROLLINGBUG/icon-192.png', sizes: '192x192', type: 'image/png' },
                    { src: 'https://eltonaguiar.github.io/MOVIESHOWS2_CURSORNOSCROLLINGBUG/icon-512.png', sizes: '512x512', type: 'image/png' }
                ]
            };
            
            const blob = new Blob([JSON.stringify(manifest)], { type: 'application/json' });
            const manifestLink = document.querySelector('link[rel="manifest"]') || document.createElement('link');
            manifestLink.rel = 'manifest';
            manifestLink.href = URL.createObjectURL(blob);
            if (!document.querySelector('link[rel="manifest"]')) {
                document.head.appendChild(manifestLink);
            }
        },
        
        async registerServiceWorker() {
            if ('serviceWorker' in navigator) {
                try {
                    // Service worker would need to be a separate file
                    console.log('[MovieShows] PWA support initialized');
                } catch (e) {
                    console.error('[MovieShows] SW registration failed:', e);
                }
            }
        },
        
        addInstallPrompt() {
            let deferredPrompt;
            
            window.addEventListener('beforeinstallprompt', (e) => {
                e.preventDefault();
                deferredPrompt = e;
                this.showInstallButton(deferredPrompt);
            });
        },
        
        showInstallButton(deferredPrompt) {
            const existing = document.getElementById('install-app-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'install-app-btn';
            btn.innerHTML = '📱 Install App';
            btn.style.cssText = 'position: fixed; top: 80px; right: 20px; padding: 10px 15px; background: linear-gradient(135deg, #22c55e, #16a34a); color: white; border: none; border-radius: 8px; cursor: pointer; z-index: 9999; font-size: 12px; font-weight: bold; box-shadow: 0 4px 15px rgba(34,197,94,0.3);';
            btn.onclick = async () => {
                deferredPrompt.prompt();
                const { outcome } = await deferredPrompt.userChoice;
                if (outcome === 'accepted') {
                    btn.remove();
                }
            };
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 16: THEME TOGGLE
    // ============================================================
    const ThemeToggle = {
        storageKey: 'movieshows-theme',
        
        getTheme() {
            return localStorage.getItem(this.storageKey) || 'dark';
        },
        
        setTheme(theme) {
            localStorage.setItem(this.storageKey, theme);
            document.documentElement.setAttribute('data-theme', theme);
            this.applyTheme(theme);
        },
        
        toggle() {
            const current = this.getTheme();
            const newTheme = current === 'dark' ? 'light' : 'dark';
            this.setTheme(newTheme);
            window.showToast?.(`${newTheme === 'dark' ? '🌙' : '☀️'} ${newTheme.charAt(0).toUpperCase() + newTheme.slice(1)} mode`);
        },
        
        applyTheme(theme) {
            const root = document.documentElement;
            if (theme === 'light') {
                root.style.setProperty('--bg-primary', '#f5f5f5');
                root.style.setProperty('--bg-secondary', '#ffffff');
                root.style.setProperty('--text-primary', '#1a1a1a');
                root.style.setProperty('--text-secondary', '#666666');
            } else {
                root.style.setProperty('--bg-primary', '#0a0a0a');
                root.style.setProperty('--bg-secondary', '#1a1a2e');
                root.style.setProperty('--text-primary', '#ffffff');
                root.style.setProperty('--text-secondary', '#888888');
            }
        },
        
        createToggleButton() {
            const existing = document.getElementById('theme-toggle-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'theme-toggle-btn';
            btn.innerHTML = this.getTheme() === 'dark' ? '☀️' : '🌙';
            btn.title = 'Toggle theme';
            btn.style.cssText = 'position: fixed; top: 20px; right: 140px; padding: 10px; background: rgba(0,0,0,0.5); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 50%; cursor: pointer; z-index: 9999; font-size: 16px; width: 40px; height: 40px;';
            btn.onclick = () => {
                this.toggle();
                btn.innerHTML = this.getTheme() === 'dark' ? '☀️' : '🌙';
            };
            document.body.appendChild(btn);
        },
        
        init() {
            this.applyTheme(this.getTheme());
            this.createToggleButton();
        }
    };
    
    // ============================================================
    // FEATURE 17: ACCESSIBILITY IMPROVEMENTS
    // ============================================================
    const Accessibility = {
        init() {
            this.addSkipLinks();
            this.improveARIA();
            this.addFocusIndicators();
        },
        
        addSkipLinks() {
            const skipLink = document.createElement('a');
            skipLink.href = '#main-content';
            skipLink.className = 'skip-link';
            skipLink.textContent = 'Skip to main content';
            skipLink.style.cssText = 'position: fixed; top: -100px; left: 20px; padding: 10px 20px; background: #22c55e; color: black; z-index: 99999; border-radius: 4px; text-decoration: none; font-weight: bold; transition: top 0.3s;';
            
            skipLink.addEventListener('focus', () => skipLink.style.top = '20px');
            skipLink.addEventListener('blur', () => skipLink.style.top = '-100px');
            
            document.body.insertBefore(skipLink, document.body.firstChild);
        },
        
        improveARIA() {
            // Add ARIA labels to buttons
            document.querySelectorAll('button').forEach(btn => {
                if (!btn.getAttribute('aria-label') && btn.textContent) {
                    btn.setAttribute('aria-label', btn.textContent.trim());
                }
            });
            
            // Mark main content area
            const main = document.querySelector('.snap-y') || document.querySelector('main');
            if (main) {
                main.id = 'main-content';
                main.setAttribute('role', 'main');
            }
        },
        
        addFocusIndicators() {
            const style = document.createElement('style');
            style.textContent = `
                *:focus-visible {
                    outline: 2px solid #22c55e !important;
                    outline-offset: 2px !important;
                }
                .skip-link:focus {
                    top: 20px !important;
                }
            `;
            document.head.appendChild(style);
        }
    };
    
    // ============================================================
    // FEATURE 18: PERSONAL STATS DASHBOARD
    // ============================================================
    const StatsDashboard = {
        getStats() {
            const history = WatchHistory.getHistory();
            const favorites = Favorites.getFavorites();
            const ratings = UserRatings.getRatings();
            
            const genreCounts = {};
            history.forEach(h => {
                const movie = window.allMoviesData?.find(m => m.title === h.title);
                movie?.genres?.forEach(g => {
                    genreCounts[g] = (genreCounts[g] || 0) + 1;
                });
            });
            
            const topGenres = Object.entries(genreCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);
            
            return {
                totalWatched: history.length,
                totalFavorites: favorites.length,
                totalRated: Object.keys(ratings).length,
                avgRating: Object.values(ratings).length > 0 
                    ? (Object.values(ratings).reduce((sum, r) => sum + r.rating, 0) / Object.values(ratings).length).toFixed(1)
                    : 0,
                topGenres,
                watchStreak: this.calculateStreak(history)
            };
        },
        
        calculateStreak(history) {
            if (history.length === 0) return 0;
            
            let streak = 0;
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            
            for (let i = 0; i < 30; i++) {
                const checkDate = new Date(today);
                checkDate.setDate(checkDate.getDate() - i);
                const dayStart = checkDate.getTime();
                const dayEnd = dayStart + 86400000;
                
                const watchedThatDay = history.some(h => h.watchedAt >= dayStart && h.watchedAt < dayEnd);
                if (watchedThatDay) {
                    streak++;
                } else if (i > 0) {
                    break;
                }
            }
            
            return streak;
        },
        
        showDashboard() {
            const existing = document.getElementById('stats-dashboard');
            if (existing) { existing.remove(); return; }
            
            const stats = this.getStats();
            
            const dashboard = document.createElement('div');
            dashboard.id = 'stats-dashboard';
            dashboard.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; max-width: 500px; border: 1px solid rgba(34,197,94,0.3); box-shadow: 0 20px 60px rgba(0,0,0,0.5);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                        <h2 style="color: white; margin: 0;">📊 Your Stats</h2>
                        <button onclick="this.closest('#stats-dashboard').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px;">
                        <div style="background: rgba(34,197,94,0.1); padding: 20px; border-radius: 12px; text-align: center;">
                            <div style="font-size: 32px; color: #22c55e; font-weight: bold;">${stats.totalWatched}</div>
                            <div style="color: #888; font-size: 12px;">Watched</div>
                        </div>
                        <div style="background: rgba(239,68,68,0.1); padding: 20px; border-radius: 12px; text-align: center;">
                            <div style="font-size: 32px; color: #ef4444; font-weight: bold;">${stats.totalFavorites}</div>
                            <div style="color: #888; font-size: 12px;">Favorites</div>
                        </div>
                        <div style="background: rgba(245,158,11,0.1); padding: 20px; border-radius: 12px; text-align: center;">
                            <div style="font-size: 32px; color: #f59e0b; font-weight: bold;">${stats.avgRating}</div>
                            <div style="color: #888; font-size: 12px;">Avg Rating</div>
                        </div>
                    </div>
                    
                    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; margin-bottom: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: white;">🔥 Watch Streak</span>
                            <span style="color: #22c55e; font-weight: bold;">${stats.watchStreak} days</span>
                        </div>
                    </div>
                    
                    <div>
                        <h4 style="color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 12px;">Top Genres</h4>
                        ${stats.topGenres.map(([genre, count]) => `
                            <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <span style="color: white;">${genre}</span>
                                <span style="color: #22c55e;">${count} watched</span>
                            </div>
                        `).join('') || '<p style="color: #666;">No data yet</p>'}
                    </div>
                </div>
            `;
            document.body.appendChild(dashboard);
        },
        
        createStatsButton() {
            const existing = document.getElementById('stats-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'stats-btn';
            btn.innerHTML = '📊 Stats';
            btn.style.cssText = 'position: fixed; bottom: 20px; left: 260px; padding: 10px 15px; background: rgba(0,0,0,0.8); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; cursor: pointer; z-index: 9999; font-size: 12px;';
            btn.onclick = () => this.showDashboard();
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 19: CONTENT WARNINGS
    // ============================================================
    const ContentWarnings = {
        warnings: {
            'Horror': '⚠️ Contains scary content',
            'Thriller': '⚠️ Intense scenes',
            'Crime': '⚠️ Violence',
            'War': '⚠️ War violence',
            'R-rated': '🔞 Adult content'
        },
        
        getWarning(genres) {
            if (!genres || !Array.isArray(genres)) return null;
            
            for (const [genre, warning] of Object.entries(this.warnings)) {
                if (genres.some(g => g.toLowerCase().includes(genre.toLowerCase()))) {
                    return warning;
                }
            }
            return null;
        },
        
        addWarningBadge(movie, container) {
            const warning = this.getWarning(movie.genres);
            if (!warning) return;
            
            const badge = document.createElement('div');
            badge.className = 'content-warning-badge';
            badge.textContent = warning;
            badge.style.cssText = 'position: absolute; top: 60px; left: 10px; padding: 4px 8px; background: rgba(239,68,68,0.9); color: white; font-size: 10px; border-radius: 4px; z-index: 10;';
            container?.appendChild(badge);
        }
    };
    
    // ============================================================
    // FEATURE 20: ENHANCED SOCIAL SHARING
    // ============================================================
    const SocialSharing = {
        platforms: [
            { name: 'Twitter', icon: '𝕏', url: (title, url) => `https://twitter.com/intent/tweet?text=Check out ${encodeURIComponent(title)} on MovieShows!&url=${encodeURIComponent(url)}` },
            { name: 'Facebook', icon: 'f', url: (title, url) => `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}` },
            { name: 'WhatsApp', icon: '💬', url: (title, url) => `https://wa.me/?text=Check out ${encodeURIComponent(title)} on MovieShows! ${encodeURIComponent(url)}` },
            { name: 'Telegram', icon: '✈️', url: (title, url) => `https://t.me/share/url?url=${encodeURIComponent(url)}&text=Check out ${encodeURIComponent(title)} on MovieShows!` },
            { name: 'Email', icon: '✉️', url: (title, url) => `mailto:?subject=${encodeURIComponent(title)} - MovieShows&body=Check out ${encodeURIComponent(title)} on MovieShows! ${encodeURIComponent(url)}` }
        ],
        
        share(movie) {
            const url = window.location.href;
            
            const shareUI = document.createElement('div');
            shareUI.id = 'share-ui';
            shareUI.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 16px; padding: 25px; z-index: 99999; min-width: 300px; border: 1px solid rgba(34,197,94,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="color: white; margin: 0;">Share "${movie.title}"</h3>
                        <button onclick="this.closest('#share-ui').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 20px;">×</button>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 20px;">
                        ${this.platforms.map(p => `
                            <a href="${p.url(movie.title, url)}" target="_blank" rel="noopener" style="display: flex; flex-direction: column; align-items: center; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 12px; text-decoration: none; color: white; transition: background 0.2s;" onmouseover="this.style.background='rgba(34,197,94,0.2)'" onmouseout="this.style.background='rgba(255,255,255,0.1)'">
                                <span style="font-size: 24px;">${p.icon}</span>
                                <span style="font-size: 10px; margin-top: 5px;">${p.name}</span>
                            </a>
                        `).join('')}
                    </div>
                    
                    <div style="display: flex; gap: 10px;">
                        <input type="text" value="${url}" readonly style="flex: 1; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; font-size: 12px;">
                        <button id="copy-share-link" style="padding: 12px 20px; background: #22c55e; color: black; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">Copy</button>
                    </div>
                </div>
            `;
            document.body.appendChild(shareUI);
            
            document.getElementById('copy-share-link')?.addEventListener('click', () => {
                navigator.clipboard.writeText(url);
                window.showToast?.('Link copied!');
            });
        }
    };
    
    // ============================================================
    // INITIALIZATION
    // ============================================================
    function initializeFeatures() {
        console.log('[MovieShows] Initializing Premium Features v2.0...');
        
        // Wait for DOM and main app to be ready
        setTimeout(() => {
            try {
                SearchFilters.init();
                KeyboardShortcuts.init();
                AutoplaySettings.init();
                SleepTimer.createTimerUI();
                PictureInPicture.init();
                TrendingSection.createTrendingCategory();
                NewReleases.createNewReleasesCategory();
                RandomShuffle.createShuffleButton();
                ThemeToggle.init();
                Accessibility.init();
                StatsDashboard.createStatsButton();
                PWASupport.init();
                
                // Initialize on filter panel open
                const filterBtn = document.querySelector('button:has-text("Filters")') || document.querySelector('[id*="filter"]');
                filterBtn?.addEventListener('click', () => {
                    setTimeout(() => {
                        DecadeBrowsing.createDecadeFilters();
                        GenrePages.createGenreFilters();
                    }, 100);
                });
                
                // Initialize search filters on search panel open
                const searchBtn = document.querySelector('button:has-text("Search")') || document.querySelector('[id*="search"]');
                searchBtn?.addEventListener('click', () => {
                    setTimeout(() => SearchFilters.enhanceSearchPanel(), 100);
                });
                
                // Track watch history
                window.addEventListener('videoStarted', (e) => {
                    if (e.detail?.movie) {
                        WatchHistory.addToHistory(e.detail.movie);
                    }
                });
                
                // Show continue watching after a delay
                setTimeout(() => ContinueWatching.init(), 3000);
                
                console.log('[MovieShows] Premium Features initialized successfully!');
                
            } catch (e) {
                console.error('[MovieShows] Error initializing features:', e);
            }
        }, 2000);
    }
    
    // Expose features globally
    window.MovieShowsFeatures = {
        SearchFilters,
        WatchHistory,
        ContinueWatching,
        KeyboardShortcuts,
        AutoplaySettings,
        SleepTimer,
        PictureInPicture,
        TrendingSection,
        NewReleases,
        RandomShuffle,
        DecadeBrowsing,
        GenrePages,
        UserRatings,
        Favorites,
        PWASupport,
        ThemeToggle,
        Accessibility,
        StatsDashboard,
        ContentWarnings,
        SocialSharing
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeFeatures);
    } else {
        initializeFeatures();
    }
    
})();
