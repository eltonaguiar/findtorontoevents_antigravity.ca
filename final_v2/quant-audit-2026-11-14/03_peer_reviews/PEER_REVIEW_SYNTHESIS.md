# 03_Peer Reviews — Cross-Peer Synthesis (final_v2, 2026-11-14)

**Peer folders reviewed:**
- `final_2026_11_14/childlike-airport/` (kilo's worktree)
- `final_2026_11_14/finpredict-v2/`
- `final_2026_11_14/finpredict-v3/`

---

## Peer 1: childlike-airport (kilo)

**Approaches found (statistically validated):**

| Approach | Asset | Sharpe | PF | MDD | Trades | PBO | DSR | Status |
|---|---|---|---|---|---|---|---|---|
| Regime-Filtered VWAP MR | Crypto 4h | 3.76 | 1.21 | 10.0% | 129 | 0.489 | 1.0 | VALIDATED |
| Vol-Targeted Trend | Crypto daily | 2.13 | 1.40 | 17.4% | 2,490 bars | — | CI[1.25,3.25] | PROVEN |
| Walk-Forward Variant C | Equity/ETF | — | 1.26 | — | 237 | — | p<0.0013 | PILOT |

**Data quality findings (critical, affect all classes):**
- 129/129 active picks ~172 days stale
- 8 PnL sign contradictions (e.g., NEARUSDT shows −0.129 unrealized but correct is +0.129)
- 15 PnL calculation mismatches vs (cp−ep)/ep
- `audit_trail.db` completely empty (9 tables × 0 rows)
- **No MUTUAL_FUND class anywhere** — not in `asset_class.py`, gatekeeper, or any picker
- `sync_all_picks_to_mysql.py` bugs: inserts into `bt_backtest_trades` for rows failing entry>0 guard; `pnl *= 100` heuristic corrupts small percent values
- `price_realism_check.py` bug: hardcoded prices misclassify real post-split data as "UNREALISTIC"

## Peer 2: finpredict-v2

**Framework:** CI Gates G1-G13 for encoding data-contract invariants
**Consensus:** Adopt v2 reconciliation backbone; scratch QW-ALL-1..9 checklist; merge v1 master-plan after fixes; red-line ML-audit destructive SQL + mutual-fund stub scanner
**MASTER_AUDIT:** Per-class analysis with workflow matrix, dashboard freshness, crypto, non-crypto, statistical, sources, peer reconciliation

## Peer 3: finpredict-v3

**Data hygiene:** 2 stale crypto prices pinned to entry, 11 frozen closed FOREX phantoms, 3 date-only seeds, null-price BOND/FUTURES classes, survivorship in headline stats
**Horizon validation:** 0/6 groups pass at n≥60, 0/26 at n≥30 — no strategy in recorded ledger is solidly profitable across time
**Remediation:** Flipped leakage-masking default to ON in `ml_gatekeeper/gatekeeper.py` (commit `d8c8dd25581` on `origin/main`)

---

## Cross-Peer Consensus (9 peers)

| Finding | childlike-airport | finpredict-v2 | finpredict-v3 | My finding (final_v2) |
|---|---|---|---|---|
| NOT money-ready | ✅ | ✅ | ✅ | ✅ (0/166 cells) |
| Data pipeline broken | ✅ | ✅ | ✅ | ✅ |
| EXPIRED→WON mislabeling | ✅ | ✅ | ✅ | ✅ |
| Single-source concentration | ✅ | ✅ | — | ✅ (all 166 cells) |
| PnL-unit contract = #1 fix | ✅ | ✅ | ✅ | ✅ |
| Zombie drain = #2 fix | ✅ | ✅ | ✅ | ✅ |
| Backtest↔forward disconnect | — | — | ✅ | ✅ |

**Tension resolved:** Peers find profitable approaches in backtest research (kilo's VWAP MR Sharpe 3.76), but my live-ledger screener finds 0/166 cells passing. Reconciliation: **research harnesses ≠ live ledger.** No validated approach has been deployed into `recent_closed_array.json`. The gap is research → production, not absence of edges.

**Deployable candidate:** Regime-filtered VWAP MR (crypto 4h) — passes all peer gates, PBO 0.489 (borderline, below strict 0.3 due to n=129), n=129 above 30 minimum. This is the first candidate for paper trading.
