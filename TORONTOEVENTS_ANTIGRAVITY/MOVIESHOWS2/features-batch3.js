/**
 * MovieShows Premium Features v2.2
 * 20 Major Updates - Batch 3 (Features 41-60)
 */

(function() {
    'use strict';
    
    // ============================================================
    // FEATURE 41: LIVE CHAT/COMMENTS SECTION
    // ============================================================
    const LiveChat = {
        storageKey: 'movieshows-comments',
        
        getComments(movieTitle) {
            try {
                const all = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
                return all[movieTitle] || [];
            } catch { return []; }
        },
        
        addComment(movieTitle, comment) {
            const all = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
            if (!all[movieTitle]) all[movieTitle] = [];
            
            const profile = window.MovieShowsFeaturesBatch2?.UserProfiles?.getProfile() || { name: 'Anonymous', avatar: '👤' };
            
            all[movieTitle].unshift({
                id: Date.now(),
                text: comment,
                author: profile.name,
                avatar: profile.avatar,
                timestamp: Date.now(),
                likes: 0
            });
            
            localStorage.setItem(this.storageKey, JSON.stringify(all));
            return all[movieTitle];
        },
        
        showCommentsPanel(movieTitle) {
            const existing = document.getElementById('comments-panel');
            if (existing) { existing.remove(); return; }
            
            const comments = this.getComments(movieTitle);
            
            const panel = document.createElement('div');
            panel.id = 'comments-panel';
            panel.innerHTML = `
                <div style="position: fixed; right: 0; top: 0; bottom: 0; width: 380px; background: rgba(0,0,0,0.98); z-index: 99999; border-left: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column;">
                    <div style="padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="color: white; margin: 0;">💬 Comments</h3>
                            <button onclick="this.closest('#comments-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 20px;">×</button>
                        </div>
                        <p style="color: #888; font-size: 12px; margin: 5px 0 0 0;">${movieTitle}</p>
                    </div>
                    
                    <div style="padding: 15px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <textarea id="comment-input" placeholder="Write a comment..." style="width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; resize: none; height: 60px;"></textarea>
                        <button id="post-comment" style="width: 100%; margin-top: 10px; padding: 10px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Post Comment</button>
                    </div>
                    
                    <div id="comments-list" style="flex: 1; overflow-y: auto; padding: 15px;">
                        ${comments.length === 0 ? '<p style="color: #666; text-align: center;">No comments yet. Be the first!</p>' : ''}
                        ${comments.map(c => `
                            <div style="padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 10px;">
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                    <span style="font-size: 20px;">${c.avatar}</span>
                                    <span style="color: white; font-weight: bold; font-size: 13px;">${c.author}</span>
                                    <span style="color: #666; font-size: 11px; margin-left: auto;">${this.formatTime(c.timestamp)}</span>
                                </div>
                                <p style="color: #ccc; font-size: 13px; margin: 0; line-height: 1.4;">${c.text}</p>
                                <div style="margin-top: 8px; display: flex; gap: 15px;">
                                    <button class="like-comment" data-id="${c.id}" style="background: none; border: none; color: #888; cursor: pointer; font-size: 12px;">👍 ${c.likes}</button>
                                    <button style="background: none; border: none; color: #888; cursor: pointer; font-size: 12px;">💬 Reply</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            document.getElementById('post-comment')?.addEventListener('click', () => {
                const input = document.getElementById('comment-input');
                const text = input.value.trim();
                if (text) {
                    this.addComment(movieTitle, text);
                    input.value = '';
                    panel.remove();
                    this.showCommentsPanel(movieTitle);
                    window.showToast?.('Comment posted!');
                }
            });
        },
        
        formatTime(timestamp) {
            const diff = Date.now() - timestamp;
            const mins = Math.floor(diff / 60000);
            if (mins < 60) return `${mins}m ago`;
            const hours = Math.floor(diff / 3600000);
            if (hours < 24) return `${hours}h ago`;
            return `${Math.floor(diff / 86400000)}d ago`;
        }
    };
    
    // ============================================================
    // FEATURE 42: USER REVIEWS WITH RATINGS
    // ============================================================
    const UserReviews = {
        storageKey: 'movieshows-reviews',
        
        getReviews(movieTitle) {
            try {
                const all = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
                return all[movieTitle] || [];
            } catch { return []; }
        },
        
        addReview(movieTitle, review) {
            const all = JSON.parse(localStorage.getItem(this.storageKey) || '{}');
            if (!all[movieTitle]) all[movieTitle] = [];
            
            const profile = window.MovieShowsFeaturesBatch2?.UserProfiles?.getProfile() || { name: 'Anonymous', avatar: '👤' };
            
            all[movieTitle].unshift({
                id: Date.now(),
                rating: review.rating,
                title: review.title,
                text: review.text,
                author: profile.name,
                avatar: profile.avatar,
                timestamp: Date.now(),
                helpful: 0
            });
            
            localStorage.setItem(this.storageKey, JSON.stringify(all));
        },
        
        getAverageRating(movieTitle) {
            const reviews = this.getReviews(movieTitle);
            if (reviews.length === 0) return null;
            const sum = reviews.reduce((acc, r) => acc + r.rating, 0);
            return (sum / reviews.length).toFixed(1);
        },
        
        showReviewForm(movieTitle) {
            const existing = document.getElementById('review-form');
            if (existing) { existing.remove(); return; }
            
            const form = document.createElement('div');
            form.id = 'review-form';
            form.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 450px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
                        ✍️ Write a Review
                        <button onclick="this.closest('#review-form').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <p style="color: #888; margin-bottom: 20px;">${movieTitle}</p>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="color: #888; font-size: 12px; display: block; margin-bottom: 8px;">Your Rating</label>
                        <div id="review-stars" style="display: flex; gap: 8px;">
                            ${[1,2,3,4,5].map(i => `<button class="star-btn" data-rating="${i}" style="font-size: 30px; background: none; border: none; cursor: pointer;">☆</button>`).join('')}
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="color: #888; font-size: 12px; display: block; margin-bottom: 8px;">Review Title</label>
                        <input type="text" id="review-title" placeholder="Summarize your thoughts..." style="width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white;">
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="color: #888; font-size: 12px; display: block; margin-bottom: 8px;">Your Review</label>
                        <textarea id="review-text" placeholder="What did you think?" style="width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; height: 100px; resize: none;"></textarea>
                    </div>
                    
                    <button id="submit-review" style="width: 100%; padding: 14px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Submit Review</button>
                </div>
            `;
            document.body.appendChild(form);
            
            let selectedRating = 0;
            form.querySelectorAll('.star-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    selectedRating = parseInt(btn.dataset.rating);
                    form.querySelectorAll('.star-btn').forEach((s, idx) => {
                        s.textContent = idx < selectedRating ? '⭐' : '☆';
                    });
                });
            });
            
            document.getElementById('submit-review')?.addEventListener('click', () => {
                if (selectedRating === 0) {
                    window.showToast?.('Please select a rating');
                    return;
                }
                
                this.addReview(movieTitle, {
                    rating: selectedRating,
                    title: document.getElementById('review-title').value,
                    text: document.getElementById('review-text').value
                });
                
                window.showToast?.('Review submitted!');
                form.remove();
            });
        }
    };
    
    // ============================================================
    // FEATURE 43: VIDEO PLAYLISTS
    // ============================================================
    const Playlists = {
        storageKey: 'movieshows-playlists',
        
        getPlaylists() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        createPlaylist(name, description = '') {
            const playlists = this.getPlaylists();
            const newPlaylist = {
                id: 'playlist_' + Date.now(),
                name,
                description,
                videos: [],
                createdAt: Date.now()
            };
            playlists.push(newPlaylist);
            localStorage.setItem(this.storageKey, JSON.stringify(playlists));
            return newPlaylist;
        },
        
        addToPlaylist(playlistId, movie) {
            const playlists = this.getPlaylists();
            const playlist = playlists.find(p => p.id === playlistId);
            if (playlist && !playlist.videos.some(v => v.title === movie.title)) {
                playlist.videos.push({
                    title: movie.title,
                    posterUrl: movie.posterUrl,
                    trailerUrl: movie.trailerUrl,
                    addedAt: Date.now()
                });
                localStorage.setItem(this.storageKey, JSON.stringify(playlists));
                window.showToast?.(`Added to "${playlist.name}"`);
            }
        },
        
        playPlaylist(playlistId) {
            const playlists = this.getPlaylists();
            const playlist = playlists.find(p => p.id === playlistId);
            if (playlist && playlist.videos.length > 0) {
                // Store playlist for autoplay
                sessionStorage.setItem('current-playlist', JSON.stringify(playlist));
                sessionStorage.setItem('playlist-index', '0');
                window.playMovieByTitle?.(playlist.videos[0].title);
                window.showToast?.(`Playing "${playlist.name}"`);
            }
        },
        
        showPlaylistManager() {
            const playlists = this.getPlaylists();
            const existing = document.getElementById('playlist-manager');
            if (existing) { existing.remove(); return; }
            
            const manager = document.createElement('div');
            manager.id = 'playlist-manager';
            manager.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 500px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        🎵 My Playlists
                        <button onclick="this.closest('#playlist-manager').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: flex; gap: 10px; margin-bottom: 25px;">
                        <input type="text" id="new-playlist-name" placeholder="New playlist name..." style="flex: 1; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white;">
                        <button id="create-playlist-btn" style="padding: 12px 20px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Create</button>
                    </div>
                    
                    <div id="playlists-list">
                        ${playlists.length === 0 ? '<p style="color: #666; text-align: center;">No playlists yet</p>' : ''}
                        ${playlists.map(p => `
                            <div class="playlist-card" style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 15px; margin-bottom: 12px;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <h4 style="color: white; margin: 0;">${p.name}</h4>
                                        <span style="color: #888; font-size: 12px;">${p.videos.length} videos</span>
                                    </div>
                                    <div style="display: flex; gap: 8px;">
                                        <button class="play-playlist" data-id="${p.id}" style="padding: 8px 16px; background: #22c55e; color: black; border: none; border-radius: 6px; cursor: pointer; font-size: 12px;">▶ Play</button>
                                        <button class="delete-playlist" data-id="${p.id}" style="padding: 8px 12px; background: rgba(239,68,68,0.2); color: #ef4444; border: none; border-radius: 6px; cursor: pointer;">🗑️</button>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(manager);
            
            document.getElementById('create-playlist-btn')?.addEventListener('click', () => {
                const name = document.getElementById('new-playlist-name').value.trim();
                if (name) {
                    this.createPlaylist(name);
                    window.showToast?.(`Created "${name}"`);
                    manager.remove();
                    this.showPlaylistManager();
                }
            });
            
            manager.querySelectorAll('.play-playlist').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.playPlaylist(btn.dataset.id);
                    manager.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 44: TRAILERS CAROUSEL
    // ============================================================
    const TrailersCarousel = {
        currentIndex: 0,
        trailers: [],
        
        showCarousel(category = 'all') {
            const movies = window.allMoviesData || [];
            this.trailers = movies.filter(m => m.trailerUrl && m.trailerUrl.length > 10).slice(0, 20);
            
            const existing = document.getElementById('trailers-carousel');
            if (existing) { existing.remove(); return; }
            
            const carousel = document.createElement('div');
            carousel.id = 'trailers-carousel';
            carousel.innerHTML = `
                <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.95); z-index: 99999; display: flex; flex-direction: column;">
                    <div style="padding: 20px; display: flex; justify-content: space-between; align-items: center;">
                        <h2 style="color: white; margin: 0;">🎬 Trailers</h2>
                        <button onclick="this.closest('#trailers-carousel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </div>
                    
                    <div style="flex: 1; display: flex; align-items: center; justify-content: center; position: relative;">
                        <button id="carousel-prev" style="position: absolute; left: 20px; padding: 20px; background: rgba(255,255,255,0.1); border: none; border-radius: 50%; color: white; cursor: pointer; font-size: 24px;">‹</button>
                        
                        <div style="width: 80%; max-width: 900px; aspect-ratio: 16/9; background: black; border-radius: 12px; overflow: hidden;">
                            <iframe id="carousel-video" src="" style="width: 100%; height: 100%; border: none;" allow="autoplay; encrypted-media"></iframe>
                        </div>
                        
                        <button id="carousel-next" style="position: absolute; right: 20px; padding: 20px; background: rgba(255,255,255,0.1); border: none; border-radius: 50%; color: white; cursor: pointer; font-size: 24px;">›</button>
                    </div>
                    
                    <div style="padding: 20px; text-align: center;">
                        <h3 id="carousel-title" style="color: white; margin: 0 0 10px 0;"></h3>
                        <div id="carousel-dots" style="display: flex; justify-content: center; gap: 8px;"></div>
                    </div>
                </div>
            `;
            document.body.appendChild(carousel);
            
            this.updateCarousel();
            
            document.getElementById('carousel-prev')?.addEventListener('click', () => {
                this.currentIndex = (this.currentIndex - 1 + this.trailers.length) % this.trailers.length;
                this.updateCarousel();
            });
            
            document.getElementById('carousel-next')?.addEventListener('click', () => {
                this.currentIndex = (this.currentIndex + 1) % this.trailers.length;
                this.updateCarousel();
            });
        },
        
        updateCarousel() {
            const trailer = this.trailers[this.currentIndex];
            if (!trailer) return;
            
            const videoId = this.extractYouTubeId(trailer.trailerUrl);
            document.getElementById('carousel-video').src = `https://www.youtube.com/embed/${videoId}?autoplay=1&mute=1`;
            document.getElementById('carousel-title').textContent = trailer.title;
            
            const dots = document.getElementById('carousel-dots');
            dots.innerHTML = this.trailers.slice(0, 10).map((_, i) => `
                <div style="width: 10px; height: 10px; border-radius: 50%; background: ${i === this.currentIndex % 10 ? '#22c55e' : 'rgba(255,255,255,0.3)'}; cursor: pointer;" data-index="${i}"></div>
            `).join('');
        },
        
        extractYouTubeId(url) {
            const match = url?.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\s]+)/);
            return match ? match[1] : '';
        }
    };
    
    // ============================================================
    // FEATURE 45: CAST & CREW DETAILS
    // ============================================================
    const CastCrew = {
        showDetails(movie) {
            const existing = document.getElementById('cast-crew-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'cast-crew-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 500px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                        🎭 Cast & Crew
                        <button onclick="this.closest('#cast-crew-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    <p style="color: #22c55e; margin-bottom: 25px;">${movie.title}</p>
                    
                    <div style="margin-bottom: 25px;">
                        <h4 style="color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 15px;">Cast</h4>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
                            ${(movie.cast || ['Actor 1', 'Actor 2', 'Actor 3', 'Actor 4', 'Actor 5', 'Actor 6']).map(actor => `
                                <div style="text-align: center; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px;">
                                    <div style="width: 60px; height: 60px; background: rgba(255,255,255,0.1); border-radius: 50%; margin: 0 auto 10px; display: flex; align-items: center; justify-content: center; font-size: 24px;">👤</div>
                                    <div style="color: white; font-size: 13px;">${actor}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div>
                        <h4 style="color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 15px;">Crew</h4>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                            <div style="padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                                <span style="color: #888; font-size: 11px;">Director</span>
                                <div style="color: white; font-size: 13px;">${movie.director || 'Unknown'}</div>
                            </div>
                            <div style="padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                                <span style="color: #888; font-size: 11px;">Writer</span>
                                <div style="color: white; font-size: 13px;">${movie.writer || 'Unknown'}</div>
                            </div>
                            <div style="padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                                <span style="color: #888; font-size: 11px;">Producer</span>
                                <div style="color: white; font-size: 13px;">${movie.producer || 'Unknown'}</div>
                            </div>
                            <div style="padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                                <span style="color: #888; font-size: 11px;">Composer</span>
                                <div style="color: white; font-size: 13px;">${movie.composer || 'Unknown'}</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 46: BOX OFFICE DATA
    // ============================================================
    const BoxOffice = {
        // Simulated box office data
        getData(movieTitle) {
            // In a real app, this would fetch from an API
            const randomBudget = Math.floor(Math.random() * 200 + 50);
            const randomGross = Math.floor(Math.random() * 1000 + 100);
            
            return {
                budget: randomBudget * 1000000,
                domesticGross: randomGross * 1000000,
                internationalGross: randomGross * 1500000,
                totalGross: randomGross * 2500000,
                openingWeekend: Math.floor(randomGross * 300000)
            };
        },
        
        formatMoney(amount) {
            if (amount >= 1000000000) return '$' + (amount / 1000000000).toFixed(1) + 'B';
            if (amount >= 1000000) return '$' + (amount / 1000000).toFixed(0) + 'M';
            return '$' + amount.toLocaleString();
        },
        
        showBoxOffice(movie) {
            const data = this.getData(movie.title);
            
            const existing = document.getElementById('box-office-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'box-office-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                        💰 Box Office
                        <button onclick="this.closest('#box-office-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    <p style="color: #22c55e; margin-bottom: 25px;">${movie.title}</p>
                    
                    <div style="display: grid; gap: 15px;">
                        <div style="padding: 20px; background: rgba(255,255,255,0.05); border-radius: 12px;">
                            <div style="color: #888; font-size: 11px; text-transform: uppercase;">Budget</div>
                            <div style="color: white; font-size: 24px; font-weight: bold;">${this.formatMoney(data.budget)}</div>
                        </div>
                        
                        <div style="padding: 20px; background: linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05)); border-radius: 12px;">
                            <div style="color: #888; font-size: 11px; text-transform: uppercase;">Worldwide Gross</div>
                            <div style="color: #22c55e; font-size: 28px; font-weight: bold;">${this.formatMoney(data.totalGross)}</div>
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                            <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px;">
                                <div style="color: #888; font-size: 11px;">Domestic</div>
                                <div style="color: white; font-size: 18px;">${this.formatMoney(data.domesticGross)}</div>
                            </div>
                            <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px;">
                                <div style="color: #888; font-size: 11px;">International</div>
                                <div style="color: white; font-size: 18px;">${this.formatMoney(data.internationalGross)}</div>
                            </div>
                        </div>
                        
                        <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px;">
                            <div style="color: #888; font-size: 11px;">Opening Weekend</div>
                            <div style="color: white; font-size: 18px;">${this.formatMoney(data.openingWeekend)}</div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 47: CRITICS REVIEWS (AGGREGATED)
    // ============================================================
    const CriticsReviews = {
        getScores(movie) {
            // Simulated critic scores based on actual rating
            const baseRating = parseFloat(movie.rating) || 7;
            return {
                rottenTomatoes: Math.min(100, Math.floor(baseRating * 10 + Math.random() * 10)),
                metacritic: Math.min(100, Math.floor(baseRating * 9 + Math.random() * 15)),
                imdb: baseRating.toFixed(1),
                audienceScore: Math.min(100, Math.floor(baseRating * 10 + Math.random() * 5))
            };
        },
        
        showScores(movie) {
            const scores = this.getScores(movie);
            
            const existing = document.getElementById('critics-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'critics-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                        📊 Critics Scores
                        <button onclick="this.closest('#critics-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    <p style="color: #22c55e; margin-bottom: 25px;">${movie.title}</p>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                        <div style="padding: 20px; background: ${scores.rottenTomatoes >= 60 ? 'rgba(239,68,68,0.1)' : 'rgba(76,175,80,0.1)'}; border-radius: 12px; text-align: center;">
                            <div style="font-size: 32px;">🍅</div>
                            <div style="color: ${scores.rottenTomatoes >= 60 ? '#ef4444' : '#4caf50'}; font-size: 28px; font-weight: bold;">${scores.rottenTomatoes}%</div>
                            <div style="color: #888; font-size: 11px;">Rotten Tomatoes</div>
                        </div>
                        
                        <div style="padding: 20px; background: rgba(245,197,24,0.1); border-radius: 12px; text-align: center;">
                            <div style="font-size: 32px;">Ⓜ️</div>
                            <div style="color: #f5c518; font-size: 28px; font-weight: bold;">${scores.metacritic}</div>
                            <div style="color: #888; font-size: 11px;">Metacritic</div>
                        </div>
                        
                        <div style="padding: 20px; background: rgba(245,197,24,0.1); border-radius: 12px; text-align: center;">
                            <div style="font-size: 32px;">⭐</div>
                            <div style="color: #f5c518; font-size: 28px; font-weight: bold;">${scores.imdb}/10</div>
                            <div style="color: #888; font-size: 11px;">IMDb</div>
                        </div>
                        
                        <div style="padding: 20px; background: rgba(59,130,246,0.1); border-radius: 12px; text-align: center;">
                            <div style="font-size: 32px;">👥</div>
                            <div style="color: #3b82f6; font-size: 28px; font-weight: bold;">${scores.audienceScore}%</div>
                            <div style="color: #888; font-size: 11px;">Audience Score</div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 48: MULTI-PROFILE SUPPORT
    // ============================================================
    const MultiProfile = {
        storageKey: 'movieshows-profiles',
        activeKey: 'movieshows-active-profile',
        
        getProfiles() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        getActiveProfile() {
            const id = localStorage.getItem(this.activeKey);
            const profiles = this.getProfiles();
            return profiles.find(p => p.id === id) || profiles[0] || this.createDefaultProfile();
        },
        
        createDefaultProfile() {
            return { id: 'default', name: 'Default', avatar: '👤', isKids: false };
        },
        
        createProfile(name, avatar, isKids = false) {
            const profiles = this.getProfiles();
            const newProfile = {
                id: 'profile_' + Date.now(),
                name,
                avatar,
                isKids,
                createdAt: Date.now()
            };
            profiles.push(newProfile);
            localStorage.setItem(this.storageKey, JSON.stringify(profiles));
            return newProfile;
        },
        
        switchProfile(profileId) {
            localStorage.setItem(this.activeKey, profileId);
            window.showToast?.('Switched profile');
            window.location.reload();
        },
        
        showProfileSelector() {
            const profiles = this.getProfiles();
            const active = this.getActiveProfile();
            
            const existing = document.getElementById('profile-selector');
            if (existing) { existing.remove(); return; }
            
            const avatars = ['👤', '👩', '👨', '👧', '👦', '🦸', '🧙', '🎭', '🐻', '🦊'];
            
            const selector = document.createElement('div');
            selector.id = 'profile-selector';
            selector.innerHTML = `
                <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.95); z-index: 99999; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                    <h1 style="color: white; margin-bottom: 40px;">Who's watching?</h1>
                    
                    <div style="display: flex; gap: 30px; margin-bottom: 40px;">
                        ${profiles.map(p => `
                            <div class="profile-option" data-id="${p.id}" style="text-align: center; cursor: pointer; opacity: ${p.id === active.id ? 1 : 0.7}; transition: opacity 0.2s;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=${p.id === active.id ? 1 : 0.7}">
                                <div style="width: 120px; height: 120px; background: ${p.isKids ? 'linear-gradient(135deg, #22c55e, #3b82f6)' : 'linear-gradient(135deg, #6366f1, #8b5cf6)'}; border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 50px; margin-bottom: 15px; ${p.id === active.id ? 'border: 3px solid white;' : ''}">${p.avatar}</div>
                                <div style="color: white; font-size: 16px;">${p.name}</div>
                                ${p.isKids ? '<div style="color: #22c55e; font-size: 12px;">Kids</div>' : ''}
                            </div>
                        `).join('')}
                        
                        <div id="add-profile-btn" style="text-align: center; cursor: pointer; opacity: 0.5; transition: opacity 0.2s;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.5">
                            <div style="width: 120px; height: 120px; background: rgba(255,255,255,0.1); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 50px; margin-bottom: 15px;">➕</div>
                            <div style="color: white; font-size: 16px;">Add Profile</div>
                        </div>
                    </div>
                    
                    <button onclick="this.closest('#profile-selector').remove()" style="padding: 12px 30px; background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.3); border-radius: 8px; cursor: pointer;">Manage Profiles</button>
                </div>
            `;
            document.body.appendChild(selector);
            
            selector.querySelectorAll('.profile-option').forEach(opt => {
                opt.addEventListener('click', () => {
                    this.switchProfile(opt.dataset.id);
                });
            });
            
            document.getElementById('add-profile-btn')?.addEventListener('click', () => {
                const name = prompt('Profile name:');
                if (name) {
                    const avatar = avatars[Math.floor(Math.random() * avatars.length)];
                    this.createProfile(name, avatar);
                    selector.remove();
                    this.showProfileSelector();
                }
            });
        }
    };
    
    // ============================================================
    // FEATURE 49: SMART TV INTERFACE MODE
    // ============================================================
    const TVMode = {
        isEnabled: false,
        
        toggle() {
            this.isEnabled = !this.isEnabled;
            if (this.isEnabled) {
                this.enableTVMode();
            } else {
                this.disableTVMode();
            }
        },
        
        enableTVMode() {
            document.body.classList.add('tv-mode');
            
            const style = document.createElement('style');
            style.id = 'tv-mode-styles';
            style.textContent = `
                .tv-mode {
                    cursor: none !important;
                }
                .tv-mode * {
                    cursor: none !important;
                }
                .tv-mode button, .tv-mode a {
                    font-size: 18px !important;
                    padding: 15px 25px !important;
                }
                .tv-mode h1, .tv-mode h2 {
                    font-size: 2.5em !important;
                }
                .tv-mode p {
                    font-size: 1.3em !important;
                }
            `;
            document.head.appendChild(style);
            
            window.showToast?.('TV Mode enabled - Use arrow keys to navigate');
        },
        
        disableTVMode() {
            document.body.classList.remove('tv-mode');
            document.getElementById('tv-mode-styles')?.remove();
            window.showToast?.('TV Mode disabled');
        },
        
        createToggle() {
            const existing = document.getElementById('tv-mode-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'tv-mode-btn';
            btn.innerHTML = '📺 TV Mode';
            btn.style.cssText = 'position: fixed; bottom: 20px; left: 500px; padding: 10px 15px; background: rgba(0,0,0,0.8); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; cursor: pointer; z-index: 9998; font-size: 12px;';
            btn.onclick = () => this.toggle();
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 50: CONTENT SCHEDULER
    // ============================================================
    const ContentScheduler = {
        storageKey: 'movieshows-scheduled',
        
        getScheduled() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        scheduleWatch(movie, datetime) {
            const scheduled = this.getScheduled();
            scheduled.push({
                id: Date.now(),
                movie: { title: movie.title, posterUrl: movie.posterUrl },
                datetime: datetime.getTime(),
                notified: false
            });
            localStorage.setItem(this.storageKey, JSON.stringify(scheduled));
            window.showToast?.(`Scheduled "${movie.title}" for ${datetime.toLocaleString()}`);
        },
        
        checkScheduled() {
            const scheduled = this.getScheduled();
            const now = Date.now();
            
            scheduled.forEach(item => {
                if (!item.notified && item.datetime <= now) {
                    item.notified = true;
                    this.showReminder(item.movie);
                }
            });
            
            localStorage.setItem(this.storageKey, JSON.stringify(scheduled));
        },
        
        showReminder(movie) {
            const reminder = document.createElement('div');
            reminder.innerHTML = `
                <div style="position: fixed; top: 100px; right: 20px; background: linear-gradient(135deg, rgba(34,197,94,0.95), rgba(59,130,246,0.95)); border-radius: 16px; padding: 20px; z-index: 99999; max-width: 300px; animation: slideIn 0.5s ease;">
                    <h4 style="color: white; margin: 0 0 10px 0;">⏰ Time to Watch!</h4>
                    <p style="color: white; margin: 0;">"${movie.title}" is scheduled for now</p>
                    <div style="margin-top: 15px; display: flex; gap: 10px;">
                        <button onclick="window.playMovieByTitle?.('${movie.title}'); this.closest('div').parentElement.remove();" style="flex: 1; padding: 10px; background: white; color: black; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">▶ Watch Now</button>
                        <button onclick="this.closest('div').parentElement.remove();" style="padding: 10px 15px; background: rgba(255,255,255,0.2); color: white; border: none; border-radius: 8px; cursor: pointer;">Later</button>
                    </div>
                </div>
            `;
            document.body.appendChild(reminder);
            
            setTimeout(() => reminder.remove(), 30000);
        },
        
        showScheduler(movie) {
            const existing = document.getElementById('scheduler-panel');
            if (existing) { existing.remove(); return; }
            
            const now = new Date();
            const defaultTime = new Date(now.getTime() + 3600000).toISOString().slice(0, 16);
            
            const panel = document.createElement('div');
            panel.id = 'scheduler-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 350px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                        ⏰ Schedule Watch
                        <button onclick="this.closest('#scheduler-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    <p style="color: #888; margin-bottom: 25px;">${movie.title}</p>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="color: #888; font-size: 12px; display: block; margin-bottom: 8px;">When do you want to watch?</label>
                        <input type="datetime-local" id="schedule-datetime" value="${defaultTime}" style="width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white;">
                    </div>
                    
                    <button id="confirm-schedule" style="width: 100%; padding: 14px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Schedule</button>
                </div>
            `;
            document.body.appendChild(panel);
            
            document.getElementById('confirm-schedule')?.addEventListener('click', () => {
                const datetime = new Date(document.getElementById('schedule-datetime').value);
                if (datetime > new Date()) {
                    this.scheduleWatch(movie, datetime);
                    panel.remove();
                } else {
                    window.showToast?.('Please select a future time');
                }
            });
        },
        
        init() {
            // Check scheduled items every minute
            setInterval(() => this.checkScheduled(), 60000);
        }
    };
    
    // ============================================================
    // FEATURE 51: CONTENT COMPARISON
    // ============================================================
    const ContentComparison = {
        compareList: [],
        
        addToCompare(movie) {
            if (this.compareList.length >= 4) {
                window.showToast?.('Max 4 items for comparison');
                return;
            }
            if (this.compareList.some(m => m.title === movie.title)) {
                window.showToast?.('Already in comparison');
                return;
            }
            this.compareList.push(movie);
            window.showToast?.(`Added "${movie.title}" to compare (${this.compareList.length}/4)`);
            this.updateCompareButton();
        },
        
        clearCompare() {
            this.compareList = [];
            this.updateCompareButton();
        },
        
        updateCompareButton() {
            const btn = document.getElementById('compare-btn');
            if (btn) {
                btn.innerHTML = `⚖️ Compare (${this.compareList.length})`;
                btn.style.display = this.compareList.length > 0 ? 'block' : 'none';
            }
        },
        
        showComparison() {
            if (this.compareList.length < 2) {
                window.showToast?.('Add at least 2 items to compare');
                return;
            }
            
            const existing = document.getElementById('comparison-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'comparison-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.98); z-index: 99999; overflow-y: auto; padding: 30px;">
                    <div style="max-width: 1200px; margin: 0 auto;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px;">
                            <h2 style="color: white; margin: 0;">⚖️ Comparison</h2>
                            <button onclick="this.closest('#comparison-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                        </div>
                        
                        <div style="display: grid; grid-template-columns: repeat(${this.compareList.length}, 1fr); gap: 20px;">
                            ${this.compareList.map(movie => `
                                <div style="background: rgba(255,255,255,0.05); border-radius: 16px; padding: 20px;">
                                    <img src="${movie.posterUrl}" style="width: 100%; aspect-ratio: 2/3; object-fit: cover; border-radius: 12px; margin-bottom: 15px;">
                                    <h3 style="color: white; margin: 0 0 15px 0; font-size: 16px;">${movie.title}</h3>
                                    
                                    <div style="display: grid; gap: 10px;">
                                        <div style="padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                                            <div style="color: #888; font-size: 11px;">Year</div>
                                            <div style="color: white;">${movie.year || 'N/A'}</div>
                                        </div>
                                        <div style="padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                                            <div style="color: #888; font-size: 11px;">Rating</div>
                                            <div style="color: #22c55e; font-weight: bold;">⭐ ${movie.rating || 'N/A'}</div>
                                        </div>
                                        <div style="padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                                            <div style="color: #888; font-size: 11px;">Type</div>
                                            <div style="color: white;">${movie.type || 'N/A'}</div>
                                        </div>
                                        <div style="padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                                            <div style="color: #888; font-size: 11px;">Genres</div>
                                            <div style="color: white; font-size: 12px;">${movie.genres?.join(', ') || 'N/A'}</div>
                                        </div>
                                    </div>
                                    
                                    <button onclick="window.playMovieByTitle?.('${movie.title}'); this.closest('#comparison-panel').remove();" style="width: 100%; margin-top: 15px; padding: 12px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">▶ Watch</button>
                                </div>
                            `).join('')}
                        </div>
                        
                        <button onclick="window.MovieShowsFeaturesBatch3.ContentComparison.clearCompare(); this.closest('#comparison-panel').remove();" style="display: block; margin: 30px auto 0; padding: 12px 30px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 8px; cursor: pointer;">Clear Comparison</button>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        },
        
        createCompareButton() {
            const existing = document.getElementById('compare-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'compare-btn';
            btn.innerHTML = '⚖️ Compare (0)';
            btn.style.cssText = 'position: fixed; bottom: 60px; left: 500px; padding: 10px 15px; background: rgba(0,0,0,0.8); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; cursor: pointer; z-index: 9998; font-size: 12px; display: none;';
            btn.onclick = () => this.showComparison();
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 52: MOVIE TRIVIA/FACTS
    // ============================================================
    const MovieTrivia = {
        triviaData: {
            'Action': [
                'Most action movies require months of stunt training',
                'CGI has revolutionized action sequences since the 90s',
                'Many actors perform their own stunts'
            ],
            'Comedy': [
                'Improv is commonly used in comedy films',
                'The first comedy film was made in 1895',
                'Comedy is one of the oldest film genres'
            ],
            'Horror': [
                'Horror films often use infrared cameras',
                'Many iconic horror sounds are everyday objects',
                'The horror genre dates back to the silent film era'
            ],
            'Sci-Fi': [
                'Sci-fi often predicts real technology',
                'Star Wars popularized the space opera genre',
                'Many sci-fi films explore philosophical themes'
            ],
            'Drama': [
                'Drama is the most Oscar-winning genre',
                'Method acting is common in dramatic roles',
                'Drama often reflects real social issues'
            ]
        },
        
        getTrivia(movie) {
            const genres = movie.genres || [];
            const allTrivia = [];
            
            genres.forEach(genre => {
                const trivia = this.triviaData[genre];
                if (trivia) allTrivia.push(...trivia);
            });
            
            if (allTrivia.length === 0) {
                allTrivia.push('This film features amazing cinematography', 'The production took several months', 'The cast underwent extensive preparation');
            }
            
            return allTrivia[Math.floor(Math.random() * allTrivia.length)];
        },
        
        showTrivia(movie) {
            const trivia = this.getTrivia(movie);
            
            const toast = document.createElement('div');
            toast.innerHTML = `
                <div style="position: fixed; bottom: 100px; left: 50%; transform: translateX(-50%); background: linear-gradient(135deg, rgba(139,92,246,0.95), rgba(59,130,246,0.95)); border-radius: 12px; padding: 20px; z-index: 99999; max-width: 400px; text-align: center;">
                    <div style="font-size: 24px; margin-bottom: 10px;">💡</div>
                    <h4 style="color: white; margin: 0 0 10px 0;">Did You Know?</h4>
                    <p style="color: rgba(255,255,255,0.9); margin: 0; font-size: 14px;">${trivia}</p>
                </div>
            `;
            document.body.appendChild(toast);
            
            setTimeout(() => toast.remove(), 5000);
        }
    };
    
    // ============================================================
    // FEATURE 53: VIEWING ANALYTICS
    // ============================================================
    const ViewingAnalytics = {
        storageKey: 'movieshows-analytics',
        
        trackView(movie) {
            const analytics = this.getAnalytics();
            
            const today = new Date().toISOString().split('T')[0];
            if (!analytics.dailyViews[today]) analytics.dailyViews[today] = 0;
            analytics.dailyViews[today]++;
            
            const genre = movie.genres?.[0] || 'Other';
            analytics.genreViews[genre] = (analytics.genreViews[genre] || 0) + 1;
            
            const hour = new Date().getHours();
            analytics.hourlyViews[hour] = (analytics.hourlyViews[hour] || 0) + 1;
            
            analytics.totalViews++;
            
            localStorage.setItem(this.storageKey, JSON.stringify(analytics));
        },
        
        getAnalytics() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey)) || {
                    dailyViews: {},
                    genreViews: {},
                    hourlyViews: {},
                    totalViews: 0
                };
            } catch {
                return { dailyViews: {}, genreViews: {}, hourlyViews: {}, totalViews: 0 };
            }
        },
        
        showAnalytics() {
            const analytics = this.getAnalytics();
            const existing = document.getElementById('analytics-panel');
            if (existing) { existing.remove(); return; }
            
            const topGenres = Object.entries(analytics.genreViews)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);
            
            const peakHour = Object.entries(analytics.hourlyViews)
                .sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A';
            
            const panel = document.createElement('div');
            panel.id = 'analytics-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 450px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        📈 Your Viewing Analytics
                        <button onclick="this.closest('#analytics-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px;">
                        <div style="padding: 20px; background: linear-gradient(135deg, rgba(34,197,94,0.2), rgba(34,197,94,0.1)); border-radius: 12px; text-align: center;">
                            <div style="color: #22c55e; font-size: 32px; font-weight: bold;">${analytics.totalViews}</div>
                            <div style="color: #888; font-size: 12px;">Total Views</div>
                        </div>
                        <div style="padding: 20px; background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(59,130,246,0.1)); border-radius: 12px; text-align: center;">
                            <div style="color: #3b82f6; font-size: 32px; font-weight: bold;">${Object.keys(analytics.genreViews).length}</div>
                            <div style="color: #888; font-size: 12px;">Genres Explored</div>
                        </div>
                        <div style="padding: 20px; background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(139,92,246,0.1)); border-radius: 12px; text-align: center;">
                            <div style="color: #8b5cf6; font-size: 32px; font-weight: bold;">${peakHour}:00</div>
                            <div style="color: #888; font-size: 12px;">Peak Watch Time</div>
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <h4 style="color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 12px;">Top Genres</h4>
                        ${topGenres.map(([genre, count]) => `
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                                <div style="flex: 1; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
                                    <div style="height: 100%; width: ${(count / analytics.totalViews * 100)}%; background: linear-gradient(90deg, #22c55e, #3b82f6); border-radius: 4px;"></div>
                                </div>
                                <span style="color: white; font-size: 12px; min-width: 80px;">${genre}</span>
                                <span style="color: #888; font-size: 12px;">${count}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        }
    };
    
    // ============================================================
    // FEATURE 54: SMART RECOMMENDATIONS ENGINE
    // ============================================================
    const SmartRecommendations = {
        getRecommendations(limit = 10) {
            const history = window.MovieShowsFeatures?.WatchHistory?.getHistory() || [];
            const movies = window.allMoviesData || [];
            
            if (history.length === 0) {
                return movies.filter(m => m.rating >= 8).slice(0, limit);
            }
            
            // Analyze viewing patterns
            const genreWeights = {};
            const yearWeights = {};
            
            history.forEach((h, index) => {
                const movie = movies.find(m => m.title === h.title);
                if (movie) {
                    const recency = 1 / (index + 1); // More recent = higher weight
                    movie.genres?.forEach(g => {
                        genreWeights[g] = (genreWeights[g] || 0) + recency;
                    });
                    const decade = Math.floor(parseInt(movie.year) / 10) * 10;
                    yearWeights[decade] = (yearWeights[decade] || 0) + recency;
                }
            });
            
            // Score all movies
            const scored = movies
                .filter(m => !history.some(h => h.title === m.title) && m.trailerUrl)
                .map(m => {
                    let score = 0;
                    m.genres?.forEach(g => {
                        score += (genreWeights[g] || 0) * 2;
                    });
                    const decade = Math.floor(parseInt(m.year) / 10) * 10;
                    score += (yearWeights[decade] || 0);
                    score += parseFloat(m.rating || 0) / 2;
                    return { ...m, recommendationScore: score };
                })
                .sort((a, b) => b.recommendationScore - a.recommendationScore);
            
            return scored.slice(0, limit);
        },
        
        showRecommendations() {
            const recs = this.getRecommendations();
            const existing = document.getElementById('smart-recs-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'smart-recs-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 600px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        🎯 Recommended for You
                        <button onclick="this.closest('#smart-recs-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px;">
                        ${recs.map(m => `
                            <div class="rec-item" data-title="${m.title}" style="cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                <img src="${m.posterUrl}" style="width: 100%; aspect-ratio: 2/3; object-fit: cover; border-radius: 8px;">
                                <h4 style="color: white; font-size: 11px; margin: 8px 0 0 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${m.title}</h4>
                                <div style="color: #22c55e; font-size: 10px;">⭐ ${m.rating || 'N/A'}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.rec-item').forEach(item => {
                item.addEventListener('click', () => {
                    window.playMovieByTitle?.(item.dataset.title);
                    panel.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 55: CONTENT BOOKMARKS WITH TIMESTAMPS
    // ============================================================
    const Bookmarks = {
        storageKey: 'movieshows-bookmarks',
        
        getBookmarks() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        addBookmark(movie, timestamp = 0, note = '') {
            const bookmarks = this.getBookmarks();
            bookmarks.push({
                id: Date.now(),
                movieTitle: movie.title,
                posterUrl: movie.posterUrl,
                timestamp,
                note,
                createdAt: Date.now()
            });
            localStorage.setItem(this.storageKey, JSON.stringify(bookmarks));
            window.showToast?.('Bookmark added!');
        },
        
        showBookmarks() {
            const bookmarks = this.getBookmarks();
            const existing = document.getElementById('bookmarks-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'bookmarks-panel';
            panel.innerHTML = `
                <div style="position: fixed; right: 0; top: 0; bottom: 0; width: 380px; background: rgba(0,0,0,0.98); z-index: 99999; border-left: 1px solid rgba(255,255,255,0.1); display: flex; flex-direction: column;">
                    <div style="padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="color: white; margin: 0;">🔖 Bookmarks</h3>
                            <button onclick="this.closest('#bookmarks-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 20px;">×</button>
                        </div>
                    </div>
                    
                    <div style="flex: 1; overflow-y: auto; padding: 15px;">
                        ${bookmarks.length === 0 ? '<p style="color: #666; text-align: center;">No bookmarks yet</p>' : ''}
                        ${bookmarks.map(b => `
                            <div class="bookmark-item" style="display: flex; gap: 12px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 10px; cursor: pointer;">
                                <img src="${b.posterUrl}" style="width: 50px; height: 75px; object-fit: cover; border-radius: 6px;" onerror="this.style.display='none'">
                                <div style="flex: 1;">
                                    <h4 style="color: white; margin: 0 0 5px 0; font-size: 13px;">${b.movieTitle}</h4>
                                    ${b.note ? `<p style="color: #888; font-size: 11px; margin: 0 0 5px 0;">${b.note}</p>` : ''}
                                    <span style="color: #22c55e; font-size: 10px;">${this.formatTimestamp(b.timestamp)}</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        },
        
        formatTimestamp(seconds) {
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }
    };
    
    // ============================================================
    // FEATURE 56: QUICK ACTIONS MENU
    // ============================================================
    const QuickActions = {
        show(movie, x, y) {
            const existing = document.getElementById('quick-actions');
            if (existing) existing.remove();
            
            const menu = document.createElement('div');
            menu.id = 'quick-actions';
            menu.innerHTML = `
                <div style="position: fixed; left: ${x}px; top: ${y}px; background: rgba(0,0,0,0.98); border-radius: 12px; padding: 8px; z-index: 99999; border: 1px solid rgba(255,255,255,0.1); min-width: 200px;">
                    <button class="qa-btn" data-action="play" style="display: block; width: 100%; padding: 12px 15px; background: none; border: none; color: white; text-align: left; cursor: pointer; border-radius: 8px;">▶️ Play Now</button>
                    <button class="qa-btn" data-action="queue" style="display: block; width: 100%; padding: 12px 15px; background: none; border: none; color: white; text-align: left; cursor: pointer; border-radius: 8px;">📋 Add to Queue</button>
                    <button class="qa-btn" data-action="favorite" style="display: block; width: 100%; padding: 12px 15px; background: none; border: none; color: white; text-align: left; cursor: pointer; border-radius: 8px;">❤️ Add to Favorites</button>
                    <button class="qa-btn" data-action="playlist" style="display: block; width: 100%; padding: 12px 15px; background: none; border: none; color: white; text-align: left; cursor: pointer; border-radius: 8px;">🎵 Add to Playlist</button>
                    <button class="qa-btn" data-action="share" style="display: block; width: 100%; padding: 12px 15px; background: none; border: none; color: white; text-align: left; cursor: pointer; border-radius: 8px;">📤 Share</button>
                    <button class="qa-btn" data-action="compare" style="display: block; width: 100%; padding: 12px 15px; background: none; border: none; color: white; text-align: left; cursor: pointer; border-radius: 8px;">⚖️ Add to Compare</button>
                    <button class="qa-btn" data-action="info" style="display: block; width: 100%; padding: 12px 15px; background: none; border: none; color: white; text-align: left; cursor: pointer; border-radius: 8px;">ℹ️ More Info</button>
                </div>
            `;
            document.body.appendChild(menu);
            
            menu.querySelectorAll('.qa-btn').forEach(btn => {
                btn.addEventListener('mouseover', () => btn.style.background = 'rgba(255,255,255,0.1)');
                btn.addEventListener('mouseout', () => btn.style.background = 'none');
                btn.addEventListener('click', () => {
                    this.executeAction(btn.dataset.action, movie);
                    menu.remove();
                });
            });
            
            // Close on click outside
            setTimeout(() => {
                document.addEventListener('click', function close(e) {
                    if (!menu.contains(e.target)) {
                        menu.remove();
                        document.removeEventListener('click', close);
                    }
                });
            }, 100);
        },
        
        executeAction(action, movie) {
            switch (action) {
                case 'play':
                    window.playMovieByTitle?.(movie.title);
                    break;
                case 'queue':
                    window.userQueue?.push(movie);
                    window.showToast?.('Added to queue');
                    break;
                case 'favorite':
                    window.MovieShowsFeatures?.Favorites?.toggleFavorite(movie);
                    break;
                case 'playlist':
                    Playlists.showPlaylistManager();
                    break;
                case 'share':
                    window.MovieShowsFeatures?.SocialSharing?.share(movie);
                    break;
                case 'compare':
                    ContentComparison.addToCompare(movie);
                    break;
                case 'info':
                    CastCrew.showDetails(movie);
                    break;
            }
        }
    };
    
    // ============================================================
    // FEATURE 57: VOICE SEARCH (Placeholder)
    // ============================================================
    const VoiceSearch = {
        isSupported: 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window,
        
        startListening() {
            if (!this.isSupported) {
                window.showToast?.('Voice search not supported in this browser');
                return;
            }
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            
            recognition.lang = 'en-US';
            recognition.continuous = false;
            
            const indicator = document.createElement('div');
            indicator.id = 'voice-indicator';
            indicator.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.95); border-radius: 20px; padding: 40px; z-index: 99999; text-align: center;">
                    <div style="font-size: 60px; animation: pulse 1s infinite;">🎤</div>
                    <p style="color: white; margin-top: 15px;">Listening...</p>
                </div>
            `;
            document.body.appendChild(indicator);
            
            recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                indicator.remove();
                window.showToast?.(`Searching for: "${transcript}"`);
                // Trigger search
            };
            
            recognition.onerror = () => {
                indicator.remove();
                window.showToast?.('Voice search error');
            };
            
            recognition.onend = () => {
                indicator.remove();
            };
            
            recognition.start();
        },
        
        createButton() {
            const existing = document.getElementById('voice-search-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'voice-search-btn';
            btn.innerHTML = '🎤';
            btn.title = 'Voice Search';
            btn.style.cssText = 'position: fixed; top: 20px; right: 260px; padding: 10px; background: rgba(0,0,0,0.5); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 50%; cursor: pointer; z-index: 9999; font-size: 16px; width: 40px; height: 40px;';
            btn.onclick = () => this.startListening();
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 58: VIEWING REMINDERS
    // ============================================================
    const ViewingReminders = {
        storageKey: 'movieshows-reminders',
        
        setReminder(movie, reminderTime) {
            const reminders = this.getReminders();
            reminders.push({
                id: Date.now(),
                movie: { title: movie.title, posterUrl: movie.posterUrl },
                time: reminderTime,
                triggered: false
            });
            localStorage.setItem(this.storageKey, JSON.stringify(reminders));
            window.showToast?.('Reminder set!');
        },
        
        getReminders() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        checkReminders() {
            const reminders = this.getReminders();
            const now = Date.now();
            
            reminders.forEach(r => {
                if (!r.triggered && r.time <= now) {
                    r.triggered = true;
                    this.showReminder(r.movie);
                }
            });
            
            localStorage.setItem(this.storageKey, JSON.stringify(reminders));
        },
        
        showReminder(movie) {
            if (Notification.permission === 'granted') {
                new Notification('MovieShows Reminder', {
                    body: `Time to watch "${movie.title}"!`,
                    icon: movie.posterUrl
                });
            }
            
            window.showToast?.(`Reminder: Time to watch "${movie.title}"!`);
        },
        
        init() {
            // Request notification permission
            if ('Notification' in window && Notification.permission === 'default') {
                Notification.requestPermission();
            }
            
            // Check reminders every minute
            setInterval(() => this.checkReminders(), 60000);
        }
    };
    
    // ============================================================
    // FEATURE 59: CONTENT TAGS
    // ============================================================
    const ContentTags = {
        storageKey: 'movieshows-tags',
        
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
        },
        
        getMoviesByTag(tag) {
            const tags = this.getTags();
            return Object.entries(tags)
                .filter(([_, movieTags]) => movieTags.includes(tag))
                .map(([title]) => title);
        }
    };
    
    // ============================================================
    // FEATURE 60: EXPORT/IMPORT DATA
    // ============================================================
    const DataManager = {
        exportData() {
            const data = {
                version: '2.0',
                exportedAt: Date.now(),
                watchHistory: localStorage.getItem('movieshows-watch-history'),
                favorites: localStorage.getItem('movieshows-favorites'),
                ratings: localStorage.getItem('movieshows-user-ratings'),
                playlists: localStorage.getItem('movieshows-playlists'),
                watchlists: localStorage.getItem('movieshows-watchlists'),
                profile: localStorage.getItem('movieshows-user-profile'),
                settings: localStorage.getItem('movieshows-settings')
            };
            
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `movieshows-backup-${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            URL.revokeObjectURL(url);
            
            window.showToast?.('Data exported!');
        },
        
        importData(file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    
                    if (data.watchHistory) localStorage.setItem('movieshows-watch-history', data.watchHistory);
                    if (data.favorites) localStorage.setItem('movieshows-favorites', data.favorites);
                    if (data.ratings) localStorage.setItem('movieshows-user-ratings', data.ratings);
                    if (data.playlists) localStorage.setItem('movieshows-playlists', data.playlists);
                    if (data.watchlists) localStorage.setItem('movieshows-watchlists', data.watchlists);
                    if (data.profile) localStorage.setItem('movieshows-user-profile', data.profile);
                    if (data.settings) localStorage.setItem('movieshows-settings', data.settings);
                    
                    window.showToast?.('Data imported! Refreshing...');
                    setTimeout(() => window.location.reload(), 1500);
                } catch (err) {
                    window.showToast?.('Invalid backup file');
                }
            };
            reader.readAsText(file);
        },
        
        showDataManager() {
            const existing = document.getElementById('data-manager');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'data-manager';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        💾 Data Manager
                        <button onclick="this.closest('#data-manager').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; gap: 15px;">
                        <button id="export-data-btn" style="padding: 15px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 14px;">📤 Export All Data</button>
                        
                        <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                            <label style="color: white; font-size: 14px; display: block; margin-bottom: 10px;">📥 Import Data</label>
                            <input type="file" id="import-file" accept=".json" style="width: 100%; color: #888;">
                        </div>
                        
                        <button id="clear-data-btn" style="padding: 15px; background: rgba(239,68,68,0.2); color: #ef4444; border: none; border-radius: 8px; cursor: pointer; font-size: 14px;">🗑️ Clear All Data</button>
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            document.getElementById('export-data-btn')?.addEventListener('click', () => this.exportData());
            
            document.getElementById('import-file')?.addEventListener('change', (e) => {
                if (e.target.files[0]) {
                    this.importData(e.target.files[0]);
                }
            });
            
            document.getElementById('clear-data-btn')?.addEventListener('click', () => {
                if (confirm('This will delete all your MovieShows data. Continue?')) {
                    Object.keys(localStorage).forEach(key => {
                        if (key.startsWith('movieshows-')) {
                            localStorage.removeItem(key);
                        }
                    });
                    window.showToast?.('All data cleared! Refreshing...');
                    setTimeout(() => window.location.reload(), 1500);
                }
            });
        }
    };
    
    // ============================================================
    // INITIALIZATION
    // ============================================================
    function initializeBatch3Features() {
        console.log('[MovieShows] Initializing Premium Features v2.2 (Batch 3)...');
        
        setTimeout(() => {
            try {
                TVMode.createToggle();
                ContentComparison.createCompareButton();
                VoiceSearch.createButton();
                ContentScheduler.init();
                ViewingReminders.init();
                
                console.log('[MovieShows] Premium Features v2.2 initialized successfully!');
                
            } catch (e) {
                console.error('[MovieShows] Error initializing batch 3 features:', e);
            }
        }, 4000);
    }
    
    // Expose features globally
    window.MovieShowsFeaturesBatch3 = {
        LiveChat,
        UserReviews,
        Playlists,
        TrailersCarousel,
        CastCrew,
        BoxOffice,
        CriticsReviews,
        MultiProfile,
        TVMode,
        ContentScheduler,
        ContentComparison,
        MovieTrivia,
        ViewingAnalytics,
        SmartRecommendations,
        Bookmarks,
        QuickActions,
        VoiceSearch,
        ViewingReminders,
        ContentTags,
        DataManager
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeBatch3Features);
    } else {
        initializeBatch3Features();
    }
    
})();
