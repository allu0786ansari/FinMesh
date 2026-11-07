# Feature build · HI-Medium-FULL

Federation B8, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,898,238.

**Total 404 s; peak memory 1,226 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 14,702,453 |
| val | 4,303,199 |
| test | 5,160,298 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 19.90 | 415.50 |
| neighbourhood | 164.70 | 1,145.10 |
| accounts | 219.80 | 1,226.10 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 18.59 | 12,409,331 | 667,527.22 |
| 1 | 16.80 | 12,495,456 | 743,777.14 |
| 2 | 16.93 | 12,526,534 | 739,901.59 |
| 3 | 16.76 | 12,528,394 | 747,517.54 |
| 4 | 16.35 | 12,446,020 | 761,224.46 |
| 5 | 15.66 | 12,427,204 | 793,563.47 |
| 6 | 15.21 | 12,329,145 | 810,594.67 |
| 7 | 20.80 | 17,323,869 | 832,878.32 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,882.58 |
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

Currency pairs observed: 206. Every currency has a rate.
