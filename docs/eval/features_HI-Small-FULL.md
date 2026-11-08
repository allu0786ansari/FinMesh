# Feature build · HI-Small-FULL

Federation B8, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 3 account slices. Edge rows in the observation window: 5,078,345.

**Total 64 s; peak memory 1,060 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 2,424,291 |
| val | 708,764 |
| test | 719,671 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 1.10 | 455.50 |
| neighbourhood | 35.60 | 411.10 |
| accounts | 27.60 | 1,059.70 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 3.95 | 1,905,343 | 482,365.32 |
| 1 | 3.87 | 1,904,785 | 492,192.51 |
| 2 | 4.13 | 1,894,788 | 458,786.44 |
| 3 | 4.86 | 2,668,409 | 549,055.35 |
| 4 | 4.12 | 1,923,350 | 466,832.52 |
| 5 | 3.79 | 1,904,041 | 502,385.49 |
| 6 | 3.75 | 1,870,238 | 498,730.13 |
| 7 | 4.01 | 1,915,553 | 477,694.01 |

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
