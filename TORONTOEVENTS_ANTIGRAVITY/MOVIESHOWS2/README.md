# MovieShows v2 Deployment Guide

## 🚀 Quick Deploy

### Option 1: Automated (PowerShell)
```powershell
cd E:\findtorontoevents_antigravity.ca\TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS2
.\deploy.ps1
```

### Option 2: Manual FTP Upload

1. **Connect to FTP:**
   - Host: `ftps2.50webs.com`
   - Port: `22` (SFTP)
   - Username: `ejaguiar1`
   - Password: (from .env file)

2. **Navigate to:**
   - Remote: `/findtorontoevents.ca/`

3. **Upload:**
   - Upload the entire `MOVIESHOWS2` folder
   - Ensure `index.html` is inside `/findtorontoevents.ca/MOVIESHOWS2/`

4. **Verify:**
   - Visit: https://findtorontoevents.ca/MOVIESHOWS2/
   - Check tooltip on navigation links
   - Test link to original /MOVIESHOWS

## 📁 What Gets Deployed

```
/findtorontoevents.ca/MOVIESHOWS2/
├── index.html          [Main demo page]
└── deploy.ps1          [Deployment script]
```

## ✅ Post-Deployment Checklist

- [ ] Site loads at https://findtorontoevents.ca/MOVIESHOWS2/
- [ ] Tooltip appears on "v1.0 (Original)" link
- [ ] Link to /MOVIESHOWS works
- [ ] All features display correctly
- [ ] Pricing cards are interactive
- [ ] Footer links work

## 🌐 Live URLs

- **v2.0 Demo:** https://findtorontoevents.ca/MOVIESHOWS2/
- **v1.0 Original:** https://findtorontoevents.ca/MOVIESHOWS/
- **Main Site:** https://findtorontoevents.ca/

## 📝 Features Showcased

- Complete monetization stack (Updates 101-110)
- Enterprise features (Updates 121-126)
- Advanced infrastructure (Updates 111-120)
- 60+ components, 24K+ lines of code
- 126/400 updates complete (31.5%)

## 🔧 Troubleshooting

### Site Not Loading
- Verify file uploaded to correct path
- Check file permissions (644 for HTML)
- Clear browser cache

### Tooltip Not Working
- Ensure CSS is loading
- Check browser console for errors
- Verify hover functionality

### Links Broken
- Confirm /MOVIESHOWS directory exists
- Check relative vs absolute paths
- Test in different browsers

## 📞 Support

If issues occur:
1. Check deployment log
2. Verify FTP credentials
3. Test file permissions
4. Contact support@findtorontoevents.ca
