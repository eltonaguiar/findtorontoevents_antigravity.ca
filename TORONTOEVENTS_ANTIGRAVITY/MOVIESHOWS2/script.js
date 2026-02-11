// Application State
const appState = {
  currentVideo: null,
  queue: [],
  favorites: new Set(),
  liked: new Set(),
  watchHistory: [],
  allContent: [],
  filteredContent: [],
  currentFilter: "all",
  searchQuery: "",
  sortMode: "title-asc",
  viewMode: "grid", // grid or list
  compactQueue: false,
  theaterMode: false,
  repeatMode: "off", // off, one, all
  shuffleMode: false,
  autoPlayNext: true,
};

// Content source paths - your scraper output will be loaded from these locations
const CONTENT_SOURCES = [
    "./movies-database-2026-01-30.json",
    "./content.json",
    "./catalog.json",
    "./data.json",
    "./data/content.json",
    "./data/catalog.json",
    "./data/all.json",
    "./data/movies.json",
    "./data/tv.json",
];

function safeText(v) {
  return typeof v === "string" ? v : v == null ? "" : String(v);
}

function buildId(raw) {
  const id =
    raw?.id ??
    raw?.tmdb_id ??
    raw?.tmdbId ??
    raw?.imdb_id ??
    raw?.imdbId ??
    raw?.slug ??
    raw?.key;
  if (id != null) return String(id);

  const title = safeText(raw?.title ?? raw?.name ?? raw?.primaryTitle).trim();
  const year = raw?.year ?? raw?.release_year ?? raw?.releaseYear ?? raw?.first_air_date?.slice?.(0, 4);
  return `${title || "unknown"}-${year || "unknown"}`;
}

function normalizeType(raw) {
  const t = (raw?.type ?? raw?.media_type ?? raw?.mediaType ?? raw?.kind ?? "").toString().toLowerCase();
  if (t.includes("tv") || t.includes("show") || t === "series") return "tv";
  if (t.includes("movie") || t === "film") return "movies";
  if (raw?.number_of_seasons != null || raw?.seasons != null) return "tv";
  return "movies";
}

function normalizeItem(raw) {
  const id = buildId(raw);
  const title = safeText(raw?.title ?? raw?.name ?? raw?.primaryTitle ?? raw?.original_title ?? raw?.originalTitle).trim();

  const year =
    raw?.year ??
    raw?.release_year ??
    raw?.releaseYear ??
    (typeof raw?.release_date === "string" ? Number(raw.release_date.slice(0, 4)) : undefined) ??
    (typeof raw?.first_air_date === "string" ? Number(raw.first_air_date.slice(0, 4)) : undefined);

  const thumbnail =
    raw?.thumbnail ??
    raw?.poster ??
    raw?.posterUrl ??
    raw?.poster_url ??
    raw?.backdrop ??
    raw?.backdropUrl ??
    raw?.image ??
    raw?.img ??
    "";

  const videoUrl =
    raw?.videoUrl ??
    raw?.video_url ??
    raw?.mp4 ??
    raw?.stream ??
    raw?.trailerUrl ??
    raw?.trailer_url ??
    "";

  const description =
    raw?.description ??
    raw?.overview ??
    raw?.plot ??
    raw?.summary ??
    "";

  const comingSoon =
    Boolean(raw?.comingSoon ?? raw?.coming_soon ?? raw?.upcoming) ||
    (typeof raw?.status === "string" && raw.status.toLowerCase().includes("coming"));
  
  const addedDate = raw?.addedDate ?? raw?.added_date ?? Date.now();
  const isNew = (Date.now() - addedDate) < (7 * 24 * 60 * 60 * 1000); // 7 days

  return {
    id,
    title: title || id,
    type: normalizeType(raw),
    year: Number.isFinite(Number(year)) ? Number(year) : "",
    thumbnail: safeText(thumbnail),
    videoUrl: safeText(videoUrl),
    description: safeText(description),
    comingSoon,
    addedDate,
    isNew,
    _raw: raw,
  };
}

function normalizePayload(payload) {
  let items = null;

  if (Array.isArray(payload)) items = payload;
  else if (payload && Array.isArray(payload.items)) items = payload.items;
  else if (payload && Array.isArray(payload.all)) items = payload.all;
  else if (payload && (Array.isArray(payload.movies) || Array.isArray(payload.tv))) {
    items = [...(payload.movies || []), ...(payload.tv || [])];
  }

  if (!Array.isArray(items)) return [];

  const normalized = items.map(normalizeItem).filter((x) => x.title && x.id);

  const seen = new Set();
  return normalized.filter((x) => (seen.has(x.id) ? false : (seen.add(x.id), true)));
}

async function fetchJson(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return await res.json();
}

async function loadContent() {
  // 1) If your scraper/build injects content directly:
  if (Array.isArray(window.MOVIESHOWS_CONTENT) || window.MOVIESHOWS_CONTENT?.items) {
    return normalizePayload(window.MOVIESHOWS_CONTENT);
  }

  // 2) Allow query override: ?source=/path/to/file.json
  const params = new URLSearchParams(window.location.search);
  const sourceOverride = params.get("source");
  if (sourceOverride) {
    try {
      const payload = await fetchJson(sourceOverride);
      return normalizePayload(payload);
    } catch (_) {}
  }

  // 3) Try known local paths
  for (const src of CONTENT_SOURCES) {
    try {
      const payload = await fetchJson(src);
      const normalized = normalizePayload(payload);
      if (normalized.length) return normalized;
    } catch (_) {}
  }

  return [];
}

// DOM Elements
const elements = {
    videoPlayer: document.getElementById('videoPlayer'),
    currentTitle: document.getElementById('currentTitle'),
    currentDescription: document.getElementById('currentDescription'),
    btnLike: document.getElementById('btnLike'),
    btnFavorite: document.getElementById('btnFavorite'),
    btnFullscreen: document.getElementById('btnFullscreen'),
    btnPip: document.getElementById('btnPip'),
    btnSpeed: document.getElementById('btnSpeed'),
    btnTheater: document.getElementById('btnTheater'),
    btnSkipBack: document.getElementById('btnSkipBack'),
    btnSkipForward: document.getElementById('btnSkipForward'),
    speedText: document.getElementById('speedText'),
    btnShuffle: document.getElementById('btnShuffle'),
    btnRepeat: document.getElementById('btnRepeat'),
    btnAutoPlay: document.getElementById('btnAutoPlay'),
    btnClearQueue: document.getElementById('btnClearQueue'),
    btnExportQueue: document.getElementById('btnExportQueue'),
    btnImportQueue: document.getElementById('btnImportQueue'),
    btnCompactQueue: document.getElementById('btnCompactQueue'),
    repeatIcon: document.getElementById('repeatIcon'),
    queueContainer: document.getElementById('queueContainer'),
    queueEmpty: document.getElementById('queueEmpty'),
    queueCount: document.getElementById('queueCount'),
    sidePanel: document.getElementById('sidePanel'),
    favoritesPanel: document.getElementById('favoritesPanel'),
    togglePanel: document.getElementById('togglePanel'),
    closePanel: document.getElementById('closePanel'),
    toggleFavorites: document.getElementById('toggleFavorites'),
    closeFavorites: document.getElementById('closeFavorites'),
    panelContent: document.getElementById('panelContent'),
    favoritesContent: document.getElementById('favoritesContent'),
    searchInput: document.getElementById('searchInput'),
    sortSelect: document.getElementById('sortSelect'),
    filterButtons: document.querySelectorAll('.filter-btn'),
    overlay: document.getElementById('overlay'),
    favoritesCount: document.getElementById('favoritesCount'),
    scrollToTop: document.getElementById('scrollToTop'),
    progressMarkers: document.getElementById('progressMarkers'),
    continueWatchingSection: document.getElementById('continueWatchingSection'),
    continueWatchingGrid: document.getElementById('continueWatchingGrid'),
    btnThemeToggle: document.getElementById('btnThemeToggle'),
    themeIcon: document.getElementById('themeIcon'),
    searchResultsCount: document.getElementById('searchResultsCount'),
    offlineBanner: document.getElementById('offlineBanner'),
    videoTimeInfo: document.getElementById('videoTimeInfo'),
    queueDuration: document.getElementById('queueDuration')
};

function scrollPlayerSectionIntoView({ behavior = 'smooth', block = 'center', delay = 80 } = {}) {
    const section = document.querySelector('.player-section');
    if (!section || typeof section.scrollIntoView !== 'function') return;
    window.setTimeout(() => {
        section.scrollIntoView({ behavior, block });
    }, delay);
}

let scrollPlayerOnNextPlay = false;
// Initialize App
async function init() {
    loadState();

    elements.panelContent.innerHTML =
        '<p style="grid-column: 1/-1; text-align: center; color: var(--text-secondary);">Loading content…</p>';

    const content = await loadContent();
    appState.allContent = content;
    appState.filteredContent = content;

    renderBrowseContent();
    renderQueue();
    renderFavorites();
    renderWatchHistory();
    updateFavoritesCount();

    setupEventListeners();
    setupDragAndDrop();
    setupLazyLoading();
    setupScrollToTop();
    setupOfflineDetection();

    elements.videoPlayer.addEventListener('playing', () => {
        if (scrollPlayerOnNextPlay) {
            scrollPlayerOnNextPlay = false;
            scrollPlayerSectionIntoView();
        }
    });

    // Load state from URL after content is loaded
    loadFromURL();
}

// Load state from localStorage
function loadState() {
    const savedFavorites = localStorage.getItem('favorites');
    const savedLiked = localStorage.getItem('liked');
    const savedQueue = localStorage.getItem('queue');
    const savedHistory = localStorage.getItem('watchHistory');
    const savedVolume = localStorage.getItem('videoVolume');
    const savedMuted = localStorage.getItem('videoMuted');
    
    if (savedFavorites) {
        appState.favorites = new Set(JSON.parse(savedFavorites));
    }
    if (savedLiked) {
        appState.liked = new Set(JSON.parse(savedLiked));
    }
    if (savedQueue) {
        appState.queue = JSON.parse(savedQueue);
    }
    if (savedHistory) {
        appState.watchHistory = JSON.parse(savedHistory);
    }
    
    // Restore playback settings
    const savedShuffle = localStorage.getItem('shuffleMode');
    const savedRepeat = localStorage.getItem('repeatMode');
    
    if (savedShuffle !== null) {
        appState.shuffleMode = savedShuffle === 'true';
        elements.btnShuffle.classList.toggle('active', appState.shuffleMode);
    }
    
    if (savedRepeat !== null) {
        appState.repeatMode = savedRepeat;
        updateRepeatButton();
    }
    
    // Restore auto-play setting
    const savedAutoPlay = localStorage.getItem('autoPlayNext');
    if (savedAutoPlay !== null) {
        appState.autoPlayNext = savedAutoPlay === 'true';
        elements.btnAutoPlay.classList.toggle('active', appState.autoPlayNext);
        elements.btnAutoPlay.title = appState.autoPlayNext ? 'Auto-play Next: ON' : 'Auto-play Next: OFF';
    }
    
    // Restore view mode
    const savedView = localStorage.getItem('viewMode');
    if (savedView) {
        appState.viewMode = savedView;
        elements.panelContent.classList.toggle('list-view', appState.viewMode === 'list');
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === appState.viewMode);
        });
    }
    
    // Restore sort mode
    const savedSort = localStorage.getItem('sortMode');
    if (savedSort) {
        appState.sortMode = savedSort;
        elements.sortSelect.value = savedSort;
    }
    
    // Restore video settings
    if (savedVolume !== null) {
        elements.videoPlayer.volume = parseFloat(savedVolume);
    }
    if (savedMuted !== null) {
        elements.videoPlayer.muted = savedMuted === 'true';
    }
    
    // Restore playback speed
    const savedSpeed = localStorage.getItem('playbackSpeed');
    if (savedSpeed !== null) {
        setPlaybackSpeed(parseFloat(savedSpeed));
    }
    
    // Restore theme
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
        elements.themeIcon.textContent = savedTheme === 'dark' ? '🌙' : '☀️';
    }
}

// Save state to localStorage
function saveState() {
    localStorage.setItem('favorites', JSON.stringify([...appState.favorites]));
    localStorage.setItem('liked', JSON.stringify([...appState.liked]));
    localStorage.setItem('queue', JSON.stringify(appState.queue));
    localStorage.setItem('watchHistory', JSON.stringify(appState.watchHistory));
}

// Setup Event Listeners
function setupEventListeners() {
    // Panel toggles
    elements.togglePanel.addEventListener('click', () => toggleSidePanel());
    elements.closePanel.addEventListener('click', () => toggleSidePanel());
    elements.toggleFavorites.addEventListener('click', () => toggleFavoritesPanel());
    elements.closeFavorites.addEventListener('click', () => toggleFavoritesPanel());
    
    // Overlay click to close panels
    elements.overlay.addEventListener('click', () => {
        closeAllPanels();
    });
    
    // Like and Favorite buttons
    elements.btnLike.addEventListener('click', toggleLike);
    elements.btnFavorite.addEventListener('click', toggleFavorite);
    elements.btnFullscreen.addEventListener('click', toggleFullscreen);
    elements.btnPip.addEventListener('click', togglePictureInPicture);
    elements.btnSpeed.addEventListener('click', cyclePlaybackSpeed);
    elements.btnTheater.addEventListener('click', toggleTheaterMode);
    elements.btnSkipBack.addEventListener('click', () => seekVideo(-5));
    elements.btnSkipForward.addEventListener('click', () => seekVideo(5));
    
    // Queue controls
    elements.btnShuffle.addEventListener('click', toggleShuffle);
    elements.btnRepeat.addEventListener('click', cycleRepeatMode);
    elements.btnAutoPlay.addEventListener('click', toggleAutoPlay);
    elements.btnClearQueue.addEventListener('click', clearQueue);
    elements.btnCompactQueue.addEventListener('click', toggleCompactQueue);
    elements.btnExportQueue.addEventListener('click', exportQueue);
    elements.btnImportQueue.addEventListener('click', () => importQueueDialog());
    elements.btnThemeToggle.addEventListener('click', toggleTheme);
    
    // PiP events
    elements.videoPlayer.addEventListener('enterpictureinpicture', () => {
        elements.btnPip.classList.add('active');
    });
    elements.videoPlayer.addEventListener('leavepictureinpicture', () => {
        elements.btnPip.classList.remove('active');
    });
    
    // Search
    elements.searchInput.addEventListener('input', (e) => {
        appState.searchQuery = e.target.value.toLowerCase();
        filterContent();
    });
    
    // Sort
    elements.sortSelect.addEventListener('change', (e) => {
        appState.sortMode = e.target.value;
        sortAndFilterContent();
        localStorage.setItem('sortMode', appState.sortMode);
    });
    
    // Filter buttons
    elements.filterButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            elements.filterButtons.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            appState.currentFilter = e.target.dataset.filter;
            filterContent();
        });
    });
    
    // View mode toggle
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            appState.viewMode = e.target.dataset.view;
            elements.panelContent.classList.toggle('list-view', appState.viewMode === 'list');
            localStorage.setItem('viewMode', appState.viewMode);
        });
    });
    
    // Video player events
    elements.videoPlayer.addEventListener('ended', () => {
        if (appState.autoPlayNext) {
            playNextInQueue();
        }
    });
    
    // Save progress periodically and track completion
    elements.videoPlayer.addEventListener('timeupdate', () => {
        saveCurrentProgress();
        trackVideoCompletion();
        updateVideoTimeInfo();
    });
    
    // Loading states
    elements.videoPlayer.addEventListener('loadstart', showVideoLoading);
    elements.videoPlayer.addEventListener('canplay', hideVideoLoading);
    elements.videoPlayer.addEventListener('playing', hideVideoLoading);
    elements.videoPlayer.addEventListener('waiting', showVideoLoading);
    
    // Error handling
    elements.videoPlayer.addEventListener('error', handleVideoError);
    elements.videoPlayer.addEventListener('stalled', () => {
        console.warn('Video playback stalled');
    });
    
    // Double-click to fullscreen
    elements.videoPlayer.addEventListener('dblclick', toggleFullscreen);
    
    // Click to play/pause (single click)
    elements.videoPlayer.addEventListener('click', (e) => {
        // Only if not double-click
        if (e.detail === 1) {
            setTimeout(() => {
                if (e.detail === 1) {
                    togglePlayPause();
                }
            }, 200);
        }
    });
    
    // Keyboard shortcuts
    setupKeyboardShortcuts();
}

// Keyboard Shortcuts Setup
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Don't trigger shortcuts if user is typing in input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }

        switch (e.key.toLowerCase()) {
            case ' ':
            case 'k':
                // Space or K: Play/Pause
                e.preventDefault();
                togglePlayPause();
                break;

            case 'f':
                // F: Fullscreen
                e.preventDefault();
                toggleFullscreen();
                break;
            
            case 'p':
                // P: Picture-in-Picture
                e.preventDefault();
                togglePictureInPicture();
                break;
            
            case '<':
            case ',':
                // < or ,: Decrease speed
                e.preventDefault();
                decreaseSpeed();
                break;
            
            case '>':
            case '.':
                // > or .: Increase speed
                e.preventDefault();
                increaseSpeed();
                break;

            case 'm':
                // M: Mute/Unmute
                e.preventDefault();
                toggleMute();
                break;

            case 'arrowleft':
                // Left Arrow: Seek backward 10s
                e.preventDefault();
                seekVideo(-10);
                break;

            case 'arrowright':
                // Right Arrow: Seek forward 10s
                e.preventDefault();
                seekVideo(10);
                break;

            case 'arrowup':
                // Up Arrow: Volume up
                e.preventDefault();
                adjustVolume(0.1);
                break;

            case 'arrowdown':
                // Down Arrow: Volume down
                e.preventDefault();
                adjustVolume(-0.1);
                break;

            case 'n':
                // N: Next in queue
                e.preventDefault();
                playNextInQueue();
                break;

            case 'l':
                // L: Like current video
                e.preventDefault();
                if (appState.currentVideo) toggleLike();
                break;

            case 's':
                // S: Add to favorites
                e.preventDefault();
                if (appState.currentVideo) toggleFavorite();
                break;

            case 'b':
                // B: Toggle browse panel
                e.preventDefault();
                toggleSidePanel();
                break;

            case 'escape':
                // ESC: Close panels or exit fullscreen
                if (document.fullscreenElement) {
                    document.exitFullscreen();
                } else {
                    closeAllPanels();
                }
                break;

            case '?':
                // ?: Show keyboard shortcuts help
                e.preventDefault();
                showKeyboardShortcutsHelp();
                break;
        }
    });
}

function togglePlayPause() {
    if (!elements.videoPlayer.src) return;
    
    if (elements.videoPlayer.paused) {
        elements.videoPlayer.play().catch(() => {});
    } else {
        elements.videoPlayer.pause();
    }
}

function toggleFullscreen() {
    const container = document.querySelector('.video-wrapper');
    
    if (!document.fullscreenElement) {
        if (container.requestFullscreen) {
            container.requestFullscreen();
        } else if (container.webkitRequestFullscreen) {
            container.webkitRequestFullscreen();
        } else if (container.msRequestFullscreen) {
            container.msRequestFullscreen();
        }
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }
}

async function togglePictureInPicture() {
    try {
        if (document.pictureInPictureElement) {
            await document.exitPictureInPicture();
        } else if (document.pictureInPictureEnabled) {
            await elements.videoPlayer.requestPictureInPicture();
        }
    } catch (error) {
        console.log('Picture-in-Picture not supported or failed:', error);
    }
}

function cyclePlaybackSpeed() {
    const speeds = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
    const currentSpeed = elements.videoPlayer.playbackRate;
    const currentIndex = speeds.indexOf(currentSpeed);
    const nextIndex = (currentIndex + 1) % speeds.length;
    const nextSpeed = speeds[nextIndex];
    
    setPlaybackSpeed(nextSpeed);
}

function setPlaybackSpeed(speed) {
    elements.videoPlayer.playbackRate = speed;
    elements.speedText.textContent = speed === 1 ? '1x' : `${speed}x`;
    elements.btnSpeed.classList.toggle('active', speed !== 1);
    localStorage.setItem('playbackSpeed', speed);
}

function increaseSpeed() {
    const speeds = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
    const currentSpeed = elements.videoPlayer.playbackRate;
    const nextSpeed = speeds.find(s => s > currentSpeed) || 2;
    setPlaybackSpeed(nextSpeed);
}

function decreaseSpeed() {
    const speeds = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];
    const currentSpeed = elements.videoPlayer.playbackRate;
    const prevSpeed = speeds.reverse().find(s => s < currentSpeed) || 0.25;
    setPlaybackSpeed(prevSpeed);
}

function toggleMute() {
    elements.videoPlayer.muted = !elements.videoPlayer.muted;
    localStorage.setItem('videoMuted', elements.videoPlayer.muted);
}

function seekVideo(seconds) {
    if (!elements.videoPlayer.src) return;
    elements.videoPlayer.currentTime = Math.max(
        0,
        Math.min(elements.videoPlayer.duration || 0, elements.videoPlayer.currentTime + seconds)
    );
}

function adjustVolume(delta) {
    const newVolume = Math.max(0, Math.min(1, elements.videoPlayer.volume + delta));
    elements.videoPlayer.volume = newVolume;
    elements.videoPlayer.muted = false;
    localStorage.setItem('videoVolume', newVolume);
    localStorage.setItem('videoMuted', false);
}

function showKeyboardShortcutsHelp() {
    const helpText = `
🎹 Keyboard Shortcuts:

Space/K - Play/Pause
F - Fullscreen
P - Picture-in-Picture
M - Mute/Unmute
← - Seek backward 10s
→ - Seek forward 10s
↑ - Volume up
↓ - Volume down
< - Decrease speed
> - Increase speed
N - Next in queue
L - Like video
S - Add to favorites
B - Toggle browse panel
ESC - Close panels / Exit fullscreen
? - Show this help
    `.trim();

    alert(helpText);
}

// Video Progress Tracking
let progressSaveTimeout = null;

function saveCurrentProgress() {
    if (!appState.currentVideo || !elements.videoPlayer.src) return;
    
    // Throttle saves to every 2 seconds
    if (progressSaveTimeout) return;
    
    progressSaveTimeout = setTimeout(() => {
        const progress = {
            videoId: appState.currentVideo.id,
            currentTime: elements.videoPlayer.currentTime,
            duration: elements.videoPlayer.duration,
            timestamp: Date.now()
        };
        
        localStorage.setItem(`progress_${appState.currentVideo.id}`, JSON.stringify(progress));
        progressSaveTimeout = null;
    }, 2000);
}

function getVideoProgress(videoId) {
    const saved = localStorage.getItem(`progress_${videoId}`);
    if (!saved) return null;
    
    try {
        return JSON.parse(saved);
    } catch {
        return null;
    }
}

function clearVideoProgress(videoId) {
    localStorage.removeItem(`progress_${videoId}`);
}

// Watch History Tracking
function addToWatchHistory(video, completionPercent) {
    // Remove existing entry for this video
    appState.watchHistory = appState.watchHistory.filter(item => item.id !== video.id);
    
    // Add new entry at the beginning
    appState.watchHistory.unshift({
        id: video.id,
        title: video.title,
        thumbnail: video.thumbnail,
        type: video.type,
        year: video.year,
        completionPercent: Math.round(completionPercent),
        watchedAt: Date.now(),
        _video: video
    });
    
    // Keep only last 50 items
    if (appState.watchHistory.length > 50) {
        appState.watchHistory = appState.watchHistory.slice(0, 50);
    }
    
    saveState();
}

function trackVideoCompletion() {
    if (!appState.currentVideo || !elements.videoPlayer.duration) return;
    
    const percent = (elements.videoPlayer.currentTime / elements.videoPlayer.duration) * 100;
    
    // Track as "watched" if >80% completed
    if (percent >= 80) {
        addToWatchHistory(appState.currentVideo, percent);
    }
}

function clearWatchHistory() {
    if (confirm('Clear all watch history?')) {
        appState.watchHistory = [];
        saveState();
        renderWatchHistory();
    }
}

function renderWatchHistory() {
    if (appState.watchHistory.length === 0) {
        elements.continueWatchingSection.style.display = 'none';
        return;
    }
    
    elements.continueWatchingSection.style.display = 'block';
    elements.continueWatchingGrid.innerHTML = '';
    
    // Show only unwatched (< 95% completed) items
    const inProgress = appState.watchHistory.filter(item => item.completionPercent < 95);
    
    if (inProgress.length === 0) {
        elements.continueWatchingSection.style.display = 'none';
        return;
    }
    
    inProgress.slice(0, 6).forEach(item => {
        const div = document.createElement('div');
        div.className = 'continue-item';
        
        div.innerHTML = `
            <div style="position: relative;">
                <img src="${item.thumbnail || 'https://via.placeholder.com/300x169?text=No+Image'}" alt="${item.title}" class="continue-item-thumbnail">
                <div class="continue-progress-bar" style="width: ${item.completionPercent}%"></div>
            </div>
            <div class="continue-item-info">
                <div class="continue-item-title">${item.title}</div>
                <div class="continue-item-progress">${item.completionPercent}% watched</div>
            </div>
        `;
        
        div.addEventListener('click', () => {
            const video = appState.allContent.find(v => v.id === item.id);
            if (video) {
                playVideo(video);
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
        
        elements.continueWatchingGrid.appendChild(div);
    });
}

// Make globally accessible
window.clearWatchHistory = clearWatchHistory;

// URL State Management
function updateURL() {
    if (!('URLSearchParams' in window)) return;
    
    const params = new URLSearchParams();
    
    // Add current video
    if (appState.currentVideo) {
        params.set('v', appState.currentVideo.id);
    }
    
    // Add queue (limit to first 10 items to avoid huge URLs)
    if (appState.queue.length > 0) {
        const queueIds = appState.queue.slice(0, 10).map(item => item.id).join(',');
        params.set('q', queueIds);
    }
    
    // Add playback modes
    if (appState.repeatMode !== 'off') {
        params.set('repeat', appState.repeatMode);
    }
    if (appState.shuffleMode) {
        params.set('shuffle', '1');
    }
    
    const newURL = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, '', newURL);
}

function loadFromURL() {
    if (!('URLSearchParams' in window)) return;
    
    const params = new URLSearchParams(window.location.search);
    
    // Load current video
    const videoId = params.get('v');
    if (videoId && appState.allContent.length > 0) {
        const video = appState.allContent.find(item => item.id === videoId);
        if (video) {
            setTimeout(() => playVideo(video), 500);
        }
    }
    
    // Load queue
    const queueIds = params.get('q');
    if (queueIds && appState.allContent.length > 0) {
        const ids = queueIds.split(',');
        ids.forEach(id => {
            const item = appState.allContent.find(item => item.id === id);
            if (item && !appState.queue.some(q => q.id === id)) {
                appState.queue.push(item);
            }
        });
        renderQueue();
    }
    
    // Load playback modes
    const repeat = params.get('repeat');
    if (repeat && ['off', 'all', 'one'].includes(repeat)) {
        appState.repeatMode = repeat;
        updateRepeatButton();
    }
    
    const shuffle = params.get('shuffle');
    if (shuffle === '1') {
        appState.shuffleMode = true;
        elements.btnShuffle.classList.add('active');
    }
}

function shareCurrentState() {
    const url = window.location.href;
    
    if (navigator.share) {
        navigator.share({
            title: 'MovieShows Queue',
            text: appState.currentVideo ? `Watch: ${appState.currentVideo.title}` : 'Check out this queue!',
            url: url
        }).catch(() => {
            copyToClipboard(url);
        });
    } else {
        copyToClipboard(url);
    }
}

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            alert('Link copied to clipboard!');
        });
    } else {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        alert('Link copied to clipboard!');
    }
}

// Make globally accessible
window.shareCurrentState = shareCurrentState;

// Scroll to top functionality
function setupScrollToTop() {
    const scrollThreshold = 300;
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > scrollThreshold) {
            elements.scrollToTop.classList.add('visible');
        } else {
            elements.scrollToTop.classList.remove('visible');
        }
    });
    
    elements.scrollToTop.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// Theme Toggle
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    elements.themeIcon.textContent = newTheme === 'dark' ? '🌙' : '☀️';
    localStorage.setItem('theme', newTheme);
}

// Offline Detection
function setupOfflineDetection() {
    function updateOnlineStatus() {
        if (navigator.onLine) {
            elements.offlineBanner.style.display = 'none';
        } else {
            elements.offlineBanner.style.display = 'flex';
        }
    }
    
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();
}

// Theater Mode
function toggleTheaterMode() {
    appState.theaterMode = !appState.theaterMode;
    const playerSection = document.querySelector('.player-section');
    playerSection.classList.toggle('theater-mode', appState.theaterMode);
    elements.btnTheater.classList.toggle('active', appState.theaterMode);
    localStorage.setItem('theaterMode', appState.theaterMode);
}

// Video Time Info
function updateVideoTimeInfo() {
    if (!elements.videoPlayer.duration) {
        elements.videoTimeInfo.textContent = '';
        return;
    }
    
    const current = elements.videoPlayer.currentTime;
    const duration = elements.videoPlayer.duration;
    const remaining = duration - current;
    
    const formatTime = (seconds) => {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        
        if (h > 0) {
            return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }
        return `${m}:${s.toString().padStart(2, '0')}`;
    };
    
    elements.videoTimeInfo.textContent = `${formatTime(current)} / ${formatTime(duration)} (${formatTime(remaining)} remaining)`;
}

// Export/Import Queue
function exportQueue() {
    if (appState.queue.length === 0) {
        alert('Queue is empty!');
        return;
    }
    
    const queueData = {
        version: '1.0',
        exportedAt: new Date().toISOString(),
        queue: appState.queue.map(item => ({
            id: item.id,
            title: item.title,
            type: item.type,
            year: item.year
        })),
        settings: {
            repeatMode: appState.repeatMode,
            shuffleMode: appState.shuffleMode,
            autoPlayNext: appState.autoPlayNext
        }
    };
    
    const blob = new Blob([JSON.stringify(queueData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `movieshows-queue-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

function importQueueDialog() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = (event) => {
            try {
                const data = JSON.parse(event.target.result);
                importQueue(data);
            } catch (err) {
                alert('Invalid queue file!');
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

function importQueue(data) {
    if (!data.queue || !Array.isArray(data.queue)) {
        alert('Invalid queue format!');
        return;
    }
    
    // Find matching content items
    const importedQueue = [];
    data.queue.forEach(qItem => {
        const found = appState.allContent.find(item => 
            item.id === qItem.id || 
            (item.title === qItem.title && item.year === qItem.year)
        );
        if (found) {
            importedQueue.push(found);
        }
    });
    
    if (importedQueue.length === 0) {
        alert('No matching content found in catalog!');
        return;
    }
    
    if (confirm(`Import ${importedQueue.length} items? This will replace your current queue.`)) {
        appState.queue = importedQueue;
        
        // Import settings if available
        if (data.settings) {
            if (data.settings.repeatMode) {
                appState.repeatMode = data.settings.repeatMode;
                updateRepeatButton();
            }
            if (data.settings.shuffleMode !== undefined) {
                appState.shuffleMode = data.settings.shuffleMode;
                elements.btnShuffle.classList.toggle('active', appState.shuffleMode);
            }
            if (data.settings.autoPlayNext !== undefined) {
                appState.autoPlayNext = data.settings.autoPlayNext;
                elements.btnAutoPlay.classList.toggle('active', appState.autoPlayNext);
            }
        }
        
        saveState();
        renderQueue();
        updateURL();
    }
}

// Lazy Loading for Images
let imageObserver = null;

function setupLazyLoading() {
    if ('IntersectionObserver' in window) {
        imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    const src = img.dataset.src;
                    
                    if (src) {
                        img.src = src;
                        img.removeAttribute('data-src');
                        img.classList.remove('lazy');
                        observer.unobserve(img);
                    }
                }
            });
        }, {
            rootMargin: '50px 0px',
            threshold: 0.01
        });
    }
}

function observeImage(img) {
    if (imageObserver) {
        imageObserver.observe(img);
    } else {
        // Fallback for browsers without IntersectionObserver
        if (img.dataset.src) {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        }
    }
}

// Toggle Side Panel
function toggleSidePanel() {
    elements.sidePanel.classList.toggle('open');
    elements.overlay.classList.toggle('active');
}

// Toggle Favorites Panel
function toggleFavoritesPanel() {
    elements.favoritesPanel.classList.toggle('open');
    elements.overlay.classList.toggle('active');
}

// Close All Panels
function closeAllPanels() {
    elements.sidePanel.classList.remove('open');
    elements.favoritesPanel.classList.remove('open');
    elements.overlay.classList.remove('active');
}

// Filter Content
function filterContent() {
    let filtered = appState.allContent;
    
    // Apply filter
    if (appState.currentFilter !== 'all') {
        if (appState.currentFilter === 'coming-soon') {
            filtered = filtered.filter(item => item.comingSoon);
        } else {
            filtered = filtered.filter(item => item.type === appState.currentFilter);
        }
    }
    
    // Apply search
    if (appState.searchQuery) {
        filtered = filtered.filter(item => 
            item.title.toLowerCase().includes(appState.searchQuery)
        );
    }
    
    appState.filteredContent = filtered;
    sortAndFilterContent();
}

function sortAndFilterContent() {
    let sorted = [...appState.filteredContent];
    
    const [field, direction] = appState.sortMode.split('-');
    
    sorted.sort((a, b) => {
        let aVal = a[field];
        let bVal = b[field];
        
        if (field === 'title') {
            aVal = (aVal || '').toLowerCase();
            bVal = (bVal || '').toLowerCase();
        } else if (field === 'year') {
            aVal = parseInt(aVal) || 0;
            bVal = parseInt(bVal) || 0;
        }
        
        if (direction === 'asc') {
            return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
        } else {
            return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
        }
    });
    
    appState.filteredContent = sorted;
    updateSearchResultsCount();
    renderBrowseContent();
}

function updateSearchResultsCount() {
    if (appState.searchQuery || appState.currentFilter !== 'all') {
        const count = appState.filteredContent.length;
        const total = appState.allContent.length;
        elements.searchResultsCount.textContent = `${count} of ${total}`;
        elements.searchResultsCount.style.display = 'block';
    } else {
        elements.searchResultsCount.style.display = 'none';
    }
}

// Render Browse Content
function renderBrowseContent() {
    elements.panelContent.innerHTML = '';
    
    if (appState.filteredContent.length === 0) {
        const msg = appState.allContent.length === 0
            ? `<div style="text-align: center; padding: 3rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📺</div>
                <h3 style="margin-bottom: 0.5rem;">No Content Available</h3>
                <p style="color: var(--text-secondary);">Place your scraper output as <b>content.json</b> or <b>data/content.json</b></p>
                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.5rem;">Or set <code>window.MOVIESHOWS_CONTENT</code> before page load</p>
               </div>`
            : `<div style="text-align: center; padding: 3rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">🔍</div>
                <h3 style="margin-bottom: 0.5rem;">No Results Found</h3>
                <p style="color: var(--text-secondary);">Try adjusting your search or filters</p>
               </div>`;
        elements.panelContent.innerHTML = msg;
        return;
    }
    
    appState.filteredContent.forEach(item => {
        const contentItem = createContentItem(item);
        elements.panelContent.appendChild(contentItem);
    });
}

// Create Content Item Element
function createContentItem(item) {
    const div = document.createElement('div');
    div.className = 'content-item';
    div.dataset.id = item.id;
    
  const isFavorite = appState.favorites.has(item.id);
  const isLiked = appState.liked.has(item.id);
  const isWatched = appState.watchHistory.some(h => h.id === item.id && h.completionPercent >= 95);
  const thumbnailUrl = item.thumbnail || 'https://via.placeholder.com/300x169?text=No+Image';
  const placeholderUrl = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="300" height="169"%3E%3Crect fill="%231a1a1a"/%3E%3C/svg%3E';
  
  div.innerHTML = `
    <img data-src="${thumbnailUrl}" src="${placeholderUrl}" alt="${item.title}" class="content-item-thumbnail lazy" onerror="this.src='https://via.placeholder.com/300x169?text=No+Image'">
    ${item.isNew ? '<span class="badge-new">NEW</span>' : ''}
    ${isWatched ? '<span class="badge-watched">✓ WATCHED</span>' : ''}
    <div class="content-item-info">
      <div class="content-item-title">${item.title}</div>
      <div class="content-item-meta">${item.year ? item.year + ' • ' : ''}${item.type === 'tv' ? 'TV Show' : 'Movie'}${item.comingSoon ? ' • Coming Soon' : ''}</div>
    </div>
    <div class="content-item-actions">
            <button class="content-item-btn" data-action="play" title="Play">▶️</button>
            <button class="content-item-btn ${isFavorite ? 'active' : ''}" data-action="favorite" title="Add to Favorites">❤️</button>
            <button class="content-item-btn ${isLiked ? 'active' : ''}" data-action="like" title="Like">👍</button>
            <button class="content-item-btn" data-action="add-queue" title="Add to Queue">➕</button>
        </div>
    `;
    
    // Add event listeners
    div.querySelector('[data-action="play"]').addEventListener('click', (e) => {
        e.stopPropagation();
        playVideo(item);
        closeAllPanels();
    });
    
    div.querySelector('[data-action="favorite"]').addEventListener('click', (e) => {
        e.stopPropagation();
        toggleFavoriteById(item.id);
        renderBrowseContent();
        renderFavorites();
        updateFavoritesCount();
    });
    
    div.querySelector('[data-action="like"]').addEventListener('click', (e) => {
        e.stopPropagation();
        toggleLikeById(item.id);
        renderBrowseContent();
    });
    
    div.querySelector('[data-action="add-queue"]').addEventListener('click', (e) => {
        e.stopPropagation();
        addToQueue(item);
    });
    
    // Click on item to play
    div.addEventListener('click', () => {
        playVideo(item);
        closeAllPanels();
    });
    
    // Set up lazy loading for the image
    const img = div.querySelector('.lazy');
    if (img) {
        observeImage(img);
    }
    
    return div;
}

// Play Video
function playVideo(item) {
    appState.currentVideo = item;
    elements.currentTitle.textContent = item.title;
    elements.currentDescription.textContent = item.description || '';
    
    updatePlayerButtons();
    updateURL();
    addProgressMarkers();
    
    if (!item.videoUrl) {
        elements.videoPlayer.removeAttribute('src');
        elements.videoPlayer.load();
        return;
    }
    
    // Show loading state
    showVideoLoading();
    
    elements.videoPlayer.src = item.videoUrl;
    if (item.thumbnail) elements.videoPlayer.poster = item.thumbnail;
    
    // Restore saved progress
    const savedProgress = getVideoProgress(item.id);
    if (savedProgress && savedProgress.currentTime > 5 && savedProgress.currentTime < savedProgress.duration - 30) {
        elements.videoPlayer.currentTime = savedProgress.currentTime;
    }
    
    elements.videoPlayer.play().catch(() => {});
}

function addProgressMarkers() {
    elements.progressMarkers.innerHTML = '';
    
    // Add markers at 25%, 50%, 75%
    [25, 50, 75].forEach(percent => {
        const marker = document.createElement('div');
        marker.className = 'progress-marker';
        marker.style.left = `${percent}%`;
        marker.title = `${percent}%`;
        elements.progressMarkers.appendChild(marker);
    });
}

function showVideoLoading() {
    const wrapper = document.querySelector('.video-wrapper');
    wrapper.classList.add('video-loading');
}

function hideVideoLoading() {
    const wrapper = document.querySelector('.video-wrapper');
    wrapper.classList.remove('video-loading');
}

function handleVideoError(e) {
    hideVideoLoading();
    
    const error = elements.videoPlayer.error;
    let errorMessage = 'An unknown error occurred.';
    
    if (error) {
        switch (error.code) {
            case error.MEDIA_ERR_ABORTED:
                errorMessage = 'Video playback was aborted.';
                break;
            case error.MEDIA_ERR_NETWORK:
                errorMessage = 'A network error caused the video download to fail.';
                break;
            case error.MEDIA_ERR_DECODE:
                errorMessage = 'The video playback was aborted due to a corruption problem or because the video used features your browser did not support.';
                break;
            case error.MEDIA_ERR_SRC_NOT_SUPPORTED:
                errorMessage = 'The video could not be loaded, either because the server or network failed or because the format is not supported.';
                break;
        }
    }
    
    showVideoError(errorMessage);
}

function showVideoError(message) {
    // Remove existing error if any
    const existingError = document.querySelector('.video-error');
    if (existingError) existingError.remove();
    
    const wrapper = document.querySelector('.video-wrapper');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'video-error';
    errorDiv.innerHTML = `
        <div class="video-error-icon">⚠️</div>
        <div class="video-error-title">Playback Error</div>
        <div class="video-error-message">${message}</div>
        <div class="video-error-actions">
            <button class="btn-error-action btn-error-retry" onclick="retryVideo()">Retry</button>
            <button class="btn-error-action btn-error-skip" onclick="skipToNext()">Skip to Next</button>
        </div>
    `;
    wrapper.appendChild(errorDiv);
}

function retryVideo() {
    const errorDiv = document.querySelector('.video-error');
    if (errorDiv) errorDiv.remove();
    
    if (appState.currentVideo) {
        elements.videoPlayer.load();
        elements.videoPlayer.play().catch(() => {});
    }
}

function skipToNext() {
    const errorDiv = document.querySelector('.video-error');
    if (errorDiv) errorDiv.remove();

    scrollPlayerOnNextPlay = true;
    playNextInQueue();
}

// Make functions globally accessible for onclick handlers
window.retryVideo = retryVideo;
window.skipToNext = skipToNext;

// Update Player Buttons
function updatePlayerButtons() {
    if (!appState.currentVideo) return;
    
    const isLiked = appState.liked.has(appState.currentVideo.id);
    const isFavorite = appState.favorites.has(appState.currentVideo.id);
    
    elements.btnLike.classList.toggle('active', isLiked);
    elements.btnFavorite.classList.toggle('active', isFavorite);
}

// Toggle Like
function toggleLike() {
    if (!appState.currentVideo) return;
    
    const id = appState.currentVideo.id;
    if (appState.liked.has(id)) {
        appState.liked.delete(id);
    } else {
        appState.liked.add(id);
    }
    
    updatePlayerButtons();
    saveState();
    renderBrowseContent();
}

// Toggle Like by ID
function toggleLikeById(id) {
    if (appState.liked.has(id)) {
        appState.liked.delete(id);
    } else {
        appState.liked.add(id);
    }
    saveState();
}

// Toggle Favorite
function toggleFavorite() {
    if (!appState.currentVideo) return;
    
    const id = appState.currentVideo.id;
    if (appState.favorites.has(id)) {
        appState.favorites.delete(id);
    } else {
        appState.favorites.add(id);
    }
    
    updatePlayerButtons();
    updateFavoritesCount();
    saveState();
    renderFavorites();
    renderBrowseContent();
}

// Toggle Favorite by ID
function toggleFavoriteById(id) {
    if (appState.favorites.has(id)) {
        appState.favorites.delete(id);
    } else {
        appState.favorites.add(id);
    }
    saveState();
}

// Update Favorites Count
function updateFavoritesCount() {
    elements.favoritesCount.textContent = appState.favorites.size;
}

// Add to Queue
function addToQueue(item) {
    // Check if already in queue
    if (appState.queue.some(q => q.id === item.id)) {
        return;
    }
    
    appState.queue.push(item);
    saveState();
    renderQueue();
    updateURL();
}

// Remove from Queue
function removeFromQueue(index) {
    appState.queue.splice(index, 1);
    saveState();
    renderQueue();
    updateURL();
}

// Render Queue
function renderQueue() {
    elements.queueCount.textContent = `${appState.queue.length} ${appState.queue.length === 1 ? 'item' : 'items'}`;
    
    if (appState.queue.length === 0) {
        elements.queueEmpty.style.display = 'block';
        elements.queueContainer.innerHTML = '';
        return;
    }
    
    elements.queueEmpty.style.display = 'none';
    elements.queueContainer.innerHTML = '';
    
    appState.queue.forEach((item, index) => {
        const queueItem = createQueueItem(item, index);
        elements.queueContainer.appendChild(queueItem);
    });
}

// Create Queue Item Element
function createQueueItem(item, index) {
    const div = document.createElement('div');
    div.className = 'queue-item';
    div.draggable = true;
    div.dataset.index = index;
    div.dataset.id = item.id;
    
    const thumbnailUrl = item.thumbnail || 'https://via.placeholder.com/300x169?text=No+Image';
    const placeholderUrl = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="120" height="68"%3E%3Crect fill="%231a1a1a"/%3E%3C/svg%3E';
    
  div.innerHTML = `
    <div class="queue-item-drag-handle">☰</div>
    <div class="queue-position">#${index + 1}</div>
    <img data-src="${thumbnailUrl}" src="${placeholderUrl}" alt="${item.title}" class="queue-item-thumbnail lazy" onerror="this.src='https://via.placeholder.com/300x169?text=No+Image'">
    <div class="queue-item-info">
            <div class="queue-item-title">${item.title}</div>
            <div class="queue-item-meta">${item.year ? item.year + ' • ' : ''}${item.type === 'tv' ? 'TV Show' : 'Movie'}</div>
        </div>
        <div class="queue-item-actions">
            <button class="queue-item-btn" data-action="play" title="Play Now">▶️</button>
            <button class="queue-item-btn" data-action="remove" title="Remove">✕</button>
        </div>
    `;
    
    // Event listeners
    div.querySelector('[data-action="play"]').addEventListener('click', (e) => {
        e.stopPropagation();
        playVideo(item);
        // Remove from queue if playing
        removeFromQueue(index);
    });
    
    div.querySelector('[data-action="remove"]').addEventListener('click', (e) => {
        e.stopPropagation();
        removeFromQueue(index);
    });
    
    // Set up lazy loading for queue thumbnail
    const img = div.querySelector('.lazy');
    if (img) {
        observeImage(img);
    }
    
    return div;
}

// Setup Drag and Drop
function setupDragAndDrop() {
    let draggedElement = null;
    let draggedIndex = null;
    
    // Drag start
    document.addEventListener('dragstart', (e) => {
        if (e.target.closest('.queue-item')) {
            draggedElement = e.target.closest('.queue-item');
            draggedIndex = parseInt(draggedElement.dataset.index);
            draggedElement.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/html', draggedElement.innerHTML);
        }
    });
    
    // Drag end
    document.addEventListener('dragend', (e) => {
        if (draggedElement) {
            draggedElement.classList.remove('dragging');
            document.querySelectorAll('.queue-item').forEach(item => {
                item.classList.remove('drag-over');
            });
            draggedElement = null;
            draggedIndex = null;
        }
    });
    
    // Drag over
    document.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        
        const target = e.target.closest('.queue-item');
        if (target && target !== draggedElement) {
            target.classList.add('drag-over');
        }
    });
    
    // Drag leave
    document.addEventListener('dragleave', (e) => {
        const target = e.target.closest('.queue-item');
        if (target) {
            target.classList.remove('drag-over');
        }
    });
    
    // Drop
    document.addEventListener('drop', (e) => {
        e.preventDefault();
        
        const target = e.target.closest('.queue-item');
        if (target && draggedElement && target !== draggedElement) {
            const targetIndex = parseInt(target.dataset.index);
            
            // Reorder queue
            const item = appState.queue[draggedIndex];
            appState.queue.splice(draggedIndex, 1);
            appState.queue.splice(targetIndex, 0, item);
            
            saveState();
            renderQueue();
        }
        
        // Clean up
        document.querySelectorAll('.queue-item').forEach(item => {
            item.classList.remove('drag-over');
        });
    });
}

// Play Next in Queue
function playNextInQueue() {
    // Mark as completed and clear progress
    if (appState.currentVideo) {
        addToWatchHistory(appState.currentVideo, 100);
        clearVideoProgress(appState.currentVideo.id);
        
        // Handle repeat one
        if (appState.repeatMode === 'one') {
            playVideo(appState.currentVideo);
            return;
        }
        
        // Handle repeat all
        if (appState.repeatMode === 'all' && appState.queue.length === 0 && appState.currentVideo) {
            // Queue is empty, add current back to queue
            appState.queue.push(appState.currentVideo);
        }
    }
    
    if (appState.queue.length > 0) {
        const nextItem = appState.queue.shift();
        scrollPlayerOnNextPlay = true;
        playVideo(nextItem);
        
        // If repeat all, add to end of queue
        if (appState.repeatMode === 'all') {
            appState.queue.push(nextItem);
        }
        
        saveState();
        renderQueue();
    }
}

function toggleShuffle() {
    appState.shuffleMode = !appState.shuffleMode;
    elements.btnShuffle.classList.toggle('active', appState.shuffleMode);
    
    if (appState.shuffleMode && appState.queue.length > 0) {
        // Shuffle the queue
        for (let i = appState.queue.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [appState.queue[i], appState.queue[j]] = [appState.queue[j], appState.queue[i]];
        }
        renderQueue();
        saveState();
    }
    
    localStorage.setItem('shuffleMode', appState.shuffleMode);
}

function cycleRepeatMode() {
    const modes = ['off', 'all', 'one'];
    const currentIndex = modes.indexOf(appState.repeatMode);
    const nextIndex = (currentIndex + 1) % modes.length;
    appState.repeatMode = modes[nextIndex];
    
    updateRepeatButton();
    localStorage.setItem('repeatMode', appState.repeatMode);
}

function updateRepeatButton() {
    const icons = {
        'off': '🔁',
        'all': '🔁',
        'one': '🔂'
    };
    
    const titles = {
        'off': 'Repeat Off',
        'all': 'Repeat All',
        'one': 'Repeat One'
    };
    
    elements.repeatIcon.textContent = icons[appState.repeatMode];
    elements.btnRepeat.title = titles[appState.repeatMode];
    elements.btnRepeat.classList.toggle('active', appState.repeatMode !== 'off');
}

function toggleAutoPlay() {
    appState.autoPlayNext = !appState.autoPlayNext;
    elements.btnAutoPlay.classList.toggle('active', appState.autoPlayNext);
    elements.btnAutoPlay.title = appState.autoPlayNext ? 'Auto-play Next: ON' : 'Auto-play Next: OFF';
    localStorage.setItem('autoPlayNext', appState.autoPlayNext);
}

function clearQueue() {
    if (appState.queue.length === 0) return;
    
    if (confirm(`Clear all ${appState.queue.length} items from queue?`)) {
        appState.queue = [];
        saveState();
        renderQueue();
        updateURL();
    }
}

function toggleCompactQueue() {
    appState.compactQueue = !appState.compactQueue;
    elements.btnCompactQueue.classList.toggle('active', appState.compactQueue);
    elements.queueContainer.classList.toggle('compact', appState.compactQueue);
    localStorage.setItem('compactQueue', appState.compactQueue);
}

// Render Favorites
function renderFavorites() {
    if (appState.favorites.size === 0) {
        elements.favoritesContent.innerHTML = '<div class="favorites-empty"><p>No favorites yet. Start liking videos!</p></div>';
        return;
    }
    
    elements.favoritesContent.innerHTML = '';
    
    const favoritesList = Array.from(appState.favorites)
        .map(id => appState.allContent.find(item => item.id === id))
        .filter(item => item !== undefined);
    
    favoritesList.forEach(item => {
        const contentItem = createContentItem(item);
        elements.favoritesContent.appendChild(contentItem);
    });
}

// Initialize on load
document.addEventListener('DOMContentLoaded', init);
