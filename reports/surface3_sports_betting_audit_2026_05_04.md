# Surface 3 — Sports Betting Audit (2026-05-04)

**URL:** https://findtorontoevents.ca/live-monitor/sports-betting.html
**Probe artifacts:** `tmp/surface3_artifacts/` (console.json, requests.json, sections.json, tabs.json, picks.json, page.png)
**Probe script:** `tmp/surface3_sports_probe.js`
**Run time:** 2026-05-04 ~01:26 local (UTC-4), wall-clock ~5.2s page load.

## Executive summary

The page loads cleanly with **0 JS errors and 0 network failures** on the primary host, BUT the **production 50webs DB is DOWN** for the sports tables — every primary `findtorontoevents.ca/live-monitor/api/sports_*.php` endpoint returns `{"ok":false,"error":"Sports DB connection failed"}`. Page UX is salvaged by an automatic mirror failover to `torontoevent.net` (which IS up and serves real data), but that mirror's most recent picks are dated **2026-04-25 — 9 days stale**. The existing in-page stale-banner fires correctly (`>48h` threshold, see `sports-betting.html:2110`) and a yellow "Stale picks: ... Odds API key is unauthorized" warning is rendered.

Real (mirror-served) bankroll/performance numbers, headline cohort:
- Lifetime: **41 bets, 9W-15L-0P-17V, WR 37.5%, ROI 25.29%, bankroll +$65.06**
- Post-guardrail cohort (`value_bet_gr202604`, since 2026-04-04): **n=15, 7W-8L, WR 46.67%, ROI 27.91%, Wilson95 [24.81%, 69.88%]** — promising but small.

Top finding: **the page is a graceful-degradation success story but is silently serving 9-day-old picks with no per-card "X days ago" badge.** Users can't tell at a glance that "Today's Picks" are actually from April 25.

## Live probe results

| Endpoint (findtorontoevents.ca) | Status | Body |
|---|---|---|
| `sports_picks.php?action=today` | 200 | `{"ok":false,"error":"Sports DB connection failed"}` |
| `sports_bets.php?action=dashboard` | 200 | `{"ok":false,"error":"Sports DB connection failed"}` |
| `sports_odds.php?action=credit_usage` | 200 | `{"ok":false,"error":"Sports DB connection failed"}` |
| `sports_clv.php` | **404** | endpoint does not exist on disk |

| Endpoint (torontoevent.net mirror — failover target) | Status | Notable fields |
|---|---|---|
| `sports_picks.php?action=today` | 200 | `value_bet_count=6, last_updated=2026-04-25, generated_at=2026-04-25` (**9d stale**) |
| `sports_bets.php?action=dashboard` | 200 | bankroll 1065.06, total_bets 41, WR 37.5%, ROI 25.29% |
| `sports_odds.php?action=credit_usage` | 200 | The Odds API: 414 credits remaining, 0/500 monthly used |

23 API responses captured; **DB-down counted in 3 primary endpoints**, mirror returned `ok:true` for all surveyed endpoints.

Tabs detected (15): Today's Picks, Playoffs, Odds Comparison, Arbitrage, Steam Moves, My Bets, Performance, Pick History, Glossary, System Analysis, Research & Future. Sport filters (15): NHL/NBA active; WNBA/NFL/MLB/CFL/MLS/NCAAF/NCAAB/EPL/LaLiga/UFC/Tennis/Golf marked `empty`.

DOM card count at landing: **0 (`pick-card`/`data-pick` selectors)** — picks render into `#value-bets-grid` via `innerHTML` strings, not class-tagged cards. Probe upgrade needed if per-card EV/odds capture becomes a recurring need.

## Precision verification

Rolling tracker numbers are populated **only from the mirror** (primary DB-down means the production-host bets endpoint cannot confirm). Self-reported on the mirror:

| Cohort | n | W | L | P | V | WR | ROI | PnL | Wilson 95 |
|---|---|---|---|---|---|---|---|---|---|
| Lifetime (all settled) | 24 | 9 | 15 | 0 | 17 | 37.5% | 25.29% | +$65.06 | 21.16–57.29 |
| Post-guardrail v1 (`gr202604`) | 15 | 7 | 8 | 0 | 0 | 46.67% | 27.91% | +$48.40 | 24.81–69.88 |

Sanity: Lifetime ROI 25% with WR 37.5% implies large average win odds — consistent with the page's own "HEAVY UNDERDOG BIAS (Now Fixed)" admission (7/9 wins from underdogs at 6x-31x). Post-guardrail cohort is the trustworthy slice but n=15 is well below the 30-trade Wilson stability point and the 100-trade charter floor. Verdict: **"proven" status NOT yet earned per CLAUDE.md Goal #2 (≥4-week live + non-negative CLV trend); can claim "directionally encouraging".**

`sports_clv.php` does not exist → no closing-line-value cross-check possible. CLV trend tab on the page is unbacked.

## Stale-data risk register

| # | Risk | Severity | Evidence |
|---|---|---|---|
| 1 | Primary DB has been intermittently down; no auto-recovery monitoring visible | **HIGH** | 3/3 sports_*.php endpoints return DB-failure on findtorontoevents.ca |
| 2 | Mirror-served picks are 9 days stale; >48h banner triggers but per-card age badge missing | **HIGH** | `last_updated:"2026-04-25"`, today is 2026-05-04 |
| 3 | The Odds API key reported "unauthorized" → no new picks can be generated even if DB recovers | **HIGH** | banner text `sports-betting.html:524` |
| 4 | `sports_clv.php` 404 — CLV tab/feature has no backend | MEDIUM | filesystem listing of `live-monitor/api/` |
| 5 | Pick-card DOM lacks `data-*` attributes for sport/odds/EV → hard to verify automatically | MEDIUM | `picks.json` empty, all rendering via `innerHTML` strings |
| 6 | No per-section "Updated Xm ago" indicator (only one global `#last-refresh`) | MEDIUM | `sports-betting.html:419` |
| 7 | No responsible-gambling external resource (ConnexOntario/19+) — only "paper simulation" disclaimer | LOW-MED | `sports-betting.html:427-428` |
| 8 | DB-failure JSON returns HTTP 200, not 503 → caches, monitors, and CDN treat as success | MEDIUM | `db_connect.php:19-22` |
| 9 | `db_connect.php` only handles `connect_error`, not query failures or stale-row detection | MEDIUM | `db_connect.php` (25 lines total) |
| 10 | Stale guard threshold is 48h — too generous for "Today's Picks" semantics | MEDIUM | `sports-betting.html:2110` |

## Proposed enhancements (ranked)

1. **Per-card data-age badge.** Add `Updated Nd ago` chip on every pick card; red >24h, amber 6-24h, green <6h. (`sports-betting.html:2148-2160` render loop.)
2. **Drop stale threshold from 48h → 24h** for "Today's Picks" semantics. Add separate >6h amber. (`sports-betting.html:2110`.)
3. **HTTP 503 + `Cache-Control: no-store` on DB failure** so monitors/CDN see real status. (`db_connect.php:19-22`, all `sports_*.php` early-exit branches.)
4. **Mirror-feed auto-swap is already partially live** (page transparently serves torontoevent.net data) — formalize: `multi_source_odds_fallback.py` exists; wire a 15-min freshness check that tries OddsAPI → OddsJam → BallDontLie odds → cached. Sketch:
   ```
   for src in [oddsapi, oddsjam, balldontlie, espn, cache]:
       data = src.fetch(timeout=4)
       if data and data.age_seconds < 900: return data
   return cache  # serve last-known with explicit age badge
   ```
5. **Responsible-gambling banner upgrade**: include ConnexOntario 1-866-531-2600 + 19+ chip + self-exclusion link. The current "paper simulation only" line is fine for liability but doesn't meet RG best practice.
6. **Live precision dashboard**: surface 7d/30d rolling WR+PF+ROI per sport on Performance tab using `cohort_guardrail_v1` slice (already returned in `sports_bets.php`).
7. **Data-freshness telemetry beacon**: 10% sample rate emits `{age_seconds, source, sport, n_picks}` to a lightweight endpoint; alarm if p95 age > 1h for 30 min.
8. **Implement `sports_clv.php`** so the CLV tab has data, OR remove the tab.
9. **Tag pick cards with `data-event-id`, `data-sport`, `data-ev`, `data-odds`** so e2e probes can verify without HTML scraping.
10. **Page-level red banner if `>50%` of section endpoints failed in last poll** (currently only the picks-grid emptiness signals failure).

## Top 3 ship-today fixes

1. **Per-card stale-age chip** — `live-monitor/sports-betting.html:2148-2160` (inside the `for (var i = 0; i < vb.length; i++)` render loop). Compute `ageH = (Date.now() - new Date(b.commence_time||d.generated_at).getTime())/3600000;` then inject `<span class="age-chip age-${ageH>24?'red':ageH>6?'amber':'green'}">${fmtAge(ageH)}</span>` next to the recommendation badge. ~10 lines, no new fetch.
2. **HTTP 503 on DB-down** — `live-monitor/api/db_connect.php:19-22`. Replace:
   ```php
   if ($conn->connect_error) {
       echo json_encode(['ok'=>false,'error'=>'...']); exit;
   }
   ```
   with `http_response_code(503); header('Cache-Control: no-store'); ...`. One-liner per file; also patch the duplicated check in `sports_picks.php:115`-ish guard. Lets the failover proxy and uptime monitors actually see the failure.
3. **Tighten stale-banner threshold to 24h** — `live-monitor/sports-betting.html:2110`. Change `(_ageH > 48)` → `(_ageH > 24)` and add a second amber tier at `>6`. The 48h threshold was set when picks refreshed daily; current mirror-served behavior makes "Today's Picks" silently 9 days old without tripping the banner-of-shame strongly enough.

## Data integrity notes

- `sports_picks.php` and `sports_bets.php` already return `last_updated`/`generated_at` — frontend has the data, just needs to render it per-card.
- `cohort_guardrail_v1` slice in `sports_bets.php` is the right hook for surface-3 precision metrics; n=15 is too small for tier verdicts but trajectory is positive (PF implied ~1.6 from 7W/8L * avg odds).
- Cursor's hardening commit `2f05d6db2be` on PR #777 covers the EST-bucketing regression; orthogonal to this audit.

## Repro

```
node tmp/surface3_sports_probe.js   # writes tmp/surface3_artifacts/*
```
Read-only. Hits production. ~5s.
