# Feature build · LI-Medium

Federation B8c50, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,250,113.

**Total 404 s; peak memory 903 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 10,128,163 |
| val | 2,453,695 |
| test | 3,473,798 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 8.70 | 638.90 |
| neighbourhood | 156.50 | 853.90 |
| accounts | 238.80 | 903.10 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 17.57 | 7,907,656 | 450,065.79 |
| 1 | 12.41 | 7,950,648 | 640,664.63 |
| 2 | 11.63 | 7,991,434 | 687,139.64 |
| 3 | 11.17 | 8,014,604 | 717,511.55 |
| 4 | 10.99 | 8,079,062 | 735,128.48 |
| 5 | 11.02 | 8,027,704 | 728,466.79 |
| 6 | 10.98 | 7,903,626 | 719,820.22 |
| 7 | 10.32 | 7,885,370 | 764,086.24 |

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
