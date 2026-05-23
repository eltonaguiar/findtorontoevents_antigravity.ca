# Asset Class 90-Day Plan — CRYPTO — 2026-05-15

**Senior Quant Audit** using `money-maker-continual-improve` skill (7-step process).  
**Focus**: Why high volume (n=8k resolved) but sub-T2 performance (PF 1.36 / WR 46.7%); symbol universe quality (meme/alt noise vs liquid core); on-chain usage; hidden drags (specific systems/sources/symbols); realistic recommendation on dramatic universe shrink.  
**Data sources**: `audit_dashboard/data/dashboard_data.json` (2026-05-15T02:06Z), `reports/MASTER_ACTION_PLAN_2026-05-15.md`, `alpha_engine/config.py` (SECTOR_MAP), `alpha_engine/crypto_onchain_momentum.py`, `alpha_engine/production_scanner.py`, `alpha_engine/asset_class.py`, recent closed picks analysis, `reports/asset_class_research_CRYPTO_2026_05_12_0437Z.md`, `reports/backtest_crypto_onchain_2026_05_12_0616Z.md`, `reports/aa1_ml_crypto_pred_autopsy_20260513.md`, `reports/fix_CRYPTO_20260505T005402Z.md`, `reports/audit_asset_feedback_2026-05-05T0121Z_CRYPTO.md`.

**Current Charter context** (from CLAUDE.md / master plan): CRYPTO sub-T2 (PF 1.25/44.6 n=8067 in May-3 snapshot; improved to 1.36/46.7 n=8011 today). Drags cited: `quan_engine` (~18% vol @ PF 0.70 historical) + `unknown` (~7% @ PF 0.35). `luxalgo_confluence` now top strategy (16% share). Sizing allowed but needs −20% noisy volume share + quality lift to reach T2 (PF>1.5 / WR>50 / n≥100 stable). Not system pilot (COMMODITY CT=F leads with PF 2.49 / WR 61.5% n=322). M-001 (BTC UTC death-zone), M-004 (CRYPTO drag autopsy + auto-quarantine >40% vol & PF<1), M-034 (confidence-inversion gate), M-038 (MEMECOIN quarantine) pending.

---

## Step 1: Establish Brutal Baseline (CRYPTO)

**Live performance** (`dashboard_data.json::performance.asset_class_health.CRYPTO` + `by_asset_class.CRYPTO` + `picks.recent_closed`):
- Resolved n=8011 (huge vs EQUITY 420 / COMMODITY 322 / ETF 106) — high volume from broad scanners.
- WR: 46.7% (recent_closed 2891 samples: 3738 wins / 4273 losses overall class).
- PF: 1.36 (by_asset_class), expectancy +0.39.
- Active picks: 165; closed: 26k+; total_pnl_pct: +3082 (but system-wide diluted).
- Concentration: OK tier (no block). Top symbol BTCUSDT (10.32% PnL mass), top_strategy `luxalgo_confluence` (16.18% share). `honest_label`: "CRYPTO edge = luxalgo_confluence on BTCUSDT".
- Circuit breaker: cold_start (n=0<30 realized_30d), no breach.
- Older snapshot (master plan May-3): PF 1.25 / WR 44.6% / n=8067 — quan_engine + unknown dragged elites (PF 2.34-3.97).
- Recent closed CRYPTO (2891 picks): overall class WR ~46.7% PF 1.36.

**Symbol universe quality**:
- Defined in `alpha_engine/config.py:SECTOR_MAP` (~45-50 crypto entries): 2 majors (BTCUSDT/ETHUSDT exempt from sector cap), ~20 L1 (SOL, AVAX, NEAR, SUI, ADA, DOT, ATOM, APT, TON, MATIC/POL, ALGO, ICP, SEI, INJ, TIA, KAS, HBAR, ETC, FTM), ~12 DeFi (AAVE, UNI, LINK, MKR, SNX, COMP, CRV, LDO, PENDLE, JUP, ENA, EIGEN), 9 memes (DOGE, SHIB, PEPE, FARTCOIN, BONK, FLOKI, WIF, TRUMP, BRETT — explicit "meme" sector with loose CATEGORY_RISK: SL -15% / TP +35% / hold 3d), 6 AI (RENDER, TAO, FET, OCEAN, ARKM, VIRT), 5 gaming (AXS, SAND, MANA, IMX, GALA), 3 L2 (ARB, OP, STRK), payments (XLM, LTC, BCH), storage/privacy/enterprise/exchange (FIL, ZEC, BAT, QNT, XMR, BNB, HYPE).
- `asset_class.py:CRYPTO_SOURCE_HINTS` + `CRYPTO_STRATEGY_HINTS` drive dynamic classification (coinglass, binance, onchain, funding, skyrocket, dex etc).
- Actual production universe broader/dynamic: `production_scanner.py` + `top_gainer_capture.py` + `smart_picks_engine.py` + baby/mutation emitters add symbols on-the-fly (no hard ADV gate found). Recent_closed analysis: **179 unique CRYPTO symbols**.
  - Top by count: BTCUSDT (461), ETHUSDT (221), ONDOUSDT (204), SOLUSDT (183), XRPUSDT (129), AVAXUSDT (101), JUPUSDT (96), SUIUSDT (91), ADAUSDT (89), DOTUSDT (88), NEARUSDT (84), LINKUSDT (70), ARBUSDT (66), STXUSDT (61), WIFUSDT (51), DOGEUSDT (46), TIAUSDT (43), APTUSDT (42), SEIUSDT (40), INJUSDT (39), ETCUSDT (38), HYPEUSDT (38), ATOMUSDT (29), SHIBUSDT (25), APEUSDT (24), FETUSDT (22), ... + SOL-USD/DOGE-USD variants, POLUSDT, ALGOUSDT.
  - Mix: ~40% majors/L1 liquid, ~30% mid-tier alts (ONDO, JUP, SUI, TIA, SEI, INJ, APT, STX, HYPE, FET — many <3-6mo old or lower ADV), ~15% memes (WIF, DOGE, SHIB, PEPE, FARTCOIN, BRETT, TRUMP — explicit low-liq risk in legacy config comments e.g. LIT/TOMO/HIFI "Low liquidity (<$1M vol), prone to pump/dump" / "Sub-$1M volume... illiquid").
- Quality verdict: **Poor**. High % low-liquidity / meme / new alts dilute edge. No enforced min daily volume / ADV filter in critical path (scanners emit, risk_warnings exist only in old dicts, not runtime gate). MAX_PICKS_PER_SYMBOL=1 + sector caps help but insufficient vs slippage/manipulation on illiquids. Results in high signal volume (easy for scanners on volatile names) but realized poor WR/PF (noise dominates, execution costs eat edge).

**On-chain data usage**:
- Dedicated module: `alpha_engine/crypto_onchain_momentum.py` (Glassnode MVRV-Z + active addresses 30d + exchange balance; LONG MVRV-Z < -0.5 + rising addr; SHORT MVRV-Z >2.0 + falling exch bal. Confidence 0.55-0.75. Universe: only BTC/ETH. Default-OFF (`CRYPTO_ONCHAIN_MOMENTUM_ENABLED=1`).
- Backtest (`reports/backtest_crypto_onchain_2026_05_12_0616Z.md`): synthetic price z-score proxy (not live Glassnode), n=167 (BTC 89 WR43.8% PF1.0; ETH 78 WR51.3% PF1.61), overall WR47.3% PF1.28 MDD42% — **WARN** (not T2). Best/worst trades listed, but low n, no live paper volume.
- Not a volume driver (not in top sources of recent_closed). Underused despite research priority in `asset_class_research_CRYPTO_2026_05_12_0437Z.md` (Grok-4: "On-Chain Momentum candidate PF~1.65", "priority: Validate On-Chain Momentum with anti_overfit_validator").
- Other on-chain hints: `coinglass_integration.py`, `coinglass_strategies/`, Dune mentions in hints, but no broad production adoption. `hayes_liquidity_index` / `onchain_composite_score` in strategy catalog but low adoption.
- Verdict: **Minimal / experimental**. Missed opportunity for high-signal, low-cost edge on majors (Glassnode free tier sufficient for BTC/ETH; funding/liquidation from Binance free).

**Outcome tracking / DB reality**:
- High resolved n good for CRYPTO (resolver-v2 post-filter applied system-wide).
- But `reports/aa1_ml_crypto_pred_autopsy_20260513.md`: `ml_crypto_pred` system closed_picks=848, resolved=40, **excluded_closed=808 (95.3%)** — resolver gap (pre-v2 backfill? forward_validator skip? different close path). Sub-strats: orig ml_crypto_pred (n=32 WR28% LONG-inverted 12%/85% SHORT), "unknown" n=7 0% WR (DEAD-EDGE), enhanced variants 0-1 resolved. System-level PF1.86 but asymmetric + hidden 95% exclusion hides rot. Similar non-crypto resolver bugs noted elsewhere.
- Paper trading active (tv-paper-trade) but CRYPTO benefits from volume; freshness via new DB guardian (M-002) pending wire.
- `at_signal_outcomes` coverage high for class but many low-quality (noise symbols).

**GitHub Actions / Data flow**: CRYPTO flows through production_scanner → alpha_engine scoring (elite_scorer, score_booster) → quality_gates (passes_active_gate) → smart_picks / dashboard. GHA audit-dashboard.yml + others cover. Recent direct commits (Hermes c2c072c0123: quan_engine cap 12%→5%, VIX gate ON) + PR #1027 (crypto short bias — disputed: live recent_closed shows LONG wins 48.8% vs SHORT 37.4%, Wire-Up violation no caller/Wiring Plan).

**Summary baseline**: High volume from broad/dynamic 179-sym universe + 20+ sources (many mediocre) produces n=8k but caps PF at 1.36 / WR 46.7% (just above random after costs/slippage on alts). Elites (mega_mutation PF2.29, dna_winner_picks PF1.88, kimi_riseoftheclaw PF1.57, claude_gainer_st PF1.66) diluted by drags. Post-May5 fixes (quan_engine confidence inversion fixed in elite_scorer.py + volume cap), current quan_engine n=305 PF1.36 WR35% (still low WR). No "unknown" in recent_closed (historical). COMMODITY shows what focused liquid + high-signal data (COT) can achieve.

---

## Step 2: Identify the Single Best Pilot Candidate (within CRYPTO)

**Filters applied**: Live PF>1.5 + WR>50% + n≥100 post-noise on sub-universe; clear explainable edge; feasible with current infra (no new paid APIs first).

- **Recommended Pilot**: **Liquid Majors Core (BTCUSDT + ETHUSDT + SOLUSDT + 5-7 top L1 by ADV: AVAX, NEAR, SUI, ADA, LINK, ARBUSDT)** powered by:
  - On-chain momentum (extend Glassnode to SOL if feasible; funding rate carry/arbitrage from Binance/Hyperliquid free endpoints — high system Sharpe 8+ in funding strategies per master plan).
  - High-PF sources only: dna_winner_picks, mega_mutation, kimi_riseoftheclaw, baby_strats_forward, aggregated_picks (elite).
  - BTC UTC-hour death-zone filter (M-001: reject 08-09Z, boost 22Z — memory-backed n>1000).
  - Strict liquidity gate (new ADV filter) + trust_score ≥0.6 + source whitelist.
- Justification: BTC/ETH already 23%+ of recent_closed volume, highest liquidity (lowest slippage), best on-chain data availability. Funding rates provide persistent carry edge (academic + live in system). Current top luxalgo + baby_strats show path to 1.46+ PF when filtered. Avoids meme/alt noise. Matches "size up where edge is best worth the risk". External replication: Hyperliquid HLP, on-chain dashboards (Dune/CoinGecko), Coinglass funding/liquidation.
- Secondary: If pilot succeeds, expand to DeFi established (JUP, AAVE, UNI) with on-chain whale tx.

**Not system-wide pilot** (COMMODITY remains #1 per skill + master plan convergence). CRYPTO pilot for 2026-06-08 per schedule but gated on M-004 autopsy + M-014 calibration.

---

## Step 3: Gap Analysis (CRYPTO)

| Gap Type                  | Diagnostic (data-backed)                                                                 | Severity | Typical Fix |
|---------------------------|------------------------------------------------------------------------------------------|----------|-------------|
| Symbol universe quality (low-liq meme/alt vs real) | 179 unique (vs focused 25); 9 explicit memes + many mid alts (ONDO/JUP/SUI/TIA/SEI/INJ/APT/HYPE/FET/APE/WIF/FARTCOIN etc) in top counts; legacy risk_warnings for < $1M vol (LIT/TOMO/HIFI); dynamic scanners no ADV gate; SECTOR_MAP has meme sector but no hard filter. High signal volume on noise names. | **P0** | Shrink to 25 liquid (ADV>$10M 24h or Binance top-30 vol tier); new LIQUID_CRYPTO_SYMBOLS list + runtime gate in production_scanner.py + asset_class.py. Deprecate memes to research-only (M-038). |
| On-chain data usage      | Only BTC/ETH in crypto_onchain_momentum.py (Glassnode MVRV-Z+addr+bal, opt-in); backtest synthetic PF1.28 n167 WARN (not live Glassnode); not in top sources (0% volume driver); research priority but zero production scale. | **P1** | Enable + wire for BTC/ETH/SOL; add free funding/liquidation (Binance API) + whale (Dune free queries or coinglass); cache responses; extend backtest to live data; target 10-15% volume share. |
| Hidden drags (systems/symbols) | Recent_closed sources (2891 CRYPTO): luxalgo_filters n=678 (~23% vol) PF1.07 WR45.1%; alpha_engine n=335 (~12%) PF0.99 WR42.7%; quan_engine n=305 (~10.5%) PF1.36 WR35.4% (post-cap); copy_trader_highscore n=99 PF0.80 WR30.3%; battleground n=63 PF0.65; regime_terminal n=65 PF0.95 WR32.3%; ml_crypto_pred variants 95% excluded + 0% WR subs (aa1 autopsy). Historical quan_engine/unknown 18%+7% @ PF<0.7/0.35 (pre May5 cap + elite_scorer fix in fix_CRYPTO). BTC/ETH good; alts/memes drag. PR #1027 short bias inverted on live data. | **P0** | Auto-quarantine in quality_gates.py (M-004: >40% vol & PF<1 or WR<40% for 30d+); source whitelist for crypto pilot; delete/invert low-PF (see Step 4); confidence-inversion gate (M-034) for cloud-agent. |
| Backtest vs forward decay / execution realism | High n but PF/WR below T2; no full slippage/ADV model for 179 alts (CATEGORY_RISK crypto/meme tuned but slippage_validator scaffold in PR #1026 not wired for crypto); CATEGORY_RISK "meme" loose (-15%/+35%/3d) insufficient vs real liq. MFE analysis old. | **P1** | Wire slippage_validator + position_sizer (M-017/M-018) with per-symbol ADV; add tx cost model 0.1-0.5% crypto; walk-forward on filtered universe only. |
| Strategy bloat / outcome tracking | 20+ sources for CRYPTO (many sub-PF1.1 high n); resolver gaps in ML crypto (95% excluded); high auto-expired/integrity_excluded system-wide. | **P1** | Prune via quality_gates + BLOCKED_SOURCE_SYSTEMS; fix resolver for crypto ML paths; DSR/trust_score gate (M-012/M-006). |
| Data freshness / missing features | Funding rates, full Glassnode, whale flows, macro-crypto corr (DXY) underused per research swarm. DB freshness guardian pending. | **P2** | Low-cost: Binance funding WS, CoinGecko vol, cached Glassnode; FRED DXY for macro filter (M-032). |

**Why high volume but poor PF/WR overall?** Volume = broad scanners emit easily on volatile alts/memes (179 syms). Poor quality = noise (manipulation, low ADV slippage not modeled, low edge persistence on illiquids), diluted by 5+ high-vol mediocre sources (luxalgo/alpha_engine/copy/battleground/regime ~40%+ combined share, sub 1.1 PF or <40% WR), historical quan/unknown + confidence inversion (fixed but volume was drag). Elites exist but swamped. Contrast COMMODITY (focused COT on 1 liquid CT=F, high PF).

---

## Step 4: Decision Framework for Strategies (live >60d)

- **Statistically significant negative alpha (PF<1.0 or WR<40% sustained, n>50)**: **Delete or hard quarantine** (BLOCKED_SOURCE_SYSTEMS + probation in shadow_probation.json). Examples:
  - `copy_trader_highscore` (crypto contrib): PF 0.80 WR 30% — delete or invert.
  - `battleground`: PF 0.65 — quarantine (crypto volume).
  - `regime_terminal`: PF 0.95 WR 32% — quarantine.
  - `alpha_engine` generic (if not BTC/ETH filtered): PF 0.99 — tighten or reduce volume.
  - `ml_crypto_pred` sub-strats (per aa1): "unknown" 0% WR, orig LONG-inverted 12% WR, enhanced 0-resolved — delete; keep only if SHORT-only mutation.
  - `dna_rapid_fire_mutations`, `mutation_lab` (low n zero WR) — delete.
  - Historical: quan_engine_scalp / position (already blocked/retired per fix_CRYPTO + strategy_blocklist.py).
- **Strong negative correlation with main signal**: Consider **inverted version** (e.g. short bias on underperformers per PR #1027 but only after fixing inversion + Wire-Up).
- **Positive but fragile (PF 1.0-1.3, high vol)**: Tighten entry + add cost/liquidity model. `luxalgo_filters` (PF1.07 23% vol), `quan_engine` (now 1.36 but 35% WR) — apply volume cap + elite_score gate stricter for alts; keep if on BTC/ETH only.
- **Only keep if survives walk-forward + live paper with real costs**: Promote `mega_mutation` (PF2.29), `dna_winner_picks` (1.88), `kimi_riseoftheclaw` (1.57), `baby_strats_forward` (1.46), `claude_gainer_st` (1.66), `aggregated_picks` (1.88). On-chain + funding for core symbols.
- **Per master (M-004)**: Any >40% CRYPTO vol AND PF<1.0 auto to probation. Add to `audit_trail/quality_gates.py`.

**Strategies to delete/invert/promote (file paths)**:
- Delete/quarantine: `copy_trader_highscore`, `battleground`, `regime_terminal`, ml_crypto_pred subs, low-n mutations → `alpha_engine/strategy_blocklist.py`, `audit_trail/quality_gates.py` (new quarantine fn), `BLOCKED_SOURCE_SYSTEMS`.
- Promote/wire: `crypto_onchain_momentum` (enable + extend), funding_rate_carry (already high weight in config), dna/mega/kimi sources → `alpha_engine/config.py` (STRATEGY_WEIGHT_OVERRIDES), `production_scanner.py` (source whitelist), `score_booster.py` (M-001 hour filter).
- Invert/test: Short bias only on verified (after fix PR #1027 issues).
- Reference: `elite_scorer.py` (quan confidence fix already done), `smart_picks_engine.py` (blocks).

---

## Step 5: Leverage AI Keys Intelligently — High-ROI Prompt Templates (tailored to gaps)

**1. On-chain / Alternative Data Feature Ideation (for CRYPTO majors + liquid L1)**:
```
For CRYPTO (BTC/ETH/SOL + top L1), give 8-10 high-signal, low-cost on-chain + funding features from peer-reviewed or production quant papers 2018-2025 (Glassnode, Dune, Coinglass, Binance funding, whale tx, exchange flows, active addresses, MVRV variants, liquidation cascades). For each: exact free/near-free data source (2026 endpoints), statistical test/validation (e.g. Spearman on 30d windows), expected edge (PF lift), and integration point in alpha_engine (crypto_onchain_momentum.py or new funding_arb.py). Prioritize BTC/ETH/SOL feasibility. Cite sources.
```

**2. Symbol Universe Pruning / Liquidity Gate Design**:
```
Given CRYPTO's 179 symbols in recent_closed (top: BTC/ETH/ONDO/SOL... including 9+ memes like FARTCOIN/WIF/TRUMP/BRETT/PEPE and mid-alts ONDO/JUP/SUI/TIA/SEI/INJ with likely ADV <$5-10M), design a production-grade liquidity filter (ADV 24h > $X from CoinGecko/Binance free API or cached). Recommend: (a) exact 25-symbol LIQUID_CRYPTO_SYMBOLS list (majors + proven L1, exclude pure memes), (b) runtime gate in production_scanner.py + asset_class.py (with fallback to SECTOR_MAP), (c) risk tiering (meme → research-only per M-038), (d) expected impact on n/volume/PF/WR (target -30% noisy volume, +0.15-0.25 PF lift). Include pseudocode + test against current recent_closed distribution.
```

**3. Source Pruning / Quarantine Decision**:
```
Given these CRYPTO source stats from recent_closed (2891 picks): luxalgo_filters n=678 PF=1.07 WR=45%, alpha_engine n=335 PF=0.99 WR=43%, quan_engine n=305 PF=1.36 WR=35%, copy_trader_highscore n=99 PF=0.80 WR=30%, battleground n=63 PF=0.65, regime_terminal n=65 PF=0.95 WR=32%, mega_mutation n=87 PF=2.29, dna_winner n=103 PF=1.88 — plus historical quan/unknown drag and ml_crypto_pred 95% resolver exclusion + inversion: recommend 3 concrete actions (delete / invert / tighten + volume cap). For each: expected turnover reduction, edge impact (PF/WR), file paths (quality_gates.py, strategy_blocklist.py, config.py), and 30d monitoring metric. Reference M-004 quarantine rule.
```

---

## Step 6: Low-Cost Data & Validation Stack

- **Cache everything**: Glassnode (rate limits), Binance funding/klines/liquidations (WS + REST cache in alpha_engine/data/), CoinGecko vol snapshots (daily JSON), Coinglass. Never hit on every run.
- **Walk-forward / rolling OOS mandatory**: On filtered 25-sym universe only. Use CPCV / PBO per Lopez de Prado (M-052 spike).
- **Monte-Carlo / bootstrap**: For CI on Sharpe/PF/MDD on reduced n (target 95% CI PF>1.5).
- **Truth source**: Live paper trading (tv-paper-trade + smart_picks) vs backtest only metric that matters. 7d/30d rolling WR/PF post-costs (0.1-0.3% crypto + slippage model).
- **Resolver/DB**: Extend DB freshness + cross-db consistency (M-002/M-005); fix ML crypto resolver gaps (aa1).
- **External cheap**: FRED DXY (macro corr M-032), free Dune queries for whale, Binance public endpoints. No paid first 60d.
- **Anti-overfit**: DSR gate (M-012), trust_score (M-006), elite_score per-class, anti_overfit_audit.json.

---

## Step 7: Focused Output — 30/60/90-Day Execution Recommendation

**Pilot**: Liquid Core CRYPTO (BTC/ETH/SOL + 5-7 L1). Not full class expansion until 3 live-profitable 90d (M-062). Target post-90d: PF ≥1.55 / WR ≥50% / n≥100 clean resolved on core (quality > quantity), -25-35% noisy volume share, on-chain/funding contributing 15%+ of CRYPTO PnL.

**30 Days (P0 — Stop the bleeding, shrink + gate)**:
- Implement hard liquidity/ADV filter + LIQUID_CRYPTO_SYMBOLS (~25 names: BTC,ETH,SOL,AVAX,NEAR,SUI,ADA,LINK,ARB + 5-7 more by 30d ADV from CoinGecko cache) in `alpha_engine/production_scanner.py`, `scanner.py`, `asset_class.py` (new `is_liquid_crypto(symbol)` + gate before emit). Update SECTOR_MAP or deprecate memes (M-038). Expected: -30% volume, focus on BTC/ETH/SOL (already high count).
- Quarantine bad sources (M-004): add fn in `audit_trail/quality_gates.py` (read asset_class_concentration.CRYPTO + source PF/WR from dashboard or hf_stats); auto-add to BLOCKED_SOURCE_SYSTEMS / shadow_probation if >40% vol & PF<1.1 or WR<40% 30d rolling (luxalgo tighten, alpha_engine cap, copy_trader/battleground/regime delete, quan_engine volume cap enforce + source whitelist for pilot). Wire in `passes_active_gate` + `score_pick`.
- Enable + extend on-chain: set CRYPTO_ONCHAIN_MOMENTUM_ENABLED=1; extend `crypto_onchain_momentum.py` to SOL (funding + basic onchain if data); add Binance funding_rate_arb sidecar (low-cost, high Sharpe); cache layer. Backtest live Glassnode on BTC/ETH.
- BTC UTC-hour filter (M-001): implement `_hour_filter()` in `alpha_engine/score_booster.py` (env CRYPTO_HOUR_FILTER=1); A/B telemetry.
- Confidence/trust gate (M-034/M-006/M-014): wire inversion gate + trust_score ≥0.6 for crypto in `audit_dashboard/template.html` + `quality_gates`; clamp in dashboard_generator.
- Resolver fix for crypto ML (aa1): audit `forward_validator.py` + `lm_signals` for CRYPTO paths; reduce excluded %.
- Paper: 0.1-0.5% sizing shadow on new filtered core + new features (7d soak, target n≥20 PF>1.4).
- Docs: Update `reports/MASTER_ACTION_PLAN_2026-05-15.md` Section 21 + M-004/M-001 status (Wire-Up compliant PRs only); create `reports/asset_class_90day_plan_CRYPTO_2026-05-15.md` (this file).
- Success: Dashboard shows CRYPTO vol share drop 10%+, core symbols PF lift 0.1+, no new low-liq emissions.

**60 Days (P1 — Validate + pilot paper)**:
- Walk-forward + MC bootstrap on new 25-sym universe (vs old 179); CPCV for on-chain/funding.
- Full paper pilot: 1% risk on Liquid Core (BTC/ETH/SOL focus) with on-chain + funding + hour filter + liquidity gate + DSR/trust. 30d rolling target: PF>1.5 / WR>50 / n≥50 clean. Journal deviations (M-061 skin-in-game prep).
- Extend on-chain (whale tx via free Dune/Coinglass if viable); macro DXY filter (M-032).
- Prune more (mutation lab etc if still emitting); promote 3-4 high-PF sources only for crypto.
- External validation spike: compare to Hyperliquid public leaderboards / MyFXBook crypto analogs / DBMF-style for replication.
- GHA: db-freshness + audit-dashboard for CRYPTO freshness badge.
- Success: Paper PF ≥1.55 WR≥50 n≥80 on core; live dashboard concentration improves (less alt/meme share); M-004 quarantine active + telemetry.

**90 Days (P2 — Scale decision or shrink further)**:
- If paper pilot meets gates (30d clean rolling PF>1.55 WR>50 n≥100 post real costs/slippage, DSR>0.9, corr<0.7 with COMMODITY, no MDD breach): promote to 0.5-1% live sizing (micro skin-in-game $500-2k real per M-061), expand carefully to 30-40 symbols (add 5 DeFi), full Glassnode paid tier if ROI proven. Update master plan institutional schedule CRYPTO pilot date.
- Else (more likely initial): Maintain shrink, double down on on-chain/funding for 3-5 majors only, further quarantine (e.g. luxalgo if no lift), consider "MEMECOIN research-only" permanent. Re-eval universe quality (target <50 syms total for class). No broad expansion.
- Master plan updates: Close M-004/M-001/M-034/M-038 with evidence (reproducible paper log + dashboard delta); add M-0xx for funding_arb wire + ADV gate. Reference Wire-Up Rule + clean branches.
- Overall: CRYPTO moves from "sub-T2 drag" to "focused Tier-2 candidate on liquid core" or "research-only / minimal vol". Contributes to "3 live-profitable classes before 4th" rule. Prioritize COMMODITY pilot to Level 4/5 first.

**Risks / Anti-patterns avoided**: No spread across all 179; no trust backtest without paper; no new complex models before liquidity gate + resolver fix; prune > add (delete 5+ sources); no production risk code without verification.

**Files to touch (Wire-Up compliant, small PRs, opt-in/sidecar where possible)**: `alpha_engine/config.py` (new LIQUID list + enable onchain), `alpha_engine/production_scanner.py` / `scanner.py` (ADV gate), `alpha_engine/crypto_onchain_momentum.py` + new `funding_arb.py` (sidecar), `audit_trail/quality_gates.py` (quarantine + M-004), `alpha_engine/score_booster.py` (hour filter), `alpha_engine/asset_class.py` (helpers), `audit_dashboard/template.html` (trust gate), `strategy_blocklist.py` / BLOCKED. Reference `docs/MUTATION_THREE_AXIS_PROTOCOL.md` for any rehab (not silent kill).

**Expected impact**: -25-40% CRYPTO volume (noise cut), +0.15-0.30 PF / +3-6pp WR on remaining (quality core), on-chain/funding 10-20% of class PnL, path to T2 on pilot sub-universe within 90d. Positions CRYPTO for conditional expansion post-COMMODITY success.

**Next**: Spawn deep-dive subagent if needed for specific source (e.g. luxalgo autopsy) or external replication (Hyperliquid). Update `reports/MASTER_ACTION_PLAN_2026-05-15.md` highest-priority only (M-004 completion). All changes via clean PRs + swarm review per AGENTS.md.

**References** (absolute paths):
- Data: `/mnt/e/findtorontoevents_antigravity.ca/audit_dashboard/data/dashboard_data.json`
- Master: `/mnt/e/findtorontoevents_antigravity.ca/reports/MASTER_ACTION_PLAN_2026-05-15.md`
- Code: `/mnt/e/findtorontoevents_antigravity.ca/alpha_engine/config.py`, `crypto_onchain_momentum.py`, `production_scanner.py`, `asset_class.py`, `quality_gates.py` (audit_trail/), `elite_scorer.py`
- Reports: `asset_class_research_CRYPTO_2026_05_12_0437Z.md`, `backtest_crypto_onchain_2026_05_12_0616Z.md`, `aa1_ml_crypto_pred_autopsy_20260513.md`, `fix_CRYPTO_20260505T005402Z.md`, `audit_asset_feedback_2026-05-05T0121Z_CRYPTO.md`

This plan is ruthless, data-driven, focused on compounding real edge while eliminating waste. Quality over quantity for CRYPTO.

---
*Generated 2026-05-15 per money-maker-continual-improve skill invocation. Pilot asset class for system remains COMMODITY; this is CRYPTO-specific 90d rescue/shrink plan.*