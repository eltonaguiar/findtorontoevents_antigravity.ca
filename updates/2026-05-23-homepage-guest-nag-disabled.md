---
title: Homepage Guest Nag Disabled
date: 2026-05-23
---

# Homepage Guest Nag Disabled

## What Was Broken

Signed-in users could still see the full-page "Sign in to continue" nag on the Toronto Events homepage.

The backend guest-usage endpoint had already been relaxed to allow browsing, but the live homepage HTML still contained the old client-side login-wall script.

## What Changed

The canonical homepage deploy flow now has a targeted `--main-index-only` mode that uploads `TORONTOEVENTS_ANTIGRAVITY/index.html` to the live site root.

The deployed homepage no longer contains the `fte-guest-login-wall` lockdown script, so signed-in users are not blocked by the stale nag overlay.

## Verification

- `node tools/check_syntax.js TORONTOEVENTS_ANTIGRAVITY/index.html` passed.
- `python -m py_compile tools/deploy_to_ftp.py tools/validate_php52.py` passed.
- Live HTML was checked for removal of `fte-guest-login-wall`.
