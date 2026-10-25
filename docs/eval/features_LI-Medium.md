# Feature build · LI-Medium

Federation B8, 6 h windows, feature schema v1 (`240e2915d01e`), 16 account slices. Edge rows in the observation window: 31,250,113.

**Total 300 s; peak memory 1,242 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 14,807,916 |
| val | 3,325,074 |
| test | 5,044,290 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 28.40 | 281.50 |
| neighbourhood | 85.10 | 808.80 |
| accounts | 186.30 | 1,242.20 |

## Neighbourhood pass per member (lookback 4 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 9.14 | 5,273,903 | 577,013.46 |
| 1 | 8.45 | 5,298,769 | 627,073.25 |
| 2 | 8.55 | 5,305,232 | 620,494.97 |
| 3 | 11.52 | 7,441,870 | 645,995.66 |
| 4 | 8.42 | 5,341,623 | 634,397.03 |
| 5 | 8.33 | 5,305,615 | 636,928.57 |
| 6 | 8.38 | 5,260,695 | 627,767.90 |
| 7 | 8.14 | 5,245,235 | 644,377.76 |

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
