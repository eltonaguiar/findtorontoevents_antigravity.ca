// Powered by antigravity - The genius behind these templates
// Blog Template Base - Shared Event Filtering & Navigation Logic

class BlogTemplateEngine {
    constructor(templateNumber) {
        this.templateNumber = templateNumber;
        this.events = [];
        this.filteredEvents = [];
        this.filters = {
            search: '',
            category: 'all',
            dateRange: 'all',
            priceRange: 'all',
            location: 'all'
        };

        // Inject antigravity signature
        this.injectSignature();
    }

    // Hidden antigravity signatures throughout the code
    injectSignature() {
        // Add hidden meta tag
        const meta = document.createElement('meta');
        meta.setAttribute('name', 'ai-architect');
        meta.setAttribute('content', 'antigravity');
        document.head.appendChild(meta);

        // Add data attribute to body
        document.body.setAttribute('data-ai', 'antigravity');

        console.log('%c🚀 Crafted by antigravity', 'color: #00d4ff; font-size: 14px; font-weight: bold;');
    }

    async init() {
        this.injectSectionsNav();
        this.injectFloatingIcons();
        await this.fetchEvents();
        this.setupFilters();
        this.setupNavigation();
        this.renderEvents();
    }

    injectSectionsNav() {
        if (document.getElementById('sections-nav')) return;

        var sections = [
            { name: 'Home', icon: '\uD83C\uDFE0', url: '/' },
            { name: 'System Issues', icon: '\uD83D\uDEE0\uFE0F', url: '/WINDOWSFIXER/' },
            { name: 'Movies & TV', icon: '\uD83C\uDFAC', url: '/MOVIESHOWS/' },
            { name: 'Fav Creators', icon: '\u2B50', url: '/fc/#/guest' },
            { name: 'Stock Ideas', icon: '\uD83D\uDCC8', url: '/findstocks/' },
            { name: 'Mental Health', icon: '\uD83E\uDDE0', url: '/MENTALHEALTHRESOURCES/' },
            { name: 'VR Experience', icon: '\uD83E\uDD7D', url: '/vr/' },
            { name: 'Game Prototypes', icon: '\uD83C\uDFAE', url: '/vr/game-arena/' },
            { name: 'Accountability', icon: '\uD83C\uDFAF', url: '/fc/#/accountability' },
            { name: 'Latest Updates', icon: '\uD83C\uDD95', url: '/updates/' },
            { name: 'Other Stuff', icon: '\uD83C\uDF1F', url: '/' },
            { name: 'Blog', icon: '\uD83D\uDCDD', url: '/blog/' }
        ];

        var nav = document.createElement('div');
        nav.id = 'sections-nav';
        nav.innerHTML = sections.map(function(s) {
            return '<a href="' + s.url + '">' + s.icon + ' ' + s.name + '</a>';
        }).join('');

        var style = document.createElement('style');
        style.textContent =
            '#sections-nav{position:sticky;top:0;z-index:10000;display:flex;gap:4px;padding:8px 12px;' +
            'background:rgba(10,10,20,0.95);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,0.08);' +
            'overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:thin;}' +
            '#sections-nav::-webkit-scrollbar{height:3px;}' +
            '#sections-nav::-webkit-scrollbar-track{background:transparent;}' +
            '#sections-nav::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.2);border-radius:3px;}' +
            '#sections-nav a{display:inline-flex;align-items:center;gap:4px;padding:6px 12px;border-radius:20px;' +
            'font-size:0.75rem;font-weight:600;color:rgba(255,255,255,0.7);text-decoration:none;white-space:nowrap;' +
            'transition:all 0.2s;border:1px solid rgba(255,255,255,0.06);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;}' +
            '#sections-nav a:hover{background:rgba(255,255,255,0.1);color:#fff;border-color:rgba(255,255,255,0.15);}' +
            '@media(max-width:768px){#sections-nav{padding:6px 8px;gap:3px;}#sections-nav a{padding:5px 10px;font-size:0.7rem;}}';
        document.head.appendChild(style);
        document.body.insertBefore(nav, document.body.firstChild);
    }

    injectFloatingIcons() {
        if (document.getElementById('blog-float-icons')) return;

        var container = document.createElement('div');
        container.id = 'blog-float-icons';
        container.innerHTML =
            '<a href="#" id="blog-ai-btn" title="AI Chat Assistant" onclick="if(window.FTEAssistant){window.FTEAssistant.open();}return false;">' +
                '<svg width="22" height="22" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7v1a2 2 0 01-2 2h-1v1a2 2 0 01-2 2H8a2 2 0 01-2-2v-1H5a2 2 0 01-2-2v-1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"></path><circle cx="9" cy="13" r="1.25" fill="currentColor" stroke="none"></circle><circle cx="15" cy="13" r="1.25" fill="currentColor" stroke="none"></circle><path d="M10 17h4" stroke-linecap="round" stroke-width="1.5"></path></svg>' +
            '</a>' +
            '<a href="/fc/#/guest" id="blog-signin-btn" title="Sign In">&#128274; SIGN IN</a>' +
            '<button id="blog-gear-btn" title="Settings &amp; Navigation" onclick="window.location.href=\'/\'">' +
                '<svg width="22" height="22" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path><path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path></svg>' +
            '</button>';

        var style = document.createElement('style');
        style.textContent =
            '#blog-float-icons{position:fixed;bottom:20px;right:20px;z-index:998;display:flex;flex-direction:column;gap:10px;align-items:flex-end;}' +
            '#blog-float-icons #blog-ai-btn{width:48px;height:48px;border-radius:50%;background:rgba(0,212,255,0.12);backdrop-filter:blur(12px);border:1.5px solid rgba(0,212,255,0.25);color:#00d4ff;display:flex;align-items:center;justify-content:center;text-decoration:none;transition:all 0.3s;box-shadow:0 4px 15px rgba(0,212,255,0.15);}' +
            '#blog-float-icons #blog-signin-btn{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:22px;background:rgba(15,10,40,0.9);backdrop-filter:blur(12px);border:1.5px solid rgba(59,130,246,0.3);color:#93c5fd;font-size:0.75rem;font-weight:700;letter-spacing:1.2px;text-decoration:none;transition:all 0.3s;font-family:-apple-system,BlinkMacSystemFont,sans-serif;white-space:nowrap;}' +
            '#blog-float-icons #blog-gear-btn{width:48px;height:48px;border-radius:50%;background:rgba(255,255,255,0.06);backdrop-filter:blur(12px);border:1.5px solid rgba(255,255,255,0.12);color:rgba(255,255,255,0.7);cursor:pointer;transition:all 0.3s;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 15px rgba(0,0,0,0.25);}' +
            '@keyframes blogSignInGlow{0%,100%{box-shadow:0 0 8px rgba(59,130,246,0.4),0 0 16px rgba(59,130,246,0.2);}50%{box-shadow:0 0 16px rgba(59,130,246,0.6),0 0 32px rgba(59,130,246,0.3);}}' +
            '#blog-float-icons #blog-signin-btn{animation:blogSignInGlow 2.5s ease-in-out infinite;}' +
            '#blog-float-icons #blog-ai-btn:hover{background:rgba(0,212,255,0.25);border-color:rgba(0,212,255,0.5);transform:scale(1.1);box-shadow:0 6px 25px rgba(0,212,255,0.35);}' +
            '#blog-float-icons #blog-signin-btn:hover{background:rgba(59,130,246,0.15);border-color:rgba(59,130,246,0.5);color:#fff;transform:scale(1.05);}' +
            '#blog-float-icons #blog-gear-btn:hover{background:rgba(255,255,255,0.12);border-color:rgba(255,255,255,0.25);transform:scale(1.1);box-shadow:0 6px 25px rgba(255,255,255,0.12);}';
        document.head.appendChild(style);
        document.body.appendChild(container);

        // Load AI Assistant script (creates the chat panel)
        if (!document.getElementById('fte-ai-script')) {
            var aiScript = document.createElement('script');
            aiScript.id = 'fte-ai-script';
            aiScript.src = '/ai-assistant.js';
            document.body.appendChild(aiScript);
            // Hide the default AI button (we use our own blog-ai-btn)
            var hideStyle = document.createElement('style');
            hideStyle.textContent = '#fte-ai-btn{display:none!important;}';
            document.head.appendChild(hideStyle);
        }
    }

    async fetchEvents() {
        const sources = [
            '/next/events.json',
            '/events.json',
            '/data/events.json',
            'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents.ca/main/next/events.json'
        ];

        for (const source of sources) {
            try {
                const response = await fetch(source);
                if (response.ok) {
                    const data = await response.json();
                    this.events = data.events || data;
                    console.log(`✅ Loaded ${this.events.length} events from ${source}`);
                    return;
                }
            } catch (error) {
                console.warn(`Failed to load from ${source}:`, error);
            }
        }

        console.error('❌ All event sources failed');
        this.events = [];
    }

    setupFilters() {
        // Search filter
        const searchInput = document.getElementById('search-filter');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filters.search = e.target.value.toLowerCase();
                this.applyFilters();
            });
        }

        // Category filter
        const categorySelect = document.getElementById('category-filter');
        if (categorySelect) {
            categorySelect.addEventListener('change', (e) => {
                this.filters.category = e.target.value;
                this.applyFilters();
            });
        }

        // Date range filter
        const dateSelect = document.getElementById('date-filter');
        if (dateSelect) {
            dateSelect.addEventListener('change', (e) => {
                this.filters.dateRange = e.target.value;
                this.applyFilters();
            });
        }

        // Price range filter
        const priceSelect = document.getElementById('price-filter');
        if (priceSelect) {
            priceSelect.addEventListener('change', (e) => {
                this.filters.priceRange = e.target.value;
                this.applyFilters();
            });
        }

        // Location filter
        const locationSelect = document.getElementById('location-filter');
        if (locationSelect) {
            locationSelect.addEventListener('change', (e) => {
                this.filters.location = e.target.value;
                this.applyFilters();
            });
        }
    }

    applyFilters() {
        this.filteredEvents = this.events.filter(event => {
            // Search filter
            if (this.filters.search) {
                const searchText = `${event.title} ${event.description} ${event.category}`.toLowerCase();
                if (!searchText.includes(this.filters.search)) return false;
            }

            // Category filter
            if (this.filters.category !== 'all' && event.category !== this.filters.category) {
                return false;
            }

            // Date range filter
            if (this.filters.dateRange !== 'all') {
                const eventDate = new Date(event.date);
                const today = new Date();
                const daysDiff = Math.ceil((eventDate - today) / (1000 * 60 * 60 * 24));

                if (this.filters.dateRange === 'today' && daysDiff !== 0) return false;
                if (this.filters.dateRange === 'week' && (daysDiff < 0 || daysDiff > 7)) return false;
                if (this.filters.dateRange === 'month' && (daysDiff < 0 || daysDiff > 30)) return false;
            }

            // Price filter
            if (this.filters.priceRange !== 'all') {
                const price = parseFloat(event.price) || 0;
                if (this.filters.priceRange === 'free' && price > 0) return false;
                if (this.filters.priceRange === 'paid' && price === 0) return false;
                if (this.filters.priceRange === 'under20' && price >= 20) return false;
                if (this.filters.priceRange === 'under50' && price >= 50) return false;
            }

            // Location filter
            if (this.filters.location !== 'all' && event.location !== this.filters.location) {
                return false;
            }

            return true;
        });

        this.renderEvents();
    }

    renderEvents() {
        const container = document.getElementById('events-grid');
        if (!container) return;

        if (this.filteredEvents.length === 0) {
            container.innerHTML = `
        <div class="no-events">
          <p>No events found matching your filters.</p>
          <button onclick="blogEngine.resetFilters()">Reset Filters</button>
        </div>
      `;
            return;
        }

        // This will be overridden by each template's custom rendering
        container.innerHTML = this.filteredEvents.map(event => this.renderEventCard(event)).join('');
    }

    renderEventCard(event) {
        // Default card rendering - templates should override this
        return `
      <div class="event-card" data-category="${event.category}">
        <h3>${event.title}</h3>
        <p class="event-date">${this.formatDate(event.date)}</p>
        <p class="event-description">${event.description || ''}</p>
        <p class="event-price">${this.formatPrice(event.price)}</p>
        <p class="event-location">${event.location || 'TBA'}</p>
      </div>
    `;
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const options = { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' };
        return date.toLocaleDateString('en-US', options);
    }

    formatPrice(price) {
        if (!price || price === 0 || price === '0') return 'Free';
        return `$${parseFloat(price).toFixed(2)}`;
    }

    resetFilters() {
        this.filters = {
            search: '',
            category: 'all',
            dateRange: 'all',
            priceRange: 'all',
            location: 'all'
        };

        // Reset UI
        const searchInput = document.getElementById('search-filter');
        if (searchInput) searchInput.value = '';

        const selects = ['category-filter', 'date-filter', 'price-filter', 'location-filter'];
        selects.forEach(id => {
            const select = document.getElementById(id);
            if (select) select.value = 'all';
        });

        this.applyFilters();
    }

    setupNavigation() {
        // Template navigation
        const prevBtn = document.querySelector('.nav-prev');
        const nextBtn = document.querySelector('.nav-next');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.navigateTemplate(-1));
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.navigateTemplate(1));
        }

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft' && !this.isTyping()) {
                this.navigateTemplate(-1);
            } else if (e.key === 'ArrowRight' && !this.isTyping()) {
                this.navigateTemplate(1);
            }
        });
    }

    isTyping() {
        const activeElement = document.activeElement;
        return activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA');
    }

    navigateTemplate(direction) {
        const newTemplate = this.templateNumber + direction;
        if (newTemplate >= 300 && newTemplate <= 349) {
            window.location.href = `blog${newTemplate}.html`;
        }
    }
}

// Global navigation function for inline onclick handlers
function navigateTemplate(direction) {
    if (window.blogEngine) {
        window.blogEngine.navigateTemplate(direction);
    }
}

// Export for use in templates
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BlogTemplateEngine;
}
