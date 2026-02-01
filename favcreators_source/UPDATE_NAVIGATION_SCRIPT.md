# Quick Reference: Navigation Update Code

## Exact Code to Add

### HTML Version (for static HTML files)
Add this code **after** the "Movies & TV" link:

```html
<a 
  href="https://eltonaguiar.github.io/FAVCREATORS/" 
  target="_blank" 
  rel="noopener noreferrer" 
  class="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-pink-500/20 text-pink-200 hover:text-white transition-all border border-transparent hover:border-pink-500/30 overflow-hidden"
  title="Keep track of your favorite creators and why you follow them, and who to check out on a rainy day"
>
  <span class="text-lg">⭐</span> Favorite Creators
</a>
```

### JSX/React Version (for Next.js/React components)
Add this code **after** the "Movies & TV" link:

```jsx
<a 
  href="https://eltonaguiar.github.io/FAVCREATORS/" 
  target="_blank" 
  rel="noopener noreferrer" 
  className="w-full text-left px-4 py-3 rounded-xl flex items-center gap-3 hover:bg-pink-500/20 text-pink-200 hover:text-white transition-all border border-transparent hover:border-pink-500/30 overflow-hidden"
  title="Keep track of your favorite creators and why you follow them, and who to check out on a rainy day"
>
  <span className="text-lg">⭐</span> Favorite Creators
</a>
```

## Where to Find the Code

### Pattern to Search For
Look for this pattern in your codebase:

```html
<a href="https://findtorontoevents.ca/MOVIESHOWS/" ...>🎬 Movies &amp; TV</a>
```

Or in JSX:
```jsx
<a href="https://findtorontoevents.ca/MOVIESHOWS/" ...>🎬 Movies & TV</a>
```

### Insert Location
Add the new link **immediately after** the Movies & TV link, **before** the System Settings button.

## Quick Find Commands

### If using Git/GitHub:
```bash
# Search for the navigation section
grep -r "Movies & TV" .
grep -r "NETWORK" .
grep -r "System Settings" .
```

### If using VS Code:
- Press `Ctrl+Shift+F` (or `Cmd+Shift+F` on Mac)
- Search for: `Movies & TV` or `MOVIESHOWS`
- Look for files containing the navigation menu

## Common File Locations (Next.js)

If using Next.js, check these locations:
- `app/layout.tsx` (App Router)
- `components/Navigation.tsx`
- `components/QuickNav.tsx`
- `components/Header.tsx`
- `app/components/Nav.tsx`
- `src/components/Navigation.tsx`

## Verification

After adding the code, verify:
1. The link appears in the navigation menu
2. Tooltip shows on hover
3. Link opens in new tab
4. Styling matches other links
