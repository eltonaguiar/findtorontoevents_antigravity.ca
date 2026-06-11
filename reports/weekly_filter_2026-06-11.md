# Weekly Real-Money Filter — 2026-06-11 (UTC)

**Verdict up front: 0/9 asset classes are money-ready. Live sizing for ALL classes = 0%.**
This is the honest output of the v2 audit run on the now-live intrabar-truth chain — not a placeholder.
Every number below is `(asset_class | n | timeframe)`-labeled and from the canonical sources
(`money_ready_verdict.json` live 2026-06-11T01:55Z, age 1.5h FRESH; `pf_registry.json::*policy_clean_net`;
`entry_conditions_forward.json`; `at_signal_outcomes.intrabar_*`).

## The two-layer truth (why no class qualifies)

| Class | Policy-clean (Layer A) | Intrabar-honest (Layer C) | Verdict |
|---|---|---|---|
| CRYPTO | n=1598 51.7%/PF0.63 NOT_READY | **n=1154 32.4%/PF0.73** | FAIL |
| EQUITY | n=406 47.3%/PF0.73 NOT_READY | **n=107 34.6%/PF0.47** | FAIL |
| FOREX | n=113 57.5%/PF1.77 "WATCH" | **n=88 42.0%/PF1.13** | NOT TRUSTED — Layer A optimism is the close-walk artifact class; intrabar layer is canonical |
| COMMODITY | n=31 58.1%/PF2.04 | **n=90 41.1%/PF1.39** | INSUFF-N (verdict due at n≥100) |
| ETF | n=52 69.2%/PF2.01 | **n=16 0%/PF0** | Layer A number REJECTED (0/16 intrabar TP) |
| BOND | n=67 65.7%/PF0.99 | n=6 | INSUFF-N |
| FUTURES | n=17 | n=7 | INSUFF-N |
| MEME | n=10 10% | n=77 26.0%/PF0.58 | DO-NOT-TRADE (nothing conditions it — entry-conditioning experiment 2026-06-10) |
| PENNY | n=1 | — | INSUFF-N |

**Strategy-cell screen (canonical pf_registry, policy-clean-net): 0 cells pass n≥30 + PF≥1.5 + WR≥50 + not-single-source. 0 cells even reach PF≥1.3 at n≥30.** There is no hidden qualifying filter; the 1,278-slice Bonferroni edge audit (2026-06-10) independently reached the same null, and every "narrowed" slice failed the time-split.

## Forward-test candidates (paper lane ONLY — live size 0%)

The only statistically disciplined candidates in the system, tracked continuously in
`audit_dashboard/data/entry_conditions_forward.json` (R1 time-split / R2 concentration<35% / R3 p<0.005 at discovery):

### CRYPTO | entry filter: RSI(14,1h) 50–70 at entry AND US-session (13:30–21:00 UTC)
- (CRYPTO | n=108 | since 2026-05-27): WR 47.2%, PF 1.535 — vs class baseline 32.1%/PF 0.72
- Rolling 30d: n=59, 49.2%/PF 1.50 — **holds out-of-snapshot but sits BELOW the 50% WR promote bar**
- Kelly (for the paper book only): b=1.72, full Kelly 16.5%, **quarter-Kelly 4.1% — applies to PAPER sizing only**
- Promote/kill rule (pre-registered): at n≥150 across ≥3 regime-weeks, promote to probation ONLY if WR≥50 & PF≥1.5 & R1/R2/R3 re-pass; else drop.

### CRYPTO | strategy-direction cell: luxalgo_confluence SHORT
- (CRYPTO | n=38 | last 30d only): WR 71.1%, PF 2.21 — direct-SQL verified
- **Caveat that blocks promotion: 100% of the sample is inside one 30-day window** (single-regime). Needs a time-split across ≥2 regimes.
- Quarter-Kelly would be 9.7% — NOT applicable until the recency caveat clears. Paper lane only.

### Negative entry filters (cheap risk reduction, also measurement-only today)
- FOREX: trend-CONTRARIAN entries carry ~74-76% of class losses (forward lane: contrarian cohort n=24, 29.2%/PF 0.53 vs aligned n=14, 64.3%/PF 4.74 — small n, direction consistent).
- EQUITY: the high-vol negative filter FLIPPED under fuller bar history (n=30, 53.3%/PF 0.81) — fragile, kept under measurement, not actionable.

## How to apply (this week)
1. **Do not size live capital on any class.** The audit bar (n≥100 clean + ≥3 months + PF>1.5 + WR>52% EXPIRED-inclusive + intrabar-validated + multi-source) has 0 survivors.
2. Watch `findtorontoevents.ca/audit/` Money Ready tab — it now renders the intrabar-honest verdict directly.
3. Paper book may track the two CRYPTO candidates at quarter-Kelly (4.1% / 9.7%) to build forward n; outcomes accrue automatically to `entry_conditions_forward.json` via `tools/stamp_entry_conditions.py` (cron-able, read-only).
4. COMMODITY (n=90) and FOREX (n=88) get their FIRST honest class verdicts at n=100 — expected within days as the hourly resolver accrues; do not pre-position.

## Risk controls (unchanged)
- Max per-pick when anything ever qualifies: quarter-Kelly, capped 5% of account.
- Daily soft-stop −2% PnL; rolling-30d MDD >30% halts all sizing (Hyro overlay).
- Tournament/leaderboard surfaces are discovery-only, never sizing (MISPRICED_ENTRY artifacts; 4154/7099 rows).

## Current OPEN cohort (context)
(all | n=89 OPEN | 2026-06-11): CRYPTO 61, COMMODITY 9, FOREX 9, EQUITY 5, BOND 3, STOCKS 1, FUTURES 1.
The RSI50-70×US filter is measured at resolution time by the stamper (entry features computed from pre-entry bars), so OPEN-pick matching is automatic — no manual filter application is required or trusted.

## Provenance
- Freshness gate: PASS (verdict age 1.5h).
- Sources: live `money_ready_verdict.json` (2026-06-11T01:55Z) · `pf_registry.json` @ origin/main · `entry_conditions_forward.json` @ origin/main · `reports/entry_conditioning_experiment_2026-06-10.json` · `reports/sigma_geometry_experiment_2026-06-10.json` (geometry NULL → entry-selection pivot) · session log `reports/MASTER_PROGRESS_2026-06-10.md`.
- Known limitations: clean cohort still time-concentrated (most resolutions 2026-05-27→06-10); COMMODITY intrabar baseline is the small recent cohort, horizon-censored; do not extrapolate.
