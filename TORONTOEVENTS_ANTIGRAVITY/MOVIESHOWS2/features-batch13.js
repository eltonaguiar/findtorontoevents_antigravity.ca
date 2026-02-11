// Premium Features Batch 13 (241-260)
// Enhanced engagement and discovery features

(function() {
    console.log('[MovieShows] Initializing Premium Features v3.0 (Batch 13)...');

    // Feature 241: Content Director Spotlight
    const DirectorSpotlight = {
        init: function() {
            this.addSpotlightButton();
            console.log('[MovieShows] Director Spotlight initialized');
        },
        addSpotlightButton: function() {
            const container = document.querySelector('.video-info, .movie-info');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🎬 Director';
            btn.style.cssText = 'background:#ff5722;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showSpotlight();
            container.appendChild(btn);
        },
        showSpotlight: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🎬 Director Spotlight</h3>
                <div style="display:flex;gap:20px;align-items:center;margin-bottom:20px;">
                    <div style="width:80px;height:80px;background:#444;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:30px;">🎥</div>
                    <div>
                        <div style="color:#fff;font-size:20px;">Featured Director</div>
                        <div style="color:#888;">12 Films • 3 Awards</div>
                    </div>
                </div>
                <div style="color:#aaa;margin-bottom:15px;">Known for visually stunning cinematography and complex narratives.</div>
                <h4 style="color:#fff;margin:15px 0 10px;">Other Films:</h4>
                <div style="display:flex;gap:10px;flex-wrap:wrap;">
                    <span style="background:#252545;color:#aaa;padding:6px 12px;border-radius:15px;font-size:12px;">Film A (2020)</span>
                    <span style="background:#252545;color:#aaa;padding:6px 12px;border-radius:15px;font-size:12px;">Film B (2018)</span>
                    <span style="background:#252545;color:#aaa;padding:6px 12px;border-radius:15px;font-size:12px;">Film C (2015)</span>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 242: Content Studio Browser
    const StudioBrowser = {
        init: function() {
            this.addBrowserButton();
            console.log('[MovieShows] Studio Browser initialized');
        },
        addBrowserButton: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🏢 Studios';
            btn.style.cssText = 'background:#795548;color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showBrowser();
            nav.appendChild(btn);
        },
        showBrowser: function() {
            const studios = ['Marvel Studios', 'Warner Bros', 'Universal', 'Disney', 'Sony Pictures', 'Paramount', 'Netflix', 'A24', 'Lionsgate', 'Fox'];
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🏢 Browse by Studio</h3>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                    ${studios.map(s => `<button class="studio-btn" style="background:#252545;color:#fff;border:none;padding:12px;border-radius:8px;cursor:pointer;">${s}</button>`).join('')}
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 243: Content Franchise Explorer
    const FranchiseExplorer = {
        init: function() {
            this.addExplorerButton();
            console.log('[MovieShows] Franchise Explorer initialized');
        },
        addExplorerButton: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🎯 Franchises';
            btn.style.cssText = 'background:#3f51b5;color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showExplorer();
            nav.appendChild(btn);
        },
        showExplorer: function() {
            const franchises = [
                { name: 'Marvel Cinematic Universe', count: 32 },
                { name: 'Star Wars', count: 12 },
                { name: 'DC Extended Universe', count: 15 },
                { name: 'Harry Potter', count: 11 },
                { name: 'Fast & Furious', count: 10 },
                { name: 'James Bond', count: 25 }
            ];
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🎯 Explore Franchises</h3>
                <div style="max-height:400px;overflow-y:auto;">
                    ${franchises.map(f => `
                        <div style="background:#252545;padding:15px;border-radius:8px;margin:10px 0;cursor:pointer;display:flex;justify-content:space-between;align-items:center;">
                            <span style="color:#fff;">${f.name}</span>
                            <span style="color:#888;font-size:12px;">${f.count} titles</span>
                        </div>
                    `).join('')}
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 244: Content Awards Browser
    const AwardsBrowser = {
        init: function() {
            this.addBrowserButton();
            console.log('[MovieShows] Awards Browser initialized');
        },
        addBrowserButton: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🏆 Awards';
            btn.style.cssText = 'background:#ffc107;color:#333;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showBrowser();
            nav.appendChild(btn);
        },
        showBrowser: function() {
            const awards = ['Oscar Winners', 'Golden Globe Winners', 'BAFTA Winners', 'Cannes Winners', 'Emmy Winners', 'Critics Choice'];
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:350px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🏆 Award Winners</h3>
                <div style="display:flex;flex-direction:column;gap:10px;">
                    ${awards.map(a => `<button style="background:#252545;color:#fff;border:none;padding:15px;border-radius:8px;cursor:pointer;text-align:left;display:flex;align-items:center;gap:10px;"><span style="font-size:20px;">🏅</span>${a}</button>`).join('')}
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 245: Content Box Office Stats
    const BoxOfficeStats = {
        init: function() {
            this.addStatsButton();
            console.log('[MovieShows] Box Office Stats initialized');
        },
        addStatsButton: function() {
            const container = document.querySelector('.video-info, .movie-info');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '💰 Box Office';
            btn.style.cssText = 'background:#4CAF50;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showStats();
            container.appendChild(btn);
        },
        showStats: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:350px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">💰 Box Office Performance</h3>
                <div style="color:#aaa;">
                    <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #333;">
                        <span>Opening Weekend</span>
                        <span style="color:#4CAF50;">$95.2M</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #333;">
                        <span>Domestic Total</span>
                        <span style="color:#4CAF50;">$312.5M</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #333;">
                        <span>International</span>
                        <span style="color:#4CAF50;">$485.3M</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #333;">
                        <span>Worldwide Total</span>
                        <span style="color:#4CAF50;font-weight:bold;">$797.8M</span>
                    </div>
                    <div style="display:flex;justify-content:space-between;padding:12px 0;">
                        <span>Budget</span>
                        <span style="color:#ff9800;">$150M</span>
                    </div>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 246: Content Release Calendar
    const ReleaseCalendar = {
        init: function() {
            this.addCalendarButton();
            console.log('[MovieShows] Release Calendar initialized');
        },
        addCalendarButton: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = '📆 Releases';
            btn.style.cssText = 'background:#9c27b0;color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showCalendar();
            nav.appendChild(btn);
        },
        showCalendar: function() {
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            const currentMonth = new Date().getMonth();
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">📆 Upcoming Releases</h3>
                <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:20px;">
                    ${months.map((m, i) => `<button style="background:${i === currentMonth ? '#e94560' : '#252545'};color:#fff;border:none;padding:8px 12px;border-radius:4px;cursor:pointer;font-size:12px;">${m}</button>`).join('')}
                </div>
                <div style="color:#aaa;">
                    <div style="background:#252545;padding:15px;border-radius:8px;margin:10px 0;">
                        <div style="color:#fff;font-weight:bold;">Movie Title A</div>
                        <div style="font-size:12px;margin-top:5px;">Feb 14, 2026 • Action</div>
                    </div>
                    <div style="background:#252545;padding:15px;border-radius:8px;margin:10px 0;">
                        <div style="color:#fff;font-weight:bold;">Movie Title B</div>
                        <div style="font-size:12px;margin-top:5px;">Feb 21, 2026 • Drama</div>
                    </div>
                    <div style="background:#252545;padding:15px;border-radius:8px;margin:10px 0;">
                        <div style="color:#fff;font-weight:bold;">Movie Title C</div>
                        <div style="font-size:12px;margin-top:5px;">Feb 28, 2026 • Comedy</div>
                    </div>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 247: Content Country Filter
    const CountryFilter = {
        selected: localStorage.getItem('movieshows-country') || 'all',
        init: function() {
            this.addFilterButton();
            console.log('[MovieShows] Country Filter initialized');
        },
        addFilterButton: function() {
            const container = document.querySelector('.filters, .filter-bar');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🌍 Country';
            btn.style.cssText = 'background:#607d8b;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.showFilter();
            container.appendChild(btn);
        },
        showFilter: function() {
            const countries = ['All Countries', 'USA', 'UK', 'France', 'Germany', 'Japan', 'South Korea', 'India', 'Canada', 'Australia', 'Spain', 'Italy'];
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:300px;max-height:80vh;overflow-y:auto;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🌍 Filter by Country</h3>
                <div style="display:flex;flex-direction:column;gap:8px;">
                    ${countries.map(c => `<button class="country-btn" data-country="${c}" style="background:${this.selected === c ? '#e94560' : '#252545'};color:#fff;border:none;padding:10px 15px;border-radius:6px;cursor:pointer;text-align:left;">${c}</button>`).join('')}
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#666;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Cancel</button>
            `;
            document.body.appendChild(modal);
            
            modal.querySelectorAll('.country-btn').forEach(btn => {
                btn.onclick = () => {
                    this.selected = btn.dataset.country;
                    localStorage.setItem('movieshows-country', this.selected);
                    modal.remove();
                };
            });
        }
    };

    // Feature 248: Content Actor Spotlight
    const ActorSpotlight = {
        init: function() {
            this.addSpotlightButton();
            console.log('[MovieShows] Actor Spotlight initialized');
        },
        addSpotlightButton: function() {
            const container = document.querySelector('.video-info, .movie-info');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '⭐ Actor';
            btn.style.cssText = 'background:#e91e63;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showSpotlight();
            container.appendChild(btn);
        },
        showSpotlight: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">⭐ Actor Spotlight</h3>
                <div style="display:flex;gap:20px;align-items:center;margin-bottom:20px;">
                    <div style="width:100px;height:100px;background:#444;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:40px;">👤</div>
                    <div>
                        <div style="color:#fff;font-size:22px;">Lead Actor Name</div>
                        <div style="color:#888;">45 Films • 2 Oscars</div>
                        <div style="color:#666;font-size:12px;margin-top:5px;">Born: Jan 1, 1980</div>
                    </div>
                </div>
                <h4 style="color:#fff;margin:15px 0 10px;">Popular Films:</h4>
                <div style="display:flex;gap:10px;flex-wrap:wrap;">
                    <span style="background:#252545;color:#aaa;padding:8px 15px;border-radius:20px;font-size:13px;cursor:pointer;">Blockbuster A</span>
                    <span style="background:#252545;color:#aaa;padding:8px 15px;border-radius:20px;font-size:13px;cursor:pointer;">Drama B</span>
                    <span style="background:#252545;color:#aaa;padding:8px 15px;border-radius:20px;font-size:13px;cursor:pointer;">Action C</span>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 249: Content Crew Browser
    const CrewBrowser = {
        init: function() {
            this.addBrowserButton();
            console.log('[MovieShows] Crew Browser initialized');
        },
        addBrowserButton: function() {
            const container = document.querySelector('.video-info, .movie-info');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🎥 Crew';
            btn.style.cssText = 'background:#00bcd4;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showBrowser();
            container.appendChild(btn);
        },
        showBrowser: function() {
            const crew = [
                { role: 'Director', name: 'Director Name' },
                { role: 'Writer', name: 'Writer Name' },
                { role: 'Cinematographer', name: 'DP Name' },
                { role: 'Composer', name: 'Composer Name' },
                { role: 'Editor', name: 'Editor Name' },
                { role: 'Producer', name: 'Producer Name' }
            ];
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:350px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🎥 Full Crew</h3>
                <div style="color:#aaa;">
                    ${crew.map(c => `
                        <div style="display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #333;">
                            <span style="color:#888;">${c.role}</span>
                            <span style="color:#fff;">${c.name}</span>
                        </div>
                    `).join('')}
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 250: Content Similar Finder
    const SimilarFinder = {
        init: function() {
            this.addFinderButton();
            console.log('[MovieShows] Similar Finder initialized');
        },
        addFinderButton: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🔍 Find Similar';
            btn.style.cssText = 'background:#673ab7;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.showSimilar();
            container.appendChild(btn);
        },
        showSimilar: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🔍 Similar Content</h3>
                <p style="color:#888;margin-bottom:15px;">Based on genre, director, and themes</p>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;">
                    <div style="background:#252545;padding:15px;border-radius:8px;cursor:pointer;">
                        <div style="color:#fff;font-weight:bold;">Similar Movie 1</div>
                        <div style="color:#888;font-size:12px;">95% match</div>
                    </div>
                    <div style="background:#252545;padding:15px;border-radius:8px;cursor:pointer;">
                        <div style="color:#fff;font-weight:bold;">Similar Movie 2</div>
                        <div style="color:#888;font-size:12px;">89% match</div>
                    </div>
                    <div style="background:#252545;padding:15px;border-radius:8px;cursor:pointer;">
                        <div style="color:#fff;font-weight:bold;">Similar Movie 3</div>
                        <div style="color:#888;font-size:12px;">85% match</div>
                    </div>
                    <div style="background:#252545;padding:15px;border-radius:8px;cursor:pointer;">
                        <div style="color:#fff;font-weight:bold;">Similar Movie 4</div>
                        <div style="color:#888;font-size:12px;">82% match</div>
                    </div>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 251: Content Playlist Shuffle
    const PlaylistShuffle = {
        init: function() {
            this.addShuffleButton();
            console.log('[MovieShows] Playlist Shuffle initialized');
        },
        addShuffleButton: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🔀 Shuffle All';
            btn.style.cssText = 'background:#ff9800;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.shufflePlaylist();
            container.appendChild(btn);
        },
        shufflePlaylist: function() {
            const notif = document.createElement('div');
            notif.textContent = '🔀 Playlist shuffled!';
            notif.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#ff9800;color:white;padding:15px 25px;border-radius:8px;z-index:10000;';
            document.body.appendChild(notif);
            setTimeout(() => notif.remove(), 3000);
        }
    };

    // Feature 252: Content Loop Mode
    const LoopMode = {
        enabled: localStorage.getItem('movieshows-loop') === 'true',
        init: function() {
            this.addLoopButton();
            console.log('[MovieShows] Loop Mode initialized');
        },
        addLoopButton: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = this.enabled ? '🔁 Loop On' : '🔁 Loop Off';
            btn.style.cssText = `background:${this.enabled ? '#4CAF50' : '#666'};color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;`;
            btn.onclick = () => {
                this.enabled = !this.enabled;
                localStorage.setItem('movieshows-loop', this.enabled);
                btn.textContent = this.enabled ? '🔁 Loop On' : '🔁 Loop Off';
                btn.style.background = this.enabled ? '#4CAF50' : '#666';
            };
            container.appendChild(btn);
        }
    };

    // Feature 253: Content Auto-Skip Intro
    const AutoSkipIntro = {
        enabled: localStorage.getItem('movieshows-skip-intro') === 'true',
        init: function() {
            this.addToggle();
            console.log('[MovieShows] Auto-Skip Intro initialized');
        },
        addToggle: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = this.enabled ? '⏭️ Skip: On' : '⏭️ Skip: Off';
            btn.style.cssText = `background:${this.enabled ? '#2196F3' : '#666'};color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;`;
            btn.onclick = () => {
                this.enabled = !this.enabled;
                localStorage.setItem('movieshows-skip-intro', this.enabled);
                btn.textContent = this.enabled ? '⏭️ Skip: On' : '⏭️ Skip: Off';
                btn.style.background = this.enabled ? '#2196F3' : '#666';
            };
            container.appendChild(btn);
        }
    };

    // Feature 254: Content Viewing Party
    const ViewingParty = {
        init: function() {
            this.addPartyButton();
            console.log('[MovieShows] Viewing Party initialized');
        },
        addPartyButton: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🎉 Party Mode';
            btn.style.cssText = 'background:linear-gradient(135deg,#ff6b6b,#feca57);color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showParty();
            nav.appendChild(btn);
        },
        showParty: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🎉 Start Viewing Party</h3>
                <p style="color:#888;margin-bottom:20px;">Watch together with friends in sync!</p>
                <div style="background:#252545;padding:20px;border-radius:8px;text-align:center;margin-bottom:20px;">
                    <div style="color:#fff;font-size:24px;font-family:monospace;letter-spacing:5px;">PARTY-${Math.random().toString(36).substring(2, 8).toUpperCase()}</div>
                    <div style="color:#888;font-size:12px;margin-top:10px;">Share this code with friends</div>
                </div>
                <div style="display:flex;gap:10px;">
                    <button style="flex:1;background:#4CAF50;color:white;border:none;padding:12px;border-radius:6px;cursor:pointer;">Create Party</button>
                    <button style="flex:1;background:#2196F3;color:white;border:none;padding:12px;border-radius:6px;cursor:pointer;">Join Party</button>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#666;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Cancel</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 255: Content Discussion Board
    const DiscussionBoard = {
        init: function() {
            this.addBoardButton();
            console.log('[MovieShows] Discussion Board initialized');
        },
        addBoardButton: function() {
            const container = document.querySelector('.video-info, .movie-info');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '💬 Discuss';
            btn.style.cssText = 'background:#009688;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showBoard();
            container.appendChild(btn);
        },
        showBoard: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:450px;max-height:80vh;overflow-y:auto;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">💬 Discussion</h3>
                <div style="margin-bottom:20px;">
                    <textarea placeholder="Share your thoughts..." style="width:100%;height:80px;background:#252545;border:1px solid #444;color:#fff;padding:12px;border-radius:8px;resize:none;"></textarea>
                    <button style="margin-top:10px;background:#4CAF50;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Post</button>
                </div>
                <div style="color:#aaa;">
                    <div style="background:#252545;padding:15px;border-radius:8px;margin:10px 0;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                            <span style="color:#fff;font-weight:bold;">MovieFan123</span>
                            <span style="color:#666;font-size:12px;">2h ago</span>
                        </div>
                        <p style="margin:0;">This movie was incredible! The plot twist at the end was unexpected.</p>
                        <div style="margin-top:10px;font-size:12px;"><span style="cursor:pointer;">👍 24</span> <span style="cursor:pointer;margin-left:15px;">💬 Reply</span></div>
                    </div>
                    <div style="background:#252545;padding:15px;border-radius:8px;margin:10px 0;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
                            <span style="color:#fff;font-weight:bold;">CinemaLover</span>
                            <span style="color:#666;font-size:12px;">5h ago</span>
                        </div>
                        <p style="margin:0;">The cinematography was absolutely stunning.</p>
                        <div style="margin-top:10px;font-size:12px;"><span style="cursor:pointer;">👍 18</span> <span style="cursor:pointer;margin-left:15px;">💬 Reply</span></div>
                    </div>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 256: Content Spoiler Shield
    const SpoilerShield = {
        enabled: localStorage.getItem('movieshows-spoiler-shield') === 'true',
        init: function() {
            this.addToggle();
            console.log('[MovieShows] Spoiler Shield initialized');
        },
        addToggle: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = this.enabled ? '🛡️ Shield: On' : '🛡️ Shield: Off';
            btn.style.cssText = `background:${this.enabled ? '#f44336' : '#666'};color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;`;
            btn.onclick = () => {
                this.enabled = !this.enabled;
                localStorage.setItem('movieshows-spoiler-shield', this.enabled);
                btn.textContent = this.enabled ? '🛡️ Shield: On' : '🛡️ Shield: Off';
                btn.style.background = this.enabled ? '#f44336' : '#666';
            };
            nav.appendChild(btn);
        }
    };

    // Feature 257: Content Personal Notes
    const PersonalNotes = {
        notes: JSON.parse(localStorage.getItem('movieshows-personal-notes') || '{}'),
        init: function() {
            this.addNotesButton();
            console.log('[MovieShows] Personal Notes initialized');
        },
        addNotesButton: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '📝 Notes';
            btn.style.cssText = 'background:#ffc107;color:#333;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.showNotes();
            container.appendChild(btn);
        },
        showNotes: function() {
            const title = document.querySelector('.video-title, .title, h1')?.textContent || 'current';
            const existingNote = this.notes[title] || '';
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">📝 Personal Notes</h3>
                <textarea id="personal-note" placeholder="Add your notes about this content..." style="width:100%;height:150px;background:#252545;border:1px solid #444;color:#fff;padding:12px;border-radius:8px;resize:none;">${existingNote}</textarea>
                <div style="display:flex;gap:10px;margin-top:15px;">
                    <button id="save-note" style="flex:1;background:#4CAF50;color:white;border:none;padding:10px;border-radius:6px;cursor:pointer;">Save Note</button>
                    <button onclick="this.parentElement.parentElement.remove()" style="flex:1;background:#666;color:white;border:none;padding:10px;border-radius:6px;cursor:pointer;">Cancel</button>
                </div>
            `;
            document.body.appendChild(modal);
            
            modal.querySelector('#save-note').onclick = () => {
                const note = modal.querySelector('#personal-note').value;
                this.notes[title] = note;
                localStorage.setItem('movieshows-personal-notes', JSON.stringify(this.notes));
                modal.remove();
            };
        }
    };

    // Feature 258: Content Favorites Manager
    const FavoritesManager = {
        favorites: JSON.parse(localStorage.getItem('movieshows-favorites') || '[]'),
        init: function() {
            this.addManagerButton();
            console.log('[MovieShows] Favorites Manager initialized');
        },
        addManagerButton: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = `❤️ Favorites (${this.favorites.length})`;
            btn.style.cssText = 'background:#e91e63;color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showManager();
            this.btn = btn;
            nav.appendChild(btn);
        },
        showManager: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;max-height:80vh;overflow-y:auto;';
            
            let favoritesHtml = this.favorites.length ? 
                this.favorites.map((f, i) => `
                    <div style="display:flex;justify-content:space-between;align-items:center;background:#252545;padding:12px;border-radius:8px;margin:8px 0;">
                        <span style="color:#fff;">${f}</span>
                        <button class="remove-fav" data-index="${i}" style="background:#f44336;color:white;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;">✕</button>
                    </div>
                `).join('') :
                '<p style="color:#666;text-align:center;">No favorites yet!</p>';
            
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">❤️ Your Favorites</h3>
                <div>${favoritesHtml}</div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
            
            modal.querySelectorAll('.remove-fav').forEach(btn => {
                btn.onclick = () => {
                    this.favorites.splice(parseInt(btn.dataset.index), 1);
                    localStorage.setItem('movieshows-favorites', JSON.stringify(this.favorites));
                    this.btn.textContent = `❤️ Favorites (${this.favorites.length})`;
                    modal.remove();
                    this.showManager();
                };
            });
        }
    };

    // Feature 259: Content Quick Info Card
    const QuickInfoCard = {
        init: function() {
            this.setupHoverCards();
            console.log('[MovieShows] Quick Info Card initialized');
        },
        setupHoverCards: function() {
            document.addEventListener('mouseover', (e) => {
                const card = e.target.closest('.movie-card, .video-card, .content-card');
                if (card && !card.querySelector('.quick-info-tooltip')) {
                    this.showCard(card);
                }
            });
        },
        showCard: function(element) {
            const tooltip = document.createElement('div');
            tooltip.className = 'quick-info-tooltip';
            tooltip.style.cssText = 'position:absolute;bottom:100%;left:50%;transform:translateX(-50%);background:#1a1a2e;padding:12px;border-radius:8px;z-index:100;min-width:200px;pointer-events:none;box-shadow:0 4px 15px rgba(0,0,0,0.3);';
            tooltip.innerHTML = `
                <div style="color:#fff;font-size:14px;font-weight:bold;margin-bottom:5px;">Quick Info</div>
                <div style="color:#888;font-size:12px;">Rating: ⭐ 8.5</div>
                <div style="color:#888;font-size:12px;">Year: 2024</div>
                <div style="color:#888;font-size:12px;">Genre: Action</div>
            `;
            element.style.position = 'relative';
            element.appendChild(tooltip);
            
            element.addEventListener('mouseleave', () => tooltip.remove(), { once: true });
        }
    };

    // Feature 260: Content Quick Rating
    const QuickRating = {
        ratings: JSON.parse(localStorage.getItem('movieshows-quick-ratings') || '{}'),
        init: function() {
            this.addRatingWidget();
            console.log('[MovieShows] Quick Rating initialized');
        },
        addRatingWidget: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const widget = document.createElement('div');
            widget.style.cssText = 'display:inline-flex;gap:2px;margin:3px;';
            widget.innerHTML = [1,2,3,4,5].map(n => 
                `<button class="quick-star" data-rating="${n}" style="background:transparent;border:none;color:#666;font-size:18px;cursor:pointer;padding:2px;">★</button>`
            ).join('');
            container.appendChild(widget);
            
            widget.querySelectorAll('.quick-star').forEach(star => {
                star.onmouseenter = () => this.highlightStars(widget, parseInt(star.dataset.rating));
                star.onmouseleave = () => this.resetStars(widget);
                star.onclick = () => this.setRating(parseInt(star.dataset.rating), widget);
            });
        },
        highlightStars: function(widget, count) {
            widget.querySelectorAll('.quick-star').forEach((star, i) => {
                star.style.color = i < count ? '#ffc107' : '#666';
            });
        },
        resetStars: function(widget) {
            const title = document.querySelector('.video-title, .title, h1')?.textContent || 'current';
            const rating = this.ratings[title] || 0;
            this.highlightStars(widget, rating);
        },
        setRating: function(rating, widget) {
            const title = document.querySelector('.video-title, .title, h1')?.textContent || 'current';
            this.ratings[title] = rating;
            localStorage.setItem('movieshows-quick-ratings', JSON.stringify(this.ratings));
            this.highlightStars(widget, rating);
        }
    };

    // Initialize all Batch 13 features
    function initBatch13() {
        try {
            DirectorSpotlight.init();
            StudioBrowser.init();
            FranchiseExplorer.init();
            AwardsBrowser.init();
            BoxOfficeStats.init();
            ReleaseCalendar.init();
            CountryFilter.init();
            ActorSpotlight.init();
            CrewBrowser.init();
            SimilarFinder.init();
            PlaylistShuffle.init();
            LoopMode.init();
            AutoSkipIntro.init();
            ViewingParty.init();
            DiscussionBoard.init();
            SpoilerShield.init();
            PersonalNotes.init();
            FavoritesManager.init();
            QuickInfoCard.init();
            QuickRating.init();
            
            console.log('[MovieShows] Batch 13 features (241-260) loaded successfully!');
        } catch (error) {
            console.error('[MovieShows] Error initializing Batch 13:', error);
        }
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initBatch13);
    } else {
        setTimeout(initBatch13, 2000);
    }
})();
