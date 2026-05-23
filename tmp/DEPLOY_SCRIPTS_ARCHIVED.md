# tmp/deploy_*.py — ARCHIVED / DO NOT RUN

**2026-04-17 audit:** the `tmp/deploy_*.py` scripts were one-shot ad-hoc deploys
(MOVIESHOWS3 thumbnails, cache-bust, mercy fixes, etc.). Several of them have
latent footguns:

- Hard-coded `FTPGODADDYPASS` credential reference but verify URL on
  `findtorontoevents.ca` (50webs) — the two-host confusion that caused the
  2026-04-14 root-dump incident.
- Some are missing `import os` at the top (`deploy_force.py`, `deploy_final.py`,
  `deploy_final_fix.py`, `deploy_fix_v3.py`) so they crash immediately — if
  someone "fixes" the import, they'll deploy to the wrong host.
- All of them use relative `cwd("MOVIESHOWS3")` paths that land at session root.

**Action taken:** no code changes inside the files (diff noise, hard to review),
but any future contributor running them should treat this file as a stop-sign.

If you genuinely need one of these scripts, port the logic into
`tools/deploy_to_altsite.py` (which has explicit host/target guards) rather than
reviving a `tmp/` one-shot.
