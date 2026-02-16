// Auto-scroll settings
let autoScrollSettings = {
    enabled: false,
    delay: 10 // default 10 seconds
};
let autoScrollTimeout = null;

// Load auto-scroll settings from localStorage
function loadAutoScrollSettings() {
    const saved = localStorage.getItem('autoScrollSettings');
    if (saved) {
        autoScrollSettings = JSON.parse(saved);
    }

    // Update UI
    document.getElementById('autoScrollToggle').checked = autoScrollSettings.enabled;
    document.getElementById('autoScrollDelay').value = autoScrollSettings.delay;
    document.getElementById('delayValue').textContent = autoScrollSettings.delay;

    // Show/hide delay container
    const delayContainer = document.getElementById('autoScrollDelayContainer');
    if (autoScrollSettings.enabled) {
        delayContainer.style.display = 'flex';
    } else {
        delayContainer.style.display = 'none';
    }
}

// Save auto-scroll settings to localStorage
function saveAutoScrollSettings() {
    localStorage.setItem('autoScrollSettings', JSON.stringify(autoScrollSettings));
}

// Toggle auto-scroll on/off
function toggleAutoScroll() {
    autoScrollSettings.enabled = document.getElementById('autoScrollToggle').checked;
    saveAutoScrollSettings();

    const delayContainer = document.getElementById('autoScrollDelayContainer');
    if (autoScrollSettings.enabled) {
        delayContainer.style.display = 'flex';
        console.log('Auto-scroll enabled with', autoScrollSettings.delay, 'second delay');
    } else {
        delayContainer.style.display = 'none';
        // Clear any pending auto-scroll
        if (autoScrollTimeout) {
            clearTimeout(autoScrollTimeout);
            autoScrollTimeout = null;
        }
        console.log('Auto-scroll disabled');
    }
}

// Update auto-scroll delay
function updateAutoScrollDelay(value) {
    autoScrollSettings.delay = parseInt(value);
    document.getElementById('delayValue').textContent = value;
    saveAutoScrollSettings();
    console.log('Auto-scroll delay updated to', value, 'seconds');
}

// Trigger auto-scroll to next video
function triggerAutoScroll() {
    if (!autoScrollSettings.enabled) return;

    // Clear any existing timeout
    if (autoScrollTimeout) {
        clearTimeout(autoScrollTimeout);
    }

    // Set new timeout
    autoScrollTimeout = setTimeout(() => {
        const cards = document.querySelectorAll('.video-card');
        if (cards.length === 0) return;

        // Find current playing card
        let currentIndex = -1;
        cards.forEach((card, index) => {
            const rect = card.getBoundingClientRect();
            const isInView = rect.top >= 0 && rect.top < window.innerHeight / 2;
            if (isInView) {
                currentIndex = index;
            }
        });

        // Scroll to next card
        const nextIndex = currentIndex + 1;
        if (nextIndex < cards.length) {
            cards[nextIndex].scrollIntoView({ behavior: 'smooth', block: 'start' });
            console.log('Auto-scrolled to video', nextIndex + 1);
        } else {
            // Loop back to first video
            cards[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
            console.log('Auto-scrolled back to first video');
        }
    }, autoScrollSettings.delay * 1000);
}
