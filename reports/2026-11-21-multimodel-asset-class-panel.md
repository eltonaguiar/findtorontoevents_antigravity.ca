# Multi-model panel — strategies per asset class (2026-11-21)

**Question put to the models:** for each of CRYPTO, EQUITY, ETF, FOREX, COMMODITY,
BOND, name one concrete strategy (universe, signal, entry, exit, holding period,
sizing), the single forward number that would falsify it, a 0-100 confidence, and
— if nothing can clear the bar — the one configuration change most likely to
reveal an edge the current tests hide.

Every prompt carried the **mandatory leakage-context block** (H-101 COT T+3 lag,
M-095 cotton 14× re-emission, M-069 net-vs-gross reclassification, circular
`quality_bucket`) plus the measured ledger, so no model could answer from priors
alone:

| class | n | net exp/trade | net 95% CI | verdict |
|---|---|---|---|---|
| CRYPTO | 6,836 | −0.380% | [−0.647, −0.114] | KILL |
| EQUITY | 955 | +0.098% | [−0.516, +0.720] | WEAK |
| ETF | 589 | −0.003% | [−0.420, +0.450] | WEAK |
| FOREX | 264 | — | includes 0 | WEAK |
| COMMODITY | 48 | PF 0.29 policy-clean | — | KILL |
| BOND | 37 | below floor | — | WEAK |
| FUTURES | 4 | — | — | INSUFFICIENT_N |

Search space quoted to them: 629 CRYPTO cells, 19 EQUITY, 12 ETF, 18 FOREX,
9 COMMODITY, 3 FUTURES, 2 BOND.

## Who actually answered

Round 1 (per-class proposals): **Nemotron-3-Ultra 550B** (kilo), **openrouter/free**,
**deepseek-r1:32b** (local Ollama).
Round 2 (critique of round 1, different models): **Nemotron-3.5-Super-VL**,
**Nemotron-3.5-Lightning**, **recursive/flint-v1.0**, **reflection/beam-free**,
**Nemotron-3-Ultra** again.

Failed routes, recorded rather than hidden: `consult_multi` 12 of 14 providers
(410 Gone for nvidia, 404 groq/cerebras/fireworks, 401 together, 429 mistral,
403 aimlapi, 402 hypereal, DNS failure github_models, malformed URL gemini_api —
its key is being read with trailing whitespace, and the error echoed the key into
the URL, so the captured logs were redacted before being committed);
`gemini` CLI (ineligible tier), `grok` CLI (401), Kilo paid models
(gpt-6.2-astra/sol, qwen4-max: "add credits"), `opencode-zen/qwen3.6-plus`
(unavailable), Cloudflare gpt-oss-20b (read timeout), `particle-ai` and
`baidu/ernie` (spent their budget running `find /` against the filesystem instead
of answering — free models in a tool-bearing "code" agent need an explicit
no-tools instruction, which is why round 2 carries one).

## Round 1 — what each model proposed

**CRYPTO** — all three call it blocked at class level. Nemotron: "no strategy
family can overcome this without a regime filter that survives forward test".
OpenRouter's configuration change: benchmark against **cash, not BTC-hold**, and
require a funding-rate filter on entry. No model proposed a live crypto rule.

**EQUITY** — Nemotron: SPY/S&P-500 RSI(2)<10 at close, enter next open, exit day 2
or RSI(2)>90, ~1% risk/vol-target 15%, conf 35. deepseek-r1: EMA crossover with RSI
filter, conf 50. Round 2 rejected the 2-day horizon in favour of 20–60 days.

**ETF** — Nemotron: 11 SPDR sectors ranked on 63-day return, long top 3 equal
weight, month-end rebalance, conf 30. deepseek: RSI+EMA momentum, conf 40.
OpenRouter: long factor / short SPY to isolate alpha.

**FOREX** — Nemotron: G10 carry, 3-month rate-differential rank, long top 3 /
short bottom 3, weekly rebalance, vol-target 10%, conf 25. deepseek: high-yield
carry, conf 30. OpenRouter: G10 carry + 3M trend, 2-week max hold.

**COMMODITY** — nobody proposed a strategy; all three declared it blocked by
H-101/M-095. OpenRouter's remedy (T+3 embargo + dedup by signal date) is
data hygiene, not an edge.

**BOND** — Nemotron: 2s10s steepener on TU/TY when the spread <5bp, DV01-neutral,
exit >25bp or 30 days, conf 20. deepseek: "insufficient data to propose a
strategy". OpenRouter: expand to global govvies + IG credit, 3M hold.

**FUTURES** — no proposal; n=4.

## Round 2 — what the critics converged on (4 of 4 independently)

1. **"Every class is blocked" is a category error.** CRYPTO is genuinely blocked
   (CI excludes zero *on the negative side*). EQUITY and ETF are **inconclusive /
   underpowered** — their CIs include zero, which cannot rule out a subset edge the
   aggregate dilutes. BOND and FUTURES are blocked by *sample size*, which is not
   the same claim as blocked by *edge*. Beam phrased it best: "blocked applies to
   the current aggregate, not the search space".
2. **The single defensible next experiment** (4 of 4, unprompted agreement):
   pre-register an **EQUITY mid-cap quality subset**, 20–60 day holds,
   factor-matched benchmark, 2× slippage + funding, promote only at n≥100 forward
   rows, net CI excluding zero, IR≥0.5 — falsifiable in 90 days. Confidence 55–80.
3. **Specific round-1 errors they caught:** Nemotron's per-class "conf 35/30/25/20"
   is undefined (not a p-value, posterior or CV score) and therefore unfalsifiable;
   "benchmark against factor models" is unfalsifiable unless the factor set and
   holding window are declared *before* the run, otherwise any result can be
   reframed post hoc as alpha; the commodity embargo does not help a class already
   below the n floor.

## SubQ (Decisions API, `subq-snap-1.2`) — bare vs measured

Two arms, both HTTP 200, same questions, second arm given the ledger
(`subq_run_20261121T090909Z.json`):

| question | P(yes) bare | P(yes) with evidence |
|---|---|---|
| closing CRYPTO on the negative aggregate is justified | 0.129 | 0.417 |
| any class is a defensible forward-test candidate | 0.225 | **0.054** |
| longer holding periods are the highest-leverage fix | 0.454 | 0.341 |
| model consensus is evidence about the edge | 0.009 | **0.004** |

Read honestly: SubQ moves toward "yes, closing CRYPTO is defensible" once it sees
the CI, still short of a majority; it says **no class is promotable on current
numbers** (0.054), which does not contradict the panel — the panel proposed an
*experiment*, not a promotion; and it scores model agreement as evidence at
0.004, i.e. this document is a hypothesis generator, not proof. Longer holding
periods are *not* endorsed by SubQ (0.34), so that part of the consensus is
contested rather than settled.

## What I take from it

- **Do not close CRYPTO.** Negative aggregate, but 629 cells means the aggregate is
  an average over a search, not a ceiling on any subset. Do not add more CRYPTO
  cells without the global trial counter, or the DSR debt grows silently.
- **EQUITY is the only class with a convergent, falsifiable proposal.** Register it
  before any backtest (rule M-107): subset definition, factor benchmark named
  explicitly, 20–60 day window fixed, baseline = EQUITY aggregate n=955,
  +0.098%, CI [−0.516, +0.720] so the subset is compared against the diluted
  aggregate rather than in isolation.
- **FOREX proposals are untestable as written.** `fx_prices` is stale to
  2026-02-09; carry/trend rules cannot be evaluated until it is backfilled, so
  any FX answer in this panel is an opinion about markets, not about this system.
- **BOND's steepener needs a Treasury-futures feed** (TU/TY) that is not among the
  data artifacts inspected here; treat that proposal as untestable in-repo until a
  feed exists.
- **COMMODITY** stays closed; the embargo/dedup work is required for data honesty
  but cannot manufacture an edge from 48 picks.

## Evidence and reproduction

Raw replies (ANSI-stripped, secrets redacted) in
`reports/2026-11-21-multimodel-panel/`; SubQ payload in the same directory.

```bash
# round 1 (per-class)
python3 tools/consult_multi.py --fanout all --prompt-file /tmp/q_classes.md --out-dir /tmp/fan1
kilo run -m kilo/nvidia/nemotron-3-ultra-550b-a55b:free --dir /tmp/consult "$(cat /tmp/q_classes.md)"
# round 2 (critique)
kilo run -m kilo/nvidia/nemotron-3.5-super-vl:free --dir /tmp/consult "$(cat /tmp/q2.md)"
# SubQ, bare vs evidence
python3 tools/subq_consult.py --questions /tmp/subq_q.json --out /tmp/subq_out
```

Caveat that survives the whole document: these are model opinions conditioned on
a ledger snapshot. The ledger itself reconciles 8,733 of 14,811 closed picks
(59.0%), so the unmeasured 41% could still change any class verdict.
