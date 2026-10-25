# Feature build · LI-Small

Federation B8, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 4 account slices. Edge rows in the observation window: 6,923,826.

**Total 70 s; peak memory 1,000 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 3,086,445 |
| val | 968,125 |
| test | 980,766 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 1.70 | 632.10 |
| neighbourhood | 28.50 | 508.50 |
| accounts | 39.80 | 999.70 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 3.27 | 2,305,860 | 705,155.96 |
| 1 | 3.92 | 3,153,058 | 804,351.53 |
| 2 | 3.05 | 2,293,252 | 751,885.90 |
| 3 | 3.08 | 2,259,583 | 733,630.84 |
| 4 | 2.99 | 2,249,129 | 752,217.06 |
| 5 | 3.00 | 2,219,123 | 739,707.67 |
| 6 | 3.01 | 2,266,535 | 753,001.66 |
| 7 | 3.06 | 2,248,440 | 734,784.31 |

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
