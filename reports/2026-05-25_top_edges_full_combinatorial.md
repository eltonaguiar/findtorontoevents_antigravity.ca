# Top Edges — Full Combinatorial Audit (2026-05-25)

Generated: 2026-05-25T04:18:46Z
Window: last 90d closed picks

## Criteria

PROVEN = WR_shrunk>=55%, PF>=1.5, n>=20, holdout_pass (PF>=1.2 on both 60/40 chrono splits), Bonferroni-adjusted alpha=0.05/673=7.429e-05. Enumerates all C(7,3)+C(7,4)=70 tag-dim combos across [trust,conf,rr,fam,dir,score_dec,source]; cap top-200 cells per class by n.

- Total cells evaluated (after n>=20 + top-200/class cap): **673**
- Dim combos enumerated per pick: **70** (C(7,3)+C(7,4))
- Bonferroni alpha: **7.429e-05**

## Per-class summary

| Class | n_closed | cells | holdout_pass | bonf_pass | PROVEN (adj) | PROVEN (unadj) | Top edge |
|-------|----------|-------|--------------|-----------|--------------|----------------|----------|
| BOND | 12 | 0 | 0 | 0 | 0 | 0 | — |
| COMMODITY | 1219 | 200 | 64 | 71 | 10 | 10 | conf=C0.60-0.70 & rr=RR1.0-1.5 & source=multi_asset_copytrader (PF 3.274, WR_s 67.52%, n 137) |
| CRYPTO | 3684 | 200 | 21 | 8 | 0 | 5 | trust=UNK & conf=C<0.60 & rr=RR1.0-1.5 (PF 22.223, WR_s 59.45%, n 345) |
| EQUITY | 126 | 72 | 30 | 0 | 0 | 0 | — |
| ETF | 13 | 0 | 0 | 0 | 0 | 0 | — |
| FOREX | 2519 | 200 | 13 | 0 | 0 | 0 | — |
| FUTURES | 18 | 0 | 0 | 0 | 0 | 0 | — |
| INDEX | 2 | 0 | 0 | 0 | 0 | 0 | — |
| MEME | 49 | 1 | 0 | 0 | 0 | 0 | — |
| PENNY | 7 | 0 | 0 | 0 | 0 | 0 | — |
| UNKNOWN | 2 | 0 | 0 | 0 | 0 | 0 | — |

## PROVEN (Bonferroni + holdout) — top 5 per class

### BOND
_No cells passed all gates._

### COMMODITY
| Cell | n | WR | WR_shrunk | PF | train_pf | holdout_pf |
|------|---|----|-----------|----|----------|------------|
| conf=C0.60-0.70 & rr=RR1.0-1.5 & source=multi_asset_copytrader | 137 | 70.07% | 67.52% | 3.274 | 24.272 | 2.307 |
| trust=UNK & conf=C0.60-0.70 & rr=RR1.0-1.5 & source=multi_asset_copytrader | 137 | 70.07% | 67.52% | 3.274 | 24.272 | 2.307 |
| fam=cot & dir=SHORT & score_dec=S20 | 137 | 74.45% | 71.34% | 3.219 | 13.391 | 2.131 |
| dir=SHORT & score_dec=S20 & source=multi_asset_cot | 137 | 74.45% | 71.34% | 3.219 | 13.391 | 2.131 |
| trust=UNK & fam=cot & dir=SHORT & score_dec=S20 | 137 | 74.45% | 71.34% | 3.219 | 13.391 | 2.131 |

### CRYPTO
_No cells passed all gates._

### EQUITY
_No cells passed all gates._

### ETF
_No cells passed all gates._

### FOREX
_No cells passed all gates._

### FUTURES
_No cells passed all gates._

### INDEX
_No cells passed all gates._

### MEME
_No cells passed all gates._

### PENNY
_No cells passed all gates._

### UNKNOWN
_No cells passed all gates._
