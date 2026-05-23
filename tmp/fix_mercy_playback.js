const fs = require('fs');
const path = require('path');

// Read the index.html file
const indexPath = 'fte_clone/TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/index.html';
let content = fs.readFileSync(indexPath, 'utf8');

// The old playMovieFromBrowse function (lines 3511-3593)
const oldFunction = `        function playMovieFromBrowse(index) {
            _browseScrolling = true;

            var current = document.querySelector('.video-card iframe[src*="autoplay=1"]');
            if (current) {
                var s = current.src;
                current.src = '';
                setTimeout(function() { current.src = s.replace(/autoplay=1/, 'autoplay=0'); }, 50);
            }

            _removeBrowseOverlay();
            document.getElementById('browseView').classList.remove('active');
            document.getElementById('muteOverlay').classList.add('hidden');

            setTimeout(function() {
                var container = document.getElementById('container');
                var targetTop = index * window.innerHeight;
                container.scrollTo({ top: targetTop, behavior: 'instant' });

                setTimeout(function() {
                    var movie = filteredMovies[index];
                    var muted = (videoMuteStates[index] === false) ? 0 : 1;
                    var ytSrc = 'https://www.youtube.com/embed/' + movie.trailer_id +
                        '?autoplay=1&mute=' + muted + '&controls=1&playsinline=1&loop=0&modestbranding=1&rel=0&enablejsapi=1';

                    // Chromium defers iframe rendering at extreme scroll offsets (>500K px).
                    // A fixed overlay at viewport origin forces the compositor to render it.
                    var overlay = document.createElement('div');
                    overlay.id = 'browse-play-overlay';
                    overlay.style.cssText = 'position:fixed;inset:0;z-index:150;background:#000;';

                    var iframe = document.createElement('iframe');
                    iframe.id = 'browse-player-frame';
                    iframe.src = ytSrc;
                    iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
                    iframe.allowFullscreen = true;
                    iframe.style.cssText = 'width:100%;height:100%;border:none;';
                    overlay.appendChild(iframe);

                    var unmBtn = document.createElement('button');
                    unmBtn.textContent = '\uD83D\uDD07 Tap to Unmute';
                    unmBtn.style.cssText = 'position:absolute;bottom:80px;left:50%;transform:translateX(-50%);z-index:10;padding:12px 24px;background:rgba(255,68,68,0.9);color:#fff;border:none;border-radius:12px;font-size:16px;cursor:pointer;';
                    unmBtn.onclick = function() {
                        iframe.src = iframe.src.replace(/mute=1/, 'mute=0');
                        videoMuteStates[index] = false;
                        unmBtn.remove();
                    };
                    if (muted) overlay.appendChild(unmBtn);

                    document.body.appendChild(overlay);

                    if (typeof YT !== 'undefined' && YT.Player) {
                        iframe.addEventListener('load', function onLoad() {
                            iframe.removeEventListener('load', onLoad);
                            console.log('[browse] overlay iframe loaded for ' + movie.title);
                            try {
                                new YT.Player('browse-player-frame', {
                                    events: {
                                        onStateChange: function(event) {
                                            if (event.data === YT.PlayerState.ENDED) {
                                                _removeBrowseOverlay();
                                                var nextIdx = index + 1;
                                                if (nextIdx < filteredMovies.length) {
                                                    container.scrollTo({ top: nextIdx * window.innerHeight, behavior: 'smooth' });
                                                }
                                            }
                                        }
                                    }
                                });
                            } catch(e) {}
                        });
                    }

                    container.addEventListener('scroll', function onScroll() {
                        container.removeEventListener('scroll', onScroll);
                        _removeBrowseOverlay();
                    });

                    _currentlyPlaying = String(index);
                    _browseScrolling = false;
                }, 200);
            }, 350);
        }`;

// The new fixed playMovieFromBrowse function
const newFunction = `        function playMovieFromBrowse(index) {
            _browseScrolling = true;

            // Stop any currently playing video
            var current = document.querySelector('.video-card iframe[src*="autoplay=1"]');
            if (current) {
                var s = current.src;
                current.src = '';
                setTimeout(function() { current.src = s.replace(/autoplay=1/, 'autoplay=0'); }, 50);
            }

            _removeBrowseOverlay();
            document.getElementById('browseView').classList.remove('active');
            document.getElementById('muteOverlay').classList.add('hidden');

            var movie = filteredMovies[index];
            if (!movie || !movie.trailer_id) {
                console.error('[playMovieFromBrowse] No movie or trailer_id at index', index);
                _browseScrolling = false;
                return;
            }

            var container = document.getElementById('container');
            var targetTop = index * window.innerHeight;
            var muted = (videoMuteStates[index] === false) ? 0 : 1;
            
            // Pre-create the overlay before scrolling to ensure it's ready
            var ytSrc = 'https://www.youtube.com/embed/' + movie.trailer_id +
                '?autoplay=1&mute=' + muted + '&controls=1&playsinline=1&loop=0&modestbranding=1&rel=0&enablejsapi=1';

            // Chromium defers iframe rendering at extreme scroll offsets (>500K px).
            // We need multiple techniques to force the compositor to render:
            // 1. position:fixed at viewport origin (already done)
            // 2. loading="eager" to prevent lazy loading
            // 3. opacity:1 and visibility:visible to force paint
            // 4. transform:translateZ(0) to force GPU layer
            // 5. will-change:transform hint
            var overlay = document.createElement('div');
            overlay.id = 'browse-play-overlay';
            overlay.style.cssText = 'position:fixed;inset:0;z-index:150;background:#000;opacity:1;visibility:visible;transform:translateZ(0);will-change:transform;';

            var iframe = document.createElement('iframe');
            iframe.id = 'browse-player-frame';
            iframe.src = ytSrc;
            iframe.setAttribute('loading', 'eager');
            iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
            iframe.allowFullscreen = true;
            iframe.style.cssText = 'width:100%;height:100%;border:none;opacity:1;visibility:visible;transform:translateZ(0);';
            
            // Force iframe to be considered "contentful" by adding it to DOM immediately
            overlay.appendChild(iframe);
            document.body.appendChild(overlay);

            // Force a reflow to ensure the compositor picks up the iframe
            overlay.offsetHeight;
            iframe.offsetHeight;

            // Now scroll to the target position
            container.scrollTo({ top: targetTop, behavior: 'instant' });

            // Add unmute button
            var unmBtn = document.createElement('button');
            unmBtn.id = 'browse-unmute-btn';
            unmBtn.textContent = '\uD83D\uDD07 Tap to Unmute';
            unmBtn.style.cssText = 'position:absolute;bottom:80px;left:50%;transform:translateX(-50%);z-index:1000;padding:12px 24px;background:rgba(255,68,68,0.95);color:#fff;border:none;border-radius:12px;font-size:16px;cursor:pointer;opacity:1;visibility:visible;';
            unmBtn.onclick = function() {
                iframe.src = iframe.src.replace(/mute=1/, 'mute=0');
                videoMuteStates[index] = false;
                unmBtn.remove();
            };
            if (muted) overlay.appendChild(unmBtn);

            // Set up YouTube player API if available
            if (typeof YT !== 'undefined' && YT.Player) {
                iframe.addEventListener('load', function onLoad() {
                    iframe.removeEventListener('load', onLoad);
                    console.log('[browse] overlay iframe loaded for ' + movie.title);
                    try {
                        new YT.Player('browse-player-frame', {
                            events: {
                                onStateChange: function(event) {
                                    if (event.data === YT.PlayerState.ENDED) {
                                        _removeBrowseOverlay();
                                        var nextIdx = index + 1;
                                        if (nextIdx < filteredMovies.length) {
                                            container.scrollTo({ top: nextIdx * window.innerHeight, behavior: 'smooth' });
                                        }
                                    }
                                }
                            }
                        });
                    } catch(e) {}
                });
            }

            // Remove overlay on scroll
            container.addEventListener('scroll', function onScroll() {
                container.removeEventListener('scroll', onScroll);
                _removeBrowseOverlay();
            });

            _currentlyPlaying = String(index);
            _browseScrolling = false;
        }`;

// Replace the function
if (content.includes(oldFunction)) {
    content = content.replace(oldFunction, newFunction);
    console.log('✅ Successfully replaced playMovieFromBrowse function');
} else {
    console.log('⚠️ Could not find exact function match, trying alternative approach...');
    
    // Try to find and replace using the function signature
    const functionStart = 'function playMovieFromBrowse(index) {';
    const functionEnd = '_browseScrolling = false;\n        }';
    
    const startIdx = content.indexOf(functionStart);
    if (startIdx === -1) {
        console.error('❌ Could not find playMovieFromBrowse function');
        process.exit(1);
    }
    
    // Find the end of the function by looking for the pattern after the function
    const searchAfterStart = content.indexOf('_browseScrolling = false;', startIdx);
    const endIdx = content.indexOf('}', searchAfterStart);
    
    if (startIdx === -1 || endIdx === -1) {
        console.error('❌ Could not find function boundaries');
        process.exit(1);
    }
    
    const beforeFunction = content.substring(0, startIdx);
    const afterFunction = content.substring(endIdx + 1);
    content = beforeFunction + newFunction + afterFunction;
    console.log('✅ Successfully replaced playMovieFromBrowse function (alternative method)');
}

// Write the updated file
fs.writeFileSync(indexPath, content);
console.log('✅ File saved:', indexPath);

// Also create a backup
const backupPath = indexPath + '.backup_' + Date.now();
fs.writeFileSync(backupPath, fs.readFileSync(indexPath));
console.log('✅ Backup saved:', backupPath);
