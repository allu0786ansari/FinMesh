# Feature build · LI-Small-FULL

Federation B8, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 4 account slices. Edge rows in the observation window: 6,924,049.

**Total 72 s; peak memory 1,141 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 3,314,583 |
| val | 968,135 |
| test | 981,002 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 1.90 | 337.80 |
| neighbourhood | 35.10 | 507.80 |
| accounts | 35.00 | 1,140.80 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 4.09 | 2,650,836 | 648,126.16 |
| 1 | 4.85 | 3,620,295 | 746,452.58 |
| 2 | 3.99 | 2,636,177 | 660,695.99 |
| 3 | 3.95 | 2,597,340 | 657,554.43 |
| 4 | 3.70 | 2,584,759 | 698,583.51 |
| 5 | 3.39 | 2,550,530 | 752,368.73 |
| 6 | 3.78 | 2,605,295 | 689,231.48 |
| 7 | 3.79 | 2,585,577 | 682,210.29 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,881.82 |
| Brazil Real | 0.1771 |
| Canadian Dollar | 0.7580 |
| Euro | 1.17 |
| Mexican Peso | 0.0472 |
| Ruble | 0.0129 |
| Rupee | 0.0136 |
| Saudi Riyal | 0.2666 |
| Shekel | 0.2961 |
| Swiss Franc | 1.09 |
| UK Pound | 1.29 |
| US Dollar | 1.00 |
| Yen | 0.0095 |
| Yuan | 0.1493 |

Currency pairs observed: 189. Every currency has a rate.
