# Feature build · HI-Medium

Federation B8c10, member view, 6 h windows, feature schema v3 (`550f9243bb68`), 16 account slices. Edge rows in the observation window: 31,891,251.

**Total 120 s; peak memory 1,145 MB** (anonymous memory, the part that counts against RAM; budget 8 GB).

| Partition | Account-windows |
| --- | --- |
| train | 2,459,180 |
| val | 617,670 |
| test | 852,115 |

## Stages

| Stage | Seconds | Peak MB |
| --- | --- | --- |
| edges | 7.10 | 657.60 |
| neighbourhood | 48.40 | 1,144.60 |
| accounts | 64.00 | 291.90 |

## Neighbourhood pass per member (lookback 12 windows, hub cap 64)

| Member | Seconds | Visible edge rows (with lookback) | Rows per second |
| --- | --- | --- | --- |
| 0 | 4.34 | 2,250,735 | 518,602.53 |
| 1 | 4.12 | 2,254,999 | 547,329.85 |
| 2 | 4.02 | 2,286,599 | 568,805.72 |
| 3 | 3.95 | 2,263,333 | 572,995.70 |
| 4 | 3.99 | 2,245,824 | 562,863.16 |
| 5 | 3.88 | 2,152,444 | 554,753.61 |
| 6 | 3.72 | 2,189,134 | 588,476.88 |
| 7 | 3.91 | 2,197,947 | 562,134.78 |

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
