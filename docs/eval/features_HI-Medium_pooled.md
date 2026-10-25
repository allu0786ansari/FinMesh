# Feature build · HI-Medium · pooled view

Federation B8, pooled view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,891,251.

**Total 252 s; peak memory 1,253 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 15,116,933 |
| val | 3,392,862 |
| test | 5,152,867 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 29.10 | 322.50 |
| neighbourhood | 129.60 | 1,252.70 |
| merge | 93.20 | 1,033.70 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 102.92 | 49,101,132 | 477,080.57 |

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
