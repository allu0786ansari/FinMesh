# Feature build · LI-Small

Federation B8, 6 h windows, feature schema v2 (`c092db8f0957`), 4 account slices. Edge rows in the observation window: 6,923,826.

**Total 57 s; peak memory 1,127 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 3,086,445 |
| val | 968,125 |
| test | 980,766 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 1.90 | 440.90 |
| neighbourhood | 20.20 | 345.40 |
| accounts | 35.10 | 1,127.20 |

## Neighbourhood pass per member (lookback 4 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 2.27 | 1,175,056 | 517,645.81 |
| 1 | 2.83 | 1,610,816 | 569,192.93 |
| 2 | 2.24 | 1,168,028 | 521,441.07 |
| 3 | 2.20 | 1,151,036 | 523,198.18 |
| 4 | 2.22 | 1,145,457 | 515,971.62 |
| 5 | 2.17 | 1,130,207 | 520,832.72 |
| 6 | 2.18 | 1,155,812 | 530,188.99 |
| 7 | 2.12 | 1,146,273 | 540,694.81 |

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
