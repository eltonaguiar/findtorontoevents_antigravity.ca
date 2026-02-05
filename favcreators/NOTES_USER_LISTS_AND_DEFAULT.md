# FavCreators: user_lists and default list

## Summary

- **User ID 2** (admin, e.g. zerounderscore@gmail.com): their `user_lists` row should contain **all creators** from the `creators` table. The UI shows whatever is in their list; they can add/remove creators and it only affects their view.
- **User ID 0**: the "default list" (guest list). This is built from `creators` where `in_guest_list = 1` (ordered by `guest_sort_order`). When the admin edits the guest/default list and saves, this row is updated; that becomes the template for new users.
- **All other users**: should start with a copy of the default list (user_id=0). They can remove or add creators in their own list without affecting anyone else.
- **New users** (e.g. Google sign-in): on first signup, `google_callback.php` copies the default list (user_id=0) into a new `user_lists` row for that user. Going forward, only the current default list is mirrored to new users; if the admin changes the default, only new users (and anyone who gets re-synced) see that change.
- **Per-user customization**: Any user can remove (or add) creators from their own list via save; changes are stored only in their `user_lists` row and do not impact other users.

## One-time fix after SQL import (user 2 not seeing all creators)

The web sync URL may return 500 on some hosts (e.g. `.htaccess: SecRuleEngine not allowed here`). Use the **CLI fix** instead.

### Option 1: Run on the server via SSH (recommended)

1. Deploy the repo so `fix_user2_list_cli.php` is on the server (e.g. in `findevents/fc/api/` or `fc/api/`).
2. SSH into the server, then:
   ```bash
   cd /path/to/findtorontoevents.ca/findevents/fc/api
   php fix_user2_list_cli.php
   ```
   (Use the real path where your site’s `fc/api` lives; it must have `.env` there for DB credentials.)
3. You should see: `OK: user_id=2 now has N creators in user_lists.`
4. Log in as zerounderscore@gmail.com (user 2) and refresh; you should see all creators.

### Option 2: Sync via browser (if the API returns 200)

If your host does not block the API with 500:

1. Open: `https://yoursite.com/fc/api/sync_user_lists_from_creators.php` (or `.../findevents/fc/api/...`).
2. You should get JSON with `user_2_updated: true` and counts.
3. Then user 2 will see all creators after refresh.

## Lazy init

If a logged-in user has no `user_lists` row yet (e.g. created by another flow), `get_my_creators.php` will copy the default list (user_id=0) into a new row for them and return it, so they immediately see the default list and can customize it.

## Files

- **sync_user_lists_from_creators.php** – one-time sync of user_lists from creators table (user 2 = all creators; user 0 = guest list; others = default).
- **get_my_creators.php** – returns the user’s list from `user_lists`; if missing and user_id > 0, initializes from default and returns it.
- **save_creators.php** – saves the user’s list; any user (including admin) can remove creators from their own view.
- **google_callback.php** – on new user signup, copies default list (user_id=0) to the new user’s `user_lists` row.
