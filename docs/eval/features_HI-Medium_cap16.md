# Feature build · HI-Medium · cap16 view

Federation B8, cap16 view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 28,727,596.

**Total 338 s; peak memory 1,305 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 15,116,933 |
| val | 3,392,862 |
| test | 5,152,867 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 52.60 | 681.60 |
| neighbourhood | 110.50 | 1,108.90 |
| accounts | 175.40 | 1,304.90 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 12.34 | 10,142,570 | 821,926.26 |
| 1 | 12.26 | 10,227,168 | 834,189.89 |
| 2 | 11.56 | 10,235,917 | 885,459.95 |
| 3 | 11.52 | 10,246,165 | 889,424.05 |
| 4 | 11.55 | 10,171,934 | 880,686.93 |
| 5 | 11.85 | 10,160,893 | 857,459.32 |
| 6 | 11.52 | 10,065,668 | 873,755.90 |
| 7 | 11.32 | 10,144,622 | 896,168.02 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,882.63 |
| Brazil Real | 0.1771 |
| Canadian Dollar | 0.7580 |
| Euro | 1.17 |
| Mexican Peso | 0.0473 |
| Ruble | 0.0129 |
| Rupee | 0.0136 |
| Saudi Riyal | 0.2666 |
| Shekel | 0.2961 |
| Swiss Franc | 1.09 |
| UK Pound | 1.29 |
| US Dollar | 1.00 |
| Yen | 0.0095 |
| Yuan | 0.1493 |

Currency pairs observed: 207. Every currency has a rate.
