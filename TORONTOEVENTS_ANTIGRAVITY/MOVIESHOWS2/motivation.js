/**
 * Motivation Videos Module for MOVIESHOWS2
 * Ported from MOVIESHOWS3 — adds curated motivational YouTube content
 * with filter tab, settings, and YouTube iframe playback
 */

// ── Data ──────────────────────────────────────────────────────────
const MOTIVATION_CHANNELS = [
    {
        channel: 'Motiversity',
        videos: [
            { id: 'wnHW6o8WMas', title: 'NO EXCUSES - Best Motivational Video', duration: '10:15', isShort: false },
            { id: 'mgmVOAJgBKI', title: 'WINNERS MINDSET - Powerful Motivational Speech', duration: '11:32', isShort: false },
            { id: 'tbnzAVRZ9Xc', title: 'THIS IS YOUR SIGN - Best Motivational Speech', duration: '13:45', isShort: false },
            { id: 'qzOFs4hSG5I', title: 'THE MINDSET OF A WINNER - Motivational Speech', duration: '15:20', isShort: false },
            { id: 'Ur_kBBVKauw', title: 'PROVE THEM WRONG - Motivational Speech', duration: '12:08', isShort: false },
            { id: '1XHfiEoNQBI', title: 'NEVER GIVE UP - Best Motivational Speech', duration: '14:52', isShort: false },
            { id: 'k9zTr2MAFRg', title: 'RISE UP - Powerful Motivation', duration: '11:40', isShort: false },
            { id: 'pxBQLFLei70', title: 'MAKE IT HAPPEN - Motivational Speech', duration: '16:22', isShort: false }
        ]
    },
    {
        channel: 'MotivationHub',
        videos: [
            { id: 'A14OxK7iOcI', title: 'THE LION MINDSET - Motivational Speech Compilation', duration: '28:15', isShort: false },
            { id: 'bMknL96fwbI', title: 'OBSESSED - Motivational Speech', duration: '12:45', isShort: false },
            { id: 'g_SwGy0YAzc', title: 'DISCIPLINE YOUR MIND - Best Motivational Speech', duration: '22:10', isShort: false },
            { id: 'kNMbZ8KUCGQ', title: 'WHEN LIFE HITS YOU - Motivational Speech', duration: '18:30', isShort: false }
        ]
    },
    {
        channel: 'Ben Lionel Scott',
        videos: [
            { id: 'DGKMb0f0Ndw', title: 'NOTHING IS IMPOSSIBLE - Powerful Motivational Speech', duration: '10:00', isShort: false },
            { id: 'JwLayhG5F0s', title: 'THE COMEBACK - Motivational Speech', duration: '15:30', isShort: false },
            { id: 'TjnDYkkcDwk', title: 'GO AFTER YOUR DREAMS - Motivational Video', duration: '12:00', isShort: false },
            { id: '2GvyYWD-HTI', title: 'BECOME UNSTOPPABLE - Motivational Speech', duration: '14:20', isShort: false }
        ]
    },
    {
        channel: 'Be Inspired',
        videos: [
            { id: '5fsm-QzhL0M', title: 'STAY HARD - Best Motivational Speech (David Goggins)', duration: '20:15', isShort: false },
            { id: '1Ho2oY1CkjE', title: 'BELIEVE IN YOURSELF - Motivational Speech', duration: '18:45', isShort: false }
        ]
    },
    {
        channel: 'Fearless Motivation',
        videos: [
            { id: 'gXvuJu1kt48', title: 'RELENTLESS - Best Motivational Speech', duration: '10:30', isShort: false },
            { id: 'V6xLYt265ZM', title: 'RISE AND GRIND - Morning Motivation', duration: '8:45', isShort: false },
            { id: 'IHhAbMFkNDI', title: 'LIMITLESS - Motivational Speech', duration: '12:20', isShort: false },
            { id: 'Pb5oIIPO62g', title: 'CHAMPION MENTALITY - Motivational Video', duration: '15:10', isShort: false }
        ]
    },
    {
        channel: 'Motivation2Study',
        videos: [
            { id: 'hbkKdryzf_E', title: 'STUDY MOTIVATION - You Can Do This!', duration: '11:00', isShort: false },
            { id: 'Yc791lCWrk4', title: 'FOCUS - Study Motivation', duration: '14:30', isShort: false }
        ]
    },
    {
        channel: 'Absolute Motivation',
        videos: [
            { id: 'dDGdNGq9lKg', title: 'THE GREATEST MOTIVATION - Best Speeches', duration: '25:00', isShort: false }
        ]
    },
    {
        channel: 'GaryVee',
        videos: [
            { id: 'K5waqFRIlOQ', title: 'Stop Making Excuses', duration: '0:58', isShort: true },
            { id: 'RTowMhKCkGk', title: 'The KEY to Happiness', duration: '0:45', isShort: true },
            { id: 'N1S3JDh0s8I', title: 'PATIENCE IS THE KEY - GaryVee Motivation', duration: '12:30', isShort: false },
            { id: 'JJbeoFz5GYA', title: 'WORK ETHIC - GaryVee Best Speeches', duration: '15:00', isShort: false }
        ]
    },
    {
        channel: 'Evan Carmichael',
        videos: [
            { id: 'PVrLKdVyM98', title: 'TOP 10 Rules for SUCCESS - Compilation', duration: '25:40', isShort: false },
            { id: 'ug1yF3heuuM', title: 'BELIEVE IN YOURSELF - Best Motivation', duration: '20:00', isShort: false }
        ]
    },
    {
        channel: 'Eric Thomas',
        videos: [
            { id: 'V689VxMa9oY', title: 'HOW BAD DO YOU WANT IT? - Eric Thomas', duration: '7:12', isShort: false },
            { id: 'JC82Il2cjqA', title: 'WHEN YOU WANT TO SUCCEED - Eric Thomas', duration: '5:50', isShort: false },
            { id: 'tYzMYcUty6s', title: 'I CAN. I WILL. I MUST. - Best Speech', duration: '12:00', isShort: false }
        ]
    },
    {
        channel: 'Tony Robbins',
        videos: [
            { id: 'fFSo0oYJelk', title: 'CHANGE YOUR MINDSET - Tony Robbins Motivation', duration: '18:00', isShort: false },
            { id: 'wVjcPMCGsBM', title: 'THE POWER OF DECISION - Tony Robbins', duration: '14:20', isShort: false },
            { id: 'x7qh3Fox_Xw', title: 'TAKE CONTROL OF YOUR LIFE - Best Speech', duration: '22:30', isShort: false }
        ]
    },
    {
        channel: 'David Goggins',
        videos: [
            { id: 'oIrT1eHs1b0', title: 'Stay Hard', duration: '0:42', isShort: true },
            { id: 'B_S77MwEOcE', title: 'Who\'s gonna carry the boats?', duration: '0:55', isShort: true },
            { id: 'TLKxdTmk-zc', title: 'Mental Toughness', duration: '0:38', isShort: true },
            { id: '78I9dTB9vqM', title: 'SUFFER MORE - David Goggins Motivation', duration: '15:00', isShort: false },
            { id: 'n_mYaCRNh4s', title: 'CALLOUS YOUR MIND - Best Goggins Speech', duration: '20:15', isShort: false },
            { id: 'P4CYntQR_gg', title: 'YOU DONT KNOW ME SON - Goggins Best', duration: '12:45', isShort: false },
            { id: 'gDJG3VLelME', title: 'WHO IS GOING TO CARRY THE BOATS - Full Speech', duration: '10:30', isShort: false }
        ]
    }
];

// ── State ─────────────────────────────────────────────────────────
let allMotivationalVideos = [];
let motivationSettings = {
    showInAll: false,
    showLongForm: true
};

// ── Build Videos ──────────────────────────────────────────────────
function buildMotivationalVideos() {
    allMotivationalVideos = [];
    let idCounter = 100000;
    const currentYear = new Date().getFullYear();

    MOTIVATION_CHANNELS.forEach(channel => {
        channel.videos.forEach(video => {
            if (!motivationSettings.showLongForm && !video.isShort) return;

            allMotivationalVideos.push({
                id: 'mot_' + idCounter++,
                title: video.title,
                type: 'motivation',
                year: currentYear,
                description: `${channel.channel} - Motivational ${video.isShort ? 'Short' : 'Video'}`,
                thumbnail: `https://img.youtube.com/vi/${video.id}/hqdefault.jpg`,
                videoUrl: null, // No direct video URL — uses YouTube iframe
                _youtubeId: video.id,
                _isMotivation: true,
                _channel: channel.channel,
                _duration: video.duration,
                _isShort: video.isShort
            });
        });
    });

    // Fisher-Yates shuffle
    for (let i = allMotivationalVideos.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [allMotivationalVideos[i], allMotivationalVideos[j]] = [allMotivationalVideos[j], allMotivationalVideos[i]];
    }
}

// ── Settings ──────────────────────────────────────────────────────
function loadMotivationSettings() {
    const saved = localStorage.getItem('ms2_motivationSettings');
    if (saved) {
        try { motivationSettings = JSON.parse(saved); } catch(e) {}
    }
}

function saveMotivationSettings() {
    localStorage.setItem('ms2_motivationSettings', JSON.stringify(motivationSettings));
}

// ── YouTube Iframe Player ─────────────────────────────────────────
let _ytIframe = null;

function playYouTubeVideo(youtubeId) {
    const playerSection = document.querySelector('.player-section') || document.querySelector('[class*="player"]');
    if (!playerSection) return;

    // Hide the HTML5 video player
    const videoPlayer = document.getElementById('videoPlayer');
    if (videoPlayer) videoPlayer.style.display = 'none';

    // Create or reuse YouTube iframe
    if (!_ytIframe) {
        _ytIframe = document.createElement('iframe');
        _ytIframe.id = 'ms2-yt-player';
        _ytIframe.style.cssText = 'width:100%;aspect-ratio:16/9;border:none;border-radius:8px;background:#000;';
        _ytIframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
        _ytIframe.allowFullscreen = true;

        // Insert before/after the video player
        const wrapper = videoPlayer ? videoPlayer.parentElement : playerSection;
        if (videoPlayer) {
            wrapper.insertBefore(_ytIframe, videoPlayer);
        } else {
            playerSection.prepend(_ytIframe);
        }
    }

    _ytIframe.style.display = 'block';
    _ytIframe.src = `https://www.youtube.com/embed/${youtubeId}?autoplay=1&rel=0&modestbranding=1&enablejsapi=1`;
}

function hideYouTubePlayer() {
    if (_ytIframe) {
        _ytIframe.src = 'about:blank';
        _ytIframe.style.display = 'none';
    }
    const videoPlayer = document.getElementById('videoPlayer');
    if (videoPlayer) videoPlayer.style.display = '';
}

// ── Hook into MS2's playVideo ─────────────────────────────────────
(function patchPlayVideo() {
    // Wait for script.js to define playVideo
    const check = setInterval(() => {
        if (typeof window.playVideo === 'function' || typeof playVideo === 'function') {
            clearInterval(check);

            const _origPlayVideo = window.playVideo || playVideo;
            const patched = function(item) {
                if (item && item._youtubeId) {
                    // YouTube content — use iframe
                    if (typeof appState !== 'undefined') {
                        appState.currentVideo = item;
                    }
                    const titleEl = document.getElementById('currentTitle');
                    const descEl = document.getElementById('currentDescription');
                    if (titleEl) titleEl.textContent = item.title;
                    if (descEl) descEl.textContent = item.description || '';

                    playYouTubeVideo(item._youtubeId);
                    return;
                }
                // Regular content — hide YT iframe, use original player
                hideYouTubePlayer();
                _origPlayVideo.call(this, item);
            };

            // Replace globally
            if (typeof window.playVideo !== 'undefined') window.playVideo = patched;
            // Also try to replace the module-scoped reference via prototype chain
            try {
                const scriptEl = document.querySelector('script[src*="script.js"]');
                if (scriptEl) window.playVideo = patched;
            } catch(e) {}
        }
    }, 100);

    // Timeout safety
    setTimeout(() => clearInterval(check), 10000);
})();

// ── Hook into MS2's filterContent ─────────────────────────────────
(function patchFilterContent() {
    const check = setInterval(() => {
        if (typeof window.filterContent === 'function' || typeof filterContent === 'function') {
            clearInterval(check);

            const _origFilterContent = window.filterContent || filterContent;
            const patched = function() {
                if (typeof appState === 'undefined') return _origFilterContent.call(this);

                if (appState.currentFilter === 'motivation') {
                    appState.filteredContent = [...allMotivationalVideos];
                    if (typeof sortAndFilterContent === 'function') {
                        sortAndFilterContent();
                    }
                    return;
                }

                // For 'all' filter, optionally include motivation videos
                _origFilterContent.call(this);

                if (appState.currentFilter === 'all' && motivationSettings.showInAll) {
                    appState.filteredContent = [...appState.filteredContent, ...allMotivationalVideos];
                    if (typeof sortAndFilterContent === 'function') {
                        sortAndFilterContent();
                    }
                }
            };

            if (typeof window.filterContent !== 'undefined') window.filterContent = patched;
        }
    }, 100);

    setTimeout(() => clearInterval(check), 10000);
})();

// ── Hook into MS2's createContentItem for motivation badges ──────
(function patchCreateContentItem() {
    const check = setInterval(() => {
        if (typeof window.createContentItem === 'function' || typeof createContentItem === 'function') {
            clearInterval(check);

            const _origCreate = window.createContentItem || createContentItem;
            const patched = function(item) {
                const el = _origCreate.call(this, item);

                if (item._isMotivation && el) {
                    // Add motivation badge
                    const info = el.querySelector('.content-info') || el.querySelector('[class*="info"]');
                    if (info) {
                        const badge = document.createElement('span');
                        badge.className = 'motivation-badge';
                        badge.textContent = 'MOTIVATION';
                        badge.style.cssText = 'background:linear-gradient(135deg,#8b5cf6,#7c3aed);color:white;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:800;text-transform:uppercase;margin-right:4px;';
                        info.prepend(badge);

                        // Add channel badge
                        if (item._channel) {
                            const chBadge = document.createElement('span');
                            chBadge.textContent = item._channel;
                            chBadge.style.cssText = 'background:rgba(139,92,246,0.3);border:1px solid rgba(139,92,246,0.5);color:#c4b5fd;padding:2px 8px;border-radius:10px;font-size:9px;font-weight:600;margin-right:4px;';
                            info.prepend(chBadge);
                        }
                    }
                }
                return el;
            };

            if (typeof window.createContentItem !== 'undefined') window.createContentItem = patched;
        }
    }, 100);

    setTimeout(() => clearInterval(check), 10000);
})();

// ── Inject UI (filter button + settings) ──────────────────────────
function injectMotivationUI() {
    // Add filter button
    const filterBtns = document.querySelectorAll('.filter-btn');
    if (filterBtns.length > 0) {
        const lastBtn = filterBtns[filterBtns.length - 1];
        const motBtn = document.createElement('button');
        motBtn.className = 'filter-btn';
        motBtn.dataset.filter = 'motivation';
        motBtn.style.cssText = 'color:#c4b5fd;';
        motBtn.textContent = `Motivation (${allMotivationalVideos.length})`;
        motBtn.addEventListener('click', function() {
            filterBtns.forEach(b => b.classList.remove('active'));
            motBtn.classList.remove('active');
            motBtn.classList.add('active');
            if (typeof appState !== 'undefined') {
                appState.currentFilter = 'motivation';
                if (typeof filterContent === 'function') filterContent();
                else if (typeof window.filterContent === 'function') window.filterContent();
            }
        });

        // Insert after last filter button
        lastBtn.parentNode.insertBefore(motBtn, lastBtn.nextSibling);

        // Hook existing filter buttons to remove active from motivation button
        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => motBtn.classList.remove('active'));
        });
    }

    // Add CSS
    const style = document.createElement('style');
    style.textContent = `
        .motivation-badge {
            background: linear-gradient(135deg, #8b5cf6, #7c3aed);
            color: white; padding: 2px 8px; border-radius: 10px;
            font-size: 9px; font-weight: 800; text-transform: uppercase;
        }
        #ms2-yt-player {
            max-height: 70vh;
        }
    `;
    document.head.appendChild(style);
}

// ── Init ──────────────────────────────────────────────────────────
function initMotivation() {
    loadMotivationSettings();
    buildMotivationalVideos();
    injectMotivationUI();
    console.log(`💪 Motivation module loaded: ${allMotivationalVideos.length} videos from ${MOTIVATION_CHANNELS.length} channels`);
}

// Run after DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(initMotivation, 500));
} else {
    setTimeout(initMotivation, 500);
}
