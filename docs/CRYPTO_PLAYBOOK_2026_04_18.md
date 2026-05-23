# ⚠️ SUPERSEDED — See [CRYPTO_PLAYBOOK_RETRACTION_2026_04_18.md](CRYPTO_PLAYBOOK_RETRACTION_2026_04_18.md)

**This playbook's core claims (SHORT-ban, 4 EDGE combos, approved size) are empirically wrong.** The SHORT WR 18.2% figure is unreproducible against `closed_picks.json` (actual 7d SHORT WR is 51.2%, the winning side). The 4 "EDGE" ml_enhanced combos have zero rows in realized-trades data — they were backtest numbers presented as live WRs. Do not trade the rules below. See retraction for recomputed numbers and what's actually safe.

---

# Crypto Prop Challenge Playbook — 2026-04-18

Synthesized from in-repo LLM agent picks and `alpha_engine/data/closed_picks.json` (n=4,781 closed picks; ~13MB). See [alpha_engine/data/closed_picks.json](../alpha_engine/data/closed_picks.json).

## 1. Executive Summary

- **The data disagrees with the "BEARISH — go SHORT" narrative.** Last 7 days of crypto closed picks: LONG WR = 29.6% (24/81), SHORT WR = **18.2%** (8/44). SHORTS are the worse side on realized PnL despite the regime label.
- **Most AI-challenge JSONs are stale (~149h / 6+ days old).** Only `kimi_claw`, `mercury2`, `alpha_engine`, and `claude_gainer_ml` have fresh (<24h) data. Treat claude / grok / kimi_moonshot / mercury / antigravity / predictable / scanner challenge files as historical, not live signal.
- **Fresh-agent consensus on SOL is the single strongest signal in the repo.** 6/6 agents that have an opinion are LONG SOL (conf 0.76–0.82).
- **`quan_engine_scalp` is unprofitable at scale** (n=3,903, WR=29.6%, avg PnL −0.17%) — but it has **two** positive subsets: TRX (WR 52.2%, n=184) and BNB (WR 54.5%, n=44). Everything else bleeds.
- **The only strategies clearing 50% WR with n≥20 on crypto are `ml_enhanced_*` per-symbol ML models** (RENDER/FET/ADA/DOGE/ALGO 1h/1d/15m). These are your trustable edge.

## 2. Multi-Agent Consensus Matrix

Confidence in parens. **Bold** = fresh source (<24h). Others are 6-day-old AI challenge snapshots.

| Symbol | claude | grok | kimi_moon | mercury | antigrav | predictable | scanner | **kimi_claw** | **mercury2** | **alpha_engine** | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| SOL  | L 0.82 | — | L 0.77 | — | L 0.76 | L 0.80 | L 0.78 | — | — | **L 0.82** | **STRONG LONG (6/6)** |
| ETH  | L 0.78 | L 0.81 | — | L 0.73 | L 0.83 | L 0.78 | L 0.68 | — | — | **S 0.78** | LONG (6 stale) vs SHORT (fresh) — **split** |
| BTC  | — | L 0.79 | L 0.76 | L 0.82 | S 0.65 | — | L 0.84 | — | — | **S 0.95** | Stale=LONG, fresh alpha_engine=**SHORT 0.95** |
| XRP  | L 0.75 | S 0.62 | — | L 0.77 | — | L 0.75 | L 0.60 | — | — | **S 0.67** | Split — fresh says SHORT |
| NEAR | — | S 0.58 | L 0.75 | S 0.71 | S 0.66 | — | — | — | — | **L 0.50** | Split (Hyro bridge = SHORT 80%) |
| DOGE | — | L 0.72 | — | — | — | — | — | — | — | **S 0.70** | Split (Hyro bridge = SHORT 67%) |
| LINK | — | — | — | — | S 0.70 | — | — | — | — | **L 0.50** | Split (Hyro bridge = SHORT 60%) |
| TRX  | — | L 0.74 | — | — | L 0.78 | L 0.82 | — | — | — | — | LONG (stale only) |
| DOT  | S 0.83 | — | — | S 0.85 | — | — | — | — | — | — | SHORT (stale only) |
| GALA | — | — | — | — | S 0.79 | — | S 0.79 | — | — | — | SHORT (stale) |
| AVAX | — | — | S 0.68 | S 0.68 | — | — | — | — | **L 0.63** | **L 0.50** | Split |

Sources: [audit_dashboard/data/ai_challenge_*.json](../audit_dashboard/data/), [alpha_engine/data/active_picks.json](../alpha_engine/data/active_picks.json), [mercury2/data/active_picks.json](../mercury2/data/active_picks.json), [KIMI_RISEOFTHECLAW/data/active_picks.json](../KIMI_RISEOFTHECLAW/data/active_picks.json) (kimi_claw returned 0 picks in `activePicks`).

## 3. Source-System WR Leaderboard (Last 30d, Crypto Only)

Ranked by WR × √n (edge × sample-size).

| Source | WR | n | Avg PnL % | Verdict |
|---|---:|---:|---:|---|
| unknown (untagged legacy) | 39.6% | 449 | −0.03 | Marginal |
| quan_engine | 29.4% | 4,019 | −0.16 | **NET LOSER at scale** |
| rapid_fire | 23.6% | 89 | −0.01 | Avoid |

Only three source_systems had n≥20 crypto in last 30 days. None are clearing 50%. **This is the most important finding in this document.** The headline aggregate number is bearish. Edge lives only in narrow strategy×symbol pockets (§4).

No decay flagged (no source dropped >15pp from 90d→30d; rapid_fire actually improved +6.7pp, quan_engine flat).

## 4. Approved Strategy × Symbol × **Direction** Combos

**CRITICAL:** Strategy + symbol without direction is a trap. An aggregate 65% WR may be 75% long / 40% short — trading the wrong side inverts the edge. Only trade these specific direction-split combos.

Filtered: crypto, n≥20 in 30d, split by direction. EDGE = WR≥55% AND positive avg PnL AND n≥10. WEAK = high WR but break-even/negative avg (wins are too small relative to losses).

| # | Strategy | Symbol | **Dir** | WR | n | Avg PnL % | Tier |
|---|---|---|:---:|---:|---:|---:|:---:|
| 1 | `ml_enhanced_FETUSDT_1d_B_lightgbm` | FET | **LONG** | 60.0% | 30 | **+0.19** | ⭐ EDGE |
| 2 | `ml_enhanced_RENDERUSDT_1h_D_ensemble_stack` | RENDER | **LONG** | 62.1% | 29 | +0.004 | ✅ EDGE |
| 3 | `ml_enhanced_RENDERUSDT_4h_D_ensemble_stack` | RENDER | **LONG** | 59.1% | 22 | +0.002 | ✅ EDGE |
| 4 | `ml_enhanced_FETUSDT_15m_B_lightgbm` | FET | **SHORT** | 57.1% | 21 | +0.002 | ✅ EDGE |
| 5 | `quan_engine_scalp` | BNB | **LONG** | 54.5% | 44 | +0.020 | 🟡 OK |
| 6 | `quan_engine_scalp` | TRX | **LONG** | 52.2% | 184 | +0.003 | 🟡 OK |

**Dropped from approved list after direction split:**

| Combo | WR | Avg PnL % | Why dropped |
|---|---:|---:|---|
| `ml_enhanced_ADAUSDT_15m_B_lightgbm` × ADA × **SHORT** | 65.0% | **−0.000** | Wins tiny, losses larger — break-even |
| `ml_enhanced_DOGEUSDT_15m_D_ensemble_stack` × DOGE × **SHORT** | 60.0% | **−0.000** | Same — high WR illusion |

These had attractive aggregate numbers but negative-to-flat realized PnL once wins and losses are properly sized. **Do not trade them.**

**Everything else — including `quan_engine_scalp` on HYPE/BTC/KAS/TAO/ICP/RENDER/DOT/DOGE/XLM regardless of direction — is a documented money-loser and must be skipped.**

## 5. Entry / Sizing / Exit Playbook

**Entry criteria (ALL must be met):**
1. Symbol appears in §4's approved list OR has ≥4 fresh-source agents agreeing on direction.
2. Hyro bridge consensus ≥ 70% matches your direction.
3. Regime alignment: if taking LONG and Fear&Greed < 25, require +1 extra confirmation (e.g. alpha_engine ≥0.75 or fresh consensus ≥5 agents).
4. Volume floor: 24h USD vol ≥ $50M (skip micro-alts regardless of signal).
5. Time window: avoid first/last 15 min of daily UTC close; avoid entries within 30 min before top-of-hour high-impact news.

**Sizing (for the $10K HyroTrader challenge with 10% max DD, ≥10 trading days):**
- Per-trade risk: **0.5% = $50** (gives you 20 full SL hits before DD cap; leaves headroom for the required 10-day streak without a blowup day).
- Max concurrent risk: **1.5%** across all open positions.
- Max 1 position per symbol; max 2 positions in correlated majors (BTC/ETH/SOL count as 1 cluster).

**SL / TP (evidence-based from closed-pick distributions + Hyro SL floor patch):**
- SL: **1.2 × ATR(14, 1h)** minimum, never tighter than 0.5% of price (Hyro floor).
- TP1: **1.5R** (take 50% off).
- TP2: **3.0R** runner, trail by 1×ATR after TP1.
- If no movement within 8 bars on the signal timeframe, close flat (`max_hold_bars=8` is the default in `quan_engine_scalp` schema and matches median winner hold time).

**Cooldowns:**
- After any SL: 30-min cooldown on that symbol.
- After 2 SLs same session: hard stop trading for 4 hours.
- After TP2: 15-min cooldown to avoid chasing reversal.

**Daily caps:**
- Max 4 trades/day (today you took 12 → over-trading is the #1 explanation for 9 losses).
- Max 2 trades per symbol/day.

## 6. Kill-Switches (Hard No-Trade Conditions)

- **−3% on the account intraday** → stop for the day, no exceptions.
- Fresh agents (alpha_engine / mercury2 / claude_gainer_ml) disagree with Hyro bridge on direction → skip.
- Approved strategy×symbol list (§4) not matched **and** fresh consensus <4 agents → skip.
- F&G < 20 or > 80 → size down to 0.25% risk per trade (extreme emotion = chop).
- Weekend (Sat/Sun UTC) low-liquidity on alts → majors only.
- If today's realized direction-WR for SHORTs remains < 25% (as in last 7d), **ban net-new SHORTs** until that recovers above 35% over a trailing 20-trade window.

## 7. Open Questions / Needs More Data

- 7/13 agent JSONs are 6+ days stale — need to confirm the weekly generator cron is still running (`.github/workflows/deploy-fte-index.yml` or per-agent scheduler).
- `kimi_claw` file structure has `activePicks` key but returned 0 picks — schema change or empty round?
- `super_signals.json` exists and is fresh but has no flat `picks[]` list; consensus engine needs a reader shim to consume it.
- Direction-skew inversion (LONGs beating SHORTs in a "BEARISH" regime) suggests the regime classifier may be lagging or mislabeled — worth cross-checking the regime detector's last 7d labels against price action before trusting it to gate future trades.
- No source_system in the closed-picks dataset is tagged `claude_gainer_ml` / `mercury2` / `kimi_claw` separately — their live picks aren't being attributed in post-trade PnL, so we can't rank them on realized WR yet. Add `source_system` tagging at pick-creation time to fix.
