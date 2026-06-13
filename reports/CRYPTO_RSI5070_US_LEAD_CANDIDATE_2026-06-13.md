# crypto_rsi5070_us — the project's strongest HONEST money-ready lead (not yet promotable)

**Author:** claude-opus (8h money-ready loop, tick 2) · 2026-06-13 ~17:10Z
**What it is:** a pre-entry **entry-condition** layered on the honest intrabar CRYPTO cohort — `CRYPTO ∧ Wilder RSI(14, 1h) ∈ [50,70] ∧ session=US (13:30–21:00 UTC)` — defined in `tools/stamp_entry_conditions.py`. Features are computed strictly from pre-entry bars (≥77 bars, no look-ahead); outcomes are `at_signal_outcomes` intrabar first-touch (TP_HIT/SL_HIT), deduped (symbol,direction,day).

## Referee result (cluster-bootstrap PF CI-LB, symbol-day clusters, `tools/pf_ci_lower.py`)

| cost | PF | **CI-LB** | n_eff | verdict |
|---|--:|--:|--:|---|
| gross | 1.53 | 1.073 | 108 | sub-bar |
| **net ~16bp RT (crypto)** | **1.36** | **0.953** | 108 | **sub-bar — not promotable yet** |

- **WR 47.2%**, avg **+0.59%/trade** — crypto winners are large enough that 16bp barely dents PF (1.53→1.36), the **opposite** of the FOREX-consensus failure mode (tiny winners erased by 2bp).
- **IS/OOS net@16bp: 1.44 / 1.30** (split 2026-05-21) — **HOLDS the time-split with no decay.** This is the only candidate this session that does not collapse OOS.
- **No concentration:** top symbol RENDERUSDT only 6%. Well-diversified across the CRYPTO universe.

## Why this is the lead (and why it's NOT a FOREX-consensus repeat)
- It is **honestly intrabar-resolved** — not a daily-resolution artifact (cf. `reports/FOREX_CONSENSUS_HONEST_FIRSTTOUCH_2026-06-13.md`, where daily PF 2.88 → honest 1.02). The 1.36 net PF is on first-touch outcomes.
- It survives **realistic cost** (16bp RT) and **holds OOS** and is **diversified** — three independent robustness checks that every prior "candidate" failed on at least one axis.
- The **only** thing missing is statistical confidence: at n=108 the net CI-LB is 0.95, below the 1.15 promotion bar. The point estimate (1.36) and OOS-robustness (1.30) are promotion-grade; the lower bound needs more n to tighten.

## Status: FORWARD-ACCRUING, pre-registered gate
- **Gate (pre-registered, master loop §7):** n ≥ 150 honest intrabar → re-run the net-16bp CI-LB. **Promote to probation only if net CI-LB > 1.15 at n_eff ≥ 80** with the time-split and concentration still clean. ETA ~2026-06-25.
- Do **not** size now. Do **not** promote on the gross 1.53 or the point 1.36. The earlier grok `admissible=FALSE` flag (gross CI-LB 1.07 < 1.15, WR<50%) is consistent — it is sub-bar *today* — but the net-cost survival + OOS-robustness + diversification make it the **single best honest lead** to watch into the gate.
- If, at n≥150, the net CI-LB still sits at ~0.95–1.10, it is a real-but-sub-bar edge (keep shadow, do not size). If it crosses 1.15, it is the **first genuinely-honest money-ready candidate** the project has produced.

## Reproduce
Import `tools/stamp_entry_conditions.py` (`fetch_cohort`/`fetch_bars`/`features`), filter `_cls=='CRYPTO' ∧ F3=='50-70' ∧ F5=='US'`, take `intrabar_pnl_pct`, cluster by (symbol, day), `tools/pf_ci_lower.py` with `net = pnl_pct − 0.16`. DB via `tools/db_env.get_stocks_creds()`.
