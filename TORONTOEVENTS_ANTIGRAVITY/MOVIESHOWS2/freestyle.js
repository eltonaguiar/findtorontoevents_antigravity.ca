/**
 * Freestyle Search Module for MOVIESHOWS2
 * Ported from MOVIESHOWS3 — adds YouTube/TMDB/Dailymotion search overlay
 * Searches via PHP proxy with Piped/Invidious/Dailymotion client-side fallbacks
 */

// ── State ─────────────────────────────────────────────────────────
let freestyleResults = [];
let freestyleSearching = false;

// ── Escape HTML helper ────────────────────────────────────────────
const _fsEscDiv = document.createElement('div');
function _fsEscape(text) {
    _fsEscDiv.textContent = text || '';
    return _fsEscDiv.innerHTML;
}

// ── Open/Close Overlay ────────────────────────────────────────────
function openFreestyle() {
    document.getElementById('freestyleOverlay').classList.add('active');
    setTimeout(() => document.getElementById('freestyleSearchInput').focus(), 200);
}

function closeFreestyle() {
    document.getElementById('freestyleOverlay').classList.remove('active');
}

function updateFreestylePlaceholder() {
    const type = document.getElementById('freestyleType').value;
    const input = document.getElementById('freestyleSearchInput');
    input.placeholder = type === 'youtube'
        ? 'Search YouTube: music videos, tutorials, vlogs, anything...'
        : 'Try: sci-fi thriller, anime, Korean drama, horror 2025...';
}

// ── Client-Side YouTube Search (Piped/Invidious/Dailymotion) ─────
async function clientSideYouTubeSearch(query) {
    var pipedHosts = [
        'https://pipedapi.kavin.rocks', 'https://pipedapi-libre.kavin.rocks',
        'https://pipedapi.adminforge.de', 'https://pipedapi.leptons.xyz',
        'https://piped-api.privacy.com.de', 'https://pipedapi.nosebs.ru',
        'https://pipedapi.drgns.space', 'https://pipedapi.owo.si',
        'https://piped-api.codespace.cz', 'https://pipedapi.reallyaweso.me',
        'https://pipedapi.darkness.services', 'https://pipedapi.orangenet.cc'
    ];
    for (var s = pipedHosts.length - 1; s > 0; s--) {
        var r = Math.floor(Math.random() * (s + 1));
        var t = pipedHosts[s]; pipedHosts[s] = pipedHosts[r]; pipedHosts[r] = t;
    }
    for (var i = 0; i < Math.min(5, pipedHosts.length); i++) {
        try {
            var resp = await fetch(pipedHosts[i] + '/search?q=' + encodeURIComponent(query) + '&filter=videos', { signal: AbortSignal.timeout(5000) });
            if (!resp.ok) continue;
            var data = await resp.json();
            if (data && data.items && data.items.length > 0) {
                var results = parsePipedResults(data.items);
                if (results.length > 0) return { success: true, results: results, total_results: results.length, source: 'youtube' };
            }
        } catch(e) { continue; }
    }

    var invHosts = [
        'https://inv.nadeko.net', 'https://invidious.fdn.fr', 'https://vid.puffyan.us',
        'https://invidious.privacydev.net', 'https://invidious.lunar.icu',
        'https://iv.ggtyler.dev', 'https://invidious.nerdvpn.de'
    ];
    for (var j = 0; j < Math.min(4, invHosts.length); j++) {
        try {
            var resp2 = await fetch(invHosts[j] + '/api/v1/search?q=' + encodeURIComponent(query) + '&type=video', { signal: AbortSignal.timeout(5000) });
            if (!resp2.ok) continue;
            var data2 = await resp2.json();
            if (data2 && Array.isArray(data2) && data2.length > 0) {
                var results2 = parseInvidiousResults(data2);
                if (results2.length > 0) return { success: true, results: results2, total_results: results2.length, source: 'youtube' };
            }
        } catch(e) { continue; }
    }

    try {
        var dmResp = await fetch('https://api.dailymotion.com/videos?search=' + encodeURIComponent(query) + '&fields=id,title,description,thumbnail_url,duration,owner.screenname,views_total&limit=20&sort=relevance', { signal: AbortSignal.timeout(6000) });
        if (dmResp.ok) {
            var dmData = await dmResp.json();
            if (dmData && dmData.list && dmData.list.length > 0) {
                var dmResults = parseDailymotionResults(dmData.list);
                if (dmResults.length > 0) return { success: true, results: dmResults, total_results: dmResults.length, source: 'dailymotion' };
            }
        }
    } catch(e) {}

    return null;
}

function parsePipedResults(items) {
    var results = [];
    items.slice(0, 20).forEach(function(item) {
        if (!item.url) return;
        var vid = '';
        var m = item.url.match(/[?&]v=([a-zA-Z0-9_-]{11})/);
        if (m) vid = m[1];
        if (!vid && item.thumbnail) { var m2 = item.thumbnail.match(/\/vi\/([a-zA-Z0-9_-]{11})\//); if (m2) vid = m2[1]; }
        if (!vid) return;
        var dur = item.duration > 0 ? Math.floor(item.duration/60) + ':' + String(item.duration % 60).padStart(2, '0') : '';
        results.push({
            title: item.title || 'Untitled', description: item.shortDescription || item.uploaderName || '',
            trailer_id: vid, thumbnail: 'https://img.youtube.com/vi/' + vid + '/hqdefault.jpg',
            _isYouTube: true, _channel: item.uploaderName || '', _duration: dur
        });
    });
    return results;
}

function parseInvidiousResults(items) {
    var results = [];
    items.slice(0, 20).forEach(function(item) {
        if (!item.videoId) return;
        var dur = item.lengthSeconds > 0 ? Math.floor(item.lengthSeconds / 60) + ':' + String(item.lengthSeconds % 60).padStart(2, '0') : '';
        results.push({
            title: item.title || 'Untitled', description: item.description || item.author || '',
            trailer_id: item.videoId, thumbnail: 'https://img.youtube.com/vi/' + item.videoId + '/hqdefault.jpg',
            _isYouTube: true, _channel: item.author || '', _duration: dur,
            _views: item.viewCount ? item.viewCount.toLocaleString() + ' views' : ''
        });
    });
    return results;
}

function parseDailymotionResults(items) {
    var results = [];
    items.forEach(function(item) {
        if (!item.id) return;
        var dur = item.duration > 0 ? Math.floor(item.duration / 60) + ':' + String(item.duration % 60).padStart(2, '0') : '';
        results.push({
            title: item.title || 'Untitled', description: item.description || '',
            trailer_id: item.id, thumbnail: item.thumbnail_url || '',
            _isDailymotion: true, _isYouTube: false,
            _channel: (item['owner.screenname'] || ''), _duration: dur,
            _views: item.views_total ? item.views_total.toLocaleString() + ' views' : ''
        });
    });
    return results;
}

function localDatabaseSearch(query) {
    if (typeof appState === 'undefined' || !appState.allContent) return null;
    var q = query.toLowerCase().trim();
    var words = q.split(/\s+/);
    var matches = [];

    appState.allContent.forEach(function(movie) {
        var title = (movie.title || '').toLowerCase();
        var desc = (movie.description || '').toLowerCase();
        var score = 0;
        if (title === q) score += 100;
        else if (title.includes(q)) score += 50;
        else if (words.every(function(w) { return title.includes(w); })) score += 30;
        else { words.forEach(function(w) { if (title.includes(w)) score += 10; if (desc.includes(w)) score += 3; }); }
        if (score > 0) matches.push({ movie: movie, score: score });
    });

    matches.sort(function(a, b) { return b.score - a.score; });
    var top = matches.slice(0, 20);
    if (top.length === 0) return null;

    var results = top.map(function(m) {
        return {
            title: m.movie.title, description: m.movie.description || '',
            trailer_id: m.movie.videoUrl ? m.movie.id : null,
            thumbnail: m.movie.thumbnail || '',
            _isYouTube: false, _isMS2Content: true,
            _channel: '', _duration: '', release_year: m.movie.year
        };
    });

    return { success: true, results: results, total_results: matches.length, source: 'local_database' };
}

// ── Main Search Function ──────────────────────────────────────────
async function doFreestyleSearch() {
    const query = document.getElementById('freestyleSearchInput').value.trim();
    const type = document.getElementById('freestyleType').value;
    const resultsDiv = document.getElementById('freestyleResults');

    if (!query || freestyleSearching) return;
    freestyleSearching = true;

    const isYouTube = type === 'youtube';
    const searchLabel = isYouTube ? 'YouTube' : 'TMDB';

    resultsDiv.innerHTML = `<div style="text-align:center;padding:60px 20px;color:rgba(255,255,255,0.6);">
        <div style="width:40px;height:40px;border:3px solid rgba(255,255,255,0.2);border-top-color:#f59e0b;border-radius:50%;animation:fsSpin 0.8s linear infinite;margin:0 auto 16px;"></div>
        <div>Searching ${searchLabel} for "${_fsEscape(query)}"...</div>
    </div>`;

    try {
        var data = null;

        // PRIMARY: PHP proxy
        try {
            var url = 'https://findtorontoevents.ca/MOVIESHOWS2/api/freestyle-search.php?q=' + encodeURIComponent(query) + '&type=' + (isYouTube ? 'youtube' : type);
            var resp = await fetch(url, { signal: AbortSignal.timeout(15000) });
            var parsed = await resp.json();
            if (parsed && parsed.success) data = parsed;
        } catch(e) {}

        if (!data && isYouTube) data = await clientSideYouTubeSearch(query);
        if (!data && isYouTube) data = localDatabaseSearch(query);

        if (!data || !data.success) {
            var ytLink = isYouTube ? '<br><br><a href="https://www.youtube.com/results?search_query=' + encodeURIComponent(query) + '" target="_blank" style="display:inline-block;background:#ff0000;color:#fff;padding:10px 24px;border-radius:8px;text-decoration:none;font-weight:700;">Search on YouTube.com</a>' : '';
            resultsDiv.innerHTML = '<div style="text-align:center;padding:60px 20px;color:rgba(255,255,255,0.6);">Search failed.' + ytLink + '</div>';
            freestyleSearching = false;
            return;
        }

        freestyleResults = data.results || [];
        if (freestyleResults.length === 0) {
            resultsDiv.innerHTML = '<div style="text-align:center;padding:60px 20px;color:rgba(255,255,255,0.6);">No results found. Try different keywords.</div>';
            freestyleSearching = false;
            return;
        }

        var sourceLabel = data.source === 'dailymotion' ? 'Dailymotion' : (data.source === 'local_database' ? 'Our Library' : (isYouTube ? 'YouTube' : 'TMDB'));
        var html = `<div style="margin-bottom:12px;color:rgba(255,255,255,0.4);font-size:13px;">${freestyleResults.length} results from ${sourceLabel}</div>`;
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">';

        freestyleResults.forEach((item, i) => {
            const isYt = item._isYouTube;
            const isDm = item._isDailymotion;
            const videoId = item.trailer_id;
            const thumb = isDm ? (item.thumbnail || '') : (isYt && videoId ? `https://img.youtube.com/vi/${videoId}/hqdefault.jpg` : (item.thumbnail || ''));
            const hasTrailer = !!videoId;

            let badge = isYt ? '<span style="background:#ff0000;color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">YouTube</span>'
                : isDm ? '<span style="background:#0062ff;color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">Dailymotion</span>'
                : '<span style="background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">FREESTYLE</span>';
            if (item._channel) badge += ` <span style="color:rgba(255,255,255,0.4);font-size:11px;">${_fsEscape(item._channel)}</span>`;

            html += `
            <div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);border-radius:12px;overflow:hidden;cursor:pointer;transition:border-color 0.2s,transform 0.2s;"
                 onmouseenter="this.style.borderColor='rgba(245,158,11,0.4)';this.style.transform='translateY(-2px)'"
                 onmouseleave="this.style.borderColor='rgba(255,255,255,0.08)';this.style.transform='none'">
                <div style="position:relative;aspect-ratio:16/9;overflow:hidden;background:#111;" onclick="${hasTrailer ? `playFreestyleTrailer(${i})` : ''}">
                    ${thumb ? `<img src="${thumb}" alt="" style="width:100%;height:100%;object-fit:cover;" loading="lazy" onerror="this.style.display='none'">` : ''}
                    ${hasTrailer ? `<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity 0.2s;background:rgba(0,0,0,0.4);" onmouseenter="this.style.opacity='1'" onmouseleave="this.style.opacity='0'"><span style="font-size:48px;">▶</span></div>` : ''}
                </div>
                <div style="padding:12px 14px;">
                    <div style="font-size:14px;font-weight:700;color:#fff;margin-bottom:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${_fsEscape(item.title)}</div>
                    <div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:6px;">
                        ${badge}
                        ${item._duration ? `<span style="color:rgba(255,255,255,0.4);font-size:11px;">${item._duration}</span>` : ''}
                    </div>
                    <div style="font-size:12px;color:rgba(255,255,255,0.35);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${_fsEscape(item.description || '')}</div>
                </div>
                <div style="display:flex;gap:8px;padding:8px 14px 12px;">
                    ${hasTrailer ? `<button onclick="event.stopPropagation();playFreestyleTrailer(${i})" style="flex:1;padding:8px;border:none;border-radius:8px;background:rgba(245,158,11,0.15);color:#f59e0b;font-size:12px;font-weight:600;cursor:pointer;">▶ Play</button>` : ''}
                    ${hasTrailer && isYt ? `<button onclick="event.stopPropagation();queueFreestyleItem(${i},this)" style="flex:1;padding:8px;border:none;border-radius:8px;background:rgba(34,197,94,0.15);color:#4ade80;font-size:12px;font-weight:600;cursor:pointer;">➕ Queue</button>` : ''}
                </div>
            </div>`;
        });

        html += '</div>';
        resultsDiv.innerHTML = html;
    } catch (err) {
        resultsDiv.innerHTML = `<div style="text-align:center;padding:60px 20px;color:rgba(255,255,255,0.6);">Error: ${err.message}</div>`;
    }
    freestyleSearching = false;
}

// ── Play Freestyle Result ─────────────────────────────────────────
function playFreestyleTrailer(index) {
    const item = freestyleResults[index];
    if (!item || !item.trailer_id) return;

    // External platforms — open in new tab
    if (item._isDailymotion) { window.open('https://www.dailymotion.com/video/' + item.trailer_id, '_blank'); return; }
    if (item._isArchive) { window.open('https://archive.org/details/' + item.trailer_id, '_blank'); return; }
    if (item._isVimeo) { window.open('https://vimeo.com/' + item.trailer_id, '_blank'); return; }

    // MS2 local content — play via MS2 player
    if (item._isMS2Content) {
        closeFreestyle();
        const found = typeof appState !== 'undefined' ? appState.allContent.find(c => c.id === item.trailer_id) : null;
        if (found && typeof playVideo === 'function') { playVideo(found); return; }
    }

    // YouTube content — play via YouTube iframe (uses motivation.js's playYouTubeVideo)
    closeFreestyle();
    if (typeof playYouTubeVideo === 'function') {
        // Update title display
        if (typeof appState !== 'undefined') {
            appState.currentVideo = {
                id: 'freestyle_' + item.trailer_id,
                title: item.title,
                description: item.description || '',
                thumbnail: item.thumbnail || '',
                _youtubeId: item.trailer_id
            };
        }
        const titleEl = document.getElementById('currentTitle');
        const descEl = document.getElementById('currentDescription');
        if (titleEl) titleEl.textContent = item.title;
        if (descEl) descEl.textContent = item.description || '';
        playYouTubeVideo(item.trailer_id);
    } else {
        // Fallback: open on YouTube
        window.open('https://www.youtube.com/watch?v=' + item.trailer_id, '_blank');
    }
}

// ── Queue Freestyle Result ────────────────────────────────────────
function queueFreestyleItem(index, btn) {
    const item = freestyleResults[index];
    if (!item || !item.trailer_id) return;

    if (typeof appState === 'undefined') return;

    const queueItem = {
        id: 'freestyle_' + item.trailer_id,
        title: item.title,
        description: item.description || '',
        thumbnail: item.thumbnail || `https://img.youtube.com/vi/${item.trailer_id}/hqdefault.jpg`,
        videoUrl: null,
        _youtubeId: item.trailer_id,
        _isFreestyle: true
    };

    if (appState.queue.some(q => q.id === queueItem.id)) {
        if (btn) { btn.textContent = 'Already queued'; btn.disabled = true; }
        return;
    }

    appState.queue.push(queueItem);
    localStorage.setItem('queue', JSON.stringify(appState.queue));
    if (typeof renderQueue === 'function') renderQueue();

    const queueCount = document.getElementById('queueCount');
    if (queueCount) queueCount.textContent = `${appState.queue.length} ${appState.queue.length === 1 ? 'item' : 'items'}`;

    if (btn) { btn.textContent = '✓ Queued'; btn.disabled = true; btn.style.background = 'rgba(34,197,94,0.25)'; }
}

// ── Inject Freestyle UI ───────────────────────────────────────────
function injectFreestyleUI() {
    // Add freestyle overlay to body
    const overlay = document.createElement('div');
    overlay.id = 'freestyleOverlay';
    overlay.className = 'freestyle-overlay';
    overlay.innerHTML = `
        <div style="position:sticky;top:0;z-index:10;background:rgba(15,15,25,0.95);backdrop-filter:blur(20px);padding:20px;border-bottom:1px solid rgba(255,255,255,0.08);">
            <button onclick="closeFreestyle()" style="position:absolute;top:16px;right:20px;width:36px;height:36px;border-radius:50%;border:1px solid rgba(255,255,255,0.2);background:rgba(255,255,255,0.1);color:white;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;">✕</button>
            <h2 style="color:white;margin:0 0 8px;font-size:20px;">🎯 Freestyle <span style="background:rgba(245,158,11,0.2);border:1px solid rgba(245,158,11,0.4);color:#f59e0b;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;animation:fsPulse 3s ease-in-out infinite;">Beta</span></h2>
            <p style="color:rgba(255,255,255,0.5);margin:0 0 16px;font-size:13px;">Search for anything — movies, TV shows, or switch to YouTube for music, vlogs, tutorials...</p>
            <div style="display:flex;gap:8px;">
                <input type="text" id="freestyleSearchInput" placeholder="Try: sci-fi thriller, anime..." style="flex:1;padding:12px 16px;border-radius:10px;border:1px solid rgba(255,255,255,0.15);background:rgba(255,255,255,0.08);color:white;font-size:14px;outline:none;" onkeydown="if(event.key==='Enter')doFreestyleSearch()">
                <select id="freestyleType" onchange="updateFreestylePlaceholder()" style="padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.15);background:rgba(255,255,255,0.08);color:white;font-size:13px;cursor:pointer;">
                    <option value="multi">All (TMDB)</option>
                    <option value="movie">Movies</option>
                    <option value="tv">TV Shows</option>
                    <option value="youtube" style="color:#ff4444;">YouTube</option>
                </select>
                <button onclick="doFreestyleSearch()" style="padding:12px 24px;border-radius:10px;border:none;background:linear-gradient(135deg,#f59e0b,#d97706);color:white;font-weight:700;cursor:pointer;font-size:14px;">Search</button>
            </div>
        </div>
        <div id="freestyleResults" style="padding:20px;overflow-y:auto;flex:1;">
            <div style="text-align:center;padding:60px 20px;color:rgba(255,255,255,0.3);">
                <div style="font-size:48px;margin-bottom:16px;">🔍</div>
                <div style="font-size:16px;">Search for anything above to get started</div>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);

    // Add freestyle filter button
    const filterBtns = document.querySelectorAll('.filter-btn');
    if (filterBtns.length > 0) {
        const lastBtn = filterBtns[filterBtns.length - 1];
        const fsBtn = document.createElement('button');
        fsBtn.className = 'filter-btn';
        fsBtn.style.cssText = 'color:#f59e0b;';
        fsBtn.innerHTML = 'Freestyle <span style="background:rgba(245,158,11,0.2);border:1px solid rgba(245,158,11,0.4);color:#f59e0b;padding:1px 6px;border-radius:8px;font-size:9px;font-weight:700;margin-left:4px;">Beta</span>';
        fsBtn.addEventListener('click', openFreestyle);
        lastBtn.parentNode.insertBefore(fsBtn, lastBtn.nextSibling);
    }

    // Add CSS
    const style = document.createElement('style');
    style.textContent = `
        .freestyle-overlay {
            position: fixed; inset: 0; z-index: 300;
            background: rgba(10, 10, 18, 0.98);
            backdrop-filter: blur(20px);
            display: none; flex-direction: column;
        }
        .freestyle-overlay.active { display: flex; }
        @keyframes fsSpin { to { transform: rotate(360deg); } }
        @keyframes fsPulse { 0%,100% { opacity:1; } 50% { opacity:0.6; } }
    `;
    document.head.appendChild(style);
}

// ── Init ──────────────────────────────────────────────────────────
function initFreestyle() {
    injectFreestyleUI();
    console.log('🎯 Freestyle search module loaded');
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(initFreestyle, 600));
} else {
    setTimeout(initFreestyle, 600);
}
