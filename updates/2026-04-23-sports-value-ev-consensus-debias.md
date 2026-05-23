# Value-bet EV: Jensen fix + leave-one-out + Pinnacle anchor

**Date:** 2026-04-23

## Problem

- **Jensen:** Old code used `1/mean(decimal_prices)` per outcome, then normalized — i.e. `1/E[price]`. Fair probability from multiple books should use `E[1/price]` (devig) then renormalize, not `1/E[price]`.
- **Self-referential consensus:** A book’s own price was included in the consensus used to test that book for +EV.
- **Equal weighting:** Pinnacle and long-tail books were averaged equally for “true” p.

## Changes (`live-monitor/api/sports_value_analyze_lib.php`)

1. **`sports_value_truep_consensus_jensen()`** — `mean(1/odds)` per outcome, optional **exclude one book** for leave-one-out. Returns normalized p-vector.

2. **`sports_value_truep_pinnacle()`** — If **every** outcome in the market has a usable Pinnacle line, de-vig using **only** Pinnacle inverses (sharp anchor).

3. **`sports_value_book_is_pinnacle()`** — Detects Pinnacle in `bookmaker_key`.

4. **Per-quote logic:**
   - If Pinnacle cover is available **and** the quote is **not** Pinnacle: use Pinnacle-anchored `truep[oi]` (soft line vs sharp fair).
   - Otherwise: `truep` = leave-one-out Jensen (exclude that book) when possible, else `truepBase`.

5. **Display `consensus_implied_prob` (`cq`)** — Mean of `1/price` over **usable** quotes only (aligns with devig input).

## Not in this change

- CLV / closing line column (separate schema + cron).
- Middles / arb scanner (sibling lib).
- Kelly cap, market-stratified `min_ev_pct`, line-move velocity, per-event exposure caps (future PRs).
- `tools/validate_php52.py` — not present in repo; this file already targeted PHP 5.2 (no `??` / `?:` in new code).

## How verified

- Manual read-through for PHP 5.2–safe syntax.
- Local `php -l` if PHP CLI is available in CI or dev.
