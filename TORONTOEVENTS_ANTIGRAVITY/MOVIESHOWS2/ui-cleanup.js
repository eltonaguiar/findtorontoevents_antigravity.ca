// UI Cleanup - Organize buttons and reduce clutter
// This script runs LAST to clean up the interface

(function() {
    console.log('[MovieShows] UI Cleanup starting...');
    
    // Features that are FULLY implemented and should stay visible
    const CORE_FEATURES = [
        'mute', 'unmute', 'sound',
        'play', 'pause', 'next', 'previous',
        'all', 'movies', 'tv', 'now playing',
        'filters', 'search', 'queue', 'my queue',
        'like', 'save', 'share', 
        'close', 'hide', 'show',
        'small', 'medium', 'large', 'full',
        'shuffle', 'stats'
    ];
    
    // Features that should go to sandbox (UI exists but not fully functional)
    const SANDBOX_FEATURES = [
        'ratings', 'accessibility', 'parental', 'download',
        'audio description', 'cast', 'crew', 'soundtrack',
        'reviews', 'bts', 'behind the scenes', 'quotes',
        'trivia', 'mood match', 'export history', 'share card',
        'gallery', 'runtime', 'by year', 'language',
        'director', 'studios', 'franchises', 'awards',
        'box office', 'releases', 'country', 'actor',
        'similar', 'loop', 'skip intro', 'party',
        'discuss', 'spoiler', 'notes', 'favorites',
        'collections', 'binge', 'compare', 'themes',
        'milestones', 'goals', 'bookmarks', 'pip',
        'session', 'celebration', 'calendar', 'tags',
        'invites', 'insights', 'notifications', 'streaks',
        'chapters', 'theater', 'subtitles', 'report',
        'versions', 'quality', 'sync', 'alerts', 'preview',
        'smart pause', 'freshness', 'mini player', 'rating comparison',
        'auto-resume', 'discovery', 'gesture', 'availability',
        'schedule', 'quick actions', 'speed', 'mood tags',
        'content notes', 'watchlist folders', 'keyboard', 'age rating',
        'recently viewed', 'duration filter', 'video quality'
    ];
    
    let cleanupAttempts = 0;
    const MAX_CLEANUP_ATTEMPTS = 5;
    
    function isCoreFeatature(text) {
        const lowerText = text.toLowerCase().trim();
        return CORE_FEATURES.some(f => lowerText.includes(f) || lowerText === f);
    }
    
    function isSandboxFeature(text) {
        const lowerText = text.toLowerCase().trim();
        return SANDBOX_FEATURES.some(f => lowerText.includes(f));
    }
    
    function createSandboxButton() {
        if (document.getElementById('sandbox-link-btn')) return;
        
        const btn = document.createElement('a');
        btn.id = 'sandbox-link-btn';
        btn.href = 'FUTURE.html';
        btn.innerHTML = '🧪 Sandbox';
        btn.title = 'View experimental & upcoming features';
        btn.style.cssText = `
            position: fixed;
            bottom: 80px;
            left: 20px;
            background: linear-gradient(135deg, #9c27b0, #673ab7);
            color: white;
            text-decoration: none;
            padding: 12px 20px;
            border-radius: 25px;
            font-size: 14px;
            font-weight: bold;
            z-index: 10000;
            box-shadow: 0 4px 15px rgba(156, 39, 176, 0.4);
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        `;
        
        btn.addEventListener('mouseenter', () => {
            btn.style.transform = 'scale(1.05)';
            btn.style.boxShadow = '0 6px 20px rgba(156, 39, 176, 0.6)';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.transform = 'scale(1)';
            btn.style.boxShadow = '0 4px 15px rgba(156, 39, 176, 0.4)';
        });
        
        document.body.appendChild(btn);
        console.log('[MovieShows] Sandbox link button added');
    }
    
    function createMenuButton() {
        if (document.getElementById('main-menu-btn')) return;
        
        const btn = document.createElement('button');
        btn.id = 'main-menu-btn';
        btn.innerHTML = '☰ Menu';
        btn.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(233, 69, 96, 0.9);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 25px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            z-index: 10001;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            transition: all 0.3s;
        `;
        
        btn.onclick = toggleMainMenu;
        document.body.appendChild(btn);
    }
    
    function toggleMainMenu() {
        let menu = document.getElementById('main-popup-menu');
        if (menu) {
            menu.remove();
            return;
        }
        
        menu = document.createElement('div');
        menu.id = 'main-popup-menu';
        menu.style.cssText = `
            position: fixed;
            top: 70px;
            right: 20px;
            background: rgba(26, 26, 46, 0.98);
            border: 1px solid #333;
            border-radius: 12px;
            padding: 15px;
            z-index: 10002;
            min-width: 200px;
            max-height: 70vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
        `;
        
        menu.innerHTML = `
            <div style="color:#fff;font-weight:bold;margin-bottom:15px;padding-bottom:10px;border-bottom:1px solid #333;">
                ⚙️ Quick Menu
            </div>
            <div class="menu-section">
                <div style="color:#888;font-size:12px;margin-bottom:8px;">PLAYER</div>
                <button class="menu-item" onclick="document.body.className=document.body.className.replace(/player-\\w+/,'')+'player-small'">📺 Small Player</button>
                <button class="menu-item" onclick="document.body.className=document.body.className.replace(/player-\\w+/,'')+'player-medium'">📺 Medium Player</button>
                <button class="menu-item" onclick="document.body.className=document.body.className.replace(/player-\\w+/,'')+'player-large'">📺 Large Player</button>
                <button class="menu-item" onclick="document.body.className=document.body.className.replace(/player-\\w+/,'')+'player-full'">📺 Full Player</button>
            </div>
            <div class="menu-section" style="margin-top:15px;">
                <div style="color:#888;font-size:12px;margin-bottom:8px;">NAVIGATE</div>
                <button class="menu-item" onclick="window.scrollToPreviousSlide && window.scrollToPreviousSlide()">⬆️ Previous</button>
                <button class="menu-item" onclick="window.scrollToNextSlide && window.scrollToNextSlide()">⬇️ Next</button>
                <button class="menu-item" onclick="window.shuffleContent && window.shuffleContent()">🎲 Shuffle</button>
            </div>
            <div class="menu-section" style="margin-top:15px;">
                <div style="color:#888;font-size:12px;margin-bottom:8px;">LINKS</div>
                <a class="menu-item" href="FUTURE.html" style="display:block;text-decoration:none;">🧪 Feature Sandbox</a>
            </div>
            <button class="menu-item" onclick="this.parentElement.remove()" style="margin-top:15px;background:#e94560;">✕ Close Menu</button>
        `;
        
        // Add menu item styles
        const style = document.createElement('style');
        style.textContent = `
            .menu-item {
                display: block;
                width: 100%;
                background: #252545;
                color: #fff;
                border: none;
                padding: 10px 15px;
                margin: 5px 0;
                border-radius: 6px;
                cursor: pointer;
                text-align: left;
                font-size: 13px;
                transition: background 0.2s;
            }
            .menu-item:hover {
                background: #3a3a6a;
            }
        `;
        menu.appendChild(style);
        
        document.body.appendChild(menu);
        
        // Close when clicking outside
        setTimeout(() => {
            document.addEventListener('click', function closeMenu(e) {
                if (!menu.contains(e.target) && e.target.id !== 'main-menu-btn') {
                    menu.remove();
                    document.removeEventListener('click', closeMenu);
                }
            });
        }, 100);
    }
    
    function hideExcessButtons() {
        // Hide buttons from feature batches that are sandbox features
        const allButtons = document.querySelectorAll('button, .btn, [role="button"]');
        let hiddenCount = 0;
        
        allButtons.forEach(btn => {
            const text = btn.textContent || btn.innerText || '';
            const title = btn.title || '';
            const combined = (text + ' ' + title).toLowerCase();
            
            // Skip essential buttons
            if (btn.id && ['mute-control', 'info-toggle', 'action-panel-toggle', 'main-menu-btn', 'sandbox-link-btn'].includes(btn.id)) {
                return;
            }
            
            // Skip buttons that are part of core functionality
            if (isCoreFeatature(combined)) {
                return;
            }
            
            // Hide sandbox feature buttons
            if (isSandboxFeature(combined)) {
                btn.style.display = 'none';
                hiddenCount++;
            }
        });
        
        console.log(`[MovieShows] Hidden ${hiddenCount} sandbox feature buttons`);
    }
    
    function consolidateNavButtons() {
        // Find and consolidate navigation elements
        const quickNav = document.querySelector('.quick-nav, #quick-nav, nav');
        if (!quickNav) return;
        
        // Remove excessive margin/padding
        quickNav.style.maxWidth = '300px';
        quickNav.style.overflowY = 'auto';
        quickNav.style.maxHeight = '80vh';
    }
    
    function fixVideoPlayback() {
        // Ensure videos can play
        console.log('[MovieShows] Checking video playback...');
        
        const currentSlide = document.querySelector('.video-slide.active, .slide.active, [data-active="true"]');
        if (currentSlide) {
            const iframe = currentSlide.querySelector('iframe');
            if (iframe) {
                const dataSrc = iframe.getAttribute('data-src');
                const currentSrc = iframe.getAttribute('src');
                
                if (dataSrc && (!currentSrc || currentSrc === 'about:blank' || !currentSrc.includes('youtube'))) {
                    console.log('[MovieShows] Activating video playback...');
                    iframe.src = dataSrc;
                }
            }
        }
        
        // Also check first slide if no active slide
        const firstSlide = document.querySelector('.video-slide, .slide');
        if (firstSlide && !currentSlide) {
            const iframe = firstSlide.querySelector('iframe');
            if (iframe) {
                const dataSrc = iframe.getAttribute('data-src');
                if (dataSrc && !iframe.src.includes('youtube')) {
                    console.log('[MovieShows] Activating first video...');
                    iframe.src = dataSrc;
                    firstSlide.classList.add('active');
                }
            }
        }
    }
    
    function cleanupUI() {
        cleanupAttempts++;
        console.log(`[MovieShows] UI Cleanup attempt ${cleanupAttempts}/${MAX_CLEANUP_ATTEMPTS}`);
        
        try {
            createSandboxButton();
            createMenuButton();
            hideExcessButtons();
            consolidateNavButtons();
            fixVideoPlayback();
            
            // Add CSS to reduce clutter
            if (!document.getElementById('ui-cleanup-styles')) {
                const style = document.createElement('style');
                style.id = 'ui-cleanup-styles';
                style.textContent = `
                    /* Hide excessive feature buttons */
                    .ratings-breakdown-btn,
                    .accessibility-modal,
                    .parental-btn,
                    .download-btn,
                    .cast-crew-btn,
                    .soundtrack-btn,
                    .reviews-btn,
                    .bts-btn,
                    .quotes-btn,
                    .trivia-btn,
                    .mood-match-btn,
                    .export-btn,
                    .gallery-btn,
                    .runtime-btn,
                    .year-btn,
                    .lang-btn,
                    .director-btn,
                    .studio-btn,
                    .franchise-btn,
                    .awards-btn,
                    .box-office-btn,
                    .calendar-btn,
                    .country-btn,
                    .actor-btn,
                    .crew-btn,
                    .similar-btn,
                    .loop-btn,
                    .skip-btn,
                    .party-btn,
                    .discuss-btn,
                    .spoiler-btn,
                    .notes-btn {
                        display: none !important;
                    }
                    
                    /* Clean up nav */
                    .quick-nav, #quick-nav {
                        max-height: 70vh !important;
                        overflow-y: auto !important;
                    }
                    
                    /* Reduce button overlap */
                    .video-controls button,
                    .player-controls button {
                        margin: 2px !important;
                        font-size: 11px !important;
                        padding: 4px 8px !important;
                    }
                    
                    /* Ensure video is visible */
                    .video-slide iframe,
                    .slide iframe {
                        min-height: 300px !important;
                    }
                    
                    /* Hide empty containers */
                    .empty-container,
                    div:empty {
                        display: none;
                    }
                `;
                document.head.appendChild(style);
            }
            
            console.log('[MovieShows] UI Cleanup complete!');
            
        } catch (error) {
            console.error('[MovieShows] UI Cleanup error:', error);
            
            if (cleanupAttempts < MAX_CLEANUP_ATTEMPTS) {
                setTimeout(cleanupUI, 2000);
            }
        }
    }
    
    // Run cleanup after all feature batches have loaded
    function init() {
        // Wait for DOM and other scripts
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => setTimeout(cleanupUI, 3000));
        } else {
            setTimeout(cleanupUI, 3000);
        }
        
        // Also run on window load
        window.addEventListener('load', () => setTimeout(cleanupUI, 4000));
    }
    
    init();
    
})();
