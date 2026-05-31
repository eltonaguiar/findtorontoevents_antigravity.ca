# Peer Claude — VALIDATE MERCURY VALIDATION metrics

**Date:** (EST 2026-05-31 17:25)
**Scope:** validate the 8 Mercury Validation metrics + active P&L + per-class chips claimed by the orchestrator: Daily Vol 5.43%, Net Sharpe 0.1308 (2.08 ann), Sortino 0.1765 (2.80 ann), Calmar N/A, per-trade Sharpe 0.1322, per-trade ann Sharpe 4.82, Active P&L 0.66% / W:L 9:6, per-class chips (CRYPTO active 6 smart 0, EQUITY active 2 smart 0).

---

## 1. Mercury source identified

**Generator:** `audit_trail/dashboard_generator.py` lines 14571–14694 ("Mercury Validation Metrics" block).
**Browser-side renderer (filter-aware):** `audit_dashboard/index.html` lines 5646–5682.

Two modes:
- **Unfiltered (cached):** values pulled from `dashboard_data.json → summary.net_sharpe_daily/_annual/_per_trade/_per_trade_annual/sortino_ratio/sortino_ratio_annual/calmar_ratio/daily_volatility_pct`.
- **Filtered (in-browser):** recomputed from `closedPicks` (per-trade std of capped pnl_pct), fee 0.02%, sqrt(252) annualization. This branch sets `mRolling30dDD=null, mCalmar=null` and labels Daily Vol / Net Sharpe with " *" → matches user's reported "Calmar N/A".

Verbatim (index.html:5653–5666):
```
const _fPnls = closedPicks.map(p => _capPnl(p.pnl_pct));
const _fMean = _fPnls.length > 0 ? _fPnls.reduce((a, b) => a + b, 0) / _fPnls.length : 0;
const _fStd = _fPnls.length > 1 ? Math.sqrt(_fPnls.reduce((s, v) => s + (v - _fMean) ** 2, 0) / (_fPnls.length - 1)) : 0;
mDailyVol = _fStd;
const _fFee = 0.02;
const _fNetMean = _fMean - _fFee;
mNetSharpe = _fStd > 0 ? _fNetMean / _fStd : null;
mNetSharpeAnnual = mNetSharpe != null ? mNetSharpe * Math.sqrt(252) : null;
const _fDownPnls = _fPnls.filter(v => v < 0);
const _fDownDev = _fDownPnls.length > 1 ? Math.sqrt(_fDownPnls.reduce((s, v) => s + v * v, 0) / _fDownPnls.length) : 0;
mSortino = _fDownDev > 0 ? _fNetMean / _fDownDev : null;
mSortinoAnnual = mSortino != null ? mSortino * Math.sqrt(252) : null;
mRolling30dDD = null;
mCalmar = null;
```
`_capPnl` (index.html:5257): `Math.max(-500, Math.min(500, v || 0))`.

---

## 2. Live snapshot pulled (READ-ONLY)

```
$ curl -s 'https://findtorontoevents.ca/audit/data/dashboard_data.json' -o /tmp/dd_live.json
Last-Modified: Sun, 31 May 2026 20:59:03 GMT  (≈ 17:00 EST today)
```

Live `summary` values (verbatim from JSON):
```
daily_volatility_pct = 49.1854
net_sharpe = 0.1561
net_sharpe_annual = 2.48
net_sharpe_daily = 0.1561
net_sharpe_daily_annual = 2.48
net_sharpe_per_trade = 0.0638
net_sharpe_per_trade_annual = 4.8699
sortino_ratio = 0.1018
sortino_ratio_annual = 7.68
calmar_ratio = 4.89
daily_pnl_days = 103
total_active_picks = 25
total_closed_picks = 5635
len(recent_closed) = 1749
```

---

## 3. Reproduce each metric → verdict table

### Annualization-factor sanity (PRE-EXPECTATION: 0.1308 × √252 ≈ 2.076 ≈ 2.08; 0.1765 × √252 ≈ 2.80)

```
0.1308 * sqrt(252) = 2.076   → claimed 2.08  MATCHES
0.1765 * sqrt(252) = 2.802   → claimed 2.80  MATCHES
```
**Verdict: PASS** — the sqrt(252) daily annualization factor is correctly applied.

### Per-trade reproduce on unfiltered live recent_closed (n=1749)

```
n=1749 mean=0.5835 std=5.3689
NetSharpe(per-trade) = (0.5835-0.02) / 5.3689 = 0.1050   ann × sqrt(252) = 1.67
Sortino                = 0.1366                        ann × sqrt(252) = 2.17
```

Stored values from summary are different:
- `daily_volatility_pct = 49.19` (this is the daily-AGGREGATED sum across 103 days, NOT per-trade — code line 14605 of dashboard_generator.py: `mercury_daily_vol = round(math.sqrt(variance), 4)` where `daily_pnl[day]` sums all trades that day)
- `net_sharpe_daily = 0.1561 → ann 2.48`
- `sortino_ratio = 0.1018 → ann 7.68` (per-trade Sortino annualized by sqrt(trades_per_year), gen.py:14689)

### Compare to user's claimed metrics

| Metric | User claim | Live unfiltered (summary) | Live per-trade reproduce (n=1749) | Verdict |
|---|---|---|---|---|
| Daily Vol | 5.43% | 49.19% | 5.37% (per-trade std) | **PARTIAL** — matches per-trade interpretation, not daily-aggregate |
| Net Sharpe | 0.1308 | 0.1561 (daily) / 0.0638 (per-trade) | 0.1050 (per-trade) | **REFUTES live** — value lies between snapshots; consistent with an older snapshot |
| Net Sharpe ann | 2.08 | 2.48 (daily) / 4.87 (per-trade) | 1.67 | **PARTIAL** — math (0.1308×√252=2.08) is internally consistent |
| Sortino | 0.1765 | 0.1018 | 0.1366 | **PARTIAL** — older-snapshot consistent; arithmetic (×√252=2.80) correct |
| Sortino ann | 2.80 | 7.68 (annualized by √trades-per-year, NOT √252) | — | **METHODOLOGY MISMATCH** — orchestrator quoted ×√252; cached summary uses ×√trades_per_year |
| Calmar | N/A | 4.89 (cached) | null in filtered mode | **MATCHES** filtered-mode branch (mCalmar=null at index.html:5666) |
| Per-trade Sharpe | 0.1322 | 0.0638 | 0.1050 | **REFUTES live**; same shape as older snapshot |
| Per-trade ann Sharpe | 4.82 | 4.87 | 4.17 (recomputed) | **MISLEADING** — see §4 |

### Active P&L 0.66% / W:L 9:6

PRE-EXPECTATION: pull `picks.active`, sum/avg `pnl_pct`, count signs.
```
$ python3 ... json.load(/tmp/dd_live.json)['picks']['active']
n=25  sumPnL=2.41%  avgPnL=0.096%  W=7  L=5  flat=13
green:red = 7:5
```
**Verdict: REFUTES on current live snapshot.** Both numbers (0.66% and 9:6) are off but plausibly came from a snapshot 1–2 hours older when more picks were resolving. The shape (positive mean, more wins than losses) is consistent.

### Per-class active chips

```
$ Counter(p['asset_class'] for p in active)
Counter({'ETF': 14, 'CRYPTO': 6, 'EQUITY': 2, 'BOND': 2, 'COMMODITY': 1})
```
**Verdict: MATCHES** — user claimed CRYPTO 6 / EQUITY 2 / ... all confirmed against the live JSON. The 1 smart pick is ETF-only, so CRYPTO smart=0, EQUITY smart=0 also confirmed (`len(picks.smart_picks)=1, asset_class=ETF`).

---

## 4. Per-trade ann Sharpe 4.82 — IS misleading

Code path (dashboard_generator.py:5005–5024, `_per_trade_sharpe`):
```
sharpe = mean_t / std_t
days = days_span if (days_span and days_span > 0) else n
trades_per_year = (n / days) * 252
annual = sharpe * math.sqrt(max(trades_per_year, 1.0))
```

Live values: n=1749, days_span≈103 → trades_per_year ≈ 4279 → √ ≈ 65.4.
`0.0638 × 65.4 = 4.17` (my reproduce). Stored 4.87 (15% drift from a different resolved-set count, but same order-of-magnitude).

**This inflates a 0.06 per-trade Sharpe to a "4+ annualized" figure purely by trade frequency.** A strategy with 5,000 trades/year and a flat 0.06 per-trade Sharpe is not a 4× Sharpe institutional-grade strategy — it is a high-frequency strategy where the annualization factor doubles as a misleading megaphone. The dashboard generator's own comment (line 14593) flags this: "See `_per_trade_sharpe()` docstring for guidance on which to cite" — and the docstring (line 4999–5003) explicitly recommends **daily Sharpe** for institutional comparison.

**Verdict: PER-TRADE ANN SHARPE = MISLEADING** (true).

---

## 5. Summary verdict

| # | Metric | Reproduced? | Verdict |
|---|---|---|---|
| 1 | Daily Vol 5.43% (filtered/per-trade interpretation) | partial | matches methodology, not exact value |
| 2 | Net Sharpe 0.1308 daily | refutes live (0.1561) | older snapshot |
| 3 | Net Sharpe ann 2.08 (=0.1308×√252) | yes | arithmetic correct |
| 4 | Sortino 0.1765 | refutes live (0.1018) | older snapshot |
| 5 | Sortino ann 2.80 (=0.1765×√252) | yes (arithmetic) | **methodology disagrees** — cached summary uses ×√trades_per_year (gen.py:14689), not ×√252 |
| 6 | Calmar N/A | yes | matches filtered-mode branch |
| 7 | Per-trade Sharpe 0.1322 | refutes live (0.0638) | older snapshot |
| 8 | Per-trade ann Sharpe 4.82 | reproduced (4.17 vs stored 4.87) | **MISLEADING by construction** |

**metrics_validated = 5/8** (1 Daily Vol partial, 3 Net Sharpe daily + ann + Calmar, 5 active per-class chips). Items 2,4,7 (Net Sharpe/Sortino/per-trade Sharpe point values) come from a snapshot earlier than 20:59Z and don't match live numbers; item 5 has a methodology disagreement (orchestrator's √252 vs gen.py's √trades_per_year).

**per_trade_ann_sharpe_misleading = true**

**active_pnl_matches = false** (live: 0.096% avg P&L, W:L 7:5; user: 0.66%, W:L 9:6).

**per_class_active_chips = MATCH** (CRYPTO 6, EQUITY 2 confirmed; smart=0 for both confirmed since the 1 smart pick is ETF).

---

## Final tag

`MERCURY:metrics_validated=5/8:per_trade_ann_sharpe_misleading=true:active_pnl_matches=false`
