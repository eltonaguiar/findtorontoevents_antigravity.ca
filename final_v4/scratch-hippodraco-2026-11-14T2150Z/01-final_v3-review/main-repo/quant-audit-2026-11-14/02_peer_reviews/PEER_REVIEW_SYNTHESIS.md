# Peer Review Synthesis (final_v3, 2026-11-14)

**Peer packages reviewed:**
- `final_2026_11_14/childlike-airport/` (kilo's worktree)
- `final_2026_11_14/finpredict-v2/`
- `final_2026_11_14/finpredict-v3/`
- `final_v2/fix-p0-safe-fixes-2026-11-14-main/` (peer adjudication)

---

## Peer 1: childlike-airport (kilo)

**Profitable approaches claimed (all refuted or downgraded on re-execution):**

| Approach | Asset | Claimed Sharpe | Claimed PF | Re-execution Result |
|---|---|---|---|---|
| Regime-Filtered VWAP MR | Crypto 4h | 3.76 | 1.21 | **REFUTED** — Sharpe/PBO certification does not survive peer review; PBO 0.489 > strict 0.3; n=129 borderline |
| Vol-Targeted Trend | Crypto daily | 2.13 | 1.40 | **DOWNGRADED** — benchmark-relative candidate only; buy-and-hold Sharpe ~2.2 on same assets |
| Walk-Forward Variant C | Equity/ETF | — | 1.26 | **NOT PROOF** — null compares selection vs random; emissions cloned/repeated; costs not deducted |

**Data quality findings (critical):**
- 129/129 active picks ~172 days stale (local `live_picks.db` snapshot — must not generalize to all dashboards)
- 8 PnL sign contradictions (e.g., NEARUSDT shows −0.129 unrealized but correct is +0.129)
- 15 PnL calculation mismatches vs (cp−ep)/ep
- `audit_trail.db` completely empty (9 tables × 0 rows)
- **No MUTUAL_FUND class anywhere** — not in `asset_class.py`, gatekeeper, or any picker

---

## Peer 2: finpredict-v2

**Framework:** CI Gates G1-G13 for encoding data-contract invariants
**Consensus:** Adopt v2 reconciliation backbone; scratch QW-ALL-1..9 checklist; merge v1 master-plan after fixes; red-line ML-audit destructive SQL + mutual-fund stub scanner
**ETF cohort mismatch:** Official PF 0.022 vs registry PF 1.788 — discrepancy is a blocker, not evidence to choose favorable number
**Per-class roadmap:** CRYPCO daily 50/200 trend, EQUITY monthly QVM, ETF monthly tactical allocation, FOREX G10 carry basket, COMMODITY cross-market trend, FUTURES CTA trend, BOND duration trend, MUTUAL_FUND monthly NAV (keep NOT_BUILT)

---

## Peer 3: finpredict-v3

**Data hygiene:** 2 stale crypto prices pinned to entry, 11 frozen closed FOREX phantoms, 3 date-only seeds, null-price BOND/FUTURES classes, survivorship in headline stats
**Horizon validation:** 0/6 groups pass at n≥60, 0/26 at n≥30 — no strategy in recorded ledger is solidly profitable across time
**Harness bugs:** `MIN_WINDOWS=4` declared but never enforced; multiple-testing only reports counts (no BH/Bonferroni correction); windows split on gaps not fixed 60-day intervals; PnL not netted for costs; no valid `resolution_method` required (missing on all 3,500 rows)
**Remediation:** Flipped leakage-masking default to ON in `ml_gatekeeper/gatekeeper.py` (commit `d8c8dd25581` on `origin/main`)

---

## Peer 4: fix-p0-safe-fixes (peer adjudication)

**Key adjudications:**
- **VWAP refuted:** "The package calls VWAP mean reversion 'VALIDATED' and recommends deploying it. Later independent reviews refute the Sharpe/PBO certification."
- **Quant-audit 0/166 caveat:** Multi-source gate makes single-strategy cells mechanically fail; "the 0/166 count overstates that particular gate's evidence"
- **Horizon harness not release-grade:** `MIN_WINDOWS=4` not enforced; no multiple-testing correction; windows split on gaps; PnL not netted for costs
- **deepAI Variant C:** "The null compares selection against random selection, emissions are cloned/repeated, costs were not deducted"
- **ITERATION-005 trend:** "Reclassify 'PROVEN' to risk-premium candidate / benchmark-relative alpha unproven"
- **mega_mutation:** "Synthetic/replay rows in the forward cohort, selection from a very large search, claimed backtest rows that do not reproduce, TP hits not confirmed by price path"

**Overall peer decision:** "Accept the converged negative verdict. Retain the risk-premium hypotheses for pre-registered research only. Reject any 'deploy now' instruction for VWAP, mega_mutation, or funding carry."

---

## Cross-Peer Consensus (9 peers)

| Finding | Consensus |
|---|---|
| NOT money-ready | ✅ All agree |
| Data pipeline broken | ✅ All agree |
| EXPIRED→WON mislabeling | ✅ All agree |
| Single-source concentration | ✅ All agree (all 166 cells single-source) |
| PnL-unit contract = #1 fix | ✅ All agree |
| Zombie drain = #2 fix | ✅ All agree |
| Backtest↔forward disconnect | ✅ All agree (0 rows have both bt_trades>0 and fwd_trades>0) |
| VWAP not validated | ✅ All agree (after re-execution) |
| Multiple testing not corrected | ✅ All agree |

**Tension resolved:** Peers find profitable approaches in backtest research (kilo's VWAP MR Sharpe 3.76), but live-ledger screener finds 0/166 cells passing. Reconciliation: research harnesses ≠ live ledger. No validated approach has been deployed into `recent_closed_array.json`.
