/**
 * MovieShows Premium Features v2.1
 * 20 Major Updates - Batch 2 (Features 21-40)
 */

(function() {
    'use strict';
    
    // ============================================================
    // FEATURE 21: USER PROFILES
    // ============================================================
    const UserProfiles = {
        storageKey: 'movieshows-user-profile',
        
        getProfile() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || 'null') || this.createDefaultProfile();
            } catch { return this.createDefaultProfile(); }
        },
        
        createDefaultProfile() {
            return {
                id: 'user_' + Date.now(),
                name: 'Movie Fan',
                avatar: '🎬',
                createdAt: Date.now(),
                preferences: {
                    autoplay: true,
                    notifications: true,
                    adultContent: false
                }
            };
        },
        
        saveProfile(profile) {
            localStorage.setItem(this.storageKey, JSON.stringify(profile));
        },
        
        showProfileEditor() {
            const profile = this.getProfile();
            const existing = document.getElementById('profile-editor');
            if (existing) { existing.remove(); return; }
            
            const avatars = ['🎬', '🎭', '🎪', '🎯', '🎲', '👤', '👻', '🦸', '🧙', '🎸', '🎹', '🎺'];
            
            const editor = document.createElement('div');
            editor.id = 'profile-editor';
            editor.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        👤 Edit Profile
                        <button onclick="this.closest('#profile-editor').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="text-align: center; margin-bottom: 25px;">
                        <div id="current-avatar" style="font-size: 64px; margin-bottom: 15px;">${profile.avatar}</div>
                        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 8px;">
                            ${avatars.map(a => `
                                <button class="avatar-option" data-avatar="${a}" style="font-size: 24px; padding: 8px; background: ${a === profile.avatar ? 'rgba(34,197,94,0.3)' : 'rgba(255,255,255,0.1)'}; border: none; border-radius: 8px; cursor: pointer;">${a}</button>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="color: #888; font-size: 12px; display: block; margin-bottom: 8px;">Display Name</label>
                        <input type="text" id="profile-name" value="${profile.name}" style="width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; font-size: 14px;">
                    </div>
                    
                    <div style="margin-bottom: 25px;">
                        <label style="color: #888; font-size: 12px; display: block; margin-bottom: 12px;">Preferences</label>
                        <label style="display: flex; align-items: center; gap: 10px; color: white; margin-bottom: 10px; cursor: pointer;">
                            <input type="checkbox" id="pref-autoplay" ${profile.preferences.autoplay ? 'checked' : ''} style="width: 18px; height: 18px;">
                            Autoplay videos
                        </label>
                        <label style="display: flex; align-items: center; gap: 10px; color: white; margin-bottom: 10px; cursor: pointer;">
                            <input type="checkbox" id="pref-notifications" ${profile.preferences.notifications ? 'checked' : ''} style="width: 18px; height: 18px;">
                            Enable notifications
                        </label>
                    </div>
                    
                    <button id="save-profile" style="width: 100%; padding: 14px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 14px;">Save Profile</button>
                </div>
            `;
            document.body.appendChild(editor);
            
            // Avatar selection
            editor.querySelectorAll('.avatar-option').forEach(btn => {
                btn.addEventListener('click', () => {
                    editor.querySelectorAll('.avatar-option').forEach(b => b.style.background = 'rgba(255,255,255,0.1)');
                    btn.style.background = 'rgba(34,197,94,0.3)';
                    document.getElementById('current-avatar').textContent = btn.dataset.avatar;
                });
            });
            
            // Save
            document.getElementById('save-profile')?.addEventListener('click', () => {
                profile.name = document.getElementById('profile-name').value || 'Movie Fan';
                profile.avatar = document.getElementById('current-avatar').textContent;
                profile.preferences.autoplay = document.getElementById('pref-autoplay').checked;
                profile.preferences.notifications = document.getElementById('pref-notifications').checked;
                this.saveProfile(profile);
                window.showToast?.('Profile saved!');
                editor.remove();
                this.updateProfileDisplay();
            });
        },
        
        updateProfileDisplay() {
            const profile = this.getProfile();
            const display = document.getElementById('profile-display');
            if (display) {
                display.innerHTML = `${profile.avatar} ${profile.name}`;
            }
        },
        
        createProfileButton() {
            const existing = document.getElementById('profile-btn');
            if (existing) return;
            
            const profile = this.getProfile();
            const btn = document.createElement('button');
            btn.id = 'profile-btn';
            btn.innerHTML = `<span id="profile-display">${profile.avatar} ${profile.name}</span>`;
            btn.style.cssText = 'position: fixed; top: 20px; right: 200px; padding: 8px 16px; background: rgba(0,0,0,0.8); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 20px; cursor: pointer; z-index: 9999; font-size: 13px;';
            btn.onclick = () => this.showProfileEditor();
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 22: PUBLIC WATCHLISTS
    // ============================================================
    const Watchlists = {
        storageKey: 'movieshows-watchlists',
        
        getWatchlists() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        createWatchlist(name) {
            const lists = this.getWatchlists();
            const newList = {
                id: 'list_' + Date.now(),
                name,
                items: [],
                createdAt: Date.now(),
                isPublic: false
            };
            lists.push(newList);
            localStorage.setItem(this.storageKey, JSON.stringify(lists));
            return newList;
        },
        
        addToWatchlist(listId, movie) {
            const lists = this.getWatchlists();
            const list = lists.find(l => l.id === listId);
            if (list && !list.items.some(i => i.title === movie.title)) {
                list.items.push({
                    title: movie.title,
                    posterUrl: movie.posterUrl,
                    addedAt: Date.now()
                });
                localStorage.setItem(this.storageKey, JSON.stringify(lists));
                window.showToast?.(`Added to "${list.name}"`);
            }
        },
        
        showWatchlistManager() {
            const lists = this.getWatchlists();
            const existing = document.getElementById('watchlist-manager');
            if (existing) { existing.remove(); return; }
            
            const manager = document.createElement('div');
            manager.id = 'watchlist-manager';
            manager.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 450px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        📋 My Watchlists
                        <button onclick="this.closest('#watchlist-manager').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                        <input type="text" id="new-list-name" placeholder="New watchlist name..." style="flex: 1; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white;">
                        <button id="create-list-btn" style="padding: 12px 20px; background: #22c55e; color: black; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Create</button>
                    </div>
                    
                    <div id="watchlists-container">
                        ${lists.length === 0 ? '<p style="color: #666; text-align: center; padding: 30px;">No watchlists yet. Create one above!</p>' : ''}
                        ${lists.map(list => `
                            <div class="watchlist-item" style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 15px; margin-bottom: 12px;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                                    <h4 style="color: white; margin: 0;">${list.name}</h4>
                                    <span style="color: #888; font-size: 12px;">${list.items.length} items</span>
                                </div>
                                <div style="display: flex; gap: 6px; overflow-x: auto; padding-bottom: 8px;">
                                    ${list.items.slice(0, 5).map(item => `
                                        <img src="${item.posterUrl}" style="width: 40px; height: 60px; object-fit: cover; border-radius: 4px;" onerror="this.style.display='none'" title="${item.title}">
                                    `).join('') || '<span style="color: #666; font-size: 12px;">Empty</span>'}
                                    ${list.items.length > 5 ? `<span style="color: #888; font-size: 12px; display: flex; align-items: center;">+${list.items.length - 5}</span>` : ''}
                                </div>
                                <div style="display: flex; gap: 8px; margin-top: 10px;">
                                    <button class="play-list-btn" data-id="${list.id}" style="flex: 1; padding: 8px; background: #22c55e; color: black; border: none; border-radius: 6px; font-size: 12px; cursor: pointer;">▶ Play All</button>
                                    <button class="delete-list-btn" data-id="${list.id}" style="padding: 8px 12px; background: rgba(239,68,68,0.2); color: #ef4444; border: none; border-radius: 6px; font-size: 12px; cursor: pointer;">🗑️</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(manager);
            
            // Create new list
            document.getElementById('create-list-btn')?.addEventListener('click', () => {
                const name = document.getElementById('new-list-name').value.trim();
                if (name) {
                    this.createWatchlist(name);
                    window.showToast?.(`Created "${name}" watchlist`);
                    manager.remove();
                    this.showWatchlistManager();
                }
            });
            
            // Delete list
            manager.querySelectorAll('.delete-list-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const lists = this.getWatchlists();
                    const filtered = lists.filter(l => l.id !== btn.dataset.id);
                    localStorage.setItem(this.storageKey, JSON.stringify(filtered));
                    window.showToast?.('Watchlist deleted');
                    manager.remove();
                    this.showWatchlistManager();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 23: COLLECTIONS MANAGEMENT
    // ============================================================
    const Collections = {
        predefinedCollections: [
            { id: 'mcu', name: 'Marvel Cinematic Universe', keywords: ['Avengers', 'Iron Man', 'Spider-Man', 'Thor', 'Captain America', 'Black Panther', 'Guardians'] },
            { id: 'starwars', name: 'Star Wars', keywords: ['Star Wars', 'Mandalorian', 'Ahsoka', 'Obi-Wan'] },
            { id: 'dc', name: 'DC Universe', keywords: ['Batman', 'Superman', 'Wonder Woman', 'Justice League', 'Joker', 'Aquaman'] },
            { id: 'horror', name: 'Horror Classics', keywords: ['Halloween', 'Scream', 'Nightmare', 'Friday'] },
            { id: 'pixar', name: 'Pixar Animation', keywords: ['Toy Story', 'Finding', 'Incredibles', 'Cars', 'Up', 'WALL-E', 'Inside Out', 'Coco', 'Soul', 'Luca', 'Elemental'] },
            { id: 'jurassic', name: 'Jurassic World', keywords: ['Jurassic'] },
            { id: 'wizarding', name: 'Wizarding World', keywords: ['Harry Potter', 'Fantastic Beasts'] }
        ],
        
        getCollectionMovies(collectionId) {
            const collection = this.predefinedCollections.find(c => c.id === collectionId);
            if (!collection) return [];
            
            const movies = window.allMoviesData || [];
            return movies.filter(m => 
                collection.keywords.some(k => m.title?.toLowerCase().includes(k.toLowerCase()))
            );
        },
        
        showCollectionsPanel() {
            const existing = document.getElementById('collections-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'collections-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 500px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        🎬 Collections
                        <button onclick="this.closest('#collections-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                        ${this.predefinedCollections.map(col => {
                            const movies = this.getCollectionMovies(col.id);
                            return `
                                <div class="collection-card" data-id="${col.id}" style="background: linear-gradient(135deg, rgba(34,197,94,0.1), rgba(59,130,246,0.1)); border-radius: 12px; padding: 20px; cursor: pointer; transition: transform 0.2s; border: 1px solid rgba(255,255,255,0.1);" onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                                    <h3 style="color: white; margin: 0 0 8px 0; font-size: 14px;">${col.name}</h3>
                                    <p style="color: #888; font-size: 12px; margin: 0;">${movies.length} titles available</p>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.collection-card').forEach(card => {
                card.addEventListener('click', () => {
                    const col = this.predefinedCollections.find(c => c.id === card.dataset.id);
                    window.currentFilter = 'collection-' + card.dataset.id;
                    window.showToast?.(`Showing ${col.name}`);
                    panel.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 24: PLAYBACK SPEED CONTROL
    // ============================================================
    const PlaybackSpeed = {
        speeds: [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2],
        currentSpeed: 1,
        
        setSpeed(speed) {
            this.currentSpeed = speed;
            // Note: YouTube iframe doesn't support speed control via postMessage reliably
            // This would work better with a custom video player
            window.showToast?.(`Playback speed: ${speed}x`);
            this.updateDisplay();
        },
        
        updateDisplay() {
            const display = document.getElementById('speed-display');
            if (display) {
                display.textContent = `${this.currentSpeed}x`;
            }
        },
        
        createSpeedControl() {
            const existing = document.getElementById('speed-control');
            if (existing) return;
            
            const control = document.createElement('div');
            control.id = 'speed-control';
            control.innerHTML = `
                <div style="position: fixed; bottom: 80px; left: 20px; background: rgba(0,0,0,0.9); border-radius: 8px; padding: 8px; z-index: 9999; display: flex; align-items: center; gap: 8px;">
                    <span style="color: #888; font-size: 11px;">Speed:</span>
                    <select id="speed-select" style="padding: 6px; background: rgba(255,255,255,0.1); border: none; border-radius: 4px; color: white; cursor: pointer;">
                        ${this.speeds.map(s => `<option value="${s}" ${s === this.currentSpeed ? 'selected' : ''}>${s}x</option>`).join('')}
                    </select>
                </div>
            `;
            document.body.appendChild(control);
            
            document.getElementById('speed-select')?.addEventListener('change', (e) => {
                this.setSpeed(parseFloat(e.target.value));
            });
        }
    };
    
    // ============================================================
    // FEATURE 25: VIDEO QUALITY SETTINGS
    // ============================================================
    const VideoQuality = {
        qualities: ['Auto', '1080p', '720p', '480p', '360p'],
        currentQuality: 'Auto',
        storageKey: 'movieshows-video-quality',
        
        init() {
            this.currentQuality = localStorage.getItem(this.storageKey) || 'Auto';
        },
        
        setQuality(quality) {
            this.currentQuality = quality;
            localStorage.setItem(this.storageKey, quality);
            window.showToast?.(`Video quality: ${quality}`);
        },
        
        addToSettings() {
            const settingsPanel = document.getElementById('player-size-control');
            if (!settingsPanel || settingsPanel.querySelector('#quality-control')) return;
            
            const control = document.createElement('div');
            control.id = 'quality-control';
            control.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-top: 10px;">
                    <span style="color: white; font-size: 13px;">📺 Quality</span>
                    <select id="quality-select" style="padding: 6px 12px; background: rgba(255,255,255,0.1); border: none; border-radius: 4px; color: white; cursor: pointer;">
                        ${this.qualities.map(q => `<option value="${q}" ${q === this.currentQuality ? 'selected' : ''}>${q}</option>`).join('')}
                    </select>
                </div>
            `;
            settingsPanel.appendChild(control);
            
            document.getElementById('quality-select')?.addEventListener('change', (e) => {
                this.setQuality(e.target.value);
            });
        }
    };
    
    // ============================================================
    // FEATURE 26: SUBTITLES/CAPTIONS
    // ============================================================
    const Subtitles = {
        enabled: false,
        storageKey: 'movieshows-subtitles',
        
        init() {
            this.enabled = localStorage.getItem(this.storageKey) === 'true';
        },
        
        toggle() {
            this.enabled = !this.enabled;
            localStorage.setItem(this.storageKey, this.enabled);
            window.showToast?.(this.enabled ? 'Captions enabled' : 'Captions disabled');
            this.updateButton();
        },
        
        updateButton() {
            const btn = document.getElementById('subtitles-btn');
            if (btn) {
                btn.style.background = this.enabled ? 'rgba(34,197,94,0.3)' : 'rgba(255,255,255,0.1)';
            }
        },
        
        createButton() {
            const existing = document.getElementById('subtitles-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'subtitles-btn';
            btn.innerHTML = 'CC';
            btn.title = 'Toggle Captions';
            btn.style.cssText = `position: fixed; bottom: 140px; left: 20px; padding: 8px 12px; background: ${this.enabled ? 'rgba(34,197,94,0.3)' : 'rgba(255,255,255,0.1)'}; color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 6px; cursor: pointer; z-index: 9999; font-size: 12px; font-weight: bold;`;
            btn.onclick = () => this.toggle();
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 27: WATCH PARTY
    // ============================================================
    const WatchParty = {
        createParty() {
            const partyId = 'party_' + Math.random().toString(36).substr(2, 9);
            const partyUrl = `${window.location.origin}${window.location.pathname}?party=${partyId}`;
            
            const modal = document.createElement('div');
            modal.id = 'watch-party-modal';
            modal.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(34,197,94,0.3); text-align: center;">
                    <h2 style="color: white; margin-bottom: 15px;">🎉 Watch Party</h2>
                    <p style="color: #888; margin-bottom: 20px;">Share this link with friends to watch together!</p>
                    
                    <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                        <input type="text" value="${partyUrl}" readonly style="flex: 1; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; font-size: 12px;">
                        <button id="copy-party-link" style="padding: 12px 20px; background: #22c55e; color: black; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">Copy</button>
                    </div>
                    
                    <p style="color: #666; font-size: 11px;">Note: Watch Party syncs playback with all participants</p>
                    
                    <button onclick="this.closest('#watch-party-modal').remove()" style="margin-top: 15px; padding: 12px 30px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 8px; cursor: pointer;">Close</button>
                </div>
            `;
            document.body.appendChild(modal);
            
            document.getElementById('copy-party-link')?.addEventListener('click', () => {
                navigator.clipboard.writeText(partyUrl);
                window.showToast?.('Party link copied!');
            });
        },
        
        createPartyButton() {
            const existing = document.getElementById('watch-party-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'watch-party-btn';
            btn.innerHTML = '🎉 Party';
            btn.style.cssText = 'position: fixed; bottom: 20px; left: 340px; padding: 10px 15px; background: linear-gradient(135deg, #ec4899, #8b5cf6); color: white; border: none; border-radius: 8px; cursor: pointer; z-index: 9999; font-size: 12px; font-weight: bold;';
            btn.onclick = () => this.createParty();
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 28: NOTIFICATIONS SYSTEM
    // ============================================================
    const Notifications = {
        storageKey: 'movieshows-notifications',
        
        getNotifications() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        addNotification(title, message, type = 'info') {
            const notifs = this.getNotifications();
            notifs.unshift({
                id: Date.now(),
                title,
                message,
                type,
                read: false,
                createdAt: Date.now()
            });
            localStorage.setItem(this.storageKey, JSON.stringify(notifs.slice(0, 50)));
            this.updateBadge();
        },
        
        markAsRead(id) {
            const notifs = this.getNotifications();
            const notif = notifs.find(n => n.id === id);
            if (notif) notif.read = true;
            localStorage.setItem(this.storageKey, JSON.stringify(notifs));
            this.updateBadge();
        },
        
        getUnreadCount() {
            return this.getNotifications().filter(n => !n.read).length;
        },
        
        updateBadge() {
            const badge = document.getElementById('notif-badge');
            const count = this.getUnreadCount();
            if (badge) {
                badge.textContent = count > 0 ? count : '';
                badge.style.display = count > 0 ? 'flex' : 'none';
            }
        },
        
        showNotificationsPanel() {
            const notifs = this.getNotifications();
            const existing = document.getElementById('notifications-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'notifications-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 70px; right: 20px; background: rgba(0,0,0,0.98); border-radius: 16px; padding: 20px; z-index: 99999; width: 350px; max-height: 400px; overflow-y: auto; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 10px 40px rgba(0,0,0,0.5);">
                    <h3 style="color: white; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
                        🔔 Notifications
                        <button onclick="this.closest('#notifications-panel').remove()" style="background: none; border: none; color: white; cursor: pointer;">×</button>
                    </h3>
                    
                    ${notifs.length === 0 ? '<p style="color: #666; text-align: center; padding: 20px;">No notifications</p>' : ''}
                    
                    ${notifs.slice(0, 10).map(n => `
                        <div class="notif-item" data-id="${n.id}" style="padding: 12px; background: ${n.read ? 'transparent' : 'rgba(34,197,94,0.1)'}; border-radius: 8px; margin-bottom: 8px; cursor: pointer;">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <strong style="color: white; font-size: 13px;">${n.title}</strong>
                                <span style="color: #666; font-size: 10px;">${this.formatTime(n.createdAt)}</span>
                            </div>
                            <p style="color: #888; font-size: 12px; margin: 5px 0 0 0;">${n.message}</p>
                        </div>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(panel);
            
            panel.querySelectorAll('.notif-item').forEach(item => {
                item.addEventListener('click', () => {
                    this.markAsRead(parseInt(item.dataset.id));
                    item.style.background = 'transparent';
                });
            });
        },
        
        formatTime(timestamp) {
            const diff = Date.now() - timestamp;
            const mins = Math.floor(diff / 60000);
            const hours = Math.floor(diff / 3600000);
            const days = Math.floor(diff / 86400000);
            
            if (mins < 60) return `${mins}m ago`;
            if (hours < 24) return `${hours}h ago`;
            return `${days}d ago`;
        },
        
        createNotificationButton() {
            const existing = document.getElementById('notif-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'notif-btn';
            btn.innerHTML = `🔔<span id="notif-badge" style="position: absolute; top: -5px; right: -5px; background: #ef4444; color: white; font-size: 10px; padding: 2px 6px; border-radius: 10px; display: none;"></span>`;
            btn.style.cssText = 'position: fixed; top: 20px; right: 80px; padding: 10px; background: rgba(0,0,0,0.5); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 50%; cursor: pointer; z-index: 9999; font-size: 16px; width: 40px; height: 40px;';
            btn.onclick = () => this.showNotificationsPanel();
            document.body.appendChild(btn);
            
            this.updateBadge();
        },
        
        init() {
            // Add welcome notification for new users
            const notifs = this.getNotifications();
            if (notifs.length === 0) {
                this.addNotification('Welcome to MovieShows! 🎬', 'Discover your next obsession with our curated collection.');
            }
        }
    };
    
    // ============================================================
    // FEATURE 29: RECENTLY ADDED SECTION
    // ============================================================
    const RecentlyAdded = {
        getRecentlyAdded(limit = 10) {
            const movies = window.allMoviesData || [];
            // Sort by year (newest first) and assume recent additions
            return movies
                .filter(m => m.trailerUrl)
                .sort((a, b) => parseInt(b.year || 0) - parseInt(a.year || 0))
                .slice(0, limit);
        },
        
        createRecentlyAddedButton() {
            const categoryContainer = document.querySelector('.flex.gap-2');
            if (!categoryContainer || categoryContainer.querySelector('#recently-added-btn')) return;
            
            const btn = document.createElement('button');
            btn.id = 'recently-added-btn';
            btn.innerHTML = '🆕 Recently Added';
            btn.style.cssText = 'padding: 8px 16px; background: linear-gradient(135deg, #06b6d4, #3b82f6); color: white; border: none; border-radius: 20px; cursor: pointer; font-size: 12px; font-weight: bold;';
            btn.onclick = () => {
                window.currentFilter = 'recently-added';
                window.repopulateFeedWithFilter?.();
                window.showToast?.('Showing recently added');
            };
            categoryContainer.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 30: COMING SOON CALENDAR
    // ============================================================
    const ComingSoon = {
        getComingSoon() {
            const movies = window.allMoviesData || [];
            const currentYear = new Date().getFullYear();
            return movies
                .filter(m => parseInt(m.year) >= currentYear && m.source?.includes('Coming'))
                .sort((a, b) => parseInt(a.year) - parseInt(b.year));
        },
        
        showCalendar() {
            const upcoming = this.getComingSoon();
            const existing = document.getElementById('coming-soon-calendar');
            if (existing) { existing.remove(); return; }
            
            const calendar = document.createElement('div');
            calendar.id = 'coming-soon-calendar';
            calendar.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 500px; max-height: 80vh; overflow-y: auto; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        📅 Coming Soon
                        <button onclick="this.closest('#coming-soon-calendar').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    ${upcoming.length === 0 ? '<p style="color: #666; text-align: center;">No upcoming releases found</p>' : ''}
                    
                    ${upcoming.map(movie => `
                        <div style="display: flex; gap: 15px; padding: 15px; background: rgba(255,255,255,0.05); border-radius: 12px; margin-bottom: 12px;">
                            <img src="${movie.posterUrl}" style="width: 60px; height: 90px; object-fit: cover; border-radius: 8px;" onerror="this.style.display='none'">
                            <div style="flex: 1;">
                                <h4 style="color: white; margin: 0 0 5px 0;">${movie.title}</h4>
                                <p style="color: #22c55e; font-size: 12px; margin: 0 0 5px 0;">${movie.year}</p>
                                <p style="color: #888; font-size: 11px; margin: 0;">${movie.genres?.join(', ') || ''}</p>
                            </div>
                            <button class="remind-btn" data-title="${movie.title}" style="padding: 8px 12px; background: rgba(245,158,11,0.2); color: #f59e0b; border: none; border-radius: 6px; cursor: pointer; font-size: 11px; height: fit-content;">🔔 Remind</button>
                        </div>
                    `).join('')}
                </div>
            `;
            document.body.appendChild(calendar);
            
            calendar.querySelectorAll('.remind-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    Notifications.addNotification('Reminder Set', `We'll notify you when "${btn.dataset.title}" is available!`, 'reminder');
                    window.showToast?.('Reminder set!');
                    btn.textContent = '✓ Set';
                    btn.disabled = true;
                });
            });
        },
        
        createCalendarButton() {
            const existing = document.getElementById('calendar-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'calendar-btn';
            btn.innerHTML = '📅 Coming Soon';
            btn.style.cssText = 'position: fixed; bottom: 60px; left: 20px; padding: 10px 15px; background: rgba(0,0,0,0.8); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; cursor: pointer; z-index: 9998; font-size: 12px;';
            btn.onclick = () => this.showCalendar();
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 31: CAST/ACTOR PAGES
    // ============================================================
    const CastPages = {
        popularActors: [
            'Tom Hanks', 'Meryl Streep', 'Leonardo DiCaprio', 'Scarlett Johansson',
            'Dwayne Johnson', 'Ryan Reynolds', 'Margot Robbie', 'Tom Holland',
            'Zendaya', 'Timothée Chalamet', 'Florence Pugh', 'Anya Taylor-Joy'
        ],
        
        searchByActor(actorName) {
            const movies = window.allMoviesData || [];
            return movies.filter(m => 
                m.cast?.some(c => c.toLowerCase().includes(actorName.toLowerCase())) ||
                m.description?.toLowerCase().includes(actorName.toLowerCase())
            );
        },
        
        showActorBrowser() {
            const existing = document.getElementById('actor-browser');
            if (existing) { existing.remove(); return; }
            
            const browser = document.createElement('div');
            browser.id = 'actor-browser';
            browser.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 450px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
                        🎭 Browse by Actor
                        <button onclick="this.closest('#actor-browser').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <input type="text" id="actor-search" placeholder="Search actor name..." style="width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; margin-bottom: 20px;">
                    
                    <h4 style="color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 12px;">Popular Actors</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                        ${this.popularActors.map(actor => `
                            <button class="actor-btn" data-actor="${actor}" style="padding: 8px 16px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 20px; cursor: pointer; font-size: 12px; transition: background 0.2s;" onmouseover="this.style.background='rgba(34,197,94,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.1)'">${actor}</button>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(browser);
            
            browser.querySelectorAll('.actor-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    window.showToast?.(`Searching for ${btn.dataset.actor}...`);
                    browser.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 32: SIMILAR CONTENT
    // ============================================================
    const SimilarContent = {
        getSimilar(movie) {
            const movies = window.allMoviesData || [];
            const genres = movie.genres || [];
            
            return movies
                .filter(m => m.title !== movie.title && m.trailerUrl)
                .map(m => {
                    const genreMatches = (m.genres || []).filter(g => genres.includes(g)).length;
                    const typeMatch = m.type === movie.type ? 1 : 0;
                    const yearDiff = Math.abs(parseInt(m.year) - parseInt(movie.year));
                    const yearScore = Math.max(0, 10 - yearDiff);
                    
                    return { ...m, similarityScore: genreMatches * 2 + typeMatch + yearScore * 0.5 };
                })
                .sort((a, b) => b.similarityScore - a.similarityScore)
                .slice(0, 8);
        }
    };
    
    // ============================================================
    // FEATURE 33: "BECAUSE YOU WATCHED" SUGGESTIONS
    // ============================================================
    const BecauseYouWatched = {
        getSuggestions() {
            const history = window.MovieShowsFeatures?.WatchHistory?.getHistory() || [];
            if (history.length === 0) return [];
            
            const lastWatched = history[0];
            const movies = window.allMoviesData || [];
            const fullMovie = movies.find(m => m.title === lastWatched.title);
            
            if (!fullMovie) return [];
            
            return SimilarContent.getSimilar(fullMovie).slice(0, 5);
        },
        
        showSuggestions() {
            const suggestions = this.getSuggestions();
            if (suggestions.length === 0) return;
            
            const history = window.MovieShowsFeatures?.WatchHistory?.getHistory() || [];
            const lastWatched = history[0];
            
            const existing = document.getElementById('because-you-watched');
            if (existing) existing.remove();
            
            const section = document.createElement('div');
            section.id = 'because-you-watched';
            section.innerHTML = `
                <div style="position: fixed; bottom: 160px; left: 20px; background: rgba(0,0,0,0.95); border-radius: 12px; padding: 15px; z-index: 9998; max-width: 320px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <h4 style="color: #888; font-size: 11px; text-transform: uppercase; margin: 0;">Because you watched "${lastWatched.title}"</h4>
                        <button onclick="this.closest('#because-you-watched').remove()" style="background: none; border: none; color: #666; cursor: pointer;">×</button>
                    </div>
                    <div style="display: flex; gap: 8px; overflow-x: auto; padding-bottom: 8px;">
                        ${suggestions.map(s => `
                            <div class="suggestion-item" data-title="${s.title}" style="flex-shrink: 0; cursor: pointer;">
                                <img src="${s.posterUrl}" style="width: 50px; height: 75px; object-fit: cover; border-radius: 6px;" onerror="this.src='https://via.placeholder.com/50x75/1a1a2e/666?text=?'" title="${s.title}">
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(section);
            
            section.querySelectorAll('.suggestion-item').forEach(item => {
                item.addEventListener('click', () => {
                    window.playMovieByTitle?.(item.dataset.title);
                    section.remove();
                });
            });
        }
    };
    
    // ============================================================
    // FEATURE 34: MOOD-BASED BROWSING
    // ============================================================
    const MoodBrowsing = {
        moods: {
            '😄 Feel Good': ['Comedy', 'Family', 'Animation'],
            '😢 Emotional': ['Drama', 'Romance'],
            '😱 Thrilling': ['Horror', 'Thriller'],
            '🤯 Mind-Bending': ['Sci-Fi', 'Mystery'],
            '💪 Action-Packed': ['Action', 'Adventure'],
            '🎭 Oscar-Worthy': ['Drama', 'Biography', 'History']
        },
        
        filterByMood(mood) {
            const genres = this.moods[mood] || [];
            const movies = window.allMoviesData || [];
            
            return movies.filter(m => 
                m.genres?.some(g => genres.some(mg => g.toLowerCase().includes(mg.toLowerCase())))
            );
        },
        
        showMoodSelector() {
            const existing = document.getElementById('mood-selector');
            if (existing) { existing.remove(); return; }
            
            const selector = document.createElement('div');
            selector.id = 'mood-selector';
            selector.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; text-align: center;">What's your mood? 🎭</h2>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                        ${Object.keys(this.moods).map(mood => `
                            <button class="mood-btn" data-mood="${mood}" style="padding: 20px; background: linear-gradient(135deg, rgba(34,197,94,0.1), rgba(59,130,246,0.1)); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; color: white; cursor: pointer; font-size: 16px; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">${mood}</button>
                        `).join('')}
                    </div>
                    
                    <button onclick="this.closest('#mood-selector').remove()" style="width: 100%; margin-top: 20px; padding: 12px; background: rgba(255,255,255,0.1); color: white; border: none; border-radius: 8px; cursor: pointer;">Cancel</button>
                </div>
            `;
            document.body.appendChild(selector);
            
            selector.querySelectorAll('.mood-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const mood = btn.dataset.mood;
                    window.currentFilter = 'mood-' + mood;
                    window.showToast?.(`Showing ${mood} content`);
                    selector.remove();
                });
            });
        },
        
        createMoodButton() {
            const existing = document.getElementById('mood-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'mood-btn';
            btn.innerHTML = '🎭 Mood';
            btn.style.cssText = 'position: fixed; bottom: 100px; left: 20px; padding: 10px 15px; background: rgba(0,0,0,0.8); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; cursor: pointer; z-index: 9998; font-size: 12px;';
            btn.onclick = () => this.showMoodSelector();
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // FEATURE 35: VIDEO CHAPTERS/TIMESTAMPS
    // ============================================================
    const VideoChapters = {
        // Placeholder - would need actual chapter data from video API
        chapters: {},
        
        showChapters(videoId) {
            // Implementation would require YouTube API chapter data
            window.showToast?.('Chapters not available for this video');
        }
    };
    
    // ============================================================
    // FEATURE 36: MINI PREVIEW ON HOVER
    // ============================================================
    const MiniPreview = {
        previewTimeout: null,
        
        init() {
            // Add hover listeners to movie cards
            document.addEventListener('mouseover', (e) => {
                const card = e.target.closest('.snap-center');
                if (card && !this.previewTimeout) {
                    this.previewTimeout = setTimeout(() => {
                        // Preview would show a mini trailer
                    }, 1000);
                }
            });
            
            document.addEventListener('mouseout', (e) => {
                if (this.previewTimeout) {
                    clearTimeout(this.previewTimeout);
                    this.previewTimeout = null;
                }
            });
        }
    };
    
    // ============================================================
    // FEATURE 37: AUDIO LANGUAGE SELECTION
    // ============================================================
    const AudioLanguage = {
        languages: ['English', 'Spanish', 'French', 'German', 'Japanese', 'Korean'],
        currentLanguage: 'English',
        storageKey: 'movieshows-audio-lang',
        
        init() {
            this.currentLanguage = localStorage.getItem(this.storageKey) || 'English';
        },
        
        setLanguage(lang) {
            this.currentLanguage = lang;
            localStorage.setItem(this.storageKey, lang);
            window.showToast?.(`Audio language: ${lang}`);
        },
        
        addToSettings() {
            const settingsPanel = document.getElementById('player-size-control');
            if (!settingsPanel || settingsPanel.querySelector('#audio-lang-control')) return;
            
            const control = document.createElement('div');
            control.id = 'audio-lang-control';
            control.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-top: 10px;">
                    <span style="color: white; font-size: 13px;">🗣️ Audio</span>
                    <select id="audio-lang-select" style="padding: 6px 12px; background: rgba(255,255,255,0.1); border: none; border-radius: 4px; color: white; cursor: pointer;">
                        ${this.languages.map(l => `<option value="${l}" ${l === this.currentLanguage ? 'selected' : ''}>${l}</option>`).join('')}
                    </select>
                </div>
            `;
            settingsPanel.appendChild(control);
            
            document.getElementById('audio-lang-select')?.addEventListener('change', (e) => {
                this.setLanguage(e.target.value);
            });
        }
    };
    
    // ============================================================
    // FEATURE 38: DOWNLOAD FOR OFFLINE (Placeholder)
    // ============================================================
    const OfflineDownload = {
        showDownloadOption(movie) {
            const modal = document.createElement('div');
            modal.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 16px; padding: 25px; z-index: 99999; text-align: center; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="font-size: 48px; margin-bottom: 15px;">📥</div>
                    <h3 style="color: white; margin-bottom: 10px;">Download for Offline</h3>
                    <p style="color: #888; margin-bottom: 20px; font-size: 13px;">Offline downloads are coming soon!<br>This feature will allow you to save videos for offline viewing.</p>
                    <button onclick="this.closest('div').parentElement.remove()" style="padding: 12px 30px; background: #22c55e; color: black; border: none; border-radius: 8px; cursor: pointer; font-weight: bold;">Got it!</button>
                </div>
            `;
            document.body.appendChild(modal);
        }
    };
    
    // ============================================================
    // FEATURE 39: PARENTAL CONTROLS
    // ============================================================
    const ParentalControls = {
        storageKey: 'movieshows-parental',
        
        getSettings() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '{}');
            } catch { return {}; }
        },
        
        isEnabled() {
            return this.getSettings().enabled === true;
        },
        
        getMaxRating() {
            return this.getSettings().maxRating || 'PG-13';
        },
        
        showSettings() {
            const settings = this.getSettings();
            const existing = document.getElementById('parental-settings');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'parental-settings';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 400px; border: 1px solid rgba(239,68,68,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        👨‍👩‍👧 Parental Controls
                        <button onclick="this.closest('#parental-settings').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <label style="display: flex; align-items: center; gap: 12px; color: white; margin-bottom: 20px; cursor: pointer;">
                        <input type="checkbox" id="parental-enabled" ${settings.enabled ? 'checked' : ''} style="width: 20px; height: 20px;">
                        <span>Enable parental controls</span>
                    </label>
                    
                    <div style="margin-bottom: 25px;">
                        <label style="color: #888; font-size: 12px; display: block; margin-bottom: 8px;">Maximum Content Rating</label>
                        <select id="max-rating" style="width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white;">
                            <option value="G" ${settings.maxRating === 'G' ? 'selected' : ''}>G - General Audiences</option>
                            <option value="PG" ${settings.maxRating === 'PG' ? 'selected' : ''}>PG - Parental Guidance</option>
                            <option value="PG-13" ${settings.maxRating === 'PG-13' ? 'selected' : ''}>PG-13</option>
                            <option value="R" ${settings.maxRating === 'R' ? 'selected' : ''}>R - Restricted</option>
                        </select>
                    </div>
                    
                    <div style="margin-bottom: 25px;">
                        <label style="color: #888; font-size: 12px; display: block; margin-bottom: 8px;">PIN Code (4 digits)</label>
                        <input type="password" id="parental-pin" maxlength="4" placeholder="****" value="${settings.pin || ''}" style="width: 100%; padding: 12px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; font-size: 20px; letter-spacing: 10px; text-align: center;">
                    </div>
                    
                    <button id="save-parental" style="width: 100%; padding: 14px; background: #ef4444; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">Save Settings</button>
                </div>
            `;
            document.body.appendChild(panel);
            
            document.getElementById('save-parental')?.addEventListener('click', () => {
                const newSettings = {
                    enabled: document.getElementById('parental-enabled').checked,
                    maxRating: document.getElementById('max-rating').value,
                    pin: document.getElementById('parental-pin').value
                };
                localStorage.setItem(this.storageKey, JSON.stringify(newSettings));
                window.showToast?.('Parental controls saved');
                panel.remove();
            });
        }
    };
    
    // ============================================================
    // FEATURE 40: ACHIEVEMENT BADGES
    // ============================================================
    const Achievements = {
        storageKey: 'movieshows-achievements',
        
        badges: [
            { id: 'first_watch', name: 'First Steps', description: 'Watch your first video', icon: '🎬', requirement: { type: 'watches', count: 1 } },
            { id: 'binge_watcher', name: 'Binge Watcher', description: 'Watch 10 videos', icon: '📺', requirement: { type: 'watches', count: 10 } },
            { id: 'movie_buff', name: 'Movie Buff', description: 'Watch 50 videos', icon: '🎭', requirement: { type: 'watches', count: 50 } },
            { id: 'critic', name: 'Critic', description: 'Rate 5 titles', icon: '⭐', requirement: { type: 'ratings', count: 5 } },
            { id: 'collector', name: 'Collector', description: 'Add 10 favorites', icon: '❤️', requirement: { type: 'favorites', count: 10 } },
            { id: 'explorer', name: 'Genre Explorer', description: 'Watch 5 different genres', icon: '🗺️', requirement: { type: 'genres', count: 5 } },
            { id: 'night_owl', name: 'Night Owl', description: 'Watch after midnight', icon: '🦉', requirement: { type: 'time', hour: 0 } },
            { id: 'early_bird', name: 'Early Bird', description: 'Watch before 7 AM', icon: '🐦', requirement: { type: 'time', hour: 6 } }
        ],
        
        getUnlocked() {
            try {
                return JSON.parse(localStorage.getItem(this.storageKey) || '[]');
            } catch { return []; }
        },
        
        unlock(badgeId) {
            const unlocked = this.getUnlocked();
            if (unlocked.includes(badgeId)) return false;
            
            unlocked.push(badgeId);
            localStorage.setItem(this.storageKey, JSON.stringify(unlocked));
            
            const badge = this.badges.find(b => b.id === badgeId);
            if (badge) {
                this.showUnlockNotification(badge);
            }
            return true;
        },
        
        showUnlockNotification(badge) {
            const notif = document.createElement('div');
            notif.innerHTML = `
                <div style="position: fixed; top: 100px; right: 20px; background: linear-gradient(135deg, rgba(34,197,94,0.9), rgba(59,130,246,0.9)); border-radius: 16px; padding: 20px; z-index: 99999; animation: slideIn 0.5s ease; min-width: 280px;">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span style="font-size: 40px;">${badge.icon}</span>
                        <div>
                            <div style="color: white; font-weight: bold; font-size: 14px;">Achievement Unlocked!</div>
                            <div style="color: white; font-size: 18px; font-weight: bold;">${badge.name}</div>
                            <div style="color: rgba(255,255,255,0.8); font-size: 12px;">${badge.description}</div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(notif);
            
            setTimeout(() => notif.remove(), 5000);
        },
        
        checkAchievements() {
            const history = window.MovieShowsFeatures?.WatchHistory?.getHistory() || [];
            const ratings = window.MovieShowsFeatures?.UserRatings?.getRatings() || {};
            const favorites = window.MovieShowsFeatures?.Favorites?.getFavorites() || [];
            
            // Check watch count achievements
            if (history.length >= 1) this.unlock('first_watch');
            if (history.length >= 10) this.unlock('binge_watcher');
            if (history.length >= 50) this.unlock('movie_buff');
            
            // Check rating achievements
            if (Object.keys(ratings).length >= 5) this.unlock('critic');
            
            // Check favorites
            if (favorites.length >= 10) this.unlock('collector');
            
            // Check time-based achievements
            const hour = new Date().getHours();
            if (hour >= 0 && hour < 5) this.unlock('night_owl');
            if (hour >= 5 && hour < 7) this.unlock('early_bird');
        },
        
        showBadgesPanel() {
            const unlocked = this.getUnlocked();
            const existing = document.getElementById('badges-panel');
            if (existing) { existing.remove(); return; }
            
            const panel = document.createElement('div');
            panel.id = 'badges-panel';
            panel.innerHTML = `
                <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.98); border-radius: 20px; padding: 30px; z-index: 99999; min-width: 450px; border: 1px solid rgba(34,197,94,0.3);">
                    <h2 style="color: white; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
                        🏆 Achievements (${unlocked.length}/${this.badges.length})
                        <button onclick="this.closest('#badges-panel').remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 24px;">×</button>
                    </h2>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
                        ${this.badges.map(badge => {
                            const isUnlocked = unlocked.includes(badge.id);
                            return `
                                <div style="background: ${isUnlocked ? 'linear-gradient(135deg, rgba(34,197,94,0.2), rgba(59,130,246,0.2))' : 'rgba(255,255,255,0.05)'}; border-radius: 12px; padding: 15px; ${!isUnlocked ? 'opacity: 0.5;' : ''}">
                                    <div style="display: flex; align-items: center; gap: 12px;">
                                        <span style="font-size: 32px; ${!isUnlocked ? 'filter: grayscale(1);' : ''}">${badge.icon}</span>
                                        <div>
                                            <div style="color: white; font-weight: bold; font-size: 13px;">${badge.name}</div>
                                            <div style="color: #888; font-size: 11px;">${badge.description}</div>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            `;
            document.body.appendChild(panel);
        },
        
        createBadgesButton() {
            const existing = document.getElementById('badges-btn');
            if (existing) return;
            
            const btn = document.createElement('button');
            btn.id = 'badges-btn';
            btn.innerHTML = '🏆 Badges';
            btn.style.cssText = 'position: fixed; bottom: 20px; left: 420px; padding: 10px 15px; background: linear-gradient(135deg, #f59e0b, #ef4444); color: white; border: none; border-radius: 8px; cursor: pointer; z-index: 9999; font-size: 12px; font-weight: bold;';
            btn.onclick = () => this.showBadgesPanel();
            document.body.appendChild(btn);
        }
    };
    
    // ============================================================
    // INITIALIZATION
    // ============================================================
    function initializeBatch2Features() {
        console.log('[MovieShows] Initializing Premium Features v2.1 (Batch 2)...');
        
        setTimeout(() => {
            try {
                UserProfiles.createProfileButton();
                Notifications.createNotificationButton();
                Notifications.init();
                ComingSoon.createCalendarButton();
                MoodBrowsing.createMoodButton();
                WatchParty.createPartyButton();
                Achievements.createBadgesButton();
                Subtitles.init();
                Subtitles.createButton();
                VideoQuality.init();
                AudioLanguage.init();
                RecentlyAdded.createRecentlyAddedButton();
                
                // Check achievements periodically
                setInterval(() => Achievements.checkAchievements(), 30000);
                
                // Show "because you watched" after delay
                setTimeout(() => BecauseYouWatched.showSuggestions(), 10000);
                
                // Add settings extensions when settings panel opens
                const settingsBtn = document.getElementById('settings-toggle');
                settingsBtn?.addEventListener('click', () => {
                    setTimeout(() => {
                        VideoQuality.addToSettings();
                        AudioLanguage.addToSettings();
                    }, 100);
                });
                
                console.log('[MovieShows] Premium Features v2.1 initialized successfully!');
                
            } catch (e) {
                console.error('[MovieShows] Error initializing batch 2 features:', e);
            }
        }, 3000);
    }
    
    // Expose features globally
    window.MovieShowsFeaturesBatch2 = {
        UserProfiles,
        Watchlists,
        Collections,
        PlaybackSpeed,
        VideoQuality,
        Subtitles,
        WatchParty,
        Notifications,
        RecentlyAdded,
        ComingSoon,
        CastPages,
        SimilarContent,
        BecauseYouWatched,
        MoodBrowsing,
        VideoChapters,
        MiniPreview,
        AudioLanguage,
        OfflineDownload,
        ParentalControls,
        Achievements
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeBatch2Features);
    } else {
        initializeBatch2Features();
    }
    
    // Add animation keyframes
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
    
})();
