# `/audit` asset-class ledgers — source trace + per-class reconciliation

**Date:** 2026-11-18 · **Author:** buffy (Freebuff)
**Payload inspected:** `https://findtorontoevents.ca/audit/data/dashboard_data.json`
(HTTP 200, 25.5 MB, `generated_at 2026-11-18T01:15:43Z`)
**Local cross-check:** `audit_dashboard/data/pf_registry.json` (16.7 MB, mtime 2026-11-18 00:27)

## 1. The two ledgers, traced

Both numbers ship **in the same payload, from the same generator, one timestamp
apart** — but they are computed from **different sources**.

### Ledger A — `performance.by_asset_class` (the headline)

`audit_trail/dashboard_generator.py`

| Line | What |
|---|---|
| 15343 | `ac_breakdown = {}` — the accumulator |
| ~15540-15565 | loop over closed picks: `pnl = deduct_slippage(float(p.get("pnl_pct")))`, then `wins/losses/flat`, `win_pnl/loss_pnl`, plus `ac_sym_pnl` / `ac_strat_pnl` for the concentration block |
| 15560-15600 | finalize: `win_rate`, `avg_win`, `avg_loss`, `profit_factor`, `expectancy` |
| 17119 | `"by_asset_class": ac_breakdown` in the `performance` object |

**Source:** the in-memory `resolved_closed` + `final_active_picks` lists the
generator already holds for this run (the JSON pick feeds / universal resolved
picks it loaded). Not a database query of its own.

**Policy applied here:** `deduct_slippage()`, `COMMODITY_BLACKLIST` /
`ETF_BLACKLIST` symbol exclusion (`COMMODITY_SUBCLASS_KILL_DISABLED`,
`ETF_IWM_GLD_KILL_DISABLED` rollbacks), `PERMANENTLY_KILLED_STRATEGIES`
exclusion (`KILLED_STRATEGY_AGG_EXCLUDE_DISABLED` rollback), and
`_dedup_cot_over_emission()` for `COT_DEDUP_SYSTEMS`.

### Ledger B — `readiness.by_class` (the sizing gate)

| Line | What |
|---|---|
| 17167 | `"readiness": _build_readiness_payload(asset_class_health, now)` |
| 6343 | `def _build_readiness_payload(...)` — derives `gate_state`, `sample_tier`, `sizing_allowed`, `tier_vs_charter` |
| 15604 | `_registry_breakdown = _registry_backed_ac_breakdown()` |
| 15605-15608 | `asset_class_health = compute_asset_class_health(_registry_breakdown or ac_breakdown)` |
| 5970 | `compute_asset_class_health()` — `n = wins + losses`, tiers, `sizing_allowed` |
| 5880 | `_registry_backed_ac_breakdown()` — **reads `audit_dashboard/data/pf_registry.json`** |

**Source:** `audit_dashboard/data/pf_registry.json`, built by
`tools/build_pf_registry.py`. Its 16 MB of views are:

```
by_asset_class                      10 rows   (raw, all sources)
by_asset_class_policy_clean         10 rows
by_asset_class_policy_clean_net     10 rows   <-- readiness basis
by_asset_class_strategy_policy_clean_net  697 rows
by_asset_class_strategy             743
by_asset_class_strategy_symbol     2511
by_asset_class_strategy_date      24985
```

Each row carries `top_source` (e.g. `file:mysql:…`, `bond_duration_rotation`),
i.e. the registry is assembled from **MySQL `ejaguiar1_stocks`** (the
`trading_picks` ledger) plus file feeds — not from the generator's in-memory
list.

**Activation:** `_registry_backed_ac_breakdown()` is **on by default**
(`AUDIT_HEALTH_SOURCE` defaults to `"registry"` at line 5909 — flipped
2026-05-17 by M-067). It fails open to the recompute on: registry missing, no
`schema_version`, `source_files_canonical` false, registry older than the
closed-pick ledger mtime, or an empty net view. Locally the registry exists and
`schema_version = 1.1.0`, `source_files_canonical = true` — so **both paths are
live and both can be inspected**.

## 2. Per-class reconciliation diff

`closed` = Ledger A resolved rows; `n` = Ledger B (`wins + losses`).

| Class | A closed | A WR | A PF | B n | B WR | B PF | n ratio |
|---|---|---|---|---|---|---|---|
| CRYPTO | 5,031 | 40.3 | 0.91 | 22,379 | 41.6 | 0.26 | 4.4× |
| EQUITY | **12** | **66.7** | **10.16** | **476** | **38.7** | **0.62** | **40×** |
| FOREX | 102 | 21.6 | 0.42 | 433 | 35.3 | 0.31 | 4.2× |
| ETF | 12 | 25.0 | 0.53 | 25 | 52.0 | **1.65** | 2.1× |
| COMMODITY | 11 | 9.1 | 0.06 | 23 | 21.7 | 0.53 | 2.1× |
| BOND | 3 | 33.3 | 0.06 | 1 | 0.0 | 0.0 | 0.3× |
| FUTURES | 0 | — | None | 13 | 30.8 | 1.01 | — |

Against the registry file on disk (`by_asset_class_policy_clean_net`): CRYPTO
n=23,053 / PF 0.261, EQUITY 478 / 0.621, FOREX 434 / 0.312, ETF 25 / 1.646,
COMMODITY 23 / 0.528, BOND 1 / 0.0, FUTURES 13 / 1.009. The residual versus B
(22,379 vs 23,053) is a **snapshot-time gap** — the payload was generated at
01:15Z, the registry file on disk is from 00:27Z; CI rebuilds it hourly.

## 3. What the diff means

1. **The gap is a universe gap, not a math bug.** Non-crypto classes are nearly
   absent from Ledger A (EQUITY 12 closed, COMMODITY 11, BOND 3, FUTURES 0) while
   the MySQL-backed registry holds 476 / 23 / 1 / 13. The headline PF for EQUITY
   is 8 wins out of 12 trades; the gate's is 184 wins out of 478.
2. **EQUITY flips conclusion.** A says PF 10.16 / WR 66.7 / expectancy +0.97
   (looks like the best class on the board). B says PF 0.62 / WR 38.7 (below the
   1.0 no-sizing floor). This is the **exact failure mode M-067 was created to
   stop** — the 2026-05-17 comment at line 5905 records "the inflated
   recompute's PF 2.04 wrongly allowed" EQUITY; today the recompute reports
   **10.16**. The inflation is not only still present, it is 5× larger.
3. **ETF flips the other way.** A says PF 0.53 (a losing class); B says 1.65 —
   the only class above the 1.25 bar. Whichever ledger you read, you reach the
   opposite conclusion about the one class that might have an edge.
4. **Neither ledger is "the truth" on its own.** A applies slippage + blacklist
   + COT dedup on a thin non-crypto set; B is policy-clean but is a different
   universe (MySQL ledger, net view) and includes classes A drops (MEME,
   PENNY_STOCK, CHEAP_STOCKS).
5. **Concentration undermines A even where A is flattering.** From
   `performance.asset_class_concentration`: EQUITY's `top_strategy` is 53.45% of
   class PnL on AAPL 54.01% of class PnL; CRYPTO's is 80.22%
   `luxalgo_confluence`. So "PF 10.16" is one strategy, one symbol, 12 trades.

## 4. Recommended canonicalisation (needs an owner call — not applied)

Pick one, then make both keys read it:

- **Option 1 (recommended): registry is canonical.** Point
  `performance.by_asset_class` at the same `_registry_backed_ac_breakdown()`
  result the gate uses, and keep the recompute only for the concentration block
  (which needs per-symbol/per-strategy mass). Result: headline and gate can
  never disagree, and the headline stops being computed on 12 trades.
- **Option 2: recompute is canonical.** Set `AUDIT_HEALTH_SOURCE=recompute` and
  accept that non-crypto classes are unmeasurable below ~50 resolved rows —
  i.e. EQUITY/COMMODITY/BOND/FUTURES report "insufficient data" instead of a PF.
- **Option 3: keep both, label both.** Ship
  `by_asset_class {basis: "recompute_in_memory"}` and
  `readiness {basis: "pf_registry_policy_clean_net"}` and render both in the
  dashboard with the basis string. Cheapest, but leaves the reader to reconcile.

Whichever is chosen, add a CI assertion that
`|A.pf − B.pf| < 0.35` per class or fail the dashboard build — a silent 10.16
vs 0.62 split is a *rendering* problem until someone sizes a trade off it.

## 5. Verification of this trace

- `grep -n "by_asset_class" audit_trail/dashboard_generator.py` → 17119 (emit),
  15606/15608 (health), 5880 (registry source), 5970 (tier logic).
- `grep -n "_registry_backed_ac_breakdown"` → 5880 def, 15604 call.
- `pf_registry.json` inspected directly: `schema_version 1.1.0`,
  `source_files_canonical true`, 7 asset-class views, class-level
  `policy_clean_net` numbers as quoted in §2.
- Live payload read over HTTPS at `2026-11-18T01:15:43Z`; both key paths parsed
  from the same response, so the divergence is not a stale-copy artefact.
- The **local** `audit_dashboard/data/dashboard_data.json` is from **2026-10-23**
  and must not be used for this comparison — it is the stale build output, while
  the deployed file is CI-generated.
