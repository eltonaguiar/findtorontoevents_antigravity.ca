# TikTok Live Detection Implementation

## Overview
FavCreators now has **two methods** for detecting TikTok live status:

1. **Frontend Proxy Method** (Immediate, works now)
2. **Backend WebCast API** (Robust, requires backend service)

---

## ✅ Method 1: Frontend Proxy Detection (ACTIVE)

### How It Works
The frontend checks `https://www.tiktok.com/@username/live` via proxy and looks for specific markers:

**Primary Indicator (Most Reliable):**
- **Offline**: Page contains `"LIVE has ended"` text
- **Live**: Page does NOT contain `"LIVE has ended"`

**Secondary Indicator (SIGI_STATE JSON):**
- **Live**: `status: 2` in `LiveRoom.liveRoomUserInfo.user.status`
- **Offline**: `status: 4` in `LiveRoom.liveRoomUserInfo.user.status`

**Tertiary Indicator:**
- **Live**: Page contains `"Log in for full experience"` without `"LIVE has ended"`

### Implementation Location
- **File**: `favcreators/src/App.tsx`
- **Function**: `checkLiveStatus()` (lines 276-337)

### Code Example
```typescript
if (platform === "tiktok") {
  const html = await fetchViaProxy(`https://www.tiktok.com/@${username}/live`);
  
  // PRIMARY CHECK: "LIVE has ended" text
  if (html.includes("LIVE has ended")) {
    return false; // Offline
  }
  
  // SECONDARY CHECK: SIGI_STATE status
  const sigiStateMatch = html.match(/<script id="SIGI_STATE"[^>]*>(.*?)<\/script>/s);
  if (sigiStateMatch) {
    const sigiData = JSON.parse(sigiStateMatch[1]);
    if (sigiData.LiveRoom?.liveRoomUserInfo?.user?.status === 2) {
      return true; // Live
    }
    if (sigiData.LiveRoom?.liveRoomUserInfo?.user?.status === 4) {
      return false; // Offline
    }
  }
  
  // TERTIARY CHECK: Login prompt without "ended" message
  if (html.includes("Log in for full experience") && !html.includes("LIVE has ended")) {
    return true; // Live
  }
  
  return null; // Unknown
}
```

### Pros & Cons
✅ **Pros:**
- Works immediately, no backend required
- Free, no API keys or OAuth
- Simple text-based detection

❌ **Cons:**
- Relies on proxy availability
- May be slower (full page fetch)
- Subject to TikTok UI changes

---

## 🚀 Method 2: Backend WebCast API (RECOMMENDED)

### How It Works
Uses the open-source `tiktok-live-connector` library to connect directly to TikTok's internal WebCast LIVE endpoints.

**Key Benefits:**
- No OAuth, no app review, no client secrets
- Connects using only the username (`unique_id`)
- More reliable than DOM scraping
- Faster response times
- Built-in caching (90 seconds)

### Implementation Files
1. **Route Handler**: `favcreators/server/src/routes/tiktok.js`
2. **Standalone Service**: `favcreators/server/tiktok-live-service.js` (optional)

### Setup Instructions

#### Option A: Integrate into Existing Server

1. **Install dependency:**
```bash
cd favcreators/server
npm install tiktok-live-connector
```

2. **Add routes to `src/index.js`:**
```javascript
import { getTikTokLiveStatus, getTikTokLiveStatusBatch } from './routes/tiktok.js';

// Add these routes
app.get('/api/tiktok/live/:username', getTikTokLiveStatus);
app.post('/api/tiktok/live/batch', express.json(), getTikTokLiveStatusBatch);
```

3. **Update frontend to use backend:**
```typescript
// In App.tsx, add new function:
const checkTikTokLiveViaBackend = async (username: string): Promise<boolean | null> => {
  try {
    const response = await fetch(`http://localhost:3000/api/tiktok/live/${username}`);
    if (response.ok) {
      const data = await response.json();
      return data.is_live;
    }
  } catch (error) {
    console.warn("Backend TikTok check failed", error);
  }
  return null;
};

// Then in checkLiveStatus():
if (platform === "tiktok") {
  // Try backend first
  const backendResult = await checkTikTokLiveViaBackend(username);
  if (backendResult !== null) return backendResult;
  
  // Fallback to proxy method...
}
```

#### Option B: Run as Standalone Service

1. **Start the service:**
```bash
cd favcreators/server
node tiktok-live-service.js
```

2. **Service runs on port 3001:**
- Single check: `GET http://localhost:3001/api/live-status/tiktok/:username`
- Batch check: `POST http://localhost:3001/api/live-status/tiktok/batch`
- Health check: `GET http://localhost:3001/health`

### API Endpoints

#### GET /api/tiktok/live/:username
Check if a single user is live.

**Response:**
```json
{
  "username": "gabbyvn3",
  "is_live": true,
  "cached": false,
  "checked_at": "2026-02-04T21:30:00.000Z"
}
```

#### POST /api/tiktok/live/batch
Check multiple users at once.

**Request:**
```json
{
  "usernames": ["gabbyvn3", "starfireara", "wtfprestonlive"]
}
```

**Response:**
```json
{
  "results": [
    { "username": "gabbyvn3", "is_live": true, "cached": false },
    { "username": "starfireara", "is_live": false, "cached": false },
    { "username": "wtfprestonlive", "is_live": true, "cached": true }
  ],
  "checked_at": "2026-02-04T21:30:00.000Z"
}
```

### Caching Strategy
- **Cache Duration**: 90 seconds (configurable via `CACHE_TTL`)
- **Cache Cleanup**: Automatic cleanup every 90 seconds
- **Memory Safe**: Old entries are purged to prevent memory leaks

### Error Handling
- Connection failures return `is_live: false`
- Errors are logged but don't crash the service
- Frontend should have fallback to proxy method

---

## 📊 Comparison: Browser Inspection Findings

Based on actual inspection of live vs offline TikTok streams:

| Indicator | Live Stream (Gabbyvn3) | Offline Stream (Gillianunrestricted) |
|-----------|------------------------|--------------------------------------|
| **"LIVE has ended" text** | ❌ Not present | ✅ Present |
| **Video element** | ✅ `<video autoplay>` | ❌ Black screen |
| **Viewer count** | ✅ Real-time (e.g., "35") | ⚠️ Static "1 viewer" |
| **Chat messages** | ✅ Real-time messages | ❌ "Comments off" |
| **SIGI_STATE status** | `status: 2` | `status: 4` |
| **Login prompt** | ✅ "Log in for full experience" | ⚠️ May appear |
| **Auto-play countdown** | ❌ Not present | ✅ "Next LIVE in X seconds" |

---

## 🔧 Troubleshooting

### Issue: Frontend shows "offline" but user is live

**Check:**
1. Verify the TikTok username is correct
2. Check browser console for proxy errors
3. Try the backend API directly: `curl http://localhost:3000/api/tiktok/live/gabbyvn3`
4. Manually visit `https://www.tiktok.com/@gabbyvn3/live` to confirm

### Issue: Backend service fails to start

**Solutions:**
1. Ensure Node.js version >= 16
2. Run `npm install` in the server directory
3. Check for port conflicts (default: 3001)
4. Review error logs for missing dependencies

### Issue: All TikTok users show as offline

**Possible Causes:**
1. TikTok changed their HTML structure (update detection logic)
2. Proxy is blocked or rate-limited
3. Backend service is down
4. Network connectivity issues

---

## 🎯 Recommended Setup

For **production use**, I recommend:

1. **Use Method 2 (Backend WebCast API)** as primary
2. **Keep Method 1 (Frontend Proxy)** as fallback
3. **Enable caching** to reduce API calls
4. **Monitor error rates** and adjust retry logic

### Deployment Checklist
- [ ] Install `tiktok-live-connector` dependency
- [ ] Add TikTok routes to server
- [ ] Update frontend to use backend API
- [ ] Configure fallback to proxy method
- [ ] Test with known live and offline users
- [ ] Set up monitoring/logging
- [ ] Deploy backend service
- [ ] Update CORS settings if needed

---

## 📝 Testing

### Manual Test
```bash
# Test offline user
curl http://localhost:3000/api/tiktok/live/gillianunrestricted

# Test live user (when Gabbyvn3 is live)
curl http://localhost:3000/api/tiktok/live/gabbyvn3

# Test batch
curl -X POST http://localhost:3000/api/tiktok/live/batch \
  -H "Content-Type: application/json" \
  -d '{"usernames": ["gabbyvn3", "gillianunrestricted"]}'
```

### Automated Test (Playwright)
```typescript
test('TikTok live detection', async ({ page }) => {
  // Test offline user
  const offlineResponse = await page.request.get(
    'http://localhost:3000/api/tiktok/live/gillianunrestricted'
  );
  const offlineData = await offlineResponse.json();
  expect(offlineData.is_live).toBe(false);
  
  // Test live user (update username as needed)
  const liveResponse = await page.request.get(
    'http://localhost:3000/api/tiktok/live/gabbyvn3'
  );
  const liveData = await liveResponse.json();
  expect(liveData.is_live).toBe(true);
});
```

---

## 🔗 Resources

- **tiktok-live-connector**: https://github.com/zerodytrash/TikTok-Live-Connector
- **TikTokLive (Python)**: https://github.com/isaackogan/TikTokLive
- **TikTok WebCast Protocol**: https://github.com/zerodytrash/TikTok-Livestream-Chat-Connector

---

## 📅 Implementation Status

- ✅ **Frontend proxy detection** - Implemented in `App.tsx`
- ✅ **Backend route handlers** - Created in `server/src/routes/tiktok.js`
- ✅ **Standalone service** - Created in `server/tiktok-live-service.js`
- ✅ **Dependency added** - `tiktok-live-connector` in `server/package.json`
- ⏳ **Frontend integration** - Pending (needs backend API calls)
- ⏳ **Testing** - Pending
- ⏳ **Deployment** - Pending

---

**Last Updated**: February 4, 2026  
**Status**: Ready for testing and deployment
