# Feature build · LI-Medium

Federation B8, 6 h windows, feature schema v2 (`c092db8f0957`), 16 account slices. Edge rows in the observation window: 31,250,113.

**Total 305 s; peak memory 1,282 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 14,807,916 |
| val | 3,325,074 |
| test | 5,044,290 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 21.00 | 845.00 |
| neighbourhood | 85.30 | 800.20 |
| accounts | 198.40 | 1,281.70 |

## Neighbourhood pass per member (lookback 4 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 9.61 | 5,273,903 | 548,793.24 |
| 1 | 9.04 | 5,298,769 | 586,147.01 |
| 2 | 9.32 | 5,305,232 | 569,230.90 |
| 3 | 11.87 | 7,441,870 | 626,947.77 |
| 4 | 8.25 | 5,341,623 | 647,469.45 |
| 5 | 8.30 | 5,305,615 | 639,230.72 |
| 6 | 8.26 | 5,260,695 | 636,888.01 |
| 7 | 8.21 | 5,245,235 | 638,883.68 |

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
