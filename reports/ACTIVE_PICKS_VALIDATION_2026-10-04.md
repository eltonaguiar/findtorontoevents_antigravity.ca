# Active Picks Validation — 2026-10-04

**Source:** live `https://findtorontoevents.ca/audit/data/dashboard_data.json`
(generated_at `2026-10-04T02:49:21Z`, repo_sha `22da70fccd`)
**Scope:** `picks.active_raw` = every non-closed pick. "Active" here = `status == OPEN`.
**Request:** validate all active picks; check each has a solid documented reason; aside from
today's picks, look for picks within the last week; flag broken picks.

---

## TL;DR

| Bucket | OPEN picks | With documented reason | Undocumented |
|---|---|---|---|
| **Last week** (2026-09-27 → 2026-10-03) | **327** | 123 (38%) | **204 (62%)** |
| Today (2026-10-04) — excluded per request | 403 | 195 (48%) | 208 |
| Stale leftovers (< 2026-09-27) | 11 | 0 | 11 |

- **Yes, there are picks within the last week:** 327 OPEN, dated 09-27 → 10-03.
- **The documented-reason requirement fails on the majority.** 62% of last-week OPEN picks carry
  no `reason` and no `notes`. EQUITY is the worst (1/66 documented). CRYPTO is 66/191.
- **3 picks are structurally broken** (bad TP/SL geometry or already-breached stop/target still OPEN).
- **Duplication is severe:** 179 of 327 last-week rows are duplicate
  `(symbol, direction, strategy)` groups — 55% of the book.
- **168 of 334 non-today picks have no `current_price`** (140 are CRYPTO, which trades 24/7 →
  a pricing/staleness defect, not a market-hours artifact).

---

## 1. Where each pick's justification comes from

A pick is counted **documented** if `reason` or `notes` is non-empty. The strongest examples
carry quantified logic, e.g.:

```
EURUSD=X LONG  Z-score=-2.24 below 200d SMA (1.16125), RSI=4. Backtest: 68.3% WR on 167 trades (p<0.001).
ZROUSDT  LONG  TSMOM: 14d return +80.2% (rank 3/20), BTC BULLISH, vol-scale 0.25x (rv=112% -> target 15%)
QQQ      LONG  Donchian 55-day breakout: price 749.58 > 55d high 748.35. 20d trailing stop 699.27. Turtle, Dennis (1983).
```

### Last week (09-27 → 10-03), documented vs total by class

| Asset class | Documented / total |
|---|---|
| BOND | 22 / 24 |
| COMMODITY | 3 / 3 |
| CRYPTO | 66 / 191 |
| **EQUITY** | **1 / 66** |
| ETF | 4 / 13 |
| FOREX | 19 / 22 |
| FUTURES | 8 / 8 |

**Largest undocumented buckets (last week):** `inverse_luxalgo_confluence` (85), 
`magic_formula_x_piotroski_x_acquirers` (22), `penny_stock_screener` (20), 
`regime_mild_bull` (7), `luxalgo_confluence` (5).

### Today (10-04), documented vs total by class (for contrast)

| Asset class | Documented / total |
|---|---|
| COMMODITY | 57 / 58 |
| FOREX | 87 / 90 |
| ETF | 15 / 16 |
| EQUITY | 7 / 13 |
| FUTURES | 8 / 10 |
| **CRYPTO** | **21 / 215** |
| SPORTS | 0 / 1 |

The variation by class/source shows the reason field is populated by *some* emitters
(FOREX z-score, COMMODITY momentum, bond yield-momentum) and not by others
(most CRYPTO consensus/luxalgo emitters, equity factor screeners).

---

## 2. Broken picks

Structural defects among non-today OPEN picks (current-price-aware — trailing stops that have
ratcheted above entry are **not** counted as broken):

| Date | Symbol | Dir | entry | TP | SL | current | Defect |
|---|---|---|---|---|---|---|---|
| 10-03 | **DOGEUSDT** | SHORT | 0.093 | 0.09579 | 0.09114 | — | **INVERTED** — for a SHORT the target sits *above* entry and the stop *below*; TP/SL are on the wrong sides |
| 10-03 | **CL=F** | LONG | 100.05 | 102.051 | 99.05 | **91.11** | Stop already breached (price 91.11 << SL 99.05) yet still OPEN — resolver never closed it |
| 10-03 | **NG=F** | LONG | 2.831 | 2.8876 | 2.8027 | **3.035** | Target already reached (price 3.035 > TP 2.8876) yet still OPEN — resolver never closed it |

Also note the earlier "bad geometry" candidates (NVDA, SOL, ADA, AVAX, ETH) were **false
positives** — their stops sit above entry because they are *trailing* stops that moved up as
price advanced. Excluding them is the correct call.

### Stale leftovers (OPEN, before 09-27, all undocumented)

11 rows, including non-trading entries that should not be in the tradeable book:

```
MKR LONG crypto_gainer_ml (no timestamp)
TIA LONG crypto_gainer_ml (no timestamp)
OP  LONG crypto_gainer_ml (no timestamp)
"Montreal Canadiens vs Buffalo Sabres" LONG value_bet   <-- SPORTS bet in the trading active set
GOOGL/XLK/XOM/JPM/XBI/AAPL  (2026-09-24/25 scout picks, no reason)
```

---

## 3. Duplication & conflict flags

- **62 duplicate `(symbol, direction, strategy)` groups** covering **179 / 327 (55%)** of the
  last-week OPEN book. Worst: `WIFUSDT/XRPUSDT/AVAXUSDT LONG inverse_luxalgo_confluence ×6`,
  `BTCUSDT SHORT ×5`, `AAPL LONG regime_mild_bull ×4`, `DNA LONG regime_accumulation ×4`.
- 74 picks carry an internal `_dup_cross` flag; 45 carry `has_conflict`.
- Duplicates inflate the apparent number of "active picks" and multiply per-name risk
  (6× the same long on one symbol = 6× exposure unless deduped upstream).

---

## 4. Data-quality gaps

- **No `current_price` on 168 / 334 non-today OPEN picks** (140 CRYPTO). If the field is null,
  the dashboard cannot compute live PnL → these are effectively blind.
- **Local repo copy is stale:** `alpha_engine/data/active_picks.json` in the working tree is
  frozen at **2026-06-21** (120 picks, all June 19–21). It does not reflect the live book and
  will mislead any local analysis. The live dashboard payload is the only current source.

---

## 5. Recommendations

1. **Populate `reason` at emit time for the undocumented emitters** — prioritize EQUITY
   (`magic_formula_x_piotroski_x_acquirers`, `penny_stock_screener`) and CRYPTO
   (`inverse_luxalgo_confluence` dominates). A pick without a reason should not reach the book.
2. **Fix the 3 broken picks** — DOGEUSDT direction/TP-SL inversion; force-close or re-resolve
   the breached CL=F and reached NG=F.
3. **Dedupe at the source** — collapse the 62 duplicate groups (55% of the book) before they
   hit `active_raw`.
4. **Investigate null `current_price`** for the 140 CRYPTO picks — it is not a market-hours
   artifact.
5. **Purge stale/foreign rows** — the 11 pre-09-27 leftovers and the SPORTS bet in the
   trading active set.
6. **Refresh the local `active_picks.json`** or document that the local copy is non-authoritative.

---
*Generated by Buffy via live /audit payload review. Numbers reproducible from
`dashboard_data.json::picks.active_raw` filtered to `status == OPEN`.*
