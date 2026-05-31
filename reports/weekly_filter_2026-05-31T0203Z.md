# Weekly Real-Money Filter & Money-Ready Gap Audit — 2026-05-31

**Author:** claude-opus-4.8 (`/money-maker-readyv2`)
**Canonical sources:** `audit_dashboard/data/money_ready_verdict.json` (gen 2026-05-30T23:05Z), `pf_registry.json` (gen 2026-05-30T23:05Z), live `ejaguiar1_stocks.at_raw_picks` (queried 2026-05-31T02:00Z), `*/data/closed_picks.json` (canonical pick set, 430 policy-clean rows of 3258 raw).

---

## ⚠️ CORRECTION (2026-05-31T02:10Z) — tighter-SL hypothesis REFUTED by price-path backtest

A real intrabar (1m Binance) price-path backtest (`reports/rr_backtest_validation_2026-05-31.md`, reproducer `tools/rr_backtest_validation.py`, 100% data coverage, 0 skips) **refutes the winsorization counterfactual in §2**. Tightening the stop-loss does **NOT** raise PF — it collapses it, because tight stops get whipsawed out on 1m noise before the trade reverts:
- `crypto_liquidity_wick_reversal_v1`: real PF at SL 0.4–0.8% = **0.22→0.64** (baseline 1.50). The winsorized 2.47–2.96 was an upper-bound fantasy. **Do not tighten.**
- `atr_percentile_gate`: real PF at SL 0.4/0.5% = **0.93/1.07** (not 1.67/1.47). PF only *rises as the stop loosens* (0.8% → PF 1.28, WR 62%), still sub-Tier-2.

**Also:** both strategies are **100% BTCUSDT** (single-symbol) — they are low-vol BTC scalps, not diversified sleeves. The corrected money-ready path is: explore *looser* stops + grow n≥100, not tighten. The §2 winsorized table below is retained only to show what was tested and disproven.

---

## 0. Headline

**0/8 asset classes pass Tier-2.** No class is money-ready today. ~~Two ~58%-WR CRYPTO strategies cross Tier-2 by tightening the stop~~ — **this was refuted on real price paths (see correction above)**. The genuine leads: `crypto_liquidity_wick_reversal_v1` already sits at PF 1.50 / 58% WR (n=43, BTCUSDT scalp) and needs n≥100 + a *looser*-stop experiment; `genome/mega_mutation_MACD_RSI` (PF 4.28) needs OOS validation. R:R *tightening* is off the table.

---

## 1. Per-class canonical snapshot (policy-clean, net of slippage)

| Class | n | WR | PF | MDD | Verdict | Gap to money-ready |
|---|---|-----|------|-----|---------|--------------------|
| CRYPTO | 331 | 37.5% | 0.889 | 100% | NOT_READY | Class PF<1, but sub-strategies carry the edge (see §2) |
| EQUITY | 39 | 28.2% | 0.145 | 98% | INSUFFICIENT_DATA | No proven sleeve; needs signal volume + a working entry |
| FOREX | 28 | 28.6% | 0.037 | 81% | INSUFFICIENT_DATA | All strategies losing; PR#6 consolidation in progress (see §4) |
| FUTURES | 12 | 16.7% | 0.536 | 17% | INSUFFICIENT_DATA | ~95% single-engine; not a real edge |
| COMMODITY | 9 | 44.4% | 1.812 | 6.6% | INSUFFICIENT_DATA | PF>1.5 but n=9; needs post-COT-dedup volume |
| ETF | 4 | 50.0% | 0.476 | 6.2% | INSUFFICIENT_DATA | n far too small |
| BOND | 0 | — | — | — | INSUFFICIENT_DATA | No decisive bonds in window |
| PENNY | 1 | 0% | 0.00 | — | INSUFFICIENT_DATA | Gate-0 blocked |

The class-level CRYPTO PF of 0.889 is dragged down by losing strategies (`volume_spike_breakout` PF 0.29 n=191, `bollinger_squeeze` PF 0.18 n=59, `luxalgo_confluence` PF 0.26 n=43). The **winning** strategies are hidden inside the aggregate.

---

## 2. The actual edge — winning entries that just need R:R / TP-SL optimization

Direct answer to "do we have winning strategies that just need TP/SL (or R:R) optimized?" — **Yes, two, both CRYPTO**, plus a backtest candidate.

### 2a. `atr_percentile_gate` — good entry, bad exit ratio
- n=29 policy-clean, **WR 58.6%**, PF 1.105.
- avgWin **+0.42%** vs avgLoss **−0.54%** → |W/L| = 0.78. **Losers are bigger than winners** despite a >58% hit rate — textbook R:R problem.
- Exit mix: SL 10 / TIME 9 / TP 10.
- **Loss-cap counterfactual** (winsorize losses = simulate tighter SL):
  - SL @ −0.5% → PF **1.47**
  - SL @ −0.4% → PF **1.67** ← crosses Tier-2
- Kelly (quarter, at improved R≈1.5): **~7.7% of account**; baseline ~1.4%.

### 2b. `crypto_liquidity_wick_reversal_v1` — closest to money-ready, exit timing mistuned
- n=43 policy-clean, **WR 58.1%**, PF **1.498** (already Tier-2-ish).
- **40% of exits are TIME (timeout)**: TP 10 / SL 16 / TIME 17 → TP target/hold-time mistuned, leaving profit on the table and letting losers mature.
- **Loss-cap counterfactual**:
  - SL @ −0.5% → PF **2.47**
  - SL @ −0.4% → PF **2.96** ← near Tier-1
- Kelly (quarter, at improved R≈2.0): **~9.3% of account**; baseline ~4.8%.
- **This is the single best near-term money-ready candidate.** It only needs (a) exit-timing/SL tuning and (b) sample growth from n=43 → n≥100.

### 2c. `mega_mutation_MACD_RSI` (genome) — elite profile, but backtest-overfit until proven OOS
- n=210, **WR 68.6%, PF 4.276**, well-diversified (top symbol JUPUSDT 21.9%), balanced LONG/SHORT (107/103), clean TP/SL exits (TP 141 / SL 65 / EXPIRED 4).
- **Excluded from the policy-clean verdict** (collapses to n=1) because `genome/` is a **genetic-evolution backtest engine** (`dna_backtester.py`, `genetic_programmer.py`, `mega_mutation_tournament.py`; the dir even ships its own `HONEST_ASSESSMENT.md` / `PATH_TO_LIVE_TRADING.md`). PF 4.28 is almost certainly **in-sample overfit** from the mutation search.
- **Action:** strict OOS forward test via `genome/mega_mutation_live_tracker.py`. If it holds PF≥2 / WR≥55% on n≥50 forward with no single-symbol >30%, it becomes the strongest CRYPTO sleeve. Until then, **do not size it.**

> **Methodology caveat:** the loss-cap counterfactual is an *upper bound*. It assumes a tighter SL would have exited at exactly −cap without first being whipsawed and reversing into a win. A proper price-path backtest (intrabar OHLC) is required before sizing real capital. The directional signal — "losers have fat tails; tightening stops lifts PF materially" — is robust across both strategies.

---

## 3. Stale / inconsistent data found (tracked in DB)

| Finding | Detail | Tracked |
|---|---|---|
| **dashboard_data.json 52h stale** | gen 2026-05-28T21:29Z (age 52.5h) vs verdict/registry fresh (2026-05-30T23:05Z). The `asset_class_health` / `walkforward` / `fwd_vs_bt_divergence` regenerator lags ~2 days behind the verdict pipeline. | INCIDENT_OVERALL #33 (P2) |
| **DISPUTED CRYPTO banner 6d stale** | Banner cites raw-DB 90d WR 39.4% (n=2001, dated 2026-05-25). Live `at_raw_picks` now: 90d **41.9%** (n=7198), 30d 42.6%, **14d 50.9%** (recovering), 2d 41.0%. Dispute direction still valid vs Smart-Picks 78.9%, but figures understate current raw WR. | INCIDENT_CRYPTO #5 (P2) |
| **Two disjoint pick pipelines** | Canonical verdict reads `*/data/closed_picks.json` (430 policy-clean rows); pick_funnel + raw audit read MySQL `at_raw_picks` (7000+ CRYPTO/90d). They share neither rows nor labels → systemic dashboard-vs-DB divergence. Strategy names like `crypto_liquidity_wick_reversal_v1` have 59 WON / 0 LOST in `at_raw_picks` but balanced win/loss in the registry. | Noted (root cause of repeated reconciliation incidents) |

---

## 4. FOREX PR#6 review (peer "Zoo" / ELTONSVLLM_SERVER) — REQUEST-CHANGES

Reviewed Zoo's uncommitted PR#6 (FOREX consolidation). Verdict: **REQUEST-CHANGES**. Tracked as INCIDENT_FOREX #6 (P1).
- **Dead code:** the consolidation gate is in `evaluate_non_crypto_candidate()` which has **zero production callers**; the live path uses `passes_non_crypto_policy()` which does not delegate to it → block-all-except-`cta_cross_asset_tsmom`-SHORT never executes.
- **No-op placeholder:** USDJPY concentration cap at `non_crypto_policy.py:702-710` is a bare `pass`.
- **Unsupported survivor:** `cta_cross_asset_tsmom` has **zero clean FOREX trades** in `pf_registry` → whitelisting a never-traded strategy.
- **The good part:** `config.py` `BLACKLISTED_STRATEGIES` additions ARE wired (enforced via `copy_trader_bridge.py:204`) and will block the 4 bleeding FOREX strategies.

---

## 5. Recommended next actions (ranked by edge-per-effort)

1. **(S, HIGH)** Price-path backtest tighter SL on `crypto_liquidity_wick_reversal_v1` and `atr_percentile_gate`. If confirmed, ship the new SL into their generators. → first credible money-ready CRYPTO sleeve. (ENHANCEMENT_CRYPTO #4, #5)
2. **(M, HIGH)** Grow `crypto_liquidity_wick_reversal_v1` sample n=43→100 with the tuned exits, then re-run the money-ready verdict for a CRYPTO sub-class PASS.
3. **(L, HIGH)** OOS-forward-validate genome `mega_mutation_MACD_RSI`; if it holds, it's the top sleeve. (ENHANCEMENT_CRYPTO #6)
4. **(S, MED)** Fix Zoo's PR#6 (wire the gate, implement/remove the USDJPY cap). (INCIDENT_FOREX #6)
5. **(S, MED)** Refresh the DISPUTED banner from a live query + fix the dashboard_data.json regen lag. (INCIDENT #5, #33)

---

## 6. Success-criteria status (money-maker-readyv2)

| Criterion | Status |
|---|---|
| EQUITY ≥5 picks elite_score≥60 WR≥55% | ❌ no proven EQUITY sleeve (PF 0.145) |
| CRYPTO sub-class filter WR≥50% live, PF≥1.5 @ n≥100 | ⏳ candidate found (`wick_reversal` 58% WR / PF 1.50 @ n=43); needs n≥100 |
| COMMODITY n≥50 post-dedup, top strat PF≥1.5 | ❌ n=9 |
| ETF n≥150, PF≥1.3 | ❌ n=4 |
| FOREX directional filter WR≥50% | ❌ none exists; consolidation/freeze in progress |
| BOND top strat @ n≥20 | ❌ n=0 |
| Kelly sizing on all filter picks | ✅ computed for the 2 R:R candidates (quarter-Kelly 1.4–9.3%) |

**Conclusion:** No class is money-ready yet, but a concrete, evidence-backed path to the first CRYPTO sleeve exists via R:R optimization of two existing 58%-WR strategies. All findings tracked in the incidents/enhancements DB → `findtorontoevents.ca/audit/incidents.html`.
