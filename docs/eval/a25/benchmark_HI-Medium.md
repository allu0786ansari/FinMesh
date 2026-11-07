# Benchmark anchor (A25 P6) · HI-Medium

AMLworld's published split: every transaction, by day 60/20/20 (train 2022-09-01 00:00:00 – 2022-09-10 00:00:00, validation 2022-09-10 00:00:00 – 2022-09-14 00:00:00, test 2022-09-14 00:00:00 – 2022-09-29 00:00:00). Minority-class F1 (%) on test at the threshold that maximises validation F1; seeds [0, 1, 2, 3, 4], mean ± sd.

| Model | Test F1 | Validation F1 | Test AUPRC |
| --- | --- | --- | --- |
| A · our pooled detector (account-window LightGBM, max of the two accounts) | 42.67 ± 2.76 | 45.03 ± 0.81 | 0.308 |
| B · transaction LightGBM (own fields + both accounts' features) | 67.01 ± 2.27 | 67.32 ± 0.40 | 0.609 |
| LightGBM + graph features (Egressy et al., AAAI 2024) | 59.48 | — | — |
| XGBoost + graph features (Egressy et al., AAAI 2024) | 65.70 | — | — |
| Multi-PNA + EU (Egressy et al., AAAI 2024) | 66.48 | — | — |

Test: 6,890,229 transactions, 11,016 laundering. Validation: 5,520,883, 8,501. Account-windows missing: 0.

Adequacy rule: model A's validation F1 45.03 vs LightGBM + graph features 59.48 → gap -14.45 points (threshold −5): **triggered**: the stronger-detector track (S0+, S2+, oracle+) is developed on validation and added to the Large confirmation.

