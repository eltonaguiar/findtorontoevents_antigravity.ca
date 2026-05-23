# Super-Swarm Synthesis Report — 2026-05-04

**3 super-swarms × 10-11 engines = 31 analyses, ~175 KB raw output.**
Surfaces audited: `/audit`, `/` (events homepage), `/live-monitor/sports-betting.html`.

Outputs: `swarm_runs/super_audit_v3/`, `swarm_runs/super_events_v1/`, `swarm_runs/super_sports_v1/`.

---

## Engine Reliability Scoreboard (lessons learned)

| Engine | Audit | Events | Sports | Reliability | Notes |
|---|---|---|---|---|---|
| **claude** | 13 KB | 18.5 KB | 13.5 KB | ★★★★★ | Always deepest, most evidence-cited. Slowest (~3 min). |
| **deepseek** | 7.2 KB | 11.5 KB | 7.2 KB | ★★★★★ | Fast, well-structured, no schema fails. |
| **cerebras** | 7.0 KB | 9.7 KB | 7.1 KB | ★★★★★ | Sub-30s, clean JSON, good signal. |
| **opencode** | 6.1 KB | 7.6 KB | 6.2 KB | ★★★★ | Reliable but verbose. |
| **kilo** | 4.4 KB | 6.1 KB | 4.9 KB | ★★★★ | CLI, slower (~50s), but stable. |
| **gemini** | 4.4 KB | 5.7 KB | 4.4 KB | ★★★★ | Improved after env-var fix. |
| **xai** | 4.3 KB | 5.8 KB | 4.1 KB | ★★★★ | Decent depth, fast. |
| **ollama_cloud** | 0.2 KB ❌ | 10.8 KB | 7.3 KB | ★★★ | Highly variable; first audit run schema-rejected. |
| **inception** | 0 KB ❌ | 0 KB ❌ | 0 KB ❌ | ★ | **0/3 produced output despite valid key.** Drop. |
| **openrouter** | 0 KB ❌ | 0 KB ❌ | 0 KB ❌ | ★ | **0/3 produced output.** Drop or use only as model proxy. |
| **nous** | (skipped) | — | — | — | User: out of tokens. |

**Lessons:**
1. **Drop inception + openrouter** until upstream issue diagnosed — both passed health checks but returned empty `*.raw.txt` for every prompt. The swarm's `transport_status="ok"` masks this; needs a tokens_in/out>0 assertion as a real liveness check.
2. **Top-5 reliable fleet:** `claude, deepseek, cerebras, opencode, kilo` — these 5 should be the default `consensus-5` preset. Adding `gemini, xai` extends to 7; `ollama_cloud` is opportunistic.
3. **Env-var pickup is the silent killer.** Bash and PowerShell don't share Windows User env vars by default. Always source `tmp/super_swarm/.envkeys` (built from `[Environment]::GetEnvironmentVariable($k,'User')`) before any swarm run. Without it 7/11 engines fail invisibly.
4. **No schema enforcement on first run** = silent acceptance of empty output. Future swarms should drop `--json-strict` (it just stamps invalid; doesn't fail loud) and instead post-validate `len(raw_text) > 500` before counting an engine as "OK".

---

## Surface 1 — `/audit` (consensus from claude, deepseek, cerebras, opencode, kilo, xai, gemini)

### P0 critical findings (≥3 engine consensus)

| # | Finding | Evidence | Confidence |
|---|---|---|---|
| **A1** | **Shadow probation gate is OFF** despite documented R:R [1.5, 2.0] PF 5.81 edge. | `dashboard_data.json::shadow_probation.enabled = false` | 0.97 |
| **A2** | **11/11 strategies in HIGH degradation alert** — common-mode failure, not random noise. | `dashboard_data.json::performance_alerts` | 0.93 |
| **A3** | **CRYPTO PF divergence**: `asset_class_health.profit_factor = 1.25` (n=8116, full history) vs `hf_stats.by_asset_class.CRYPTO.profit_factor = 0.89` (n=1650, recent). Recent subset shows PF<1. | dashboard data | 0.88 |
| **A4** | **Portfolio MDD 680% / Ulcer Index 332** — 34× the T1 charter floor. Likely mark-to-market, not realized; MUST be split on the dashboard. | `hf_stats.hf_metrics` | 0.91 |
| **A5** | **EQUITY raw vs capped PnL gap of 10×** (363.32 raw vs 35.71 capped @ 10% cap). Reported edge driven by 1-2 outlier wins. | `system_clean_metrics.alpha_engine` | 0.82 |
| **A6** | **COMMODITY KC=F (coffee) concentration = 147% of total PnL.** Single-symbol risk masquerading as asset-class edge. | `system_clean_metrics.multi_asset_cot.concentration_warning` | 0.85 |

### P0 verdicts (cross-engine consensus)

- **EQUITY**: caution (T2-adjacent but degrading + capped/raw gap)
- **COMMODITY**: caution (PF 1.78 headline vs 1.09 recent; concentration risk)
- **BOND**: investigate (PF/WR meet T2 but n=18 < 50 floor)
- **CRYPTO**: **HALT** (recent subset PF 0.89, MDD 674%, Sharpe -0.60)
- **ETF**: caution (PF 1.24 < 1.5 floor, walkforward worst-fold WR 20%)
- **FOREX**: **HALT** — mutate-before-kill protocol per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`
- **FUTURES**: investigate (n=2; null PF could leak through routing filters)
- **SPORTS** (asset class): no resolved trades flowing into health; pipeline gap

### Top P0 PRs to open

1. **Enable shadow_probation** with R:R [1.5, 2.0] gate already shipped in branch `feat/rr-hard-gate-shadow-2026-05-04`. Set `RR_HARD_GATE_ENABLED=1` after a 14-day shadow log review.
2. **Add hf_stats / asset_class_health split disclosure** on the dashboard. Two contradictory PF numbers exist for every class without a footnote explaining the sample selection.
3. **Add capped vs raw PnL footnote to EQUITY card.** Report capped (35.71) as primary; show raw as a hover tooltip with "outlier-driven" warning.
4. **Add KC=F concentration cap** at ≤15% of COMMODITY class PnL until diversification improves.
5. **Add n<10 hard guard in tiering logic** — FUTURES n=2 with WR=100% could pass naive filters and corrupt routing.

---

## Surface 2 — `/` events homepage (consensus from claude, deepseek, cerebras, opencode, kilo, gemini, xai, ollama_cloud)

### P0/P1 findings (≥2 engine consensus)

| # | Severity | Finding | Confidence |
|---|---|---|---|
| **E1** | high | **Gear panel blurs/disappears on scroll** — likely `backdrop-filter` stacking-context tear-down on parent repaint. Fix: `overflow:hidden` on body when panel open + `isolation: isolate` on panel root. | 0.82 |
| **E2** | high | **Chip active-state detection is brittle** — uses literal Tailwind JIT class `from-[var(--pk-600)]`. If React rebuilds with a different color token, all chips silently revert to inactive (= 0-events bug returns). Add `data-active="true"` or rely on `aria-pressed`. | 0.85 |
| **E3** | medium | **Mutually-exclusive chip state not enforced** — clicking This Month then Today can leave both visually active because `__thisMonthOverrideActive__` isn't cleared. | 0.72 |
| **E4** | medium | **Thumbnail prefix-match collision** — `findEventByTitle` uses 20-char prefix; events sharing prefixes (e.g. "Toronto Jazz Festival — Night 1/2") get swapped images. Fix: return null on ambiguous match. | 0.78 |
| **E5** | medium | **Tabular view has no sort affordance** — counter says "N EVENTS FOUND" but no clickable column headers. | 0.90 |
| **E6** | medium | **Mobile mega-menu likely overflows at 360-480px** — rightmost items (Earn, Sign In) may be clipped. Fix: horizontal scroll + scroll-snap. | 0.65 |
| **E7** | low | **Image proxy whitelist incomplete** — only Eventbrite + Fatsoma covered. BlogTO/NowToronto/U-of-T images bypass proxy and may CORS-fail silently. | 0.70 |

### Data-quality concerns

- **TZ ambiguity**: Eventbrite returns UTC; BlogTO/NowToronto return display strings. Server-side normalize all to America/Toronto before writing `events.json`.
- **Cancelled-event filter is text-keyword based** — Eventbrite events with `status: 'canceled'` (no "cancelled" in title) slip through. Fix at scraper level.

### Top Toronto data sources to integrate (cross-engine consensus, ranked by events/week × ease)

1. **Toronto Open Data Portal** — free, official, festivals + civic events (~50/wk)
2. **Ticketmaster Discovery API** — free tier 5K calls/day, concerts/sports/theatre (~200/wk)
3. **Bandsintown** — free, music-only (~150/wk)
4. **AGO + ROM + Harbourfront Centre** — scrape, high-quality curated (~30/wk combined)
5. **TIFF / Hot Docs / Inside Out** — film festival schedules, RSS available
6. **U of T / TMU / OCAD events feeds** — academic + public (~80/wk)
7. **TPL (Toronto Public Library)** — workshops, kids events (~100/wk)
8. **BlogTO Events** — already partially covered; expand depth
9. **TodoCanada Toronto** — editorial-curated (~30/wk)
10. **Pride Toronto / Nuit Blanche / Caribbean Carnival** — major event calendars

---

## Surface 3 — `/live-monitor/sports-betting.html` (consensus from claude, deepseek, cerebras, opencode, kilo, gemini, xai, ollama_cloud)

### P0/P1 findings

| # | Severity | Finding | Confidence |
|---|---|---|---|
| **S1** | **CRITICAL** | **n=3 sample sizes drive headline ROI claims** (NBA +164%, NHL −100%). Statistically meaningless. **Hide tier-vs-ROI until n ≥ 30.** Add Wilson CI bars; gate "edge proven" badge behind n≥50 AND CLV-beat-rate>50%. | 0.90 |
| **S2** | high | **Mirror-failover stale-serve gap** — age chip is client-side cosmetic. PHP `sports_picks.php` should server-side `HTTP 503` if `max(created_at) < NOW() - 24h`. (Just-landed branch covers DB-fail 503 but not stale-data 503.) | 0.82 |
| **S3** | medium | **EST date bucketing relies on `Intl.DateTimeFormat`** — fails in legacy Android WebView / minimal-ICU Chromium. Add try/catch with UTC-offset fallback. | 0.65 |
| **S4** | low | **TheOddsAPI 500-credit budget has no exhaust alerting.** When credits hit 0, fallback to ESPN/etc may use different vig structures, silently corrupting EV. | 0.75 |
| **S5** | high | **Responsible-gambling disclaimer partial** — "paper simulation only" present but does NOT meet Ontario AGCO standards (no 18+, no ConnexOntario number, no self-exclusion link). | 0.85 |
| **S6** | medium | **CLV (closing line value) tracking unverified** — Pinnacle anchoring code present, but no per-pick CLV-beat-rate column on the page. Without CLV, edge claims are unfalsifiable. | 0.78 |
| **S7** | low | **vig-net pnl unit-tested?** — assumed but no test asserting `−110 stake=100 win → pnl=90.9 (not 190.9)`. | 0.70 |

### Top P0 PRs (after `fix/sports-stale-data-hardening-2026-05-04` lands)

1. **Hide n<30 ROI rows** + add Wilson CI bars + edge-proven gate.
2. **Server-side stale-data 503** in `sports_picks.php` (extends just-landed DB-fail 503).
3. **Ontario AGCO compliance pass** — full disclaimer text with ConnexOntario 1-866-531-2600 link, 18+ gate, self-exclusion path.
4. **CLV-beat-rate column** on every pick + 30d rolling aggregate.
5. **Vig-net pnl unit test** in `tests/sports_pnl_regression.py`.

---

## Cross-surface meta-findings

1. **Dashboard credibility erosion** is the dominant theme — 3 of the 6 P0 audit findings are "two contradictory PF numbers shown on the same page". Same pattern emerged in sports (n=3 displayed as if statistically meaningful). **Fix: add explicit sample-size + selection-criteria footnotes to every metric badge** site-wide.

2. **Brittleness from class-name string matching** appears in BOTH events (Tailwind JIT class for chip detection) AND audit (asset-class verdict tags via CSS class). Replace with `data-*` attributes or `aria-*` semantics for stability.

3. **Stale-data detection is half-implemented** — events page has cancelled-event filter, sports has age chip, audit has resolver-v2. None have **server-side guards that return non-200 status codes** when staleness exceeds threshold. CDN/uptime monitors can't catch outages without this.

4. **Hand-coded HTML host** (4,800 lines of `index.html`) is constantly at risk of regression from React-bundle drift in the embedded event-grid widget. Consider a CI test that parses key Tailwind tokens from the React build and grep-asserts they still exist in `index.html` selectors.

---

## Lessons learned (process)

| Lesson | Action |
|---|---|
| Bash and PowerShell don't share Windows User env vars. | Always source `tmp/super_swarm/.envkeys` before swarm runs; built from `[Environment]::GetEnvironmentVariable($k, 'User')`. |
| `transport_status="ok"` lies — engines can return empty raw with 200. | Add `len(raw_text) > 500` check in `swarm_run.py` summary; flag as `EMPTY_OUTPUT` not `OK`. |
| `--json-strict` silently downgrades — doesn't fail loud. | Drop the flag; use post-hoc `swarm_inspect.py` instead. |
| Inception + OpenRouter dropped 0 KB across all 3 swarms. | Investigate before re-adding to fleet. Probably api_consult.py response-parsing bug for these providers. |
| Claude is consistently the deepest source but slowest. | Always include claude; budget ~3min for it; use it as the "anchor" engine. |
| Cerebras + DeepSeek are the fastest-deepest combo. | Use as `fast-cheap-2` preset for time-bounded runs. |
| Counter-oscillation pattern in `KNOWN_BAD_PATTERNS` regex (Kimi insight) is gold. | Promote any field-discovered bug into shared utils as a permanent regression net. |

---

## Kimi-archive review subagents (4 parallel runs, all completed)

Each reviewed one Kimi MD against live state and produced a focused review .md in `reports/`:

### `reports/kimi_review_audit_gap_2026_05_04.md`
- **14/18 Kimi gaps AGREE-not-fixed**, 1 DISAGREE (`hyrotrader_journal.json` exists), 3 NEEDS-MORE-INFO. None of the 3 just-landed branches address Kimi's gaps.
- **Verified P0 evidence**: `dashboard_data.json::asset_class_health.FOREX` PF 0.27 n=1176; `walkforward.by_class` missing BOND key; `hyro_quan_bridge.json` only `BTCUSDT` (Apr 18 stale); `hyrotrader_picks.json::account_snapshot.trading_days=0`; `template.html:918` literal `🏆 TIER-2 PROVEN` badge.
- **Top-3 PRs**: (1) `fix/hyro-quan-bridge-atomic-write-2026-05-04`, (2) `fix/audit-dashboard-headline-source-clarity-2026-05-04`, (3) `chore/hyro-trading-days-from-journal-2026-05-04`.

### `reports/kimi_review_enhancement_proposals_2026_05_04.md`
- **Kimi authored against React/Next.js + Postgres + JWT** — none of which exist here. `index.html` is 6,178 lines vanilla. Every `.tsx` / `interface` / `CREATE TABLE` block must be adapted.
- **Three gear buttons already in DOM** (`index.html:994, :1021, :1029`) and all three are unwired. localStorage `toronto-events-settings` already in use (`:3154`).
- **Multi-source dedup already done server-side** by `/fc/api/events_get_sources.php` — no need to re-implement Jaro-Winkler client-side.
- **Top-3 PRs**: (1) `feat/homepage-calendar-export` (1d), (2) `feat/homepage-settings-panel` wiring the gear (2d), (3) `feat/homepage-max-per-source` (1d).
- **Top-5 sources** to ingest in scraper repo (not here): Ticketmaster, Toronto Open Data, Bandsintown, Sports leagues, BlogTO RSS. Skip Meetup (OAuth2) and FB Events (ToS).

### `reports/kimi_review_sports_betting_2026_05_04.md`
- **Kimi's #1 root cause (expired TheOddsAPI key) AGREE.** Env var actually named `THE_ODDS_API_KEY` (not `ODDS_API_KEY`). Wiring correct in `db_config.php:74`, `sports_picks.php:1384`, `sports_odds.php:254`, `sports_bets.php:908`. Fix is **operational** (rotate + update GitHub secret), not code.
- **`fix/sports-stale-data-hardening` addresses symptoms only** — correctly. Won't bring data back; will make staleness visibly truthful.
- **AGCO compliance MISSING** — only "paper simulation" disclaimer at line 428. No 19+ age gate, no ConnexOntario helpline.
- **Top-3 PRs**: (1) conditional WR warning + Wilson CI, (2) cached-odds fallback from `lm_sports_odds_history`, (3) reconciliation sub-tab. Plus AGCO compliance block as a fast independent PR.

### `reports/kimi_review_gear_integration_2026_05_04.md`
- **Verdict: adopt vanilla shim with modifications; reject the .tsx; defer the PHP backend.**
- **Selector mis-bind risk**: Kimi used Playwright-only `:has-text()` + case-sensitive `[title*="config"]` (live host has `title="System Configuration"`). Bind to `#top-right-controls button`; remove auto-create-fourth-gear fallback.
- **Blocking data gap**: `__RAW_EVENTS__` events lack a `source` field. Max-per-source is a no-op until upstream events-pipeline PR adds provenance.
- **PHP backend is dead on 50webs** (static host, no MySQL, no auth). Defer entirely; Phase 1 ships localStorage-only.
- **Security**: no P0/P1. Three medium items for eventual backend (CSRF token, source-allowlist + length cap, `__proto__` guard in client deepMerge).
- **PR**: branch `feat/gear-settings-modal-phase1`, 2-line homepage edit + 2 new files in `TORONTOEVENTS_ANTIGRAVITY/static/`. Phase 1 = max-N + Eventbrite exemption + source toggles (with "activates when provenance lands" banner).

---

## Aggregated PR backlog (post-Kimi-review consensus)

**Ship-this-week (P0):**
1. Open the 3 already-landed branches as PRs once git lock clears (R:R hard gate, Today/Tomorrow/Week 0-events, sports stale-hardening).
2. **Rotate `THE_ODDS_API_KEY`** + update GitHub secret (15 min, operational).
3. `fix/hyro-quan-bridge-atomic-write` (P0 — 14 symbols dropped, stale since Apr 18).
4. `fix/audit-dashboard-headline-source-clarity` (P0 — hf_stats vs asset_class_health 6.5× sample-size split disclosure).
5. `chore/hyro-trading-days-from-journal` (P0 — `trading_days_logged=0` despite real PnL).

**Ship-this-week (P1):**
6. `feat/sports-conditional-wr-warning` (n<30 hides ROI, adds Wilson CI bars).
7. `feat/sports-agco-compliance-block` (19+ gate, ConnexOntario helpline, self-exclusion).
8. `feat/gear-settings-modal-phase1` (vanilla, localStorage-only, max-N + Eventbrite exemption).

**Ship-next-sprint (P2):**
9. `feat/homepage-calendar-export` (.ics + Google Calendar URL).
10. `feat/sports-cached-odds-fallback` (read from `lm_sports_odds_history` when key unauthorized).
11. `feat/audit-server-side-stale-503` (HTTP 503 when max(created_at) < NOW()-24h).
12. `chore/events-source-field-provenance` (upstream events-pipeline — required for max-per-source feature to do anything).

---

## Next steps

1. Open 3 of the just-landed branches as PRs (R:R hard gate, Today/Tomorrow/Week 0-events, sports stale-hardening) once Hermes git lock clears.
2. Open a `consensus-5` swarm preset (claude, deepseek, cerebras, opencode, kilo) in `swarm_run.py`.
3. Wire up the 5 new Kimi-derived personas (`playwright_architect`, `audit_gap_analyst`, `ux_enhancer`, `sports_betting_analyst`, `code_implementer`) into the persona router.
4. Schedule the 4 review subagents' outputs to be merged into a single follow-up PR backlog .md.
5. Commit this synthesis + Kimi archive once git lock clears.
