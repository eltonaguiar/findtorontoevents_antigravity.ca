# Copy-trader & prediction markets vs High Conviction — validation (2026-04-14)

This note cross-checks Claude’s **META** near-miss write-up, expands **copy-trader** and **prediction market (PM)** actives **by asset class** on the current embedded snapshot, and states what would need to change for those rows to reach **strict HC**.

**Snapshot:** `audit_dashboard/data/dashboard_data.json` (97 `picks.active` at time of analysis). Re-run:

```powershell
python tools/_hc_noncrypto_diagnostic.py
```

## 1. Claude / Cursor alignment — META

**Confirmed.** The diagnostic lists:

`META  multi_asset_copytrader  sc=37  tr=5  n=746  wr=46.8  Gate1_score_lt_40`

| Gate | META | HC floor (typical) |
|------|------|---------------------|
| 1 Score | 37 | ≥ 40 (`scoreAbsoluteFloor`) |
| 2 Compound | — | Not evaluated first; Gate 1 fails first |
| 4 Forward N | 746 | ≥ 5 |
| 5 Forward WR | 46.8% | ≥ 45% |
| 6 Trust | 5 | ≥ 5 for non-crypto |
| Strict edge (EQUITY) | Need score ≥ 50 & trust ≥ 3 | After clearing base HC |

**Important nuance:** Even a **+3** bump to clear **Gate 1** (37 → 40) is **not enough** for **strict** HC: `passesValidatedEdgePerClass` for **EQUITY** requires **`score ≥ 50`** (and `trust ≥ 3`). META already satisfies trust for that layer. So the real gap for **first EQUITY strict HC row** is **score 37 → 50** (or compound rule with **trust ≥ 8** if score stays &lt; 50), not **37 → 40**.

Claude’s “+3 unlocks first EQUITY HC” is correct for **Gate 1 only**; the **validated-edge** layer still blocks until **50+** unless the UI uses non-strict HC (`filterHighConvictionOrdered` only, without `filterValidatedEdgePerClass`).

## 2. Copy-trader pipeline — by asset class (this snapshot)

`JSON_PICK_SOURCES` in `audit_trail/dashboard_generator.py` loads multiple files under **`source_system: multi_asset_copytrader`** (multi-asset, forex, stocks, commodity) plus `copy_trader_intel`, highscore, clones, etc.

**Despite that, `picks.active` only contains two copy-related rows:**

| Symbol | `source_system` | Asset class | Score | Trust | `strat_fwd_trades` | `strat_fwd_wr` | First HC fail |
|--------|-----------------|-------------|-------|-------|--------------------|----------------|---------------|
| META | `multi_asset_copytrader` | EQUITY | 37 | 5 | 746 | 46.8% | Gate 1 (strict edge also needs score ≥ 50) |
| COST | `multi_asset_copytrader` | EQUITY | 34 | 4 | 4 | 25.0% | Gate 1 |

No **FOREX / COMMODITY** `multi_asset_copytrader` rows appear in this **active** list (ingestion, kill-list, collapse, and `passes_active_gate` / score floors still winnow the 69-file universe down — see `docs/COPYTRADER_MERGE_BUG_20260405.md`).

**Follow-up worth doing (as Claude said):** trace **penalty stack** and **raw vs displayed score** for `multi_asset_copytrader` in `audit_trail/quality_gates.py` (e.g. copytrader stale/dead signal penalties ~lines 2042–2053, non-crypto raw score floor ~2074+). Goal: decide whether **META**’s 37 is **intentionally conservative** or **over-penalized** relative to 746-trade forward history.

## 3. Prediction markets — by asset class (this snapshot)

All PM-tagged actives are **CRYPTO** (no EQUITY/FOREX PM rows in this file):

| Symbol | `source_system` | Score | Trust | `strat_fwd_trades` | `strat_fwd_wr` | First HC fail |
|--------|-----------------|-------|-------|--------------------|----------------|---------------|
| DOGEUSDT | `pm_kalshi_signals` | 78 | 4 | **0** | null | **Gate 4** |
| BNBUSDT | `pm_kalshi_signals` | 72 | 4 | **0** | null | **Gate 4** |
| ETHUSDT | `pm_kalshi_signals` | 57 | 4 | **0** | null | **Gate 4** |
| BTCUSDT | `pm_whale_signals` | 51 | 4 | **0** | null | **Gate 4** |

**Interpretation:** PM rows carry **rich multi-source groupings** but **no joined strategy forward ledger** on the dashboard row (`strat_fwd_trades == 0`). So they die at **Gate 4** before Gate 5, independent of headline score.

**What would unlock PM for HC (policy / engineering):**

1. **Forward-stats join:** attach `strat_fwd_trades` / `strat_fwd_wr` for `pm_kalshi_signals` / `pm_whale_signals` / `polymarket_signals` the same way other strategies get leaderboard stats, **or**
2. **Narrow exemption** (high risk): gated exception for PM sources with proven cohort stats — must be explicit in `hc_gate_params` / code and documented.

## 4. Post-deploy checks (peer checklist)

When fresh `dashboard_data.json` lands after PRs **#206–#208**:

| Check | Expected |
|-------|----------|
| `active_total` | 91 if **6 SPORTS** removed |
| `by_asset_class.SPORTS` | 0 or absent |
| Goldmine sample | e.g. strat_fwd_trades ~85, strat_fwd_wr ~21% (forward visible) |
| Goldmine first fail | Still **Gate 2** if score 45 and trust 4 |
| META | Still **Gate 1** / strict **edge** unless scoring changes |
| PM rows | Still **Gate 4** until forward join exists |

## 5. Summary

- **Claude’s META analysis matches** the diagnostic; tighten language: **strict HC** needs **score ≥ 50** for EQUITY, not only **≥ 40**.
- **Copy-trader:** only **two** EQUITY survivors in actives; **META** is the stand-out **near-miss** on score floors.
- **Prediction markets:** **four** crypto actives; **all** blocked at **Gate 4** (no forward N), not at PM-specific logic.
