# FIXBLANKIMAGES.MD

## Summary
The event images on the **findtorontoevents.ca** site are occasionally displayed incorrectly. Some images appear as a tiny, random‑color block instead of the full picture (e.g., the *EarLyON Family Fun Time* event). This is caused by the current image handling logic serving a mini version that is too large for the allocated space.

## Identified Issues
1. **Mini‑image rendering** – The thumbnail generated for an event is larger than the UI container, causing the image to be clipped and appear as a random color.
2. **Age‑filter mismatch** – Certain events are listed for ages **4‑12**, but the site should only display events with a **minimum age of 16+** unless the age cannot be determined.

## Recommended Fixes
### Image Handling
- Detect when the generated thumbnail exceeds the container dimensions.
- If it does, replace the thumbnail with a **scaled‑down version** (e.g., using CSS `object-fit: contain` or server‑side resizing).
- Ensure the fallback image is a **transparent placeholder** instead of a solid color.

### Age Filtering
- Update the event import pipeline to **filter out events** where `minAge < 16`.
- Keep events where `minAge` is **undefined** or **null** (age cannot be determined).
- Add a **log entry** for each filtered event for audit purposes.

## Next Steps
1. Locate the image‑processing script in `findtorontoevents.ca/` (likely under `scripts/` or `tools/`).
2. Implement the thumbnail size check and scaling logic.
3. Modify the event‑age validation step to enforce the 16+ rule.
4. Run the existing test suite (`npm test` or `pytest`) to confirm no regressions.
5. Deploy the changes to a staging environment and manually verify the *EarLyON Family Fun Time* event image.

## References
- Event URL example: `https://tpl.bibliocommons.com/v2/events/6a59177f9943bdf31e9f5799`
- Current site directory: `findtorontoevents.ca/`

---
*Created to document the image and age‑filter issues and outline a remediation plan.*
