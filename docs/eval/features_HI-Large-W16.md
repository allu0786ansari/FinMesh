# Feature build · HI-Large-W16

Federation B8, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 30,259,872.

**Total 322 s; peak memory 1,204 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 13,756,545 |
| val | 4,565,386 |
| test | 4,309,615 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 7.40 | 652.00 |
| neighbourhood | 132.60 | 1,150.80 |
| accounts | 182.10 | 1,203.90 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 15.54 | 10,835,651 | 697,274.84 |
| 1 | 14.56 | 10,958,029 | 752,611.88 |
| 2 | 13.50 | 10,984,353 | 813,655.78 |
| 3 | 13.37 | 10,965,944 | 820,190.28 |
| 4 | 12.93 | 10,941,097 | 846,179.20 |
| 5 | 12.68 | 10,790,913 | 851,018.38 |
| 6 | 12.26 | 10,822,301 | 882,732.54 |
| 7 | 17.52 | 15,173,851 | 866,087.39 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,882.32 |
| Brazil Real | 0.1771 |
| Canadian Dollar | 0.7580 |
| Euro | 1.17 |
| Mexican Peso | 0.0473 |
| Ruble | 0.0129 |
| Rupee | 0.0136 |
| Saudi Riyal | 0.2666 |
| Shekel | 0.2963 |
| Swiss Franc | 1.09 |
| UK Pound | 1.29 |
| US Dollar | 1.00 |
| Yen | 0.0095 |
| Yuan | 0.1493 |

Currency pairs observed: 205. Every currency has a rate.
