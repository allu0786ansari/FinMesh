# Benchmark anchor (A25 P6) · LI-Small

AMLworld's published split: every transaction, by day 60/20/20 (train 2022-09-01 00:00:00 – 2022-09-07 00:00:00, validation 2022-09-07 00:00:00 – 2022-09-09 00:00:00, test 2022-09-09 00:00:00 – 2022-09-18 00:00:00). Minority-class F1 (%) on test at the threshold that maximises validation F1; seeds [0, 1, 2, 3, 4], mean ± sd.

| Model | Test F1 | Validation F1 | Test AUPRC |
| --- | --- | --- | --- |
| A · our pooled detector (account-window LightGBM, max of the two accounts) | 23.21 ± 2.80 | 21.43 ± 0.80 | 0.131 |
| B · transaction LightGBM (own fields + both accounts' features) | 34.99 ± 1.51 | 27.89 ± 0.19 | 0.276 |
| LightGBM + graph features (Egressy et al., AAAI 2024) | 20.83 | — | — |
| XGBoost + graph features (Egressy et al., AAAI 2024) | 27.30 | — | — |
| Multi-PNA + EU (Egressy et al., AAAI 2024) | 33.07 | — | — |

Test: 1,174,673 transactions, 802 laundering. Validation: 1,316,442, 770. Account-windows missing: 0.

Adequacy rule: model A's validation F1 21.43 vs LightGBM + graph features 20.83 → gap +0.60 points (threshold −5): reported only (the rule reads the Medium sets).

