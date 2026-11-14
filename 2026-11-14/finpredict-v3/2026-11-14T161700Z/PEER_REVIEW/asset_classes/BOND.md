# Peer Review — BOND

**Reviewer:** finpredict-v3 (2026-11-14T16:17Z)

---

## 1. Peer docs read (inventory)

| Peer | File | Verdict |
|---|---|---|
| v4 | `audits/2026-11-14/finpredict-v4_2026-11-14-1555/noncrypto_deep_dive.md` | BOND EMITTING / POOR |
| v2 | `.kilo/worktrees/finpredict-v2/2026-11-14/finpredict-v2_20261114-1602/sub/D_non_crypto.md` | **FAIL** — triple-emission, 60% never priced |
| v1 | `.kilo/worktrees/finpredict/2026-11-14/finpredict/2026-11-14T160004Z/updates/2026-11-14-prediction-system-audit.md` | BOND effectively dead (both ends) |
| ML | `updates/2026-11-14-ML-AUDIT-childlike-airport/proposed_fixes/bonds/FIX_PROPOSED.md` | fresh feed vs stale DB sync gap |
| self(v3) | `2026-11-14T155500Z/updates/2026-11-14-prediction-data-hygiene.md` | bond picks unmarked / dead class |

**v4 `proposed_fixes/bond/` = EMPTY** (0 files).

---

## 2. Peer verdicts (quoted + key numbers)

- **v4 noncrypto:** "BOND … EMITTING but POOR." 1,293 open picks; avg PnL **−1.66%**, 72% underwater; intrabar n=26 WR 7.7% PF 0.39 → INSUFFICIENT_N; `db_n=0` for all top picks (WIP/TIP/SCHP) — no track record; `tp_sl_quality_score=0.0` for many.
- **v2 D_non_crypto:** **FAIL** — 15 `active_raw` rows, only 5 unique instruments (SHY/TLT/HYG/JNK/EMB) from **3 emitters** (`alpha_engine`, `bond_scanner`, `orphan_emitter_bond`); **9/15 (60%) `current_price=None`/pnl=0**; TLT SHORT emitted ×3 with different entries; newest CLOSED = 2026-11-10 → **4.09d** old; one-session entry lag (entries = 11-12 close); cohort conflict n=1 policy-clean vs n=503 tournament (500× discrepancy). Readiness `BLOCKED`, sizing_allowed=false.
- **v1 audit:** BOND **15 OPEN** in `active_raw`, 60% frozen (current==entry or null); newest ~25.3h; newest closed ~98h (4.1d); "effectively dead."
- **ML FIX_PROPOSED:** fresh `active_picks_bond.json` (7 picks, 2d, SHY×3/LQD/MUB/TLT) **never lands in `live_picks.db`** (only 2 active rows, ~172d stale). Closed bond picks = **3 total** (no exit events emitted). Root sync bug: feed exists, DB not synced.
- **self(v3):** open bond seeds signal Nov 13 but most `current_price=null`; only settled bond trade closed Nov 10 ("4 days ago"); class `n=1` closed / insufficient_data.

---

## 3. Quick-win fixes proposed by peers

| Fix | Source(s) | Multi-peer? |
|---|---|---|
| Sync `active_picks_bond.json` (7 picks) into `live_picks.db`; upsert by (symbol,strategy) | ML (Fix 3.1); self (unmarked seeds) | **YES** |
| Refresh `current_price`/recompute PnL for stale bond rows (feature fetch_stock_prices/price enricher) | ML (Fix 3.2); v2 (never priced); self (NULL price) | **YES** |
| Emit exit events (TP/SL/time) for bond picks so closed sample grows past 3 | ML (Fix 3.3); v4 (n=26 thin); v2 (0 exit events) | **YES** |
| Populate `symbol_strategy_stats` for bond strategies (attribution) | ML (Fix 3.4) | single |
| Dedupl/e/stop triple-emission (3 emitters per instrument; TLT×3) | v2 (§5) | single |
| Keep class `INSUFFICIENT_DATA`; do not size until a real closed sample exists | v4; v1; self | **YES** |

---

## 4. Disagreements / contradictions

- **Bond counts:** v4 = 1,293 open (picks_now_live_pnl); v1 = 15 OPEN (active_raw); v2 = 15 active_raw; ML = 2 active (live_picks.db) vs 7 in the fresh feed. The DB (2) and the dashboard feed (15/1,293) disagree — this is exactly the sync gap ML identified.
- **Recency:** v1 says newest OPEN ~25h; v2/v4 say newest CLOSED 4.09d. Different metrics (open vs closed) — not a true conflict, but the master plan must say which it means.
- **Class taxonomy:** v2 flags `VCSH` (short-term corporate bond ETF) sitting in ETF while HYG/JNK/EMB are BOND — same economic exposure split across classes.
- **Yield reconciliation:** v2 notes FRED reachable (DGS10 = 5.10 on 11-12) but picks carry no yield field → **yield-level reconciliation UNVERIFIED**. No peer fixed this.

---

## 5. Gaps (not fixed/verified by any peer)

- Yield-level reconciliation (FRED vs pick entries) UNVERIFIED — no peer implemented it.
- No peer actually executed the sync/refresh/exit fixes; ML's are proposed SQL/plans, not applied.
- The "4 days ago" claim is confirmed (v2/v4) but the UI banner still shows it unresolved — no fix shipped.

---

## 6. Recommended best-of for the master plan (BOND)

1. **Adopt the ML FIX_PROPOSED as the master-plan backbone** — its four fixes (sync feed→DB, refresh current_price/PnL, emit exit events, populate symbol_strategy_stats) are concrete, with SQL and verification steps, and directly address the 2-vs-7-vs-15-vs-1,293 layer mismatch.
2. **Adopt v2's dedup/taxonomy notes** in the same pass: stop triple-emission and decide VCSH/BOND boundary.
3. **Adopt v4/v1's gate:** keep BOND `INSUFFICIENT_DATA`/`BLOCKED`; do not size any bond pick until a real closed sample (n≥100) exists — no peer found any money-ready bond edge.
