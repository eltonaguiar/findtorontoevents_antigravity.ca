# Creator Count Fix - Race Condition Resolution

**Date:** February 5, 2026  
**Status:** ✅ Fixed  
**Issue:** Only 11 creators were being checked for live status when users followed 42+ creators

---

## Root Cause

The issue was a **race condition** between:
1. Loading creators from the database API (`loadMyList`)
2. Starting the live status check (`updateAllLiveStatuses`)

### The Problem

- `INITIAL_DATA` (the default creator list) contains exactly **11 creators**
- When a logged-in user loads the page, the initial state uses `INITIAL_DATA`
- The live status check was starting after only **2 seconds** (via `setTimeout`)
- If the API hadn't finished loading the user's actual creators by then, the check would only process the 11 default creators

### Code Flow (Before Fix)

```
Page Load
  ↓
Initial State = INITIAL_DATA (11 creators)
  ↓
API Call to get_my_creators.php starts (loading 42 creators)
  ↓
[2 seconds later] Live check starts with creatorsRef.current
  ↓
Only 11 creators checked! ❌
  ↓
API returns 42 creators (too late)
```

---

## The Fix

### 1. Added Loading State Tracking

Added a new state variable to track when creators have been loaded from the API:

```typescript
const [creatorsLoadedFromApi, setCreatorsLoadedFromApi] = useState<boolean>(false);
```

### 2. Set Flag When Creators Load

Set the flag to `true` when creators are successfully loaded:

**For logged-in users (line ~1144):**
```typescript
if (list.length > 0) {
  console.log("Loaded creators from DB:", list.length);
  setCreators(ensureAvatarForCreators(list as Creator[]));
  setCreatorsLoadedFromApi(true);  // ← NEW
}
```

**For guest users (line ~1409):**
```typescript
if (!authUserRef.current || authUserRef.current.id === 0) {
  setCreators(withNotes);
  setCreatorsLoadedFromApi(true);  // ← NEW
}
```

### 3. Wait for Load Before Starting Live Check

Modified the auto-check effect to wait for the flag:

```typescript
useEffect(() => {
  // Don't start live checking until creators are loaded from API
  if (!creatorsLoadedFromApi) {
    console.log('[Live Check] Waiting for creators to load from API...');
    return;
  }

  console.log(`[Live Check] Creators loaded: ${creatorsRef.current.length}. Starting live checks...`);

  // Now safe to start checks...
  const timer = setTimeout(() => {
    console.log(`[Live Check] Starting check with ${creatorsRef.current.length} creators`);
    updateAllLiveStatuses();
  }, 2000);

  // ...
}, [updateAllLiveStatuses, loadCachedLiveStatus, creatorsLoadedFromApi]);
```

### 4. Added Debug Logging

Added console logs to help diagnose issues:

```typescript
const updateAllLiveStatuses = useCallback(async () => {
  const creatorCount = creatorsRef.current.length;
  console.log(`[Live Check] Starting updateAllLiveStatuses with ${creatorCount} creators`);
  
  // Warn if we're checking only the default 11
  if (currentCreators.length <= 11 && authUser) {
    console.warn(`[Live Check] WARNING: Only ${currentCreators.length} creators to check`);
  }
  // ...
}, [addLiveFoundToast, authUser]);
```

---

## Code Flow (After Fix)

```
Page Load
  ↓
Initial State = INITIAL_DATA (11 creators)
  ↓
API Call to get_my_creators.php starts
  ↓
Live check effect runs but WAITs (creatorsLoadedFromApi = false)
  ↓
API returns 42 creators
  ↓
setCreators(42 creators)
setCreatorsLoadedFromApi(true)
  ↓
Effect re-runs, creatorsLoadedFromApi = true
  ↓
[2 seconds later] Live check starts with 42 creators ✅
```

---

## Files Modified

| File | Lines Changed | Description |
|------|---------------|-------------|
| `src/App.tsx` | ~+15 lines | Added `creatorsLoadedFromApi` state, loading flags, and wait logic |

---

## Testing

### Test Files Created

1. **`tests/creator-count-debug.spec.ts`** - Diagnoses the issue
2. **`tests/creator-count-fix.spec.ts`** - Verifies the fix works

### Key Test Cases

| Test | Description |
|------|-------------|
| Live check should wait for API-loaded creators | Verifies check uses API count, not INITIAL_DATA |
| Logged-in user should have all creators checked | Ensures count > 11 for users with more creators |
| Console should show correct sequence | Confirms "load" happens before "check" |
| Race condition fix verification | Ensures total count doesn't change mid-check |

### Run Tests

```bash
cd favcreators
npx playwright test tests/creator-count-fix.spec.ts --headed
```

---

## Verification Checklist

- [x] Added `creatorsLoadedFromApi` state variable
- [x] Set flag when API returns creators (logged-in users)
- [x] Set flag when API returns creators (guest users)
- [x] Modified live check effect to wait for flag
- [x] Added debug logging for creator counts
- [x] Build passes without errors
- [x] Tests created to verify fix

---

## Console Output (Expected)

### Before Fix
```
[Live Check] Starting check with 11 creators
```

### After Fix
```
[Live Check] Waiting for creators to load from API...
...
Loaded creators from DB: 42
...
[Live Check] Creators loaded: 42. Starting live checks...
[Live Check] Starting check with 42 creators
```

---

## Impact

- **Users with >11 creators:** Will now have ALL their creators checked for live status
- **Users with ≤11 creators:** No change in behavior
- **Performance:** Slight delay (until API responds) before live check starts
- **Guest mode:** Unaffected (uses default list intentionally)
