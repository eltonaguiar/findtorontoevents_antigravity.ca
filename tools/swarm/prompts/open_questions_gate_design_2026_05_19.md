# Quant-Design Open Questions — Money-Ready / Tier Gate (2026-05-19)

You are a senior quant reviewer. Settle TWO open design questions for a real-money
trading-pick certification system. Be definitive: give a recommendation, the exact
formula/threshold, and the exact file+function where the change lands.

## Repo facts (verified — do not re-investigate, use these)

The per-asset-class certification gate lives in `alpha_engine/money_ready_verdict.py`.

**Q1 — current WR gate (the thing in question):**
- `_verdict()` at lines 613-647. Inside it:
  - line 620: `wr_floor = MIN_WR_BY_CLASS.get(asset_class.upper(), MIN_WR)`
  - line 621: `wr_ok = wr >= wr_floor`
  - line 628: `if wr_ok and pf_ok and (dsr_ok or spa_ok) and (pbo_ok or spa_ok): ... return "MONEY_READY"`
  So WR is a HARD AND-gate: a sleeve with WR below the floor can NEVER be MONEY_READY,
  even at PF 1.78.
- Floors (`CLASS_WR_FLOORS`, line 169): EQUITY 0.52, CRYPTO 0.50, default `MIN_WR=0.55`
  (COMMODITY/FOREX/ETF/BOND/FUTURES).
- An `_expectancy_gate()` ALREADY EXISTS at lines 650-673 but is WARNING-ONLY. It computes
  `E = WR*(avg_win - slippage) - (1-WR)*(avg_loss + slippage)` and stamps
  `expectancy` / `expectancy_ok` on the verdict (lines 822-823). It does NOT affect the verdict.
- Live data showing the problem: COMMODITY PF 1.78 / WR 46.9% / n=750 — a textbook healthy
  trend-following book, but currently BLOCKED from MONEY_READY purely by the 55% WR floor.
  FOREX PF 0.27 / WR 46.4% — correctly sub-floor, but blocked by WR for the WRONG reason
  (PF, not WR, is what kills it).

**Q2 — class-level MDD:**
- `_rolling_mdd()` (line 680) and `_mdd_cvar_gate()` (line 702) ALREADY compute per-class
  max drawdown from the per-pick NET return series, and stamp `mdd` / `mdd_ok` / `cvar_95`
  on the verdict (lines 847-850). Threshold `MDD_GATE_THRESHOLD = 0.20`. Enforcement is
  shadow-only (`MDD_GATE_ENFORCE` env, default OFF).
- BUT: MDD is NOT stored in the two canonical published surfaces:
  - `audit_dashboard/data/pf_registry.json` — `by_asset_class_policy_clean_net` rows have
    `n`, `win_rate_pct`, `profit_factor` but NO `mdd`.
  - `audit_dashboard/data/dashboard_data.json::performance.asset_class_health` — same, no MDD.
- `money_ready_verdict.py` reads pf_registry via `build_pf_registry.py` (functions
  `load_rows` / `classify_rows`). The MDD it computes is ephemeral (recomputed each run,
  never persisted).
- Charter `docs/PERFORMANCE_CHARTER.md` §2 tier table REQUIRES MaxDD (Tier1 <=10%,
  Tier2 <=20%, Tier3 <=25%); §6 defines MaxDD = peak-to-trough on cumulative pnl curve as
  a % of peak. So MDD is mandatory for tier certification but not surfaced per class.

## The two questions

### Q1
Should the money-ready / tier gate switch from a flat hard `WR >= floor` rule to an
EXPECTANCY-based gate (so a PF>1.5 trend/carry sleeve with WR<50% can certify)?
- If yes: give the EXACT gate predicate to replace line 628's `wr_ok` term. Specify how
  WR, PF, expectancy, and slippage combine. Should WR be dropped entirely, kept as a soft
  signal, or kept only as a floor (e.g. a much lower 40% sanity floor)?
- State the exact threshold for the expectancy term and whether expectancy should be
  net-of-cost (it currently is — uses per-class `SLIPPAGE_BPS`).
- Name the exact function + line in `money_ready_verdict.py` to edit.

### Q2
Where should class-level MDD be computed and stored so a sleeve can be tier-certified on
PF + WR + MDD together?
- Should MDD be computed in `build_pf_registry.py` and written into each
  `by_asset_class_policy_clean_net` row of `pf_registry.json` (one source of truth), or
  stay computed in `money_ready_verdict.py`, or both?
- Give the exact key name and definition (peak-to-trough on what series — per-pick NET
  cumulative? equity curve? % of peak?).
- Name the exact file + function for the change.

## Output format (per question)
1. Definitive recommendation (one sentence).
2. Exact formula / threshold / gate predicate.
3. Exact target file + function + approximate line.
4. Any risk or dissent worth recording.
