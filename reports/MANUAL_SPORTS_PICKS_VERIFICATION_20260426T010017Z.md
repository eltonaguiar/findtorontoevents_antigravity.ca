# Manual Sports Picks Verification — 20260426T010017Z

Cross-checks the curated UFC/Tennis/Golf picks in `live-monitor/sports-betting.html` against Polymarket Gamma API last-trade prices.

**Verdicts:**

- `polymarket_confirms_edge` — Polymarket gap and manual gap both lean the same way ≥ 2pp.

- `polymarket_alone_signals_edge` — Polymarket gap ≥ 5pp but manual model didn't flag it (or no manual prob).

- `polymarket_disagrees_strongly` — Polymarket says the opposite of the manual call by ≥ 5pp.

- `soft_signal` — small gap (2–5pp).

- `polymarket_neutral` — gap < 2pp; no edge vs market.

- `no_polymarket_match` — no fuzzy match found on Polymarket.


## ufc_mma

| Date | Matchup | Pick | Odds | Book impl % | Manual WP % | Poly impl % | Poly−Book pp | Verdict | Poly market |
|---|---|---|---|---:|---:|---:|---:|---|---|
| 2026-04-25 | Rafa Garcia vs Alexander Hernandez | Rafa Garcia | +130 | 43.48 | — | — | — | no_polymarket_match |  |
| 2026-04-25 | Aljamain Sterling vs Youssef Zalal | Aljamain Sterling | +120 | 45.45 | — | — | — | no_polymarket_match |  |
| 2026-05-02 | Carlos Prates vs Jack Della Maddalena | Carlos Prates | +100 | 50.0 | — | — | — | no_polymarket_match |  |
| 2026-05-09 | Sean Strickland vs Khamzat Chimaev | Sean Strickland | +450 | 18.18 | — | — | — | no_polymarket_match |  |

## tennis_atp

| Date | Matchup | Pick | Odds | Book impl % | Manual WP % | Poly impl % | Poly−Book pp | Verdict | Poly market |
|---|---|---|---|---:|---:|---:|---:|---|---|
| 2026-05-24 | Carlos Alcaraz vs Jannik Sinner | Carlos Alcaraz | +150 | 40.0 | 42.0 | 1.15 | -38.9 | polymarket_disagrees_strongly | Will Carlos Alcaraz win the 2026 Roland Garros Men's Singles |
| 2026-05-25 | Alexander Zverev vs Novak Djokovic | Alexander Zverev | +200 | 33.33 | 35.0 | 10.5 | -22.8 | polymarket_disagrees_strongly | Will Alexander Zverev win the 2026 Men's Singles tournament  |
| 2026-05-02 | Taylor Fritz vs Jack Draper | Taylor Fritz | -110 | 52.36 | 52.0 | 0.25 | -52.1 | polymarket_confirms_edge | Will Taylor Fritz win the 2026 Roland Garros Men's Singles? |

## golf_pga

| Date | Matchup | Pick | Odds | Book impl % | Manual WP % | Poly impl % | Poly−Book pp | Verdict | Poly market |
|---|---|---|---|---:|---:|---:|---:|---|---|
| 2026-05-14 | Scottie Scheffler vs Field | Scottie Scheffler | +400 | 20.0 | 20.0 | — | — | no_polymarket_match |  |
| 2026-05-14 | Rory McIlroy vs Field | Rory McIlroy | +650 | 13.33 | 13.3 | — | — | no_polymarket_match |  |
| 2026-05-14 | Tommy Fleetwood vs Field | Tommy Fleetwood | +3300 | 2.94 | 3.0 | — | — | no_polymarket_match |  |
