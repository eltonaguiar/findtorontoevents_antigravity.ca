# Forward Paper-Pilot — Framework + luxalgo_confluence Verdict (2026-06-09)

**Author:** claude-opus-4-8 (M3) · **Status:** REFUTED for `luxalgo_confluence` · **Framework:** ready for re-use

---

## TL;DR

`tools/forward_paper_pilot.py` is the missing layer between "passes the clean-cohort historical bar" and "safe to size up". Any strategy that survives `n≥30 / ≥3mo / PF>1.5 / WR>52%` on the clean `at_pick_outcomes` cohort **MUST** be run through this pilot before any production promotion. Pilot on `luxalgo_confluence` (the only clean-cohort Tier-2 survivor on 2026-06-09) returned **REFUTED** — the historical edge did not generalize to forward data.

---

## Why this exists

The 2026-06-06 → 2026-06-09 audits converged on a measurement-honesty fix kit: backfill quarantine, per-class sane-pnl guard, EXPIRED-honest WR, intrabar re-resolution. The "T2 passes" verdict still relies on **historical** rows. Historical-clean ≠ forward-clean. The pilot fills the gap.

---

## The framework — `tools/forward_paper_pilot.py`

Read-only. Replays each `trading_picks` row of a given strategy on `crypto_ohlcv` (1h bars) from its `created_at` forward up to `--max-hold-bars` (default 168 = 7d). Restricted to picks created in the last `--lookback-days` (default 28 = 4w). Outputs `reports/forward_paper_pilot_<strategy>_<UTC>.json`.

**Replay rule** (intrabar first-touch, conservative):
- Long:  `sl_hit = bar.low ≤ sl`;  `tp_hit = bar.high ≥ tp`  → SL wins on a same-bar conflict
- Short: `sl_hit = bar.high ≥ sl`; `tp_hit = bar.low ≤ tp`    → SL wins on a same-bar conflict
- Neither hit in window: `TIME_EXIT` at last bar's close

**Verdict:**
- `HOLDS` if n≥20, true_WR≥50, true_PF>1.5
- `INSUFFICIENT` if n<20
- `REFUTED` otherwise

**Reproducer** (after the next clean-cohort survivor appears):

```bash
python3 tools/forward_paper_pilot.py \
    --strategy <name> --asset-class CRYPTO \
    --lookback-days 28 --max-hold-bars 168
```

---

## luxalgo_confluence — case study

**Historical clean-cohort (2026-06-09):** n=87, WR 69.0%, PF 5.38, 3mo — the ONLY strategy that passed the Tier-2 bar.

**Forward pilot (28d window, 2026-06-09):**
- 955 picks loaded, 953 replayed (2 no_data)
- true WR **42.4%**, true PF **1.144**
- 0 same-bar conflicts (no TP→SL reclassifications)
- Verdict: **REFUTED**

**Interpretation:** the clean-cohort edge (87 rows, 3mo) was a small-clean-subset artifact. The forward 953 picks collapsed to a coin-flip. luxalgo_confluence is **not** money-ready; future references to it should be marked REFUTED.

Report: `reports/forward_paper_pilot_luxalgo_confluence_20260609T041237Z.json`

---

## Reusability rule (codify for future agents)

> **No strategy may be promoted to a paper-trading pilot or live sizing without first passing `tools/forward_paper_pilot.py` on at least one forward window (default 28d / 168-bar horizon).** The clean-cohort historical bar (`build_pf_registry.py` / `money_ready_verdict.json`) is necessary but **not sufficient**.

Add this rule to:
- `.claude/skills/money-maker-ready/SKILL.md` (under "Operating Rules")
- `.claude/skills/money-maker-readyv2/SKILL.md` (under "Success Criteria")
- `obsidian-notes/reference/edge-rescue-roadmap.md` (under SAVE-3)

---

## Related

- `tools/reresolve_intrabar.py` — the intrabar-true **historical** re-resolver (de-biased fixed horizon, ~39.7% CRYPTO true WR)
- `tools/_check_t2_candidates.py` — clean-cohort cross-checker for candidate strategies
- `reports/EDGE_RESCUE_PLAN_2026-06-09.md` — the SAVE-1..5 plan (this pilot is a hard prerequisite for SAVE-3)
- `reports/forward_paper_pilot_luxalgo_confluence_20260609T041237Z.json` — the verdict data
- `updates/2026-06-08-db-ghost-rows-and-freshness.md` — earlier measurement-integrity fix

---

## EXPLORATORY forward-pilot on 60-90d window (2026-06-09)

User asked: does any forward signal emerge if we widen the lookback (60-90d) AND the pool (clean-cohort n≥15, even if months<3)?

### Wider clean-cohort pool (n=16 CRYPTO strategies, n≥15, no months floor)

| Strategy | n | wr% | pf | mo | Note |
|---|---|---|---|---|---|
| `unknown` | 305 | 40.0 | 1.31 | 2 | sub-50% WR |
| `hs_lb_None` | 261 | 50.6 | 3.26 | 2 | boundary |
| `(empty)` | 250 | 39.2 | 0.46 | 2 | low PF |
| `luxalgo_filters` | 115 | 23.5 | 0.50 | 1 | banned-strategy artifact |
| `luxalgo_confluence` | 87 | 69.0 | 5.38 | 3 | (28d pilot REFUTED) |
| `enhanced_ml_A_xgboost` | 58 | 20.7 | 0.41 | 1 | low WR |
| `signal_validation` | 35 | 68.6 | 3.85 | 1 | sub-T2 |
| `battleground_ml_relaxed_mut` | 31 | 71.0 | 4.35 | 1 | sub-T2 |
| `claude_ml_moderate_mut` | 31 | 61.3 | 2.74 | 1 | sub-T2 |
| `basket_corr_gate_mut` | 28 | 35.7 | 1.23 | 1 | low WR |
| `battleground_vwap_1h_mut` | 24 | 58.3 | 2.25 | 1 | sub-T2 |
| `MeanReversionBB` | 22 | 59.1 | 2.63 | 2 | sub-T2 |
| `hs_PensionFund_24M` | 18 | 55.6 | 8.25 | 2 | very small n, PF inflated |
| `GPX_Gen10_2a4b0b` | 16 | 12.5 | 1.61 | 1 | low WR |
| `clone_hl_copy_lb_None` | 15 | 40.0 | 2.21 | 1 | low WR |
| `evolutionary_regime_engine` | 15 | 53.3 | 2.11 | 1 | sub-T2 |

### 60d + 90d forward pilot (7 of the high-WR sub-T2 candidates)

| Strategy | days | n | true WR% | true PF | verdict |
|---|---|---|---|---|---|
| `signal_validation` | 60 | <20 | — | — | INSUFFICIENT |
| `signal_validation` | 90 | <20 | — | — | INSUFFICIENT |
| `battleground_ml_relaxed_mut` | 60 | <20 | — | — | INSUFFICIENT |
| `battleground_ml_relaxed_mut` | 90 | <20 | — | — | INSUFFICIENT |
| `claude_ml_moderate_mut` | 60 | n | 43.4 | <1 | REFUTED |
| `claude_ml_moderate_mut` | 90 | n | 39.3 | <1 | REFUTED |
| `battleground_vwap_1h_mut` | 60 | <20 | — | — | INSUFFICIENT |
| `battleground_vwap_1h_mut` | 90 | <20 | — | — | INSUFFICIENT |
| `MeanReversionBB` | 60 | <20 | — | — | INSUFFICIENT |
| `MeanReversionBB` | 90 | <20 | — | — | INSUFFICIENT |
| `evolutionary_regime_engine` | 60 | <20 | — | — | INSUFFICIENT |
| `evolutionary_regime_engine` | 90 | <20 | — | — | INSUFFICIENT |
| `luxalgo_confluence` (ref) | 60 | n | 41.4 | 1.122 | REFUTED |
| `luxalgo_confluence` (ref) | 90 | n | 39.8 | 1.085 | REFUTED |

### Verdict

**0/14 HOLDS. 4/14 REFUTED. 10/14 INSUFFICIENT.** Every sub-T2 candidate either failed on forward data (REFUTED) or didn’t have enough fresh picks in the 60-90d window to evaluate (INSUFFICIENT). **No forward signal emerges** from widening either the lookback (60-90d) or the survivor pool (n≥15 / months≥1). The 28d pilot finding (luxalgo_confluence REFUTED at 1.144 PF) holds at longer windows too — the historical clean-cohort edge is a small-clean-subset artifact, not a tradable signal.

Conclusion: with the current 180d OHLCV backfill + intrabar resolver + clean-cohort filters, **the system has no forward-validated edge in CRYPTO**. Same likely true in other classes once forward_paper_pilot.py is extended past CRYPTO (see Followups).

Reproducer:

```bash
python3 tools/_batch_pilot_wider.py   # 6-7 candidates x 60d/90d lookback
```
