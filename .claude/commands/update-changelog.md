# Update Changelog

Add new entries to the Updates page at `updates/index.html` based on recent work.

## Instructions

You are updating the changelog page at `https://findtorontoevents.ca/updates/`. Follow these steps precisely:

### Step 1: Gather changes

Determine what to post. Use these sources in order of priority:

1. **User description** — If the user provided `$ARGUMENTS`, use that as the primary source of what changed.
2. **Recent commits** — Run `git log --oneline -30` and `git diff HEAD~10 --stat` to see recent work.
3. **Staged/unstaged changes** — Run `git status` and `git diff --stat` to see in-progress work.

Ask the user to confirm which changes should be included if unclear.

### Step 2: Classify each change

**Type badges** (pick 1-2 per entry):
| Badge class | Label | Dot color | When to use |
|---|---|---|---|
| `badge-feature` | New | `#22c55e` (green) | Brand new feature or page |
| `badge-improvement` | Improved | `#6366f1` (indigo) | Enhancement to existing feature |
| `badge-fix` | Fix | `#ef4444` (red) | Bug fix |
| `badge-ui` | UI | `#f97316` (orange) | Visual/layout change |

**Category tags** (for filter pills — pick all that apply):
| Category value | When to use |
|---|---|
| `stocks` | Stock picks, portfolio, dividends, penny stocks, smart money, conviction |
| `crypto` | Cryptocurrency features |
| `trading` | Live monitor, algorithms, signals, paper trading, goldmine |
| `events` | Toronto events, daily feed, deals, freebies, weather |
| `gaming` | Sports betting |
| `media` | Movies, creators, MOVIESHOWS, FavCreators |
| `movies` | Movie showtimes, trailers, MOVIESHOWS |
| `creators` | FavCreators, creator updates, live tracking |
| `tools` | Windows fixer, general utilities, deployment tools |
| `ui` | Cross-cutting UI changes |

**Path-to-category mapping** (use file paths to auto-detect categories):
- `live-monitor/` → stocks, trading
- `findstocks/` or `portfolio2/` → stocks
- `scripts/smart_money*` or `smart-money*` → stocks
- `deals/` or `deals.php` → events
- `TORONTOEVENTS_ANTIGRAVITY/` → events
- `MOVIESHOWS*` → media, movies
- `favcreators/` → creators, media
- `daily-feed/` → events, stocks
- `sports*` → gaming
- `WINDOWSFIXER/` → tools
- `news_feed*` → events

### Step 3: Determine page links

Map changes to their public URLs. **Exclude admin/internal pages** (anything requiring auth keys, GitHub Actions config, Python scripts with no public page).

| Path pattern | Public URL |
|---|---|
| `live-monitor/*.html` | `/live-monitor/{filename}` |
| `findstocks/portfolio2/*.html` | `/findstocks/portfolio2/{filename}` |
| `favcreators/` | `/fc/` |
| `deals/` | `/deals/` |
| `daily-feed/` | `/daily-feed/` |
| `MOVIESHOWS2/` | `/movieshows2/play.html` |
| `MOVIESHOWS3/` | `/movieshows3/` |
| `updates/` | `/updates/` |
| Root site | `/` |

### Step 4: Generate HTML entry

Use this exact template for each update entry:

```html
<!-- {Mon} {DD}, {YYYY} — {Short title} -->
<div class="update-entry" style="--dot-color: {dot_color};" data-tags="{comma-separated-lowercase-keywords}" data-category="{comma-separated-category-values}">
  <div class="update-date">{Mon} {DD}, {YYYY}</div>
  <div class="update-title">
    {Title — use &mdash; for em dashes}
    <span class="badge {badge_class}">{Badge Label}</span>
  </div>
  <div class="update-body">
    <p>{Summary paragraph describing the change. Use &ldquo; and &rdquo; for quotes, &mdash; for dashes.}</p>
    <ul>
      <li><strong>{Bullet title}</strong> &mdash; {Description} <span class="app-tag">{Short Tag}</span></li>
    </ul>
    <p><a href="{page_url}">{Link text} &rarr;</a></p>
  </div>
</div>
```

Rules for the HTML:
- Use HTML entities: `&mdash;` `&ldquo;` `&rdquo;` `&rarr;` `&amp;` `&ge;` `&le;`
- Never use raw `<` `>` `&` `"` in text content
- `data-tags` = lowercase keywords for search (not displayed)
- `data-category` = must match filter pill values exactly
- `app-tag` spans = short labels like: Backend, Frontend, UI, Trading, Algorithm, Chatbot, Discord, DevOps, UX, API, etc.
- Dot color should match the primary badge type (green=feature, red=fix, amber=improvement, orange=ui)
- Date format: `Mon DD, YYYY` (e.g., `Feb 11, 2026`)

### Step 5: Insert into the file

1. Read `updates/index.html`
2. Find the correct insertion point:
   - If today's month/year already has a `<div class="section-year">` header, insert the new entry **after** that header (before existing entries for that month)
   - If today's month/year does NOT have a header, create one: `<div class="section-year">{Month} {YYYY}</div>` and insert it after `<div class="container" id="updatesContainer">`
3. Insert the new entry HTML
4. Show the user the generated entry for approval before saving

### Step 6: Deploy

After the user approves:
1. Save the changes to `updates/index.html`
2. Ask the user if they want to deploy now
3. If yes, run: `python tools/deploy_updates.py`
4. Verify deployment by checking the output for "SUCCESS: sizes match"

### Category-specific rules

- **Goldmine alerts / Live monitor signals** → Tag as `stocks, trading`, NOT as a generic tool
- **Sports betting** → Tag as `gaming`, link to `/live-monitor/sports-bets.html`
- **Smart Money / Consensus / Challenger Bot** → Tag as `stocks, trading`
- **Penny Stocks** → Tag as `stocks`
- **Daily Feed** → Tag as `events, stocks, trading, crypto` (it covers everything)
- **Deals & Freebies** → Tag as `events`
- **Creator Updates / FavCreators** → Tag as `creators, media` or just `media`
- **MOVIESHOWS** → Tag as `media, movies`
- **News Feed** → Tag as `events`
- **Discord bot changes** → Include in the parent feature's category, not as a separate "tools" entry
- **Admin/internal changes** (GitHub Actions config, deploy scripts, Python cron jobs) → Do NOT create update entries for these. Only post about user-facing changes.
- **Algorithm parameter tuning** → Only post if it materially changes behavior (e.g., new algo, rewrite). Skip routine learned-parameter updates.

### Grouping rules

- If multiple related changes happened on the same day, **group them into one entry** with multiple bullet points
- If changes span different systems (e.g., stocks + events), create **separate entries** for each
- Maximum 8 bullet points per entry — summarize if there are more
- Each bullet should explain **what changed** and **why it matters to the user**
