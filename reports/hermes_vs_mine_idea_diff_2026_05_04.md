# Hermes 60-Model Swarm vs My Super-Swarm + Kimi Reviews — Idea Diff
**Date:** 2026-05-04
**Compared:** Hermes `prs/PR{1,2,3}-60MODEL-ADDITIONS.md` + `updates/SWARM-ANALYSIS-task{1,2,3}*.md` vs my `reports/super_swarm_synthesis_2026_05_04.md` + 4 kimi_review_*.md files.

---

## 1. NOVEL TO HERMES (not in mine)

### Events
- Interactive cluster map with venue overlay + "Near Me" geolocation toggle (1km/5km/10km radius). [Hermes Mercury-v6]
- WCAG 2.2 explicit SC coverage: 2.4.11 focus appearance (3:1, 2px), 2.5.8 target size 24x24, 4.1.3 aria-live status messages. [Mercury]
- Skeleton loaders during filter/settings updates. [Mercury-v3/v4]
- Skip-to-content link + aria-live "N events found" announcer. [Mercury]
- Multi-language / RTL / community-localized feeds (Mandarin, Punjabi, Tagalog). [Mercury-v13/v19]
- Source-preference ML weighting (learn user engagement, A/B personalized vs default). [Mercury-v8/v12]
- Token-bucket + exponential-backoff-with-jitter rate limiting; shared Redis cache by request params. [Mercury-v11/v15]
- Fuzzy (Fuse.js) + semantic embedding search + autocomplete from popular terms. [Mercury-v3/v5]
- Specific new venues: Massey Hall, Roy Thomson Hall, Artscape, TIFF Lightbox, U-of-T. [Mercury-v1/v6]

### Audit
- Multiple-testing correction (Bonferroni / BH-FDR / Holm-Bonferroni) on strategy claims. [Grok-v4/v7]
- PCA orthogonalization + rolling-30d pairwise correlation matrix for portfolio dedup. [Grok-v13/v15]
- Explicit kill-switch types: daily-loss 2%, 5-consecutive-loss halt, vol>95th-pct circuit breaker, per-strategy auto-disable on OOS<0 or PF<1. [Grok-v2/v4/v14]
- Public "scoring governance ledger" + collapsible per-pick scoring-logic component breakdown. [Grok-v11]
- Quantified allocation targets: Equity 40-50%, ETF cap 5%, Cash reserve 70%. [Grok-v3/v5]

### Sports
- Multi-book odds comparison matrix (3+ books, highlight best). [Claude-v9]
- Cross-book arbitrage scanner + best-odds edge alert. [Claude-v7/v16]
- Streak granularity: per-pick-type streaks, milestone notifications, profit attribution per streak, length-distribution + WR-correlation charts. [Claude-v3/v5/v10]
- Fractional Kelly (25-50%) with confidence-scaling by n + 5%-bankroll cap, daily recalc. [Claude-v8/v12]
- Multi-bankroll segregation (Conservative/Aggressive/Props) + bankroll recovery tracker. [Claude-v14/v17]
- Reality-check notifications (15/30/60 min) + loss-pacing 10-min cooldown after 3 losses + self-exclusion 24h/7d/30d. [Claude-v4/v17]
- Immutable AGCO audit log (24+ months retention). [Claude-v17]
- Mobile-specific tests: 44x44 touch targets, iPhone 12 viewport overflow, WebSocket reconnect with heartbeat. [Claude-v6/v13]
- WebSocket binary frames (protobuf) + topic-based subscriptions for edge/odds/streak streams. [Claude-v7]
- Interactive glossary + historical pick autopsy + personalized learning path. [Claude-v8/v14/v15]
- Betting Circles (private invite groups) + community leaderboards + per-pick discussion threads. [Claude-v14/v15]

---

## 2. NOVEL TO MINE (not in Hermes)

### Events
- Gear-panel `backdrop-filter` stacking-context tear-down on scroll → `isolation:isolate` fix.
- Tailwind-JIT chip-active-class brittleness → bind to `data-active`/`aria-pressed`.
- Mutually-exclusive chip state bug (`__thisMonthOverrideActive__` not cleared).
- `findEventByTitle` 20-char prefix collision (Jazz Fest Night 1/2 swap).
- Image-proxy whitelist gap (BlogTO/NowToronto/U-of-T silently CORS-fail).
- Server-side TZ normalization to America/Toronto (Eventbrite UTC vs scraped display strings).
- Cancelled-event filter is text-keyword based, missing Eventbrite `status:'canceled'` events.
- Three existing unwired gear buttons in DOM (lines 994/1021/1029); reuse `toronto-events-settings` localStorage key.
- Server-side dedup already done in `/fc/api/events_get_sources.php` (don't reimplement Jaro-Winkler client-side).
- Blocking gap: `__RAW_EVENTS__` lacks `source` field — max-per-source is no-op until upstream PR.
- Reject the React `.tsx`; adopt vanilla shim; `:has-text()` is invalid CSS.
- Defer PHP backend (50webs is static, no MySQL/auth).

### Audit
- **Shadow probation gate is currently OFF** despite shipped R:R [1.5,2.0] code (`shadow_probation.enabled=false`).
- 11/11 strategies in HIGH degradation alert — common-mode failure signal.
- CRYPTO PF divergence: `asset_class_health` 1.25 (n=8116) vs `hf_stats.by_asset_class` 0.89 (n=1650) — same page contradicts itself.
- Portfolio MDD 680% / Ulcer 332 likely mark-to-market not realized; need split.
- EQUITY raw-vs-capped 10× PnL gap (363 vs 35.71) — outlier-driven.
- COMMODITY KC=F (coffee) = 147% of class PnL — single-symbol concentration.
- BOND missing entirely from `walkforward.by_class`.
- `🏆 TIER-2 PROVEN` literal badge applied below n=100 charter floor.
- `hyro_quan_bridge.json` truncated to 1 symbol (BTCUSDT only), 16 days stale; needs atomic-write + ≥15-symbol assert.
- HyroTrader `trading_days_logged=0` despite real PnL; `largest_single_day_profit_usdt=null`.
- `ASSET_CLASS_EDGE_ANALYSIS.json` 22 days stale (3× n drift).
- Server-side stale-data 503 (HTTP) gate, not client-cosmetic age chips.

### Sports
- Root cause: **`THE_ODDS_API_KEY` expired/unauthorized** — operational rotation, not code (Hermes never identifies this).
- Kimi's secret name `ODDS_API_KEY` is wrong; actual is `THE_ODDS_API_KEY`.
- Win-rate warning at line 457 is unconditional static markup; should gate on `directional_n<15 || wilson_upper<0.5`.
- Two-ledger reconciliation (Pick History 126 vs Bankroll 41) — banner exists, full side-by-side tab missing.
- Cached-odds graceful degradation from `lm_sports_odds_history` when key 401s.
- Auto-open GitHub issue on 401 (extend `sports-betting-refresh.yml:656`).
- n<30 hides ROI rows; Wilson CI bars on every win-rate; "edge proven" badge gated by n≥50 + CLV-beat-rate>50%.
- CLV-beat-rate column per pick + 30d rolling aggregate.
- Vig-net pnl unit test (`-110 stake=100 win → pnl=90.9`).

### Cross-surface
- "Same page contradicts itself" credibility-erosion meta-pattern (audit PF, sports n=3 ROI).
- CI test parsing Tailwind tokens from React build vs grep-asserting in `index.html` selectors (drift guard).

---

## 3. CONSENSUS (both flagged — highest-confidence backlog)

- **Halt FOREX** (PF 0.27 / OOS Sharpe -1.4). Both flag. (Mine: per CLAUDE.md mutate-before-kill protocol.)
- **R:R 1.5-2.0 hard gate** as enforced filter. Both flag. (Mine: branch already shipped, just needs `RR_HARD_GATE_ENABLED=1`.)
- **AGCO compliance block missing** (19+ gate, ConnexOntario 1-866-531-2600, self-exclusion). Both flag P1.
- **Color-coded data-freshness chips** (🟢<5m / 🟡5-10m / 🔴>10m) on sports page. Both flag.
- **EV / Edge% / Kelly display** per sports pick. Both flag.
- **Calendar export (.ics + Google Calendar URL)** on events homepage. Both flag.
- **Gear modal wiring** with max-N-per-source + Eventbrite exemption. Both flag.
- **Wire 5 priority sources:** Ticketmaster, Toronto Open Data, Bandsintown, BlogTO, sports-leagues. Both flag.
- **Transaction-cost integration** in backtests + n≥200 minimum gate. Both flag.
- **Correlation guard ρ≤0.70** in position sizing. Both flag.
- **Ban toxic strategies** (`unknown`, `gainer_compression_relaxed_mut`, `cta_commodity_momentum_term`). Both flag.
- **Remove `regime_bonus` weight** (r=-0.115). Both flag.
- **`pageerror` listener** in Playwright tests. Both flag.

---

## 4. CONFLICT (we disagree)

- **CRYPTO allocation.** Hermes Grok: 0% until OOS>0 (full halt). Mine: HALT, but flagged that the within-class problem is `quan_engine` (18% vol @ PF 0.70) + `unknown` (7% @ PF 0.35) dragging elite strategies (PF 2.34-3.97); cut volume share, don't blanket-zero. CLAUDE.md elite-strategy preservation should win.
- **EQUITY scale-up.** Hermes Grok: scale to 40-50%. Mine: caution — capped/raw 10× gap shows edge is outlier-driven; do not size up until raw-vs-capped reconciled.
- **COMMODITY ban entire `cta_commodity_momentum_term`.** Hermes: BAN. Mine: KC=F concentration cap at ≤15% first; the strategy may be salvageable diversified (mutate-before-kill).
- **PHP user-settings backend.** Hermes Mercury implies build it (settings panel sync). Mine + Kimi-gear-review: defer entirely — 50webs static, no MySQL, no auth.
- **Server-side dedup re-implementation.** Hermes Mercury-v2: implement Jaro-Winkler / fingerprint hash client-side. Mine: redundant — `/fc/api/events_get_sources.php` already does it server-side.
- **Auto-create 4th gear button.** Hermes shim fallback: yes. Mine: no — three already exist, fourth damages UX.
- **Kelly sizing display.** Hermes Claude-v8: 25-50% fractional Kelly with 5% cap. Mine (Kimi sports review): conditional WR warning + Wilson CI is the prerequisite; Kelly display is premature while underlying WR (37.5% n=24) lacks confidence bounds. Order matters: Wilson CI first, Kelly second.

---

## 5. TOP 10 IDEAS TO ABSORB INTO UNIFIED PLAN

1. **Multi-book odds matrix + cross-book arbitrage scanner** [Hermes Claude-v9/v16] — true alpha for sports Goal #2; orthogonal to all my findings.
2. **Per-pick-type streak tracking + Wilson CI confidence-adjusted WR** [Hermes Claude-v3/v5 + mine] — combines Hermes streak granularity with my n<30 statistical-floor gate.
3. **Multi-testing correction (Bonferroni / BH-FDR)** on strategy claims [Hermes Grok-v4/v7] — directly addresses my "11/11 HIGH degradation alert = common-mode failure" finding.
4. **PCA orthogonalization + rolling-30d correlation matrix** [Hermes Grok-v13/v15] — operationalizes my abstract "correlation guard ρ≤0.70".
5. **Explicit kill-switch suite** (daily-loss 2%, 5-consecutive halt, vol>95th-pct breaker, per-strategy OOS<0 auto-disable) [Hermes Grok-v2/v4/v14] — concrete primitives for my "server-side stale-data 503" philosophy.
6. **WCAG 2.2 SC 2.4.11/2.5.8/4.1.3 compliance** [Hermes Mercury] — pure win, zero conflict with my findings.
7. **Reality-check + self-exclusion + immutable AGCO audit log** [Hermes Claude-v4/v17] — extends my "AGCO compliance block" from disclosure-only to full operator-grade.
8. **Tailwind-JIT chip-active brittleness fix** (data-active / aria-pressed) [mine] — silent regression source Hermes missed entirely.
9. **`hyro_quan_bridge` atomic write + ≥15-symbol assertion** [mine] — P0 16-day staleness Hermes missed entirely.
10. **`THE_ODDS_API_KEY` rotation runbook + auto-issue on 401** [mine + Hermes Claude-v7 alerting] — root cause Hermes 60-model swarm never identified despite analyzing the symptom.

---

*Read-only. No code changed. No commits.*
