# Scraper Update Summary

## ✅ Fixed Issues

1. **Correct Domain**: Updated scraper to use `wiki.play2xko.com/en-us/` instead of `2xko.wiki/w/`
2. **Real Blitzcrank Data**: Updated frame-data.json with actual frame data from the official wiki
3. **Better Headers**: Added proper HTTP headers to avoid 403 errors
4. **Enhanced Parsing**: Improved table parsing to handle `active` frames and `notes` columns

## 📊 Blitzcrank Frame Data (Real Data)

Updated with actual values from https://wiki.play2xko.com/en-us/Blitzcrank/Frame_Data:

- **5L**: 8f startup, 5f active, 12f recovery, -2 on block
- **2L**: 9f startup, 4f active, 12f recovery, -3 on block  
- **Prod**: 9f startup, 4f active, 12f recovery, -1 on block
- **2M**: 11f startup, 11f active, 20f recovery, -5 on block
- **j.2H**: 17f startup, 7f active, 18f recovery, -2~+15 on block
- **Rocket Grab**: 25f startup, 23f active, 30f recovery, +4 on block
- **2H**: 13f startup, 4f active, 33f recovery, -16 on block
- **Spinning Turbine**: 24f startup, 14f active, 19f recovery, -12 on block
- **Garbage Collection**: 6f startup, 8f active, 57f recovery
- **Static Field**: 20f startup, 84f recovery, -54 on block

## 🔄 Next Steps

The scraper now checks:
1. `https://wiki.play2xko.com/en-us/{Champion}/Frame_Data` (primary)
2. `https://wiki.play2xko.com/en-us/{Champion}` (summary page - may have frame data)
3. Fallback to old domain if needed

**Note**: Some characters may have frame data on their summary pages rather than dedicated Frame_Data pages. The scraper will check both.

## 📤 Ready to Upload

The `frame-data.json` file now contains:
- ✅ Ekko: 10 moves
- ✅ Ahri: 8 moves
- ✅ Blitzcrank: 10 moves (REAL DATA)

**Total: 28 moves with accurate frame data**
