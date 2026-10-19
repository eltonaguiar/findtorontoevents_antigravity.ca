# FIXBLANKIMAGES.md — Image Display & Age Filtering Issues

## Problem 1: TPL Bibliocommons Images "Cut Off"

### Root Cause
The TPL scraper (`tools/scrapers/tpl_bibliocommons_scraper.py:133-138`) extracts `featuredImageId` from event definitions and resolves it via the `entities.images` map. The gateway returns **full-size banner images** (e.g., `TPLIcons-Crafts&Hobbies.jpg`, `TPLIconBanners-ReadingPrograms&Storytimes.jpg`) that are **wide landscape banners** (~1200×400px).

The frontend thumbnail injector (`TORONTOEVENTS_ANTIGRAVITY/index.html` — `applyThumbnails()` around line 3700+) renders these as:
```html
<img class="card-thumbnail" src="..." style="width: 100%; height: 160px; object-fit: cover;">
```

Because the source images are **wide banners** and the card thumbnail is **tall/narrow** (160px height, ~300px width), `object-fit: cover` crops aggressively — showing only a thin horizontal slice (often a solid color bar from the banner's top/bottom).

### Evidence
- Sample event: `https://tpl.bibliocommons.com/v2/events/6a59177f9943bdf31e9f5799` (EarlyON Family Fun Time)
- Image URL pattern: `https://tpl.bibliocommons.com/events/uploads/images/full/{hash}/{banner-name}.jpg`
- Banner names: `TPLIcons-*`, `TPLIconBanners-*`, `ReadyforReading12.16.jpg`, etc. — all wide decorative banners, not event-specific photos

### Proposed Fixes

#### Option A: Skip Generic Banner Images (Recommended)
Detect and discard known generic TPL banner patterns in the scraper:
```python
# In _build_event(), after resolving image_url:
GENERIC_BANNER_PATTERNS = [
    "TPLIcons-",
    "TPLIconBanners-",
    "ReadyforReading",
    "PopUpLearningLabs",
    "TP87CA~1",
    "GOLDENHOUR",
    "Picture1",
    "BookClubs&WritersGroups",
]
if image_url and any(p in image_url for p in GENERIC_BANNER_PATTERNS):
    image_url = None
```
Result: Events with only generic banners get `image: null` → frontend shows placeholder/color gradient instead of cropped banner slice.

#### Option B: Request Thumbnail Variants
BiblioCommons may expose thumbnail sizes (e.g., `/images/thumb/...` or query params). Need to inspect gateway response for `image` entity structure — check if `img_ent` has `thumbUrl`, `sizes`, or `derivatives` fields.

#### Option C: Frontend CSS Adjustment
Change `object-fit: cover` → `object-fit: contain` with background color. Shows full banner but with letterboxing. Less ideal for card grid consistency.

---

## Problem 2: Age Filtering — Minimum Age 16+

### Current State
The scraper categorizes events via `_categorize()` (lines 77-106) using `type_names` and `audience_names` from BiblioCommons entities. It adds "Family" category for kids/children/family/preschool/baby/storytime/teen/youth types.

**No age-based filtering exists** — all TPL events are imported regardless of target audience.

### Data Available
- `audience_names` from `entities.eventAudiences` — contains strings like:
  - "Children", "Preschool", "Families", "Teens", "Adults", "Older Adults", "Newcomers", etc.
- `type_names` from `entities.eventTypes` — contains strings like:
  - "Storytime", "Kids", "Family Programs", "Teen", "Adult", "Senior", etc.

### Proposed Fix: Filter in Scraper `_build_event()`

Add age gate after resolving `audience_names` and `type_names`:

```python
def _is_adult_event(self, audience_names: List[str], type_names: List[str]) -> bool:
    """
    Return True if event is for ages 16+.
    Keep event if age cannot be determined (no audience/type signals).
    """
    # Explicit child/family/teen audiences → exclude
    child_keywords = [
        "children", "preschool", "baby", "toddler", "kids", "family",
        "storytime", "earlyon", "early years", "ages 0", "ages 1",
        "ages 2", "ages 3", "ages 4", "ages 5", "ages 6", "ages 7",
        "ages 8", "ages 9", "ages 10", "ages 11", "ages 12",
        "ages 13", "ages 14", "ages 15",
    ]
    teen_keywords = ["teen", "youth", "ages 16", "ages 17", "ages 18"]
    adult_keywords = ["adult", "older adult", "senior", "ages 19", "ages 20+"]
    
    all_text = " ".join(audience_names + type_names).lower()
    
    # If explicitly child/family → exclude
    if any(k in all_text for k in child_keywords):
        return False
    
    # If explicitly adult/senior → include
    if any(k in all_text for k in adult_keywords):
        return True
    
    # If teen-only (no adult) → exclude (under 16)
    if any(k in all_text for k in teen_keywords) and not any(k in all_text for k in adult_keywords):
        return False
    
    # Age cannot be determined → KEEP (per requirement)
    return True
```

Then in `_build_event()`:
```python
if not self._is_adult_event(audience_names, type_names):
    return None  # Skip this event
```

### Edge Cases
| Audience/Type | Decision | Reason |
|--------------|----------|--------|
| "Children", "Preschool" | Exclude | Explicitly under 16 |
| "Families" | Exclude | Implies children present |
| "Teens" only | Exclude | Ages 13-18, under 16 |
| "Adults", "Older Adults" | Include | 18+ |
| "Teens", "Adults" | Include | Mixed, includes 16+ |
| No audience/type data | Include | Age undetermined → keep |
| "Newcomers", "ESL" (no age) | Include | Age undetermined → keep |

---

## Implementation Plan

1. **Update `tpl_bibliocommons_scraper.py`**:
   - Add `GENERIC_BANNER_PATTERNS` constant
   - Add `_is_adult_event()` method
   - Apply both filters in `_build_event()`

2. **Test**:
   - Run scraper with `max_pages=2` 
   - Verify EarlyON Family Fun Time (children) is excluded
   - Verify adult events (book clubs, author talks, tech workshops) retained
   - Verify events with generic banners get `image: null`

3. **Regenerate `next/events.json`** via unified scraper pipeline

4. **Deploy** — FTP upload updated `next/events.json` to production

---

## Files to Modify
- `tools/scrapers/tpl_bibliocommons_scraper.py` — primary fix location
- (No frontend changes needed — `image: null` handled by existing placeholder logic)