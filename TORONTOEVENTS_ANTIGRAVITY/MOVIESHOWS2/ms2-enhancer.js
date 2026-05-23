/**
 * MS2 Enhancer v1.4 — Works with Next.js React UI
 * Adds: Motivation, Freestyle, Top 50, Genre Categories, TMDB ID fix, Playlist
 * Detects actual Tailwind-styled buttons and injects matching UI.
 * v1.1: Multi-tier freestyle search (MS3 parity)
 * v1.2: Top 50 scrollable list
 * v1.3: In-feed playback (injects native scroll cards instead of overlay),
 *        playlist feature to save & mix videos into the feed
 * v1.4: Motivation auto-play chain (prompt + queue + video-end detection),
 *        gear icon filter fix (year/genre actually filter content)
 * v1.5: Freestyle + Top 50 auto-play chains,
 *        box office data fix, MS1 upgrade toast
 */
(function() {
    'use strict';

    // ════════════════════════════════════════════════════════════════
    //  TMDB GENRE ID → NAME MAPPING
    // ════════════════════════════════════════════════════════════════
    const TMDB_GENRES = {
        28:'Action',12:'Adventure',16:'Animation',35:'Comedy',80:'Crime',
        99:'Documentary',18:'Drama',10751:'Family',14:'Fantasy',36:'History',
        27:'Horror',10402:'Music',9648:'Mystery',10749:'Romance',878:'Sci-Fi',
        10770:'TV Movie',53:'Thriller',10752:'War',37:'Western',10759:'Action & Adventure',
        10762:'Kids',10763:'News',10764:'Reality',10765:'Sci-Fi & Fantasy',
        10766:'Soap',10767:'Talk',10768:'War & Politics',10110:'Fantasy',
        16:'Animation',99:'Documentary'
    };

    // ════════════════════════════════════════════════════════════════
    //  DOM DETECTION HELPERS
    // ════════════════════════════════════════════════════════════════
    function findFilterContainer() {
        const allBtns = document.querySelectorAll('button');
        for (const btn of allBtns) {
            const txt = btn.textContent.trim();
            if (/^All\s*\(/.test(txt) || /^All$/.test(txt)) {
                const parent = btn.parentElement;
                if (parent && parent.querySelectorAll('button').length >= 3) {
                    return parent;
                }
            }
        }
        return null;
    }

    function findScrollContainer() {
        const containers = document.querySelectorAll('[class*="overflow-y-scroll"]');
        for (const c of containers) {
            if (c.className.includes('snap-y')) return c;
        }
        const snapEl = document.querySelector('[class*="snap-center"]');
        return snapEl ? snapEl.parentElement : null;
    }

    function getButtonStyle(active) {
        return active
            ? 'px-3 py-1.5 rounded-full text-xs font-bold transition-all bg-white text-black shadow-lg cursor-pointer border-0'
            : 'px-3 py-1.5 rounded-full text-xs font-bold transition-all text-white/70 hover:text-white cursor-pointer border-0 bg-transparent';
    }

    // ════════════════════════════════════════════════════════════════
    //  1. TMDB GENRE FIX — MutationObserver
    // ════════════════════════════════════════════════════════════════
    function fixGenreIds(root) {
        const candidates = (root || document).querySelectorAll('button, span, div, a');
        let fixed = 0;
        for (const el of candidates) {
            if (el.children.length > 0) continue;
            const txt = el.textContent.trim();
            if (/^\d+$/.test(txt) && TMDB_GENRES[parseInt(txt)]) {
                el.textContent = TMDB_GENRES[parseInt(txt)];
                fixed++;
            }
        }
        return fixed;
    }

    function startGenreObserver() {
        fixGenreIds();
        const observer = new MutationObserver((mutations) => {
            for (const m of mutations) {
                for (const node of m.addedNodes) {
                    if (node.nodeType === 1) fixGenreIds(node);
                }
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    // ════════════════════════════════════════════════════════════════
    //  2. PLAYLIST — localStorage persistence
    // ════════════════════════════════════════════════════════════════
    const PLAYLIST_KEY = 'ms2-custom-playlist';
    function loadPlaylist() {
        try { return JSON.parse(localStorage.getItem(PLAYLIST_KEY) || '[]'); } catch { return []; }
    }
    function savePlaylist(list) {
        localStorage.setItem(PLAYLIST_KEY, JSON.stringify(list));
        updatePlaylistCount();
    }
    function addToPlaylist(item) {
        const list = loadPlaylist();
        if (list.some(p => p.id === item.id)) return false; // already saved
        list.push(item);
        savePlaylist(list);
        return true;
    }
    function removeFromPlaylist(id) {
        const list = loadPlaylist().filter(p => p.id !== id);
        savePlaylist(list);
        return list;
    }
    function updatePlaylistCount() {
        const btn = document.getElementById('ms2BtnPlaylist');
        if (btn) {
            const n = loadPlaylist().length;
            btn.textContent = n > 0 ? '\u{1F4CB} Playlist (' + n + ')' : '\u{1F4CB} Playlist';
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  2.5 MOTIVATION AUTO-PLAY SYSTEM
    // ════════════════════════════════════════════════════════════════
    let _motAutoPlayActive = false;
    let _motQueue = [];
    let _motQueueIndex = 0;
    let _motPromptShown = false;
    let _motEndDebounce = 0;

    function showMotToast(msg) {
        var t = document.createElement('div');
        t.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.9);color:white;padding:12px 24px;border-radius:12px;font-size:15px;font-weight:600;z-index:9999;pointer-events:none;transition:opacity 0.3s;';
        t.textContent = msg;
        document.body.appendChild(t);
        setTimeout(function() { t.style.opacity = '0'; setTimeout(function() { t.remove(); }, 300); }, 2000);
    }

    function showMotivationPrompt(currentVideoId) {
        _motPromptShown = true;
        if (document.getElementById('ms2-mot-prompt')) return;
        var banner = document.createElement('div');
        banner.id = 'ms2-mot-prompt';
        banner.innerHTML =
            '<div class="mot-prompt-text">Auto-play more motivation videos after this one?</div>' +
            '<div class="mot-prompt-actions">' +
                '<button class="mot-prompt-yes">Yes, keep going!</button>' +
                '<button class="mot-prompt-no">No thanks</button>' +
            '</div>';
        document.body.appendChild(banner);
        requestAnimationFrame(function() { banner.classList.add('active'); });
        banner.querySelector('.mot-prompt-yes').addEventListener('click', function() {
            enableMotivationAutoPlay(currentVideoId);
            banner.remove();
        });
        banner.querySelector('.mot-prompt-no').addEventListener('click', function() {
            banner.remove();
        });
        setTimeout(function() {
            var el = document.getElementById('ms2-mot-prompt');
            if (el) el.remove();
        }, 15000);
    }

    function enableMotivationAutoPlay(currentVideoId) {
        var allVideos = [];
        for (var ci = 0; ci < MOTIVATION_CHANNELS.length; ci++) {
            var ch = MOTIVATION_CHANNELS[ci];
            for (var vi = 0; vi < ch.videos.length; vi++) {
                var v = ch.videos[vi];
                if (v.id !== currentVideoId) {
                    allVideos.push({ id: v.id, title: v.title, channel: ch.channel });
                }
            }
        }
        // Shuffle queue
        for (var i = allVideos.length - 1; i > 0; i--) {
            var j = Math.floor(Math.random() * (i + 1));
            var tmp = allVideos[i]; allVideos[i] = allVideos[j]; allVideos[j] = tmp;
        }
        _motQueue = allVideos;
        _motQueueIndex = 0;
        _motAutoPlayActive = true;
        showMotivationIndicator();
        showMotToast('Motivation auto-play ON \u2014 ' + _motQueue.length + ' videos queued');
        console.log('[MS2 Enhancer] Motivation auto-play enabled, ' + _motQueue.length + ' videos queued');
    }

    function showMotivationIndicator() {
        var ind = document.getElementById('ms2-mot-indicator');
        if (!ind) {
            ind = document.createElement('div');
            ind.id = 'ms2-mot-indicator';
            document.body.appendChild(ind);
        }
        var remaining = _motQueue.length - _motQueueIndex;
        ind.innerHTML = '<span class="mot-ind-text">Motivation: ' + remaining + ' remaining</span>' +
            '<button class="mot-ind-stop" title="Stop auto-play">&#10005;</button>';
        ind.querySelector('.mot-ind-stop').addEventListener('click', function() { cancelMotivationAutoPlay(); });
    }

    function cancelMotivationAutoPlay() {
        _motAutoPlayActive = false;
        _motQueue = [];
        _motQueueIndex = 0;
        var ind = document.getElementById('ms2-mot-indicator');
        if (ind) ind.remove();
        console.log('[MS2 Enhancer] Motivation auto-play cancelled');
    }

    function playNextMotivation() {
        if (!_motAutoPlayActive || _motQueueIndex >= _motQueue.length) {
            cancelMotivationAutoPlay();
            showMotToast('Motivation playlist complete!');
            return;
        }
        var next = _motQueue[_motQueueIndex];
        _motQueueIndex++;
        showMotivationIndicator();
        playInFeed(next.id, next.title, next.channel, 'Motivation');
    }

    function isCurrentSlideEnhancer() {
        var sc = findScrollContainer();
        if (!sc) return false;
        var slides = sc.querySelectorAll(':scope > [class*="snap-center"]');
        var scrollTop = sc.scrollTop;
        var height = sc.clientHeight;
        var idx = Math.round(scrollTop / height);
        var slide = slides[idx];
        return slide && slide.dataset.injectedByEnhancer === '1';
    }

    function setupVideoEndListener() {
        // Handles motivation auto-play chain (video-end detection).
        // Freestyle and Top 50 don't need this — they inject all cards at once.
        window.addEventListener('message', function(event) {
            if (!event.origin.includes('youtube.com')) return;
            if (!_motAutoPlayActive) return;
            try {
                var data = event.data;
                if (typeof data === 'string') data = JSON.parse(data);
                var ended = false;
                if (data.event === 'onStateChange' && data.info === 0) ended = true;
                if (data.info && typeof data.info === 'object' && data.info.playerState === 0) ended = true;
                if (ended && isCurrentSlideEnhancer()) {
                    var now = Date.now();
                    if (now - _motEndDebounce < 3000) return;
                    _motEndDebounce = now;
                    console.log('[MS2 Enhancer] Motivation video ended, playing next in 1.5s...');
                    setTimeout(function() { playNextMotivation(); }, 1500);
                }
            } catch(e) {}
        });
    }

    // ════════════════════════════════════════════════════════════════
    //  2.6 FREESTYLE AUTO-PLAY SYSTEM
    // ════════════════════════════════════════════════════════════════
    let _fsAutoPlayActive = false;
    let _fsQueue = [];
    let _fsQueueIndex = 0;
    let _fsPromptShown = false;
    let _fsEndDebounce = 0;
    let _fsLastQuery = '';

    function showFreestylePrompt(currentVideoId) {
        _fsPromptShown = true;
        if (document.getElementById('ms2-fs-prompt')) return;
        var banner = document.createElement('div');
        banner.id = 'ms2-fs-prompt';
        var queryLabel = _fsLastQuery.length > 30 ? _fsLastQuery.substring(0, 30) + '...' : _fsLastQuery;
        banner.innerHTML =
            '<div class="fs-prompt-text">Keep playing &ldquo;' + queryLabel + '&rdquo; results?</div>' +
            '<div class="fs-prompt-actions">' +
                '<button class="fs-prompt-yes">Yes, keep going!</button>' +
                '<button class="fs-prompt-no">No thanks</button>' +
            '</div>';
        document.body.appendChild(banner);
        requestAnimationFrame(function() { banner.classList.add('active'); });
        banner.querySelector('.fs-prompt-yes').addEventListener('click', function() {
            enableFreestyleAutoPlay(currentVideoId);
            banner.remove();
        });
        banner.querySelector('.fs-prompt-no').addEventListener('click', function() {
            banner.remove();
        });
        setTimeout(function() {
            var el = document.getElementById('ms2-fs-prompt');
            if (el) el.remove();
        }, 15000);
    }

    function enableFreestyleAutoPlay(currentVideoId) {
        var queue = [];
        for (var i = 0; i < _fsResults.length; i++) {
            var item = _fsResults[i];
            if (item.type === 'youtube' && item.id && item.id !== currentVideoId) {
                queue.push({ id: item.id, title: item.title, channel: item._channel || 'YouTube' });
            }
        }
        if (!queue.length) {
            showMotToast('No more results to play');
            return;
        }

        _fsAutoPlayActive = true;

        // Find the currently visible slide so we inject AFTER it (don't skip current video)
        var sc = findScrollContainer();
        var currentSlide = null;
        if (sc) {
            var allSlides = sc.querySelectorAll(':scope > [class*="snap-center"]');
            var scrollTop = sc.scrollTop;
            var slideH = sc.clientHeight;
            var visibleIdx = Math.round(scrollTop / slideH);
            if (visibleIdx >= 0 && visibleIdx < allSlides.length) {
                currentSlide = allSlides[visibleIdx];
            }
        }

        // Inject all cards after the current position — user scrolls into them naturally
        var lastSlide = currentSlide;
        for (var i = 0; i < queue.length; i++) {
            var newSlide = injectFeedCard(queue[i].id, queue[i].title, queue[i].channel, 'Freestyle', lastSlide);
            if (newSlide) lastSlide = newSlide;
        }

        _fsAutoPlayActive = false; // No ongoing chain needed — all cards are in feed
        showMotToast(queue.length + ' Freestyle results queued \u2014 scroll down when ready');
        console.log('[MS2 Enhancer] Freestyle: injected ' + queue.length + ' videos after current position');
    }

    // ════════════════════════════════════════════════════════════════
    //  2.7 TOP 50 AUTO-PLAY SYSTEM
    // ════════════════════════════════════════════════════════════════
    let _topAutoPlayActive = false;
    let _topQueue = [];
    let _topQueueIndex = 0;
    let _topPromptShown = false;
    let _topEndDebounce = 0;
    let _topLastSection = '';

    function showTopPrompt(currentVideoId) {
        _topPromptShown = true;
        if (document.getElementById('ms2-top-prompt')) return;
        var banner = document.createElement('div');
        banner.id = 'ms2-top-prompt';
        banner.innerHTML =
            '<div class="top-prompt-text">Keep playing Top 50 (' + _topLastSection + ')?</div>' +
            '<div class="top-prompt-actions">' +
                '<button class="top-prompt-yes">Yes, keep going!</button>' +
                '<button class="top-prompt-no">No thanks</button>' +
            '</div>';
        document.body.appendChild(banner);
        requestAnimationFrame(function() { banner.classList.add('active'); });
        banner.querySelector('.top-prompt-yes').addEventListener('click', function() {
            enableTopAutoPlay(currentVideoId);
            banner.remove();
        });
        banner.querySelector('.top-prompt-no').addEventListener('click', function() {
            banner.remove();
        });
        setTimeout(function() {
            var el = document.getElementById('ms2-top-prompt');
            if (el) el.remove();
        }, 15000);
    }

    function enableTopAutoPlay(currentVideoId) {
        // _topQueue is already populated when the video was clicked
        var queue = [];
        for (var i = 0; i < _topQueue.length; i++) {
            if (_topQueue[i].id !== currentVideoId) {
                queue.push(_topQueue[i]);
            }
        }
        if (!queue.length) {
            showMotToast('No more titles to play');
            return;
        }

        _topAutoPlayActive = true;

        // Find the currently visible slide so we inject AFTER it (don't skip current video)
        var sc = findScrollContainer();
        var currentSlide = null;
        if (sc) {
            var allSlides = sc.querySelectorAll(':scope > [class*="snap-center"]');
            var scrollTop = sc.scrollTop;
            var slideH = sc.clientHeight;
            var visibleIdx = Math.round(scrollTop / slideH);
            if (visibleIdx >= 0 && visibleIdx < allSlides.length) {
                currentSlide = allSlides[visibleIdx];
            }
        }

        // Inject all cards after the current position — user scrolls into them naturally
        var lastSlide = currentSlide;
        for (var i = 0; i < queue.length; i++) {
            var newSlide = injectFeedCard(queue[i].id, queue[i].title, queue[i].source, 'Top 50', lastSlide);
            if (newSlide) lastSlide = newSlide;
        }

        _topAutoPlayActive = false; // No ongoing chain needed — all cards are in feed
        showMotToast(queue.length + ' Top 50 titles queued \u2014 scroll down when ready');
        console.log('[MS2 Enhancer] Top 50: injected ' + queue.length + ' videos after current position');
    }

    // ════════════════════════════════════════════════════════════════
    //  3. MOTIVATION CHANNELS DATA
    // ════════════════════════════════════════════════════════════════
    const MOTIVATION_CHANNELS = [
        { channel: 'Motiversity', videos: [
            { id: 'wnHW6o8WMas', title: 'NO EXCUSES - Best Motivational Video', dur: '10:15' },
            { id: 'mgmVOAJgBKI', title: 'WINNERS MINDSET - Powerful Speech', dur: '11:32' },
            { id: 'tbnzAVRZ9Xc', title: 'THIS IS YOUR SIGN - Best Speech', dur: '13:45' },
            { id: 'qzOFs4hSG5I', title: 'THE MINDSET OF A WINNER', dur: '15:20' },
            { id: 'Ur_kBBVKauw', title: 'PROVE THEM WRONG', dur: '12:08' },
            { id: '1XHfiEoNQBI', title: 'NEVER GIVE UP - Best Speech', dur: '14:52' },
            { id: 'k9zTr2MAFRg', title: 'RISE UP - Powerful Motivation', dur: '11:40' },
            { id: 'pxBQLFLei70', title: 'MAKE IT HAPPEN', dur: '16:22' }
        ]},
        { channel: 'MotivationHub', videos: [
            { id: 'A14OxK7iOcI', title: 'THE LION MINDSET - Compilation', dur: '28:15' },
            { id: 'bMknL96fwbI', title: 'OBSESSED - Motivational Speech', dur: '12:45' },
            { id: 'g_SwGy0YAzc', title: 'DISCIPLINE YOUR MIND', dur: '22:10' },
            { id: 'kNMbZ8KUCGQ', title: 'WHEN LIFE HITS YOU', dur: '18:30' }
        ]},
        { channel: 'Ben Lionel Scott', videos: [
            { id: 'DGKMb0f0Ndw', title: 'NOTHING IS IMPOSSIBLE', dur: '10:00' },
            { id: 'JwLayhG5F0s', title: 'THE COMEBACK', dur: '15:30' },
            { id: 'TjnDYkkcDwk', title: 'GO AFTER YOUR DREAMS', dur: '12:00' },
            { id: '2GvyYWD-HTI', title: 'BECOME UNSTOPPABLE', dur: '14:20' }
        ]},
        { channel: 'Be Inspired', videos: [
            { id: '5fsm-QzhL0M', title: 'STAY HARD (David Goggins)', dur: '20:15' },
            { id: '1Ho2oY1CkjE', title: 'BELIEVE IN YOURSELF', dur: '18:45' }
        ]},
        { channel: 'Fearless Motivation', videos: [
            { id: 'gXvuJu1kt48', title: 'RELENTLESS - Best Speech', dur: '10:30' },
            { id: 'DOuMFazoXrw', title: 'THE WARRIOR MINDSET', dur: '8:45' }
        ]},
        { channel: 'Eddie Pinero (Your World Within)', videos: [
            { id: '7Oxz060iedY', title: 'THE REAL YOU - Motivational Speech', dur: '12:40' },
            { id: 'aDJkR4HBGVE', title: 'START BEFORE YOU\'RE READY', dur: '11:15' }
        ]},
        { channel: 'Marcus Taylor', videos: [
            { id: '0PjnU-D6pMw', title: 'PAIN IS YOUR FRIEND', dur: '15:20' },
            { id: 'RdX0VPblhFE', title: 'OUTWORK EVERYONE', dur: '13:40' }
        ]},
        { channel: 'T&H Inspiration', videos: [
            { id: 'xJ20jYkL2rQ', title: 'YOU VS YOU - Motivational Video', dur: '19:50' },
            { id: 'WxfZkMm3wcg', title: 'DESTROY YOUR LIMITS', dur: '14:10' }
        ]},
        { channel: 'Absolute Motivation', videos: [
            { id: 'MLU-XvEkbk4', title: 'FOCUS - Motivational Video', dur: '10:00' },
            { id: 'NlWMnF-ZCQI', title: 'CHAMPIONS MENTALITY', dur: '16:30' }
        ]},
        { channel: 'Mulligan Brothers', videos: [
            { id: 'WDDmCrIZsBg', title: 'HARD WORK BEATS TALENT', dur: '11:25' },
            { id: 'L_jWHffIx5E', title: 'SUCCESS IS NOT COMFORT', dur: '13:50' }
        ]}
    ];

    function buildMotivationOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'ms2-motivation-overlay';
        overlay.innerHTML = `
            <div class="mot-header">
                <button class="mot-close" data-nav-handled="true" onclick="document.getElementById('ms2-motivation-overlay').classList.remove('active')">✕</button>
                <h2>Motivation Videos</h2>
                <p>${MOTIVATION_CHANNELS.reduce((n,c)=>n+c.videos.length,0)} curated videos from ${MOTIVATION_CHANNELS.length} channels &mdash; plays right in your feed</p>
            </div>
            <div class="mot-grid" id="ms2MotGrid"></div>
        `;
        document.body.appendChild(overlay);

        const grid = overlay.querySelector('#ms2MotGrid');
        for (const ch of MOTIVATION_CHANNELS) {
            for (const v of ch.videos) {
                const card = document.createElement('div');
                card.className = 'mot-card';
                card.innerHTML = `
                    <div class="mot-thumb">
                        <img src="https://img.youtube.com/vi/${v.id}/hqdefault.jpg" alt="${v.title.replace(/"/g,'&quot;')}" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22480%22 height=%22360%22><rect fill=%22%23111%22 width=%22480%22 height=%22360%22/><text fill=%22%23555%22 x=%22240%22 y=%22180%22 text-anchor=%22middle%22 font-size=%2220%22>Video</text></svg>';this.onerror=null">
                        <div class="mot-play">&#9654;</div>
                        <div class="mot-dur">${v.dur}</div>
                    </div>
                    <div class="mot-info">
                        <div class="mot-title">${v.title}</div>
                        <div class="mot-channel">${ch.channel}</div>
                    </div>
                    <div class="mot-actions">
                        <button class="mot-play-btn" data-nav-handled="true" title="Play in feed">&#9654; Play</button>
                        <button class="mot-add-btn" data-nav-handled="true" title="Add to playlist">+ Playlist</button>
                    </div>
                `;
                card.querySelector('.mot-play-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    playInFeed(v.id, v.title, ch.channel, 'Motivation');
                });
                card.querySelector('.mot-add-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    const added = addToPlaylist({ id: v.id, title: v.title, channel: ch.channel, source: 'Motivation' });
                    const btn = e.currentTarget;
                    btn.textContent = added ? 'Added!' : 'Already saved';
                    btn.style.background = 'rgba(34,197,94,0.3)';
                    setTimeout(() => { btn.textContent = '+ Playlist'; btn.style.background = ''; }, 1500);
                });
                card.querySelector('.mot-thumb').addEventListener('click', () => {
                    playInFeed(v.id, v.title, ch.channel, 'Motivation');
                });
                grid.appendChild(card);
            }
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  4. IN-FEED PLAYBACK — Injects native scroll cards
    // ════════════════════════════════════════════════════════════════
    // Instead of overlaying a player on top, we create a native card
    // matching scroll-fix.js's createSlide() format and append it to
    // the scroll container. scroll-fix.js's handleScroll() then
    // auto-manages playback via forcePlayVisibleVideos().

    // Creates a feed card without scrolling or stopping other videos.
    // Used for batch injection (auto-play queues).
    // Returns the created slide element.
    function injectFeedCard(youtubeId, title, channel, source, afterElement) {
        var sc = findScrollContainer();
        if (!sc) return null;

        var muteVal = localStorage.getItem('movieshows-muted') === 'true' ? 1 : 0;
        var embedUrl = 'https://www.youtube.com/embed/' + youtubeId +
            '?autoplay=1&mute=' + muteVal + '&controls=1&playsinline=1&modestbranding=1&rel=0&enablejsapi=1';

        var slide = document.createElement('div');
        slide.className = 'h-full w-full snap-center';
        slide.dataset.movieTitle = title;
        slide.dataset.injectedByEnhancer = '1';

        var sourceBadge = source || 'Custom';
        var channelBadge = channel ? '<div class="bg-white/20 backdrop-blur-md text-white text-[10px] font-bold px-2 py-0.5 rounded">' + channel + '</div>' : '';

        slide.innerHTML =
            '<div class="relative w-full h-full flex items-center justify-center overflow-hidden snap-center bg-transparent">' +
                '<div class="absolute inset-0 w-full h-full bg-black">' +
                    '<iframe data-src="' + embedUrl + '" data-movie-title="' + title.replace(/"/g, '&quot;') + '"' +
                        ' src="" class="w-full h-full object-cover lazy-iframe"' +
                        ' allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen' +
                        ' style="pointer-events:auto;" frameborder="0"></iframe>' +
                '</div>' +
                '<div class="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/80 pointer-events-none z-20"></div>' +
                '<div class="absolute right-4 bottom-20 flex flex-col items-center gap-4 z-30 pointer-events-auto">' +
                    '<button class="flex flex-col items-center gap-1 group" onclick="this.querySelector(\'svg\').style.fill=\'red\'">' +
                        '<div class="p-3 rounded-full bg-black/40 backdrop-blur-sm transition-all duration-200 group-hover:bg-black/60">' +
                            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-8 h-8 text-white"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path></svg>' +
                        '</div>' +
                        '<span class="text-xs font-semibold drop-shadow-md text-white">Like</span>' +
                    '</button>' +
                '</div>' +
                '<div class="absolute bottom-4 left-4 right-16 z-30 flex flex-col gap-2 pointer-events-none">' +
                    '<div class="flex items-center gap-2">' +
                        '<div class="bg-purple-600 text-white text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">' + sourceBadge + '</div>' +
                        channelBadge +
                    '</div>' +
                    '<h2 class="text-2xl font-bold text-white drop-shadow-lg leading-tight pointer-events-auto w-full">' + title + '</h2>' +
                '</div>' +
            '</div>';

        // Insert after the specified element instead of at the end
        if (afterElement && afterElement.nextSibling) {
            sc.insertBefore(slide, afterElement.nextSibling);
        } else {
            sc.appendChild(slide);
        }
        return slide;
    }

    function playInFeed(youtubeId, title, channel, source) {
        // Cancel other auto-play chains if user plays from a different source
        if (source !== 'Motivation' && _motAutoPlayActive) {
            cancelMotivationAutoPlay();
        }
        if (source !== 'Freestyle' && _fsAutoPlayActive) {
            cancelFreestyleAutoPlay();
        }
        if (source !== 'Top 50' && _topAutoPlayActive) {
            cancelTopAutoPlay();
        }

        // Close all overlays
        document.getElementById('ms2-motivation-overlay')?.classList.remove('active');
        document.getElementById('ms2-freestyle-overlay')?.classList.remove('active');
        document.getElementById('ms2-top-panel')?.classList.remove('active');
        document.getElementById('ms2-playlist-panel')?.classList.remove('active');

        const sc = findScrollContainer();
        if (!sc) { console.error('[MS2 Enhancer] No scroll container found'); return; }

        // Stop all currently playing iframes
        document.querySelectorAll('iframe[src*="youtube"]').forEach(iframe => {
            try { iframe.setAttribute('src', ''); } catch(e) {}
        });

        // Build the embed URL (matches scroll-fix.js getYouTubeEmbedUrl pattern)
        const muteVal = localStorage.getItem('movieshows-muted') === 'true' ? 1 : 0;
        const embedUrl = 'https://www.youtube.com/embed/' + youtubeId +
            '?autoplay=1&mute=' + muteVal + '&controls=1&playsinline=1&modestbranding=1&rel=0&enablejsapi=1';

        // Create a native slide matching createSlide() in scroll-fix.js
        const slide = document.createElement('div');
        slide.className = 'h-full w-full snap-center';
        slide.dataset.movieTitle = title;
        slide.dataset.injectedByEnhancer = '1'; // Mark as enhancer-injected

        const sourceBadge = source || 'Custom';
        const channelHtml = channel ? '<p class="text-sm text-gray-200 drop-shadow-sm">' + channel + '</p>' : '';

        slide.innerHTML =
            '<div class="relative w-full h-full flex items-center justify-center overflow-hidden snap-center bg-transparent">' +
                '<div class="absolute inset-0 w-full h-full bg-black">' +
                    '<iframe data-src="' + embedUrl + '" data-movie-title="' + title.replace(/"/g, '&quot;') + '"' +
                        ' src="" class="w-full h-full object-cover lazy-iframe"' +
                        ' allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen' +
                        ' style="pointer-events:auto;" frameborder="0"></iframe>' +
                '</div>' +
                '<div class="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-black/80 pointer-events-none z-20"></div>' +
                // Right action buttons (simplified)
                '<div class="absolute right-4 bottom-20 flex flex-col items-center gap-4 z-30 pointer-events-auto">' +
                    '<button class="flex flex-col items-center gap-1 group" onclick="this.querySelector(\'svg\').style.fill=\'red\'">' +
                        '<div class="p-3 rounded-full bg-black/40 backdrop-blur-sm transition-all duration-200 group-hover:bg-black/60">' +
                            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-8 h-8 text-white"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"></path></svg>' +
                        '</div>' +
                        '<span class="text-xs font-semibold drop-shadow-md text-white">Like</span>' +
                    '</button>' +
                    '<button class="flex flex-col items-center gap-1 group" onclick="this.querySelector(\'svg\').style.fill=\'#22c55e\'">' +
                        '<div class="p-3 rounded-full bg-black/40 backdrop-blur-sm transition-all duration-200 group-hover:bg-black/60">' +
                            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-8 h-8 text-white"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>' +
                        '</div>' +
                        '<span class="text-xs font-semibold drop-shadow-md text-white">List</span>' +
                    '</button>' +
                    '<button class="flex flex-col items-center gap-1 group">' +
                        '<div class="p-3 rounded-full bg-black/40 backdrop-blur-sm transition-all duration-200 group-hover:bg-black/60">' +
                            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="w-8 h-8 text-white"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"></line><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"></line></svg>' +
                        '</div>' +
                        '<span class="text-xs font-semibold drop-shadow-md text-white">Share</span>' +
                    '</button>' +
                '</div>' +
                // Bottom info
                '<div class="absolute bottom-4 left-4 right-16 z-30 flex flex-col gap-2 pointer-events-none">' +
                    '<div class="flex items-center gap-2">' +
                        '<div class="bg-purple-600 text-white text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">' + sourceBadge + '</div>' +
                        (channel ? '<div class="bg-white/20 backdrop-blur-md text-white text-[10px] font-bold px-2 py-0.5 rounded">' + channel + '</div>' : '') +
                    '</div>' +
                    '<h2 class="text-2xl font-bold text-white drop-shadow-lg leading-tight pointer-events-auto w-full">' + title + '</h2>' +
                    channelHtml +
                '</div>' +
            '</div>';

        // Append to scroll container
        sc.appendChild(slide);

        // Get new slide count and scroll to it
        const allSlides = sc.querySelectorAll(':scope > [class*="snap-center"]');
        const newIndex = allSlides.length - 1;
        const slideHeight = sc.clientHeight;

        console.log('[MS2 Enhancer] Injected card "' + title + '" at index ' + newIndex + ', scrolling...');

        // Scroll to the new slide
        sc.scrollTo({ top: newIndex * slideHeight, behavior: 'smooth' });

        // After scroll completes, load the iframe (play the video)
        setTimeout(function() {
            const iframe = slide.querySelector('iframe');
            if (iframe && iframe.dataset.src) {
                iframe.setAttribute('src', iframe.dataset.src);
                console.log('[MS2 Enhancer] Playing "' + title + '" in feed');
            }
        }, 700);

        // If this is a motivation video and auto-play not yet offered, show prompt
        if (source === 'Motivation' && !_motAutoPlayActive && !_motPromptShown) {
            setTimeout(function() { showMotivationPrompt(youtubeId); }, 2500);
        }

        // Freestyle auto-play prompt
        if (source === 'Freestyle' && !_fsAutoPlayActive && !_fsPromptShown && _fsResults.length > 1) {
            setTimeout(function() { showFreestylePrompt(youtubeId); }, 2500);
        }

        // Top 50 auto-play prompt
        if (source === 'Top 50' && !_topAutoPlayActive && !_topPromptShown && _topQueue.length > 1) {
            setTimeout(function() { showTopPrompt(youtubeId); }, 2500);
        }

        return slide;
    }

    // ════════════════════════════════════════════════════════════════
    //  5. FREESTYLE SEARCH OVERLAY
    // ════════════════════════════════════════════════════════════════
    let _fsResults = [];

    function buildFreestyleOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'ms2-freestyle-overlay';
        overlay.innerHTML = `
            <div class="fs-header">
                <button class="fs-close" data-nav-handled="true" onclick="document.getElementById('ms2-freestyle-overlay').classList.remove('active')">✕</button>
                <h2>Freestyle <span class="fs-beta">Beta</span></h2>
                <p>Search for anything — plays right in your feed, or save to playlist</p>
                <div class="fs-search-row">
                    <input type="text" id="ms2FsInput" placeholder="Try: how to be more positive, sci-fi thriller, best motivation 2025..." onkeydown="if(event.key==='Enter')window._ms2DoFreestyle()">
                    <select id="ms2FsType">
                        <option value="youtube">YouTube</option>
                        <option value="multi">Movies & TV (TMDB)</option>
                        <option value="movie">Movies Only</option>
                        <option value="tv">TV Shows Only</option>
                    </select>
                    <button class="fs-search-btn" data-nav-handled="true" onclick="window._ms2DoFreestyle()">Search</button>
                </div>
            </div>
            <div class="fs-results" id="ms2FsResults">
                <div class="fs-empty"><div style="font-size:48px;margin-bottom:16px;">&#128269;</div><div>Search for anything above &mdash; plays in your feed</div></div>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    let _fsSearching = false;

    window._ms2DoFreestyle = async function() {
        const query = document.getElementById('ms2FsInput')?.value?.trim();
        const type = document.getElementById('ms2FsType')?.value || 'youtube';
        const results = document.getElementById('ms2FsResults');
        if (!query || !results || _fsSearching) return;

        _fsSearching = true;
        results.innerHTML = '<div class="fs-loading">Searching...</div>';

        try {
            const isYouTube = (type === 'youtube');

            if (isYouTube) {
                // MS3-style multi-tier search: PHP proxy → Piped → Invidious → Dailymotion
                let data = null;

                // Tier 1: Server-side PHP proxy
                try {
                    const r = await fetch(API_BASE + 'freestyle-search.php?q=' + encodeURIComponent(query) + '&type=youtube',
                        { signal: AbortSignal.timeout(10000) });
                    const d = await r.json();
                    if (d && d.success && d.results?.length) {
                        data = d.results.map(i => ({
                            title: i.title, id: i.trailer_id || i.videoId,
                            thumb: i.thumbnail, type: 'youtube', desc: i.channelTitle || i.description || '',
                            _channel: i.channelTitle || ''
                        }));
                    }
                } catch(e) { console.log('[Freestyle] PHP proxy failed:', e.message); }

                // Tier 2: Client-side Piped API (5 hosts, shuffled)
                if (!data) data = await searchPiped(query);

                // Tier 3: Client-side Invidious API (4 hosts)
                if (!data) data = await searchInvidious(query);

                // Tier 4: Dailymotion API (free, CORS-enabled)
                if (!data) data = await searchDailymotion(query);

                if (data && data.length) {
                    renderFreestyleResults(data, results);
                } else {
                    // All APIs failed — show fallback with YouTube.com link
                    const ytUrl = 'https://www.youtube.com/results?search_query=' + encodeURIComponent(query);
                    results.innerHTML = `
                        <div class="fs-empty">
                            <div style="font-size:48px;margin-bottom:16px;">😔</div>
                            <div>All search APIs are temporarily unavailable.</div>
                            <div style="margin-top:12px;">
                                <a href="${ytUrl}" target="_blank" style="color:#f59e0b;text-decoration:underline;font-size:15px;">
                                    🔍 Search on YouTube.com directly →
                                </a>
                            </div>
                        </div>`;
                }
            } else {
                // TMDB search (movies/TV)
                const data = await searchTMDB(query, type);
                renderFreestyleResults(data, results);
            }
        } catch(e) {
            results.innerHTML = '<div class="fs-empty">Search failed: ' + (e.message || 'Unknown error') + '</div>';
        }
        _fsSearching = false;
    };

    // ── Piped API (YouTube frontend, CORS-friendly) ──
    async function searchPiped(query) {
        const hosts = [
            'https://pipedapi.kavin.rocks',
            'https://pipedapi-libre.kavin.rocks',
            'https://pipedapi.adminforge.de',
            'https://pipedapi.in.projectsegfau.lt',
            'https://api.piped.yt'
        ];
        // Shuffle for load balancing
        for (let i = hosts.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [hosts[i], hosts[j]] = [hosts[j], hosts[i]];
        }
        for (const host of hosts) {
            try {
                console.log('[Freestyle] Trying Piped:', host);
                const r = await fetch(host + '/search?q=' + encodeURIComponent(query) + '&filter=videos',
                    { signal: AbortSignal.timeout(5000) });
                if (!r.ok) continue;
                const d = await r.json();
                if (d?.items?.length) {
                    const mapped = d.items.slice(0, 20).map(i => ({
                        title: i.title,
                        id: i.url?.includes('v=') ? i.url.split('v=')[1] : i.url?.split('/').pop(),
                        thumb: i.thumbnail,
                        type: 'youtube',
                        desc: i.uploaderName || '',
                        _channel: i.uploaderName || '',
                        _duration: i.duration ? formatDuration(i.duration) : ''
                    }));
                    if (mapped.length) {
                        console.log('[Freestyle] Piped success:', mapped.length, 'results');
                        return mapped;
                    }
                }
            } catch(e) { console.log('[Freestyle] Piped failed:', e.message); }
        }
        return null;
    }

    // ── Invidious API (YouTube frontend, CORS-friendly) ──
    async function searchInvidious(query) {
        const hosts = [
            'https://inv.nadeko.net',
            'https://invidious.fdn.fr',
            'https://vid.puffyan.us',
            'https://invidious.privacydev.net'
        ];
        for (const host of hosts) {
            try {
                console.log('[Freestyle] Trying Invidious:', host);
                const r = await fetch(host + '/api/v1/search?q=' + encodeURIComponent(query) + '&type=video',
                    { signal: AbortSignal.timeout(5000) });
                if (!r.ok) continue;
                const d = await r.json();
                if (Array.isArray(d) && d.length) {
                    const mapped = d.slice(0, 20).map(i => ({
                        title: i.title,
                        id: i.videoId,
                        thumb: i.videoThumbnails?.[0]?.url || '',
                        type: 'youtube',
                        desc: i.author || '',
                        _channel: i.author || '',
                        _duration: i.lengthSeconds ? formatDuration(i.lengthSeconds) : ''
                    }));
                    if (mapped.length) {
                        console.log('[Freestyle] Invidious success:', mapped.length, 'results');
                        return mapped;
                    }
                }
            } catch(e) { console.log('[Freestyle] Invidious failed:', e.message); }
        }
        return null;
    }

    // ── Dailymotion API (free, CORS-enabled, no auth) ──
    async function searchDailymotion(query) {
        try {
            console.log('[Freestyle] Trying Dailymotion...');
            const r = await fetch('https://api.dailymotion.com/videos?search=' + encodeURIComponent(query) +
                '&fields=id,title,description,thumbnail_url,duration,owner.screenname,views_total' +
                '&limit=20&sort=relevance',
                { signal: AbortSignal.timeout(6000) });
            if (!r.ok) return null;
            const d = await r.json();
            if (d?.list?.length) {
                const mapped = d.list.map(i => ({
                    title: i.title,
                    id: null,
                    thumb: i.thumbnail_url,
                    type: 'dailymotion',
                    desc: i['owner.screenname'] || '',
                    _channel: i['owner.screenname'] || '',
                    _duration: i.duration ? formatDuration(i.duration) : '',
                    _dmId: i.id
                }));
                console.log('[Freestyle] Dailymotion success:', mapped.length, 'results');
                return mapped;
            }
        } catch(e) { console.log('[Freestyle] Dailymotion failed:', e.message); }
        return null;
    }

    function formatDuration(seconds) {
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return m + ':' + (s < 10 ? '0' : '') + s;
    }

    async function searchTMDB(query, type) {
        try {
            const r = await fetch(API_BASE + 'freestyle-search.php?q=' + encodeURIComponent(query) + '&type=' + type,
                { signal: AbortSignal.timeout(10000) });
            const d = await r.json();
            return (d.results || []).slice(0, 20).map(i => ({
                title: i.title || i.name, thumb: i.poster_path ? 'https://image.tmdb.org/t/p/w300' + i.poster_path : '',
                id: i.id, year: (i.release_date || i.first_air_date || '').slice(0,4),
                type: i.media_type || type, desc: (i.overview || '').slice(0, 120)
            }));
        } catch { return []; }
    }

    function renderFreestyleResults(items, container) {
        // Store results for auto-play queue
        _fsResults = items;
        _fsPromptShown = false; // Reset prompt for new search
        _fsLastQuery = document.getElementById('ms2FsInput')?.value?.trim() || 'search';

        if (!items.length) {
            container.innerHTML = '<div class="fs-empty">No results found</div>';
            return;
        }
        container.innerHTML = '<div class="fs-grid"></div>';
        const grid = container.querySelector('.fs-grid');
        for (const item of items) {
            const card = document.createElement('div');
            card.className = 'fs-card';
            const isYT = item.type === 'youtube';
            const isDM = item.type === 'dailymotion';
            const thumb = isYT && item.id ? 'https://img.youtube.com/vi/' + item.id + '/hqdefault.jpg'
                : item.thumb || 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22300%22 height=%22169%22%3E%3Crect fill=%22%231a1a1a%22 width=%22300%22 height=%22169%22/%3E%3C/svg%3E';
            const sourceLabel = isYT ? 'YouTube' : isDM ? 'Dailymotion' : item.type === 'tv' ? 'TV' : 'Movie';
            const canPlay = (isYT && item.id);
            const isTMDB = (!isYT && !isDM && (item.type === 'movie' || item.type === 'tv' || item.type === 'multi'));
            card.innerHTML = `
                <div class="fs-card-thumb">
                    <img src="${thumb}" alt="" loading="lazy">
                    <div class="fs-card-play">&#9654;</div>
                    ${item._duration ? '<div class="fs-card-dur">' + item._duration + '</div>' : ''}
                </div>
                <div class="fs-card-body">
                    <div class="fs-card-title">${item.title || ''}</div>
                    <div class="fs-card-meta">${item._channel || item.desc ? (item._channel || item.desc) + ' &middot; ' : ''}${item.year ? item.year + ' &middot; ' : ''}${sourceLabel}</div>
                </div>
                ${canPlay ? '<div class="fs-card-actions"><button class="fs-play-btn" data-nav-handled="true">&#9654; Play</button><button class="fs-add-btn" data-nav-handled="true">+ Playlist</button></div>' : ''}
                ${isTMDB ? '<div class="fs-card-actions"><button class="fs-play-btn fs-tmdb-trailer-btn" data-nav-handled="true">&#9654; Watch Trailer</button></div>' : ''}
            `;
            if (canPlay) {
                card.querySelector('.fs-play-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    playInFeed(item.id, item.title, item._channel || 'YouTube', 'Freestyle');
                });
                card.querySelector('.fs-add-btn').addEventListener('click', (e) => {
                    e.stopPropagation();
                    const added = addToPlaylist({ id: item.id, title: item.title, channel: item._channel || '', source: 'Freestyle' });
                    const btn = e.currentTarget;
                    btn.textContent = added ? 'Added!' : 'Already saved';
                    btn.style.background = 'rgba(34,197,94,0.3)';
                    setTimeout(() => { btn.textContent = '+ Playlist'; btn.style.background = ''; }, 1500);
                });
                card.querySelector('.fs-card-thumb').addEventListener('click', () => {
                    playInFeed(item.id, item.title, item._channel || 'YouTube', 'Freestyle');
                });
            } else if (isTMDB) {
                // TMDB movies/TV: search YouTube for trailer and play in feed
                const playTMDBTrailer = async (btnEl) => {
                    const trailerQuery = (item.title || '') + ' ' + (item.year || '') + ' official trailer';
                    if (btnEl) { btnEl.textContent = 'Searching...'; btnEl.disabled = true; }
                    try {
                        let ytId = null;
                        // Try Piped first
                        const pipedResults = await searchPiped(trailerQuery);
                        if (pipedResults && pipedResults.length) ytId = pipedResults[0].id;
                        // Fallback to Invidious
                        if (!ytId) {
                            const invResults = await searchInvidious(trailerQuery);
                            if (invResults && invResults.length) ytId = invResults[0].id;
                        }
                        if (ytId) {
                            playInFeed(ytId, item.title + ' - Trailer', '', 'Freestyle');
                        } else {
                            // Fallback: open YouTube search in new tab
                            window.open('https://www.youtube.com/results?search_query=' + encodeURIComponent(trailerQuery), '_blank');
                        }
                    } catch(e) {
                        window.open('https://www.youtube.com/results?search_query=' + encodeURIComponent(trailerQuery), '_blank');
                    }
                    if (btnEl) { btnEl.textContent = '\u25b6 Watch Trailer'; btnEl.disabled = false; }
                };
                card.querySelector('.fs-tmdb-trailer-btn')?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    playTMDBTrailer(e.currentTarget);
                });
                card.querySelector('.fs-card-thumb').addEventListener('click', () => {
                    playTMDBTrailer(null);
                });
            } else if (isDM && item._dmId) {
                card.addEventListener('click', () => {
                    window.open('https://www.dailymotion.com/video/' + item._dmId, '_blank');
                });
            }
            grid.appendChild(card);
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  6. TOP 50 + GENRE CATEGORIES — Auto-refreshed from TMDB + The Numbers
    // ════════════════════════════════════════════════════════════════
    const API_BASE = 'https://findtorontoevents.ca/MOVIESHOWS2/api/';
    const TOP_MOVIES_URL = 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/TORONTOEVENTS_ANTIGRAVITY/shared/top-movies.json';

    function buildTopCard(m, rank, source, sectionMovies) {
        const card = document.createElement('div');
        card.className = 'top-card';
        const thumb = m.poster || m.thumbnail || (m.trailer_id ? 'https://img.youtube.com/vi/' + m.trailer_id + '/mqdefault.jpg' : '');
        const ratingBadge = m.rating ? '<div class="top-badge-rating">' + Number(m.rating).toFixed(1) + '</div>' : '';
        const grossBadge = m.weekend_gross ? '<div class="top-badge-gross">' + m.weekend_gross + '</div>' : '';
        card.innerHTML =
            '<img src="' + thumb + '" alt="' + (m.title||'').replace(/"/g,'&quot;') + '" loading="lazy" onerror="this.style.background=\'#222\'">' +
            (rank ? '<div class="top-rank">' + rank + '</div>' : '') +
            '<div class="top-card-title">' + (m.title || '') + '</div>' +
            ratingBadge + grossBadge;
        card.addEventListener('click', function() {
            if (m.trailer_id) {
                // Populate top auto-play queue with all playable movies from this section
                _topQueue = [];
                _topLastSection = source;
                _topPromptShown = false;
                if (sectionMovies) {
                    for (var si = 0; si < sectionMovies.length; si++) {
                        var sm = sectionMovies[si];
                        if (sm.trailer_id) {
                            _topQueue.push({ id: sm.trailer_id, title: sm.title, source: source });
                        }
                    }
                }
                playInFeed(m.trailer_id, m.title, source, 'Top 50');
            }
        });
        return card;
    }

    function buildTopRow(movies, title, icon, badge, container) {
        if (!movies || !movies.length) return;
        var section = document.createElement('div');
        section.className = 'ms2-top-section';
        section.innerHTML =
            '<div class="top-header">' +
                (icon ? '<span class="top-icon">' + icon + '</span>' : '') +
                '<span class="top-title">' + title + '</span>' +
                (badge ? '<span class="top-badge">' + badge + '</span>' : '') +
                '<span class="top-count">' + movies.length + ' titles</span>' +
            '</div>' +
            '<div class="top-row"></div>';
        var row = section.querySelector('.top-row');
        movies.forEach(function(m, i) {
            row.appendChild(buildTopCard(m, m.rank || (i + 1), m.source || title, movies));
        });
        container.appendChild(section);
    }

    async function buildTopSection(container) {
        try {
            // Primary: auto-refreshed JSON from TMDB + The Numbers (via GitHub raw)
            var r = await fetch(TOP_MOVIES_URL, { signal: AbortSignal.timeout(10000) });
            var data = await r.json();

            if (!data) throw new Error('Empty response');

            // Show update timestamp
            if (data.updated_at) {
                var updated = new Date(data.updated_at);
                var agoHours = Math.round((Date.now() - updated.getTime()) / 3600000);
                var timeLabel = agoHours < 1 ? 'just now' : agoHours + 'h ago';
                container.innerHTML = '<div style="color:#556;font-size:11px;padding:0 4px 8px;">Updated ' + timeLabel + ' &middot; TMDB + The Numbers &middot; Auto-refreshes every 6h</div>';
            }

            buildTopRow(data.now_playing, 'In Theaters Now', '\uD83C\uDFAC', 'LIVE', container);
            buildTopRow(data.box_office, 'Weekend Box Office', '\uD83D\uDCB0', 'THE NUMBERS', container);
            buildTopRow(data.trending, 'Trending This Week', '\uD83D\uDD25', 'TMDB', container);
            buildTopRow(data.popular, 'Popular Right Now', '\u2B50', null, container);
            buildTopRow(data.top_rated, 'All-Time Top Rated', '\uD83C\uDFC6', null, container);

            console.log('[MS2 Enhancer] Top section loaded from auto-refreshed JSON');
        } catch(e) {
            console.warn('[MS2 Enhancer] Auto-refresh JSON failed, falling back to database:', e);
            // Fallback: database API
            try {
                var r2 = await fetch(API_BASE + 'movies.php?action=list&limit=50');
                var d2 = await r2.json();
                if (d2.success && d2.movies && d2.movies.length) {
                    buildTopRow(d2.movies.map(function(m) {
                        return { title: m.title, trailer_id: m.trailer_id, poster: m.thumbnail, rating: m.imdb_rating ? parseFloat(m.imdb_rating) : null, source: 'Top Rated' };
                    }), 'Top Rated', '\uD83C\uDFC6', 'DATABASE', container);
                }
                var r3 = await fetch(API_BASE + 'movies.php?action=top_by_genre&limit=20');
                var d3 = await r3.json();
                if (d3.success && d3.categories && d3.categories.length) {
                    for (var ci = 0; ci < d3.categories.length; ci++) {
                        var cat = d3.categories[ci];
                        buildTopRow(cat.movies.map(function(m) {
                            return { title: m.title, trailer_id: m.trailer_id, poster: m.thumbnail, rating: m.imdb_rating ? parseFloat(m.imdb_rating) : null, source: cat.genre };
                        }), 'Top ' + cat.genre, null, null, container);
                    }
                }
            } catch(e2) { console.warn('[MS2 Enhancer] Fallback also failed:', e2); }
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  7. INJECT FILTER BUTTONS
    // ════════════════════════════════════════════════════════════════
    function injectFilterButtons(filterContainer) {
        if (!filterContainer || filterContainer.querySelector('#ms2BtnMotivation')) return;

        // Motivation button
        const motBtn = document.createElement('button');
        motBtn.id = 'ms2BtnMotivation';
        motBtn.className = getButtonStyle(false);
        motBtn.style.cssText = 'color:#c4b5fd; background:rgba(139,92,246,0.15); border:1px solid rgba(139,92,246,0.3);';
        motBtn.textContent = 'Motivation';
        motBtn.addEventListener('click', () => {
            document.getElementById('ms2-motivation-overlay')?.classList.add('active');
        });

        // Freestyle button
        const fsBtn = document.createElement('button');
        fsBtn.id = 'ms2BtnFreestyle';
        fsBtn.className = getButtonStyle(false);
        fsBtn.style.cssText = 'color:#f59e0b; background:rgba(245,158,11,0.15); border:1px solid rgba(245,158,11,0.3);';
        fsBtn.textContent = 'Freestyle';
        fsBtn.addEventListener('click', () => {
            document.getElementById('ms2-freestyle-overlay')?.classList.add('active');
            setTimeout(() => document.getElementById('ms2FsInput')?.focus(), 200);
        });

        // Categories button
        const catBtn = document.createElement('button');
        catBtn.id = 'ms2BtnCategories';
        catBtn.className = getButtonStyle(false);
        catBtn.style.cssText = 'color:#22c55e; background:rgba(34,197,94,0.15); border:1px solid rgba(34,197,94,0.3);';
        catBtn.textContent = 'Top 50';
        catBtn.addEventListener('click', () => {
            const panel = document.getElementById('ms2-top-panel');
            if (panel) {
                const isOpen = panel.classList.toggle('active');
                catBtn.style.background = isOpen ? 'rgba(34,197,94,0.3)' : 'rgba(34,197,94,0.15)';
            }
        });

        // Playlist button
        const plBtn = document.createElement('button');
        plBtn.id = 'ms2BtnPlaylist';
        plBtn.className = getButtonStyle(false);
        const plCount = loadPlaylist().length;
        plBtn.style.cssText = 'color:#f472b6; background:rgba(244,114,182,0.15); border:1px solid rgba(244,114,182,0.3);';
        plBtn.textContent = plCount > 0 ? 'Playlist (' + plCount + ')' : 'Playlist';
        plBtn.addEventListener('click', () => {
            const panel = document.getElementById('ms2-playlist-panel');
            if (panel) {
                panel.classList.add('active');
                renderPlaylistPanel();
            }
        });

        filterContainer.appendChild(motBtn);
        filterContainer.appendChild(fsBtn);
        filterContainer.appendChild(catBtn);
        filterContainer.appendChild(plBtn);

        // Cancel all auto-play chains if user clicks any built-in filter (All, Movies, TV, etc.)
        filterContainer.querySelectorAll('button:not(#ms2BtnMotivation):not(#ms2BtnFreestyle):not(#ms2BtnCategories):not(#ms2BtnPlaylist)').forEach(function(btn) {
            btn.addEventListener('click', function() {
                if (_motAutoPlayActive) cancelMotivationAutoPlay();
                if (_fsAutoPlayActive) cancelFreestyleAutoPlay();
                if (_topAutoPlayActive) cancelTopAutoPlay();
                _motPromptShown = false;
                _fsPromptShown = false;
                _topPromptShown = false;
            });
        });
    }

    // ════════════════════════════════════════════════════════════════
    //  8. CSS
    // ════════════════════════════════════════════════════════════════
    function injectStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* ── Motivation Overlay ── */
            #ms2-motivation-overlay {
                position:fixed;inset:0;z-index:400;background:rgba(10,10,18,0.98);
                backdrop-filter:blur(20px);display:none;flex-direction:column;overflow:hidden;
            }
            #ms2-motivation-overlay.active { display:flex; }
            .mot-header {
                position:sticky;top:0;z-index:10;background:rgba(15,15,25,0.95);
                padding:20px;border-bottom:1px solid rgba(255,255,255,0.08);
            }
            .mot-header h2 { color:white;margin:0 0 4px;font-size:20px; }
            .mot-header p { color:rgba(255,255,255,0.5);margin:0;font-size:13px; }
            .mot-close,.fs-close {
                position:absolute;top:16px;right:20px;width:36px;height:36px;
                border-radius:50%;border:1px solid rgba(255,255,255,0.2);
                background:rgba(255,255,255,0.1);color:white;font-size:18px;
                cursor:pointer;display:flex;align-items:center;justify-content:center;
            }
            .mot-grid {
                display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
                gap:16px;padding:20px;overflow-y:auto;flex:1;
            }
            .mot-card { border-radius:12px;overflow:hidden;background:rgba(255,255,255,0.04);transition:transform 0.2s; }
            .mot-card:hover { transform:scale(1.03); }
            .mot-thumb { position:relative;aspect-ratio:16/9;cursor:pointer; }
            .mot-thumb img { width:100%;height:100%;object-fit:cover;display:block; }
            .mot-play {
                position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
                background:rgba(0,0,0,0.3);opacity:0;transition:opacity 0.2s;font-size:32px;color:white;
            }
            .mot-card:hover .mot-play { opacity:1; }
            .mot-dur {
                position:absolute;bottom:6px;right:6px;background:rgba(0,0,0,0.8);
                color:white;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;
            }
            .mot-info { padding:10px 12px; }
            .mot-title { color:white;font-size:13px;font-weight:600;line-height:1.3; }
            .mot-channel { color:rgba(255,255,255,0.4);font-size:11px;margin-top:4px; }
            .mot-actions { display:flex;gap:6px;padding:0 12px 10px; }
            .mot-play-btn,.mot-add-btn {
                flex:1;padding:6px 0;border:none;border-radius:6px;font-size:12px;
                font-weight:600;cursor:pointer;transition:background 0.2s;
            }
            .mot-play-btn { background:rgba(139,92,246,0.3);color:#c4b5fd; }
            .mot-play-btn:hover { background:rgba(139,92,246,0.5); }
            .mot-add-btn { background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.6); }
            .mot-add-btn:hover { background:rgba(255,255,255,0.15); }

            /* ── Freestyle Overlay ── */
            #ms2-freestyle-overlay {
                position:fixed;inset:0;z-index:400;background:rgba(10,10,18,0.98);
                backdrop-filter:blur(20px);display:none;flex-direction:column;
            }
            #ms2-freestyle-overlay.active { display:flex; }
            .fs-header {
                position:sticky;top:0;z-index:10;background:rgba(15,15,25,0.95);
                padding:20px;border-bottom:1px solid rgba(255,255,255,0.08);
            }
            .fs-header h2 { color:white;margin:0 0 4px;font-size:20px; }
            .fs-header p { color:rgba(255,255,255,0.5);margin:0 0 16px;font-size:13px; }
            .fs-beta {
                background:rgba(245,158,11,0.2);border:1px solid rgba(245,158,11,0.4);
                color:#f59e0b;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;
            }
            .fs-search-row { display:flex;gap:8px; }
            .fs-search-row input {
                flex:1;padding:12px 16px;border-radius:10px;border:1px solid rgba(255,255,255,0.15);
                background:rgba(255,255,255,0.08);color:white;font-size:14px;outline:none;
            }
            .fs-search-row select {
                padding:12px;border-radius:10px;border:1px solid rgba(255,255,255,0.15);
                background:rgba(255,255,255,0.08);color:white;font-size:13px;cursor:pointer;
            }
            .fs-search-btn {
                padding:12px 24px;border-radius:10px;border:none;
                background:linear-gradient(135deg,#f59e0b,#d97706);color:white;
                font-weight:700;cursor:pointer;font-size:14px;
            }
            .fs-results { padding:20px;overflow-y:auto;flex:1; }
            .fs-grid { display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px; }
            .fs-card { border-radius:12px;overflow:hidden;background:rgba(255,255,255,0.04);transition:transform 0.2s; }
            .fs-card:hover { transform:scale(1.03); }
            .fs-card-thumb { position:relative;aspect-ratio:16/9;cursor:pointer; }
            .fs-card-thumb img { width:100%;height:100%;object-fit:cover;display:block;background:#1a1a1a; }
            .fs-card-play {
                position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
                background:rgba(0,0,0,0.3);opacity:0;transition:opacity 0.2s;font-size:32px;color:white;
            }
            .fs-card:hover .fs-card-play { opacity:1; }
            .fs-card-body { padding:10px 12px; }
            .fs-card-title { color:white;font-size:13px;font-weight:600;line-height:1.3; }
            .fs-card-meta { color:rgba(255,255,255,0.4);font-size:11px;margin-top:4px; }
            .fs-empty,.fs-loading { text-align:center;padding:60px 20px;color:rgba(255,255,255,0.3);font-size:16px; }
            .fs-card-actions { display:flex;gap:6px;padding:0 12px 10px; }
            .fs-play-btn,.fs-add-btn {
                flex:1;padding:6px 0;border:none;border-radius:6px;font-size:12px;
                font-weight:600;cursor:pointer;transition:background 0.2s;
            }
            .fs-play-btn { background:rgba(245,158,11,0.3);color:#f59e0b; }
            .fs-play-btn:hover { background:rgba(245,158,11,0.5); }
            .fs-add-btn { background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.6); }
            .fs-add-btn:hover { background:rgba(255,255,255,0.15); }

            /* ── Freestyle duration badge ── */
            .fs-card-dur {
                position:absolute;bottom:6px;right:6px;background:rgba(0,0,0,0.8);
                color:white;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:600;
            }

            /* ── Playlist Panel ── */
            #ms2-playlist-panel {
                position:fixed;inset:0;z-index:400;background:rgba(10,10,18,0.98);
                backdrop-filter:blur(20px);display:none;flex-direction:column;overflow:hidden;
            }
            #ms2-playlist-panel.active { display:flex; }
            .pl-header {
                position:sticky;top:0;z-index:10;background:rgba(15,15,25,0.95);
                padding:20px;border-bottom:1px solid rgba(255,255,255,0.08);
                display:flex;align-items:center;justify-content:space-between;
            }
            .pl-header h2 { color:white;margin:0;font-size:20px; }
            .pl-header-actions { display:flex;gap:8px;align-items:center; }
            .pl-mix-btn {
                padding:8px 16px;border-radius:8px;border:none;
                background:linear-gradient(135deg,#f472b6,#ec4899);color:white;
                font-weight:700;font-size:13px;cursor:pointer;
            }
            .pl-mix-btn:hover { opacity:0.85; }
            .pl-clear-btn {
                padding:8px 12px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);
                background:transparent;color:rgba(255,255,255,0.5);font-size:12px;cursor:pointer;
            }
            .pl-list { padding:12px 20px;overflow-y:auto;flex:1; }
            .pl-item {
                display:flex;align-items:center;gap:12px;padding:10px;
                border-radius:10px;background:rgba(255,255,255,0.04);margin-bottom:8px;
                transition:background 0.2s;
            }
            .pl-item:hover { background:rgba(255,255,255,0.08); }
            .pl-item-thumb {
                width:80px;height:45px;border-radius:6px;object-fit:cover;flex-shrink:0;
                background:#1a1a1a;cursor:pointer;
            }
            .pl-item-info { flex:1;min-width:0; }
            .pl-item-title { color:white;font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
            .pl-item-meta { color:rgba(255,255,255,0.4);font-size:11px;margin-top:2px; }
            .pl-item-actions { display:flex;gap:6px;flex-shrink:0; }
            .pl-item-play {
                padding:6px 12px;border-radius:6px;border:none;
                background:rgba(139,92,246,0.3);color:#c4b5fd;font-size:12px;
                font-weight:600;cursor:pointer;
            }
            .pl-item-remove {
                padding:6px 10px;border-radius:6px;border:none;
                background:rgba(239,68,68,0.2);color:#f87171;font-size:12px;cursor:pointer;
            }
            .pl-empty { text-align:center;padding:60px 20px;color:rgba(255,255,255,0.3);font-size:15px; }

            /* ── Motivation Auto-Play ── */
            #ms2-mot-prompt {
                position:fixed;top:80px;left:50%;transform:translateX(-50%) translateY(-20px);
                z-index:500;background:rgba(15,15,30,0.95);border:1px solid rgba(139,92,246,0.4);
                border-radius:16px;padding:16px 20px;display:flex;align-items:center;gap:12px;
                backdrop-filter:blur(20px);opacity:0;transition:opacity 0.3s,transform 0.3s;
                box-shadow:0 8px 32px rgba(0,0,0,0.5);max-width:90vw;
            }
            #ms2-mot-prompt.active { opacity:1;transform:translateX(-50%) translateY(0); }
            .mot-prompt-text { color:white;font-size:14px;font-weight:600;white-space:nowrap; }
            .mot-prompt-actions { display:flex;gap:8px; }
            .mot-prompt-yes {
                padding:8px 16px;border-radius:8px;border:none;
                background:linear-gradient(135deg,#8b5cf6,#7c3aed);color:white;
                font-weight:700;font-size:13px;cursor:pointer;white-space:nowrap;
            }
            .mot-prompt-no {
                padding:8px 16px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);
                background:transparent;color:rgba(255,255,255,0.6);
                font-size:13px;cursor:pointer;white-space:nowrap;
            }
            #ms2-mot-indicator {
                position:fixed;top:16px;right:16px;z-index:450;
                background:rgba(139,92,246,0.2);border:1px solid rgba(139,92,246,0.4);
                border-radius:12px;padding:8px 14px;display:flex;align-items:center;gap:10px;
                backdrop-filter:blur(10px);
            }
            .mot-ind-text { color:#c4b5fd;font-size:12px;font-weight:600; }
            .mot-ind-stop {
                width:20px;height:20px;border-radius:50%;border:none;
                background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.5);
                font-size:12px;cursor:pointer;display:flex;align-items:center;justify-content:center;
                padding:0;
            }

            /* ── Freestyle Auto-Play ── */
            #ms2-fs-prompt {
                position:fixed;top:80px;left:50%;transform:translateX(-50%) translateY(-20px);
                z-index:500;background:rgba(15,15,30,0.95);border:1px solid rgba(245,158,11,0.4);
                border-radius:16px;padding:16px 20px;display:flex;align-items:center;gap:12px;
                backdrop-filter:blur(20px);opacity:0;transition:opacity 0.3s,transform 0.3s;
                box-shadow:0 8px 32px rgba(0,0,0,0.5);max-width:90vw;
            }
            #ms2-fs-prompt.active { opacity:1;transform:translateX(-50%) translateY(0); }
            .fs-prompt-text { color:white;font-size:14px;font-weight:600;white-space:nowrap; }
            .fs-prompt-actions { display:flex;gap:8px; }
            .fs-prompt-yes {
                padding:8px 16px;border-radius:8px;border:none;
                background:linear-gradient(135deg,#f59e0b,#d97706);color:white;
                font-weight:700;font-size:13px;cursor:pointer;white-space:nowrap;
            }
            .fs-prompt-no {
                padding:8px 16px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);
                background:transparent;color:rgba(255,255,255,0.6);
                font-size:13px;cursor:pointer;white-space:nowrap;
            }
            #ms2-fs-indicator {
                position:fixed;top:16px;right:16px;z-index:450;
                background:rgba(245,158,11,0.2);border:1px solid rgba(245,158,11,0.4);
                border-radius:12px;padding:8px 14px;display:flex;align-items:center;gap:10px;
                backdrop-filter:blur(10px);
            }
            .fs-ind-text { color:#f59e0b;font-size:12px;font-weight:600; }
            .fs-ind-stop {
                width:20px;height:20px;border-radius:50%;border:none;
                background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.5);
                font-size:12px;cursor:pointer;display:flex;align-items:center;justify-content:center;
                padding:0;
            }

            /* ── Top 50 Auto-Play ── */
            #ms2-top-prompt {
                position:fixed;top:80px;left:50%;transform:translateX(-50%) translateY(-20px);
                z-index:500;background:rgba(15,15,30,0.95);border:1px solid rgba(34,197,94,0.4);
                border-radius:16px;padding:16px 20px;display:flex;align-items:center;gap:12px;
                backdrop-filter:blur(20px);opacity:0;transition:opacity 0.3s,transform 0.3s;
                box-shadow:0 8px 32px rgba(0,0,0,0.5);max-width:90vw;
            }
            #ms2-top-prompt.active { opacity:1;transform:translateX(-50%) translateY(0); }
            .top-prompt-text { color:white;font-size:14px;font-weight:600;white-space:nowrap; }
            .top-prompt-actions { display:flex;gap:8px; }
            .top-prompt-yes {
                padding:8px 16px;border-radius:8px;border:none;
                background:linear-gradient(135deg,#22c55e,#16a34a);color:white;
                font-weight:700;font-size:13px;cursor:pointer;white-space:nowrap;
            }
            .top-prompt-no {
                padding:8px 16px;border-radius:8px;border:1px solid rgba(255,255,255,0.15);
                background:transparent;color:rgba(255,255,255,0.6);
                font-size:13px;cursor:pointer;white-space:nowrap;
            }
            #ms2-top-indicator {
                position:fixed;top:16px;right:16px;z-index:450;
                background:rgba(34,197,94,0.2);border:1px solid rgba(34,197,94,0.4);
                border-radius:12px;padding:8px 14px;display:flex;align-items:center;gap:10px;
                backdrop-filter:blur(10px);
            }
            .top-ind-text { color:#22c55e;font-size:12px;font-weight:600; }
            .top-ind-stop {
                width:20px;height:20px;border-radius:50%;border:none;
                background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.5);
                font-size:12px;cursor:pointer;display:flex;align-items:center;justify-content:center;
                padding:0;
            }

            /* ── Top 50 / Categories Panel ── */
            #ms2-top-panel {
                position:fixed;inset:0;z-index:350;background:rgba(10,10,18,0.98);
                backdrop-filter:blur(20px);display:none;flex-direction:column;overflow-y:auto;
            }
            #ms2-top-panel.active { display:flex; }
            .ms2-top-header {
                position:sticky;top:0;z-index:10;background:rgba(15,15,25,0.95);
                padding:20px;border-bottom:1px solid rgba(255,255,255,0.08);
                display:flex;align-items:center;justify-content:space-between;
            }
            .ms2-top-header h2 { color:white;margin:0;font-size:20px; }
            .ms2-top-content { padding:20px; }
            .ms2-top-section { margin-bottom:24px; }
            .top-header {
                display:flex;align-items:center;gap:8px;padding:0 4px;margin-bottom:10px;
            }
            .top-icon { font-size:20px; }
            .top-title { font-size:15px;font-weight:800;color:white; }
            .top-count { font-size:11px;color:#888; }
            .top-badge {
                background:rgba(245,158,11,0.2);color:#fbbf24;
                padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;
            }
            .top-row {
                display:flex;gap:12px;overflow-x:auto;padding:4px 0;
                scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;
            }
            .top-row::-webkit-scrollbar { height:4px; }
            .top-row::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.15);border-radius:4px; }
            .top-card {
                flex:0 0 120px;position:relative;cursor:pointer;overflow:hidden;
                border-radius:8px;transition:transform 0.2s;scroll-snap-align:start;
                background:rgba(255,255,255,0.04);
            }
            .top-card:hover { transform:scale(1.05); }
            .top-card img { width:100%;aspect-ratio:2/3;object-fit:cover;display:block;background:#1a1a1a; }
            .top-rank {
                position:absolute;bottom:28px;left:4px;font-size:36px;font-weight:900;
                color:white;text-shadow:2px 2px 4px rgba(0,0,0,0.8);
                -webkit-text-stroke:1px rgba(0,0,0,0.5);line-height:1;
            }
            .top-card-title {
                position:absolute;bottom:0;left:0;right:0;padding:4px 6px;
                background:linear-gradient(transparent,rgba(0,0,0,0.9));
                color:white;font-size:10px;font-weight:600;line-height:1.2;
            }
            .top-badge-rating {
                position:absolute;top:6px;right:6px;background:rgba(0,0,0,0.7);
                color:#fbbf24;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700;
            }
            .top-badge-gross {
                position:absolute;top:6px;left:6px;background:rgba(34,197,94,0.85);
                color:white;padding:2px 6px;border-radius:4px;font-size:9px;font-weight:700;
            }
        `;
        document.head.appendChild(style);
    }

    // ════════════════════════════════════════════════════════════════
    //  9. BUILD TOP PANEL
    // ════════════════════════════════════════════════════════════════
    function buildTopPanel() {
        const panel = document.createElement('div');
        panel.id = 'ms2-top-panel';
        panel.innerHTML = `
            <div class="ms2-top-header">
                <h2>Top 50 & Categories</h2>
                <button class="mot-close" data-nav-handled="true" onclick="document.getElementById('ms2-top-panel').classList.remove('active');document.getElementById('ms2BtnCategories').style.background='rgba(34,197,94,0.15)'">&#10005;</button>
            </div>
            <div class="ms2-top-content" id="ms2TopContent">
                <div class="fs-loading">Loading Top 50 & Categories...</div>
            </div>
        `;
        document.body.appendChild(panel);
        buildTopSection(panel.querySelector('#ms2TopContent'));
    }

    // ════════════════════════════════════════════════════════════════
    //  10. BUILD PLAYLIST PANEL
    // ════════════════════════════════════════════════════════════════
    function buildPlaylistPanel() {
        const panel = document.createElement('div');
        panel.id = 'ms2-playlist-panel';
        panel.innerHTML = `
            <div class="pl-header">
                <h2>Playlist</h2>
                <div class="pl-header-actions">
                    <button class="pl-mix-btn" id="ms2PlMix" data-nav-handled="true" title="Add all playlist videos into your feed">Mix All Into Feed</button>
                    <button class="pl-clear-btn" id="ms2PlClear" data-nav-handled="true">Clear All</button>
                    <button class="mot-close" data-nav-handled="true" onclick="document.getElementById('ms2-playlist-panel').classList.remove('active')">&#10005;</button>
                </div>
            </div>
            <div class="pl-list" id="ms2PlList"></div>
        `;
        document.body.appendChild(panel);

        panel.querySelector('#ms2PlMix').addEventListener('click', () => {
            const list = loadPlaylist();
            if (!list.length) return;
            // Close panel, inject all into feed
            panel.classList.remove('active');
            list.forEach((item, i) => {
                setTimeout(() => {
                    playInFeed(item.id, item.title, item.channel, item.source || 'Playlist');
                }, i === 0 ? 0 : i * 300); // Stagger slightly
            });
        });

        panel.querySelector('#ms2PlClear').addEventListener('click', () => {
            savePlaylist([]);
            renderPlaylistPanel();
        });
    }

    function renderPlaylistPanel() {
        const container = document.getElementById('ms2PlList');
        if (!container) return;
        const list = loadPlaylist();
        if (!list.length) {
            container.innerHTML = '<div class="pl-empty">No saved videos yet.<br>Use "+ Playlist" on motivation or freestyle videos to save them here.</div>';
            return;
        }
        container.innerHTML = '';
        for (const item of list) {
            const row = document.createElement('div');
            row.className = 'pl-item';
            row.innerHTML = `
                <img class="pl-item-thumb" src="https://img.youtube.com/vi/${item.id}/mqdefault.jpg" alt="" loading="lazy">
                <div class="pl-item-info">
                    <div class="pl-item-title">${item.title}</div>
                    <div class="pl-item-meta">${item.channel || ''} ${item.source ? '&middot; ' + item.source : ''}</div>
                </div>
                <div class="pl-item-actions">
                    <button class="pl-item-play" data-nav-handled="true">&#9654; Play</button>
                    <button class="pl-item-remove" data-nav-handled="true">&#10005;</button>
                </div>
            `;
            row.querySelector('.pl-item-thumb').addEventListener('click', () => {
                playInFeed(item.id, item.title, item.channel, item.source || 'Playlist');
            });
            row.querySelector('.pl-item-play').addEventListener('click', () => {
                playInFeed(item.id, item.title, item.channel, item.source || 'Playlist');
            });
            row.querySelector('.pl-item-remove').addEventListener('click', () => {
                removeFromPlaylist(item.id);
                renderPlaylistPanel();
            });
            container.appendChild(row);
        }
    }

    // ════════════════════════════════════════════════════════════════
    //  INIT — Poll until React renders, then enhance
    // ════════════════════════════════════════════════════════════════
    function init() {
        const fc = findFilterContainer();
        if (!fc) {
            setTimeout(init, 500);
            return;
        }

        console.log('[MS2 Enhancer v1.5] Filter container found, injecting enhancements');

        injectStyles();
        injectFilterButtons(fc);
        buildMotivationOverlay();
        buildFreestyleOverlay();
        buildTopPanel();
        buildPlaylistPanel();
        startGenreObserver();
        setupVideoEndListener();

        // Re-inject buttons if React re-renders
        const observer = new MutationObserver(() => {
            const fc2 = findFilterContainer();
            if (fc2 && !fc2.querySelector('#ms2BtnMotivation')) {
                injectFilterButtons(fc2);
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => setTimeout(init, 1000));
    } else {
        setTimeout(init, 1000);
    }
})();
