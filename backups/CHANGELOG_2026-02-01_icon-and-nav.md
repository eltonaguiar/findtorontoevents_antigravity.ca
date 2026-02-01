# Change log: Icon links + Nav reorder (2026-02-01)

## Backup

- **index.html** → `backups/index.html.backup-2026-02-01-icon-and-nav`

## Files modified

### index.html

#### 1. Icon links section (icon-links-section)

- **Change:** Add one new promo block for **Stocks** (Open App → style) after Movies & TV, before the ad container.
- **Location:** After last promo block (movieshows-promo), before `<div class="max-w-7xl mx-auto px-4 py-6">`.
- **Content:** stocks-promo, icon 📈, title "Stocks", subtitle "Research &amp; Portfolio", href="/findstocks", pill "Open App →", gradient from-blue-500 to-indigo-600.
- **Note:** Fav Creators promo already exists; no duplicate added.

#### 2. Nav menu reorder (fix-nav-menu)

- **Change A:** Remove **2XKO Frame Data** link from its current position (immediately after NETWORK `</details>`).
- **Change B:** Remove **Data Management** section (header + JSON/CSV/Calendar buttons + Import Collection button + file input) from its current position.
- **Change C:** Add at bottom of nav (after Support section, before `</nav>`):
  1. **2XKO Frame Data** (standalone link, same HTML as before).
  2. **Data Management** (full block: header, grid of export buttons, Import Collection button, file input).

Resulting nav order: Platform → NETWORK → Event System Settings → Contact Support (dashed) → PERSONAL → Support → **2XKO Frame Data** → **Data Management**.

#### Per-edit summary (index.html)

| # | Edit | Location (approx.) |
|---|------|---------------------|
| 1 | Insert Stocks promo block (stocks-promo, 📈, Open App → /findstocks) | After movieshows-promo, before ad container |
| 2 | Remove 2XKO Frame Data `<a>` from after NETWORK `</details>` | Nav block |
| 3 | Remove Data Management `<div>...</div>` (header + buttons + Import + input) | Nav block |
| 4 | Insert 2XKO link in new `<div class="space-y-1 pt-4 border-t...">` before `</nav>` | After Support section |
| 5 | Insert Data Management block (same HTML as removed) before `</nav>` | After 2XKO section |

---

*Generated for debugging. Do not edit asset URLs (_next) or events grid.*
