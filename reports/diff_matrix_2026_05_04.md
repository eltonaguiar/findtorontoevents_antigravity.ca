# Diff Matrix — Hermes vs Mine vs Branches (2026-05-04)

Inputs: `reports/hermes_code_diff_review_2026_05_04.md`, `reports/hermes_vs_mine_idea_diff_2026_05_04.md`, `reports/super_swarm_synthesis_2026_05_04.md`, the 4 `reports/kimi_review_*` files, branches `feat/rr-hard-gate-shadow-2026-05-04`, `fix/today-tomorrow-week-zero-events-2026-05-04`, `fix/sports-stale-data-hardening-2026-05-04`, Hermes's `pr1/pr2/pr3-*` branches.

## Code-side matrix

| Asset | Source | Status | Action |
|---|---|---|---|
| `TORONTOEVENTS_ANTIGRAVITY/index.html` Today/Tomorrow/Week fix | mine: `fix/today-tomorrow-week-zero-events-2026-05-04` (`d85e6fd6b6e`) | **Authoritative** | Open PR from this branch |
| Same file on `pr1-events-page-tests` | Hermes copy | **Byte-for-byte duplicate** | DROP branch |
| `audit_dashboard/template.html` "fix" on `pr2-audit-pages-gap-analysis` | Hermes | **Pure CRLF→LF churn (35K-line cosmetic diff)** | DROP branch — would conflict with everything |
| `tests/events-page.spec.ts` (102 lines) | Hermes | Aspirational selectors (`aria-pressed`, `getByText('today')`); will false-green or hard-fail | DROP, rewrite against actual selectors |
| `tests/audit-pages.spec.ts` (189 lines) | Hermes | Testids that don't exist; `isVisible()`-guarded → silent no-ops | DROP, rewrite |
| `tests/test_event_filters_chips.spec.ts` (86 lines) | Hermes | **Correct selectors** (`.glow-text.tabular-nums`, `glass-panel`, `🔥 Today`) | **KEEP**, cherry-pick onto fresh branch |
| `feat/rr-hard-gate-shadow-2026-05-04` (`149fbacd`) | mine | 7/7 new tests green, full suite no-new-failures | Open PR |
| `fix/sports-stale-data-hardening-2026-05-04` (`40f98fe0`) | mine | Per-card age chip + 24h banner + 503 on DB-fail | Open PR |
| `pr3-sports-betting-tests` | Hermes branch name | **Zero Hermes commits — just my Today/Tomorrow fix** | Misnamed; ignore |

## Idea-side matrix (cross-engine consensus)

### Tier 1 — both Hermes + mine flagged (highest confidence)
1. R:R [1.5, 2.0] hard gate — already shipped on `feat/rr-hard-gate-shadow-2026-05-04`
2. FOREX halt + mutate-before-kill protocol
3. Ontario AGCO compliance block (19+, ConnexOntario, self-exclusion, reality checks)
4. Freshness/age chips per card on sports page — already shipped on `fix/sports-stale-data-hardening-2026-05-04`
5. Calendar export (.ics + Google Calendar URL) on events page
6. Wire the 3 unwired gear buttons; vanilla shim only (no React .tsx, no PHP backend on 50webs)
7. Top-5 Toronto sources to integrate (scraper repo, not homepage): Ticketmaster, Toronto Open Data, Bandsintown, BlogTO RSS, sports leagues
8. n ≥ 200 gate + transaction-cost integration in backtests
9. Correlation guard (ρ ≤ 0.70) in position sizer
10. Ban 3 toxic strategies (`unknown`, `gainer_compression_relaxed_mut`, `cta_commodity_momentum_term`)
11. Remove `regime_bonus` from composite score (anti-predictive r=-0.115)
12. Add `page.on('pageerror')` listener (not just `console.error`) in test suites
13. EV/Edge/Kelly display per pick on sports page

### Tier 2 — novel-to-Hermes (worth absorbing)
- Multi-book odds matrix + Pinnacle arbitrage scanner (sports)
- Multi-testing correction (Bonferroni / BH-FDR) for strategy selection
- PCA orthogonalization for portfolio-dedup (vs simple correlation cap)
- Kill-switch primitives with thresholds: 2% daily loss / 5-consec / vol-95th-pct
- Per-pick-type streak granularity (NBA / NHL / UFC separate trackers)
- Fractional Kelly scaled by confidence band
- WCAG 2.2 specific SCs: 2.4.11, 4.1.3, 2.5.8 (focus / status / target-size)
- Mobile 44×44 touch-target Playwright tests

### Tier 3 — novel-to-mine (operational P0s Hermes missed)
- `THE_ODDS_API_KEY` rotation is the **actual root cause** of 9-day sports staleness (operational, not code)
- `shadow_probation.enabled = false` despite shipped R:R gate — flip the env flag
- `hyro_quan_bridge.json` truncated to 1 symbol (BTCUSDT only) since Apr 18 — atomic write race condition
- CRYPTO PF self-contradiction on dashboard: `asset_class_health.PF = 1.25` (n=8116) vs `hf_stats.PF = 0.89` (n=1650) — same page, two contradictory numbers
- EQUITY raw-vs-capped PnL 10× gap (363.32 raw vs 35.71 capped) — outlier-driven edge claim
- KC=F (coffee) = 147% of COMMODITY PnL — single-symbol concentration risk
- Tailwind-JIT chip-state brittleness (`from-[var(--pk-600)]` literal class)
- 3 unwired gear buttons in `index.html` (`:994, :1021, :1029`) and missing `source` field on `__RAW_EVENTS__` — blocking-data-gap for max-per-source feature
- Hermes's "60 models" was 60 calls to `tencent/hy3-preview:free` — same model

### Tier 4 — conflicts (we disagree)
| Topic | Hermes | Mine | Resolver |
|---|---|---|---|
| CRYPTO posture | Blanket halt all crypto | Cut `quan_engine` 18% volume share + `unknown` 7%; preserve elite strategies (PF 2.34-3.97) | **Mine** (per CLAUDE.md mutate-before-kill) |
| EQUITY scaling | Scale to 40-50% allocation | Hold flat until capped/raw 10× gap reconciled | **Mine** (raw inflated by outliers) |
| PHP backend for gear settings | Build it | Defer — 50webs is static-only, no MySQL | **Mine** (Kimi-review verdict) |
| React `GearSettingsModal.tsx` | Adopt as-is | Reject — vanilla shim only | **Mine** (Kimi-review verdict) |

## Open PRs (`gh pr list` not used per session memory; checking via local `git log`)

3 fix branches ready for PR open:
- `feat/rr-hard-gate-shadow-2026-05-04` → P0
- `fix/today-tomorrow-week-zero-events-2026-05-04` → P0
- `fix/sports-stale-data-hardening-2026-05-04` → P0

Hermes's 3 `pr1/pr2/pr3` branches: 1 dropped (duplicate), 1 dropped (CRLF), 1 misnamed (no Hermes content).
