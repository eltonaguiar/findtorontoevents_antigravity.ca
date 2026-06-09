# Crypto A/S-Tier Scoring Tiles — Edge Verdict (2026-06-09)

**Swarm:** w976lbctb (4 dimensions + adversarial synthesis, HIGH confidence)
**Question:** Are the /audit crypto S-Tier (100% WR) / A-Tier (72.6% WR PF 4.0) score-band tiles a real tradable edge?
**Verdict:** **NON_EXISTENT_EDGE_ARTIFACT. You cannot trade A/S-tier crypto and profit.**

## Honest forward numbers (intrabar first-touch replay, SL wins ties)
- S-tier source `clone_hl_copy_PensionFund_24M`: true WR **0.0%** / PF 0.0 (8/8 replayed flip EXPIRED→SL_HIT at -1.0%).
- `luxalgo_confluence` (largest A-tier driver): true WR **40.4%** / PF 1.086 → REFUTED (86 TP→SL reclass).
- `prediction_market_consensus`: true WR **38.2%** / PF 1.36 → REFUTED (59 reclass).
- `hoffman_ema_trend`: WR 16.7% / PF 0.347 → INSUFFICIENT.
- Intrabar-corrected band cohort: S ~34% WR, A ~37-39% WR / PF 0.50.
- Class verdict (money_ready_verdict.json 2026-06-09): CRYPTO WR 47.7% / PF 0.945 / negative expectancy.
- **NO strategy HOLDS** (n≥20, WR≥50, PF≥1.5). Zero genuine survivors.

## Why the tiles lie (artifact mechanisms)
1. **Selection/survivorship** — tiles bucket the curated `recent_closed` slice (template.html:6597-6617 ← dashboard_data.json), surfacing fresh TP_HIT winners while excluding 72-96% of same-band TIME_EXIT/EXPIRED/OPEN picks (TIME_EXIT bucket runs negative avg pnl).
2. **Fixed-TP / nominal-TP labeling** — snapshot resolver stamps status=TP_HIT at the TP price with NO intrabar SL-first check. Smoking gun: identical PnL clusters (+3.948% ×8, +3.55% ×3, +3.50% ×2), exit_price == take_profit exactly; 16.3% of S+A TP_HIT pnl exactly equals the implied TP move.
3. **Intrabar SL-first flip** — where intrabar_status exists, 23-24% of S+A snapshot "wins" flip TP_HIT→SL_HIT. The S-tier +3.5% picks flip 8/8.
4. **Tiny-n + outlier/concentration** — S-tier n=16-19 single-source (alpha_engine); A-tier PF outlier-driven (one HYPEUSDT +51% ≈ 51 of 262 raw-sum %), JUPUSDT (incident #14) = 24.8% of A-band.
5. **Untraceable labeling layer** — some S-tile rows (`-USD` symbols, strategy=alpha_engine) aren't in trading_picks/at_raw_picks and can't be matched to crypto_ohlcv.

## Fix (recommended)
- Tile DISCLAIMER added to /audit MAJOR GOAL banner (INCIDENT #18). 
- Switch tile WR/PF to intrabar-true (TP/(TP+SL) over full band population) + surface the 23-24% reclass rate.
- Upstream: make intrabar first-touch the PRODUCTION resolver (not a sidecar) — THE recurring T2 blocker.
- Keep clone_hl / luxalgo_confluence / prediction_market_consensus / hoffman OUT of money-ready.

**Bottom line:** consistent with the whole-session finding — 0/9 money-ready, no forward-validated edge. The 100%/72.6% tiles are backward-looking mislabeled-winner groupings; the honest forward number is ~38-48% WR / PF <1 = coin-flip-to-losing.
