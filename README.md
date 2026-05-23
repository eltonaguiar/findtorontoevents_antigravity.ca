# findtorontoevents_antigravity.ca

Monorepo for **findtorontoevents.ca**, including the **live signal audit** at [findtorontoevents.ca/audit](https://findtorontoevents.ca/audit) (multi-asset picks, closed history, hygiene gates, and research tooling).

---

## What `/audit` is

A **read-mostly dashboard** fed by `audit_dashboard/data/dashboard_data.json`, regenerated on a schedule (see `.github/workflows/audit-dashboard.yml`). It aggregates:

- **Active picks** — merged from multiple `active_picks*.json` sources, then filtered by `alpha_engine/feed_hygiene.py` and **`audit_trail/quality_gates.py::passes_active_gate`** before display.
- **~3,500 recent closed picks** — used for WR/PF, tier trust, HC/Smart filters, and internal research scripts.

Canonical UI template for the audit surface: **`audit_dashboard/template.html`** (not root `index.html` — see `CLAUDE.md`).

---

## Asset-class methodology (summary)

| Class | Emission | Active visibility philosophy |
|-------|----------|------------------------------|
| **CRYPTO** | Highest volume (battleground, ML predictors, copy-trader, alpha_engine, …) | **Permissive** active display: catastrophic symbol tracks and large-sample **low forward WR** cohorts are hard-dropped; quality is mostly **sort order** (score), not hard-hide-all. Phase-1 **TOD / confidence dead-zone** gates default to **shadow** (tag, don’t reject) unless env tightened. |
| **EQUITY** | `multi_asset_copytrader`, `stocks_competition`, `ml_gatekeeper`, … | **Stricter** than crypto: trust floor, raw-score floor (unless exempt sources), **per-class forward WR floor** once `forward_trades >= 20` (see `active_non_crypto_forward_wr_floor()` in `quality_gates.py`). Smart Picks use **higher** score floors (`SMART_PICKS_MIN_SCORE_EQUITY`). |
| **FOREX** | Copy-trader + CTA paths | Trust + score; **Smart** layer adds forward WR ≥ 50% rule (score alone mis-ranks FX). |
| **COMMODITY / FUTURES** | CTA, multi-asset, cot | Similar to FOREX; commodity smart floor tuned for thinner booster coverage. |
| **ETF** | *Sparse upstream* — strategy library exists (`alpha_engine/etf_strategies.py`) | ETF **hard ban removed** (2026-04-19); visibility now limited mainly by **lack of emitted rows** + same non-crypto gates when rows exist. |
| **BOND** | *Sparse upstream* — `bond_strategies.py` + FRED helper `bond_data_fred.py` | Same as ETF: **supply gap** dominates; gates are secondary. |

**Feeds (tabs):** Verified Alpha, Smart Picks, High Conviction, etc., each map to JSON fields and/or `hc_filter.js` / `audit_trail/feed_membership.py` — see `docs/STRATEGY_FACTORY_V1_1_AMENDMENTS.md` and `docs/AUDIT_FULL_REVIEW_PACKAGE_2026_04_20.md`.

---

## Latest performance snapshot (how to refresh)

Numbers **stale immediately** after the next dashboard regen. To print **closed-book** tables from your local JSON:

```bash
.venv/Scripts/python.exe tools/audit_closed_quadrants.py
```

**Example output** (payload `generated_at` **2026-04-22T18:34:45Z**, `recent_closed` **n = 3500**):

| Slice | WR | Mean pnl% | PF |
|-------|-----|-----------|-----|
| CRYPTO last 10 | ~60% | ~+1.0 | ~3.2 |
| CRYPTO last 50 | ~68% | ~+1.1 | ~5.1 |
| CRYPTO **all** (~1650 rows) | ~38% | negative | ~0.9 |

**Interpretation:** short **recency** windows can look strong while the **long tail** still reflects retired toxic strategies — do not equate “green last 20” with “fixed pool.”

Full narrative + empty-class RCA: **`docs/ACTIVE_PICKS_ASSET_CLASS_DIAGNOSIS_2026_04_22.md`**.

---

## Key code paths

| Concern | Location |
|---------|----------|
| Active pick admission | `audit_trail/quality_gates.py` → `passes_active_gate` |
| Smart / HC tiers | `passes_smart_gate`, `audit_dashboard/hc_filter.js`, `audit_trail/feed_membership.py` |
| Ingest hygiene | `alpha_engine/feed_hygiene.py`, `alpha_engine/strategy_blocklist.py` |
| Payload build | `audit_trail/dashboard_generator.py` |
| Elite score floors (scanner) | `alpha_engine/config.py` → `MIN_ELITE_SCORE_BY_CLASS`, `min_elite_score_for()` |

---

## Developers / quant stack

- **Architecture:** [docs/ARCHITECTURE_OVERVIEW.md](docs/ARCHITECTURE_OVERVIEW.md)
- **Active vs emitter diagnosis:** [docs/ACTIVE_PICKS_ASSET_CLASS_DIAGNOSIS_2026_04_22.md](docs/ACTIVE_PICKS_ASSET_CLASS_DIAGNOSIS_2026_04_22.md)
- **Code review (trading systems):** [docs/CODE_REVIEW_QUANT_SYSTEM_2026-04-13.md](docs/CODE_REVIEW_QUANT_SYSTEM_2026-04-13.md)
- **Testing protocol:** [TESTING_PROTOCOL.MD](TESTING_PROTOCOL.MD)
- **Setup & pytest:** [docs/DEVELOPER_SETUP_QUANT.md](docs/DEVELOPER_SETUP_QUANT.md)
- **Data sources (copy / PM):** [docs/DATA_SOURCES_INTEGRATION.md](docs/DATA_SOURCES_INTEGRATION.md)

---

## Redirect note

`/findstocks/` root now **301 / meta-refresh** to `/audit/` while preserving subpaths like `findstocks/kimis_claw/` — see `findstocks/index.html` and `findstocks/.htaccess`.
