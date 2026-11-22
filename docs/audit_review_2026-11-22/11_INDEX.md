# 11 INDEX

Central question: is INDEX a class at all, or a futures alias that double-counts?

## 1 Identity
[SRC: alpha_engine/money_ready_verdict.py:255] Not one of the canonical classes.
[SRC: _raw/audit_data_dashboard_data.json] It does not appear as a class on `/audit` this pass.
[SRC: _raw/audit3_audit3_ledger.json] It has no bucket in the ledger.
Inclusion is justified only as a probe, because the program asked whether it is a real class.

## 2 What the class is
Index exposure is usually index futures (ES, NQ) or index ETFs (SPY, QQQ).
[SRC: _raw/audit3_audit3_ledger.json] In this repo, SPY, QQQ, IWM, XLK, XLE, GLD, XLF, SOXX and ARKK are all filed under ETF, so INDEX has no instrument of its own.

## 3 Measured state
[SRC: _raw/audit_data_dashboard_data.json] `/audit` class verdict: absent.
[SRC: _raw/audit2_audit2.js:154] `/audit2` inherits the ledger, so absent too.
[SRC: _raw/audit3_audit3_ledger.json] `/audit3` has zero INDEX cells; verdict UNMEASURED.

## 4 Contradictions
The contradiction is structural: the program lists INDEX as one of the classes, but index products are counted under ETF and index futures under FUTURES/COMMODITY. Adding INDEX as a separate bucket without moving the instruments would double-count SPY.

## 5 Data integrity
[SRC: _raw/audit3_audit3_ledger.json] Zero rows under the name INDEX. Any number attributed to INDEX today would be borrowed from ETF or FUTURES rows and would not be INDEX's.

## 6 Cost reality
UNMEASURED: no INDEX trades.
[SRC: _raw/audit3_audit3_ledger.json] Index ETFs are already costed at 0.05 pct under ETF.

## 7 What would change the verdict
[SRC: _raw/audit3_audit3_ledger.json] One experiment: define INDEX as ETF rows whose underlying is a broad index (SPY, QQQ, IWM, DIA) and re-bucket without copying, then compare to ETF. Gate: no symbol appears in two buckets. Falsifier: if re-bucketing leaves ETF unchanged except for those symbols, INDEX is an alias.

## 8 Blunt answer
UNMEASURED as a class; on present evidence it is an alias, not a class, and should not be counted separately.

Least survivable number: there is no INDEX number at all [SRC: _raw/audit3_audit3_ledger.json]. The least survivable claim is that INDEX is a class: any re-bucketing test will show SPY already lives under ETF.

## 9 Cross-check against /audit and the database
[SRC: _raw/audit_data_money_ready_verdict.json] INDEX does not appear in `/audit`'s classes at all, and `/audit3` has no INDEX class bucket, so the canonical taxonomy does not recognise it as a class.
[SRC: reports/class_metric_reconciliation_20261122.md] The live `trading_picks` table does have 25 INDEX rows with gross PF 0.392, so data exists under a name the verdict surfaces do not score. INDEX is effectively an alias that leaks rows out of the denominator.
[SRC: _raw/audit3_audit3_ledger.json] INDEX is absent from `slippage_pct_by_class`, so even if it were scored there is no cost model for it.

## Provenance
- model: none (drafter fan-out blocked, see BLOCKERS.md B1; written by the curator from frozen evidence)
- prompt: none
- snapshot: `/audit3/audit3_ledger.json` 88606e1e… generated 2026-11-22T06:35:41Z
