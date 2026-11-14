# Peer Review — CRYPTO

**Reviewer:** finpredict-v3 (2026-11-14T16:17Z)
**Scope:** consolidate per-asset-class peer reviews for the master plan.

---

## 1. Peer docs read (inventory)

| Peer | File | Verdict |
|---|---|---|
| v4 | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/crypto_deep_dive.md` | live-vs-stale split; 3 active crypto picks |
| v4 | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/market_crossref_report.md` | AI Challenge crypto registry out of sync |
| v2 | `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/sub/C_crypto.md` | **FAIL** data integrity |
| v1 | `.kilo/worktrees/finpredict/2026-11-14/finpredict/2026-11-14T160004Z/updates/2026-11-14-prediction-system-audit.md` | **FAIL** — crypto net loser |
| ML | `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/crypto/FIX_PROPOSED.md` | 101 stale live_picks.db crypto rows |
| self(v3) | `2026-11-14T155500Z/updates/2026-11-14-prediction-data-hygiene.md` | crypto prices pinned to entry (STALE) |

**v4 `proposed_fixes/crypto/` = EMPTY** (0 files, confirmed by `ls -A`).

---

## 2. Peer verdicts (quoted + key numbers)

- **v4 crypto_deep_dive:** "2 picks genuinely live, 1 current_price stale … all 3 dashboard `current_price` stale vs live Binance." Key: NEAR SHORT 3.324→3.209 = **+3.46%** live vs dashboard 2.74% (+0.72pp); XRP +1.46pp; BTC +0.97pp hidden by frozen 0.00%. All 3 `forward_validated=false`, `forward_trades=0`, trust ≤4 WATCH, `_backfilled=true`. RSI5070: net PF 1.113, CI-LB 0.916 → **gate FAIL, below promotion bar**.
- **v4 market_crossref_report:** AI-challenge crypto (5 stocks) "all >8 months old (2026-03-15) still OPEN … pnl stuck 0.0". NEARUSDT **+143%** away from entry (SL 1.37 blown); TRX past TP should be WIN; BTC/SOL past TP should be WIN.
- **v2 C_crypto:** **FAIL** — "crypto book dominated by never-resolved zombie re-emissions." 3,322/3,577 (92.9%) `pnl=0`; 3,170 (88.6%) null `current_price`; **inverse_mutations/inverse_luxalgo_confluence = 2,267 rows** daily since 2026-05-23 (20 symbols, EXPIRED 2,231). NEAR 3.16% **plausible & real** (3.324→3.219 = 3.1588%).
- **v1 audit:** CRYPTO PF **0.93** (net −458 over 4,907 closed); **z = −7.1** (worse than random); "verified strategies" batch 96.9% frozen; kalshi on-disk snapshot ~7mo stale; garbage rows exist (`XRP entry=0.0`, `BTC 0.3322`). June gate: 31/38 (82%) OVERFIT_LIKELY.
- **ML FIX_PROPOSED:** 101 active crypto rows in `live_picks.db` stale **~172 days** (last activity 2026-05-25); **8 sign contradictions** (NEARUSDT entry 2.42/current 2.733 → `unrealized=-0.129` wrong sign vs correct +0.129) + **15 calc mismatches**; case-dupe `CRYPTO`/`crypto` (1,348 rows).
- **self(v3):** XRP/BTC `current==entry` exactly while Binance moved +1.3%/+0.9%; banner "1.9h ago" is signal age, not price freshness.

---

## 3. Quick-win fixes proposed by peers

| Fix | Source(s) | Multi-peer? |
|---|---|---|
| Recompute `unrealized_pnl_pct`/`pnl_pct` from `(current-entry)/entry` for all active crypto rows | ML (SQL §3.1); v4 (understated PnL); v2; self | **YES — strong** |
| Refresh `current_price`/`last_checked` vs live Binance at build time; never publish `current==entry` as a quote | v4; v2 (rec 5); self (UNQUOTED label); ML (§3.2) | **YES — strong** |
| Quarantine/stop `inverse_mutations`/`inverse_luxalgo_confluence` zombie emission; archive 2,267 rows | v2 (rec 1); v1 (auto_expired zombies) | YES |
| Emit exit/close events for stale picks (>N days, no price) or mark EXPIRED; purge OPEN ghosts | ML (§3.3); v4 market (purge >7d OPEN); v1 | **YES** |
| Reject `entry_price<=0` / out-of-band entries; mark INVALID, never EXPIRED/pnl=0 | v2 (rec 2); v1 (garbage rows present) | YES |
| Enforce `SL<entry<TP` direction + status/PnL sign consistency (LOST with pnl>0 block) | v2 (rec 3,4) | single |
| Dedupe (id + symbol/dir/entry/ts; case-dupe class) | v2 (rec 4); ML (§3.4) | **YES** |

---

## 4. Disagreements / contradictions

- **Active crypto count:** v4 = 3 (curated dashboard panel); v1 = 402 OPEN in `active_raw` / 3 clean; ML = **101 active** in `live_picks.db` (~172d stale). These are different layers/DBs — the live-picks DB disagrees with the dashboard panel.
- **NEAR PnL mark:** v4 2.74% (dash) vs 3.46% (live @15:52); v2 3.16% (@15:00) vs 3.82%; v1 3.07%. Same pick, different quote times — not a logic conflict, but the master plan should pick one mark convention.
- **Staleness horizon:** v1 raw median 2,128h (89d), oldest 6,421h; v2 median ~1,500–2,400h; ML all-101 = ~172d. Consistent theme (raw feed old) but different references.
- **"Flat 0%" interpretation — all agree it is an artifact, not true flat** (v2 §5, self): no disagreement.
- ML says the 101 rows' last activity is 2026-05-25, while dashboard-based audits show fresh signals today (13:53Z). Reconcilable (DB vs JSON feed) but should be flagged as a data-layer mismatch.

---

## 5. Gaps (not fixed/verified by any peer)

- Root cause of `0.0/0.26/1.334` BTC entries in `inverse_luxalgo_confluence` **untraced** to source (v2 UNVERIFIED).
- Exact intraday exit prints used by the dashboard resolver UNVERIFIED (v2 UNVERIFIED).
- No peer fixed the `dashboard_data.json` 26-day staleness itself (only diagnosed).
- Real-money vs paper distinction for active picks unresolved (v1 UNVERIFIED).
- No peer hardened the `kalshi_mtf_consensus` 7-month-stale on-disk snapshot beyond flagging.

---

## 6. Recommended best-of for the master plan (CRYPTO)

1. **Adopt ML's concrete fixes** (§3.1–3.4) as the DB-level backbone: recompute unrealized PnL, fix 8 sign + 15 calc mismatches, refresh prices, emit exits for stale, dedupe case/class — all with the provided verification SQL.
2. **Adopt v2's quarantine** of `inverse_mutations`/`inverse_luxalgo_confluence` (2,267-row zombie factory) + entry-sanity rejection + `SL<entry<TP` enforcement — the highest-volume data-integrity win.
3. **Adopt v4/self's UI fix:** re-quote crypto `current_price` from Binance at build time; never display `current==entry` as live (label UNQUOTED); fix the age banner to price-time, not signal-time.
4. **Gate on v1/v4 reality:** crypto has **no statistically distinguishable edge** (z=−7.1; RSI5070 CI-LB 0.916 FAIL) — do not size; treat any "verified alpha" as unproven until forward-validated.
5. **Reconcile the layer mismatch** (dashboard 3 vs live_picks.db 101) as a dedicated task before any global count is trusted.
