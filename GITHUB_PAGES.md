# GitHub Pages

This repo deploys to **GitHub Pages** via GitHub Actions.

## Enable Pages (one-time)

1. In the repo: **Settings** → **Pages**
2. Under **Build and deployment** → **Source**: choose **GitHub Actions**
3. Save (no branch needed; the workflow deploys the artifact)

## After pushing

- **Workflow:** `.github/workflows/deploy-pages.yml` runs on every push to `main` (and on **Run workflow**)
- **Site URL:** `https://<your-username>.github.io/findtorontoevents_antigravity.ca/`
- The workflow copies `index.html`, `next/`, `data/`, and rewrites asset paths so chunks and events load under the project path.

## Local development

For local testing (root at `/`), use `python tools/serve_local.py` and open `http://localhost:9000/`.
