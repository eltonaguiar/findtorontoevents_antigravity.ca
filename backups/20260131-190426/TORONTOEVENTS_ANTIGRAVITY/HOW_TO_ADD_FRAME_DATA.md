# How to Add Frame Data to 2XKOFRAMEDATA Repository

## Current Status

The repository `eltonaguiar/2XKOFRAMEDATA` currently only contains a README.md file. To make the frame data viewer work, you need to add a JSON file with frame data.

## Quick Setup

### Option 1: Use Sample Template

1. Use the `sample-frame-data.json` file in this repository as a template
2. Rename it to `frame-data.json` or `data.json`
3. Upload it to the `eltonaguiar/2XKOFRAMEDATA` GitHub repository

### Option 2: Create Your Own JSON File

Create a JSON file with this structure:

```json
{
  "champions": [
    {
      "name": "ChampionName",
      "moves": [
        {
          "name": "5L",
          "startup": 6,
          "onHit": 0,
          "onBlock": -2,
          "recovery": 10,
          "type": "normal"
        }
      ]
    }
  ]
}
```

## Data Sources

Frame data can be obtained from:

1. **2XKO Wiki**: https://2xko.wiki
   - Navigate to each champion's Frame Data page
   - Example: https://2xko.wiki/w/Ekko/Frame_Data

2. **Manual Entry**: Enter frame data manually from in-game training mode

3. **Community Resources**: Check fighting game community spreadsheets or databases

## File Naming

The viewer will automatically look for these filenames (in order):
- `frame-data.json` (recommended)
- `data.json`
- `framedata.json`
- `champions.json`
- `index.json`

## Upload to GitHub

1. Go to: https://github.com/eltonaguiar/2XKOFRAMEDATA
2. Click "Add file" → "Upload files"
3. Drag and drop your JSON file
4. Commit with message: "Add frame data"
5. The viewer will automatically detect and load it

## Data Format Details

### Required Fields
- `name`: Move notation (e.g., "5L", "2M", "236H")
- `startup`: Number of frames until move is active
- `onHit`: Frame advantage on hit (can be negative)
- `onBlock`: Frame advantage on block (can be negative)
- `recovery`: Frames of recovery after move

### Optional Fields
- `damage`: Damage value
- `guard`: Guard type (high/low/overhead)
- `type`: Move category ("normal", "special", "super")

### Champion Structure
Each champion needs:
- `name`: Champion name (e.g., "Ekko", "Ahri")
- `moves`: Array of move objects

## Verification

After uploading:
1. Wait 1-2 minutes for GitHub to process
2. Visit: https://findtorontoevents.ca/2xko
3. The frame data should load automatically
4. If not, click "Refresh Data" button

## Troubleshooting

**"No Frame Data Available" error:**
- Check that the JSON file is valid JSON
- Verify the file is in the `main` branch
- Ensure the file has a `.json` extension
- Check that the structure matches the expected format

**Data not updating:**
- Clear browser cache/localStorage
- Click "Refresh Data" button
- Check browser console for errors

---

**Note**: Frame data values may change with game patches. Keep the repository updated for accurate information.
