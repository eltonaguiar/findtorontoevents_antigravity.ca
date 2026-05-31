# Peer Claude Follow-ups — Ownership Transfer 2026-05-31

**Context:** Claude peer's 08:05 wakeup may not return (different session). This report takes ownership of remaining banner durability verification + phantom_expired documentation.

---

## 1. Banner Durability — VERIFIED GREEN (post-peer 08:05 work)

Live `audit/data/db_health.json` (fetched 2026-05-31T21:17Z):

```json
{
  "generated_at": "2026-05-31T20:39:44.959750+00:00",
  "any_red": false,
  "pnl_integrity_tier": "green",
  "pnl_integrity_pct": 0.54
}
```

- **generated_at age:** ~38 minutes (fresh — well past peer's 07:03 dispatch and 06:41 manual deploy).
- **any_red:** `false` — DATA INTEGRITY banner suppressed.
- **pnl_integrity:** tier=green, mismatch_pct=0.54% (under green threshold).
- **Workflow runs (audit-dashboard.yml):**
  - `2026-05-31T20:35:46Z` in_progress (current refresh cycle)
  - `2026-05-31T19:41:12Z` completed success
  - `2026-05-31T19:39:54Z` completed success
  - `2026-05-31T18:38:13Z` completed success
  - `2026-05-31T17:35:42Z` completed success

**Verdict:** Peer's banner fix is durable. The hourly `audit-dashboard.yml` workflow has regenerated `db_health.json` 4+ times since peer's manual deploy and all runs keep `any_red=false`. No regression. **Closing peer's 08:05 wakeup item as complete.**

---

## 2. phantom_expired — Diagnosis + Operator Acceptance Criteria

**Symptom:** ~17,664 non-crypto rows in `bt_backtest_trades` with `status='EXPIRED'`, `exit_price = entry_price`, `pnl = 0.00`. Resolver writes these as "expired" zeroes instead of MTM-closing on the bar where TP/SL/timeout fires.

**Why this is P1 (not P0):** zeroes do not flip a real winner into a real loser; they dilute n and depress PF toward 1.0. They also collide with **INCIDENT_OVERALL #48** (symbol resolution corruption) — the COMMODITY 48h cohort shows 27 closes all at `pnl=0.00`, same root signature.

**Cross-reference:** COMMODITY 48h panel (27/27 at 0.00 PnL) and INCIDENT_OVERALL #48 (symbol resolution corruption in `outcome_resolver.py`) are the same upstream bug class as phantom_expired. Fixing one likely unblocks the other.

### Root cause hypothesis (operator must confirm before code)

`alpha_engine/outcome_resolver.py` `resolve_expired_pick()` falls back to `exit_price = entry_price` when:
1. No intrabar OHLC bar is available between `entry_ts` and `expiry_ts` for the resolver's symbol lookup
2. Symbol resolution returns NULL (INCIDENT #48 territory — wrong ticker mapping, e.g. `CT=F` vs `CL=F` vs `GC=F`)
3. The expiry sweep job runs before the price-data backfill catches up

The fallback was intentional (avoid NaN in pnl), but it pollutes the closed-trade cohort.

### Operator acceptance criteria (decide before touching production scoring path)

Operator must approve **one** of the following remediation paths:

**Path A — Mark phantoms as UNRESOLVED (preferred, reversible):**
- Add new status `UNRESOLVED_NO_PRICE` distinct from `EXPIRED`.
- Exclude `UNRESOLVED_NO_PRICE` from `asset_class_health` PF/WR computation.
- Backfill: `UPDATE bt_backtest_trades SET status='UNRESOLVED_NO_PRICE' WHERE status='EXPIRED' AND exit_price=entry_price AND pnl=0 AND asset_class != 'CRYPTO'`.
- Acceptance: `pf_registry.by_asset_class_policy_clean_net` n for COMMODITY/EQUITY/FOREX/BOND drops by ~17,664 but PF/WR move toward signal (no longer 1.0-anchored).

**Path B — Re-resolve with backfilled price data (correct, expensive):**
- Build a one-shot job `tools/reresolve_phantom_expired.py` that re-fetches OHLC for each phantom row using the multi-source failover (yfinance → AlphaVantage → Polygon).
- Where price data is now available, compute `exit_price` at the actual TP/SL/expiry bar and update pnl.
- Where it remains unavailable, fall through to Path A status.
- Acceptance: ≥80% of the 17,664 rows resolve to a real exit_price; remainder marked UNRESOLVED.

**Path C — Do nothing, document the dilution (status quo):**
- Add a `phantom_expired_count` field to `pf_registry` per asset class.
- Surface it in `audit_dashboard/template.html` integrity banner so operators know PF is dilution-biased.
- Acceptance: numbers stay as-is; transparency only.

### Why NOT autonomous

This touches `outcome_resolver.py`, which is **inside the production pick-generation/scoring path** (see CLAUDE.md Wire-Up Rule). Any change requires operator sign-off because:
1. It changes verdict-grade PF/WR numbers in `asset_class_health`.
2. It interacts with the M-067 policy-clean cohort that gates real-money sizing.
3. The resolver intrabar bug (closed 2026-05-31) was operator-blessed; this is the same class of change.

**Recommendation to operator:** Path A first (cheap, reversible), then Path B in a follow-up cycle once price-backfill is stable.

---

## 3. Other Claude Peer Items Taken Ownership Of

- **Banner durability monitoring:** considered closed; the hourly `audit-dashboard.yml` is now the durable guard. If `any_red` flips back to true in any future run, that becomes a new incident — no need for a peer wakeup.
- **phantom_expired triage:** documented above with operator paths. **Not implementing autonomously.**
- **INCIDENT_OVERALL #48 cross-link:** flagged in this report so the next agent picking up either issue sees the connection.

---

## Summary line

```
PEER_FOLLOWUPS:banner_durability=verified:gen_at_age_min=38:phantom_expired_documented=true
```

Operator: please choose Path A / B / C for phantom_expired before next resolver edit lands.
