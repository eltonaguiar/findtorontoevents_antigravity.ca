---
title: FavCreators Google Sign-In Client ID Fallback
date: 2026-05-23
---

# FavCreators Google Sign-In Client ID Fallback

## What Was Broken

Google sign-in on `findtorontoevents.ca/fc/` could send users to Google's OAuth error page with `Missing required parameter: client_id`.

The live `findtorontoevents.ca` endpoint rendered `CLIENT_ID=""`, while the alternate domains rendered the expected public Google OAuth client ID.

## What Changed

`favcreators/docs/api/config.php` now uses the known public Google OAuth client ID as the default fallback when `.env`, `getenv()`, and `$_ENV` do not provide `GOOGLE_CLIENT_ID`.

This keeps configured environments overrideable while preventing production from emitting an empty Google Identity Services config.

## Verification

- PHP 5.2 compatibility validator passed for `favcreators/docs/api/config.php`.
- Live OAuth config endpoints were checked before deployment and showed the main domain had an empty client ID.
