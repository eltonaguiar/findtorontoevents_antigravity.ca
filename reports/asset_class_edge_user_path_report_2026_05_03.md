# Asset-Class Edge And User Path Report — 2026-05-03

Goal prioritized: **#1 — phenomenal performance across asset classes on `/audit`**.

## Question

If a real-money user goes to `findtorontoevents.ca/audit`, where should they go to find actual edge while minimizing risk? Is the edge in `Active Picks`, `Smart Picks`, `Verified Alpha`, `High Conviction`, or somewhere else?

## Dashboard User Path

The dashboard exposes these relevant paths:

- Header link: `Jump to Active Picks`, which switches to the `Active Picks` tab.
- Main tabs: `Active Picks`, `Verified Alpha`, `Smart Picks`, `US Equity Picks`, `Closed Picks`, `Performance`, `ML Health`, etc.
- Active Picks toolbar buttons: `Best Score`, `Proven Only`, `In Profit`, `SMART PICKS`, `Verified Alpha`, and `HIGH CONVICTION`.
- Guide popup: `? Guide` inside the Crypto + Non-Crypto Performance section.

## Current Payload Reality

Source: `audit_dashboard/data/dashboard_data.json`, generated `2026-05-04T02:21:53.631237+00:00`.

- Total live active picks in payload: `77`.
- Active pick asset mix: `CRYPTO 38`, `EQUITY 29`, `FOREX 6`, `ETF 4`.
- `smart_picks_feed.picks`: `4`, all `CRYPTO`.
- Active rows with `is_smart_pick` / `at_issue_is_smart_pick`: `0`.
- Active rows with `is_verified_alpha` / `at_issue_is_verified_alpha`: `0`.
- Active rows with `hc_tier` / `at_issue_hc_tier`: `0`.
- Active rows with trust tier `PROVEN` / `DEVELOPING`: `0`; active rows are `WATCH 63`, `RELIABLE 14`.
- `verified_alpha` summary exists, but current per-pick active flags are not stamped.
- Backend Verified Alpha allow-list in `audit_trail/feed_membership.py` is intentionally narrow: only `claws_of_doom`.

## Where The User Should Go Today

### 1. Best First Stop: `Performance` / `? Guide`, then `Active Picks`

The safest current workflow is not a single magic tab. A real-money user should first read the `? Guide` in the performance section, then use `Active Picks` with conservative filters.

Why: the Guide contains the most explicit closed-book edge notes, including:

- Crypto confidence `0.85-0.90` was historically strongest.
- Proven ML strategies were historically strong.
- R:R behavior is asset-specific and currently contradictory in places.
- Non-crypto edges are thinner and need smaller sizing.

### 2. In `Active Picks`, Use Filters Conservatively

The current active rows do not have stamped Smart Pick / Verified Alpha / HC flags. Therefore:

- `HIGH CONVICTION` button is the intended recommended path, but the current payload does not show stamped HC tiers. Treat it as a live UI filter that needs parity verification, not as a settled empirical edge.
- `SMART PICKS` button is a live overlay against `smart_picks_feed`; it currently contains 4 crypto picks only. Use it as a short list, not as proof of closed-book edge.
- `Verified Alpha` should be treated cautiously until the active per-pick flags and source allow-list produce real rows.
- `In Profit` is useful for risk triage but is not predictive edge by itself.
- `Proven Only` title explicitly says it uses a manual trust registry and does not run a live closed-pick query.

### 3. Practical Current Real-Money Path

For minimal risk today:

1. Go to `/audit`.
2. Open `? Guide` in the Crypto + Non-Crypto Performance section.
3. Click `Active Picks`.
4. Prefer `Asset = CRYPTO` only if the pick also meets high-quality conditions from the Guide: proven/ML-enhanced source, confidence in the empirically favorable band, no conflict, reasonable R:R, positive or stable live PnL, and fresh age.
5. For non-crypto picks, size smaller or wait for stronger proof. Equity is promising at the asset-class level, but current active rows are not clearly stamped as edge.
6. Avoid treating `Verified Alpha`, `High Conviction`, or `Smart Picks` labels as settled proof until the stamp/closed-book contract is fixed.

## Asset-Class Performance Diagnosis

### EQUITY — Promising, Not Yet Clean Scale

- Asset health: `WR 53.0%`, `PF 1.42`, `PnL +272.46%`, status `stable`.
- Walk-forward: `47` folds, `oos_sharpe 3.527`, `std 9.164`, `oos_wr 57.9%`, `worst_fold_wr 20.0`.
- Active picks: `29`.

Edge verdict: there is a real signal, but it is noisy and below formal T2 PF `>1.5`. Equity should be `watch / selective allocation`, not blanket scale.

User path: `Performance` to inspect walk-forward and asset health, then `Active Picks` filtered to `EQUITY`, sorted by score/confidence, manually checking source and R:R. Do not rely on UEPS yet: its own UI says it is building track record.

### ETF — Thin, Noisy Promise

- Asset health: `WR 55.2%`, `PF 1.24`, `PnL +23.55%`, status `stable`.
- Walk-forward: `12` folds, `oos_sharpe 6.368`, `std 16.882`, `oos_wr 61.7%`, `worst_fold_wr 20.0`.
- Active picks: `4`.

Edge verdict: ETF is promising but too thin/noisy for real-money confidence. The fold count is below the charter floor.

User path: watch only. Do not size up from ETF until `n>=100` closed or a robust DSR/PSR result clears.

### COMMODITY — Conflicted

- Asset health: `WR 46.9%`, `PF 1.78`, `PnL +167.19%`, status `stable`.
- Walk-forward: `130` folds, `oos_sharpe -2.412`, `std 9.396`, `oos_wr 43.2%`, `worst_fold_wr 0.0`.
- Active picks: `0` in current active payload.

Edge verdict: asset-health PF is strong, but walk-forward is negative. This is not allocation-ready until source/regime attribution explains the divergence.

User path: no live action from current active picks. Use `Performance` and `Closed Picks` for diagnostics only.

### CRYPTO — Broad Book Weak, Subsets May Have Edge

- Asset health: `WR 44.5%`, `PF 1.24`, `PnL +2067.3%`, status `watch`.
- Walk-forward: `302` folds, `oos_sharpe -0.088`, `std 11.334`, `oos_wr 43.3%`, `worst_fold_wr 0.0`.
- Active picks: `38`.
- Smart feed: `4`, all crypto.

Edge verdict: crypto aggregate is not institutional-grade, but the Guide claims specific subsets have historical edge. Real-money use should be subset-only, not broad crypto.

User path: `Smart Picks` and `Active Picks` can help shortlist, but only when combined with Guide constraints: ML/proven source, favorable confidence band, no conflicts, tight risk, and R:R consistency. Avoid broad `CRYPTO` exposure.

### FOREX — Rescue / Avoid For Now

- Asset health: `WR 46.3%`, `PF 0.27`, `PnL -986.54%`, status `stressed`.
- Walk-forward: `177` folds, `oos_sharpe -1.406`, `std 29.947`, `oos_wr 47.5%`, `worst_fold_wr 0.0`.
- Active picks: `6`.

Edge verdict: no current real-money edge. FOREX needs feed/resolver diagnostics and mutation-before-kill before any allocation.

User path: avoid live FOREX picks for now. Use only for diagnostics or paper trading.

### BOND / FUTURES / UNKNOWN / SPORTS

These are not currently investable from the dashboard:

- BOND: thin sample, no current active payload rows.
- FUTURES / SPORTS: insufficient data.
- UNKNOWN: insufficient data and resolver threshold policy risk.

## Main UX Integrity Gaps

1. The UI suggests `High Conviction`, `Smart Picks`, and `Verified Alpha` are the answer, but current active rows do not carry those stamps.
2. `Smart Picks` feed is only 4 crypto rows, so it cannot answer cross-asset allocation.
3. `Verified Alpha` backend is intentionally narrow and does not currently produce active per-pick flags.
4. `US Equity Picks` is still a building track-record product, not an investable proof path.
5. The strongest evidence is split between `Performance`/Guide/closed-book notes and `Active Picks`, requiring manual user synthesis.

## Bottom Line

If investing real money today, the only defensible path is **selective crypto and selective equity**, sized conservatively, using `Performance`/`? Guide` evidence first and `Active Picks` only as a live shortlist. Avoid FOREX; do not treat ETF, Commodity, BOND, UEPS, Verified Alpha, or High Conviction as fully allocation-ready until the contracts and validation gaps are fixed.
