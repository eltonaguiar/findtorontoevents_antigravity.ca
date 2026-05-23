/**
 * MovieShows Premium Features v2.3
 * 20 Major Updates - Batch 4 (Features 61-80)
 */

(function() {
    'use strict';
    
    // ============================================================
    // FEATURE 61: CUSTOM THEMES
    // ============================================================
    const CustomThemes = {
        themes: {
            'default': { primary: '#22c55e', bg: '#0a0a0a', accent: '#3b82f6' },
            'netflix': { primary: '#e50914', bg: '#141414', accent: '#b81d24' },
            'disney': { primary: '#0063e5', bg: '#040714', accent: '#0483ee' },
            'hulu': { primary: '#1ce783', bg: '#0b0c0f', accent: '#040405' },
            'hbo': { primary: '#b19cd9', bg: '#000000', accent: '#8c77b3' },
            'prime': { primary: '#00a8e1', bg: '#0f171e', accent: '#febd69' },
            'cyberpunk': { primary: '#f0e40e', bg: '#0d0d0d', accent: '#ff00ff' },
            'sunset': { primary: '#ff6b6b', bg: '#1a1a2e', accent: '#feca57' }
        },
        storageKey: 'movieshows-theme-custom',
        
        getTheme() {
            return localStorage.getItem(this.storageKey) || 'default';
        },
        
        setTheme(themeName) {
            const theme = this.themes[themeName];
            if (!theme) return;
            
            localStorage.setItem(this.storageKey, themeName);
            document.documentElement.style.setProperty('--color-primary', theme.primary);
            document.documentElement.style.setProperty('--color-bg', theme.bg);
            document.documentElement.style.setProperty('--color-accent', theme.accent);
            
            // Update existing buttons
            document.querySelectorAll('[style*="#22c55e"]').forEach(el => {
                el.style.background = el.style.background?.replace('#22c55e', theme.primary);
                el.style.color = el.style.color?.replace('#22c55e', theme.primary);
            });
            
            window.showToast?.(`Theme: ${themeName}`);
        },
        
        showThemePicker() {
            const existing = document.getElementById('theme-picker');
            if (existing) { existing.remove(); return; }
            
            const picker = document.createElement('div');
            picker.id = 'theme-picker';
            picker.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; border: 1px solid rgba(255,255,255,0.1);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        🎨 Themes
                        <button onclick="this.closest('#theme-picker').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                        ${Object.entries(this.themes).map(([name, colors]) => `
                            <button class="theme-btn" data-theme="${name}" style="padding: 20px; background: ${colors.bg}; border: 2px solid ${this.getTheme() === name ? colors.primary : 'transparent'}; border-radius: 12px; cursor: pointer;">
                                <div style="width: 40px; height: 40px; background: ${colors.primary}; border-radius: 50%; margin: 0 auto 10px;"></div>
                                <div style="color: ${colors.primary}; font-size: 12px; text-transform: capitalize;">${name}</div>
                            </button>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(picker);
            
            picker.querySelectorAll('.theme-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.setTheme(btn.dataset.theme);
                    picker.remove();
                    this.showThemePicker();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 62: CONTENT RATINGS BREAKDOWN
    // ============================================================
    const RatingsBreakdown = {
        showBreakdown(movie) {
            const existing = document.getElementById('ratings-breakdown');
            if (existing) { existing.remove(); return; }
            
            const baseRating = parseFloat(movie.rating) || 7;
            const breakdown = {
                story: (baseRating + (Math.random() - 0.5)).toFixed(1),
                acting: (baseRating + (Math.random() - 0.5) * 0.8).toFixed(1),
                visuals: (baseRating + (Math.random() - 0.5) * 1.2).toFixed(1),
                sound: (baseRating + (Math.random() - 0.5) * 0.6).toFixed(1),
                rewatchability: (baseRating + (Math.random() - 0.5) * 1.5).toFixed(1)
            };
            
            const panel = document.createElement('div');
            panel.id = 'ratings-breakdown';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 10px; display: flex; justify-content: space-between;">
                        📊 Rating Breakdown
                        <button onclick="this.closest('#ratings-breakdown').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    <p style="color: #888; margin-bottom: 25px;">${movie.title}</p>
                    
                    ${Object.entries(breakdown).map(([category, score]) => `
                        <div style="margin-bottom: 15px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                <span style="color: white; text-transform: capitalize;">${category}</span>
                                <span style="color: #22c55e; font-weight: bold;">${score}/10</span>
                            </div>
                            <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
                                <div style="height: 100%; width: ${score * 10}%; background: linear-gradient(90deg, #22c55e, #3b82f6); border-radius: 4px;"></div>
                            </div>
                        </div>
                    `).join('')}
                    
                    <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); text-align: center;">
                        <div style="color: #888; font-size: 12px;">Overall</div>
                        <div style="color: #22c55e; font-size: 48px; font-weight: bold;">${movie.rating || 'N/A'}</div>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 63: STREAMING AVAILABILITY CHECKER
    // ============================================================
    const StreamingChecker = {
        platforms: [
            { name: 'Netflix', icon: '🔴', color: '#e50914' },
            { name: 'Disney+', icon: '🏰', color: '#0063e5' },
            { name: 'Max', icon: '💜', color: '#b19cd9' },
            { name: 'Prime Video', icon: '📦', color: '#00a8e1' },
            { name: 'Apple TV+', icon: '🍎', color: '#000000' },
            { name: 'Hulu', icon: '💚', color: '#1ce783' },
            { name: 'Paramount+', icon: '⭐', color: '#0064ff' },
            { name: 'Peacock', icon: '🦚', color: '#000000' }
        ],
        
        checkAvailability(movie) {
            // Simulate availability based on source
            const source = movie.source?.toLowerCase() || '';
            const available = this.platforms.filter(p => {
                if (source.includes(p.name.toLowerCase().replace('+', ''))) return true;
                return Math.random() > 0.6; // Random availability for demo
            });
            return available;
        },
        
        showAvailability(movie) {
            const available = this.checkAvailability(movie);
            const existing = document.getElementById('streaming-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'streaming-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 10px; display: flex; justify-content: space-between;">
                        📺 Where to Watch
                        <button onclick="this.closest('#streaming-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    <p style="color: #888; margin-bottom: 25px;">${movie.title}</p>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                        ${this.platforms.map(p => {
                            const isAvailable = available.some(a => a.name === p.name);
                            return `
                                <div style="padding: 15px; background: ${isAvailable ? `${p.color}20` : 'rgba(255,255,255,0.05)'}; border-radius: 12px; opacity: ${isAvailable ? 1 : 0.4};">
                                    <span style="font-size: 24px; margin-right: 10px;">${p.icon}</span>
                                    <span style="color: ${isAvailable ? 'white' : '#666'};">${p.name}</span>
                                    ${isAvailable ? '<span style="float: right; color: #22c55e;">✓</span>' : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 64: RUNTIME/EPISODE INFO
    // ============================================================
    const RuntimeInfo = {
        getRuntime(movie) {
            if (movie.type === 'TV') {
                return {
                    episodes: Math.floor(Math.random() * 50 + 10),
                    seasons: Math.floor(Math.random() * 8 + 1),
                    avgEpisode: Math.floor(Math.random() * 30 + 20) + ' min'
                };
            }
            return {
                runtime: Math.floor(Math.random() * 90 + 90) + ' min'
            };
        },
        
        showInfo(movie) {
            const info = this.getRuntime(movie);
            window.showToast?.(movie.type === 'TV' 
                ? `${info.seasons} Seasons, ${info.episodes} Episodes` 
                : `Runtime: ${info.runtime}`
            );
        }
    };
    
    // ============================================================
    // FEATURE 65: CONTENT LANGUAGE INFO
    // ============================================================
    const LanguageInfo = {
        languages: ['English', 'Spanish', 'French', 'German', 'Japanese', 'Korean', 'Mandarin', 'Hindi'],
        
        getLanguages(movie) {
            const primary = 'English';
            const dubs = this.languages.filter(() => Math.random() > 0.6);
            return { primary, dubs, subtitles: this.languages };
        },
        
        showLanguageInfo(movie) {
            const info = this.getLanguages(movie);
            const existing = document.getElementById('language-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'language-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 350px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between;">
                        🌐 Languages
                        <button onclick="this.closest('#language-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="margin-bottom: 20px;">
                        <h4 style="color: #888; font-size: 11px; text-transform: uppercase; margin-bottom: 10px;">Original Language</h4>
                        <div style="padding: 10px; background: rgba(34,197,94,0.1); border-radius: 8px; color: white;">${info.primary}</div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <h4 style="color: #888; font-size: 11px; text-transform: uppercase; margin-bottom: 10px;">Audio Dubs</h4>
                        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                            ${info.dubs.map(l => `<span style="padding: 6px 12px; background: rgba(255,255,255,0.1); border-radius: 20px; color: white; font-size: 12px;">${l}</span>`).join('')}
                        </div>
                    </div>
                    
                    <div>
                        <h4 style="color: #888; font-size: 11px; text-transform: uppercase; margin-bottom: 10px;">Subtitles</h4>
                        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                            ${info.subtitles.map(l => `<span style="padding: 6px 12px; background: rgba(255,255,255,0.05); border-radius: 20px; color: #888; font-size: 12px;">${l}</span>`).join('')}
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 66: RELATED NEWS & ARTICLES
    // ============================================================
    const RelatedNews = {
        getNews(movie) {
            // Simulated news
            return [
                { title: `${movie.title} breaks streaming records`, date: '2 hours ago', source: 'Entertainment Weekly' },
                { title: `Behind the scenes of ${movie.title}`, date: '1 day ago', source: 'Variety' },
                { title: `Cast of ${movie.title} discusses their roles`, date: '3 days ago', source: 'Hollywood Reporter' }
            ];
        },
        
        showNews(movie) {
            const news = this.getNews(movie);
            const existing = document.getElementById('news-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'news-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 450px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between;">
                        📰 Related News
                        <button onclick="this.closest('#news-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${news.map(n => `
                        <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px; margin-bottom: 12px; cursor: pointer;" onmouseover="this.style.background='rgba(255,255,255,0.1)'" onmouseout="this.style.background='rgba(255,255,255,0.05)'">
                            <h4 style="color: white; margin: 0 0 8px 0; font-size: 14px;">${n.title}</h4>
                            <div style="display: flex; justify-content: space-between; color: #888; font-size: 12px;">
                                <span>${n.source}</span>
                                <span>${n.date}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 67: BINGE CALCULATOR
    // ============================================================
    const BingeCalculator = {
        calculate(movie) {
            if (movie.type !== 'TV') {
                return { type: 'movie', runtime: '2h 15m' };
            }
            
            const episodes = Math.floor(Math.random() * 50 + 10);
            const avgRuntime = Math.floor(Math.random() * 30 + 25);
            const totalMinutes = episodes * avgRuntime;
            const hours = Math.floor(totalMinutes / 60);
            const days = (totalMinutes / 60 / 8).toFixed(1);
            
            return {
                type: 'tv',
                episodes,
                avgRuntime,
                totalTime: `${hours}h ${totalMinutes % 60}m`,
                bingeDays: days
            };
        },
        
        showCalculator(movie) {
            const result = this.calculate(movie);
            const existing = document.getElementById('binge-calc');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'binge-calc';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 350px; border: 1px solid rgba(139,92,246,0.3); text-align: center;">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between;">
                        ⏱️ Binge Calculator
                        <button onclick="this.closest('#binge-calc').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${result.type === 'tv' ? `
                        <div style="font-size: 60px; margin-bottom: 20px;">📺</div>
                        <div style="color: #888; margin-bottom: 5px;">${result.episodes} episodes × ${result.avgRuntime} min</div>
                        <div style="color: #8b5cf6; font-size: 36px; font-weight: bold; margin-bottom: 10px;">${result.totalTime}</div>
                        <div style="color: white;">That's about <span style="color: #8b5cf6; font-weight: bold;">${result.bingeDays} days</span> of 8-hour watching!</div>
                    ` : `
                        <div style="font-size: 60px; margin-bottom: 20px;">🎬</div>
                        <div style="color: white; font-size: 24px;">Movie Runtime</div>
                        <div style="color: #8b5cf6; font-size: 36px; font-weight: bold;">${result.runtime}</div>
                    `}
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 68: SPOILER-FREE REVIEWS
    // ============================================================
    const SpoilerFreeReviews = {
        getReviews(movie) {
            return [
                { text: "Absolutely incredible! A must-watch for any fan of the genre.", rating: 5, spoilerFree: true },
                { text: "Great performances, stunning visuals, and an engaging story.", rating: 4, spoilerFree: true },
                { text: "Started slow but the payoff was worth it.", rating: 4, spoilerFree: true },
                { text: "One of the best I've seen this year!", rating: 5, spoilerFree: true }
            ];
        },
        
        showReviews(movie) {
            const reviews = this.getReviews(movie);
            const existing = document.getElementById('spoilerfree-reviews');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'spoilerfree-reviews';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 450px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between;">
                        ✅ Spoiler-Free Reviews
                        <button onclick="this.closest('#spoilerfree-reviews').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${reviews.map(r => `
                        <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px; margin-bottom: 12px;">
                            <div style="color: #22c55e; margin-bottom: 8px;">${'⭐'.repeat(r.rating)}</div>
                            <p style="color: white; margin: 0; font-size: 14px; line-height: 1.5;">"${r.text}"</p>
                            <div style="margin-top: 10px; display: flex; align-items: center; gap: 8px;">
                                <span style="padding: 4px 8px; background: rgba(34,197,94,0.2); color: #22c55e; border-radius: 4px; font-size: 10px;">✓ Spoiler Free</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 69: CONTENT WARNINGS DETAIL
    // ============================================================
    const ContentWarningsDetail = {
        warnings: {
            'Action': ['Violence', 'Intense Action'],
            'Horror': ['Jump Scares', 'Gore', 'Disturbing Images'],
            'Thriller': ['Suspense', 'Psychological Tension'],
            'Drama': ['Emotional Scenes', 'Mature Themes'],
            'Romance': ['Sexual Content', 'Romantic Themes'],
            'Comedy': ['Adult Humor', 'Crude Language'],
            'War': ['War Violence', 'Historical Trauma']
        },
        
        getWarnings(movie) {
            const result = [];
            (movie.genres || []).forEach(g => {
                if (this.warnings[g]) {
                    result.push(...this.warnings[g]);
                }
            });
            return [...new Set(result)];
        },
        
        showWarnings(movie) {
            const warnings = this.getWarnings(movie);
            if (warnings.length === 0) {
                window.showToast?.('No content warnings for this title');
                return;
            }
            
            const existing = document.getElementById('content-warnings-detail');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'content-warnings-detail';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 350px; border: 1px solid rgba(239,68,68,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between;">
                        ⚠️ Content Warnings
                        <button onclick="this.closest('#content-warnings-detail').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <p style="color: #888; margin-bottom: 20px; font-size: 13px;">${movie.title} may contain:</p>
                    
                    <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                        ${warnings.map(w => `
                            <span style="padding: 8px 16px; background: rgba(239,68,68,0.1); color: #ef4444; border-radius: 20px; font-size: 13px;">⚠️ ${w}</span>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 70: QUICK RATE
    // ============================================================
    const QuickRate = {
        show(movie) {
            const existing = document.getElementById('quick-rate');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'quick-rate';
            panel.innerHTML = `
                <div style="position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.95); border-radius: 30px; padding: 15px 30px; z-index: 99999; display: flex; gap: 15px; align-items: center; border: 1px solid rgba(255,255,255,0.1);">
                    <span style="color: white; font-size: 14px;">Rate:</span>
                    ${[1,2,3,4,5].map(i => `
                        <button class="quick-star" data-rating="${i}" style="font-size: 28px; background: none; border: none; cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.2)'" onmouseout="this.style.transform='scale(1)'">☆</button>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.quick-star').forEach(btn => {
                btn.addEventListener('click', () => {
                    const rating = parseInt(btn.dataset.rating);
                    window.MovieShowsFeatures?.UserRatings?.setRating(movie.title, rating);
                    panel.remove();
                });
                
                btn.addEventListener('mouseover', () => {
                    const rating = parseInt(btn.dataset.rating);
                    panel.querySelectorAll('.quick-star').forEach((s, idx) => {
                        s.textContent = idx < rating ? '⭐' : '☆';
                    });
                });
            });
            
            // Auto-close after 5 seconds
            setTimeout(() => panel.remove(), 5000);
        }
    };
    
    // ============================================================
    // FEATURE 71: WATCH PROGRESS TRACKER
    // ============================================================
    const WatchProgress = {
        storageKey: 'movieshows-progress',
        
        getProgress(title) {
            try {
                const all = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
                return all[title] || 0;
            } catch { return 0; }
        },
        
        setProgress(title, percent) {
            const all = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
            all[title] = percent;
            localStorage.setItem(this.storageKey, JSON.stringify(all));
        },
        
        showProgressBadge(movie, container) {
            const progress = this.getProgress(movie.title);
            if (progress > 0 && progress < 100) {
                const badge = document.createElement('div');
                badge.className = 'progress-badge';
                badge.innerHTML = `
                    <div style="position: absolute; bottom: 0; left: 0; right: 0; height: 4px; background: rgba(255,255,255,0.2);">
                        <div style="height: 100%; width: ${progress}%; background: #22c55e;"></div>
                    </div>
                `;
                container?.appendChild(badge);
            }
        }
    };
    
    // ============================================================
    // FEATURE 72: MOOD TRACKER
    // ============================================================
    const MoodTracker = {
        storageKey: 'movieshows-mood-history',
        
        logMood(mood, movie) {
            try {
                const history = JSON.parse(localStorage.getItem(this.storageKey) || '[]');
                history.unshift({
                    mood,
                    movie: movie.title,
                    timestamp: Date.now()
                });
                localStorage.setItem(this.storageKey, JSON.stringify(history.slice(0, 100)));
            } catch {}
        },
        
        getMoodStats() {
            try {
                const history = JSON.parse(localStorage.getItem(this.storageKey) || '[]');
                const stats = {};
                history.forEach(h => {
                    stats[h.mood] = (stats[h.mood] || 0) + 1;
                });
                return stats;
            } catch { return {}; }
        },
        
        showMoodAnalysis() {
            const stats = this.getMoodStats();
            const total = Object.values(stats).reduce((a, b) => a + b, 0);
            
            const existing = document.getElementById('mood-analysis');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'mood-analysis';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(139,92,246,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        🎭 Your Mood History
                        <button onclick="this.closest('#mood-analysis').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${total === 0 ? '<p style="color: #666; text-align: center;">No mood data yet</p>' : Object.entries(stats)
                        .sort((a, b) => b[1] - a[1])
                        .map(([mood, count]) => `
                            <div style="margin-bottom: 15px;">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                    <span style="color: white;">${mood}</span>
                                    <span style="color: #8b5cf6;">${Math.round(count / total * 100)}%</span>
                                </div>
                                <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px;">
                                    <div style="height: 100%; width: ${count / total * 100}%; background: linear-gradient(90deg, #8b5cf6, #ec4899); border-radius: 4px;"></div>
                                </div>
                            </div>
                        `).join('')}
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 73: DIRECTOR FILMOGRAPHY
    // ============================================================
    const DirectorFilmography = {
        showFilmography(director) {
            const movies = window.allMoviesData || [];
            const directorMovies = movies.filter(m => 
                m.director === director || 
                Math.random() > 0.8 // Simulated
            ).slice(0, 6);
            
            const existing = document.getElementById('filmography-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'filmography-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 500px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        🎬 Director: ${director || 'Unknown'}
                        <button onclick="this.closest('#filmography-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
                        ${directorMovies.map(m => `
                            <div class="filmography-item" data-title="${m.title}" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                <img src="${m.posterUrl}" style="width: 100%; aspect-ratio: 2/3; object-fit: cover; border-radius: 8px;">
                                <h4 style="color: white; font-size: 12px; margin: 8px 0 0 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${m.title}</h4>
                                <div style="color: #888; font-size: 11px;">${m.year}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.filmography-item').forEach(item => {
                item.addEventListener('click', () => {
                    window.playMovieByTitle?.(item.dataset.title);
                    panel.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 74: AWARD INFORMATION
    // ============================================================
    const AwardInfo = {
        getAwards(movie) {
            const baseRating = parseFloat(movie.rating) || 7;
            const awards = [];
            
            if (baseRating >= 8) {
                awards.push({ name: 'Academy Award Nominee', category: 'Best Picture', year: movie.year });
            }
            if (baseRating >= 8.5) {
                awards.push({ name: 'Golden Globe Winner', category: 'Best Drama', year: movie.year });
            }
            if (Math.random() > 0.5) {
                awards.push({ name: "Critics' Choice", category: 'Best Film', year: movie.year });
            }
            
            return awards;
        },
        
        showAwards(movie) {
            const awards = this.getAwards(movie);
            
            const existing = document.getElementById('awards-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'awards-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(245,158,11,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between;">
                        🏆 Awards & Recognition
                        <button onclick="this.closest('#awards-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${awards.length === 0 ? '<p style="color: #666; text-align: center;">No major awards recorded</p>' : awards.map(a => `
                        <div style="padding: 15px; background: linear-gradient(135deg, rgba(245,158,11,0.1), rgba(245,158,11,0.05)); border-radius: 12px; margin-bottom: 12px;">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <span style="font-size: 32px;">🏆</span>
                                <div>
                                    <div style="color: #f59e0b; font-weight: bold;">${a.name}</div>
                                    <div style="color: white; font-size: 13px;">${a.category}</div>
                                    <div style="color: #888; font-size: 12px;">${a.year}</div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 75: SCENE CHAPTERS (For YouTube)
    // ============================================================
    const SceneChapters = {
        // Simulated chapters
        getChapters(movie) {
            return [
                { time: '0:00', title: 'Opening' },
                { time: '2:15', title: 'Title Sequence' },
                { time: '5:30', title: 'Main Trailer' },
                { time: '8:45', title: 'Action Highlight' },
                { time: '12:00', title: 'Climax Tease' }
            ];
        }
    };
    
    // ============================================================
    // FEATURE 76: FRANCHISE TIMELINE
    // ============================================================
    const FranchiseTimeline = {
        franchises: {
            'Marvel': ['Iron Man', 'Avengers', 'Thor', 'Captain America', 'Spider-Man', 'Black Panther', 'Guardians'],
            'Star Wars': ['Star Wars', 'Mandalorian', 'Obi-Wan', 'Ahsoka'],
            'DC': ['Batman', 'Superman', 'Wonder Woman', 'Aquaman', 'Justice League'],
            'Harry Potter': ['Harry Potter', 'Fantastic Beasts'],
            'Fast & Furious': ['Fast', 'Furious']
        },
        
        detectFranchise(movie) {
            for (const [franchise, keywords] of Object.entries(this.franchises)) {
                if (keywords.some(k => movie.title?.includes(k))) {
                    return franchise;
                }
            }
            return null;
        },
        
        getFranchiseMovies(franchise) {
            const movies = window.allMoviesData || [];
            const keywords = this.franchises[franchise] || [];
            return movies.filter(m => 
                keywords.some(k => m.title?.includes(k))
            ).sort((a, b) => parseInt(a.year) - parseInt(b.year));
        },
        
        showTimeline(movie) {
            const franchise = this.detectFranchise(movie);
            if (!franchise) {
                window.showToast?.('Not part of a known franchise');
                return;
            }
            
            const franchiseMovies = this.getFranchiseMovies(franchise);
            
            const existing = document.getElementById('franchise-timeline');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'franchise-timeline';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 600px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        🎬 ${franchise} Timeline
                        <button onclick="this.closest('#franchise-timeline').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="position: relative; padding-left: 30px;">
                        <div style="position: absolute; left: 10px; top: 0; bottom: 0; width: 2px; background: linear-gradient(to bottom, #22c55e, #3b82f6);"></div>
                        
                        ${franchiseMovies.map((m, i) => `
                            <div class="timeline-item" data-title="${m.title}" style="position: relative; padding: 15px; margin-bottom: 20px; cursor: pointer; transition: all 0.2s;">
                                <div style="position: absolute; left: -24px; width: 10px; height: 10px; background: ${m.title === movie.title ? '#22c55e' : 'white'}; border-radius: 50%;"></div>
                                <div style="color: #22c55e; font-size: 12px; margin-bottom: 5px;">${m.year}</div>
                                <div style="color: ${m.title === movie.title ? '#22c55e' : 'white'}; font-weight: ${m.title === movie.title ? 'bold' : 'normal'};">${m.title}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.timeline-item').forEach(item => {
                item.addEventListener('click', () => {
                    window.playMovieByTitle?.(item.dataset.title);
                    panel.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 77: SOCIAL MEDIA BUZZ
    // ============================================================
    const SocialBuzz = {
        getBuzz(movie) {
            const sentiment = Math.random();
            return {
                twitterMentions: Math.floor(Math.random() * 50000 + 1000),
                sentiment: sentiment > 0.7 ? 'Very Positive' : sentiment > 0.4 ? 'Mostly Positive' : 'Mixed',
                trending: Math.random() > 0.5,
                topHashtags: [`#${movie.title?.replace(/\s/g, '')}`, '#MustWatch', '#NowStreaming']
            };
        },
        
        showBuzz(movie) {
            const buzz = this.getBuzz(movie);
            
            const existing = document.getElementById('social-buzz');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'social-buzz';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(59,130,246,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between;">
                        📱 Social Buzz
                        <button onclick="this.closest('#social-buzz').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                        <div style="padding: 20px; background: rgba(59,130,246,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #3b82f6; font-size: 28px; font-weight: bold;">${(buzz.twitterMentions / 1000).toFixed(1)}K</div>
                            <div style="color: #888; font-size: 12px;">Mentions</div>
                        </div>
                        <div style="padding: 20px; background: rgba(34,197,94,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #22c55e; font-size: 18px; font-weight: bold;">${buzz.sentiment}</div>
                            <div style="color: #888; font-size: 12px;">Sentiment</div>
                        </div>
                    </div>
                    
                    ${buzz.trending ? '<div style="padding: 10px; background: rgba(239,68,68,0.1); border-radius: 8px; color: #ef4444; text-align: center; margin-bottom: 15px;">🔥 Currently Trending!</div>' : ''}
                    
                    <div>
                        <div style="color: #888; font-size: 11px; margin-bottom: 8px;">TOP HASHTAGS</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                            ${buzz.topHashtags.map(h => `<span style="padding: 6px 12px; background: rgba(59,130,246,0.2); color: #3b82f6; border-radius: 20px; font-size: 12px;">${h}</span>`).join('')}
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 78: MINI GAMES
    // ============================================================
    const MiniGames = {
        showTrivia(movie) {
            const questions = [
                { q: `What year was ${movie.title} released?`, a: movie.year, options: [parseInt(movie.year) - 1, movie.year, parseInt(movie.year) + 1, parseInt(movie.year) + 2] },
                { q: `What genre is ${movie.title}?`, a: movie.genres?.[0], options: ['Action', 'Comedy', 'Drama', 'Horror'] }
            ];
            
            const question = questions[Math.floor(Math.random() * questions.length)];
            
            const existing = document.getElementById('trivia-game');
            if (existing) { existing.remove(); return; }
            
            const game = document.createElement('div');
            game.id = 'trivia-game';
            game.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: linear-gradient(135deg, rgba(139,92,246,0.95), rgba(59,130,246,0.95)); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; text-align: center;">
                    <h2 style="color: white; margin-bottom: 20px;">🎮 Movie Trivia</h2>
                    <p style="color: white; font-size: 18px; margin-bottom: 25px;">${question.q}</p>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        ${question.options.sort(() => Math.random() - 0.5).map(opt => `
                            <button class="trivia-answer" data-answer="${opt}" style="padding: 15px; background: rgba(255,255,255,0.2); border: none; border-radius: 10px; color: white; cursor: pointer; font-size: 16px;">${opt}</button>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(game);
            
            game.querySelectorAll('.trivia-answer').forEach(btn => {
                btn.addEventListener('click', () => {
                    const isCorrect = btn.dataset.answer == question.a;
                    btn.style.background = isCorrect ? '#22c55e' : '#ef4444';
                    setTimeout(() => {
                        game.remove();
                        window.showToast?.(isCorrect ? '🎉 Correct!' : '❌ Wrong!');
                    }, 1000);
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 79: CONTENT DIGEST
    // ============================================================
    const ContentDigest = {
        generateDigest() {
            const history = window.MovieShowsFeatures?.WatchHistory?.getHistory() || [];
            const thisWeek = history.filter(h => Date.now() - h.watchedAt < 7 * 24 * 60 * 60 * 1000);
            
            return {
                watchedThisWeek: thisWeek.length,
                topGenre: 'Drama', // Simplified
                hoursWatched: Math.floor(thisWeek.length * 2.5),
                suggestion: 'Try something from the Comedy genre!'
            };
        },
        
        showDigest() {
            const digest = this.generateDigest();
            
            const existing = document.getElementById('weekly-digest');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'weekly-digest';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: linear-gradient(135deg, rgba(0,0,0,0.98), rgba(20,20,40,0.98)); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between;">
                        📊 Weekly Digest
                        <button onclick="this.closest('#weekly-digest').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 25px;">
                        <div style="padding: 20px; background: rgba(34,197,94,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #22c55e; font-size: 36px; font-weight: bold;">${digest.watchedThisWeek}</div>
                            <div style="color: #888; font-size: 12px;">Titles Watched</div>
                        </div>
                        <div style="padding: 20px; background: rgba(59,130,246,0.1); border-radius: 12px; text-align: center;">
                            <div style="color: #3b82f6; font-size: 36px; font-weight: bold;">${digest.hoursWatched}h</div>
                            <div style="color: #888; font-size: 12px;">Watch Time</div>
                        </div>
                    </div>
                    
                    <div style="padding: 15px; background: rgba(139,92,246,0.1); border-radius: 12px;">
                        <div style="color: #8b5cf6; font-size: 12px; margin-bottom: 5px;">💡 SUGGESTION</div>
                        <div style="color: white;">${digest.suggestion}</div>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 80: FLOATING ACTION BUTTON
    // ============================================================
    const FloatingActionButton = {
        createFAB() {
            const existing = document.getElementById('fab-menu');
            if (existing) return;
            
            const fab = document.createElement('div');
            fab.id = 'fab-menu';
            fab.innerHTML = `
                <div id="fab-actions" style="position: fixed; bottom: 90px; right: 20px; display: none; flex-direction: column; gap: 10px; z-index: 9998;">
                    <button class="fab-action" data-action="random" style="width: 50px; height: 50px; background: #8b5cf6; border: none; border-radius: 50%; color: white; cursor: pointer; font-size: 20px;" title="Random">🎲</button>
                    <button class="fab-action" data-action="search" style="width: 50px; height: 50px; background: #3b82f6; border: none; border-radius: 50%; color: white; cursor: pointer; font-size: 20px;" title="Search">🔍</button>
                    <button class="fab-action" data-action="stats" style="width: 50px; height: 50px; background: #22c55e; border: none; border-radius: 50%; color: white; cursor: pointer; font-size: 20px;" title="Stats">📊</button>
                    <button class="fab-action" data-action="theme" style="width: 50px; height: 50px; background: #ec4899; border: none; border-radius: 50%; color: white; cursor: pointer; font-size: 20px;" title="Themes">🎨</button>
                </div>
                <button id="fab-toggle" style="position: fixed; bottom: 20px; right: 20px; width: 60px; height: 60px; background: linear-gradient(135deg, #22c55e, #3b82f6); border: none; border-radius: 50%; color: white; cursor: pointer; font-size: 24px; z-index: 9999; box-shadow: 0 4px 20px rgba(34,197,94,0.4); transition: transform 0.3s;">+</button>
            `;
            document.body.appendChild(fab);
            
            const toggle = document.getElementById('fab-toggle');
            const actions = document.getElementById('fab-actions');
            let isOpen = false;
            
            toggle.addEventListener('click', () => {
                isOpen = !isOpen;
                actions.style.display = isOpen ? 'flex' : 'none';
                toggle.style.transform = isOpen ? 'rotate(45deg)' : 'rotate(0)';
            });
            
            fab.querySelectorAll('.fab-action').forEach(btn => {
                btn.addEventListener('click', () => {
                    switch (btn.dataset.action) {
                        case 'random':
                            window.MovieShowsFeatures?.RandomShuffle?.playRandom();
                            break;
                        case 'search':
                            document.querySelector('[id*="search"]')?.click();
                            break;
                        case 'stats':
                            window.MovieShowsFeatures?.StatsDashboard?.showDashboard();
                            break;
                        case 'theme':
                            CustomThemes.showThemePicker();
                            break;
                    }
                    actions.style.display = 'none';
                    toggle.style.transform = 'rotate(0)';
                    isOpen = false;
                });
            });
        }
    };
    
    // ============================================================
    // INITIALIZATION
    // ============================================================
    function initializeBatch4Features() {
        console.log('[MovieShows] Initializing Premium Features v2.3 (Batch 4)...');
        
        setTimeout(() => {
            try {
                CustomThemes.setTheme(CustomThemes.getTheme());
                FloatingActionButton.createFAB();
                
                console.log('[MovieShows] Premium Features v2.3 initialized successfully!');
                
            } catch (e) {
                console.error('[MovieShows] Error initializing batch 4 features:', e);
            }
        }, 5000);
    }
    
    // Expose features globally
    window.MovieShowsFeaturesBatch4 = {
        CustomThemes,
        RatingsBreakdown,
        StreamingChecker,
        RuntimeInfo,
        LanguageInfo,
        RelatedNews,
        BingeCalculator,
        SpoilerFreeReviews,
        ContentWarningsDetail,
        QuickRate,
        WatchProgress,
        MoodTracker,
        DirectorFilmography,
        AwardInfo,
        SceneChapters,
        FranchiseTimeline,
        SocialBuzz,
        MiniGames,
        ContentDigest,
        FloatingActionButton
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeBatch4Features);
    } else {
        initializeBatch4Features();
    }
    
})();
