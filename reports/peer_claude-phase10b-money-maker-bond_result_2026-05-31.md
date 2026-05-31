# /money-maker-readyv2 — BOND

**Author:** peer_claude (Opus 4.7), Phase 10b
**Timestamp:** 2026-05-31 ~06:30Z
**DB:** `ejaguiar1_stocks.trading_picks` (live)

## Class verdict at 06:30Z 2026-05-31

```
PF = 1.085   (gross_win 5.1131 / gross_loss 4.7119, real closures only)
WR = 27.3%   (3 wins / 11 real closures; resolver-zero excluded)
n_real = 11  (out of 164 total picks)
Sharpe~ undefined (sd 0.47, mean +0.31bp → ~0.007 — noise)
T2-status: FAIL on (PF<1.5, WR<50, n<<100)  →  INSUFFICIENT_N + CONTAMINATED
```

**Raw breakdown (live DB):**

| status | n | null_pnl | avg_pnl_pct | notes |
|---|---|---|---|---|
| OPEN | 33 | 25 | +0.0012% | live, unsettled |
| ACTIVE | 1 | 0 | -0.006% | live |
| TIME_EXIT | **117** | 0 | **0.0000%** | **100% forged exit==entry** |
| LOST | 10 | 2 | -0.589% | real |
| TP_HIT | 3 | 0 | +1.704% | real (1 capped at +5.00) |

**71% of the BOND dataset is resolver-corrupted (117 forged TIME_EXIT rows with `exit_price = entry_price` literally).**

## Best candidate

`multi_asset_copytrader` on `ZN=F` (10Y T-Note futures, SHORT):
- n_real = 4 (3 TP_HIT, 1 LOST)
- WR = 75% (3/4)
- gross_win = 5.1131 / gross_loss = 0.0141 → **PF = 363** (but 1 win is capped +5.0000 — the same +5%-cap artefact Phase 4 flagged)
- Stripping the cap-artefact: 2 wins at +0.056% + 1 loss at -0.014% → PF ≈ 8, n=3 → INSUFF
- MC Phase 3 watchlist: **no BOND candidate** present. BOND wasn't profiled at n=100 because no strategy had enough closures.

## T2 gap

- Current "real closed n" = 11. Need 89 more clean closures to reach n=100.
- Emission cadence (last 30d, May 4-31): **84 picks emitted but only 32 reached `closed` status** (rest are forged-TIME_EXIT or still OPEN).
- True closure rate (post-resolver-fix estimate): ~1.0-1.5 real closures/day.
- **Time-to-T2 at current cadence: ~9-12 weeks** — but ONLY if the TIME_EXIT resolver bug is fixed and forged rows are repaired.
- Without fix: time-to-T2 = ∞ (resolver permanently writes pnl=0 → no edge can ever surface).

**Bottlenecks (ranked):**
1. **Forged exit_price on TIME_EXIT** (P0, blocks 71% of data).
2. **Phase 4 TP capping at +5.00%** (1 of 3 wins is `pnl_pct = 5.0000` capped — distorts BOND PF since avg bond move ≪ 5%).
3. Concentration: 60% of TIME_EXIT rows are on ZN=F alone (single instrument).
4. `bond_scanner` has 0 wins / 8 losses (-3.87 gross_loss) → strategy is mis-calibrated to bond duration/vol.

## Actions ranked by impact

### 1. P0 — Fix TIME_EXIT exit_price forgery (blocks 117/164 rows)

**Files / lines:**
- `alpha_engine/outcome_resolver.py:1500-1520` (the `time_exit_outcome` branch in the resolver loop) — currently writes `exit_reason="TIME_EXIT"` but downstream sync code (likely `mysql_trading_sync.py:182` and `active_picks_sync.py:215-221`) copies `entry_price` into `exit_price` when no fresh quote is supplied for the asset class.
- `alpha_engine/active_picks_sync.py:212-221` — the `time_exit` else-branch does NOT verify that `live_price != entry_price` before persisting. For BOND symbols (`ZN=F`, `TLT`, `IEF`, `HYG`, `EMB`, `JNK`, `BNDX`, `TIP`, `MUB`, `AGG`, `LQD`), the live-price fetch path must NOT fall through to the entry value on fetch failure.
- `alpha_engine/active_picks_sync.py:243+` (`fetch_live_prices` for non-CRYPTO) — needs an explicit BOND fetcher (FRED + Yahoo `ZN=F` works, see `alpha_engine/bond_data_fred.py` which is already imported but unused by the sync path).

**Action:** add a guard in `active_picks_sync._build_proposal()`: if `time_exit AND abs(live_price - entry_price) < 1e-9`, skip the row (do NOT close it as TIME_EXIT with pnl=0). Force a re-fetch via `bond_data_fred.fetch_bond_data()` for bond symbols before any TIME_EXIT closure.

**Backfill:** one-shot script `tools/backfill_bond_time_exit_2026_05_31.py` that re-fetches close prices for the 117 forged rows from FRED + yfinance and writes real pnl_pct + correct status (WON/LOST/EXPIRED via `outcome_resolver.classify_outcome`). Expected outcome: ~80-100 of these become EXPIRED with small pnl, lifting n_real from 11 to ~120 in one batch.

### 2. P0 — Cap-artefact on `multi_asset_copytrader` ZN=F TP_HIT (+5.0000 row)

- Row id `multi_asset_futures_momentum::ZN=F::2026-03-26_1653` reports `pnl_pct=5.0000` exactly (entry 110.3125 → exit 104.7969 = +5.0% — but ZN moved ~5% in 35 minutes is implausible).
- Already covered by Phase 4 / Phase 8 backfills for OTHER classes, but **BOND was not in scope**. Add `BOND` to the Phase 4 capping-detector allowlist (`tools/detect_resolver_capping.py` if it exists; otherwise extend `tools/backfill_pnl_pct.py`).
- Reproducer: `SELECT * FROM trading_picks WHERE category='bond' AND pnl_pct=5.0000`.

### 3. P1 — `bond_scanner` 0-win calibration

- 0/8 wins, avg pnl -0.65%, all losses ≤ -0.43%, gross_loss 3.87. Strategy is using equity-style TP/SL widths on bond ETFs (TLT, IEF, LQD).
- File `alpha_engine/bond_scanner.py:261` (`run_bond_scanner`) likely passes default TP/SL multipliers. Bonds typically move 0.1-0.5% per day; a 0.5% SL is a coin-flip.
- **Mutation (three-axis per `docs/MUTATION_THREE_AXIS_PROTOCOL.md`):**
  - axis-1 regime gate: skip when 10Y-yield ATR(20d) < median (low-vol drift kills bond breakouts)
  - axis-2 vol floor: require `ATR_pct >= 0.4%` on TLT before emitting
  - axis-3 source confluence: require co-signal from `non_crypto_consensus` or `cta_replicator` before promoting bond_scanner picks past probation
- Reference for axis tuning: `alpha_engine/bond_strategy_harness.py` (already in repo, unwired).

### 4. P1 — Wire `bond_yield_curve_inversion` strategy

- `alpha_engine/bond_yield_curve_inversion.py` exists but emits 0 rows in `trading_picks` (not in `source_system` enum above). Classic inversion-as-signal has documented edge (Estrella-Mishkin 1998).
- **Wire-up plan:**
  - Add to `production_scanner.py` rotation (likely in `alpha_engine/scanner.py` since `scanner.py:1685` already handles TIME_EXIT).
  - Run on FRED daily series `T10Y2Y` (already fetched via `bond_data_fred.fetch_bond_data`).
  - Emit picks on TLT/IEF when `T10Y2Y` crosses zero from below (long duration on inversion-reversal).
- Acceptance: 6-month paper run, target PF>1.3 at n>=30 → graduate to live.

### 5. P2 — Diversify symbol set

- Currently 60% ZN=F, 25% TLT, 15% IEF/HYG/etc. ZN=F-only edge is fragile.
- Add: `SHY` (short-duration), `TBT` (inverse long-bond), `BIL` (1-3M T-bill), `BNDW` (global bonds) to the bond_scanner universe. File: `alpha_engine/bond_scanner.py:146` `fetch_bond_data` symbol list.

### 6. P2 — `non_crypto_consensus` BOND closure SLA

- 15 emitted, 0 closed-real (9 forged TIME_EXIT, 6 OPEN). Same resolver bug as #1.
- Once #1 ships, this contributes ~12 real closures in the backfill.

## What I would ship next (2 concrete PRs)

### PR A — `fix(bond): resolver time-exit forgery + 117-row backfill` (P0)

- `alpha_engine/active_picks_sync.py`: add `_validate_live_price()` guard refusing `live==entry` on TIME_EXIT for BOND.
- `alpha_engine/active_picks_sync.py:fetch_live_prices()`: add explicit BOND branch using `bond_data_fred.fetch_bond_data()` + yfinance fallback for futures (`ZN=F`).
- `tools/backfill_bond_time_exit_2026_05_31.py`: idempotent backfill, re-prices 117 forged rows, writes real pnl_pct + status. Dry-run / commit modes.
- Test: `alpha_engine/tests/test_bond_time_exit_resolver.py` — assert no row written with `exit_price == entry_price` when status=TIME_EXIT.
- Expected impact: BOND n_real jumps from 11 → ~120 in one merge; class moves from INSUFF-N to a real Tier-3/Tier-2 verdict.

### PR B — `feat(bond): wire bond_yield_curve_inversion + symbol diversification` (P1)

- `alpha_engine/scanner.py`: register `bond_yield_curve_inversion.scan()` in the non-crypto rotation.
- `alpha_engine/bond_scanner.py:146` (`fetch_bond_data`): expand symbol list to SHY, TBT, BIL, BNDW.
- Add `axis-2` vol floor to `bond_scanner.run_bond_scanner` (ATR_pct >= 0.4% on bond ETF before emit).
- Acceptance: 4-week shadow run, target n>=30, PF>=1.3 before promoting to picks-of-the-day.

## Risk register

- **Resolver bug**: if PR A backfill re-prices wrong (FRED EOD only, while picks are intraday), we may pile bias the OTHER direction. Mitigation: use yfinance 1H bars for `ZN=F` (futures trade 24h); use FRED close only as last resort.
- **+5.00 cap artefact**: already a known cross-class Phase 4 issue. Confirm BOND is in scope of the existing cap-detector before PR A merges.
- **Survivorship/look-ahead in `bond_scanner`**: harness at `alpha_engine/bond_strategy_harness.py` not yet run on production sample — should be a pre-req for PR B.
- **Liquidity**: ZN=F futures liquid 24h, but IEF/MUB/LQD have wide spreads in after-hours; bond_scanner currently emits any-time. Add session gate (NYSE 09:30-16:00 ET only for ETFs).

## Cross-references

- `docs/MUTATION_THREE_AXIS_PROTOCOL.md` (axis-1/2/3 mutation framework)
- `docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md` (do not RETIRE bond_scanner before mutation attempt)
- `reports/peer_blackbox_incidents-enhancements-pr_2026-05-31.md` (Phase 4/8 resolver-bug context)
- `audit_dashboard/data/money_ready_verdict.json` (2026-05-24 BOND verdict snapshot)
- `alpha_engine/bond_data_fred.py`, `alpha_engine/bond_yield_curve_inversion.py`, `alpha_engine/bond_strategy_harness.py` (dormant code waiting for PR B wire-up)
