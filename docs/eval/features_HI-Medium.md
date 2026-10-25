# Feature build · HI-Medium

Federation B8, 6 h windows, feature schema v1 (`240e2915d01e`), 16 account slices. Edge rows in the observation window: 31,891,251.

**Total 283 s; peak memory 1,315 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 15,116,933 |
| val | 3,392,862 |
| test | 5,152,867 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 21.80 | 377.80 |
| neighbourhood | 87.00 | 823.30 |
| accounts | 174.50 | 1,314.90 |

## Neighbourhood pass per member (lookback 4 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 9.44 | 5,386,446 | 570,598.09 |
| 1 | 9.05 | 5,422,944 | 599,220.33 |
| 2 | 9.06 | 5,437,999 | 600,220.64 |
| 3 | 8.68 | 5,437,767 | 626,470.85 |
| 4 | 8.48 | 5,402,304 | 637,064.15 |
| 5 | 8.32 | 5,393,206 | 648,221.88 |
| 6 | 8.21 | 5,349,199 | 651,546.77 |
| 7 | 11.70 | 7,558,442 | 646,020.68 |

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
