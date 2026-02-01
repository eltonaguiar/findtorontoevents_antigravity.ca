# Update 2XKO Frame Data on GitHub

## ✅ Frame Data Scraped Successfully!

Frame data has been scraped from the 2XKO Wiki and saved to `frame-data.json`.

**Current Data:**
- ✅ Ekko: 10 moves
- ✅ Ahri: 8 moves
- ⚠️ Other champions: Wiki pages not available yet

## 📤 Upload to GitHub

### Option 1: Manual Upload (Easiest)

1. **Go to the repository**: https://github.com/eltonaguiar/2XKOFRAMEDATA

2. **Upload frame-data.json**:
   - Click "Add file" → "Upload files"
   - Drag and drop `frame-data.json` from this repository
   - Commit message: "Add frame data from 2XKO Wiki"
   - Click "Commit changes"

3. **Update README.md**:
   - Click on `README.md`
   - Click the pencil icon to edit
   - Copy content from `2XKOFRAMEDATA_README.md` in this repository
   - Paste and save

### Option 2: Automated Upload (Requires GitHub Token)

1. **Create GitHub Personal Access Token**:
   - Go to: https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Name: "2XKO Frame Data Updater"
   - Select scope: `repo` (full control)
   - Generate and copy the token

2. **Set environment variable**:
   ```powershell
   $env:GITHUB_TOKEN="your_token_here"
   ```

3. **Run update script**:
   ```bash
   npm run update:2xko:github
   ```

## 📁 Files to Upload

- **frame-data.json** - Main frame data (already created in this repo)
- **README.md** - Documentation (copy from `2XKOFRAMEDATA_README.md`)

## ✅ Verify Upload

After uploading, verify the files are accessible:
- Frame data: https://raw.githubusercontent.com/eltonaguiar/2XKOFRAMEDATA/main/frame-data.json
- README: https://github.com/eltonaguiar/2XKOFRAMEDATA/blob/main/README.md

The web viewer at https://findtorontoevents.ca/2xko will automatically detect and load the data within 1-2 minutes.

## 🔄 Update More Champions

To scrape more champions when their wiki pages become available:

```bash
npm run scrape:2xko
```

This will update `frame-data.json` with any new data found. Then upload the updated file to GitHub.

## 📝 Notes

- Frame data is scraped from: https://2xko.wiki
- Currently only Ekko and Ahri have frame data pages
- Other champions will be added as wiki pages are created
- The scraper automatically handles different table formats

---

**Status**: ✅ Frame data scraped and ready for upload  
**File Location**: `frame-data.json` in this repository  
**Next Step**: Upload to GitHub repository
