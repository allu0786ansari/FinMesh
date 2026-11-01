# Feature build · LI-Medium

Federation B8c25, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,250,113.

**Total 170 s; peak memory 1,060 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 5,540,649 |
| val | 1,367,826 |
| test | 1,913,222 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 9.50 | 420.20 |
| neighbourhood | 67.40 | 1,059.50 |
| accounts | 93.60 | 584.70 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 7.05 | 4,661,750 | 661,241.13 |
| 1 | 6.80 | 4,690,291 | 689,748.68 |
| 2 | 6.22 | 4,693,148 | 754,525.40 |
| 3 | 6.35 | 4,746,834 | 747,532.91 |
| 4 | 6.17 | 4,788,777 | 776,138.90 |
| 5 | 6.30 | 4,711,112 | 747,795.56 |
| 6 | 6.13 | 4,604,801 | 751,191.03 |
| 7 | 5.66 | 4,623,676 | 816,903.89 |

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
