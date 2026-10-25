# Feature build · LI-Medium · pooled view

Federation B8, pooled view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,250,113.

**Total 223 s; peak memory 1,135 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 14,807,916 |
| val | 3,325,074 |
| test | 5,044,290 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 47.80 | 287.00 |
| neighbourhood | 130.30 | 1,135.40 |
| merge | 44.50 | 1,040.00 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 98.77 | 48,109,500 | 487,086.16 |

## Exchange rates (reference-currency value of one unit, from training rows)

| Currency | Rate |
| --- | --- |
| Australian Dollar | 0.7078 |
| Bitcoin | 11,882.35 |
| Brazil Real | 0.1771 |
| Canadian Dollar | 0.7580 |
| Euro | 1.17 |
| Mexican Peso | 0.0474 |
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
