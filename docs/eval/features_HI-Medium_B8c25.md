# Feature build · HI-Medium

Federation B8c25, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,891,251.

**Total 167 s; peak memory 1,165 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 5,660,932 |
| val | 1,398,404 |
| test | 1,954,229 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 7.80 | 643.60 |
| neighbourhood | 66.50 | 1,165.10 |
| accounts | 93.00 | 605.20 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 6.27 | 4,789,292 | 763,842.42 |
| 1 | 6.41 | 4,829,115 | 753,372.07 |
| 2 | 6.17 | 4,847,733 | 785,694.17 |
| 3 | 6.33 | 4,844,970 | 765,398.10 |
| 4 | 6.24 | 4,819,307 | 772,324.84 |
| 5 | 6.21 | 4,720,973 | 760,221.10 |
| 6 | 6.10 | 4,672,747 | 766,024.10 |
| 7 | 6.32 | 4,757,036 | 752,695.57 |

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
