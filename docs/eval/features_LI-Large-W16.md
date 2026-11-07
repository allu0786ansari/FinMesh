# Feature build · LI-Large-W16

Federation B8, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 15 account slices. Edge rows in the observation window: 29,650,722.

**Total 597 s; peak memory 1,246 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 13,471,815 |
| val | 4,474,933 |
| test | 4,218,098 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 12.80 | 506.00 |
| neighbourhood | 186.60 | 965.10 |
| accounts | 397.80 | 1,246.20 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 20.73 | 10,647,639 | 513,634.30 |
| 1 | 15.89 | 10,683,527 | 672,342.79 |
| 2 | 22.01 | 14,935,902 | 678,596.18 |
| 3 | 14.15 | 10,692,878 | 755,680.42 |
| 4 | 13.34 | 10,747,021 | 805,623.76 |
| 5 | 13.43 | 10,637,885 | 792,098.66 |
| 6 | 13.54 | 10,620,932 | 784,411.52 |
| 7 | 14.19 | 10,704,550 | 754,372.80 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,882.47 |
| Brazil Real | 0.1771 |
| Canadian Dollar | 0.7580 |
| Euro | 1.17 |
| Mexican Peso | 0.0473 |
| Ruble | 0.0129 |
| Rupee | 0.0136 |
| Saudi Riyal | 0.2667 |
| Shekel | 0.2961 |
| Swiss Franc | 1.09 |
| UK Pound | 1.29 |
| US Dollar | 1.00 |
| Yen | 0.0095 |
| Yuan | 0.1493 |

Currency pairs observed: 204. Every currency has a rate.
