# Feature build · HI-Medium

Federation B8, 6 h windows, feature schema v2 (`c092db8f0957`), 16 account slices. Edge rows in the observation window: 31,891,251.

**Total 298 s; peak memory 1,299 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 15,116,933 |
| val | 3,392,862 |
| test | 5,152,867 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 17.90 | 677.60 |
| neighbourhood | 84.60 | 849.20 |
| accounts | 195.50 | 1,299.30 |

## Neighbourhood pass per member (lookback 4 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 9.06 | 5,386,446 | 594,530.46 |
| 1 | 8.74 | 5,422,944 | 620,474.14 |
| 2 | 8.51 | 5,437,999 | 639,012.81 |
| 3 | 8.73 | 5,437,767 | 622,882.82 |
| 4 | 8.43 | 5,402,304 | 640,842.70 |
| 5 | 8.39 | 5,393,206 | 642,813.59 |
| 6 | 8.35 | 5,349,199 | 640,622.63 |
| 7 | 11.77 | 7,558,442 | 642,178.59 |

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
