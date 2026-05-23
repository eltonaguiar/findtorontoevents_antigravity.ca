# Proposed Solution for "Ghost Events" on findtorontoevents.ca

## Diagnosis
Based on code analysis, semantic search, and CSS inspection from the local clone (tmp/fte_clone/index.html and associated chunks), the "ghost events" (cards that appear invisible or faded until hovered) are caused by deliberate Tailwind CSS styles applied to event cards (classes like `.glass-panel`, `.event-card`):

- **Base Styles**: Cards start with `grayscale(100%)` (desaturated/grayed out) and reduced opacity (e.g., `.opacity-50` or pulsing via `.animate-pulse` for skeletons). Thumbnails use placeholders (`.card-thumb-placeholder`) with similar faded effects.
- **Hover Styles**: On hover, CSS transitions to `grayscale-0` (full color), `opacity-100` (full visibility), and slight scaling (`.hover\:scale-105`).
- **Why This Happens**: This creates a dynamic UI effect to highlight interacted cards, but it makes non-hovered cards look "ghostly" (faded and desaturated). No JS bugs or console errors contribute—it's purely CSS. If events load slowly or skeletons persist (due to failed `events-loaded` class addition), the pulsing/faded state lingers.
- **Runtime Evidence**: Confirmed via grep on minified CSS files (e.g., bb44232864466eee.css) showing grayscale and opacity rules. Semantic search located card rendering in index.html (applyThumbnails function) and similar components (e.g., MovieCard.tsx with potential shared styles). Static WebFetch of the site showed initial HTML without dynamic cards, aligning with JS-loaded content.

This matches the screenshots: cards appear faded/desaturated until interaction brings color and visibility.

## Proposed Solution
If the ghost effect is unintended and cards should be fully visible by default (with hover for subtle emphasis only), apply these targeted CSS overrides. This keeps the glassmorphic design but removes the initial fade/grayscale.

### Steps to Implement
1. **Locate the Relevant CSS**: The styles are in minified Tailwind chunks (e.g., _next/static/chunks/bb44232864466eee.css). For a clean fix, add overrides directly in index.html's `<style>` block or a custom CSS file loaded after the chunks.

2. **Add CSS Overrides**:
   - Target `.glass-panel`, `.event-card`, and thumbnail classes.
   - Set full opacity and no grayscale by default; keep hover for scale/shadow if desired.

   Example overrides (add to `<style>` in index.html or a new custom.css):

   ```css
   .glass-panel, .event-card {
     opacity: 1 !important; /* Full opacity by default */
     filter: grayscale(0) !important; /* Full color by default */
     transition: transform 0.3s ease, box-shadow 0.3s ease; /* Keep smooth hover */
   }

   .glass-panel:hover, .event-card:hover {
     transform: scale(1.05); /* Optional: Keep scale on hover */
     box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3); /* Optional: Enhanced shadow */
   }

   .animate-pulse {
     animation: none !important; /* Disable pulsing if skeletons persist */
     opacity: 1 !important;
   }

   .card-thumbnail, .card-thumb-placeholder {
     opacity: 1 !important;
     filter: grayscale(0) !important;
   }
   ```

3. **Handle Skeletons**: Ensure JS properly adds `.events-loaded` to hide skeletons after data loads. If not, patch the rendering function (e.g., in index.html's applyThumbnails or renderEvents).

4. **Test Locally**:
   - Use skill "deploy-and-fix-local" or manually: Run `python tools/serve_local.py`, apply changes, and check http://localhost:5173/ for visible cards without hover.
   - Run Playwright: `npx playwright test tests/no_js_errors.spec.ts` to ensure no errors.

5. **Deploy and Verify**:
   - Deploy with `python tools/deploy_to_ftp.py`.
   - Verify remote with skill "verify-remote-site" or `npm run verify:remote`.
   - Reproduce: Visit https://findtorontoevents.ca, confirm cards are visible immediately (no fade/grayscale until hover if kept for effect).

### Potential Edge Cases
- **If Thumbnails Still Ghost**: Ensure image src loads eagerly (remove loading="lazy" if present).
- **Performance Impact**: Removing grayscale/opacity might slightly increase initial render load; monitor if needed.
- **If Intended Design**: If this is a feature (e.g., for focus), no fix needed—confirm with user.

This fix is minimal and targeted, preserving the site's aesthetic while addressing the issue. If runtime browser inspection is needed for further confirmation, resolve the MCP config and re-run the browser subagent.