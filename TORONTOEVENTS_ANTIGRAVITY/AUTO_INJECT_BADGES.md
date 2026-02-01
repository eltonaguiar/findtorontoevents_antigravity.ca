# Automatic Badge Injection

I've created scripts to automatically embed the VirusTotal badges into your WINDOWSFIXER page HTML.

## Option 1: Fetch from Live Site and Inject (Easiest)

This downloads your live page, injects badges, and saves it:

```bash
npx tsx scripts/fetch-and-inject-badges.ts
```

This will:
1. Download the page from https://findtorontoevents.ca/WINDOWSFIXER/
2. Automatically find the download sections
3. Inject the VirusTotal badges
4. Save to `WINDOWSFIXER/index.html`

Then you can upload the updated file to your server.

## Option 2: Inject into Local HTML File

If you have the HTML file locally:

```bash
npx tsx scripts/inject-virustotal-badges.ts [path-to-html-file]
```

Or place it in one of these locations and run without arguments:
- `WINDOWSFIXER/index.html`
- `public/WINDOWSFIXER/index.html`
- `WINDOWSFIXER.html`
- `build/WINDOWSFIXER/index.html`

## How It Works

The script automatically:
- ✅ Finds "GitHub Version" download section
- ✅ Finds "Cursor Version" download section
- ✅ Injects badges right after each download link
- ✅ Creates a backup of the original file
- ✅ Skips if badges are already present

## What Gets Injected

The badges include:
- ✅ Links to your VirusTotal scan results
- ✅ "Clean" status (or detection counts if you update the script)
- ✅ Links to full VirusTotal reports
- ✅ Styled badges with hover effects

## Update Detection Counts

If you need to update detection counts:

1. Edit `scripts/inject-virustotal-badges.ts`
2. Update the `GITHUB_BADGE` and `CURSOR_BADGE` constants
3. Or use `scripts/generate-virustotal-badges-with-explanations.ts` to generate new HTML
4. Copy the generated HTML into the constants

## Next Steps

1. **Run the fetch script:**
   ```bash
   npx tsx scripts/fetch-and-inject-badges.ts
   ```

2. **Review the updated file:**
   - Check `WINDOWSFIXER/index.html`
   - Verify badges are in the right places

3. **Upload to your server:**
   - Use your FTP/SFTP deployment method
   - Or update your deployment script to include this file

---

**The badges will be automatically embedded - no copy/paste needed!**
