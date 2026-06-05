# Multi-Class Real-Money Dig — Master Synthesis (2026-06-05)

**Mission:** Find statistically-validated real-money picks per asset class, without waiting months on forward-test n→100. Six concurrent agent sessions (claude-this + peer claude-minimax + Zoo + Grok-worktree) audited all 8 asset classes against `pf_registry.json` policy-clean + `at_pick_outcomes` resolver-grade + 5-axis scrutiny.

**Honest headline:** **0/8 classes pass charter T2 today.** 4 CRYPTO sleeves are tradeable at micro size with operator approval + 1 EQUITY sleeve surfaces via resolver-grade-only path. Every other class is HOLD until upstream resolver work lands.

---

## 5-axis scrutiny passes per class

| Class | Validated sleeve | n | WR | PF | Verdict | Caveat |
|---|---|---:|---:|---:|---|---|
| **CRYPTO** | JUPUSDT × mega_mutation | 47 | 85.1% | 9.08 | STRONG | Correlated with ENA/ADA (1 edge × 3 symbols) |
| **CRYPTO** | ENAUSDT × mega_mutation | 30 | 80.0% | 8.88 | STRONG | Same edge as JUP |
| **CRYPTO** | ADAUSDT × mega_mutation | 27 | 77.8% | 6.87 | STRONG | Same edge as JUP |
| **CRYPTO** | DYDXUSDT × alpha_engine | 35 | 91.4% | 8.91 | STRONG (independent) | win/loss ratio 0.84 → brittle |
| **CRYPTO** | ml_enhanced_DYDXUSDT_15m_D_ensemble_stack | 35 | 91.4% | 8.87 | PROBABLY-DUP of above | per-source dedup needed |
| **EQUITY** | MeanReversionBB | 214 | 55.6% | 1.88 | RESOLVER-ONLY | Invisible to /audit until pf_registry ingest |
| EQUITY | (all others) | — | — | — | FAIL | regime_terminal n=17 PF=0.19 poisoning policy-clean cohort |
| FOREX | none | — | — | — | FAIL | Single-snapshot resolver; fx_smart_carry n=99 PF=0.23 |
| ETF | none | 39 closed | 0% | — | FAIL | 0/39 closed wins; etf_dual_momentum paper pilot n_closed=0 |
| COMMODITY | none | 593 closed | 0% | — | FAIL | 0/593 closed wins; multi_asset_copytrader 0/426 |
| BOND | cta_replicator BOND slice | 53 | 64% | 4.54 | STALE (14d=0) | Best is dead — emitter retired |
| PENNY_STOCK | none | — | — | — | FAIL | PF<1 on best; WULF/GSAT/RKLB have 0 picks despite Wall Street consensus |
| FUTURES | USDJPY × cta_replicator | 109 | 69.7% | 3.40 | INVESTIGATE | Emitter silently retired 2026-05-21 — recover or kill |

---

## Common upstream blocker

**Single-snapshot resolver (no intrabar OHLC replay)** explains 6/8 class FAILs. PR #500 already disputed the WR inflation; intrabar replay was deployed at 02:01Z 2026-06-04 for CRYPTO (~89% coverage), but **non-CRYPTO classes are still on the old path**. Fix-this-first unlocks most of the inventory.

---

## Sizing — adversarial swarm verdict (Eighth-Kelly, not Quarter)

Peer recommended Quarter-Kelly (0.25×). Adversarial swarm review refuted this and landed:

| Axis | Adversarial verdict | Reasoning |
|---|---|---|
| Sizing fraction | **Eighth-Kelly (0.125×)** | Correlation 37-60% → variance multiplier ~2.0× shrinks effective Quarter → Sixth-Kelly. Resolver bias drops it further. n=25-30 wide PF CI [1.4, 4.5] adds 1/√n shrink |
| Per-trade cap | **1.0% bankroll at risk** (SL × size) | Hard ceiling regardless of Kelly math |
| Per-day cap | **3% bankroll risk/day, max 4 concurrent** | Bounds cluster-loss damage |
| Cohort cap | **8% notional / 4% risk-at-stop** (mega bucket 6%, DYDX 2%) | Treat mega as 1 bucket × 3 symbols, NOT 4 independent |
| Kill-switch | **3 consec losing days OR −5% DD OR any resolver-vs-fill divergence >50bp** | Halt + post-mortem |
| **Minority verdict** | **🛑 NO real-money this week** | Resolver-fill divergence (TP=±2% vs realized 3-11% on mega_mutation) unresolved — paper for 2 more weeks until intrabar OHLC replay confirms fill distribution |

**Codebase note:** `alpha_engine/kelly_position_sizer.py` already defaults to `fraction=0.25` with 50% portfolio cap — so peer's Quarter-Kelly rec just restates current code without tightening for this brittle pilot cohort. The Eighth-Kelly recommendation requires a config flag, not a sizing-policy default change.

**Earliest defensible real-money date** if paper pilot ladder passes: **2026-07-03**.

Full adversarial review: `reports/QUARTER_KELLY_ADVERSARIAL_REVIEW_2026-06-05.md`.

---

## Code shipped this session (commits on main)

| Commit | What | Status |
|---|---|---|
| `7f557f31ac` | T1-badge ⚠️ tooltip + warning icons on /audit/ai-tournament.html | ✅ LIVE |
| `030efe8d3e` | Recency gate wired into money_ready_verdict.py (shadow mode) | ✅ LIVE |
| `23f24c6d8c` | DRY refactor of eagle_gates.py recency helper | ✅ LIVE |
| `f56e42b733` | mysql_stale_picks_resolver: 500% price-unit-mismatch cap (caught 2 fake AUD-USD rows) | ✅ LIVE |
| `151741a218` | MIN_N_CLASS 50→100 + bootstrap CI + WF OOS gates (shadow) | ✅ LIVE |
| `b1b970b066` | _top_sleeves_from_outcomes + _merge_top_sleeves (resolver-grade) | ✅ LIVE |
| `0fdc3ceece` | EST updates entry for real-money edge hunt | ✅ LIVE + FTP-deployed |
| `d7d62be979` | PEAD earnings max_age_days filter + guidance default | ✅ LIVE |
| `d3a6e87802` | Real-money edge hunt master report (PR #550) | ✅ MERGED |

PRs #547, #548, #549 CLOSED as superseded by `be7721dc34` (money-ready blitz). #551 OPEN — pending CI.

---

## Action items (prioritized, autonomous-execute scope)

### P0 (this week — unlocks 6/8 verdicts)
1. **Intrabar OHLC resolver for non-CRYPTO classes** — currently CRYPTO ~89% / others 0%
2. **Repopulate `alpha_engine/data/pead_earnings_cache.json`** — `next_earnings_date=None` for every major symbol
3. **Quarantine `multi_asset_copytrader`** (0/426 ETF + 0/120 COMMODITY wins) into `BANNED_SOURCES`
4. **Investigate `USDJPY × cta_replicator` silent retirement** — recover or kill the only FUTURES lead

### P1 (this month)
5. **Wire `bond_duration_momentum` to production scanner** (Wire-Up Rule — shipped at `49443c0375` but 0 picks emitted)
6. **Paper-pilot 4 CRYPTO sleeves with Quarter-Kelly** (pending adversarial review) — treat mega_mutation as 1 edge × 3 symbols + DYDX as 1 independent
7. **Add WULF/GSAT/RKLB to penny universe** — Wall Street consensus edge unused
8. **External FOREX integration** (DBMF/KMLM replication + FRED rate-differential carry sidecar)

### P2
9. **Block `regime_terminal` for EQUITY** (batch-emission pattern, n=17 PF=0.19 poisoning pf_registry)
10. **ETF paper-pilot once `etf_verified_dual_momentum` accumulates closes** (currently 0)
11. **Re-check `commodity_term_cot` emitter** after 7 days (just shipped this session)

---

## Reports written across all parallel sessions (8 + master)

- `reports/PER_ASSET_CLASS_REAL_MONEY_PICKS_2026-06-05.md` — peer's original 4 CRYPTO STRONG validation
- `reports/EQUITY_real_money_picks_2026-06-05.md` — claude-this swarm
- `reports/FOREX_real_money_picks_2026-06-05.md` — claude-this swarm
- `reports/ETF_COMMODITY_real_money_picks_2026-06-05.md` — claude-this swarm
- `reports/BOND_PENNY_real_money_picks_2026-06-05.md` — claude-this swarm
- `reports/FUTURES_CROSS_CLASS_real_money_picks_2026-06-05.md` — claude-this swarm
- `reports/edge_hunt_ALL_CLASSES_v2_2026-06-06.md` — peer master synthesis (untracked)
- `reports/edge_hunt_REAL_MONEY_2026-06-05.md` — peer-minimax synthesis (PR #550)
- `reports/QUARTER_KELLY_ADVERSARIAL_REVIEW_2026-06-05.md` — pending swarm agent
- `reports/MULTI_CLASS_REAL_MONEY_DIG_2026-06-05.md` — this file

---

## Open questions for operator

1. Approve Quarter-Kelly sizing for the 4 CRYPTO sleeves once adversarial review lands? (Default no until reviewed.)
2. Unblock `mega_mutation` from `strategy_blocklist.py:211,216` (sign-coherence 0 flips per evidence doc) — or keep blocked pending paper pilot accumulates 30+ closes?
3. Merge PR #551 once CI green?
4. Block `regime_terminal` for EQUITY in `quality_gates.py::BLOCKED_ASSET_STRATEGY_PAIRS`?
