# Feature build · HI-Medium

Federation B8c75, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,891,251.

**Total 612 s; peak memory 1,050 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 14,241,169 |
| val | 3,384,250 |
| test | 4,855,224 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 8.20 | 623.90 |
| neighbourhood | 161.50 | 1,049.70 |
| accounts | 442.20 | 1,043.90 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 18.08 | 10,573,662 | 584,826.44 |
| 1 | 14.73 | 10,653,166 | 723,229.19 |
| 2 | 15.04 | 10,679,135 | 710,048.87 |
| 3 | 14.46 | 10,680,674 | 738,635.82 |
| 4 | 14.08 | 10,609,493 | 753,515.13 |
| 5 | 13.80 | 10,593,718 | 767,660.72 |
| 6 | 13.46 | 10,500,880 | 780,154.53 |
| 7 | 14.30 | 10,573,216 | 739,385.73 |

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
