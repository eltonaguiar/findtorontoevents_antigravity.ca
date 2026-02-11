// TikTok-style scroll navigation fix for MovieShows
(function () {
    "use strict";

    let initialized = false;
    let scrollContainer = null;
    let videoSlides = [];
    let currentIndex = 0;
    let isScrolling = false;
    let scrollTimeout = null;
    const SCROLL_COOLDOWN = 500;
    
    // ========== NAVIGATION STATE ==========
    let currentFilter = 'all'; // all, movies, tv, nowplaying
    let searchPanel = null;
    let filterPanel = null;
    let queuePanel = null;
    let userQueue = JSON.parse(localStorage.getItem("movieshows-queue") || "[]");
    let watchedHistory = JSON.parse(localStorage.getItem("movieshows-watched") || "[]");
    let queueViewMode = localStorage.getItem("movieshows-queue-view") || "thumbnail"; // "thumbnail" or "text"
    let queueTabMode = "queue"; // Always default to queue tab showing Up Next
    
    // ========== MUTE & VOLUME CONTROL ==========
    let isMuted = localStorage.getItem("movieshows-muted") !== "false"; // Default to muted for autoplay
    let volumeLevel = parseInt(localStorage.getItem("movieshows-volume") || "50"); // 0-100, default 50%
    let infoHidden = localStorage.getItem("movieshows-info-hidden") === "true";
    let actionPanelHidden = localStorage.getItem("movieshows-action-hidden") === "true";
    
    // ========== AUTO-SCROLL SETTINGS ==========
    let autoScrollEnabled = localStorage.getItem("movieshows-auto-scroll") !== "false"; // Default enabled
    let autoScrollDelay = parseInt(localStorage.getItem("movieshows-auto-scroll-delay") || "3"); // Delay AFTER video ends (default 3s)
    let autoScrollTimer = null;
    let autoScrollCountdown = 0;
    let autoScrollCountdownInterval = null;
    let autoScrollPaused = false; // Pause when user interacts
    let ytApiReady = false;
    let activeYTPlayer = null;
    let videoEndedWaitingForScroll = false;
    
    // ========== USER AUTH & DATA ==========
    let currentUser = JSON.parse(localStorage.getItem("movieshows-user") || "null");
    let likedMovies = JSON.parse(localStorage.getItem("movieshows-likes") || "[]");
    let watchHistory = JSON.parse(localStorage.getItem("movieshows-watch-history") || "[]");
    
    // ========== API KEYS ==========
    // YouTube API Key (for future enhanced features)
    const YOUTUBE_API_KEY = "AIzaSyBjZruHqjPi2I5XEkpfoNMO5LY-8pzbvgs";
    
    // TMDB API Credentials (for movie data)
    const TMDB_API_KEY = "b84ff7bfe35ffad8779b77bcbbda317f";
    const TMDB_READ_ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiODRmZjdiZmUzNWZmYWQ4Nzc5Yjc3YmNiYmRhMzE3ZiIsIm5iZiI6MTU4NTg2ODk2NC41Mzc5OTk5LCJzdWIiOiI1ZTg2NzBhNGE1NzQzZDAwMTEwZmU3MWUiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.zKkPzhHNhnlghJQeJJz2GddR8NEI_TzXAUgU96Ky_Q4";
    const TMDB_BASE_URL = "https://api.themoviedb.org/3";
    const TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p";
    
    function createInfoToggle() {
        if (document.getElementById("info-toggle")) return;
        
        const btn = document.createElement("button");
        btn.id = "info-toggle";
        btn.innerHTML = infoHidden ? "📝 Show Info" : "📝 Hide Info";
        btn.title = "Toggle movie title and description visibility";
        
        if (infoHidden) {
            document.body.classList.add("hide-movie-info");
        }
        
        btn.addEventListener("click", () => {
            infoHidden = !infoHidden;
            localStorage.setItem("movieshows-info-hidden", infoHidden ? "true" : "false");
            document.body.classList.toggle("hide-movie-info", infoHidden);
            btn.innerHTML = infoHidden ? "📝 Show Info" : "📝 Hide Info";
        });
        
        document.body.appendChild(btn);
    }
    
    function createActionPanelToggle() {
        if (document.getElementById("action-panel-toggle")) return;
        
        const btn = document.createElement("button");
        btn.id = "action-panel-toggle";
        
        const updateBtn = () => {
            btn.innerHTML = actionPanelHidden ? "◀" : "▶";
            btn.title = actionPanelHidden ? "Show actions (Like/List/Share)" : "Hide actions";
            btn.style.opacity = actionPanelHidden ? "1" : "0.5";
        };
        
        if (actionPanelHidden) {
            document.body.classList.add("hide-action-panel");
        }
        
        updateBtn();
        
        btn.addEventListener("click", () => {
            actionPanelHidden = !actionPanelHidden;
            localStorage.setItem("movieshows-action-hidden", actionPanelHidden ? "true" : "false");
            document.body.classList.toggle("hide-action-panel", actionPanelHidden);
            updateBtn();
        });
        
        // Allow drag to reveal (swipe from right edge)
        let dragStartX = 0;
        btn.addEventListener("touchstart", (e) => {
            dragStartX = e.touches[0].clientX;
        });
        btn.addEventListener("touchend", (e) => {
            const dragEndX = e.changedTouches[0].clientX;
            if (dragStartX - dragEndX > 50 && !actionPanelHidden) {
                // Swiped left - hide
                actionPanelHidden = true;
                localStorage.setItem("movieshows-action-hidden", "true");
                document.body.classList.add("hide-action-panel");
                updateBtn();
            } else if (dragEndX - dragStartX > 50 && actionPanelHidden) {
                // Swiped right - show
                actionPanelHidden = false;
                localStorage.setItem("movieshows-action-hidden", "false");
                document.body.classList.remove("hide-action-panel");
                updateBtn();
            }
        });
        
        document.body.appendChild(btn);
    }
    
    function createMuteControl() {
        if (document.getElementById("mute-control")) return;
        
        const btn = document.createElement("button");
        btn.id = "mute-control";
        
        const updateMuteButton = () => {
            if (isMuted) {
                btn.innerHTML = "🔇 Click to Unmute";
                btn.style.background = "rgba(239, 68, 68, 0.95)"; // Red when muted
                btn.style.borderColor = "#ef4444";
                btn.style.animation = "pulse-mute 1.5s infinite";
            } else {
                btn.innerHTML = "🔊 Sound On";
                btn.style.background = "rgba(34, 197, 94, 0.9)"; // Green when unmuted
                btn.style.borderColor = "#22c55e";
                btn.style.animation = "none";
            }
            // Also update any center overlay
            updateCenterMuteOverlay();
        };
        
        btn.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 20px;
            z-index: 10001;
            color: white;
            border: 3px solid #ef4444;
            padding: 16px 28px;
            border-radius: 30px;
            cursor: pointer;
            font-size: 17px;
            font-weight: bold;
            backdrop-filter: blur(10px);
            transition: all 0.2s;
            box-shadow: 0 6px 25px rgba(239, 68, 68, 0.5);
            animation: pulse-mute 1.5s infinite;
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        `;
        
        // Add pulse animation for muted state
        if (!document.getElementById("mute-animation-style")) {
            const style = document.createElement("style");
            style.id = "mute-animation-style";
            style.textContent = `
                @keyframes pulse-mute {
                    0%, 100% { transform: scale(1); box-shadow: 0 6px 25px rgba(239, 68, 68, 0.5); }
                    50% { transform: scale(1.08); box-shadow: 0 8px 35px rgba(239, 68, 68, 0.8); }
                }
                @keyframes bounce-attention {
                    0%, 20%, 50%, 80%, 100% { transform: translateY(0) scale(1); }
                    40% { transform: translateY(-15px) scale(1.1); }
                    60% { transform: translateY(-8px) scale(1.05); }
                }
            `;
            document.head.appendChild(style);
        }
        
        updateMuteButton();
        btn.title = "Toggle sound on/off. Click to unmute videos.";
        
        btn.addEventListener("mouseenter", () => {
            btn.style.transform = "scale(1.12)";
            btn.style.animation = "none";
        });
        btn.addEventListener("mouseleave", () => {
            btn.style.transform = "";
            if (isMuted) btn.style.animation = "pulse-mute 1.5s infinite";
        });
        
        btn.addEventListener("click", () => {
            toggleMute();
        });
        
        document.body.appendChild(btn);
        console.log("[MovieShows] Mute control created");
        
        // Create center screen overlay for first-time users when muted
        createCenterMuteOverlay();
    }
    
    function toggleMute() {
        isMuted = !isMuted;
        localStorage.setItem("movieshows-muted", isMuted ? "true" : "false");
        
        // Update bottom-left button
        const btn = document.getElementById("mute-control");
        if (btn) {
            if (isMuted) {
                btn.innerHTML = "🔇 Click to Unmute";
                btn.style.background = "rgba(239, 68, 68, 0.95)";
                btn.style.borderColor = "#ef4444";
                btn.style.animation = "pulse-mute 1.5s infinite";
            } else {
                btn.innerHTML = "🔊 Sound On";
                btn.style.background = "rgba(34, 197, 94, 0.9)";
                btn.style.borderColor = "#22c55e";
                btn.style.animation = "none";
            }
        }
        
        applyMuteStateToAllVideos();
        updateCenterMuteOverlay();
        updateVolumeControlUI();
        console.log(`[MovieShows] Sound ${isMuted ? 'muted' : 'unmuted'}`);
        showToast(isMuted ? "Sound muted" : "Sound enabled!");
    }
    
    function createCenterMuteOverlay() {
        // Remove existing to recreate fresh
        const existingOverlay = document.getElementById("center-mute-overlay");
        if (existingOverlay) existingOverlay.remove();
        
        // Only create if actually muted
        if (!isMuted) {
            console.log("[MovieShows] Sound not muted, skipping overlay");
            return;
        }
        
        console.log("[MovieShows] Creating center mute overlay (muted state: " + isMuted + ")");
        
        const overlay = document.createElement("div");
        overlay.id = "center-mute-overlay";
        overlay.innerHTML = `
            <div id="center-mute-clickable" style="
                display: flex; 
                flex-direction: column; 
                align-items: center; 
                gap: 20px;
                cursor: pointer;
                padding: 30px;
                border-radius: 20px;
                transition: all 0.2s;
            ">
                <div style="font-size: 80px; line-height: 1; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));">🔇</div>
                <div style="font-size: 26px; font-weight: bold; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">Audio is Muted</div>
                <div style="
                    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                    color: white;
                    border: none;
                    padding: 20px 50px;
                    border-radius: 35px;
                    font-size: 22px;
                    font-weight: bold;
                    box-shadow: 0 6px 25px rgba(239, 68, 68, 0.6);
                    animation: pulse-button 2s infinite;
                ">🔊 TAP TO ENABLE SOUND</div>
                <div style="font-size: 14px; opacity: 0.8; margin-top: 5px;">or press <kbd style="background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 6px; font-family: monospace;">M</kbd> key</div>
            </div>
        `;
        overlay.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10002;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 20px;
            border-radius: 25px;
            text-align: center;
            backdrop-filter: blur(15px);
            box-shadow: 0 15px 60px rgba(0,0,0,0.8);
            display: block;
            animation: fadeIn 0.3s ease;
            border: 2px solid rgba(239, 68, 68, 0.5);
        `;
        
        // Add animations
        if (!document.getElementById("fade-animation-style")) {
            const style = document.createElement("style");
            style.id = "fade-animation-style";
            style.textContent = `
                @keyframes fadeIn { from { opacity: 0; transform: translate(-50%, -50%) scale(0.9); } to { opacity: 1; transform: translate(-50%, -50%) scale(1); } }
                @keyframes fadeOut { from { opacity: 1; } to { opacity: 0; } }
                @keyframes pulse-button { 
                    0%, 100% { transform: scale(1); box-shadow: 0 6px 25px rgba(239, 68, 68, 0.6); } 
                    50% { transform: scale(1.03); box-shadow: 0 8px 35px rgba(239, 68, 68, 0.8); } 
                }
                /* Volume slider styling */
                #volume-slider::-webkit-slider-thumb {
                    -webkit-appearance: none;
                    appearance: none;
                    width: 16px;
                    height: 16px;
                    border-radius: 50%;
                    background: #22c55e;
                    cursor: pointer;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                    transition: all 0.15s;
                }
                #volume-slider::-webkit-slider-thumb:hover {
                    transform: scale(1.2);
                    background: #16a34a;
                }
                #volume-slider::-moz-range-thumb {
                    width: 16px;
                    height: 16px;
                    border-radius: 50%;
                    background: #22c55e;
                    cursor: pointer;
                    border: none;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(overlay);
        
        // Make the ENTIRE clickable area work for unmuting
        const clickableArea = document.getElementById("center-mute-clickable");
        if (clickableArea) {
            clickableArea.addEventListener("click", (e) => {
                e.stopPropagation();
                toggleMute();
            });
            clickableArea.addEventListener("mouseenter", () => {
                clickableArea.style.background = "rgba(239, 68, 68, 0.15)";
                clickableArea.style.transform = "scale(1.02)";
            });
            clickableArea.addEventListener("mouseleave", () => {
                clickableArea.style.background = "transparent";
                clickableArea.style.transform = "scale(1)";
            });
        }
        
        // Clicking outside the clickable area dismisses temporarily
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) {
                overlay.style.display = "none";
                setTimeout(() => {
                    if (isMuted && overlay) {
                        overlay.style.display = "block";
                    }
                }, 30000);
            }
        });
        
        console.log("[MovieShows] Center mute overlay created");
    }
    
    function updateCenterMuteOverlay() {
        const overlay = document.getElementById("center-mute-overlay");
        if (isMuted) {
            // If muted and overlay doesn't exist, create it
            if (!overlay) {
                createCenterMuteOverlay();
            } else {
                overlay.style.display = "block";
            }
        } else {
            // If not muted, hide the overlay
            if (overlay) {
                overlay.style.display = "none";
            }
        }
    }
    
    function applyMuteStateToAllVideos() {
        const muteValue = isMuted ? 1 : 0;
        
        // Update all data-src attributes for future loads
        const allIframes = document.querySelectorAll('iframe[data-src*="youtube"]');
        allIframes.forEach(iframe => {
            const dataSrc = iframe.getAttribute('data-src');
            if (dataSrc) {
                const newDataSrc = dataSrc.replace(/mute=\d/, `mute=${muteValue}`);
                iframe.setAttribute('data-src', newDataSrc);
            }
        });
        
        // Update the currently playing video's src
        if (currentlyPlayingIframe) {
            const currentSrc = currentlyPlayingIframe.getAttribute('src');
            if (currentSrc && currentSrc.includes('youtube')) {
                const newSrc = currentSrc.replace(/mute=\d/, `mute=${muteValue}`);
                if (newSrc !== currentSrc) {
                    console.log(`[MovieShows] Updating current video mute state to: ${isMuted ? 'muted' : 'unmuted'}`);
                    currentlyPlayingIframe.src = newSrc;
                }
            }
        }
    }
    
    function getMuteParam() {
        return isMuted ? 1 : 0;
    }

    // ========== NAVIGATION PANELS ==========
    
    function createPanelBase(id, title) {
        const panel = document.createElement("div");
        panel.id = id;
        panel.style.cssText = `
            position: fixed;
            top: 0;
            right: -400px;
            width: 380px;
            max-width: 90vw;
            height: 100vh;
            background: rgba(15, 15, 20, 0.98);
            backdrop-filter: blur(20px);
            z-index: 10001;
            transition: right 0.3s ease;
            overflow-y: auto;
            border-left: 1px solid rgba(255,255,255,0.1);
            box-shadow: -10px 0 30px rgba(0,0,0,0.5);
        `;
        
        const header = document.createElement("div");
        header.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            position: sticky;
            top: 0;
            background: rgba(15, 15, 20, 0.98);
            z-index: 10;
        `;
        
        const titleEl = document.createElement("h2");
        titleEl.textContent = title;
        titleEl.style.cssText = "color: white; font-size: 20px; font-weight: bold; margin: 0;";
        
        const closeBtn = document.createElement("button");
        closeBtn.innerHTML = "✕";
        closeBtn.style.cssText = `
            background: rgba(255,255,255,0.1);
            border: none;
            color: white;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            transition: all 0.2s;
        `;
        closeBtn.addEventListener("mouseenter", () => closeBtn.style.background = "rgba(255,255,255,0.2)");
        closeBtn.addEventListener("mouseleave", () => closeBtn.style.background = "rgba(255,255,255,0.1)");
        closeBtn.addEventListener("click", () => closePanel(panel));
        
        header.appendChild(titleEl);
        header.appendChild(closeBtn);
        panel.appendChild(header);
        
        const content = document.createElement("div");
        content.className = "panel-content";
        content.style.cssText = "padding: 20px;";
        panel.appendChild(content);
        
        document.body.appendChild(panel);
        return panel;
    }
    
    function openPanel(panel) {
        // Close any other open panels
        [searchPanel, filterPanel, queuePanel].forEach(p => {
            if (p && p !== panel) closePanel(p);
        });
        panel.style.right = "0";
    }
    
    function closePanel(panel) {
        if (panel) panel.style.right = "-400px";
    }
    
    function createSearchPanel() {
        if (searchPanel) return searchPanel;
        
        searchPanel = createPanelBase("search-panel", "Search & Browse");
        const content = searchPanel.querySelector(".panel-content");
        
        // Search input
        const searchBox = document.createElement("div");
        searchBox.style.cssText = "margin-bottom: 16px;";
        searchBox.innerHTML = `
            <div style="position: relative;">
                <input type="text" id="movie-search-input" placeholder="Search movies & shows..." 
                    style="width: 100%; padding: 14px 14px 14px 45px; background: rgba(255,255,255,0.1); 
                    border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; color: white; 
                    font-size: 16px; outline: none; transition: all 0.2s;">
                <svg style="position: absolute; left: 14px; top: 50%; transform: translateY(-50%); width: 20px; height: 20px; color: #888;" 
                    xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
            </div>
        `;
        content.appendChild(searchBox);
        
        // Filter buttons (Movies / TV / All)
        const filterBox = document.createElement("div");
        filterBox.id = "search-filter-box";
        filterBox.style.cssText = "display: flex; gap: 8px; margin-bottom: 16px;";
        filterBox.innerHTML = `
            <button id="search-filter-all" class="search-filter-btn ${currentFilter === 'all' ? 'active' : ''}" 
                style="flex: 1; padding: 10px; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; 
                background: ${currentFilter === 'all' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255,255,255,0.05)'}; 
                color: ${currentFilter === 'all' ? '#22c55e' : '#888'}; cursor: pointer; font-weight: bold;
                transition: all 0.2s;" title="Show all content">
                📺 All
            </button>
            <button id="search-filter-movies" class="search-filter-btn ${currentFilter === 'movies' ? 'active' : ''}" 
                style="flex: 1; padding: 10px; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; 
                background: ${currentFilter === 'movies' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255,255,255,0.05)'}; 
                color: ${currentFilter === 'movies' ? '#22c55e' : '#888'}; cursor: pointer; font-weight: bold;
                transition: all 0.2s;" title="Show only movies">
                🎬 Movies
            </button>
            <button id="search-filter-tv" class="search-filter-btn ${currentFilter === 'tv' ? 'active' : ''}" 
                style="flex: 1; padding: 10px; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; 
                background: ${currentFilter === 'tv' ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255,255,255,0.05)'}; 
                color: ${currentFilter === 'tv' ? '#22c55e' : '#888'}; cursor: pointer; font-weight: bold;
                transition: all 0.2s;" title="Show only TV shows">
                📺 TV Shows
            </button>
        `;
        content.appendChild(filterBox);
        
        // Add filter button handlers
        filterBox.querySelector("#search-filter-all").addEventListener("click", () => {
            currentFilter = 'all';
            updateSearchFilterButtons();
            performSearch(document.getElementById("movie-search-input")?.value || "");
        });
        filterBox.querySelector("#search-filter-movies").addEventListener("click", () => {
            currentFilter = 'movies';
            updateSearchFilterButtons();
            performSearch(document.getElementById("movie-search-input")?.value || "");
        });
        filterBox.querySelector("#search-filter-tv").addEventListener("click", () => {
            currentFilter = 'tv';
            updateSearchFilterButtons();
            performSearch(document.getElementById("movie-search-input")?.value || "");
        });
        
        // Results container
        const results = document.createElement("div");
        results.id = "search-results";
        results.style.cssText = "display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;";
        content.appendChild(results);
        
        // Search functionality
        const input = searchBox.querySelector("#movie-search-input");
        input.addEventListener("focus", () => {
            input.style.borderColor = "#22c55e";
            input.style.background = "rgba(255,255,255,0.15)";
        });
        input.addEventListener("blur", () => {
            input.style.borderColor = "rgba(255,255,255,0.2)";
            input.style.background = "rgba(255,255,255,0.1)";
        });
        
        let searchTimeout;
        input.addEventListener("input", (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => performSearch(e.target.value), 300);
        });
        
        // Show initial results
        setTimeout(() => performSearch(""), 100);
        
        return searchPanel;
    }
    
    function updateSearchFilterButtons() {
        const filterBox = document.getElementById("search-filter-box");
        if (!filterBox) return;
        
        filterBox.querySelectorAll(".search-filter-btn").forEach(btn => {
            const isAll = btn.id === "search-filter-all" && currentFilter === 'all';
            const isMovies = btn.id === "search-filter-movies" && currentFilter === 'movies';
            const isTV = btn.id === "search-filter-tv" && currentFilter === 'tv';
            const isActive = isAll || isMovies || isTV;
            
            btn.style.background = isActive ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255,255,255,0.05)';
            btn.style.color = isActive ? '#22c55e' : '#888';
            btn.style.borderColor = isActive ? '#22c55e' : 'rgba(255,255,255,0.2)';
        });
    }
    
    function performSearch(query) {
        const results = document.getElementById("search-results");
        if (!results) return;
        
        let filtered = allMoviesData;
        
        if (query.trim()) {
            const q = query.toLowerCase();
            filtered = allMoviesData.filter(m => 
                m.title?.toLowerCase().includes(q) ||
                m.description?.toLowerCase().includes(q) ||
                m.genres?.some(g => g.toLowerCase().includes(q))
            );
        }
        
        // Apply category filter
        if (currentFilter === 'movies') {
            filtered = filtered.filter(m => !m.type || m.type === 'movie');
        } else if (currentFilter === 'tv') {
            filtered = filtered.filter(m => m.type === 'tv' || m.type === 'series');
        } else if (currentFilter === 'nowplaying') {
            filtered = filtered.filter(m => m.source === 'Now Playing' || m.source === 'In Theatres');
        }
        
        // Limit results
        filtered = filtered.slice(0, 30);
        
        results.innerHTML = filtered.length === 0 
            ? '<p style="color: #888; text-align: center; grid-column: span 2;">No results found</p>'
            : filtered.map(m => createMovieCard(m)).join("");
        
        // Add click handlers
        results.querySelectorAll(".movie-card").forEach(card => {
            card.addEventListener("click", () => {
                const title = card.dataset.title;
                const movie = allMoviesData.find(m => m.title === title);
                if (movie) {
                    closePanel(searchPanel);
                    showToast(`Playing: ${movie.title}`);
                    addMovieToFeed(movie, true, true);
                }
            });
        });
    }
    
    function createMovieCard(movie) {
        const getCardPlaceholder = (text, w, h) => {
            const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><rect width="100%" height="100%" fill="#1a1a2e"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#888" font-size="14" font-family="Arial">${text}</text></svg>`;
            return `data:image/svg+xml,${encodeURIComponent(svg)}`;
        };
        const posterUrl = movie.posterUrl || movie.image || getCardPlaceholder(movie.title?.substring(0,10) || 'Movie', 150, 225);
        const fallbackPoster = getCardPlaceholder('No Image', 150, 225);
        return `
            <div class="movie-card" data-title="${movie.title || ''}" style="
                cursor: pointer;
                border-radius: 12px;
                overflow: hidden;
                background: rgba(255,255,255,0.05);
                transition: all 0.2s;
                border: 1px solid rgba(255,255,255,0.1);
            " onmouseenter="this.style.transform='scale(1.03)';this.style.borderColor='#22c55e'" 
               onmouseleave="this.style.transform='scale(1)';this.style.borderColor='rgba(255,255,255,0.1)'">
                <img src="${posterUrl}" alt="${movie.title}" style="width: 100%; aspect-ratio: 2/3; object-fit: cover;" 
                    onerror="this.src='${fallbackPoster}'">
                <div style="padding: 10px;">
                    <h4 style="color: white; font-size: 13px; font-weight: 600; margin: 0 0 4px 0; 
                        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${movie.title || 'Unknown'}</h4>
                    <p style="color: #888; font-size: 11px; margin: 0;">${movie.year || ''} ${movie.rating ? '• ⭐ ' + movie.rating : ''}</p>
                </div>
            </div>
        `;
    }
    
    function createFilterPanel() {
        if (filterPanel) return filterPanel;
        
        filterPanel = createPanelBase("filter-panel", "Filters");
        const content = filterPanel.querySelector(".panel-content");
        
        content.innerHTML = `
            <div style="margin-bottom: 24px;">
                <h3 style="color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 12px;">Content Type</h3>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    <button class="filter-btn active" data-filter="all">All</button>
                    <button class="filter-btn" data-filter="movies">Movies</button>
                    <button class="filter-btn" data-filter="tv">TV Shows</button>
                    <button class="filter-btn" data-filter="nowplaying">Now Playing</button>
                </div>
            </div>
            <div style="margin-bottom: 24px;">
                <h3 style="color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 12px;">Genres</h3>
                <div id="genre-filters" style="display: flex; flex-wrap: wrap; gap: 8px;"></div>
            </div>
            <div style="margin-bottom: 24px;">
                <h3 style="color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 12px;">Year</h3>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    <button class="filter-btn" data-year="2026">2026</button>
                    <button class="filter-btn" data-year="2025">2025</button>
                    <button class="filter-btn" data-year="2024">2024</button>
                    <button class="filter-btn" data-year="older">Older</button>
                </div>
            </div>
            <button id="apply-filters" style="
                width: 100%; padding: 14px; background: #22c55e; color: black; font-weight: bold;
                border: none; border-radius: 12px; cursor: pointer; font-size: 16px; margin-top: 20px;
                transition: all 0.2s;
            ">Apply Filters</button>
        `;
        
        // Style filter buttons
        const style = document.createElement("style");
        style.textContent = `
            .filter-btn {
                padding: 8px 16px;
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                color: #ccc;
                border-radius: 20px;
                cursor: pointer;
                font-size: 13px;
                transition: all 0.2s;
            }
            .filter-btn:hover {
                background: rgba(255,255,255,0.2);
                color: white;
            }
            .filter-btn.active {
                background: #22c55e;
                border-color: #22c55e;
                color: black;
            }
        `;
        document.head.appendChild(style);
        
        // Populate genres
        const genreContainer = content.querySelector("#genre-filters");
        const genres = [...new Set(allMoviesData.flatMap(m => m.genres || []))].sort();
        genreContainer.innerHTML = genres.slice(0, 15).map(g => 
            `<button class="filter-btn" data-genre="${g}">${g}</button>`
        ).join("");
        
        // Add click handlers
        content.querySelectorAll(".filter-btn[data-filter]").forEach(btn => {
            btn.addEventListener("click", () => {
                content.querySelectorAll(".filter-btn[data-filter]").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                currentFilter = btn.dataset.filter;
                updateCategoryButtons();
            });
        });
        
        content.querySelectorAll(".filter-btn[data-genre]").forEach(btn => {
            btn.addEventListener("click", () => btn.classList.toggle("active"));
        });
        
        content.querySelectorAll(".filter-btn[data-year]").forEach(btn => {
            btn.addEventListener("click", () => {
                content.querySelectorAll(".filter-btn[data-year]").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
            });
        });
        
        content.querySelector("#apply-filters").addEventListener("click", () => {
            closePanel(filterPanel);
            showToast("Filters applied!");
            // Refresh search if open
            if (searchPanel && searchPanel.style.right === "0px") {
                const input = document.getElementById("movie-search-input");
                if (input) performSearch(input.value);
            }
        });
        
        return filterPanel;
    }
    
    function createQueuePanel() {
        if (queuePanel) return queuePanel;
        
        queuePanel = createPanelBase("queue-panel", "My Queue");
        updateQueuePanel();
        return queuePanel;
    }
    
    // Mark a video as watched
    function markAsWatched(title, posterUrl, year) {
        if (!title || title === 'Unknown') return;
        
        // Check if already in watched
        const existingIndex = watchedHistory.findIndex(w => w.title === title);
        if (existingIndex >= 0) {
            // Move to front (most recent)
            watchedHistory.splice(existingIndex, 1);
        }
        
        // Add to front with timestamp
        watchedHistory.unshift({
            title,
            posterUrl: posterUrl || null,
            year: year || null,
            watchedAt: new Date().toISOString()
        });
        
        // Keep only last 100 watched items
        if (watchedHistory.length > 100) {
            watchedHistory = watchedHistory.slice(0, 100);
        }
        
        localStorage.setItem("movieshows-watched", JSON.stringify(watchedHistory));
    }
    
    // Get alternate trailers for a movie
    function getAlternateTrailers(title) {
        if (!title || !window.allMoviesData) return [];
        
        const movie = window.allMoviesData.find(m => m.title === title);
        if (!movie) return [];
        
        // Look for alternate trailers in the data
        const trailers = [];
        if (movie.trailerUrl) trailers.push({ url: movie.trailerUrl, label: 'Official Trailer' });
        if (movie.trailer2Url) trailers.push({ url: movie.trailer2Url, label: 'Trailer 2' });
        if (movie.trailer3Url) trailers.push({ url: movie.trailer3Url, label: 'Trailer 3' });
        if (movie.teaserUrl) trailers.push({ url: movie.teaserUrl, label: 'Teaser' });
        if (movie.clipUrl) trailers.push({ url: movie.clipUrl, label: 'Clip' });
        
        // Also search for same title with different trailers in database
        const alternates = window.allMoviesData.filter(m => 
            m.title === title && m.trailerUrl && m.trailerUrl !== movie.trailerUrl
        );
        alternates.forEach((alt, i) => {
            trailers.push({ url: alt.trailerUrl, label: `Alternate ${i + 1}` });
        });
        
        return trailers;
    }
    
    function updateQueuePanel() {
        if (!queuePanel) return;
        const content = queuePanel.querySelector(".panel-content");
        
        console.log(`[MovieShows] updateQueuePanel called. queueTabMode=${queueTabMode}, viewMode=${queueViewMode}`);
        
        // CRITICAL: Get the actual visible video from DOM, not from index calculation
        videoSlides = findVideoSlides();
        
        // Better method: Find which slide is actually visible
        let actualVisibleIndex = 0;
        let nowPlayingTitle = 'Unknown';
        let nowPlayingPoster = null;
        
        // PRIORITY Method: Use currentlyPlayingTitle if we have it (this is the actual playing video)
        if (currentlyPlayingTitle && currentlyPlayingTitle !== 'Unknown') {
            nowPlayingTitle = currentlyPlayingTitle;
            // Find the index of this playing video
            for (let i = 0; i < videoSlides.length; i++) {
                const slideTitle = videoSlides[i].dataset?.movieTitle || videoSlides[i].querySelector('h2')?.textContent;
                if (slideTitle === currentlyPlayingTitle) {
                    actualVisibleIndex = i;
                    nowPlayingPoster = videoSlides[i].querySelector('img')?.src;
                    console.log(`[MovieShows] updateQueuePanel: Using currentlyPlayingTitle "${nowPlayingTitle}" at index ${actualVisibleIndex}`);
                    break;
                }
            }
        }
        
        // Method 1: Use scroll position (fallback if no currentlyPlayingTitle)
        if (nowPlayingTitle === 'Unknown') {
            actualVisibleIndex = getCurrentVisibleIndex();
            console.log(`[MovieShows] updateQueuePanel: getCurrentVisibleIndex=${actualVisibleIndex}, videoSlides.length=${videoSlides.length}`);
            
            if (actualVisibleIndex >= 0 && actualVisibleIndex < videoSlides.length) {
                const slide = videoSlides[actualVisibleIndex];
                nowPlayingTitle = slide.dataset?.movieTitle || slide.querySelector('h2')?.textContent || 'Unknown';
                nowPlayingPoster = slide.querySelector('img')?.src;
                console.log(`[MovieShows] updateQueuePanel: Found playing video "${nowPlayingTitle}" at index ${actualVisibleIndex}`);
            }
        }
        
        // Method 2: Check which iframe is currently playing (as verification)
        if (nowPlayingTitle === 'Unknown') {
            const playingIframe = document.querySelector('iframe[src*="youtube"]');
            if (playingIframe) {
                const parentSlide = playingIframe.closest('.snap-center');
                if (parentSlide) {
                    const slideIndex = videoSlides.indexOf(parentSlide);
                    if (slideIndex >= 0) {
                        actualVisibleIndex = slideIndex;
                        nowPlayingTitle = parentSlide.dataset?.movieTitle || parentSlide.querySelector('h2')?.textContent || 'Unknown';
                        nowPlayingPoster = parentSlide.querySelector('img')?.src;
                        console.log(`[MovieShows] updateQueuePanel: Found via iframe "${nowPlayingTitle}"`);
                    }
                }
            }
        }
        
        // Method 3: Check which slide has the .active class
        if (nowPlayingTitle === 'Unknown') {
            const activeSlide = document.querySelector('.snap-center.active, .video-slide.active');
            if (activeSlide) {
                const slideIndex = videoSlides.indexOf(activeSlide);
                if (slideIndex >= 0) {
                    actualVisibleIndex = slideIndex;
                    nowPlayingTitle = activeSlide.dataset?.movieTitle || activeSlide.querySelector('h2')?.textContent || 'Unknown';
                    nowPlayingPoster = activeSlide.querySelector('img')?.src;
                    console.log(`[MovieShows] updateQueuePanel: Found via .active class "${nowPlayingTitle}"`);
                }
            }
        }
        
        currentIndex = actualVisibleIndex; // Sync currentIndex
        
        // Helper function to get poster URL from allMoviesData
        const getPosterFromData = (title) => {
            if (!title || title === 'Unknown') return null;
            const movie = window.allMoviesData?.find(m => m.title === title);
            // Check posterUrl first, then image property, then try to construct from TMDB
            if (movie) {
                return movie.posterUrl || movie.image || 
                    (movie.tmdbId ? `https://image.tmdb.org/t/p/w200/${movie.tmdbId}.jpg` : null);
            }
            return null;
        };
        
        // Generate a placeholder image as inline SVG data URL (no external dependency)
        const getPlaceholderUrl = (title, width = 50, height = 75, color = '666') => {
            const letter = title?.charAt(0)?.toUpperCase() || '?';
            const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
                <rect width="100%" height="100%" fill="#1a1a2e"/>
                <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#${color}" font-size="${Math.min(width, height) * 0.5}" font-family="Arial, sans-serif" font-weight="bold">${letter}</text>
            </svg>`;
            return `data:image/svg+xml,${encodeURIComponent(svg)}`;
        };
        
        // Build playlist with deduplication
        const seenTitles = new Set();
        const currentPlaylist = [];
        videoSlides.forEach((slide, idx) => {
            const title = slide.dataset?.movieTitle || slide.querySelector('h2')?.textContent || 'Unknown';
            // Try to get poster from DOM first, then from allMoviesData
            const posterUrl = slide.querySelector('img')?.src || getPosterFromData(title);
            
            // Only add if not seen before (deduplicate)
            if (!seenTitles.has(title)) {
                seenTitles.add(title);
                currentPlaylist.push({
                    title,
                    index: idx,
                    isPlaying: idx === actualVisibleIndex,
                    posterUrl
                });
            }
        });
        
        // Get "Up Next" items - deduplicated and excluding current
        const upNextItems = currentPlaylist.filter(item => 
            item.index > actualVisibleIndex && item.title !== nowPlayingTitle
        ).slice(0, 5);
        
        const isThumbnailMode = queueViewMode === 'thumbnail';
        
        // Get alternate trailers for current video
        const alternateTrailers = getAlternateTrailers(nowPlayingTitle);
        const isQueueTab = queueTabMode === 'queue';
        
        // Build the panel HTML
        content.innerHTML = `
            <!-- Tab Selector: Queue vs Watched -->
            <div style="display: flex; gap: 4px; background: rgba(255,255,255,0.05); border-radius: 10px; padding: 4px; margin-bottom: 12px;">
                <button id="tab-queue" style="
                    flex: 1; padding: 8px 12px; border: none; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 500;
                    background: ${isQueueTab ? 'rgba(34, 197, 94, 0.3)' : 'transparent'};
                    color: ${isQueueTab ? '#22c55e' : '#888'};
                    transition: all 0.2s;
                ">📋 Queue</button>
                <button id="tab-watched" style="
                    flex: 1; padding: 8px 12px; border: none; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 500;
                    background: ${!isQueueTab ? 'rgba(147, 51, 234, 0.3)' : 'transparent'};
                    color: ${!isQueueTab ? '#a855f7' : '#888'};
                    transition: all 0.2s;
                ">✅ Watched (${watchedHistory.length})</button>
            </div>
            
            <!-- View Mode Toggle + Resync -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <button id="queue-resync-btn" style="
                    padding: 6px 12px; border: none; border-radius: 8px; cursor: pointer; font-size: 11px;
                    background: rgba(59, 130, 246, 0.2); color: #3b82f6;
                    transition: all 0.2s; display: flex; align-items: center; gap: 4px;
                " title="Resync queue with current video">🔄 Resync</button>
                <div style="display: flex; gap: 4px; background: rgba(255,255,255,0.05); border-radius: 8px; padding: 3px;">
                    <button id="queue-view-thumbnail" style="
                        padding: 6px 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 11px;
                        background: ${isThumbnailMode ? 'rgba(34, 197, 94, 0.3)' : 'transparent'};
                        color: ${isThumbnailMode ? '#22c55e' : '#888'};
                        transition: all 0.2s;
                    " title="Thumbnail view">🖼️ Thumbnails</button>
                    <button id="queue-view-text" style="
                        padding: 6px 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 11px;
                        background: ${!isThumbnailMode ? 'rgba(34, 197, 94, 0.3)' : 'transparent'};
                        color: ${!isThumbnailMode ? '#22c55e' : '#888'};
                        transition: all 0.2s;
                    " title="Text only view">📝 Text Only</button>
                </div>
            </div>
            
            <!-- Now Playing Section -->
            <div style="margin-bottom: 20px;">
                <h3 style="color: #22c55e; font-size: 14px; text-transform: uppercase; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                    <span style="width: 8px; height: 8px; background: #22c55e; border-radius: 50%; animation: pulse 1.5s infinite;"></span>
                    Now Playing
                </h3>
                <div id="now-playing-item" style="padding: 12px; background: rgba(34, 197, 94, 0.1); border-radius: 12px; border: 1px solid rgba(34, 197, 94, 0.3);">
                    <div style="display: flex; gap: 12px; align-items: center;">
                        ${isThumbnailMode ? `
                            <img src="${nowPlayingPoster || getPlaceholderUrl(nowPlayingTitle, 50, 75, '22c55e')}" 
                                style="width: 50px; height: 75px; object-fit: cover; border-radius: 6px; flex-shrink: 0; background: #1a1a2e;" 
                                onerror="this.src='${getPlaceholderUrl(nowPlayingTitle, 50, 75, '22c55e')}'">
                        ` : ''}
                        <div style="flex: 1; min-width: 0;">
                            <h4 style="color: white; font-size: 16px; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${nowPlayingTitle}</h4>
                            <p style="color: #888; font-size: 12px; margin: 4px 0 0 0;">Video ${actualVisibleIndex + 1} of ${videoSlides.length}</p>
                        </div>
                        <button id="mark-watched-btn" style="
                            padding: 6px 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 11px;
                            background: rgba(147, 51, 234, 0.2); color: #a855f7;
                            transition: all 0.2s;
                        " title="Mark as watched">✅</button>
                    </div>
                    ${alternateTrailers.length > 1 ? `
                        <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
                            <label style="color: #888; font-size: 11px; display: block; margin-bottom: 6px;">Switch Trailer:</label>
                            <select id="alternate-trailer-select" style="
                                width: 100%; padding: 8px 10px; background: rgba(0,0,0,0.3); 
                                border: 1px solid rgba(255,255,255,0.2); border-radius: 6px;
                                color: white; font-size: 12px; cursor: pointer;
                            ">
                                ${alternateTrailers.map((t, i) => `
                                    <option value="${t.url}" ${i === 0 ? 'selected' : ''}>${t.label}</option>
                                `).join('')}
                            </select>
                        </div>
                    ` : ''}
                </div>
            </div>
            
            ${isQueueTab ? `
            <!-- QUEUE TAB CONTENT -->
            <!-- Up Next Section -->
            <div style="margin-bottom: 20px;">
                <h3 style="color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 12px;">Up Next (${Math.max(0, videoSlides.length - actualVisibleIndex - 1)} videos)</h3>
                <div id="up-next-items" style="display: flex; flex-direction: column; gap: ${isThumbnailMode ? '8px' : '4px'}; max-height: 200px; overflow-y: auto;">
                    ${upNextItems.map((item, i) => {
                        const itemPoster = item.posterUrl || getPosterFromData(item.title) || getPlaceholderUrl(item.title, 30, 45, '666');
                        return isThumbnailMode ? `
                        <div class="up-next-item" data-index="${item.index}" style="
                            display: flex; gap: 10px; padding: 8px; background: rgba(255,255,255,0.03);
                            border-radius: 8px; cursor: pointer; transition: all 0.2s;
                            border: 1px solid rgba(255,255,255,0.05); align-items: center;
                        " onmouseover="this.style.background='rgba(255,255,255,0.08)'" onmouseout="this.style.background='rgba(255,255,255,0.03)'">
                            <span style="color: #666; font-size: 12px; min-width: 20px;">${i + 1}</span>
                            <img src="${itemPoster}" 
                                style="width: 30px; height: 45px; object-fit: cover; border-radius: 4px; flex-shrink: 0; background: #1a1a2e;" 
                                onerror="this.src='${getPlaceholderUrl(item.title, 30, 45, '666')}'">
                            <span style="color: white; font-size: 13px; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.title}</span>
                        </div>
                    ` : `
                        <div class="up-next-item" data-index="${item.index}" style="
                            display: flex; gap: 8px; padding: 6px 8px; background: transparent;
                            cursor: pointer; transition: all 0.2s; border-radius: 4px;
                        " onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'">
                            <span style="color: #666; font-size: 11px; min-width: 18px;">${i + 1}.</span>
                            <span style="color: #ccc; font-size: 12px; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.title}</span>
                        </div>
                    `; }).join('') || '<p style="color: #666; font-size: 13px; padding: 8px;">No more videos in queue</p>'}
                </div>
            </div>
            
            <!-- Saved Queue Section -->
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3 style="color: #888; font-size: 12px; text-transform: uppercase;">My Saved Queue (${userQueue.length})</h3>
                    ${userQueue.length > 0 ? '<button id="clear-queue" style="color: #ef4444; background: none; border: none; cursor: pointer; font-size: 11px;">Clear All</button>' : ''}
                </div>
                
                ${userQueue.length === 0 ? `
                    <div style="text-align: center; padding: 20px; background: rgba(255,255,255,0.02); border-radius: 12px;">
                        <p style="color: #666; font-size: 13px; margin: 0;">Click the "List" button on any video to save it here</p>
                    </div>
                ` : isThumbnailMode ? `
                    <div id="queue-items" style="display: flex; flex-direction: column; gap: 8px;">
                        ${userQueue.map((item, index) => {
                            const savedPoster = item.posterUrl || getPosterFromData(item.title) || getPlaceholderUrl(item.title, 40, 60, 'fff');
                            return `
                            <div class="queue-item" draggable="true" data-index="${index}" style="
                                display: flex; gap: 10px; padding: 10px; background: rgba(255,255,255,0.05);
                                border-radius: 10px; cursor: grab; transition: all 0.2s;
                                border: 1px solid rgba(255,255,255,0.1);
                            ">
                                <div class="drag-handle" style="display: flex; align-items: center; color: #555; cursor: grab;">⋮⋮</div>
                                <img src="${savedPoster}" 
                                    style="width: 40px; height: 60px; object-fit: cover; border-radius: 6px; background: #1a1a2e;" 
                                    onerror="this.src='${getPlaceholderUrl(item.title, 40, 60, 'fff')}'">
                                <div style="flex: 1; min-width: 0;">
                                    <h4 style="color: white; font-size: 13px; margin: 0 0 2px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.title}</h4>
                                    <p style="color: #888; font-size: 11px; margin: 0;">${item.year || ''}</p>
                                    <div style="margin-top: 6px; display: flex; gap: 6px;">
                                        <button class="play-queue-item" style="padding: 4px 10px; background: #22c55e; color: black; 
                                            border: none; border-radius: 4px; font-size: 11px; font-weight: bold; cursor: pointer;">▶ Play</button>
                                        <button class="remove-queue-item" style="padding: 4px 8px; background: rgba(255,255,255,0.1); 
                                            color: #aaa; border: none; border-radius: 4px; font-size: 11px; cursor: pointer;">✕</button>
                                    </div>
                                </div>
                            </div>
                        `; }).join('')}
                    </div>
                ` : `
                    <div id="queue-items" style="display: flex; flex-direction: column; gap: 4px;">
                        ${userQueue.map((item, index) => `
                            <div class="queue-item" draggable="true" data-index="${index}" style="
                                display: flex; gap: 8px; padding: 8px 10px; background: rgba(255,255,255,0.03);
                                border-radius: 6px; cursor: grab; transition: all 0.2s;
                                border: 1px solid rgba(255,255,255,0.05); align-items: center;
                            ">
                                <div class="drag-handle" style="color: #555; cursor: grab; font-size: 10px;">⋮⋮</div>
                                <span style="color: white; font-size: 12px; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.title}</span>
                                <button class="play-queue-item" style="padding: 3px 8px; background: #22c55e; color: black; 
                                    border: none; border-radius: 4px; font-size: 10px; font-weight: bold; cursor: pointer;">▶</button>
                                <button class="remove-queue-item" style="padding: 3px 6px; background: rgba(255,255,255,0.1); 
                                    color: #aaa; border: none; border-radius: 4px; font-size: 10px; cursor: pointer;">✕</button>
                            </div>
                        `).join('')}
                    </div>
                `}
            </div>
            ` : `
            <!-- WATCHED TAB CONTENT -->
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <h3 style="color: #a855f7; font-size: 12px; text-transform: uppercase;">Watch History (${watchedHistory.length})</h3>
                    ${watchedHistory.length > 0 ? '<button id="clear-watched" style="color: #ef4444; background: none; border: none; cursor: pointer; font-size: 11px;">Clear All</button>' : ''}
                </div>
                
                ${watchedHistory.length === 0 ? `
                    <div style="text-align: center; padding: 30px 20px; background: rgba(147, 51, 234, 0.05); border-radius: 12px; border: 1px dashed rgba(147, 51, 234, 0.3);">
                        <p style="color: #666; font-size: 13px; margin: 0;">Videos you watch will appear here</p>
                        <p style="color: #555; font-size: 11px; margin: 8px 0 0 0;">Click ✅ on any video to mark it as watched</p>
                    </div>
                ` : `
                    <div id="watched-items" style="display: flex; flex-direction: column; gap: 8px; max-height: 400px; overflow-y: auto;">
                        ${watchedHistory.map((item, index) => {
                            const watchedPoster = item.posterUrl || getPosterFromData(item.title) || getPlaceholderUrl(item.title, 40, 60, 'a855f7');
                            const watchedDate = item.watchedAt ? new Date(item.watchedAt).toLocaleDateString() : '';
                            return isThumbnailMode ? `
                            <div class="watched-item" data-index="${index}" style="
                                display: flex; gap: 10px; padding: 10px; background: rgba(147, 51, 234, 0.05);
                                border-radius: 10px; cursor: pointer; transition: all 0.2s;
                                border: 1px solid rgba(147, 51, 234, 0.2);
                            " onmouseover="this.style.background='rgba(147, 51, 234, 0.1)'" onmouseout="this.style.background='rgba(147, 51, 234, 0.05)'">
                                <img src="${watchedPoster}" 
                                    style="width: 40px; height: 60px; object-fit: cover; border-radius: 6px; background: #1a1a2e;" 
                                    onerror="this.src='${getPlaceholderUrl(item.title, 40, 60, 'a855f7')}'">
                                <div style="flex: 1; min-width: 0;">
                                    <h4 style="color: white; font-size: 13px; margin: 0 0 2px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.title}</h4>
                                    <p style="color: #888; font-size: 11px; margin: 0;">${item.year || ''} ${watchedDate ? '• Watched ' + watchedDate : ''}</p>
                                    <div style="margin-top: 6px; display: flex; gap: 6px;">
                                        <button class="play-watched-item" style="padding: 4px 10px; background: #a855f7; color: white; 
                                            border: none; border-radius: 4px; font-size: 11px; font-weight: bold; cursor: pointer;">▶ Rewatch</button>
                                        <button class="remove-watched-item" style="padding: 4px 8px; background: rgba(255,255,255,0.1); 
                                            color: #aaa; border: none; border-radius: 4px; font-size: 11px; cursor: pointer;">✕</button>
                                    </div>
                                </div>
                            </div>
                        ` : `
                            <div class="watched-item" data-index="${index}" style="
                                display: flex; gap: 8px; padding: 8px 10px; background: rgba(147, 51, 234, 0.03);
                                border-radius: 6px; cursor: pointer; transition: all 0.2s;
                                border: 1px solid rgba(147, 51, 234, 0.1); align-items: center;
                            " onmouseover="this.style.background='rgba(147, 51, 234, 0.08)'" onmouseout="this.style.background='rgba(147, 51, 234, 0.03)'">
                                <span style="color: #a855f7; font-size: 11px;">✓</span>
                                <span style="color: white; font-size: 12px; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.title}</span>
                                <button class="play-watched-item" style="padding: 3px 8px; background: #a855f7; color: white; 
                                    border: none; border-radius: 4px; font-size: 10px; font-weight: bold; cursor: pointer;">▶</button>
                                <button class="remove-watched-item" style="padding: 3px 6px; background: rgba(255,255,255,0.1); 
                                    color: #aaa; border: none; border-radius: 4px; font-size: 10px; cursor: pointer;">✕</button>
                            </div>
                        `; }).join('')}
                    </div>
                `}
            </div>
            `}
            
            <style>
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                .queue-item.dragging {
                    opacity: 0.5;
                    background: rgba(34, 197, 94, 0.2) !important;
                }
                .queue-item.drag-over {
                    border-color: #22c55e !important;
                }
            </style>
        `;
        
        // Add handler for resync button - IMPROVED
        content.querySelector("#queue-resync-btn")?.addEventListener("click", () => {
            console.log('[MovieShows] Manual resync triggered');
            
            // Force refresh videoSlides
            videoSlides = findVideoSlides();
            
            // Better detection: find which slide is actually visible in viewport
            let bestIndex = 0;
            let bestVisibility = 0;
            
            videoSlides.forEach((slide, idx) => {
                const rect = slide.getBoundingClientRect();
                const viewportHeight = window.innerHeight;
                const visibleTop = Math.max(0, rect.top);
                const visibleBottom = Math.min(viewportHeight, rect.bottom);
                const visibleHeight = Math.max(0, visibleBottom - visibleTop);
                const visibility = visibleHeight / rect.height;
                
                if (visibility > bestVisibility) {
                    bestVisibility = visibility;
                    bestIndex = idx;
                }
            });
            
            currentIndex = bestIndex;
            const title = videoSlides[bestIndex]?.dataset?.movieTitle || videoSlides[bestIndex]?.querySelector('h2')?.textContent || 'Unknown';
            console.log(`[MovieShows] Resync: Found video "${title}" at index ${bestIndex} with ${Math.round(bestVisibility * 100)}% visibility`);
            
            // Stop all videos and play only the visible one
            forceStopAllVideos();
            setTimeout(() => {
                // CRITICAL: Update currentlyPlayingTitle BEFORE playing
                currentlyPlayingTitle = title;
                const targetIframe = videoSlides[bestIndex]?.querySelector('iframe[data-src]');
                if (targetIframe) {
                    currentlyPlayingIframe = targetIframe;
                    playVideo(targetIframe, title);
                } else {
                    forcePlayVisibleVideos();
                }
                updateQueuePanel();
                showToast(`Synced to: ${title}`);
            }, 100);
        });
        
        // Add handlers for view mode toggle
        content.querySelector("#queue-view-thumbnail")?.addEventListener("click", () => {
            if (queueViewMode !== 'thumbnail') {
                queueViewMode = 'thumbnail';
                localStorage.setItem("movieshows-queue-view", queueViewMode);
                updateQueuePanel();
            }
        });
        
        content.querySelector("#queue-view-text")?.addEventListener("click", () => {
            if (queueViewMode !== 'text') {
                queueViewMode = 'text';
                localStorage.setItem("movieshows-queue-view", queueViewMode);
                updateQueuePanel();
            }
        });
        
        // Add handlers for tab switching - only once
        if (!content.dataset.tabHandlerAttached) {
            content.dataset.tabHandlerAttached = "true";
            content.addEventListener("click", (e) => {
                const target = e.target;
                
                // Check if clicked on Queue tab or inside it
                const queueTab = target.closest("#tab-queue");
                const watchedTab = target.closest("#tab-watched");
                
                if (queueTab) {
                    e.stopPropagation();
                    console.log(`[MovieShows] Queue tab clicked (delegation). Current mode: ${queueTabMode}`);
                    queueTabMode = 'queue';
                    localStorage.setItem("movieshows-queue-tab", queueTabMode);
                    updateQueuePanel();
                    return;
                }
                
                if (watchedTab) {
                    e.stopPropagation();
                    console.log(`[MovieShows] Watched tab clicked (delegation). Current mode: ${queueTabMode}`);
                    queueTabMode = 'watched';
                    localStorage.setItem("movieshows-queue-tab", queueTabMode);
                    updateQueuePanel();
                    return;
                }
            });
        }
        
        // Add handler for mark as watched button
        content.querySelector("#mark-watched-btn")?.addEventListener("click", () => {
            if (nowPlayingTitle && nowPlayingTitle !== 'Unknown') {
                const movie = window.allMoviesData?.find(m => m.title === nowPlayingTitle);
                markAsWatched(nowPlayingTitle, nowPlayingPoster || movie?.posterUrl, movie?.year);
                showToast(`✅ Marked "${nowPlayingTitle}" as watched`);
                updateQueuePanel();
            }
        });
        
        // Add handler for alternate trailer select
        content.querySelector("#alternate-trailer-select")?.addEventListener("change", (e) => {
            const newTrailerUrl = e.target.value;
            if (newTrailerUrl && videoSlides[actualVisibleIndex]) {
                const iframe = videoSlides[actualVisibleIndex].querySelector('iframe');
                if (iframe) {
                    // Extract video ID and construct new URL
                    let videoId = '';
                    const match = newTrailerUrl.match(/(?:embed\/|watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
                    if (match) videoId = match[1];
                    else if (newTrailerUrl.length === 11) videoId = newTrailerUrl;
                    
                    if (videoId) {
                        const newSrc = `https://www.youtube.com/embed/${videoId}?autoplay=1&mute=${isMuted ? 1 : 0}&enablejsapi=1&modestbranding=1&rel=0`;
                        iframe.src = newSrc;
                        showToast('Switched to alternate trailer');
                    }
                }
            }
        });
        
        // Add handlers for clear queue
        content.querySelector("#clear-queue")?.addEventListener("click", () => {
            userQueue = [];
            saveQueue();
            updateQueuePanel();
            showToast("Queue cleared");
        });
        
        // Add handlers for clear watched
        content.querySelector("#clear-watched")?.addEventListener("click", () => {
            watchedHistory = [];
            localStorage.setItem("movieshows-watched", JSON.stringify(watchedHistory));
            updateQueuePanel();
            showToast("Watch history cleared");
        });
        
        // Add handlers for up-next items
        content.querySelectorAll(".up-next-item").forEach(item => {
            item.addEventListener("click", () => {
                const idx = parseInt(item.dataset.index);
                const itemTitle = item.querySelector('span:last-child')?.textContent || item.textContent;
                
                // Debug logging
                console.log(`[MovieShows] Up-next click: index=${idx}, title="${itemTitle}"`);
                console.log(`[MovieShows] videoSlides.length=${videoSlides.length}, currentIndex=${currentIndex}`);
                
                // Verify the target slide exists and has the expected title
                if (videoSlides[idx]) {
                    const targetTitle = videoSlides[idx].querySelector('h2')?.textContent || 'Unknown';
                    console.log(`[MovieShows] Target slide title: "${targetTitle}"`);
                }
                
                scrollToSlide(idx);
                showToast(`Playing: ${itemTitle}`);
            });
        });
        
        // Add handlers for queue items
        const itemsContainer = content.querySelector("#queue-items");
        if (itemsContainer) {
            itemsContainer.querySelectorAll(".play-queue-item").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const index = parseInt(btn.closest(".queue-item").dataset.index);
                    const item = userQueue[index];
                    console.log(`[MovieShows] Play queue item clicked: index=${index}, item=${item?.title}`);
                    if (item) {
                        const movie = allMoviesData.find(m => m.title === item.title) || item;
                        console.log(`[MovieShows] Playing from queue: "${movie.title}"`);
                        closePanel(queuePanel);
                        showToast(`Playing: ${movie.title}`);
                        addMovieToFeed(movie, true, true);
                    }
                });
            });
            
            itemsContainer.querySelectorAll(".remove-queue-item").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const index = parseInt(btn.closest(".queue-item").dataset.index);
                    const removed = userQueue.splice(index, 1);
                    saveQueue();
                    updateQueuePanel();
                    showToast(`Removed "${removed[0]?.title || 'item'}"`);
                });
            });
            
            // Drag and drop for reordering
            setupQueueDragAndDrop(itemsContainer);
        }
        
        // Add handlers for watched items
        const watchedContainer = content.querySelector("#watched-items");
        if (watchedContainer) {
            watchedContainer.querySelectorAll(".play-watched-item").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const index = parseInt(btn.closest(".watched-item").dataset.index);
                    const item = watchedHistory[index];
                    if (item) {
                        const movie = allMoviesData.find(m => m.title === item.title) || item;
                        closePanel(queuePanel);
                        showToast(`Rewatching: ${movie.title}`);
                        addMovieToFeed(movie, true, true);
                    }
                });
            });
            
            watchedContainer.querySelectorAll(".remove-watched-item").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const index = parseInt(btn.closest(".watched-item").dataset.index);
                    const removed = watchedHistory.splice(index, 1);
                    localStorage.setItem("movieshows-watched", JSON.stringify(watchedHistory));
                    updateQueuePanel();
                    showToast(`Removed "${removed[0]?.title || 'item'}" from history`);
                });
            });
        }
    }
    
    function setupQueueDragAndDrop(container) {
        let draggedItem = null;
        let draggedIndex = -1;
        
        container.querySelectorAll(".queue-item").forEach(item => {
            item.addEventListener("dragstart", (e) => {
                draggedItem = item;
                draggedIndex = parseInt(item.dataset.index);
                item.classList.add("dragging");
                e.dataTransfer.effectAllowed = "move";
            });
            
            item.addEventListener("dragend", () => {
                item.classList.remove("dragging");
                container.querySelectorAll(".queue-item").forEach(i => i.classList.remove("drag-over"));
                draggedItem = null;
            });
            
            item.addEventListener("dragover", (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
                if (draggedItem && draggedItem !== item) {
                    item.classList.add("drag-over");
                }
            });
            
            item.addEventListener("dragleave", () => {
                item.classList.remove("drag-over");
            });
            
            item.addEventListener("drop", (e) => {
                e.preventDefault();
                item.classList.remove("drag-over");
                
                if (draggedItem && draggedItem !== item) {
                    const dropIndex = parseInt(item.dataset.index);
                    
                    // Reorder the queue
                    const [movedItem] = userQueue.splice(draggedIndex, 1);
                    userQueue.splice(dropIndex, 0, movedItem);
                    
                    saveQueue();
                    updateQueuePanel();
                    showToast("Queue reordered");
                }
            });
        });
    }
    
    function addToQueue(movie) {
        if (!movie?.title) return;
        if (userQueue.some(q => q.title === movie.title)) {
            showToast("Already in queue", true);
            return;
        }
        userQueue.push({
            title: movie.title,
            posterUrl: movie.posterUrl || movie.image,
            year: movie.year,
            trailerUrl: movie.trailerUrl
        });
        saveQueue();
        updateQueuePanel();
        showToast(`Added "${movie.title}" to queue`);
    }
    
    function saveQueue() {
        localStorage.setItem("movieshows-queue", JSON.stringify(userQueue));
    }
    
    function setupNavigationHandlers() {
        // Utility to get clean button text (handles nested elements, icons, etc.)
        const getButtonText = (btn) => {
            // Try aria-label first
            const ariaLabel = btn.getAttribute("aria-label");
            if (ariaLabel) return ariaLabel.toLowerCase();
            
            // Try title attribute
            const title = btn.getAttribute("title");
            if (title) return title.toLowerCase();
            
            // Look for child span or text nodes
            const spans = btn.querySelectorAll("span");
            for (const span of spans) {
                const spanText = span.textContent?.trim();
                if (spanText && spanText.length > 1) return spanText.toLowerCase();
            }
            
            // Try innerText which ignores SVG text
            const innerText = btn.innerText?.trim().toLowerCase();
            if (innerText) return innerText;
            
            // Check adjacent sibling text (sometimes buttons have text next to them)
            const nextSibling = btn.nextSibling;
            if (nextSibling && nextSibling.nodeType === 3) { // Text node
                const siblingText = nextSibling.textContent?.trim();
                if (siblingText) return siblingText.toLowerCase();
            }
            
            // Fallback to textContent
            return btn.textContent?.trim().toLowerCase() || "";
        };
        
        // Find nav buttons directly and add click handlers
        const findAndSetupNavButtons = () => {
            const allButtons = document.querySelectorAll("button");
            
            allButtons.forEach(btn => {
                const text = getButtonText(btn);
                
                // Skip if already handled
                if (btn.dataset.navHandled) return;
                
                // Debug: only log important navigation buttons (reduce console spam)
                // Removed verbose button logging to clean up console
                
                // Check for SVG icons to identify icon-only buttons
                const hasSvg = btn.querySelector("svg");
                const svgClass = hasSvg?.classList.toString().toLowerCase() || "";
                
                // Search & Browse (check for "search" in text OR search icon)
                if (text.includes("search") || svgClass.includes("search")) {
                    btn.dataset.navHandled = "true";
                    btn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        console.log("[MovieShows] Search button clicked");
                        const panel = createSearchPanel();
                        openPanel(panel);
                        setTimeout(() => document.getElementById("movie-search-input")?.focus(), 100);
                    }, true);
                    console.log("[MovieShows] Bound Search & Browse button");
                }
                
                // Filters (check for "filter" in text OR filter/sliders icon)
                if (text.includes("filter") || svgClass.includes("filter") || svgClass.includes("sliders")) {
                    btn.dataset.navHandled = "true";
                    btn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        console.log("[MovieShows] Filters button clicked");
                        const panel = createFilterPanel();
                        openPanel(panel);
                    }, true);
                    console.log("[MovieShows] Bound Filters button");
                }
                
                // My Queue (check for "queue" in text - but NOT "next up" buttons)
                // Exclude "next up" and "up next" buttons which have their own function
                const isQueueButton = text.includes("queue") || text.includes("my queue");
                const isNextUpButton = text.includes("next up") || text.includes("up next");
                if (isQueueButton && !isNextUpButton) {
                    btn.dataset.navHandled = "true";
                    btn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        console.log("[MovieShows] Queue button clicked");
                        const panel = createQueuePanel();
                        openPanel(panel);
                    }, true);
                    // Only log once per unique button
                    if (!btn.dataset.queueBound) {
                        btn.dataset.queueBound = "true";
                        console.log("[MovieShows] Bound My Queue button");
                    }
                }
                
                // Category: All
                if (text.match(/^all\s*\(\s*\d+\s*\)$/i)) {
                    btn.dataset.navHandled = "true";
                    btn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        if (currentFilter !== 'all') {
                            currentFilter = 'all';
                            updateCategoryButtons();
                            repopulateFeedWithFilter();
                            showToast("Showing all content");
                        }
                    }, true);
                }
                
                // Category: Movies
                if (text.match(/^movies\s*\(\s*\d+\s*\)$/i)) {
                    btn.dataset.navHandled = "true";
                    btn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        if (currentFilter !== 'movies') {
                            currentFilter = 'movies';
                            updateCategoryButtons();
                            repopulateFeedWithFilter();
                            showToast("Showing movies only");
                        }
                    }, true);
                }
                
                // Category: TV
                if (text.match(/^tv\s*\(\s*\d+\s*\)$/i)) {
                    btn.dataset.navHandled = "true";
                    btn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        if (currentFilter !== 'tv') {
                            currentFilter = 'tv';
                            updateCategoryButtons();
                            repopulateFeedWithFilter();
                            showToast("Showing TV shows only");
                        }
                    }, true);
                }
                
                // Category: Now Playing (flexible regex to match various formats)
                if (text.match(/now\s*playing/i) && text.includes("(")) {
                    btn.dataset.navHandled = "true";
                    console.log("[MovieShows] Bound Now Playing button:", text);
                    btn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        if (currentFilter !== 'nowplaying') {
                            currentFilter = 'nowplaying';
                            updateCategoryButtons();
                            repopulateFeedWithFilter();
                            showToast("Showing now playing in theaters");
                        }
                    }, true);
                }
                
                // List/Save button - check for various button text patterns
                if (text === "list" || text === "save" || text === "+list" || text.includes("list") || text.includes("save")) {
                    // Skip if it's a different button type (filter, share, etc.)
                    if (text.includes("filter") || text.includes("search") || text.includes("share")) return;
                    
                    btn.dataset.navHandled = "true";
                    btn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        
                        console.log("[MovieShows] List button clicked");
                        
                        const slide = btn.closest(".snap-center") || videoSlides[currentIndex];
                        if (slide) {
                            const title = slide.querySelector("h2")?.textContent || slide.getAttribute("data-movie-title");
                            console.log("[MovieShows] Adding to queue:", title);
                            if (title) {
                                const movie = allMoviesData.find(m => m.title === title);
                                if (movie) {
                                    addToQueue(movie);
                                } else {
                                    // Fallback: create minimal movie object from slide data
                                    addToQueue({ title: title });
                                }
                            }
                        }
                    }, true);
                }
                
                // Like button
                if (text === "like") {
                    btn.dataset.navHandled = "true";
                    btn.dataset.action = "like";
                    btn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        const slide = btn.closest(".snap-center") || videoSlides[currentIndex];
                        if (slide) {
                            const title = slide.querySelector("h2")?.textContent || slide.getAttribute("data-movie-title");
                            if (title) {
                                const movie = allMoviesData.find(m => m.title === title);
                                if (movie) {
                                    toggleLike(movie);
                                    // Update this button's appearance
                                    const liked = isLiked(movie.title);
                                    btn.innerHTML = liked ? '❤️<br><span style="font-size:10px">Liked</span>' : '🤍<br><span style="font-size:10px">Like</span>';
                                }
                            }
                        }
                    }, true);
                }
                
                // Share button
                if (text === "share") {
                    btn.dataset.navHandled = "true";
                    btn.addEventListener("click", (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        const slide = btn.closest(".snap-center") || videoSlides[currentIndex];
                        if (slide) {
                            const title = slide.querySelector("h2")?.textContent || slide.getAttribute("data-movie-title");
                            if (title) {
                                const movie = allMoviesData.find(m => m.title === title);
                                if (movie) shareMovie(movie);
                            }
                        }
                    }, true);
                }
            });
        };
        
        // Run immediately
        findAndSetupNavButtons();
        
        // Re-run when DOM changes to catch dynamically added buttons
        const navObserver = new MutationObserver(() => {
            findAndSetupNavButtons();
        });
        navObserver.observe(document.body, { childList: true, subtree: true });
        
        // Handle Escape key to close panels
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                [searchPanel, filterPanel, queuePanel].forEach(p => {
                    if (p) closePanel(p);
                });
            }
        });
        
        console.log("[MovieShows] Navigation handlers set up");
    }
    
    function updateCategoryButtons() {
        // Calculate actual counts from data
        const allWithTrailers = allMoviesData.filter(m => m.trailerUrl && m.trailerUrl.length > 10);
        const moviesWithTrailers = allWithTrailers.filter(m => !m.type || m.type === 'movie' || m.type === 'Movie');
        const tvWithTrailers = allWithTrailers.filter(m => m.type === 'tv' || m.type === 'TV' || m.type === 'series');
        const nowPlayingWithTrailers = allWithTrailers.filter(m => 
            m.source === 'Now Playing' || m.source === 'In Theatres' || 
            (m.nowPlaying && m.nowPlaying.length > 0)
        );
        
        // Update the visual state and counts of category buttons
        const buttons = document.querySelectorAll("button");
        buttons.forEach(btn => {
            const text = btn.textContent?.toLowerCase() || "";
            const isActive = 
                (currentFilter === 'all' && text.includes("all (")) ||
                (currentFilter === 'movies' && text.includes("movies (")) ||
                (currentFilter === 'tv' && text.includes("tv (")) ||
                (currentFilter === 'nowplaying' && text.includes("now playing"));
            
            // Update counts in button text
            if (text.includes("all (")) {
                btn.textContent = `All (${allWithTrailers.length})`;
            } else if (text.includes("movies (")) {
                btn.textContent = `Movies (${moviesWithTrailers.length})`;
            } else if (text.includes("tv (")) {
                btn.textContent = `TV (${tvWithTrailers.length})`;
            } else if (text.includes("now playing")) {
                btn.textContent = `Now Playing (${nowPlayingWithTrailers.length})`;
            }
            
            // Update visual styling
            if (text.includes("all (") || text.includes("movies (") || text.includes("tv (") || text.includes("now playing")) {
                if (isActive) {
                    btn.style.background = "#22c55e";
                    btn.style.color = "black";
                } else {
                    btn.style.background = "";
                    btn.style.color = "";
                }
            }
        });
    }

    // ========== PLAYER SIZE CONTROL ==========

    let settingsCollapsed = localStorage.getItem("movieshows-settings-collapsed") === "true";
    
    function createPlayerSizeControl() {
        if (document.getElementById("player-size-control")) return;

        const wrapper = document.createElement("div");
        wrapper.id = "player-size-wrapper";
        wrapper.style.cssText = `
            position: fixed;
            top: 60px;
            right: 10px;
            z-index: 9998;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
        `;
        
        // Toggle button to show/hide settings
        const toggleBtn = document.createElement("button");
        toggleBtn.id = "settings-toggle";
        toggleBtn.innerHTML = settingsCollapsed ? "⚙️ Settings" : "✕ Hide";
        toggleBtn.style.cssText = `
            background: rgba(0, 0, 0, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
            padding: 6px 14px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
            backdrop-filter: blur(10px);
            transition: all 0.2s;
        `;
        toggleBtn.addEventListener("mouseenter", () => {
            toggleBtn.style.background = "rgba(34, 197, 94, 0.8)";
        });
        toggleBtn.addEventListener("mouseleave", () => {
            toggleBtn.style.background = "rgba(0, 0, 0, 0.7)";
        });

        const control = document.createElement("div");
        control.id = "player-size-control";
        control.innerHTML = `
      <span style="color: #888; font-size: 11px; margin-right: 8px;">Player:</span>
      <button data-size="small">S</button>
      <button data-size="medium">M</button>
      <button data-size="large" class="active">L</button>
      <button data-size="full">Full</button>
    `;
        
        // Apply collapsed state
        if (settingsCollapsed) {
            control.style.display = "none";
        }
        
        toggleBtn.addEventListener("click", () => {
            settingsCollapsed = !settingsCollapsed;
            localStorage.setItem("movieshows-settings-collapsed", settingsCollapsed ? "true" : "false");
            control.style.display = settingsCollapsed ? "none" : "";
            toggleBtn.innerHTML = settingsCollapsed ? "⚙️ Settings" : "✕ Hide";
            
            // Also hide/show the layout control
            const layoutControl = document.getElementById("layout-control");
            if (layoutControl) {
                layoutControl.style.display = settingsCollapsed ? "none" : "";
            }
        });
        
        wrapper.appendChild(toggleBtn);
        wrapper.appendChild(control);
        document.body.appendChild(wrapper);

        const savedSize = localStorage.getItem("movieshows-player-size") || "large";
        setPlayerSize(savedSize);

        control.querySelectorAll("button").forEach((btn) => {
            btn.addEventListener("click", () => {
                const size = btn.dataset.size;
                setPlayerSize(size);
                localStorage.setItem("movieshows-player-size", size);
            });
        });
    }

    function findCarouselElement() {
        // Heuristic to find the bottom carousel
        // Look for the "Hot Picks" section specifically
        const headings = Array.from(document.querySelectorAll('h3'));
        const hotPicksHeader = headings.find(h => h.textContent.includes('Hot Picks'));
        if (hotPicksHeader) {
            let p = hotPicksHeader.parentElement;
            while (p && p.tagName !== 'BODY') {
                const style = window.getComputedStyle(p);
                // "absolute top-[85vh]..."
                if ((style.position === 'absolute' || style.position === 'fixed') &&
                    (style.top.includes('85vh') || p.classList.contains('top-[85vh]'))) {
                    return p;
                }
                if (p.querySelector && p.querySelector('.overflow-x-auto')) {
                    const wrapper = p.closest('section') || p.parentElement;
                    return wrapper;
                }
                p = p.parentElement;
            }
        }

        // Fallback: look for the specific top-[85vh] Class
        const specific = document.querySelector('.top-\\[85vh\\]');
        if (specific) return specific;

        // Fallback heuristic
        const candidates = Array.from(document.querySelectorAll('div'));
        return candidates.find(el => {
            const style = window.getComputedStyle(el);
            return (style.position === 'absolute' && style.top.includes('85vh'));
        });
    }

    function updateCarouselVisibility() {
        const carousel = findCarouselElement();
        if (!carousel) {
            console.log("[MovieShows] Carousel NOT found");
            return;
        }

        console.log("[MovieShows] Toggling carousel:", carousel);

        const shouldHide = document.body.classList.contains('carousel-hidden');
        // Use display: none !important to force it
        if (shouldHide) {
            carousel.style.setProperty('display', 'none', 'important');
        } else {
            carousel.style.setProperty('display', 'block', 'important'); // Or original display? 
            // Better to just remove the property if showing, but if we set none important we might need block important
            // Try removing first
            carousel.style.removeProperty('display');
            if (window.getComputedStyle(carousel).display === 'none') {
                carousel.style.setProperty('display', 'block', 'important');
            }
        }
    }

    function createLayoutControl() {
        if (document.getElementById("layout-control")) return;

        const control = document.createElement("div");
        control.id = "layout-control";
        control.style.marginTop = "4px";
        control.innerHTML = `
      <div style="display: flex; align-items: center; gap: 4px; margin-bottom: 4px;">
          <span style="color: #888; font-size: 11px; margin-right: 2px;">Txt:</span>
          <button data-layout="default" class="active">Def</button>
          <button data-layout="raised">High</button>
          <button data-layout="center">Mid</button>
      </div>
      <div style="display: flex; align-items: center; justify-content:space-between; gap: 2px; margin-bottom: 4px;">
          <div style="display:flex; align-items:center; gap:2px;">
             <span style="color: #888; font-size: 11px;">Y:</span>
             <button id="adj-up" style="padding: 2px 6px;">▲</button>
             <button id="adj-down" style="padding: 2px 6px;">▼</button>
             <span id="adj-val-y" style="color: #fff; font-size: 10px; min-width: 25px; text-align: center;">0</span>
          </div>
          <div style="display:flex; align-items:center; gap:2px;">
             <span style="color: #888; font-size: 11px;">X:</span>
             <button id="adj-left" style="padding: 2px 6px;">◄</button>
             <button id="adj-right" style="padding: 2px 6px;">►</button>
             <span id="adj-val-x" style="color: #fff; font-size: 10px; min-width: 25px; text-align: center;">0</span>
          </div>
      </div>
      <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
          <button data-action="toggle-carousel" class="active" style="width:100%;">Bar: Show</button>
      </div>
      <div style="display: flex; align-items: center; gap: 4px;">
          <span style="color: #888; font-size: 11px; margin-right: 2px;">Dtl:</span>
          <button data-detail="full" class="active">Full</button>
          <button data-detail="title">Title</button>
      </div>
      <div id="volume-control-section" style="display: flex; flex-direction: column; gap: 6px; margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
          <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="color: #888; font-size: 11px;">🔊 Volume:</span>
              <span id="volume-value" style="color: #22c55e; font-size: 12px; font-weight: bold;">${volumeLevel}%</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
              <button id="volume-mute-btn" style="padding: 4px 8px; font-size: 14px;">${isMuted ? '🔇' : '🔊'}</button>
              <input type="range" id="volume-slider" min="0" max="100" value="${volumeLevel}" style="
                  flex: 1;
                  height: 6px;
                  -webkit-appearance: none;
                  appearance: none;
                  background: linear-gradient(to right, #22c55e ${volumeLevel}%, #333 ${volumeLevel}%);
                  border-radius: 3px;
                  cursor: pointer;
              ">
          </div>
      </div>
      <div id="auto-scroll-section" style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.1);">
          <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="color: #888; font-size: 11px;">⏩ Auto-next (at video end):</span>
              <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
                  <input type="checkbox" id="auto-scroll-toggle" ${autoScrollEnabled ? 'checked' : ''} style="
                      width: 36px;
                      height: 18px;
                      appearance: none;
                      background: ${autoScrollEnabled ? '#22c55e' : '#333'};
                      border-radius: 9px;
                      position: relative;
                      cursor: pointer;
                      transition: background 0.3s;
                  ">
                  <span style="color: ${autoScrollEnabled ? '#22c55e' : '#888'}; font-size: 11px; font-weight: bold;">${autoScrollEnabled ? 'ON' : 'OFF'}</span>
              </label>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
              <span style="color: #666; font-size: 10px;">Wait after end:</span>
              <input type="range" id="auto-scroll-delay-input" min="1" max="15" value="${autoScrollDelay}" style="
                  flex: 1;
                  height: 6px;
                  -webkit-appearance: none;
                  appearance: none;
                  background: linear-gradient(to right, #3b82f6 ${((autoScrollDelay - 1) / 14) * 100}%, #333 ${((autoScrollDelay - 1) / 14) * 100}%);
                  border-radius: 3px;
                  cursor: pointer;
              ">
              <span id="auto-scroll-delay-value" style="color: #3b82f6; font-size: 12px; font-weight: bold; min-width: 28px;">${autoScrollDelay}s</span>
          </div>
      </div>
    `;

        const container = document.getElementById("player-size-control");
        if (container) {
            container.appendChild(control);

            // Layout Mode
            const layoutBtns = control.querySelectorAll('button[data-layout]');
            layoutBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    layoutBtns.forEach(b => b.classList.remove('active'));
                    e.target.classList.add('active');
                    setTextLayout(e.target.dataset.layout);
                });
            });

            // Detail Mode
            const detailBtns = control.querySelectorAll('button[data-detail]');
            detailBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    detailBtns.forEach(b => b.classList.remove('active'));
                    e.target.classList.add('active');
                    const mode = e.target.dataset.detail;
                    document.body.classList.remove('detail-full', 'detail-title');
                    document.body.classList.add(`detail-${mode}`);
                });
            });

            // Carousel Toggle
            const carouselBtn = control.querySelector('[data-action="toggle-carousel"]');
            carouselBtn.addEventListener('click', () => {
                document.body.classList.toggle('carousel-hidden');
                const isHidden = document.body.classList.contains('carousel-hidden');
                carouselBtn.textContent = isHidden ? 'Bar: Hide' : 'Bar: Show';
                carouselBtn.classList.toggle('active', !isHidden);
                updateCarouselVisibility();
            });

            // Manual Adjustment
            let currentOffsetY = 0;
            let currentOffsetX = 0;

            const updateOffset = () => {
                document.documentElement.style.setProperty('--text-offset-y', `${currentOffsetY}px`);
                document.documentElement.style.setProperty('--text-offset-x', `${currentOffsetX}px`);
                document.getElementById('adj-val-y').textContent = currentOffsetY;
                document.getElementById('adj-val-x').textContent = currentOffsetX;
            };

            document.getElementById('adj-up').addEventListener('click', () => { currentOffsetY += 10; updateOffset(); });
            document.getElementById('adj-down').addEventListener('click', () => { currentOffsetY -= 10; updateOffset(); });
            document.getElementById('adj-left').addEventListener('click', () => { currentOffsetX -= 10; updateOffset(); });
            document.getElementById('adj-right').addEventListener('click', () => { currentOffsetX += 10; updateOffset(); });
            
            // Volume Slider Control
            const volumeSlider = document.getElementById('volume-slider');
            const volumeValue = document.getElementById('volume-value');
            const volumeMuteBtn = document.getElementById('volume-mute-btn');
            
            if (volumeSlider) {
                volumeSlider.addEventListener('input', (e) => {
                    volumeLevel = parseInt(e.target.value);
                    localStorage.setItem("movieshows-volume", volumeLevel);
                    volumeValue.textContent = `${volumeLevel}%`;
                    // Update slider background gradient
                    volumeSlider.style.background = `linear-gradient(to right, #22c55e ${volumeLevel}%, #333 ${volumeLevel}%)`;
                    
                    // If volume > 0 and currently muted, unmute
                    if (volumeLevel > 0 && isMuted) {
                        toggleMute();
                    }
                    // If volume is 0, mute
                    if (volumeLevel === 0 && !isMuted) {
                        toggleMute();
                    }
                    
                    applyVolumeToVideos();
                });
            }
            
            if (volumeMuteBtn) {
                volumeMuteBtn.addEventListener('click', () => {
                    toggleMute();
                    volumeMuteBtn.textContent = isMuted ? '🔇' : '🔊';
                });
            }
            
            // Auto-scroll Controls
            const autoScrollToggle = document.getElementById('auto-scroll-toggle');
            const autoScrollDelayInput = document.getElementById('auto-scroll-delay-input');
            const autoScrollDelayValue = document.getElementById('auto-scroll-delay-value');
            
            if (autoScrollToggle) {
                // Style the toggle checkbox
                const updateToggleStyle = () => {
                    autoScrollToggle.style.background = autoScrollEnabled ? '#22c55e' : '#333';
                    const label = autoScrollToggle.nextElementSibling;
                    if (label) {
                        label.style.color = autoScrollEnabled ? '#22c55e' : '#888';
                        label.textContent = autoScrollEnabled ? 'ON' : 'OFF';
                    }
                };
                
                autoScrollToggle.addEventListener('change', () => {
                    toggleAutoScroll();
                    updateToggleStyle();
                });
                
                // Add thumb to toggle
                const style = document.createElement('style');
                style.textContent = `
                    #auto-scroll-toggle::before {
                        content: '';
                        position: absolute;
                        width: 14px;
                        height: 14px;
                        border-radius: 50%;
                        background: white;
                        top: 2px;
                        left: ${autoScrollEnabled ? '20px' : '2px'};
                        transition: left 0.3s;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.3);
                    }
                    #auto-scroll-toggle:checked::before {
                        left: 20px;
                    }
                `;
                document.head.appendChild(style);
            }
            
            if (autoScrollDelayInput) {
                autoScrollDelayInput.addEventListener('input', (e) => {
                    const newDelay = parseInt(e.target.value);
                    autoScrollDelay = newDelay;
                    localStorage.setItem("movieshows-auto-scroll-delay", newDelay.toString());
                    
                    if (autoScrollDelayValue) {
                        autoScrollDelayValue.textContent = `${newDelay}s`;
                    }
                    
                    // Update slider background
                    const percent = ((newDelay - 1) / 14) * 100;
                    autoScrollDelayInput.style.background = `linear-gradient(to right, #3b82f6 ${percent}%, #333 ${percent}%)`;
                });
                
                autoScrollDelayInput.addEventListener('change', (e) => {
                    const newDelay = parseInt(e.target.value);
                    setAutoScrollDelay(newDelay);
                });
            }
        } else {
            document.body.appendChild(control);
        }

        // Initialize saved layout
        const savedLayout = localStorage.getItem("movieshows-text-layout") || "default";
        setTextLayout(savedLayout);
    }
    
    function applyVolumeToVideos() {
        // Note: YouTube iframe API doesn't allow direct volume control without the JS API
        // We use URL params for mute state. For volume, we'd need YouTube Player API
        // For now, we show this is a preference that will be applied when possible
        console.log(`[MovieShows] Volume set to ${volumeLevel}%`);
    }
    
    function updateVolumeControlUI() {
        const volumeSlider = document.getElementById('volume-slider');
        const volumeValue = document.getElementById('volume-value');
        const volumeMuteBtn = document.getElementById('volume-mute-btn');
        
        if (volumeSlider) {
            volumeSlider.value = volumeLevel;
            volumeSlider.style.background = `linear-gradient(to right, #22c55e ${volumeLevel}%, #333 ${volumeLevel}%)`;
        }
        if (volumeValue) {
            volumeValue.textContent = `${volumeLevel}%`;
        }
        if (volumeMuteBtn) {
            volumeMuteBtn.textContent = isMuted ? '🔇' : '🔊';
        }
    }

    // ========== AUTO-SCROLL FUNCTIONALITY ==========
    // Now triggers at END of video, not arbitrary timer
    
    function initYouTubeAPI() {
        // We rely on postMessage infoDelivery for video end detection
        // which works without needing to create YT.Player instances
        ytApiReady = true;
        console.log('[MovieShows] YouTube event detection ready (via postMessage)');
    }
    
    let lastVideoEndedTime = 0;
    const VIDEO_END_DEBOUNCE_MS = 2000; // Prevent duplicate triggers within 2 seconds
    let currentVideoDuration = 0;
    let currentVideoTime = 0;
    let videoEndCheckInterval = null;
    
    function onVideoEnded() {
        // Debounce: prevent duplicate end triggers
        const now = Date.now();
        if (now - lastVideoEndedTime < VIDEO_END_DEBOUNCE_MS) {
            console.log('[MovieShows] Video ended event ignored (debounced)');
            return;
        }
        lastVideoEndedTime = now;
        
        // Don't trigger if already waiting for scroll
        if (videoEndedWaitingForScroll) {
            console.log('[MovieShows] Video ended but already waiting for scroll');
            return;
        }
        
        if (!autoScrollEnabled || autoScrollPaused) {
            console.log('[MovieShows] Video ended but auto-scroll disabled or paused');
            return;
        }
        
        console.log(`[MovieShows] VIDEO ENDED! Starting ${autoScrollDelay}s countdown to next video...`);
        videoEndedWaitingForScroll = true;
        
        // Reset tracking
        currentVideoDuration = 0;
        currentVideoTime = 0;
        
        // Show countdown indicator
        startPostVideoCountdown();
    }
    
    // Track video progress from infoDelivery messages
    function trackVideoProgress(currentTime, duration) {
        if (!duration || duration <= 0) return;
        
        currentVideoDuration = duration;
        currentVideoTime = currentTime;
        
        // Check if video has reached the end (within 1 second of duration)
        const remaining = duration - currentTime;
        if (remaining <= 1 && currentTime > 0 && !videoEndedWaitingForScroll) {
            console.log(`[MovieShows] Video reached end via progress tracking: ${currentTime.toFixed(1)}/${duration.toFixed(1)}`);
            onVideoEnded();
        }
    }
    
    function startPostVideoCountdown() {
        if (!autoScrollEnabled) return;
        
        stopAutoScrollTimer();
        
        autoScrollCountdown = autoScrollDelay;
        autoScrollPaused = false;
        
        // Create/update countdown display
        createAutoScrollIndicator();
        updateAutoScrollIndicator();
        
        console.log(`[MovieShows] Post-video countdown: ${autoScrollDelay}s until next video`);
        
        autoScrollCountdownInterval = setInterval(() => {
            if (autoScrollPaused) return;
            
            autoScrollCountdown--;
            updateAutoScrollIndicator();
            
            if (autoScrollCountdown <= 0) {
                stopAutoScrollTimer();
                videoEndedWaitingForScroll = false;
                scrollToNextVideo();
            }
        }, 1000);
    }
    
    function startAutoScrollTimer() {
        // This is now just for showing status - actual scroll triggers on video end
        if (!autoScrollEnabled) return;
        
        // Hide the countdown indicator while video is playing
        hideAutoScrollIndicator();
        videoEndedWaitingForScroll = false;
        
        console.log(`[MovieShows] Auto-scroll ready: will advance when video ends`);
    }
    
    function stopAutoScrollTimer() {
        if (autoScrollTimer) {
            clearTimeout(autoScrollTimer);
            autoScrollTimer = null;
        }
        if (autoScrollCountdownInterval) {
            clearInterval(autoScrollCountdownInterval);
            autoScrollCountdownInterval = null;
        }
        autoScrollCountdown = 0;
        videoEndedWaitingForScroll = false;
        hideAutoScrollIndicator();
    }
    
    function pauseAutoScrollTimer() {
        autoScrollPaused = true;
        updateAutoScrollIndicator();
    }
    
    function resumeAutoScrollTimer() {
        autoScrollPaused = false;
        updateAutoScrollIndicator();
    }
    
    function resetAutoScrollTimer() {
        // Just reset the status - video end will trigger actual scroll
        if (autoScrollEnabled) {
            startAutoScrollTimer();
        }
    }
    
    // Listen for YouTube iframe messages (for video end detection)
    let youtubeMessageListenerSetup = false;
    
    function setupYouTubeMessageListener() {
        // Prevent duplicate listener registration
        if (youtubeMessageListenerSetup) {
            console.log('[MovieShows] YouTube message listener already set up');
            return;
        }
        youtubeMessageListenerSetup = true;
        
        window.addEventListener('message', function(event) {
            // Handle messages from YouTube domain
            if (!event.origin.includes('youtube.com')) return;
            
            try {
                let data = event.data;
                
                // YouTube sometimes sends string, sometimes object
                if (typeof data === 'string') {
                    data = JSON.parse(data);
                }
                
                // Debug: Only log non-infoDelivery YouTube messages to reduce spam
                if (data && data.event && data.event !== 'infoDelivery') {
                    console.log('[MovieShows] YouTube message:', JSON.stringify(data).substring(0, 200));
                }
                
                // YouTube sends state changes through postMessage
                // State 0 = ended, 1 = playing, 2 = paused, 3 = buffering, 5 = cued
                if (data.event === 'onStateChange') {
                    console.log(`[MovieShows] YouTube state change: ${data.info}`);
                    if (data.info === 0) {
                        console.log('[MovieShows] YouTube video ENDED (via onStateChange)');
                        onVideoEnded();
                    }
                }
                
                // Check for infoDelivery format (YouTube uses this too)
                if (data.info && typeof data.info === 'object') {
                    if (typeof data.info.playerState === 'number') {
                        // Only log state changes (not every time update)
                        if (data.info.playerState !== 1 || !currentVideoDuration) {
                            console.log(`[MovieShows] YouTube playerState: ${data.info.playerState}`);
                        }
                        if (data.info.playerState === 0) {
                            console.log('[MovieShows] YouTube video ENDED (via infoDelivery playerState=0)');
                            onVideoEnded();
                        }
                    }
                    
                    // CRITICAL: Track video progress to detect end
                    // This is the most reliable method since we always receive these updates
                    if (typeof data.info.currentTime === 'number' && typeof data.info.duration === 'number') {
                        trackVideoProgress(data.info.currentTime, data.info.duration);
                    }
                }
            } catch (e) {
                // Not a JSON message or parsing error, ignore
            }
        });
        
        console.log('[MovieShows] YouTube message listener set up');
    }
    
    function scrollToNextVideo() {
        if (videoSlides.length === 0) return;
        
        const nextIndex = currentIndex + 1;
        if (nextIndex < videoSlides.length) {
            console.log(`[MovieShows] Auto-scrolling to video ${nextIndex + 1}`);
            scrollToSlide(nextIndex);
            // Timer will restart when new video plays
        } else {
            // At the end - try to load more or loop back
            console.log("[MovieShows] Reached end of videos, loading more...");
            loadMoreVideos();
            // Check again after loading
            setTimeout(() => {
                if (currentIndex + 1 < videoSlides.length) {
                    scrollToSlide(currentIndex + 1);
                }
            }, 1000);
        }
    }
    
    function createAutoScrollIndicator() {
        if (document.getElementById("auto-scroll-indicator")) return;
        
        const indicator = document.createElement("div");
        indicator.id = "auto-scroll-indicator";
        indicator.style.cssText = `
            position: fixed;
            bottom: 100px;
            right: 20px;
            background: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 10px 16px;
            border-radius: 25px;
            font-size: 13px;
            font-weight: 500;
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 10px;
            border: 2px solid rgba(34, 197, 94, 0.6);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            transition: all 0.3s ease;
            cursor: pointer;
        `;
        
        indicator.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12,6 12,12 16,14"/>
                </svg>
                <span id="auto-scroll-text">Video ended! Next in <strong id="auto-scroll-countdown">${autoScrollDelay}</strong>s</span>
            </div>
            <button id="auto-scroll-skip" style="
                background: rgba(34, 197, 94, 0.3);
                border: 1px solid #22c55e;
                color: #22c55e;
                padding: 4px 10px;
                border-radius: 12px;
                cursor: pointer;
                font-size: 11px;
                font-weight: bold;
                transition: all 0.2s;
            ">Skip ⏭</button>
            <button id="auto-scroll-pause" style="
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                cursor: pointer;
                font-size: 11px;
                transition: all 0.2s;
            ">⏸</button>
        `;
        
        document.body.appendChild(indicator);
        
        // Skip button - immediately scroll to next
        const skipBtn = document.getElementById("auto-scroll-skip");
        if (skipBtn) {
            skipBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                stopAutoScrollTimer();
                scrollToNextVideo();
            });
            skipBtn.addEventListener("mouseenter", () => {
                skipBtn.style.background = "rgba(34, 197, 94, 0.5)";
            });
            skipBtn.addEventListener("mouseleave", () => {
                skipBtn.style.background = "rgba(34, 197, 94, 0.3)";
            });
        }
        
        // Pause/Resume button
        const pauseBtn = document.getElementById("auto-scroll-pause");
        if (pauseBtn) {
            pauseBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                if (autoScrollPaused) {
                    resumeAutoScrollTimer();
                    pauseBtn.textContent = "⏸";
                    pauseBtn.title = "Pause auto-scroll";
                } else {
                    pauseAutoScrollTimer();
                    pauseBtn.textContent = "▶";
                    pauseBtn.title = "Resume auto-scroll";
                }
            });
        }
        
        // Click on indicator shows settings
        indicator.addEventListener("click", (e) => {
            if (e.target === indicator || e.target.id === "auto-scroll-text") {
                showToast(`Auto-scroll: ${autoScrollDelay}s delay. Change in Settings.`);
            }
        });
    }
    
    function updateAutoScrollIndicator() {
        const countdownEl = document.getElementById("auto-scroll-countdown");
        const indicator = document.getElementById("auto-scroll-indicator");
        const pauseBtn = document.getElementById("auto-scroll-pause");
        
        if (countdownEl) {
            countdownEl.textContent = autoScrollCountdown;
        }
        
        if (indicator) {
            if (autoScrollPaused) {
                indicator.style.borderColor = "rgba(239, 68, 68, 0.6)";
                indicator.style.opacity = "0.7";
            } else {
                indicator.style.borderColor = "rgba(34, 197, 94, 0.6)";
                indicator.style.opacity = "1";
            }
            
            // Pulse effect when countdown is low
            if (autoScrollCountdown <= 3 && !autoScrollPaused) {
                indicator.style.animation = "pulse-indicator 0.5s infinite";
            } else {
                indicator.style.animation = "none";
            }
        }
        
        if (pauseBtn) {
            pauseBtn.textContent = autoScrollPaused ? "▶" : "⏸";
        }
    }
    
    function hideAutoScrollIndicator() {
        const indicator = document.getElementById("auto-scroll-indicator");
        if (indicator) {
            indicator.style.display = "none";
        }
    }
    
    function showAutoScrollIndicator() {
        const indicator = document.getElementById("auto-scroll-indicator");
        if (indicator && autoScrollEnabled) {
            indicator.style.display = "flex";
        }
    }
    
    function toggleAutoScroll() {
        autoScrollEnabled = !autoScrollEnabled;
        localStorage.setItem("movieshows-auto-scroll", autoScrollEnabled ? "true" : "false");
        
        if (autoScrollEnabled) {
            startAutoScrollTimer();
            showToast(`Auto-next enabled (advances ${autoScrollDelay}s after video ends)`);
        } else {
            stopAutoScrollTimer();
            showToast("Auto-next disabled");
        }
        
        updateAutoScrollSettingsUI();
    }
    
    function setAutoScrollDelay(delay) {
        autoScrollDelay = Math.max(1, Math.min(15, delay)); // Clamp between 1-15 seconds (wait after video ends)
        localStorage.setItem("movieshows-auto-scroll-delay", autoScrollDelay.toString());
        
        // Restart timer with new delay if enabled
        if (autoScrollEnabled && autoScrollCountdownInterval) {
            startAutoScrollTimer();
        }
        
        updateAutoScrollSettingsUI();
        showToast(`Wait after video ends: ${autoScrollDelay}s`);
    }
    
    function updateAutoScrollSettingsUI() {
        const toggle = document.getElementById("auto-scroll-toggle");
        const delayInput = document.getElementById("auto-scroll-delay-input");
        const delayValue = document.getElementById("auto-scroll-delay-value");
        
        if (toggle) {
            toggle.checked = autoScrollEnabled;
        }
        if (delayInput) {
            delayInput.value = autoScrollDelay;
        }
        if (delayValue) {
            delayValue.textContent = `${autoScrollDelay}s`;
        }
    }
    
    // Add CSS animation for pulse effect
    function addAutoScrollStyles() {
        if (document.getElementById("auto-scroll-styles")) return;
        
        const style = document.createElement("style");
        style.id = "auto-scroll-styles";
        style.textContent = `
            @keyframes pulse-indicator {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }
            #auto-scroll-indicator:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 25px rgba(0, 0, 0, 0.6);
            }
        `;
        document.head.appendChild(style);
    }

    // ========== USER AUTHENTICATION SYSTEM ==========
    
    function createLoginButton() {
        if (document.getElementById("user-login-btn")) return;
        
        const btn = document.createElement("button");
        btn.id = "user-login-btn";
        
        const updateButtonDisplay = () => {
            if (currentUser) {
                btn.innerHTML = `<span style="font-size: 18px;">👤</span> ${currentUser.name?.split(' ')[0] || 'User'}`;
                btn.style.background = "rgba(34, 197, 94, 0.9)";
            } else {
                btn.innerHTML = `<span style="font-size: 18px;">👤</span> Sign In`;
                btn.style.background = "rgba(59, 130, 246, 0.9)";
            }
        };
        
        btn.style.cssText = `
            position: fixed;
            top: 15px;
            right: 120px;
            z-index: 10001;
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            backdrop-filter: blur(10px);
            transition: all 0.2s;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            display: flex;
            align-items: center;
            gap: 8px;
        `;
        
        updateButtonDisplay();
        
        btn.addEventListener("mouseenter", () => {
            btn.style.transform = "scale(1.05)";
        });
        btn.addEventListener("mouseleave", () => {
            btn.style.transform = "scale(1)";
        });
        
        btn.addEventListener("click", () => {
            if (currentUser) {
                showUserProfilePanel();
            } else {
                showLoginPopup();
            }
        });
        
        document.body.appendChild(btn);
        
        // Store reference for updates
        window.updateLoginButton = updateButtonDisplay;
    }
    
    // Auth API base URL
    const AUTH_API = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? '/api/auth.php'
        : 'https://findtorontoevents.ca/movieshows2/api/auth.php';
    
    function showLoginPopup() {
        // Remove existing popup
        const existing = document.getElementById("login-popup-overlay");
        if (existing) existing.remove();
        
        const overlay = document.createElement("div");
        overlay.id = "login-popup-overlay";
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.85);
            z-index: 20000;
            display: flex;
            align-items: center;
            justify-content: center;
            backdrop-filter: blur(5px);
            overflow-y: auto;
            padding: 20px;
        `;
        
        const popup = document.createElement("div");
        popup.style.cssText = `
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 24px;
            padding: 30px;
            width: 90%;
            max-width: 400px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
            position: relative;
            max-height: 90vh;
            overflow-y: auto;
        `;
        
        const inputStyle = `
            width: 100%;
            padding: 12px 16px;
            border: 2px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            background: rgba(255,255,255,0.05);
            color: white;
            font-size: 14px;
            box-sizing: border-box;
            outline: none;
            margin-bottom: 10px;
        `;
        
        const btnPrimaryStyle = `
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
            border: none;
            border-radius: 10px;
            color: white;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s, opacity 0.2s;
        `;
        
        popup.innerHTML = `
            <button id="close-login-popup" style="
                position: absolute;
                top: 12px;
                right: 12px;
                background: none;
                border: none;
                color: #888;
                font-size: 24px;
                cursor: pointer;
            ">×</button>
            
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 40px; margin-bottom: 10px;">🎬</div>
                <h2 style="color: white; margin: 0 0 8px 0; font-size: 22px;">Welcome to MovieShows</h2>
                <p style="color: #888; margin: 0; font-size: 13px;">Sign in to save your likes, queue, and watch history</p>
            </div>
            
            <!-- Google Login -->
            <button id="google-login-btn" style="
                width: 100%;
                padding: 12px;
                background: white;
                border: none;
                border-radius: 10px;
                color: #333;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            ">
                <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
                Continue with Google
            </button>
            
            <div style="display: flex; align-items: center; gap: 10px; margin: 15px 0;">
                <div style="flex: 1; height: 1px; background: rgba(255,255,255,0.1);"></div>
                <span style="color: #666; font-size: 11px;">or use email</span>
                <div style="flex: 1; height: 1px; background: rgba(255,255,255,0.1);"></div>
            </div>
            
            <!-- Login Form -->
            <div id="login-form">
                <input type="text" id="login-email" placeholder="Email or username" style="${inputStyle}">
                <input type="password" id="login-password" placeholder="Password" style="${inputStyle}">
                <button id="email-login-btn" style="${btnPrimaryStyle}">Sign In</button>
                <p style="color: #888; font-size: 12px; text-align: center; margin: 12px 0 0 0;">
                    New here? <a href="#" id="show-register" style="color: #3b82f6; text-decoration: none;">Create account</a>
                </p>
            </div>
            
            <!-- Register Form (hidden by default) -->
            <div id="register-form" style="display: none;">
                <input type="text" id="register-name" placeholder="Display name" style="${inputStyle}">
                <input type="email" id="register-email" placeholder="Email" style="${inputStyle}">
                <input type="password" id="register-password" placeholder="Password (min 6 characters)" style="${inputStyle}">
                <button id="register-btn" style="${btnPrimaryStyle}">Create Account</button>
                <p style="color: #888; font-size: 12px; text-align: center; margin: 12px 0 0 0;">
                    Already have an account? <a href="#" id="show-login" style="color: #3b82f6; text-decoration: none;">Sign in</a>
                </p>
            </div>
            
            <div style="display: flex; align-items: center; gap: 10px; margin: 15px 0;">
                <div style="flex: 1; height: 1px; background: rgba(255,255,255,0.1);"></div>
                <span style="color: #666; font-size: 11px;">or</span>
                <div style="flex: 1; height: 1px; background: rgba(255,255,255,0.1);"></div>
            </div>
            
            <button id="guest-login-btn" style="
                width: 100%;
                padding: 12px;
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 10px;
                color: white;
                font-size: 14px;
                cursor: pointer;
            ">Continue as Guest</button>
            
            <p style="color: #555; font-size: 10px; text-align: center; margin-top: 15px;">
                By continuing, you agree to our Terms of Service and Privacy Policy
            </p>
        `;
        
        overlay.appendChild(popup);
        document.body.appendChild(overlay);
        
        // Close on overlay click
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) overlay.remove();
        });
        
        // Close button
        popup.querySelector("#close-login-popup").addEventListener("click", () => overlay.remove());
        
        // Toggle between login and register
        popup.querySelector("#show-register").addEventListener("click", (e) => {
            e.preventDefault();
            popup.querySelector("#login-form").style.display = "none";
            popup.querySelector("#register-form").style.display = "block";
        });
        
        popup.querySelector("#show-login").addEventListener("click", (e) => {
            e.preventDefault();
            popup.querySelector("#login-form").style.display = "block";
            popup.querySelector("#register-form").style.display = "none";
        });
        
        // Email/Password login
        popup.querySelector("#email-login-btn").addEventListener("click", async () => {
            const email = popup.querySelector("#login-email").value.trim();
            const password = popup.querySelector("#login-password").value;
            
            if (!email) {
                showToast("Please enter email or username", true);
                return;
            }
            if (!password) {
                showToast("Please enter password", true);
                return;
            }
            
            const btn = popup.querySelector("#email-login-btn");
            btn.textContent = "Signing in...";
            btn.disabled = true;
            
            const result = await loginWithEmailPassword(email, password);
            
            if (result.success) {
                overlay.remove();
            } else {
                btn.textContent = "Sign In";
                btn.disabled = false;
            }
        });
        
        // Register
        popup.querySelector("#register-btn").addEventListener("click", async () => {
            const name = popup.querySelector("#register-name").value.trim();
            const email = popup.querySelector("#register-email").value.trim();
            const password = popup.querySelector("#register-password").value;
            
            if (!email || !email.includes("@")) {
                showToast("Please enter a valid email", true);
                return;
            }
            if (password.length < 6) {
                showToast("Password must be at least 6 characters", true);
                return;
            }
            
            const btn = popup.querySelector("#register-btn");
            btn.textContent = "Creating account...";
            btn.disabled = true;
            
            const result = await registerUser(email, password, name);
            
            if (result.success) {
                overlay.remove();
            } else {
                btn.textContent = "Create Account";
                btn.disabled = false;
            }
        });
        
        // Google login
        popup.querySelector("#google-login-btn").addEventListener("click", () => {
            initiateGoogleLogin();
            overlay.remove();
        });
        
        // Guest login
        popup.querySelector("#guest-login-btn").addEventListener("click", () => {
            continueAsGuest();
            overlay.remove();
        });
        
        // Enter key handlers
        popup.querySelector("#login-password").addEventListener("keypress", (e) => {
            if (e.key === "Enter") popup.querySelector("#email-login-btn").click();
        });
        popup.querySelector("#register-password").addEventListener("keypress", (e) => {
            if (e.key === "Enter") popup.querySelector("#register-btn").click();
        });
    }
    
    async function loginWithEmailPassword(email, password) {
        // All authentication handled server-side for security
        try {
            const response = await fetch(AUTH_API + '?action=login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            
            const result = await response.json();
            
            if (result.success && result.user) {
                currentUser = result.user;
                localStorage.setItem("movieshows-user", JSON.stringify(currentUser));
                syncUserData();
                if (window.updateLoginButton) window.updateLoginButton();
                showToast(`Welcome back, ${currentUser.name}! 🎉`);
                return { success: true };
            } else {
                // NO local fallback for security - only allow verified users
                showToast(result.error || "Invalid credentials", true);
                return { success: false };
            }
        } catch (error) {
            console.error("[MovieShows] Login error:", error);
            // NO local fallback - database required for email login
            showToast("Login service unavailable. Try again later or continue as guest.", true);
            return { success: false };
        }
    }
    
    // Local login removed for security - only admin/admin works offline
    
    async function registerUser(email, password, displayName) {
        try {
            const response = await fetch(AUTH_API + '?action=register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password, displayName })
            });
            
            const result = await response.json();
            
            if (result.success && result.user) {
                currentUser = result.user;
                localStorage.setItem("movieshows-user", JSON.stringify(currentUser));
                syncUserData();
                if (window.updateLoginButton) window.updateLoginButton();
                showToast(`Account created! Welcome, ${currentUser.name}! 🎉`);
                return { success: true };
            } else {
                // NO local fallback for security
                showToast(result.error || "Registration unavailable. Please try again later.", true);
                return { success: false };
            }
        } catch (error) {
            console.error("[MovieShows] Registration error:", error);
            // NO local fallback - database required for registration
            showToast("Registration service unavailable. Continue as guest for now.", true);
            return { success: false };
        }
    }
    
    function continueAsGuest() {
        const guestId = "guest_" + Math.random().toString(36).substring(2, 10);
        currentUser = {
            id: guestId,
            name: "Guest",
            loginMethod: "guest",
            createdAt: new Date().toISOString()
        };
        localStorage.setItem("movieshows-user", JSON.stringify(currentUser));
        
        if (window.updateLoginButton) window.updateLoginButton();
        showToast("Continuing as guest - your data is saved locally");
    }
    
    function showUserProfilePanel() {
        const existing = document.getElementById("user-profile-panel");
        if (existing) { existing.remove(); return; }
        
        const panel = document.createElement("div");
        panel.id = "user-profile-panel";
        panel.style.cssText = `
            position: fixed;
            top: 70px;
            right: 120px;
            z-index: 20000;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 20px;
            width: 280px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
        `;
        
        panel.innerHTML = `
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1);">
                <div style="width: 50px; height: 50px; background: linear-gradient(135deg, #3b82f6, #6366f1); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px;">
                    ${currentUser?.name?.charAt(0)?.toUpperCase() || '👤'}
                </div>
                <div>
                    <div style="color: white; font-weight: bold; font-size: 16px;">${currentUser?.name || 'User'}</div>
                    <div style="color: #888; font-size: 12px;">${currentUser?.email || currentUser?.loginMethod || 'Guest'}</div>
                </div>
            </div>
            
            <div style="margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-around; text-align: center;">
                    <div>
                        <div style="color: #3b82f6; font-size: 24px; font-weight: bold;">${likedMovies.length}</div>
                        <div style="color: #888; font-size: 11px;">Likes</div>
                    </div>
                    <div>
                        <div style="color: #22c55e; font-size: 24px; font-weight: bold;">${userQueue.length}</div>
                        <div style="color: #888; font-size: 11px;">Queue</div>
                    </div>
                    <div>
                        <div style="color: #f59e0b; font-size: 24px; font-weight: bold;">${watchedHistory.length}</div>
                        <div style="color: #888; font-size: 11px;">Watched</div>
                    </div>
                </div>
            </div>
            
            <button id="logout-btn" style="
                width: 100%;
                padding: 12px;
                background: rgba(239, 68, 68, 0.2);
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 10px;
                color: #ef4444;
                font-size: 14px;
                cursor: pointer;
                transition: all 0.2s;
            ">Sign Out</button>
        `;
        
        document.body.appendChild(panel);
        
        // Close when clicking outside
        const closePanel = (e) => {
            if (!panel.contains(e.target) && e.target.id !== "user-login-btn") {
                panel.remove();
                document.removeEventListener("click", closePanel);
            }
        };
        setTimeout(() => document.addEventListener("click", closePanel), 100);
        
        // Logout
        panel.querySelector("#logout-btn").addEventListener("click", () => {
            currentUser = null;
            localStorage.removeItem("movieshows-user");
            if (window.updateLoginButton) window.updateLoginButton();
            panel.remove();
            showToast("Signed out successfully");
        });
    }
    
    function syncUserData() {
        // Sync likes, queue, watch history to database if connected
        if (window.MovieShowsDB?.isConnected) {
            console.log("[MovieShows] Syncing user data to database...");
            // Future: implement full sync
        }
    }
    
    // ========== GOOGLE OAUTH ==========
    
    const GOOGLE_CLIENT_ID = '975574174292-n332bled0ud1bc51v1hcqpnmp8dass12.apps.googleusercontent.com';
    const GOOGLE_REDIRECT_URI = 'https://findtorontoevents.ca/movieshows2/api/google_callback.php';
    
    function initiateGoogleLogin() {
        // Build Google OAuth URL
        const params = new URLSearchParams({
            client_id: GOOGLE_CLIENT_ID,
            redirect_uri: GOOGLE_REDIRECT_URI,
            response_type: 'code',
            scope: 'email profile',
            access_type: 'online',
            prompt: 'select_account',
            state: '/movieshows2/'
        });
        
        const googleAuthUrl = 'https://accounts.google.com/o/oauth2/v2/auth?' + params.toString();
        
        // Open Google login in same window
        window.location.href = googleAuthUrl;
    }
    
    function checkGoogleAuthCallback() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // Check for successful Google auth
        const googleAuthData = urlParams.get('google_auth');
        if (googleAuthData) {
            try {
                const userData = JSON.parse(atob(googleAuthData));
                if (userData && userData.email) {
                    currentUser = userData;
                    localStorage.setItem("movieshows-user", JSON.stringify(currentUser));
                    
                    // Clean up URL
                    const cleanUrl = window.location.origin + window.location.pathname;
                    window.history.replaceState({}, document.title, cleanUrl);
                    
                    // Update UI
                    if (window.updateLoginButton) window.updateLoginButton();
                    showToast(`Welcome, ${userData.name}! 🎉`);
                    
                    console.log("[MovieShows] Google login successful:", userData.email);
                }
            } catch (e) {
                console.error("[MovieShows] Failed to parse Google auth data:", e);
            }
        }
        
        // Check for Google auth error
        const googleError = urlParams.get('google_error');
        if (googleError) {
            showToast("Google login failed: " + googleError, true);
            
            // Clean up URL
            const cleanUrl = window.location.origin + window.location.pathname;
            window.history.replaceState({}, document.title, cleanUrl);
        }
    }
    
    // ========== LIKE FUNCTIONALITY ==========
    
    function toggleLike(movie) {
        if (!movie?.title) return;
        
        const index = likedMovies.findIndex(m => m.title === movie.title);
        if (index >= 0) {
            likedMovies.splice(index, 1);
            showToast(`Removed from likes`);
        } else {
            likedMovies.push({
                title: movie.title,
                type: movie.type,
                posterUrl: movie.posterUrl || movie.image,
                likedAt: new Date().toISOString()
            });
            showToast(`❤️ Added to likes!`);
        }
        
        localStorage.setItem("movieshows-likes", JSON.stringify(likedMovies));
        updateLikeButtonStates();
    }
    
    function isLiked(title) {
        return likedMovies.some(m => m.title === title);
    }
    
    function updateLikeButtonStates() {
        // Update all visible like buttons based on current likes
        document.querySelectorAll('.snap-center[data-movie-title]').forEach(slide => {
            const title = slide.getAttribute('data-movie-title');
            const likeBtn = slide.querySelector('button[data-action="like"]');
            if (likeBtn && title) {
                const liked = isLiked(title);
                likeBtn.innerHTML = liked ? '❤️' : '🤍';
                likeBtn.style.color = liked ? '#ef4444' : 'white';
            }
        });
    }
    
    // ========== SHARE FUNCTIONALITY ==========
    
    /**
     * Check URL for ?play= parameter and navigate to that movie
     */
    function handlePlayUrlParameter() {
        const urlParams = new URLSearchParams(window.location.search);
        const playTitle = urlParams.get('play');
        
        if (!playTitle) return;
        
        console.log("[MovieShows] URL has play parameter:", playTitle);
        
        // Wait for data to load then find and play the movie
        const checkAndPlay = () => {
            if (!allMoviesData || allMoviesData.length === 0) {
                console.log("[MovieShows] Waiting for movies data to load...");
                setTimeout(checkAndPlay, 500);
                return;
            }
            
            // Find the movie in the database
            const movie = allMoviesData.find(m => 
                m.title.toLowerCase() === playTitle.toLowerCase() ||
                m.title.toLowerCase().includes(playTitle.toLowerCase())
            );
            
            if (movie) {
                console.log("[MovieShows] Found movie from URL:", movie.title);
                
                // Wait for slides to be populated
                setTimeout(() => {
                    // Find the slide with this movie title
                    const slides = document.querySelectorAll('.snap-center');
                    let targetIndex = -1;
                    
                    slides.forEach((slide, index) => {
                        const slideTitle = slide.querySelector('h2')?.textContent || slide.getAttribute('data-movie-title');
                        if (slideTitle && slideTitle.toLowerCase() === movie.title.toLowerCase()) {
                            targetIndex = index;
                        }
                    });
                    
                    if (targetIndex >= 0) {
                        console.log("[MovieShows] Scrolling to movie at index:", targetIndex);
                        scrollToSlide(targetIndex);
                        setTimeout(() => playSlideAtIndex(targetIndex), 500);
                    } else {
                        // Movie not in current view, try to add it at the top
                        console.log("[MovieShows] Movie not in current slides, adding to feed");
                        // For now, show a toast with the movie info
                        showToast(`Loading: ${movie.title}`);
                    }
                }, 1500);
            } else {
                console.log("[MovieShows] Movie not found in database:", playTitle);
                showToast(`Movie not found: ${playTitle}`, true);
            }
            
            // Clean the URL after processing
            const cleanUrl = window.location.origin + window.location.pathname;
            window.history.replaceState({}, document.title, cleanUrl);
        };
        
        checkAndPlay();
    }
    
    function shareMovie(movie) {
        if (!movie?.title) return;
        
        const shareUrl = `${window.location.origin}${window.location.pathname}?play=${encodeURIComponent(movie.title)}`;
        const shareText = `Check out "${movie.title}" on MovieShows! 🎬`;
        
        if (navigator.share) {
            navigator.share({
                title: movie.title,
                text: shareText,
                url: shareUrl
            }).catch(err => {
                if (err.name !== 'AbortError') {
                    copyToClipboard(shareUrl);
                }
            });
        } else {
            copyToClipboard(shareUrl);
        }
    }
    
    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            showToast("📋 Link copied to clipboard!");
        }).catch(() => {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            showToast("📋 Link copied to clipboard!");
        });
    }
    
    // ========== ADD TO WATCH HISTORY ==========
    
    function addToWatchHistory(movie) {
        if (!movie?.title) return;
        
        // Remove if already exists (to move to front)
        const index = watchHistory.findIndex(m => m.title === movie.title);
        if (index >= 0) {
            watchHistory.splice(index, 1);
        }
        
        // Add to front
        watchHistory.unshift({
            title: movie.title,
            type: movie.type,
            posterUrl: movie.posterUrl || movie.image,
            watchedAt: new Date().toISOString()
        });
        
        // Keep only last 100
        if (watchHistory.length > 100) {
            watchHistory = watchHistory.slice(0, 100);
        }
        
        localStorage.setItem("movieshows-watch-history", JSON.stringify(watchHistory));
    }

    function setTextLayout(layout) {
        document.body.classList.remove(
            "text-layout-default",
            "text-layout-raised",
            "text-layout-center",
            "text-layout-overlay",
            "text-layout-compact"
        );
        document.body.classList.add(`text-layout-${layout}`);

        const control = document.getElementById("layout-control");
        if (control) {
            control.querySelectorAll("button").forEach((btn) => {
                btn.classList.toggle("active", btn.dataset.layout === layout);
            });
        }
        console.log("[MovieShows] Text layout:", layout);
    }

    function setPlayerSize(size) {
        document.body.classList.remove(
            "player-small",
            "player-medium",
            "player-large",
            "player-full",
        );
        document.body.classList.add(`player-${size}`);

        const control = document.getElementById("player-size-control");
        if (control) {
            // Only toggle the size buttons, which are direct children of the container's top level (before we added the layout control) or we need to be specific
            // Actually, we can just look for buttons with data-size
            control.querySelectorAll("button[data-size]").forEach((btn) => {
                btn.classList.toggle("active", btn.dataset.size === size);
            });
        }

        // Apply size directly to iframes found on page
        applyPlayerSize(size);

        console.log("[MovieShows] Player size:", size);
    }

    function applyPlayerSize(size) {
        const heights = {
            small: "40vh",
            medium: "60vh",
            large: "85vh",
            full: "100vh",
        };

        const height = heights[size] || heights.large;

        // 1. Resize all iframes
        const iframes = document.querySelectorAll('iframe');
        iframes.forEach((iframe) => {
            iframe.style.height = height;
            iframe.style.maxHeight = height;
        });

        // 2. Resize the main section container
        // struct: section > div.group/player
        const playerGroups = document.querySelectorAll('.group\\/player');
        playerGroups.forEach(group => {
            // Resize the group itself
            group.style.height = height;

            // Resize the parent section
            const section = group.closest('section');
            if (section) {
                section.style.height = height;
                section.style.maxHeight = height;
                // Ensure z-index is correct for full screen
                if (size === 'full') {
                    section.style.zIndex = '50';
                } else {
                    section.style.removeProperty('z-index');
                }
            }
        });

        // 3. Fallback: Search for the section by class signature if group not found
        if (playerGroups.length === 0) {
            const sections = document.querySelectorAll('section');
            sections.forEach(sec => {
                if (sec.classList.contains('bg-black') && sec.classList.contains('z-10')) {
                    sec.style.height = height;
                }
            });
        }
    }

    function fixCarouselZIndex() {
        // Use the existing finder logic
        const carousel = findCarouselElement();
        if (carousel) {
            carousel.style.zIndex = "1000"; // Ensure it's above everything including the player
            // If it's fixed or absolute, z-index will work
        }
    }

    let isProcessingCarouselClick = false;

    function setupCarouselInteractions() {
        const observer = new MutationObserver(() => {
            const carousel = findCarouselElement();
            if (!carousel) return;

            const items = carousel.querySelectorAll('img:not([data-click-handled])');
            items.forEach(img => {
                img.setAttribute('data-click-handled', 'true');
                // Target the parent A tag or DIV, or just the IMG itself if no parent
                const container = img.closest('a') || img.closest('div.cursor-pointer') || img.parentElement;

                // Allow clicking the image itself if container is weird
                const target = container || img;

                target.style.pointerEvents = "auto";
                target.style.cursor = "pointer";

                target.addEventListener('click', (e) => {
                    // Stop any other listeners (like the broken one)
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();

                    if (isProcessingCarouselClick) return;
                    isProcessingCarouselClick = true;
                    setTimeout(() => { isProcessingCarouselClick = false; }, 1000);

                    const title = img.alt || img.title;
                    console.log(`[MovieShows] Clicked carousel item: "${title}"`);
                    if (!title) return;

                    // 1. Check if already properly loaded in feed (Video Slides)
                    // We check the LAST 50 slides to save perf but cover most use cases
                    const recentSlides = videoSlides;
                    let index = -1;

                    // First exact match (Case insensitive)
                    index = recentSlides.findIndex(slide => {
                        const h2 = slide.querySelector('h2');
                        return h2 && h2.textContent.toLowerCase().trim() === title.toLowerCase().trim();
                    });

                    // If not found, try VERY Strict inclusion (must contain full title)
                    if (index === -1) {
                        index = recentSlides.findIndex(slide => {
                            const h2 = slide.querySelector('h2');
                            // If title is "Scream 7", "Scream" should NOT match.
                            // But if title is "Scream", "Scream 7" might be okay? No, let's be strict.
                            // The carousel item is usually the "source of truth" for what user wants.
                            return h2 && h2.textContent.toLowerCase() === title.toLowerCase();
                        });
                    }

                    if (index !== -1) {
                        console.log(`[MovieShows] Found in feed at index ${index}. Jumping...`);
                        scrollToSlide(index);
                        return;
                    }

                    // 2. Load from DB or Fallback
                    let movie = null;

                    if (allMoviesData.length > 0) {
                        // Improved Fuzzy Match Strategy
                        const normalize = (str) => str.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim();
                        const targetSlug = normalize(title);
                        const targetTokens = targetSlug.split(' ').filter(t => t.length > 2);

                        movie = allMoviesData.find(m => {
                            const mTitle = normalize(m.title);
                            return mTitle.includes(targetSlug) || targetSlug.includes(mTitle);
                        });

                        // Fallback: Token matching
                        if (!movie && targetTokens.length > 0) {
                            movie = allMoviesData.find(m => {
                                const mTitle = normalize(m.title);
                                return targetTokens.some(token => mTitle.includes(token));
                            });
                        }
                    }

                    // 3. Check hardcoded Fallback Data (for missing 2026 Hot Picks)
                    if (!movie) {
                        const fallbackMovies = [
                            {
                                title: "Scream 7",
                                year: "2026",
                                trailerUrl: "https://www.youtube.com/watch?v=UJrghaPJ0RY", // Official Teaser
                                genres: ["Horror", "Mystery"],
                                rating: "8.5"
                            },
                            {
                                title: "Scream", // In case title is just Scream
                                year: "2026",
                                trailerUrl: "https://www.youtube.com/watch?v=UJrghaPJ0RY",
                                genres: ["Horror", "Mystery"],
                                rating: "8.5"
                            },
                            {
                                title: "Avatar: Fire and Ash",
                                year: "2026",
                                trailerUrl: "https://www.youtube.com/watch?v=d9My665987w", // Avatar 2 as placeholder
                                genres: ["Sci-Fi", "Action"],
                                rating: "9.0"
                            },
                            {
                                title: "The Batman Part II",
                                year: "2026",
                                trailerUrl: "https://www.youtube.com/watch?v=mqqft2x_Aa4", // The Batman
                                genres: ["Action", "Crime"],
                                rating: "8.8"
                            },
                            {
                                title: "Shrek 5",
                                year: "2026",
                                trailerUrl: "https://www.youtube.com/watch?v=CwXOrWvPBPk", // Shrek placeholder
                                genres: ["Animation", "Comedy"],
                                rating: "8.0"
                            },
                            {
                                title: "Toy Story 5",
                                year: "2026",
                                trailerUrl: "https://www.youtube.com/watch?v=wmiIUN-7qhE", // Toy Story 4
                                genres: ["Animation", "Family"],
                                rating: "8.2"
                            }
                        ];

                        // Strict/Loose match on fallback
                        const normalize = (str) => str.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim();
                        const targetSlug = normalize(title);
                        movie = fallbackMovies.find(m => {
                            const mTitle = normalize(m.title);
                            return mTitle.includes(targetSlug) || targetSlug.includes(mTitle);
                        });
                    }

                    if (movie) {
                        console.log(`[MovieShows] Found movie: "${movie.title}"`);
                        showToast(`Playing: ${movie.title}`);
                        addMovieToFeed(movie, true);
                    } else {
                        console.warn(`[MovieShows] Movie "${title}" not found in DB or Fallback.`);
                        showToast(`Could not find "${title}"`, true);
                    }
                }, true); // Capture phase
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    // Simple Toast Notification
    function showToast(message, isError = false) {
        let toast = document.getElementById('movieshows-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'movieshows-toast';
            toast.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0,0,0,0.85);
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
                z-index: 10000;
                pointer-events: none;
                transition: opacity 0.3s;
                opacity: 0;
                box-shadow: 0 4px 12px rgba(0,0,0,0.5);
                text-align: center;
                backdrop-filter: blur(4px);
                border: 1px solid rgba(255,255,255,0.1);
            `;
            document.body.appendChild(toast);
        }

        toast.textContent = message;
        toast.style.color = isError ? '#f87171' : '#4ade80'; // Red or Green
        toast.style.opacity = '1';

        // Hide previous timeout
        if (toast.timeout) clearTimeout(toast.timeout);
        toast.timeout = setTimeout(() => {
            toast.style.opacity = '0';
        }, 2000);
    }

    function injectStyles() {
        if (document.getElementById("movieshows-custom-styles")) return;

        const style = document.createElement("style");
        style.id = "movieshows-custom-styles";
        style.textContent = `
      /* HAMBURGER/TOP-LEFT NAV FIX - Don't block Next.js nav buttons */
      /* Create a safe zone in top-left corner for hamburger and nav buttons */
      button[aria-label="Open Quick Nav"],
      button[title="Quick Navigation"],
      .fixed.top-4.left-4,
      [class*="fixed"][class*="top-4"][class*="left-4"] {
          z-index: 99999 !important;
          pointer-events: auto !important;
          position: relative !important;
      }
      
      /* CRITICAL: Create a click-through zone at the top of the page */
      /* All overlays in the top 100px should not intercept clicks */
      .snap-center .absolute.inset-0,
      .snap-center > .absolute.inset-0,
      div[class*="absolute"][class*="inset-0"]:not(iframe):not([class*="bottom"]) {
          pointer-events: none !important;
      }
      
      /* Top navigation bar - ensure nothing blocks it */
      body > div > div.fixed.top-4,
      body > div > button.fixed.top-4,
      div.fixed.top-0,
      nav.fixed.top-0,
      header.fixed.top-0,
      .fixed[class*="top-4"][class*="left-4"] {
          z-index: 99999 !important;
          pointer-events: auto !important;
      }
      
      /* But allow clicks on the iframe itself and bottom UI elements */
      .snap-center iframe,
      .snap-center .absolute.bottom-4,
      .snap-center .absolute.right-4,
      .snap-center [class*="bottom-4"],
      .snap-center [class*="right-4"],
      iframe.lazy-iframe {
          pointer-events: auto !important;
      }
      
      /* Player size control */
      #player-size-control {
        display: flex;
        align-items: center;
        gap: 6px;
        background: rgba(0, 0, 0, 0.9);
        padding: 8px 16px;
        border-radius: 12px;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        font-family: sans-serif;
        flex-wrap: wrap;
        justify-content: center;
        max-width: 90vw;
      }
      
      #layout-control button, #player-size-control button {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #aaa;
        padding: 4px 10px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 11px;
        font-weight: bold;
        transition: all 0.2s;
        flex: 1;
        text-align: center;
      }

      #layout-control button:hover, #player-size-control button:hover {
        background: rgba(255, 255, 255, 0.2);
        color: white;
      }

      #layout-control button.active, #player-size-control button.active {
        background: #22c55e;
        border-color: #22c55e;
        color: black;
      }

      /* Fix title and description visibility */
      h2.text-2xl {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        font-size: 3.5rem !important;
        line-height: 1.1 !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.9);
        margin-bottom: 0.5rem !important;
        transition: transform 0.3s ease;
        pointer-events: auto; /* Allow text selection/interaction */
      }
      
      p.text-sm {
        font-size: 1.25rem !important;
        line-height: 1.5 !important;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.9);
        max-width: 80% !important;
        transition: opacity 0.3s ease;
        pointer-events: auto;
      }
      
      /* Text Container Interaction Fix */
      .snap-center > div.absolute.bottom-4.left-4 {
          pointer-events: auto; /* Allow interaction so wheel events bubble to document */
          transform: translate(var(--text-offset-x), var(--text-offset-y)) !important; 
          transition: transform 0.1s ease-out, bottom 0.3s ease;
      }

      /* Detail Modes */
      body.detail-title p.text-sm {
        display: none !important;
      }
      body.detail-title .flex.flex-wrap {
        display: none !important;
      }

      /* Ensure the bottom info section is fully visible */
      .snap-center [class*="bottom-4"][class*="left-4"] {
        left: 16px !important;
      }
      
      /* AUTOMATIC POSITION ADJUSTMENT FOR SIZES (Default "Def" position) */
      .player-medium .snap-center > div.absolute.bottom-4.left-4 {
          bottom: 15vh !important;
      }
      .player-large .snap-center > div.absolute.bottom-4.left-4 {
          bottom: 22vh !important;
      }
      
      /* Make sure text isn't clipped */
      [class*="line-clamp"] {
        -webkit-line-clamp: 4 !important;
        line-clamp: 4 !important;
        display: -webkit-box !important;
        overflow: visible !important;
      }

      /* Layout Modes */
      
      /* Raised: Lift the ENTIRE text container up explicitly */
      /* Redefine Raised to be a specific high position */
      .text-layout-raised .snap-center > div.absolute.bottom-4.left-4 {
         bottom: 35vh !important; /* Definitive high position */
         transform: none !important;
         transition: bottom 0.3s ease;
      }

      /* Center: Centered in screen - heavily modified to look like a title card */
      .text-layout-center .snap-center > div.absolute.bottom-4.left-4 {
         bottom: 50% !important;
         top: auto !important;
         /* Include offsets in calculation: x, y */
         transform: translate(var(--text-offset-x), calc(50% + var(--text-offset-y))) !important;
         display: flex;
         flex-direction: column;
         align-items: center;
         text-align: center;
         width: 100%;
         left: 0 !important;
         right: 0 !important;
         background: transparent !important;
         /* pointer-events: auto by default now */
      }
      .text-layout-center h2.text-2xl {
         font-size: 5rem !important;
         text-align: center;
         text-shadow: 0 4px 8px rgba(0,0,0,0.8);
      }
      /* Hide description/badges in center mode, but keep title */
      .text-layout-center p.text-sm,
      .text-layout-center .flex.flex-wrap,
      .text-layout-center .flex.items-center.gap-2 { 
         display: none !important;
      }

      /* Player size CSS classes - FIXED to fill horizontally */
      .player-small iframe[src*="youtube"], .player-small iframe.lazy-iframe { 
        width: 100vw !important; 
        height: 40vh !important; 
        max-height: 40vh !important;
        object-fit: cover !important;
      }
      .player-medium iframe[src*="youtube"], .player-medium iframe.lazy-iframe { 
        width: 100vw !important; 
        height: 60vh !important; 
        max-height: 60vh !important;
        object-fit: cover !important;
      }
      .player-large iframe[src*="youtube"], .player-large iframe.lazy-iframe { 
        width: 100vw !important; 
        height: 85vh !important; 
        max-height: 85vh !important;
        object-fit: cover !important;
      }
      .player-full iframe[src*="youtube"], .player-full iframe.lazy-iframe { 
        width: 100vw !important; 
        height: 100vh !important; 
        max-height: 100vh !important;
        object-fit: cover !important;
      }
      
      /* Ensure iframe container fills width */
      .snap-center .absolute.inset-0 {
        width: 100vw !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
      }
      
      /* Hide movie info when toggled */
      body.hide-movie-info .snap-center > div.absolute.bottom-4.left-4,
      body.hide-movie-info .snap-center [class*="bottom-4"][class*="left-4"] {
        opacity: 0 !important;
        pointer-events: none !important;
        transition: opacity 0.3s ease !important;
      }
      
      /* Hide right action panel when toggled */
      body.hide-action-panel .snap-center .absolute.right-4,
      body.hide-action-panel .snap-center [class*="right-4"][class*="bottom-"] {
        opacity: 0 !important;
        pointer-events: none !important;
        transition: opacity 0.3s ease !important;
      }
      
      /* Action panel toggle button */
      #action-panel-toggle {
        position: fixed;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        z-index: 10000;
        background: rgba(0, 0, 0, 0.7);
        border: 1px solid rgba(255,255,255,0.3);
        color: white;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        cursor: pointer;
        font-size: 16px;
        transition: all 0.2s;
      }
      #action-panel-toggle:hover {
        background: rgba(34, 197, 94, 0.8);
      }
      
      /* Info toggle button */
      #info-toggle {
        position: fixed;
        left: 10px;
        bottom: 80px;
        z-index: 10000;
        background: rgba(0, 0, 0, 0.7);
        border: 1px solid rgba(255,255,255,0.3);
        color: white;
        padding: 8px 12px;
        border-radius: 20px;
        cursor: pointer;
        font-size: 12px;
        transition: all 0.2s;
      }
      #info-toggle:hover {
        background: rgba(34, 197, 94, 0.8);
      }
    `;
        document.head.appendChild(style);

        // Also apply z-index fix immediately
        fixCarouselZIndex();
        setInterval(fixCarouselZIndex, 2000); // Polling checks
    }

    // ========== DATA & INFINITE SCROLL ==========

    let allMoviesData = [];

    function transformDbMovie(m) {
        return {
            title: m.title || '',
            type: m.type || 'movie',
            year: String(m.release_year || m.year || '2026'),
            rating: String(m.imdb_rating || m.rating || ''),
            genres: m.genres || (m.genre ? m.genre.split(',').map(function(g){ return g.trim(); }).filter(Boolean) : []),
            source: m.source || 'In Theatres',
            trailerUrl: m.trailerUrl || (m.trailer_id ? 'https://www.youtube.com/watch?v=' + m.trailer_id : ''),
            posterUrl: m.posterUrl || m.thumbnail || '',
            description: m.description || '',
            nowPlaying: m.nowPlaying || [],
            imdb_id: m.imdb_id || '',
            tmdb_id: m.tmdb_id || '',
            runtime: m.runtime || ''
        };
    }

    async function loadMoviesData() {
        if (allMoviesData.length > 0) return;

        // Try database API first, fall back to static JSON
        var sources = [
            { url: 'api/get-movies.php', name: 'Database API', needsTransform: true },
            { url: 'movies-database.json?v=' + new Date().getTime(), name: 'Static JSON', needsTransform: false }
        ];

        for (var i = 0; i < sources.length; i++) {
            var src = sources[i];
            try {
                console.log('[MovieShows] Attempting to load from: ' + src.name + ' (' + src.url + ')');
                var res = await fetch(src.url);

                if (res.ok) {
                    var data = await res.json();
                    var items = data.items || data.movies || data;

                    if (Array.isArray(items) && items.length > 0) {
                        if (src.needsTransform) {
                            items = items.map(transformDbMovie);
                        }
                        allMoviesData = items;
                        window.allMoviesData = items;
                        console.log('[MovieShows] SUCCESS: Loaded ' + items.length + ' items from ' + src.name + '. Data exposed to window.allMoviesData');

                        setTimeout(function(){ updateCategoryButtons(); }, 100);
                        ensureMinimumCount(20);
                        updateUpNextCount();
                        checkInfiniteScroll();
                        return;
                    } else {
                        console.warn('[MovieShows] ' + src.name + ' returned empty or invalid data, trying next source...');
                    }
                } else {
                    console.warn('[MovieShows] ' + src.name + ' HTTP ' + res.status + ', trying next source...');
                }
            } catch (e) {
                console.warn('[MovieShows] ' + src.name + ' failed: ' + e.message + ', trying next source...');
            }
        }

        console.error('[MovieShows] CRITICAL: All data sources failed');
    }

    function ensureMinimumCount(min) {
        if (videoSlides.length < min && allMoviesData.length > 0) {
            const needed = min - videoSlides.length;
            console.log(`[MovieShows] Pre-filling feed with ${needed} more shows...`);

            // Get current titles
            const existingTitles = videoSlides.map(s => s.querySelector('h2')?.textContent || "");

            // Filter candidates
            let candidates = allMoviesData.filter(m => !existingTitles.includes(m.title));

            // If we ran out of unique content, allow duplicates (but shuffle)
            if (candidates.length < needed) {
                console.log("[MovieShows] Running low on unique content, recycling...");
                candidates = [...allMoviesData].sort(() => 0.5 - Math.random());
            }

            const toAdd = candidates
                .sort(() => 0.5 - Math.random())
                .slice(0, needed);

            toAdd.forEach(m => addMovieToFeed(m, false));
        }
    }

    function getYouTubeEmbedUrl(url, forceInitialMute = true) {
        if (!url) return "";
        let videoId = "";
        try {
            if (url.includes("v=")) {
                videoId = url.split("v=")[1].split("&")[0];
            } else if (url.includes("youtu.be/")) {
                videoId = url.split("youtu.be/")[1].split("?")[0];
            } else if (url.includes("embed/")) {
                return url;
            }
        } catch (e) { return url; }

        if (videoId) {
            // For initial load, always mute=1 for autoplay compliance
            // After user interaction (unmute button), we can use mute=0
            const muteValue = forceInitialMute ? 1 : getMuteParam();
            // IMPORTANT: No loop=1 - we want video to END so auto-next can advance to next slide
            return `https://www.youtube.com/embed/${videoId}?autoplay=1&mute=${muteValue}&controls=1&playsinline=1&modestbranding=1&rel=0&enablejsapi=1`;
        }
        return url;
    }

    function createSlide(movie, loadImmediately = false) {
        const slide = document.createElement("div");
        slide.className = "h-full w-full snap-center";
        slide.dataset.movieTitle = movie.title || "Unknown"; // Store movie title for sync checking

        const embedUrl = getYouTubeEmbedUrl(movie.trailerUrl);
        const genresHtml = (movie.genres || []).map(g =>
            `<span class="text-xs bg-white/10 backdrop-blur-sm px-2 py-1 rounded-full text-gray-100 border border-white/10">${g}</span>`
        ).join("");

        const rating = movie.rating ? `IMDb ${movie.rating}` : "TBD";
        const year = movie.year || "2026";

        // If loadImmediately is true, set src directly; otherwise use lazy loading
        const iframeSrc = loadImmediately ? embedUrl : "";
        
        slide.innerHTML = `
            <div class="relative w-full h-full flex items-center justify-center overflow-hidden snap-center bg-transparent">
                <div class="absolute inset-0 w-full h-full bg-black">
                     <iframe 
                        data-src="${embedUrl}" 
                        data-movie-title="${movie.title || 'Unknown'}"
                        src="${iframeSrc}" 
                        class="w-full h-full object-cover lazy-iframe" 
                        allow="autoplay; encrypted-media; picture-in-picture" 
                        allowfullscreen 
                        style="pointer-events: auto;"
                        frameborder="0">
                     </iframe>
                </div>
                <div class="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/80 pointer-events-none z-20"></div>
                
                <!-- Right Action Buttons (Simplified) -->
                <div class="absolute right-4 bottom-20 flex flex-col items-center gap-4 z-30 pointer-events-auto">
                    <button class="flex flex-col items-center gap-1 group">
                         <div class="p-3 rounded-full bg-black/40 backdrop-blur-sm transition-all duration-200 group-hover:bg-black/60">
                              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-heart w-8 h-8 text-white"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path></svg>
                         </div>
                        <span class="text-xs font-semibold drop-shadow-md text-white">Like</span>
                    </button>
                    <button class="flex flex-col items-center gap-1 group">
                        <div class="p-3 rounded-full bg-black/40 backdrop-blur-sm transition-all duration-200 group-hover:bg-black/60">
                             <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-plus w-8 h-8 text-white"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                        </div>
                        <span class="text-xs font-semibold drop-shadow-md text-white">List</span>
                    </button>
                    <button class="flex flex-col items-center gap-1 group">
                        <div class="p-3 rounded-full bg-black/40 backdrop-blur-sm transition-all duration-200 group-hover:bg-black/60">
                             <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-share2 w-8 h-8 text-white"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"></line><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"></line></svg>
                        </div>
                        <span class="text-xs font-semibold drop-shadow-md text-white">Share</span>
                    </button>
                </div>

                <!-- Bottom Info -->
                <div class="absolute bottom-4 left-4 right-16 z-30 flex flex-col gap-2 pointer-events-none">
                    <div class="flex items-center gap-2">
                         <div class="bg-yellow-500 text-black text-[10px] font-black px-2 py-0.5 rounded flex items-center gap-1 cursor-pointer pointer-events-auto hover:bg-yellow-400">${rating}</div>
                         <div class="bg-white/20 backdrop-blur-md text-white text-[10px] font-bold px-2 py-0.5 rounded">${year}</div>
                         <div class="bg-blue-600 text-white text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">${movie.source || "In Theatres"}</div>
                    </div>
                    <h2 class="text-2xl font-bold text-white drop-shadow-lg leading-tight pointer-events-auto w-full">${movie.title}</h2>
                    <div class="relative group/desc pointer-events-auto max-w-[90%]">
                        <p class="text-sm text-gray-200 line-clamp-3 drop-shadow-sm transition-all duration-300 w-full">${movie.description || ""}</p>
                    </div>
                    <div class="flex flex-wrap gap-2 mt-2">
                        ${genresHtml}
                    </div>
                </div>
            </div>
        `;
        return slide;
    }

    function addMovieToFeed(movie, scrollAfter = false, loadImmediately = false) {
        if (!scrollContainer) {
            console.error("[MovieShows] addMovieToFeed failed: No scrollContainer.");
            scrollContainer = findScrollContainer(); // Try again
            if (!scrollContainer) return;
        }

        // Verbose logging removed - see summary log in populateInitialVideos

        // Check for duplicates in the entire feed (unless forced scroll which means user clicked)
        if (!scrollAfter) {
            const existingTitles = new Set();
            videoSlides.forEach(slide => {
                const h2 = slide.querySelector('h2');
                if (h2) existingTitles.add(h2.textContent);
            });
            
            if (existingTitles.has(movie.title)) {
                console.log(`[MovieShows] Skipped adding duplicate: ${movie.title}`);
                return;
            }
        }

        const slide = createSlide(movie, loadImmediately);
        scrollContainer.appendChild(slide);

        // Refresh videoSlides list
        videoSlides = findVideoSlides();

        updateUpNextCount();

        if (scrollAfter) {
            // Force scroll
            setTimeout(() => {
                console.log(`[MovieShows] Scattering to index ${videoSlides.length - 1}`);
                scrollToSlide(videoSlides.length - 1);

                // Force player size application on new slide
                const size = localStorage.getItem("movieshows-player-size") || "large";
                applyPlayerSize(size);

                // FORCE PLAY with sound: user explicitly chose this video
                const iframe = slide.querySelector('iframe');
                if (iframe && iframe.dataset.src) {
                    console.log("[MovieShows] Force playing video (user selection)...");
                    // Stop all other videos first
                    forceStopAllVideos();
                    // Play with sound - user explicitly selected this
                    isMuted = false;
                    localStorage.setItem("movieshows-muted", "false");
                    const title = movie.title || 'Unknown';
                    currentlyPlayingTitle = title;
                    currentlyPlayingIframe = iframe;
                    playVideo(iframe, title);
                    updateMuteControl();
                    removeCenterMuteOverlay();
                    console.log("[MovieShows] User-selected video playing with sound");
                }
            }, 100);
        }
    }

    function injectQueueCloseButton(headerEl) {
        if (headerEl.querySelector('.custom-queue-close')) return;

        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '✕';
        closeBtn.className = 'custom-queue-close';
        closeBtn.title = "Close Queue";
        closeBtn.style.cssText = "margin-left: auto; background: #ef4444; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: bold; border: none; cursor: pointer; pointer-events: auto; z-index: 9999;";

        closeBtn.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log("[MovieShows] Closing queue...");

            // 1. Try finding the React close button (usually 'x' SVG)
            const panel = headerEl.closest('div.fixed') || headerEl.parentElement.parentElement;
            if (panel) {
                const buttons = panel.querySelectorAll('button');
                const nativeClose = Array.from(buttons).find(b => b.textContent.includes('✕') || b.querySelector('svg') || b.getAttribute('aria-label') === 'Close menu');
                if (nativeClose && nativeClose !== closeBtn) {
                    nativeClose.click();
                    return;
                }
                // If no native close, just hide the panel
                panel.style.display = 'none';
            }
        };

        headerEl.style.display = 'flex';
        headerEl.style.alignItems = 'center';
        headerEl.style.justifyContent = 'space-between';

        // Ensure the header text is wrapped if needed, but usually we can just append
        headerEl.appendChild(closeBtn);
    }

    function updateUpNextCount() {
        // Update the green button
        const spans = Array.from(document.querySelectorAll('span'));
        const upNextSpan = spans.find(s => s.textContent.includes("Up Next"));
        if (upNextSpan) {
            const count = Math.max(20, allMoviesData.length - videoSlides.length + 20);
            upNextSpan.textContent = `${count}+ Up Next - Infinite`;
            if (upNextSpan.parentElement) upNextSpan.parentElement.style.background = "#22c55e";
        }

        // Try to update the "Queue (10)" text in the side panel header if visible
        // And ensure it has a close button
        const headings = Array.from(document.querySelectorAll('h2, div'));
        const queueHeader = headings.find(el =>
            el.textContent && /Queue\s*\((\d+|Infinite)\)/.test(el.textContent) && (el.tagName === 'H2' || el.classList.contains('text-xl'))
        );

        if (queueHeader) {
            if (!queueHeader.textContent.includes('Infinite')) {
                queueHeader.innerHTML = queueHeader.innerHTML.replace(/\(\d+\)/, '(Infinite)');
            }
            injectQueueCloseButton(queueHeader);
        }
    }

    let processingInfiniteScroll = false;

    function checkInfiniteScroll() {
        if (!scrollContainer || allMoviesData.length === 0) return;

        // Threshold: 3 screens from bottom
        const scrollBottom = scrollContainer.scrollTop + scrollContainer.clientHeight;
        const totalHeight = scrollContainer.scrollHeight;
        const distance = totalHeight - scrollBottom;

        // If we are close to the end (within 3 slides height)
        if (distance < (scrollContainer.clientHeight * 3)) {
            // Rate limit to avoid spamming
            if (processingInfiniteScroll) return;
            processingInfiniteScroll = true;
            setTimeout(() => processingInfiniteScroll = false, 1000);

            console.log("[MovieShows] Infinite Scroll Triggered!");
            const recentTitles = videoSlides.slice(-15).map(s => s.querySelector('h2')?.textContent).filter(Boolean);
            
            // Use filtered movies based on current filter
            const filteredMovies = getFilteredMovies();
            const candidates = filteredMovies.filter(m => !recentTitles.includes(m.title));

            if (candidates.length > 0) {
                const toAdd = candidates.sort(() => 0.5 - Math.random()).slice(0, 3);
                toAdd.forEach(m => addMovieToFeed(m));
            } else if (filteredMovies.length > 0) {
                // Recycle from filtered list
                const recycled = filteredMovies.sort(() => 0.5 - Math.random()).slice(0, 3);
                recycled.forEach(m => addMovieToFeed(m));
            }
        }
    }

    // ========== SCROLL NAVIGATION ==========

    function findScrollContainer() {
        const containers = document.querySelectorAll(
            '[class*="overflow-y-scroll"]',
        );
        for (const container of containers) {
            if (container.className.includes("snap-y")) {
                return container;
            }
        }
        const snapCenterEl = document.querySelector('[class*="snap-center"]');
        if (snapCenterEl && snapCenterEl.parentElement) {
            return snapCenterEl.parentElement;
        }
        return null;
    }

    function findVideoSlides() {
        if (!scrollContainer) return [];
        // Use direct child selector to avoid matching nested snap-center elements
        // The outer slide has class "h-full w-full snap-center"
        // The inner wrapper has "relative ... snap-center bg-transparent"
        // We only want the outer ones (direct children with data-movie-title)
        const slides = Array.from(
            scrollContainer.querySelectorAll(':scope > .snap-center[data-movie-title]'),
        );
        // Fallback to the old selector if no results (for compatibility)
        if (slides.length === 0) {
            return Array.from(
                scrollContainer.querySelectorAll(':scope > [class*="snap-center"]'),
            );
        }
        return slides;
    }

    function clickQueuePlayButton() {
        const allButtons = document.querySelectorAll("button");
        for (const btn of allButtons) {
            if (btn.textContent?.includes("Play Queue")) {
                btn.click();
                return true;
            }
        }

        const greenPlayBtn = document.querySelector('button[class*="bg-green"]');
        if (greenPlayBtn) {
            greenPlayBtn.click();
            return true;
        }

        return false;
    }

    function getCurrentVisibleIndex() {
        if (!scrollContainer || videoSlides.length === 0) return 0;

        const slideHeight = scrollContainer.clientHeight;
        if (slideHeight <= 0) return 0;

        return Math.max(
            0,
            Math.min(
                videoSlides.length - 1,
                Math.round(scrollContainer.scrollTop / slideHeight),
            ),
        );
    }

    function scrollToSlide(index) {
        if (!scrollContainer || index < 0 || index >= videoSlides.length) return;

        console.log(`[MovieShows] scrollToSlide: index=${index}, total slides=${videoSlides.length}`);
        
        const slideHeight = scrollContainer.clientHeight;
        const targetTop = index * slideHeight;
        
        console.log(`[MovieShows] scrollToSlide: slideHeight=${slideHeight}, targetTop=${targetTop}`);
        
        scrollContainer.scrollTo({
            top: targetTop,
            behavior: "smooth",
        });

        currentIndex = index;
        
        // Force play the specific slide after scroll animation completes
        setTimeout(() => {
            // Directly play the target slide instead of using visibility detection
            playSlideAtIndex(index);
        }, 600);
    }
    
    // New function to directly play a specific slide by index
    function playSlideAtIndex(index) {
        if (index < 0 || index >= videoSlides.length) return;
        
        console.log(`[MovieShows] playSlideAtIndex: ${index}`);
        
        // Stop all other videos first
        const allYouTubeIframes = document.querySelectorAll('iframe[src*="youtube"], iframe[data-src*="youtube"]');
        allYouTubeIframes.forEach(iframe => {
            const src = iframe.getAttribute('src');
            if (src && src !== '') {
                iframe.setAttribute('src', '');
            }
        });
        
        // Reset playing state
        currentlyPlayingIframe = null;
        currentlyPlayingTitle = null;
        
        // Get the target slide and its iframe
        const targetSlide = videoSlides[index];
        if (!targetSlide) {
            console.log(`[MovieShows] playSlideAtIndex: No slide at index ${index}`);
            return;
        }
        
        const iframe = targetSlide.querySelector('iframe[data-src]');
        if (!iframe) {
            console.log(`[MovieShows] playSlideAtIndex: No iframe with data-src in slide ${index}`);
            return;
        }
        
        const title = targetSlide.querySelector('h2')?.textContent || 'Unknown';
        const dataSrc = iframe.getAttribute('data-src');
        
        if (dataSrc) {
            console.log(`[MovieShows] playSlideAtIndex: Playing "${title}" at index ${index}`);
            iframe.src = dataSrc;
            currentlyPlayingIframe = iframe;
            currentlyPlayingTitle = title;
            currentIndex = index;
        }
    }

    function isQueuePanelOpen() {
        return queuePanel && (queuePanel.style.right === '0' || queuePanel.style.right === '0px');
    }
    
    // Debounce timer for scroll end detection
    let scrollEndTimer = null;
    let lastScrollTime = 0;
    
    function handleScroll() {
        if (isScrolling) return;
        
        lastScrollTime = Date.now();

        const newIndex = getCurrentVisibleIndex();
        if (newIndex !== currentIndex) {
            currentIndex = newIndex;
            checkInfiniteScroll(); // Check if we need more content
            // Switch to the new video - stop all first to prevent multiple playing
            forceStopAllVideos();
            setTimeout(() => forcePlayVisibleVideos(), 50);
        }
        
        // Always update queue panel on scroll (debounced)
        if (isQueuePanelOpen()) {
            // Clear previous timer
            if (scrollEndTimer) clearTimeout(scrollEndTimer);
            // Set new timer to update after scrolling stops
            scrollEndTimer = setTimeout(() => {
                console.log('[MovieShows] Scroll ended - syncing queue');
                videoSlides = findVideoSlides();
                currentIndex = getCurrentVisibleIndex();
                forceStopAllVideos();
                setTimeout(() => {
                    forcePlayVisibleVideos();
                    updateQueuePanel();
                }, 100);
            }, 150); // 150ms after scroll stops
        }
    }

    function handleWheel(e) {
        const target = e.target;
        
        // User is manually scrolling - stop auto-scroll timer (will restart on next video)
        stopAutoScrollTimer();

        if (
            target.closest("#player-size-control") ||
            target.closest('.overflow-y-auto:not([class*="snap-y"])') ||
            target.closest('[class*="Queue"]') ||
            target.closest('[class*="fixed"][class*="right"]') ||
            target.closest("select")
        ) {
            return;
        }

        if (!scrollContainer || isScrolling) {
            if (isScrolling) e.preventDefault();
            return;
        }

        if (Math.abs(e.deltaY) < 20) return;

        e.preventDefault();

        const direction = e.deltaY > 0 ? 1 : -1;
        const newIndex = Math.max(
            0,
            Math.min(videoSlides.length - 1, currentIndex + direction),
        );

        if (newIndex !== currentIndex) {
            isScrolling = true;
            scrollToSlide(newIndex);

            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                isScrolling = false;
                currentIndex = getCurrentVisibleIndex();
                // Re-apply player size after scroll
                const size = localStorage.getItem("movieshows-player-size") || "large";
                setTimeout(() => applyPlayerSize(size), 100);
            }, SCROLL_COOLDOWN);
        }
    }

    function handleKeydown(e) {
        if (
            e.target.tagName === "INPUT" ||
            e.target.tagName === "TEXTAREA" ||
            e.target.tagName === "SELECT"
        ) {
            return;
        }

        if (isScrolling) return;

        let direction = 0;
        switch (e.key) {
            case "ArrowDown":
            case "j":
            case "J":
                direction = 1;
                break;
            case "ArrowUp":
            case "k":
            case "K":
                direction = -1;
                break;
            case "Home":
                if (videoSlides.length > 0) {
                    e.preventDefault();
                    isScrolling = true;
                    scrollToSlide(0);
                    clearTimeout(scrollTimeout);
                    scrollTimeout = setTimeout(() => {
                        isScrolling = false;
                    }, SCROLL_COOLDOWN);
                }
                return;
            case "End":
                if (videoSlides.length > 0) {
                    e.preventDefault();
                    isScrolling = true;
                    scrollToSlide(videoSlides.length - 1);
                    clearTimeout(scrollTimeout);
                    scrollTimeout = setTimeout(() => {
                        isScrolling = false;
                    }, SCROLL_COOLDOWN);
                }
                return;
            case "1":
                setPlayerSize("small");
                localStorage.setItem("movieshows-player-size", "small");
                return;
            case "2":
                setPlayerSize("medium");
                localStorage.setItem("movieshows-player-size", "medium");
                return;
            case "3":
                setPlayerSize("large");
                localStorage.setItem("movieshows-player-size", "large");
                return;
            case "4":
                setPlayerSize("full");
                localStorage.setItem("movieshows-player-size", "full");
                return;
            case "m":
            case "M":
                toggleMute();
                e.preventDefault();
                return;
        }

        if (direction === 0) return;

        e.preventDefault();

        const newIndex = Math.max(
            0,
            Math.min(videoSlides.length - 1, currentIndex + direction),
        );

        if (newIndex !== currentIndex) {
            isScrolling = true;
            scrollToSlide(newIndex);

            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                isScrolling = false;
                currentIndex = getCurrentVisibleIndex();
            }, SCROLL_COOLDOWN);
        }
    }

    let touchStartY = 0;
    let touchStartTime = 0;

    function handleTouchStart(e) {
        touchStartY = e.touches[0].clientY;
        touchStartTime = Date.now();
    }

    function handleTouchEnd(e) {
        if (isScrolling) return;

        const touchEndY = e.changedTouches[0].clientY;
        const deltaY = touchStartY - touchEndY;
        const duration = Date.now() - touchStartTime;

        if (duration < 300 && Math.abs(deltaY) > 50) {
            const direction = deltaY > 0 ? 1 : -1;
            const newIndex = Math.max(
                0,
                Math.min(videoSlides.length - 1, currentIndex + direction),
            );

            if (newIndex !== currentIndex) {
                isScrolling = true;
                scrollToSlide(newIndex);

                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    isScrolling = false;
                    currentIndex = getCurrentVisibleIndex();
                }, SCROLL_COOLDOWN);
            }
        }
    }

    // Watch for new iframes being added and apply size
    function setupIframeObserver() {
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                if (mutation.addedNodes.length) {
                    const size =
                        localStorage.getItem("movieshows-player-size") || "large";
                    setTimeout(() => applyPlayerSize(size), 200);

                    // Also observe new iframes for playback control
                    const newIframes = Array.from(mutation.addedNodes)
                        .flatMap(node => node.querySelectorAll ? Array.from(node.querySelectorAll('iframe.lazy-iframe')) : []);

                    if (videoObserver && newIframes.length > 0) {
                        newIframes.forEach(iframe => videoObserver.observe(iframe));
                    }
                    break;
                }
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    let videoObserver = null;
    let currentlyPlayingIframe = null;
    let currentlyPlayingTitle = null;
    
    function setupVideoObserver() {
        if (videoObserver) return;

        // Observer only PAUSES out-of-view videos
        // Playback is controlled by forcePlayVisibleVideos() based on currentIndex
        videoObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const iframe = entry.target;
                
                // Only pause if completely out of view
                if (!entry.isIntersecting && entry.intersectionRatio < 0.1) {
                    pauseVideo(iframe);
                }
            });
        }, {
            threshold: [0, 0.1, 0.5] 
        });

        // Observe existing
        document.querySelectorAll('iframe.lazy-iframe').forEach(iframe => {
            videoObserver.observe(iframe);
        });
    }
    
    function playVideo(iframe, expectedTitle = null) {
        if (!iframe) return;
        
        let dataSrc = iframe.getAttribute('data-src');
        if (!dataSrc) return;
        
        const movieTitle = iframe.getAttribute('data-movie-title') || 'Unknown';
        
        // Apply current mute state to the URL
        dataSrc = dataSrc.replace(/mute=\d/, `mute=${getMuteParam()}`);
        
        const currentSrc = iframe.getAttribute('src');
        
        // Only update if different (to avoid reloading)
        if (currentSrc !== dataSrc) {
            // First, pause any other playing video
            if (currentlyPlayingIframe && currentlyPlayingIframe !== iframe) {
                pauseVideo(currentlyPlayingIframe);
            }
            
            console.log(`[MovieShows] Playing: "${movieTitle}" (muted=${isMuted})`);
            iframe.setAttribute('src', dataSrc);
            currentlyPlayingIframe = iframe;
            currentlyPlayingTitle = movieTitle;
            
            // Reset video end tracking for new video
            currentVideoDuration = 0;
            currentVideoTime = 0;
            videoEndedWaitingForScroll = false;
            
            // Subscribe to YouTube events after iframe loads
            // Use setTimeout as backup since onload doesn't always fire reliably
            const subscribeAfterLoad = () => subscribeToYouTubeEvents(iframe);
            iframe.onload = subscribeAfterLoad;
            setTimeout(subscribeAfterLoad, 1000); // Backup
            
            // Verify sync if expected title provided
            if (expectedTitle && expectedTitle !== movieTitle) {
                console.warn(`[MovieShows] SYNC WARNING: Expected "${expectedTitle}" but playing "${movieTitle}"`);
            }
            
            // Start auto-scroll timer when video starts playing
            resetAutoScrollTimer();
        }
    }
    
    // Subscribe to YouTube iframe events
    function subscribeToYouTubeEvents(iframe) {
        if (!iframe) return;
        
        // Reset video tracking for new video
        currentVideoDuration = 0;
        currentVideoTime = 0;
        
        // Only try postMessage if iframe has YouTube src
        const src = iframe.getAttribute('src') || '';
        if (!src.includes('youtube.com')) {
            console.log('[MovieShows] Skipping event subscription - not a YouTube iframe');
            return;
        }
        
        // Wait a bit for the iframe to be fully loaded
        setTimeout(() => {
            if (!iframe.contentWindow) return;
            
            try {
                // Tell YouTube we want to listen for events
                const listenCommand = JSON.stringify({
                    event: 'listening',
                    id: 1,
                    channel: 'widget'
                });
                iframe.contentWindow.postMessage(listenCommand, '*'); // Use * to avoid origin mismatch
                
                console.log(`[MovieShows] Subscribed to YouTube events`);
            } catch (e) {
                // Silently fail - we'll still get infoDelivery messages
            }
        }, 100);
    }
    
    function pauseVideo(iframe) {
        if (!iframe) return;
        const src = iframe.getAttribute('src');
        if (src && src !== '') {
            const movieTitle = iframe.getAttribute('data-movie-title') || 'Unknown';
            console.log(`[MovieShows] Pausing: "${movieTitle}"`);
            iframe.setAttribute('src', '');
            if (currentlyPlayingIframe === iframe) {
                currentlyPlayingIframe = null;
                currentlyPlayingTitle = null;
            }
        }
    }
    
    // Force stop ALL videos - used to fix multiple videos playing
    function forceStopAllVideos() {
        console.log('[MovieShows] Force stopping ALL videos');
        const allIframes = document.querySelectorAll('iframe');
        let stoppedCount = 0;
        allIframes.forEach(iframe => {
            const src = iframe.getAttribute('src');
            if (src && src !== '' && src.includes('youtube')) {
                iframe.setAttribute('src', '');
                stoppedCount++;
            }
        });
        currentlyPlayingIframe = null;
        currentlyPlayingTitle = null;
        console.log(`[MovieShows] Stopped ${stoppedCount} videos`);
    }
    
    function getCurrentSlideTitle() {
        if (videoSlides.length === 0 || currentIndex < 0 || currentIndex >= videoSlides.length) {
            return null;
        }
        const currentSlide = videoSlides[currentIndex];
        return currentSlide?.dataset?.movieTitle || currentSlide?.querySelector('h2')?.textContent || null;
    }
    
    function verifySyncState() {
        const slideTitle = getCurrentSlideTitle();
        if (slideTitle && currentlyPlayingTitle && slideTitle !== currentlyPlayingTitle) {
            console.warn(`[MovieShows] DESYNC DETECTED: Slide shows "${slideTitle}" but playing "${currentlyPlayingTitle}". Fixing...`);
            forcePlayVisibleVideos();
            return false;
        }
        return true;
    }

    function clearPlaceholderSlides() {
        if (!scrollContainer) return;
        
        // Find slides that don't have real video content (no data-src on iframe)
        const slides = scrollContainer.querySelectorAll('[class*="snap-center"]');
        let removed = 0;
        
        slides.forEach(slide => {
            const iframe = slide.querySelector('iframe[data-src]');
            // If no iframe with data-src, it's a placeholder - remove it
            if (!iframe) {
                slide.remove();
                removed++;
            }
        });
        
        if (removed > 0) {
            console.log(`[MovieShows] Cleared ${removed} placeholder slides`);
        }
    }

    function getFilteredMovies() {
        // Filter movies based on current category
        let filtered = allMoviesData.filter(m => m.trailerUrl && m.trailerUrl.length > 10);
        
        if (currentFilter === 'movies') {
            filtered = filtered.filter(m => !m.type || m.type === 'movie' || m.type === 'Movie');
        } else if (currentFilter === 'tv') {
            filtered = filtered.filter(m => m.type === 'tv' || m.type === 'TV' || m.type === 'series' || m.type === 'Series');
        } else if (currentFilter === 'nowplaying') {
            filtered = filtered.filter(m => 
                m.source === 'Now Playing' || 
                m.source === 'In Theatres' || 
                m.source === 'In Theaters' ||
                m.nowPlaying === true ||
                (m.badges && m.badges.includes('IN THEATRES'))
            );
        }
        
        return filtered;
    }
    
    function repopulateFeedWithFilter() {
        if (!scrollContainer || allMoviesData.length === 0) {
            console.warn("[MovieShows] Cannot repopulate - no container or data");
            return;
        }
        
        console.log(`[MovieShows] Repopulating feed with filter: ${currentFilter}`);
        
        // Pause current video
        if (currentlyPlayingIframe) {
            pauseVideo(currentlyPlayingIframe);
        }
        
        // Clear existing slides
        const existingSlides = scrollContainer.querySelectorAll('.snap-center');
        existingSlides.forEach(slide => slide.remove());
        videoSlides = [];
        currentIndex = 0;
        
        // Get filtered movies
        const filteredMovies = getFilteredMovies();
        console.log(`[MovieShows] Found ${filteredMovies.length} ${currentFilter} items with trailers`);
        
        if (filteredMovies.length === 0) {
            showToast(`No ${currentFilter === 'nowplaying' ? 'now playing' : currentFilter} content with trailers`, true);
            // Fall back to showing all
            currentFilter = 'all';
            updateCategoryButtons();
            const allMovies = allMoviesData.filter(m => m.trailerUrl && m.trailerUrl.length > 10).slice(0, 10);
            allMovies.forEach((movie, index) => {
                addMovieToFeed(movie, false, index === 0);
            });
        } else {
            // Add filtered movies (up to 15 initially)
            const toAdd = filteredMovies.slice(0, 15);
            toAdd.forEach((movie, index) => {
                addMovieToFeed(movie, false, index === 0);
            });
        }
        
        // Refresh slide list
        videoSlides = findVideoSlides();
        
        // Scroll to first and play
        setTimeout(() => {
            scrollToSlide(0);
            forcePlayVisibleVideos();
            // Always update queue panel after filter change
            updateQueuePanel();
        }, 300);
    }
    
    function populateInitialVideos() {
        if (allMoviesData.length === 0) {
            console.log("[MovieShows] Waiting for movie data...");
            setTimeout(populateInitialVideos, 500);
            return;
        }

        // Clear any placeholder slides first
        clearPlaceholderSlides();
        
        // Reset videoSlides after clearing
        videoSlides = [];

        // Check if we already have video slides with real content
        const existingSlides = scrollContainer?.querySelectorAll('iframe[data-src]') || [];
        if (existingSlides.length > 0) {
            console.log(`[MovieShows] Already have ${existingSlides.length} video slides`);
            videoSlides = findVideoSlides();
            return;
        }

        console.log("[MovieShows] Populating initial videos from database...");

        // Use filtered movies based on current filter
        const filteredMovies = getFilteredMovies();
        console.log(`[MovieShows] Found ${filteredMovies.length} movies with valid trailer URLs (filter: ${currentFilter})`);

        if (filteredMovies.length === 0) {
            console.error("[MovieShows] No movies with trailer URLs found!");
            return;
        }

        // Build initial list (up to 10)
        const initialMovies = filteredMovies.slice(0, 10);

        // Add movies to feed - load first one immediately, others lazy
        initialMovies.forEach((movie, index) => {
            addMovieToFeed(movie, false, index === 0); // loadImmediately for first one
        });

        // Refresh slide list AFTER adding all movies
        videoSlides = findVideoSlides();
        console.log(`[MovieShows] Added ${initialMovies.length} initial videos: ${initialMovies.slice(0, 3).map(m => m.title).join(', ')}...`);

        // Scroll to first slide and FORCE play video
        if (videoSlides.length > 0) {
            setTimeout(() => {
                scrollToSlide(0);
                // Force all visible iframes to load
                forcePlayVisibleVideos();
            }, 300);
        }
    }
    
    function forcePlayVisibleVideos() {
        // CRITICAL: Stop ALL YouTube iframes first (not just data-src ones)
        const allYouTubeIframes = document.querySelectorAll('iframe[src*="youtube"], iframe[data-src*="youtube"]');
        console.log(`[MovieShows] forcePlayVisibleVideos - Stopping ${allYouTubeIframes.length} YouTube iframes first`);
        
        allYouTubeIframes.forEach(iframe => {
            const src = iframe.getAttribute('src');
            if (src && src !== '') {
                iframe.setAttribute('src', '');
            }
        });
        
        // Reset playing state
        currentlyPlayingIframe = null;
        currentlyPlayingTitle = null;
        
        // Find iframes with data-src (lazy loaded)
        const lazyIframes = document.querySelectorAll('iframe[data-src]');
        console.log(`[MovieShows] forcePlayVisibleVideos - Found ${lazyIframes.length} lazy iframes`);
        
        if (lazyIframes.length === 0) {
            console.log("[MovieShows] WARNING: No iframes found with data-src!");
            return;
        }
        
        // Find which iframe is most visible (based on currentIndex or viewport)
        let targetIframe = null;
        
        // Refresh videoSlides and currentIndex
        videoSlides = findVideoSlides();
        const actualIndex = getCurrentVisibleIndex();
        currentIndex = actualIndex;
        
        // FIX: Get iframe from the actual visible slide, not by index into lazyIframes array
        // The lazyIframes NodeList order may not match videoSlides order
        if (actualIndex >= 0 && actualIndex < videoSlides.length) {
            const targetSlide = videoSlides[actualIndex];
            targetIframe = targetSlide.querySelector('iframe[data-src]');
            console.log(`[MovieShows] forcePlayVisibleVideos - Using iframe from slide ${actualIndex}`);
        }
        
        // Fallback: find the most centered iframe
        if (!targetIframe) {
            let bestMatch = null;
            let bestScore = -Infinity;
            
            lazyIframes.forEach((iframe, index) => {
                const rect = iframe.getBoundingClientRect();
                const centerY = rect.top + rect.height / 2;
                const viewportCenterY = window.innerHeight / 2;
                const distance = Math.abs(centerY - viewportCenterY);
                const score = -distance; // Higher score = closer to center
                
                if (score > bestScore && rect.top < window.innerHeight && rect.bottom > 0) {
                    bestScore = score;
                    bestMatch = iframe;
                }
            });
            
            targetIframe = bestMatch || lazyIframes[0];
        }
        
        // Play only the target iframe
        if (targetIframe) {
            const movieTitle = targetIframe.getAttribute('data-movie-title') || 'Unknown';
            console.log(`[MovieShows] Playing ONLY: "${movieTitle}"`);
            playVideo(targetIframe);
        }
    }

    function init() {
        if (initialized) return;

        console.log("[MovieShows] Initializing...");

        injectStyles();
        setupVideoObserver();
        setupIframeObserver();
        createPlayerSizeControl();
        createLayoutControl();
        createMuteControl();  // Add persistent mute/unmute button
        addAutoScrollStyles(); // Add CSS for auto-scroll indicator
        setupYouTubeMessageListener(); // Listen for video end events
        initYouTubeAPI(); // Load YouTube IFrame API for better control
        checkGoogleAuthCallback();  // Check for Google OAuth callback
        createLoginButton();  // Add login/profile button
        createInfoToggle();   // Toggle movie info visibility
        createActionPanelToggle(); // Toggle right action panel
        setupCarouselInteractions();
        setupNavigationHandlers();  // Enable search, filters, queue panels

        // START LOADING DATA
        loadMoviesData();

        scrollContainer = findScrollContainer();
        if (!scrollContainer) {
            setTimeout(init, 1000);
            return;
        }

        // Clear placeholders and populate with real videos
        setTimeout(populateInitialVideos, 1000);

        videoSlides = findVideoSlides();
        // Don't require existing slides - we'll add them
        if (videoSlides.length === 0) {
            console.log("[MovieShows] No slides yet, will populate after data loads");
        }

        console.log("[MovieShows] Found", videoSlides.length, "videos");

        document.addEventListener("wheel", handleWheel, {
            passive: false,
            capture: true,
        });
        document.addEventListener("keydown", handleKeydown);
        document.addEventListener("touchstart", handleTouchStart, {
            passive: true,
        });
        document.addEventListener("touchend", handleTouchEnd, { passive: true });
        scrollContainer.addEventListener("scroll", handleScroll, { passive: true });

        currentIndex = getCurrentVisibleIndex();

        // Setup observer to apply size when iframes load
        setupIframeObserver();

        // Apply initial player size
        const savedSize = localStorage.getItem("movieshows-player-size") || "large";
        setTimeout(() => applyPlayerSize(savedSize), 500);

        // Auto-click play queue
        setTimeout(() => {
            if (!clickQueuePlayButton()) {
                setTimeout(clickQueuePlayButton, 2000);
            }
        }, 2000);
        
        // Handle ?play= URL parameter for share links
        setTimeout(handlePlayUrlParameter, 2500);
        
        // Add tooltips to all buttons for better UX
        setTimeout(addTooltipsToAllButtons, 3000);
        
        // Fix hamburger menu button click issues
        setTimeout(fixHamburgerButton, 1000);

        initialized = true;
        console.log(
            "[MovieShows] Ready! Scroll: wheel/arrows/J/K | Size: 1/2/3/4 keys",
        );
    }
    
    // Wire up the existing hamburger button from the HTML (or create one if missing)
    function fixHamburgerButton() {
        console.log('[MovieShows] Wiring up hamburger menu...');
        
        // Check if we already wired it up
        if (window._hamburgerWired) {
            console.log('[MovieShows] Hamburger already wired');
            return;
        }
        
        // Find the EXISTING hamburger button in the HTML
        const existingHamburger = document.querySelector('button[aria-label="Open Quick Nav"]') 
            || document.querySelector('button[title="Quick Navigation"]')
            || document.querySelector('.fixed.top-4.left-4');
        
        // Find the EXISTING menu overlay and drawer in the HTML
        const existingOverlay = document.querySelector('.fixed.inset-0.z-\\[250\\]') 
            || document.querySelector('[class*="fixed"][class*="inset-0"][class*="bg-black"]');
        const existingDrawer = document.querySelector('.fixed.top-0.left-0.h-full.w-80') 
            || document.querySelector('[class*="fixed"][class*="left-0"][class*="h-full"]');
        
        if (existingHamburger && existingOverlay && existingDrawer) {
            console.log('[MovieShows] Found existing hamburger, overlay, and drawer - wiring them up!');
            
            // Find the close button in the drawer
            const closeBtn = existingDrawer.querySelector('button[aria-label="Close menu"]') 
                || existingDrawer.querySelector('button svg[class*="x"]')?.closest('button')
                || existingDrawer.querySelector('button');
            
            let isOpen = false;
            
            const openMenu = () => {
                isOpen = true;
                existingOverlay.classList.remove('opacity-0', 'pointer-events-none');
                existingOverlay.classList.add('opacity-100', 'pointer-events-auto');
                existingDrawer.classList.remove('-translate-x-full');
                existingDrawer.classList.add('translate-x-0');
                console.log('[MovieShows] Menu opened');
            };
            
            const closeMenu = () => {
                isOpen = false;
                existingOverlay.classList.add('opacity-0', 'pointer-events-none');
                existingOverlay.classList.remove('opacity-100', 'pointer-events-auto');
                existingDrawer.classList.add('-translate-x-full');
                existingDrawer.classList.remove('translate-x-0');
                console.log('[MovieShows] Menu closed');
            };
            
            // Wire up hamburger click
            existingHamburger.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault();
                console.log('[MovieShows] Existing hamburger clicked');
                if (isOpen) {
                    closeMenu();
                } else {
                    openMenu();
                }
            });
            
            // Wire up overlay click to close
            existingOverlay.addEventListener('click', (e) => {
                if (e.target === existingOverlay) {
                    closeMenu();
                }
            });
            
            // Wire up close button if found
            if (closeBtn) {
                closeBtn.addEventListener('click', closeMenu);
            }
            
            window._hamburgerWired = true;
            console.log('[MovieShows] Existing hamburger menu wired successfully');
            return;
        }
        
        console.log('[MovieShows] No existing hamburger found - creating new one');
        
        // If no existing hamburger, create our own (fallback)
        if (document.getElementById('movieshows-hamburger')) {
            console.log('[MovieShows] Custom hamburger already exists');
            return;
        }
        
        // Create hamburger button
        const hamburger = document.createElement('button');
        hamburger.id = 'movieshows-hamburger';
        hamburger.setAttribute('aria-label', 'Open Quick Nav');
        hamburger.title = 'Open navigation menu';
        hamburger.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
        `;
        hamburger.style.cssText = `
            position: fixed;
            top: 16px;
            left: 16px;
            z-index: 999999;
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            pointer-events: auto;
        `;
        
        // Hover effect
        hamburger.onmouseenter = () => {
            hamburger.style.background = 'rgba(34, 197, 94, 0.8)';
            hamburger.style.transform = 'scale(1.05)';
        };
        hamburger.onmouseleave = () => {
            hamburger.style.background = 'rgba(0, 0, 0, 0.6)';
            hamburger.style.transform = 'scale(1)';
        };
        
        // Create navigation panel
        const navPanel = document.createElement('div');
        navPanel.id = 'movieshows-nav-panel';
        navPanel.style.cssText = `
            position: fixed;
            top: 0;
            left: -320px;
            width: 300px;
            height: 100vh;
            background: rgba(10, 10, 15, 0.98);
            backdrop-filter: blur(20px);
            z-index: 999998;
            transition: left 0.3s ease;
            border-right: 1px solid rgba(255, 255, 255, 0.1);
            overflow-y: auto;
            pointer-events: auto;
        `;
        navPanel.innerHTML = `
            <div style="padding: 24px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;">
                    <h2 style="color: white; font-size: 20px; font-weight: bold; margin: 0;">🎬 MovieShows</h2>
                    <button id="close-nav-panel" style="background: none; border: none; color: #888; font-size: 24px; cursor: pointer; padding: 8px;">&times;</button>
                </div>
                
                <nav style="display: flex; flex-direction: column; gap: 8px;">
                    <a href="#" class="nav-link" data-action="home" style="display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-radius: 10px; color: white; text-decoration: none; transition: all 0.2s;">
                        <span style="font-size: 20px;">🏠</span>
                        <span>Home</span>
                    </a>
                    <a href="#" class="nav-link" data-action="search" style="display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-radius: 10px; color: white; text-decoration: none; transition: all 0.2s;">
                        <span style="font-size: 20px;">🔍</span>
                        <span>Search</span>
                    </a>
                    <a href="#" class="nav-link" data-action="queue" style="display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-radius: 10px; color: white; text-decoration: none; transition: all 0.2s;">
                        <span style="font-size: 20px;">📋</span>
                        <span>My Queue</span>
                    </a>
                    <a href="#" class="nav-link" data-action="filters" style="display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-radius: 10px; color: white; text-decoration: none; transition: all 0.2s;">
                        <span style="font-size: 20px;">🎛️</span>
                        <span>Filters</span>
                    </a>
                    <a href="#" class="nav-link" data-action="settings" style="display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-radius: 10px; color: white; text-decoration: none; transition: all 0.2s;">
                        <span style="font-size: 20px;">⚙️</span>
                        <span>Settings</span>
                    </a>
                </nav>
                
                <div style="margin-top: 32px; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.1);">
                    <h3 style="color: #888; font-size: 12px; text-transform: uppercase; margin-bottom: 16px;">Quick Filters</h3>
                    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                        <button class="quick-filter-btn" data-filter="all" style="padding: 8px 16px; border-radius: 20px; background: rgba(34, 197, 94, 0.2); border: 1px solid #22c55e; color: #22c55e; cursor: pointer; font-size: 13px;">All</button>
                        <button class="quick-filter-btn" data-filter="movies" style="padding: 8px 16px; border-radius: 20px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2); color: white; cursor: pointer; font-size: 13px;">Movies</button>
                        <button class="quick-filter-btn" data-filter="tv" style="padding: 8px 16px; border-radius: 20px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2); color: white; cursor: pointer; font-size: 13px;">TV Shows</button>
                        <button class="quick-filter-btn" data-filter="nowplaying" style="padding: 8px 16px; border-radius: 20px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2); color: white; cursor: pointer; font-size: 13px;">Now Playing</button>
                    </div>
                </div>
                
                <div style="position: absolute; bottom: 24px; left: 24px; right: 24px;">
                    <p style="color: #666; font-size: 11px; text-align: center;">MovieShows v2.0</p>
                </div>
            </div>
        `;
        
        // Add overlay for closing
        const overlay = document.createElement('div');
        overlay.id = 'nav-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.5);
            z-index: 999997;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        `;
        
        document.body.appendChild(hamburger);
        document.body.appendChild(navPanel);
        document.body.appendChild(overlay);
        
        let isNavOpen = false;
        
        const openNav = () => {
            isNavOpen = true;
            navPanel.style.left = '0';
            overlay.style.opacity = '1';
            overlay.style.pointerEvents = 'auto';
            hamburger.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            `;
        };
        
        const closeNav = () => {
            isNavOpen = false;
            navPanel.style.left = '-320px';
            overlay.style.opacity = '0';
            overlay.style.pointerEvents = 'none';
            hamburger.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="3" y1="6" x2="21" y2="6"></line>
                    <line x1="3" y1="12" x2="21" y2="12"></line>
                    <line x1="3" y1="18" x2="21" y2="18"></line>
                </svg>
            `;
        };
        
        // Toggle nav on hamburger click
        hamburger.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log('[MovieShows] Hamburger clicked');
            if (isNavOpen) {
                closeNav();
            } else {
                openNav();
            }
        });
        
        // Close on overlay click
        overlay.addEventListener('click', closeNav);
        
        // Close button
        navPanel.querySelector('#close-nav-panel').addEventListener('click', closeNav);
        
        // Nav link actions
        navPanel.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('mouseenter', () => {
                link.style.background = 'rgba(34, 197, 94, 0.2)';
            });
            link.addEventListener('mouseleave', () => {
                link.style.background = 'transparent';
            });
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const action = link.dataset.action;
                closeNav();
                
                setTimeout(() => {
                    switch(action) {
                        case 'home':
                            scrollToSlide(0);
                            break;
                        case 'search':
                            const searchBtn = Array.from(document.querySelectorAll('button')).find(b => 
                                b.textContent?.toLowerCase().includes('search') || 
                                b.textContent?.toLowerCase().includes('browse')
                            );
                            if (searchBtn) searchBtn.click();
                            break;
                        case 'queue':
                            const queueBtn = Array.from(document.querySelectorAll('button')).find(b => 
                                b.textContent?.toLowerCase().includes('queue')
                            );
                            if (queueBtn) queueBtn.click();
                            break;
                        case 'filters':
                            const filterBtn = Array.from(document.querySelectorAll('button')).find(b => 
                                b.textContent?.toLowerCase().includes('filter')
                            );
                            if (filterBtn) filterBtn.click();
                            break;
                        case 'settings':
                            showToast('Settings coming soon!');
                            break;
                    }
                }, 100);
            });
        });
        
        // Quick filter buttons
        navPanel.querySelectorAll('.quick-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const filter = btn.dataset.filter;
                closeNav();
                repopulateFeed(filter);
                
                // Update button styles
                navPanel.querySelectorAll('.quick-filter-btn').forEach(b => {
                    if (b.dataset.filter === filter) {
                        b.style.background = 'rgba(34, 197, 94, 0.2)';
                        b.style.borderColor = '#22c55e';
                        b.style.color = '#22c55e';
                    } else {
                        b.style.background = 'rgba(255,255,255,0.05)';
                        b.style.borderColor = 'rgba(255,255,255,0.2)';
                        b.style.color = 'white';
                    }
                });
            });
        });
        
        window._hamburgerWired = true;
        console.log('[MovieShows] Hamburger menu created successfully');
    }
    
    // Add tooltips to all buttons for user guidance
    function addTooltipsToAllButtons() {
        console.log('[MovieShows] Adding tooltips to buttons...');
        
        // Tooltip mappings for buttons based on text content or aria-label
        const tooltipMap = {
            // Navigation buttons
            'open quick nav': 'Open navigation menu to access other apps and settings',
            'quick navigation': 'Open navigation menu to access other apps and settings',
            // Filter buttons
            'all': 'Show all movies and TV shows',
            'movies': 'Filter to show only movies',
            'tv': 'Filter to show only TV shows',
            'now playing': 'Show currently in theaters',
            // Action buttons
            'like': 'Add this title to your favorites',
            'list': 'Save this title to your watch list',
            '+list': 'Save this title to your watch list',
            'share': 'Share this title with friends',
            // Search/Filter
            'search': 'Search for movies and TV shows',
            'filters': 'Apply filters to narrow down results',
            // Queue buttons
            'queue': 'View your watch queue and history',
            'my queue': 'View your saved watch list',
            // Settings
            'settings': 'Adjust player settings and preferences',
            // Playback
            'play': 'Play this video',
            'pause': 'Pause playback',
            'next': 'Go to next video',
            'previous': 'Go to previous video',
            'skip': 'Skip to next video immediately',
            // Sign in
            'sign in': 'Sign in to save your preferences and watch list',
            'login': 'Sign in to your account',
        };
        
        // Find all buttons and add tooltips
        const buttons = document.querySelectorAll('button, [role="button"], a.btn, .btn');
        let tooltipsAdded = 0;
        
        buttons.forEach(btn => {
            // Skip if already has a title
            if (btn.title && btn.title.length > 5) return;
            
            const text = (btn.textContent || btn.innerText || '').toLowerCase().trim();
            const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
            const combined = text + ' ' + ariaLabel;
            
            // Check for matches in tooltip map
            for (const [key, tooltip] of Object.entries(tooltipMap)) {
                if (combined.includes(key)) {
                    btn.title = tooltip;
                    tooltipsAdded++;
                    break;
                }
            }
            
            // Special handling for icon-only buttons
            if (!btn.title) {
                // Search icon
                if (btn.querySelector('svg path[d*="21 21l-6-6"]') || combined.includes('search')) {
                    btn.title = 'Search for movies and TV shows';
                    tooltipsAdded++;
                }
                // Hamburger/menu icon (3 lines)
                else if (btn.querySelectorAll('span.bg-white.rounded-full').length === 3) {
                    btn.title = 'Open navigation menu';
                    tooltipsAdded++;
                }
                // Heart/like icon
                else if (btn.querySelector('svg path[d*="M4.318 6.318"]')) {
                    btn.title = 'Add to favorites';
                    tooltipsAdded++;
                }
                // Plus/add icon  
                else if (btn.querySelector('svg path[d*="M12 4v16m8-8H4"]')) {
                    btn.title = 'Add to watch list';
                    tooltipsAdded++;
                }
                // Share icon
                else if (btn.querySelector('svg path[d*="M8.684 13.342"]')) {
                    btn.title = 'Share this title';
                    tooltipsAdded++;
                }
            }
        });
        
        console.log(`[MovieShows] Added ${tooltipsAdded} tooltips to buttons`);
    }

    function setupMutationObserver() {
        const observer = new MutationObserver(() => {
            if (!initialized) {
                init();
            } else if (scrollContainer) {
                const newSlides = findVideoSlides();
                if (newSlides.length !== videoSlides.length) {
                    videoSlides = newSlides;
                }
            }
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
            // Wait for React Hydration to finish
            setupMutationObserver();
            setTimeout(init, 3000);
        });
    } else {
        setupMutationObserver();
        setTimeout(init, 3000);
    }
})();
