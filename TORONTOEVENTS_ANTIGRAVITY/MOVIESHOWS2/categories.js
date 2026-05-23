/**
 * MovieShows2 — Categories Carousels v1.0
 * Horizontal scroll rows for Top 10 per genre, sourced live from the database API.
 * Injected below the search panel filters.
 */
(function() {
    'use strict';

    // Always use the central API — database only exists on findtorontoevents.ca (50webs)
    const API_BASE = 'https://findtorontoevents.ca/MOVIESHOWS2/api/';

    const CACHE_KEY = 'ms2-categories-cache';
    const CACHE_TTL = 30 * 60 * 1000; // 30 min

    // ── Styles ───────────────────────────────────────────────────────
    const style = document.createElement('style');
    style.textContent = `
        #ms2-categories { padding: 0 0 10px; }
        .cat-section { margin-bottom: 18px; }
        .cat-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 12px; margin-bottom: 8px;
        }
        .cat-title {
            font-size: 15px; font-weight: 700; color: #fff;
            display: flex; align-items: center; gap: 6px;
        }
        .cat-title .cat-count {
            font-size: 11px; color: #888; font-weight: 400;
        }
        .cat-see-all {
            font-size: 11px; color: #22c55e; cursor: pointer;
            background: none; border: none; padding: 4px 8px; border-radius: 4px;
        }
        .cat-see-all:hover { background: rgba(34,197,94,0.1); }
        .cat-row {
            display: flex; gap: 10px; overflow-x: auto; padding: 0 12px 6px;
            scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
        }
        .cat-row::-webkit-scrollbar { display: none; }
        .cat-card {
            flex: 0 0 130px; scroll-snap-align: start; cursor: pointer;
            border-radius: 8px; overflow: hidden; position: relative;
            background: rgba(255,255,255,0.04); transition: transform 0.2s;
        }
        .cat-card:hover { transform: scale(1.05); }
        .cat-card img {
            width: 130px; height: 73px; object-fit: cover; display: block;
            background: #1a1a1a;
        }
        .cat-card-info {
            padding: 6px 8px;
        }
        .cat-card-title {
            font-size: 11px; font-weight: 600; color: #eee;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .cat-card-meta {
            font-size: 10px; color: #888; margin-top: 2px;
            display: flex; align-items: center; gap: 4px;
        }
        .cat-card-rating {
            color: #fbbf24; font-weight: 600;
        }
        .cat-loading {
            text-align: center; padding: 20px; color: #666; font-size: 12px;
        }
        .cat-error {
            text-align: center; padding: 12px; color: #ef4444; font-size: 12px;
            cursor: pointer;
        }
        .cat-toggle {
            display: flex; align-items: center; justify-content: center;
            padding: 8px; margin: 0 12px 10px; border-radius: 8px;
            background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.15);
            color: #22c55e; font-size: 12px; font-weight: 600; cursor: pointer;
            transition: background 0.2s;
        }
        .cat-toggle:hover { background: rgba(34,197,94,0.15); }
        .cat-toggle .arrow { transition: transform 0.2s; margin-left: 6px; }
        .cat-toggle.collapsed .arrow { transform: rotate(-90deg); }
    `;
    document.head.appendChild(style);

    // ── Data ──────────────────────────────────────────────────────────
    function getCached() {
        try {
            const raw = localStorage.getItem(CACHE_KEY);
            if (!raw) return null;
            const { ts, data } = JSON.parse(raw);
            if (Date.now() - ts > CACHE_TTL) return null;
            return data;
        } catch { return null; }
    }

    function setCache(data) {
        try {
            localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data }));
        } catch {}
    }

    async function fetchCategories() {
        const cached = getCached();
        if (cached) return cached;

        const res = await fetch(API_BASE + 'movies.php?action=top_by_genre&limit=10');
        if (!res.ok) throw new Error('API ' + res.status);
        const json = await res.json();
        if (!json.success || !json.categories) throw new Error('Bad response');

        setCache(json.categories);
        return json.categories;
    }

    // ── Playback ─────────────────────────────────────────────────────
    function playFromCategory(movie) {
        // Try to find existing item in appState
        if (typeof appState !== 'undefined' && appState.allContent) {
            const existing = appState.allContent.find(c =>
                c.title && movie.title && c.title.toLowerCase() === movie.title.toLowerCase()
            );
            if (existing) {
                if (typeof playVideo === 'function') {
                    playVideo(existing);
                    scrollPlayerSectionIntoView?.();
                    return;
                }
            }
        }

        // Build a synthetic item for playback
        const youtubeId = movie.trailer_id;
        const item = {
            id: 'cat-' + (movie.id || movie.title),
            title: movie.title,
            type: movie.type || 'movie',
            year: movie.release_year,
            thumbnail: movie.thumbnail || (youtubeId ? 'https://img.youtube.com/vi/' + youtubeId + '/hqdefault.jpg' : ''),
            videoUrl: null,
            description: '',
            _youtubeId: youtubeId || null,
            _raw: movie
        };

        if (typeof playVideo === 'function') {
            playVideo(item);
            scrollPlayerSectionIntoView?.();
        }
    }

    // ── "See All" → filter by genre ──────────────────────────────────
    function seeAllGenre(genre) {
        const genreSelect = document.getElementById('filter-genre');
        if (genreSelect) {
            genreSelect.value = genre;
            document.getElementById('apply-filters')?.click();
        }
    }

    // ── Render ────────────────────────────────────────────────────────
    function renderCategories(categories, container) {
        container.innerHTML = '';

        // Collapse toggle
        const collapsed = localStorage.getItem('ms2-cat-collapsed') === '1';
        const toggle = document.createElement('div');
        toggle.className = 'cat-toggle' + (collapsed ? ' collapsed' : '');
        toggle.innerHTML = 'Browse by Category <span class="arrow">▼</span>';
        toggle.addEventListener('click', () => {
            const inner = container.querySelector('.cat-inner');
            const isCollapsed = toggle.classList.toggle('collapsed');
            inner.style.display = isCollapsed ? 'none' : '';
            localStorage.setItem('ms2-cat-collapsed', isCollapsed ? '1' : '0');
        });
        container.appendChild(toggle);

        const inner = document.createElement('div');
        inner.className = 'cat-inner';
        inner.style.display = collapsed ? 'none' : '';

        for (const cat of categories) {
            const section = document.createElement('div');
            section.className = 'cat-section';

            const header = document.createElement('div');
            header.className = 'cat-header';
            header.innerHTML = `
                <div class="cat-title">${cat.genre} <span class="cat-count">${cat.movies.length} titles</span></div>
                <button class="cat-see-all" data-genre="${cat.genre}">See all →</button>
            `;
            header.querySelector('.cat-see-all').addEventListener('click', () => seeAllGenre(cat.genre));
            section.appendChild(header);

            const row = document.createElement('div');
            row.className = 'cat-row';

            for (const movie of cat.movies) {
                const card = document.createElement('div');
                card.className = 'cat-card';
                const thumb = movie.thumbnail || (movie.trailer_id ? 'https://img.youtube.com/vi/' + movie.trailer_id + '/hqdefault.jpg' : '');
                const rating = movie.imdb_rating ? parseFloat(movie.imdb_rating).toFixed(1) : '';

                card.innerHTML = `
                    <img src="${thumb}" alt="${(movie.title || '').replace(/"/g, '&quot;')}" loading="lazy" onerror="this.src='https://via.placeholder.com/130x73?text=No+Image'">
                    <div class="cat-card-info">
                        <div class="cat-card-title">${movie.title || ''}</div>
                        <div class="cat-card-meta">
                            ${rating ? '<span class="cat-card-rating">★ ' + rating + '</span>' : ''}
                            ${movie.release_year ? '<span>' + movie.release_year + '</span>' : ''}
                        </div>
                    </div>
                `;
                card.addEventListener('click', () => playFromCategory(movie));
                row.appendChild(card);
            }

            section.appendChild(row);
            inner.appendChild(section);
        }

        container.appendChild(inner);
    }

    // ── Init ──────────────────────────────────────────────────────────
    async function initCategories() {
        // Find injection point: after #advanced-filters or after search input's parent
        const searchPanel = document.getElementById('search-panel');
        if (!searchPanel) return;

        const content = searchPanel.querySelector('.panel-content');
        if (!content) return;

        // Create container
        const container = document.createElement('div');
        container.id = 'ms2-categories';

        // Insert after advanced-filters if present, otherwise after search input parent
        const advFilters = content.querySelector('#advanced-filters');
        if (advFilters) {
            advFilters.insertAdjacentElement('afterend', container);
        } else {
            const input = content.querySelector('input');
            if (input) {
                (input.parentElement || input).insertAdjacentElement('afterend', container);
            } else {
                content.appendChild(container);
            }
        }

        container.innerHTML = '<div class="cat-loading">Loading categories…</div>';

        try {
            const categories = await fetchCategories();
            if (!categories.length) {
                container.innerHTML = '';
                return;
            }
            renderCategories(categories, container);
        } catch (err) {
            console.warn('[Categories] fetch failed:', err);
            container.innerHTML = '<div class="cat-error">Failed to load categories. Tap to retry.</div>';
            container.querySelector('.cat-error')?.addEventListener('click', () => initCategories());
        }
    }

    // Wait for DOM and features.js to inject filters first
    function waitAndInit() {
        if (document.getElementById('search-panel')) {
            // Delay slightly so features.js can inject advanced-filters first
            setTimeout(initCategories, 500);
        } else {
            const observer = new MutationObserver((_, obs) => {
                if (document.getElementById('search-panel')) {
                    obs.disconnect();
                    setTimeout(initCategories, 500);
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', waitAndInit);
    } else {
        waitAndInit();
    }
})();
