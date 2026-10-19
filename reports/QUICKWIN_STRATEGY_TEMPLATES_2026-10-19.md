# Quick-Win Symbols & Strategy Templates by Asset Class — VERIFIED EDITION (2026-10-19)

**Provenance:** This is the materialized + verified form of the "Quick-Win Symbols & Strategy
Templates by Asset Class" task output (2026-10-19). Every claim in that draft was traced back to
a repo source; corrections are marked **[CORRECTED]**. Grounded in the June 13 2026 honest ledger
run (`reports/weekly_cycle_output.md`), the frozen canonical ledger
(`audit_dashboard/data/intrabar_truth_by_class.json`, generated 2026-06-21), the July 2026 edition
pivot (`.claude/skills/money-maker-ready-July112026edition/`), and the money-maker-ready tier
gates (`alpha_engine/value_backtest.py::classify_tier`, `.claude/skills/money-maker-readyv2/SKILL.md`).

**Not financial advice — research/educational.**

## 0. The gates (exact, from code)

Tier classification — `alpha_engine/value_backtest.py::classify_tier(wr, pf, max_dd, n)`:

| Tier | PF | WR | MaxDD | n floor |
|---|---|---|---|---|
| Tier 1 | ≥ 2.0 | ≥ 55% | ≤ 10% | n ≥ 100 |
| **Tier 2 (money-ready bar)** | **≥ 1.5** | **≥ 50%** | **≤ 20%** | **n ≥ 100** |
| Tier 3 | ≥ 1.2 | ≥ 45% | ≤ 30% | n ≥ 100 |
| below | — | — | — | n < 100 → `"below"` regardless |

Data-integrity filters — `.claude/skills/money-maker-readyv2/SKILL.md` (raw `at_pick_outcomes` WRs are inflated
artifacts unless ALL apply):
1. Exclude backfill (`resolver_version NOT LIKE 'backfill%'`, `resolved_at IS NOT NULL`)
2. Exclude banned sources (13-strategy blocklist)
3. Per-class sane-pnl guard (`ABS(pnl_pct)` caps: FOREX 20 / COMMODITY 30 / BOND 25 / CRYPTO 95 / else 50)
4. Count EXPIRED as a non-win (`WR = WON / (WON+LOST+EXPIRED+FLAT)`)
5. Intrabar validation before trusting a WR (first-touch, SL-wins-ties)
6. Reject single-snapshot artifacts — ≥3 distinct months at n≥30/month

**[CORRECTED]** The draft said "filters 1–4 mandatory" then listed 6 items; filters 5 and 6 are
part of the same mandatory list, and the money-ready bar additionally requires **WR > 52%
(EXPIRED-inclusive)** plus a ≥4-week paper pilot before real capital.

## 1. Current gate status — measured, not asserted

### 1a. Canonical frozen honest ledger (`intrabar_truth_by_class.json`, generated 2026-06-21T06:22Z)

| Class | n | WR% | PF | verdict | Tier-2 gates (n≥100 / PF≥1.5 / WR≥50%) |
|---|---|---|---|---|---|
| CRYPTO | 1155 | 32.4 | 0.727 | FAIL | Y / N / N |
| EQUITY | 120 | 35.0 | 0.465 | FAIL | Y / N / N |
| COMMODITY | 116 | 35.3 | 1.06 | FAIL | Y / N / N |
| FOREX | 101 | 43.6 | 1.169 | FAIL | Y / N / N |
| MEMECOIN | 77 | 26.0 | 0.58 | INSUFFICIENT_N | N / N / N |
| ETF | 16 | 0.0 | 0.0 | INSUFFICIENT_N | N / N / N |
| FUTURES | 16 | 31.2 | 0.49 | INSUFFICIENT_N | N / N / N |
| BOND | 6 | 33.3 | 2.242 | INSUFFICIENT_N | N / Y / N |
| UNKNOWN | 4 | 25.0 | 0.425 | INSUFFICIENT_N | N / N / N |

**0/9 classes pass Tier-2** (`classify_tier` → `"below"` for every class; MDD is a
backtest-series concept not carried in the ledger, but n/PF/WR already fail everywhere).

### 1b. Live money-readiness verdicts (payload `audit_dashboard/data/dashboard_data.json`, generated 2026-10-19T06:55Z — refreshed from the live site via `tools/refresh_local_audit_mirror.py`; the 2026-10-18T08:34Z copy produced identical n/WR/PF for all 9 classes)

| Class | n | WR% | PF | MDD | n_ok | wr_ok | pf_ok | mdd_ok |
|---|---|---|---|---|---|---|---|---|
| CRYPTO | 3497 | 35.5 | 0.881 | 1.0009 | ✅ | ❌ | ❌ | ❌ |
| EQUITY | 229 | 55.9 | 0.8365 | 0.9998 | ✅ | ✅ | ❌ | ❌ |
| FOREX | 547 | 30.7 | 0.6111 | 0.9855 | ✅ | ❌ | ❌ | ❌ |
| COMMODITY | 227 | 40.1 | 1.0281 | 0.1703 | ✅ | ❌ | ❌ | ✅ |
| FUTURES | 47 | 40.4 | 1.0402 | 0.1758 | ❌ | ✅ | ❌ | ✅ |
| ETF | 15 | 73.3 | 1.8251 | — | ❌ | ✅ | ✅ | — |
| MEME | 13 | 7.7 | 0.0206 | 0.5378 | ❌ | ❌ | ❌ | ❌ |
| PENNY_STOCK | 1 | 0.0 | 0.0 | — | ❌ | ❌ | ❌ | — |
| BOND | 0 | 0.0 | 0.0 | — | ❌ | ❌ | ❌ | — |

**0/9 money-ready.** Notable movement since June: EQUITY cleared n≥100 *and* WR≥50% (55.9%) but
still fails PF (0.837 vs 1.5); ETF shows the best-looking numbers (WR 73.3%, PF 1.83) on **n=15** —
classic small-n mirage, correctly blocked by the n-floor. FOREX n=547 but PF collapsed to 0.611.

## 2. Templates (corrected, with code pointers)

### 2.1 ETF — Tactical Asset Allocation (TAA) — Money-Ready Track

**Methodology:** Antonacci dual momentum (absolute + relative), monthly rebalance.

- Universe: **[CORRECTED]** 14 ETFs, not 12 — `tools/tactical_rotation_tracker.py::UNIVERSE`
  = SPY, QQQ, IWM, EFA, EEM, TLT, IEF, AGG, GLD, DBC, VNQ, LQD, HYG, TIP (VTI/SHY from the
  draft are not in the tracked universe).
- Entry rule: **[CORRECTED]** top-**5** by trailing 6-month return (not top-3); negative absolute
  momentum slots rotate to **AGG** (not SHY/TLT) — `TOP_N = 5`, `LOOKBACK_MONTHS = 6`,
  `CASH_ASSET = "AGG"`. 6m is the regime-robust default; the 2026-07-04 POC picks were locked
  with the 9-month signal.
- Proven edge (verified in `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md`): top5-6m rotation
  Sharpe **0.88**, MaxDD **−19%**, all-3-thirds positive; the 9m region does Sharpe 1.09–1.21 /
  MaxDD −12/−17% vs SPY −24%. Smart-beta/risk-adjusted improvement, NOT excess return.
- Tools: `tools/tactical_rotation_tracker.py`, `tools/tactical_blend_tracker.py`; each run
  writes its sidecar JSON (`audit_dashboard/data/tactical_rotation_status.json` — not present
  until the tracker is run; read-only, no orders).
- Gating: backtest-tier claim only — it does **not** pass through the pick ledger, so the class's
  ledger n=16/15 does not refute it; forward-track monthly before sizing up.

### 2.2 Equity — High-Dividend, Low-Beta Quality

- Symbols: SCHD, VIG, AAPL, MSFT, JNJ, KO, PEP, PG, V, WMT.
- Entry rules split into **code-backed** vs **proposed**:
  - Code-backed (`alpha_engine/value_screener.py`): SafetyGate = Altman Z'' ≥ 1.10 **AND**
    Beneish M ≤ −1.78; universe gates: market cap ≥ $300M, ≥5y operating history, 10-K age ≤
    540d, excludes Financial/Utilities; Piotroski F enters QualityComposite (F/9), not an F≥7
    hard filter.
  - **[CORRECTED]** Proposed (NOT implemented anywhere): yield ≥ 2.5%, beta ≤ 0.8,
    Piotroski F ≥ 7 as hard gates.
- Exit/thesis-break: `alpha_engine/long_term_pick_contract.py` (`thesis_break_rules`,
  exit_mode `thesis`), contract is an opt-in sidecar — "dividend cut / 2 consecutive earnings
  misses / beta > 1.2" are **proposed** rules, not coded thresholds.
- Gate status: **[CORRECTED]** the cohort constraint is NOT n — EQUITY is n=120 (June) / n=229
  (Oct). The binding failure is **PF 0.465 → 0.8365 vs ≥1.5**  (the draft's "PF 0.460" number is
  the *equity* ledger row, see §4).

### 2.3 Commodity — Carry Strategy

- Symbols: GLD, SLV, USO, UNG, DBC.
- Implementation that exists: `alpha_engine/commodity_basis_carry.py` (backwardation proxy =
  price above SMA → long top-3 strongest carry), plus `alpha_engine/basis_carry.py`. The draft's
  "positive roll yield + 3-month momentum > 0" is a **proposed** refinement of the SMA proxy.
- Gate status: COMMODITY ledger n=116 (June) / 227 (Oct) — n clears, PF 1.06 / 1.03 and WR
  35.3% / 40.1% fail. Class is frozen at intake (BLOCKED_ASSET_CLASSES, 0.0 volume cap, SHORT
  kill) — paper only until the freeze is an operator decision.

### 2.4 Forex — Carry Trade

- Pairs: USD/JPY, EUR/JPY, AUD/JPY.
- Implementations: `alpha_engine/forex_carry_momentum_harvest.py`,
  `alpha_engine/forex_carry_ppp.py`, `alpha_engine/fx_carry_vix_regime.py`. "Vol-targeted to
  10% annualized" is **proposed** (no vol-target code found).
- **[CORRECTED]** "forex ledger currently blocked (PF 0.460)" — wrong attribution. The honest
  ledger FOREX row is PF **1.102 (n=95, June 13)** → **1.169 (n=101, June 21)** → **0.611
  (n=547, 2026-10-19)**; PF 0.460 is the **EQUITY** row of the same June 13 run
  (`reports/weekly_cycle_output.md`). FOREX's real blocker is different and stronger: the gross
  edge (PF 1.79, CI-LB 1.35 @ n_eff 304) **dies at ~1bp of round-trip cost** (net PF 0.46 @ 5bp)
  — `reports/FOREX_NETCOST_CILB_SENSITIVITY_2026-06-13.md`. "Only deploy after n≥100 clean
  cohort" is also stale: n cleared long ago; the binding gates are net **CI-LB ≥ 1.15** and PF.

### 2.5 Crypto — Stable-Coin Inflow Signal + Funding-Rate Arb

- Signals: USDT/USDC inflow > 2× 7-day avg → long BTC/ETH (24–48h); funding > +0.05%/8h →
  short perp/long spot; funding < −0.03%/8h → long perp/short spot.
- Funding threshold verified: `alpha_engine/funding_rate_arb.py::MIN_FUNDING_THRESHOLD = 0.0005`
  (0.05% per 8h) ✅. Related modules: `crypto_funding_rate_carry.py`, `pairs_arb` (BTC-ETH/SOL).
- **[CORRECTED]** On-chain source: the repo's on-chain momentum uses the **Glassnode free tier**
  (MVRV-Z, active addresses, exchange balance) via `alpha_engine/crypto_onchain_momentum.py`
  (BTC/ETH, default-OFF) — **not Santiment**; no Santiment integration exists in `alpha_engine/`.
- Ledger claim verified ✅: CRYPTO WR 32.4% / PF 0.727 (n=1155, frozen ledger); current  verdicts n=3497 / WR 35.5% / PF 0.881 — still FAIL. Paper-trade only until n≥250 clean cohort with
  PF ≥ 1.5 (the draft's stricter crypto bar).

### 2.6 Bond — Yield-Curve Carry

- Positions: long TLT / short SHY (steepener), or long IEF (belly).
- Implementations that exist: `alpha_engine/bond_yield_curve_slope.py` (emitted as
  `bond_yield_curve_slope` by `academic_strategies_emitter.py`), `ag_bond_yield_curve_momentum`,
  backtests `audit_dashboard/data/bond_tlt_ief*.json`, `bond_duration_rotation_backtest.json`.
  The "2s10s > 50bp + VIX < 20" entry rule is **proposed** (no code match).
- Gate status: BOND n=6 (June) → n=0 (Oct payload) — sample far below the n≥100 bar. Freeze
  stands.

## 3. Mandatory pre-deployment checklist (unchanged, all classes)

1. Data-integrity filters 1–6 (§0) before ANY WR/PF is quoted.
2. Tier gate: PF ≥ 1.5, WR ≥ 50% (money-ready bar: WR > 52% EXPIRED-inclusive), MDD < 20%,
   n ≥ 100 — via `classify_tier()`.
3. No fabricated win-rates — every claim traces to `at_pick_outcomes` / `at_signal_outcomes`
   (honest ledger) or `tournament_picks`.
4. Thesis-break rules via `alpha_engine/long_term_pick_contract.py` for long-horizon equity.
5. Walk-forward validation via `alpha_engine/value_backtest.py::classify_tier()` + the
   moneyreadiness page gates (bootstrap CI-LB, DSR/PBO/SPA, wf_oos) on `/audit/moneyreadiness/`.

## 4. Claim-by-claim verification of the original draft

| Draft claim | Verdict | Source |
|---|---|---|
| `reports/TACTICAL_ROTATION_EDGE_2026-07-04.md` exists | ✅ verified | glob |
| Sharpe 0.88 / MaxDD −19% (6m TAA) | ✅ verified | report L48 (top5-6m row) |
| "12-ETF universe" | ❌ → 14 ETFs | `tactical_rotation_tracker.py::UNIVERSE` |
| "hold top-3, else SHY/TLT" | ❌ → top-5, else AGG | same file `TOP_N`/`CASH_ASSET` |
| Tier gates PF≥1.5/WR≥50/MDD≤20/n≥100 | ✅ verified | `value_backtest.py::classify_tier` (Tier 2) |
| Filters 1–4 mandatory | ⚠️ → list is 1–6 + WR>52% bar | `.claude/skills/money-maker-readyv2/SKILL.md` |
| `value_screener.py` safety gates exist | ✅ verified (Z''≥1.10, M≤−1.78) | file header |
| `long_term_pick_contract.py` thesis-break | ✅ verified (opt-in sidecar) | file header |
| `value_backtest.py classify_tier()` | ✅ verified | L388 |
| FOREX "ledger PF 0.460" | ❌ → that's EQUITY (n=119, 0.460); FOREX 1.102 | `weekly_cycle_output.md` L32 |
| FOREX "blocked until n≥100" | ❌ → n=101+ since June; blocker is cost CI-LB | `FOREX_NETCOST_CILB_SENSITIVITY_2026-06-13.md` |
| CRYPTO WR 32.4% / PF 0.727 | ✅ verified (n=1155) | `intrabar_truth_by_class.json` |
| "on-chain stable-coin flow (Santiment)" | ❌ → Glassnode free tier, no Santiment | `crypto_onchain_momentum.py` L13 |
| Funding > 0.05%/8h threshold | ✅ verified | `funding_rate_arb.py::MIN_FUNDING_THRESHOLD` |
| "Only ETF TAA is money-ready today" | ✅ with caveat | true for the *TAA backtest track*; the ETF *pick class* is n=15 → INSUFFICIENT_N; 0/9 classes pass |
| "Equity next-best once n≥100" | ⚠️ stale → n=229 already; PF is the blocker | 2026-10-19 verdicts |
| Bond n thin, freeze until n≥100 | ✅ verified | BOND n=6 → n=0 |

## 5. Bottom line (corrected)

- **0/9 asset classes pass the Tier-2 / money-ready gates today** (both on the frozen June
  ledger and the 2026-10-19 live verdicts).
- The only defensible "money-ready track" remains the **ETF TAA rotation backtest**
  (Sharpe 0.88–1.21 region, MaxDD −12/−19% vs SPY −24%) — deploy at modest size,
  forward-track monthly; it is risk-adjusted smart-beta, not alpha.
- **Equity quality/dividend** is the closest pick-ledger candidate: n and WR gates now pass
  (n=229, WR 55.9%); it needs PF ≥ 1.5 (currently 0.8365) on a clean cohort before promotion.
- **Commodity / forex / crypto / bond** quick-wins stay paper-trade templates: commodity and
  bond are frozen (freeze + n=0), forex needs a sub-1bp execution edge (net CI-LB ≥ 1.15),
  crypto needs PF ≥ 1.5 on n ≥ 250 clean.

## 6. Machine-readable artifacts

- `reports/quickwin_strategy_templates.json` — the six templates as a versioned registry
  (`quickwin_strategy_templates/v1`): universe/symbols, entry rules tagged
  `implemented: true | partial` with code pointers, proposed-only rules listed separately,
  evidence, and `ledger_gate_applies` / `paper_only` / `track` flags.
- `tools/quickwin_template_gate_check.py` — gates every registry template against the live
  `money_ready_verdicts` + the frozen honest ledger using `classify_tier`. Read-only, stdlib,
  no network/DB. `--stdout` (table only), `--json` (machine output), default also writes
  `reports/quickwin_template_gate_status.json`. Exit 0 = ran, 1 = missing input.
- Last run (2026-10-19T07:14Z): **0/5 ledger-gated templates pass Tier-2 live; 5 paper-only;
  1 backtest-track (ETF TAA)** — consistent with §1.
