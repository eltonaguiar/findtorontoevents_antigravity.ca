// UI Minimal - Clean interface with WORKING navigation
// Does NOT interfere with search, queue, or filter panels

(function() {
    console.log('[MovieShows] UI Minimal - Navigation-safe mode...');
    
    // IDs/classes to NEVER hide (essential UI panels)
    const NEVER_HIDE = [
        'search-panel', 'search-modal', 'search-overlay',
        'queue-panel', 'queue-modal', 'queue-overlay',
        'filter-panel', 'filter-modal', 'filters',
        'quick-nav', 'quicknav', 'nav-panel',
        'mute-control', 'mute',
        'player-size-wrapper', 'player-size-control', 'settings-toggle',
        'layout-control', 'volume-control', 'volume-slider'
    ];
    
    function shouldNeverHide(element) {
        const id = (element.id || '').toLowerCase();
        const className = (element.className || '').toLowerCase();
        
        // Check if element or parent contains essential panel
        for (const keep of NEVER_HIDE) {
            if (id.includes(keep) || className.includes(keep)) return true;
        }
        
        // Check parent containers too
        let parent = element.parentElement;
        let depth = 0;
        while (parent && depth < 5) {
            const parentId = (parent.id || '').toLowerCase();
            const parentClass = (parent.className || '').toLowerCase();
            for (const keep of NEVER_HIDE) {
                if (parentId.includes(keep) || parentClass.includes(keep)) return true;
            }
            parent = parent.parentElement;
            depth++;
        }
        
        return false;
    }
    
    function cleanupExtraButtons() {
        // Only hide non-essential action buttons on video slides
        const hideButtonTexts = [
            'hype', 'thought', 'boring', 'emotional',
            'movie fan', 'shuffle', 'stats', 'badges',
            'mood', 'coming soon', 'autoplay', 'bar:',
            'player:', 'txt', 'dt', 'accessibility', 'parental',
            'trivia', 'export', 'studios', 'franchises', 'awards',
            'releases', 'party', 'shield', 'director', 'actor', 'crew',
            'ratings', 'download', 'soundtrack', 'reviews', 'quotes',
            'gallery', 'runtime', 'loop', 'skip', 'discuss', 'notes',
            'collections', 'binge', 'compare', 'themes', 'milestones',
            'goals', 'bookmarks', 'pip', 'session', 'celebration',
            'calendar', 'tags', 'invites', 'insights', 'notifications',
            'streaks', 'chapters', 'theater', 'subtitles', 'report',
            'versions', 'quality', 'sync', 'alerts', 'preview', 'speed',
            'cast', 'box office', 'scene', 'quick share', 'timeline',
            'dashboard', 'reminders', 'watch party', 'mood board',
            'playlist manager', 'browse collections', 'compare content'
        ];
        
        document.querySelectorAll('.video-slide button, .slide button').forEach(btn => {
            // Skip if in essential panel
            if (shouldNeverHide(btn)) return;
            
            const text = (btn.textContent || '').toLowerCase().trim();
            
            for (const hideText of hideButtonTexts) {
                if (text.includes(hideText)) {
                    btn.style.display = 'none';
                    break;
                }
            }
        });
        
        // Hide buttons on non-active slides
        document.querySelectorAll('.video-slide:not(.active), .slide:not(.active)').forEach(slide => {
            slide.querySelectorAll('button').forEach(btn => {
                btn.style.display = 'none';
            });
        });
    }
    
    function hideSettingsPanel() {
        // NO LONGER HIDE settings panel - we need it for volume control
        // The settings panel now has important user controls like volume slider
        // Users can collapse it themselves using the Settings toggle button
        return;
    }
    
    function addMinimalStyles() {
        if (document.getElementById('minimal-ui-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'minimal-ui-styles';
        style.textContent = `
            /* Hide settings panel and feature panels */
            .settings-panel, #settings-panel,
            .feature-panel, .feature-modal,
            [class*="premium"], [class*="batch"],
            #main-popup-menu, #sandbox-link-btn,
            .genre-buttons, .duration-filter, .speed-controls {
                display: none !important;
            }
            
            /* KEEP search, queue, and filter panels visible! */
            #search-panel, .search-panel, [class*="search-modal"],
            #queue-panel, .queue-panel, [class*="queue-modal"],
            #filter-panel, .filter-panel, [class*="filter-modal"],
            .quick-nav, #quick-nav {
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
            }
            
            /* Keep mute button visible */
            #mute-control {
                display: block !important;
                position: fixed !important;
                bottom: 20px !important;
                left: 20px !important;
                z-index: 10000 !important;
            }
            
            /* Ensure video fills screen */
            .video-slide, .slide {
                width: 100vw !important;
                height: 100vh !important;
            }
            
            .video-slide iframe, .slide iframe {
                width: 100% !important;
                height: 100% !important;
            }
        `;
        document.head.appendChild(style);
    }
    
    function ensureVideoPlays() {
        const activeSlide = document.querySelector('.video-slide.active, .slide.active') 
            || document.querySelector('.video-slide, .slide');
        
        if (!activeSlide) return;
        
        const iframe = activeSlide.querySelector('iframe');
        if (!iframe) return;
        
        const dataSrc = iframe.getAttribute('data-src');
        const currentSrc = iframe.getAttribute('src');
        
        if (dataSrc && (!currentSrc || !currentSrc.includes('youtube'))) {
            console.log('[MovieShows] Activating video...');
            iframe.src = dataSrc;
            activeSlide.classList.add('active');
        }
    }
    
    function init() {
        addMinimalStyles();
        
        // Light cleanup - don't break navigation
        setTimeout(cleanupExtraButtons, 1000);
        setTimeout(hideSettingsPanel, 1500);
        
        // Ensure video plays
        setTimeout(ensureVideoPlays, 1000);
        setTimeout(ensureVideoPlays, 3000);
        
        console.log('[MovieShows] Minimal UI ready - navigation preserved');
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    window.addEventListener('load', () => {
        setTimeout(ensureVideoPlays, 1000);
    });
})();
