# Feature build · LI-Medium

Federation B8, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,250,113.

**Total 600 s; peak memory 1,170 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 14,807,916 |
| val | 3,325,074 |
| test | 5,044,290 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 98.30 | 253.10 |
| neighbourhood | 146.50 | 1,034.40 |
| accounts | 354.80 | 1,170.10 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 15.73 | 10,671,914 | 678,443.36 |
| 1 | 15.99 | 10,721,377 | 670,505.13 |
| 2 | 13.18 | 10,733,950 | 814,411.99 |
| 3 | 17.55 | 14,982,970 | 853,730.48 |
| 4 | 12.49 | 10,808,272 | 865,354.04 |
| 5 | 12.56 | 10,732,740 | 854,517.52 |
| 6 | 12.31 | 10,643,199 | 864,597.81 |
| 7 | 12.61 | 10,615,165 | 841,805.31 |

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
