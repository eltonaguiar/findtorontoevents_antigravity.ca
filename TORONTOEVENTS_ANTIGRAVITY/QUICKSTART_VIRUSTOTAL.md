# Quick Start: Add VirusTotal Badges to WINDOWSFIXER Page

## What Was Created

✅ **Scripts:**
- `scripts/generate-virustotal-badges.ts` - Generates HTML badges for scan results
- `scripts/scan-virustotal.ts` - Automated scanning via VirusTotal API (optional)
- `scripts/find-github-download-urls.ts` - Helper to find download URLs

✅ **Documentation:**
- `WINDOWSFIXER_VIRUSTOTAL_SETUP.md` - Complete setup guide

## Quick Steps

### 1. Find Your ZIP File URLs

Run this to see possible download URLs:
```bash
npx tsx scripts/find-github-download-urls.ts
```

### 2. Scan Files on VirusTotal

**Option A: Manual (Easiest)**
1. Go to https://www.virustotal.com
2. Upload each ZIP file or paste the download URL
3. Wait for scan to complete
4. Copy the permalink URL (looks like: `https://www.virustotal.com/gui/file/abc123...`)

**Option B: API (If you have an API key)**
```bash
export VIRUSTOTAL_API_KEY="your-key-here"
npx tsx scripts/scan-virustotal.ts
```

### 3. Generate Badge HTML

1. Open `scripts/generate-virustotal-badges.ts`
2. Update the `scanResults` array with your VirusTotal URLs and scan results
3. Run:
```bash
npx tsx scripts/generate-virustotal-badges.ts
```
4. Copy the generated HTML

### 4. Add to WINDOWSFIXER Page

Add the generated HTML badges right after each download button/link in your WINDOWSFIXER page HTML.

## Example

After scanning, your badge will look like this:

```html
<div class="virustotal-scan" style="margin-top: 0.75rem;">
  <a href="https://www.virustotal.com/gui/file/..." target="_blank" rel="noopener noreferrer" style="...">
    🛡️ VirusTotal: Clean
  </a>
  <p style="...">
    Scanned by 70 antivirus engines • 
    <a href="...">View full report</a>
  </p>
</div>
```

## Files to Update

- `scripts/generate-virustotal-badges.ts` - Add your scan results here
- Your WINDOWSFIXER page HTML - Add the generated badges

## Handling False Positives

If your scan shows any detections (even 1-3 out of 70+ engines), this is normal for boot repair tools. They perform operations that malware also uses, causing false positives.

**To maintain user trust:**
1. Use `scripts/generate-virustotal-badges-with-explanations.ts` to generate badges with built-in explanations
2. Add the false positive explanation section to your page
3. Link to `FALSE_POSITIVE_EXPLANATIONS.md` for detailed information

## Need Help?

- **Setup Guide:** See `WINDOWSFIXER_VIRUSTOTAL_SETUP.md` for detailed instructions
- **False Positives:** See `FALSE_POSITIVE_EXPLANATIONS.md` for why detections occur
- **Security:** See `SECURITY_TRANSPARENCY.md` for our security commitment
