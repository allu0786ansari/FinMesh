# Feature build · LI-Medium · cap16 view

Federation B8, cap16 view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 28,165,821.

**Total 354 s; peak memory 1,293 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 14,807,916 |
| val | 3,325,074 |
| test | 5,044,290 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 64.20 | 381.70 |
| neighbourhood | 120.50 | 1,078.70 |
| accounts | 169.30 | 1,292.80 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 13.21 | 9,935,958 | 752,154.28 |
| 1 | 12.46 | 9,989,520 | 801,727.13 |
| 2 | 12.45 | 9,992,611 | 802,619.36 |
| 3 | 12.65 | 10,010,252 | 791,324.27 |
| 4 | 12.71 | 10,061,191 | 791,596.46 |
| 5 | 12.70 | 9,993,613 | 786,898.66 |
| 6 | 12.58 | 9,909,600 | 787,726.55 |
| 7 | 12.64 | 9,884,092 | 781,969.30 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,882.35 |
| Brazil Real | 0.1771 |
| Canadian Dollar | 0.7580 |
| Euro | 1.17 |
| Mexican Peso | 0.0474 |
| Ruble | 0.0129 |
| Rupee | 0.0136 |
| Saudi Riyal | 0.2666 |
| Shekel | 0.2961 |
| Swiss Franc | 1.09 |
| UK Pound | 1.29 |
| US Dollar | 1.00 |
| Yen | 0.0095 |
| Yuan | 0.1493 |

Currency pairs observed: 206. Every currency has a rate.
