# Audit Dashboard Link Fixes — March 13, 2026

## Problem

Multiple system links (`sysLinks` mapping) in `audit_dashboard/template.html` pointed to pages that never existed, causing 404 errors when users clicked system names on the audit dashboard.

### Dead Pages Identified

| Dead URL | Linked From |
|----------|-------------|
| `/findcryptopairs/ml_edge.html` | crypto_ml_edge |
| `/findcryptopairs/mercury.html` | mercury2, mercury2_fast, revival_mercury2 |
| `/findcryptopairs/paper_trading.html` | paper_trading, revival_paper_trading |
| `/findcryptopairs/crypto_winners.html` | crypto_winners |
| `/findcryptopairs/ml_predictions.html` | ml_crypto_pred, predictions, ml_crypto_predictor |
| `/findcryptopairs/signals.html` | crypto_signal_engine, super_signals, revival_signal_engine, signal_engine_mutations |
| `/findcryptopairs/regime.html` | regime_terminal |
| `/findcryptopairs/competition.html` | stocks_competition, fast_stocks_competition, stocks_*_comp |
| `/spikes/` | spike_scanner |
| `/coinglass/` | coinglass |
| `/audit/` | audit_ensemble |

### Existing Pages (verified Mar 13 2026)

| Page | Path |
|------|------|
| Now (Rapid Fire) | `/findcryptopairs/now.html` ✅ |
| Pump Watch | `/findcryptopairs/pump-watch.html` ✅ |
| Audit Trail | `/findcryptopairs/audit-trail.html` ✅ |
| Genome | `/findcryptopairs/genome.html` ✅ |
| Algo Competition | `/findcryptopairs/algo-competition-enhanced.html` ✅ |
| Incubator | `/findcryptopairs/incubator.html` ✅ |
| Battleground | `/battleground/` ✅ |
| Rise of the Claw | `/riseoftheclaw.html` ✅ |
| ML Gainer | `/updates/antigravity-ml-gainer.html` ✅ |
| Audit Dashboard | `/audit_dashboard/` ✅ |

## Fix Applied

Replaced all dead links with closest living page. Mapping logic:

| Dead Link | Redirected To | Rationale |
|-----------|--------------|-----------|
| `mercury.html` | `audit-trail.html` | Mercury system audit data visible there |
| `paper_trading.html` | `audit-trail.html` | Paper trading audit data visible there |
| `ml_edge.html` | `audit-trail.html` | ML Edge audit data visible there |
| `ml_predictions.html` | `audit-trail.html` | Prediction audit data visible there |
| `crypto_winners.html` | `audit-trail.html` | Winners audit data visible there |
| `signals.html` | `audit-trail.html` | Signal engine audit data visible there |
| `regime.html` | `audit-trail.html` | Regime data visible there |
| `competition.html` | `algo-competition-enhanced.html` | Same competition concept, upgraded page |
| `/spikes/` | `pump-watch.html` | Spike detection = pump watch |
| `/coinglass/` | `pump-watch.html` | CoinGlass data feeds pump watch |
| `/audit/` | `/audit_dashboard/` | Correct directory name |

## Files Changed

- `audit_dashboard/template.html` — `sysLinks` mapping (lines 671-769) completely rewritten with verified URLs and categorized comments

## Systems Count

- **Total unique systems mapped:** 70+
- **Dead links fixed:** 20+
- **Categories:** Live pages, Redirected (audit-trail), Competition, Pump Watch, Genome family, Revival systems, Battleground family, Goldmine, GitHub Pages hosted

## Verification

After deploying, these pages should all resolve (no 404):
- Every `sysLinks` value should return HTTP 200
- Template placeholders (`${sysLinks[...]}`) should resolve to valid URLs
- `null` entries (e.g., `incubator_fwd`) correctly show no link
