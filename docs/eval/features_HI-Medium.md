# Feature build · HI-Medium

Federation B8, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,891,251.

**Total 336 s; peak memory 1,302 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 15,116,933 |
| val | 3,392,862 |
| test | 5,152,867 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 17.60 | 406.30 |
| neighbourhood | 130.40 | 1,253.60 |
| accounts | 188.10 | 1,301.90 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 13.50 | 10,894,226 | 806,979.70 |
| 1 | 13.69 | 10,971,541 | 801,427.39 |
| 2 | 13.52 | 10,999,897 | 813,601.85 |
| 3 | 13.50 | 10,999,626 | 814,787.11 |
| 4 | 13.26 | 10,928,964 | 824,205.43 |
| 5 | 13.04 | 10,911,951 | 836,806.06 |
| 6 | 12.48 | 10,822,486 | 867,186.38 |
| 7 | 17.63 | 15,216,023 | 863,075.61 |

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
