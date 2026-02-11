/**
 * MovieShows Database Connector
 * Integrates frontend with MySQL database via PHP API
 * Falls back to localStorage when API is unavailable
 */

const MovieShowsDB = {
    // API base URL - update this when deployed
    API_BASE: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? '/api'  // Local development
        : 'https://findtorontoevents.ca/MOVIESHOWS2/api', // Production
    
    // User ID (stored in localStorage for persistence)
    userId: null,
    
    // Connection status
    isConnected: false,
    lastSyncTime: null,
    
    // Pending operations queue (for offline support)
    pendingOps: [],
    
    /**
     * Initialize the database connector
     */
    init() {
        // Get or create user ID
        this.userId = localStorage.getItem('movieshows-user-id');
        if (!this.userId) {
            this.userId = 'user_' + this.generateId();
            localStorage.setItem('movieshows-user-id', this.userId);
        }
        
        // Test connection
        this.testConnection();
        
        // Set up auto-sync
        this.setupAutoSync();
        
        // Process any pending operations
        this.processPendingOps();
        
        console.log('[MovieShows DB] Connector initialized, user:', this.userId.substring(0, 15) + '...');
        
        return this;
    },
    
    /**
     * Generate random ID
     */
    generateId() {
        return Math.random().toString(36).substring(2) + Date.now().toString(36);
    },
    
    /**
     * Test database connection
     */
    async testConnection() {
        try {
            const response = await this.fetchAPI('movies.php?action=stats');
            if (response && response.success) {
                this.isConnected = true;
                console.log('[MovieShows DB] Connected to database');
                this.showConnectionStatus(true);
                return true;
            }
        } catch (error) {
            // Silently handle - using localStorage is fine
        }
        this.isConnected = false;
        console.log('[MovieShows DB] Using localStorage (offline mode)');
        this.showConnectionStatus(false);
        return false;
    },
    
    /**
     * Show connection status indicator
     */
    showConnectionStatus(connected) {
        let indicator = document.getElementById('db-status-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'db-status-indicator';
            indicator.style.cssText = `
                position: fixed; bottom: 10px; left: 10px; z-index: 9999;
                padding: 6px 12px; border-radius: 20px; font-size: 11px;
                display: flex; align-items: center; gap: 6px;
                background: rgba(0,0,0,0.8); backdrop-filter: blur(10px);
                transition: all 0.3s; cursor: pointer;
            `;
            indicator.onclick = () => this.showSyncPanel();
            document.body.appendChild(indicator);
        }
        
        indicator.innerHTML = connected 
            ? `<span style="width: 8px; height: 8px; background: #22c55e; border-radius: 50%;"></span><span style="color: #22c55e;">Synced</span>`
            : `<span style="width: 8px; height: 8px; background: #f59e0b; border-radius: 50%;"></span><span style="color: #f59e0b;">Local</span>`;
    },
    
    /**
     * Make API request
     */
    async fetchAPI(endpoint, options = {}) {
        const url = `${this.API_BASE}/${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-User-Id': this.userId
            }
        };
        
        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: { ...defaultOptions.headers, ...options.headers }
        };
        
        try {
            const response = await fetch(url, mergedOptions);
            const text = await response.text();
            
            // Check if response is HTML (PHP error) instead of JSON
            if (text.startsWith('<') || text.startsWith('<!')) {
                // API returned HTML error - silently fail, app will use localStorage
                throw new Error('API returned HTML instead of JSON');
            }
            
            return JSON.parse(text);
        } catch (error) {
            // Silently handle - localStorage fallback is fine
            throw error;
        }
    },
    
    // ==================== MOVIES ====================
    
    /**
     * Get all movies from database
     */
    async getMovies(options = {}) {
        const { type, year, limit = 100, offset = 0 } = options;
        
        let endpoint = `movies.php?action=list&limit=${limit}&offset=${offset}`;
        if (type) endpoint += `&type=${type}`;
        if (year) endpoint += `&year=${year}`;
        
        try {
            const response = await this.fetchAPI(endpoint);
            if (response.success) {
                return response.data;
            }
        } catch (error) {
            // Silently fail - use fallback
        }
        
        // Fallback to allMoviesData
        return window.allMoviesData || [];
    },
    
    /**
     * Search movies
     */
    async searchMovies(query, limit = 20) {
        if (!query || query.length < 2) return [];
        
        try {
            const response = await this.fetchAPI(`movies.php?action=search&q=${encodeURIComponent(query)}&limit=${limit}`);
            if (response.success) {
                return response.data;
            }
        } catch (error) {
            // Silently fail - use local search
        }
        
        // Fallback to local search
        const movies = window.allMoviesData || [];
        return movies.filter(m => 
            m.title?.toLowerCase().includes(query.toLowerCase())
        ).slice(0, limit);
    },
    
    /**
     * Get random movies
     */
    async getRandomMovies(count = 10, type = null) {
        try {
            let endpoint = `movies.php?action=random&count=${count}`;
            if (type) endpoint += `&type=${type}`;
            
            const response = await this.fetchAPI(endpoint);
            if (response.success) {
                return response.data;
            }
        } catch (error) {
            // Silently fail - use local random
        }
        
        // Fallback to local random
        const movies = type 
            ? (window.allMoviesData || []).filter(m => m.type === type)
            : (window.allMoviesData || []);
        return movies.sort(() => Math.random() - 0.5).slice(0, count);
    },
    
    /**
     * Get database stats
     */
    async getStats() {
        try {
            const response = await this.fetchAPI('movies.php?action=stats');
            if (response.success) {
                return response.data;
            }
        } catch (error) {
            // Silently fail - use local stats
        }
        
        // Fallback stats
        const movies = window.allMoviesData || [];
        return {
            totalMovies: movies.length,
            movies: movies.filter(m => m.type === 'movie').length,
            tvShows: movies.filter(m => m.type === 'tv').length,
            trailers: movies.filter(m => m.trailerUrl).length
        };
    },
    
    /**
     * Sync local movies to database
     */
    async syncMoviesToDB() {
        const movies = window.allMoviesData || [];
        if (movies.length === 0) {
            console.log('[MovieShows DB] No movies to sync');
            return { synced: 0 };
        }
        
        // Format movies for API
        const formatted = movies.map(m => ({
            title: m.title,
            type: m.type || 'movie',
            genre: m.genre,
            year: m.year,
            trailerUrl: m.trailerUrl,
            posterUrl: m.posterUrl || m.image,
            youtubeId: this.extractYouTubeId(m.trailerUrl)
        }));
        
        try {
            const response = await this.fetchAPI('movies.php?action=bulk-add', {
                method: 'POST',
                body: JSON.stringify({ movies: formatted })
            });
            
            if (response.success) {
                console.log(`[MovieShows DB] Synced ${response.added} new, ${response.updated} updated`);
                this.lastSyncTime = Date.now();
                localStorage.setItem('movieshows-last-sync', this.lastSyncTime);
                return response;
            }
        } catch (error) {
            // Add to pending for retry later
            this.addToPendingOps({ type: 'sync-movies', data: formatted });
        }
        
        return { synced: 0, error: true };
    },
    
    // ==================== USER QUEUE ====================
    
    /**
     * Get user's queue from database
     */
    async getQueue() {
        try {
            const response = await this.fetchAPI('user.php?action=queue');
            if (response.success && response.data.length > 0) {
                // Update localStorage with DB data
                localStorage.setItem('movieshows-queue', JSON.stringify(response.data));
                return response.data;
            }
        } catch (error) {
            // Silently fail - use localStorage
        }
        
        // Fallback to localStorage
        return JSON.parse(localStorage.getItem('movieshows-queue') || '[]');
    },
    
    /**
     * Add to queue
     */
    async addToQueue(movie) {
        // Always update localStorage first
        const localQueue = JSON.parse(localStorage.getItem('movieshows-queue') || '[]');
        if (!localQueue.some(q => q.title === movie.title)) {
            localQueue.push(movie);
            localStorage.setItem('movieshows-queue', JSON.stringify(localQueue));
        }
        
        // Then sync to database
        if (this.isConnected) {
            try {
                await this.fetchAPI('user.php?action=queue-add', {
                    method: 'POST',
                    body: JSON.stringify({
                        title: movie.title,
                        type: movie.type,
                        year: movie.year,
                        posterUrl: movie.posterUrl,
                        youtubeId: this.extractYouTubeId(movie.trailerUrl)
                    })
                });
            } catch (error) {
                this.addToPendingOps({ type: 'add-queue', data: movie });
            }
        }
        
        return true;
    },
    
    /**
     * Sync entire queue to database
     */
    async syncQueue() {
        const localQueue = JSON.parse(localStorage.getItem('movieshows-queue') || '[]');
        
        if (localQueue.length === 0 || !this.isConnected) return;
        
        try {
            await this.fetchAPI('user.php?action=queue-sync', {
                method: 'POST',
                body: JSON.stringify({ queue: localQueue })
            });
            console.log('[MovieShows DB] Queue synced');
        } catch (error) {
            // Silently fail
        }
    },
    
    /**
     * Remove from queue
     */
    async removeFromQueue(movieId) {
        if (this.isConnected) {
            try {
                await this.fetchAPI(`user.php?action=queue-remove&movie_id=${movieId}`, {
                    method: 'DELETE'
                });
        } catch (error) {
            // Silently fail
        }
        }
    },
    
    // ==================== PLAYLISTS ====================
    
    /**
     * Create shared playlist
     */
    async createPlaylist(title, items = []) {
        if (!this.isConnected) {
            // Generate local code
            const code = 'LOCAL-' + Math.random().toString(36).substring(2, 10).toUpperCase();
            localStorage.setItem(`playlist-${code}`, JSON.stringify({ title, items }));
            return { success: true, shareCode: code, local: true };
        }
        
        try {
            const response = await this.fetchAPI('playlists.php?action=create', {
                method: 'POST',
                body: JSON.stringify({ title, items })
            });
            return response;
        } catch (error) {
            return { success: false, error: 'Offline' };
        }
    },
    
    /**
     * Get playlist by code
     */
    async getPlaylist(code) {
        // Check local first
        const local = localStorage.getItem(`playlist-${code}`);
        if (local) {
            return { success: true, data: JSON.parse(local), local: true };
        }
        
        if (!this.isConnected) {
            return { success: false, error: 'Offline' };
        }
        
        try {
            return await this.fetchAPI(`playlists.php?action=get&code=${code}`);
        } catch (error) {
            return { success: false, error: error.message };
        }
    },
    
    // ==================== PREFERENCES ====================
    
    /**
     * Get user preferences
     */
    async getPreferences() {
        try {
            const response = await this.fetchAPI('user.php?action=preferences');
            if (response.success) {
                return response.data;
            }
        } catch (error) {
            // Silently fail - use localStorage
        }
        
        // Fallback to localStorage
        return {
            autoplay: localStorage.getItem('movieshows-autoplay') !== 'false',
            sound_on_scroll: localStorage.getItem('movieshows-muted') !== 'true',
            rewatch_enabled: localStorage.getItem('movieshows-rewatch') === 'true'
        };
    },
    
    /**
     * Save preferences
     */
    async savePreferences(prefs) {
        // Save locally
        if (prefs.autoplay !== undefined) {
            localStorage.setItem('movieshows-autoplay', prefs.autoplay);
        }
        if (prefs.sound_on_scroll !== undefined) {
            localStorage.setItem('movieshows-muted', !prefs.sound_on_scroll);
        }
        
        // Sync to database
        if (this.isConnected) {
            try {
                await this.fetchAPI('user.php?action=preferences', {
                    method: 'POST',
                    body: JSON.stringify(prefs)
                });
            } catch (error) {
                this.addToPendingOps({ type: 'save-prefs', data: prefs });
            }
        }
    },
    
    // ==================== UTILITIES ====================
    
    /**
     * Extract YouTube video ID
     */
    extractYouTubeId(url) {
        if (!url) return null;
        if (/^[a-zA-Z0-9_-]{11}$/.test(url)) return url;
        
        const match = url.match(/(?:youtube\.com\/(?:embed\/|watch\?v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
        return match ? match[1] : null;
    },
    
    /**
     * Set up auto-sync
     */
    setupAutoSync() {
        // Sync queue when leaving page
        window.addEventListener('beforeunload', () => {
            if (this.isConnected) {
                this.syncQueue();
            }
        });
        
        // Periodic sync check
        setInterval(() => {
            if (this.isConnected) {
                this.processPendingOps();
            }
        }, 60000); // Every minute
        
        // Sync on visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && this.isConnected) {
                this.processPendingOps();
            }
        });
    },
    
    /**
     * Add operation to pending queue
     */
    addToPendingOps(op) {
        this.pendingOps.push({ ...op, timestamp: Date.now() });
        localStorage.setItem('movieshows-pending-ops', JSON.stringify(this.pendingOps));
    },
    
    /**
     * Process pending operations
     */
    async processPendingOps() {
        const stored = localStorage.getItem('movieshows-pending-ops');
        if (stored) {
            this.pendingOps = JSON.parse(stored);
        }
        
        if (this.pendingOps.length === 0 || !this.isConnected) return;
        
        const processed = [];
        
        for (const op of this.pendingOps) {
            try {
                switch (op.type) {
                    case 'sync-movies':
                        await this.fetchAPI('movies.php?action=bulk-add', {
                            method: 'POST',
                            body: JSON.stringify({ movies: op.data })
                        });
                        break;
                    case 'add-queue':
                        await this.fetchAPI('user.php?action=queue-add', {
                            method: 'POST',
                            body: JSON.stringify(op.data)
                        });
                        break;
                    case 'save-prefs':
                        await this.fetchAPI('user.php?action=preferences', {
                            method: 'POST',
                            body: JSON.stringify(op.data)
                        });
                        break;
                }
                processed.push(op);
            } catch (error) {
                // Will retry next time
            }
        }
        
        // Remove processed operations
        this.pendingOps = this.pendingOps.filter(op => !processed.includes(op));
        localStorage.setItem('movieshows-pending-ops', JSON.stringify(this.pendingOps));
    },
    
    /**
     * Show sync panel
     */
    showSyncPanel() {
        let panel = document.getElementById('db-sync-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'db-sync-panel';
        panel.style.cssText = `
            position: fixed; bottom: 50px; left: 10px; z-index: 10000;
            width: 300px; background: rgba(20, 20, 30, 0.98);
            border-radius: 16px; padding: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.6);
            border: 1px solid rgba(255,255,255,0.1);
        `;
        
        const lastSync = localStorage.getItem('movieshows-last-sync');
        const lastSyncText = lastSync 
            ? new Date(parseInt(lastSync)).toLocaleString()
            : 'Never';
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="color: white; margin: 0; font-size: 16px;">🔄 Database Sync</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 20px; cursor: pointer;">×</button>
            </div>
            
            <div style="margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #888;">Status</span>
                    <span style="color: ${this.isConnected ? '#22c55e' : '#f59e0b'};">${this.isConnected ? 'Connected' : 'Offline'}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #888;">Last Sync</span>
                    <span style="color: white;">${lastSyncText}</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #888;">Pending Ops</span>
                    <span style="color: white;">${this.pendingOps.length}</span>
                </div>
            </div>
            
            <button id="sync-movies-btn" style="
                width: 100%; padding: 12px; background: linear-gradient(135deg, #3b82f6, #6366f1);
                border: none; border-radius: 8px; color: white; font-weight: bold;
                cursor: pointer; margin-bottom: 10px;
            ">📤 Sync Movies to Database</button>
            
            <button id="sync-queue-btn" style="
                width: 100%; padding: 12px; background: linear-gradient(135deg, #22c55e, #16a34a);
                border: none; border-radius: 8px; color: white; font-weight: bold;
                cursor: pointer; margin-bottom: 10px;
            ">📋 Sync Queue</button>
            
            <button id="test-connection-btn" style="
                width: 100%; padding: 12px; background: rgba(255,255,255,0.1);
                border: none; border-radius: 8px; color: white;
                cursor: pointer;
            ">🔌 Test Connection</button>
        `;
        
        document.body.appendChild(panel);
        
        // Button handlers
        panel.querySelector('#sync-movies-btn')?.addEventListener('click', async () => {
            const btn = panel.querySelector('#sync-movies-btn');
            btn.textContent = '⏳ Syncing...';
            btn.disabled = true;
            
            const result = await this.syncMoviesToDB();
            
            btn.textContent = result.error 
                ? '❌ Sync Failed' 
                : `✅ Synced ${result.added || 0} movies`;
            
            setTimeout(() => {
                btn.textContent = '📤 Sync Movies to Database';
                btn.disabled = false;
            }, 3000);
        });
        
        panel.querySelector('#sync-queue-btn')?.addEventListener('click', async () => {
            const btn = panel.querySelector('#sync-queue-btn');
            btn.textContent = '⏳ Syncing...';
            btn.disabled = true;
            
            await this.syncQueue();
            
            btn.textContent = '✅ Queue Synced';
            setTimeout(() => {
                btn.textContent = '📋 Sync Queue';
                btn.disabled = false;
            }, 2000);
        });
        
        panel.querySelector('#test-connection-btn')?.addEventListener('click', async () => {
            const btn = panel.querySelector('#test-connection-btn');
            btn.textContent = '⏳ Testing...';
            
            const connected = await this.testConnection();
            btn.textContent = connected ? '✅ Connected' : '❌ Not Connected';
            
            setTimeout(() => {
                btn.textContent = '🔌 Test Connection';
            }, 2000);
        });
    }
};

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        window.MovieShowsDB = MovieShowsDB.init();
    }, 1000);
});

// Also initialize immediately if DOM already loaded
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(() => {
        if (!window.MovieShowsDB) {
            window.MovieShowsDB = MovieShowsDB.init();
        }
    }, 1000);
}

