# Fix: Show Loading State While Fetching Live Status

## Problem
The "Creators Live Now" section shows "No creators live right now. Check back soon!" initially, even when creators are actually live. This is because:
1. The page loads with stale cached data from localStorage
2. API calls take 1-3 seconds to complete
3. User sees "No creators live" during this loading period
4. Eventually the UI updates with correct live status

## Solution
Add a loading state to the LiveSummary component that shows while live status is being fetched.

## Files to Modify

### 1. favcreators/src/App.tsx

**Add a loading state variable:**
```typescript
// Around line 1510, add to state:
const [isCheckingLiveStatus, setIsCheckingLiveStatus] = useState(false);
```

**Modify the updateAllLiveStatuses function:**
```typescript
const updateAllLiveStatuses = useCallback(async () => {
  setIsCheckingLiveStatus(true); // Start loading
  
  // ... existing logic ...
  
  setIsCheckingLiveStatus(false); // End loading
}, [creators, liveStatuses]);
```

**Modify the LiveSummary component call:**
```typescript
<LiveSummary
  liveCreators={liveCreators}
  isLoading={isCheckingLiveStatus} // Pass loading state
  onToggle={() => setShowLiveSummary(!showLiveSummary)}
  isCollapsed={!showLiveSummary}
/>
```

### 2. favcreators/src/components/LiveSummary.tsx (or wherever it's defined)

**Modify the component to accept and display loading state:**
```typescript
interface LiveSummaryProps {
  liveCreators: LiveCreator[];
  isLoading?: boolean; // Add this prop
  onToggle: () => void;
  isCollapsed: boolean;
}

// In the render:
{isLoading ? (
  <div className="flex items-center gap-2 text-gray-400">
    <div className="animate-spin w-4 h-4 border-2 border-purple-500 border-t-transparent rounded-full"></div>
    <span>Checking live status...</span>
  </div>
) : liveCreators.length === 0 ? (
  <p className="text-gray-400">No creators live right now. Check back soon!</p>
) : (
  // ... existing live creators display ...
)}
```

## Alternative Quick Fix (No Component Changes)

If you want a simpler fix without modifying components, change the default message:

```typescript
// In LiveSummary component
<p className="text-gray-400">
  {isLoading ? "Checking who's live..." : "No creators live right now. Check back soon!"}
</p>
```

## Implementation Steps

1. Open `favcreators/src/App.tsx`
2. Find the LiveSummary component usage (around line 2704-2709)
3. Add `isLoading` prop
4. Create loading state variable
5. Update `updateAllLiveStatuses` to set loading state
6. Build and deploy

## Build & Deploy Commands

```bash
cd favcreators
npm run build
python ../tools/deploy_to_ftp.py
```

## Testing

1. Clear browser cache (Ctrl+Shift+R)
2. Load https://findtorontoevents.ca/fc/#/guest
3. Verify "Checking live status..." appears initially
4. Verify live creators appear after API calls complete
5. Verify message changes to "No creators live" only if truly offline
