# FavCreators Database Setup

## Tables

- **creators** – Global pool of creators. Columns: id, name, bio, avatar_url, category, reason, tags (JSON), accounts (JSON), is_favorite, is_pinned, in_guest_list, guest_sort_order, created_at, updated_at. Guest list = rows with in_guest_list=1 ordered by guest_sort_order.
- **user_lists** – Per-user list: user_id (PK), creators (LONGTEXT JSON), updated_at. user_id=0 = guest list (admin-managed).
- **creator_defaults** – Default notes for guests: creator_id (PK), note, updated_at.
- **user_notes** – Per-user notes: user_id, creator_id, note. Only that user sees their notes.

## Automatic setup (no user action)

**creators** and **user_lists** are created and the guest list is seeded automatically when the API is first used. **get_my_creators.php**, **save_creators.php**, and **sync_creators_table.php** include **ensure_tables.php**, which runs `CREATE TABLE IF NOT EXISTS` for `creators` and `user_lists` and seeds the guest list (user_id=0) from **initial_creators.json** if empty. No manual step or URL run is required.

Optional endpoints (for debugging or one-off validation):

- **setup_tables.php** – Standalone create + seed; returns JSON.
- **validate_tables.php** – Checks table existence and structure; returns JSON.
- **run_setup_then_validate.php** – Runs both and returns combined JSON.

## Guest list (user_id=0)

- **get_my_creators.php?user_id=0** – Returns guest list from user_lists(0) if present; otherwise from **creators** WHERE in_guest_list=1 ORDER BY guest_sort_order.
- **save_creators.php** with user_id=0 – Saves to user_lists(0) and syncs each creator into **creators** (upsert with in_guest_list=1).

## Admin: add one creator for guests

- **POST add_creator_for_guest.php** – Body: `{ "creator": { id, name, bio, avatarUrl, category, reason, tags, accounts, isFavorite, isPinned } }`. Inserts/updates **creators** and appends to user_lists(0).

## Per-user list and notes

- Logged-in user: **get_my_creators.php?user_id=X** returns their list from user_lists(X). **save_creators.php** saves their list. **save_note.php** saves their personal notes to **user_notes** (only they see them).
- Guest: sees guest list + notes from **creator_defaults** (and fallback from user_notes).
