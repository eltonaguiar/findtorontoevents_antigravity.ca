# GHA post-checkout: openclaude submodule exit 128

**Date:** 2026-05-21  
**Workflow:** Deploy findtorontoevents.ca next/events.json (and others using `actions/checkout@v6`)

## Symptom

Job **succeeded** (FTP deploy OK) but **Post job cleanup** logged:

```
fatal: No url found for submodule path 'openclaude' in .gitmodules
Warning: The process '/usr/bin/git' failed with exit code 128
```

## Cause

Git index had orphan **gitlinks** (`160000`) for `openclaude` and `openclaude-vscode` with **no** `.gitmodules` URL mapping (legacy Hermes/opencode integration). `actions/checkout` post-step runs `git submodule foreach`, which fails on those paths.

## Fix

1. **`.github/scripts/fix_orphan_submodules.sh`** — `submodule.recurse false`, drop orphan gitlinks from index in CI.
2. **`deploy-fte-events-json.yml`** — `submodules: false`, run fix script after checkout and in `if: always()` restore step.
3. **`scrape-events.yml`** — use shared fix script.
4. **Repo:** `git rm --cached openclaude openclaude-vscode`; add to `.gitignore` (empty placeholder dirs).

Deploy success was never blocked; this removes red noise and prevents future confusion.
