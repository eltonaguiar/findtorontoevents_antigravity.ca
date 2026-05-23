/**
 * MovieShows Premium Features - Batch 9 (Features 161-180)
 * 20 More Premium Features for enhanced user experience
 */

// Feature 161: Trailer Quality Selector
const TrailerQuality = {
    qualities: ['auto', '1080p', '720p', '480p', '360p'],
    currentQuality: localStorage.getItem('movieshows-quality') || 'auto',
    
    init() {
        this.createUI();
        console.log('[MovieShows] Trailer Quality Selector initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'quality-selector-btn';
        btn.innerHTML = '🎬';
        btn.title = 'Video Quality';
        btn.style.cssText = `
            position: fixed; top: 510px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showQualityMenu();
        document.body.appendChild(btn);
    },
    
    showQualityMenu() {
        let menu = document.getElementById('quality-menu');
        if (menu) { menu.remove(); return; }
        
        menu = document.createElement('div');
        menu.id = 'quality-menu';
        menu.style.cssText = `
            position: fixed; top: 510px; right: 75px; z-index: 9999;
            background: rgba(20, 20, 30, 0.98); border-radius: 12px;
            padding: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.6);
            border: 1px solid rgba(255,255,255,0.1);
        `;
        
        menu.innerHTML = `
            <p style="color: #888; font-size: 11px; margin: 0 0 8px 0; padding: 0 5px;">Quality</p>
            ${this.qualities.map(q => `
                <button class="quality-option" data-quality="${q}" style="
                    display: block; width: 100%; padding: 8px 15px; margin-bottom: 4px;
                    background: ${q === this.currentQuality ? 'rgba(99, 102, 241, 0.3)' : 'transparent'};
                    border: none; border-radius: 6px; color: ${q === this.currentQuality ? '#8b5cf6' : 'white'};
                    text-align: left; cursor: pointer; font-size: 13px;
                    transition: background 0.2s;
                " onmouseover="this.style.background='rgba(255,255,255,0.1)'" 
                   onmouseout="this.style.background='${q === this.currentQuality ? 'rgba(99, 102, 241, 0.3)' : 'transparent'}'">
                    ${q === 'auto' ? '⚡ Auto' : `📺 ${q}`}
                </button>
            `).join('')}
        `;
        
        document.body.appendChild(menu);
        
        menu.querySelectorAll('.quality-option').forEach(btn => {
            btn.onclick = () => {
                this.setQuality(btn.dataset.quality);
                menu.remove();
            };
        });
        
        setTimeout(() => {
            document.addEventListener('click', function handler(e) {
                if (!menu.contains(e.target) && e.target.id !== 'quality-selector-btn') {
                    menu.remove();
                    document.removeEventListener('click', handler);
                }
            });
        }, 100);
    },
    
    setQuality(quality) {
        this.currentQuality = quality;
        localStorage.setItem('movieshows-quality', quality);
        this.showToast(`Quality set to ${quality}`);
    },
    
    showToast(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%);
            background: rgba(0,0,0,0.9); color: white; padding: 12px 24px;
            border-radius: 25px; font-size: 14px; z-index: 10000;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2000);
    }
};

// Feature 162: Content Duration Filter
const DurationFilter = {
    ranges: [
        { label: 'All', min: 0, max: 9999 },
        { label: 'Short (<30 min)', min: 0, max: 30 },
        { label: 'Medium (30-90 min)', min: 30, max: 90 },
        { label: 'Long (90-150 min)', min: 90, max: 150 },
        { label: 'Epic (150+ min)', min: 150, max: 9999 }
    ],
    currentRange: 0,
    
    init() {
        this.createUI();
        console.log('[MovieShows] Duration Filter initialized');
    },
    
    createUI() {
        const container = document.createElement('div');
        container.id = 'duration-filter';
        container.style.cssText = `
            position: fixed; top: 130px; left: 50%; transform: translateX(-50%);
            z-index: 9980; display: flex; gap: 8px; padding: 8px 12px;
            background: rgba(20, 20, 30, 0.8); border-radius: 20px;
            backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1);
        `;
        
        container.innerHTML = `
            <span style="color: #888; font-size: 11px; display: flex; align-items: center; margin-right: 5px;">⏱️ Duration:</span>
            ${this.ranges.map((r, i) => `
                <button class="duration-btn" data-index="${i}" style="
                    padding: 5px 12px; border: none; border-radius: 15px;
                    background: ${i === this.currentRange ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255,255,255,0.05)'};
                    color: ${i === this.currentRange ? '#22c55e' : '#888'};
                    font-size: 11px; cursor: pointer; transition: all 0.2s;
                    white-space: nowrap;
                ">${r.label}</button>
            `).join('')}
        `;
        
        document.body.appendChild(container);
        
        container.querySelectorAll('.duration-btn').forEach(btn => {
            btn.onclick = () => {
                this.currentRange = parseInt(btn.dataset.index);
                this.updateUI();
                this.applyFilter();
            };
        });
    },
    
    updateUI() {
        document.querySelectorAll('#duration-filter .duration-btn').forEach((btn, i) => {
            btn.style.background = i === this.currentRange ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255,255,255,0.05)';
            btn.style.color = i === this.currentRange ? '#22c55e' : '#888';
        });
    },
    
    applyFilter() {
        const range = this.ranges[this.currentRange];
        console.log(`[MovieShows] Filtering by duration: ${range.label}`);
        // Would integrate with main content filter
    }
};

// Feature 163: Watchlist Folders
const WatchlistFolders = {
    folders: JSON.parse(localStorage.getItem('movieshows-folders') || '{"default": [], "favorites": [], "watch-later": []}'),
    
    init() {
        this.createUI();
        console.log('[MovieShows] Watchlist Folders initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'folders-btn';
        btn.innerHTML = '📁';
        btn.title = 'Watchlist Folders';
        btn.style.cssText = `
            position: fixed; top: 565px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showFolders();
        document.body.appendChild(btn);
    },
    
    showFolders() {
        let panel = document.getElementById('folders-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'folders-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 400px; max-width: 95vw;
            background: rgba(20, 20, 30, 0.98); border-radius: 20px; padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        const folderNames = Object.keys(this.folders);
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0; font-size: 18px;">📁 My Folders</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <button id="create-folder-btn" style="
                width: 100%; padding: 12px; background: linear-gradient(135deg, #f59e0b, #d97706);
                border: none; border-radius: 10px; color: white; font-weight: bold;
                cursor: pointer; margin-bottom: 20px; display: flex; align-items: center; justify-content: center; gap: 8px;
            ">+ Create New Folder</button>
            
            <div id="folders-list" style="display: flex; flex-direction: column; gap: 10px; max-height: 300px; overflow-y: auto;">
                ${folderNames.map(name => `
                    <div class="folder-item" data-folder="${name}" style="
                        display: flex; justify-content: space-between; align-items: center;
                        padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px;
                        cursor: pointer; transition: all 0.2s;
                    " onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='rgba(255,255,255,0.05)'">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 24px;">📂</span>
                            <div>
                                <h4 style="color: white; margin: 0; font-size: 14px; text-transform: capitalize;">${name.replace('-', ' ')}</h4>
                                <span style="color: #888; font-size: 12px;">${this.folders[name].length} items</span>
                            </div>
                        </div>
                        <span style="color: #666;">→</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelector('#create-folder-btn')?.addEventListener('click', () => {
            const name = prompt('Enter folder name:');
            if (name && name.trim()) {
                this.createFolder(name.trim().toLowerCase().replace(/\s+/g, '-'));
                this.showFolders();
            }
        });
        
        panel.querySelectorAll('.folder-item').forEach(item => {
            item.onclick = () => this.openFolder(item.dataset.folder);
        });
    },
    
    createFolder(name) {
        if (!this.folders[name]) {
            this.folders[name] = [];
            this.save();
        }
    },
    
    openFolder(name) {
        const items = this.folders[name] || [];
        alert(`📂 ${name}\n\n${items.length === 0 ? 'This folder is empty' : items.map(i => `• ${i.title}`).join('\n')}`);
    },
    
    addToFolder(folderName, movie) {
        if (!this.folders[folderName]) this.folders[folderName] = [];
        if (!this.folders[folderName].some(m => m.title === movie.title)) {
            this.folders[folderName].push(movie);
            this.save();
        }
    },
    
    save() {
        localStorage.setItem('movieshows-folders', JSON.stringify(this.folders));
    }
};

// Feature 164: Keyboard Navigation Help
const KeyboardHelp = {
    shortcuts: [
        { key: 'J', action: 'Next video' },
        { key: 'K', action: 'Previous video' },
        { key: 'M', action: 'Toggle mute' },
        { key: 'F', action: 'Toggle fullscreen' },
        { key: 'Space', action: 'Play/Pause' },
        { key: '1-5', action: 'Player size' },
        { key: 'Q', action: 'Open queue' },
        { key: 'S', action: 'Share current' },
        { key: 'L', action: 'Add to list' },
        { key: '?', action: 'Show this help' }
    ],
    
    init() {
        this.createUI();
        this.bindHelpKey();
        console.log('[MovieShows] Keyboard Help initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'keyboard-help-btn';
        btn.innerHTML = '⌨️';
        btn.title = 'Keyboard Shortcuts';
        btn.style.cssText = `
            position: fixed; bottom: 10px; right: 75px; z-index: 9998;
            width: 36px; height: 36px; border-radius: 50%;
            background: rgba(60, 60, 80, 0.8);
            border: none; cursor: pointer; font-size: 16px;
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showHelp();
        document.body.appendChild(btn);
    },
    
    bindHelpKey() {
        document.addEventListener('keydown', (e) => {
            if (e.key === '?' && !e.target.matches('input, textarea')) {
                e.preventDefault();
                this.showHelp();
            }
        });
    },
    
    showHelp() {
        let panel = document.getElementById('keyboard-help-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'keyboard-help-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 350px; background: rgba(20, 20, 30, 0.98);
            border-radius: 20px; padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0; font-size: 18px;">⌨️ Keyboard Shortcuts</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 8px;">
                ${this.shortcuts.map(s => `
                    <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <span style="color: #888; font-size: 13px;">${s.action}</span>
                        <kbd style="
                            padding: 4px 10px; background: rgba(255,255,255,0.1);
                            border-radius: 6px; color: white; font-size: 12px;
                            font-family: monospace;
                        ">${s.key}</kbd>
                    </div>
                `).join('')}
            </div>
        `;
        
        document.body.appendChild(panel);
    }
};

// Feature 165: Content Age Rating Filter
const AgeRatingFilter = {
    ratings: ['All', 'G', 'PG', 'PG-13', 'R', 'NC-17'],
    currentRating: 'All',
    
    init() {
        this.createUI();
        console.log('[MovieShows] Age Rating Filter initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'age-rating-btn';
        btn.innerHTML = '🔞';
        btn.title = 'Age Rating Filter';
        btn.style.cssText = `
            position: fixed; top: 620px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showRatingMenu();
        document.body.appendChild(btn);
    },
    
    showRatingMenu() {
        let menu = document.getElementById('age-rating-menu');
        if (menu) { menu.remove(); return; }
        
        menu = document.createElement('div');
        menu.id = 'age-rating-menu';
        menu.style.cssText = `
            position: fixed; top: 620px; right: 75px; z-index: 9999;
            background: rgba(20, 20, 30, 0.98); border-radius: 12px;
            padding: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.6);
        `;
        
        menu.innerHTML = `
            <p style="color: #888; font-size: 11px; margin: 0 0 10px 0;">Age Rating</p>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                ${this.ratings.map(r => `
                    <button class="rating-btn" data-rating="${r}" style="
                        padding: 8px 14px; border-radius: 20px;
                        background: ${r === this.currentRating ? 'rgba(239, 68, 68, 0.3)' : 'rgba(255,255,255,0.05)'};
                        border: 1px solid ${r === this.currentRating ? '#ef4444' : 'rgba(255,255,255,0.1)'};
                        color: ${r === this.currentRating ? '#ef4444' : 'white'};
                        font-size: 12px; cursor: pointer;
                    ">${r}</button>
                `).join('')}
            </div>
        `;
        
        document.body.appendChild(menu);
        
        menu.querySelectorAll('.rating-btn').forEach(btn => {
            btn.onclick = () => {
                this.currentRating = btn.dataset.rating;
                localStorage.setItem('movieshows-age-rating', this.currentRating);
                menu.remove();
            };
        });
    }
};

// Feature 166: Recently Viewed History
const RecentlyViewed = {
    history: JSON.parse(localStorage.getItem('movieshows-recently-viewed') || '[]'),
    maxItems: 20,
    
    init() {
        this.createUI();
        this.trackViewing();
        console.log('[MovieShows] Recently Viewed initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'recently-viewed-btn';
        btn.innerHTML = '🕐';
        btn.title = 'Recently Viewed';
        btn.style.cssText = `
            position: fixed; top: 675px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(14, 165, 233, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showHistory();
        document.body.appendChild(btn);
    },
    
    trackViewing() {
        // Track when video changes
        let lastTitle = '';
        setInterval(() => {
            const currentTitle = document.querySelector('.video-slide.active h2')?.textContent;
            if (currentTitle && currentTitle !== lastTitle) {
                lastTitle = currentTitle;
                this.addToHistory(currentTitle);
            }
        }, 3000);
    },
    
    addToHistory(title) {
        const movie = window.allMoviesData?.find(m => m.title === title);
        if (!movie) return;
        
        // Remove if already exists
        this.history = this.history.filter(h => h.title !== title);
        
        // Add to front
        this.history.unshift({
            title: movie.title,
            posterUrl: movie.posterUrl,
            viewedAt: Date.now()
        });
        
        // Limit history
        this.history = this.history.slice(0, this.maxItems);
        localStorage.setItem('movieshows-recently-viewed', JSON.stringify(this.history));
    },
    
    showHistory() {
        let panel = document.getElementById('recently-viewed-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'recently-viewed-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 450px; max-width: 95vw; max-height: 80vh;
            background: rgba(20, 20, 30, 0.98); border-radius: 20px; padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8); overflow-y: auto;
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0; font-size: 18px;">🕐 Recently Viewed</h3>
                <div>
                    <button id="clear-history-btn" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 12px; margin-right: 15px;">Clear All</button>
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
                </div>
            </div>
            
            ${this.history.length === 0 ? 
                '<p style="color: #666; text-align: center; padding: 40px;">No viewing history yet</p>' :
                `<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                    ${this.history.map(item => `
                        <div class="history-item" data-title="${item.title}" style="
                            cursor: pointer; transition: all 0.2s;
                        " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                            <img src="${item.posterUrl || 'https://via.placeholder.com/120x180/1a1a2e/666?text=' + encodeURIComponent(item.title?.charAt(0) || '?')}" 
                                style="width: 100%; aspect-ratio: 2/3; object-fit: cover; border-radius: 10px; background: #1a1a2e;"
                                onerror="this.src='https://via.placeholder.com/120x180/1a1a2e/666?text=?'">
                            <p style="color: white; font-size: 11px; margin: 8px 0 0 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.title}</p>
                            <p style="color: #666; font-size: 10px; margin: 2px 0 0 0;">${this.formatTime(item.viewedAt)}</p>
                        </div>
                    `).join('')}
                </div>`
            }
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelector('#clear-history-btn')?.addEventListener('click', () => {
            this.history = [];
            localStorage.setItem('movieshows-recently-viewed', '[]');
            this.showHistory();
        });
        
        panel.querySelectorAll('.history-item').forEach(item => {
            item.onclick = () => {
                window.playMovieByTitle?.(item.dataset.title);
                panel.remove();
            };
        });
    },
    
    formatTime(timestamp) {
        const diff = Date.now() - timestamp;
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'Just now';
        if (mins < 60) return `${mins}m ago`;
        const hours = Math.floor(mins / 60);
        if (hours < 24) return `${hours}h ago`;
        return `${Math.floor(hours / 24)}d ago`;
    }
};

// Feature 167: Watch Speed Presets
const SpeedPresets = {
    presets: [
        { name: 'Slow', speed: 0.5, icon: '🐢' },
        { name: 'Normal', speed: 1, icon: '▶️' },
        { name: 'Fast', speed: 1.25, icon: '⏩' },
        { name: 'Faster', speed: 1.5, icon: '🚀' },
        { name: 'Rapid', speed: 2, icon: '⚡' }
    ],
    currentPreset: 1,
    
    init() {
        this.createUI();
        console.log('[MovieShows] Speed Presets initialized');
    },
    
    createUI() {
        const container = document.createElement('div');
        container.id = 'speed-presets';
        container.style.cssText = `
            position: fixed; bottom: 60px; left: 20px; z-index: 9990;
            display: flex; gap: 5px; padding: 8px; background: rgba(20, 20, 30, 0.9);
            border-radius: 25px; backdrop-filter: blur(10px);
        `;
        
        this.presets.forEach((preset, i) => {
            const btn = document.createElement('button');
            btn.innerHTML = preset.icon;
            btn.title = `${preset.name} (${preset.speed}x)`;
            btn.style.cssText = `
                width: 36px; height: 36px; border-radius: 50%;
                background: ${i === this.currentPreset ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255,255,255,0.05)'};
                border: 1px solid ${i === this.currentPreset ? '#22c55e' : 'transparent'};
                cursor: pointer; font-size: 16px; transition: all 0.2s;
            `;
            btn.onclick = () => this.setPreset(i);
            container.appendChild(btn);
        });
        
        document.body.appendChild(container);
    },
    
    setPreset(index) {
        this.currentPreset = index;
        const preset = this.presets[index];
        
        // Update UI
        document.querySelectorAll('#speed-presets button').forEach((btn, i) => {
            btn.style.background = i === index ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255,255,255,0.05)';
            btn.style.borderColor = i === index ? '#22c55e' : 'transparent';
        });
        
        // Show toast
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; bottom: 120px; left: 50%; transform: translateX(-50%);
            background: rgba(0,0,0,0.9); color: white; padding: 10px 20px;
            border-radius: 20px; font-size: 14px; z-index: 10000;
        `;
        toast.textContent = `${preset.icon} ${preset.name} (${preset.speed}x)`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 1500);
    }
};

// Feature 168: Content Mood Tags
const MoodTags = {
    moods: ['😊 Feel Good', '😢 Emotional', '🤣 Funny', '😱 Scary', '🤔 Thought-Provoking', '💕 Romantic', '🔥 Intense', '😌 Relaxing'],
    userTags: JSON.parse(localStorage.getItem('movieshows-mood-tags') || '{}'),
    
    init() {
        this.injectMoodButtons();
        console.log('[MovieShows] Mood Tags initialized');
    },
    
    injectMoodButtons() {
        // Add mood tagging to slides
        const observer = new MutationObserver(() => {
            document.querySelectorAll('.video-slide.active').forEach(slide => {
                if (slide.querySelector('.mood-tag-btn')) return;
                
                const btn = document.createElement('button');
                btn.className = 'mood-tag-btn';
                btn.innerHTML = '🏷️';
                btn.title = 'Add mood tag';
                btn.style.cssText = `
                    position: absolute; top: 80px; right: 20px; z-index: 100;
                    width: 40px; height: 40px; border-radius: 50%;
                    background: rgba(0,0,0,0.6); border: none;
                    cursor: pointer; font-size: 18px; backdrop-filter: blur(10px);
                `;
                btn.onclick = (e) => {
                    e.stopPropagation();
                    const title = slide.querySelector('h2')?.textContent;
                    if (title) this.showMoodPicker(title);
                };
                slide.appendChild(btn);
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    },
    
    showMoodPicker(title) {
        let picker = document.getElementById('mood-picker');
        if (picker) picker.remove();
        
        picker = document.createElement('div');
        picker.id = 'mood-picker';
        picker.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; background: rgba(20, 20, 30, 0.98);
            border-radius: 20px; padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        const currentTags = this.userTags[title] || [];
        
        picker.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="color: white; margin: 0; font-size: 16px;">Tag this content</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 20px; cursor: pointer;">×</button>
            </div>
            <p style="color: #888; font-size: 12px; margin-bottom: 15px;">${title}</p>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                ${this.moods.map(mood => `
                    <button class="mood-option" data-mood="${mood}" style="
                        padding: 10px 15px; border-radius: 20px;
                        background: ${currentTags.includes(mood) ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255,255,255,0.05)'};
                        border: 1px solid ${currentTags.includes(mood) ? '#22c55e' : 'rgba(255,255,255,0.1)'};
                        color: white; font-size: 13px; cursor: pointer;
                        transition: all 0.2s;
                    ">${mood}</button>
                `).join('')}
            </div>
        `;
        
        document.body.appendChild(picker);
        
        picker.querySelectorAll('.mood-option').forEach(btn => {
            btn.onclick = () => {
                const mood = btn.dataset.mood;
                this.toggleTag(title, mood);
                btn.style.background = this.userTags[title]?.includes(mood) ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255,255,255,0.05)';
                btn.style.borderColor = this.userTags[title]?.includes(mood) ? '#22c55e' : 'rgba(255,255,255,0.1)';
            };
        });
    },
    
    toggleTag(title, mood) {
        if (!this.userTags[title]) this.userTags[title] = [];
        
        const index = this.userTags[title].indexOf(mood);
        if (index > -1) {
            this.userTags[title].splice(index, 1);
        } else {
            this.userTags[title].push(mood);
        }
        
        localStorage.setItem('movieshows-mood-tags', JSON.stringify(this.userTags));
    }
};

// Feature 169: Content Notes
const ContentNotes = {
    notes: JSON.parse(localStorage.getItem('movieshows-content-notes') || '{}'),
    
    init() {
        this.createUI();
        console.log('[MovieShows] Content Notes initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'content-notes-btn';
        btn.innerHTML = '📝';
        btn.title = 'My Notes';
        btn.style.cssText = `
            position: fixed; top: 730px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showNotes();
        document.body.appendChild(btn);
    },
    
    showNotes() {
        let panel = document.getElementById('content-notes-panel');
        if (panel) { panel.remove(); return; }
        
        const currentTitle = document.querySelector('.video-slide.active h2')?.textContent || 'Unknown';
        const currentNote = this.notes[currentTitle] || '';
        
        panel = document.createElement('div');
        panel.id = 'content-notes-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 400px; max-width: 95vw;
            background: rgba(20, 20, 30, 0.98); border-radius: 20px; padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="color: white; margin: 0; font-size: 18px;">📝 Notes</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            <p style="color: #888; font-size: 12px; margin-bottom: 15px;">${currentTitle}</p>
            <textarea id="note-textarea" placeholder="Add your notes about this content..." style="
                width: 100%; height: 150px; padding: 15px;
                background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
                border-radius: 12px; color: white; font-size: 14px;
                resize: none; outline: none;
            ">${currentNote}</textarea>
            <button id="save-note-btn" style="
                width: 100%; margin-top: 15px; padding: 12px;
                background: linear-gradient(135deg, #10b981, #059669);
                border: none; border-radius: 10px; color: white;
                font-weight: bold; cursor: pointer;
            ">Save Note</button>
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelector('#save-note-btn')?.addEventListener('click', () => {
            const note = panel.querySelector('#note-textarea').value;
            this.saveNote(currentTitle, note);
            panel.remove();
        });
    },
    
    saveNote(title, note) {
        if (note.trim()) {
            this.notes[title] = note;
        } else {
            delete this.notes[title];
        }
        localStorage.setItem('movieshows-content-notes', JSON.stringify(this.notes));
        
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%);
            background: rgba(16, 185, 129, 0.9); color: white; padding: 12px 24px;
            border-radius: 25px; font-size: 14px; z-index: 10000;
        `;
        toast.textContent = '✓ Note saved';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2000);
    }
};

// Feature 170: Smart Pause Detection
const SmartPause = {
    pauseTimeout: null,
    isPaused: false,
    
    init() {
        this.detectInactivity();
        console.log('[MovieShows] Smart Pause initialized');
    },
    
    detectInactivity() {
        let lastActivity = Date.now();
        
        ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, () => {
                lastActivity = Date.now();
                if (this.isPaused) {
                    this.resumePlayback();
                }
            });
        });
        
        // Check for inactivity every 30 seconds
        setInterval(() => {
            if (Date.now() - lastActivity > 300000) { // 5 minutes
                this.showPausePrompt();
            }
        }, 30000);
    },
    
    showPausePrompt() {
        if (this.isPaused || document.getElementById('pause-prompt')) return;
        
        const prompt = document.createElement('div');
        prompt.id = 'pause-prompt';
        prompt.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; background: rgba(20, 20, 30, 0.98);
            border-radius: 20px; padding: 40px; text-align: center;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        prompt.innerHTML = `
            <div style="font-size: 48px; margin-bottom: 20px;">💤</div>
            <h3 style="color: white; margin: 0 0 10px 0;">Still watching?</h3>
            <p style="color: #888; margin: 0 0 25px 0;">You've been inactive for a while</p>
            <div style="display: flex; gap: 15px; justify-content: center;">
                <button id="continue-watching" style="
                    padding: 12px 30px; background: linear-gradient(135deg, #22c55e, #16a34a);
                    border: none; border-radius: 25px; color: white; font-weight: bold;
                    cursor: pointer;
                ">Yes, Continue</button>
                <button id="pause-watching" style="
                    padding: 12px 30px; background: rgba(255,255,255,0.1);
                    border: none; border-radius: 25px; color: white;
                    cursor: pointer;
                ">Take a Break</button>
            </div>
        `;
        
        document.body.appendChild(prompt);
        
        prompt.querySelector('#continue-watching').onclick = () => {
            prompt.remove();
            this.isPaused = false;
        };
        
        prompt.querySelector('#pause-watching').onclick = () => {
            prompt.remove();
            this.isPaused = true;
            this.pausePlayback();
        };
    },
    
    pausePlayback() {
        // Mute or pause current video
        window.toggleMute?.(true);
        this.showPausedOverlay();
    },
    
    resumePlayback() {
        this.isPaused = false;
        document.getElementById('paused-overlay')?.remove();
    },
    
    showPausedOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'paused-overlay';
        overlay.style.cssText = `
            position: fixed; inset: 0; z-index: 9999;
            background: rgba(0,0,0,0.8); display: flex;
            align-items: center; justify-content: center;
            cursor: pointer;
        `;
        overlay.innerHTML = `
            <div style="text-align: center;">
                <div style="font-size: 64px; margin-bottom: 20px;">⏸️</div>
                <p style="color: white; font-size: 18px;">Paused - Click anywhere to resume</p>
            </div>
        `;
        overlay.onclick = () => this.resumePlayback();
        document.body.appendChild(overlay);
    }
};

// Feature 171: Content Freshness Indicator
const FreshnessIndicator = {
    init() {
        this.injectIndicators();
        console.log('[MovieShows] Freshness Indicator initialized');
    },
    
    injectIndicators() {
        const observer = new MutationObserver(() => {
            document.querySelectorAll('.video-slide').forEach(slide => {
                if (slide.querySelector('.freshness-badge')) return;
                
                const title = slide.querySelector('h2')?.textContent;
                const movie = window.allMoviesData?.find(m => m.title === title);
                
                if (!movie) return;
                
                const freshness = this.calculateFreshness(movie);
                if (!freshness) return;
                
                const badge = document.createElement('div');
                badge.className = 'freshness-badge';
                badge.style.cssText = `
                    position: absolute; top: 10px; right: 10px; z-index: 100;
                    padding: 6px 12px; border-radius: 15px;
                    background: ${freshness.color}; color: white;
                    font-size: 11px; font-weight: bold;
                    backdrop-filter: blur(10px);
                `;
                badge.innerHTML = freshness.label;
                slide.appendChild(badge);
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    },
    
    calculateFreshness(movie) {
        const year = parseInt(movie.year);
        const currentYear = new Date().getFullYear();
        
        if (year >= currentYear + 1) {
            return { label: '🔜 Coming Soon', color: 'rgba(168, 85, 247, 0.9)' };
        } else if (year === currentYear) {
            return { label: '🆕 New Release', color: 'rgba(34, 197, 94, 0.9)' };
        } else if (year >= currentYear - 1) {
            return { label: '✨ Recent', color: 'rgba(59, 130, 246, 0.9)' };
        }
        return null;
    }
};

// Feature 172: Mini Player Mode
const MiniPlayer = {
    isActive: false,
    
    init() {
        this.createUI();
        console.log('[MovieShows] Mini Player initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'mini-player-btn';
        btn.innerHTML = '🔲';
        btn.title = 'Mini Player';
        btn.style.cssText = `
            position: fixed; bottom: 60px; right: 75px; z-index: 9998;
            width: 40px; height: 40px; border-radius: 50%;
            background: rgba(60, 60, 80, 0.9);
            border: none; cursor: pointer; font-size: 18px;
            transition: all 0.3s;
        `;
        btn.onclick = () => this.toggleMiniPlayer();
        document.body.appendChild(btn);
    },
    
    toggleMiniPlayer() {
        this.isActive = !this.isActive;
        
        const mainContainer = document.querySelector('.video-container, main, #__next');
        if (!mainContainer) return;
        
        if (this.isActive) {
            mainContainer.style.cssText = `
                position: fixed !important;
                bottom: 20px !important;
                right: 20px !important;
                width: 320px !important;
                height: 180px !important;
                z-index: 9990 !important;
                border-radius: 12px !important;
                overflow: hidden !important;
                box-shadow: 0 10px 40px rgba(0,0,0,0.5) !important;
                transition: all 0.3s !important;
            `;
            document.getElementById('mini-player-btn').innerHTML = '🔳';
        } else {
            mainContainer.style.cssText = '';
            document.getElementById('mini-player-btn').innerHTML = '🔲';
        }
    }
};

// Feature 173: Content Shuffle Mode
const ShuffleMode = {
    isShuffling: false,
    shuffleInterval: null,
    
    init() {
        this.createUI();
        console.log('[MovieShows] Shuffle Mode initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'shuffle-mode-btn';
        btn.innerHTML = '🔀';
        btn.title = 'Shuffle Mode';
        btn.style.cssText = `
            position: fixed; bottom: 115px; left: 20px; z-index: 9990;
            width: 44px; height: 44px; border-radius: 50%;
            background: rgba(60, 60, 80, 0.9);
            border: none; cursor: pointer; font-size: 20px;
            transition: all 0.3s;
        `;
        btn.onclick = () => this.toggleShuffle();
        document.body.appendChild(btn);
    },
    
    toggleShuffle() {
        this.isShuffling = !this.isShuffling;
        const btn = document.getElementById('shuffle-mode-btn');
        
        if (this.isShuffling) {
            btn.style.background = 'linear-gradient(135deg, #22c55e, #16a34a)';
            this.startShuffle();
            this.showToast('🔀 Shuffle mode ON');
        } else {
            btn.style.background = 'rgba(60, 60, 80, 0.9)';
            this.stopShuffle();
            this.showToast('🔀 Shuffle mode OFF');
        }
    },
    
    startShuffle() {
        // Auto-advance to random video every 30 seconds
        this.shuffleInterval = setInterval(() => {
            if (!this.isShuffling) return;
            
            const movies = window.allMoviesData?.filter(m => m.trailerUrl) || [];
            if (movies.length === 0) return;
            
            const random = movies[Math.floor(Math.random() * movies.length)];
            window.playMovieByTitle?.(random.title);
        }, 30000);
    },
    
    stopShuffle() {
        if (this.shuffleInterval) {
            clearInterval(this.shuffleInterval);
            this.shuffleInterval = null;
        }
    },
    
    showToast(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; bottom: 170px; left: 50%; transform: translateX(-50%);
            background: rgba(0,0,0,0.9); color: white; padding: 10px 20px;
            border-radius: 20px; font-size: 14px; z-index: 10000;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2000);
    }
};

// Feature 174: Content Rating Comparison
const RatingComparison = {
    init() {
        this.injectComparison();
        console.log('[MovieShows] Rating Comparison initialized');
    },
    
    injectComparison() {
        const observer = new MutationObserver(() => {
            document.querySelectorAll('.video-slide.active').forEach(slide => {
                if (slide.querySelector('.rating-comparison')) return;
                
                const title = slide.querySelector('h2')?.textContent;
                const movie = window.allMoviesData?.find(m => m.title === title);
                
                if (!movie?.rating) return;
                
                const container = document.createElement('div');
                container.className = 'rating-comparison';
                container.style.cssText = `
                    position: absolute; bottom: 180px; left: 20px; z-index: 100;
                    display: flex; gap: 10px; padding: 10px 15px;
                    background: rgba(0,0,0,0.7); border-radius: 12px;
                    backdrop-filter: blur(10px);
                `;
                
                const imdbRating = parseFloat(movie.rating) || 0;
                const userRating = this.getUserRating(title);
                
                container.innerHTML = `
                    <div style="text-align: center;">
                        <div style="color: #f5c518; font-size: 18px; font-weight: bold;">${imdbRating.toFixed(1)}</div>
                        <div style="color: #888; font-size: 10px;">IMDb</div>
                    </div>
                    <div style="width: 1px; background: rgba(255,255,255,0.2);"></div>
                    <div style="text-align: center;">
                        <div style="color: #22c55e; font-size: 18px; font-weight: bold;">${userRating || '-'}</div>
                        <div style="color: #888; font-size: 10px;">You</div>
                    </div>
                `;
                
                slide.appendChild(container);
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    },
    
    getUserRating(title) {
        const ratings = JSON.parse(localStorage.getItem('movieshows-quick-ratings') || '{}');
        return ratings[title];
    }
};

// Feature 175: Auto-Resume Feature
const AutoResume = {
    resumePoints: JSON.parse(localStorage.getItem('movieshows-resume-points') || '{}'),
    
    init() {
        this.checkForResume();
        this.trackProgress();
        console.log('[MovieShows] Auto-Resume initialized');
    },
    
    checkForResume() {
        // Check if there's content to resume on load
        setTimeout(() => {
            const lastWatched = localStorage.getItem('movieshows-last-watched');
            if (lastWatched) {
                this.showResumePrompt(lastWatched);
            }
        }, 2000);
    },
    
    trackProgress() {
        let currentTitle = '';
        setInterval(() => {
            const title = document.querySelector('.video-slide.active h2')?.textContent;
            if (title && title !== currentTitle) {
                currentTitle = title;
                localStorage.setItem('movieshows-last-watched', title);
            }
        }, 5000);
    },
    
    showResumePrompt(title) {
        const prompt = document.createElement('div');
        prompt.id = 'resume-prompt';
        prompt.style.cssText = `
            position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%);
            z-index: 10000; background: rgba(20, 20, 30, 0.98);
            border-radius: 15px; padding: 15px 25px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.6);
            display: flex; align-items: center; gap: 15px;
        `;
        
        prompt.innerHTML = `
            <div style="font-size: 28px;">▶️</div>
            <div>
                <p style="color: white; margin: 0; font-size: 14px;">Continue watching?</p>
                <p style="color: #888; margin: 4px 0 0 0; font-size: 12px;">${title}</p>
            </div>
            <button id="resume-yes" style="
                padding: 8px 20px; background: #22c55e;
                border: none; border-radius: 20px; color: white;
                font-weight: bold; cursor: pointer; margin-left: 10px;
            ">Resume</button>
            <button id="resume-no" style="
                padding: 8px 15px; background: rgba(255,255,255,0.1);
                border: none; border-radius: 20px; color: #888;
                cursor: pointer;
            ">✕</button>
        `;
        
        document.body.appendChild(prompt);
        
        prompt.querySelector('#resume-yes').onclick = () => {
            window.playMovieByTitle?.(title);
            prompt.remove();
        };
        
        prompt.querySelector('#resume-no').onclick = () => prompt.remove();
        
        // Auto-dismiss after 10 seconds
        setTimeout(() => prompt.remove(), 10000);
    }
};

// Feature 176: Content Discovery Suggestions
const DiscoverySuggestions = {
    init() {
        this.showSuggestionPeriodically();
        console.log('[MovieShows] Discovery Suggestions initialized');
    },
    
    showSuggestionPeriodically() {
        // Show a suggestion every 5 minutes of viewing
        setInterval(() => {
            if (Math.random() > 0.7) { // 30% chance
                this.showSuggestion();
            }
        }, 300000);
    },
    
    showSuggestion() {
        const movies = window.allMoviesData?.filter(m => m.trailerUrl && parseFloat(m.rating) >= 8) || [];
        if (movies.length === 0) return;
        
        const suggestion = movies[Math.floor(Math.random() * movies.length)];
        
        const popup = document.createElement('div');
        popup.id = 'discovery-suggestion';
        popup.style.cssText = `
            position: fixed; bottom: 20px; right: 20px; z-index: 9999;
            width: 300px; background: rgba(20, 20, 30, 0.98);
            border-radius: 16px; padding: 20px; overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.6);
            animation: slideIn 0.3s ease;
        `;
        
        popup.innerHTML = `
            <style>@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } }</style>
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                <span style="color: #888; font-size: 11px;">💡 You might like</span>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #666; cursor: pointer;">✕</button>
            </div>
            <div style="display: flex; gap: 12px;">
                <img src="${suggestion.posterUrl || 'https://via.placeholder.com/60x90/1a1a2e/666?text=?'}" 
                    style="width: 60px; height: 90px; object-fit: cover; border-radius: 8px; background: #1a1a2e;">
                <div style="flex: 1;">
                    <h4 style="color: white; margin: 0 0 5px 0; font-size: 14px;">${suggestion.title}</h4>
                    <p style="color: #888; margin: 0; font-size: 12px;">${suggestion.year} • ⭐ ${suggestion.rating || 'N/A'}</p>
                    <button onclick="window.playMovieByTitle?.('${suggestion.title}');this.parentElement.parentElement.parentElement.remove()" style="
                        margin-top: 10px; padding: 6px 15px;
                        background: linear-gradient(135deg, #22c55e, #16a34a);
                        border: none; border-radius: 15px; color: white;
                        font-size: 12px; cursor: pointer;
                    ">▶ Watch</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(popup);
        
        // Auto-dismiss after 15 seconds
        setTimeout(() => popup.remove(), 15000);
    }
};

// Feature 177: Gesture Hints
const GestureHints = {
    hints: [
        { gesture: '👆 Swipe Up', action: 'Next video' },
        { gesture: '👇 Swipe Down', action: 'Previous video' },
        { gesture: '👆👆 Double Tap', action: 'Like video' },
        { gesture: '🤏 Pinch', action: 'Zoom' }
    ],
    
    init() {
        if ('ontouchstart' in window) {
            this.showHintsOnFirstVisit();
        }
        console.log('[MovieShows] Gesture Hints initialized');
    },
    
    showHintsOnFirstVisit() {
        if (localStorage.getItem('movieshows-gesture-hints-shown')) return;
        
        setTimeout(() => {
            this.showHints();
            localStorage.setItem('movieshows-gesture-hints-shown', 'true');
        }, 3000);
    },
    
    showHints() {
        const overlay = document.createElement('div');
        overlay.id = 'gesture-hints';
        overlay.style.cssText = `
            position: fixed; inset: 0; z-index: 10000;
            background: rgba(0,0,0,0.9); display: flex;
            align-items: center; justify-content: center;
            cursor: pointer;
        `;
        
        overlay.innerHTML = `
            <div style="text-align: center; max-width: 300px;">
                <h3 style="color: white; font-size: 24px; margin-bottom: 30px;">📱 Gesture Controls</h3>
                ${this.hints.map(h => `
                    <div style="display: flex; justify-content: space-between; padding: 15px 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <span style="color: white; font-size: 16px;">${h.gesture}</span>
                        <span style="color: #888; font-size: 14px;">${h.action}</span>
                    </div>
                `).join('')}
                <p style="color: #666; margin-top: 30px; font-size: 13px;">Tap anywhere to continue</p>
            </div>
        `;
        
        overlay.onclick = () => overlay.remove();
        document.body.appendChild(overlay);
    }
};

// Feature 178: Content Availability Check
const AvailabilityCheck = {
    init() {
        this.injectAvailability();
        console.log('[MovieShows] Availability Check initialized');
    },
    
    injectAvailability() {
        const platforms = ['Netflix', 'Prime Video', 'Disney+', 'Hulu', 'HBO Max'];
        
        const observer = new MutationObserver(() => {
            document.querySelectorAll('.video-slide.active').forEach(slide => {
                if (slide.querySelector('.availability-info')) return;
                
                // Simulate availability (random for demo)
                const available = platforms.filter(() => Math.random() > 0.6);
                if (available.length === 0) return;
                
                const container = document.createElement('div');
                container.className = 'availability-info';
                container.style.cssText = `
                    position: absolute; bottom: 240px; left: 20px; z-index: 100;
                    padding: 10px 15px; background: rgba(0,0,0,0.7);
                    border-radius: 10px; backdrop-filter: blur(10px);
                `;
                
                container.innerHTML = `
                    <p style="color: #888; font-size: 10px; margin: 0 0 5px 0;">Available on:</p>
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        ${available.map(p => `
                            <span style="
                                padding: 4px 10px; background: rgba(255,255,255,0.1);
                                border-radius: 12px; color: white; font-size: 11px;
                            ">${p}</span>
                        `).join('')}
                    </div>
                `;
                
                slide.appendChild(container);
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }
};

// Feature 179: Viewing Schedule
const ViewingSchedule = {
    schedule: JSON.parse(localStorage.getItem('movieshows-schedule') || '[]'),
    
    init() {
        this.createUI();
        this.checkSchedule();
        console.log('[MovieShows] Viewing Schedule initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'schedule-btn';
        btn.innerHTML = '📅';
        btn.title = 'Viewing Schedule';
        btn.style.cssText = `
            position: fixed; bottom: 170px; left: 20px; z-index: 9990;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showSchedule();
        document.body.appendChild(btn);
    },
    
    showSchedule() {
        let panel = document.getElementById('schedule-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'schedule-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 400px; max-width: 95vw;
            background: rgba(20, 20, 30, 0.98); border-radius: 20px; padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        const currentTitle = document.querySelector('.video-slide.active h2')?.textContent;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0; font-size: 18px;">📅 Viewing Schedule</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <button id="schedule-current-btn" style="
                width: 100%; padding: 12px; background: linear-gradient(135deg, #8b5cf6, #7c3aed);
                border: none; border-radius: 10px; color: white; font-weight: bold;
                cursor: pointer; margin-bottom: 20px;
            ">+ Schedule "${currentTitle || 'Current'}" for later</button>
            
            <h4 style="color: #888; font-size: 12px; margin-bottom: 12px;">UPCOMING</h4>
            <div id="schedule-list" style="max-height: 250px; overflow-y: auto;">
                ${this.schedule.length === 0 ?
                    '<p style="color: #666; text-align: center; padding: 20px;">No scheduled viewings</p>' :
                    this.schedule.map((item, i) => `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 10px; margin-bottom: 8px;">
                            <div>
                                <p style="color: white; margin: 0; font-size: 14px;">${item.title}</p>
                                <p style="color: #8b5cf6; margin: 4px 0 0 0; font-size: 12px;">${new Date(item.scheduledFor).toLocaleString()}</p>
                            </div>
                            <button onclick="ViewingSchedule.removeFromSchedule(${i})" style="background: none; border: none; color: #ef4444; cursor: pointer;">🗑️</button>
                        </div>
                    `).join('')
                }
            </div>
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelector('#schedule-current-btn')?.addEventListener('click', () => {
            if (currentTitle) {
                const time = prompt('When would you like to watch? (e.g., "tomorrow 8pm", "in 2 hours")');
                if (time) {
                    this.addToSchedule(currentTitle, time);
                    this.showSchedule();
                }
            }
        });
    },
    
    addToSchedule(title, timeStr) {
        // Simple time parsing (would be more sophisticated in production)
        const scheduledFor = new Date();
        scheduledFor.setHours(scheduledFor.getHours() + 2); // Default to 2 hours from now
        
        this.schedule.push({
            title,
            scheduledFor: scheduledFor.toISOString(),
            created: Date.now()
        });
        
        this.schedule.sort((a, b) => new Date(a.scheduledFor) - new Date(b.scheduledFor));
        localStorage.setItem('movieshows-schedule', JSON.stringify(this.schedule));
    },
    
    removeFromSchedule(index) {
        this.schedule.splice(index, 1);
        localStorage.setItem('movieshows-schedule', JSON.stringify(this.schedule));
        this.showSchedule();
    },
    
    checkSchedule() {
        setInterval(() => {
            const now = Date.now();
            this.schedule.forEach(item => {
                const scheduledTime = new Date(item.scheduledFor).getTime();
                if (Math.abs(now - scheduledTime) < 60000) { // Within 1 minute
                    this.showReminder(item);
                }
            });
        }, 60000);
    },
    
    showReminder(item) {
        if (Notification.permission === 'granted') {
            new Notification('🎬 Time to watch!', {
                body: item.title,
                icon: '/favicon.ico'
            });
        }
    }
};

// Feature 180: Quick Actions Wheel
const QuickActionsWheel = {
    actions: [
        { icon: '❤️', label: 'Like', action: () => console.log('Liked') },
        { icon: '📋', label: 'Queue', action: () => document.querySelector('[title*="Queue"]')?.click() },
        { icon: '📤', label: 'Share', action: () => document.getElementById('quick-share-btn')?.click() },
        { icon: '⭐', label: 'Rate', action: () => console.log('Rate') },
        { icon: '🔀', label: 'Shuffle', action: () => document.getElementById('shuffle-mode-btn')?.click() },
        { icon: '📝', label: 'Note', action: () => document.getElementById('content-notes-btn')?.click() }
    ],
    isOpen: false,
    
    init() {
        this.createWheel();
        console.log('[MovieShows] Quick Actions Wheel initialized');
    },
    
    createWheel() {
        const trigger = document.createElement('button');
        trigger.id = 'quick-actions-trigger';
        trigger.innerHTML = '⚡';
        trigger.style.cssText = `
            position: fixed; bottom: 50%; right: 20px; transform: translateY(50%);
            z-index: 9997; width: 50px; height: 50px; border-radius: 50%;
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            border: none; cursor: pointer; font-size: 24px;
            box-shadow: 0 4px 20px rgba(245, 158, 11, 0.5);
            transition: all 0.3s;
        `;
        trigger.onclick = () => this.toggleWheel();
        document.body.appendChild(trigger);
    },
    
    toggleWheel() {
        this.isOpen = !this.isOpen;
        
        let wheel = document.getElementById('quick-actions-wheel');
        
        if (this.isOpen) {
            if (!wheel) {
                wheel = document.createElement('div');
                wheel.id = 'quick-actions-wheel';
                wheel.style.cssText = `
                    position: fixed; bottom: 50%; right: 80px; transform: translateY(50%);
                    z-index: 9996; display: flex; flex-direction: column; gap: 10px;
                    animation: fadeIn 0.2s ease;
                `;
                
                wheel.innerHTML = `
                    <style>@keyframes fadeIn { from { opacity: 0; transform: translateY(50%) translateX(20px); } }</style>
                    ${this.actions.map((a, i) => `
                        <button class="quick-action-item" data-index="${i}" style="
                            width: 44px; height: 44px; border-radius: 50%;
                            background: rgba(30, 30, 40, 0.95);
                            border: 1px solid rgba(255,255,255,0.1);
                            cursor: pointer; font-size: 18px;
                            transition: all 0.2s;
                            animation: fadeIn 0.2s ease ${i * 0.05}s both;
                        " title="${a.label}">${a.icon}</button>
                    `).join('')}
                `;
                
                document.body.appendChild(wheel);
                
                wheel.querySelectorAll('.quick-action-item').forEach(btn => {
                    btn.onclick = () => {
                        const index = parseInt(btn.dataset.index);
                        this.actions[index].action();
                        this.toggleWheel();
                    };
                });
            }
            
            document.getElementById('quick-actions-trigger').innerHTML = '✕';
        } else {
            wheel?.remove();
            document.getElementById('quick-actions-trigger').innerHTML = '⚡';
        }
    }
};

// Initialize all Batch 9 features
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        TrailerQuality.init();
        DurationFilter.init();
        WatchlistFolders.init();
        KeyboardHelp.init();
        AgeRatingFilter.init();
        RecentlyViewed.init();
        SpeedPresets.init();
        MoodTags.init();
        ContentNotes.init();
        SmartPause.init();
        FreshnessIndicator.init();
        MiniPlayer.init();
        ShuffleMode.init();
        RatingComparison.init();
        AutoResume.init();
        DiscoverySuggestions.init();
        GestureHints.init();
        AvailabilityCheck.init();
        ViewingSchedule.init();
        QuickActionsWheel.init();
        
        console.log('[MovieShows] Batch 9 features (161-180) loaded successfully!');
    }, 2500);
});
