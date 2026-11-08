# Feature build · LI-Small-FULL · pooled view

Federation B8, pooled view, 6 h windows, feature schema v3 (`550f9243bb68`), 4 account slices. Edge rows in the observation window: 6,924,049.

**Total 31 s; peak memory 949 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 3,314,583 |
| val | 968,135 |
| test | 981,002 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 2.60 | 451.90 |
| neighbourhood | 24.30 | 648.70 |
| merge | 4.40 | 948.80 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 20.85 | 11,730,094 | 562,594.44 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,881.82 |
| Brazil Real | 0.1771 |
| Canadian Dollar | 0.7580 |
| Euro | 1.17 |
| Mexican Peso | 0.0472 |
| Ruble | 0.0129 |
| Rupee | 0.0136 |
| Saudi Riyal | 0.2666 |
| Shekel | 0.2961 |
| Swiss Franc | 1.09 |
| UK Pound | 1.29 |
| US Dollar | 1.00 |
| Yen | 0.0095 |
| Yuan | 0.1493 |

Currency pairs observed: 189. Every currency has a rate.
