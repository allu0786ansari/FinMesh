# Feature build · LI-Medium · pooled view

Federation B8c25, pooled view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,250,113.

**Total 156 s; peak memory 1,062 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 5,540,649 |
| val | 1,367,826 |
| test | 1,913,222 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 9.10 | 398.40 |
| neighbourhood | 131.10 | 1,062.10 |
| merge | 15.70 | 704.60 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 107.08 | 48,109,500 | 449,285.58 |

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
