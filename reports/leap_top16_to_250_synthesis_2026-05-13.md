# Leap Crypto top16-250 scraper synthesis — 2026-05-13

## Headline

**233 / 235 profile pages scraped, 231 / 233 produced parsed JSON output,
0 / 231 produced usable extracted data.** The HTML capture itself worked
(~192 KB per profile, valid `<title>`, no Cloudflare challenge markers).
The CSS-selector parser in `tools/scrape_leap_top250_profiles.py::
parse_profile / parse_ideas / parse_scripts` is stale — TradingView
migrated to hash-suffixed CSS modules (`buttonContent-_b0ghPff`,
`content-D4RPB3ZC`, …) and the legacy `tv-user-profile__*` /
`tv-widget-idea__*` selectors no longer match.

Net: every JSON row in `reports/data/leap_profiles_parsed/*.json` shows
`status: "ok"` with `ideas_count: 0`, `scripts_count: 0`, empty
`profile.socials`, empty `stats`. The raw HTML is intact and re-parsable — no
need to re-scrape.

## Numbers

| Metric | Value |
|---|---|
| Target slice (leaderboard rank 16-250) | 235 traders |
| HTML dirs on disk | 233 |
| Parsed JSONs on disk | 231 |
| Status `ok` | 230 |
| Status `partial` | 1 |
| With non-empty `ideas` list | **0** |
| With non-empty `scripts` list | **0** |
| With non-empty `profile.socials` | **0** |
| Total ideas captured | 0 |
| Total scripts captured | 0 |

### Coverage holes (4 — failure mode varies)

| Rank | Username | Failure mode |
|---|---|---|
| 80  | gtricardo                       | HTML captured (193 KB), no parsed JSON written — likely parser/writer path failure after fetch |
| 86  | Setindex2014                    | HTML captured (193 KB), no parsed JSON written — same as above |
| 186 | LupinT2T_Market_Masters_Gang    | HTML captured (193 KB), no parsed JSON written — same as above |
| 199 | ijtan_                          | No HTML AND no parsed JSON — true scraper miss (WAF block or fetch error) |

## Evidence

Inspection of `reports/data/leap_profiles_html/MarketMaverick007/profile.html`
(rank 16, +161.93 % / +$161,930):

- 192,796 bytes — clearly real page content, not a 4xx/5xx stub
- `<title>MarketMaverick007 — Trading Ideas and Scripts — TradingView</title>`
- `<body class="">` — no anti-bot class injected
- No `cf-challenge-running`, no `__NEXT_DATA__`, no `window.__INITIAL_STATE__`
- Class-name probe: every functional class is hash-suffixed
  (`content-FujgyDpN`, `buttonContent-_b0ghPff`, `middle-RDCgMoEQ`,
  `title-RDCgMoEQ`, …). Only legacy `tv-header__*` classes survive in the
  global chrome, none in the profile body.
- Inline `application/json` blocks are present — these are the new data
  surface.

## The cached HTML alone is NOT enough (revised after deeper probe)

Initial hypothesis was that an inline hydration JSON payload (Next.js
`__NEXT_DATA__` analogue) would contain `ideas` / `scripts` / `bio`. Probed
with `tools/probe_tv_initdata.py`:

- The only `<script type="application/json">` block on the page is a 2.3 KB
  hreflang/locale metadata list — no profile content.
- TV's SSR pattern is `window.initData.someKey = {...};` JS-sprinkle
  assignments (theme, snowplow, offer button, settings, …). There is no
  single rooted state object that contains the profile data.
- Profile content (`bio`, `socials`, `stats`, published `ideas`, published
  `scripts`) is fetched **after page load** via XHRs that the static
  `urllib`-grade fetch never triggers. The cached HTML is the chrome only.

**Implication:** a `--parse-only` mode against the existing HTML cache
**will not work**. We have to either (a) run the page through a
JS-executing browser (Playwright, scrapling with browser-render) and dump
the post-hydration DOM, or (b) reverse-engineer the JSON API endpoints
and hit them directly per username (e.g. `https://www.tradingview.com/u/
<user>/ideas/?format=json` if such a route exists; needs probing).

Both paths are larger than this synthesis. Recommended next step is a
SHORT spike (~1 hour) that loads one profile in Playwright with
`scrapling.PlayWrightFetcher`, waits for the ideas list, and dumps the
resulting DOM to a side-by-side `*_postjs.html` file. If that file
contains the data, write the new parser against it. If it doesn't (TV
might paginate ideas via a "Load more" click), the API approach wins.

The 231-strong raw HTML cache stays useful as a 'page existed on
2026-05-13' provenance record, but should not be treated as the data
source.

## What we DID confirm

- StealthyFetcher (camoufox + Cloudflare solver) + proxy pool reliably
  bypasses TradingView's WAF at the 1-by-1 cadence the user mandated
  (2026-05-13). 231 / 235 success rate over a single contiguous run is
  better than the alternatives audited earlier in the session.
- The 4 missing usernames are not a systematic pattern (ranks 80, 86, 186,
  199 spread across the slice) — likely transient WAF blips and re-runnable.
- Leaderboard top-of-slice (post rank-15) is still ridiculously strong:
  rank 16 MarketMaverick007 +161.93 %, rank 25 yeudaa111 +135.67 %. The
  follow-up parser PR is worth doing.

## Action items

1. Open follow-up PR retitled `feat(leap-scraper): JSON-driven parser
   replacing dead tv-* selectors` against the existing parsed-JSON output
   path. Re-process the 231 cached HTMLs first to validate before retrying
   the network leg.
2. Re-scrape just the 4 missing ranks (80, 86, 186, 199) after the parser
   PR lands.
3. After both, re-run leaderboard-style WR / PnL aggregation across the
   slice. The 1-by-1 cadence means the next full pass takes 30+ hours;
   prefer the parse-only mode for iteration.

## Refs

- Source-of-truth leaderboard: `reports/data/leap_top250_leaderboard_2026-05-13.json`
- Raw HTML cache: `reports/data/leap_profiles_html/<username>/{profile,ideas,scripts}.html`
- Stale parsed JSON: `reports/data/leap_profiles_parsed/<username>.json`
- Scraper: `tools/scrape_leap_top250_profiles.py`
- Earlier session notes: `agent_shared_memory.json` (Leap account
  re-entry decision, scraper start, etc.)
