# Feature build · LI-Medium

Federation B8c75, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,250,113.

**Total 474 s; peak memory 1,080 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 13,949,761 |
| val | 3,316,388 |
| test | 4,753,202 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 15.00 | 438.20 |
| neighbourhood | 183.70 | 954.30 |
| accounts | 275.50 | 1,079.60 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 22.14 | 10,356,468 | 467,771.82 |
| 1 | 20.07 | 10,409,666 | 518,667.96 |
| 2 | 19.53 | 10,422,923 | 533,687.81 |
| 3 | 18.98 | 10,436,217 | 549,853.37 |
| 4 | 18.14 | 10,493,388 | 578,466.81 |
| 5 | 17.25 | 10,420,850 | 604,107.25 |
| 6 | 16.89 | 10,330,684 | 611,645.00 |
| 7 | 17.09 | 10,301,783 | 602,795.96 |

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
