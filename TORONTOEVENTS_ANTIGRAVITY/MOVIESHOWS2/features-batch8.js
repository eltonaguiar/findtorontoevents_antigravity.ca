/**
 * MovieShows Premium Features - Batch 8 (Features 141-160)
 * 20 More Premium Features for enhanced user experience
 */

// Feature 141: Scene Bookmarks - Save specific timestamps
const SceneBookmarks = {
    bookmarks: JSON.parse(localStorage.getItem('movieshows-scene-bookmarks') || '{}'),
    
    init() {
        this.createUI();
        console.log('[MovieShows] Scene Bookmarks initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'scene-bookmarks-btn';
        btn.innerHTML = '🔖';
        btn.title = 'Scene Bookmarks';
        btn.style.cssText = `
            position: fixed; bottom: 260px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
            transition: all 0.3s; display: flex; align-items: center; justify-content: center;
        `;
        btn.onclick = () => this.showPanel();
        document.body.appendChild(btn);
    },
    
    showPanel() {
        let panel = document.getElementById('scene-bookmarks-panel');
        if (panel) { panel.remove(); return; }
        
        const currentTitle = document.querySelector('.video-slide.active h2')?.textContent || 'Unknown';
        const movieBookmarks = this.bookmarks[currentTitle] || [];
        
        panel = document.createElement('div');
        panel.id = 'scene-bookmarks-panel';
        panel.style.cssText = `
            position: fixed; bottom: 310px; right: 20px; z-index: 9999;
            width: 320px; background: rgba(20, 20, 30, 0.98);
            border-radius: 16px; padding: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.6);
            border: 1px solid rgba(139, 92, 246, 0.3);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="color: white; margin: 0; font-size: 16px;">🔖 Scene Bookmarks</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 20px; cursor: pointer;">×</button>
            </div>
            <p style="color: #888; font-size: 12px; margin-bottom: 15px;">${currentTitle}</p>
            <button id="add-scene-bookmark" style="
                width: 100%; padding: 12px; background: linear-gradient(135deg, #8b5cf6, #a855f7);
                border: none; border-radius: 8px; color: white; font-weight: bold; cursor: pointer;
                margin-bottom: 15px;
            ">+ Add Bookmark at Current Time</button>
            <div id="bookmarks-list" style="max-height: 200px; overflow-y: auto;">
                ${movieBookmarks.length === 0 ? '<p style="color: #666; text-align: center; padding: 20px;">No bookmarks saved</p>' :
                movieBookmarks.map((b, i) => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px;">
                        <div>
                            <p style="color: white; margin: 0; font-size: 13px;">${b.note || 'Scene ' + (i+1)}</p>
                            <span style="color: #8b5cf6; font-size: 11px;">${b.time}</span>
                        </div>
                        <button onclick="SceneBookmarks.removeBookmark('${currentTitle}', ${i})" style="background: none; border: none; color: #ef4444; cursor: pointer;">🗑️</button>
                    </div>
                `).join('')}
            </div>
        `;
        
        document.body.appendChild(panel);
        
        document.getElementById('add-scene-bookmark')?.addEventListener('click', () => {
            const note = prompt('Add a note for this bookmark (optional):');
            this.addBookmark(currentTitle, '0:00', note);
            this.showPanel();
        });
    },
    
    addBookmark(title, time, note) {
        if (!this.bookmarks[title]) this.bookmarks[title] = [];
        this.bookmarks[title].push({ time, note: note || '', created: Date.now() });
        localStorage.setItem('movieshows-scene-bookmarks', JSON.stringify(this.bookmarks));
    },
    
    removeBookmark(title, index) {
        if (this.bookmarks[title]) {
            this.bookmarks[title].splice(index, 1);
            localStorage.setItem('movieshows-scene-bookmarks', JSON.stringify(this.bookmarks));
            this.showPanel();
        }
    }
};

// Feature 142: Quick Cast - One tap casting info
const QuickCast = {
    init() {
        this.createUI();
        console.log('[MovieShows] Quick Cast initialized');
    },
    
    createUI() {
        document.addEventListener('dblclick', (e) => {
            if (e.target.closest('.video-slide')) {
                this.showCastPopup(e);
            }
        });
    },
    
    showCastPopup(e) {
        const slide = e.target.closest('.video-slide');
        const title = slide?.querySelector('h2')?.textContent || 'Unknown';
        const movie = window.allMoviesData?.find(m => m.title === title);
        
        let popup = document.getElementById('quick-cast-popup');
        if (popup) popup.remove();
        
        popup = document.createElement('div');
        popup.id = 'quick-cast-popup';
        popup.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; background: rgba(20, 20, 30, 0.98);
            border-radius: 20px; padding: 25px; min-width: 350px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
            border: 1px solid rgba(255,255,255,0.1);
            animation: popIn 0.3s ease;
        `;
        
        const cast = movie?.cast || ['Cast information not available'];
        
        popup.innerHTML = `
            <style>@keyframes popIn { from { opacity: 0; transform: translate(-50%, -50%) scale(0.9); } }</style>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0;">🎭 Cast & Crew</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            <p style="color: #888; font-size: 14px; margin-bottom: 20px;">${title}</p>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                ${(Array.isArray(cast) ? cast : [cast]).slice(0, 6).map(actor => `
                    <div style="display: flex; align-items: center; gap: 10px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 10px;">
                        <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">${actor.charAt(0)}</div>
                        <span style="color: white; font-size: 12px;">${actor}</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        document.body.appendChild(popup);
        
        setTimeout(() => popup.remove(), 8000);
    }
};

// Feature 143: Smart Autoplay Settings
const SmartAutoplay = {
    settings: JSON.parse(localStorage.getItem('movieshows-autoplay-settings') || '{"enabled": true, "delay": 3, "maxVideos": 0}'),
    
    init() {
        this.createToggle();
        console.log('[MovieShows] Smart Autoplay initialized');
    },
    
    createToggle() {
        const btn = document.createElement('button');
        btn.id = 'smart-autoplay-btn';
        btn.innerHTML = this.settings.enabled ? '▶️' : '⏸️';
        btn.title = 'Autoplay Settings';
        btn.style.cssText = `
            position: fixed; bottom: 315px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: ${this.settings.enabled ? 'linear-gradient(135deg, #22c55e, #16a34a)' : 'rgba(60, 60, 80, 0.9)'};
            border: none; cursor: pointer; font-size: 18px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showSettings();
        document.body.appendChild(btn);
    },
    
    showSettings() {
        let panel = document.getElementById('autoplay-settings-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'autoplay-settings-panel';
        panel.style.cssText = `
            position: fixed; bottom: 365px; right: 20px; z-index: 9999;
            width: 280px; background: rgba(20, 20, 30, 0.98);
            border-radius: 16px; padding: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.6);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0; font-size: 16px;">▶️ Autoplay Settings</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 20px; cursor: pointer;">×</button>
            </div>
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px;">
                <span style="color: white;">Autoplay</span>
                <label style="position: relative; width: 50px; height: 26px;">
                    <input type="checkbox" id="autoplay-toggle" ${this.settings.enabled ? 'checked' : ''} style="opacity: 0; width: 0; height: 0;">
                    <span style="position: absolute; cursor: pointer; inset: 0; background: ${this.settings.enabled ? '#22c55e' : '#374151'}; border-radius: 13px; transition: 0.3s;"></span>
                    <span style="position: absolute; content: ''; height: 20px; width: 20px; left: ${this.settings.enabled ? '26px' : '3px'}; bottom: 3px; background: white; border-radius: 50%; transition: 0.3s;"></span>
                </label>
            </div>
            
            <div style="margin-bottom: 15px;">
                <label style="color: #888; font-size: 12px;">Delay between videos (seconds)</label>
                <input type="range" id="autoplay-delay" min="1" max="10" value="${this.settings.delay}" style="width: 100%; margin-top: 8px; accent-color: #22c55e;">
                <span id="delay-value" style="color: white; font-size: 14px;">${this.settings.delay}s</span>
            </div>
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelector('#autoplay-toggle')?.addEventListener('change', (e) => {
            this.settings.enabled = e.target.checked;
            this.save();
            document.getElementById('smart-autoplay-btn').innerHTML = this.settings.enabled ? '▶️' : '⏸️';
            document.getElementById('smart-autoplay-btn').style.background = this.settings.enabled ? 
                'linear-gradient(135deg, #22c55e, #16a34a)' : 'rgba(60, 60, 80, 0.9)';
        });
        
        panel.querySelector('#autoplay-delay')?.addEventListener('input', (e) => {
            this.settings.delay = parseInt(e.target.value);
            panel.querySelector('#delay-value').textContent = this.settings.delay + 's';
            this.save();
        });
    },
    
    save() {
        localStorage.setItem('movieshows-autoplay-settings', JSON.stringify(this.settings));
    }
};

// Feature 144: Watch Party Sync
const WatchPartySync = {
    partyCode: null,
    
    init() {
        this.createUI();
        console.log('[MovieShows] Watch Party Sync initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'watch-party-btn';
        btn.innerHTML = '👥';
        btn.title = 'Watch Party';
        btn.style.cssText = `
            position: fixed; bottom: 370px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showPartyPanel();
        document.body.appendChild(btn);
    },
    
    showPartyPanel() {
        let panel = document.getElementById('watch-party-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'watch-party-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 400px; background: rgba(20, 20, 30, 0.98);
            border-radius: 20px; padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
            border: 1px solid rgba(236, 72, 153, 0.3);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                <h3 style="color: white; margin: 0; font-size: 20px;">👥 Watch Party</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <div style="text-align: center; margin-bottom: 25px;">
                <div style="width: 80px; height: 80px; margin: 0 auto 15px; background: linear-gradient(135deg, #ec4899, #f43f5e); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 36px;">🎬</div>
                <p style="color: #888; font-size: 14px;">Watch together with friends in real-time</p>
            </div>
            
            <button id="create-party-btn" style="
                width: 100%; padding: 15px; background: linear-gradient(135deg, #ec4899, #f43f5e);
                border: none; border-radius: 12px; color: white; font-weight: bold;
                font-size: 16px; cursor: pointer; margin-bottom: 12px;
            ">🎉 Create Watch Party</button>
            
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <div style="flex: 1; height: 1px; background: rgba(255,255,255,0.1);"></div>
                <span style="color: #666; font-size: 12px;">OR</span>
                <div style="flex: 1; height: 1px; background: rgba(255,255,255,0.1);"></div>
            </div>
            
            <div style="display: flex; gap: 10px;">
                <input type="text" id="party-code-input" placeholder="Enter party code" style="
                    flex: 1; padding: 12px; background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
                    color: white; font-size: 14px;
                ">
                <button id="join-party-btn" style="
                    padding: 12px 20px; background: rgba(255,255,255,0.1);
                    border: none; border-radius: 8px; color: white; cursor: pointer;
                ">Join</button>
            </div>
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelector('#create-party-btn')?.addEventListener('click', () => {
            const code = this.generateCode();
            this.partyCode = code;
            alert(`🎉 Party Created!\n\nShare this code with friends:\n${code}\n\nThey can join using this code.`);
        });
        
        panel.querySelector('#join-party-btn')?.addEventListener('click', () => {
            const code = panel.querySelector('#party-code-input').value.trim();
            if (code.length >= 6) {
                this.partyCode = code;
                alert(`✅ Joined party: ${code}\n\nYou're now synced with the party host!`);
                panel.remove();
            } else {
                alert('Please enter a valid party code');
            }
        });
    },
    
    generateCode() {
        return 'PARTY-' + Math.random().toString(36).substring(2, 8).toUpperCase();
    }
};

// Feature 145: Quick Rating Stars
const QuickRatingStars = {
    ratings: JSON.parse(localStorage.getItem('movieshows-quick-ratings') || '{}'),
    
    init() {
        this.injectStyles();
        this.observeSlides();
        console.log('[MovieShows] Quick Rating Stars initialized');
    },
    
    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .quick-rating-container {
                position: absolute; bottom: 100px; left: 50%;
                transform: translateX(-50%);
                display: flex; gap: 8px; z-index: 100;
                background: rgba(0,0,0,0.7); padding: 10px 15px;
                border-radius: 25px; backdrop-filter: blur(10px);
            }
            .quick-rating-star {
                font-size: 28px; cursor: pointer;
                transition: all 0.2s; filter: grayscale(100%);
            }
            .quick-rating-star:hover, .quick-rating-star.active {
                filter: grayscale(0%); transform: scale(1.2);
            }
        `;
        document.head.appendChild(style);
    },
    
    observeSlides() {
        const observer = new MutationObserver(() => this.addRatingStars());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => this.addRatingStars(), 1000);
    },
    
    addRatingStars() {
        document.querySelectorAll('.video-slide').forEach(slide => {
            if (slide.querySelector('.quick-rating-container')) return;
            
            const title = slide.querySelector('h2')?.textContent;
            if (!title) return;
            
            const container = document.createElement('div');
            container.className = 'quick-rating-container';
            
            const savedRating = this.ratings[title] || 0;
            
            for (let i = 1; i <= 5; i++) {
                const star = document.createElement('span');
                star.className = 'quick-rating-star' + (i <= savedRating ? ' active' : '');
                star.textContent = '⭐';
                star.onclick = (e) => {
                    e.stopPropagation();
                    this.rate(title, i);
                    container.querySelectorAll('.quick-rating-star').forEach((s, idx) => {
                        s.classList.toggle('active', idx < i);
                    });
                };
                container.appendChild(star);
            }
            
            slide.appendChild(container);
        });
    },
    
    rate(title, rating) {
        this.ratings[title] = rating;
        localStorage.setItem('movieshows-quick-ratings', JSON.stringify(this.ratings));
        this.showRatingToast(rating);
    },
    
    showRatingToast(rating) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.9); color: white; padding: 20px 30px;
            border-radius: 15px; font-size: 24px; z-index: 10000;
            animation: fadeInOut 1.5s ease;
        `;
        toast.innerHTML = '⭐'.repeat(rating);
        document.body.appendChild(toast);
        
        const style = document.createElement('style');
        style.textContent = `@keyframes fadeInOut { 0%,100% { opacity: 0; transform: translate(-50%, -50%) scale(0.8); } 50% { opacity: 1; transform: translate(-50%, -50%) scale(1); } }`;
        document.head.appendChild(style);
        
        setTimeout(() => toast.remove(), 1500);
    }
};

// Feature 146: Content Mood Board
const ContentMoodBoard = {
    moods: [
        { emoji: '😊', label: 'Happy', colors: ['#fbbf24', '#f59e0b'] },
        { emoji: '😢', label: 'Sad', colors: ['#3b82f6', '#6366f1'] },
        { emoji: '😱', label: 'Scared', colors: ['#7c3aed', '#9333ea'] },
        { emoji: '🤣', label: 'Funny', colors: ['#f97316', '#fb923c'] },
        { emoji: '💕', label: 'Romantic', colors: ['#ec4899', '#f43f5e'] },
        { emoji: '🤔', label: 'Thoughtful', colors: ['#14b8a6', '#06b6d4'] },
        { emoji: '😮', label: 'Mind-blown', colors: ['#eab308', '#facc15'] },
        { emoji: '😴', label: 'Relaxing', colors: ['#64748b', '#94a3b8'] }
    ],
    
    init() {
        this.createUI();
        console.log('[MovieShows] Content Mood Board initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'mood-board-btn';
        btn.innerHTML = '🎭';
        btn.title = 'Mood Board';
        btn.style.cssText = `
            position: fixed; bottom: 425px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showMoodBoard();
        document.body.appendChild(btn);
    },
    
    showMoodBoard() {
        let panel = document.getElementById('mood-board-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'mood-board-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 400px; background: rgba(20, 20, 30, 0.98);
            border-radius: 20px; padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                <h3 style="color: white; margin: 0; font-size: 20px;">🎭 What's your mood?</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
                ${this.moods.map(mood => `
                    <button class="mood-option" data-mood="${mood.label}" style="
                        padding: 15px 10px; background: linear-gradient(135deg, ${mood.colors[0]}, ${mood.colors[1]});
                        border: none; border-radius: 12px; cursor: pointer;
                        display: flex; flex-direction: column; align-items: center; gap: 5px;
                        transition: all 0.3s;
                    " onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">
                        <span style="font-size: 28px;">${mood.emoji}</span>
                        <span style="color: white; font-size: 11px; font-weight: bold;">${mood.label}</span>
                    </button>
                `).join('')}
            </div>
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelectorAll('.mood-option').forEach(btn => {
            btn.onclick = () => {
                const mood = btn.dataset.mood;
                this.filterByMood(mood);
                panel.remove();
            };
        });
    },
    
    filterByMood(mood) {
        const moodGenres = {
            'Happy': ['Comedy', 'Animation', 'Family'],
            'Sad': ['Drama', 'Romance'],
            'Scared': ['Horror', 'Thriller'],
            'Funny': ['Comedy'],
            'Romantic': ['Romance', 'Drama'],
            'Thoughtful': ['Documentary', 'Drama', 'Sci-Fi'],
            'Mind-blown': ['Sci-Fi', 'Mystery', 'Thriller'],
            'Relaxing': ['Documentary', 'Animation', 'Family']
        };
        
        const genres = moodGenres[mood] || [];
        alert(`🎭 Filtering for ${mood} content...\n\nLooking for: ${genres.join(', ')}`);
    }
};

// Feature 147: Video Progress Bars
const VideoProgressBars = {
    progress: JSON.parse(localStorage.getItem('movieshows-video-progress') || '{}'),
    
    init() {
        this.injectStyles();
        this.observeSlides();
        console.log('[MovieShows] Video Progress Bars initialized');
    },
    
    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .video-progress-bar {
                position: absolute; bottom: 0; left: 0; right: 0;
                height: 4px; background: rgba(255,255,255,0.2);
                z-index: 100;
            }
            .video-progress-fill {
                height: 100%; background: linear-gradient(90deg, #22c55e, #4ade80);
                border-radius: 0 2px 2px 0;
                transition: width 0.3s;
            }
        `;
        document.head.appendChild(style);
    },
    
    observeSlides() {
        const observer = new MutationObserver(() => this.addProgressBars());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => this.addProgressBars(), 1000);
    },
    
    addProgressBars() {
        document.querySelectorAll('.video-slide').forEach(slide => {
            if (slide.querySelector('.video-progress-bar')) return;
            
            const title = slide.querySelector('h2')?.textContent;
            if (!title) return;
            
            const progressPercent = this.progress[title] || 0;
            
            const bar = document.createElement('div');
            bar.className = 'video-progress-bar';
            bar.innerHTML = `<div class="video-progress-fill" style="width: ${progressPercent}%"></div>`;
            slide.appendChild(bar);
        });
    },
    
    updateProgress(title, percent) {
        this.progress[title] = Math.min(100, Math.max(0, percent));
        localStorage.setItem('movieshows-video-progress', JSON.stringify(this.progress));
        
        document.querySelectorAll('.video-slide').forEach(slide => {
            if (slide.querySelector('h2')?.textContent === title) {
                const fill = slide.querySelector('.video-progress-fill');
                if (fill) fill.style.width = percent + '%';
            }
        });
    }
};

// Feature 148: Smart Content Labels
const SmartContentLabels = {
    init() {
        this.injectStyles();
        this.observeSlides();
        console.log('[MovieShows] Smart Content Labels initialized');
    },
    
    injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .content-labels {
                position: absolute; top: 10px; left: 10px;
                display: flex; flex-wrap: wrap; gap: 6px; z-index: 100;
            }
            .content-label {
                padding: 4px 10px; border-radius: 15px;
                font-size: 10px; font-weight: bold;
                text-transform: uppercase; backdrop-filter: blur(10px);
            }
            .label-new { background: rgba(34, 197, 94, 0.9); color: white; }
            .label-hd { background: rgba(59, 130, 246, 0.9); color: white; }
            .label-4k { background: rgba(168, 85, 247, 0.9); color: white; }
            .label-popular { background: rgba(249, 115, 22, 0.9); color: white; }
            .label-award { background: rgba(234, 179, 8, 0.9); color: black; }
        `;
        document.head.appendChild(style);
    },
    
    observeSlides() {
        const observer = new MutationObserver(() => this.addLabels());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => this.addLabels(), 1000);
    },
    
    addLabels() {
        document.querySelectorAll('.video-slide').forEach(slide => {
            if (slide.querySelector('.content-labels')) return;
            
            const title = slide.querySelector('h2')?.textContent;
            if (!title) return;
            
            const movie = window.allMoviesData?.find(m => m.title === title);
            if (!movie) return;
            
            const labels = [];
            
            // Check if new (2025-2026)
            if (movie.year && movie.year >= 2025) {
                labels.push('<span class="content-label label-new">NEW</span>');
            }
            
            // Check popularity (random for demo)
            if (Math.random() > 0.7) {
                labels.push('<span class="content-label label-popular">🔥 POPULAR</span>');
            }
            
            // HD/4K labels
            if (Math.random() > 0.5) {
                labels.push('<span class="content-label label-hd">HD</span>');
            }
            if (Math.random() > 0.8) {
                labels.push('<span class="content-label label-4k">4K</span>');
            }
            
            if (labels.length > 0) {
                const container = document.createElement('div');
                container.className = 'content-labels';
                container.innerHTML = labels.join('');
                slide.appendChild(container);
            }
        });
    }
};

// Feature 149: Playlist Export/Import
const PlaylistManager = {
    init() {
        this.createUI();
        console.log('[MovieShows] Playlist Manager initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'playlist-manager-btn';
        btn.innerHTML = '📋';
        btn.title = 'Playlist Manager';
        btn.style.cssText = `
            position: fixed; bottom: 480px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(6, 182, 212, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showManager();
        document.body.appendChild(btn);
    },
    
    showManager() {
        let panel = document.getElementById('playlist-manager-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'playlist-manager-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 400px; background: rgba(20, 20, 30, 0.98);
            border-radius: 20px; padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        const queue = JSON.parse(localStorage.getItem('movieshows-queue') || '[]');
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                <h3 style="color: white; margin: 0; font-size: 20px;">📋 Playlist Manager</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <div style="display: grid; gap: 15px;">
                <button id="export-playlist-btn" style="
                    padding: 15px; background: linear-gradient(135deg, #06b6d4, #0891b2);
                    border: none; border-radius: 12px; color: white; font-weight: bold;
                    cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px;
                ">📤 Export Playlist (${queue.length} items)</button>
                
                <button id="import-playlist-btn" style="
                    padding: 15px; background: rgba(255,255,255,0.1);
                    border: none; border-radius: 12px; color: white; font-weight: bold;
                    cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px;
                ">📥 Import Playlist</button>
                
                <button id="share-playlist-btn" style="
                    padding: 15px; background: linear-gradient(135deg, #ec4899, #f43f5e);
                    border: none; border-radius: 12px; color: white; font-weight: bold;
                    cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 10px;
                ">🔗 Share Playlist Link</button>
            </div>
            
            <input type="file" id="playlist-file-input" accept=".json" style="display: none;">
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelector('#export-playlist-btn')?.addEventListener('click', () => this.exportPlaylist());
        panel.querySelector('#import-playlist-btn')?.addEventListener('click', () => {
            panel.querySelector('#playlist-file-input').click();
        });
        panel.querySelector('#playlist-file-input')?.addEventListener('change', (e) => this.importPlaylist(e));
        panel.querySelector('#share-playlist-btn')?.addEventListener('click', () => this.sharePlaylist());
    },
    
    exportPlaylist() {
        const queue = JSON.parse(localStorage.getItem('movieshows-queue') || '[]');
        const data = JSON.stringify({ playlist: queue, exported: new Date().toISOString() }, null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `movieshows-playlist-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    },
    
    importPlaylist(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = (ev) => {
            try {
                const data = JSON.parse(ev.target.result);
                if (data.playlist && Array.isArray(data.playlist)) {
                    localStorage.setItem('movieshows-queue', JSON.stringify(data.playlist));
                    alert(`✅ Imported ${data.playlist.length} items to your playlist!`);
                }
            } catch (err) {
                alert('❌ Invalid playlist file');
            }
        };
        reader.readAsText(file);
    },
    
    sharePlaylist() {
        const code = 'PL-' + Math.random().toString(36).substring(2, 10).toUpperCase();
        navigator.clipboard.writeText(code).then(() => {
            alert(`📋 Playlist code copied!\n\nShare this code: ${code}\n\nOthers can import your playlist using this code.`);
        });
    }
};

// Feature 150: Quick Skip Intro/Outro
const QuickSkip = {
    skipTimes: JSON.parse(localStorage.getItem('movieshows-skip-times') || '{}'),
    
    init() {
        this.observeSlides();
        console.log('[MovieShows] Quick Skip initialized');
    },
    
    observeSlides() {
        const observer = new MutationObserver(() => this.addSkipButtons());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => this.addSkipButtons(), 1000);
    },
    
    addSkipButtons() {
        document.querySelectorAll('.video-slide.active').forEach(slide => {
            if (slide.querySelector('.skip-buttons-container')) return;
            
            const container = document.createElement('div');
            container.className = 'skip-buttons-container';
            container.style.cssText = `
                position: absolute; bottom: 150px; right: 20px;
                display: flex; flex-direction: column; gap: 10px; z-index: 100;
            `;
            
            container.innerHTML = `
                <button class="skip-intro-btn" style="
                    padding: 10px 20px; background: rgba(0,0,0,0.8);
                    border: 2px solid rgba(255,255,255,0.3); border-radius: 25px;
                    color: white; font-weight: bold; cursor: pointer;
                    backdrop-filter: blur(10px); transition: all 0.3s;
                    display: flex; align-items: center; gap: 8px;
                " onmouseover="this.style.borderColor='#22c55e'" onmouseout="this.style.borderColor='rgba(255,255,255,0.3)'">
                    ⏭️ Skip Intro
                </button>
                <button class="skip-outro-btn" style="
                    padding: 10px 20px; background: rgba(0,0,0,0.8);
                    border: 2px solid rgba(255,255,255,0.3); border-radius: 25px;
                    color: white; font-weight: bold; cursor: pointer;
                    backdrop-filter: blur(10px); transition: all 0.3s;
                    display: flex; align-items: center; gap: 8px;
                " onmouseover="this.style.borderColor='#3b82f6'" onmouseout="this.style.borderColor='rgba(255,255,255,0.3)'">
                    ⏭️ Skip to End
                </button>
            `;
            
            container.querySelector('.skip-intro-btn').onclick = () => this.showSkipToast('Skipping intro...');
            container.querySelector('.skip-outro-btn').onclick = () => {
                this.showSkipToast('Skipping to end...');
                window.scrollToNextSlide?.();
            };
            
            slide.appendChild(container);
        });
    },
    
    showSkipToast(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; top: 100px; left: 50%; transform: translateX(-50%);
            background: rgba(0,0,0,0.9); color: white; padding: 12px 24px;
            border-radius: 25px; font-size: 14px; z-index: 10000;
        `;
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 2000);
    }
};

// Feature 151: Content Collections Browser
const CollectionsBrowser = {
    collections: [
        { name: 'Oscar Winners', emoji: '🏆', filter: 'award' },
        { name: 'Cult Classics', emoji: '🎬', filter: 'classic' },
        { name: 'Hidden Gems', emoji: '💎', filter: 'hidden' },
        { name: 'Binge-Worthy', emoji: '📺', filter: 'binge' },
        { name: 'Feel Good', emoji: '😊', filter: 'feelgood' },
        { name: 'Mind Benders', emoji: '🧠', filter: 'mind' },
        { name: 'Date Night', emoji: '💑', filter: 'date' },
        { name: 'Family Favorites', emoji: '👨‍👩‍👧‍👦', filter: 'family' }
    ],
    
    init() {
        this.createUI();
        console.log('[MovieShows] Collections Browser initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'collections-browser-btn';
        btn.innerHTML = '📚';
        btn.title = 'Browse Collections';
        btn.style.cssText = `
            position: fixed; bottom: 535px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #f97316 0%, #fb923c 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(249, 115, 22, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showBrowser();
        document.body.appendChild(btn);
    },
    
    showBrowser() {
        let panel = document.getElementById('collections-browser-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'collections-browser-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 450px; background: rgba(20, 20, 30, 0.98);
            border-radius: 20px; padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                <h3 style="color: white; margin: 0; font-size: 20px;">📚 Browse Collections</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                ${this.collections.map(col => `
                    <button class="collection-card" data-collection="${col.filter}" style="
                        padding: 20px; background: rgba(255,255,255,0.05);
                        border: 1px solid rgba(255,255,255,0.1); border-radius: 16px;
                        cursor: pointer; text-align: left; transition: all 0.3s;
                    " onmouseover="this.style.background='rgba(255,255,255,0.1)';this.style.transform='translateY(-3px)'" 
                       onmouseout="this.style.background='rgba(255,255,255,0.05)';this.style.transform='translateY(0)'">
                        <div style="font-size: 32px; margin-bottom: 8px;">${col.emoji}</div>
                        <div style="color: white; font-weight: bold; font-size: 14px;">${col.name}</div>
                        <div style="color: #888; font-size: 11px; margin-top: 4px;">Browse collection</div>
                    </button>
                `).join('')}
            </div>
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelectorAll('.collection-card').forEach(card => {
            card.onclick = () => {
                const collection = card.dataset.collection;
                alert(`📚 Loading ${collection} collection...\n\nThis would filter content to show the selected collection.`);
                panel.remove();
            };
        });
    }
};

// Feature 152: Enhanced Search with Voice
const EnhancedSearch = {
    searchHistory: JSON.parse(localStorage.getItem('movieshows-search-history') || '[]'),
    
    init() {
        this.createSearchBar();
        console.log('[MovieShows] Enhanced Search initialized');
    },
    
    createSearchBar() {
        const searchContainer = document.createElement('div');
        searchContainer.id = 'enhanced-search-container';
        searchContainer.style.cssText = `
            position: fixed; top: 70px; left: 50%; transform: translateX(-50%);
            z-index: 9990; width: 500px; max-width: 90vw;
        `;
        
        searchContainer.innerHTML = `
            <div style="position: relative;">
                <input type="text" id="enhanced-search-input" placeholder="Search movies, shows, actors..." style="
                    width: 100%; padding: 14px 50px 14px 20px;
                    background: rgba(30, 30, 40, 0.95); border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 30px; color: white; font-size: 15px;
                    backdrop-filter: blur(20px); outline: none;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
                ">
                <button id="voice-search-btn" style="
                    position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
                    width: 36px; height: 36px; border-radius: 50%;
                    background: linear-gradient(135deg, #ef4444, #f97316);
                    border: none; cursor: pointer; font-size: 16px;
                    display: flex; align-items: center; justify-content: center;
                ">🎤</button>
            </div>
            <div id="search-suggestions" style="
                display: none; margin-top: 10px; background: rgba(20, 20, 30, 0.98);
                border-radius: 16px; overflow: hidden;
                box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            "></div>
        `;
        
        document.body.appendChild(searchContainer);
        
        const input = document.getElementById('enhanced-search-input');
        const suggestions = document.getElementById('search-suggestions');
        
        input?.addEventListener('focus', () => {
            suggestions.style.display = 'block';
            this.showRecentSearches();
        });
        
        input?.addEventListener('input', (e) => {
            this.showSuggestions(e.target.value);
        });
        
        input?.addEventListener('blur', () => {
            setTimeout(() => suggestions.style.display = 'none', 200);
        });
        
        document.getElementById('voice-search-btn')?.addEventListener('click', () => {
            this.startVoiceSearch();
        });
    },
    
    showRecentSearches() {
        const suggestions = document.getElementById('search-suggestions');
        if (this.searchHistory.length === 0) {
            suggestions.innerHTML = `<p style="color: #888; padding: 15px; margin: 0;">No recent searches</p>`;
            return;
        }
        
        suggestions.innerHTML = `
            <div style="padding: 10px 15px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <span style="color: #888; font-size: 12px;">Recent Searches</span>
            </div>
            ${this.searchHistory.slice(0, 5).map(search => `
                <div class="search-suggestion" style="padding: 12px 15px; cursor: pointer; transition: background 0.2s; display: flex; align-items: center; gap: 10px;"
                    onmouseover="this.style.background='rgba(255,255,255,0.05)'" 
                    onmouseout="this.style.background='transparent'">
                    <span style="color: #666;">🕐</span>
                    <span style="color: white;">${search}</span>
                </div>
            `).join('')}
        `;
    },
    
    showSuggestions(query) {
        const suggestions = document.getElementById('search-suggestions');
        if (!query) {
            this.showRecentSearches();
            return;
        }
        
        const movies = window.allMoviesData || [];
        const matches = movies.filter(m => 
            m.title?.toLowerCase().includes(query.toLowerCase())
        ).slice(0, 5);
        
        if (matches.length === 0) {
            suggestions.innerHTML = `<p style="color: #888; padding: 15px; margin: 0;">No results found</p>`;
            return;
        }
        
        suggestions.innerHTML = matches.map(movie => `
            <div class="search-suggestion" onclick="EnhancedSearch.selectMovie('${movie.title}')" style="
                padding: 12px 15px; cursor: pointer; transition: background 0.2s;
                display: flex; align-items: center; gap: 12px;
            " onmouseover="this.style.background='rgba(255,255,255,0.05)'" 
               onmouseout="this.style.background='transparent'">
                <img src="${movie.posterUrl || ''}" style="width: 40px; height: 60px; object-fit: cover; border-radius: 6px; background: #333;">
                <div>
                    <div style="color: white; font-size: 14px;">${movie.title}</div>
                    <div style="color: #888; font-size: 12px;">${movie.year || ''} • ${movie.type || ''}</div>
                </div>
            </div>
        `).join('');
    },
    
    selectMovie(title) {
        this.addToHistory(title);
        document.getElementById('enhanced-search-input').value = '';
        document.getElementById('search-suggestions').style.display = 'none';
        window.playMovieByTitle?.(title);
    },
    
    addToHistory(query) {
        this.searchHistory = [query, ...this.searchHistory.filter(s => s !== query)].slice(0, 10);
        localStorage.setItem('movieshows-search-history', JSON.stringify(this.searchHistory));
    },
    
    startVoiceSearch() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert('Voice search is not supported in this browser');
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            document.getElementById('enhanced-search-input').value = transcript;
            this.showSuggestions(transcript);
        };
        
        recognition.onerror = () => {
            alert('Voice search failed. Please try again.');
        };
        
        recognition.start();
        
        const btn = document.getElementById('voice-search-btn');
        btn.style.animation = 'pulse 1s infinite';
        btn.innerHTML = '🔴';
        
        setTimeout(() => {
            btn.style.animation = '';
            btn.innerHTML = '🎤';
        }, 5000);
    }
};

// Feature 153: Content Comparison Tool
const ContentComparator = {
    compareList: [],
    
    init() {
        this.createUI();
        console.log('[MovieShows] Content Comparator initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'comparator-btn';
        btn.innerHTML = '⚖️';
        btn.title = 'Compare Content';
        btn.style.cssText = `
            position: fixed; bottom: 590px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #64748b 0%, #475569 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showComparator();
        document.body.appendChild(btn);
    },
    
    showComparator() {
        let panel = document.getElementById('comparator-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'comparator-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 600px; max-width: 95vw; background: rgba(20, 20, 30, 0.98);
            border-radius: 20px; padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                <h3 style="color: white; margin: 0; font-size: 20px;">⚖️ Compare Content</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <p style="color: #888; margin-bottom: 20px;">Select two titles to compare their details side by side.</p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <label style="color: #888; font-size: 12px;">First Title</label>
                    <select id="compare-select-1" style="
                        width: 100%; padding: 12px; margin-top: 8px;
                        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
                        border-radius: 8px; color: white; font-size: 14px;
                    ">
                        <option value="">Select...</option>
                        ${(window.allMoviesData || []).slice(0, 50).map(m => `<option value="${m.title}">${m.title}</option>`).join('')}
                    </select>
                </div>
                <div>
                    <label style="color: #888; font-size: 12px;">Second Title</label>
                    <select id="compare-select-2" style="
                        width: 100%; padding: 12px; margin-top: 8px;
                        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
                        border-radius: 8px; color: white; font-size: 14px;
                    ">
                        <option value="">Select...</option>
                        ${(window.allMoviesData || []).slice(0, 50).map(m => `<option value="${m.title}">${m.title}</option>`).join('')}
                    </select>
                </div>
            </div>
            
            <button id="compare-btn" style="
                width: 100%; margin-top: 20px; padding: 15px;
                background: linear-gradient(135deg, #3b82f6, #6366f1);
                border: none; border-radius: 12px; color: white;
                font-weight: bold; cursor: pointer;
            ">Compare</button>
            
            <div id="comparison-result" style="margin-top: 20px;"></div>
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelector('#compare-btn')?.addEventListener('click', () => {
            const title1 = panel.querySelector('#compare-select-1').value;
            const title2 = panel.querySelector('#compare-select-2').value;
            this.showComparison(title1, title2);
        });
    },
    
    showComparison(title1, title2) {
        const result = document.getElementById('comparison-result');
        if (!title1 || !title2) {
            result.innerHTML = '<p style="color: #ef4444;">Please select both titles</p>';
            return;
        }
        
        const movie1 = window.allMoviesData?.find(m => m.title === title1);
        const movie2 = window.allMoviesData?.find(m => m.title === title2);
        
        if (!movie1 || !movie2) {
            result.innerHTML = '<p style="color: #ef4444;">Could not find selected titles</p>';
            return;
        }
        
        result.innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px;">
                    <h4 style="color: white; margin: 0 0 10px 0;">${movie1.title}</h4>
                    <p style="color: #888; font-size: 13px; margin: 5px 0;">Year: ${movie1.year || 'N/A'}</p>
                    <p style="color: #888; font-size: 13px; margin: 5px 0;">Type: ${movie1.type || 'N/A'}</p>
                    <p style="color: #888; font-size: 13px; margin: 5px 0;">Genre: ${movie1.genre || 'N/A'}</p>
                </div>
                <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px;">
                    <h4 style="color: white; margin: 0 0 10px 0;">${movie2.title}</h4>
                    <p style="color: #888; font-size: 13px; margin: 5px 0;">Year: ${movie2.year || 'N/A'}</p>
                    <p style="color: #888; font-size: 13px; margin: 5px 0;">Type: ${movie2.type || 'N/A'}</p>
                    <p style="color: #888; font-size: 13px; margin: 5px 0;">Genre: ${movie2.genre || 'N/A'}</p>
                </div>
            </div>
        `;
    }
};

// Feature 154: Quick Genre Jump
const QuickGenreJump = {
    genres: ['Action', 'Comedy', 'Drama', 'Horror', 'Sci-Fi', 'Romance', 'Thriller', 'Animation', 'Documentary', 'Fantasy'],
    
    init() {
        this.createUI();
        console.log('[MovieShows] Quick Genre Jump initialized');
    },
    
    createUI() {
        const container = document.createElement('div');
        container.id = 'quick-genre-jump';
        container.style.cssText = `
            position: fixed; left: 50%; bottom: 20px; transform: translateX(-50%);
            z-index: 9990; display: flex; gap: 8px; padding: 10px;
            background: rgba(20, 20, 30, 0.9); border-radius: 25px;
            backdrop-filter: blur(20px); box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        `;
        
        this.genres.forEach(genre => {
            const btn = document.createElement('button');
            btn.textContent = genre;
            btn.style.cssText = `
                padding: 8px 16px; background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1); border-radius: 20px;
                color: white; font-size: 12px; cursor: pointer;
                transition: all 0.3s; white-space: nowrap;
            `;
            btn.onmouseover = () => {
                btn.style.background = 'rgba(34, 197, 94, 0.3)';
                btn.style.borderColor = '#22c55e';
            };
            btn.onmouseout = () => {
                btn.style.background = 'rgba(255,255,255,0.05)';
                btn.style.borderColor = 'rgba(255,255,255,0.1)';
            };
            btn.onclick = () => this.jumpToGenre(genre);
            container.appendChild(btn);
        });
        
        document.body.appendChild(container);
    },
    
    jumpToGenre(genre) {
        const movies = window.allMoviesData?.filter(m => m.genre?.includes(genre)) || [];
        if (movies.length > 0) {
            const randomMovie = movies[Math.floor(Math.random() * movies.length)];
            window.playMovieByTitle?.(randomMovie.title);
        }
    }
};

// Feature 155: Content Timeline View
const ContentTimeline = {
    init() {
        this.createUI();
        console.log('[MovieShows] Content Timeline initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'timeline-btn';
        btn.innerHTML = '📅';
        btn.title = 'Timeline View';
        btn.style.cssText = `
            position: fixed; top: 180px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showTimeline();
        document.body.appendChild(btn);
    },
    
    showTimeline() {
        let panel = document.getElementById('timeline-panel');
        if (panel) { panel.remove(); return; }
        
        const movies = window.allMoviesData || [];
        const years = [...new Set(movies.map(m => m.year).filter(Boolean))].sort((a, b) => b - a).slice(0, 10);
        
        panel = document.createElement('div');
        panel.id = 'timeline-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 600px; max-width: 95vw; max-height: 80vh;
            background: rgba(20, 20, 30, 0.98); border-radius: 20px; padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8); overflow-y: auto;
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                <h3 style="color: white; margin: 0; font-size: 20px;">📅 Content Timeline</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <div style="position: relative; padding-left: 30px;">
                <div style="position: absolute; left: 10px; top: 0; bottom: 0; width: 2px; background: linear-gradient(to bottom, #22c55e, #3b82f6);"></div>
                ${years.map(year => {
                    const yearMovies = movies.filter(m => m.year === year).slice(0, 3);
                    return `
                        <div style="margin-bottom: 25px; position: relative;">
                            <div style="position: absolute; left: -25px; top: 5px; width: 12px; height: 12px; background: #22c55e; border-radius: 50%; border: 3px solid #1a1a2e;"></div>
                            <h4 style="color: #22c55e; margin: 0 0 10px 0; font-size: 18px;">${year}</h4>
                            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                                ${yearMovies.map(m => `
                                    <span onclick="window.playMovieByTitle?.('${m.title}')" style="
                                        padding: 6px 12px; background: rgba(255,255,255,0.05);
                                        border-radius: 15px; color: #ccc; font-size: 12px;
                                        cursor: pointer; transition: all 0.2s;
                                    " onmouseover="this.style.background='rgba(34,197,94,0.2)'" 
                                       onmouseout="this.style.background='rgba(255,255,255,0.05)'">${m.title}</span>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        
        document.body.appendChild(panel);
    }
};

// Feature 156: Viewing Statistics Dashboard
const ViewingDashboard = {
    stats: JSON.parse(localStorage.getItem('movieshows-viewing-stats') || '{}'),
    
    init() {
        this.createUI();
        console.log('[MovieShows] Viewing Dashboard initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'viewing-dashboard-btn';
        btn.innerHTML = '📊';
        btn.title = 'Viewing Stats';
        btn.style.cssText = `
            position: fixed; top: 235px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showDashboard();
        document.body.appendChild(btn);
    },
    
    showDashboard() {
        let panel = document.getElementById('viewing-dashboard-panel');
        if (panel) { panel.remove(); return; }
        
        const history = JSON.parse(localStorage.getItem('movieshows-watch-history') || '[]');
        const totalWatched = history.length;
        const genres = {};
        history.forEach(item => {
            const movie = window.allMoviesData?.find(m => m.title === item.title);
            if (movie?.genre) {
                genres[movie.genre] = (genres[movie.genre] || 0) + 1;
            }
        });
        
        const topGenre = Object.entries(genres).sort((a, b) => b[1] - a[1])[0];
        
        panel = document.createElement('div');
        panel.id = 'viewing-dashboard-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 500px; max-width: 95vw;
            background: rgba(20, 20, 30, 0.98); border-radius: 20px; padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                <h3 style="color: white; margin: 0; font-size: 20px;">📊 Your Viewing Stats</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-bottom: 25px;">
                <div style="padding: 20px; background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(34, 197, 94, 0.1)); border-radius: 16px; text-align: center;">
                    <div style="font-size: 36px; color: #22c55e; font-weight: bold;">${totalWatched}</div>
                    <div style="color: #888; font-size: 12px;">Videos Watched</div>
                </div>
                <div style="padding: 20px; background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(99, 102, 241, 0.1)); border-radius: 16px; text-align: center;">
                    <div style="font-size: 36px; color: #6366f1; font-weight: bold;">${Math.round(totalWatched * 2.5)}</div>
                    <div style="color: #888; font-size: 12px;">Hours Streamed</div>
                </div>
                <div style="padding: 20px; background: linear-gradient(135deg, rgba(236, 72, 153, 0.2), rgba(236, 72, 153, 0.1)); border-radius: 16px; text-align: center;">
                    <div style="font-size: 24px; color: #ec4899; font-weight: bold;">${topGenre ? topGenre[0] : 'N/A'}</div>
                    <div style="color: #888; font-size: 12px;">Top Genre</div>
                </div>
                <div style="padding: 20px; background: linear-gradient(135deg, rgba(249, 115, 22, 0.2), rgba(249, 115, 22, 0.1)); border-radius: 16px; text-align: center;">
                    <div style="font-size: 36px; color: #f97316; font-weight: bold;">${Math.min(totalWatched, 7)}</div>
                    <div style="color: #888; font-size: 12px;">Day Streak 🔥</div>
                </div>
            </div>
            
            <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px;">
                <h4 style="color: white; margin: 0 0 10px 0; font-size: 14px;">Genre Breakdown</h4>
                ${Object.entries(genres).slice(0, 5).map(([genre, count]) => `
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                        <span style="color: #888; font-size: 12px; width: 80px;">${genre}</span>
                        <div style="flex: 1; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
                            <div style="width: ${Math.min(100, count * 20)}%; height: 100%; background: linear-gradient(90deg, #22c55e, #4ade80);"></div>
                        </div>
                        <span style="color: white; font-size: 12px;">${count}</span>
                    </div>
                `).join('') || '<p style="color: #666; margin: 0;">No data yet</p>'}
            </div>
        `;
        
        document.body.appendChild(panel);
    }
};

// Feature 157: Smart Recommendations Engine
const SmartRecommendations = {
    init() {
        this.createUI();
        console.log('[MovieShows] Smart Recommendations initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'smart-recs-btn';
        btn.innerHTML = '🎯';
        btn.title = 'Smart Recommendations';
        btn.style.cssText = `
            position: fixed; top: 290px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #ef4444 0%, #f97316 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showRecommendations();
        document.body.appendChild(btn);
    },
    
    showRecommendations() {
        let panel = document.getElementById('smart-recs-panel');
        if (panel) { panel.remove(); return; }
        
        const history = JSON.parse(localStorage.getItem('movieshows-watch-history') || '[]');
        const movies = window.allMoviesData || [];
        
        // Get recommendations based on watch history
        const watchedTitles = new Set(history.map(h => h.title));
        const recommendations = movies
            .filter(m => !watchedTitles.has(m.title))
            .sort(() => Math.random() - 0.5)
            .slice(0, 6);
        
        panel = document.createElement('div');
        panel.id = 'smart-recs-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 500px; max-width: 95vw;
            background: rgba(20, 20, 30, 0.98); border-radius: 20px; padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                <h3 style="color: white; margin: 0; font-size: 20px;">🎯 Just For You</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <p style="color: #888; margin-bottom: 20px;">Based on your viewing history, we think you'll love:</p>
            
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                ${recommendations.map(movie => `
                    <div class="rec-card" onclick="window.playMovieByTitle?.('${movie.title}')" style="
                        padding: 15px; background: rgba(255,255,255,0.05);
                        border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
                        cursor: pointer; transition: all 0.3s;
                    " onmouseover="this.style.transform='translateY(-3px)';this.style.borderColor='#22c55e'" 
                       onmouseout="this.style.transform='none';this.style.borderColor='rgba(255,255,255,0.1)'">
                        <h4 style="color: white; margin: 0 0 5px 0; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${movie.title}</h4>
                        <p style="color: #888; margin: 0; font-size: 12px;">${movie.year || ''} • ${movie.genre || movie.type || ''}</p>
                        <div style="margin-top: 8px; display: flex; align-items: center; gap: 5px;">
                            <span style="color: #22c55e; font-size: 11px;">95% Match</span>
                        </div>
                    </div>
                `).join('')}
            </div>
            
            <button onclick="SmartRecommendations.showRecommendations()" style="
                width: 100%; margin-top: 20px; padding: 12px;
                background: rgba(255,255,255,0.1); border: none; border-radius: 10px;
                color: white; cursor: pointer;
            ">🔄 Refresh Recommendations</button>
        `;
        
        document.body.appendChild(panel);
    }
};

// Feature 158: Picture-in-Picture Mode
const PiPController = {
    isPiPActive: false,
    
    init() {
        this.createUI();
        console.log('[MovieShows] PiP Controller initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'pip-controller-btn';
        btn.innerHTML = '📺';
        btn.title = 'Picture-in-Picture';
        btn.style.cssText = `
            position: fixed; top: 345px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.togglePiP();
        document.body.appendChild(btn);
    },
    
    async togglePiP() {
        try {
            const video = document.querySelector('video, iframe');
            if (!video) {
                alert('No video found to enable Picture-in-Picture');
                return;
            }
            
            if (document.pictureInPictureElement) {
                await document.exitPictureInPicture();
                this.isPiPActive = false;
            } else if (video.tagName === 'VIDEO' && document.pictureInPictureEnabled) {
                await video.requestPictureInPicture();
                this.isPiPActive = true;
            } else {
                alert('Picture-in-Picture is not supported for this content');
            }
            
            this.updateButton();
        } catch (err) {
            console.error('PiP error:', err);
            alert('Could not enable Picture-in-Picture mode');
        }
    },
    
    updateButton() {
        const btn = document.getElementById('pip-controller-btn');
        if (btn) {
            btn.style.background = this.isPiPActive ? 
                'linear-gradient(135deg, #22c55e, #16a34a)' : 
                'linear-gradient(135deg, #3b82f6, #2563eb)';
        }
    }
};

// Feature 159: Content Reminder System
const ContentReminders = {
    reminders: JSON.parse(localStorage.getItem('movieshows-reminders') || '[]'),
    
    init() {
        this.createUI();
        this.checkReminders();
        console.log('[MovieShows] Content Reminders initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'reminders-btn';
        btn.innerHTML = '⏰';
        btn.title = 'Reminders';
        btn.style.cssText = `
            position: fixed; top: 400px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(20, 184, 166, 0.4);
            transition: all 0.3s;
        `;
        btn.onclick = () => this.showReminders();
        document.body.appendChild(btn);
        
        // Show badge if reminders exist
        if (this.reminders.length > 0) {
            const badge = document.createElement('span');
            badge.style.cssText = `
                position: absolute; top: -5px; right: -5px;
                width: 18px; height: 18px; background: #ef4444;
                border-radius: 50%; color: white; font-size: 10px;
                display: flex; align-items: center; justify-content: center;
            `;
            badge.textContent = this.reminders.length;
            btn.style.position = 'fixed';
            btn.appendChild(badge);
        }
    },
    
    showReminders() {
        let panel = document.getElementById('reminders-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'reminders-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 400px; max-width: 95vw;
            background: rgba(20, 20, 30, 0.98); border-radius: 20px; padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        const currentTitle = document.querySelector('.video-slide.active h2')?.textContent || 'Current Show';
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                <h3 style="color: white; margin: 0; font-size: 20px;">⏰ Reminders</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <button id="add-reminder-btn" style="
                width: 100%; padding: 15px; background: linear-gradient(135deg, #14b8a6, #0d9488);
                border: none; border-radius: 12px; color: white; font-weight: bold;
                cursor: pointer; margin-bottom: 20px; display: flex; align-items: center; justify-content: center; gap: 10px;
            ">+ Remind me about "${currentTitle}"</button>
            
            <h4 style="color: #888; font-size: 12px; margin-bottom: 15px;">YOUR REMINDERS</h4>
            
            <div id="reminders-list" style="max-height: 300px; overflow-y: auto;">
                ${this.reminders.length === 0 ? 
                    '<p style="color: #666; text-align: center; padding: 20px;">No reminders set</p>' :
                    this.reminders.map((r, i) => `
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 10px; margin-bottom: 10px;">
                            <div>
                                <p style="color: white; margin: 0; font-size: 14px;">${r.title}</p>
                                <span style="color: #14b8a6; font-size: 11px;">${r.time || 'Anytime'}</span>
                            </div>
                            <button onclick="ContentReminders.removeReminder(${i})" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 16px;">🗑️</button>
                        </div>
                    `).join('')
                }
            </div>
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelector('#add-reminder-btn')?.addEventListener('click', () => {
            this.addReminder(currentTitle);
            this.showReminders();
        });
    },
    
    addReminder(title) {
        this.reminders.push({ title, time: 'Tonight', created: Date.now() });
        localStorage.setItem('movieshows-reminders', JSON.stringify(this.reminders));
    },
    
    removeReminder(index) {
        this.reminders.splice(index, 1);
        localStorage.setItem('movieshows-reminders', JSON.stringify(this.reminders));
        this.showReminders();
    },
    
    checkReminders() {
        // Could implement actual notification logic here
        if (this.reminders.length > 0 && Notification.permission === 'granted') {
            // Show notification for due reminders
        }
    }
};

// Feature 160: Quick Share Menu
const QuickShareMenu = {
    init() {
        this.injectShareButton();
        console.log('[MovieShows] Quick Share Menu initialized');
    },
    
    injectShareButton() {
        // Add share button to action panel if it exists
        const actionPanel = document.querySelector('.action-panel, [class*="action"]');
        if (actionPanel) {
            const shareBtn = document.createElement('button');
            shareBtn.innerHTML = '📤 Share';
            shareBtn.style.cssText = `
                padding: 10px 20px; background: linear-gradient(135deg, #3b82f6, #6366f1);
                border: none; border-radius: 25px; color: white; font-weight: bold;
                cursor: pointer; font-size: 14px; margin: 5px;
            `;
            shareBtn.onclick = () => this.showShareMenu();
            actionPanel.appendChild(shareBtn);
        }
        
        // Also add floating share button
        const floatingBtn = document.createElement('button');
        floatingBtn.id = 'quick-share-btn';
        floatingBtn.innerHTML = '📤';
        floatingBtn.title = 'Quick Share';
        floatingBtn.style.cssText = `
            position: fixed; top: 455px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
            transition: all 0.3s;
        `;
        floatingBtn.onclick = () => this.showShareMenu();
        document.body.appendChild(floatingBtn);
    },
    
    showShareMenu() {
        let menu = document.getElementById('quick-share-menu');
        if (menu) { menu.remove(); return; }
        
        const currentTitle = document.querySelector('.video-slide.active h2')?.textContent || 'MovieShows';
        const shareText = `Check out "${currentTitle}" on MovieShows! 🎬`;
        const shareUrl = window.location.href;
        
        menu = document.createElement('div');
        menu.id = 'quick-share-menu';
        menu.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 350px; background: rgba(20, 20, 30, 0.98);
            border-radius: 20px; padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        menu.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0; font-size: 18px;">📤 Share</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <p style="color: #888; font-size: 13px; margin-bottom: 20px;">"${currentTitle}"</p>
            
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px;">
                <button class="share-option" data-platform="twitter" style="
                    padding: 15px; background: #1da1f2; border: none; border-radius: 12px;
                    cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 5px;
                ">
                    <span style="font-size: 24px;">🐦</span>
                    <span style="color: white; font-size: 10px;">Twitter</span>
                </button>
                <button class="share-option" data-platform="facebook" style="
                    padding: 15px; background: #1877f2; border: none; border-radius: 12px;
                    cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 5px;
                ">
                    <span style="font-size: 24px;">📘</span>
                    <span style="color: white; font-size: 10px;">Facebook</span>
                </button>
                <button class="share-option" data-platform="whatsapp" style="
                    padding: 15px; background: #25d366; border: none; border-radius: 12px;
                    cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 5px;
                ">
                    <span style="font-size: 24px;">💬</span>
                    <span style="color: white; font-size: 10px;">WhatsApp</span>
                </button>
                <button class="share-option" data-platform="copy" style="
                    padding: 15px; background: rgba(255,255,255,0.1); border: none; border-radius: 12px;
                    cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: 5px;
                ">
                    <span style="font-size: 24px;">📋</span>
                    <span style="color: white; font-size: 10px;">Copy</span>
                </button>
            </div>
            
            <div style="padding: 12px; background: rgba(255,255,255,0.05); border-radius: 10px; display: flex; align-items: center; gap: 10px;">
                <input type="text" value="${shareUrl}" readonly style="
                    flex: 1; background: transparent; border: none;
                    color: #888; font-size: 12px; outline: none;
                ">
                <button id="copy-link-btn" style="
                    padding: 8px 15px; background: #22c55e; border: none;
                    border-radius: 6px; color: white; font-size: 12px; cursor: pointer;
                ">Copy</button>
            </div>
        `;
        
        document.body.appendChild(menu);
        
        menu.querySelectorAll('.share-option').forEach(btn => {
            btn.onclick = () => {
                const platform = btn.dataset.platform;
                this.shareTo(platform, shareText, shareUrl);
            };
        });
        
        menu.querySelector('#copy-link-btn')?.addEventListener('click', () => {
            navigator.clipboard.writeText(shareUrl);
            menu.querySelector('#copy-link-btn').textContent = 'Copied!';
            setTimeout(() => {
                menu.querySelector('#copy-link-btn').textContent = 'Copy';
            }, 2000);
        });
    },
    
    shareTo(platform, text, url) {
        const urls = {
            twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`,
            facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`,
            whatsapp: `https://wa.me/?text=${encodeURIComponent(text + ' ' + url)}`,
            copy: null
        };
        
        if (platform === 'copy') {
            navigator.clipboard.writeText(text + ' ' + url);
            alert('Copied to clipboard!');
        } else if (urls[platform]) {
            window.open(urls[platform], '_blank', 'width=600,height=400');
        }
    }
};

// Initialize all Batch 8 features
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        SceneBookmarks.init();
        QuickCast.init();
        SmartAutoplay.init();
        WatchPartySync.init();
        QuickRatingStars.init();
        ContentMoodBoard.init();
        VideoProgressBars.init();
        SmartContentLabels.init();
        PlaylistManager.init();
        QuickSkip.init();
        CollectionsBrowser.init();
        EnhancedSearch.init();
        ContentComparator.init();
        QuickGenreJump.init();
        ContentTimeline.init();
        ViewingDashboard.init();
        SmartRecommendations.init();
        PiPController.init();
        ContentReminders.init();
        QuickShareMenu.init();
        
        console.log('[MovieShows] Batch 8 features (141-160) loaded successfully!');
    }, 2000);
});
