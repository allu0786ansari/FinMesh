# Feature build · HI-Small · pooled view

Federation B8, pooled view, 6 h windows, feature schema v3 (`550f9243bb68`), 3 account slices. Edge rows in the observation window: 5,077,237.

**Total 22 s; peak memory 878 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 2,257,373 |
| val | 708,657 |
| test | 718,551 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 2.10 | 557.30 |
| neighbourhood | 16.10 | 514.20 |
| merge | 3.70 | 878.50 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 13.39 | 7,471,397 | 557,983.35 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,881.50 |
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

Currency pairs observed: 193. Every currency has a rate.
