# Disable Guest Sign-In Wall on findtorontoevents.ca

**Date:** 2026-05-25  
**File modified:** `TORONTOEVENTS_ANTIGRAVITY/index.html`, `tdotevent_ca_backup.html`

## Problem
Guest users who browsed the site for ~100+ calendar days were shown a "Sign in to continue" modal overlay that blocked event browsing unless they created an account. The message: "You've been enjoying Toronto events for a while! Create a free account to keep browsing and unlock all features."

## Root Cause
The `checkGuestSiteLockdown()` function (inside an IIFE near end of index.html) polls `https://findtorontoevents.ca/fc/api/guest_usage.php?action=check_site`. When the API returns `allowed: false` after 100 IP-based visits, it calls `showLoginWall()` which injects a full-screen blocking modal (z-index 9998) with a sign-in button.

Two other functions (`highlightSignInIsland()`, `run()`) supported this wall — adding pulsing animation to sign-in buttons and triggering the periodic check.

## Fix
Added early-return guards (`return;`) at the top of 4 functions:

1. **`checkGuestSiteLockdown()`** — now returns immediately, never pings guest_usage API or calls showLoginWall
2. **`showLoginWall()`** — now returns immediately, no modal ever injected
3. **`highlightSignInIsland()`** — now returns immediately, no CSS pulse animation added
4. **`run()`** — now returns immediately, no setTimeout triggers

All original code preserved below the return statements with `/* DISABLED */` comments so it can be re-enabled by removing the return lines if needed later.

## Verification
- No network requests to guest_usage.php on page load
- No `fte-guest-login-wall` div ever injected into DOM
- No `fte-signin-pulse-css` style tag added
- Guests can browse freely regardless of visit count

## Files Changed
- `TORONTOEVENTS_ANTIGRAVITY/index.html` — main live file
- `tdotevent_ca_backup.html` — backup copy (same changes applied)
