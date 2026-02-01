# Social Summary Plan

## Chunk 1 – Map the UI surface
- [x] Confirmed each creator's `accounts-list` is a good place for the tooltip and decided to trigger research when hovering over or focusing the account row.

## Chunk 2 – Scraper helper
- [x] Added `fetchSocialSummary` to `src/utils/socialSummary.ts`, which proxies through AllOrigins, inspects meta descriptions, and truncates clean text for reuse.

## Chunk 3 – Tooltip wiring
- [x] Hooked `CreatorCard` to cache per-account summaries, trigger the scraper on hover/focus, and render a tooltip with loading/error states; updated `App.css` with new tooltip styles.

## Chunk 4 – Validate and record
- [x] Run `npm run lint` (fails for the same pre-existing issues in `src/App.tsx`, `src/api/proxy.ts`, `src/components/CreatorCard.tsx`, `src/utils/avatarFetcher.ts`, and `src/utils/googleSearch.ts`).
