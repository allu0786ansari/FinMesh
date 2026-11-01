# Feature build · LI-Medium

Federation B8c90, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,250,113.

**Total 703 s; peak memory 1,083 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 14,490,060 |
| val | 3,324,400 |
| test | 4,945,012 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 18.50 | 290.20 |
| neighbourhood | 200.30 | 934.70 |
| accounts | 483.90 | 1,082.70 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 23.88 | 10,565,237 | 442,430.36 |
| 1 | 14.97 | 10,616,782 | 709,203.87 |
| 2 | 15.32 | 10,627,855 | 693,724.22 |
| 3 | 22.72 | 14,879,254 | 654,896.74 |
| 4 | 15.27 | 10,701,986 | 700,850.43 |
| 5 | 14.57 | 10,626,168 | 729,318.33 |
| 6 | 13.92 | 10,537,200 | 756,982.76 |
| 7 | 14.81 | 10,507,013 | 709,453.95 |

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
