# Feature build · LI-Medium

Federation B8c10, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,250,113.

**Total 120 s; peak memory 1,060 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 2,380,970 |
| val | 596,844 |
| test | 825,380 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 9.90 | 556.60 |
| neighbourhood | 47.60 | 1,059.90 |
| accounts | 62.20 | 283.20 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 3.95 | 2,162,384 | 547,438.99 |
| 1 | 3.87 | 2,245,877 | 580,329.97 |
| 2 | 3.65 | 2,142,140 | 586,887.67 |
| 3 | 3.66 | 2,203,572 | 602,068.85 |
| 4 | 3.98 | 2,217,434 | 557,144.22 |
| 5 | 3.68 | 2,141,981 | 582,060.05 |
| 6 | 3.69 | 2,084,823 | 564,992.68 |
| 7 | 3.66 | 2,098,721 | 573,421.04 |

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
