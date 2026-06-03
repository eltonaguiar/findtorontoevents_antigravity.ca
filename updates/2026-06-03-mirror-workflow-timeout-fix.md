## What was broken

The stale `Mirror: findtorontoevents.ca  torontoevent.net` failure on `main` was not an auth problem and not a destination upload problem. The job died in the **download** step after hitting its 15-minute cap while recursively pulling non-site ballast from the source 50webs FTP tree.

The failed run log showed the mirror step spending time on paths like:

- `backups/20260131-175859/...`
- `MOVIESHOWS3/tests/node_modules/...`

Those are not required to mirror the live site payload to `torontoevent.net` or `tdotevent.ca`, but they were still being walked because the workflow only excluded secrets (`db_config.php`, `.env`, `.htpasswd`) and not bulky archive/dependency trees.

## What I changed

I tightened `.github/workflows/mirror-site.yml` so the lftp `mirror` commands now exclude:

- `^backups/`
- `(^|/)node_modules/`

The excludes were added to the source download step and the reverse-upload steps for both mirror destinations, keeping the workflow focused on live site content instead of archived snapshots and dependency folders.

## Why this matters

The mirror workflow already has a deliberate 15-minute timeout on each FTP leg to fail fast instead of burning the full job wall clock. That only works if the mirrored tree is scoped sanely. Excluding the bulky non-site directories preserves the timeout guard while removing the main cause of recent stale failures.

## How it was verified

- Inspected the failing run `26889022117` and confirmed the timeout occurred in `Download from findtorontoevents.ca (50webs FTP)`.
- Verified from the run log that the step was transferring `backups/...` and `.../node_modules/...` paths immediately before timing out.
- Reviewed the updated workflow to ensure the new excludes apply consistently to the download and both reverse-upload mirror commands.
