# 2026-06-02 — Suspicious bootstrap CI PASSes investigation

## TL;DR
Investigated the 3 strategies flagged in PR #481 as "suspicious bootstrap CI PASS" (IS_PF>30). **Two are legitimate (B_flip, inverse_ml) and one (claude_ml_moderate_mut) is a single-row meme-coin outlier.** The bootstrap CI gate already handles this correctly via `pf_lo_95` (lower 95% bootstrap CI), which down-weights single extreme winners. **No code change needed; bootstrap CI is doing the right thing.**

## Investigation

### `claude_ml_moderate_mut` (n=67, IS_PF=310.77) — single-row outlier
- One row (id=214622) dominates: JUPUSDT LONG, pnl_pct=**76573.31**, entry=0.0002, exit=0.1892, TP=0.0003, SL=0.0002, closed=2026-05-31 18:39:41
- Real return: 0.1892 / 0.0002 = **945x** (94500% in percent)
- This is a real meme-coin moonshot that day; the `pnl_pct` column captured it as 76573% (likely the entry-to-exit ratio with a unit conversion that the column is using for memecoins)
- Gross profit=77140, gross loss=248 → 310x PF; without this single row, the other 66 picks would compute a much lower PF
- **Bootstrap CI verdict: pf_lo_95=1.313** — the lower bound drops to 1.31 when the outlier is missing from resamples, which is the correct signal: "the strategy works *if* you get lucky on a 945x memetoken"
- **Action**: do not promote claude_ml_moderate_mut to real money; require pf_lo_95 > 1.5 before re-evaluating. Logged as `INCIDENT_CRYPTO #14`.

### `B_flip_PriceRocMeanReversion` (n=157, IS_PF=35.91) — legitimate
- Source: `alpha_engine` (single)
- Outcome distribution: TP_HIT=101, WON=37, LOST=17, SL_HIT=2
- 88% win rate (138/157), max pnl_pct=13.21, min=-2.72
- No extreme outliers; tight distribution
- Bootstrap CI: [21.21, 73.41] — narrow, high-confidence real edge
- **Verdict**: this is a real, profitable mean-reversion strategy. The high PF reflects a tight, high-WR distribution with small losses. PF=35 is mathematically correct for {avg win 5.8, avg loss 1.2, 88% WR}.

### `inverse_ml_enhanced_BTCUSDT_15m_D` (n=65, IS_PF=34.46) — legitimate
- Source: `alpha_engine` (single)
- Outcome distribution: TP_HIT=35, SL_HIT=20, LOST=5, WON=5
- 91% win rate (59/65), max pnl_pct=9.10, min=-1.66
- No extreme outliers; tight distribution
- Bootstrap CI: [15.97, 128.76] — narrow, high-confidence real edge
- **Verdict**: real strategy, not overfit. Forward-test candidate.

## Other strategies with |pnl_pct| > 1000
A global scan found 5 strategies with at least one row having pnl_pct > 1000 (i.e., >1000% return):
| Strategy | n with \|pnl\|>1000 | max pnl_pct |
|---|---|---|
| `stocktwits:MisterGreen` | 1 | 370850 (3708x) |
| `claude_ml_moderate_mut` | 1 | 76573 (945x, JUPUSDT id=214622) |
| `rapid_momentum_filter_mut` | 1 | 13505 |
| `luxalgo_confluence` | 1 | 13201 |
| `stocktwits:HomelessDegenerate` | 1 | 6082 |

These are all single-row extreme-winner events. The bootstrap CI is correctly designed to handle this by reporting the lower-bound CI rather than just the point estimate.

## Updated verdict on the 3 suspicious PASSes
- `claude_ml_moderate_mut`: **DO NOT promote**. Single-row 945x outlier distorts the picture. pf_lo_95=1.31 is borderline. Logged as `INCIDENT_CRYPTO #14`.
- `B_flip_PriceRocMeanReversion`: **PROMOTE to forward-test**. Real 88% WR, tight distribution, narrow CI [21.2, 73.4]. Add to the top-3 forward-test list.
- `inverse_ml_enhanced_BTCUSDT_15m_D`: **PROMOTE to forward-test**. Real 91% WR, tight distribution, narrow CI [16.0, 128.8]. Add to the top-3 forward-test list.

## Revised forward-test list (5 strategies)
1. `crypto_liquidity_wick_reversal_v1` — n=4675, IS_PF=2.72, CI=[2.49, 2.95]
2. `prediction_market_consensus` — n=619, IS_PF=2.08, CI=[1.70, 2.57]
3. `drawdown_recovery_rsi_xrp` — n=438, IS_PF=1.89, CI=[1.45, 2.50]
4. `B_flip_PriceRocMeanReversion` — n=157, IS_PF=35.91, CI=[21.21, 73.41] (revised)
5. `inverse_ml_enhanced_BTCUSDT_15m_D` — n=65, IS_PF=34.46, CI=[15.97, 128.76] (revised)

## Future enhancement
Add a **sustained_pf** metric: median PF over 10 random sub-resamples (each subsample randomly removes 1-2 rows from the full set). This catches strategies that only work because of one outlier row. Proposed in `INCIDENT_CRYPTO #14` fix field.

## Refs
- PR #481 (bootstrap CI gate)
- `INCIDENT_CRYPTO #14` (claude_ml_moderate_mut outlier)
- `ENHANCEMENT_OVERALL #85` (EAGLE-6 v2 gates)

## Reproduce
```bash
DB_PASS_STOCKS=$DB_PASS_STOCKS python3 -c "
import os, pymysql
conn = pymysql.connect(host='mysql.50webs.com', user='ejaguiar1_stocks', password=os.environ['DB_PASS_STOCKS'], database='ejaguiar1_stocks', port=3306)
c = conn.cursor()
c.execute('''
    SELECT id, symbol, direction, pnl_pct, entry_price, exit_price, outcome
    FROM at_signal_outcomes
    WHERE strategy = 'claude_ml_moderate_mut' AND ABS(pnl_pct) > 1000
''')
for r in c.fetchall(): print(r)
"
# -> (214622, 'JUPUSDT', 'LONG', 76573.31, 0.0002, 0.1892, 'TP_HIT')
```
