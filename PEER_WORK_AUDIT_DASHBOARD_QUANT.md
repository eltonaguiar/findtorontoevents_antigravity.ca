# Peer work log — Unified Audit Dashboard quant / data-quality initiative

**Updated:** 2026-04-04 UTC  
**Agent:** Cursor (implementing plan `audit_dashboard_quant_review` — do not edit the plan file in `.cursor/plans/`)

## Purpose (tell other peers)

Multiple agents touch `audit_trail/`, `audit_dashboard/`, and live `/audit/`. This file is the **single detailed status** for the **quant-style audit** workstream: crypto vs non-crypto performance, Smart Picks, Verified Alpha, PnL sanity, magnifying-glass drill-down consistency, and market validation.

**Shorthand for CHATWITHIT:** see bottom of this file for one-line summary.

## Redis agent bus (`localhost:6379`)

- **Agent ID:** `cursor-audit-quant` (Cursor). Status key: `agent:cursor-audit-quant:status` (TTL 3600s); refresh when task changes.
- **Handy:** `python tools/redis_agent_handshake.py` — sets status, lists peers, drains inbox, shows last broadcasts, posts an “online” message to `bus:broadcast:log`.
- **15m traction:** `python tools/redis_bus_tick.py --interval-sec 900` (single tick: omit flag). Drains `agent:cursor-audit-quant:inbox`, logs broadcasts, posts heartbeat.
- **Shared files:** acquire `SET lock:file:<path> <agent_id> NX EX 300` before editing `dashboard_generator.py` / `audit_dashboard/template.html`; `DEL` after commit.

---

## Scope (what I am working on)

1. **Playwright + data parse** — Load `https://findtorontoevents.ca/audit/`, attach `pageerror` / `console` listeners, evaluate `window.DASHBOARD_DATA` to count PnL anomalies (null, zero, outliers), and reconcile asset-class splits with server logic.
2. **Non-crypto classification** — Align `compute_non_crypto_performance._category_for_pick` in [`audit_trail/dashboard_generator.py`](audit_trail/dashboard_generator.py) with client-side `matchCategory` in [`audit_dashboard/template.html`](audit_dashboard/template.html) (e.g. `=X` forex, `XAU`/`XAG` commodities) so **card totals** and **drill-down filters** describe the same population.
3. **Magnifying glass / drill-down** — Fix unrealized PnL field precedence in `showNcDrillDown` to match the card (`unrealized_pnl_pct`, `_livePnl`, then fallback). Optionally extend server payload so modal aggregates are not silently computed on an arbitrary `recent_closed` cap when cards use full `resolved_closed`.
4. **Market validation sample** — Stratified spot-checks: Binance (or mirror chain) for crypto, Yahoo/Stooq-style feeds where the repo already has helpers (e.g. [`audit_trail/fetch_stock_prices.py`](audit_trail/fetch_stock_prices.py)), recomputing PnL from entry/direction/exit and flagging &gt;20% error or wrong sign.
5. **Verified Alpha audit** — Trace `_is_verified_alpha_pick` / `_extract_verified_alpha_audit` usage; ensure displayed VA rows carry auditable metadata (which gate qualified the pick).
6. **Quant memo** — Short institutional-style note: per-asset-class edge, data gaps (MySQL vs JSON, generator vs template), alignment with [`audit_dashboard/WORLD_CLASS_ROADMAP.md`](audit_dashboard/WORLD_CLASS_ROADMAP.md).

## Coordination with related peer work

- **[`PEER_STATUS_NONCRYPTO_FIX.md`](PEER_STATUS_NONCRYPTO_FIX.md)** — Documents per-category `recent_closed` reservation and post-gate recomputation of `non_crypto_performance`. My classification + drill-down fixes **stack on top** of that; avoid reverting quota logic in `_build_recent_closed_picks`.
- **Generator vs template** — Per [`CLAUDE.md`](CLAUDE.md): prefer editing [`audit_dashboard/template.html`](audit_dashboard/template.html) for UI/JS; `index.html` is generated. Do not run dashboard generators locally if policy says they overwrite live HTML; use CI or `py_compile` for sanity checks as appropriate.
- **Merge hotspots** — `audit_trail/dashboard_generator.py` (payload, `compute_non_crypto_performance`, closed-pick reservation), `audit_dashboard/template.html` (Non-Crypto panel + modal). Ping in this file if you are editing the same regions.

## Files I expect to touch (others: beware conflicts)

| Area | Files |
|------|--------|
| Server metrics / NC buckets | `audit_trail/dashboard_generator.py` |
| Drill-down UI | `audit_dashboard/template.html` |
| Automated audit | New or existing test under `tests/` / `tools/` (Playwright or Node) |
| Documentation | This file; optional `audit_dashboard/` memo if user asks |
| Integration reference | [`CHATWITHIT.MD`](CHATWITHIT.MD) (pointer only) |

## Risks / known landmines

- **Headline dashboard stats** aggregate many experimental systems; weak global PnL does not necessarily invalidate gated subsets (Smart Picks, Verified Alpha).
- **±500% PnL cap** in aggregation masks absurd raw rows; validation must still **log source rows** for debugging bad entry prices.
- **Mirror deduplication** on closed picks can hide duplicates; do not assume `len(recent_closed)` equals economic trade count.

## How to message me (human / next agent)

Update this file with your name, timestamp, and bullet “Conflicts / requests” if you need coordination. Keep [`CHATWITHIT.MD`](CHATWITHIT.MD) to a **link + one paragraph**; put detail here.

---

## One-line summary for CHATWITHIT

*Implementing audit-dashboard quant plan: NC bucket parity server/UI, drill-down PnL field alignment, Playwright DASHBOARD_DATA audit, sampled market PnL checks, Verified Alpha traceability — see `PEER_WORK_AUDIT_DASHBOARD_QUANT.md`.*
