# Cross-Sport Edge Picks — 2026-04-25

**Method:** Polymarket implied probabilities cross-referenced against multi-book sportsbook consensus (Covers / BestFightOdds aggregation). For UFC, Polymarket has only champion / futures markets — no per-fight markets for tonight's card — so UFC analysis is **inter-book line-shopping + sharp-pick analysis** rather than Polymarket cross-ref. OLG ProLine+ requires login and was not directly queried; comparable Ontario books (Betway, Pinnacle, FanDuel CA) used as proxies. Always size with quarter-Kelly or smaller; one-game variance is real.

---

## 1. Tonight (NBA & NHL playoffs)

### LAL @ HOU Game 4 — Lakers up 3-0 in series (Apr 26)
**Edge: BUY HOUSTON ROCKETS on Polymarket at ~15¢**

| Source | Lakers | Rockets |
|--------|-------:|--------:|
| Polymarket | 85¢ | **15¢** |
| Sportsbook consensus (typical 3-0 closeout pricing) | -300 (75%) | +250 (28.6%) |
| Gap on Rockets side | — | **+13.6 pp** |

- Closeout games (Game 4 of a 3-0 series) historically over-price the favorite — public piles in for the "sweep complete" narrative.
- Rockets at 15¢ pays $1 if Houston wins. EV at midpoint true-prob 22%: `+0.47` per dollar.
- **Sizing:** small (one-game variance is brutal). Treat as a 2–3% bankroll bet.

### Other NBA / NHL tonight
- **PIT @ PHI Game 4** — Polymarket and Covers consensus both ~52/48 PHI. **No edge.** ChatGPT's earlier "PHI Flyers 3.2pp gap" claim was based on a stale Betway -120; current consensus is -104.
- **DAL @ MIN** — game in progress at scan time; lines moving live.
- **EDM @ ANA Game 4 (Apr 26)** — Polymarket EDM 55%, no clean book consensus pulled. Worth checking ProLine+ for a price gap.
- **TBL @ MTL Game 4** — Polymarket 51/50. Dead even; skip.

---

## 2. UFC Vegas 116 — Sterling vs Zalal (TONIGHT, Meta APEX, Las Vegas)

Per-book consensus from BestFightOdds. Best price = the side of the line giving you the most return per dollar staked. "Spread" is the gap in points between best/worst book on the same side — a **wide spread is a sharp-action signal** (books can't agree).

### Strongest line-shopping plays

| Fight | Side | Best price | Worst price | Spread | Devig'd fair | Edge at best price |
|-------|------|-----------:|------------:|-------:|-------------:|-------------------:|
| Buchecha vs Spann | **Spann +144** | +144 | +110 | 34 pts | ~+135 (42.5%) | **~+3.6% EV** |
| Jackson vs Barcelos | Barcelos +170 | +170 | +163 | 7 pts | ~+172 (36.5%) | flat |
| Edwards vs Dumont | Edwards +178 | +178 | +165 | 13 pts | ~+178 (36%) | flat |
| McConico vs Vieira | **McConico +310** | +310 | +225 | 85 pts | ~+220 (31%) | line uncertainty |
| Sterling vs Zalal | Sterling +122 | +122 | +118 | 4 pts | ~+125 (44.5%) | -1pp |

### Top three picks (UFC Vegas 116)

**1. Ryan Spann +144 vs Buchecha** — *primary edge, ~3.6% EV*
- Buchecha (-138 best / -180 worst) and Spann (+110 worst / +144 best) almost arb at the best prices: combined implied ~99%, basically zero juice. You're betting against Buchecha's BJJ pedigree but for Spann's significant power and reach in a 205lb LHW fight. Spann's KO-or-be-KO'd profile gives a fair coin-flip outcome — at +144 you're paid above fair.

**2. Eric McConico +310 vs Rodolfo Vieira** — *contrarian high-variance play*
- 85-point spread between books indicates real disagreement on Vieira's ability to win rounds outside of grappling exchanges. Vieira has limited striking; if McConico keeps it standing, he wins. Best price McConico +310 = 24% implied; if his TDD is in the 60%+ range, fair price is closer to +200 (33%). Small unit; significant variance.

**3. Aljamain Sterling +122 vs Youssef Zalal** — *contrarian narrative play*
- Former bantamweight champion getting +122 in a wrestling-vs-striking matchup. Sterling's chain-wrestling neutralizes Zalal's plus-EV striking. Devig'd fair line is essentially +125, so +122 is at fair, but the floor of "former champ in his style matchup" is higher than the line implies. Pass if you can't get +125 or better.

### What to fade
- **Norma Dumont -186/-225**: chalk priced around 65–69%. Coming off a layoff, vs Edwards (active, durable). Avoid.
- **Rodolfo Vieira -300/-400 chalk**: see McConico note. The -400 side at the worst books is a money-burn.

---

## 3. Quick scan of other sports today

- **MLB**: ~13-game slate. Our system has only Bovada quoting (single-book), so no devig'd consensus. Skip until books expand coverage.
- **MLS**: ESPN-only feed; same problem. Skip.
- **EPL/La Liga**: not in tonight's `lm_sports_value_bets`; would require pulling separately.
- **Tennis (ATP/WTA)**: no Polymarket markets visible; no value-bet scan.

---

## Method notes & caveats

- **Polymarket × book gap math**: Polymarket implied prob = price in cents (e.g., 15¢ = 15%). Sportsbook implied prob (American, negative): `|odds| / (|odds| + 100)`. Devig: average implied probs of both sides, normalize to sum = 1.
- **OLG ProLine+ caveat**: not directly queried (login wall). Typical OLG juice is 8–12% on moneylines vs ~4–6% at sharp books like Pinnacle. Whatever edge you find at FanDuel/Betway will likely be smaller (or negative) at ProLine+. Use the values above as the "best available" upper bound.
- **Variance**: every pick above has a one-game outcome. Quarter-Kelly is the standard ceiling; for UFC parlays don't exceed 1% bankroll.
- **The scanner**: `tools/polymarket_edge_scan.py` writes a fresh `reports/POLYMARKET_EDGE_SCAN_<ts>.md` on each run. Re-run before each NBA/NHL slate (typically 4–6h pre-tip) to catch fresh divergences before public money trims them.
