# Weather sidebar: source-checked sci-fi TV picks

## What needed updating

The weather page's news sidebar had no curated TV-series recommendations.
Several supplied roundups mixed series premieres with episode dates or
conflicting upcoming dates.

## What changed

Added a Sci-Fi TV watchlist immediately below Latest News, using the
existing sidebar styles. The automated news feed, weather controls, player,
books and other sidebar sections remain unchanged.

- VisionQuest: Disney+, October 14, 2026, per [Marvel](https://www.marvel.com/articles/tv-shows/marvel-television-visionquest-release-date).
- Sparks of Tomorrow: Netflix, July 5, 2026, not a September debut, per [Netflix](https://www.netflix.com/tudum/articles/sparks-of-tomorrow-release-date-news).
- Star City: Apple TV, May 29, 2026, per [Apple](https://www.apple.com/tv-pr/originals/star-city/).
- The Boroughs: Netflix, a 2026 series explicitly described as streaming now by [Netflix](https://www.netflix.com/tudum/articles/the-boroughs-duffer-brothers-new-series).
- Upcoming Blade Runner 2099: November 25, 2026, per [Amazon](https://www.aboutamazon.com/news/entertainment/blade-runner-2099-prime-video).
- Upcoming Neuromancer: January 22, 2027, per [Apple](https://www.apple.com/tv-pr/originals/neuromancer/).

Descriptions are original summaries, not copied articles or critic rankings.
The selection date is October 31 in Toronto (November 1 UTC). Older premieres
are explicitly not labelled new this week. Unverified September/October anime
episode dates and the unverified Rings of Power date were not adopted.
The two upcoming series have separate labels and a dates-may-change caveat;
neither is presented as already streaming or critically acclaimed.

## Source preservation

`weather/index.html` was absent from both the current shared checkout and
refreshed `origin/main`. Its exact live production HTML was retrieved before
editing and preserved here rather than deploying an older worktree version.
The only content change against that live baseline is the watchlist block.

## Verification

- Exact baseline comparison passed: removing only the watchlist block yields
  the original production HTML byte-for-byte.
- Offline Playwright DOM checks passed at 1280px and 390px: four entries,
  official studio links, `target="_blank"` with `rel="noopener"`, correct
  premiere labels, and existing news/weather elements preserved.
- Direct diff review found only the 26-line watchlist insertion. No JavaScript,
  weather calculations, fetch endpoints or existing controls changed.
- Targeted FTPS upload passed with a pre-upload production drift guard and
  byte-for-byte FTP read-back verification.
- Public HTTPS verification passed using `curl -fsSL` and `cmp`; served HTML
  matches the validated local file byte-for-byte.
- Live browser check passed: opening the side panel shows all four TV titles,
  the original four-item watchlist is visible, and existing weather loaded a temperature of 6 C.

The PR follow-up expands the list to six entries, including the two verified
upcoming releases. Its offline DOM/baseline checks are repeated before commit;
production remains at the verified four-item version until this follow-up is
deployed.

The older weather test uses `#hero-temp`, which is absent from the inspected
live baseline; this check used the current `#cur-temp` instead. No claim is
made that the legacy network-dependent weather suite passed. No dashboard
generator or broad site deployment was run.
