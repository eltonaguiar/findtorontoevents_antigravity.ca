# VirusTotal Scan Badges for WINDOWSFIXER Page

This guide explains how to add VirusTotal scan badges to the download sections on the WINDOWSFIXER page to enhance user trust.

## Overview

The WINDOWSFIXER page offers two ZIP file downloads:
- **GitHub Version** (1.5 MB)
- **Cursor Version** (4.3 MB)

Adding VirusTotal scan badges shows users that the files have been scanned and are safe to download.

## Step 1: Scan Files on VirusTotal

### Option A: Manual Upload (Recommended for First Time)

1. Go to [https://www.virustotal.com](https://www.virustotal.com)
2. Click "Choose File" or drag and drop your ZIP file
3. Wait for the scan to complete (usually 30-60 seconds)
4. Once complete, copy the **permalink URL** from the results page
   - It will look like: `https://www.virustotal.com/gui/file/abc123def456...`
5. Repeat for the second ZIP file

### Option B: Scan by URL (If Files Are Already Hosted)

1. Go to [https://www.virustotal.com](https://www.virustotal.com)
2. Click on the "URL" tab
3. Paste the direct download URL of your ZIP file
4. Click "Scan it!"
5. Wait for the scan to complete
6. Copy the permalink URL

### Option C: Use API (Advanced)

If you have a VirusTotal API key:

```bash
# Set your API key
export VIRUSTOTAL_API_KEY="your-api-key-here"

# Run the scan script
npx tsx scripts/scan-virustotal.ts
```

Get a free API key at: https://www.virustotal.com/gui/join-us

## Step 2: Generate Badge HTML

1. Open `scripts/generate-virustotal-badges.ts`
2. Update the `scanResults` array with:
   - Your VirusTotal permalink URLs
   - Scan results (positives, total, isClean)
3. Run the script:

```bash
npx tsx scripts/generate-virustotal-badges.ts
```

4. Copy the generated HTML code

## Step 3: Add Badges to WINDOWSFIXER Page

### If the page is in this repository:

1. Find the WINDOWSFIXER HTML file
2. Locate the download section for each version
3. Add the badge HTML right after each download button/link

### If the page is deployed separately:

1. Access your WINDOWSFIXER page source (HTML file or CMS)
2. Find the download sections
3. Add the generated badge HTML

### Example Placement

The badges should be placed right after the download button/link, like this:

```html
<!-- Download Section for GitHub Version -->
<div class="download-section">
  <a href="download-url" class="download-button">
    Download GitHub Version (1.5 MB)
  </a>
  
  <!-- Add VirusTotal badge here -->
  <div class="virustotal-scan" style="margin-top: 0.75rem;">
    <a href="virustotal-url" target="_blank" rel="noopener noreferrer" style="...">
      🛡️ VirusTotal: Clean
    </a>
    <p style="...">
      Scanned by 70 antivirus engines • 
      <a href="virustotal-url">View full report</a>
    </p>
  </div>
</div>
```

## Step 4: Update Scans Periodically

VirusTotal scans should be updated when:
- You release a new version of the ZIP files
- You make significant changes to the files
- You want to refresh the scan results

**Note:** VirusTotal allows re-scanning files. You can use the same permalink URL, or scan again to get a fresh report.

## Badge Styles

The script generates two badge styles:

1. **Full Badge**: Large, detailed badge with scan statistics
   - Best for: Main download sections
   - Shows: Scan status, engine count, link to full report

2. **Compact Badge**: Small, minimal badge
   - Best for: Limited space, inline with download links
   - Shows: Just the status icon and text

## Troubleshooting

### Badge Not Showing
- Check that the HTML was added correctly
- Verify the CSS styles are included
- Check browser console for errors

### Scan Results Not Updating
- Re-scan the file on VirusTotal
- Update the permalink URL in the script
- Regenerate the badge HTML

### Files Not Scanning
- Ensure files are accessible (not behind authentication)
- Check file size limits (VirusTotal has a 650MB limit)
- Try uploading directly instead of URL scanning

## Example Badge HTML

Here's what a generated badge looks like:

```html
<div class="virustotal-scan" style="margin-top: 0.75rem; margin-bottom: 0.75rem;">
  <a 
    href="https://www.virustotal.com/gui/file/..." 
    target="_blank" 
    rel="noopener noreferrer"
    style="display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.625rem 1.25rem; background: #4caf50; color: white; border-radius: 6px; text-decoration: none; font-size: 0.875rem; font-weight: 600; box-shadow: 0 2px 8px rgba(0,0,0,0.15);"
  >
    <span>🛡️</span>
    <span>VirusTotal: Clean</span>
    <span>↗</span>
  </a>
  <p style="margin-top: 0.5rem; font-size: 0.8125rem; color: #666;">
    Scanned by <strong>70</strong> antivirus engines • 
    <a href="https://www.virustotal.com/gui/file/..." target="_blank" rel="noopener noreferrer" style="color: #0066cc;">View full report</a>
  </p>
</div>
```

## Next Steps

1. ✅ Scan both ZIP files on VirusTotal
2. ✅ Update `scripts/generate-virustotal-badges.ts` with scan results
3. ✅ Generate badge HTML
4. ✅ Add badges to WINDOWSFIXER page
5. ✅ Test the badges on the live page
6. ✅ Verify links work correctly

## Handling False Positives

Boot repair tools commonly trigger false positives from antivirus software. This is expected and normal because:

- Boot repair requires deep system access (same operations malware uses)
- BCD editing, registry modifications, and driver injection are flagged by heuristics
- Most detections are generic heuristics, not specific malware signatures

**Important:** If your scan shows any detections (even 1-3 out of 70+ engines), add an explanation section to maintain user trust. See `FALSE_POSITIVE_EXPLANATIONS.md` for detailed explanations and use `scripts/generate-virustotal-badges-with-explanations.ts` to generate badges with built-in explanations.

## Resources

- [VirusTotal Website](https://www.virustotal.com)
- [VirusTotal API Documentation](https://developers.virustotal.com/reference)
- [Get VirusTotal API Key](https://www.virustotal.com/gui/join-us)
- [False Positive Explanations](./FALSE_POSITIVE_EXPLANATIONS.md) - Detailed guide on why boot repair tools trigger false positives
