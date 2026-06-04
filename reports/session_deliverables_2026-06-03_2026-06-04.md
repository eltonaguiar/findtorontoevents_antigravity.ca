# Session Deliverables — 2026-06-03 / 2026-06-04 (claude-opus-4-7)

**Sessions span:** ~2026-06-03 14:00 UTC → 2026-06-04 01:30 UTC (~12 hours)
**PRs merged:** 15+
**Operator-visible outcomes:** /audit/ai-tournament + /audit/pf populated, mostly DISPUTED banners shipped, weekly filter report, INCIDENT #89 fully scrubbed.

---

## Live-site impact

| Surface | Before | After |
|---|---|---|
| `/audit/pf.html?key=*` drill columns (Weight%, TP, Current$, Unrealized%) | blank | populated |
| Empty AI tournament portfolios | 54 / 120 (45%) | **0 / 120** |
| Open positions across all portfolios | 476 | **1,050** |
| `/audit/ai-tournament.html` DISPUTED banner | absent | live |
| `/audit/model.html` UNVERIFIED banner | absent | live |
| Model drill-down hyperlinks on leaderboard | absent | live |
| pf.html "Last mark" → "Last updated" | confusing | renamed |
| Trail-only aggressive TP="—" | confusing | "Trail" badge with tooltip |
| Non-CRYPTO intrabar replay coverage | 13–23% | **100%** |
| CRYPTO intrabar replay coverage | 0% | pending validation (chain of 4 PRs needed; just unblocked) |
| `git grep stocks1234560 -- '*.py'` | 26 .py files | **0** |

---

## PRs merged (chronological)

1. **#488** export_json import hoist (P0; introduced workflow-break — superseded by #494)
2. **#494** sys.path hotfix replacing #488 — populates pf.html drill columns
3. **#497** 6j correlation sizer off-by-one
4. **#500** DISPUTED banner + drill-down on ai-tournament + model.html
5. **#501** BOND added to BLOCKED_ASSET_CLASSES (Pillar 1 freeze)
6. **#503** Decimal→float in engine.mark_position — unblocked 44 empty portfolios
7. **#507** aimlapi/gh_models alias map → gpt4o picks (6 more portfolios)
8. **#510** allowlist pre-filter before 25-cap (1 more portfolio) → 120/120 populated
9. **#512** Binance OHLC for CRYPTO intrabar replay
10. **#513** macd_rsi_m048 shadow generator + daily GHA cron
11. **f273b6db57** KuCoin Tier-3 OHLC fallback (GHA unblocked from Binance)
12. **#501 + sed batches** INCIDENT #89 scrub — 26 .py files in 4 batches
13. **db-password-leak-guard.yml** Forward-fence CI prevents new leak additions
14. **06091018ee** Workflow timeout 20→45m for Step 2 (Resolve DB picks) headroom
15. **893c660c10 + 4fd7cb4c69** Sibling fixes removing CRYPTO guards from price_tracker.py:621 + resolve_db_picks.py:143 (the actual last lines blocking CRYPTO REPLAY)

---

## Standing items requiring operator action

1. **DB password rotation** (INCIDENT #89 follow-up) — 26 .py files are scrubbed, but the literal exists in git history. Rotate the DB password + update GH Secrets/env vars to retire the exposed value.
2. **ETF_VERIFIED_DUAL_MOMENTUM_ENABLED=1** — flip the GH repo var to start the ETF VDM shadow accumulation (sidecar wired, default OFF).
3. **CRYPTO data source for production scanner** — Binance is geo-blocked from GHA runners; ai_tournament now uses KuCoin Tier-3 which works. Consider replicating that pattern for the production scanner's CRYPTO data feed.
4. **Mutation protocol on 4 MUTATE_CANDIDATEs** — blocked on row-level data scarcity (3–15 rows vs ≥30 required). Document: `reports/mutation_2026-06-03/BLOCKER.md`. Option A (skip) recommended.

---

## Reports filed

- `reports/weekly_filter_2026-06-03T23-02Z.md` — `/money-maker-readyv2` honest verdict + AI tournament panel filter + Kelly sizing
- `reports/mutation_2026-06-03/BLOCKER.md` — mutation protocol data gap
- `reports/affected_portfolios_resolver_artifact_2026-06-03.md` — AI tournament vs portfolio_mix family separation
- `AGENTS.md` — relative-imports vs script-invocation gotcha (saves future agents from PR #488's mistake)

---

## Updates page entries (live on findtorontoevents.ca/updates/)

- 2026-06-03 — Portfolios 54 empty → 0 + 3 root causes (PRs #503/#507/#510)
- 2026-06-03 — Weekly real-money filter (/money-maker-readyv2): 0/8 classes Tier-2

---

## Standing memory entries (`memory/`)

- `feedback-relative-imports-vs-script-invocation.md` — gotcha that broke PR #488
- `project-ai-tournament-wr-artifact-2026-06-03.md` — DISPUTED banner rationale
- Existing entries reinforced: shared-tree silent revert, stash loss, peer-broadcast handoff
