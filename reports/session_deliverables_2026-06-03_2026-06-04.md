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

---

## AUDIT STORM ADDENDUM (later in same session, 2026-06-04 02:00Z onwards)

After the initial deliverables doc was written, operator caught a specific
LODE pick claiming +1373% PnL and asked for a deep audit. This triggered
~5 additional hours of work uncovering and fixing a class of bugs that
inflated the AI tournament leaderboard.

### Root causes uncovered

1. **AI stale-training-data + corporate actions**: 553 of 969 (57.1%) top-15-model tournament picks had entry_price drift >25% from market at submission. Models trained on pre-corporate-action data submitted picks at pre-split prices (LODE $0.27 vs market $4.10 post-1:10-split; INTC $10 vs market $116; KO $10 vs market $79; futures contract rolls like CT=F $10 vs $77).

2. **My own portfolio chain side-effect** (PR #503/#507/#510): the chain that fixed 54 empty portfolios also started writing `pnl_pct: None` for symbols with unfetched prices. This exposed 17 sibling crash sites across the codebase where `dict.get(k, default) > 0` returned None and failed comparison/arithmetic. Documented in memory note `feedback-dict-get-default-vs-explicit-none.md`.

3. **`if ac != "CRYPTO"` guards** in 2 places (price_tracker.py:621 + resolve_db_picks.py:143) silently excluded CRYPTO from intrabar replay even after PR #512 wired the OHLC sources. Removed via 893c660c10 + 4fd7cb4c69. CRYPTO REPLAY coverage went 0% → 88.9%.

### Fixes shipped (audit-storm specific)

| Commit | Surface | Result |
|---|---|---|
| `71062a7462` | `tools/ai_tournament/price_tracker.py` — drift-guard | Future mispriced entries auto-rejected as MISPRICED_ENTRY |
| `5853ca6c3b` | `tools/ai_tournament/normalize.py` — leaderboard filter | MISPRICED excluded from WR/PF aggregates |
| (DB UPDATE) | `tournament_picks` MySQL | 553 + 361 (= 914 total) backfilled MISPRICED |
| `9c97671050` + `afe3891cd5` | `audit_dashboard/model.html` | MISPRICED badge + header tile in per-model drill |
| `bb67189faf` + `8c2dcccc42` | `audit_dashboard/ai-tournament.html` | DISPUTED banner expanded |
| `45a2609a93` | `tools/daily_top_picks_filter.py` | Robust panel derived dynamically from cleaned leaderboard |
| `7f896db0ba` | `reports/trading_picks_mispriced_audit_2026-06-04/` | trading_picks essentially clean (3/10) |

### Truth-restoration impact

| Model | WR before | WR after |
|---|---:|---:|
| fireworks_qwen | 92.1% | 18.4% (BUILDING, n=8) |
| gemini_25_pro | 87.5% | 9.3% (BUILDING) |
| gpt4o | 57.7% | 6.7% (BUILDING) |
| claude_opus | 84.4% | 14.7% (BUILDING) |
| deepseek_v4 | 57.9% | 22.1% (BUILDING) |
| cursor_agent | 64.2% | 40.7% |
| **claude_haiku_4_5** | 67.0% | **71.2%** (genuinely real edge) |

### Honest current leaderboard (post-cleanup)

| Rank | Model | n_resolved | WR | PF |
|---|---|---:|---:|---:|
| 1 | claude_haiku_4_5 | 59 | 71.2% | 3.90 |
| 2 | grok3 | 378 | 57.4% | 2.40 |
| 3 | gpt5_mini | 81 | 65.4% | 3.05 |
| 4 | nvidia_deepseek_v4_pro | 55 | 63.6% | 2.95 |
| 5 | kimi_k2_6 | 100 | 60.0% | 2.34 |

Most defensible by sample size: **grok3** (n=378). Most attractive WR: **claude_haiku_4_5** (uniformly 50-78% across all 6 asset classes, max pnl 21%, avg 4.4%).

### Updates page card

`2026-06-04 — Reverse-split + stale-price audit: 553/969 (57.1%) tournament picks marked MISPRICED_ENTRY` — live on findtorontoevents.ca/updates/

### Pilot accumulation (3 live)

| Pilot | Day | Promotion bar |
|---|---|---|
| `macd_rsi_m048` | 1 | 30d / PF≥1.5 / WR≥55% / n≥30 |
| `etf_dual_momentum` | accumulating | n≥30 + forward PF within 30% of lab |
| **`equity_vix_regime_rotator`** (swarm winner) | 1 | 30d / Sharpe within 30% of OOS 3.16 / MDD<5% |

### Session totals (after audit storm)

- 30+ merged PRs (mine + auto-cron + parallel peers)
- 914 MISPRICED tournament picks excluded
- 17 null-coalesce crash sites fixed
- 26/26 INCIDENT #89 .py files scrubbed
- 120/120 portfolios populated
- 1 statistically validated swarm-winner strategy (MC p=0.000, OOS Sharpe 3.16)
- 3 paper-pilots accumulating
- Live `/audit/` surfaces honest end-to-end

