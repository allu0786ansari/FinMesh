# Feature build · HI-Medium

Federation B8c90, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,891,251.

**Total 416 s; peak memory 1,206 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 14,791,614 |
| val | 3,392,135 |
| test | 5,051,145 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 11.80 | 584.20 |
| neighbourhood | 153.90 | 1,136.10 |
| accounts | 250.30 | 1,205.80 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 17.97 | 10,785,376 | 600,187.87 |
| 1 | 15.83 | 10,862,428 | 686,192.55 |
| 2 | 14.75 | 10,889,340 | 738,260.34 |
| 3 | 15.06 | 10,889,337 | 723,063.55 |
| 4 | 15.19 | 10,820,409 | 712,337.66 |
| 5 | 14.53 | 10,804,081 | 743,570.61 |
| 6 | 14.82 | 10,713,574 | 722,913.23 |
| 7 | 19.56 | 15,110,547 | 772,522.85 |

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
