# MovieShows V3 - Bug Fix Implementation Plan

## Issues Identified

### 1. **Z-Index Overlap: Unmute Button Over Share Icon**
- **Current State**: Unmute button has `z-index: 12`, Sidebar actions have `z-index: 15`
- **Problem**: Unmute button appears on top of the share (🔗) icon
- **Root Cause**: Unmute button is positioned `bottom: 80px; right: 20px` which overlaps with sidebar actions at `right: 16px; bottom: 100px`
- **Solution**: Lower unmute button z-index to `10` (below sidebar actions)

### 2. **Browse View Click-to-Play Not Working (Console Closed)**
- **Current State**: Works with DevTools open, fails when closed
- **Problem**: Timing issue - `playMovieFromBrowse()` scrolls but doesn't trigger autoplay reliably
- **Root Cause**: Race condition between scroll completion and video load
- **Solution**: Use `scrollend` event or longer timeout to ensure scroll completes before triggering play

### 3. **Database Only Returns 200 Items**
- **Current State**: API returns exactly 200 movies (100 movies + 100 TV shows)
- **Problem**: Database should have more items based on population script
- **Root Cause**: Need to verify API query limit and database actual count
- **Solution**: Check `get-movies.php` for LIMIT clause and verify database contents

### 4. **Top Filter Buttons (All/Movies/TV) May Not Re-Initialize Autoplay**
- **Current State**: `filterContent()` now calls `setupScrollAutoplay()` after rendering
- **Problem**: Need to verify this works across all scenarios
- **Solution**: Comprehensive testing with Puppeteer

## Implementation Steps

### Phase 1: Code Fixes (15 minutes)

#### Fix 1.1: Unmute Button Z-Index
**File**: `index.html` line ~752
```html
<!-- Change from z-index: 12 to z-index: 10 -->
.unmute-btn {
    z-index: 10;  /* Below sidebar actions (15) */
}
```

#### Fix 1.2: Browse Click-to-Play Reliability
**File**: `index.html` line ~1570
```javascript
function playMovieFromBrowse(index) {
    // Stop ALL currently playing videos first
    document.querySelectorAll('.video-card iframe').forEach(iframe => {
        const currentSrc = iframe.src;
        if (currentSrc && currentSrc.includes('autoplay=1')) {
            iframe.src = '';
            setTimeout(() => {
                iframe.src = currentSrc.replace(/autoplay=1/, 'autoplay=0');
            }, 50);
        }
    });

    // Close browse view
    document.getElementById('browseView').classList.remove('active');

    // Wait for transition, then scroll
    setTimeout(() => {
        const container = document.getElementById('container');
        container.scrollTo({
            top: index * window.innerHeight,
            behavior: 'smooth'
        });
        
        // Use scrollend event for reliable timing
        const handleScrollEnd = () => {
            const targetIframe = document.getElementById(`player-${index}`);
            if (targetIframe) {
                const currentSrc = targetIframe.src;
                if (!currentSrc.includes('autoplay=1')) {
                    targetIframe.src = currentSrc.replace(/autoplay=[01]/, 'autoplay=1');
                }
            }
            updateMuteOverlay();
            container.removeEventListener('scrollend', handleScrollEnd);
        };
        
        // Fallback for browsers without scrollend
        if ('onscrollend' in container) {
            container.addEventListener('scrollend', handleScrollEnd, { once: true });
        } else {
            setTimeout(handleScrollEnd, 800);
        }
    }, 350);
}
```

#### Fix 1.3: Verify Database Count
**File**: `api/get-movies.php`
- Check for LIMIT clause
- Verify actual database row count
- Remove or increase LIMIT if present

### Phase 2: Puppeteer Testing Suite (30 minutes)

#### Test Suite 1: Z-Index & Layout Tests (25 tests)
```javascript
// File: tests/z-index-layout.test.js
describe('Z-Index and Layout Tests', () => {
    test('Unmute button does not overlap sidebar actions', async () => {
        // Get bounding boxes of unmute button and all sidebar action buttons
        // Verify no overlap
    });
    
    test('Unmute button is clickable', async () => {
        // Click unmute button
        // Verify it responds
    });
    
    test('Share button is clickable when unmute button is visible', async () => {
        // Ensure both buttons are visible
        // Click share button
        // Verify it responds
    });
    
    // ... 22 more layout tests
});
```

#### Test Suite 2: Filter Functionality Tests (25 tests)
```javascript
// File: tests/filter-functionality.test.js
describe('Filter Functionality Tests', () => {
    test('All filter shows all 200+ movies', async () => {
        // Click "All" button
        // Verify count matches total
        // Verify videos are rendered
    });
    
    test('Movies filter shows only movies', async () => {
        // Click "Movies" button
        // Verify all items have type='movie'
    });
    
    test('TV filter shows only TV shows', async () => {
        // Click "TV" button
        // Verify all items have type='tv'
    });
    
    test('Filter buttons re-initialize scroll autoplay', async () => {
        // Click filter button
        // Scroll to second video
        // Verify autoplay triggers
    });
    
    // ... 21 more filter tests
});
```

#### Test Suite 3: Browse View Tests (25 tests)
```javascript
// File: tests/browse-view.test.js
describe('Browse View Click-to-Play Tests', () => {
    test('Clicking movie from browse triggers autoplay (DevTools closed)', async () => {
        // Open browse view
        // Click a movie
        // Verify video autoplays
        // Verify mute overlay appears
    });
    
    test('Clicking movie from browse scrolls to correct position', async () => {
        // Click movie at index 50
        // Verify scroll position matches
    });
    
    test('Previous videos stop when playing from browse', async () => {
        // Play video 1
        // Click video 10 from browse
        // Verify video 1 is stopped
    });
    
    // ... 22 more browse tests
});
```

#### Test Suite 4: Autoplay & Mute Tests (25 tests)
```javascript
// File: tests/autoplay-mute.test.js
describe('Autoplay and Mute Tests', () => {
    test('First video autoplays on page load', async () => {
        // Load page
        // Wait for first video
        // Verify autoplay=1 in iframe src
    });
    
    test('Mute overlay appears when all videos are muted', async () => {
        // Verify mute overlay is visible
    });
    
    test('Unmute button toggles mute state', async () => {
        // Click unmute
        // Verify iframe src changes to mute=0
        // Verify button icon changes
    });
    
    test('Scrolling to new video stops previous video', async () => {
        // Play video 1
        // Scroll to video 2
        // Verify video 1 iframe src is removed then restored with autoplay=0
    });
    
    // ... 21 more autoplay/mute tests
});
```

### Phase 3: Validation & Deployment (15 minutes)

1. **Run all 100 Puppeteer tests**
   - Verify 100% pass rate
   - Review any failures
   - Fix and re-test

2. **Manual verification**
   - Test on local server
   - Test with DevTools closed
   - Test all filter combinations
   - Test browse view click-to-play

3. **Deploy to production**
   - Commit changes with descriptive message
   - Push to repository
   - Deploy to hosting

## Success Criteria

- ✅ All 100 Puppeteer tests pass
- ✅ Unmute button does not overlap any sidebar icons
- ✅ Browse view click-to-play works with DevTools closed
- ✅ All filter buttons work correctly
- ✅ Database returns all available movies (not limited to 200)
- ✅ Autoplay works after filtering
- ✅ Mute overlay appears correctly
- ✅ Previous videos stop when scrolling to new ones

## Timeline

- **Phase 1 (Code Fixes)**: 15 minutes
- **Phase 2 (Testing Suite)**: 30 minutes
- **Phase 3 (Validation)**: 15 minutes
- **Total**: 60 minutes

## Notes

- The passive event listener warnings are from YouTube's iframe and can be ignored
- CORS errors from Google ads are expected and don't affect functionality
- Current database has exactly 200 items - need to verify if this is intentional or a limit
