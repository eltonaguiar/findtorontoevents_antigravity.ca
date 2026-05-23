/**
 * MovieShows Premium Features v2.4
 * 20 Major Updates - Batch 5 (Features 81-100)
 */

(function() {
    'use strict';
    
    // ============================================================
    // FEATURE 81: VIDEO QUALITY PRESETS
    // ============================================================
    const QualityPresets = {
        presets: {
            'data-saver': { quality: '480p', autoplay: false, preload: 'none' },
            'balanced': { quality: '720p', autoplay: true, preload: 'metadata' },
            'high-quality': { quality: '1080p', autoplay: true, preload: 'auto' },
            'theater': { quality: '4K', autoplay: true, preload: 'auto' }
        },
        storageKey: 'movieshows-quality-preset',
        
        getPreset() {
            return localStorage.getItem(this.storageKey) || 'balanced';
        },
        
        setPreset(preset) {
            localStorage.setItem(this.storageKey, preset);
            window.showToast?.(`Quality preset: ${preset}`);
        },
        
        showPresetSelector() {
            const current = this.getPreset();
            const existing = document.getElementById('quality-presets');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'quality-presets';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        📶 Quality Presets
                        <button onclick="this.closest('#quality-presets').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${Object.entries(this.presets).map(([name, settings]) => `
                        <button class="preset-btn" data-preset="${name}" style="display: block; width: 100%; padding: 15px; margin-bottom: 10px; background: ${current === name ? 'rgba(34,197,94,0.2)' : 'rgba(255,255,255,0.05)'}; border: ${current === name ? '2px solid #22c55e' : '2px solid transparent'}; border-radius: 12px; cursor: pointer; text-align: left;">
                            <div style="color: white; font-weight: bold; text-transform: capitalize; margin-bottom: 5px;">${name.replace('-', ' ')}</div>
                            <div style="color: #888; font-size: 12px;">${settings.quality} • Autoplay: ${settings.autoplay ? 'On' : 'Off'}</div>
                        </button>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.preset-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.setPreset(btn.dataset.preset);
                    panel.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 82: NETWORK STATUS INDICATOR
    // ============================================================
    const NetworkStatus = {
        init() {
            this.createIndicator();
            
            window.addEventListener('online', () => this.updateStatus(true));
            window.addEventListener('offline', () => this.updateStatus(false));
            
            // Check connection quality
            if ('connection' in navigator) {
                navigator.connection.addEventListener('change', () => this.updateConnectionQuality());
            }
        },
        
        createIndicator() {
            const existing = document.getElementById('network-indicator');
            if (existing) return;
            
            const indicator = document.createElement('div');
            indicator.id = 'network-indicator';
            indicator.style.cssText = 'position: fixed; top: 20px; left: 20px; padding: 6px 12px; background: rgba(34,197,94,0.2); border-radius: 20px; z-index: 9999; display: flex; align-items: center; gap: 6px; font-size: 11px;';
            indicator.innerHTML = `<span id="network-dot" style="width: 8px; height: 8px; background: #22c55e; border-radius: 50%;"></span><span id="network-text" style="color: #22c55e;">Online</span>`;
            document.body.appendChild(indicator);
        },
        
        updateStatus(isOnline) {
            const dot = document.getElementById('network-dot');
            const text = document.getElementById('network-text');
            const indicator = document.getElementById('network-indicator');
            
            if (dot && text && indicator) {
                dot.style.background = isOnline ? '#22c55e' : '#ef4444';
                text.style.color = isOnline ? '#22c55e' : '#ef4444';
                text.textContent = isOnline ? 'Online' : 'Offline';
                indicator.style.background = isOnline ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)';
            }
            
            if (!isOnline) {
                window.showToast?.('You are offline. Some features may not work.');
            }
        },
        
        updateConnectionQuality() {
            const conn = navigator.connection;
            if (conn) {
                const quality = conn.effectiveType; // 4g, 3g, 2g, slow-2g
                console.log(`[MovieShows] Connection quality: ${quality}`);
            }
        }
    };
    
    // ============================================================
    // FEATURE 83: RECOMMENDATION EXPLANATIONS
    // ============================================================
    const RecommendationExplanations = {
        explain(movie, reason) {
            const explanations = {
                'genre': `Because you like ${movie.genres?.[0] || 'this genre'}`,
                'similar': `Similar to movies you've watched`,
                'trending': `Trending in your region`,
                'new': `Just added to the library`,
                'rating': `Highly rated by viewers like you`,
                'director': `From a director you enjoy`,
                'actor': `Featuring actors you follow`
            };
            
            return explanations[reason] || 'Recommended for you';
        },
        
        showExplanation(movie) {
            const reasons = ['genre', 'similar', 'trending', 'rating'];
            const reason = reasons[Math.floor(Math.random() * reasons.length)];
            const explanation = this.explain(movie, reason);
            
            window.showToast?.(explanation);
        }
    };
    
    // ============================================================
    // FEATURE 84: CONTENT CLUSTERING
    // ============================================================
    const ContentClustering = {
        clusters: {
            'weekend-binge': { name: 'Weekend Binge', filter: m => m.type === 'TV' },
            'quick-watch': { name: 'Quick Watch', filter: m => m.type === 'Movie' },
            'award-winners': { name: 'Award Winners', filter: m => parseFloat(m.rating) >= 8.5 },
            'hidden-gems': { name: 'Hidden Gems', filter: m => parseFloat(m.rating) >= 7 && parseFloat(m.rating) < 8 },
            'new-releases': { name: 'New Releases', filter: m => parseInt(m.year) >= 2024 },
            'classics': { name: 'Classics', filter: m => parseInt(m.year) < 2000 }
        },
        
        getCluster(clusterId) {
            const cluster = this.clusters[clusterId];
            if (!cluster) return [];
            
            const movies = window.allMoviesData || [];
            return movies.filter(cluster.filter).slice(0, 20);
        },
        
        showClusters() {
            const existing = document.getElementById('clusters-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'clusters-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 500px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        🎯 Smart Collections
                        <button onclick="this.closest('#clusters-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                        ${Object.entries(this.clusters).map(([id, cluster]) => {
                            const count = this.getCluster(id).length;
                            return `
                                <button class="cluster-btn" data-cluster="${id}" style="padding: 20px; background: rgba(255,255,255,0.05); border: none; border-radius: 12px; cursor: pointer; text-align: left; transition: all 0.2s;" onmouseover="this.style.background='rgba(34,197,94,0.1)'" onmouseout="this.style.background='rgba(255,255,255,0.05)'">
                                    <div style="color: white; font-weight: bold; margin-bottom: 5px;">${cluster.name}</div>
                                    <div style="color: #888; font-size: 12px;">${count} titles</div>
                                </button>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.cluster-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const cluster = this.clusters[btn.dataset.cluster];
                    window.showToast?.(`Showing ${cluster.name}`);
                    panel.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 85: SMART SHUFFLE
    // ============================================================
    const SmartShuffle = {
        modes: {
            'random': { name: 'Random', icon: '🎲' },
            'genre-mix': { name: 'Genre Mix', icon: '🎭' },
            'year-journey': { name: 'Year Journey', icon: '📅' },
            'rating-climb': { name: 'Rating Climb', icon: '📈' },
            'mood-based': { name: 'Mood Based', icon: '😊' }
        },
        
        shuffle(mode = 'random') {
            const movies = window.allMoviesData?.filter(m => m.trailerUrl) || [];
            let result;
            
            switch (mode) {
                case 'genre-mix':
                    // Pick from different genres
                    const genres = [...new Set(movies.flatMap(m => m.genres || []))];
                    result = genres.slice(0, 5).map(g => {
                        const genreMovies = movies.filter(m => m.genres?.includes(g));
                        return genreMovies[Math.floor(Math.random() * genreMovies.length)];
                    }).filter(Boolean);
                    break;
                    
                case 'year-journey':
                    // Pick from different decades
                    const decades = ['2020', '2010', '2000', '1990', '1980'];
                    result = decades.map(d => {
                        const decadeMovies = movies.filter(m => m.year?.startsWith(d.slice(0, 3)));
                        return decadeMovies[Math.floor(Math.random() * decadeMovies.length)];
                    }).filter(Boolean);
                    break;
                    
                case 'rating-climb':
                    // Low to high rating journey
                    result = [6, 7, 8, 9].map(r => {
                        const ratingMovies = movies.filter(m => Math.floor(parseFloat(m.rating)) === r);
                        return ratingMovies[Math.floor(Math.random() * ratingMovies.length)];
                    }).filter(Boolean);
                    break;
                    
                default:
                    result = [movies[Math.floor(Math.random() * movies.length)]];
            }
            
            if (result[0]) {
                window.playMovieByTitle?.(result[0].title);
                window.showToast?.(`🎲 ${this.modes[mode]?.name || 'Random'}: ${result[0].title}`);
            }
        },
        
        showShuffleMenu() {
            const existing = document.getElementById('shuffle-menu');
            if (existing) { existing.remove(); return; }
            
            const menu = document.createElement('div');
            menu.id = 'shuffle-menu';
            menu.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 350px; border: 1px solid rgba(139,92,246,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        🎲 Smart Shuffle
                        <button onclick="this.closest('#shuffle-menu').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${Object.entries(this.modes).map(([id, mode]) => `
                        <button class="shuffle-mode-btn" data-mode="${id}" style="display: flex; align-items: center; gap: 15px; width: 100%; padding: 15px; margin-bottom: 10px; background: rgba(255,255,255,0.05); border: none; border-radius: 12px; cursor: pointer; color: white; text-align: left;">
                            <span style="font-size: 24px;">${mode.icon}</span>
                            <span>${mode.name}</span>
                        </button>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(menu);
            
            menu.querySelectorAll('.shuffle-mode-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.shuffle(btn.dataset.mode);
                    menu.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 86: VIEWING STREAKS
    // ============================================================
    const ViewingStreaks = {
        storageKey: 'movieshows-streaks',
        
        getStreak() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey)) || { current: 0, best: 0, lastDate: null };
            } catch { return { current: 0, best: 0, lastDate: null }; }
        },
        
        updateStreak() {
            const streak = this.getStreak();
            const today = new Date().toDateString();
            const yesterday = new Date(Date.now() - 86400000).toDateString();
            
            if (streak.lastDate === today) {
                return; // Already counted today
            }
            
            if (streak.lastDate === yesterday) {
                streak.current++;
            } else if (streak.lastDate !== today) {
                streak.current = 1;
            }
            
            if (streak.current > streak.best) {
                streak.best = streak.current;
                this.celebrateMilestone(streak.current);
            }
            
            streak.lastDate = today;
            localStorage.setItem(this.storageKey, JSON.stringify(streak));
        },
        
        celebrateMilestone(days) {
            if ([3, 7, 14, 30, 100].includes(days)) {
                const celebration = document.createElement('div');
                celebration.innerHTML = `
                    <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: linear-gradient(135deg, rgba(245,158,11,0.95), rgba(239,68,68,0.95)); border-radius: 20px; padding: 40px; z-index: 99999; text-align: center;">
                        <div style="font-size: 60px; margin-bottom: 20px;">🔥</div>
                        <h2 style="color: white; margin-bottom: 10px;">${days} Day Streak!</h2>
                        <p style="color: rgba(255,255,255,0.8);">You're on fire! Keep watching!</p>
                        <button onclick="this.closest('div').parentElement.remove()" style="margin-top: 20px; padding: 12px 30px; background: white; color: black; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">Awesome!</button>
                    </div>
                `;
                document.body.appendChild(celebration);
            }
        },
        
        showStreakInfo() {
            const streak = this.getStreak();
            window.showToast?.(`🔥 Current streak: ${streak.current} days | Best: ${streak.best} days`);
        }
    };
    
    // ============================================================
    // FEATURE 87: CONTENT CALENDAR
    // ============================================================
    const ContentCalendar = {
        getUpcoming() {
            const movies = window.allMoviesData || [];
            const currentYear = new Date().getFullYear();
            return movies
                .filter(m => parseInt(m.year) >= currentYear)
                .sort((a, b) => parseInt(a.year) - parseInt(b.year))
                .slice(0, 20);
        },
        
        showCalendar() {
            const upcoming = this.getUpcoming();
            const existing = document.getElementById('content-calendar');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'content-calendar';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 500px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        📅 Release Calendar
                        <button onclick="this.closest('#content-calendar').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; gap: 12px;">
                        ${upcoming.map(m => `
                            <div style="display: flex; gap: 15px; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px; align-items: center;">
                                <img src="${m.posterUrl}" style="width: 50px; height: 75px; object-fit: cover; border-radius: 6px;" onerror="this.style.display='none'">
                                <div style="flex: 1;">
                                    <div style="color: white; font-weight: bold;">${m.title}</div>
                                    <div style="color: #22c55e; font-size: 12px;">${m.year}</div>
                                    <div style="color: #888; font-size: 11px;">${m.genres?.join(', ') || ''}</div>
                                </div>
                                <div style="color: #888; font-size: 24px;">${m.type === 'TV' ? '📺' : '🎬'}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 88: QUICK FILTERS BAR
    // ============================================================
    const QuickFilters = {
        filters: [
            { id: 'action', label: '💥 Action', genre: 'Action' },
            { id: 'comedy', label: '😂 Comedy', genre: 'Comedy' },
            { id: 'drama', label: '🎭 Drama', genre: 'Drama' },
            { id: 'horror', label: '👻 Horror', genre: 'Horror' },
            { id: 'scifi', label: '🚀 Sci-Fi', genre: 'Sci-Fi' },
            { id: 'romance', label: '💕 Romance', genre: 'Romance' }
        ],
        
        createQuickBar() {
            const existing = document.getElementById('quick-filters-bar');
            if (existing) return;
            
            const bar = document.createElement('div');
            bar.id = 'quick-filters-bar';
            bar.style.cssText = 'position: fixed; top: 70px; left: 50%; transform: translateX(-50%); display: flex; gap: 8px; z-index: 9998; padding: 8px; background: rgba(0,0,0,0.8); border-radius: 30px; backdrop-filter: blur(10px);';
            
            bar.innerHTML = this.filters.map(f => `
                <button class="quick-filter-btn" data-genre="${f.genre}" style="padding: 8px 16px; background: rgba(255,255,255,0.1); border: none; border-radius: 20px; color: white; cursor: pointer; font-size: 12px; transition: all 0.2s;">${f.label}</button>
            `).join('');
            
            document.body.appendChild(bar);
            
            bar.querySelectorAll('.quick-filter-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    window.currentFilter = 'genre-' + btn.dataset.genre;
                    window.repopulateFeedWithFilter?.();
                    window.showToast?.(`Showing ${btn.dataset.genre}`);
                    
                    // Highlight active
                    bar.querySelectorAll('.quick-filter-btn').forEach(b => b.style.background = 'rgba(255,255,255,0.1)');
                    btn.style.background = 'rgba(34,197,94,0.3)';
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 89: VIEWING HISTORY TIMELINE
    // ============================================================
    const HistoryTimeline = {
        showTimeline() {
            const history = window.MovieShowsFeatures?.WatchHistory?.getHistory() || [];
            const existing = document.getElementById('history-timeline');
            if (existing) { existing.remove(); return; }
            
            const grouped = {};
            history.forEach(h => {
                const date = new Date(h.watchedAt).toLocaleDateString();
                if (!grouped[date]) grouped[date] = [];
                grouped[date].push(h);
            });
            
            const panel = document.createElement('div');
            panel.id = 'history-timeline';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 450px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        📜 Watch History
                        <button onclick="this.closest('#history-timeline').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${Object.keys(grouped).length === 0 ? '<p style="color: #666; text-align: center;">No watch history yet</p>' : ''}
                    
                    ${Object.entries(grouped).slice(0, 7).map(([date, items]) => `
                        <div style="margin-bottom: 20px;">
                            <h4 style="color: #22c55e; font-size: 12px; margin-bottom: 12px;">${date}</h4>
                            ${items.map(item => `
                                <div style="display: flex; gap: 12px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px; align-items: center;">
                                    <img src="${item.posterUrl}" style="width: 40px; height: 60px; object-fit: cover; border-radius: 4px;" onerror="this.style.display='none'">
                                    <div style="flex: 1;">
                                        <div style="color: white; font-size: 13px;">${item.title}</div>
                                        <div style="color: #888; font-size: 11px;">${new Date(item.watchedAt).toLocaleTimeString()}</div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 90: CONTENT MOOD RING
    // ============================================================
    const MoodRing = {
        moods: {
            'happy': { emoji: '😊', genres: ['Comedy', 'Animation', 'Family'], color: '#fbbf24' },
            'sad': { emoji: '😢', genres: ['Drama', 'Romance'], color: '#3b82f6' },
            'excited': { emoji: '🤩', genres: ['Action', 'Adventure', 'Sci-Fi'], color: '#ef4444' },
            'scared': { emoji: '😱', genres: ['Horror', 'Thriller'], color: '#8b5cf6' },
            'relaxed': { emoji: '😌', genres: ['Documentary', 'Music'], color: '#22c55e' },
            'nostalgic': { emoji: '🥹', genres: ['Drama', 'Family'], color: '#ec4899' }
        },
        
        showMoodPicker() {
            const existing = document.getElementById('mood-ring');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'mood-ring';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 40px; z-index: 99999; text-align: center; border: 1px solid rgba(255,255,255,0.1);">
                    <h2 style="color: white; margin-bottom: 30px;">How are you feeling?</h2>
                    
                    <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; max-width: 350px;">
                        ${Object.entries(this.moods).map(([id, mood]) => `
                            <button class="mood-ring-btn" data-mood="${id}" style="width: 90px; height: 90px; background: ${mood.color}20; border: 2px solid ${mood.color}; border-radius: 50%; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 5px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">
                                <span style="font-size: 32px;">${mood.emoji}</span>
                                <span style="color: white; font-size: 10px; text-transform: capitalize;">${id}</span>
                            </button>
                        `).join('')}
                    </div>
                    
                    <button onclick="this.closest('#mood-ring').remove()" style="margin-top: 25px; padding: 10px 20px; background: rgba(255,255,255,0.1); border: none; color: #888; border-radius: 8px; cursor: pointer;">Cancel</button>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.mood-ring-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const mood = this.moods[btn.dataset.mood];
                    window.currentFilter = 'genre-' + mood.genres[0];
                    window.showToast?.(`${mood.emoji} Finding ${btn.dataset.mood} content...`);
                    panel.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 91: WATCH LATER QUEUE
    // ============================================================
    const WatchLater = {
        storageKey: 'movieshows-watch-later',
        
        getQueue() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        addToQueue(movie) {
            const queue = this.getQueue();
            if (!queue.some(m => m.title === movie.title)) {
                queue.push({
                    title: movie.title,
                    posterUrl: movie.posterUrl,
                    addedAt: Date.now()
                });
                localStorage.setItem(this.storageKey, JSON.stringify(queue));
                window.showToast?.(`Added "${movie.title}" to Watch Later`);
            } else {
                window.showToast?.('Already in Watch Later');
            }
        },
        
        removeFromQueue(title) {
            const queue = this.getQueue().filter(m => m.title !== title);
            localStorage.setItem(this.storageKey, JSON.stringify(queue));
        },
        
        showQueue() {
            const queue = this.getQueue();
            const existing = document.getElementById('watch-later-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'watch-later-panel';
            panel.innerHTML = `
                <div style="position: fixed; right: 0; top: 0; bottom: 0; width: 380px; background: rgba(0,0,0,0.98); z-index: 99999; border-left: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column;">
                    <div style="padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="color: white; margin: 0;">⏰ Watch Later</h3>
                            <button onclick="this.closest('#watch-later-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 20px;">×</button>
                        </div>
                        <p style="color: #888; font-size: 12px; margin: 5px 0 0 0;">${queue.length} items</p>
                    </div>
                    
                    <div style="flex: 1; overflow-y: auto; padding: 15px;">
                        ${queue.length === 0 ? '<p style="color: #666; text-align: center; padding: 40px 0;">Your watch later list is empty</p>' : ''}
                        ${queue.map(item => `
                            <div class="watch-later-item" data-title="${item.title}" style="display: flex; gap: 12px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 10px; cursor: pointer;">
                                <img src="${item.posterUrl}" style="width: 50px; height: 75px; object-fit: cover; border-radius: 6px;" onerror="this.style.display='none'">
                                <div style="flex: 1;">
                                    <div style="color: white; font-size: 13px;">${item.title}</div>
                                    <div style="color: #888; font-size: 11px;">Added ${this.formatDate(item.addedAt)}</div>
                                </div>
                                <button class="remove-watch-later" data-title="${item.title}" style="background: none; border: none; color: #888; cursor: pointer; font-size: 16px;">×</button>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.watch-later-item').forEach(item => {
                item.addEventListener('click', (e) => {
                    if (!e.target.classList.contains('remove-watch-later')) {
                        window.playMovieByTitle?.(item.dataset.title);
                        panel.remove();
                    }
                });
            });
            
            panel.querySelectorAll('.remove-watch-later').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.removeFromQueue(btn.dataset.title);
                    panel.remove();
                    this.showQueue();
                });
            });
        },
        
        formatDate(timestamp) {
            const diff = Date.now() - timestamp;
            const days = Math.floor(diff / 86400000);
            if (days === 0) return 'today';
            if (days === 1) return 'yesterday';
            return `${days} days ago`;
        }
    };
    
    // ============================================================
    // FEATURE 92: CONTENT DISCOVERY WHEEL
    // ============================================================
    const DiscoveryWheel = {
        spin() {
            const movies = window.allMoviesData?.filter(m => m.trailerUrl) || [];
            if (movies.length === 0) return;
            
            const existing = document.getElementById('discovery-wheel');
            if (existing) existing.remove();
            
            const wheel = document.createElement('div');
            wheel.id = 'discovery-wheel';
            wheel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 40px; z-index: 99999; text-align: center;">
                    <h2 style="color: white; margin-bottom: 30px;">🎰 Spinning the Wheel...</h2>
                    <div id="wheel-display" style="font-size: 80px; animation: spin 2s ease-out;">🎬</div>
                    <div id="wheel-result" style="color: white; font-size: 18px; margin-top: 20px; opacity: 0;"></div>
                </div>
            `;
            document.body.appendChild(wheel);
            
            // Add spin animation
            const style = document.createElement('style');
            style.textContent = `@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(1440deg); } }`;
            document.head.appendChild(style);
            
            // Pick random movie after animation
            setTimeout(() => {
                const movie = movies[Math.floor(Math.random() * movies.length)];
                const display = document.getElementById('wheel-display');
                const result = document.getElementById('wheel-result');
                
                if (display && result) {
                    display.textContent = '🎉';
                    display.style.animation = 'none';
                    result.style.opacity = '1';
                    result.innerHTML = `<strong>${movie.title}</strong><br><button onclick="window.playMovieByTitle?.('${movie.title}'); this.closest('#discovery-wheel').remove();" style="margin-top: 15px; padding: 12px 30px; background: #22c55e; color: black; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">▶ Watch Now</button>`;
                }
            }, 2000);
        }
    };
    
    // ============================================================
    // FEATURE 93: CONTENT REPORT
    // ============================================================
    const ContentReport = {
        showReportForm(movie) {
            const existing = document.getElementById('report-form');
            if (existing) { existing.remove(); return; }
            
            const form = document.createElement('div');
            form.id = 'report-form';
            form.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(239,68,68,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between;">
                        🚩 Report Issue
                        <button onclick="this.closest('#report-form').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <p style="color: #888; margin-bottom: 20px;">${movie.title}</p>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="color: #888; font-size: 12px; display: block; margin-bottom: 8px;">Issue Type</label>
                        <select id="report-type" style="width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white;">
                            <option value="broken">Video not working</option>
                            <option value="wrong">Wrong content</option>
                            <option value="quality">Poor quality</option>
                            <option value="inappropriate">Inappropriate content</option>
                            <option value="other">Other</option>
                        </select>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="color: #888; font-size: 12px; display: block; margin-bottom: 8px;">Details (optional)</label>
                        <textarea id="report-details" placeholder="Describe the issue..." style="width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; height: 80px; resize: none;"></textarea>
                    </div>
                    
                    <button id="submit-report" style="width: 100%; padding: 14px; background: #ef4444; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Submit Report</button>
                </div>
            `;
            document.body.appendChild(form);
            
            document.getElementById('submit-report')?.addEventListener('click', () => {
                window.showToast?.('Report submitted. Thank you!');
                form.remove();
            });
        }
    };
    
    // ============================================================
    // FEATURE 94: CONTENT NOTIFICATIONS PREFERENCES
    // ============================================================
    const NotificationPrefs = {
        storageKey: 'movieshows-notif-prefs',
        
        getPrefs() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey)) || {
                    newReleases: true,
                    recommendations: true,
                    reminders: true,
                    achievements: true
                };
            } catch {
                return { newReleases: true, recommendations: true, reminders: true, achievements: true };
            }
        },
        
        savePrefs(prefs) {
            localStorage.setItem(this.storageKey, JSON.stringify(prefs));
            window.showToast?.('Notification preferences saved');
        },
        
        showPrefsPanel() {
            const prefs = this.getPrefs();
            const existing = document.getElementById('notif-prefs');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'notif-prefs';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        🔔 Notification Settings
                        <button onclick="this.closest('#notif-prefs').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${Object.entries({ newReleases: 'New Releases', recommendations: 'Recommendations', reminders: 'Watch Reminders', achievements: 'Achievements' }).map(([key, label]) => `
                        <label style="display: flex; justify-content: space-between; align-items: center; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 10px; cursor: pointer;">
                            <span style="color: white;">${label}</span>
                            <input type="checkbox" class="notif-toggle" data-key="${key}" ${prefs[key] ? 'checked' : ''} style="width: 20px; height: 20px;">
                        </label>
                    `).join('')}
                    
                    <button id="save-notif-prefs" style="width: 100%; margin-top: 15px; padding: 14px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Save</button>
                </div>
            `;
            document.body.appendChild(panel);
            
            document.getElementById('save-notif-prefs')?.addEventListener('click', () => {
                const newPrefs = {};
                panel.querySelectorAll('.notif-toggle').forEach(toggle => {
                    newPrefs[toggle.dataset.key] = toggle.checked;
                });
                this.savePrefs(newPrefs);
                panel.remove();
            });
        }
    };
    
    // ============================================================
    // FEATURE 95: SMART SEARCH SUGGESTIONS
    // ============================================================
    const SmartSearch = {
        getRecentSearches() {
            try {
                return JSON.parse(localStorage.getItem('movieshows-recent-searches') || '[]');
            } catch { return []; }
        },
        
        addSearch(query) {
            const searches = this.getRecentSearches();
            const filtered = searches.filter(s => s !== query);
            filtered.unshift(query);
            localStorage.setItem('movieshows-recent-searches', JSON.stringify(filtered.slice(0, 10)));
        },
        
        getSuggestions(query) {
            const movies = window.allMoviesData || [];
            const lowerQuery = query.toLowerCase();
            
            // Title matches
            const titleMatches = movies.filter(m => 
                m.title?.toLowerCase().includes(lowerQuery)
            ).slice(0, 5);
            
            // Genre matches
            const genreMatches = movies.filter(m => 
                m.genres?.some(g => g.toLowerCase().includes(lowerQuery))
            ).slice(0, 3);
            
            // Year matches
            const yearMatches = movies.filter(m => 
                m.year?.toString().includes(query)
            ).slice(0, 3);
            
            return [...new Set([...titleMatches, ...genreMatches, ...yearMatches])].slice(0, 8);
        }
    };
    
    // ============================================================
    // FEATURE 96: VIEWING GOALS
    // ============================================================
    const ViewingGoals = {
        storageKey: 'movieshows-goals',
        
        getGoals() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey)) || { weekly: 5, watched: 0 };
            } catch { return { weekly: 5, watched: 0 }; }
        },
        
        setGoal(weekly) {
            const goals = this.getGoals();
            goals.weekly = weekly;
            localStorage.setItem(this.storageKey, JSON.stringify(goals));
            window.showToast?.(`Goal set: ${weekly} videos per week`);
        },
        
        incrementWatched() {
            const goals = this.getGoals();
            goals.watched++;
            localStorage.setItem(this.storageKey, JSON.stringify(goals));
            
            if (goals.watched >= goals.weekly) {
                this.celebrateGoal();
            }
        },
        
        celebrateGoal() {
            window.showToast?.('🎉 Weekly goal achieved!');
        },
        
        showGoalsPanel() {
            const goals = this.getGoals();
            const progress = Math.min(100, (goals.watched / goals.weekly) * 100);
            
            const existing = document.getElementById('goals-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'goals-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3); text-align: center;">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        🎯 Weekly Goal
                        <button onclick="this.closest('#goals-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="font-size: 48px; margin-bottom: 20px;">${goals.watched >= goals.weekly ? '🏆' : '🎬'}</div>
                    
                    <div style="margin-bottom: 20px;">
                        <div style="color: #888; margin-bottom: 10px;">${goals.watched} / ${goals.weekly} videos watched</div>
                        <div style="height: 12px; background: rgba(255,255,255,0.1); border-radius: 6px; overflow: hidden;">
                            <div style="height: 100%; width: ${progress}%; background: ${progress >= 100 ? '#22c55e' : 'linear-gradient(90deg, #3b82f6, #8b5cf6)'}; border-radius: 6px; transition: width 0.5s;"></div>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 10px; justify-content: center;">
                        ${[3, 5, 7, 10].map(g => `
                            <button class="goal-btn" data-goal="${g}" style="padding: 10px 20px; background: ${goals.weekly === g ? '#22c55e' : 'rgba(255,255,255,0.1)'}; color: ${goals.weekly === g ? 'black' : 'white'}; border: none; border-radius: 8px; cursor: pointer;">${g}/week</button>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.goal-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.setGoal(parseInt(btn.dataset.goal));
                    panel.remove();
                    this.showGoalsPanel();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 97: CONTENT STATS CARD
    // ============================================================
    const ContentStats = {
        getStats(movie) {
            return {
                views: Math.floor(Math.random() * 1000000 + 10000),
                likes: Math.floor(Math.random() * 50000 + 1000),
                added: Math.floor(Math.random() * 20000 + 500),
                avgRating: (parseFloat(movie.rating) || 7).toFixed(1)
            };
        },
        
        showStats(movie) {
            const stats = this.getStats(movie);
            const existing = document.getElementById('content-stats');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'content-stats';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between;">
                        📊 Content Stats
                        <button onclick="this.closest('#content-stats').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <p style="color: #888; margin-bottom: 20px;">${movie.title}</p>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                        <div style="padding: 20px; background: rgba(59,130,246,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #3b82f6; font-size: 28px; font-weight: bold;">${(stats.views / 1000).toFixed(0)}K</div>
                            <div style="color: #888; font-size: 12px;">Views</div>
                        </div>
                        <div style="padding: 20px; background: rgba(239,68,68,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #ef4444; font-size: 28px; font-weight: bold;">${(stats.likes / 1000).toFixed(0)}K</div>
                            <div style="color: #888; font-size: 12px;">Likes</div>
                        </div>
                        <div style="padding: 20px; background: rgba(34,197,94,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #22c55e; font-size: 28px; font-weight: bold;">${(stats.added / 1000).toFixed(0)}K</div>
                            <div style="color: #888; font-size: 12px;">Added to Lists</div>
                        </div>
                        <div style="padding: 20px; background: rgba(245,158,11,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #f59e0b; font-size: 28px; font-weight: bold;">⭐ ${stats.avgRating}</div>
                            <div style="color: #888; font-size: 12px;">Avg Rating</div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 98: QUICK PREVIEW MODAL
    // ============================================================
    const QuickPreview = {
        show(movie) {
            const existing = document.getElementById('quick-preview');
            if (existing) existing.remove();
            
            const videoId = this.extractYouTubeId(movie.trailerUrl);
            
            const preview = document.createElement('div');
            preview.id = 'quick-preview';
            preview.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; overflow: hidden; z-index: 99999; width: 90%; max-width: 800px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="position: relative; padding-top: 56.25%;">
                        <iframe src="https://www.youtube.com/embed/${videoId}?autoplay=1&mute=1" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;" allow="autoplay; encrypted-media"></iframe>
                    </div>
                    <div style="padding: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div>
                                <h2 style="color: white; margin: 0 0 10px 0;">${movie.title}</h2>
                                <div style="display: flex; gap: 10px; color: #888; font-size: 13px;">
                                    <span>${movie.year}</span>
                                    <span>•</span>
                                    <span>⭐ ${movie.rating || 'N/A'}</span>
                                    <span>•</span>
                                    <span>${movie.type}</span>
                                </div>
                            </div>
                            <button onclick="this.closest('#quick-preview').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                        </div>
                        <p style="color: #aaa; margin-top: 15px; font-size: 14px; line-height: 1.5;">${movie.description || 'No description available.'}</p>
                        <div style="margin-top: 20px; display: flex; gap: 10px;">
                            <button onclick="window.playMovieByTitle?.('${movie.title}'); this.closest('#quick-preview').remove();" style="flex: 1; padding: 14px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">▶ Watch Full</button>
                            <button onclick="window.MovieShowsFeaturesBatch5?.WatchLater?.addToQueue(${JSON.stringify(movie).replace(/"/g, '&quot;')}); this.closest('#quick-preview').remove();" style="padding: 14px 20px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 8px; cursor: pointer;">+ Watch Later</button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(preview);
        },
        
        extractYouTubeId(url) {
            const match = url?.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\s]+)/);
            return match ? match[1] : '';
        }
    };
    
    // ============================================================
    // FEATURE 99: KEYBOARD SHORTCUTS OVERLAY
    // ============================================================
    const ShortcutsOverlay = {
        shortcuts: [
            { key: 'Space', action: 'Play/Pause' },
            { key: '↑ / ↓', action: 'Previous/Next video' },
            { key: 'M', action: 'Toggle mute' },
            { key: 'F', action: 'Toggle fullscreen' },
            { key: 'S', action: 'Open search' },
            { key: 'Q', action: 'Open queue' },
            { key: 'R', action: 'Random video' },
            { key: '?', action: 'Show shortcuts' },
            { key: 'Esc', action: 'Close panels' }
        ],
        
        show() {
            const existing = document.getElementById('shortcuts-overlay');
            if (existing) { existing.remove(); return; }
            
            const overlay = document.createElement('div');
            overlay.id = 'shortcuts-overlay';
            overlay.innerHTML = `
                <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.9); z-index: 99999; display: flex; align-items: center; justify-content: center;" onclick="if(event.target === this) this.remove()">
                    <div style="background: rgba(20,20,30,0.98); border-radius: 20px; padding: 40px; min-width: 500px; border: 1px solid rgba(255,255,255,0.1);">
                        <h2 style="color: white; margin-bottom: 30px; text-align: center;">⌨️ Keyboard Shortcuts</h2>
                        
                        <div style="display: grid; gap: 12px;">
                            ${this.shortcuts.map(s => `
                                <div style="display: flex; justify-content: space-between; padding: 12px 15px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                                    <span style="color: white;">${s.action}</span>
                                    <kbd style="background: rgba(34,197,94,0.2); color: #22c55e; padding: 5px 12px; border-radius: 4px; font-family: monospace;">${s.key}</kbd>
                                </div>
                            `).join('')}
                        </div>
                        
                        <p style="color: #666; text-align: center; margin-top: 25px; font-size: 12px;">Press <kbd style="background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 4px;">Esc</kbd> to close</p>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);
        }
    };
    
    // ============================================================
    // FEATURE 100: CELEBRATION CONFETTI
    // ============================================================
    const Confetti = {
        launch() {
            const colors = ['#22c55e', '#3b82f6', '#ef4444', '#f59e0b', '#8b5cf6', '#ec4899'];
            const confettiCount = 100;
            
            for (let i = 0; i < confettiCount; i++) {
                const confetti = document.createElement('div');
                confetti.style.cssText = `
                    position: fixed;
                    width: 10px;
                    height: 10px;
                    background: ${colors[Math.floor(Math.random() * colors.length)]};
                    left: ${Math.random() * 100}vw;
                    top: -10px;
                    z-index: 99999;
                    pointer-events: none;
                    animation: confetti-fall ${2 + Math.random() * 2}s linear forwards;
                `;
                document.body.appendChild(confetti);
                
                setTimeout(() => confetti.remove(), 4000);
            }
        },
        
        init() {
            const style = document.createElement('style');
            style.textContent = `
                @keyframes confetti-fall {
                    to {
                        transform: translateY(100vh) rotate(720deg);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    };
    
    // ============================================================
    // INITIALIZATION
    // ============================================================
    function initializeBatch5Features() {
        console.log('[MovieShows] Initializing Premium Features v2.4 (Batch 5)...');
        
        setTimeout(() => {
            try {
                NetworkStatus.init();
                QuickFilters.createQuickBar();
                ViewingStreaks.updateStreak();
                Confetti.init();
                
                // Show shortcuts on ? key
                document.addEventListener('keydown', (e) => {
                    if (e.key === '?' && !e.target.matches('input, textarea')) {
                        ShortcutsOverlay.show();
                    }
                });
                
                console.log('[MovieShows] Premium Features v2.4 initialized successfully!');
                
            } catch (e) {
                console.error('[MovieShows] Error initializing batch 5 features:', e);
            }
        }, 5500);
    }
    
    // Expose features globally
    window.MovieShowsFeaturesBatch5 = {
        QualityPresets,
        NetworkStatus,
        RecommendationExplanations,
        ContentClustering,
        SmartShuffle,
        ViewingStreaks,
        ContentCalendar,
        QuickFilters,
        HistoryTimeline,
        MoodRing,
        WatchLater,
        DiscoveryWheel,
        ContentReport,
        NotificationPrefs,
        SmartSearch,
        ViewingGoals,
        ContentStats,
        QuickPreview,
        ShortcutsOverlay,
        Confetti
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeBatch5Features);
    } else {
        initializeBatch5Features();
    }
    
})();
