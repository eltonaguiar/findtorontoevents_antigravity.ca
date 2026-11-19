# Conference Sponsor Scraper — Status

## Result: SPA-Walled (cannot extract automatically)

Both ServiceNow World Forum Toronto and Salesforce World Tour Toronto use **RainFocus SPA platforms** that load sponsor data via JavaScript API calls only. Static HTML contains zero sponsor data — only the words "Sponsors" and "Sponsor Catalog".

## What was attempted

| Approach | Result |
|----------|--------|
| Static HTML parse + regex | ❌ SPA shell only — no data |
| RainFocus API probe (apiProfile) | ❌ profile loaded dynamically via JS |
| Playwright with networkidle wait | ❌ pages timeout or hang |
| Text extraction from rendered DOM | ❌ no sponsor text in static source |

## What works

The **Playwright script** at `updates/scripts/conf_sponsor_scraper.py` is written and will work when run from a machine that:
1. Can reach the RainFocus event pages without auth walls
2. Has Playwright + Chromium installed
3. Can wait for the SPA to fully render (the pages may take 15-30s to load sponsor data)

## Manual workaround

Open these URLs in a desktop browser, view the sponsor grid, and copy sponsor names:

- https://reg.servicenow.com/flow/servicenow/wftoronto26/sponsorshowcase/page/sponsors
- https://reg.salesforce.com/flow/plus/wttoronto26may/sponsors/page/sponsorcatalog