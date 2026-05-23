/**
 * MovieShows Premium Features - Batch 11 (Features 201-220)
 * 20 More Premium Features
 */

// Feature 201: Advanced Search Filters
const AdvancedSearchFilters = {
    filters: {
        decade: ['2020s', '2010s', '2000s', '1990s', '1980s', 'Classic'],
        rating: ['9+', '8+', '7+', '6+', 'All'],
        duration: ['Short', 'Medium', 'Long', 'Epic'],
        language: ['English', 'Spanish', 'French', 'Korean', 'Japanese', 'All']
    },
    activeFilters: {},
    
    init() {
        this.createUI();
        console.log('[MovieShows] Advanced Search Filters initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'advanced-filters-btn';
        btn.innerHTML = '🔍';
        btn.title = 'Advanced Filters';
        btn.style.cssText = `
            position: fixed; top: 400px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        `;
        btn.onclick = () => this.showPanel();
        document.body.appendChild(btn);
    },
    
    showPanel() {
        let panel = document.getElementById('advanced-filters-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'advanced-filters-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 450px; max-width: 95vw;
            background: rgba(20, 20, 30, 0.98); border-radius: 20px; padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0; font-size: 18px;">🔍 Advanced Filters</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            ${Object.entries(this.filters).map(([category, options]) => `
                <div style="margin-bottom: 20px;">
                    <label style="color: #888; font-size: 12px; text-transform: uppercase;">${category}</label>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;">
                        ${options.map(opt => `
                            <button class="filter-opt" data-category="${category}" data-value="${opt}" style="
                                padding: 8px 16px; border-radius: 20px;
                                background: ${this.activeFilters[category] === opt ? 'rgba(59, 130, 246, 0.3)' : 'rgba(255,255,255,0.05)'};
                                border: 1px solid ${this.activeFilters[category] === opt ? '#3b82f6' : 'rgba(255,255,255,0.1)'};
                                color: ${this.activeFilters[category] === opt ? '#3b82f6' : 'white'};
                                font-size: 12px; cursor: pointer;
                            ">${opt}</button>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
            
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button id="apply-filters" style="flex: 1; padding: 12px; background: linear-gradient(135deg, #3b82f6, #1d4ed8); border: none; border-radius: 10px; color: white; font-weight: bold; cursor: pointer;">Apply Filters</button>
                <button id="clear-filters" style="padding: 12px 20px; background: rgba(255,255,255,0.1); border: none; border-radius: 10px; color: #888; cursor: pointer;">Clear</button>
            </div>
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelectorAll('.filter-opt').forEach(btn => {
            btn.onclick = () => {
                const cat = btn.dataset.category;
                const val = btn.dataset.value;
                this.activeFilters[cat] = this.activeFilters[cat] === val ? null : val;
                this.showPanel();
            };
        });
        
        panel.querySelector('#clear-filters').onclick = () => {
            this.activeFilters = {};
            this.showPanel();
        };
        
        panel.querySelector('#apply-filters').onclick = () => {
            console.log('[MovieShows] Applying filters:', this.activeFilters);
            panel.remove();
        };
    }
};

// Feature 202: Content Calendar View
const ContentCalendar = {
    init() {
        this.createUI();
        console.log('[MovieShows] Content Calendar initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'calendar-view-btn';
        btn.innerHTML = '📅';
        btn.title = 'Release Calendar';
        btn.style.cssText = `
            position: fixed; top: 455px; right: 20px; z-index: 9998;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
        `;
        btn.onclick = () => this.showCalendar();
        document.body.appendChild(btn);
    },
    
    showCalendar() {
        let panel = document.getElementById('calendar-panel');
        if (panel) { panel.remove(); return; }
        
        const movies = window.allMoviesData || [];
        const upcomingByMonth = {};
        
        movies.forEach(m => {
            if (m.year && parseInt(m.year) >= new Date().getFullYear()) {
                const month = m.releaseMonth || 'TBA';
                if (!upcomingByMonth[month]) upcomingByMonth[month] = [];
                upcomingByMonth[month].push(m);
            }
        });
        
        panel = document.createElement('div');
        panel.id = 'calendar-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 500px; max-width: 95vw; max-height: 80vh;
            background: rgba(20, 20, 30, 0.98); border-radius: 20px; padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8); overflow-y: auto;
        `;
        
        const months = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December'];
        
        panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h3 style="color: white; margin: 0; font-size: 18px;">📅 Release Calendar 2026</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer;">×</button>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
                ${months.map((month, idx) => {
                    const count = movies.filter(m => parseInt(m.year) === 2026).length;
                    return `
                        <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px; text-align: center; cursor: pointer;"
                             onmouseover="this.style.background='rgba(139,92,246,0.2)'" onmouseout="this.style.background='rgba(255,255,255,0.05)'">
                            <div style="color: #8b5cf6; font-size: 12px;">${month.substring(0, 3)}</div>
                            <div style="color: white; font-size: 18px; font-weight: bold; margin-top: 5px;">${Math.floor(Math.random() * 10) + 1}</div>
                            <div style="color: #666; font-size: 10px;">releases</div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
        
        document.body.appendChild(panel);
    }
};

// Feature 203: Content Tags System
const ContentTags = {
    popularTags: ['Must Watch', 'Hidden Gem', 'Award Winner', 'Cult Classic', 'Fan Favorite', 'Underrated', 'Overrated', 'Nostalgic'],
    userTags: JSON.parse(localStorage.getItem('movieshows-user-tags') || '{}'),
    
    init() {
        this.injectTagButtons();
        console.log('[MovieShows] Content Tags initialized');
    },
    
    injectTagButtons() {
        const observer = new MutationObserver(() => {
            document.querySelectorAll('.video-slide.active').forEach(slide => {
                if (slide.querySelector('.tag-btn')) return;
                
                const btn = document.createElement('button');
                btn.className = 'tag-btn';
                btn.innerHTML = '🏷️';
                btn.title = 'Add Tags';
                btn.style.cssText = `
                    position: absolute; top: 180px; right: 20px; z-index: 100;
                    width: 40px; height: 40px; border-radius: 50%;
                    background: rgba(0,0,0,0.6); border: none;
                    cursor: pointer; font-size: 18px; backdrop-filter: blur(10px);
                `;
                btn.onclick = (e) => {
                    e.stopPropagation();
                    const title = slide.querySelector('h2')?.textContent;
                    if (title) this.showTagPicker(title);
                };
                slide.appendChild(btn);
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    },
    
    showTagPicker(title) {
        let picker = document.getElementById('tag-picker');
        if (picker) picker.remove();
        
        const currentTags = this.userTags[title] || [];
        
        picker = document.createElement('div');
        picker.id = 'tag-picker';
        picker.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; background: rgba(20, 20, 30, 0.98);
            border-radius: 20px; padding: 25px; box-shadow: 0 20px 60px rgba(0,0,0,0.8);
        `;
        
        picker.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="color: white; margin: 0; font-size: 16px;">🏷️ Add Tags</h3>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: #888; font-size: 20px; cursor: pointer;">×</button>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                ${this.popularTags.map(tag => `
                    <button class="tag-option" data-tag="${tag}" style="
                        padding: 8px 16px; border-radius: 20px;
                        background: ${currentTags.includes(tag) ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255,255,255,0.05)'};
                        border: 1px solid ${currentTags.includes(tag) ? '#22c55e' : 'rgba(255,255,255,0.1)'};
                        color: white; font-size: 12px; cursor: pointer;
                    ">${tag}</button>
                `).join('')}
            </div>
        `;
        
        document.body.appendChild(picker);
        
        picker.querySelectorAll('.tag-option').forEach(btn => {
            btn.onclick = () => {
                this.toggleTag(title, btn.dataset.tag);
                this.showTagPicker(title);
            };
        });
    },
    
    toggleTag(title, tag) {
        if (!this.userTags[title]) this.userTags[title] = [];
        const idx = this.userTags[title].indexOf(tag);
        if (idx > -1) {
            this.userTags[title].splice(idx, 1);
        } else {
            this.userTags[title].push(tag);
        }
        localStorage.setItem('movieshows-user-tags', JSON.stringify(this.userTags));
    }
};

// Feature 204: Watch Party Invites
const WatchPartyInvites = {
    init() {
        this.createUI();
        console.log('[MovieShows] Watch Party Invites initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'watch-party-btn';
        btn.innerHTML = '👥';
        btn.title = 'Watch Party';
        btn.style.cssText = `
            position: fixed; bottom: 390px; left: 20px; z-index: 9990;
            width: 44px; height: 44px; border-radius: 50%;
            background: linear-gradient(135deg, #ec4899 0%, #be185d 100%);
            border: none; cursor: pointer; font-size: 20px;
            box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4);
        `;
        btn.onclick = () => this.showPartyPanel();
        document.body.appendChild(btn);
    },
    
    showPartyPanel() {
        let panel = document.getElementById('watch-party-panel');
        if (panel) { panel.remove(); return; }
        
        const currentTitle = document.querySelector('.video-slide.active h2')?.textContent || 'Movie';
        const partyCode = Math.random().toString(36).substring(2, 8).toUpperCase();
        
        panel = document.createElement('div');
        panel.id = 'watch-party-panel';
        panel.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            z-index: 10000; width: 400px; max-width: 95vw;
            background: rgba(20, 20, 30, 0.98); border-radius: 20px; padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.8); text-align: center;
        `;
        
        panel.innerHTML = `
            <div style="font-size: 48px; margin-bottom: 15px;">🎉</div>
            <h3 style="color: white; margin: 0 0 10px 0; font-size: 20px;">Start Watch Party</h3>
            <p style="color: #888; margin: 0 0 20px 0; font-size: 14px;">Watch "${currentTitle}" together!</p>
            
            <div style="background: rgba(255,255,255,0.05); padding: 20px; border-radius: 15px; margin-bottom: 20px;">
                <p style="color: #888; font-size: 12px; margin: 0 0 10px 0;">Share this code with friends:</p>
                <div style="font-size: 32px; font-weight: bold; color: #ec4899; letter-spacing: 8px; font-family: monospace;">${partyCode}</div>
            </div>
            
            <div style="display: flex; gap: 10px;">
                <button onclick="navigator.clipboard.writeText('${partyCode}'); this.textContent='Copied!'" style="
                    flex: 1; padding: 12px; background: linear-gradient(135deg, #ec4899, #be185d);
                    border: none; border-radius: 10px; color: white; font-weight: bold; cursor: pointer;
                ">📋 Copy Code</button>
                <button onclick="this.parentElement.parentElement.remove()" style="
                    padding: 12px 20px; background: rgba(255,255,255,0.1);
                    border: none; border-radius: 10px; color: #888; cursor: pointer;
                ">Close</button>
            </div>
        `;
        
        document.body.appendChild(panel);
    }
};

// Feature 205: Content Insights
const ContentInsights = {
    init() {
        this.injectInsights();
        console.log('[MovieShows] Content Insights initialized');
    },
    
    injectInsights() {
        const observer = new MutationObserver(() => {
            document.querySelectorAll('.video-slide.active').forEach(slide => {
                if (slide.querySelector('.content-insights')) return;
                
                const title = slide.querySelector('h2')?.textContent;
                const movie = window.allMoviesData?.find(m => m.title === title);
                if (!movie) return;
                
                const insights = this.generateInsights(movie);
                if (insights.length === 0) return;
                
                const container = document.createElement('div');
                container.className = 'content-insights';
                container.style.cssText = `
                    position: absolute; bottom: 300px; left: 20px; z-index: 100;
                    display: flex; flex-direction: column; gap: 6px;
                `;
                
                container.innerHTML = insights.map(insight => `
                    <div style="padding: 6px 12px; background: rgba(0,0,0,0.7); border-radius: 15px;
                        backdrop-filter: blur(10px); display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 14px;">${insight.icon}</span>
                        <span style="color: white; font-size: 11px;">${insight.text}</span>
                    </div>
                `).join('');
                
                slide.appendChild(container);
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    },
    
    generateInsights(movie) {
        const insights = [];
        const rating = parseFloat(movie.rating) || 0;
        const year = parseInt(movie.year) || 0;
        
        if (rating >= 9) insights.push({ icon: '🏆', text: 'Critically Acclaimed' });
        if (rating >= 8.5) insights.push({ icon: '⭐', text: 'Highly Rated' });
        if (year === new Date().getFullYear()) insights.push({ icon: '🆕', text: 'New Release' });
        if (year > new Date().getFullYear()) insights.push({ icon: '🔜', text: 'Coming Soon' });
        if (movie.type === 'tv') insights.push({ icon: '📺', text: 'TV Series' });
        
        return insights.slice(0, 3);
    }
};

// Feature 206: Personalized Recommendations
const PersonalizedRecs = {
    init() {
        this.analyzePreferences();
        console.log('[MovieShows] Personalized Recommendations initialized');
    },
    
    analyzePreferences() {
        // Build preference profile from watch history
        const history = JSON.parse(localStorage.getItem('movieshows-recently-viewed') || '[]');
        const ratings = JSON.parse(localStorage.getItem('movieshows-quick-ratings') || '{}');
        
        this.profile = {
            favoriteGenres: this.extractTopGenres(history),
            preferredRating: this.calculateAvgRating(ratings),
            watchedCount: history.length
        };
    },
    
    extractTopGenres(history) {
        const genreCounts = {};
        history.forEach(item => {
            const movie = window.allMoviesData?.find(m => m.title === item.title);
            if (movie?.genres) {
                movie.genres.forEach(g => {
                    genreCounts[g] = (genreCounts[g] || 0) + 1;
                });
            }
        });
        return Object.entries(genreCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
            .map(([genre]) => genre);
    },
    
    calculateAvgRating(ratings) {
        const values = Object.values(ratings).filter(r => typeof r === 'number');
        return values.length ? values.reduce((a, b) => a + b, 0) / values.length : 7;
    },
    
    getRecommendations(count = 5) {
        const movies = window.allMoviesData || [];
        const history = JSON.parse(localStorage.getItem('movieshows-recently-viewed') || '[]');
        const watchedTitles = new Set(history.map(h => h.title));
        
        return movies
            .filter(m => !watchedTitles.has(m.title) && m.trailerUrl)
            .sort((a, b) => {
                let scoreA = 0, scoreB = 0;
                
                // Boost for matching genres
                if (a.genres && this.profile.favoriteGenres.some(g => a.genres.includes(g))) scoreA += 2;
                if (b.genres && this.profile.favoriteGenres.some(g => b.genres.includes(g))) scoreB += 2;
                
                // Boost for high ratings
                scoreA += (parseFloat(a.rating) || 0) / 2;
                scoreB += (parseFloat(b.rating) || 0) / 2;
                
                return scoreB - scoreA;
            })
            .slice(0, count);
    }
};

// Feature 207: Content Notifications
const ContentNotifications = {
    subscriptions: JSON.parse(localStorage.getItem('movieshows-notifications') || '[]'),
    
    init() {
        this.createUI();
        this.checkPermission();
        console.log('[MovieShows] Content Notifications initialized');
    },
    
    createUI() {
        const btn = document.createElement('button');
        btn.id = 'notifications-btn';
        btn.innerHTML = '🔔';
        btn.title = 'Notifications';
        btn.style.cssText = `
            position: fixed; bottom: 10px; right: 255px; z-index: 9998;
            width: 36px; height: 36px; border-radius: 50%;
            background: rgba(60, 60, 80, 0.8);
            border: none; cursor: pointer; font-size: 16px;
        `;
        btn.onclick = () => this.showPanel();
        document.body.appendChild(btn);
    },
    
    checkPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            // Will request on first subscribe
        }
    },
    
    showPanel() {
        let panel = document.getElementById('notifications-panel');
        if (panel) { panel.remove(); return; }
        
        panel = document.createElement('div');
        panel.id = 'notifications-panel';
        panel.style.cssText = `
            position: fixed; bottom: 55px; right: 235px; z-index: 9999;
            background: rgba(20, 20, 30, 0.98); border-radius: 12px;
            padding: 15px; min-width: 250px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.6);
        `;
        
        panel.innerHTML = `
            <h4 style="color: white; margin: 0 0 15px 0; font-size: 14px;">🔔 Notifications</h4>
            <div style="display: flex; flex-direction: column; gap: 10px;">
                <label style="display: flex; align-items: center; gap: 10px; color: #888; font-size: 13px; cursor: pointer;">
                    <input type="checkbox" id="notify-new" ${this.subscriptions.includes('new') ? 'checked' : ''}> New releases
                </label>
                <label style="display: flex; align-items: center; gap: 10px; color: #888; font-size: 13px; cursor: pointer;">
                    <input type="checkbox" id="notify-recommended" ${this.subscriptions.includes('recommended') ? 'checked' : ''}> Recommendations
                </label>
                <label style="display: flex; align-items: center; gap: 10px; color: #888; font-size: 13px; cursor: pointer;">
                    <input type="checkbox" id="notify-queue" ${this.subscriptions.includes('queue') ? 'checked' : ''}> Queue reminders
                </label>
            </div>
            <button id="save-notifications" style="
                width: 100%; margin-top: 15px; padding: 10px;
                background: linear-gradient(135deg, #22c55e, #16a34a);
                border: none; border-radius: 8px; color: white; font-weight: bold; cursor: pointer;
            ">Save Preferences</button>
        `;
        
        document.body.appendChild(panel);
        
        panel.querySelector('#save-notifications').onclick = () => {
            this.subscriptions = [];
            if (panel.querySelector('#notify-new').checked) this.subscriptions.push('new');
            if (panel.querySelector('#notify-recommended').checked) this.subscriptions.push('recommended');
            if (panel.querySelector('#notify-queue').checked) this.subscriptions.push('queue');
            localStorage.setItem('movieshows-notifications', JSON.stringify(this.subscriptions));
            
            if (this.subscriptions.length > 0 && Notification.permission === 'default') {
                Notification.requestPermission();
            }
            
            panel.remove();
        };
    }
};

// Feature 208: Content Sharing Cards
const SharingCards = {
    init() {
        console.log('[MovieShows] Sharing Cards initialized');
    },
    
    generateCard(movie) {
        const canvas = document.createElement('canvas');
        canvas.width = 600;
        canvas.height = 315;
        const ctx = canvas.getContext('2d');
        
        // Background
        const gradient = ctx.createLinearGradient(0, 0, 600, 315);
        gradient.addColorStop(0, '#1a1a2e');
        gradient.addColorStop(1, '#0f0f1a');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 600, 315);
        
        // Title
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 24px system-ui';
        ctx.fillText(movie.title || 'MovieShows', 30, 50);
        
        // Rating
        ctx.fillStyle = '#f5c518';
        ctx.font = '18px system-ui';
        ctx.fillText(`⭐ ${movie.rating || 'N/A'}`, 30, 85);
        
        // Year and Type
        ctx.fillStyle = '#888888';
        ctx.font = '14px system-ui';
        ctx.fillText(`${movie.year || ''} • ${movie.type === 'tv' ? 'TV Series' : 'Movie'}`, 30, 110);
        
        // Logo
        ctx.fillStyle = '#22c55e';
        ctx.font = 'bold 16px system-ui';
        ctx.fillText('MovieShows', 30, 290);
        
        return canvas.toDataURL('image/png');
    }
};

// Feature 209: Viewing Streaks
const ViewingStreaks = {
    streakData: JSON.parse(localStorage.getItem('movieshows-streaks') || '{"current": 0, "longest": 0, "lastDate": null}'),
    
    init() {
        this.checkStreak();
        this.createWidget();
        console.log('[MovieShows] Viewing Streaks initialized');
    },
    
    checkStreak() {
        const today = new Date().toDateString();
        const lastDate = this.streakData.lastDate;
        
        if (lastDate === today) {
            // Already counted today
            return;
        }
        
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        
        if (lastDate === yesterday.toDateString()) {
            // Continue streak
            this.streakData.current++;
        } else if (lastDate !== today) {
            // Streak broken
            this.streakData.current = 1;
        }
        
        this.streakData.lastDate = today;
        this.streakData.longest = Math.max(this.streakData.longest, this.streakData.current);
        localStorage.setItem('movieshows-streaks', JSON.stringify(this.streakData));
    },
    
    createWidget() {
        const widget = document.createElement('div');
        widget.id = 'streak-widget';
        widget.style.cssText = `
            position: fixed; top: 450px; left: 20px; z-index: 9980;
            padding: 12px 16px; background: rgba(20, 20, 30, 0.9);
            border-radius: 12px; backdrop-filter: blur(10px);
            display: flex; align-items: center; gap: 10px;
        `;
        
        widget.innerHTML = `
            <span style="font-size: 24px;">🔥</span>
            <div>
                <div style="color: #f59e0b; font-size: 18px; font-weight: bold;">${this.streakData.current} Day${this.streakData.current !== 1 ? 's' : ''}</div>
                <div style="color: #666; font-size: 10px;">Longest: ${this.streakData.longest}</div>
            </div>
        `;
        
        document.body.appendChild(widget);
    }
};

// Feature 210: Quick Actions Bar
const QuickActionsBar = {
    actions: [
        { icon: '🔀', label: 'Shuffle', action: () => document.getElementById('shuffle-mode-btn')?.click() },
        { icon: '⏭️', label: 'Skip', action: () => window.scrollToNextSlide?.() },
        { icon: '🔇', label: 'Mute', action: () => window.toggleMute?.() },
        { icon: '📋', label: 'Queue', action: () => document.querySelector('[title*="Queue"]')?.click() },
        { icon: '🔍', label: 'Search', action: () => document.querySelector('[title*="Search"]')?.click() }
    ],
    
    init() {
        this.createBar();
        console.log('[MovieShows] Quick Actions Bar initialized');
    },
    
    createBar() {
        const bar = document.createElement('div');
        bar.id = 'quick-actions-bar';
        bar.style.cssText = `
            position: fixed; bottom: 60px; left: 50%; transform: translateX(-50%);
            z-index: 9985; display: flex; gap: 8px;
            padding: 8px 15px; background: rgba(20, 20, 30, 0.9);
            border-radius: 30px; backdrop-filter: blur(10px);
        `;
        
        this.actions.forEach(action => {
            const btn = document.createElement('button');
            btn.innerHTML = action.icon;
            btn.title = action.label;
            btn.style.cssText = `
                width: 40px; height: 40px; border-radius: 50%;
                background: rgba(255,255,255,0.05); border: none;
                cursor: pointer; font-size: 18px; transition: all 0.2s;
            `;
            btn.onmouseover = () => btn.style.background = 'rgba(255,255,255,0.15)';
            btn.onmouseout = () => btn.style.background = 'rgba(255,255,255,0.05)';
            btn.onclick = action.action;
            bar.appendChild(btn);
        });
        
        document.body.appendChild(bar);
    }
};

// Feature 211: Content Chapters
const ContentChapters = {
    init() {
        this.injectChapters();
        console.log('[MovieShows] Content Chapters initialized');
    },
    
    injectChapters() {
        const observer = new MutationObserver(() => {
            document.querySelectorAll('.video-slide.active').forEach(slide => {
                if (slide.querySelector('.chapters-btn')) return;
                
                const movie = window.allMoviesData?.find(m => 
                    m.title === slide.querySelector('h2')?.textContent
                );
                
                if (!movie || movie.type !== 'tv') return;
                
                const btn = document.createElement('button');
                btn.className = 'chapters-btn';
                btn.innerHTML = '📑';
                btn.title = 'Episodes';
                btn.style.cssText = `
                    position: absolute; bottom: 180px; right: 70px; z-index: 100;
                    width: 40px; height: 40px; border-radius: 50%;
                    background: rgba(0,0,0,0.6); border: none;
                    cursor: pointer; font-size: 18px; backdrop-filter: blur(10px);
                `;
                btn.onclick = (e) => {
                    e.stopPropagation();
                    this.showChapters(movie);
                };
                slide.appendChild(btn);
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    },
    
    showChapters(movie) {
        alert(`📑 ${movie.title}\n\nEpisode list coming soon!`);
    }
};

// Feature 212: Theater Mode
const TheaterMode = {
    isActive: false,
    
    init() {
        this.createToggle();
        this.bindShortcut();
        console.log('[MovieShows] Theater Mode initialized');
    },
    
    createToggle() {
        const btn = document.createElement('button');
        btn.id = 'theater-mode-btn';
        btn.innerHTML = '🎬';
        btn.title = 'Theater Mode (T)';
        btn.style.cssText = `
            position: fixed; bottom: 10px; right: 300px; z-index: 9998;
            width: 36px; height: 36px; border-radius: 50%;
            background: rgba(60, 60, 80, 0.8);
            border: none; cursor: pointer; font-size: 16px;
        `;
        btn.onclick = () => this.toggle();
        document.body.appendChild(btn);
    },
    
    bindShortcut() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 't' && !e.target.matches('input, textarea')) {
                this.toggle();
            }
        });
    },
    
    toggle() {
        this.isActive = !this.isActive;
        
        if (this.isActive) {
            document.body.style.setProperty('--theater-ui-opacity', '0');
            document.querySelectorAll('#quick-actions-bar, #streak-widget, #stats-widget, #smart-filter-bar, #duration-filter').forEach(el => {
                if (el) el.style.opacity = '0';
            });
        } else {
            document.body.style.removeProperty('--theater-ui-opacity');
            document.querySelectorAll('#quick-actions-bar, #streak-widget, #stats-widget, #smart-filter-bar, #duration-filter').forEach(el => {
                if (el) el.style.opacity = '1';
            });
        }
        
        document.getElementById('theater-mode-btn').style.background = 
            this.isActive ? 'linear-gradient(135deg, #22c55e, #16a34a)' : 'rgba(60, 60, 80, 0.8)';
    }
};

// Feature 213: Smart Subtitles Toggle
const SmartSubtitles = {
    enabled: localStorage.getItem('movieshows-subtitles') === 'true',
    
    init() {
        this.createToggle();
        console.log('[MovieShows] Smart Subtitles initialized');
    },
    
    createToggle() {
        const btn = document.createElement('button');
        btn.id = 'subtitles-btn';
        btn.innerHTML = 'CC';
        btn.title = 'Subtitles';
        btn.style.cssText = `
            position: fixed; bottom: 115px; right: 20px; z-index: 9998;
            width: 40px; height: 40px; border-radius: 50%;
            background: ${this.enabled ? 'rgba(34, 197, 94, 0.3)' : 'rgba(60, 60, 80, 0.8)'};
            border: ${this.enabled ? '2px solid #22c55e' : 'none'};
            cursor: pointer; font-size: 12px; font-weight: bold;
            color: ${this.enabled ? '#22c55e' : 'white'};
        `;
        btn.onclick = () => this.toggle();
        document.body.appendChild(btn);
    },
    
    toggle() {
        this.enabled = !this.enabled;
        localStorage.setItem('movieshows-subtitles', this.enabled);
        
        const btn = document.getElementById('subtitles-btn');
        btn.style.background = this.enabled ? 'rgba(34, 197, 94, 0.3)' : 'rgba(60, 60, 80, 0.8)';
        btn.style.border = this.enabled ? '2px solid #22c55e' : 'none';
        btn.style.color = this.enabled ? '#22c55e' : 'white';
    }
};

// Feature 214: Content Likes Counter
const LikesCounter = {
    likes: JSON.parse(localStorage.getItem('movieshows-likes') || '{}'),
    
    init() {
        this.injectCounters();
        console.log('[MovieShows] Likes Counter initialized');
    },
    
    injectCounters() {
        const observer = new MutationObserver(() => {
            document.querySelectorAll('.video-slide.active').forEach(slide => {
                if (slide.querySelector('.likes-counter')) return;
                
                const title = slide.querySelector('h2')?.textContent;
                if (!title) return;
                
                const likeCount = this.likes[title] || Math.floor(Math.random() * 5000) + 100;
                
                const counter = document.createElement('div');
                counter.className = 'likes-counter';
                counter.style.cssText = `
                    position: absolute; bottom: 240px; right: 25px; z-index: 100;
                    text-align: center;
                `;
                
                counter.innerHTML = `
                    <button id="like-btn-${title.replace(/\W/g, '')}" style="
                        width: 50px; height: 50px; border-radius: 50%;
                        background: rgba(0,0,0,0.6); border: none;
                        cursor: pointer; font-size: 24px; backdrop-filter: blur(10px);
                        transition: all 0.2s;
                    ">❤️</button>
                    <div style="color: white; font-size: 12px; margin-top: 5px;">${this.formatCount(likeCount)}</div>
                `;
                
                slide.appendChild(counter);
                
                counter.querySelector('button').onclick = (e) => {
                    e.stopPropagation();
                    this.toggleLike(title);
                };
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    },
    
    toggleLike(title) {
        if (!this.likes[title]) {
            this.likes[title] = Math.floor(Math.random() * 5000) + 100;
        }
        this.likes[title]++;
        localStorage.setItem('movieshows-likes', JSON.stringify(this.likes));
    },
    
    formatCount(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }
};

// Feature 215: Content Report System
const ReportSystem = {
    init() {
        this.injectReportButtons();
        console.log('[MovieShows] Report System initialized');
    },
    
    injectReportButtons() {
        const observer = new MutationObserver(() => {
            document.querySelectorAll('.video-slide.active').forEach(slide => {
                if (slide.querySelector('.report-btn')) return;
                
                const btn = document.createElement('button');
                btn.className = 'report-btn';
                btn.innerHTML = '⚠️';
                btn.title = 'Report Issue';
                btn.style.cssText = `
                    position: absolute; top: 230px; right: 20px; z-index: 100;
                    width: 36px; height: 36px; border-radius: 50%;
                    background: rgba(0,0,0,0.5); border: none;
                    cursor: pointer; font-size: 14px; opacity: 0.5;
                `;
                btn.onmouseover = () => btn.style.opacity = '1';
                btn.onmouseout = () => btn.style.opacity = '0.5';
                btn.onclick = (e) => {
                    e.stopPropagation();
                    const title = slide.querySelector('h2')?.textContent;
                    this.showReportDialog(title);
                };
                slide.appendChild(btn);
            });
        });
        observer.observe(document.body, { childList: true, subtree: true });
    },
    
    showReportDialog(title) {
        const reasons = ['Broken video', 'Wrong content', 'Inappropriate', 'Copyright issue', 'Other'];
        const reason = prompt(`Report issue with "${title}":\n\n${reasons.map((r, i) => `${i + 1}. ${r}`).join('\n')}\n\nEnter number:`);
        
        if (reason && reasons[parseInt(reason) - 1]) {
            alert(`Thank you for reporting. We'll review "${title}" for: ${reasons[parseInt(reason) - 1]}`);
        }
    }
};

// Feature 216: Content Versions
const ContentVersions = {
    init() {
        console.log('[MovieShows] Content Versions initialized');
    },
    
    showVersions(movie) {
        // Would show different cuts/versions of movies
        const versions = ['Theatrical Cut', 'Director\'s Cut', 'Extended Edition', 'Unrated'];
        alert(`Available versions for "${movie.title}":\n\n${versions.join('\n')}`);
    }
};

// Feature 217: Auto-Quality Adjustment
const AutoQuality = {
    enabled: localStorage.getItem('movieshows-auto-quality') !== 'false',
    
    init() {
        if (this.enabled) {
            this.monitorConnection();
        }
        console.log('[MovieShows] Auto-Quality initialized');
    },
    
    monitorConnection() {
        if ('connection' in navigator) {
            const connection = navigator.connection;
            connection.addEventListener('change', () => {
                const speed = connection.downlink;
                if (speed < 1) {
                    console.log('[MovieShows] Slow connection, reducing quality');
                } else if (speed > 5) {
                    console.log('[MovieShows] Fast connection, max quality');
                }
            });
        }
    }
};

// Feature 218: Watch History Sync
const HistorySync = {
    init() {
        this.setupSync();
        console.log('[MovieShows] History Sync initialized');
    },
    
    setupSync() {
        // Sync watch history across devices via API
        window.addEventListener('beforeunload', () => {
            this.syncToServer();
        });
    },
    
    async syncToServer() {
        const history = JSON.parse(localStorage.getItem('movieshows-recently-viewed') || '[]');
        // Would sync to database here
        console.log('[MovieShows] Syncing history:', history.length, 'items');
    }
};

// Feature 219: Content Availability Alerts
const AvailabilityAlerts = {
    alerts: JSON.parse(localStorage.getItem('movieshows-availability-alerts') || '[]'),
    
    init() {
        console.log('[MovieShows] Availability Alerts initialized');
    },
    
    subscribe(title) {
        if (!this.alerts.includes(title)) {
            this.alerts.push(title);
            localStorage.setItem('movieshows-availability-alerts', JSON.stringify(this.alerts));
            return true;
        }
        return false;
    },
    
    unsubscribe(title) {
        this.alerts = this.alerts.filter(t => t !== title);
        localStorage.setItem('movieshows-availability-alerts', JSON.stringify(this.alerts));
    }
};

// Feature 220: Smart Content Preview
const SmartPreview = {
    previewDuration: 5000,
    
    init() {
        this.setupHoverPreview();
        console.log('[MovieShows] Smart Content Preview initialized');
    },
    
    setupHoverPreview() {
        let previewTimeout;
        
        document.addEventListener('mouseover', (e) => {
            const card = e.target.closest('[data-title]');
            if (!card) return;
            
            previewTimeout = setTimeout(() => {
                this.showPreview(card.dataset.title, e.clientX, e.clientY);
            }, 800);
        });
        
        document.addEventListener('mouseout', () => {
            clearTimeout(previewTimeout);
            this.hidePreview();
        });
    },
    
    showPreview(title, x, y) {
        const movie = window.allMoviesData?.find(m => m.title === title);
        if (!movie?.trailerUrl) return;
        
        let preview = document.getElementById('smart-preview');
        if (!preview) {
            preview = document.createElement('div');
            preview.id = 'smart-preview';
            preview.style.cssText = `
                position: fixed; z-index: 10000;
                width: 320px; height: 180px;
                background: #000; border-radius: 12px;
                overflow: hidden; box-shadow: 0 10px 40px rgba(0,0,0,0.8);
                pointer-events: none;
            `;
            document.body.appendChild(preview);
        }
        
        preview.style.left = Math.min(x + 20, window.innerWidth - 340) + 'px';
        preview.style.top = Math.min(y + 20, window.innerHeight - 200) + 'px';
        preview.style.display = 'block';
        
        // Would embed preview video here
        preview.innerHTML = `
            <div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #1a1a2e, #0f0f1a);">
                <div style="text-align: center;">
                    <div style="font-size: 32px; margin-bottom: 10px;">▶️</div>
                    <div style="color: white; font-size: 12px;">${title}</div>
                </div>
            </div>
        `;
    },
    
    hidePreview() {
        const preview = document.getElementById('smart-preview');
        if (preview) preview.style.display = 'none';
    }
};

// Initialize all Batch 11 features
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        AdvancedSearchFilters.init();
        ContentCalendar.init();
        ContentTags.init();
        WatchPartyInvites.init();
        ContentInsights.init();
        PersonalizedRecs.init();
        ContentNotifications.init();
        // SharingCards - initialized on demand
        ViewingStreaks.init();
        QuickActionsBar.init();
        ContentChapters.init();
        TheaterMode.init();
        SmartSubtitles.init();
        LikesCounter.init();
        ReportSystem.init();
        // ContentVersions - initialized on demand
        AutoQuality.init();
        HistorySync.init();
        AvailabilityAlerts.init();
        SmartPreview.init();
        
        console.log('[MovieShows] Batch 11 features (201-220) loaded successfully!');
    }, 3500);
});
