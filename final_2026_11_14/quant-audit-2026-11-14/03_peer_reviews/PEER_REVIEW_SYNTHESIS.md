# 03_Peer Reviews — Cross-Peer Synthesis (2026-11-14)

**Worktree:** quant-audit-2026-11-14  
**Reviewed peer folders in `final_2026_11_14/`:**
- `childlike-airport/` (Kilo's worktree, branch `audit-stale-data-and-accuracy-across-asset-classes`)
- `finpredict-v2/` (worktree, branch `finpredict-v2`)
- `finpredict-v3/` (worktree, branch `archive/2026-11-14-finpredict-v3`)

---

## Peer 1: childlike-airport (kilo)

**Scope:** Stale data accuracy across asset classes + ML audit + profitable approach discovery.

**Key findings:**
- **129/129 active picks ~172 days stale** (last_updated 2026-05-25, today 2026-11-14)
- **8 PnL sign contradictions** (e.g., NEARUSDT entry 2.42 → current 2.733, unrealized shows −0.129 but correct is +0.129)
- **15 PnL calculation mismatches** vs (cp−ep)/ep
- **`audit_trail.db` completely empty** (9 tables × 0 rows)
- **No MUTUAL_FUND class anywhere** (not in asset_class.py, gatekeeper ASSET_CLASS_MAP, or any picker)
- **`sync_all_picks_to_mysql.py` bugs:** inserts into bt_backtest_trades for rows failing entry>0 guard; `pnl *= 100` heuristic corrupts small percent values
- **`price_realism_check.py` bug:** hardcoded expected_2026_prices misclassifies real post-split/appreciation data as "UNREALISTIC/SYNTHETIC"

**Profitable approaches found (statistically validated):**

| Approach | Asset Class | Sharpe | PF | PBO | DSR | MDD | Trades | Status |
|---|---|---|---|---|---|---|---|---|
| Regime-Filtered VWAP MR | Crypto 4h | 3.76 | 1.21 | 0.489 | 1.0000 | 10.0% | 129 | VALIDATED |
| Vol-Targeted Trend | Crypto daily (7.4yr) | 2.13 | 1.40 | — | CI[1.25,3.25] | 17.4% | 2,490 bars | PROVEN |
| Walk-Forward Variant C | Equity/ETF | — | 1.26 | — | p<0.0013 | — | 237 | PILOT |

**System overall:** NOT profitable (PF 0.80, 79% zombie picks). Data quality: 81% fake 0% P/L, losses understated 10x, 78.6% EXPIRED zombies, 7 workflows failing.

---

## Peer 2: finpredict-v2

**Scope:** Reconciliation backbone + CI gates framework + MASTER_AUDIT per-class analysis.

**Key findings:**
- **CI Gates G1-G13** framework for encoding data-contract invariants (G1 summary population, G2 quote honesty, G3 metric liveness, G4 dedup/identity, G5 sidecar freshness, G6 strict JSON, G7 workflow hygiene, G8 scheduler guard, G9 DB freshness, G10 open-pick backlog, G11 source authenticity, G12 push contention, G13 secret scan)
- **MASTER_AUDIT.md** with per-class analysis (A_workflow_matrix, B_dashboard_freshness, C_crypto, D_non_crypto, E_statistical, F_sources, G_peer_reconciliation)
- **Recommendations:** DATA_CONTRACT.md, ROADMAP.md, CI_GATES.md, QUICK_WINS.md, per-asset-class remediation (equity_etf, crypto_commodity, forex_futures, bond_mutual_funds)
- **Patch plan:** P0_QUICK_WINS.md, P1_STRUCTURAL.md, acceptance_tests.md
- **Peer reviews:** PF1-PF5 folder reviews, REVIEW_SYNTHESIS.md, FOLDER_REVIEW_SYNTHESIS.md

**Consensus:** Backbone = adopt v2 (reconciliation); Checklist = scratch QW-ALL-1..9; Merge after fixes = v1 master-plan; Red-line = ML-audit destructive SQL + mutual-fund stub scanner.

---

## Peer 3: finpredict-v3

**Scope:** Data-hygiene audit + ML validation + horizon validation harness + guardian tools.

**Key findings:**
- **Data-hygiene defects** in `dashboard_data.json` (generated 2026-11-14T14:30Z): 2 stale crypto prices pinned to entry, 11 frozen closed FOREX phantoms, 3 date-only seeds, null-price BOND/FUTURES classes, survivorship in headline stats, dead metric sections
- **Runnable guardian** (`tools/pi_data_hygiene.py`, exit code 1 on findings, CI-gateable) + 14 tests passing
- **ML validation:** target leakage in production gatekeeper, look-ahead in Gainer ML, random-shuffle time-series splits, stale models, placeholder ML
- **Horizon validation harness:** 0/6 groups pass at n≥60, 0/26 at n≥30 — **no strategy in the recorded ledger is solidly profitable across time**
- **Remediation:** flipped leakage-masking default to ON in `ml_gatekeeper/gatekeeper.py` (commit `d8c8dd25581` on `origin/main`, flagged for sign-off)
- **Consensus verdict (9 peers):** NOT money-ready; data pipeline broken; highest-value first changes = PnL-unit contract + NULL-tombstone zombie drain; backtest↔forward disconnect (0 rows have both bt_trades>0 and fwd_trades>0)

---

## Cross-Peer Consensus (all peers agree)

| Finding | childlike-airport | finpredict-v2 | finpredict-v3 | My finding (quant-audit) |
|---|---|---|---|---|
| NOT money-ready | ✅ | ✅ | ✅ | ✅ (0/166 cells) |
| Data pipeline broken | ✅ | ✅ | ✅ | ✅ |
| EXPIRED→WON mislabeling | ✅ | ✅ | ✅ | ✅ (53 frozen at pnl=0) |
| Single-source concentration | ✅ | ✅ | — | ✅ (all 166 cells) |
| PnL-unit contract is #1 fix | ✅ | ✅ | ✅ | ✅ |
| Zombie drain is #2 fix | ✅ | ✅ | ✅ | ✅ |
| Backtest↔forward disconnect | — | — | ✅ (0 rows both>0) | ✅ (n≥100 only 1 cell) |
| No mutual funds | ✅ | — | — | ✅ |

**Profitable approaches EXIST but are NOT deployed** — the only point of mild tension: kilo found validated approaches in backtest research (VWAP MR Sharpe 3.76), while my live-ledger screener found 0/166 cells passing. Reconciliation: research harnesses ≠ live ledger. No validated approach has been deployed into `recent_closed_array.json`.
