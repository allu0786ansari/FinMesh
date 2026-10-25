# Harness check · HI-Small

Federation B8, 6 h windows. Thresholds fitted on train, metrics on val. Both scorers are label-free references, not detectors: the **random** scorer must sit on its analytic baseline (AUPRC near the prevalence, AUROC near 0.5, detection inside the random-alert interval); **activity** (transaction count) shows the harness registers a weak signal.

## Scorer: random

707,997 account-windows, 1,150 positive (prevalence 0.0016); unscored 0.

AUPRC 0.0017 [0.0016, 0.0019]; AUROC 0.5095 [0.4920, 0.5249]; precision at 100 0.0000, at 1,000 0.0030.

| Budget | Alerts | Alerts /1000 acc /day | False /1000 acc /day | Precision | Window recall | Max member FPR | Schemes | Detected [95% CI] | Random-alert [95%] | Linked | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fpr_0.001 | 719 | 0.6979 | 0.6950 | 0.0028 | 0.0017 | 0.0013 | 68 | 0.0294 [0.0000, 0.0735] | 0.0075 [0.0000, 0.0294] | 0.0000 [0.0000, 0.0000] | 21.00 |
| fpr_0.0001 | 91 | 0.0883 | 0.0883 | 0.0000 | 0.0000 | 0.0002 | 68 | 0.0000 [0.0000, 0.0000] | 0.0009 [0.0000, 0.0147] | 0.0000 [0.0000, 0.0000] | — |
| alerts_1_per_1000_per_day | 1,024 | 0.9940 | 0.9901 | 0.0029 | 0.0026 | 0.0015 | 68 | 0.0441 [0.0000, 0.1029] | 0.0105 [0.0000, 0.0441] | 0.0000 [0.0000, 0.0000] | 6.00 |

## Scorer: activity

707,997 account-windows, 1,150 positive (prevalence 0.0016); unscored 0.

AUPRC 0.0435 [0.0158, 0.0712]; AUROC 0.4983 [0.4718, 0.5216]; precision at 100 0.5100, at 1,000 0.0803.

| Budget | Alerts | Alerts /1000 acc /day | False /1000 acc /day | Precision | Window recall | Max member FPR | Schemes | Detected [95% CI] | Random-alert [95%] | Linked | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fpr_0.001 | 711 | 0.6902 | 0.6145 | 0.1072 | 0.0661 | 0.0011 | 68 | 0.0000 [0.0000, 0.0000] | 0.0070 [0.0000, 0.0294] | 0.0000 [0.0000, 0.0000] | — |
| fpr_0.0001 | 117 | 0.1136 | 0.0883 | 0.2222 | 0.0226 | 0.0002 | 68 | 0.0000 [0.0000, 0.0000] | 0.0011 [0.0000, 0.0147] | 0.0000 [0.0000, 0.0000] | — |
| alerts_1_per_1000_per_day | 1,024 | 0.9940 | 0.9096 | 0.0814 | 0.0722 | 0.0014 | 68 | 0.0294 [0.0000, 0.0735] | 0.0105 [0.0000, 0.0441] | 0.0000 [0.0000, 0.0000] | 6.00 |

Linked detection is 0 by construction until fusion exists (week 7): without incidents every alert is its own incident.

Peak memory 296.9 MB.
