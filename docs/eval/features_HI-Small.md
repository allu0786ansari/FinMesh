# Feature build · HI-Small

Federation B8, 6 h windows, feature schema v2 (`c092db8f0957`), 3 account slices. Edge rows in the observation window: 5,077,237.

**Total 54 s; peak memory 1,094 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 2,257,373 |
| val | 708,657 |
| test | 718,551 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 2.60 | 348.50 |
| neighbourhood | 25.30 | 279.60 |
| accounts | 25.90 | 1,094.50 |

## Neighbourhood pass per member (lookback 4 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 3.04 | 844,436 | 277,775.00 |
| 1 | 2.77 | 844,460 | 304,859.21 |
| 2 | 2.89 | 838,943 | 290,291.70 |
| 3 | 3.17 | 1,187,236 | 374,522.40 |
| 4 | 2.85 | 852,222 | 299,025.26 |
| 5 | 2.86 | 843,684 | 294,994.41 |
| 6 | 2.74 | 828,887 | 302,513.50 |
| 7 | 2.57 | 849,211 | 330,432.30 |

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
