# SUMMARY — Quantitative Audit of findtorontoevents.ca/audit (2026-11-14)

Auditor: DeepAI Code agent (this thread). Isolated worktree: `.inspect-wt/` @ f54efb3b4a.
Live data fetched from findtorontoevents.ca/audit/data/* at ~15:45Z 2026-11-14.
GitHub Actions state from GitHub REST API same day. Peer-review handoff folder:
`2026-11-14/inspect-wt_20261114_1058/`.

## Overall verdict: **FAIL as an investment product; PASS as a self-critical data pipeline**

The system generates and deploys predictions hourly and honestly documents its own failure
("0/9 asset classes money-ready"), but the product surfaces (active picks, per-class stats,
hyrotrader) are polluted with zombies, garbage rows, contradictory statistics, and stale panels.

## Sub-verdicts

| Area | Verdict | One-line evidence |
|---|---|---|
| Actions health | **FAIL** | Alpha Live Scanner failing; yfinance price refresh failing 2 nights; CI failing; audit-dashboard cancelled 3/10 (0 jobs) |
| Active picks accuracy | **FAIL (structure)** | 79% of active_raw = EXPIRED pnl-0 zombies; BTC entry 0.3322, XRP entry 0.0 live rows; visible panel curated to fresh rows |
| Frozen data | **FAIL** | 3,872/28,719 closed rows spot-flicker zero-P/L; OPEN picks current_price=None for days; hyro_pick_performance 157h stale |
| Closed picks profitability | **FAIL** | 14d aggregate negative (crypto −158.8% on n=471); no class n≥100 with PF>1.3 on honest surfaces |
| Statistical soundness | **FAIL** | 69/80 strategies OVERFIT_LIKELY; 3 official surfaces disagree 2–4x per class; ~260 lucky survivors expected by chance |
| Crypto stats real? | **NO** | Registry PF 0.232 (n=23,636, 97.9% single-source) vs money_ready 0.92 — inflated presentation, honest registry |
| Non-crypto stats real? | **MIXED, mostly NO** | ETF WR 2.2% (money_ready) vs PF 1.84 (registry n=15); BOND dead (newest closed 98h); COMMODITY single-source 91% |
| Market regime | **FAIL** | with_regime_data=0; closed_without_regime=8,538 (0.25% coverage); smart_picks regime=NEUTRAL |
| Mutual funds | **VAPORWARE** | No live picks; ranker file doesn't exist |
| /audit freshness claims ("1.9h ago") | **TRUE for visible panel** | .picks.active newest 1.5–3.6h; staleness lives in uncurated layers |

## The five specific user questions, answered

1. **"Are these stats real, crypto and non-crypto?"** — No. Per-class stats vary 2–4x between the
   three official surfaces; crypto long-horizon PF 0.23 with 98% single-source; ETF contradicts
   itself (PF 1.84 vs 0.02); bonds effectively dead.
2. **"Are recent picks actually recent, or are classes dead?"** — Visible panel: genuinely fresh
   (1.5–3.6h all classes). Raw feed: crypto median 89 days old; FUTURES median 98 days; BOND
   newest closed pick 4.1 days — matches user's observations. The "active" surface is curated;
   underneath it classes are zombie graveyards.
3. **"Everything except NEAR/XRP/USDCAD/NZDUSD/BTC flat 0% — stale?"** — Yes, overwhelmingly:
   3,272 of 4,148 raw rows are EXPIRED pnl=0 with no resolved exit; plus 3,872 closed rows were
   zero-delta artifacts. Flat-0 displays are artifacts, not flat trades.
4. **"Is NEARUSDT 3.16% real/plausible?"** — Internally plausible: NEAR SHORT 3.543→3.233 (+8.75%
   TP_HIT) and LONG 3.675→−12.03% (SL_HIT) around a ~−9% NEAR move Nov 10–13. **External quote
   verification (Binance) blocked by session guard — UNVERIFIED.**
5. **"Is Kalshi MTF consensus real?"** — The consensus layer emits picks but demonstrably emits
   garbage (XRPUSDT entry=0.0, 1.5h before fetch) and rides on a 157h-stale performance file;
   independent verification of its prediction-market edge UNVERIFIED from available data.

## What the review agent should do next (proposed master-plan inputs)
1. Re-run the five interrupted subagent deep-dives (crypto / equity-ETF-bond / forex-futures-commodity /
   dashboard staleness / statistical soundness) — task briefs are in the chat transcript.
2. With repo admin/token: pull failing workflow logs (Alpha Live, yfinance refresh, hyro daily output path).
3. With network authorization: external quote cross-check (Binance/Stooq) for NEARUSDT, XRPUSDT,
   BTCUSDT, USDCAD=X, NZDUSD=X.
4. Decide: (a) surface triage — hide/mark every surface listed stale or contradictory; (b) ledger
   consolidation — one canonical dedup'd ledger feeding all surfaces; (c) strategy cull — keep only
   the 6 EDGE_LIKELY_REAL candidates into a forward pilot with n≥100 gate; (d) kill vaporware
   (mutual funds) or build it honestly.

## Files in this folder
- `summary.MD` (this file), `summary_crypto.md`, `summary_equity_etf_bond.md`,
  `summary_forex_futures_commodity.md`, `summary_dashboard_staleness.md`,
  `summary_statistical_soundness.md`, `chat_transcript_2026-11-14.md`
- `evidence_live_audit.json` — machine-readable evidence (per-class ages, zombie counts, garbage rows, 14d stats, regime coverage)
- `live_*.json` — small live payload copies; `actions_api/` — raw GitHub Actions API responses
- NOT included (too large): dashboard_data.json (25MB), dashboard_payload.json (34MB), pf_registry.json (15MB)
  — re-downloadable from findtorontoevents.ca/audit/data/

---

## POST-REVIEW ADDENDUM (2026-11-14, after peer cross-check + live Playwright)

Three corrections to the original audit above (full detail:
`2026-11-14/deepAI_proposed_fixes_20261114_1612/cross_check_and_merge.md`):

1. **Zero-PnL "spot-flicker" diagnosis refined.** Peer `reports/zero_pnl_data_pipeline_audit_2026-06-05.md`
   shows the zeros are `status=EXPIRED` / `resolution_method=TIME_EXPIRED` from the
   `backfill_widened/updated` resolvers (81%/97% zero share) — the resolver writes pnl=0 instead of
   computing close-vs-entry. Per-class zero share: FUTURES 98.4%, BOND 89.1%, COMMODITY 84.9%,
   FOREX 83.7%, ETF 83.1%, EQUITY 79.5%, CRYPTO 56.5%. This explains why non-crypto classes look
   "dead" — they are almost entirely zero-resolved.
2. **Surface disagreement explained, not arbitrary.** The dominant cause is
   `NOMINAL_TP_LEGACY` (TP assumed filled cleanly) vs intrabar-truth replay, where 28–100% of
   supposed TP hits were actually SL hits (peer `PAPER_PILOT_RESOLVER_FAIL_2026-06-05.md`).
   Intrabar-truth (money_ready) is authoritative; registry/nominal numbers are inflated.
3. **I missed a genuine edge: `mega_mutation::crypto`.** Peer T2 inventory: n=295, WR 64.1%,
   PF 3.16, PASS_ALL_AXES (the only T1). My live Nov payload confirms: n=18 in-window WR 72.2%
   PF 3.20; last-30d n=7 WR 57.1% PF 1.58. **This is the one real-edge candidate and should be the
   forward pilot.** Correcting my blanket "no class has edge" statement: no *class* has edge, but
   this one *strategy* does.

Caveats added:
- My registry-derived long-horizon numbers (CRYPTO PF 0.232 n=23,636) may include ~35,494 rows
  contaminated by the 2026-06-04 `closed_at` backfill (peer `REAL_MONEY_MASTER_2026-06-05.md`).
  My 14-day recompute (n=471) is from Nov data and is NOT affected.
- Peer-specified source bans (`prediction_market_agents`, `polymarket_whale_tracker`,
  `short_dominant_engine`, `polymarket_momentum`, `copy_trader_polymarket`, `luxalgo_filters`)
  were never enforced: live `active_raw` still contains `luxalgo_filter` (16) and
  `prediction_market*` (3) rows.

Live Playwright (Chromium 1.58.2) result: **0 hard JS exceptions** on /audit, /audit/hyrotrader,
/audit/funds.html, /audit/pick_funnel.html. Real bugs: `strategy_tribunal_latest.json` 404,
cryptocompare/kucoin CORS failures, and funds.html "Prices: Loading..." never resolving.
Report: `deepAI_proposed_fixes_20261114_1612/playwright_live_js_report.md`.
