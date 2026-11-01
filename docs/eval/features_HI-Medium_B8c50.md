# Feature build · HI-Medium

Federation B8c50, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,891,251.

**Total 250 s; peak memory 1,155 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 10,341,308 |
| val | 2,505,336 |
| test | 3,548,604 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 8.30 | 642.00 |
| neighbourhood | 100.30 | 1,155.00 |
| accounts | 141.10 | 991.00 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 10.81 | 8,125,384 | 751,654.39 |
| 1 | 10.37 | 8,168,894 | 787,742.91 |
| 2 | 10.09 | 8,177,109 | 810,417.15 |
| 3 | 10.12 | 8,206,249 | 810,894.17 |
| 4 | 9.58 | 8,147,871 | 850,508.46 |
| 5 | 9.87 | 8,095,423 | 820,204.96 |
| 6 | 9.95 | 8,034,162 | 807,453.47 |
| 7 | 10.25 | 8,106,377 | 790,866.05 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,882.63 |
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

Currency pairs observed: 207. Every currency has a rate.
