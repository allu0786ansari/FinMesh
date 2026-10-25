# Harness check · HI-Medium

Federation B8, 6 h windows. Thresholds fitted on train, metrics on val. Both scorers are label-free references, not detectors: the **random** scorer must sit on its analytic baseline (AUPRC near the prevalence, AUROC near 0.5, detection inside the random-alert interval); **activity** (transaction count) shows the harness registers a weak signal.

## Scorer: random

3,388,224 account-windows, 6,764 positive (prevalence 0.0020); unscored 0.

AUPRC 0.0020 [0.0019, 0.0021]; AUROC 0.5018 [0.4957, 0.5087]; precision at 100 0.0000, at 1,000 0.0020.

| Budget | Alerts | Alerts /1000 acc /day | False /1000 acc /day | Precision | Window recall | Max member FPR | Schemes | Detected [95% CI] | Random-alert [95%] | Linked | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fpr_0.001 | 3,435 | 0.5513 | 0.5493 | 0.0020 | 0.0010 | 0.0011 | 551 | 0.0054 [0.0000, 0.0127] | 0.0056 [0.0000, 0.0127] | 0.0000 [0.0000, 0.0000] | 0.0000 |
| fpr_0.0001 | 353 | 0.0567 | 0.0565 | 0.0000 | 0.0000 | 0.0001 | 551 | 0.0000 [0.0000, 0.0000] | 0.0006 [0.0000, 0.0036] | 0.0000 [0.0000, 0.0000] | — |
| alerts_1_per_1000_per_day | 6,240 | 1.00 | 0.9977 | 0.0022 | 0.0021 | 0.0019 | 551 | 0.0073 [0.0018, 0.0146] | 0.0102 [0.0018, 0.0200] | 0.0000 [0.0000, 0.0000] | 0.0000 |

## Scorer: activity

3,388,224 account-windows, 6,764 positive (prevalence 0.0020); unscored 0.

AUPRC 0.0269 [0.0160, 0.0369]; AUROC 0.4616 [0.4515, 0.4730]; precision at 100 0.9000, at 1,000 0.2040.

| Budget | Alerts | Alerts /1000 acc /day | False /1000 acc /day | Precision | Window recall | Max member FPR | Schemes | Detected [95% CI] | Random-alert [95%] | Linked | Median TTD h |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fpr_0.001 | 3,431 | 0.5506 | 0.5042 | 0.0829 | 0.0420 | 0.0010 | 551 | 0.0127 [0.0036, 0.0218] | 0.0056 [0.0000, 0.0127] | 0.0000 [0.0000, 0.0000] | 12.00 |
| fpr_0.0001 | 655 | 0.1051 | 0.0754 | 0.2824 | 0.0274 | 0.0002 | 551 | 0.0000 [0.0000, 0.0000] | 0.0011 [0.0000, 0.0054] | 0.0000 [0.0000, 0.0000] | — |
| alerts_1_per_1000_per_day | 6,240 | 1.00 | 0.9464 | 0.0522 | 0.0480 | 0.0018 | 551 | 0.0181 [0.0073, 0.0309] | 0.0102 [0.0018, 0.0200] | 0.0000 [0.0000, 0.0000] | 12.00 |

Linked detection is 0 by construction until fusion exists (week 7): without incidents every alert is its own incident.

Peak memory 1179.2 MB.
