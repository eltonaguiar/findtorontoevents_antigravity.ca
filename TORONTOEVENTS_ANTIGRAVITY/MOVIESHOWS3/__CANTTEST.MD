# Items That Cannot Be Properly Tested Automatically

## ❌ Cannot Test Automatically

### 1. **Audio Mute/Unmute Functionality**
- **Why**: Browser autoplay policies prevent automated tests from verifying actual audio playback
- **Limitation**: YouTube iframe API doesn't expose mute state to external scripts due to security
- **Manual Test Required**: User must manually click unmute and verify audio plays

### 2. **YouTube Video Playback Quality**
- **Why**: YouTube's player is in an iframe with cross-origin restrictions
- **Limitation**: Cannot verify if video actually plays vs. just loads
- **Manual Test Required**: Visual confirmation that videos play smoothly

### 3. **Actual "Now Playing" and "Out This Week" Data Accuracy**
- **Why**: Requires real-time TMDB API data or manual curation
- **Limitation**: Test can only verify filter logic, not if movies are actually in theaters
- **Manual Test Required**: Cross-reference with actual theater listings

### 4. **Mobile/Touch Interactions**
- **Why**: Playwright/Puppeteer simulate desktop browsers
- **Limitation**: Cannot test swipe gestures, touch scrolling behavior
- **Manual Test Required**: Test on actual mobile devices

### 5. **Cross-Browser Compatibility (Safari, iOS)**
- **Why**: Playwright on Windows cannot launch Safari
- **Limitation**: Safari has unique autoplay and video handling
- **Manual Test Required**: Test on macOS/iOS devices

### 6. **Network Throttling / Slow Connections**
- **Why**: While we can simulate, real-world behavior varies
- **Limitation**: Cannot test how app performs on actual slow 3G/4G
- **Manual Test Required**: Test on actual slow network

### 7. **Long-Term State Persistence**
- **Why**: LocalStorage queue persistence over days/weeks
- **Limitation**: Automated tests run in minutes
- **Manual Test Required**: Add items to queue, return days later

### 8. **User Perception of "Premium Design"**
- **Why**: Subjective aesthetic evaluation
- **Limitation**: No automated way to measure "wow factor"
- **Manual Test Required**: User feedback and A/B testing

### 9. **Accessibility (Screen Readers)**
- **Why**: Requires actual screen reader software
- **Limitation**: Playwright can check ARIA attributes but not actual screen reader experience
- **Manual Test Required**: Test with NVDA, JAWS, VoiceOver

### 10. **FTP Deployment Success**
- **Why**: Deployment script runs outside browser context
- **Limitation**: Cannot verify files uploaded correctly to server
- **Manual Test Required**: Check live site after deployment

## ⚠️ Partially Testable (With Limitations)

### 1. **Z-Index Layering**
- **Can Test**: Computed z-index values
- **Cannot Test**: Actual visual stacking in all scenarios
- **Recommendation**: Automated test + visual inspection

### 2. **Video Autoplay Restrictions**
- **Can Test**: iframe src attributes
- **Cannot Test**: If browser actually allows autoplay
- **Recommendation**: Check src params + manual verification

### 3. **Database Content Accuracy**
- **Can Test**: API returns data with correct structure
- **Cannot Test**: If movie metadata is accurate (titles, years, genres)
- **Recommendation**: Automated structure test + spot-check data

## ✅ Can Test Automatically

- Page load and rendering
- DOM structure and elements
- JavaScript errors in console
- Filter logic and state management
- Click interactions and navigation
- LocalStorage operations
- API response structure
- CSS computed styles
- Element visibility and positioning
- Search functionality
- Queue add/remove operations
- Modal open/close behavior

---

**Note**: This document should be reviewed before each major release to ensure comprehensive testing coverage.
