# Feature build · LI-Small

Federation B8, 6 h windows, feature schema v1 (`240e2915d01e`), 4 account slices. Edge rows in the observation window: 6,923,826.

**Total 53 s; peak memory 1,122 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 3,086,445 |
| val | 968,125 |
| test | 980,766 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 2.70 | 272.50 |
| neighbourhood | 20.40 | 363.90 |
| accounts | 29.70 | 1,122.20 |

## Neighbourhood pass per member (lookback 4 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 2.43 | 1,175,056 | 483,562.14 |
| 1 | 2.72 | 1,610,816 | 592,211.76 |
| 2 | 2.25 | 1,168,028 | 519,123.56 |
| 3 | 2.16 | 1,151,036 | 532,887.04 |
| 4 | 2.14 | 1,145,457 | 535,260.28 |
| 5 | 2.23 | 1,130,207 | 506,819.28 |
| 6 | 2.23 | 1,155,812 | 518,301.35 |
| 7 | 2.32 | 1,146,273 | 494,083.19 |

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
