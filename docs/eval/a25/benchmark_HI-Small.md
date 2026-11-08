# Benchmark anchor (A25 P6) · HI-Small

AMLworld's published split: every transaction, by day 60/20/20 (train 2022-09-01 00:00:00 – 2022-09-07 00:00:00, validation 2022-09-07 00:00:00 – 2022-09-09 00:00:00, test 2022-09-09 00:00:00 – 2022-09-19 00:00:00). Minority-class F1 (%) on test at the threshold that maximises validation F1; seeds [0, 1, 2, 3, 4], mean ± sd.

| Model | Test F1 | Validation F1 | Test AUPRC |
| --- | --- | --- | --- |
| A · our pooled detector (account-window LightGBM, max of the two accounts) | 48.20 ± 0.69 | 45.25 ± 0.95 | 0.362 |
| B · transaction LightGBM (own fields + both accounts' features) | 64.25 ± 1.24 | 60.71 ± 0.73 | 0.604 |
| LightGBM + graph features (Egressy et al., AAAI 2024) | 62.86 | — | — |
| XGBoost + graph features (Egressy et al., AAAI 2024) | 63.23 | — | — |
| Multi-PNA + EU (Egressy et al., AAAI 2024) | 68.16 | — | — |

Test: 863,900 transactions, 1,611 laundering. Validation: 965,524, 1,036. Account-windows missing: 0.

Adequacy rule: model A's validation F1 45.25 vs LightGBM + graph features 62.86 → gap -17.61 points (threshold −5): reported only (the rule reads the Medium sets).

