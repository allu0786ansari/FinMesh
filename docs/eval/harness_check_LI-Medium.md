# Harness check · LI-Medium

Federation B8, 6 h windows. Thresholds fitted on train, metrics on val. Both scorers are label-free references, not detectors: the **random** scorer must sit on its analytic baseline (AUPRC near the prevalence, AUROC near 0.5, detection inside the random-alert interval); **activity** (transaction count) shows the harness registers a weak signal.

## Scorer: random

3,324,357 account-windows, 4,433 positive (prevalence 0.0013); unscored 0.

AUPRC 0.0014 [0.0013, 0.0014]; AUROC 0.5073 [0.5001, 0.5159]; precision at 100 0.0000, at 1,000 0.0000.

| Budget | Alerts | Alerts /1000 acc /day | False /1000 acc /day | Precision | Window recall | Max member FPR | Schemes | Detected [95% CI] | Random-alert [95%] | Linked | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fpr_0.001 | 3,342 | 0.5482 | 0.5475 | 0.0009 | 0.0007 | 0.0010 | 93 | 0.0000 [0.0000, 0.0000] | 0.0062 [0.0000, 0.0215] | 0.0000 [0.0000, 0.0000] | — |
| fpr_0.0001 | 340 | 0.0558 | 0.0558 | 0.0000 | 0.0000 | 0.0001 | 93 | 0.0000 [0.0000, 0.0000] | 0.0006 [0.0000, 0.0108] | 0.0000 [0.0000, 0.0000] | — |
| alerts_1_per_1000_per_day | 6,144 | 1.01 | 1.01 | 0.0010 | 0.0014 | 0.0019 | 93 | 0.0000 [0.0000, 0.0000] | 0.0113 [0.0000, 0.0323] | 0.0000 [0.0000, 0.0000] | — |

## Scorer: activity

3,324,357 account-windows, 4,433 positive (prevalence 0.0013); unscored 0.

AUPRC 0.0385 [0.0221, 0.0574]; AUROC 0.4332 [0.4207, 0.4456]; precision at 100 0.9000, at 1,000 0.2022.

| Budget | Alerts | Alerts /1000 acc /day | False /1000 acc /day | Precision | Window recall | Max member FPR | Schemes | Detected [95% CI] | Random-alert [95%] | Linked | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fpr_0.001 | 3,312 | 0.5433 | 0.4975 | 0.0842 | 0.0629 | 0.0010 | 93 | 0.0108 [0.0000, 0.0323] | 0.0060 [0.0000, 0.0215] | 0.0000 [0.0000, 0.0000] | 0.0000 |
| fpr_0.0001 | 621 | 0.1019 | 0.0720 | 0.2931 | 0.0411 | 0.0002 | 93 | 0.0000 [0.0000, 0.0000] | 0.0011 [0.0000, 0.0108] | 0.0000 [0.0000, 0.0000] | — |
| alerts_1_per_1000_per_day | 6,144 | 1.01 | 0.9566 | 0.0506 | 0.0702 | 0.0018 | 93 | 0.0108 [0.0000, 0.0323] | 0.0113 [0.0000, 0.0323] | 0.0000 [0.0000, 0.0000] | 0.0000 |

Linked detection is 0 by construction until fusion exists (week 7): without incidents every alert is its own incident.

Peak memory 1243.2 MB.
