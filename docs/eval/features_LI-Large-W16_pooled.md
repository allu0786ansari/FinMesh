# Feature build · LI-Large-W16 · pooled view

Federation B8, pooled view, 6 h windows, feature schema v3 (`550f9243bb68`), 15 account slices. Edge rows in the observation window: 29,650,722.

**Total 292 s; peak memory 1,005 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 13,471,815 |
| val | 4,474,933 |
| test | 4,218,098 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 17.20 | 290.90 |
| neighbourhood | 187.40 | 1,005.20 |
| merge | 87.40 | 882.40 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 130.72 | 47,955,651 | 366,857.80 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,882.47 |
| Brazil Real | 0.1771 |
| Canadian Dollar | 0.7580 |
| Euro | 1.17 |
| Mexican Peso | 0.0473 |
| Ruble | 0.0129 |
| Rupee | 0.0136 |
| Saudi Riyal | 0.2667 |
| Shekel | 0.2961 |
| Swiss Franc | 1.09 |
| UK Pound | 1.29 |
| US Dollar | 1.00 |
| Yen | 0.0095 |
| Yuan | 0.1493 |

Currency pairs observed: 204. Every currency has a rate.
