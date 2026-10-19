# ServiceNow AI Features page — training links + richer moving background

**Date:** 2026-10-11  
**File:** `TORONTOEVENTS_ANTIGRAVITY/servicenow/AIFeaturesOct2026/index.html`  
**Live URL:** https://findtorontoevents.ca/servicenow/AIFeaturesOct2026/index.html

## What was wrong

The page had a contextual link block in the practical section, but no persistent internal navigation to the other ServiceNow training pages beside the hero's **Back to events** button. Its animated background also relied on a single aurora layer, so the page had motion but not much depth.

## What changed

- Added explicit hero links beside **Back to events** for:
  - `/servicenow/javascript/index.html`
  - `/servicenow/CIS-CSM/index.html`
  - `/servicenow/CIS-VR/index.html`
- Added a footer navigation bar linking the four ServiceNow training pages with explicit `index.html` targets:
  - `/servicenow/javascript/index.html`
  - `/servicenow/AIFeaturesOct2026/index.html`
  - `/servicenow/CIS-CSM/index.html`
  - `/servicenow/CIS-VR/index.html`
- Kept the page's existing practical-section cross-links.
- Added an SVG-based decorative background image layer, `.bg-scene`, so the page has a real abstract AI/network backdrop rather than only gradient bloom.
- Added a second animated decorative layer, `.bg-orbit`, using soft radial highlights plus a subtle diagonal mesh so the page background feels more intentional and alive without obscuring content.
- Extended the reduced-motion rule to disable the new background-image motion as well.

## How it was checked

Added a Playwright spec that checks:

- the hero action row includes the three ServiceNow training-page links beside the Back to events button,
- the practical section exposes the three internal training links,
- the footer contains a persistent ServiceNow training-page nav,
- the SVG background-image layer is present and animated,
- both animated background layers are present, and
- the page still avoids horizontal overflow.
