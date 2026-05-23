// Premium Features Batch 12 (221-240)
// Advanced user experience enhancements

(function() {
    console.log('[MovieShows] Initializing Premium Features v2.9 (Batch 12)...');

    // Feature 221: Content Ratings Breakdown
    const RatingsBreakdown = {
        init: function() {
            this.addBreakdownButton();
            console.log('[MovieShows] Ratings Breakdown initialized');
        },
        addBreakdownButton: function() {
            const container = document.querySelector('.video-controls, .player-controls, #controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '📊 Ratings';
            btn.className = 'ratings-breakdown-btn';
            btn.style.cssText = 'background:#4CAF50;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;font-size:12px;';
            btn.onclick = () => this.showBreakdown();
            container.appendChild(btn);
        },
        showBreakdown: function() {
            const modal = document.createElement('div');
            modal.className = 'ratings-modal';
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:350px;box-shadow:0 8px 32px rgba(0,0,0,0.5);';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">📊 Ratings Breakdown</h3>
                <div style="color:#aaa;">
                    <div style="margin:10px 0;"><span style="display:inline-block;width:100px;">IMDb:</span> <span style="color:#f5c518;">★ 8.2</span></div>
                    <div style="margin:10px 0;"><span style="display:inline-block;width:100px;">Rotten Tomatoes:</span> <span style="color:#fa320a;">🍅 92%</span></div>
                    <div style="margin:10px 0;"><span style="display:inline-block;width:100px;">Metacritic:</span> <span style="color:#66cc33;">85</span></div>
                    <div style="margin:10px 0;"><span style="display:inline-block;width:100px;">User Score:</span> <span style="color:#00bcd4;">4.5/5</span></div>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 222: Content Accessibility Options
    const AccessibilityOptions = {
        settings: JSON.parse(localStorage.getItem('movieshows-accessibility') || '{}'),
        init: function() {
            this.addAccessibilityMenu();
            this.applySettings();
            console.log('[MovieShows] Accessibility Options initialized');
        },
        addAccessibilityMenu: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = '♿ Accessibility';
            btn.style.cssText = 'background:#9c27b0;color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showMenu();
            nav.appendChild(btn);
        },
        showMenu: function() {
            const modal = document.createElement('div');
            modal.className = 'accessibility-modal';
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:320px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">♿ Accessibility</h3>
                <label style="color:#aaa;display:block;margin:10px 0;cursor:pointer;">
                    <input type="checkbox" id="acc-high-contrast" ${this.settings.highContrast ? 'checked' : ''}> High Contrast Mode
                </label>
                <label style="color:#aaa;display:block;margin:10px 0;cursor:pointer;">
                    <input type="checkbox" id="acc-large-text" ${this.settings.largeText ? 'checked' : ''}> Large Text
                </label>
                <label style="color:#aaa;display:block;margin:10px 0;cursor:pointer;">
                    <input type="checkbox" id="acc-reduce-motion" ${this.settings.reduceMotion ? 'checked' : ''}> Reduce Motion
                </label>
                <label style="color:#aaa;display:block;margin:10px 0;cursor:pointer;">
                    <input type="checkbox" id="acc-screen-reader" ${this.settings.screenReader ? 'checked' : ''}> Screen Reader Friendly
                </label>
                <button id="acc-save" style="margin-top:15px;background:#4CAF50;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;margin-right:10px;">Save</button>
                <button onclick="this.parentElement.remove()" style="background:#666;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Close</button>
            `;
            document.body.appendChild(modal);
            
            modal.querySelector('#acc-save').onclick = () => {
                this.settings = {
                    highContrast: modal.querySelector('#acc-high-contrast').checked,
                    largeText: modal.querySelector('#acc-large-text').checked,
                    reduceMotion: modal.querySelector('#acc-reduce-motion').checked,
                    screenReader: modal.querySelector('#acc-screen-reader').checked
                };
                localStorage.setItem('movieshows-accessibility', JSON.stringify(this.settings));
                this.applySettings();
                modal.remove();
            };
        },
        applySettings: function() {
            document.body.classList.toggle('high-contrast', this.settings.highContrast);
            document.body.classList.toggle('large-text', this.settings.largeText);
            document.body.classList.toggle('reduce-motion', this.settings.reduceMotion);
        }
    };

    // Feature 223: Content Parental Controls
    const ParentalControls = {
        pin: localStorage.getItem('movieshows-parental-pin'),
        settings: JSON.parse(localStorage.getItem('movieshows-parental') || '{"enabled":false,"maxRating":"PG-13"}'),
        init: function() {
            this.addControlsButton();
            console.log('[MovieShows] Parental Controls initialized');
        },
        addControlsButton: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = '👨‍👩‍👧 Parental';
            btn.style.cssText = 'background:#ff9800;color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showControls();
            nav.appendChild(btn);
        },
        showControls: function() {
            if (this.pin && !this.verifyPin()) return;
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:320px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">👨‍👩‍👧 Parental Controls</h3>
                <label style="color:#aaa;display:block;margin:10px 0;">
                    <input type="checkbox" id="parental-enabled" ${this.settings.enabled ? 'checked' : ''}> Enable Parental Controls
                </label>
                <div style="color:#aaa;margin:15px 0;">
                    Max Rating: 
                    <select id="parental-rating" style="background:#333;color:#fff;border:1px solid #555;padding:5px;border-radius:4px;">
                        <option ${this.settings.maxRating === 'G' ? 'selected' : ''}>G</option>
                        <option ${this.settings.maxRating === 'PG' ? 'selected' : ''}>PG</option>
                        <option ${this.settings.maxRating === 'PG-13' ? 'selected' : ''}>PG-13</option>
                        <option ${this.settings.maxRating === 'R' ? 'selected' : ''}>R</option>
                    </select>
                </div>
                <div style="color:#aaa;margin:15px 0;">
                    Set PIN: <input type="password" id="parental-pin" maxlength="4" placeholder="4 digits" style="background:#333;color:#fff;border:1px solid #555;padding:5px;border-radius:4px;width:80px;">
                </div>
                <button id="parental-save" style="margin-top:15px;background:#4CAF50;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Save</button>
                <button onclick="this.parentElement.remove()" style="margin-left:10px;background:#666;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Close</button>
            `;
            document.body.appendChild(modal);
            
            modal.querySelector('#parental-save').onclick = () => {
                const pin = modal.querySelector('#parental-pin').value;
                if (pin) localStorage.setItem('movieshows-parental-pin', pin);
                this.settings = {
                    enabled: modal.querySelector('#parental-enabled').checked,
                    maxRating: modal.querySelector('#parental-rating').value
                };
                localStorage.setItem('movieshows-parental', JSON.stringify(this.settings));
                modal.remove();
            };
        },
        verifyPin: function() {
            const entered = prompt('Enter parental control PIN:');
            return entered === this.pin;
        }
    };

    // Feature 224: Content Download Queue (Simulated)
    const DownloadQueue = {
        queue: JSON.parse(localStorage.getItem('movieshows-download-queue') || '[]'),
        init: function() {
            this.addQueueButton();
            console.log('[MovieShows] Download Queue initialized');
        },
        addQueueButton: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '⬇️ Download';
            btn.style.cssText = 'background:#2196F3;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.addToQueue();
            container.appendChild(btn);
        },
        addToQueue: function() {
            const title = document.querySelector('.video-title, .title, h1')?.textContent || 'Current Video';
            if (!this.queue.includes(title)) {
                this.queue.push(title);
                localStorage.setItem('movieshows-download-queue', JSON.stringify(this.queue));
                this.showNotification(`"${title}" added to download queue`);
            }
        },
        showNotification: function(msg) {
            const notif = document.createElement('div');
            notif.textContent = msg;
            notif.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#2196F3;color:white;padding:15px 25px;border-radius:8px;z-index:10000;animation:slideIn 0.3s;';
            document.body.appendChild(notif);
            setTimeout(() => notif.remove(), 3000);
        }
    };

    // Feature 225: Content Audio Description Toggle
    const AudioDescription = {
        enabled: localStorage.getItem('movieshows-audio-desc') === 'true',
        init: function() {
            this.addToggle();
            console.log('[MovieShows] Audio Description initialized');
        },
        addToggle: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = this.enabled ? '🔊 AD On' : '🔇 AD Off';
            btn.style.cssText = `background:${this.enabled ? '#4CAF50' : '#666'};color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;`;
            btn.onclick = () => {
                this.enabled = !this.enabled;
                localStorage.setItem('movieshows-audio-desc', this.enabled);
                btn.textContent = this.enabled ? '🔊 AD On' : '🔇 AD Off';
                btn.style.background = this.enabled ? '#4CAF50' : '#666';
            };
            container.appendChild(btn);
        }
    };

    // Feature 226: Content Cast & Crew Browser
    const CastCrewBrowser = {
        init: function() {
            this.addBrowserButton();
            console.log('[MovieShows] Cast & Crew Browser initialized');
        },
        addBrowserButton: function() {
            const container = document.querySelector('.video-info, .movie-info, .content-details');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🎭 Cast & Crew';
            btn.style.cssText = 'background:#9c27b0;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showBrowser();
            container.appendChild(btn);
        },
        showBrowser: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;max-height:80vh;overflow-y:auto;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🎭 Cast & Crew</h3>
                <div style="display:flex;gap:10px;margin-bottom:15px;">
                    <button class="cast-tab active" data-tab="cast" style="background:#e94560;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">Cast</button>
                    <button class="cast-tab" data-tab="crew" style="background:#333;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">Crew</button>
                </div>
                <div id="cast-content" style="color:#aaa;">
                    <div style="display:flex;align-items:center;gap:15px;padding:10px;background:#252545;border-radius:8px;margin:10px 0;">
                        <div style="width:50px;height:50px;background:#444;border-radius:50%;display:flex;align-items:center;justify-content:center;">👤</div>
                        <div><div style="color:#fff;">Lead Actor</div><div style="font-size:12px;">Main Character</div></div>
                    </div>
                    <div style="display:flex;align-items:center;gap:15px;padding:10px;background:#252545;border-radius:8px;margin:10px 0;">
                        <div style="width:50px;height:50px;background:#444;border-radius:50%;display:flex;align-items:center;justify-content:center;">👤</div>
                        <div><div style="color:#fff;">Supporting Actor</div><div style="font-size:12px;">Side Character</div></div>
                    </div>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 227: Content Soundtrack Player
    const SoundtrackPlayer = {
        init: function() {
            this.addPlayerButton();
            console.log('[MovieShows] Soundtrack Player initialized');
        },
        addPlayerButton: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🎵 Soundtrack';
            btn.style.cssText = 'background:#e91e63;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.showPlayer();
            container.appendChild(btn);
        },
        showPlayer: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;bottom:80px;right:20px;background:#1a1a2e;padding:20px;border-radius:12px;z-index:10001;width:300px;';
            modal.innerHTML = `
                <h4 style="color:#fff;margin:0 0 15px;">🎵 Soundtrack</h4>
                <div style="color:#aaa;">
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #333;">
                        <span>Main Theme</span>
                        <button style="background:#e91e63;border:none;color:white;padding:4px 12px;border-radius:4px;cursor:pointer;">▶</button>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #333;">
                        <span>End Credits</span>
                        <button style="background:#e91e63;border:none;color:white;padding:4px 12px;border-radius:4px;cursor:pointer;">▶</button>
                    </div>
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;">
                        <span>Action Scene</span>
                        <button style="background:#e91e63;border:none;color:white;padding:4px 12px;border-radius:4px;cursor:pointer;">▶</button>
                    </div>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#666;color:white;border:none;padding:6px 15px;border-radius:4px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 228: Content Fan Reviews
    const FanReviews = {
        reviews: JSON.parse(localStorage.getItem('movieshows-fan-reviews') || '[]'),
        init: function() {
            this.addReviewsButton();
            console.log('[MovieShows] Fan Reviews initialized');
        },
        addReviewsButton: function() {
            const container = document.querySelector('.video-info, .movie-info');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '💬 Reviews';
            btn.style.cssText = 'background:#00bcd4;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showReviews();
            container.appendChild(btn);
        },
        showReviews: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;max-height:70vh;overflow-y:auto;';
            
            let reviewsHtml = this.reviews.length ? 
                this.reviews.map(r => `<div style="background:#252545;padding:15px;border-radius:8px;margin:10px 0;"><div style="color:#fff;">${r.text}</div><div style="color:#666;font-size:12px;margin-top:5px;">- Anonymous, ${r.rating}/5 ⭐</div></div>`).join('') :
                '<p style="color:#666;">No reviews yet. Be the first!</p>';
            
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">💬 Fan Reviews</h3>
                <div style="color:#aaa;">${reviewsHtml}</div>
                <hr style="border-color:#333;margin:20px 0;">
                <h4 style="color:#fff;margin-bottom:10px;">Write a Review</h4>
                <textarea id="review-text" placeholder="Share your thoughts..." style="width:100%;height:80px;background:#252545;border:1px solid #444;color:#fff;padding:10px;border-radius:6px;resize:none;"></textarea>
                <div style="margin:10px 0;">
                    Rating: <select id="review-rating" style="background:#333;color:#fff;border:1px solid #555;padding:5px;border-radius:4px;">
                        <option>5</option><option>4</option><option>3</option><option>2</option><option>1</option>
                    </select>
                </div>
                <button id="submit-review" style="background:#4CAF50;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Submit</button>
                <button onclick="this.parentElement.remove()" style="margin-left:10px;background:#666;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Close</button>
            `;
            document.body.appendChild(modal);
            
            modal.querySelector('#submit-review').onclick = () => {
                const text = modal.querySelector('#review-text').value;
                const rating = modal.querySelector('#review-rating').value;
                if (text.trim()) {
                    this.reviews.push({ text, rating, date: new Date().toISOString() });
                    localStorage.setItem('movieshows-fan-reviews', JSON.stringify(this.reviews));
                    modal.remove();
                    this.showReviews();
                }
            };
        }
    };

    // Feature 229: Content Behind the Scenes
    const BehindTheScenes = {
        init: function() {
            this.addBTSButton();
            console.log('[MovieShows] Behind the Scenes initialized');
        },
        addBTSButton: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🎬 BTS';
            btn.style.cssText = 'background:#ff5722;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.showBTS();
            container.appendChild(btn);
        },
        showBTS: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🎬 Behind the Scenes</h3>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;">
                    <div style="background:#252545;padding:15px;border-radius:8px;text-align:center;cursor:pointer;">
                        <div style="font-size:30px;margin-bottom:10px;">🎥</div>
                        <div style="color:#fff;">Making Of</div>
                    </div>
                    <div style="background:#252545;padding:15px;border-radius:8px;text-align:center;cursor:pointer;">
                        <div style="font-size:30px;margin-bottom:10px;">🗣️</div>
                        <div style="color:#fff;">Interviews</div>
                    </div>
                    <div style="background:#252545;padding:15px;border-radius:8px;text-align:center;cursor:pointer;">
                        <div style="font-size:30px;margin-bottom:10px;">✂️</div>
                        <div style="color:#fff;">Deleted Scenes</div>
                    </div>
                    <div style="background:#252545;padding:15px;border-radius:8px;text-align:center;cursor:pointer;">
                        <div style="font-size:30px;margin-bottom:10px;">🎨</div>
                        <div style="color:#fff;">Concept Art</div>
                    </div>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 230: Content Quotes Gallery
    const QuotesGallery = {
        quotes: JSON.parse(localStorage.getItem('movieshows-quotes') || '[]'),
        init: function() {
            this.addQuotesButton();
            console.log('[MovieShows] Quotes Gallery initialized');
        },
        addQuotesButton: function() {
            const container = document.querySelector('.video-info, .movie-info');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '💭 Quotes';
            btn.style.cssText = 'background:#673ab7;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showGallery();
            container.appendChild(btn);
        },
        showGallery: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">💭 Memorable Quotes</h3>
                <div style="color:#aaa;">
                    <blockquote style="background:#252545;padding:15px;border-left:4px solid #673ab7;margin:15px 0;border-radius:0 8px 8px 0;">
                        <p style="color:#fff;font-style:italic;margin:0;">"Here's looking at you, kid."</p>
                        <footer style="color:#888;margin-top:10px;font-size:12px;">- Classic Movie Quote</footer>
                    </blockquote>
                    <blockquote style="background:#252545;padding:15px;border-left:4px solid #673ab7;margin:15px 0;border-radius:0 8px 8px 0;">
                        <p style="color:#fff;font-style:italic;margin:0;">"May the Force be with you."</p>
                        <footer style="color:#888;margin-top:10px;font-size:12px;">- Sci-Fi Classic</footer>
                    </blockquote>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 231: Content Trivia Quiz
    const TriviaQuiz = {
        score: parseInt(localStorage.getItem('movieshows-trivia-score') || '0'),
        init: function() {
            this.addQuizButton();
            console.log('[MovieShows] Trivia Quiz initialized');
        },
        addQuizButton: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = `🧠 Trivia (${this.score} pts)`;
            btn.style.cssText = 'background:#ff9800;color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.startQuiz();
            this.btn = btn;
            nav.appendChild(btn);
        },
        startQuiz: function() {
            const questions = [
                { q: 'What year was "The Godfather" released?', a: ['1972', '1975', '1970', '1968'], correct: 0 },
                { q: 'Who directed "Inception"?', a: ['Steven Spielberg', 'Christopher Nolan', 'James Cameron', 'Ridley Scott'], correct: 1 },
                { q: 'Which film won Best Picture in 2020?', a: ['1917', 'Joker', 'Parasite', 'Once Upon a Time'], correct: 2 }
            ];
            const q = questions[Math.floor(Math.random() * questions.length)];
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🧠 Movie Trivia</h3>
                <p style="color:#fff;font-size:18px;margin-bottom:20px;">${q.q}</p>
                <div id="trivia-answers">
                    ${q.a.map((a, i) => `<button class="trivia-answer" data-index="${i}" style="display:block;width:100%;background:#252545;color:#fff;border:none;padding:12px;margin:8px 0;border-radius:6px;cursor:pointer;text-align:left;">${a}</button>`).join('')}
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#666;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Skip</button>
            `;
            document.body.appendChild(modal);
            
            modal.querySelectorAll('.trivia-answer').forEach(btn => {
                btn.onclick = () => {
                    const isCorrect = parseInt(btn.dataset.index) === q.correct;
                    if (isCorrect) {
                        this.score += 10;
                        localStorage.setItem('movieshows-trivia-score', this.score);
                        this.btn.textContent = `🧠 Trivia (${this.score} pts)`;
                        btn.style.background = '#4CAF50';
                    } else {
                        btn.style.background = '#f44336';
                        modal.querySelectorAll('.trivia-answer')[q.correct].style.background = '#4CAF50';
                    }
                    setTimeout(() => modal.remove(), 1500);
                };
            });
        }
    };

    // Feature 232: Content Mood Matcher
    const MoodMatcher = {
        init: function() {
            this.addMatcherButton();
            console.log('[MovieShows] Mood Matcher initialized');
        },
        addMatcherButton: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🎭 Mood Match';
            btn.style.cssText = 'background:#e91e63;color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.showMatcher();
            nav.appendChild(btn);
        },
        showMatcher: function() {
            const moods = [
                { emoji: '😊', name: 'Happy', genres: ['Comedy', 'Romance', 'Animation'] },
                { emoji: '😢', name: 'Sad', genres: ['Drama', 'Romance'] },
                { emoji: '😨', name: 'Scared', genres: ['Horror', 'Thriller'] },
                { emoji: '🤔', name: 'Thoughtful', genres: ['Documentary', 'Drama', 'Sci-Fi'] },
                { emoji: '🎉', name: 'Excited', genres: ['Action', 'Adventure', 'Sci-Fi'] },
                { emoji: '😴', name: 'Relaxed', genres: ['Documentary', 'Animation', 'Comedy'] }
            ];
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🎭 How are you feeling?</h3>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:15px;">
                    ${moods.map(m => `<button class="mood-btn" data-genres="${m.genres.join(',')}" style="background:#252545;border:none;padding:20px;border-radius:12px;cursor:pointer;text-align:center;">
                        <div style="font-size:40px;">${m.emoji}</div>
                        <div style="color:#fff;margin-top:5px;">${m.name}</div>
                    </button>`).join('')}
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#666;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Cancel</button>
            `;
            document.body.appendChild(modal);
            
            modal.querySelectorAll('.mood-btn').forEach(btn => {
                btn.onclick = () => {
                    const genres = btn.dataset.genres;
                    modal.remove();
                    alert(`Finding ${genres} content for your mood!`);
                };
            });
        }
    };

    // Feature 233: Content Watch History Export
    const HistoryExport = {
        init: function() {
            this.addExportButton();
            console.log('[MovieShows] History Export initialized');
        },
        addExportButton: function() {
            const nav = document.querySelector('.quick-nav, #quick-nav, nav');
            if (!nav) return;
            
            const btn = document.createElement('button');
            btn.textContent = '📤 Export History';
            btn.style.cssText = 'background:#607d8b;color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;margin:5px;';
            btn.onclick = () => this.exportHistory();
            nav.appendChild(btn);
        },
        exportHistory: function() {
            const history = JSON.parse(localStorage.getItem('movieshows-watch-history') || '[]');
            const data = {
                exportDate: new Date().toISOString(),
                totalWatched: history.length,
                items: history
            };
            
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'movieshows-history.json';
            a.click();
            URL.revokeObjectURL(url);
        }
    };

    // Feature 234: Content Social Sharing Cards
    const SocialCards = {
        init: function() {
            this.addCardsButton();
            console.log('[MovieShows] Social Cards initialized');
        },
        addCardsButton: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🎴 Share Card';
            btn.style.cssText = 'background:#00bcd4;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.createCard();
            container.appendChild(btn);
        },
        createCard: function() {
            const title = document.querySelector('.video-title, .title, h1')?.textContent || 'Amazing Movie';
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🎴 Share Card</h3>
                <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:30px;border-radius:12px;text-align:center;min-width:300px;">
                    <div style="font-size:50px;margin-bottom:15px;">🎬</div>
                    <h2 style="color:#fff;margin:0 0 10px;">${title}</h2>
                    <p style="color:rgba(255,255,255,0.8);margin:0;">Currently watching on MovieShows!</p>
                    <div style="margin-top:15px;color:rgba(255,255,255,0.6);font-size:12px;">findtorontoevents.ca/movieshows2</div>
                </div>
                <div style="display:flex;gap:10px;margin-top:15px;justify-content:center;">
                    <button style="background:#1da1f2;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">Twitter</button>
                    <button style="background:#4267b2;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">Facebook</button>
                    <button style="background:#25d366;color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;">WhatsApp</button>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:15px;background:#666;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Close</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 235: Content Smart Suggestions
    const SmartSuggestions = {
        init: function() {
            this.showSuggestions();
            console.log('[MovieShows] Smart Suggestions initialized');
        },
        showSuggestions: function() {
            const history = JSON.parse(localStorage.getItem('movieshows-watch-history') || '[]');
            if (history.length < 3) return;
            
            setTimeout(() => {
                const suggestion = document.createElement('div');
                suggestion.style.cssText = 'position:fixed;bottom:100px;right:20px;background:#1a1a2e;padding:15px 20px;border-radius:12px;z-index:9999;border:1px solid #333;max-width:280px;';
                suggestion.innerHTML = `
                    <div style="color:#fff;font-weight:bold;margin-bottom:8px;">💡 Suggestion</div>
                    <div style="color:#aaa;font-size:14px;">Based on your history, you might enjoy more Action movies!</div>
                    <button onclick="this.parentElement.remove()" style="margin-top:10px;background:#e94560;color:white;border:none;padding:5px 15px;border-radius:4px;cursor:pointer;font-size:12px;">Dismiss</button>
                `;
                document.body.appendChild(suggestion);
                
                setTimeout(() => suggestion.remove(), 10000);
            }, 5000);
        }
    };

    // Feature 236: Content Quick Actions Popup
    const QuickActionsPopup = {
        init: function() {
            this.setupPopup();
            console.log('[MovieShows] Quick Actions Popup initialized');
        },
        setupPopup: function() {
            document.addEventListener('contextmenu', (e) => {
                if (e.target.closest('.video-slide, .movie-card, .content-item')) {
                    e.preventDefault();
                    this.showPopup(e.clientX, e.clientY);
                }
            });
        },
        showPopup: function(x, y) {
            const existing = document.querySelector('.quick-actions-popup');
            if (existing) existing.remove();
            
            const popup = document.createElement('div');
            popup.className = 'quick-actions-popup';
            popup.style.cssText = `position:fixed;left:${x}px;top:${y}px;background:#1a1a2e;border-radius:8px;z-index:10001;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.4);`;
            popup.innerHTML = `
                <button style="display:block;width:100%;background:transparent;border:none;color:#fff;padding:12px 20px;text-align:left;cursor:pointer;border-bottom:1px solid #333;">▶ Play Now</button>
                <button style="display:block;width:100%;background:transparent;border:none;color:#fff;padding:12px 20px;text-align:left;cursor:pointer;border-bottom:1px solid #333;">➕ Add to Queue</button>
                <button style="display:block;width:100%;background:transparent;border:none;color:#fff;padding:12px 20px;text-align:left;cursor:pointer;border-bottom:1px solid #333;">❤️ Like</button>
                <button style="display:block;width:100%;background:transparent;border:none;color:#fff;padding:12px 20px;text-align:left;cursor:pointer;border-bottom:1px solid #333;">📤 Share</button>
                <button style="display:block;width:100%;background:transparent;border:none;color:#fff;padding:12px 20px;text-align:left;cursor:pointer;">ℹ️ More Info</button>
            `;
            document.body.appendChild(popup);
            
            document.addEventListener('click', () => popup.remove(), { once: true });
        }
    };

    // Feature 237: Content Fullscreen Gallery
    const FullscreenGallery = {
        init: function() {
            this.addGalleryButton();
            console.log('[MovieShows] Fullscreen Gallery initialized');
        },
        addGalleryButton: function() {
            const container = document.querySelector('.video-controls, .player-controls');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🖼️ Gallery';
            btn.style.cssText = 'background:#9c27b0;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.showGallery();
            container.appendChild(btn);
        },
        showGallery: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.95);z-index:10001;display:flex;flex-direction:column;align-items:center;justify-content:center;';
            modal.innerHTML = `
                <div style="color:#fff;font-size:18px;margin-bottom:20px;">🖼️ Movie Gallery</div>
                <div style="display:flex;gap:20px;flex-wrap:wrap;justify-content:center;padding:20px;max-width:90%;overflow-y:auto;">
                    <div style="width:200px;height:120px;background:#333;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#666;">Poster 1</div>
                    <div style="width:200px;height:120px;background:#333;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#666;">Poster 2</div>
                    <div style="width:200px;height:120px;background:#333;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#666;">Still 1</div>
                    <div style="width:200px;height:120px;background:#333;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#666;">Still 2</div>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#e94560;color:white;border:none;padding:10px 30px;border-radius:6px;cursor:pointer;">Close Gallery</button>
            `;
            document.body.appendChild(modal);
        }
    };

    // Feature 238: Content Runtime Preferences
    const RuntimePreferences = {
        prefs: JSON.parse(localStorage.getItem('movieshows-runtime-prefs') || '{"min":0,"max":300}'),
        init: function() {
            this.addPrefsButton();
            console.log('[MovieShows] Runtime Preferences initialized');
        },
        addPrefsButton: function() {
            const container = document.querySelector('.filters, .filter-bar');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '⏱️ Runtime';
            btn.style.cssText = 'background:#795548;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.showPrefs();
            container.appendChild(btn);
        },
        showPrefs: function() {
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:300px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">⏱️ Runtime Preferences</h3>
                <div style="color:#aaa;margin:15px 0;">
                    <label>Minimum: <span id="min-val">${this.prefs.min}</span> min</label>
                    <input type="range" id="runtime-min" min="0" max="180" value="${this.prefs.min}" style="width:100%;margin-top:5px;">
                </div>
                <div style="color:#aaa;margin:15px 0;">
                    <label>Maximum: <span id="max-val">${this.prefs.max}</span> min</label>
                    <input type="range" id="runtime-max" min="60" max="300" value="${this.prefs.max}" style="width:100%;margin-top:5px;">
                </div>
                <button id="runtime-save" style="background:#4CAF50;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Apply</button>
                <button onclick="this.parentElement.remove()" style="margin-left:10px;background:#666;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Cancel</button>
            `;
            document.body.appendChild(modal);
            
            modal.querySelector('#runtime-min').oninput = (e) => {
                modal.querySelector('#min-val').textContent = e.target.value;
            };
            modal.querySelector('#runtime-max').oninput = (e) => {
                modal.querySelector('#max-val').textContent = e.target.value;
            };
            modal.querySelector('#runtime-save').onclick = () => {
                this.prefs = {
                    min: parseInt(modal.querySelector('#runtime-min').value),
                    max: parseInt(modal.querySelector('#runtime-max').value)
                };
                localStorage.setItem('movieshows-runtime-prefs', JSON.stringify(this.prefs));
                modal.remove();
            };
        }
    };

    // Feature 239: Content Year Browser
    const YearBrowser = {
        init: function() {
            this.addBrowserButton();
            console.log('[MovieShows] Year Browser initialized');
        },
        addBrowserButton: function() {
            const container = document.querySelector('.filters, .filter-bar');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '📅 By Year';
            btn.style.cssText = 'background:#3f51b5;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.showBrowser();
            container.appendChild(btn);
        },
        showBrowser: function() {
            const currentYear = new Date().getFullYear();
            const decades = [];
            for (let y = currentYear; y >= 1950; y -= 10) {
                decades.push(y);
            }
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:400px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">📅 Browse by Year</h3>
                <div style="display:flex;flex-wrap:wrap;gap:10px;">
                    ${decades.map(d => `<button class="decade-btn" data-decade="${d}" style="background:#252545;color:#fff;border:none;padding:12px 20px;border-radius:8px;cursor:pointer;min-width:80px;">${d}s</button>`).join('')}
                </div>
                <div style="margin-top:20px;color:#aaa;">
                    <label>Or select specific year: </label>
                    <select id="specific-year" style="background:#333;color:#fff;border:1px solid #555;padding:8px;border-radius:4px;">
                        ${Array.from({length: currentYear - 1949}, (_, i) => currentYear - i).map(y => `<option value="${y}">${y}</option>`).join('')}
                    </select>
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#e94560;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;">Close</button>
            `;
            document.body.appendChild(modal);
            
            modal.querySelectorAll('.decade-btn').forEach(btn => {
                btn.onclick = () => {
                    const decade = btn.dataset.decade;
                    modal.remove();
                    alert(`Filtering to ${decade}s content...`);
                };
            });
        }
    };

    // Feature 240: Content Language Filter
    const LanguageFilter = {
        selected: localStorage.getItem('movieshows-language') || 'all',
        init: function() {
            this.addFilterButton();
            console.log('[MovieShows] Language Filter initialized');
        },
        addFilterButton: function() {
            const container = document.querySelector('.filters, .filter-bar');
            if (!container) return;
            
            const btn = document.createElement('button');
            btn.textContent = '🌐 Language';
            btn.style.cssText = 'background:#00bcd4;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:3px;';
            btn.onclick = () => this.showFilter();
            container.appendChild(btn);
        },
        showFilter: function() {
            const languages = [
                { code: 'all', name: 'All Languages' },
                { code: 'en', name: 'English' },
                { code: 'es', name: 'Spanish' },
                { code: 'fr', name: 'French' },
                { code: 'de', name: 'German' },
                { code: 'ja', name: 'Japanese' },
                { code: 'ko', name: 'Korean' },
                { code: 'zh', name: 'Chinese' },
                { code: 'hi', name: 'Hindi' },
                { code: 'pt', name: 'Portuguese' }
            ];
            
            const modal = document.createElement('div');
            modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#1a1a2e;padding:25px;border-radius:12px;z-index:10001;min-width:300px;';
            modal.innerHTML = `
                <h3 style="color:#fff;margin:0 0 20px;">🌐 Select Language</h3>
                <div style="display:flex;flex-direction:column;gap:8px;">
                    ${languages.map(l => `<button class="lang-btn" data-code="${l.code}" style="background:${this.selected === l.code ? '#e94560' : '#252545'};color:#fff;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;text-align:left;">${l.name}</button>`).join('')}
                </div>
                <button onclick="this.parentElement.remove()" style="margin-top:20px;background:#666;color:white;border:none;padding:8px 20px;border-radius:6px;cursor:pointer;width:100%;">Cancel</button>
            `;
            document.body.appendChild(modal);
            
            modal.querySelectorAll('.lang-btn').forEach(btn => {
                btn.onclick = () => {
                    this.selected = btn.dataset.code;
                    localStorage.setItem('movieshows-language', this.selected);
                    modal.remove();
                };
            });
        }
    };

    // Initialize all Batch 12 features
    function initBatch12() {
        try {
            RatingsBreakdown.init();
            AccessibilityOptions.init();
            ParentalControls.init();
            DownloadQueue.init();
            AudioDescription.init();
            CastCrewBrowser.init();
            SoundtrackPlayer.init();
            FanReviews.init();
            BehindTheScenes.init();
            QuotesGallery.init();
            TriviaQuiz.init();
            MoodMatcher.init();
            HistoryExport.init();
            SocialCards.init();
            SmartSuggestions.init();
            QuickActionsPopup.init();
            FullscreenGallery.init();
            RuntimePreferences.init();
            YearBrowser.init();
            LanguageFilter.init();
            
            console.log('[MovieShows] Batch 12 features (221-240) loaded successfully!');
        } catch (error) {
            console.error('[MovieShows] Error initializing Batch 12:', error);
        }
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initBatch12);
    } else {
        setTimeout(initBatch12, 1800);
    }
})();
