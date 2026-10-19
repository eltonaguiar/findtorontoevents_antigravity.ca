# Design Spec: Weather Background Enhancement

**Date:** 2026-10-18
**Topic:** Aesthetic background image / graphic reflection of current day/night and weather status for `https://findtorontoevents.ca/weather/`.

## 1. Overview
The goal is to replace the current CSS gradient backgrounds with high-quality, atmospheric static images that dynamically change based on the real-time weather condition and time of day (day/night). This will create a more immersive and aesthetic experience for users checking the weather.

## 2. Requirements
- **Dynamic Reflection:** Background must reflect both weather condition (Rain, Snow, Clear, etc.) and time of day (Day, Night).
- **Aesthetic Quality:** Use high-resolution, professional photography or curated atmospheric images.
- **Smooth Transitions:** Cross-fade between backgrounds when weather updates to avoid jarring flashes.
- **Readability:** Ensure all text and UI elements remain legible over various background images.
- **Performance:** Optimize image loading to prevent slow page loads.

## 3. Architecture & Implementation

### 3.1 Image Mapping Strategy
We will map Open-Meteo weather codes and the `is_day` flag to specific image categories.

| Condition | Day Image Category | Night Image Category |
| :--- | :--- | :--- |
| **Clear** | Sunny sky, bright horizon | Starry sky, clear night city |
| **Clouds** | Overcast sky, soft light | Moody clouds, dark sky |
| **Rain** | Rainy window, wet streets (day) | Rainy city lights, wet pavement (night) |
| **Snow** | Snowy landscape, falling flakes | Snow-covered street lamps, winter night |
| **Thunder** | Dark storm clouds, lightning | Night storm, dramatic sky |
| **Fog** | Misty forest, foggy morning | Eerie fog, dim street lights |

### 3.2 Layered Background System
To achieve smooth transitions, we will implement a dual-layer background system in `weather/index.html`.

#### HTML Structure
```html
<div id="bg-container">
  <div class="bg-layer active" id="bg-layer-1"></div>
  <div class="bg-layer" id="bg-layer-2"></div>
  <div class="bg-overlay"></div>
</div>
```

#### CSS Logic
- `.bg-container`: Fixed position, inset 0, z-index 0.
- `.bg-layer`: Absolute position, inset 0, background-size: cover, background-position: center, transition: opacity 2s ease-in-out.
- `.bg-overlay`: Absolute position, inset 0, background: linear-gradient(to bottom, rgba(0,0,0,0.3), rgba(0,0,0,0.6)), z-index 1. Ensures text readability.

### 3.3 JavaScript Logic
Enhance `setWeatherBackground(cond, isDay)`:
1. **Key Generation:** Create a key (e.g., `rain-night`).
2. **Image Selection:** Select a URL from a curated list (using Unsplash Source API or a local manifest).
3. **Preloading:** Create a new `Image()` object to preload the URL.
4. **Swapping:** Once loaded, set the `background-image` of the inactive layer, then swap the `active` class.

## 4. Performance & Optimization
- **WebP Format:** Use WebP images where possible for better compression.
- **Lazy Loading:** Background images will be loaded only when needed.
- **Caching:** Browser caching will be leveraged for frequently used backgrounds.

## 5. Success Criteria
- The background accurately reflects "Rainy Night" when the API returns rain and `is_day=0`.
- Transitions between weather states are smooth (2-second cross-fade).
- Text remains readable on all backgrounds.
- No significant impact on page load time (LCP).
