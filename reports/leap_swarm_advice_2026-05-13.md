# Leap Crypto — Swarm Advice 2026-05-13 ~12:40 EDT

**Equity $100,279 | Unrealized +$271.30 | 4 positions, all profitable | Margin 1.1% used**

---

## A. Per-position actions

### 1. COINBASE:SOLUSDC.P — Short 15 @ 95.559 → 91.025 (+$68.00 / +4.74%) — **GATE 4 BREACH**
**Action: PARTIAL_50PCT + SL_TO_BE (immediate)**
- Close 7 contracts at market (~91.025). Locks ~$31.74 realized.
- Move SL on remaining 8 contracts to **95.559** (breakeven).
- Optional trail: SL = max(BE, last + 1.8 × ATR_15m) on each new lower-low close.
- **Rationale:** Gate 4 mandates lock at +3%. SOL is already +4.74% with zero protection — single largest unforced risk in the book. -4.74% in one session is parabolic and "rapid drop, reversal unclear" = textbook partial-and-protect. Keep half the position to ride if continuation, free risk if mean-reversion bounce.

### 2. COINBASE:BTCUSDC.P — Short 0.05 @ 81,189.8 → 79,116.1 (+$103.67 / +2.55%) — **near Gate 4**
**Action: TIGHTEN_SL_TO_80,600**
- Current SL already 81,500 (locked, +$24.5 worst-case lock at this fill — actually locking risk, not profit). Tighten to **80,600** to lock ~$30 realized profit on a stop-out.
- HOLD full size. Price is near bottom of the $79-84k topping range; not at +3% threshold yet so Gate 4 doesn't force partial. The +0.20 BTC/ETH correlation is fine.
- **Rationale:** BTC at range-low has higher bounce risk than continuation. Don't partial yet (under Gate 4), but a tighter stop converts the position from "could give back $103" to "guaranteed +$30, upside open."

### 3. COINBASE:ETHUSDC.P — Short 1.3 @ 2,313.25 → 2,252.10 (+$79.48 / +2.64%) — **approaching Gate 4**
**Action: TIGHTEN_SL_TO_2,300 (just above BE)**
- Set SL = **2,300** (locks ~$17 realized on stop-out, breakeven-plus).
- HOLD full size. Below Gate 4 threshold so no forced partial.
- **Rationale:** ETH/BTC ratio bleeding = thesis intact, want full size for continuation. But +2.64% with no lock invites give-back. SL-to-BE+ is the cleanest pre-Gate-4 hygiene move.

### 4. COINBASE:DOGEUSDC.P — Long 18,000 @ 0.11069 → 0.11181 (+$20.16 / +1.01%)
**Action: HOLD**
- No SL change. Below Gate 4. Acts as alt-beta diversifier vs the 3 shorts (the only LONG in the book — useful net-exposure balance).
- **Rationale:** +1% is noise. Position is the portfolio's hedge against a crypto-wide reversal that would torch BTC-S/ETH-S/SOL-S simultaneously.

---

## B. New picks tonight

**SKIP — no edge worth opening.**

Reasons (any one is sufficient):
- Edge-stability index flags **CRYPTO = DECAYING_EDGE**.
- Book already carries 3 SHORTs (BTC/ETH/SOL) — adding a 4th SHORT breaches intra-class correlation hygiene; adding a 2nd LONG (only XRP-L available — BTC/ETH/SOL/DOGE all taken or netted) lacks thesis given bearish crypto stance.
- XRP-L would also create a cross-account check vs theswarm/zerounderscore that hasn't been pre-cleared (Gate 2).
- Current book is already running +$271 with $1,076 margin — adding risk for marginal edge while Gate 4 is mid-action on SOL = bad sequencing.

Better use of the next hour: execute Section A, then re-evaluate after SOL partial fills.

---

## C. Honest verdict

**Well-constructed but under-protected.** Four positions, four winners, balanced direction (3S/1L), 1.1% margin used, well-diversified across the 5-symbol universe — this is a tidy book, not a cluttered one. The problem is **risk hygiene, not composition**: SOL-S is +4.74% with zero lock (Gate 4 violation right now), ETH-S is one tick from Gate 4 with no lock, and BTC-S has a SL but it's locking *risk* rather than *profit*. Fix that in the next 10 minutes (Section A) and the book goes from "three unforced give-back exposures" to "all profit locked, all theses still running." No need to add picks — execute the hygiene pass and let the existing book work.

**Word count: ~575**
