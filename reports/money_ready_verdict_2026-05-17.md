# Money-Ready Verdict — 2026-05-17

Class             n      WR      PF    DSR    PBO    SPA Verdict           
----------------------------------------------------------------------------
EQUITY          240   53.3%    1.97   FAIL    N/A   FAIL WATCH              [DASH]
COMMODITY       354   60.2%    2.28   PASS    N/A   PASS MONEY_READY       
CRYPTO          631   66.6%    0.76   FAIL   PASS   PASS WATCH             
ETF              74    0.0%    2.41    N/A    N/A    N/A WATCH              [DASH]
FOREX           932   25.6%    0.35   FAIL   PASS   PASS NOT_READY         
BOND             12   50.0%    0.54    N/A    N/A    N/A INSUFFICIENT_DATA  [DASH]
FUTURES         203    3.0%    0.06   FAIL    N/A   FAIL NOT_READY         
UNKNOWN           2  100.0%     inf    N/A    N/A    N/A INSUFFICIENT_DATA 

## Gate Thresholds
- n_ok: ≥50 resolved picks
- wr_ok: ≥50%
- pf_ok: ≥1.5
- DSR: probability ≥0.95
- PBO: overfit probability ≤0.55
- SPA: family-wise p ≤0.1 (α=0.1)

**MONEY_READY:** COMMODITY
**WATCH:** EQUITY, CRYPTO, ETF
