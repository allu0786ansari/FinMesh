# Feature build · HI-Small

Federation B8, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 3 account slices. Edge rows in the observation window: 5,077,237.

**Total 67 s; peak memory 1,077 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 2,257,373 |
| val | 708,657 |
| test | 718,551 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 3.80 | 519.30 |
| neighbourhood | 37.40 | 408.70 |
| accounts | 25.50 | 1,076.90 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 5.86 | 1,655,743 | 282,550.00 |
| 1 | 4.05 | 1,656,637 | 409,046.17 |
| 2 | 4.38 | 1,647,223 | 376,078.31 |
| 3 | 4.81 | 2,323,574 | 483,071.52 |
| 4 | 3.46 | 1,672,365 | 483,342.49 |
| 5 | 3.69 | 1,655,252 | 448,577.78 |
| 6 | 3.66 | 1,625,397 | 444,097.54 |
| 7 | 3.61 | 1,666,331 | 461,587.53 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,881.50 |
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

Currency pairs observed: 193. Every currency has a rate.
