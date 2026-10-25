# Feature build · HI-Small

Federation B8, 6 h windows, feature schema v1 (`240e2915d01e`), 3 account slices. Edge rows in the observation window: 5,077,237.

**Total 39 s; peak memory 1,102 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 2,257,373 |
| val | 708,657 |
| test | 718,551 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 1.60 | 273.60 |
| neighbourhood | 17.70 | 279.80 |
| accounts | 20.00 | 1,102.10 |

## Neighbourhood pass per member (lookback 4 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 2.07 | 844,436 | 407,940.10 |
| 1 | 1.99 | 844,460 | 424,351.76 |
| 2 | 1.97 | 838,943 | 425,859.39 |
| 3 | 2.33 | 1,187,236 | 509,543.35 |
| 4 | 1.94 | 852,222 | 439,289.69 |
| 5 | 1.91 | 843,684 | 441,719.37 |
| 6 | 1.90 | 828,887 | 436,256.32 |
| 7 | 1.85 | 849,211 | 459,032.97 |

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
