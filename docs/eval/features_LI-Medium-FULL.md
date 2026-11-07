# Feature build · LI-Medium-FULL

Federation B8, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,251,483.

**Total 604 s; peak memory 1,137 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 14,402,814 |
| val | 4,215,080 |
| test | 5,045,690 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 33.90 | 303.90 |
| neighbourhood | 253.70 | 906.40 |
| accounts | 316.70 | 1,137.00 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 27.31 | 12,148,687 | 444,843.90 |
| 1 | 21.07 | 12,205,643 | 579,290.13 |
| 2 | 20.20 | 12,220,561 | 604,978.27 |
| 3 | 25.43 | 17,049,037 | 670,430.08 |
| 4 | 18.19 | 12,303,200 | 676,371.63 |
| 5 | 18.70 | 12,219,305 | 653,438.77 |
| 6 | 18.63 | 12,118,880 | 650,503.49 |
| 7 | 18.16 | 12,083,393 | 665,385.08 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,882.80 |
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
