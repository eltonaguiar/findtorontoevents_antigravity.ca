# TV Paper Portfolio Decisions — 2026-04-04 18:25 UTC

**Decision authority:** claude-bus-setup (user delegated)
**Inputs:** 5 portfolio screenshots + subagent research on 209 active picks in `audit_dashboard/data/dashboard_data.json` + bus consensus from 2026-04-04-18 debate.

---

## 📊 Per-portfolio verdict

| Portfolio | Equity | User verdict | My verdict | Action |
|---|---|---|---|---|
| **SCALPER** ($2K) | $1,989 | "failing" | Over-leveraged swings forced into scalp box | CLOSE 3 losers, reduce count |
| **TESTER** ($3K) | $3,005 | "latest picks aren't good" | SHORTs underperforming, LONGs barely moving | CLOSE worst SHORT, tighten up |
| **TRUSTOURSCORE** ($90K) | $90,318 | "looking decent" | Concur — 4/5 profitable | HOLD (do not touch) |
| **BROKIE** ($1K) | $1,003 | "solid, consistent wins" | Concur — +$3 profit, 3 positions | HOLD (do not touch) |
| **zerounderscore** ($100K) | $100,224 | "ALGO backfired" | ALGO-L is 30% of equity, −$548 | CLOSE ALGO, add diversifiers |
| **THEWINNERS** ($1K) | $999 | "inconclusive" | Not my portfolio (claude-opus-trading-strategies) | NO ACTION |

---

## 🎯 Executive decisions

### 1. CLOSE list (5 trades)
| Portfolio | Symbol | Side | Reason |
|---|---|---|---|
| zerounderscore | ALGOUSDT | LONG | 30% concentration, −$548 (−1.82%) |
| SCALPER | ALGOUSDT | LONG | −1.90%, not recovering |
| SCALPER | AVAXUSDT | SHORT | −1.69%, against 7/10 consensus LONG |
| SCALPER | DOGEUSDT | SHORT | −1.62%, noise, no edge |
| TESTER | AVAXUSDT | SHORT | −2.03%, worst in portfolio |

### 2. ADD list (4 trades from subagent research, all PROVEN tier + sweet-spot conf)
| Portfolio | Symbol | Side | Conf | SL | TP | Entry | Rationale |
|---|---|---|---|---|---|---|---|
| zerounderscore | FILUSDT | LONG | 0.759 | 0.8251 | 0.8672 | 0.8419 | PROVEN + super_pick sp=120 (ml_crypto) |
| zerounderscore | POLUSDT | LONG | 0.794 | 0.0907 | 0.0936 | 0.0917 | PROVEN + super_pick sp=118 + 1.1% SL |
| SCALPER | XLMUSDT | LONG | 0.787 | 0.1597 | 0.1654 | 0.1616 | PROVEN + 1.2% SL fits scalp box |
| TESTER | USDCHF=X | SHORT | 0.869 | 0.8074 | 0.7874 | 0.7994 | FX diversifier, HMM-gated regime_terminal |

### 3. HOLD decisions
- **TRUSTOURSCORE**: don't touch — all profitable or flat. Concentration in BTC (~50%) noted but it's winning.
- **BROKIE**: don't touch — +$3 profit, clean 3-position setup.

---

## 🧮 Scoring adjustments (observed problems → recommended code changes)

These are observations for the scoring pipeline team — **not changes I'm making autonomously** (that's their code). Filing as bus tasks.

### Problem 1: Cross-portfolio concentration
ALGOUSDT LONG was scored high enough to be placed in **3 separate portfolios** (SCALPER, TRUSTOURSCORE, zerounderscore). All losing ~1.8-1.9%. The scoring system doesn't know which portfolios already hold a symbol when it ranks.

**Fix:** `smart_picks_engine.py` should accept a `held_symbols_across_portfolios` set and apply a **diversification penalty** (−10 score per portfolio already holding it).

### Problem 2: No position-size awareness
zerounderscore put 30% of equity into ALGO-L. No scoring system should score a single pick high enough to warrant 30% position size.

**Fix:** Position sizing should be based on (a) portfolio rules (SCALPER=3-5% per trade, TRUSTOURSCORE=5-10%), (b) signal conviction cap (max 15% even for highest-conviction PROVEN + super_pick).

### Problem 3: SHORT scarcity in BEAR regime
Per subagent research: regime=BEAR on 58/64 valid picks, yet 106/126 picks are LONG. Only 20 SHORTs, 1 RELIABLE, 0 PROVEN. Structural long bias against regime.

**Fix:** In BEAR regime, invert scoring for LONG picks by +strategy_short_wr bonus.

### Problem 4: elite_score=None on 96% of picks
Per copilot's analysis: this is MOSTLY by design (forward-walk gate fwd_WR<45% filters). However, a `rank_by_elite_only_if_populated` flag would prevent BANNED-tier picks from surfacing at top.

**Fix:** When sorting by elite_score DESC, exclude rows where `trust_tier == 'BANNED'` regardless of elite_score value.

---

## 📝 Execution plan

1. **Code/data changes:** None direct. Scoring observations filed as bus tasks.
2. **TV trades (execute via MCP):** 5 closes + 4 opens = 9 trades across 3 accounts (zerounderscore, SCALPER, TESTER).
3. **HOLD:** TRUSTOURSCORE, BROKIE, THEWINNERS (not touched).

## 🛎️ Coordination

- Bus broadcast sent with summary + per-portfolio verdict
- Scoring observations filed as `bus:tasks:pending` for smart_picks_engine/dashboard_generator teams
- Portfolio locks (`lock:portfolio:*`) held for 1h

## Rationale summary

Focus on **removing concentration + losers first** before adding new positions. Don't churn TRUSTOURSCORE/BROKIE which are working. Add only PROVEN tier + sweet-spot confidence picks with tight SL% to match each portfolio's risk profile.
