# MovieShows Deployment - Safe Deployment Guide

## ⚠️ IMPORTANT: Backup First!

Before deploying any files, **create a backup** of the remote `/findtorontoevents.ca/MOVIESHOWS/` directory.

### Option 1: Automated Backup (If FTP Works)
```bash
npm run movies:backup
```

This creates: `backups/movieshows-backup-2026-02-03/`

### Option 2: Manual Backup via FTP Client

1. **Connect to FTP**:
   - Host: `ftps2.50webs.com`
   - Port: `22` (SFTP)
   - Username: `ejaguiar1`
   - Password: (from .env file)

2. **Download Directory**:
   - Remote: `/findtorontoevents.ca/MOVIESHOWS/`
   - Local: `E:\findtorontoevents_antigravity.ca\TORONTOEVENTS_ANTIGRAVITY\backups\movieshows-backup-2026-02-03\`

3. **Verify Backup**:
   - Check all files downloaded
   - Note file count and sizes

---

## 📦 Files to Deploy

### New Files (Safe to Upload)

These are **new** files that won't overwrite anything:

```
/api/
  ├── db-config.php          [NEW]
  ├── movies.php             [NEW]
  └── trailers.php           [NEW]

/database/
  ├── init-db.php            [NEW]
  └── schema.sql             [NEW]
```

### Documentation (Safe)
```
DATABASE_README.md           [NEW]
DEPLOYMENT_GUIDE.md          [NEW]
```

---

## 🚀 Deployment Steps

### Step 1: Backup (REQUIRED)
```bash
# Automated (if FTP works)
npm run movies:backup

# OR manually via FTP client
# Download /findtorontoevents.ca/MOVIESHOWS/ to local backup folder
```

### Step 2: Upload New Files

**Via FTP Client** (Recommended):
1. Connect to `ftps2.50webs.com`
2. Navigate to `/findtorontoevents.ca/MOVIESHOWS/`
3. Create directories:
   - `api/`
   - `database/`
4. Upload files to respective directories

**Via Script** (If FTP works):
```bash
npm run movies:deploy
```

### Step 3: Initialize Database

Visit in browser:
```
https://findtorontoevents.ca/MOVIESHOWS/database/init-db.php
```

Expected output:
```
✓ Database connection successful!
✓ Schema creation complete!
  Successful: 5
  Failed: 0

✓ movies: 0 rows
✓ trailers: 0 rows
✓ thumbnails: 0 rows
✓ content_sources: 4 rows
✓ sync_log: 0 rows
```

### Step 4: Test API

Visit in browser:
```
https://findtorontoevents.ca/MOVIESHOWS/api/movies.php
```

Expected response:
```json
{"movies":[],"count":0}
```

### Step 5: Add Content

```bash
# Add 13 specific movies with TMDB data
npm run movies:add

# Scrape Cineplex Toronto
npm run movies:scrape

# Discover additional trailers
npm run movies:discover
```

---

## 🔍 Verification Checklist

After deployment:

- [ ] Backup created and verified
- [ ] PHP files uploaded to correct directories
- [ ] Database initialized (visit init-db.php)
- [ ] API responds (visit movies.php)
- [ ] Movies added (run movies:add)
- [ ] Cineplex scraped (run movies:scrape)
- [ ] Trailers discovered (run movies:discover)

---

## 🛡️ Safety Notes

1. **Backup First**: Always backup before deploying
2. **New Files Only**: These files won't overwrite existing content
3. **Database Separate**: Database is separate from existing site
4. **Rollback Ready**: Keep backup to restore if needed

---

## 📝 What Gets Created

### Database Tables (5)
- `movies` - Movie/TV series data
- `trailers` - Multiple trailers per movie
- `thumbnails` - Multiple thumbnails per movie
- `content_sources` - Track data sources
- `sync_log` - Sync history

### API Endpoints (2)
- `/api/movies.php` - Movies CRUD
- `/api/trailers.php` - Trailers management

### Content
- 13 requested movies with TMDB metadata
- Cineplex Toronto current movies
- Multiple trailers per movie
- High-quality thumbnails

---

## 🆘 Troubleshooting

### Database Connection Failed
- Check credentials in `api/db-config.php`
- Verify database exists: `ejaguiar1_tvmoviestrailers`
- Confirm IP whitelist includes server IP

### API Returns Error
- Check PHP error logs
- Verify file permissions (644 for .php files)
- Test database connection separately

### FTP Upload Failed
- Use FTP client instead of script
- Verify credentials in .env
- Check server connectivity

---

## 📞 Support

If issues occur:
1. Check backup is complete
2. Review error messages
3. Test each component separately
4. Restore from backup if needed
