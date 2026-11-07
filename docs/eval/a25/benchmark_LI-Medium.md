# Benchmark anchor (A25 P6) · LI-Medium

AMLworld's published split: every transaction, by day 60/20/20 (train 2022-09-01 00:00:00 – 2022-09-10 00:00:00, validation 2022-09-10 00:00:00 – 2022-09-14 00:00:00, test 2022-09-14 00:00:00 – 2022-09-28 00:00:00). Minority-class F1 (%) on test at the threshold that maximises validation F1; seeds [0, 1, 2, 3, 4], mean ± sd.

| Model | Test F1 | Validation F1 | Test AUPRC |
| --- | --- | --- | --- |
| A · our pooled detector (account-window LightGBM, max of the two accounts) | 24.08 ± 2.01 | 23.92 ± 0.52 | 0.131 |
| B · transaction LightGBM (own fields + both accounts' features) | 34.34 ± 1.55 | 27.87 ± 1.50 | 0.238 |
| LightGBM + graph features (Egressy et al., AAAI 2024) | 20.85 | — | — |
| XGBoost + graph features (Egressy et al., AAAI 2024) | 28.16 | — | — |
| Multi-PNA + EU (Egressy et al., AAAI 2024) | 36.07 | — | — |

Test: 6,740,235 transactions, 3,992 laundering. Validation: 5,410,876, 3,774. Account-windows missing: 0.

Adequacy rule: model A's validation F1 23.92 vs LightGBM + graph features 20.85 → gap +3.07 points (threshold −5): not triggered.

