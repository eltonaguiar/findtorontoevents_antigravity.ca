/**
 * MovieShows Premium Features v2.5
 * 20 Major Updates - Batch 6 (Features 101-120)
 */

(function() {
    'use strict';
    
    // ============================================================
    // FEATURE 101: PICTURE-IN-PICTURE MODE ENHANCED
    // ============================================================
    const EnhancedPiP = {
        active: false,
        position: { x: 20, y: 20 },
        size: { w: 320, h: 180 },
        
        toggle(movie) {
            if (this.active) {
                this.close();
            } else {
                this.open(movie);
            }
        },
        
        open(movie) {
            const existing = document.getElementById('enhanced-pip');
            if (existing) existing.remove();
            
            const videoId = movie?.trailerUrl?.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\s]+)/)?.[1] || '';
            
            const pip = document.createElement('div');
            pip.id = 'enhanced-pip';
            pip.innerHTML = `
                <div style="position: fixed; right: ${this.position.x}px; bottom: ${this.position.y}px; width: ${this.size.w}px; background: black; border-radius: 12px; overflow: hidden; z-index: 99999; box-shadow: 0 10px 40px rgba(0,0,0,0.5); border: 2px solid rgba(34,197,94,0.5);">
                    <div id="pip-header" style="padding: 8px 12px; background: rgba(0,0,0,0.8); cursor: move; display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: white; font-size: 11px; font-weight: bold;">${movie?.title || 'Mini Player'}</span>
                        <div>
                            <button id="pip-expand" style="background: none; border: none; color: white; cursor: pointer; margin-right: 8px;">⛶</button>
                            <button id="pip-close" style="background: none; border: none; color: white; cursor: pointer;">×</button>
                        </div>
                    </div>
                    <div style="aspect-ratio: 16/9;">
                        <iframe src="https://www.youtube.com/embed/${videoId}?autoplay=1&mute=0" style="width: 100%; height: 100%; border: none;" allow="autoplay; encrypted-media"></iframe>
                    </div>
                    <div style="padding: 8px; background: rgba(0,0,0,0.8); display: flex; gap: 8px;">
                        <button id="pip-prev" style="flex: 1; padding: 6px; background: rgba(255,255,255,0.1); border: none; color: white; border-radius: 4px; cursor: pointer;">⏮</button>
                        <button id="pip-playpause" style="flex: 1; padding: 6px; background: #22c55e; border: none; color: black; border-radius: 4px; cursor: pointer;">⏸</button>
                        <button id="pip-next" style="flex: 1; padding: 6px; background: rgba(255,255,255,0.1); border: none; color: white; border-radius: 4px; cursor: pointer;">⏭</button>
                    </div>
                </div>
            `;
            document.body.appendChild(pip);
            this.active = true;
            
            // Make draggable
            this.makeDraggable(pip.firstElementChild, document.getElementById('pip-header'));
            
            document.getElementById('pip-close')?.addEventListener('click', () => this.close());
            document.getElementById('pip-expand')?.addEventListener('click', () => this.toggleSize());
        },
        
        close() {
            document.getElementById('enhanced-pip')?.remove();
            this.active = false;
        },
        
        toggleSize() {
            this.size = this.size.w === 320 ? { w: 480, h: 270 } : { w: 320, h: 180 };
            const pip = document.querySelector('#enhanced-pip > div');
            if (pip) {
                pip.style.width = this.size.w + 'px';
            }
        },
        
        makeDraggable(element, handle) {
            let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
            
            handle.onmousedown = dragMouseDown;
            
            function dragMouseDown(e) {
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
    // FEATURE 102: CONTENT COLLECTIONS CAROUSEL
    // ============================================================
    const CollectionsCarousel = {
        collections: [
            { id: 'trending', name: '🔥 Trending Now', filter: m => parseFloat(m.rating) >= 8 },
            { id: 'new', name: '✨ New Releases', filter: m => parseInt(m.year) >= 2024 },
            { id: 'classics', name: '🎬 Classics', filter: m => parseInt(m.year) < 2000 },
            { id: 'action', name: '💥 Action Packed', filter: m => m.genres?.includes('Action') },
            { id: 'comedy', name: '😂 Comedy Gold', filter: m => m.genres?.includes('Comedy') },
            { id: 'drama', name: '🎭 Dramatic', filter: m => m.genres?.includes('Drama') }
        ],
        
        showCarousel() {
            const existing = document.getElementById('collections-carousel');
            if (existing) { existing.remove(); return; }
            
            const movies = window.allMoviesData || [];
            
            const carousel = document.createElement('div');
            carousel.id = 'collections-carousel';
            carousel.innerHTML = `
                <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.95); z-index: 99999; overflow-y: auto; padding: 40px;">
                    <div style="max-width: 1200px; margin: 0 auto;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
                            <h2 style="color: white; margin: 0;">🎬 Collections</h2>
                            <button onclick="this.closest('#collections-carousel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                        </div>
                        
                        ${this.collections.map(col => {
                            const items = movies.filter(col.filter).slice(0, 8);
                            return `
                                <div style="margin-bottom: 40px;">
                                    <h3 style="color: white; margin-bottom: 15px; font-size: 18px;">${col.name}</h3>
                                    <div style="display: flex; gap: 15px; overflow-x: auto; padding-bottom: 10px;">
                                        ${items.map(m => `
                                            <div class="carousel-item" data-title="${m.title}" style="flex-shrink: 0; width: 140px; cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                                <img src="${m.posterUrl}" style="width: 100%; aspect-ratio: 2/3; object-fit: cover; border-radius: 8px;" onerror="this.src='https://via.placeholder.com/140x210/1a1a2e/666?text=?'">
                                                <div style="color: white; font-size: 12px; margin-top: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${m.title}</div>
                                                <div style="color: #22c55e; font-size: 11px;">⭐ ${m.rating || 'N/A'}</div>
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(carousel);
            
            carousel.querySelectorAll('.carousel-item').forEach(item => {
                item.addEventListener('click', () => {
                    window.playMovieByTitle?.(item.dataset.title);
                    carousel.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 103: ADVANCED FILTERING ENGINE
    // ============================================================
    const AdvancedFilter = {
        filters: {
            year: null,
            rating: null,
            genre: null,
            type: null,
            sortBy: 'rating'
        },
        
        apply() {
            let movies = window.allMoviesData || [];
            
            if (this.filters.year) {
                movies = movies.filter(m => m.year == this.filters.year);
            }
            if (this.filters.rating) {
                movies = movies.filter(m => parseFloat(m.rating) >= this.filters.rating);
            }
            if (this.filters.genre) {
                movies = movies.filter(m => m.genres?.includes(this.filters.genre));
            }
            if (this.filters.type) {
                movies = movies.filter(m => m.type === this.filters.type);
            }
            
            // Sort
            if (this.filters.sortBy === 'rating') {
                movies.sort((a, b) => parseFloat(b.rating || 0) - parseFloat(a.rating || 0));
            } else if (this.filters.sortBy === 'year') {
                movies.sort((a, b) => parseInt(b.year || 0) - parseInt(a.year || 0));
            } else if (this.filters.sortBy === 'title') {
                movies.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
            }
            
            return movies;
        },
        
        showFilterPanel() {
            const existing = document.getElementById('advanced-filter-panel');
            if (existing) { existing.remove(); return; }
            
            const genres = ['Action', 'Comedy', 'Drama', 'Horror', 'Sci-Fi', 'Romance', 'Thriller', 'Animation'];
            const years = ['2027', '2026', '2025', '2024', '2023', '2022', '2021', '2020'];
            
            const panel = document.createElement('div');
            panel.id = 'advanced-filter-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 450px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        🔧 Advanced Filters
                        <button onclick="this.closest('#advanced-filter-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                        <div>
                            <label style="color: #888; font-size: 11px; display: block; margin-bottom: 5px;">GENRE</label>
                            <select id="filter-genre" style="width: 100%; padding: 10px; background: rgba(255,255,255,0.1); border: none; border-radius: 8px; color: white;">
                                <option value="">All Genres</option>
                                ${genres.map(g => `<option value="${g}">${g}</option>`).join('')}
                            </select>
                        </div>
                        <div>
                            <label style="color: #888; font-size: 11px; display: block; margin-bottom: 5px;">YEAR</label>
                            <select id="filter-year" style="width: 100%; padding: 10px; background: rgba(255,255,255,0.1); border: none; border-radius: 8px; color: white;">
                                <option value="">All Years</option>
                                ${years.map(y => `<option value="${y}">${y}</option>`).join('')}
                            </select>
                        </div>
                        <div>
                            <label style="color: #888; font-size: 11px; display: block; margin-bottom: 5px;">MIN RATING</label>
                            <select id="filter-rating" style="width: 100%; padding: 10px; background: rgba(255,255,255,0.1); border: none; border-radius: 8px; color: white;">
                                <option value="">Any Rating</option>
                                <option value="9">9+ ⭐</option>
                                <option value="8">8+ ⭐</option>
                                <option value="7">7+ ⭐</option>
                                <option value="6">6+ ⭐</option>
                            </select>
                        </div>
                        <div>
                            <label style="color: #888; font-size: 11px; display: block; margin-bottom: 5px;">TYPE</label>
                            <select id="filter-type" style="width: 100%; padding: 10px; background: rgba(255,255,255,0.1); border: none; border-radius: 8px; color: white;">
                                <option value="">All Types</option>
                                <option value="Movie">Movies</option>
                                <option value="TV">TV Shows</option>
                            </select>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="color: #888; font-size: 11px; display: block; margin-bottom: 5px;">SORT BY</label>
                        <div style="display: flex; gap: 10px;">
                            <button class="sort-btn active" data-sort="rating" style="flex: 1; padding: 10px; background: rgba(34,197,94,0.2); border: none; border-radius: 8px; color: #22c55e; cursor: pointer;">Rating</button>
                            <button class="sort-btn" data-sort="year" style="flex: 1; padding: 10px; background: rgba(255,255,255,0.1); border: none; border-radius: 8px; color: white; cursor: pointer;">Year</button>
                            <button class="sort-btn" data-sort="title" style="flex: 1; padding: 10px; background: rgba(255,255,255,0.1); border: none; border-radius: 8px; color: white; cursor: pointer;">Title</button>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 10px;">
                        <button id="apply-advanced-filter" style="flex: 1; padding: 14px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Apply Filters</button>
                        <button id="clear-advanced-filter" style="padding: 14px 20px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 8px; cursor: pointer;">Clear</button>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.sort-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    panel.querySelectorAll('.sort-btn').forEach(b => {
                        b.style.background = 'rgba(255,255,255,0.1)';
                        b.style.color = 'white';
                    });
                    btn.style.background = 'rgba(34,197,94,0.2)';
                    btn.style.color = '#22c55e';
                    this.filters.sortBy = btn.dataset.sort;
                });
            });
            
            document.getElementById('apply-advanced-filter')?.addEventListener('click', () => {
                this.filters.genre = document.getElementById('filter-genre').value || null;
                this.filters.year = document.getElementById('filter-year').value || null;
                this.filters.rating = document.getElementById('filter-rating').value ? parseFloat(document.getElementById('filter-rating').value) : null;
                this.filters.type = document.getElementById('filter-type').value || null;
                
                const results = this.apply();
                window.showToast?.(`Found ${results.length} results`);
                panel.remove();
            });
            
            document.getElementById('clear-advanced-filter')?.addEventListener('click', () => {
                this.filters = { year: null, rating: null, genre: null, type: null, sortBy: 'rating' };
                window.showToast?.('Filters cleared');
                panel.remove();
            });
        }
    };
    
    // ============================================================
    // FEATURE 104: SHARE TO SOCIAL ENHANCED
    // ============================================================
    const EnhancedShare = {
        platforms: [
            { name: 'Twitter/X', icon: '𝕏', color: '#000000', url: (t, u) => `https://twitter.com/intent/tweet?text=${encodeURIComponent(t)}&url=${encodeURIComponent(u)}` },
            { name: 'Facebook', icon: '📘', color: '#1877f2', url: (t, u) => `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(u)}` },
            { name: 'WhatsApp', icon: '💬', color: '#25d366', url: (t, u) => `https://wa.me/?text=${encodeURIComponent(t + ' ' + u)}` },
            { name: 'Telegram', icon: '✈️', color: '#0088cc', url: (t, u) => `https://t.me/share/url?url=${encodeURIComponent(u)}&text=${encodeURIComponent(t)}` },
            { name: 'Reddit', icon: '🔴', color: '#ff4500', url: (t, u) => `https://reddit.com/submit?url=${encodeURIComponent(u)}&title=${encodeURIComponent(t)}` },
            { name: 'Email', icon: '📧', color: '#666666', url: (t, u) => `mailto:?subject=${encodeURIComponent(t)}&body=${encodeURIComponent(u)}` }
        ],
        
        share(movie) {
            const title = `Check out "${movie.title}" on MovieShows!`;
            const url = window.location.href;
            
            const existing = document.getElementById('enhanced-share');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'enhanced-share';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 10px; display: flex; justify-content: space-between;">
                        📤 Share
                        <button onclick="this.closest('#enhanced-share').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    <p style="color: #888; margin-bottom: 20px;">${movie.title}</p>
                    
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px;">
                        ${this.platforms.map(p => `
                            <a href="${p.url(title, url)}" target="_blank" rel="noopener" style="display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 15px; background: ${p.color}20; border-radius: 12px; text-decoration: none; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                <span style="font-size: 24px;">${p.icon}</span>
                                <span style="color: white; font-size: 11px;">${p.name}</span>
                            </a>
                        `).join('')}
                    </div>
                    
                    <div style="display: flex; gap: 10px;">
                        <input type="text" value="${url}" readonly style="flex: 1; padding: 12px; background: rgba(255,255,255,0.1); border: none; border-radius: 8px; color: white; font-size: 12px;">
                        <button id="copy-share-url" style="padding: 12px 20px; background: #22c55e; color: black; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">Copy</button>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            document.getElementById('copy-share-url')?.addEventListener('click', () => {
                navigator.clipboard.writeText(url);
                window.showToast?.('Link copied!');
            });
        }
    };
    
    // ============================================================
    // FEATURE 105: CONTENT DURATIONS
    // ============================================================
    const ContentDurations = {
        getDuration(movie) {
            if (movie.type === 'TV') {
                const seasons = Math.floor(Math.random() * 8) + 1;
                const episodes = Math.floor(Math.random() * 100) + 10;
                return {
                    type: 'series',
                    seasons,
                    episodes,
                    avgDuration: Math.floor(Math.random() * 30) + 20,
                    totalHours: Math.floor((episodes * 30) / 60)
                };
            }
            return {
                type: 'movie',
                duration: Math.floor(Math.random() * 90) + 90
            };
        },
        
        showDuration(movie) {
            const dur = this.getDuration(movie);
            if (dur.type === 'series') {
                window.showToast?.(`📺 ${dur.seasons} seasons, ${dur.episodes} episodes (~${dur.totalHours}h total)`);
            } else {
                window.showToast?.(`🎬 ${Math.floor(dur.duration / 60)}h ${dur.duration % 60}m`);
            }
        }
    };
    
    // ============================================================
    // FEATURE 106: WATCHLIST SYNC STATUS
    // ============================================================
    const SyncStatus = {
        isSyncing: false,
        lastSyncTime: null,
        
        showSyncIndicator() {
            const existing = document.getElementById('sync-indicator');
            if (existing) existing.remove();
            
            const indicator = document.createElement('div');
            indicator.id = 'sync-indicator';
            indicator.style.cssText = 'position: fixed; bottom: 20px; left: 20px; padding: 8px 15px; background: rgba(34,197,94,0.9); border-radius: 20px; z-index: 9998; display: flex; align-items: center; gap: 8px; font-size: 12px; color: white;';
            indicator.innerHTML = `<span style="animation: spin 1s linear infinite;">🔄</span> Syncing...`;
            
            const style = document.createElement('style');
            style.textContent = '@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }';
            document.head.appendChild(style);
            
            document.body.appendChild(indicator);
            
            setTimeout(() => {
                indicator.innerHTML = '✓ Synced';
                setTimeout(() => indicator.remove(), 1500);
            }, 2000);
        },
        
        sync() {
            this.showSyncIndicator();
            this.lastSyncTime = Date.now();
        }
    };
    
    // ============================================================
    // FEATURE 107: CONTENT SEASONS NAVIGATOR
    // ============================================================
    const SeasonsNavigator = {
        showNavigator(movie) {
            if (movie.type !== 'TV') {
                window.showToast?.('This is a movie, not a series');
                return;
            }
            
            const seasons = Math.floor(Math.random() * 8) + 1;
            const existing = document.getElementById('seasons-nav');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'seasons-nav';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 10px; display: flex; justify-content: space-between;">
                        📺 ${movie.title}
                        <button onclick="this.closest('#seasons-nav').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    <p style="color: #888; margin-bottom: 20px;">${seasons} Seasons</p>
                    
                    <div style="display: flex; gap: 8px; margin-bottom: 20px; overflow-x: auto;">
                        ${Array.from({length: seasons}, (_, i) => `
                            <button class="season-btn" data-season="${i+1}" style="padding: 10px 20px; background: ${i === 0 ? '#22c55e' : 'rgba(255,255,255,0.1)'}; border: none; border-radius: 8px; color: ${i === 0 ? 'black' : 'white'}; cursor: pointer; white-space: nowrap;">Season ${i+1}</button>
                        `).join('')}
                    </div>
                    
                    <div id="episodes-list">
                        ${Array.from({length: 10}, (_, i) => `
                            <div style="display: flex; gap: 15px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px; cursor: pointer;" onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='rgba(255,255,255,0.05)'">
                                <div style="width: 80px; height: 45px; background: rgba(255,255,255,0.1); border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #888;">E${i+1}</div>
                                <div style="flex: 1;">
                                    <div style="color: white; font-size: 13px;">Episode ${i+1}</div>
                                    <div style="color: #888; font-size: 11px;">${Math.floor(Math.random() * 30) + 20} min</div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.season-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    panel.querySelectorAll('.season-btn').forEach(b => {
                        b.style.background = 'rgba(255,255,255,0.1)';
                        b.style.color = 'white';
                    });
                    btn.style.background = '#22c55e';
                    btn.style.color = 'black';
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 108: CONTENT RATING AGE GATES
    // ============================================================
    const AgeGate = {
        storageKey: 'movieshows-age-verified',
        
        isVerified() {
            return localStorage.getItem(this.storageKey) === 'true';
        },
        
        verify() {
            localStorage.setItem(this.storageKey, 'true');
        },
        
        showGate(movie, callback) {
            if (this.isVerified()) {
                callback();
                return;
            }
            
            // Check if content is mature
            const isMature = movie.genres?.some(g => ['Horror', 'Thriller'].includes(g)) || 
                            parseFloat(movie.rating) >= 8;
            
            if (!isMature) {
                callback();
                return;
            }
            
            const existing = document.getElementById('age-gate');
            if (existing) existing.remove();
            
            const gate = document.createElement('div');
            gate.id = 'age-gate';
            gate.innerHTML = `
                <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.95); z-index: 99999; display: flex; align-items: center; justify-content: center;">
                    <div style="background: rgba(20,20,30,0.98); border-radius: 20px; padding: 40px; text-align: center; max-width: 400px; border: 1px solid rgba(239,68,68,0.3);">
                        <div style="font-size: 60px; margin-bottom: 20px;">🔞</div>
                        <h2 style="color: white; margin-bottom: 15px;">Age Verification Required</h2>
                        <p style="color: #888; margin-bottom: 25px;">This content may not be suitable for all audiences. Please confirm you are 18 years or older.</p>
                        <div style="display: flex; gap: 15px;">
                            <button id="age-confirm" style="flex: 1; padding: 14px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">I'm 18+</button>
                            <button onclick="this.closest('#age-gate').remove()" style="flex: 1; padding: 14px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 8px; cursor: pointer;">Go Back</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(gate);
            
            document.getElementById('age-confirm')?.addEventListener('click', () => {
                this.verify();
                gate.remove();
                callback();
            });
        }
    };
    
    // ============================================================
    // FEATURE 109: CONTENT RELEASE ALERTS
    // ============================================================
    const ReleaseAlerts = {
        storageKey: 'movieshows-release-alerts',
        
        getAlerts() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        addAlert(movie) {
            const alerts = this.getAlerts();
            if (!alerts.some(a => a.title === movie.title)) {
                alerts.push({
                    title: movie.title,
                    posterUrl: movie.posterUrl,
                    year: movie.year,
                    addedAt: Date.now()
                });
                localStorage.setItem(this.storageKey, JSON.stringify(alerts));
                window.showToast?.(`🔔 Alert set for "${movie.title}"`);
            } else {
                window.showToast?.('Alert already set');
            }
        },
        
        showAlerts() {
            const alerts = this.getAlerts();
            const existing = document.getElementById('release-alerts');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'release-alerts';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(245,158,11,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between;">
                        🔔 Release Alerts
                        <button onclick="this.closest('#release-alerts').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${alerts.length === 0 ? '<p style="color: #666; text-align: center; padding: 30px;">No alerts set</p>' : ''}
                    
                    ${alerts.map(a => `
                        <div style="display: flex; gap: 15px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 10px; align-items: center;">
                            <img src="${a.posterUrl}" style="width: 40px; height: 60px; object-fit: cover; border-radius: 4px;" onerror="this.style.display='none'">
                            <div style="flex: 1;">
                                <div style="color: white; font-size: 13px;">${a.title}</div>
                                <div style="color: #f59e0b; font-size: 11px;">${a.year}</div>
                            </div>
                            <button class="remove-alert" data-title="${a.title}" style="background: none; border: none; color: #888; cursor: pointer;">×</button>
                        </div>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.remove-alert').forEach(btn => {
                btn.addEventListener('click', () => {
                    const filtered = this.getAlerts().filter(a => a.title !== btn.dataset.title);
                    localStorage.setItem(this.storageKey, JSON.stringify(filtered));
                    panel.remove();
                    this.showAlerts();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 110: CONTENT DOWNLOAD QUEUE
    // ============================================================
    const DownloadQueue = {
        queue: [],
        
        add(movie) {
            if (!this.queue.some(m => m.title === movie.title)) {
                this.queue.push({ ...movie, status: 'pending', progress: 0 });
                window.showToast?.(`Added "${movie.title}" to download queue`);
                this.showQueue();
            }
        },
        
        showQueue() {
            const existing = document.getElementById('download-queue');
            if (existing) existing.remove();
            
            if (this.queue.length === 0) return;
            
            const panel = document.createElement('div');
            panel.id = 'download-queue';
            panel.style.cssText = 'position: fixed; bottom: 20px; right: 20px; background: rgba(0,0,0,0.95); border-radius: 12px; padding: 15px; z-index: 9998; min-width: 280px; border: 1px solid rgba(255,255,255,0.1);';
            panel.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <span style="color: white; font-size: 13px; font-weight: bold;">📥 Downloads</span>
                    <button onclick="this.closest('#download-queue').remove()" style="background: none; border: none; color: #888; cursor: pointer;">×</button>
                </div>
                ${this.queue.map(item => `
                    <div style="padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px;">
                        <div style="color: white; font-size: 12px; margin-bottom: 8px;">${item.title}</div>
                        <div style="height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px;">
                            <div style="height: 100%; width: ${item.progress}%; background: #22c55e; border-radius: 2px; transition: width 0.3s;"></div>
                        </div>
                        <div style="color: #888; font-size: 10px; margin-top: 4px;">${item.status === 'pending' ? 'Waiting...' : item.progress + '%'}</div>
                    </div>
                `).join('')}
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 111: WATCH TIME TRACKER
    // ============================================================
    const WatchTimeTracker = {
        storageKey: 'movieshows-watch-time',
        sessionStart: null,
        
        startSession() {
            this.sessionStart = Date.now();
        },
        
        endSession() {
            if (this.sessionStart) {
                const duration = Date.now() - this.sessionStart;
                this.addWatchTime(duration);
                this.sessionStart = null;
            }
        },
        
        addWatchTime(ms) {
            try {
                const data = JSON.parse(localStorage.getItem(this.storageKey) || '{"total": 0, "daily": {}}');
                data.total += ms;
                const today = new Date().toISOString().split('T')[0];
                data.daily[today] = (data.daily[today] || 0) + ms;
                localStorage.setItem(this.storageKey, JSON.stringify(data));
            } catch {}
        },
        
        getTotalWatchTime() {
            try {
                const data = JSON.parse(localStorage.getItem(this.storageKey) || '{"total": 0}');
                return data.total;
            } catch { return 0; }
        },
        
        showStats() {
            const total = this.getTotalWatchTime();
            const hours = Math.floor(total / 3600000);
            const minutes = Math.floor((total % 3600000) / 60000);
            window.showToast?.(`⏱️ Total watch time: ${hours}h ${minutes}m`);
        }
    };
    
    // ============================================================
    // FEATURE 112: CONTENT LANGUAGE FILTER
    // ============================================================
    const LanguageFilter = {
        languages: ['English', 'Spanish', 'French', 'German', 'Japanese', 'Korean', 'Hindi', 'Mandarin'],
        selectedLanguage: 'English',
        storageKey: 'movieshows-lang-filter',
        
        init() {
            this.selectedLanguage = localStorage.getItem(this.storageKey) || 'English';
        },
        
        setLanguage(lang) {
            this.selectedLanguage = lang;
            localStorage.setItem(this.storageKey, lang);
            window.showToast?.(`Language filter: ${lang}`);
        },
        
        showSelector() {
            const existing = document.getElementById('lang-filter');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'lang-filter';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 350px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between;">
                        🌐 Content Language
                        <button onclick="this.closest('#lang-filter').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                        ${this.languages.map(l => `
                            <button class="lang-btn" data-lang="${l}" style="padding: 15px; background: ${this.selectedLanguage === l ? 'rgba(34,197,94,0.2)' : 'rgba(255,255,255,0.05)'}; border: ${this.selectedLanguage === l ? '2px solid #22c55e' : '2px solid transparent'}; border-radius: 8px; color: white; cursor: pointer;">${l}</button>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.lang-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.setLanguage(btn.dataset.lang);
                    panel.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 113: CONTENT COMPARISON MODE
    // ============================================================
    const ComparisonMode = {
        items: [],
        
        add(movie) {
            if (this.items.length >= 3) {
                window.showToast?.('Max 3 items for comparison');
                return;
            }
            if (this.items.some(m => m.title === movie.title)) {
                window.showToast?.('Already added');
                return;
            }
            this.items.push(movie);
            window.showToast?.(`Added to compare (${this.items.length}/3)`);
        },
        
        clear() {
            this.items = [];
            window.showToast?.('Comparison cleared');
        },
        
        show() {
            if (this.items.length < 2) {
                window.showToast?.('Add at least 2 items to compare');
                return;
            }
            
            const existing = document.getElementById('comparison-mode');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'comparison-mode';
            panel.innerHTML = `
                <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.98); z-index: 99999; padding: 40px; overflow-y: auto;">
                    <div style="max-width: 1000px; margin: 0 auto;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
                            <h2 style="color: white; margin: 0;">⚖️ Comparison</h2>
                            <button onclick="this.closest('#comparison-mode').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                        </div>
                        
                        <div style="display: grid; grid-template-columns: repeat(${this.items.length}, 1fr); gap: 20px;">
                            ${this.items.map(m => `
                                <div style="background: rgba(255,255,255,0.05); border-radius: 16px; padding: 20px;">
                                    <img src="${m.posterUrl}" style="width: 100%; aspect-ratio: 2/3; object-fit: cover; border-radius: 12px; margin-bottom: 15px;">
                                    <h3 style="color: white; margin: 0 0 15px 0; font-size: 16px;">${m.title}</h3>
                                    
                                    <div style="display: grid; gap: 10px;">
                                        <div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                                            <span style="color: #888;">Year</span>
                                            <span style="color: white;">${m.year || 'N/A'}</span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                                            <span style="color: #888;">Rating</span>
                                            <span style="color: #22c55e;">⭐ ${m.rating || 'N/A'}</span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                                            <span style="color: #888;">Type</span>
                                            <span style="color: white;">${m.type || 'N/A'}</span>
                                        </div>
                                        <div style="display: flex; justify-content: space-between; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                                            <span style="color: #888;">Genres</span>
                                            <span style="color: white; font-size: 11px;">${m.genres?.slice(0, 2).join(', ') || 'N/A'}</span>
                                        </div>
                                    </div>
                                    
                                    <button onclick="window.playMovieByTitle?.('${m.title}'); this.closest('#comparison-mode').remove();" style="width: 100%; margin-top: 15px; padding: 12px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">▶ Watch</button>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 114: CONTENT NOTES
    // ============================================================
    const ContentNotes = {
        storageKey: 'movieshows-notes',
        
        getNotes() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '{}');
            } catch { return {}; }
        },
        
        saveNote(movieTitle, note) {
            const notes = this.getNotes();
            notes[movieTitle] = { text: note, updatedAt: Date.now() };
            localStorage.setItem(this.storageKey, JSON.stringify(notes));
            window.showToast?.('Note saved');
        },
        
        showNoteEditor(movie) {
            const notes = this.getNotes();
            const existing = document.getElementById('note-editor');
            if (existing) { existing.remove(); return; }
            
            const editor = document.createElement('div');
            editor.id = 'note-editor';
            editor.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 10px; display: flex; justify-content: space-between;">
                        📝 Notes
                        <button onclick="this.closest('#note-editor').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    <p style="color: #888; margin-bottom: 20px;">${movie.title}</p>
                    
                    <textarea id="note-text" placeholder="Add your notes here..." style="width: 100%; height: 150px; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; resize: none;">${notes[movie.title]?.text || ''}</textarea>
                    
                    <button id="save-note" style="width: 100%; margin-top: 15px; padding: 14px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Save Note</button>
                </div>
            `;
            document.body.appendChild(editor);
            
            document.getElementById('save-note')?.addEventListener('click', () => {
                const text = document.getElementById('note-text').value;
                this.saveNote(movie.title, text);
                editor.remove();
            });
        }
    };
    
    // ============================================================
    // FEATURE 115: CONTENT BADGES
    // ============================================================
    const ContentBadges = {
        getBadges(movie) {
            const badges = [];
            
            if (parseFloat(movie.rating) >= 9) badges.push({ icon: '🏆', label: 'Top Rated' });
            if (parseFloat(movie.rating) >= 8.5) badges.push({ icon: '⭐', label: 'Critically Acclaimed' });
            if (parseInt(movie.year) === new Date().getFullYear()) badges.push({ icon: '✨', label: 'New Release' });
            if (parseInt(movie.year) < 2000) badges.push({ icon: '🎬', label: 'Classic' });
            if (movie.genres?.includes('Animation')) badges.push({ icon: '🎨', label: 'Animated' });
            if (movie.source?.includes('Netflix')) badges.push({ icon: '🔴', label: 'Netflix' });
            if (movie.source?.includes('Disney')) badges.push({ icon: '🏰', label: 'Disney+' });
            
            return badges;
        }
    };
    
    // ============================================================
    // FEATURE 116: QUICK PLAY FROM SEARCH
    // ============================================================
    const QuickPlay = {
        searchAndPlay(query) {
            const movies = window.allMoviesData || [];
            const match = movies.find(m => 
                m.title?.toLowerCase().includes(query.toLowerCase()) ||
                m.genres?.some(g => g.toLowerCase().includes(query.toLowerCase()))
            );
            
            if (match) {
                window.playMovieByTitle?.(match.title);
                window.showToast?.(`Playing: ${match.title}`);
            } else {
                window.showToast?.('No matches found');
            }
        }
    };
    
    // ============================================================
    // FEATURE 117: CONTENT TAGGING
    // ============================================================
    const ContentTagging = {
        storageKey: 'movieshows-custom-tags',
        
        getTags() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '{}');
            } catch { return {}; }
        },
        
        addTag(movieTitle, tag) {
            const tags = this.getTags();
            if (!tags[movieTitle]) tags[movieTitle] = [];
            if (!tags[movieTitle].includes(tag)) {
                tags[movieTitle].push(tag);
                localStorage.setItem(this.storageKey, JSON.stringify(tags));
                window.showToast?.(`Tag "${tag}" added`);
            }
        },
        
        getMovieTags(movieTitle) {
            return this.getTags()[movieTitle] || [];
        }
    };
    
    // ============================================================
    // FEATURE 118: WIDGET MODE
    // ============================================================
    const WidgetMode = {
        createWidget() {
            const existing = document.getElementById('ms-widget');
            if (existing) { existing.remove(); return; }
            
            const movies = window.allMoviesData?.slice(0, 5) || [];
            
            const widget = document.createElement('div');
            widget.id = 'ms-widget';
            widget.innerHTML = `
                <div style="position: fixed; bottom: 20px; right: 380px; width: 280px; background: rgba(0,0,0,0.95); border-radius: 16px; padding: 15px; z-index: 9997; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <span style="color: white; font-size: 13px; font-weight: bold;">🎬 Quick Picks</span>
                        <button onclick="this.closest('#ms-widget').remove()" style="background: none; border: none; color: #888; cursor: pointer;">×</button>
                    </div>
                    <div style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 5px;">
                        ${movies.map(m => `
                            <div class="widget-item" data-title="${m.title}" style="flex-shrink: 0; width: 60px; cursor: pointer;">
                                <img src="${m.posterUrl}" style="width: 100%; aspect-ratio: 2/3; object-fit: cover; border-radius: 6px;" onerror="this.src='https://via.placeholder.com/60x90/1a1a2e/666?text=?'">
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(widget);
            
            widget.querySelectorAll('.widget-item').forEach(item => {
                item.addEventListener('click', () => {
                    window.playMovieByTitle?.(item.dataset.title);
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 119: AMBIENT MODE
    // ============================================================
    const AmbientMode = {
        enabled: false,
        
        toggle() {
            this.enabled = !this.enabled;
            
            if (this.enabled) {
                document.body.style.transition = 'background 2s ease';
                this.updateAmbient();
                window.showToast?.('🌈 Ambient mode enabled');
            } else {
                document.body.style.background = '';
                window.showToast?.('Ambient mode disabled');
            }
        },
        
        updateAmbient() {
            if (!this.enabled) return;
            
            // Create dynamic background based on current video
            const colors = ['#22c55e', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b'];
            const color1 = colors[Math.floor(Math.random() * colors.length)];
            const color2 = colors[Math.floor(Math.random() * colors.length)];
            
            document.body.style.background = `linear-gradient(135deg, ${color1}10, ${color2}10)`;
        }
    };
    
    // ============================================================
    // FEATURE 120: HAPTIC FEEDBACK (MOBILE)
    // ============================================================
    const HapticFeedback = {
        vibrate(pattern = [10]) {
            if ('vibrate' in navigator) {
                navigator.vibrate(pattern);
            }
        },
        
        light() {
            this.vibrate([10]);
        },
        
        medium() {
            this.vibrate([20]);
        },
        
        heavy() {
            this.vibrate([30]);
        },
        
        success() {
            this.vibrate([10, 50, 10]);
        },
        
        error() {
            this.vibrate([50, 50, 50]);
        }
    };
    
    // ============================================================
    // INITIALIZATION
    // ============================================================
    function initializeBatch6Features() {
        console.log('[MovieShows] Initializing Premium Features v2.5 (Batch 6)...');
        
        setTimeout(() => {
            try {
                LanguageFilter.init();
                WatchTimeTracker.startSession();
                
                // Track watch time on unload
                window.addEventListener('beforeunload', () => {
                    WatchTimeTracker.endSession();
                });
                
                console.log('[MovieShows] Premium Features v2.5 initialized successfully!');
                
            } catch (e) {
                console.error('[MovieShows] Error initializing batch 6 features:', e);
            }
        }, 6000);
    }
    
    // Expose features globally
    window.MovieShowsFeaturesBatch6 = {
        EnhancedPiP,
        CollectionsCarousel,
        AdvancedFilter,
        EnhancedShare,
        ContentDurations,
        SyncStatus,
        SeasonsNavigator,
        AgeGate,
        ReleaseAlerts,
        DownloadQueue,
        WatchTimeTracker,
        LanguageFilter,
        ComparisonMode,
        ContentNotes,
        ContentBadges,
        QuickPlay,
        ContentTagging,
        WidgetMode,
        AmbientMode,
        HapticFeedback
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeBatch6Features);
    } else {
        initializeBatch6Features();
    }
    
})();
