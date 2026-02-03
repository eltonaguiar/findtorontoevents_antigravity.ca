# Events Sync & Sync History (Stats Page)

## Overview

- **Sync history** is shown on https://findtorontoevents.ca/stats/ (Recent Sync History table).
- Data comes from the **ejaguiar1_events** database via `/fc/api/events_get_stats.php`.
- Tables: `event_pulls` (each sync run), `events_log` (event rows), `stats_summary` (counts), plus `event_title_index` and `event_sources` for duplicate finder.

## Prerequisites on the server

1. **Database password**  
   Set **EVENTS_MYSQL_PASSWORD** for user **ejaguiar1_events** (database **ejaguiar1_events**):
   - In the host’s environment variables (cPanel / PHP env), or
   - In **fc/api/.env.events** on the server:  
     `EVENTS_MYSQL_PASSWORD=your_password`

2. **Tables**  
   Run once (GET):  
   https://findtorontoevents.ca/fc/api/events_setup_tables.php  

3. **events.json on server**  
   Already deployed to the site root (and findevents/) by `deploy_to_ftp.py`.

## Running a full sync

- **ModSecurity** blocks POST to `events_sync.php` from outside, so sync is done **on the server** via GET:
  1. Open: **https://findtorontoevents.ca/fc/api/events_sync.php** (GET, in browser or curl).
  2. The script reads **events.json** from the server (root or findevents) and upserts into **ejaguiar1_events**.

- Locally you can still:
  - Scrape and save: `python tools/scrape_and_sync_events.py` (no `--sync`), then deploy **events.json**.
  - After deploy, run the GET sync URL above to update the DB.

## Verification & data quality

- **Stats page:**  
  https://findtorontoevents.ca/stats/  
  Should show Total Events, Upcoming, Free, **Recent Sync History**, Sources, Categories.

- **API checks:**  
  `python tools/verify_events_sync.py`  
  Calls `events_status.php`, `events_get_stats.php`, and `events_find_duplicates.php`.

- **Duplicate finder (optional):**  
  https://findtorontoevents.ca/fc/api/events_find_duplicates.php  
  Builds title index and links same-event rows from different sources.

## Summary

| Step | Action |
|------|--------|
| 1 | Set EVENTS_MYSQL_PASSWORD on server (env or fc/api/.env.events). |
| 2 | GET https://findtorontoevents.ca/fc/api/events_setup_tables.php (once). |
| 3 | GET https://findtorontoevents.ca/fc/api/events_sync.php (after each deploy of events.json). |
| 4 | View https://findtorontoevents.ca/stats/ and run `python tools/verify_events_sync.py`. |
