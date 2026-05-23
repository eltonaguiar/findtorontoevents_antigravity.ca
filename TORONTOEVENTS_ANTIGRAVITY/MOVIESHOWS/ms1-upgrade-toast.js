/**
 * MS1 Upgrade Toast — Shows a non-intrusive banner offering to visit MS2/MS3
 * Self-contained, no dependencies. Deployed via deploy-movieshows-all.yml.
 */
(function() {
    'use strict';

    // Don't show if user already dismissed
    var DISMISSED_KEY = 'ms1-upgrade-dismissed';
    var dismissed = null;
    try { dismissed = localStorage.getItem(DISMISSED_KEY); } catch(e) {}
    if (dismissed) return;

    // Wait for DOM
    function init() {
        var banner = document.createElement('div');
        banner.id = 'ms1-upgrade-banner';
        banner.innerHTML =
            '<div class="ms1ub-content">' +
                '<div class="ms1ub-icon">&#127916;</div>' +
                '<div class="ms1ub-text">' +
                    '<div class="ms1ub-title">Newer versions available!</div>' +
                    '<div class="ms1ub-desc">Check out <b>Film Vault</b> (MovieShows 2) and <b>Binge Mode</b> (MovieShows 3) for a better experience with more features.</div>' +
                '</div>' +
                '<div class="ms1ub-actions">' +
                    '<a class="ms1ub-btn ms1ub-btn-primary" href="../MOVIESHOWS2/">Film Vault (MS2)</a>' +
                    '<a class="ms1ub-btn ms1ub-btn-secondary" href="../MOVIESHOWS3/">Binge Mode (MS3)</a>' +
                    '<button class="ms1ub-dismiss" title="Dismiss">&#10005;</button>' +
                '</div>' +
            '</div>';
        document.body.appendChild(banner);

        // Animate in
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                banner.classList.add('active');
            });
        });

        // Dismiss handler
        banner.querySelector('.ms1ub-dismiss').addEventListener('click', function() {
            banner.classList.remove('active');
            setTimeout(function() { banner.remove(); }, 400);
            try { localStorage.setItem(DISMISSED_KEY, '1'); } catch(e) {}
        });

        // Auto-dismiss after 30 seconds
        setTimeout(function() {
            if (banner.parentNode) {
                banner.classList.remove('active');
                setTimeout(function() { banner.remove(); }, 400);
            }
        }, 30000);
    }

    // Inject CSS
    var style = document.createElement('style');
    style.textContent =
        '#ms1-upgrade-banner {' +
            'position:fixed;bottom:0;left:0;right:0;z-index:9999;' +
            'transform:translateY(100%);transition:transform 0.4s cubic-bezier(0.16,1,0.3,1);' +
            'pointer-events:none;padding:12px;' +
        '}' +
        '#ms1-upgrade-banner.active { transform:translateY(0); }' +
        '.ms1ub-content {' +
            'max-width:700px;margin:0 auto;display:flex;align-items:center;gap:14px;' +
            'background:rgba(15,15,30,0.95);backdrop-filter:blur(20px);' +
            'border:1px solid rgba(139,92,246,0.4);border-radius:16px;' +
            'padding:16px 20px;box-shadow:0 -4px 32px rgba(0,0,0,0.4);' +
            'pointer-events:auto;flex-wrap:wrap;' +
        '}' +
        '.ms1ub-icon { font-size:32px;flex-shrink:0; }' +
        '.ms1ub-text { flex:1;min-width:180px; }' +
        '.ms1ub-title { color:white;font-size:15px;font-weight:700;margin-bottom:4px; }' +
        '.ms1ub-desc { color:rgba(255,255,255,0.6);font-size:12px;line-height:1.4; }' +
        '.ms1ub-desc b { color:#c4b5fd; }' +
        '.ms1ub-actions { display:flex;gap:8px;align-items:center;flex-shrink:0; }' +
        '.ms1ub-btn {' +
            'padding:8px 16px;border-radius:10px;border:none;' +
            'font-size:13px;font-weight:700;cursor:pointer;text-decoration:none;' +
            'transition:opacity 0.2s;white-space:nowrap;' +
        '}' +
        '.ms1ub-btn:hover { opacity:0.85; }' +
        '.ms1ub-btn-primary { background:linear-gradient(135deg,#8b5cf6,#7c3aed);color:white; }' +
        '.ms1ub-btn-secondary { background:rgba(245,158,11,0.25);color:#f59e0b;border:1px solid rgba(245,158,11,0.4); }' +
        '.ms1ub-dismiss {' +
            'width:28px;height:28px;border-radius:50%;border:1px solid rgba(255,255,255,0.15);' +
            'background:rgba(255,255,255,0.08);color:rgba(255,255,255,0.5);' +
            'font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;' +
            'padding:0;flex-shrink:0;' +
        '}' +
        '.ms1ub-dismiss:hover { background:rgba(255,255,255,0.15); }' +
        '@media (max-width:600px) {' +
            '.ms1ub-content { flex-direction:column;text-align:center;gap:10px; }' +
            '.ms1ub-actions { justify-content:center; }' +
        '}';
    document.head.appendChild(style);

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        setTimeout(init, 1500);
    }
})();
