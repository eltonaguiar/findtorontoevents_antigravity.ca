# Critique Plan v2 (incorporates round-1 feedback)

You are reviewing v2 of a unified test+integration plan for findtorontoevents.ca. v1 had 1 ship-with-minor / 5 major-revisions / 2 file-read failures. v2 incorporates those revisions.

PLAN CONTENT FOLLOWS BELOW (inlined; do not look for the file). Critique what's in front of you.

---

# Unified Test + Integration + Ordering Plan (2026-05-04, **v2** — incorporates round-1 swarm feedback)

**Round 1 verdict:** 1 ship-with-minor, 5 major-revisions, 2 file-read failures. Major revisions accepted in v2: corrected static-only architecture anchor, escalated AGCO to P0, fixed gear-modal sequencing, added deploy/rebase/alarm steps. See `swarm_runs/plan_review_round1/_summary.json` for details.

Inputs synthesized: my super-swarm (3 surfaces × 11 engines), 4 Kimi-review subagents, Hermes value/code/idea reviews, 3 fix branches landed locally.

## 1. Architecture anchors (non-negotiable)

- **`TORONTOEVENTS_ANTIGRAVITY/index.html` is hand-coded vanilla** (4,800+ lines). NO React build. Any React `.tsx` proposal must be adapted to vanilla JS.
- **50webs host is mostly static, with PHP available under `/live-monitor/api/`** (sports endpoints work). The homepage `index.html` itself is hand-coded vanilla. PHP IS available for sports/live-monitor; for the events-homepage user-account features, MySQL/auth infrastructure does NOT exist → use localStorage Phase 1, defer event-side PHP indefinitely. Sports `sports_picks.php`, `sports_bets.php`, `sports_odds.php`, `db_connect.php` are all fully supported.
- **`__RAW_EVENTS__` lacks a `source` field.** Any "max-N-per-source" feature is a no-op until upstream events-pipeline PR adds provenance.
- **Chip filter active state = Tailwind class `from-[var(--pk-600)]`**, NOT `aria-pressed`. All Playwright tests must use `toHaveClass(/from-\[var\(--pk-600\)\]/)`.
- **Sports backend uses env var `THE_ODDS_API_KEY`** (not `ODDS_API_KEY`). Key rotation is operational (GitHub secret), not code.
- **Charter floors:** T2 = PF>1.5 / WR>50 / MDD<20 / n≥100; T1 = PF>2 / WR>55 / MDD<10 / n≥200.
- **CLAUDE.md mutate-before-kill protocol** governs strategy demotion. No blanket halts without `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`.

## 2. Ordering (priority gates)

### P0 — ship-this-week (operational + already-coded)
1. **Rotate `THE_ODDS_API_KEY`** — GitHub secret rotation. 15 min, operational. Restores sports data freshness.
2. **Open PRs for the 3 ready branches:** `feat/rr-hard-gate-shadow-2026-05-04`, `fix/today-tomorrow-week-zero-events-2026-05-04`, `fix/sports-stale-data-hardening-2026-05-04`. CI green required before merge.
3. **Cherry-pick Hermes's `tests/test_event_filters_chips.spec.ts`** (only salvageable Hermes file) onto a new branch `tests/playwright-chip-regression-2026-05-04`. Verify the 5 chip × counter>0 + visible≥1 assertions on the live page.
4. **Drop Hermes branches** `pr1/pr2/pr3-*` after extracting the one test file. They're either duplicates or CRLF churn.
5. **Flip `RR_HARD_GATE_ENABLED`** after 14-day shadow-mode log review. Concrete monitoring: append `[RR_GATE]` rejected picks to `logs/rr_gate_shadow_2026_05_04.log` with `(symbol, rr, strategy, timestamp)`; daily cron `tools/rr_gate_shadow_daily_summary.py` aggregates rejected-band PF vs in-band PF; flip gate ON only if rejected-band PF < 1.0 AND in-band PF > 1.5 over ≥100 closed picks per band.
6. **Run `tools/deploy_sports_files.sh`** after each sports PR merge (CLAUDE.md mandate — 50webs has no shell, files don't reach prod without this).
7. **`git stash && git pull --rebase origin main && git stash pop`** before any push (CLAUDE.md mandate; multiple peer Claude instances can race).

### P0 — dashboard credibility (blocks "phenomenal performance" goal)
6. **Add hf_stats vs asset_class_health split disclosure** on `/audit` (CRYPTO PF 1.25 vs 0.89 contradiction).
7. **Add capped vs raw PnL footnote** on EQUITY card (10× gap, 363.32 raw vs 35.71 capped).
8. **Add KC=F concentration cap** (≤15% of COMMODITY PnL).
9. **Tiered n-guard** in tiering logic: `n<10` → "insufficient_data" (suppress all stats); `10 ≤ n < 100` → status capped at "candidate"; only `n ≥ 100` (T2 floor per CLAUDE.md) eligible for "stable"/"deploy". Current FUTURES n=2 slipping through is the symptom; the full guard is the fix.
10. **Fix `hyro_quan_bridge.json` atomic-write race** (truncated to 1 symbol since Apr 18; restore 15 symbols).
11. **Hyro `trading_days_logged` from journal** (currently 0 despite -70.66 USDT PnL).

### P0 — regulatory (escalated from P1 per round-1 feedback)
12. **Ontario AGCO compliance block** in `live-monitor/sports-betting.html`: 19+ gate, ConnexOntario 1-866-531-2600 link, self-exclusion path, reality-check messaging. Required wording per AGCO regs:
    - 19+ age gate (not 18+) — Ontario provincial law
    - "If you or someone you know has a gambling problem, call ConnexOntario at 1-866-531-2600 (24/7)"
    - Self-exclusion path link to https://www.connexontario.ca/en-ca/
    - Reality-check messaging at 30-min session intervals
    - "iGaming Ontario" or "AGCO" registration disclaimer if claiming licensed status; otherwise prominent "paper simulation only — no real money" banner.

### P1 — ship-this-week (sports UX, non-regulatory)
13. **Conditional WR warning** (n<30 hides ROI, replaced with "Insufficient data, need 30+").
14. **Server-side stale-data 503** in `sports_picks.php` — extends just-landed DB-fail 503; if `max(created_at) < NOW() - 24h`, return 503.
15. **CLV-beat-rate column** on every pick + 30d rolling aggregate.
16. **Phase 1 gear-settings modal — SHADOW MODE** — vanilla shim, localStorage-only, max-N + Eventbrite exemption UI present but `source`-field-dependent filters DISABLED until P2#23 lands. Wire to existing 3 gear buttons (`index.html:994, :1021, :1029`). Banner: "Source filtering activates when scraper-side `source` field ships". Avoids no-op feature confusion.

### P1 — events page UX
17. **Calendar export** (`.ics` + Google Calendar URL) per card.
18. **Chip active-state stability** — supplement Tailwind class with `data-active="true"` attribute on click.
19. **Mutually-exclusive chip state** — clear `__thisMonthOverrideActive__` when other date chips clicked.
20. **Thumbnail prefix-match dedup** — `findEventByTitle` returns null on ambiguous matches.
21. **Tabular view sort headers** — clickable Date/Venue/Category column headers.
22. **Image proxy whitelist expansion** — add BlogTO/NowToronto/U-of-T CDNs.

### P2 — next-sprint (architecture + diversity)
23. **Add `source` field to events pipeline** (upstream scraper repo). Required before P1#16 max-per-source actually filters anything.
24. **Top-5 Toronto data source integration** — Ticketmaster, Toronto Open Data, Bandsintown, BlogTO RSS, sports leagues. Skip Meetup (OAuth2), FB Events (ToS).
25. **Multi-testing correction** (Bonferroni or BH-FDR) on strategy-selection pipeline.
26. **PCA orthogonalization** for portfolio dedup (replaces naive correlation cap).
27. **Kill-switch primitives**: 2% daily loss / 5-consec / vol-95th-pct.
28. **Fractional Kelly scaled by confidence band** in `alpha_engine/position_sizer.py`.
29. **WCAG 2.2 SC 2.4.11 / 4.1.3 / 2.5.8** focus/status/target-size compliance.

## 3. Test plan (selectors verified)

### Surface 1 — events page
- **Existing salvage**: cherry-pick `tests/test_event_filters_chips.spec.ts` (correct selectors).
- **New Playwright spec** `tests/events-page-correct.spec.ts`:
  - `page.on('console')` + `page.on('pageerror')` listeners with `KNOWN_BAD_PATTERNS = [/counter\s*oscillation/i, /hydration/i, /chunk-load-failed/i, /undefined is not/i]` and `ALLOWLIST = [/posthog/i, /google.*ads/i]`.
  - 5 chip filters × counter assertion (`.glow-text.tabular-nums` text>0) + visible cards (`.group:not([style*='display:none']) [class*='glass-panel']` count≥1).
  - Click "🔥 Today" via `getByRole('button', {name:/Today/})` not `getByText('today',{exact:true})`.
  - Active-state assertion: `toHaveClass(/from-\[var\(--pk-600\)\]/)`.
- **Mobile profile** at 375×667 — verify mega-menu doesn't clip "Earn / Sign In".

### Surface 2 — `/audit`
- **New spec** `tests/audit-pages-correct.spec.ts`:
  - Page load + console-error guard.
  - Assert each asset-class card shows the n value.
  - Assert FUTURES card shows "insufficient_data" if `n<10` (P0#9 enforcement).
  - Assert COMMODITY card surfaces concentration warning (P0#8 + KC=F note).
  - Assert hf_stats vs asset_class_health disclosure visible on CRYPTO card.

### Surface 3 — sports betting
- **New spec** `tests/sports-betting-correct.spec.ts`:
  - Console + pageerror listeners.
  - Age-chip color thresholds (green<6h / amber 6-24h / red>24h).
  - Assert 19+ gate present + ConnexOntario link.
  - Assert any `.tier-row` with `n<30` does NOT show ROI percentage.
  - Mock 503 from `/api/sports_picks.php` and assert "Failed to load picks" banner.
- **Vig-net pnl unit test** `tests/sports_pnl_regression.py`:
  - Place simulated −110 odds (1.909) win bet, stake=100; assert `pnl == 90.9` (not 190.9).

## 4. Integration plan

1. **No `git push`** without user approval per current standing instruction.
2. **Stale `.git/index.lock`** (1-min-old, Hermes done) — ask user before clearing.
3. **Each PR opened individually** with the original landed-branch commit as the base; do NOT collapse.
4. **AGCO compliance block (now P0#12)** ships FIRST and INDEPENDENTLY — regulatory weight.
5. **Phase 2 events-pipeline `source` field** (P2#23) is a pre-req for P1#16 (gear settings) to function — sequence accordingly. Phase 1 ships in shadow-mode UI.
6. **Pre-push CLAUDE.md mandates:**
    - `git stash && git pull --rebase origin main && git stash pop` before any push (peer-instance race).
    - `tools/deploy_sports_files.sh` after sports merges (50webs no-shell host).
    - Never commit secrets; never run dashboard generators locally (overwrites live HTML).
7. **CI flakiness mitigation:** retry=2 on Playwright tests; mark live-site smoke tests as `@live-smoke` so they don't gate PR merges if findtorontoevents.ca itself is down.
8. **Pre-deployment smoke**: run new specs against staging URL `findtorontoevents.ca/staging/` (if present) OR mark live tests as non-blocking and run post-deploy.
9. **Updates/index.html entry** — final step after testing complete; per-domain (events / audit / sports) categorized P0/P1/P2 + done/today/partly-done.

## 5. Rollback

Each PR has a single-commit revert path. Specific concerns:
- R:R hard gate: env-flag-gated, default-OFF, no rollback needed (turn off the flag).
- Today/Tomorrow/Week fix: revert reverts to the chip-state class-detection bug; mitigate by cherry-picking the multi-day overlap semantics into a smaller patch first.
- Sports stale-hardening: revert restores 48h banner + no age chip; user-visible regression — only revert if a downstream PHP endpoint breaks.

## 6. Out-of-scope (explicit)

- Building a PHP backend for user accounts on 50webs (host doesn't support it).
- Adopting React `GearSettingsModal.tsx` (vanilla shim only).
- Blanket-halting CRYPTO (per CLAUDE.md mutate-before-kill).
- Running another giant `tencent/hy3-preview:free` × 60 swarm (4/10 value per `reports/hermes_swarm_value_assessment_2026_05_04.md`).

---

## Required output JSON

```json
{
  "engine": "<your engine name>",
  "verdict": "ship-as-is|ship-with-minor-revisions|major-revisions-needed|reject",
  "remaining_concerns": [
    {"id": "C-XX", "severity": "critical|high|medium|low", "issue": "...", "fix": "...", "confidence": 0.0-1.0}
  ],
  "round1_issues_addressed": "<which previously-flagged issues are now resolved>",
  "round1_issues_NOT_addressed": "<which are still missing>",
  "approval_to_execute": true|false
}
```

Hard rules: do NOT contradict CLAUDE.md mutate-before-kill, do NOT recommend React .tsx adoption, do NOT recommend deferring AGCO compliance below P0. Output ONLY the JSON envelope.
