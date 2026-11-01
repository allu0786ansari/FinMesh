# Feature build · HI-Medium · pooled view

Federation B8c50, pooled view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,891,251.

**Total 151 s; peak memory 1,287 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 10,341,308 |
| val | 2,505,336 |
| test | 3,548,604 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 11.30 | 331.70 |
| neighbourhood | 119.20 | 1,287.30 |
| merge | 20.20 | 874.90 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 98.86 | 49,101,132 | 496,673.40 |

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
