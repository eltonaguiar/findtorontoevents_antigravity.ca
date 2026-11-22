# Part 3 · P3-2: Backtest-vs-Forward Decay (the 0-forward blocker)

**Author:** GitHub Copilot / Mercury-3 AI (`githubcopilot-mercury3AI`)
**Date:** 2026-11-22 04:00 EST
**Source:** `dashboard_data.json` `backtest_vs_forward`, `hf_decay_watchlist`, `fwd_vs_bt_divergence`

---

## 1. The headline

**Every strategy in the backtest-vs-forward table has `fwd_trades = 0`.** The decay/divergence watchlists (`hf_decay_watchlist`, `fwd_vs_bt_divergence`) are **empty** because their minimum is n_fwd≥20, and no backtest strategy has a single forward trade linked to it.

---

## 2. Why nothing can be decay-measured

The table pairs backtest strategies with their forward trades to compute decay (BT vs FWD WR/Sharpe). With `fwd_trades = 0` everywhere:

- **Decay cannot be computed** — there is no forward leg.
- **`hf_decay_watchlist` stays empty** (needs FWD n≥20).
- **`fwd_vs_bt_divergence` stays empty** (needs FWD+BT n≥20).

This is the *same* orphan-H-119 problem as Part 2, seen from the backtest side: the forward rows exist (430, H-119) but are **not linked to any backtest strategy** in this table, so the decay clock never ticks.

---

## 3. Root cause chain

1. Forward rows exist only under H-119 (orphan) — `reports/forward_observations.jsonl`.
2. `backtest_vs_forward` links by `strategy`/`system` name, but H-119's rows carry no matching backtest strategy key.
3. ⇒ No strategy has forward trades ⇒ no decay, no divergence, no watchlist rows.

---

## 4. What this means

The system has **two disconnected forward loops**:
- The **tribunal forward gate** (audit3) — sees H-119 rows but can't attach them to a pod.
- The **backtest decay clock** (dashboard) — sees backtest strategies but can't attach any forward rows.

Both are starved by the **same missing link: H-119 is not registered as a strategy/pod.**

---

## 5. Fix (shared with P3-4)

1. Register H-119 as a strategy/pod (`POD-H119-FORWARD-ALPHA`), **and** map its 430 rows to a backtest strategy key so `backtest_vs_forward` can populate.
2. Then decay/divergence watchlists will populate as soon as n_fwd≥20.
3. Acceptance: `hf_decay_watchlist.rows` non-empty at next dashboard build.

---
*Not investment advice. Data: dashboard_data.json backtest_vs_forward.*
