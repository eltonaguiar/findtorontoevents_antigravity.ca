Thinking...
We need to provide per-strategy validation, fixes, risk, and ranking of top-3 fixes. 10 strategies. Let's go through each.

Strategy 1 mega_mutation_macd_rsi_m048: Category E regime/names. Evidence: only one open pick has strategy=None; list of setups not firing. Likely blockage due to regime due to market white. So cause correct. Fix: update regime rules, add ability to override regime for this strategy; implement manual enable flag. Risk low if only a specific regime; but might expose to volatile market.

Strategy 2 claude_ml_moderate_mut: kill_list stale. Mis-categorized? It's in kill_list ; but performance 2.65 PF moderate. kill_list might be outdated. So cause D correct. Fix: review kill_list entry, add revocation or re-flag if recent performance > threshold. Risk Med: risk of reintroducing a mediocre strategy.

Strategy 3 hs_lb_None: auto-expire timestamp. Category B correct. Evidence: picks old. So disallow due to staleness. Fix: no - strategy likely in backlog; resume reactivation by clear stale entries, or out-of-date pick source; risk low (just re-get new picks). It's just staleness; not kill.

Strategy 4 stocks_rsi2_pullback: anti-test filter. Category B correct. It's legitimate equity strategy with high WR. Fix: adjust filter to allow rsi2 when equity; maybe add whitelist or regex. Risk Low: reactivating should not produce leaks because it's legit.

Strategy 5 MeanReversionBB: kill_list+contradiction. Should be miscategorized as D, kill_list. Evidence: overlapped in core. Fix: remove/ revoke kill entry, or update kill_list logic to check core first. Risk Med: reintroducing may impact quality.

Strategy 6 multi_period_rsi_confluence_et[h]: kill_list plus string truncation. Bug: truncated baseline leads to mismatched kill. Fix: correct baseline naming, add mapping alias. Risk Low.

Strategy 7 atr_percentile_gate: kill_list. Fix: check in whitelist; maybe remove. Risk Low.

Strategy 8 forex-rsi-ema-scout: regime no setups. Root cause correct. Fix: update setup generation regime detection or add manual enable. Risk Low.

Strategy 9 fx_smart_carry_trade_momentum: cron stale. Root cause correct. Fix: update cron data refresh or ignore stale flag. Risk Med: may interpret data incorrectly.

Strategy10 cta_fx_multifactor: regime no setups. Root cause correct. Fix: similar to 8: update universe or regime. Risk Low.

Now rank top-3 highest-impact fixes: We need picks-volume × edge × low risk. Let's evaluate each:

- stocks_rsi2_pullback: high WR 73.7% and 19 picks; correcting filter will bring 19 picks each day; high impact.

- mega_mutation_macd_rsi_m048: 11 picks, WR 90.9% not active. Potential high volume? modest. Might be hard due to regime.

- forex-rsi-ema-scout: 11 picks, WR 72.7%.

- cta_fx_multifactor: 11 picks, WR 63.6%.

- fx_smart_carry_trade_momentum: 11 picks but stale; reg.

- MeanReversionBB: 18 picks, WR 55.6% moderate.

So high volume high edge likely knocks? stocks_rsi2_pullback is high and anti-qual filter kills. So top 1: stocks_rsi2_pullback.

Second: mega_mutation_macd_rsi_m048 maybe.

Third: forex-rsi-ema-scout or cta_fx_multifactor; let's pick forex-rsi-ema-scout due slight higher WR. So 3.

Now risk classification for each specific fix.

Now produce output: list each strategy with validation, fix recommendation, risk. Then ranking table.

Let's craft.
...done thinking.

**Strategy‑level review (per strategy)**  

| # | Strategy | Attribution | Agreement | Fix (action) | Risk |
|---|-----------|--------------|-----------|--------------|------|
| 1 | mega_mutation_macd_rsi_m048 | E – regime + naming | ✅ | **Un‑kill & add manual override** – add a `regime_exempt` flag so this mid‑term edge stays active even in low‑vol regimes and correct the “m048” naming logic so the engine sees the existing setups. | LOW – only affects a regime‑specific strategy; will not surface in high‑vol markets unless regime changes. |
| 2 | claude_ml_moderate_mut | D – stale kill‑list | ✅ | **Revise kill‑list** – audit its last‑run timestamp (5 wk old) and re‑evaluate over the past month. If recent performance ≥ 1.8 PF and WR>60% add to `core_whitelist` or delete the kill entry. | MED – risk that a previously “unsound” version is re‑introduced; mitigated by confirming recent data. |
| 3 | hs_lb_None | B – auto‑expire timestamp | ✅ | **Refresh stale picks** – modify cleanup logic to allow 14‑day old picks for this niche strategy or flag the source as “back‑log” so it can be manually re‑activated. | LOW – simply re‑enabling established back‑log; no risk of new stale signals. |
| 4 | stocks_rsi2_pullback | B – anti‑test rsi2 substring | ✅ | **Whitelist / tighten pattern** – change `_is_valid_pick` to reject only if “rsi2” occurs *and* strategy is crypto *(remove “non‑crypto” guard)*, or add an explicit whitelist entry for this equity strategy. | LOW – prevents accidental re‑usage of the anti‑test safeguard; deterministic. |
| 5 | MeanReversionBB | D – kill‑list & core‑strategy conflict | ✅ | **Resolve conflict** – delete the kill‑list entry for this name, or change kill‑list logic to give priority to `core_whitelist`. Also bump its last‑kill‑run to current date. | MED – risk of re‑introducing a historically weak version; monitor its edge post‑un‑kill. |
| 6 | multi_period_rsi_confluence_et[h] | D + string‑truncation | ✅ | **Correct baseline naming** – update the baseline to use the true `_eth` suffix and add an alias mapping so the ouput matches the kill‑list name. | LOW – trivial string fix, no edge‑risk. |
| 7 | atr_percentile_gate | D – kill‑list | ✅ | **Remove from kill‑list** – add to `core_whitelist` or delete kill entry; double‑check no other quality gate blocks it. | LOW – low‑edge risk, but confirm its historical performance before re‑enable. |
| 8 | forex‑rsi‑ema‑scout | E – regime / no active setups | ✅ | **Regime token** – add a `force_enable` flag and extend setup generation logic for FX low‑vol regimes to generate pick data; run a pilot to verify not over‑exposed. | LOW – minimal market risk; only touches FX low‑vol logic. |
| 9 | fx_smart_carry_trade_momentum | A – cron / stale source | ✅ | **Refresh cron** – reschedule the data pipeline to run ≥ 24 h nightly, reset the file‑mtime guard, and clear stale flag. | MED – stale data may have changed; re‑validate assumptions after resync. |
|10 | cta_fx_multifactor | E – regime / no setups | ✅ | **Slight regime tweak** – relax the volatility‑threshold check for this strategy so updated FX regime logic can trigger it; or manually seed a few back‑fills. | LOW – impact limited to FX; risk of over‑exposure in low‑vol ~ negligible. |

### Top‑3 highest‑impact fixes (expected pick‑volume × edge × low risk)

| Rank | Fixable Strategy | Reasoning |
|------|------------------|-----------|
| 1 | **Stocks rsi2 pullback** | 19 lawful equity picks, 73.7 % WR; clearing this broad “rsi2” anti‑test filter restores ~19× daily edge. |
| 2 | **Mega_mutation_macd_rsi_m048** | 11 crypto picks, 90.9 % WR; regime exemption unlocks high‑profit edge that is otherwise silent. |
| 3 | **Forex‑rsi‑ema‑scout** | 11 Forex picks, 72.7 % WR; simple regime flag restores additional FX volume. |

> **Note** – The remaining fixes (especially for kill‑list and stale‑source issues) produce valuable pick‑volume but either have lower WR or higher implementation risk. The three listed above strike the best balance of volume, edge, and simplicity.

