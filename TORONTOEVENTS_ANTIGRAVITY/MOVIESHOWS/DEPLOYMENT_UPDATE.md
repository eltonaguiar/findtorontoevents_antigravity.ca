# MovieShows Deployment - Updated Files

## New Files to Upload

The following files need to be uploaded to `/findtorontoevents.ca/MOVIESHOWS/`:

### API Directory (`/api/`)
- ✅ `db-config.php` - Database configuration
- ✅ `movies.php` - Movies CRUD API
- ✅ `trailers.php` - Trailers management API
- 🆕 `queue.php` - **User queue management API**
- 🆕 `preferences.php` - **User preferences API**
- 🆕 `playlists.php` - **Playlist sharing API**

### Database Directory (`/database/`)
- 🔄 `schema.sql` - **Updated with 4 new tables**
- ✅ `init-db.php` - Database initialization

## Manual Upload Instructions

### Via FTP Client

1. **Connect to FTP:**
   - Host: `ftps2.50webs.com`
   - Port: `22` (SFTP)
   - Username: `ejaguiar1`
   - Password: (from `.env`)

2. **Upload New Files:**
   ```
   Local: E:\findtorontoevents_antigravity.ca\TORONTOEVENTS_ANTIGRAVITY\MOVIESHOWS\api\
   Remote: /findtorontoevents.ca/MOVIESHOWS/api/
   
   Files:
   - queue.php (NEW)
   - preferences.php (NEW)
   - playlists.php (NEW)
   ```

3. **Update Schema:**
   ```
   Local: E:\findtorontoevents_antigravity.ca\TORONTOEVENTS_ANTIGRAVITY\database\schema.sql
   Remote: /findtorontoevents.ca/MOVIESHOWS/database/schema.sql
   
   (REPLACE existing file)
   ```

## After Upload

### 1. Re-initialize Database

Visit: `https://findtorontoevents.ca/MOVIESHOWS/database/init-db.php`

This will create the 4 new tables:
- ✓ `user_queues`
- ✓ `user_preferences`
- ✓ `shared_playlists`
- ✓ `playlist_items`

### 2. Test New APIs

```bash
# Test queue API (requires authentication)
curl https://findtorontoevents.ca/MOVIESHOWS/api/queue.php

# Test preferences API (requires authentication)
curl https://findtorontoevents.ca/MOVIESHOWS/api/preferences.php

# Test playlist sharing (public access)
curl https://findtorontoevents.ca/MOVIESHOWS/api/playlists.php?code=SHARE_CODE
```

## What's New

### Queue Management
- Add movies to personal queue
- Reorder queue items
- Mark as watched/unwatched
- Track watch count
- Sync localStorage to database

### User Preferences
- Toggle rewatch enabled
- Toggle auto-play
- Toggle sound on scroll
- Persistent across devices

### Playlist Sharing
- Create shareable playlists
- Generate unique share codes
- Copy playlists to queue
- Track view counts
- Optional expiration dates

## Next Steps

After backend is deployed:
1. ✅ Backend APIs deployed
2. ⏳ Frontend components (LoginPrompt, QueueManager, SharePlaylist)
3. ⏳ Login integration with /fc
4. ⏳ Queue sync logic
5. ⏳ Sound persistence implementation
