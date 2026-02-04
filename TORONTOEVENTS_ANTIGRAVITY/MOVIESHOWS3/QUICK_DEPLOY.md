# 🚀 MOVIESHOWS2 - Quick Deploy Guide

## ⚡ FASTEST METHOD: Manual FTP Upload

The automated SFTP script is experiencing connection timeouts. Here's the quickest manual method:

### 📤 Step-by-Step Upload

1. **Open FileZilla (or any FTP client)**

2. **Connect with these details:**
   ```
   Host: ftps2.50webs.com
   Port: 22
   Protocol: SFTP
   Username: ejaguiar1
   Password: CxH1Uh*#0QkIVg@KxgMZXn7Hp
   ```

3. **Navigate on remote server to:**
   ```
   /findtorontoevents.ca/
   ```

4. **Create folder (if doesn't exist):**
   ```
   movieshows2
   ```
   ⚠️ **IMPORTANT:** Use lowercase `movieshows2`

5. **Upload file:**
   - Local file: `E:\findtorontoevents_antigravity.ca\TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS2\index.html`
   - Remote path: `/findtorontoevents.ca/movieshows2/index.html`

6. **Verify:**
   - Visit: https://findtorontoevents.ca/movieshows2/
   - Should see the enterprise demo page

---

## ✅ What You're Deploying

**Single file:** `index.html` (self-contained, no dependencies)

**Features:**
- Enterprise platform showcase
- 126 updates summary (31.5% complete)
- Interactive pricing cards
- Feature showcase
- **Tooltip on "v1.0 (Original)" link** explaining /MOVIESHOWS
- Links to original version

---

## 🎯 Post-Deploy Checklist

After upload, verify:

- [ ] Site loads: https://findtorontoevents.ca/movieshows2/
- [ ] Hover "v1.0 (Original)" link - tooltip appears
- [ ] Click link to /MOVIESHOWS - works
- [ ] Pricing cards are clickable
- [ ] Feature cards are clickable
- [ ] Footer links work
- [ ] Mobile responsive

---

## 🔧 Troubleshooting

### Site shows 404
- Verify folder name is lowercase: `movieshows2`
- Verify file is named: `index.html`
- Check path: `/findtorontoevents.ca/movieshows2/index.html`

### Tooltip not working
- Clear browser cache
- Check browser console for errors
- Try different browser

### Links broken
- Verify /MOVIESHOWS directory exists
- Check relative paths in HTML

---

## 📞 Need Help?

The file is ready at:
```
E:\findtorontoevents_antigravity.ca\TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS2\index.html
```

Just drag and drop it to `/findtorontoevents.ca/movieshows2/` via FTP!

**Total time: ~2 minutes** ⚡
