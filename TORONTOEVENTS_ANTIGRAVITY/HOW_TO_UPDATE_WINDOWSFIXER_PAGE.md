# How to Update WINDOWSFIXER Page with VirusTotal Badges

## Quick Steps

### Option 1: Use the Ready-to-Use HTML File

1. **Open** `virustotal-badges-ready-to-use.html`
2. **Copy** the badge HTML for each version
3. **Paste** into your WINDOWSFIXER page HTML right after each download button/link

### Option 2: Generate Custom Badges (If You Have Detection Counts)

If you checked the VirusTotal pages and found detections:

1. **Update** `scripts/generate-virustotal-badges-with-explanations.ts` with:
   - Detection counts (`positives`)
   - Total engines (`total`)
   - Detection names (`detectionNames`)

2. **Run** the generator:
   ```bash
   npx tsx scripts/generate-virustotal-badges-with-explanations.ts
   ```

3. **Copy** the generated HTML and paste into your page

## Where to Add the Badges

Find the download sections in your WINDOWSFIXER page HTML. Look for:

```html
<!-- GitHub Version Download -->
<a href="download-url">Download GitHub Version</a>
<!-- ADD BADGE HERE -->
```

```html
<!-- Cursor Version Download -->
<a href="download-url">Download Cursor Version</a>
<!-- ADD BADGE HERE -->
```

## Your VirusTotal URLs

- **GitHub Version:** https://www.virustotal.com/gui/file/adbaf70e74b4357a21bb93cce5f53f77c647799eb38e216abd444c0e040bdf0d
- **Cursor Version:** https://www.virustotal.com/gui/file/023a7067946215bfb186040ead2aa9fbb44ce2dcb230d0d0b02de789c4ab8746

## Important Notes

1. **If you see detections:** The badges will automatically show explanations if you use the generator script with detection counts
2. **Badge colors:** Green = clean, Orange = 1-2 detections, Red = 3+ detections
3. **False positives:** 1-3 detections out of 70+ engines is normal for boot repair tools

## Files Ready to Use

- ✅ `virustotal-badges-ready-to-use.html` - Copy/paste ready badges
- ✅ `scripts/generate-virustotal-badges-with-explanations.ts` - Custom generator
- ✅ `FALSE_POSITIVE_EXPLANATIONS.md` - Detailed explanations (upload to your site)

## Need to Update Detection Counts?

1. Check your VirusTotal pages
2. Note the detection counts
3. Update `scripts/generate-virustotal-badges-with-explanations.ts`
4. Regenerate badges
5. Replace the badges on your page

---

**The badges are ready! Just copy from `virustotal-badges-ready-to-use.html` and paste into your WINDOWSFIXER page.**
