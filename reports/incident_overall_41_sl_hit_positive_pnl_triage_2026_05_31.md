# INCIDENT_OVERALL #41 — SL_HIT positive-pnl triage (2026-05-31)

**Severity:** P3
**Status:** TRIAGED (was OPEN)
**Table:** `ejaguiar1_stocks.at_signal_outcomes`
**Reporter:** peer_claude / incidents enhancements scan
**Triaged-by:** peer_claude (incident41-sl-hit-triage, 2026-05-31)

## Original report

`at_signal_outcomes` `outcome='SL_HIT'` rows: 18,511 with `pnl_pct<0` (correct) + 5,852 (24%) with `pnl_pct>0` (contradictory — a stop-loss that made money should not exist).

## Live verification (2026-05-31)

```sql
SELECT source_system, COUNT(*) total,
       SUM(pnl_pct>0) pos, SUM(pnl_pct<0) neg, SUM(pnl_pct=0) zero, SUM(pnl_pct IS NULL) null_ct
FROM at_signal_outcomes WHERE outcome='SL_HIT' GROUP BY source_system ORDER BY total DESC;
```

| source_system | total | pos | neg | zero | null |
|---|---:|---:|---:|---:|---:|
| alpha_engine | 14,679 | **7** | 14,672 | 0 | 0 |
| ml_battleground_system_f_clawsofdoom | 5,846 | 0 | 0 | 0 | **5,846** |
| battleground | 2,268 | 0 | 2,268 | 0 | 0 |
| multi_asset_copytrader | 3 | 0 | 3 | 0 | 0 |
| opposite_day | 2 | 0 | 2 | 0 | 0 |
| ml_battleground_system_a_filter | 1 | 0 | 1 | 0 | 0 |
| **TOTAL** | **22,799** | **7** | **16,946** | 0 | **5,846** |

## Finding: the "5,852 positive-pnl SL_HITs" figure was a population conflation

The original counter blended two distinct fault modes:

### Fault A — NULL `pnl_pct` (5,846 rows, 25.6% of SL_HIT)

100% from `ml_battleground_system_f_clawsofdoom`. Spot-checked rows (e.g. id 2472 SOL LONG entry=87.36 SL=82.99 exit=82.82, id 2473 ETH LONG entry=2018.69 SL=1917.76 exit=1917.57) confirm that the `outcome='SL_HIT'` label is **correctly classified** — exit_price is at or below stop_loss for LONG, consistent with a stop hit. The engine simply never populates `pnl_pct`, `opened_at`, or `closed_at`. Same engine has 5,116 TP_HIT rows with NULL pnl_pct.

**This is a resolver-completeness bug**, not a sign-convention contradiction. It is incorrectly attributed to incident #41.

**Recommendation:** track as a separate incident (`ml_battleground_system_f_clawsofdoom never backfills pnl_pct / opened_at / closed_at` — affects ~10,962 rows across SL_HIT+TP_HIT). Out of scope for #41.

### Fault B — Genuinely contradictory rows (7 rows, 0.03% of SL_HIT)

All from `alpha_engine`. Per-row diagnosis:

| id | symbol | dir | entry | SL | exit_price | pnl_pct | strategy | fault mode |
|---|---|---|---:|---:|---:|---:|---|---|
| 658 | SHIBUSDT | LONG | 5.53e-6 | 5.26e-6 | **4100.97509561** | +0.0742 | vwap_rsi_confluence | sentinel exit_price (garbage value `4100.975…`) |
| 659 | SI=F | LONG | 75.275 | 73.77 | **657.39493163** | +0.0773 | commodity_tsmom_12m | sentinel exit_price |
| 13527 | EURUSD=X | LONG | 1.163 | 1.157 | **4100.97509561** | +0.3525 | combined_confidence | sentinel exit_price (same constant as #658) |
| 43877 | RIVN | SHORT | 14.700 | 14.553 | 14.553 | +0.0100 | regime_mild_bear | SHORT @ entry hit SL @ 14.553 — for a SHORT, exit<entry is profit; resolver wrote +pnl but labeled SL_HIT |
| 49374 | RIVN | SHORT | 14.700 | 14.553 | 14.553 | +0.0100 | regime_mild_bear | duplicate of 43877 (same row written twice) |
| 105614 | TXN | LONG | 305.680 | 287.24 | 305.93 | +0.0008 | smart_money_accumulation | exit ABOVE entry — should be TP_HIT or OPEN; mislabeled |
| 163495 | TXN | LONG | 305.680 | 287.24 | 305.93 | +0.0008 | smart_money_accumulation | duplicate of 105614 |

Three distinct micro-bugs:
1. **Sentinel exit_price** (3 rows): the constant `4100.97509561` and the related `657.39493163` look like an external-quote API returning the wrong asset (possibly an index value or a different symbol's price). The resolver should reject `exit_price` outside `[0.1 × entry, 10 × entry]` before computing pnl.
2. **SHORT sign-convention bug** (2 rows, both RIVN, both `regime_mild_bear`): for a SHORT, `pnl_pct = (entry - exit) / entry`. The resolver appears to be applying the LONG formula and producing a positive number for what should be a stop-loss exit. **However**, on a SHORT, hitting stop_loss = price went UP, so the trade lost money — the +0.0100 sign is wrong AND the label is correct. Net effect: label correct, pnl sign inverted. Likely in `alpha_engine/outcome_resolver.py` near `PNL_WIN_THRESHOLD_BY_CLASS` (line 115-126) — the direction branch is the suspect.
3. **LONG exit-above-entry mislabel** (2 rows, both TXN, both `smart_money_accumulation`): exit_price (305.93) is ABOVE entry (305.68), nowhere near stop_loss (287.24). This should be TP_HIT (or still OPEN). Resolver wrote SL_HIT despite exit > entry. Possibly: `smart_money_accumulation` emits unusual SL geometry, or the strategy converted to a different orientation mid-flight.

## Forward fixes (deferred to follow-up PRs, NOT in this triage)

1. **`alpha_engine/outcome_resolver.py`** — add band-check on `exit_price`:
   ```python
   if not (0.1 * entry_price <= exit_price <= 10 * entry_price):
       log.warning("exit_price out of band, marking outcome UNRESOLVED", ...)
       return None
   ```
   Catches the 3 sentinel rows (and prevents future ones).

2. **SHORT direction branch in `outcome_resolver.py`** — audit for `pnl_pct = (entry - exit) / entry` (correct) vs `(exit - entry) / entry` (LONG formula incorrectly used). The 2 RIVN rows suggest the SHORT branch was being applied wrong, but only specifically for the `regime_mild_bear` strategy — investigate strategy-level overrides.

3. **`smart_money_accumulation` SL_HIT logic** — investigate why TXN rows were labeled SL_HIT with exit above entry. Possibly a stale stop-loss snapshot from a prior bar.

4. **Historical re-label** (NOT done this PR; would need separate P3 ticket):
   - Rows 658, 659, 13527: `outcome='UNRESOLVED'`, NULL pnl_pct (sentinel exit_price unrecoverable)
   - Rows 43877, 49374, 105614, 163495: re-derive direction-aware pnl_pct from entry/exit, OR mark `outcome='UNRESOLVED'`

5. **Constraint deferral:** A `chk_sl_hit_pnl_sign` CHECK (`outcome <> 'SL_HIT' OR pnl_pct <= 0 OR pnl_pct IS NULL`) would prevent future violations but only 7 historical rows would violate; defer until those are repaired.

## Scope decision

Per session rules (≤2 files + DB row update), this PR is docs + INCIDENT_OVERALL status flip only. The 7 historical row repairs and the resolver hardening are tracked as follow-ups.

## Evidence references

- Live verification queries above (timestamp 2026-05-31, run against `mysql.50webs.com / ejaguiar1_stocks.at_signal_outcomes`)
- Resolver source: `alpha_engine/outcome_resolver.py:115-126` (`PNL_WIN_THRESHOLD_BY_CLASS`)
- Prior related fixes: `reports/action_B_resolver_2026_04_27.md`, `reports/feedback_noncrypto_resolver_live_close_bug.md`

## Status update

`UPDATE INCIDENT_OVERALL SET status='TRIAGED', resolution_notes=<this doc>, link_md_path='reports/incident_overall_41_sl_hit_positive_pnl_triage_2026_05_31.md' WHERE incident_id=41;`

Backup: `ejaguiar1_backups.INCIDENT_OVERALL_pre_incident41_triage_20260531`
