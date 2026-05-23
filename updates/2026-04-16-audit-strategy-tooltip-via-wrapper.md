# Audit dashboard: strategy tooltip — `via` wrapper resolution + narrative

## What was wrong

Strategy column tooltips for **super-signal style labels** (e.g. `super signal (strong) via chatgpt combined`) often showed only:

> No backtest or forward data in leaderboard yet…

even when leaderboard or closed-trade history existed under the **base** name after `via`, or when a short **explanation** of the label was appropriate.

## What changed

**Files:** `audit_dashboard/template.html`, `audit_dashboard/index.html`

1. **`leaderboardKeysFromPick`** — After the initial strategy + `id` prefix keys, walk the growing list and append:
   - Base segment after **` via `** (case-insensitive), with light trailing punctuation trim (aligned with Python track fallback).
   - **`LEADERBOARD_STRATEGY_ALIASES`** expansions for each key (so new `via` bases also get alias resolution).

2. **`leaderboardLookupKeys(stratName, pick)`** — Merges candidates from `pick` and from the displayed `stratName` (with deduplication).

3. **`resolveLeaderboardRow`** — Tries **`source_system::`** composite keys for **every** candidate (not only `pick.strategy`), then legacy map / normalized keys.

4. **`stratTooltipHtml`** — Resolves **closed-trade history** using the same candidate list. When there is still no leaderboard row, injects **`_strategyTooltipNarrative`**: static-map description when present, else short copy for **super signal** and generic **` via `** composites before the existing “no leaderboard data” line.

## How to verify

1. Open the audit dashboard, hover a strategy like **super signal (strong) via …**.
2. Confirm the tooltip either shows **forward/backtest rows** matched via the base name, **history** matched under the base name, or at least the **narrative** paragraph above the “no leaderboard data” notice (instead of only the empty fallback).

## Deploy

Regenerate or sync dashboard assets as usual (CI / `deploy_to_ftp` for `/audit/` if that path is served from this repo).
