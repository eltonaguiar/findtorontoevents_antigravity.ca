# Latent-Feature Edge Diagnostic — 2026-04-22

**Purpose:** discover edge on features NOT currently surfaced as audit columns.

**Inputs:** `updates/data/claude_ml_picks.json` (486 resolved ML picks with pump_probability + confidence tier) + `audit_dashboard/data/dashboard_data.json` (3,500 closed picks, incl. technical_rsi_1h/4h + elite_breakdown components).

**Edge threshold:** n >= 20 to report a bucket.


## Claude ML: outcome distribution

| n       |   count |
|:--------|--------:|
| SL      |     206 |
| EXPIRED |     135 |
| TP1     |      84 |
| TP2     |      61 |


## Claude ML: edge by pump_probability band

| bucket          |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:----------------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| mid_0.35_0.50   |  47 |     27 |       20 | 0.5745 | 2.1329 |         2.0427 |         96.0049 |
| low_0.20_0.35   |  59 |     20 |       37 | 0.339  | 0.729  |        -0.6609 |        -38.992  |
| high_0.50_0.65  | 336 |    109 |      224 | 0.3244 | 0.3028 |        -3.0889 |      -1037.87   |
| very_high_0.65+ |  40 |     10 |       29 | 0.25   | 0.1781 |        -3.9294 |       -157.176  |


## Claude ML: edge by confidence_tier

| bucket    |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:----------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| VERY HIGH | 486 |    168 |      312 | 0.3457 | 0.4076 |        -2.3347 |        -1134.68 |


## Closed picks: edge by technical_rsi_1h band

_empty_


## Closed picks: edge by technical_rsi_4h band

| bucket           |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:-----------------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| overbought_70_80 | 121 |     51 |       70 | 0.4215 | 0.8918 |        -0.0788 |         -9.5369 |
| strong_60_70     | 421 |    145 |      276 | 0.3444 | 0.7    |        -0.2084 |        -87.7296 |
| neutral_40_60    | 159 |     52 |      107 | 0.327  | 0.5972 |        -0.3579 |        -56.8993 |


## Closed picks: edge by eb_regime_match quartile

| bucket   |    n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|-----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| all      | 3500 |   1506 |     1937 | 0.4303 | 1.0001 |         0.0001 |           0.367 |


## Closed picks: edge by eb_technical_alignment quartile

| bucket   |    n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|-----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| all      | 3500 |   1506 |     1937 | 0.4303 | 1.0001 |         0.0001 |           0.367 |


## Closed picks: edge by eb_sector_rotation quartile

| bucket   |    n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|-----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| all      | 3500 |   1506 |     1937 | 0.4303 | 1.0001 |         0.0001 |           0.367 |


## Closed picks: edge by eb_ml_score quartile

| bucket   |    n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:---------|-----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| all      | 3500 |   1506 |     1937 | 0.4303 | 1.0001 |         0.0001 |           0.367 |


## Closed picks: edge by RSI-4h × asset_class (top 20)

| bucket                    |   n |   wins |   losses |     wr |     pf |   mean_pnl_pct |   total_pnl_pct |
|:--------------------------|----:|-------:|---------:|-------:|-------:|---------------:|----------------:|
| None | EQUITY             | 354 |    187 |      164 | 0.5282 | 1.4261 |         0.6624 |        234.493  |
| None | ETF                |  77 |     40 |       35 | 0.5195 | 1.1003 |         0.1197 |          9.2165 |
| None | FOREX              | 804 |    401 |      372 | 0.4988 | 1.1463 |         0.0183 |         14.6922 |
| None | COMMODITY          | 595 |    252 |      325 | 0.4235 | 1.0855 |         0.0114 |          6.7684 |
| overbought_70_80 | CRYPTO | 121 |     51 |       70 | 0.4215 | 0.8918 |        -0.0788 |         -9.5369 |
| None | CRYPTO             | 949 |    367 |      580 | 0.3867 | 0.9022 |        -0.1198 |       -113.707  |
| strong_60_70 | CRYPTO     | 421 |    145 |      276 | 0.3444 | 0.7    |        -0.2084 |        -87.7296 |
| neutral_40_60 | CRYPTO    | 159 |     52 |      107 | 0.327  | 0.5972 |        -0.3579 |        -56.8993 |
