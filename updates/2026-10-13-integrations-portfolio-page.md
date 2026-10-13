# 2026-10-13 — Public integrations portfolio page at /integrations

## What was requested

A documentation page at **findtorontoevents.ca/integrations** acting as a tech
portfolio of every integration: CI/CD (GitHub Actions), integration type
(REST/SOAP/scraper/FTP/SMTP/WebSocket), direction (inbound vs outbound),
frequency, the specific webpages each integration serves, asset-class data
coverage, and — importantly — how duplicate integrations/records are prevented
(idempotency), including the TMDB movie/TV refresh path. No secrets may leak.

## What was built

1. **`TORONTOEVENTS_ANTIGRAVITY/integrations/index.html`** (new, self-contained,
   dark-themed static page, no external JS/CSS deps, responsive, sticky TOC).
   Sections:
   1. CI/CD backbone — 371 workflows (306 scheduled), cadence mix,
      concurrency groups, `[skip ci]`, conflict-marker/safe-push guards,
      per-surface deploy model table.
   2. Inbound integrations — events scrapers (Eventbrite, Ticketmaster,
      Meetup, BlogTO, City of Toronto, 30+ sources), TMDB (REST), market data
      (yfinance, Alpha Vantage, Binance, Bybit, CoinGecko, CryptoCompare,
      KuCoin, CoinGlass), CFTC COT (Socrata), SEC EDGAR Form 4, Polymarket +
      Kalshi, Pinnacle/NHL odds, Alternative.me Fear & Greed. Each row:
      protocol, direction, frequency, landing zone, idempotency key.
   3. Outbound integrations — FTPS hosting deploys, Git/GitHub API, Discord
      webhooks, SMTP backups, TradingView paper trading, cross-PC WebSocket
      gateway, LLM provider REST fan-out.
   4. Page → integration map (`/`, `/vr/events/`, `/MOVIESHOWS{,2,3}/`,
      `/audit`, `/fc`, live-monitor) + asset-class coverage table.
   5. Idempotency deep dive — six patterns (natural-key upsert, external-id
      PK, content-hash keys, pre-merge fuzzy dedup, append-only snapshots,
      workflow concurrency groups) + the TMDB "never twice" walkthrough
      (`movies.tmdb_id UNIQUE` + pre-insert check, `imdb_id` secondary,
      `trailers.youtube_key UNIQUE`, `uniq_user_movie` / `uniq_user_queue`).
   6. User-triggered refresh controls — the `/audit` buttons (Reload Page,
      Full Refresh → `workflow_dispatch` of audit-dashboard.yml, Refresh
      Picks → momentum-scanner.yml, Refresh Regime client-side), MOVIESHOWS
      admin fetch buttons, 120s live-price auto-refresh — all idempotent.
   7. Secrets & security posture (names only, no values).
   8. Freshness/reliability monitoring (db-freshness-guardian, asset-class
      watchdog, actions-failure-guardian, cross-DB audit, backup verify).

2. **`.github/workflows/deploy-fte-integrations.yml`** (new) — FTP upload of
   the page to `findtorontoevents.ca/integrations/index.html` (clean directory
   URL). Shares the `fte-ftp-deploy` concurrency group with the other core-site
   deploys so FTP writes never interleave. Includes a pre-upload validation
   step: conflict-marker check + **credential-literal guard** that refuses to
   publish if the page matches password/api-key/token assignment patterns.

3. **AGENTS.md path registry** — new pipeline dependency rows added
   (the integrations page + its deploy workflow), per the registry rule.

## Security note (found during research — FIXED same day)

Three committed files compared against a literal credential instead of an
environment variable. Values are omitted everywhere, including this doc.
All three were fixed on 2026-10-13 (see
`updates/2026-10-13-movieshows-sync-key-hardening.md` for the fix details);
credential rotation remains a separate operator task:

- `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/fetch_new_content.php` — now resolves
  the sync key from `MS2_SYNC_KEY` env or `sync_key.local`, failing closed.
- `TORONTOEVENTS_ANTIGRAVITY/MOVIESHOWS3/api/add-movies-batch.php` — same.
- `scripts/api_integrations.py` — default password literal removed; fails fast
  when `DB_PASS` is unset.

Per operator request, the public page carries no mention of this (the generic
remediation bullet was removed before the 2026-10-13 deploy).

## Verification

- Workflow YAML parses (`yaml.safe_load` OK).
- Page parses as HTML; renders in headless Chromium via Playwright:
  title/h1 correct, 8 sections, 7 tables, 5 stat cards, 9 TOC anchors,
  anchor navigation works, no page-level horizontal scroll, **zero
  console/page errors**. Screenshots at `/tmp/integrations_{top,mid,bottom}.png`.
- Secret scan of the published HTML: clean for password / API-key / bearer
  token assignment patterns; only match is the page's own canonical URL
  (expected). The deploy workflow re-runs a version of this guard on every
  publish.
- Facts spot-checked against source: workflow counts and crons
  (`ls .github/workflows | wc -l`, `grep cron`), audit-dashboard cron
  (`10 * * * *`), TMDB fetch crons (`0 6 * * *`, `0 7 * * *`,
  `0 */6 * * *`), DB unique keys (`tools/setup_torontoevent_databases.py`),
  TMDB dedup (`MOVIESHOWS3/fetch_new_content.php`), events MD5 key
  (`tools/scrape_and_sync_events.py`), COT/insider upserts
  (`tools/refresh_cftc_cot.py`, `tools/refresh_insider_trades.py`), dashboard
  refresh buttons (`audit_dashboard/template.html`).

## Changelog

- 2026-10-13 (later): corrected the Discord outbound row — "announced at most
  once" was misleading (a symbol recurs on every new setup). Replaced with the
  real 3-layer design (`consensus_tracked.discord_sent` per-pick send flag,
  24h/0.5% OPEN-pick skip, `at_discord_notifications` same-second ledger) plus
  a new layer-4 card documenting the FreshPicks G1 short-term cooldown
  (30-min per symbol+direction, levels-change bypass, 15-min signal expiry,
  G7 rate cap currently uncapped at 999 during a testing sprint, state in
  `data/freshpicks_gate_state.json`, rejections audited in
  `at_discord_gate_log`). Verified against
  `cross_aggregation/freshpicks_gate.py` + `audit_trail/mysql_client.py` +
  `audit_trail/migrations/001_discord_audit_tables.sql`.

## Not done / follow-ups

- **Live:** deployed manually over FTP on 2026-10-13 —
  `https://findtorontoevents.ca/integrations/` (HTTP 200, verified in Chromium).
  A `/integration/` (singular) redirect stub was added alongside it.
- Operator follow-up: rotate the MOVIESHOWS sync key (update the
  `MS2_SYNC_KEY` GitHub secret; the next scheduled deploy re-uploads the
  sidecar) and the `DB_PASS` value where used.
