# Copy-Trader Phantom PnL Audit — 2026-04-05

**Auditor:** claude-copytrader-phantom
**Triggered by:** antigrav-dash-integrity bus message 2026-04-04T19:26:32Z
**Existing fix under review:** commit `f1aaa40f4c` (100x entry/exit ratio threshold)
**Scope:** `copy_trader_intel/data/*.json` — scrubbing rules for phantom PnL

---

## 1. Context: The +500.29% Phantom Headline

The `antigrav-dash-integrity` peer flagged that the `copy_trader_intel`
system-stats row in the audit dashboard was rendering a `+500.29%` headline
PnL driven by 5 HYPEUSDT trades with:

- `entry_price = 0.050472` (airdrop/pre-market placeholder scale)
- `exit_price ≈ 39.90` (post-listing market price)
- per-trade `ratio ≈ 790x`
- each already `pnl_pct` capped at `+8.0`

The five trades — even with the per-trade +8% cap — contribute 5 × +8% = +40%
of aggregate PnL that is **entirely fictional** (the entry price is 790x off).
In the live dashboard aggregator, that +40% gets compounded/scaled further
into the +500.29% headline.

## 2. Summary of commit `f1aaa40f4c` (the existing fix)

Location: `audit_trail/dashboard_generator.py :: collect_system_stats()`

- Computes `ratio = max(entry,exit) / min(entry,exit)`.
- If `ratio > 100.0`, marks the pick with `_entry_corrupt=True`, bumps
  `excluded_closed`, and **skips the trade entirely** from metric
  aggregation.
- Separately emits `toxic_concentration` / `toxic_symbol` / `toxic_share_pct`
  when one symbol dominates >= 70% of `sum(|symbol_pnl|)` per system.

**Verdict:** the 100x threshold **does catch** the HYPEUSDT 790x phantoms
(confirmed by re-scan below). It is also strict enough to catch the
WLDUSDT 256,000x decimal-scale corruption referenced in the commit. It is,
however, a **single-layer defence** and will miss several other phantom
classes described in §5.

## 3. Per-File Phantom Counts (`copy_trader_intel/data/*`)

Scanned 122 JSON files in `copy_trader_intel/data`. Extracted every leaf
object containing both `entry_price` and `exit_price`. Counts at each ratio
threshold (phantom if `max(e,x)/min(e,x) > T`):

| File | >50x | >100x | >500x | >1000x |
|------|-----:|------:|------:|-------:|
| `closed_trades.json` | 5 | 5 | 5 | 0 |
| (all others) | 0 | 0 | 0 | 0 |
| **TOTAL** | **5** | **5** | **5** | **0** |

Note: checked files explicitly requested plus all others: `leaderboard.json`,
`multi_asset_picks.json`, `cta_picks.json`, `forex_copytrader_picks.json`,
`stocks_copytrader_picks.json`, `commodity_copytrader_picks.json`,
`variation_portfolios.json`, and the remainder. The phantoms are currently
concentrated in `closed_trades.json`.

### 3.1 All 5 phantom trades

| File | Symbol | entry | exit | ratio | pnl_pct (capped) |
|---|---|---|---|---|---|
| closed_trades.json | HYPEUSDT | 0.050472 | 40.094 | 794x | +8.0 |
| closed_trades.json | HYPEUSDT | 0.050472 | 39.971 | 792x | +8.0 |
| closed_trades.json | HYPEUSDT | 0.050472 | 39.898 | 790x | +8.0 |
| closed_trades.json | HYPEUSDT | 0.050472 | 39.658 | 786x | +8.0 |
| closed_trades.json | HYPEUSDT | 0.050472 | 39.386 | 780x | +8.0 |

All 5 show the identical entry price (`0.050472`) — a pre-listing/airdrop
placeholder. The `closed_trades.json` file contains 57 total closed trades
with `sum(pnl_pct) = 40.0` — meaning **every single +PnL point in that file
came from a HYPEUSDT phantom**. There are also 3 additional HYPEUSDT rows
with `entry=exit=39.91` and `pnl=None` (unclosed / flat).

### 3.2 Top phantom-producing symbols (>50x ratio)

| Rank | Symbol | Count |
|-----:|--------|------:|
| 1 | HYPEUSDT | 5 |
| 2–10 | *(none)* | 0 |

Only one symbol currently produces phantoms in copy_trader_intel. This is
**narrower than expected** — the known-airdrop watchlist (ENA, STRK, W, JUP,
WLD) does not currently appear with corrupted entry prices in these files,
though WLDUSDT historically surfaced in the system-stats aggregation (per
commit message of `f1aaa40f4c`).

## 4. Sibling observation: legitimate high-PnL ≠ phantom

For context, `okx_trade_history.json` and `eth_strategy_variations.json`
contain 49 trades with `|pnl_pct| > 100%` (several above +3000%). These are
leveraged-futures fills where entry/exit ratios are **under 2x** — they are
large PnL but the price scale is consistent. **The ratio rule correctly
leaves them alone.** A naive `|pnl_pct| > 200%` filter would destroy these.

## 5. Phantom Classes the 100x Ratio Rule Can Miss

| Class | Example | Caught by 100x? |
|---|---|---|
| Decimal-scale corruption | WLDUSDT 66937 → 0.26 | **Yes** (256,000x) |
| Airdrop pre-listing price | HYPEUSDT 0.050472 → 39.9 | **Yes** (790x) |
| Stock split 10:1 | NVDA 1200 → 120 | **No** (10x only) |
| Stock reverse-split 1:20 | small-cap 0.50 → 10 | **No** (20x) |
| Airdrop with closer price | PEPE-style 0.001 → 0.05 | **No** (50x) |
| Wrong-symbol leakage (BTC pasted into SHIB row) | 0.00003 → 68000 | **Yes** (>10⁹ x) |
| Leveraged futures with 200%+ PnL | real gain | **Correct no-flag** |
| Pump-and-dump legit 40x winner | microcap | **No** (legit) |

The 100x threshold is good for "obviously corrupt" but has a blind spot at
**3x–100x** where real splits, mergers, and airdrop mid-listings live.

## 6. Recommended Multi-Layer Scrubbing Rules

### Rule 1 — Asset-class tiered entry/exit ratio thresholds
| asset_class | ratio threshold | rationale |
|---|---|---|
| crypto (spot/futures) | **20x** | intraday moves rarely exceed 10x; 20x catches mid-airdrop |
| stocks | **5x** | splits typically ≤10:1 but those need a split-detection path (Rule 3) |
| forex | **3x** | FX pairs basically never move >3x |
| commodities | **5x** | |
| index_futures | **3x** | |

Flagged rows are **excluded from metric aggregation** but retained in the
underlying file with `_entry_corrupt=True` + `_entry_corrupt_reason`.

### Rule 2 — Airdrop / pre-listing detection
If `entry_price < 0.10 * reference_price` AND `entry_date < listing_date + 7d`
(or the symbol appears in a maintained airdrop watchlist: `HYPE, ENA, STRK,
W, JUP, PENGU, EIGEN, REZ, ZRO, TIA, AEVO, ALT, OMNI, ETHFI, PIXEL, …`),
flag as `_airdrop_entry_corrupt=True`. `reference_price` = symbol's median
exit_price over the trailing 30d window.

### Rule 3 — Stock split / reverse-split detection
If `asset_class=STOCKS` AND `entry/exit ratio` ∈ [2, 30] AND no `news_flag`
and no `corporate_action_flag` within ±2 trading days of exit_date, **and**
the trade's hold_days < 7, flag as `_possible_unadjusted_split=True`.
Ideally cross-reference a corporate-actions feed (yfinance Ticker.actions or
polygon /reference/splits). Until that feed is wired, fall back to: any
stock trade with entry/exit ratio >= 2x AND hold_days <= 3 gets a WARN flag
(retained in aggregates but surfaced in the audit table).

### Rule 4 — Per-trade PnL cap, asset-class tiered
Post-ratio filter, also cap raw `pnl_pct` at:
| asset_class | max |pnl_pct| |
|---|---|
| crypto | 500% |
| stocks | 200% |
| forex | 50% (FX never moves 50% unrealized; any > is leverage distortion) |
| commodities | 100% |
| index_futures | 100% |

Cap (not reject) values, set `_pnl_capped_from=<original>` on the row.

### Rule 5 (bonus) — Identical-entry clustering
If ≥3 trades in the same file share the *exact* same `entry_price` value
for the same symbol AND that value is <10% of the file's median exit for
that symbol, flag every one of them as `_cluster_entry_suspicious=True`.
(This is the pattern behind the 5 HYPEUSDT rows all sharing
`entry_price=0.050472`.)

## 7. Reference Implementation

```python
# audit_trail/phantom_scrubber.py  (proposed, not yet written)

AIRDROP_TOKENS = {
    "HYPE", "ENA", "STRK", "W", "JUP", "PENGU", "EIGEN", "REZ",
    "ZRO", "TIA", "AEVO", "ALT", "OMNI", "ETHFI", "PIXEL", "SAGA",
}

RATIO_THRESHOLD = {
    "CRYPTO": 20.0, "STOCKS": 5.0, "FOREX": 3.0,
    "COMMODITIES": 5.0, "INDEX_FUTURES": 3.0, "DEFAULT": 10.0,
}

PNL_CAP = {
    "CRYPTO": 500.0, "STOCKS": 200.0, "FOREX": 50.0,
    "COMMODITIES": 100.0, "INDEX_FUTURES": 100.0, "DEFAULT": 300.0,
}

def _base_symbol(sym: str) -> str:
    if not sym: return ""
    s = sym.upper().replace("USDT", "").replace("USDC", "").replace("USD", "")
    s = s.replace("=X", "").replace("PERP", "").replace("-", "").replace("/", "")
    return s

def scrub_phantom_trades(trades: list[dict], *, file_name: str = "") -> dict:
    """Returns {'clean': [...], 'flagged': [...], 'stats': {...}}.

    Mutates each flagged dict to add _entry_corrupt / _pnl_capped_from /
    _scrub_reason. Non-destructive: callers decide whether to exclude.
    """
    clean, flagged = [], []
    # Precompute per-symbol median exit in this file (for airdrop ref price).
    sym_exits: dict[str, list[float]] = {}
    for t in trades:
        x = _f(t.get("exit_price"))
        sym = _base_symbol(t.get("symbol", ""))
        if x and x > 0 and sym:
            sym_exits.setdefault(sym, []).append(x)
    median_exit = {s: sorted(v)[len(v)//2] for s, v in sym_exits.items() if v}

    # Identical-entry clustering (Rule 5).
    entry_clusters: dict[tuple[str, float], int] = {}
    for t in trades:
        sym = _base_symbol(t.get("symbol", ""))
        e = round(_f(t.get("entry_price")) or 0, 6)
        if e > 0 and sym:
            entry_clusters[(sym, e)] = entry_clusters.get((sym, e), 0) + 1

    for t in trades:
        reasons = []
        e, x = _f(t.get("entry_price")), _f(t.get("exit_price"))
        sym = _base_symbol(t.get("symbol", ""))
        asset_class = (t.get("asset_class") or t.get("category") or "").upper()
        if "FOREX" in asset_class: ac = "FOREX"
        elif "STOCK" in asset_class or "EQUITY" in asset_class: ac = "STOCKS"
        elif "COMMOD" in asset_class: ac = "COMMODITIES"
        elif "INDEX" in asset_class: ac = "INDEX_FUTURES"
        elif "CRYPTO" in asset_class or "USDT" in (t.get("symbol") or ""): ac = "CRYPTO"
        else: ac = "DEFAULT"

        # Rule 1: ratio.
        if e and x and e > 0 and x > 0:
            ratio = max(e, x) / min(e, x)
            if ratio > RATIO_THRESHOLD[ac]:
                reasons.append(f"ratio_{ratio:.0f}x>{RATIO_THRESHOLD[ac]}x({ac})")
                t["_entry_corrupt"] = True

        # Rule 2: airdrop pre-listing.
        if sym in AIRDROP_TOKENS and e and e > 0:
            ref = median_exit.get(sym)
            if ref and e < 0.10 * ref:
                reasons.append(f"airdrop_entry_{e}<0.1*{ref}")
                t["_airdrop_entry_corrupt"] = True

        # Rule 3: stock split heuristic.
        if ac == "STOCKS" and e and x and e > 0 and x > 0:
            ratio = max(e, x) / min(e, x)
            hold = _f(t.get("hold_days")) or 0
            if 2.0 <= ratio <= 30.0 and 0 < hold <= 3 and not t.get("news_flag"):
                reasons.append(f"possible_split_ratio_{ratio:.1f}x_hold_{hold}d")
                t["_possible_unadjusted_split"] = True

        # Rule 4: pnl cap.
        pnl = _f(t.get("pnl_pct"))
        if pnl is not None and abs(pnl) > PNL_CAP[ac]:
            t["_pnl_capped_from"] = pnl
            t["pnl_pct"] = PNL_CAP[ac] if pnl > 0 else -PNL_CAP[ac]
            reasons.append(f"pnl_capped_{pnl:.0f}%->{PNL_CAP[ac]}%({ac})")

        # Rule 5: identical-entry cluster.
        if e:
            key = (sym, round(e, 6))
            if entry_clusters.get(key, 0) >= 3:
                ref = median_exit.get(sym)
                if ref and e < 0.10 * ref:
                    reasons.append(f"entry_cluster_n={entry_clusters[key]}")
                    t["_cluster_entry_suspicious"] = True

        if reasons:
            t["_scrub_reason"] = ";".join(reasons)
            flagged.append(t)
        else:
            clean.append(t)

    return {
        "clean": clean,
        "flagged": flagged,
        "stats": {
            "total": len(trades),
            "flagged": len(flagged),
            "pct_flagged": round(100 * len(flagged) / max(1, len(trades)), 2),
            "file": file_name,
        },
    }

def _f(v):
    try: return float(v) if v not in (None, "", "null") else None
    except (TypeError, ValueError): return None
```

**Insertion point:** call `scrub_phantom_trades()` at the top of
`collect_system_stats()` (before the per-system loop) for each system's
closed-trade list. Replace the existing inline 100x block with this call
and aggregate only on the returned `clean` list (or `clean + flagged with
_pnl_capped_from`, depending on desired strictness).

## 8. Phantom-Trades Report Query

Pseudo-SQL (translate to pandas in the dashboard):

```sql
SELECT
    source_file,
    symbol,
    asset_class,
    entry_price,
    exit_price,
    pnl_pct AS raw_pnl_pct,
    ROUND(
        CASE WHEN entry_price >= exit_price
             THEN entry_price / exit_price
             ELSE exit_price / entry_price
        END, 1
    ) AS entry_exit_ratio,
    CASE
        WHEN (
            CASE WHEN entry_price >= exit_price
                 THEN entry_price / exit_price
                 ELSE exit_price / entry_price
            END
        ) > CASE asset_class
              WHEN 'CRYPTO' THEN 20.0
              WHEN 'STOCKS' THEN 5.0
              WHEN 'FOREX' THEN 3.0
              ELSE 10.0
            END
        THEN 'ratio_exceeds_threshold'
        WHEN ABS(pnl_pct) > CASE asset_class
              WHEN 'CRYPTO' THEN 500.0
              WHEN 'STOCKS' THEN 200.0
              WHEN 'FOREX' THEN 50.0
              ELSE 300.0
            END
        THEN 'pnl_exceeds_cap'
        ELSE NULL
    END AS flag_reason
FROM copy_trader_closed_trades
WHERE entry_price > 0
  AND exit_price > 0
  AND status IN ('CLOSED', 'EXITED')
HAVING flag_reason IS NOT NULL
ORDER BY entry_exit_ratio DESC, ABS(pnl_pct) DESC
LIMIT 100;
```

## 9. Recommendation Summary

1. Keep `f1aaa40f4c`'s 100x rule as the **top-level kill-switch** (catches
   obvious corruption).
2. **Add** asset-class-tiered ratio thresholds (20x crypto / 5x stocks / 3x
   forex) as a **second layer** that feeds a WARN flag rather than a hard
   exclude.
3. **Add** the airdrop-watchlist + reference-price check (Rule 2) — this is
   the only rule that would have caught HYPEUSDT at rollout time before it
   even hit the ratio gate.
4. **Add** the identical-entry cluster check (Rule 5) — cheap, file-local,
   and the strongest signal we have for data-provenance bugs.
5. **Defer** Rule 3 (stock splits) until a corporate-actions feed is wired;
   ship the hold_days<=3 WARN fallback now.
6. Add a **"phantom trades flagged"** panel to the audit dashboard fed by
   the query in §8 so regressions are visible without digging.

---

**Data files referenced (absolute paths):**
- `e:/findtorontoevents_antigravity.ca/copy_trader_intel/data/closed_trades.json`
- `e:/findtorontoevents_antigravity.ca/audit_trail/dashboard_generator.py` (commit f1aaa40f4c site)
