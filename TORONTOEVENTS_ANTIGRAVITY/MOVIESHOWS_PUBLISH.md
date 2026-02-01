# MovieShows – Publish to GitHub & FTP

## What’s set up

- **movieshows** app: static export with basePath `/MOVIESHOWS` (works on GitHub Pages and FTP).
- **FTP deploy**: `npm run deploy:sftp` (from repo root) builds MovieShows and uploads to **findtorontoevents.ca/MOVIESHOWS**, and uploads redirects so MOVIES, SHOWS, TV, TVFINDER → MOVIESHOWS.
- **GitHub Pages**: Workflow in `movieshows/.github/workflows/deploy-pages.yml` deploys to **eltonaguiar.github.io/MOVIESHOWS** when you push the `movieshows` folder to [eltonaguiar/MOVIESHOWS](https://github.com/eltonaguiar/MOVIESHOWS).

## Publish to GitHub (eltonaguiar.github.io/MOVIESHOWS)

1. **Push the app to the MOVIESHOWS repo**
   - From this repo, either:
     - Copy the contents of the `movieshows` folder into a clone of [eltonaguiar/MOVIESHOWS](https://github.com/eltonaguiar/MOVIESHOWS) and push, or  
     - Add that repo as a remote and push the `movieshows` subtree/branch.
   - Ensure the repo contains at least: `package.json`, `next.config.ts`, `src/`, `public/`, `.github/workflows/deploy-pages.yml`.

2. **Turn on GitHub Pages**
   - In the MOVIESHOWS repo: **Settings → Pages**.
   - Under **Build and deployment**, set **Source** to **GitHub Actions**.

3. **Deploy**
   - Push to `main`. The workflow builds the static export and deploys to GitHub Pages.  
   - Live site: **https://eltonaguiar.github.io/MOVIESHOWS/**

## Publish to FTP (findtorontoevents.ca/MOVIESHOWS)

From the **TORONTOEVENTS_ANTIGRAVITY** repo root (where `package.json` and `scripts/deploy-simple.ts` live):

```bash
npm run deploy:sftp
```

This will:

- Build the main site (if needed).
- Build **movieshows** (`movieshows/out`).
- Upload **movieshows/out** to **findtorontoevents.ca/MOVIESHOWS**.
- Upload **movieshows-redirects** `.htaccess` files so these redirect to MOVIESHOWS:
  - findtorontoevents.ca/MOVIES  
  - findtorontoevents.ca/SHOWS  
  - findtorontoevents.ca/TV  
  - findtorontoevents.ca/TVFINDER  

After a successful run, the app is at **https://findtorontoevents.ca/MOVIESHOWS/** and the four paths above redirect there.

## Redirects (FTP)

Redirects are implemented with Apache `.htaccess` files in **movieshows-redirects/** (MOVIES, SHOWS, TV, TVFINDER). They are uploaded automatically by `deploy:sftp`. If your host doesn’t support `.htaccess`, configure the same 301 redirects in the server’s Apache config or control panel.
