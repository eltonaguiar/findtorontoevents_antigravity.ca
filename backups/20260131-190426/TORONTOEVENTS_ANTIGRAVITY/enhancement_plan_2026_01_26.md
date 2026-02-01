# Enhancement Plan - 2026-01-26

Based on the feedback received, the following plan outlines the steps to enhance the Toronto Events Aggregator.

## 1. Data Quality and Processing

### 1.1 City Filtering
- **Goal**: Exclude scraped events that are not in Toronto or the Greater Toronto Area (GTA).
- **Implementation**:
  - Implement a location filter in the scraping/processing pipeline.
  - Use regex or a list of allowed cities (Toronto, North York, Scarborough, Etobicoke, Mississauga, etc.).
  - Add a flag or separate list for "Online/Remote" events.

### 1.2 Deduplication and Grouping
- **Goal**: Prevent the same event from appearing multiple times (e.g., multi-day festivals).
- **Implementation**:
  - Group events by `title` and `location`.
  - Create a "Series" or "Multi-day" event object that contains individual sessions.
  - Update the UI to display these as a single card with a date range, expandable details.

### 1.3 Infer Missing Times
- **Goal**: Fix "all-day" events that actually have specific times.
- **Implementation**:
  - Update scrapers to look for time patterns in descriptions if JSON-LD is missing it.
  - Use heuristics for default times (e.g., 7 PM for nightlife events) if absolutely missing, or clearly label as "Time TBD".

### 1.4 Standardize Categories
- **Goal**: Reduce category clutter.
- **Implementation**:
  - Define a fixed set of 5-10 high-level categories (Music, Food & Drink, Arts, Nightlife, Community, Sports, Family, Education).
  - Map existing diverse tags to these high-level categories.
  - Keep original tags as secondary "attributes".

### 1.5 Improve Pricing Information
- **Goal**: Clearer pricing display.
- **Implementation**:
  - Normalize price strings to numbers or ranges.
  - Add `isFree` boolean.
  - Distinguish between "Sold Out", "Free", and "Ticketed".

## 2. User Interface and Experience

### 2.1 Multiple Views
- **Goal**: Allow users to browse via Calendar or Map.
- **Implementation**:
  - **Map View**: Integrate Leaflet or Google Maps. Requires geocoding locations.
  - **Calendar View**: Month/Week view for visual planning.

### 2.2 Search and Advanced Filtering
- **Goal**: Find specific events easily.
- **Implementation**:
  - Add a text search bar (client-side filtering for now).
  - Add date range picker.
  - Add "Neighborhood" filter if data allows.

### 2.3 Personalization (Future)
- **Goal**: Save favorites.
- **Implementation**:
  - LocalStorage based "Favorites" list.
  - "My Events" tab.

## 3. Technical and SEO Improvements

### 3.1 Structured Data
- **Goal**: Google Rich Results.
- **Implementation**:
  - Ensure every event page/card has robust JSON-LD `Event` schema.
  - Validate with Google Rich Results Test.

### 3.2 SEO Optimization
- **Goal**: Better discoverability.
- **Implementation**:
  - Unique Title Tags and Meta Descriptions per page.
  - Canonical URLs for multi-day events.
